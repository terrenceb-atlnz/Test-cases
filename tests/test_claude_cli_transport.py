"""The headless `claude -p` transport must behave like a completion API, not an agent.

TWO DEFECTS THIS PINS (both found 2026-07-30, Opus batch)
---------------------------------------------------------
**1. It ran as an agent.** `claude -p` is the Claude *Code* CLI: invoked bare it has tools
and may loop for many turns. The server treated it as a one-shot completion endpoint. On a
65k-token generate prompt that cost **2,670,565 input tokens over ~23 minutes for $4.65 and
returned an EMPTY result** — with `is_error` false, so the router answered the polite and
misleading "LLM returned no python code block". The retry cost another $5.24 identically.
`--tools ""` (the CLI's documented "disable all tools") brings it back to one turn.

Why it hid for so long: on the small JSON steps the agentic path happens to return usable
output. The transport looks perfectly healthy right up to the first large artefact — so a
test that only checks "does a call succeed" cannot see it. Hence the checks below assert
the SHAPE OF THE INVOCATION, which is what actually differs.

**2. It dropped the system message.** `run_prompt` resolves a system steer for every call
and the HTTP backends send it, but this path never accepted the parameter — so the CLI
transport alone ran unsteered. That interacted badly with defect 3 below.

**3. The steer was the wrong one anyway.** `_JSON_SYSTEM_PROMPT` says "no markdown fences",
`pt_generate_script.jinja` asks for a fenced python block, and `_parse_generated_blocks`
needs the fence to find the code at all. Two authorities in one request, contradicting each
other, on every backend.

Everything here is offline: `subprocess.run` is monkeypatched, so no CLI, no tokens.
"""
import ast
import inspect
import json
import re
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SERVER = _REPO / "ask-ck" / "CK-main" / "CK_server"
sys.path[:0] = [str(_REPO / "ask-ck" / "CK-main"), str(_SERVER)]

import llm  # noqa: E402


class _FakeProc:
    returncode = 0

    def __init__(self, payload):
        # The CLI now runs in stream-json mode: newline-delimited events, not one object.
        if isinstance(payload, list):
            self.stdout = "\n".join(json.dumps(e) for e in payload)
        else:
            self.stdout = json.dumps(payload)
        self.stderr = ""


def _assistant(text):
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def _result(text="", is_error=False):
    return {"type": "result", "result": text, "is_error": is_error}


@pytest.fixture
def captured(monkeypatch):
    """Capture the argv/stdin the CLI would receive; return a canned completion."""
    seen = {}

    def fake_run(cmd, input=None, capture_output=None, text=None, timeout=None, **kw):
        seen["cmd"] = list(cmd)
        seen["stdin"] = input
        seen["timeout"] = timeout
        return _FakeProc(seen.get("reply", [_assistant("```python\nx = 1\n```"), _result()]))

    monkeypatch.setattr(llm.subprocess, "run", fake_run)
    monkeypatch.setattr(llm.shutil, "which", lambda _n: "/usr/bin/claude")
    return seen


def _flag_value(cmd, flag):
    """The argument following `flag`, or None. Presence-and-value, since `--tools ''`
    carries an EMPTY string — a truthiness check would read it as absent."""
    return cmd[cmd.index(flag) + 1] if flag in cmd else None


def test_tools_are_disabled(captured):
    """The whole difference between a completion and a 23-minute $4.65 agent session."""
    llm._call_claude_code_headless("hi", "claude-opus-5", {}, timeout=60)
    cmd = captured["cmd"]
    assert "--tools" in cmd, (
        f"no --tools flag, so the CLI runs with its full toolset and may loop for many "
        f"turns instead of answering once. cmd was: {cmd}")
    assert _flag_value(cmd, "--tools") == "", (
        f"--tools must be the empty string (the CLI's 'disable all tools'); "
        f"got {_flag_value(cmd, '--tools')!r}")


def test_the_system_message_reaches_the_cli(captured):
    llm._call_claude_code_headless("hi", "claude-opus-5", {}, timeout=60, system="BE TERSE")
    cmd = captured["cmd"]
    assert _flag_value(cmd, "--append-system-prompt") == "BE TERSE", (
        f"system message did not reach the CLI; cmd was: {cmd}")


def test_append_not_replace_system_prompt(captured):
    """`--system-prompt` would REPLACE the CLI's own harness prompt and strip context it
    needs to function; `--append-system-prompt` adds to it."""
    llm._call_claude_code_headless("hi", "m", {}, timeout=60, system="X")
    assert "--system-prompt" not in captured["cmd"]


def test_no_system_means_no_flag(captured):
    """An empty steer must not become `--append-system-prompt ''`."""
    llm._call_claude_code_headless("hi", "m", {}, timeout=60, system="")
    assert "--append-system-prompt" not in captured["cmd"]


def test_the_dispatcher_forwards_the_system_message(captured):
    """The integration half. The helper accepting `system` is worthless if _call_llm_raw
    still calls it without one — which is exactly how the message got dropped."""
    llm._call_llm_raw("hi", provider="claude", auth_method="claude_code",
                      model="claude-opus-5", timeout=300, system="STEER-ME")
    assert _flag_value(captured["cmd"], "--append-system-prompt") == "STEER-ME", (
        "_call_llm_raw did not forward `system` to the CLI helper — the defect this "
        "pins is the parameter existing but never being passed")


def test_the_dispatcher_applies_the_whole_response_floor(captured):
    """Cross-check with the other fix: a caller's 300s must reach the subprocess as the
    CLI floor, since a subprocess gets one shot at the whole response."""
    llm._call_llm_raw("hi", provider="claude", auth_method="claude_code",
                      model="m", timeout=300)
    assert captured["timeout"] == llm._CLI_WHOLE_RESPONSE_FLOOR


# ---------------------------------------------------------------------------
# The steer must match what the parser needs
# ---------------------------------------------------------------------------

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
    write the file instead of emitting it: "Continuing by writing the artifact to disk in
    pieces rather than one oversized message", plus a narrated Write call. Disabling tools
    stops the call from succeeding but not the INSTINCT, so the steer must forbid it."""
    steer = llm._CODE_SYSTEM_PROMPT.lower()
    assert "no tools" in steer or "no filesystem" in steer
    assert "pieces" in steer or "continue" in steer, (
        "the steer does not address chunk-to-disk, the actual observed failure mode")


# ---------------------------------------------------------------------------
# The output budget is shared between thinking and the answer
# ---------------------------------------------------------------------------
# These are reasoning models. A live generate was observed at 31,100 THINKING tokens with
# zero answer text emitted, against a hard maxOutputTokens of 32,000 (not raisable:
# CLAUDE_CODE_MAX_OUTPUT_TOKENS=64000 leaves it at 32,000). The answer then arrives cut
# short — measured at 35% of the required script — and a short answer still looks like an
# answer, so it lints as a syntax error rather than reporting that it ran out of room.


def test_thinking_is_capped_on_long_calls(captured):
    llm._call_llm_raw("hi", provider="claude", auth_method="claude_code", model="m", timeout=600)
    cmd = captured["cmd"]
    assert "--max-thinking-tokens" in cmd, (
        "thinking is uncapped on a long-artefact call, so it competes with the artefact for "
        "one output budget and can consume nearly all of it before the answer starts")
    assert int(_flag_value(cmd, "--max-thinking-tokens")) == llm._CLI_MAX_THINKING_TOKENS


def test_thinking_is_NOT_capped_on_short_calls(captured):
    """Passing the flag at all turns extended thinking ON — measured 2,242ms bare vs
    16,426ms with it present on an identical trivial prompt. Applied unconditionally it made
    every small call ~7x slower and timed out the 30s health ping, breaking the one check
    whose purpose is to fail fast. So a short call must not carry it."""
    llm._call_llm_raw("hi", provider="claude", auth_method="claude_code", model="m", timeout=30)
    assert "--max-thinking-tokens" not in captured["cmd"], (
        "a deliberately short call now forces extended thinking; the health ping will "
        "time out instead of reporting a dead backend")


def test_one_predicate_decides_which_calls_are_long(captured):
    """The floor and the thinking cap must agree about 'long', or a call gets half the
    treatment. Both derive from _is_long_call, so this pins them together at the boundary."""
    for timeout, expect_long in ((119, False), (120, True)):
        captured.clear()
        captured["reply"] = [_result("ok")]
        llm._call_llm_raw("hi", provider="claude", auth_method="claude_code",
                          model="m", timeout=timeout)
        capped = "--max-thinking-tokens" in captured["cmd"]
        floored = captured["timeout"] == llm._CLI_WHOLE_RESPONSE_FLOOR
        assert capped is expect_long and floored is expect_long, (
            f"at timeout={timeout}: thinking_capped={capped}, floored={floored} — the two "
            f"behaviours disagree about whether this is a long call")


def test_the_thinking_cap_leaves_room_for_a_real_script():
    """The cap is only meaningful relative to what the answer needs. A ~42-TestCase
    skeleton measures ~26,300 tokens, so the remaining budget must clear that with margin —
    otherwise the cap is decorative and generation silently truncates again."""
    budget = 32000
    assert llm._CLI_MAX_THINKING_TOKENS <= 4096, (
        f"thinking cap {llm._CLI_MAX_THINKING_TOKENS} is too generous: it leaves "
        f"{budget - llm._CLI_MAX_THINKING_TOKENS} tokens for an answer that needs ~26,300")
    assert budget - llm._CLI_MAX_THINKING_TOKENS >= 28000


# ---------------------------------------------------------------------------
# The `result` field does not carry a multi-message answer
# ---------------------------------------------------------------------------

def test_stream_json_is_the_output_format(captured):
    """`json` returns only the FINAL assistant message. On a long script that drops the
    beginning and keeps a mid-class tail, which lints as an IndentationError and points
    nowhere near the transport."""
    llm._call_claude_code_headless("hi", "m", {}, timeout=60)
    cmd = captured["cmd"]
    assert _flag_value(cmd, "--output-format") == "stream-json"
    assert "--verbose" in cmd, "stream-json in print mode requires --verbose"


def test_all_assistant_messages_are_concatenated_in_order(captured):
    """The whole point: an answer split across messages must come back whole, head first."""
    captured["reply"] = [_assistant("#!/usr/bin/python3\nHEAD\n"), _assistant("MIDDLE\n"),
                         _assistant("TAIL\n"), _result("TAIL\n")]
    meta = llm._call_claude_code_headless("hi", "m", {}, timeout=60)
    assert meta["content"] == "#!/usr/bin/python3\nHEAD\nMIDDLE\nTAIL\n", (
        f"expected every message joined in order; got {meta['content']!r}. Taking the "
        f"`result` field alone would yield only 'TAIL'.")


def test_the_head_is_never_dropped(captured):
    """Stated as its own case because losing the HEAD is the specific observed corruption:
    the delivered script began at `    def tear_down(self):`."""
    captured["reply"] = [_assistant("#!/usr/bin/python3\n"), _assistant("    def tear_down(self):\n"),
                         _result("    def tear_down(self):\n")]
    meta = llm._call_claude_code_headless("hi", "m", {}, timeout=60)
    assert meta["content"].startswith("#!/usr/bin/python3"), (
        "the answer no longer starts at its beginning — the head was dropped again")


def test_falls_back_to_result_when_there_is_no_assistant_text(captured):
    """Degrade to the old behaviour rather than to nothing: a partial answer beats none."""
    captured["reply"] = [_result("PLAIN ANSWER")]
    meta = llm._call_claude_code_headless("hi", "m", {}, timeout=60)
    assert meta["content"] == "PLAIN ANSWER"


def test_a_single_object_payload_still_works(captured):
    """An older CLI, or the format being changed back, must not break the transport."""
    captured["reply"] = {"result": "LEGACY", "is_error": False}
    meta = llm._call_claude_code_headless("hi", "m", {}, timeout=60)
    assert meta["content"] == "LEGACY"


def test_unparseable_lines_are_skipped_not_fatal(captured):
    captured["reply"] = ["not json at all", _assistant("A"), "{broken", _assistant("B"), _result()]
    monkeyed = _FakeProc(["x"])          # sanity: helper handles str entries
    assert isinstance(monkeyed.stdout, str)
    meta = llm._call_claude_code_headless("hi", "m", {}, timeout=60)
    assert meta["content"] == "AB"


def test_an_error_envelope_is_reported_as_an_error(captured):
    """A 529 must surface as error=True, not as content the parser will try to read as
    a script."""
    captured["reply"] = [_result("API Error: 529 Overloaded", is_error=True)]
    meta = llm._call_claude_code_headless("hi", "m", {}, timeout=60)
    assert meta.get("error") is True
    assert "529" in meta["content"]


def test_json_steer_still_default_for_the_json_steps():
    """The fix must not have flipped every step to the code steer: the JSON templates
    depend on the JSON steer (measured ~22x fewer completion tokens)."""
    sig = inspect.signature(llm.run_prompt)
    assert sig.parameters["system"].default is None, (
        "run_prompt's `system` default changed; the JSON steps rely on resolving to "
        "_JSON_SYSTEM_PROMPT when the caller passes nothing")
    src = inspect.getsource(llm.run_prompt)
    assert "_JSON_SYSTEM_PROMPT if system is None else system" in re.sub(r"\s+", " ", src)
