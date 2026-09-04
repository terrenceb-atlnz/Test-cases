"""ck-agent must invoke `claude -p` exactly as the server does — measured 2026-09-04.

The agent path had drifted from the server's transport on every axis that costs money or
correctness: it ran with the CLI's full toolset (one unit call went agentic for 20 turns
and 528k input tokens trying to read the framework tree), under the CLI's harness prompt
(so no call could ever hit the prompt cache), from the user's shell cwd (auto-injecting
whatever CLAUDE.md sat above it), with `--output-format json` (whose single `result` field
drops the head of a long answer), and it dropped the server's system steer entirely.

These drive a REAL fake `claude` (a shell script) because the flags, the cwd and the
stdin are what reach the process, and a mock of `run_claude` would test nothing.
"""
import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "ask-ck" / "agent"))
import ck_agent  # noqa: E402


def _events(*texts, result="", is_error=False, ids=None):
    lines = []
    for i, t in enumerate(texts):
        msg = {"content": [{"type": "text", "text": t}]}
        if ids and ids[i] is not None:
            msg["id"] = ids[i]
        lines.append(json.dumps({"type": "assistant", "message": msg}))
    lines.append(json.dumps({"type": "result", "result": result, "is_error": is_error,
                             "usage": {"input_tokens": 7, "output_tokens": 3},
                             "total_cost_usd": 0.01}))
    return "\n".join(lines)


@pytest.fixture
def recording_claude(tmp_path, monkeypatch):
    """A `claude` that records its argv, cwd and stdin, then prints canned stream-json."""
    out = tmp_path / "reply.txt"
    out.write_text(_events("hello"))
    binp = tmp_path / "claude"
    binp.write_text(
        "#!/bin/bash\n"
        f"printf '%s\\n' \"$@\" > {tmp_path}/argv.txt\n"
        f"pwd > {tmp_path}/cwd.txt\n"
        f"cat > {tmp_path}/stdin.txt\n"
        f"cat {out}\n")
    binp.chmod(0o755)
    monkeypatch.setattr(ck_agent, "_find_claude", lambda: str(binp))
    return tmp_path


def _argv(tmp):
    return (tmp / "argv.txt").read_text().splitlines()


def _flag_value(argv, flag):
    return argv[argv.index(flag) + 1] if flag in argv else None


def test_tools_are_disabled(recording_claude):
    ck_agent.run_claude("p", timeout=30)
    argv = _argv(recording_claude)
    assert "--tools" in argv and _flag_value(argv, "--tools") == "", argv


def test_the_harness_prompt_is_replaced_with_the_servers_steer(recording_claude):
    ck_agent.run_claude("p", timeout=30, system="BE TERSE")
    argv = _argv(recording_claude)
    assert _flag_value(argv, "--system-prompt") == "BE TERSE"
    assert "--append-system-prompt" not in argv


def test_no_steer_means_the_default_never_the_harness_prompt(recording_claude):
    ck_agent.run_claude("p", timeout=30)
    argv = _argv(recording_claude)
    assert _flag_value(argv, "--system-prompt") == ck_agent.DEFAULT_SYSTEM_PROMPT


def test_the_agent_and_server_defaults_are_one_sentence():
    """Two transports, one cache namespace: if the defaults drift, a case whose units
    split across them shares no prefix."""
    sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main" / "CK_server"))
    import llm
    assert ck_agent.DEFAULT_SYSTEM_PROMPT == llm._DEFAULT_CLI_SYSTEM_PROMPT


def test_stream_json_and_no_session_persistence(recording_claude):
    ck_agent.run_claude("p", timeout=30)
    argv = _argv(recording_claude)
    assert _flag_value(argv, "--output-format") == "stream-json"
    assert "--verbose" in argv, "stream-json in print mode requires --verbose"
    assert "--no-session-persistence" in argv


def test_the_cli_starts_in_a_neutral_directory(recording_claude):
    ck_agent.run_claude("p", timeout=30)
    cwd = Path((recording_claude / "cwd.txt").read_text().strip()).resolve()
    assert cwd.is_dir()
    assert not any((p / "CLAUDE.md").exists() for p in [cwd, *cwd.parents]), (
        f"a CLAUDE.md sits above {cwd}; the CLI will fold it into every call")
    assert _REPO.resolve() not in cwd.parents


def test_the_prompt_goes_on_stdin_untouched(recording_claude):
    ck_agent.run_claude("the whole prompt\nwith lines", timeout=30)
    assert (recording_claude / "stdin.txt").read_text() == "the whole prompt\nwith lines"


def test_all_assistant_messages_are_concatenated_in_order(recording_claude):
    (recording_claude / "reply.txt").write_text(_events("#!/usr/bin/python3\n", "class A: pass\n",
                                                        result="class A: pass\n"))
    r = ck_agent.run_claude("p", timeout=30)
    assert r["content"] == "#!/usr/bin/python3\nclass A: pass\n", (
        "the head was dropped — that is the `result`-only defect")
    assert r["error"] is False
    assert r["usage"] == {"input_tokens": 7, "output_tokens": 3} and r["total_cost_usd"] == 0.01


def test_synthesized_cli_error_text_is_not_model_output(recording_claude):
    (recording_claude / "reply.txt").write_text(
        _events("real", "API Error: exceeded", ids=["msg_1", "0b2f-uuid"]))
    assert ck_agent.run_claude("p", timeout=30)["content"] == "real"


def test_a_single_json_object_still_works(recording_claude):
    """An older CLI, or the existing cancel tests' fake, answer with one object."""
    (recording_claude / "reply.txt").write_text(json.dumps({"result": "done"}))
    assert ck_agent.run_claude("p", timeout=30)["content"] == "done"


def test_an_error_envelope_is_reported_as_an_error(recording_claude):
    (recording_claude / "reply.txt").write_text(_events(result="boom", is_error=True))
    r = ck_agent.run_claude("p", timeout=30)
    assert r["error"] is True and "boom" in r["content"]
