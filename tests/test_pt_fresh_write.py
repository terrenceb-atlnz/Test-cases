"""A long LLM call must not persist the session snapshot it loaded BEFORE the call.

THE DEFECT THIS FIXES (2026-09-02, AWPTCM-T44297 — 8 lost calls, ~235k tokens)
------------------------------------------------------------------------------
Every long LLM endpoint did: load the session, spend 30-600s in the model, then persist
THAT SNAPSHOT. `_pt_persist` compare-and-swaps on `rev` (locks.next_rev), so any other
write inside the window made the snapshot stale and the write was refused with HTTP 409 —
discarding the entire round trip.

The window is wide enough that ORDINARY USE lands in it. Measured on a 31-step
suggest-all: clicking "Save Selections" — the reviewer shortlisting the steps already
done, which is exactly what that panel is for — bumped the rev every 20-45s. Steps 10 and
13-19 each completed their LLM call and were then thrown away:

    step  9 -> 200      step 13 -> 409      step 17 -> 409
    step 10 -> 409      step 14 -> 409      step 18 -> 409
    step 11 -> 200      step 15 -> 409      step 19 -> 409
    step 12 -> 200      step 16 -> 409      step 20 -> 200

and `step_matches` in ck.db held keys 1-9, 11, 12, 20, 21 — precisely the 200s. In the UI
this was invisible: the coverage bar simply stopped advancing, which reads as "the LLM
stopped suggesting".

WHAT IS NOT THE FIX, and is pinned as such below: weakening the CAS, or passing force.
`next_rev` exists to stop one writer clobbering another's work. The fix is to stop writing
a stale WHOLE session — apply only the fields the endpoint owns, onto a fresh copy — so
that a concurrent write to an unrelated field is no longer a conflict at all, while a
genuine same-field conflict still loses and still refuses.
"""
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
for _p in (REPO / "ask-ck" / "CK-main", REPO / "ask-ck" / "CK-main" / "CK_server"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import locks  # noqa: E402


@pytest.fixture
def pc():
    from routers import pytest_create as mod
    return mod


@pytest.fixture
def sess(pc):
    s = pc.PtSession(key="AWPTCM-TFRESH")
    s.step3 = {"step_matches": {}, "selections": {}}
    return s


def test_it_reloads_before_applying(pc, sess, monkeypatch):
    """The whole point: the mutation must see the CURRENT row, not the caller's copy."""
    loads = []

    def _load(k):
        loads.append(k)
        return sess

    monkeypatch.setattr(pc, "_pt_load", _load)
    monkeypatch.setattr(pc, "pt_sessions", {})
    monkeypatch.setattr(pc, "_pt_persist", lambda s: None)

    pc._pt_persist_fresh("AWPTCM-TFRESH", lambda fr: fr.step3.update({"touched": True}))
    assert loads == ["AWPTCM-TFRESH"], "must reload the session before applying"
    assert sess.step3["touched"] is True


def test_a_stale_write_is_retried_against_a_reloaded_copy(pc, sess, monkeypatch):
    """The exact T44297 shape: a concurrent save lands mid-LLM, so the first CAS fails.

    The retry must RE-READ and RE-APPLY — not re-submit the same rejected payload, which
    would fail forever.
    """
    attempts = {"n": 0}
    monkeypatch.setattr(pc, "_pt_load", lambda k: sess)
    monkeypatch.setattr(pc, "pt_sessions", {})

    def _persist(s):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise locks.StaleWriteError("pt", s.key)

    monkeypatch.setattr(pc, "_pt_persist", _persist)

    applied = []
    pc._pt_persist_fresh("AWPTCM-TFRESH", lambda fr: applied.append(1))
    assert attempts["n"] == 2, "a stale write must be retried"
    assert len(applied) == 2, "the retry must RE-APPLY the mutation, not resubmit it"


def test_it_gives_up_rather_than_retrying_forever(pc, sess, monkeypatch):
    """A permanently-contended case must surface the conflict, not spin."""
    monkeypatch.setattr(pc, "_pt_load", lambda k: sess)
    monkeypatch.setattr(pc, "pt_sessions", {})
    n = {"c": 0}

    def _always_stale(s):
        n["c"] += 1
        raise locks.StaleWriteError("pt", s.key)

    monkeypatch.setattr(pc, "_pt_persist", _always_stale)
    with pytest.raises(locks.StaleWriteError):
        pc._pt_persist_fresh("AWPTCM-TFRESH", lambda fr: None)
    assert n["c"] == pc._PT_FRESH_WRITE_ATTEMPTS


def test_a_lock_conflict_is_NOT_retried(pc, sess, monkeypatch):
    """Another holder owns the case. Retrying would neither succeed nor be polite, and it
    must not be mistaken for the stale-copy case that a retry does fix."""
    monkeypatch.setattr(pc, "_pt_load", lambda k: sess)
    monkeypatch.setattr(pc, "pt_sessions", {})
    n = {"c": 0}

    def _locked(s):
        n["c"] += 1
        raise locks.LockConflictError("pt", s.key, "someone else", "earlier")

    monkeypatch.setattr(pc, "_pt_persist", _locked)
    with pytest.raises(locks.LockConflictError):
        pc._pt_persist_fresh("AWPTCM-TFRESH", lambda fr: None)
    assert n["c"] == 1, "a lock conflict must fail on the first attempt"


def test_it_does_not_use_pt_get(pc):
    """`_pt_get` prefers whichever of memory/DB is newer by `updated_at` — and a FAILED
    `_pt_persist` has already stamped `updated_at = now` on the in-memory copy before
    `next_rev` raised. So a retry through `_pt_get` would judge the poisoned cache newer
    than the DB and hand back the same stale-rev object forever. The authoritative copy
    for a CAS is the row the CAS compares against.
    """
    src = (REPO / "ask-ck" / "CK-main" / "CK_server" / "routers"
           / "pytest_create.py").read_text(encoding="utf-8")
    body = src[src.index("def _pt_persist_fresh("):]
    body = _code_only(body[:body.index("\ndef ", 1)])
    assert "_pt_load(" in body
    assert "_pt_get(" not in body, (
        "_pt_persist_fresh must reload with _pt_load; _pt_get's newer-of-memory-or-DB "
        "heuristic is defeated by the updated_at a failed persist already wrote")


def _code_only(body: str) -> str:
    """Strip the docstring and comments.

    Needed because this helper's own prose NAMES the things the assertions forbid — the
    same trap the frontend specs strip comments for. Without this the test passed on the
    docstring and told you nothing about the code.
    """
    import re
    body = re.sub(r'"""[\s\S]*?"""', "", body, count=1)     # the docstring
    return re.sub(r"^\s*#.*$", "", body, flags=re.M)          # comment lines


def test_the_cas_is_never_bypassed(pc):
    """The fix must not be 'stop checking'. No force flag, no rev assignment that skips
    the compare-and-swap — a genuine same-field conflict must still refuse."""
    src = (REPO / "ask-ck" / "CK-main" / "CK_server" / "routers"
           / "pytest_create.py").read_text(encoding="utf-8")
    body = src[src.index("def _pt_persist_fresh("):]
    body = _code_only(body[:body.index("\ndef ", 1)])
    for bad in ("force", "next_rev", "sess.rev ="):
        assert bad not in body, (
            f"_pt_persist_fresh must go through _pt_persist's normal CAS; found {bad!r} "
            f"in its code")


LONG_LLM_ENDPOINTS = [
    "extract_sequence",
    "gather_fragments",
    "generate_script",
    "fix_script",
]


@pytest.mark.parametrize("fn", LONG_LLM_ENDPOINTS)
def test_every_long_llm_endpoint_writes_a_fresh_copy(fn):
    """Structural, and the reason this is a class rather than one bug.

    Each of these loads the session, calls the model for 300-600s, then writes. Any of
    them persisting its pre-call snapshot is one concurrent click away from discarding a
    multi-minute call. `suggest_scripts_step` is covered separately — it delegates to
    `_persist_step_matches`, which owns the fresh write.
    """
    src = (REPO / "ask-ck" / "CK-main" / "CK_server" / "routers"
           / "pytest_create.py").read_text(encoding="utf-8")
    start = src.index(f"async def {fn}(")
    body = src[start:]
    nxt = body.find("\n@router.")
    body = body[:nxt] if nxt > 0 else body
    llm_at = body.find("run_prompt")
    assert llm_at > 0, f"{fn} no longer calls run_prompt — re-check this test"
    after = body[llm_at:]
    assert "_pt_persist_fresh(" in after, (
        f"{fn} does not use _pt_persist_fresh after its LLM call")
    assert "_pt_persist(sess)" not in after, (
        f"{fn} still persists its pre-LLM snapshot after the model call — that is the "
        f"T44297 defect: a concurrent save discards the whole round trip with a 409")


def test_suggest_scripts_step_delegates_the_fresh_write():
    src = (REPO / "ask-ck" / "CK-main" / "CK_server" / "routers"
           / "pytest_create.py").read_text(encoding="utf-8")
    start = src.index("async def suggest_scripts_step(")
    body = src[start:]
    body = body[:body.find("\n@router.")]
    assert "_persist_step_matches(key," in body, (
        "the per-step suggest must hand the KEY to _persist_step_matches, not a snapshot")
    assert "sess.step3 =" not in body, (
        "the endpoint must not write step3 on its pre-LLM snapshot; provenance rides "
        "along to _persist_step_matches so both fields land in one fresh write")
    helper = src[src.index("def _persist_step_matches("):]
    helper = helper[:helper.index("\n@router.")]
    assert "_pt_persist_fresh(" in helper
