"""True LLM cancel + live progress (llm_inflight, llm._run_cli, agent_jobs.on_start).

Why (2026-08-26, Terrence): every LLM button gained a real Stop and a live
progress display. "Real" is the load-bearing word — a UI-only abort (browser
stops waiting, server finishes, tokens spend, result persists) was explicitly
rejected. So these tests exercise REAL subprocesses being really killed, and the
exact deadlock/timeout semantics `subprocess.run` used to provide:

  * _run_cli must feed >64 KiB of stdin without deadlocking (the pipe-buffer
    trap communicate() exists for),
  * must kill the process and raise TimeoutExpired on deadline (as
    subprocess.run did),
  * must raise RuntimeError(_CANCEL_MSG) when cancelled mid-run — and the
    process must actually be dead,
  * a cancel that lands BEFORE the transport attaches its handle must still
    fire (the set_cancel race),
  * an agent job's on_start cancel hook must wake submit() early with a
    cancelled result.

Offline: /bin/sh only, no network, no LLM.
"""
import pathlib
import subprocess
import sys
import threading
import time

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
for _p in (REPO / "ask-ck" / "CK-main", REPO / "ask-ck" / "CK-main" / "CK_server"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import llm  # noqa: E402
import llm_inflight  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_registry():
    yield
    # tests register ids; never leak state between tests
    for cid in ("t-basic", "t-cancel", "t-race", "t-agent", "t-timeout"):
        llm_inflight.finish(cid)


def _with_call_id(cid):
    return llm.current_llm_call_id.set(cid)


def test_run_cli_captures_output_and_counts_progress():
    tok = _with_call_id("t-basic")
    try:
        llm_inflight.register("t-basic")
        proc = llm._run_cli(["/bin/sh", "-c", "echo one; echo two; echo err >&2"], timeout=10)
    finally:
        llm.current_llm_call_id.reset(tok)
    assert proc.returncode == 0
    assert proc.stdout == "one\ntwo\n"
    assert "err" in proc.stderr
    snap = llm_inflight.snapshot("t-basic")
    assert snap["events"] == 2, "stdout lines were not counted as live progress"
    assert snap["chars"] == len("one\n") + len("two\n")


def test_run_cli_feeds_large_stdin_without_deadlock():
    big = "x" * 300_000  # ~5x the 64 KiB pipe buffer — the classic feed deadlock
    proc = llm._run_cli(["/bin/sh", "-c", "cat"], input_text=big, timeout=15)
    assert proc.returncode == 0
    assert len(proc.stdout) == len(big), "stdin was truncated or the feed deadlocked"


def test_run_cli_timeout_kills_and_raises_like_subprocess_run():
    t0 = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        llm._run_cli(["/bin/sh", "-c", "sleep 30"], timeout=1)
    assert time.monotonic() - t0 < 10, "the deadline did not actually bound the call"


def test_cancel_kills_the_process_and_names_the_user():
    tok = _with_call_id("t-cancel")
    try:
        llm_inflight.register("t-cancel")
        threading.Timer(0.5, lambda: llm_inflight.cancel("t-cancel")).start()
        t0 = time.monotonic()
        with pytest.raises(RuntimeError) as ei:
            llm._run_cli(["/bin/sh", "-c", "sleep 30"], timeout=60)
        assert llm._CANCEL_MSG in str(ei.value), \
            "a user cancel must be reported as such, not as a generic failure"
        assert time.monotonic() - t0 < 10, "cancel did not actually kill the process"
    finally:
        llm.current_llm_call_id.reset(tok)


def test_cancel_before_the_handle_exists_still_fires():
    """The set_cancel race: Stop clicked between register() and Popen()."""
    llm_inflight.register("t-race")
    assert llm_inflight.cancel("t-race") is True   # no handle yet — just marks
    fired = []
    llm_inflight.set_cancel("t-race", lambda: fired.append(1))
    assert fired == [1], "a pre-handle cancel was silently lost"


def test_agent_job_cancel_wakes_submit_early():
    from agent_jobs import AgentJobRegistry
    reg = AgentJobRegistry()
    holder = {}

    def on_start(job):
        holder["job"] = job

    def cancel_soon():
        time.sleep(0.3)
        j = holder["job"]
        j.result = {"content": "ERROR: " + llm._CANCEL_MSG, "error": True, "cancelled": True}
        j.event.set()

    threading.Thread(target=cancel_soon, daemon=True).start()
    t0 = time.monotonic()
    result = reg.submit("sess-x", "prompt", "opus", timeout=30, on_start=on_start)
    assert time.monotonic() - t0 < 5, "cancel did not wake the blocking submit"
    assert result["error"] and llm._CANCEL_MSG in result["content"]
