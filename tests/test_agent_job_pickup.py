"""An unclaimed agent job fails fast; a claimed one gets the whole budget.

THE DEFECT THIS PINS (2026-09-01, AWPTCM-T33351 — a 30-minute hang)
-------------------------------------------------------------------
`submit` was a single `job.event.wait(timeout)`. A generate was enqueued for a browser
whose broker loop had died two minutes earlier — a frozen background tab left
`ckBrokerRunning` stuck true, and both restart paths in llm.js begin
`if (ckBrokerRunning) return;`, so it could never revive. Nothing ever claimed the job,
and the caller blocked for the FULL budget before reporting "did not respond in time".

Measured in the journal: `/api/agent/next` polls were perfectly regular at ~25.4s from
12:45:08 to 12:51:54, then stopped dead — no tail-off, which is what separates a renderer
freeze from timer throttling. The generate started at 12:53:54, two minutes after the last
poll, and the debug log recorded `1800.0s, err=True` with zero `/api/agent/result` calls.

At the old 600s budget this wasted ten minutes; once `generate_script`'s budget was floored
to 1800s it wasted thirty. The message was misleading too — "did not respond" describes a
slow agent, not a job nobody ever picked up.

WHY PHASE 2 HAS NO LIVENESS CHECK, AND WHY THAT IS PINNED HERE
--------------------------------------------------------------
The obvious next step — fail when the owning session stops polling — is WRONG and would
break every long generation. agent.js does not long-poll while it is running a job: it is
awaiting its local ck-agent. So `_session_seen` goes stale for the entire duration of every
legitimate 300-800s call. `test_a_claimed_job_is_not_judged_on_session_silence` exists so
nobody adds that check later on reasoning that sounds correct.
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

import agent_jobs  # noqa: E402  (CK_server flat-module layout)


@pytest.fixture
def registry():
    return agent_jobs.AgentJobRegistry()


@pytest.fixture
def fast_pickup(monkeypatch):
    """Shrink the pickup grace so these tests run in milliseconds, not a minute."""
    monkeypatch.setattr(agent_jobs, "_PICKUP_GRACE_SECONDS", 0.3)
    return 0.3


def test_an_unclaimed_job_fails_in_the_pickup_window_not_the_full_budget(registry, fast_pickup):
    """The actual defect: budget 30s, nobody polling — must return in ~0.3s, not 30."""
    t0 = time.monotonic()
    res = registry.submit("sess-nobody", "prompt", "opus", timeout=30)
    elapsed = time.monotonic() - t0
    assert res["error"] and res.get("timeout")
    assert res.get("unclaimed") is True, res
    assert elapsed < 5, (
        f"submit blocked {elapsed:.1f}s for a job nobody claimed; it must give up after "
        f"the pickup grace, not the caller's whole budget")


def test_the_unclaimed_message_says_nobody_took_it(registry, fast_pickup):
    """"did not respond in time" sent the user looking at their agent and their network.
    The honest message names the real cause and the real fix (reload the tab)."""
    res = registry.submit("sess-nobody", "prompt", "opus", timeout=30)
    msg = res["content"].lower()
    assert "picked up" in msg or "pick up" in msg, res["content"]
    assert "reload" in msg, "the message must name the fix — reloading revives a wedged broker"


def test_a_claimed_job_gets_the_whole_budget(registry, fast_pickup):
    """Claiming must buy the full remaining time. Delivering after the pickup grace has
    expired — the shape of every real generation, which takes minutes — must still work."""
    def worker():
        for _ in range(200):
            job = registry.next_job("sess-live")
            if job:
                time.sleep(fast_pickup * 3)     # well past the pickup window
                registry.deliver(job[0], "the script", False, session_id="sess-live")
                return
            time.sleep(0.01)

    threading.Thread(target=worker, daemon=True).start()
    res = registry.submit("sess-live", "prompt", "opus", timeout=30)
    assert res.get("error") is not True, res
    assert res["content"] == "the script"


def test_a_claimed_job_is_not_judged_on_session_silence(registry, fast_pickup):
    """PIN: no liveness check in phase 2.

    agent.js stops long-polling while running a job, so a session that has gone quiet is
    the NORMAL state of a long generation, not evidence of a dead tab. A staleness check
    here would kill exactly the calls the budget exists for.
    """
    src = (_SERVER / "agent_jobs.py").read_text(encoding="utf-8")
    # submit() ALONE — bounded by the next method, not by a named one. Slicing to a
    # specific sibling broke the moment a new method was inserted between them, and the
    # failure looked like the invariant had been violated when only the slice had moved.
    start = src.index("    def submit(")
    body = src[start:]
    body = body[:body.index("\n    def ", 1)]
    after_claim = body[body.index("if not got:", body.index("unclaimed")):]
    assert "_session_seen" not in after_claim, (
        "phase 2 must not consult _session_seen — a browser running a job legitimately "
        "stops polling, so silence there is normal, not a fault")


def test_next_job_stamps_the_claim(registry):
    """The claim signal must come from an actual claim. `_inflight` cannot serve: submit
    puts the job there immediately, so it means 'awaiting a result', not 'taken'."""
    done = threading.Event()
    seen = {}

    def caller():
        seen["res"] = registry.submit("sess-c", "p", "opus", timeout=2)
        done.set()

    threading.Thread(target=caller, daemon=True).start()
    for _ in range(200):
        job = registry.next_job("sess-c")
        if job:
            break
        time.sleep(0.01)
    else:
        pytest.fail("job never appeared for the poller")
    inflight = list(registry._inflight.values())
    assert inflight and inflight[0].claimed_at is not None, "next_job must stamp claimed_at"
    registry.deliver(job[0], "ok", False, session_id="sess-c")
    assert done.wait(5)


def test_an_unclaimed_job_is_removed_from_the_queue(registry, fast_pickup):
    """A job abandoned at the pickup deadline must not be handed to a later poller as if
    it were live work — the caller is gone and its result would be discarded."""
    registry.submit("sess-gone", "p", "opus", timeout=30)
    assert registry.next_job("sess-gone") is None, (
        "an abandoned job was still queued and would be served to the next browser")


def test_a_BUSY_broker_is_not_mistaken_for_an_absent_one(registry, fast_pickup):
    """THE REGRESSION THIS PINS (2026-09-02, AWPTCM-T44297).

    One broker runs ONE job at a time, so while it is inside its local ck-agent call it is
    not long-polling. The first version of the pickup grace read that as "nobody is there"
    and failed the next queued job at 60s — so a second LLM action during a long generate,
    and every action for the whole remaining budget after a Stop, died instantly. Before the
    grace existed it would have waited and been served when the broker came free.

    Here: session S has a job it already claimed (busy). A second job must NOT be
    fast-failed on the pickup deadline.
    """
    busy = {}
    t = threading.Thread(
        target=lambda: busy.update(r=registry.submit("S", "first", "opus", timeout=30)),
        daemon=True)
    t.start()
    for _ in range(200):                      # let the broker claim job one
        j = registry.next_job("S")
        if j:
            busy["job_id"] = j[0]
            break
        time.sleep(0.01)
    else:
        pytest.fail("first job was never claimable")

    # Make the poll look old, so presence can only come from the claimed job.
    registry._session_seen["S"] = time.time() - 10_000

    second = {}
    t2 = threading.Thread(
        target=lambda: second.update(r=registry.submit("S", "second", "opus", timeout=3)),
        daemon=True)
    t2.start()
    t2.join(timeout=10)
    assert "r" in second, "second submit never returned"
    assert second["r"].get("unclaimed") is not True, (
        "a queued job was abandoned while the broker was BUSY on a claimed job — that is "
        "the T44297 regression: busy is not absent")

    registry.deliver(busy["job_id"], "done", False, session_id="S")
    t.join(timeout=10)


def test_a_recently_polling_broker_is_not_abandoned(registry, fast_pickup):
    """The other presence signal on its own: no claimed job, but the session polled a
    moment ago. An idle-but-live broker must be waited for, not written off."""
    registry._session_seen["S2"] = time.time()      # polled just now
    t0 = time.monotonic()
    res = registry.submit("S2", "p", "opus", timeout=1)
    assert res.get("unclaimed") is not True, (
        f"a live, recently-polling session was declared absent: {res}")
    assert time.monotonic() - t0 >= 0.9, "should have waited out the budget, not fast-failed"


def test_an_absent_agent_is_still_detected(registry, fast_pickup):
    """The presence test must not become trivially true.

    Both signals are about OTHER activity — a recent poll, or a job someone already
    claimed. Neither can be satisfied by the calling job itself, so a genuinely absent
    agent is still caught and the original 30-minute hang cannot return.
    """
    assert registry.session_present("nobody") is False
    res = registry.submit("nobody", "p", "opus", timeout=30)
    assert res.get("unclaimed") is True, res


def test_the_pickup_grace_is_longer_than_the_long_poll_window(registry):
    """Ties the constant to the client that has to beat it. agent.js polls with wait=25,
    so a grace at or under 25s would abandon jobs a healthy broker was about to claim."""
    agent_js = (_SERVER / "static" / "js" / "agent.js").read_text(encoding="utf-8")
    assert "wait=25" in agent_js, "agent.js's long-poll window changed — re-check the grace"
    assert agent_jobs._PICKUP_GRACE_SECONDS > 25, (
        f"pickup grace {agent_jobs._PICKUP_GRACE_SECONDS}s is not comfortably above the "
        f"25s long-poll window; a live broker could be abandoned mid-poll")


def test_cancel_still_wakes_the_wait_during_pickup(registry, fast_pickup):
    """The Stop button stamps a result and sets the Event. That must work in phase 1 too —
    splitting the wait in two is exactly where a cancel path gets dropped."""
    def canceller(job):
        def go():
            time.sleep(0.05)
            job.result = {"content": "cancelled", "error": True, "cancelled": True}
            job.event.set()
        threading.Thread(target=go, daemon=True).start()

    res = registry.submit("sess-x", "p", "opus", timeout=30, on_start=canceller)
    assert res.get("cancelled") is True, res
    assert res.get("unclaimed") is not True, "a cancel must not be reported as unclaimed"
