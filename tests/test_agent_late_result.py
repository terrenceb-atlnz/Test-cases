"""A result that arrives AFTER the caller gave up must be SAVED, not dropped.

Terrence, 2026-09-22 (t44297 #6, D6c): *"we should save what's in-place, and display the results
as-is. If some things returned, save and display that data."*

The 2026-09-09 loss was not the model's work — that finished. It was that once the browser was
gone the answer had nowhere to go: `deliver` looked only in `_inflight`, `_retire` had already
dropped the job, so the reply was discarded and the Claude seat that produced it wasted.

D6a settled that this is NOT a parking lot: nothing waits in memory to be polled for. A late
result is applied the instant it arrives; the retained entry exists only so `deliver` can still
RECOGNISE the job, and it expires on the registry's existing `max_idle` rather than a new horizon.
"""
import sys
import threading
import time
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SERVER = _REPO / "ask-ck" / "CK-main" / "CK_server"
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(_SERVER))

import agent_jobs  # noqa: E402


@pytest.fixture
def registry():
    return agent_jobs.AgentJobRegistry()


@pytest.fixture
def fast_pickup(monkeypatch):
    monkeypatch.setattr(agent_jobs, "_PICKUP_GRACE_SECONDS", 0.2)


def _claim_then_vanish(registry, sid, seen_after=0.0):
    """Claim the job, then let the tab die — the 2026-09-09 shape."""
    ids = {}

    def _run():
        time.sleep(0.05)
        got = registry.next_job(sid)
        if got:
            ids["job_id"] = got[0]
        registry._session_seen[sid] = seen_after

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return ids, t


def test_a_result_arriving_after_the_caller_gave_up_reaches_the_handler(registry, fast_pickup):
    got = []
    ids, t = _claim_then_vanish(registry, "s1")
    res = registry.submit("s1", "p", "opus", timeout=0.5, on_start=lambda j: setattr(j, "late", got.append))
    t.join(timeout=2)
    assert res["reason"] == "session_dropped"          # the caller was told what broke
    assert registry.deliver(ids["job_id"], "the answer", False, session_id="s1") is True
    assert got and got[0]["content"] == "the answer"


def test_a_job_with_no_handler_is_still_dropped(registry, fast_pickup):
    """Unchanged for every caller that has nowhere to put a late answer — no retention, no leak."""
    ids, t = _claim_then_vanish(registry, "s2")
    registry.submit("s2", "p", "opus", timeout=0.5)     # no on_start => job.late stays None
    t.join(timeout=2)
    assert registry._retired == {}
    assert registry.deliver(ids["job_id"], "the answer", False, session_id="s2") is False


def test_a_CANCELLED_job_is_never_resurrected(registry, fast_pickup):
    """A user who pressed Stop must not have the answer appear anyway. The cancel stamps a
    result, and a job that already HAS a result is finished — retention must skip it."""
    got = []

    def _on_start(job):
        job.late = got.append
        # what llm._call_claude_agent's _cancel does
        job.result = {"content": "cancelled", "error": True, "cancelled": True}
        job.event.set()

    registry.submit("s3", "p", "opus", timeout=0.5, on_start=_on_start)
    assert registry._retired == {}, "a cancelled job was kept for late delivery"
    assert got == []


def test_a_delivered_job_is_not_retained(registry, fast_pickup):
    """The ordinary success path must leave nothing behind."""
    def _work():
        time.sleep(0.05)
        jid = registry.next_job("s4")[0]
        registry.deliver(jid, "answer", False, session_id="s4")

    threading.Thread(target=_work, daemon=True).start()
    res = registry.submit("s4", "p", "opus", timeout=1.0, on_start=lambda j: setattr(j, "late", lambda r: None))
    assert res["content"] == "answer"
    assert registry._retired == {}


def test_a_late_deliver_from_the_WRONG_session_is_refused(registry, fast_pickup):
    """The session check that guards in-flight delivery must guard this path too, or a late
    job_id becomes a way to post into someone else's case."""
    got = []
    ids, t = _claim_then_vanish(registry, "s5")
    registry.submit("s5", "p", "opus", timeout=0.5, on_start=lambda j: setattr(j, "late", got.append))
    t.join(timeout=2)
    assert registry.deliver(ids["job_id"], "evil", False, session_id="someone-else") is False
    assert got == []


def test_a_handler_that_raises_cannot_break_the_browser_post(registry, fast_pickup):
    def _boom(_result):
        raise RuntimeError("handler exploded")

    ids, t = _claim_then_vanish(registry, "s6")
    registry.submit("s6", "p", "opus", timeout=0.5, on_start=lambda j: setattr(j, "late", _boom))
    t.join(timeout=2)
    assert registry.deliver(ids["job_id"], "answer", False, session_id="s6") is True


def test_retained_jobs_expire_on_the_EXISTING_horizon_not_a_new_one(registry, fast_pickup):
    """D6a: reuse `max_idle`, do not introduce a second TTL."""
    ids, t = _claim_then_vanish(registry, "s7")
    registry.submit("s7", "p", "opus", timeout=0.5, on_start=lambda j: setattr(j, "late", lambda r: None))
    t.join(timeout=2)
    assert ids["job_id"] in registry._retired
    registry._retired[ids["job_id"]] = (time.time() - registry._max_idle - 1,
                                        registry._retired[ids["job_id"]][1])
    registry.gc()
    assert registry._retired == {}
    assert registry.deliver(ids["job_id"], "too late", False, session_id="s7") is False
