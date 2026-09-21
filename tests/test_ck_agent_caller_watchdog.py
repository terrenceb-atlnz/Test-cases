"""ck-agent must stop a run whose CALLER has gone away.

THE GAP THIS CLOSES (2026-09-22, t44297 #6 — PLAN-durable-agent-review.md)
--------------------------------------------------------------------------
`cancel_job` already stops a run the user CANCELS: the browser hears the server say the job
is unwanted and POSTs /cancel. That whole path needs the tab alive.

When the TAB dies — a closed window, a dropped SSH session — nobody is left to send /cancel,
and agent.js's watcher loop died with it. The run continues to its full budget and is killed
by run_claude's own `communicate(timeout=...)`, so it is bounded, not infinite. But with the
server's 1800s floor that is up to half an hour of the user's own Claude seat spent on an
answer with nowhere to go: the browser that would POST it is gone, and a reloaded tab starts
a fresh broker with no memory of the job.

The server cannot help — the browser calls this agent, never the reverse — so the only local
evidence is the request socket. These drive REAL sockets, because "has the peer closed?" is
the entire behaviour and a mock would just be asserting the mock.
"""
import socket
import sys
import threading
import time
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "ask-ck" / "agent"))

import ck_agent  # noqa: E402


@pytest.fixture
def fast_poll(monkeypatch):
    monkeypatch.setattr(ck_agent, "_CALLER_POLL_SECONDS", 0.05)


@pytest.fixture
def pair():
    """A connected socket pair standing in for the browser <-> ck-agent request socket."""
    a, b = socket.socketpair()
    yield a, b
    for s in (a, b):
        try:
            s.close()
        except OSError:
            pass


@pytest.fixture
def killed(monkeypatch):
    """Record cancel_job calls instead of killing a real process."""
    seen = []
    monkeypatch.setattr(ck_agent, "cancel_job", lambda jid: (seen.append(jid), True)[1])
    return seen


def test_a_caller_that_disconnects_kills_the_run(pair, killed, fast_poll):
    server_side, caller = pair
    stop = threading.Event()
    t = threading.Thread(target=ck_agent.watch_caller, args=(server_side, "job-abc", stop))
    t.start()
    caller.close()                       # the tab goes away
    t.join(timeout=3)
    assert not t.is_alive(), "watchdog did not notice the disconnect"
    assert killed == ["job-abc"]


def test_a_run_that_finishes_normally_kills_NOTHING(pair, killed, fast_poll):
    """The failure mode that would matter most: a watchdog that cancels healthy work."""
    server_side, _caller = pair
    stop = threading.Event()
    t = threading.Thread(target=ck_agent.watch_caller, args=(server_side, "job-ok", stop))
    t.start()
    time.sleep(0.2)                      # several poll intervals with the caller attached
    stop.set()                           # run_claude returned
    t.join(timeout=3)
    assert not t.is_alive()
    assert killed == [], "a completed run was cancelled by its own watchdog"


def test_an_attached_but_SILENT_caller_is_not_treated_as_gone(pair, killed, fast_poll):
    """An open connection sending nothing is the NORMAL case for the whole call: the browser
    posts the body once and then waits. Only EOF means gone."""
    server_side, _caller = pair
    stop = threading.Event()
    t = threading.Thread(target=ck_agent.watch_caller, args=(server_side, "job-quiet", stop))
    t.start()
    time.sleep(0.3)
    assert killed == [], "a quiet but connected caller was mistaken for a dead one"
    stop.set()
    t.join(timeout=3)


def test_a_watchdog_error_never_kills_a_healthy_run(killed, fast_poll, monkeypatch):
    """A watchdog is insurance; an exception inside it must not cancel the work it guards."""
    class _Exploding:
        def fileno(self):
            raise RuntimeError("boom")
    monkeypatch.setattr(ck_agent.select, "select",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    stop = threading.Event()
    t = threading.Thread(target=ck_agent.watch_caller, args=(_Exploding(), "job-x", stop))
    t.start()
    t.join(timeout=3)
    assert not t.is_alive()
    assert killed == [], "an internal watchdog error cancelled the run"


def test_the_run_handler_starts_a_watchdog_only_when_there_is_a_job_to_cancel():
    """Source assertion: no job_id means cancel_job has nothing to key on, so the watchdog
    would be a thread that can only ever no-op."""
    src = (_REPO / "ask-ck" / "agent" / "ck_agent.py").read_text(encoding="utf-8")
    body = src[src.index("if not prompt:"):]
    assert "watch_caller" in body[:1500]
    assert "if job_id:" in body[:1500]
    assert "stop.set()" in body[:1500], "the watchdog is never stopped when the run returns"
