"""A stale in-process session cache must never overwrite newer work in ck.db.

Why this exists (2026-07-28). The documented symptom was "the server returns HTTP 200 while
the write never reaches ck.db", with the standing workaround "never trust the 200". Chasing
it reproduced the loss live: `generate_script` returned a 14,744-char script and a fresh
read of the DB still showed the previous 18,153-char one.

A controlled generate-then-read (no restarts, no edits between) PASSED, so the write path
itself is sound. The actual mechanism is the read side:

  * `pt_sessions` is a per-PROCESS dict, and `_pt_get` preferred it unconditionally.
  * More than one server process can be alive at once — a leftover `--reload` worker, or in
    this case a 24-day-old `drafting_server` instance still answering on another port from a
    module directory that no longer exists in the tree.
  * A request served by an instance with a warm, stale cache answers from that copy AND
    re-persists it, overwriting the newer script that had already committed.

So it never was a lost write. It was a stale copy winning a race, and looking identical to
a lost write from the outside.

Two fixes, both pinned here: `_pt_get` reloads when the DB is newer, and `_pt_persist`
raises instead of printing so a genuine save failure cannot masquerade as success.

Offline: no network, no LLM, no server. Uses the real module but its own fake sessions.
"""
import datetime
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
for _p in (REPO / "ask-ck" / "CK-main", REPO / "ask-ck" / "CK-main" / "CK_server"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


@pytest.fixture
def pc():
    from routers import pytest_create as mod
    return mod


def _mk(pc, key, code, stamp):
    """A minimal PtSession carrying `code` and an explicit updated_at.

    `updated_at` is passed at CONSTRUCTION, not assigned afterwards, so the model's
    UtcDatetime validator runs — the same path a session loaded from ck.db takes. The
    naive stamps these tests pass are exactly what pre-cutover rows hold, so this also
    covers the naive -> aware coercion. Assigning post-construction would bypass the
    validator and leave a naive value no production code path can produce.
    """
    sess = pc.PtSession(key=key, group="Port (7)", updated_at=stamp)
    sess.step6 = {"files": {"test": {"name": "t.py", "code": code}}}
    return sess


def test_db_wins_when_it_is_newer_than_the_process_cache(pc, monkeypatch):
    """The exact data-loss scenario: a stale cached copy must not be served or re-saved."""
    key = "AWPTCM-TSTALE1"
    old = _mk(pc, key, "OLD-STALE-CODE", datetime.datetime(2026, 7, 28, 9, 0, 0))
    new = _mk(pc, key, "NEW-COMMITTED-CODE", datetime.datetime(2026, 7, 28, 9, 30, 0))

    monkeypatch.setitem(pc.pt_sessions, key, old)
    monkeypatch.setattr(pc, "_pt_session_updated_at", lambda k: "2026-07-28T09:30:00")
    monkeypatch.setattr(pc, "_pt_load", lambda k: new)

    got = pc._pt_get(key)
    code = got.step6["files"]["test"]["code"]
    assert code == "NEW-COMMITTED-CODE", (
        "the stale cache won — a later persist would overwrite the newer script")
    # and the cache is repaired, so the next call cannot regress
    assert pc.pt_sessions[key] is new


def test_cache_is_kept_when_it_is_at_least_as_new(pc, monkeypatch):
    """No needless reload: the cache is normally correct and reloading every call would
    make the DB the hot path for every request."""
    key = "AWPTCM-TSTALE2"
    cached = _mk(pc, key, "CACHED", datetime.datetime(2026, 7, 28, 9, 30, 0))
    monkeypatch.setitem(pc.pt_sessions, key, cached)
    monkeypatch.setattr(pc, "_pt_session_updated_at", lambda k: "2026-07-28T09:30:00")
    monkeypatch.setattr(pc, "_pt_load",
                        lambda k: pytest.fail("reloaded despite an up-to-date cache"))
    assert pc._pt_get(key) is cached


def test_cache_is_kept_when_the_db_has_no_row(pc, monkeypatch):
    """A session created in memory but not yet persisted must still be served."""
    key = "AWPTCM-TSTALE3"
    cached = _mk(pc, key, "IN-MEMORY-ONLY", datetime.datetime(2026, 7, 28, 9, 30, 0))
    monkeypatch.setitem(pc.pt_sessions, key, cached)
    monkeypatch.setattr(pc, "_pt_session_updated_at", lambda k: None)
    monkeypatch.setattr(pc, "_pt_load", lambda k: pytest.fail("reloaded on a missing row"))
    assert pc._pt_get(key) is cached


def test_reload_failure_falls_back_to_the_cache(pc, monkeypatch):
    """If the DB says it is newer but the payload will not load, serving the cache beats
    raising — the alternative is bricking the case."""
    key = "AWPTCM-TSTALE4"
    cached = _mk(pc, key, "CACHED", datetime.datetime(2026, 7, 28, 9, 0, 0))
    monkeypatch.setitem(pc.pt_sessions, key, cached)
    monkeypatch.setattr(pc, "_pt_session_updated_at", lambda k: "2026-07-28T09:30:00")
    monkeypatch.setattr(pc, "_pt_load", lambda k: None)
    assert pc._pt_get(key) is cached


def test_missing_session_still_404s(pc, monkeypatch):
    from fastapi import HTTPException
    monkeypatch.setattr(pc, "_pt_load", lambda k: None)
    pc.pt_sessions.pop("AWPTCM-TNOPE", None)
    with pytest.raises(HTTPException) as ei:
        pc._pt_get("AWPTCM-TNOPE")
    assert ei.value.status_code == 404


def test_persist_failure_raises_instead_of_printing(pc, monkeypatch):
    """The core of "never trust the 200": a save failure used to be a `print`, so the
    endpoint returned success and the user lost a multi-minute LLM round trip silently."""
    from fastapi import HTTPException

    def boom(*a, **k):
        raise RuntimeError("attempt to write a readonly database")

    monkeypatch.setattr(pc.dbx, "save_session", boom)
    sess = _mk(pc, "AWPTCM-TFAIL", "CODE", datetime.datetime(2026, 7, 28, 9, 0, 0))
    with pytest.raises(HTTPException) as ei:
        pc._pt_persist(sess)
    assert ei.value.status_code == 500
    assert "NOT saved" in str(ei.value.detail), "the error must say the work was lost"


def test_persist_stamps_updated_at(pc, monkeypatch):
    """`updated_at` is what the staleness comparison rests on, so it must always advance."""
    saved = {}
    monkeypatch.setattr(pc.dbx, "save_session",
                        lambda kind, key, data: saved.update(data=data))
    sess = _mk(pc, "AWPTCM-TSTAMP", "CODE", datetime.datetime(2020, 1, 1))
    before = sess.updated_at
    pc._pt_persist(sess)
    assert sess.updated_at > before
    assert saved, "save_session was never called"


def test_source_does_not_prefer_the_cache_unconditionally(pc):
    """Structural guard: `pt_sessions.get(key) or _pt_load(key)` is the exact expression
    that caused the loss. It must not come back."""
    import inspect
    src = inspect.getsource(pc._pt_get)
    assert "pt_sessions.get(key) or _pt_load(key)" not in src, (
        "the unconditional cache preference is back — a stale instance can overwrite "
        "newer committed work again")
    assert "_pt_session_updated_at" in src, "the staleness comparison is gone"
