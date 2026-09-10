"""True LLM cancel + live progress (llm_inflight, agent_jobs.on_start).

Why (2026-08-26, Terrence): every LLM button gained a real Stop and a live
progress display. "Real" is the load-bearing word — a UI-only abort (browser
stops waiting, server finishes, tokens spend, result persists) was explicitly
rejected. What is left to pin here after the server stopped running any CLI
itself (server-side Claude removed 2026-09-10, Grok 2026-09-11 — the
subprocess runner `_run_cli` and its four process-killing tests went with them):

  * a cancel that lands BEFORE the transport attaches its handle must still
    fire (the set_cancel race),
  * an agent job's on_start cancel hook must wake submit() early with a
    cancelled result.

Offline: no network, no LLM.
"""
import pathlib
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
    for cid in ("t-race", "t-agent"):
        llm_inflight.finish(cid)


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
