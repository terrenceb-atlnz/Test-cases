"""The server's Claude path is the browser-brokered per-user agent — and only that.

Re-homed 2026-09-10 from tests/test_claude_cli_transport.py and tests/test_cli_truncation_signal.py
when server-side Claude (`claude_code`, `llm._call_claude_code_headless`) was removed
(PLAN-seat-setup-and-per-seat-llm.md §6, decision D3). The CLI contract those files pinned
now lives in the two agents and is pinned there (tests/test_ck_agent_transport.py, against
the same tests/fixtures/cli_stream_*.jsonl captures). What stays server-side, and is pinned
here:

  * the steer rides with the agent job and the dispatcher forwards it;
  * the two steers still disagree about fences, the parser still needs the fence the JSON
    steer forbids, and the script-emitting steps pass the code steer;
  * the captured ground truth about the CLI's stream (stop_reason is useless, the signal is
    on the result event) — facts about the fixtures, independent of any implementation;
  * the refuted output-ceiling claim must not survive as a live comment;
  * the JSON steer is still run_prompt's default.
"""
import ast
import inspect
import json
import pathlib
import re
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SERVER = _REPO / "ask-ck" / "CK-main" / "CK_server"
sys.path[:0] = [str(_REPO / "ask-ck" / "CK-main"), str(_SERVER)]

import llm  # noqa: E402

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
TRUNCATED = (FIXTURES / "cli_stream_truncated.jsonl").read_text(encoding="utf-8")


# --- the agent path is the Claude path -------------------------------------------------

def test_server_side_claude_is_gone():
    """D3: "this button will go, and so will all associated code"."""
    from models import RETIRED_AUTH_METHODS, SUPPORTED_AUTH_METHODS
    assert "claude_code" not in SUPPORTED_AUTH_METHODS
    assert "claude_code" in RETIRED_AUTH_METHODS, "must be refused BY NAME, not as 'unknown'"
    for gone in ("_call_claude_code_headless", "check_claude_cli", "_parse_cli_stream",
                 "_cli_neutral_cwd", "_CLI_MAX_THINKING_TOKENS"):
        assert not hasattr(llm, gone), f"llm.{gone} still exists"
    src = llm.__file__
    assert "claude_code" not in Path(src).read_text(encoding="utf-8").replace(
        "REMOVED", "").lower().replace("claude_code", "", 0), "left for the reader to judge"


def test_a_retired_claude_code_config_is_refused_by_name():
    meta = llm._call_llm_raw("hi", provider="claude", auth_method="claude_code", model="m", timeout=30)
    assert meta.get("error") is True
    assert "retired" in meta["content"] or "no longer" in meta["content"], meta["content"]


def test_the_agent_path_carries_the_steer_with_the_job(monkeypatch):
    """The agent transport once dropped `system` entirely and ran under the harness prompt
    with tools — hence the 528k-token unit call of 2026-09-02. The steer must ride with the
    job so the agent can pass it as --system-prompt, and an empty steer must become the
    default, never nothing."""
    import agent_jobs
    seen = {}

    def fake_submit(session_id, prompt, model, timeout, on_start=None, system=""):
        seen["system"] = system
        seen["timeout"] = timeout
        return {"content": "ok", "error": False}

    monkeypatch.setattr(agent_jobs.registry, "submit", fake_submit)
    llm._call_claude_agent("hi", "m", {}, session_id="sess-x", timeout=60, system="STEER")
    assert seen["system"] == "STEER"
    llm._call_claude_agent("hi", "m", {}, session_id="sess-x", timeout=60, system="")
    assert seen["system"] == llm._DEFAULT_CLI_SYSTEM_PROMPT
    # and the dispatcher forwards it
    llm._call_llm_raw("hi", provider="claude", auth_method="claude_agent", model="m",
                      timeout=60, session_id="sess-x", system="VIA-DISPATCH")
    assert seen["system"] == "VIA-DISPATCH"


def test_the_agent_path_applies_the_whole_response_floor(monkeypatch):
    """A long call's budget is floored before submit, and the floored number is what the
    browser hands the agent — server and agent must wait on ONE number."""
    import agent_jobs
    seen = {}

    def fake_submit(session_id, prompt, model, timeout, on_start=None, system=""):
        seen["timeout"] = timeout
        return {"content": "ok", "error": False}

    monkeypatch.setattr(agent_jobs.registry, "submit", fake_submit)
    llm._call_claude_agent("hi", "m", {}, session_id="sess-x", timeout=300)
    assert seen["timeout"] == llm._CLI_WHOLE_RESPONSE_FLOOR
    llm._call_claude_agent("hi", "m", {}, session_id="sess-x", timeout=30)
    assert seen["timeout"] == 30, "a deliberately short call (the health ping) stays short"


def test_the_agent_and_server_defaults_are_one_sentence():
    sys.path.insert(0, str(_REPO / "ask-ck" / "agent"))
    import ck_agent
    assert ck_agent.DEFAULT_SYSTEM_PROMPT == llm._DEFAULT_CLI_SYSTEM_PROMPT


# --- the steer must match what the parser needs --------------------------------------

def test_the_two_steers_really_do_disagree_about_fences():
    """Establishes that picking the right one MATTERS. If this ever fails, the steers have
    converged and the tests below are guarding nothing."""
    assert "no markdown fences" in llm._JSON_SYSTEM_PROMPT
    assert "```python" in llm._CODE_SYSTEM_PROMPT


def test_the_parser_requires_the_fence_the_json_steer_forbids():
    """Why the mismatch is fatal rather than cosmetic: there is no unfenced fallback, so a
    model that obeys the JSON steer yields test_code=None and a 502."""
    from CK_server.routers.pytest_create import _parse_generated_blocks

    assert _parse_generated_blocks("```python\nx = 1\n```")["test_code"] is not None
    assert _parse_generated_blocks("x = 1\n")["test_code"] is None, (
        "an unfenced answer now parses — re-check whether the code steer is still needed")


@pytest.mark.parametrize("template", ["pt_generate_script.jinja", "pt_fix_script.jinja"])
def test_script_emitting_steps_use_the_code_steer(template):
    """Structural, on the router source: both script-emitting call sites must pass
    system=_CODE_SYSTEM_PROMPT. Without it they silently inherit run_prompt's JSON
    default."""
    src = (_SERVER / "routers" / "pytest_create.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or getattr(node.func, "id", None) != "run_in_threadpool":
            continue
        args = node.args
        if len(args) < 2 or getattr(args[0], "id", None) != "run_prompt":
            continue
        if not (isinstance(args[1], ast.Constant) and args[1].value == template):
            continue
        found.append({kw.arg: kw.value for kw in node.keywords})
    assert found, f"no run_prompt call for {template} — the scan is broken, not the code"
    for kwargs in found:
        assert "system" in kwargs, (
            f"{template} does not pass `system=`, so it inherits run_prompt's JSON steer "
            f"— which forbids the markdown fence _parse_generated_blocks requires.")
        assert getattr(kwargs["system"], "id", None) == "_CODE_SYSTEM_PROMPT", (
            f"{template} passes a system message that is not _CODE_SYSTEM_PROMPT")


def test_the_code_steer_forbids_writing_files():
    """The observed large-artefact failure was not truncation — it was the model choosing to
    write the file instead of emitting it. Disabling tools stops the call from succeeding
    but not the INSTINCT, so the steer must forbid it."""
    steer = llm._CODE_SYSTEM_PROMPT.lower()
    assert "no tools" in steer or "no filesystem" in steer
    assert "pieces" in steer or "continue" in steer, (
        "the steer does not address chunk-to-disk, the actual observed failure mode")


def test_json_steer_still_default_for_the_json_steps():
    """The JSON templates depend on the JSON steer (measured ~22x fewer completion tokens)."""
    sig = inspect.signature(llm.run_prompt)
    assert sig.parameters["system"].default is None, (
        "run_prompt's `system` default changed; the JSON steps rely on resolving to "
        "_JSON_SYSTEM_PROMPT when the caller passes nothing")
    src = inspect.getsource(llm.run_prompt)
    assert "_JSON_SYSTEM_PROMPT if system is None else system" in re.sub(r"\s+", " ", src)


# --- the captured ground truth about the CLI's stream ---------------------------------

def test_the_capture_shows_stop_reason_is_null_on_real_messages():
    """Pins WHY the obvious truncation detection does not work — a fact about the CLI's
    stream, independent of which side parses it. If a future CLI starts setting
    `stop_reason` on assistant messages this fails, and the agents' detection can be
    simplified."""
    real, synthesized = [], []
    for line in TRUNCATED.splitlines():
        evt = json.loads(line)
        if evt.get("type") != "assistant":
            continue
        msg = evt["message"]
        (real if str(msg.get("id") or "").startswith("msg_") else synthesized).append(msg)
    assert real, "fixture must contain genuine assistant messages"
    assert all(m.get("stop_reason") is None for m in real), \
        "every genuine assistant message reports stop_reason=None, even when truncated"
    assert synthesized, "fixture must contain the CLI's synthesized error message"
    assert synthesized[0].get("stop_reason") == "stop_sequence"
    assert "max_tokens" not in TRUNCATED, \
        "'max_tokens' never appears in the stream — do not detect on it"


def test_the_capture_carries_the_signal_on_the_result_event():
    result = [json.loads(l) for l in TRUNCATED.splitlines() if json.loads(l).get("type") == "result"][0]
    assert result["is_error"] is True
    assert result["terminal_reason"] == "api_error"
    assert "output token maximum" in result["result"]


# --- the refuted output ceiling must not come back as a live comment --------------------

_REFUTATION_MARKERS = ("refute", "no longer", "earlier claim", "used to", "does not exist",
                       "Phase 7.4", "is refuted", "attributed it to the model")


def test_no_surface_still_asserts_a_whole_script_must_fit_one_message():
    """`FINDINGS-generation-size-ceiling.md` measured a defective parser and called the result
    the model's budget. A comment is what the next engineer reads before deciding whether a
    "fix" is a regression, so a stale one is how a corrected constant gets reverted."""
    server = pathlib.Path(llm.__file__).parent
    stale = []
    for path in (server / "llm.py", server / "routers" / "pytest_create.py"):
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            for phrase in ("covers a ~44-TestCase script",
                           "larger cases need chunked generation",
                           "cannot fit the model's output budget"):
                if phrase not in line:
                    continue
                context = "\n".join(lines[max(0, i - 8):i + 8])
                if not any(marker in context for marker in _REFUTATION_MARKERS):
                    stale.append(f"{path.name}:{i + 1}: {phrase!r}")
    assert not stale, (
        "these comments still assert the refuted output ceiling as fact:\n  "
        + "\n  ".join(stale))


def test_that_staleness_check_can_actually_fail():
    """A context-sensitive check that never fires is worse than none — prove it fires."""
    import tempfile
    asserted = "# the 32,000 cap covers a ~44-TestCase script\nx = 1\n"
    refuted = ("# Phase 7.4: the earlier claim that it covers a ~44-TestCase script\n"
               "# is refuted — a long answer continues into further messages.\nx = 1\n")
    with tempfile.TemporaryDirectory() as tmp:
        for name, body, expect_stale in (("a.py", asserted, True), ("b.py", refuted, False)):
            path = pathlib.Path(tmp) / name
            path.write_text(body)
            lines = body.splitlines()
            hits = []
            for i, line in enumerate(lines):
                if "covers a ~44-TestCase script" not in line:
                    continue
                context = "\n".join(lines[max(0, i - 8):i + 8])
                if not any(m in context for m in _REFUTATION_MARKERS):
                    hits.append(i)
            assert bool(hits) is expect_stale, f"{name}: context discrimination is broken"
