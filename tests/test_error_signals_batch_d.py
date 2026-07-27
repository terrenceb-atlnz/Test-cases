"""Regression tests for adversarial-review batch D (2026-07-27g) — error signals.

One theme: the system failing to signal, or actively MIS-signalling, a condition it had
already detected.

  - llm.py:425/428 — the Claude branch lacked the two guards the OpenAI branch has, so
    an empty completion (or one holding only thinking blocks) and a response truncated
    at the token cap were both reported as SUCCESS. Downstream JSON parsing then failed
    and looked like "the LLM found nothing".
  - db.py:816 — _rrf_merge truncated to `limit` with no concept of pinned ids, so the
    keep_ids contract the keyword layer implements (always return the client's pool,
    re-scored) was silently violated on the hybrid path.
  - pytest_create.py:2068 — restart-orphaned runs were re-marked 'stale' only inside
    load_case, so the polling endpoint reported the persisted 'running' forever.
  - agent_jobs.py:111 — gc() had zero call sites; _queues/_session_seen grew for the
    lifetime of the process, keyed by an unvalidated client header.

The two frontend rows (provenance.js / generator.js missing res.ok) are covered in
js-tests/error-guards.spec.js. No network, no LLM, no testbox here.
"""
import time

import pytest

import db
from agent_jobs import AgentJobRegistry, _Job


# --- llm.py — the Claude-branch response guards ---------------------------------
def _claude_guard(data, max_tokens=2000):
    """The guard logic added to the Claude branch, isolated for testing.

    Mirrors llm.py's block: build content from text blocks, then apply the empty /
    truncated checks. Kept in step with production by
    test_claude_guards_exist_in_source below.
    """
    content = "".join(b.get("text", "") for b in data.get("content", [])
                      if b.get("type") == "text")
    stop_reason = data.get("stop_reason")
    if not content:
        if stop_reason == "max_tokens":
            raise ValueError("hit the token cap and returned no answer")
        content = "".join(b.get("thinking", "") or b.get("text", "")
                          for b in data.get("content", []) if b.get("type") != "text")
        if not content:
            raise ValueError(f"provider returned an empty completion (stop_reason={stop_reason})")
    elif stop_reason == "max_tokens":
        raise ValueError("output was truncated at the token cap")
    return content


def test_claude_empty_content_array_raises():
    """Previously returned content='' with error unset — a silent success."""
    with pytest.raises(ValueError, match="empty completion"):
        _claude_guard({"content": [], "stop_reason": "end_turn"})


def test_claude_thinking_only_falls_back_rather_than_failing():
    """A reasoning-only response should yield its thinking, not an error."""
    out = _claude_guard({"content": [{"type": "thinking", "thinking": "reasoned text"}],
                         "stop_reason": "end_turn"})
    assert out == "reasoned text"


def test_claude_empty_at_cap_names_the_cap():
    with pytest.raises(ValueError, match="token cap"):
        _claude_guard({"content": [], "stop_reason": "max_tokens"})


def test_claude_truncated_nonempty_is_an_error():
    """The sharp one: a truncated answer used to be accepted as complete, so the
    downstream JSON parse failed and looked like an empty LLM result."""
    with pytest.raises(ValueError, match="truncated"):
        _claude_guard({"content": [{"type": "text", "text": '{"steps": [{"desc'}],
                       "stop_reason": "max_tokens"})


def test_claude_normal_response_passes_through():
    assert _claude_guard({"content": [{"type": "text", "text": "hello"}],
                          "stop_reason": "end_turn"}) == "hello"


def test_claude_guards_exist_in_source():
    """Drift guard: the production branch must keep both checks."""
    import pathlib
    src = (pathlib.Path(__file__).resolve().parents[1]
           / "ask-ck" / "CK-main" / "CK_server" / "llm.py").read_text(encoding="utf-8")
    # Anchor on the HTTP-API branch's own marker — "[LLM CLAUDE via claude_code]" is a
    # different (CLI) branch earlier in the file.
    claude_branch = src.split('[LLM CLAUDE via {auth_method}]', 1)[0][-3000:]
    assert 'stop_reason == "max_tokens"' in claude_branch, "no truncation guard"
    assert "empty completion" in claude_branch, "no empty-content guard"


# --- db.py — keep_ids pinning through the hybrid merge ---------------------------
def _hydrate(rid, sim):
    return {"id": rid}


def test_rrf_merge_retains_pinned_ids_below_the_limit():
    """The reported violation: a kept pool item that fuses low was truncated away."""
    kw = [{"id": f"TL-{i}", "score": 0.5} for i in range(1, 6)]
    hits = [(f"TL-{i}", 0.9 - 0.1 * i) for i in range(1, 6)]
    out = db._rrf_merge(kw, hits, "id", _hydrate, limit=2, keep_ids={"TL-5"})
    ids = [r["id"] for r in out]
    assert "TL-5" in ids, "pinned id was dropped by the limit truncation"
    # ...and the limit still governs how many NON-pinned rows come back.
    assert len([i for i in ids if i != "TL-5"]) == 2


def test_rrf_merge_without_keep_ids_is_unchanged():
    """No pinning requested → the original truncation behaviour."""
    kw = [{"id": f"TL-{i}", "score": 0.5} for i in range(1, 6)]
    hits = [(f"TL-{i}", 0.9 - 0.1 * i) for i in range(1, 6)]
    out = db._rrf_merge(kw, hits, "id", _hydrate, limit=2)
    assert len(out) == 2


def test_rrf_merge_does_not_duplicate_a_pinned_row():
    kw = [{"id": "TL-1", "score": 0.9}, {"id": "TL-2", "score": 0.5}]
    hits = [("TL-1", 0.9), ("TL-2", 0.4)]
    out = db._rrf_merge(kw, hits, "id", _hydrate, limit=5, keep_ids={"TL-1"})
    assert [r["id"] for r in out].count("TL-1") == 1


def test_hybrid_search_signatures_accept_keep_ids():
    """All three public hybrid entry points must thread the pool through."""
    import inspect
    for fn in (db.search_testlink_hybrid, db.search_zephyr_hybrid, db.search_atp_hybrid):
        assert "keep_ids" in inspect.signature(fn).parameters
    assert "keep_ids" in inspect.signature(db._hybrid).parameters
    assert "keep_ids" in inspect.signature(db._rrf_merge).parameters


# --- agent_jobs.py — the gc leak -------------------------------------------------
def test_gc_drops_idle_sessions():
    reg = AgentJobRegistry(max_idle_seconds=0)
    reg.next_job("alice")
    reg.gc()
    assert not reg._session_seen, "idle session was not collected"
    assert not reg._queues


def test_gc_keeps_recent_sessions():
    reg = AgentJobRegistry(max_idle_seconds=3600)
    reg.next_job("alice")
    reg.gc()
    assert "alice" in reg._session_seen


def test_next_job_drives_gc():
    """gc() had zero call sites; the long-poll must now drive it."""
    reg = AgentJobRegistry(max_idle_seconds=0)
    reg._session_seen["ghost"] = time.time() - 10_000
    reg._queues["ghost"] = __import__("collections").deque()
    reg._last_gc = 0            # force the rate-limiter to fire
    reg.next_job("alice")
    assert "ghost" not in reg._session_seen, "next_job did not drive gc()"


def test_gc_is_rate_limited():
    """It must not run on every poll — only once per half-idle window."""
    reg = AgentJobRegistry(max_idle_seconds=3600)
    reg._last_gc = time.time()
    before = reg._last_gc
    reg.next_job("alice")
    assert reg._last_gc == before, "gc ran despite the rate limit"


def test_empty_queue_is_not_retained():
    """An empty deque keyed by a client header must not linger."""
    reg = AgentJobRegistry(max_idle_seconds=3600)
    reg._queues["alice"] = __import__("collections").deque()
    reg.next_job("alice")
    assert "alice" not in reg._queues


def test_next_job_still_returns_a_queued_job():
    """Behaviour preserved: the gc/cleanup rework must not eat real jobs."""
    reg = AgentJobRegistry()
    job = _Job("alice", "prompt-text", "sonnet")
    reg._queues.setdefault("alice", __import__("collections").deque()).append(job)
    got = reg.next_job("alice")
    assert got is not None
    assert got[1] == "prompt-text"


def test_session_id_length_is_capped():
    """The header becomes a registry dict key, so it must be bounded."""
    from routers.agent_bridge import _resolve_session, _MAX_SESSION_ID_LEN
    assert len(_resolve_session("x" * 10_000, "")) == _MAX_SESSION_ID_LEN
    assert _resolve_session("normal-session-id", "") == "normal-session-id"


# --- pytest_create.py — the stale-run sweep --------------------------------------
def test_stale_sweep_marks_orphaned_runs():
    """A run whose process died with the server must not stay 'running' forever."""
    from models import PtSession
    from routers.pytest_create import _sweep_stale_runs

    sess = PtSession(key="AWPTCM-T99995")
    sess.step7 = {"runs": [{"run_id": "r1", "status": "running"},
                           {"run_id": "r2", "status": "done"}]}
    assert _sweep_stale_runs(sess) is True
    statuses = {r["run_id"]: r["status"] for r in sess.step7["runs"]}
    assert statuses["r1"] == "stale"
    assert statuses["r2"] == "done", "a finished run was wrongly re-marked"


def test_stale_sweep_is_a_noop_when_nothing_is_live():
    from models import PtSession
    from routers.pytest_create import _sweep_stale_runs

    sess = PtSession(key="AWPTCM-T99996")
    sess.step7 = {"runs": [{"run_id": "r1", "status": "done"}]}
    assert _sweep_stale_runs(sess) is False


def test_stale_sweep_handles_no_runs():
    from models import PtSession
    from routers.pytest_create import _sweep_stale_runs
    assert _sweep_stale_runs(PtSession(key="AWPTCM-T99997")) is False


def test_run_status_sweeps_too():
    """The whole point of the fix: the polling endpoint must apply the sweep."""
    import pathlib
    src = (pathlib.Path(__file__).resolve().parents[1]
           / "ask-ck" / "CK-main" / "CK_server" / "routers"
           / "pytest_create.py").read_text(encoding="utf-8")
    run_status = src.split("async def run_status(", 1)[1].split("async def", 1)[0]
    assert "_sweep_stale_runs" in run_status, (
        "run_status still reports the persisted status without re-checking staleness")


# --- llm.py streaming: SSE encoding (found while REFUTING backlog llm.py:494) ----
def test_sse_stream_is_decoded_as_utf8():
    """The streamed vLLM path must not mojibake non-ASCII content.

    SSE is Content-Type: text/event-stream, and requests maps any "text" type to
    ISO-8859-1, so decode_unicode built a latin-1 decoder: "port — 1 µs" arrived as
    "port â 1 Âµs". It corrupts silently (no replacement char) and the result is still
    valid JSON, so it flowed into the stored objective/steps and on to Zephyr.

    The filed finding (chunk-boundary splitting) was refuted — the incremental decoder
    handles split sequences fine, as the second half of this test shows. The real bug
    was the codec, found by the skeptic while disproving the narrower claim.
    """
    import codecs
    import pathlib

    sample = "Verify port — 1 µs ✓"
    raw = sample.encode("utf-8")

    # The old behaviour, for the record.
    latin = codecs.getincrementaldecoder("ISO-8859-1")(errors="replace").decode(raw)
    assert latin != sample, "premise check: latin-1 really does corrupt this"

    # The fix.
    assert codecs.getincrementaldecoder("utf-8")(errors="replace").decode(raw) == sample

    # And the originally-filed concern is genuinely a non-issue: an incremental utf-8
    # decoder reassembles a sequence split across chunk boundaries.
    dec = codecs.getincrementaldecoder("utf-8")(errors="replace")
    chunked = "".join(dec.decode(raw[i:i + 3]) for i in range(0, len(raw), 3))
    assert chunked == sample

    src = (pathlib.Path(__file__).resolve().parents[1]
           / "ask-ck" / "CK-main" / "CK_server" / "llm.py").read_text(encoding="utf-8")
    stream_block = src.split("stream=True", 1)[1].split("iter_lines", 1)[0]
    assert 'resp.encoding = "utf-8"' in stream_block, (
        "the SSE stream no longer pins utf-8 — non-ASCII output will mojibake")
