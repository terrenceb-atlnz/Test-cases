"""`load_case(..., fresh=True)` — the "Load Case & New Session" button.

Why this exists (2026-09-17). A case edited UPSTREAM (objective/steps changed, re-exported
and pushed) kept generating from the OLD sequence in the PyTest Creator. That is not a bug in
the reload: `load_case` reuses an existing session by design — reusing the stored session is
exactly what preserves the step2-step8 work across a plain reload. The gap was that there was
no way to say "throw the stored session away and reload from the freshly exported bundle on
disk". `fresh=True` is that opt-in, and this pins its four contracts:

  * fresh reloads objective + steps from the on-disk refined bundle, discarding the stale
    session (cache row + ck.db row);
  * a plain load (fresh=False) still reuses the stored session — the by-design behaviour;
  * fresh resolves the disk bundle BEFORE deleting anything, so a case with no drop-in raises
    404 with the stored session left intact (no data loss on a failed rebuild);
  * fresh declines — touching nothing — when another seat holds the live lock.

Offline: no network, no LLM, no server. Real module, monkeypatched persistence + locks.
"""
import pathlib
import sys

import asyncio
import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
for _p in (REPO / "ask-ck" / "CK-main", REPO / "ask-ck" / "CK-main" / "CK_server"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


@pytest.fixture
def pc():
    from routers import pytest_create as mod
    return mod


KEY = "AWPTCM-TFRESH1"

STALE = {KEY: {"objective": "OLD objective",
               "testScript": {"steps": [{"description": "old step one"}]}}}
DISK = {KEY: {"objective": "NEW objective",
              "testScript": {"steps": [{"description": "new step one"},
                                       {"description": "new step two"}]}}}


def _wire(pc, monkeypatch, *, by_me=True, disk=DISK, disk_raises=False):
    """Stub persistence + locks around load_case; return the recorders.

    A stale session sits in BOTH the process cache and _pt_load, so any code path that reads
    the stored copy is visible in the result (it carries OLD objective / 1 step). The disk
    reader returns NEW / 2 steps, or 404s when `disk_raises`.
    """
    from fastapi import HTTPException
    stale = pc.PtSession(key=KEY, group="Port (7)", payload=STALE)
    deleted, persisted = [], []

    monkeypatch.setattr(pc, "_data", lambda request: {})
    monkeypatch.setattr(pc, "pt_sessions", {KEY: stale})
    monkeypatch.setattr(pc, "_pt_load", lambda k: stale)
    monkeypatch.setattr(pc, "_pt_persist", lambda s: persisted.append(s))
    monkeypatch.setattr(pc, "_sweep_stale_runs", lambda s: False)
    monkeypatch.setattr(pc.dbx, "delete_session", lambda kind, k: deleted.append((kind, k)))
    monkeypatch.setattr(pc.locks, "acquire", lambda kind, k: {"by_me": by_me})

    def _refined(k):
        if disk_raises:
            raise HTTPException(404, f"{k} is not a Complete case (no refined zephyr_payload.json).")
        return "Port (7)", disk, "trace-md"
    monkeypatch.setattr(pc, "_find_refined_case", _refined)
    return {"stale": stale, "deleted": deleted, "persisted": persisted}


def test_fresh_reloads_from_disk_and_discards_the_stale_session(pc, monkeypatch):
    rec = _wire(pc, monkeypatch)
    out = asyncio.run(pc.load_case(KEY, object(), fresh=True))

    # Served from the DISK bundle, not the stale stored session.
    assert out["read_only"] is False
    assert out["objective"] == "NEW objective"
    assert [s["description"] for s in out["steps"]] == ["new step one", "new step two"]
    # The stale ck.db row was deleted, and what got persisted is the disk payload.
    assert rec["deleted"] == [("pt", KEY)]
    assert rec["persisted"] and rec["persisted"][-1].payload == DISK
    assert pc.pt_sessions[KEY].payload == DISK


def test_plain_load_reuses_the_stored_session(pc, monkeypatch):
    # The by-design behaviour the fresh path deliberately does NOT change.
    rec = _wire(pc, monkeypatch)
    out = asyncio.run(pc.load_case(KEY, object(), fresh=False))

    assert out["objective"] == "OLD objective"
    assert [s["description"] for s in out["steps"]] == ["old step one"]
    assert rec["deleted"] == []   # nothing discarded on a plain reload


def test_fresh_does_not_delete_when_the_disk_bundle_is_missing(pc, monkeypatch):
    # Safe ordering: resolve disk first, so a 404 leaves the stored session intact.
    from fastapi import HTTPException
    rec = _wire(pc, monkeypatch, disk_raises=True)

    with pytest.raises(HTTPException) as ei:
        asyncio.run(pc.load_case(KEY, object(), fresh=True))
    assert ei.value.status_code == 404
    assert rec["deleted"] == []                       # nothing was destroyed
    assert pc.pt_sessions[KEY] is rec["stale"]        # stored session still there


def test_fresh_declines_when_another_seat_holds_the_lock(pc, monkeypatch):
    called = []
    rec = _wire(pc, monkeypatch, by_me=False)
    monkeypatch.setattr(pc, "_find_refined_case",
                        lambda k: called.append(k) or ("Port (7)", DISK, ""))

    out = asyncio.run(pc.load_case(KEY, object(), fresh=True))

    assert out["read_only"] is True
    assert rec["deleted"] == []      # did not overwrite the other seat's session
    assert called == []              # did not even attempt a disk rebuild
