#!/usr/bin/env python3
"""ck-agent — Ask CK per-user local LLM agent.

Runs on the USER's OWN machine so their Ask CK LLM requests execute against
THEIR OWN locally-logged-in Claude Code CLI seat, never a shared one. The
shared Ask CK server never runs `claude`; instead the user's browser tab brokers
prompts from the server to this agent and posts completions back. See
ask-ck/CK-main/PLAN-per-user-agent.md and, for the seat-setup flow that installs
and keeps this agent current, ask-ck/ck-facelift/PLAN-seat-setup-and-per-seat-llm.md.

Stdlib only — no pip install. Run it, leave it running, open the shared Ask CK
page, and choose "Claude Code CLI (my local machine)" in LLM -> Configure.

    python3 ck_agent.py                         # binds 127.0.0.1:8765
    CK_AGENT_PORT=9000 python3 ck_agent.py       # custom port
    CK_AGENT_ORIGIN=http://ck-box.lan:8000 python3 ck_agent.py   # lock CORS to your server
    CK_AGENT_UPDATE_ON_START=0 python3 ck_agent.py               # skip the startup `claude update`

Security model (per signed-off plan): binds 127.0.0.1 ONLY (never 0.0.0.0), and
CORS is restricted to the Ask CK server origin. No token. Any process on THIS
machine could call it, but it can only ever spend THIS user's own Claude seat.
"""
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Bump when the contract changes; the setup script compares this against the served
# manifest to decide whether a running agent is stale and must be replaced.
AGENT_VERSION = "1.2.0"

# Thinking and the answer share ONE MESSAGE's output budget (`maxOutputTokens`, 32,000 on
# the CLI and not raisable). These are reasoning models, so uncapped thinking silently
# starves the artefact — measured at 31,100 thinking tokens with zero answer text emitted.
# 2048 leaves ~30,000 of each message for the answer. NOT a ceiling on the answer: a long
# reply continues into further assistant messages, which _parse_stream concatenates.
#
# Applied ONLY to long calls, because passing the flag at all turns extended thinking ON
# (2,242ms → 16,426ms on a trivial prompt): the 30s health ping must stay fast. "Long" is
# decided by the job's timeout — the server floors long calls to 1800s and leaves short
# ones alone (llm._is_long_call / _cli_timeout), so the two sides agree by construction.
# Moved here 2026-09-10 from the server-side transport when that path was removed.
CLI_MAX_THINKING_TOKENS = 2048
LONG_CALL_SECONDS = 120

def _read_conf() -> dict:
    """`ck-agent.conf` beside this file (written by the seat setup script): origin=, port=,
    autostart=. The environment wins when set; the conf carries the settings into starts
    that have no environment of their own (a Windows logon task, a bare double-click)."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ck-agent.conf")
    conf = {}
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if "=" in line and not line.lstrip().startswith("#"):
                    k, v = line.split("=", 1)
                    conf[k.strip()] = v.strip()
    except OSError:
        pass
    return conf


_CONF = _read_conf()
PORT = int(os.environ.get("CK_AGENT_PORT") or _CONF.get("port") or "8765")

# THE CLI CONTRACT (measured 2026-09-04). This file and ck-agent.ps1 are the reference
# implementations; the gate pins both against the same captures (tests/test_ck_agent_transport.py).
#
# `claude -p` is a harness, not a completion API. Left to itself it wraps every prompt in
# its own "interactive coding agent" system prompt plus every CLAUDE.md and memory index it
# finds above the directory it starts in, gives the model tools, and keeps a transcript.
# On this path that meant ~32k tokens of harness per unit call on top of a ~12k prompt, no
# prompt-cache hit ever (the harness prompt varies per invocation), and one unit call that
# went agentic for 20 turns and 528k input tokens trying to read the framework tree.
# So, exactly as the server does:
#   --tools ""                 one completion, never an agent session
#   --system-prompt <steer>    REPLACE the harness prompt; the server sends its steer with
#                              the job, and this default covers an older server
#   --no-session-persistence   a completion is not a session
#   cwd = a neutral directory  nothing to auto-discover (no CLAUDE.md, no memory)
#   stream-json                the single `result` field drops the head of a long answer
#                              that spans several assistant messages; concatenate them
DEFAULT_SYSTEM_PROMPT = (
    "You are a precise generator. Follow the user's instructions exactly and return only "
    "what they ask for."
)


def _neutral_cwd() -> str:
    """A directory the CLI can start in without auto-discovering anything."""
    path = os.path.join(tempfile.gettempdir(), "askck-cli-cwd")
    os.makedirs(path, exist_ok=True)
    return path


def _parse_stream(raw: str):
    """(content, envelope) from `--output-format stream-json`; also accepts one JSON object.

    Every `assistant` text block is concatenated in order — the terminal `result` holds
    only the LAST message, so on a long answer it starts mid-artefact. Synthesized CLI
    error messages (a non-`msg_` id) are not model output and are dropped from the content,
    but their text is kept on the envelope as `cli_error_text`: it is the CLI's own
    diagnosis, and on a failed run it is the message the user needs. Fail open: a message
    with no id is kept, unparseable lines are skipped, and with no assistant text at all the
    result field, then the raw text, is returned.
    """
    texts, envelope, synthesized = [], {}, []
    for line in (raw or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(evt, dict):
            continue
        kind = evt.get("type")
        if kind == "assistant":
            message = evt.get("message") or {}
            chunks = [b["text"] for b in message.get("content") or []
                      if isinstance(b, dict) and b.get("type") == "text" and b.get("text")]
            if not chunks:
                continue
            msg_id = str(message.get("id") or "")
            if msg_id and not msg_id.startswith("msg_"):
                synthesized.extend(chunks)
                continue
            texts.extend(chunks)
        elif kind == "result":
            envelope = evt
        elif kind is None and evt.get("result") is not None:
            envelope = evt
    envelope = dict(envelope)
    if synthesized:
        envelope["cli_error_text"] = "".join(synthesized)[:2000]
    if texts:
        content = "".join(texts)
    elif envelope.get("result") is not None:
        content = envelope["result"]
    else:
        content = raw
    return content, envelope


def _failure_detail(out: str, err: str, returncode: int) -> str:
    """The reason a non-zero `claude -p` exit failed, in this order of trust:

    the stream's `result` event text (the CLI's own diagnosis, e.g. "API Error: 400 Claude
    Code 2.1.207 does not support this model; version 2.1.251 or newer is required"), then
    the synthesized error message text, then stderr, then the bare exit code.

    NEVER a slice of raw stdout: that is the stream's `init` event — model name, slash
    commands, tool list — which is what this used to report. On 2026-09-10 eight demo-day
    failures were logged that way and the actual reason appeared in none of them.
    """
    content, data = _parse_stream(out or "")
    for candidate in (data.get("result"), data.get("cli_error_text"), (err or "").strip()):
        text = str(candidate or "").strip()
        if text and not text.startswith("{"):
            return text[:500]
    return f"exit code {returncode}"


# Allowed browser origin (the shared Ask CK server). "*" echoes the caller's
# origin — convenient for local testing; set CK_AGENT_ORIGIN in real use.
ALLOWED_ORIGIN = os.environ.get("CK_AGENT_ORIGIN") or _CONF.get("origin") or "*"
DEFAULT_TIMEOUT = int(os.environ.get("CK_AGENT_TIMEOUT", "600"))

# job_id -> Popen, for the running CLI calls this agent owns.
#
# WHY THIS EXISTS (2026-09-02, AWPTCM-T44297)
# ------------------------------------------
# `run_claude` used `subprocess.run`, which keeps no handle, so a started `claude` could
# not be stopped. Stopping from the Ask CK UI freed the server and (after the same day's
# fix) the browser's broker loop -- but this machine kept grinding to produce an answer
# already discarded, burning the user's OWN Claude seat for up to the whole budget. With
# budgets floored to 1800s that is a half-hour of paid work for nothing.
#
# Killed as a PROCESS GROUP (start_new_session=True below), matching the server's own
# `llm._run_cli`: `claude` spawns children, and killing only the parent leaves them holding
# the seat and the pipes.
_RUNNING = {}
_RUNNING_LOCK = threading.Lock()


def cancel_job(job_id: str) -> bool:
    """Kill the CLI running `job_id`. True if there was one to kill."""
    with _RUNNING_LOCK:
        proc = _RUNNING.get(job_id)
    if proc is None:
        return False
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:
        try:
            proc.kill()          # process group gone (already reaped, or no setsid)
        except Exception:
            return False
    return True


def _jobs_in_flight() -> int:
    with _RUNNING_LOCK:
        return len(_RUNNING)


def _find_claude():
    cli = shutil.which("claude")
    if cli:
        return cli
    # The native installer's location (it does not put itself on PATH), then the
    # older ~/.claude/local layout.
    for guess in (os.path.expanduser("~/.local/bin/claude"),
                  os.path.expanduser("~/.claude/local/claude")):
        if os.path.isfile(guess) and os.access(guess, os.X_OK):
            return guess
    return None


# ---------------------------------------------------------------------------
# CLI status: version + login, and keeping the CLI current.
#
# WHY (2026-09-10, demo day). The native `claude` install auto-updates only when an
# INTERACTIVE session starts. A host where the binary is only ever spawned as `claude -p`
# — every seat whose user only ever uses Ask CK — never updates, and the CLI rots until a
# model alias it does not know appears ("Claude Code 2.1.207 does not support this model;
# version 2.1.251 or newer is required"). Three layers keep it current: this agent updates
# once at startup (`_startup_update`), the page's "Check my local agent" button calls
# `POST /update` on demand, and the server host runs a daily timer until server-side
# Claude is removed. `/health` reports `logged_in` because the old health said "ready"
# for an installed-but-logged-out CLI, and that was not true.
# ---------------------------------------------------------------------------
_STATUS_TTL = 60.0
_STATUS_CACHE = {"at": 0.0, "cli": None, "value": None}
_STATUS_LOCK = threading.Lock()
_LAST_UPDATE = {}            # result of the most recent `claude update`, for /health


def _run_quick(cli, args, timeout=20):
    try:
        return subprocess.run([cli, *args], capture_output=True, text=True, timeout=timeout,
                              cwd=_neutral_cwd())
    except Exception as e:  # noqa: BLE001 — a status probe must never take the agent down
        return e


def _cli_version(cli) -> str:
    proc = _run_quick(cli, ["--version"], timeout=20)
    if isinstance(proc, Exception):
        return ""
    text = (proc.stdout or proc.stderr or "").strip()
    m = re.search(r"\d+\.\d+\.\d+", text)
    return m.group(0) if m else text[:40]


def _auth_status(cli) -> dict:
    """`claude auth status`: JSON, exit 0 when logged in, 1 when not (CLI ≥ 2.1.2xx)."""
    proc = _run_quick(cli, ["auth", "status"], timeout=20)
    if isinstance(proc, Exception):
        return {"logged_in": False, "org": None, "error": f"auth status failed: {proc}"}
    data = {}
    try:
        data = json.loads((proc.stdout or "").strip() or "{}")
    except json.JSONDecodeError:
        data = {}
    if isinstance(data, dict) and "loggedIn" in data:
        logged_in = bool(data.get("loggedIn"))
    else:
        logged_in = proc.returncode == 0
    return {"logged_in": logged_in, "org": (data.get("orgName") if isinstance(data, dict) else None),
            "email": (data.get("email") if isinstance(data, dict) else None), "error": None}


def _invalidate_status():
    with _STATUS_LOCK:
        _STATUS_CACHE["at"] = 0.0


def _cli_status(cli) -> dict:
    """Version + login for `cli`, cached for _STATUS_TTL — both fork the CLI."""
    now = time.time()
    with _STATUS_LOCK:
        cached = _STATUS_CACHE["value"]
        if cached is not None and _STATUS_CACHE["cli"] == cli and now - _STATUS_CACHE["at"] < _STATUS_TTL:
            return cached
    value = {"cli_version": _cli_version(cli), **_auth_status(cli)}
    with _STATUS_LOCK:
        _STATUS_CACHE.update({"at": time.time(), "cli": cli, "value": value})
    return value


def update_claude(cli=None, timeout=240) -> dict:
    """Run `claude update` — unless a job is in flight, in which case say so and do nothing.

    Swapping the binary under a running call is avoidable (and on Windows impossible), so
    the button and the setup script get `{skipped: true}` and retry later. Returns
    `{ok, updated, from, to, skipped, reason, output, error}`; the status cache is
    invalidated on any attempt so `/health` reports the new version.
    """
    cli = cli or _find_claude()
    if not cli:
        return {"ok": False, "updated": False, "error": "claude CLI not found"}
    busy = _jobs_in_flight()
    if busy:
        return {"ok": True, "updated": False, "skipped": True,
                "reason": f"job in flight ({busy}); retry when the run finishes"}
    before = _cli_version(cli)
    proc = _run_quick(cli, ["update"], timeout=timeout)
    _invalidate_status()
    if isinstance(proc, Exception):
        result = {"ok": False, "updated": False, "from": before, "to": before,
                  "error": f"claude update failed: {proc}"}
    else:
        output = ((proc.stdout or "") + (proc.stderr or "")).strip()
        after = _cli_version(cli)
        result = {"ok": proc.returncode == 0, "updated": bool(before and after and before != after),
                  "from": before, "to": after, "output": output[-600:]}
        if proc.returncode != 0:
            result["error"] = f"claude update exited {proc.returncode}: {output[-300:]}"
    _LAST_UPDATE.clear()
    _LAST_UPDATE.update(result, at=time.time())
    return result


def health_payload() -> dict:
    cli = _find_claude()
    payload = {
        "ok": True,
        "agent": "ck-agent",
        "agent_version": AGENT_VERSION,
        "claude_cli": bool(cli),
        "claude_path": cli,
        "cli_version": None,
        "logged_in": None,
        "org": None,
        "jobs_in_flight": _jobs_in_flight(),
        "update_error": _LAST_UPDATE.get("error"),
        "hint": None,
    }
    if not cli:
        payload["hint"] = "Install Claude Code and run 'claude auth login'."
        return payload
    status = _cli_status(cli)
    payload.update({"cli_version": status.get("cli_version") or None,
                    "logged_in": status.get("logged_in"),
                    "org": status.get("org")})
    if status.get("error"):
        payload["hint"] = status["error"]
    elif not status.get("logged_in"):
        payload["hint"] = "Claude CLI is installed but not logged in: run 'claude auth login'."
    return payload


def run_claude(prompt: str, model: str = "default", timeout: int = DEFAULT_TIMEOUT,
               job_id: str = "", system: str = "") -> dict:
    """Run one headless `claude -p` completion on this machine's own login.

    Same flags, same neutral cwd, same stream-json parsing as ck-agent.ps1 — the two agents
    are the Claude transport, and behaviour must be identical on either OS. See the module
    note above DEFAULT_SYSTEM_PROMPT.
    """
    cli = _find_claude()
    if not cli:
        return {"content": ("ERROR: Claude Code CLI not found on this machine. Install it and run "
                            "'claude auth login' with your Claude account before using the agent."),
                "error": True}
    cmd = [cli, "-p", "--output-format", "stream-json", "--verbose", "--tools", "",
           "--no-session-persistence", "--system-prompt", system or DEFAULT_SYSTEM_PROMPT]
    if model and model != "default":
        cmd += ["--model", model]
    if timeout >= LONG_CALL_SECONDS:
        cmd += ["--max-thinking-tokens", str(CLI_MAX_THINKING_TOKENS)]
    try:
        # Popen, not subprocess.run: a run this agent cannot stop is a run that keeps
        # spending the user's seat after they pressed Stop (see _RUNNING). start_new_session
        # puts the CLI in its own process group so cancel_job can take its children too.
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, start_new_session=True,
                                cwd=_neutral_cwd())
        if job_id:
            with _RUNNING_LOCK:
                _RUNNING[job_id] = proc
        try:
            out, err = proc.communicate(input=prompt, timeout=timeout)
        except subprocess.TimeoutExpired:
            if job_id:
                cancel_job(job_id)      # takes the whole process group
            else:
                proc.kill()
            proc.communicate()          # reap, so the process does not linger as a zombie
            return {"content": f"ERROR: claude CLI timed out after {timeout}s", "error": True}
        finally:
            if job_id:
                with _RUNNING_LOCK:
                    _RUNNING.pop(job_id, None)
        if proc.returncode != 0:
            # A cancel is a negative return code from the signal, not a CLI fault. Say so:
            # "claude CLI failed: exit code -9" reads as a crash and sends the reader
            # looking at their Claude install.
            if proc.returncode < 0:
                return {"content": ("ERROR: claude CLI was cancelled on this machine "
                                    f"(signal {-proc.returncode}); nothing was kept."),
                        "error": True, "cancelled": True}
            detail = _failure_detail(out, err, proc.returncode)
            return {"content": f"ERROR: claude CLI failed: {detail}", "error": True}
        raw = (out or "").strip()
        content, data = _parse_stream(raw)
        if data.get("is_error"):
            return {"content": f"ERROR: {str(data.get('result') or content)[:500]}", "error": True}
        # Forward the CLI envelope's token accounting so the shared server's
        # debug-log + token badges populate for agent-brokered calls too
        # (the exact shape llm_debug.normalize_usage expects).
        usage = data.get("usage")
        cost = data.get("total_cost_usd")
        result = {"content": content, "error": False}
        if usage is not None:
            result["usage"] = usage
        if cost is not None:
            result["total_cost_usd"] = cost
        return result
    except Exception as e:  # noqa: BLE001 — surface anything as a clean error to the browser
        return {"content": f"ERROR: {e}", "error": True}


class Handler(BaseHTTPRequestHandler):
    server_version = f"ck-agent/{AGENT_VERSION}"

    def _cors(self):
        origin = self.headers.get("Origin", "")
        allow = origin if (ALLOWED_ORIGIN == "*" and origin) else ALLOWED_ORIGIN
        self.send_header("Access-Control-Allow-Origin", allow or "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send(self, code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self._cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path.split("?")[0] == "/health":
            self._send(200, health_payload())
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        route = self.path.split("?")[0]
        if route not in ("/run", "/cancel", "/update", "/shutdown"):
            self._send(404, {"error": "not found"})
            return
        if route in ("/update", "/shutdown"):
            # These two change the machine's state, so they insist on a JSON content type.
            # A cross-site "simple" POST (text/plain, no preflight) can reach any loopback
            # port from any page; requiring application/json forces a CORS preflight, which
            # the origin lock above then answers for the Ask CK origin only.
            ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if ctype != "application/json":
                self._send(415, {"ok": False, "error": "Content-Type must be application/json"})
                return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._send(400, {"content": "ERROR: bad JSON body", "error": True})
            return
        if route == "/cancel":
            # The browser calls this when the shared server says nobody wants the job any
            # more. Idempotent and honest: killed=false simply means it had already finished.
            killed = cancel_job(str(body.get("job_id") or ""))
            self._send(200, {"ok": True, "killed": killed})
            return
        if route == "/update":
            result = update_claude()
            result["health"] = health_payload()
            self._send(200, result)
            return
        if route == "/shutdown":
            # Used by the setup script to replace a stale agent. Answer first, then stop
            # the listener from another thread (shutdown() blocks until serve_forever exits,
            # and we are inside a request it is serving).
            self._send(200, {"ok": True, "agent_version": AGENT_VERSION, "stopping": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        prompt = body.get("prompt", "")
        if not prompt:
            self._send(400, {"content": "ERROR: no prompt", "error": True})
            return
        result = run_claude(prompt, body.get("model", "default"),
                            int(body.get("timeout", DEFAULT_TIMEOUT)),
                            job_id=str(body.get("job_id") or ""),
                            system=str(body.get("system") or ""))
        self._send(200, result)

    def log_message(self, fmt, *args):  # quieter default logging
        sys.stderr.write("ck-agent: " + (fmt % args) + "\n")


def _startup_update(cli):
    """Layer 1 of keeping the CLI current: once, before listening. Never fatal."""
    if os.environ.get("CK_AGENT_UPDATE_ON_START", "1") == "0":
        print("  claude update: skipped (CK_AGENT_UPDATE_ON_START=0)")
        return
    print("  claude update: checking…", flush=True)
    result = update_claude(cli)
    if result.get("error"):
        print(f"  claude update: FAILED — {result['error']} (continuing with {result.get('from') or 'current'})")
    elif result.get("updated"):
        print(f"  claude update: {result['from']} -> {result['to']}")
    else:
        print(f"  claude update: up to date ({result.get('to') or '?'})")


def main():
    # Line-buffered stdout: when the setup script runs us detached with stdout to agent.log,
    # block buffering held the startup lines back until exit and the log looked stuck.
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:  # noqa: BLE001 — cosmetic; never a reason not to start
        pass
    cli = _find_claude()
    print(f"ck-agent {AGENT_VERSION} starting on http://127.0.0.1:{PORT}")
    print(f"  claude CLI: {'found at ' + cli if cli else 'NOT FOUND — install + log in first'}")
    if cli:
        _startup_update(cli)
        status = _cli_status(cli)
        print(f"  claude login: {'yes (' + str(status.get('org') or '?') + ')' if status.get('logged_in') else 'NO — run: claude auth login'}")
    print(f"  CORS origin: {ALLOWED_ORIGIN}")
    print("  Leave this running; select 'Claude Code CLI (my local machine)' in Ask CK.")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
    print("ck-agent stopped.")


if __name__ == "__main__":
    main()
