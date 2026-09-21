"""When an agent-brokered call drops, the result must say WHICH part broke.

Terrence, 2026-09-22 (t44297 #6 / PLAN-durable-agent-review.md): *"If it drops, list why. Be as
explicit as possible with what part broke. I just want some basic error-handling."*

Before this, three genuinely different failures shared one sentence — "local Claude agent did not
respond in time. Is ck-agent running on your machine and this tab open?" — which asks the reader
to guess between an agent that never took the job, an agent that took it and hung, and a browser
that went away. All three are already distinguishable from `claimed_at` and session presence.

A failure the BROWSER can see never reaches this path: agent.js posts "local agent unreachable"
through /api/agent/result when its fetch to ck-agent throws. This is the path for when the
browser cannot tell us anything, which is exactly the 2026-09-09 case (the SSH session went).
"""
import sys
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
    return 0.2


def test_never_claimed_says_so_and_does_not_blame_a_slow_model(registry, fast_pickup):
    """A broker that is present but never takes the job. Distinct from 'nothing is there',
    which keeps its own `unclaimed` message and fast exit."""
    registry._session_seen["s1"] = time.time()          # present: polling, just not claiming
    res = registry.submit("s1", "p", "opus", timeout=0.5)
    assert res["error"] and res["timeout"]
    assert res["reason"] == "never_claimed"
    assert "no local Claude agent ever claimed it" in res["content"]
    assert "did not respond in time" not in res["content"]


def test_session_dropped_is_named_as_a_closed_tab_not_a_slow_model(registry, fast_pickup):
    """The 2026-09-09 shape: the job WAS claimed, then the browser went away. The message must
    say the work may have finished with nowhere to be delivered — that is the actionable part."""
    import threading

    def _claim():
        time.sleep(0.05)
        registry.next_job("s2")                        # claims, stamps claimed_at
        registry._session_seen["s2"] = 0.0             # ...then the tab/SSH dies

    threading.Thread(target=_claim, daemon=True).start()
    res = registry.submit("s2", "p", "opus", timeout=0.6)
    assert res["reason"] == "session_dropped"
    assert "CLAIMED this job at" in res["content"]
    assert "closed tab or a dropped connection" in res["content"]
    assert "NOT a slow model" in res["content"]


def test_claimed_but_silent_points_at_the_local_run_not_the_browser(registry, fast_pickup):
    """Claimed, browser still polling, no result: the browser is demonstrably fine, so the
    message must send the reader to ck-agent rather than to their tab."""
    import threading

    def _claim():
        time.sleep(0.05)
        registry.next_job("s3")
        registry._session_seen["s3"] = time.time()     # still polling, still alive

    threading.Thread(target=_claim, daemon=True).start()
    res = registry.submit("s3", "p", "opus", timeout=0.6)
    assert res["reason"] == "claimed_no_result"
    assert "is still" in res["content"] and "connected" in res["content"]
    assert "check ck-agent's console" in res["content"]


def test_every_drop_carries_a_machine_readable_reason_and_the_budget(registry, fast_pickup):
    """The prose is for a person; `reason` and `waited_s` are so a caller can branch or log
    without parsing English."""
    registry._session_seen["s4"] = time.time()
    res = registry.submit("s4", "p", "opus", timeout=0.4)
    assert res["reason"] in {"never_claimed", "session_dropped", "claimed_no_result"}
    assert res["waited_s"] == 0.4


def test_the_three_reasons_have_genuinely_different_text(registry, fast_pickup):
    """A taxonomy that renders the same sentence three times is not a taxonomy."""
    seen = {}
    registry._session_seen["a"] = time.time()
    seen["never_claimed"] = registry.submit("a", "p", "opus", timeout=0.4)["content"]

    import threading
    for sid, alive in (("b", False), ("c", True)):
        def _claim(sid=sid, alive=alive):
            time.sleep(0.05)
            registry.next_job(sid)
            registry._session_seen[sid] = time.time() if alive else 0.0
        threading.Thread(target=_claim, daemon=True).start()
        r = registry.submit(sid, "p", "opus", timeout=0.6)
        seen[r["reason"]] = r["content"]

    assert len(seen) == 3, f"expected three distinct reasons, got {sorted(seen)}"
    assert len(set(seen.values())) == 3, "two reasons render the same message"


def test_a_delivered_result_still_wins_over_any_reason(registry, fast_pickup):
    """The taxonomy must only describe FAILURE — a job that answers returns its answer."""
    import threading

    def _work():
        time.sleep(0.05)
        jid = registry.next_job("s5")[0]
        registry.deliver(jid, "the answer", False, session_id="s5")

    threading.Thread(target=_work, daemon=True).start()
    res = registry.submit("s5", "p", "opus", timeout=1.0)
    assert res["content"] == "the answer"
    assert "reason" not in res and not res.get("error")
