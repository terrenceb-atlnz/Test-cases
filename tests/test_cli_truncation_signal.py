"""The CLI transport must notice when the model ran out of output budget.

PHASE 7.1. `_parse_cli_stream` read no completion signal at all, so a generation that hit
the output cap returned HTTP 200 and was stamped, linted, persisted and written to disk
exactly like a complete one. With nothing to the contrary, a truncated script is
indistinguishable from a short one — that single omission is what made every downstream
"mask" possible.

THE SIGNAL IS NOT WHERE YOU WOULD EXPECT IT, and the first attempt at this fix was dead
code because it guessed. Captured live against CLI 2.1.207 with
`CLAUDE_CODE_MAX_OUTPUT_TOKENS=200` and a deliberately over-long prompt:

  * `stop_reason` is **null on every genuine assistant message**, including the ones that
    actually hit the cap.
  * The only truthy `stop_reason` in the whole stream sits on a message the CLI
    **synthesizes** to carry "API Error: Claude's response exceeded the 200 output token
    maximum", whose id is a UUID rather than `msg_...` — and it reads "stop_sequence", not
    "max_tokens".
  * The real signal is on the terminal `result` event: `is_error: true`,
    `terminal_reason: "api_error"`, and that error text in `result`.

Both captures are committed under `tests/fixtures/` — reduced to the structural fields, with
message text clipped and machine metadata removed — so this evidence lives in the gate
rather than on one laptop.
"""
import json
import pathlib

import pytest

import llm

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def _load(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


NORMAL = _load("cli_stream_normal.jsonl")
TRUNCATED = _load("cli_stream_truncated.jsonl")


# ------------------------------------------------------- the captured ground truth itself

def test_the_capture_shows_stop_reason_is_null_on_real_messages():
    """Pins WHY the obvious implementation does not work.

    If a future CLI starts setting `stop_reason` on assistant messages this fails, and the
    detection below can be simplified. Until then, reading it detects nothing.
    """
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


# ------------------------------------------------------------------------- the detection

def test_a_truncated_reply_is_flagged():
    content, env = llm._parse_cli_stream(TRUNCATED)
    assert env["truncated"] is True, "the transport still cannot see that it ran out of room"
    assert content, "the partial answer is still returned for forensics"


def test_a_normal_reply_is_not_flagged():
    content, env = llm._parse_cli_stream(NORMAL)
    assert env.get("truncated") is False
    assert content.strip()


def test_the_cli_error_text_is_kept_out_of_the_answer():
    """The synthesized error message used to be concatenated onto the end of the script.

    English prose on the tail of a generated file is then handed to the assembler as if it
    were code.
    """
    content, env = llm._parse_cli_stream(TRUNCATED)
    assert "API Error" not in content, "CLI error text leaked into the artefact"
    assert "output token maximum" in env.get("cli_error_text", "")


def test_message_count_counts_messages_not_text_blocks():
    """One assistant message can carry a thinking block and a text block sharing one id."""
    content, env = llm._parse_cli_stream(TRUNCATED)
    assert env["message_count"] <= env["text_block_count"]
    ids = {json.loads(l)["message"]["id"] for l in TRUNCATED.splitlines()
           if json.loads(l).get("type") == "assistant"
           and str(json.loads(l)["message"].get("id") or "").startswith("msg_")}
    assert env["message_count"] == len(ids)


def test_text_block_boundaries_line_up_with_the_joined_text():
    content, env = llm._parse_cli_stream(TRUNCATED)
    for offset in env["text_block_boundaries"]:
        assert 0 < offset < len(content)
    assert env["text_block_boundaries"] == sorted(env["text_block_boundaries"])
    assert len(env["text_block_boundaries"]) == env["text_block_count"] - 1


# --------------------------------------------------------------------- fail-open guarantee

def _assistant(text, msg_id="msg_test"):
    msg = {"role": "assistant", "content": [{"type": "text", "text": text}]}
    if msg_id is not None:
        msg["id"] = msg_id
    return json.dumps({"type": "assistant", "message": msg})


def test_a_message_with_no_id_is_kept():
    """Dropping real model output is far worse than keeping a line of CLI error text.

    An over-eager filter here silently eats the artefact, which is the failure class this
    module exists to end. Only an id that is present AND not a `msg_` id marks a message
    as synthesized.
    """
    stream = "\n".join([_assistant("A", msg_id=None), _assistant("B", msg_id=None)])
    content, _env = llm._parse_cli_stream(stream)
    assert content == "AB"


def test_only_a_non_msg_id_marks_a_message_synthesized():
    stream = "\n".join([_assistant("real"), _assistant("synthetic", msg_id="1f79ad1b-1dac-4402")])
    content, env = llm._parse_cli_stream(stream)
    assert content == "real"
    assert env.get("cli_error_text") == "synthetic"


# ------------------------------------------------------------------- what the caller sees

class _FakeProc:
    def __init__(self, stdout):
        self.stdout, self.stderr, self.returncode = stdout, "", 0


def test_the_headless_caller_raises_and_names_the_budget(monkeypatch):
    """The old message was "LLM returned no python code block", which sent three sessions
    after the wrong dial. The raise must say what actually happened."""
    monkeypatch.setattr(llm.shutil, "which", lambda _n: "/usr/bin/claude")
    monkeypatch.setattr(llm.subprocess, "run", lambda *a, **k: _FakeProc(TRUNCATED))
    meta = llm._call_claude_code_headless("hi", "m", {}, timeout=60)
    assert meta.get("error") is True
    message = meta.get("content") or ""
    assert "output budget" in message
    assert "output token maximum" in message, \
        "the CLI's own diagnosis must be surfaced, not 500 chars of the artefact"


def test_a_normal_reply_still_succeeds(monkeypatch):
    monkeypatch.setattr(llm.shutil, "which", lambda _n: "/usr/bin/claude")
    monkeypatch.setattr(llm.subprocess, "run", lambda *a, **k: _FakeProc(NORMAL))
    meta = llm._call_claude_code_headless("hi", "m", {}, timeout=60)
    assert not meta.get("error")
    assert meta["content"].strip()
