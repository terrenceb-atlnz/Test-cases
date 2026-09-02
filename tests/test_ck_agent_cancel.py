"""ck-agent must be able to STOP a run it started.

THE DEFECT THIS FIXES (2026-09-02, AWPTCM-T44297)
-------------------------------------------------
`run_claude` used `subprocess.run`, which keeps no handle on the child, so a started
`claude` could not be stopped by anything. Pressing Stop in the Ask CK UI freed the server
(it stamps a cancelled result and wakes the blocked caller) and -- after the same day's
broker fix -- freed the browser's loop. But THIS machine kept grinding, producing an answer
already discarded and spending the user's own Claude seat to do it. With `generate_script`'s
budget floored to 1800s that is up to half an hour of paid work for nothing, every time
someone changes their mind.

Two properties, and the second is what a naive fix gets wrong:

  * a cancel must kill the PROCESS GROUP, not just the parent. `claude` spawns children;
    killing only the parent leaves them holding the seat and the pipes. The server's own
    `llm._run_cli` uses `start_new_session=True` for exactly this reason; this mirrors it.
  * a cancelled run must not be reported as a CLI FAULT. A killed process returns a
    negative code, and "claude CLI failed: exit code -9" sends the reader to debug their
    Claude install for something they did on purpose.

These drive a REAL subprocess (a fake `claude`), because process-group behaviour is the
whole point and a mock cannot exercise it.
"""
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "ask-ck" / "agent"))

import ck_agent  # noqa: E402


@pytest.fixture
def blocking_claude(tmp_path, monkeypatch):
    """A `claude` that spawns a DETACHED child and then blocks.

    The child is the point: it is what a parent-only kill leaves behind.
    """
    binp = tmp_path / "claude"
    binp.write_text("#!/bin/bash\nsleep 900 &\nsleep 900\n")
    binp.chmod(0o755)
    monkeypatch.setattr(ck_agent, "_find_claude", lambda: str(binp))
    return binp


@pytest.fixture
def quick_claude(tmp_path, monkeypatch):
    binp = tmp_path / "claude"
    binp.write_text('#!/bin/bash\ncat > /dev/null\necho \'{"result":"done"}\'\n')
    binp.chmod(0o755)
    monkeypatch.setattr(ck_agent, "_find_claude", lambda: str(binp))
    return binp


def _pgid_members(pgid):
    out = subprocess.run(["ps", "-eo", "pid=,pgid="], capture_output=True, text=True).stdout
    return [ln.split()[0] for ln in out.splitlines()
            if len(ln.split()) == 2 and ln.split()[1] == str(pgid)]


def _await_registered(job_id, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        with ck_agent._RUNNING_LOCK:
            proc = ck_agent._RUNNING.get(job_id)
        if proc is not None:
            return proc
        time.sleep(0.02)
    pytest.fail(f"run_claude never registered a process for {job_id}")


def test_cancel_kills_the_whole_process_group(blocking_claude):
    box = {}
    t = threading.Thread(
        target=lambda: box.update(r=ck_agent.run_claude("p", job_id="j1", timeout=60)),
        daemon=True)
    t.start()
    proc = _await_registered("j1")
    pgid = os.getpgid(proc.pid)
    assert len(_pgid_members(pgid)) >= 2, (
        f"expected the fake CLI plus its detached child in group {pgid}; the fixture is "
        f"not exercising the group case")

    assert ck_agent.cancel_job("j1") is True
    t.join(timeout=15)
    assert not t.is_alive(), "run_claude did not return after its process was killed"

    end = time.time() + 5
    while time.time() < end and _pgid_members(pgid):
        time.sleep(0.05)
    assert _pgid_members(pgid) == [], (
        f"processes survived the cancel: {_pgid_members(pgid)} — a parent-only kill "
        f"leaves the children holding the user's Claude seat")


def test_a_cancelled_run_is_not_reported_as_a_cli_fault(blocking_claude):
    box = {}
    t = threading.Thread(
        target=lambda: box.update(r=ck_agent.run_claude("p", job_id="j2", timeout=60)),
        daemon=True)
    t.start()
    _await_registered("j2")
    ck_agent.cancel_job("j2")
    t.join(timeout=15)
    r = box["r"]
    assert r["error"] is True
    assert r.get("cancelled") is True, r
    assert "cancelled" in r["content"].lower(), r
    assert "failed" not in r["content"].lower(), (
        f"a deliberate stop must not read as a CLI failure: {r['content']}")
    assert "exit code" not in r["content"].lower(), (
        f"a raw negative exit code sends the reader to debug their install: {r['content']}")


def test_cancelling_an_unknown_job_is_harmless():
    """The browser fires /cancel best-effort, and a job that already finished is the
    COMMON case — it must not raise, nor claim a kill that did not happen."""
    assert ck_agent.cancel_job("never-existed") is False
    assert ck_agent.cancel_job("") is False


def test_the_registry_is_emptied_when_a_run_finishes(quick_claude):
    """A leaked entry holds a dead Popen forever, so a later cancel of a REUSED id would
    report success while killing nothing."""
    r = ck_agent.run_claude("p", job_id="j3", timeout=30)
    assert r["error"] is False and r["content"] == "done", r
    with ck_agent._RUNNING_LOCK:
        assert "j3" not in ck_agent._RUNNING, "finished job left in the running registry"


def test_a_run_without_a_job_id_still_works(quick_claude):
    """job_id is new. A browser or server that predates it must not break the agent."""
    r = ck_agent.run_claude("p", timeout=30)
    assert r["error"] is False and r["content"] == "done", r


def test_timeout_reports_a_timeout_and_leaves_nothing_registered(blocking_claude):
    r = ck_agent.run_claude("p", job_id="j4", timeout=1)
    assert r["error"] is True
    assert "timed out" in r["content"].lower(), r
    with ck_agent._RUNNING_LOCK:
        assert "j4" not in ck_agent._RUNNING


def test_the_agent_serves_a_cancel_route():
    """Structural: cancel_job is unreachable from the browser without the route, and the
    browser is the only thing that knows a job was abandoned."""
    src = (_REPO / "ask-ck" / "agent" / "ck_agent.py").read_text(encoding="utf-8")
    assert '"/cancel"' in src, "no /cancel route — the browser cannot stop a local run"
    assert "cancel_job(" in src
    assert "start_new_session=True" in src, (
        "the CLI must run in its own process group. Two reasons, and the second is the "
        "dangerous one: without it cancel_job cannot reach the CLI's children, AND "
        "os.killpg(os.getpgid(child)) resolves to CK-AGENT'S OWN GROUP — so a cancel would "
        "kill the agent (and whatever launched it) instead of the job. Proven by mutation "
        "2026-09-02: flipping this to False made cancel_job kill the pytest runner.")
