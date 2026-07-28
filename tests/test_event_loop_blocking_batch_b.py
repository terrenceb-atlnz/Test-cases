"""Regression tests for adversarial-review batch B (2026-07-27g) — event-loop blocking.

One theme: blocking work running bare on the event loop, at sites where the same file
already wraps identical work in run_in_threadpool.

  - export()'s generate_coverage_gaps was the only LLM call site in wizard.py without
    the wrap. In claude_agent mode that is a guaranteed SELF-DEADLOCK, not just a stall:
    _call_claude_agent -> registry.submit() blocks on threading.Event.wait(180s), and
    the event is only set when the browser POSTs /api/agent/result — which the blocked
    event loop cannot serve. It hangs the full 180s, then blames the user's ck-agent.
  - Seven search call sites ran sentence-transformer inference inline. The first one
    after a restart also constructs the model from disk (measured 16.2s; ~20ms warm).
    The review flagged three; an AST sweep found four more (load_case + the three
    suggest_* endpoints), including the one that runs on EVERY case load.

These are structural tests. Timing the loop would be flaky and would need a live LLM,
so instead we assert the invariant directly against the AST: no async handler in any
router may call a known-blocking function without the threadpool wrap. That is stricter
than the four findings and catches the next one automatically.
"""
import ast
import pathlib

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
_ROUTERS = _REPO_ROOT / "ask-ck" / "CK-main" / "CK_server" / "routers"

# Functions that block the calling thread: LLM round-trips (incl. the agent-bridge
# long-poll), sentence-transformer load/inference, and the search helpers that reach it.
_BLOCKING = {
    "generate_coverage_gaps", "synthesize_objectives", "synthesize_steps",
    "synthesize_objectives_and_steps", "analyze_atp_coverage", "call_llm",
    "_call_llm_raw", "_call_llm_with_meta", "_health_ping",
    "embed_texts", "_get_model",
    # get_atp_candidates moved to CK_server/generator/descriptions.py in commit 7 and lost
    # its underscore (a name another module imports is not private). It is listed under
    # BOTH names: the new one because that is what the routers call today, the old one
    # to pin it against revival. This set matches on the CALL NAME, so a router that
    # imports the module and calls `descriptions.get_atp_candidates(...)` would not be
    # seen at all — see test_blocking_helpers_are_imported_by_name below, which is what
    # stops that silently un-covering the handler.
    "_search_testlink", "_search_zephyr_external",
    "_get_atp_candidates", "get_atp_candidates",
    # Pure-CPU / filesystem blockers. The list above was all LLM round-trips and
    # sentence-transformer entry points, which is why it never caught
    # _select_related_zephyr_refs: a 45k-row Python scan is neither, so it sat bare
    # on the event loop for a measured 2.7s per case load until it was deleted
    # outright. `_refined_complete_keys` rglob's the whole refined-cases tree.
    # _select_related_zephyr_refs no longer exists — listed to pin the name against
    # revival, which costs nothing since this is a call-name match.
    # _refined_complete_keys / _session_progress_map moved to CK_server/case_registry.py
    # in commit 8 and lost their underscores. Both spellings listed, same reasoning as
    # get_atp_candidates above.
    "_select_related_zephyr_refs",
    "_refined_complete_keys", "refined_complete_keys",
    "_session_progress_map", "session_progress_map",
}


def _unwrapped_blocking_calls(path):
    """Blocking calls made directly inside an async def (not via run_in_threadpool)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef)]:
        wrapped = set()
        for n in ast.walk(fn):
            if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "run_in_threadpool":
                if n.args and isinstance(n.args[0], ast.Name):
                    wrapped.add(id(n.args[0]))
        for n in ast.walk(fn):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                    and n.func.id in _BLOCKING and id(n.func) not in wrapped):
                found.append(f"{path.name}:{n.lineno} async {fn.name}() -> {n.func.id}()")
    return found


# rglob, not glob: PLAN-backend-module-split.md commit 10 turns routers/wizard.py into
# routers/wizard/, at which point a top-level glob would simply stop matching the wizard
# handlers and keep passing green — a silent coverage loss. Widened here, ahead of the
# move, because it costs nothing today (routers/ has no subdirectories yet) and the
# failure mode is invisible.
@pytest.mark.parametrize("router", sorted(_ROUTERS.rglob("*.py")), ids=lambda p: p.name)
def test_no_blocking_calls_on_the_event_loop(router):
    """No async handler may call a blocking function without run_in_threadpool.

    The convention already existed at every LLM site but one; this pins it so the next
    handler cannot quietly reintroduce the stall.
    """
    offenders = _unwrapped_blocking_calls(router)
    assert not offenders, (
        "blocking call(s) on the event loop — wrap in run_in_threadpool:\n  "
        + "\n  ".join(offenders))


def test_export_gaps_call_is_wrapped():
    """Pin the specific claude_agent self-deadlock site (the sharpest of the four)."""
    src = (_ROUTERS / "wizard.py").read_text(encoding="utf-8")
    assert "await run_in_threadpool(generate_coverage_gaps" in src, (
        "export()'s coverage-gaps call must run off the event loop — on it, "
        "claude_agent mode deadlocks for the full 180s agent timeout")


def test_search_endpoints_are_wrapped():
    """All three review-flagged search endpoints plus load_case's ATP prefetch."""
    src = (_ROUTERS / "wizard.py").read_text(encoding="utf-8")
    for fn in ("_search_testlink", "_search_zephyr_external", "get_atp_candidates"):
        assert f"run_in_threadpool(\n        {fn}" in src or f"run_in_threadpool({fn}" in src, (
            f"{fn} is never dispatched via run_in_threadpool")


def test_blocking_helpers_are_imported_by_name():
    """A router must import a blocking helper BY NAME, never as `module.helper`.

    _unwrapped_blocking_calls above matches `ast.Name` call targets. That is deliberate
    — it is also how run_in_threadpool's first argument is recognised — but it means an
    attribute call is invisible to it. So as Part B moves helpers out of the routers
    (commit 7 moved get_atp_candidates to CK_server/generator/descriptions.py), a switch
    from `from generator.descriptions import get_atp_candidates` to
    `from generator import descriptions` would drop the handler out of the invariant while
    the whole suite stayed green. This asserts the import style that keeps it covered.
    """
    offenders = []
    for path in sorted(_ROUTERS.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for n in ast.walk(tree):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr in _BLOCKING
                    and isinstance(n.func.value, ast.Name)
                    # db.* is the data layer, not a helper that got moved; its search
                    # entry points are already named individually in _BLOCKING.
                    and n.func.value.id != "db"):
                offenders.append(
                    f"{path.name}:{n.lineno} {n.func.value.id}.{n.func.attr}() — "
                    "import the name directly so the AST invariant can see it")
    assert not offenders, "\n  ".join(offenders)


def test_embedding_warmup_is_backgrounded_and_non_fatal():
    """Warmup must not add its cold load to boot, and must never break startup.

    A synchronous warmup would add ~16s to every restart (painful for --reload and the
    E2E webServer); a raising one would turn a degraded search into a dead server.
    """
    src = (_REPO_ROOT / "ask-ck" / "CK-main" / "CK_server" / "main.py").read_text(encoding="utf-8")
    assert "threading.Thread" in src and "daemon=True" in src, "warmup must be backgrounded"
    assert "CK_NO_EMBED_WARMUP" in src, "warmup must be opt-out-able"
    # The warmup body must swallow its own failure.
    warm = src.split("def _warm()", 1)[1].split("threading.Thread", 1)[0]
    assert "except Exception" in warm, "warmup failure must not be fatal to startup"


def test_search_endpoints_still_work(client):
    """Behaviour is unchanged by the wrap — the endpoints still return results.

    Uses keyword mode so this stays fast and does not depend on the embedding model.
    """
    r = client.get("/api/wizard/search_testlink", params={"q": "port", "mode": "keyword"})
    assert r.status_code == 200
    assert isinstance(r.json().get("results"), list)

    r = client.get("/api/wizard/search_atp", params={"q": "port", "mode": "keyword"})
    assert r.status_code == 200
    assert isinstance(r.json().get("results"), list)

    r = client.get("/api/wizard/search_zephyr", params={"q": "port", "mode": "keyword"})
    assert r.status_code == 200
    assert isinstance(r.json().get("results"), list)


def test_concurrent_searches_are_not_serialized(client):
    """The loop stays responsive while a search runs.

    With the handler on the event loop, a slow search blocks every other request. Here
    a trivial /health must still answer while searches are in flight. This is a smoke
    check on the threadpool dispatch, not a timing assertion.
    """
    import concurrent.futures as cf

    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        searches = [ex.submit(client.get, "/api/wizard/search_testlink",
                              params={"q": "port auto negotiation", "mode": "keyword"})
                    for _ in range(3)]
        health = ex.submit(client.get, "/health")
        assert health.result(timeout=60).status_code == 200
        for f in searches:
            assert f.result(timeout=60).status_code == 200
