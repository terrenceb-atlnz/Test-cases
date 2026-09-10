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


def test_thinking_is_capped_on_long_calls_only(recording_claude):
    """Re-homed from the server-side transport (removed 2026-09-10). Thinking shares one
    message's output budget with the answer (31,100 thinking tokens with zero answer text
    was measured), so long calls cap it; but the flag turns extended thinking ON (~7x
    slower on a trivial prompt), so a short call — the health ping — must not carry it.
    "Long" is the job's timeout, which the server floors for long calls."""
    ck_agent.run_claude("p", timeout=ck_agent.LONG_CALL_SECONDS)
    argv = _argv(recording_claude)
    assert _flag_value(argv, "--max-thinking-tokens") == str(ck_agent.CLI_MAX_THINKING_TOKENS)
    ck_agent.run_claude("p", timeout=ck_agent.LONG_CALL_SECONDS - 1)
    assert "--max-thinking-tokens" not in _argv(recording_claude)
    assert ck_agent.CLI_MAX_THINKING_TOKENS <= 32000 * 0.2, "the cap must leave the message to the answer"


def test_the_model_flag_is_passed_only_when_one_is_chosen(recording_claude):
    ck_agent.run_claude("p", model="opus", timeout=30)
    assert _flag_value(_argv(recording_claude), "--model") == "opus"
    ck_agent.run_claude("p", model="default", timeout=30)
    assert "--model" not in _argv(recording_claude), "'default' means the CLI's own default"


def test_a_truncated_reply_surfaces_the_clis_own_diagnosis(tmp_path, monkeypatch):
    """Re-homed from the server-side parser tests, against the same committed capture: on
    `is_error` the CLI's `result` text ("exceeded the N output token maximum") is the
    message, and the synthesized error message never lands in the content."""
    truncated = (_REPO / "tests" / "fixtures" / "cli_stream_truncated.jsonl").read_text(encoding="utf-8")
    content, env = ck_agent._parse_stream(truncated)
    assert "API Error" not in content, "CLI error text leaked into the artefact"
    assert "output token maximum" in env.get("cli_error_text", "")
    assert env.get("is_error") is True and env.get("terminal_reason") == "api_error"
    binp = tmp_path / "claude"
    binp.write_text(f"#!/bin/bash\ncat > /dev/null\ncat {tmp_path}/reply.txt\n")
    binp.chmod(0o755)
    (tmp_path / "reply.txt").write_text(truncated)
    monkeypatch.setattr(ck_agent, "_find_claude", lambda: str(binp))
    r = ck_agent.run_claude("p", timeout=30)
    assert r["error"] is True and "output token maximum" in r["content"]
    normal = (_REPO / "tests" / "fixtures" / "cli_stream_normal.jsonl").read_text(encoding="utf-8")
    (tmp_path / "reply.txt").write_text(normal)
    r = ck_agent.run_claude("p", timeout=30)
    assert r["error"] is False and r["content"].strip() == "Hello there, friend!"


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


# ---------------------------------------------------------------------------
# Failure reporting, health truth, and keeping the CLI current
# (PLAN-seat-setup-and-per-seat-llm.md §4 / §4.1 — the 2026-09-10 demo-day set)
# ---------------------------------------------------------------------------

_INIT_EVENT = json.dumps({"type": "system", "subtype": "init", "cwd": "/tmp/askck-cli-cwd",
                          "model": "claude-fable-5-1", "tools": [], "slash_commands": ["doctor"]})
_STALE_MSG = ("API Error: 400 Claude Code 2.1.207 does not support this model; version 2.1.251 "
              "or newer is required. Run 'claude update', or update the Claude desktop app.")


def _failing_stream():
    synthesized = json.dumps({"type": "assistant", "message": {
        "id": "0f7e-not-a-msg-id", "content": [{"type": "text", "text": _STALE_MSG}]}})
    result = json.dumps({"type": "result", "subtype": "success", "is_error": True,
                         "api_error_status": 400, "result": _STALE_MSG})
    return "\n".join([_INIT_EVENT, synthesized, result])


@pytest.fixture
def stale_cli_claude(tmp_path, monkeypatch):
    """The real 2026-09-10 failure shape: exit 1, EMPTY stderr, the reason in the stream."""
    reply = tmp_path / "reply.txt"
    reply.write_text(_failing_stream())
    binp = tmp_path / "claude"
    binp.write_text(f"#!/bin/bash\ncat > /dev/null\ncat {reply}\nexit 1\n")
    binp.chmod(0o755)
    monkeypatch.setattr(ck_agent, "_find_claude", lambda: str(binp))
    return tmp_path


def test_a_nonzero_exit_reports_the_cli_diagnosis_not_the_init_event(stale_cli_claude):
    r = ck_agent.run_claude("p", timeout=30)
    assert r["error"] is True
    assert "2.1.251 or newer is required" in r["content"], r["content"]
    assert "slash_commands" not in r["content"] and "init" not in r["content"], (
        "the init event is being reported again; the reason is hidden")


def test_failure_detail_prefers_result_then_synthesized_then_stderr_then_code():
    assert "2.1.251" in ck_agent._failure_detail(_failing_stream(), "", 1)
    synth_only = json.dumps({"type": "assistant", "message": {
        "id": "not-msg", "content": [{"type": "text", "text": "CLI said so"}]}})
    assert ck_agent._failure_detail(_INIT_EVENT + "\n" + synth_only, "", 1) == "CLI said so"
    assert ck_agent._failure_detail(_INIT_EVENT, "  boom from stderr ", 1) == "boom from stderr"
    assert ck_agent._failure_detail(_INIT_EVENT, "", 3) == "exit code 3"
    # never the init event, even when it is all there is
    assert "slash_commands" not in ck_agent._failure_detail(_INIT_EVENT, "", 1)


@pytest.fixture
def status_claude(tmp_path, monkeypatch):
    """A `claude` that answers --version, auth status and update like the real 2.1.267.

    `auth status` reads its verdict from a side file so a test can log the seat out;
    `update` reads its outcome from another, and records that it was called.
    """
    (tmp_path / "logged_in").write_text("1")
    (tmp_path / "update_out").write_text("Checking for updates to latest version...\nClaude Code is up to date (2.1.267)\n")
    (tmp_path / "version").write_text("2.1.267")
    binp = tmp_path / "claude"
    binp.write_text(
        "#!/bin/bash\n"
        f"case \"$1\" in\n"
        f"  --version) echo \"$(cat {tmp_path}/version) (Claude Code)\";;\n"
        f"  auth) if [ \"$(cat {tmp_path}/logged_in)\" = 1 ]; then\n"
        f"          echo '{{\"loggedIn\": true, \"orgName\": \"Allied Telesis Labs NZ\", \"email\": \"x@y\"}}'; exit 0;\n"
        f"        else echo '{{\"loggedIn\": false}}'; exit 1; fi;;\n"
        f"  update) echo called >> {tmp_path}/update_calls; cat {tmp_path}/update_out;;\n"
        f"  *) cat > /dev/null; echo '{{\"result\":\"done\"}}';;\n"
        "esac\n")
    binp.chmod(0o755)
    monkeypatch.setattr(ck_agent, "_find_claude", lambda: str(binp))
    monkeypatch.setattr(ck_agent, "_STATUS_TTL", 0.0)      # no caching inside a test
    ck_agent._LAST_UPDATE.clear()
    return tmp_path


def test_health_reports_version_and_login_truthfully(status_claude):
    h = ck_agent.health_payload()
    assert h["agent_version"] == ck_agent.AGENT_VERSION
    assert h["claude_cli"] is True and h["cli_version"] == "2.1.267"
    assert h["logged_in"] is True and h["org"] == "Allied Telesis Labs NZ"
    assert h["hint"] is None
    (status_claude / "logged_in").write_text("0")
    h = ck_agent.health_payload()
    assert h["logged_in"] is False, "an installed-but-logged-out CLI must not read as ready"
    assert "claude auth login" in (h["hint"] or "")


def test_health_without_a_cli_says_so(monkeypatch):
    monkeypatch.setattr(ck_agent, "_find_claude", lambda: None)
    h = ck_agent.health_payload()
    assert h["claude_cli"] is False and h["logged_in"] is None
    assert "Install Claude Code" in h["hint"]


def test_status_is_cached_for_the_ttl(status_claude, monkeypatch):
    monkeypatch.setattr(ck_agent, "_STATUS_TTL", 60.0)
    ck_agent._invalidate_status()
    assert ck_agent.health_payload()["logged_in"] is True
    (status_claude / "logged_in").write_text("0")
    assert ck_agent.health_payload()["logged_in"] is True, "within the TTL the cache answers"
    ck_agent._invalidate_status()
    assert ck_agent.health_payload()["logged_in"] is False


def test_update_reports_up_to_date_and_changed_versions(status_claude):
    r = ck_agent.update_claude()
    assert r["ok"] is True and r["updated"] is False and r["to"] == "2.1.267"
    assert (status_claude / "update_calls").read_text().count("called") == 1
    # a real update: the version file changes as a side effect of `update`
    (status_claude / "claude").write_text(
        (status_claude / "claude").read_text().replace(
            f"update) echo called >> {status_claude}/update_calls;",
            f"update) echo called >> {status_claude}/update_calls; echo 2.1.300 > {status_claude}/version;"))
    r = ck_agent.update_claude()
    assert r["updated"] is True and r["from"] == "2.1.267" and r["to"] == "2.1.300"
    assert ck_agent.health_payload()["cli_version"] == "2.1.300", "health must see the new version"


def test_update_is_skipped_while_a_job_is_in_flight(status_claude):
    with ck_agent._RUNNING_LOCK:
        ck_agent._RUNNING["job-1"] = object()
    try:
        r = ck_agent.update_claude()
    finally:
        with ck_agent._RUNNING_LOCK:
            ck_agent._RUNNING.pop("job-1", None)
    assert r.get("skipped") is True and "job in flight" in r["reason"]
    assert not (status_claude / "update_calls").exists(), "`claude update` must not run under a live call"


def test_a_failed_update_is_reported_in_health_not_fatal(status_claude):
    (status_claude / "claude").write_text(
        (status_claude / "claude").read_text().replace(
            f"cat {status_claude}/update_out;;", "echo 'network down' >&2; exit 7;;"))
    r = ck_agent.update_claude()
    assert r["ok"] is False and "exited 7" in r["error"]
    assert "exited 7" in ck_agent.health_payload()["update_error"]


def test_startup_update_can_be_disabled(status_claude, monkeypatch, capsys):
    monkeypatch.setenv("CK_AGENT_UPDATE_ON_START", "0")
    ck_agent._startup_update(str(status_claude / "claude"))
    assert not (status_claude / "update_calls").exists()
    monkeypatch.delenv("CK_AGENT_UPDATE_ON_START")
    ck_agent._startup_update(str(status_claude / "claude"))
    assert (status_claude / "update_calls").exists()
    assert "up to date" in capsys.readouterr().out


def test_the_agent_serves_update_and_shutdown_routes_json_only():
    """Structural, like the cancel-route pin: the button and the setup script need these,
    and both must insist on application/json so a cross-site simple POST cannot reach them."""
    src = (_REPO / "ask-ck" / "agent" / "ck_agent.py").read_text(encoding="utf-8")
    assert '"/update"' in src and '"/shutdown"' in src
    assert 'ctype != "application/json"' in src
    assert "self.server.shutdown" in src


# ---------------------------------------------------------------------------
# The Windows agent (ck-agent.ps1) must parse and report EXACTLY like this one.
#
# Two implementations of one contract, pinned against the same captures so a transport
# change made on one side is caught on the other. Runs through `pwsh` (installed on the
# server host 2026-09-10 for exactly this, plan §4 / D5); skips with a clear message where
# pwsh is absent — a second checkout of this repo exists without it.
# ---------------------------------------------------------------------------
import shutil as _shutil
import subprocess as _subprocess

_PWSH = _shutil.which("pwsh")
_PS_AGENT = _REPO / "ask-ck" / "agent" / "ck-agent.ps1"
_FIXTURES = _REPO / "tests" / "fixtures"
needs_pwsh = pytest.mark.skipif(not _PWSH, reason="pwsh not installed — the PowerShell agent parity pins need it (snap install powershell --classic)")


def _ps(*args, timeout=60):
    proc = _subprocess.run([_PWSH, "-NoProfile", "-NonInteractive", "-File", str(_PS_AGENT), *args],
                           capture_output=True, text=True, timeout=timeout)
    assert proc.returncode == 0, f"pwsh failed: {proc.stderr[-800:]}"
    return proc.stdout.strip()


def _py_parse_view(raw):
    content, env = ck_agent._parse_stream(raw)
    return {"content": content, "cli_error_text": env.get("cli_error_text"),
            "is_error": bool(env.get("is_error")), "result": env.get("result")}


@needs_pwsh
@pytest.mark.parametrize("fixture", ["cli_stream_normal.jsonl", "cli_stream_truncated.jsonl"])
def test_powershell_parser_matches_python_on_the_committed_captures(fixture):
    path = _FIXTURES / fixture
    ps_view = json.loads(_ps("-ParseStream", str(path)))
    assert ps_view == _py_parse_view(path.read_text(encoding="utf-8")), (
        f"ck-agent.ps1 and ck_agent.py disagree on {fixture} — the two agents have drifted")


@needs_pwsh
def test_powershell_parser_matches_python_on_the_demo_day_failure(tmp_path):
    path = tmp_path / "failing.jsonl"
    path.write_text(_failing_stream(), encoding="utf-8")
    assert json.loads(_ps("-ParseStream", str(path))) == _py_parse_view(_failing_stream())


@needs_pwsh
def test_powershell_failure_detail_matches_python(tmp_path):
    failing = tmp_path / "failing.jsonl"
    failing.write_text(_failing_stream(), encoding="utf-8")
    init_only = tmp_path / "init.jsonl"
    init_only.write_text(_INIT_EVENT, encoding="utf-8")
    assert _ps("-FailureDetail", str(failing), "-Stderr", "", "-ExitCode", "1") == \
        ck_agent._failure_detail(_failing_stream(), "", 1)
    assert _ps("-FailureDetail", str(init_only), "-Stderr", "boom from stderr", "-ExitCode", "1") == \
        ck_agent._failure_detail(_INIT_EVENT, "boom from stderr", 1) == "boom from stderr"
    assert _ps("-FailureDetail", str(init_only), "-Stderr", "", "-ExitCode", "3") == "exit code 3"


def test_the_two_agents_declare_the_same_version_and_cli_contract():
    """Structural: the served manifest carries ONE agent_version, so the two agents must
    agree on it, and the CLI flags that cost money or correctness must be present in both."""
    ps = _PS_AGENT.read_text(encoding="utf-8")
    assert f"$script:AGENT_VERSION = '{ck_agent.AGENT_VERSION}'" in ps, (
        "ck-agent.ps1 AGENT_VERSION differs from ck_agent.AGENT_VERSION")
    for needle in ("'--tools', ''", "'--no-session-persistence'", "'--system-prompt'",
                   "'stream-json'", "'--verbose'", "http://127.0.0.1:", "application/json",
                   "'/update', '/shutdown'", "claude auth login", "'auth', 'status'",
                   "'--max-thinking-tokens'", f"CLI_MAX_THINKING_TOKENS = {ck_agent.CLI_MAX_THINKING_TOKENS}",
                   f"LONG_CALL_SECONDS = {ck_agent.LONG_CALL_SECONDS}"):
        assert needle in ps, f"ck-agent.ps1 is missing {needle!r}"
    assert "0.0.0.0" not in ps.replace("never 0.0.0.0", ""), "the Windows agent must bind loopback only"
    assert ck_agent.DEFAULT_SYSTEM_PROMPT.replace("'", "''") in ps, (
        "the default steer differs between the agents")


def test_the_installer_location_is_searched_when_claude_is_not_on_path(tmp_path, monkeypatch):
    """The native installer writes ~/.local/bin/claude and does NOT put it on PATH
    (demo-day issue #1). A seat that never fixed PATH must still be found."""
    home = tmp_path / "home"
    (home / ".local" / "bin").mkdir(parents=True)
    binp = home / ".local" / "bin" / "claude"
    binp.write_text("#!/bin/bash\n")
    binp.chmod(0o755)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(ck_agent.shutil, "which", lambda _n: None)
    assert ck_agent._find_claude() == str(binp)
