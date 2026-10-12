#!/usr/bin/env python3
"""ck-agent — Ask CK per-user local LLM agent.

Runs on the USER's OWN machine so their Ask CK LLM requests execute against
THEIR OWN locally-logged-in Claude Code CLI seat, never a shared one. The
shared Ask CK server never runs `claude`; instead the user's browser tab brokers
prompts from the server to this agent and posts completions back. See
archive/plans/PLAN-per-user-agent.md and, for the seat-setup flow that installs
and keeps this agent current, archive/plans/PLAN-seat-setup-and-per-seat-llm.md.

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
import select
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Bump when the contract changes; the setup script compares this against the served
# manifest to decide whether a running agent is stale and must be replaced.
AGENT_VERSION = "1.3.4"

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

# How often watch_caller checks that the requesting socket is still attached.
# Cheap (a non-blocking select + MSG_PEEK), so it can be brisk without cost;
# the window it bounds is otherwise the whole call budget.
_CALLER_POLL_SECONDS = 2.0


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


def watch_caller(sock, job_id: str, stop: "threading.Event") -> None:
    """Kill `job_id` if the HTTP caller that asked for it goes away.

    WHY THIS EXISTS (2026-09-22, t44297 #6 — PLAN-durable-agent-review.md)
    ---------------------------------------------------------------------
    `_RUNNING` + `cancel_job` already stop a run the user CANCELS: the browser hears the
    server say the job is unwanted and POSTs /cancel. That path needs the tab alive.

    When the TAB ITSELF dies -- a closed window, a dropped SSH session -- nobody is left to
    send /cancel, and the watcher loop in agent.js died with it. The run then continues to
    its full budget and is killed by `run_claude`'s own `communicate(timeout=...)`. So it is
    bounded, not infinite -- but with the server's 1800s floor that is up to half an hour of
    the user's own Claude seat spent on an answer that has nowhere to be delivered, because
    the browser that would POST it is gone and a reloaded tab starts a fresh broker with no
    memory of the job. Exactly the waste the _RUNNING comment above describes, reached by a
    different route.

    The server cannot tell us -- the browser calls this agent, never the reverse -- so the
    only local evidence is the request socket. A peer that has closed reads EOF, which is
    distinguishable from an idle-but-open connection.
    """
    while not stop.wait(_CALLER_POLL_SECONDS):
        try:
            r, _, _ = select.select([sock], [], [], 0)
            if not r:
                continue                       # nothing to read: caller still attached
            if sock.recv(1, socket.MSG_PEEK) == b"":
                break                          # clean EOF: the caller is gone
        except (OSError, ValueError):
            break                              # socket closed/invalid underneath us
        except Exception:
            return                             # never let a watchdog kill a healthy run
    else:
        return                                 # stop was set: the run finished normally
    if cancel_job(job_id):
        sys.stderr.write(
            f"ck-agent: caller for job {job_id[:8]} disconnected — killed the local run "
            "rather than spend the seat on an undeliverable answer\n")


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
        "sessions": session_capability(),
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


# ------------------------------------------------------------------ agent sessions (P1)
#
# A full-tools, long-lived Claude Code session for Ask-CK's Validation and Test Composer
# (ask-ck/plans/PLAN-agent-sessions.md, D6/D7). Not a completion: it runs device-testing's
# /test-mode in the seat's own device-testing checkout, under the seat's own login, through the
# Claude Agent SDK (D7) pointed at the system `claude` (one CLI per seat). The page starts it,
# long-polls its events and may answer its questions (W2) or send it messages (W3).
#
# The SDK is imported only when a session starts, so this file stays stdlib-only for every other
# job and a seat without the SDK still serves /run; /health says whether sessions are possible.
#
# Where things come from — the page never chooses a directory or a settings file:
#   device-testing root   CK_DT_ROOT, else `dt_root=` in ck-agent.conf, else the path the Ask-CK
#                         server advertises (its own checkout, /api/test-composer/status) when this
#                         seat can see it, else ~/claude/device-testing
#   permission profile    <dt root>/.claude/ask-ck-campaign.settings.json (D6; refused if absent)
#   hand-off file         written HERE from the page's JSON: <runs dir>/<run_id>/<run_id>.json
#   runs dir              CK_AGENT_RUNS, else `runs_dir=`, else ~/.local/share/ck-agent/runs

SESSION_SETTINGS_REL = os.path.join(".claude", "ask-ck-campaign.settings.json")
SESSION_DONE_MARKER = "ASKCK-DONE"        # /test-mode prints `ASKCK-DONE <run_id>` when stood down
# After ASKCK-DONE the session still owes the turn's ResultMessage, which carries the session's
# final cost total (subagents included). Stopping on the marker dropped it: every run's recorded
# cost missed its last turn (run 0954-val-01c5 showed $1.49 without the tester's whole triage).
# So the session closes on that result, or after this many seconds without one.
DONE_RESULT_GRACE = 120.0
D5_QUESTION_REPLY = ("Ask-CK campaign (Driver: ask-ck): no one is waiting to answer questions. "
                     "Follow /test-mode §10 (D5): send a NOTIFY, work past it, or BLOCK the case.")
HOST_PROMPT_REPLY = ("Ask-CK session: permission prompts are not answered here. The approved "
                     "profile (D6) covers bench work through tools/tb; use it, or record what you "
                     "needed with a NOTIFY and move on.")
_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")
_CASE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,40}$")


_SERVER_DT = {"at": None, "path": None}
_SERVER_DT_TTL = 300.0          # re-ask the server at most every 5 min (a failure: every 30 s)


def _fetch_server_status(origin: str) -> dict:
    """GET <origin>/api/test-composer/status. A seam: the specs swap in a fake."""
    import urllib.request  # noqa: PLC0415
    with urllib.request.urlopen(origin.rstrip("/") + "/api/test-composer/status", timeout=3) as r:
        return json.loads(r.read().decode("utf-8"))


def _server_dt_root():
    """The device-testing checkout the Ask-CK server reads campaign logs from. A session must write
    THERE for the server to see its logs, so it is the first place to look (Terrence 2026-10-12) —
    usable only when this seat sees the same path (the server host itself, or a seat mounting the
    share at that path). Cached; any failure is None."""
    now = time.monotonic()
    at = _SERVER_DT["at"]
    if at is not None and now - at < (_SERVER_DT_TTL if _SERVER_DT["path"] else 30.0):
        return _SERVER_DT["path"]
    origin = os.environ.get("CK_AGENT_ORIGIN") or _CONF.get("origin") or ""
    path = None
    if origin.startswith(("http://", "https://")):
        try:
            path = _fetch_server_status(origin).get("dt_root") or None
        except Exception:  # noqa: BLE001 — offline, old server, bad JSON: no pointer
            path = None
    _SERVER_DT.update(at=now, path=path)
    return path


def _has_profile(root: str) -> bool:
    return bool(root) and os.path.isfile(os.path.join(root, SESSION_SETTINGS_REL))


def session_dt_root() -> str:
    explicit = os.environ.get("CK_DT_ROOT") or _CONF.get("dt_root")
    if explicit:
        return explicit
    server = _server_dt_root()
    if server and _has_profile(server):
        return server
    return os.path.join(os.path.expanduser("~"), "claude", "device-testing")


def session_runs_dir() -> str:
    return (os.environ.get("CK_AGENT_RUNS") or _CONF.get("runs_dir")
            or os.path.join(os.path.expanduser("~"), ".local", "share", "ck-agent", "runs"))


def _sdk_loader():
    """The Agent SDK module. A seam: the specs swap in a fake."""
    import claude_agent_sdk  # noqa: PLC0415 — deliberately lazy (see above)
    return claude_agent_sdk


def session_capability() -> dict:
    """What /health reports about sessions: possible here, and if not, why not."""
    out = {"available": False, "sdk_version": None, "dt_root": session_dt_root(), "reason": None}
    try:
        sdk = _sdk_loader()
        out["sdk_version"] = getattr(sdk, "__version__", None)
    except Exception as e:  # noqa: BLE001
        out["reason"] = f"Claude Agent SDK not installed ({type(e).__name__}); re-run the seat setup."
        return out
    if not _has_profile(out["dt_root"]):
        server = _server_dt_root()
        seen = (f"; the Ask-CK server's checkout ({server}) is not visible from this seat" if server
                and server != out["dt_root"] else "")
        out["reason"] = (f"No device-testing checkout with the Ask-CK permission profile at "
                         f"{out['dt_root']}{seen} (set dt_root= in ck-agent.conf).")
        return out
    out["available"] = True
    return out


def _short(v, n=300):
    s = v if isinstance(v, str) else json.dumps(v, default=str)
    return s if len(s) <= n else s[:n] + f"… (+{len(s) - n})"


def _block_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(_block_text(c.get("text", "") if isinstance(c, dict) else getattr(c, "text", ""))
                         for c in content)
    return str(content or "")


def normalize_message(msg) -> list:
    """SDK message → page events (plain dicts). One message can carry several blocks."""
    kind = type(msg).__name__
    parent = getattr(msg, "parent_tool_use_id", None)
    out = []
    if kind == "AssistantMessage":
        for b in getattr(msg, "content", []) or []:
            bk = type(b).__name__
            if bk == "TextBlock":
                out.append({"kind": "text", "text": b.text, "parent": parent})
            elif bk == "ToolUseBlock":
                inp = b.input or {}
                out.append({"kind": "tool_use", "id": b.id, "name": b.name, "parent": parent,
                            "summary": _short(inp.get("description") or inp.get("command")
                                              or inp.get("prompt") or inp.get("file_path") or inp, 200),
                            "input": _short(inp, 1500)})
            elif bk == "ThinkingBlock":
                out.append({"kind": "thinking", "parent": parent})
    elif kind == "UserMessage":
        content = getattr(msg, "content", None)
        for b in content if isinstance(content, list) else []:
            if type(b).__name__ == "ToolResultBlock":
                text = _block_text(b.content)
                out.append({"kind": "tool_result", "id": b.tool_use_id, "parent": parent,
                            "is_error": bool(b.is_error), "excerpt": _short(text, 1500),
                            "denied": "auto mode classifier" in text})
    elif kind == "ResultMessage":
        out.append({"kind": "result", "subtype": msg.subtype, "is_error": msg.is_error,
                    "num_turns": msg.num_turns, "duration_ms": msg.duration_ms,
                    "total_cost_usd": msg.total_cost_usd, "usage": msg.usage,
                    "model_usage": msg.model_usage, "text": _short(msg.result or "", 4000)})
    elif hasattr(msg, "subtype") and hasattr(msg, "data"):        # SystemMessage and subclasses
        d = msg.data or {}
        st = msg.subtype
        if st.startswith("task_"):
            out.append({"kind": "task", "subtype": st, "task_id": d.get("task_id"),
                        "description": d.get("description"), "subagent_type": d.get("subagent_type"),
                        "status": d.get("status") or (d.get("patch") or {}).get("status"),
                        "background": d.get("is_backgrounded"), "summary": _short(d.get("summary") or "", 600),
                        "usage": d.get("usage")})
        elif st == "init":
            out.append({"kind": "init", "session_id": d.get("session_id"), "model": d.get("model"),
                        "permission_mode": d.get("permissionMode"), "cwd": d.get("cwd"),
                        "cli_version": d.get("claude_code_version")})
        else:
            out.append({"kind": "system", "subtype": st})
    return out


# test-mode: RESULT (logged-output §2, echoed by the sentinel), NOTIFY (§10), PROBE (§1),
# REPAIRED and REVIEWED (§11, Validation's Finalize reads REVIEWED), ASKCK-DONE (§8).
MARKERS = ("RESULT ", "NOTIFY ", "PROBE ", "REPAIRED ", "REVIEWED ", SESSION_DONE_MARKER)


def marker_lines(text: str) -> list:
    """Marker lines (MARKERS) in assistant text — the page and the server read results from
    these, never from prose."""
    out = []
    for line in (text or "").splitlines():
        s = line.strip().strip("`").strip()
        for m in MARKERS:
            if s.startswith(m):
                out.append({"kind": "marker", "marker": m.strip(), "line": s})
                break
    return out


class AgentSession:
    """One long-lived SDK session. Thread-safe: HTTP threads read events and post answers while
    the session's own thread runs an asyncio loop around ClaudeSDKClient."""

    def __init__(self, sid, run_id, handoff, mode="campaign", question_timeout=0, prompt_extra=""):
        self.id, self.run_id, self.handoff = sid, run_id, handoff
        self.mode = mode
        self.question_timeout = max(0, min(int(question_timeout or 0), 3600))
        self.prompt_extra = prompt_extra
        self.state = "starting"
        self.error = None
        self.events = []
        self.cond = threading.Condition()
        self.pending = {}          # request_id -> {"event": threading.Event, "answer": None}
        self.inbox = []            # user messages waiting to be sent
        self.stop_requested = False
        self.started = time.time()
        self.dir = os.path.join(session_runs_dir(), run_id)
        # Named <run_id>.json: device-testing's /test-mode takes the run id from the hand-off's
        # basename until it reads the JSON (its 83c0880 stopgap), so the name must BE the id.
        self.handoff_path = os.path.join(self.dir, f"{run_id}.json")
        # The sentinel's running updates (device-testing orient-dt §10, 2026-10-13): written by its
        # Haiku narrator to this file, NOT printed into the session, so the session is not woken
        # (and its whole conversation re-read) once per update. pump_updates() relays them.
        self.updates_path = os.path.join(self.dir, "sentinel-updates.jsonl")
        self._updates_off = 0
        self._done_at = None       # monotonic time ASKCK-DONE was seen; the turn's result still to come
        self._loop = None
        self._client = None
        self.thread = None

    # ---- events
    def emit(self, ev):
        with self.cond:
            ev = dict(ev, seq=len(self.events), t=round(time.time() - self.started, 2))
            self.events.append(ev)
            self.cond.notify_all()
        try:
            with open(os.path.join(self.dir, "events.jsonl"), "a", encoding="utf-8") as fh:
                fh.write(json.dumps(ev, default=str) + "\n")
        except OSError:
            pass
        return ev

    def pump_updates(self):
        """Relay new complete lines of the sentinel's updates file as `update` events; a partial
        last line waits for the next call. Never raises."""
        try:
            with open(self.updates_path, "rb") as fh:
                fh.seek(self._updates_off)
                chunk = fh.read()
        except OSError:
            return 0
        end = chunk.rfind(b"\n")
        if end < 0:
            return 0
        self._updates_off += end + 1
        n = 0
        for line in chunk[:end].decode("utf-8", "replace").splitlines():
            try:
                u = json.loads(line)
            except ValueError:
                continue
            if not isinstance(u, dict) or not (u.get("text") or u.get("attention")):
                continue
            cost = u.get("cost_usd")
            self.emit({"kind": "update", "text": _short(str(u.get("text") or ""), 1000),
                       "attention": _short(str(u["attention"]), 1000) if u.get("attention") else None,
                       "cost_usd": cost if isinstance(cost, (int, float)) else 0, "at": u.get("t")})
            n += 1
        return n

    def set_state(self, state, error=None):
        self.state = state
        if error:
            self.error = error
        self.emit({"kind": "state", "state": state, "error": error})

    def events_after(self, after, wait):
        deadline = time.time() + max(0.0, min(float(wait or 0), 25.0))
        with self.cond:
            while len(self.events) <= after and self.state not in ("done", "error", "stopped") \
                    and time.time() < deadline:
                self.cond.wait(timeout=max(0.05, deadline - time.time()))
            return self.events[after:]

    def snapshot(self):
        return {"session_id": self.id, "run_id": self.run_id, "state": self.state, "error": self.error,
                "mode": self.mode, "events": len(self.events), "started": self.started,
                "pending": sorted(self.pending)}

    # ---- the page's inputs
    def answer(self, request_id, payload):
        p = self.pending.get(request_id)
        if not p:
            return False
        p["answer"] = payload
        p["event"].set()
        return True

    def send(self, text):
        with self.cond:
            self.inbox.append(text)
            self.cond.notify_all()
        self.emit({"kind": "user_message", "text": _short(text, 2000)})

    def stop(self):
        self.stop_requested = True
        loop, client = self._loop, self._client
        if loop and client and loop.is_running() and self.state in ("starting", "running"):
            try:
                import asyncio  # noqa: PLC0415
                asyncio.run_coroutine_threadsafe(client.interrupt(), loop)
            except Exception:  # noqa: BLE001
                pass
        for p in list(self.pending.values()):
            p["event"].set()
        with self.cond:
            self.cond.notify_all()

    # ---- the run
    def prompt(self):
        cases = " ".join(c["key"] for c in self.handoff.get("cases") or [] if _CASE_RE.match(str(c.get("key", ""))))
        p = f"/test-mode --from-ask-ck {self.handoff_path} {cases}".strip()
        return p + ("\n\n" + self.prompt_extra if self.prompt_extra else "")

    async def _can_use_tool(self, tool_name, tool_input, context):
        sdk = _sdk_loader()
        rid = f"q{len(self.events)}-{int(time.time() * 1000) % 100000}"
        is_q = tool_name == "AskUserQuestion"
        self.emit({"kind": "question" if is_q else "approval", "request_id": rid, "tool": tool_name,
                   "input": tool_input if is_q else _short(tool_input, 1500),
                   "waits": self.question_timeout if (is_q or self.mode == "interactive") else 0})
        if self.question_timeout and (is_q or self.mode == "interactive"):
            import asyncio  # noqa: PLC0415
            waiter = {"event": threading.Event(), "answer": None}
            self.pending[rid] = waiter
            try:
                await asyncio.to_thread(waiter["event"].wait, self.question_timeout)
            finally:
                self.pending.pop(rid, None)
            ans = waiter["answer"]
            if ans is not None:
                self.emit({"kind": "answered", "request_id": rid, "by": "page"})
                if is_q and isinstance(ans.get("answers"), dict):
                    return sdk.PermissionResultAllow(updated_input=dict(tool_input, answers=ans["answers"]))
                if not is_q and ans.get("allow") is True:
                    return sdk.PermissionResultAllow(updated_input=tool_input)
                return sdk.PermissionResultDeny(message=str(ans.get("message") or "Denied by the user in Ask-CK."))
        self.emit({"kind": "answered", "request_id": rid, "by": "nobody"})
        return sdk.PermissionResultDeny(message=D5_QUESTION_REPLY if is_q else HOST_PROMPT_REPLY)

    async def _run(self):
        import asyncio  # noqa: PLC0415
        sdk = _sdk_loader()
        cap = session_capability()
        if not cap["available"]:
            raise RuntimeError(cap["reason"])
        dt = cap["dt_root"]
        opts = sdk.ClaudeAgentOptions(
            cwd=dt, cli_path=_find_claude() or None, settings=os.path.join(dt, SESSION_SETTINGS_REL),
            permission_mode="auto", setting_sources=["user", "project", "local"],
            env={"CK_SENTINEL_UPDATES": self.updates_path},
            can_use_tool=self._can_use_tool)
        self._loop = asyncio.get_running_loop()
        async with sdk.ClaudeSDKClient(options=opts) as client:
            self._client = client
            self.set_state("running")
            await client.query(self.prompt())
            reader = asyncio.ensure_future(self._read(client))
            next_pump = time.monotonic() + 2.0
            while not reader.done():
                if self._done_at is not None and time.monotonic() - self._done_at > DONE_RESULT_GRACE:
                    self.stop_requested = True     # the final result never came; close anyway
                if self.stop_requested:
                    reader.cancel()
                    break
                msg = None
                with self.cond:
                    if self.inbox:
                        msg = self.inbox.pop(0)
                if msg:
                    await client.query(msg)
                if time.monotonic() >= next_pump:
                    self.pump_updates()
                    next_pump = time.monotonic() + 2.0
                await asyncio.sleep(0.2)
            try:
                await reader
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            self.pump_updates()

    async def _read(self, client):
        async for msg in client.receive_messages():
            for ev in normalize_message(msg):
                self.emit(ev)
                if ev["kind"] == "text":
                    for m in marker_lines(ev["text"]):
                        self.emit(m)
                        if m["marker"] == SESSION_DONE_MARKER and self._done_at is None:
                            self._done_at = time.monotonic()
                elif ev["kind"] == "result" and self._done_at is not None:
                    self.stop_requested = True     # the final cost is in; close the session
            if self.stop_requested:
                return

    def start(self):
        os.makedirs(self.dir, exist_ok=True)
        with open(self.handoff_path, "w", encoding="utf-8") as fh:
            # sentinel_updates: where /test-mode points the sentinel's UPDATES (the env var
            # CK_SENTINEL_UPDATES says the same; the hand-off makes it explicit).
            json.dump(dict(self.handoff, sentinel_updates=self.updates_path), fh, indent=2)

        def target():
            import asyncio  # noqa: PLC0415
            try:
                asyncio.run(self._run())
                self.set_state("stopped" if self.stop_requested and not self._done_marker() else "done")
            except Exception as e:  # noqa: BLE001
                self.set_state("error", f"{type(e).__name__}: {e}")

        self.thread = threading.Thread(target=target, daemon=True, name=f"session-{self.id}")
        self.thread.start()

    def _done_marker(self):
        return any(e.get("kind") == "marker" and e.get("marker") == SESSION_DONE_MARKER for e in self.events)


_SESSIONS = {}
_SESSIONS_LOCK = threading.Lock()

# ---- after-hours runs (PLAN-agent-sessions D3, P4) ---------------------------------------
# A run scheduled for later has no tab to broker it, so THIS agent asks its Ask-CK server for
# this seat's due runs, claims one (the server hands it over once), starts the session, and
# relays the session's events to the server itself. Only runs this seat created are offered
# (the server matches the requester), so the session still runs under this seat's own login.
SCHEDULE_POLL_SECONDS = int(os.environ.get("CK_AGENT_SCHEDULE_SECONDS", "60"))


def _server_json(base, method, path, body=None, timeout=20):
    import urllib.request  # noqa: PLC0415
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base.rstrip("/") + path, data=data, method=method,
                                 headers={"Content-Type": "application/json", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"{}")


def relay_session(session, base, interval=2.0):
    """Push a session's events to the server until it ends and everything is acknowledged."""
    def run():
        sent = 0
        while True:
            evs = session.events_after(sent, 10)
            if evs:
                try:
                    _server_json(base, "POST", f"/api/test-composer/runs/{session.run_id}/events",
                                 {"events": evs, "session_id": session.id})
                    sent += len(evs)
                except Exception:  # noqa: BLE001 — retry the same batch next round
                    time.sleep(interval)
                    continue
            if session.state in ("done", "error", "stopped") and sent >= len(session.events):
                return
    t = threading.Thread(target=run, daemon=True, name=f"relay-{session.id}")
    t.start()
    return t


def poll_schedule_once(base):
    """One poll: claim and start every due run for this seat. Returns the run ids started."""
    started = []
    try:
        due = _server_json(base, "GET", "/api/test-composer/scheduled").get("due") or []
    except Exception:  # noqa: BLE001 — the server may be down; try again next round
        return started
    for d in due:
        try:
            handoff = _server_json(base, "POST", f"/api/test-composer/runs/{d['run_id']}/claim")["handoff"]
        except Exception:  # noqa: BLE001 — claimed elsewhere, or not ours
            continue
        r = start_session({"run_id": d["run_id"], "handoff": handoff, "mode": "campaign"})
        if r.get("ok"):
            relay_session(get_session(r["session_id"]), base)
            started.append(d["run_id"])
    return started


def schedule_poller(base):
    def loop():
        while True:
            if session_capability()["available"]:
                poll_schedule_once(base)
            time.sleep(max(15, SCHEDULE_POLL_SECONDS))
    threading.Thread(target=loop, daemon=True, name="schedule-poller").start()


def start_session(body: dict) -> dict:
    run_id = str(body.get("run_id") or "")
    handoff = body.get("handoff")
    if not _RUN_ID_RE.match(run_id):
        return {"ok": False, "error": "run_id missing or malformed"}
    if not isinstance(handoff, dict) or handoff.get("run_id") != run_id:
        return {"ok": False, "error": "handoff must be the run's JSON object, with the same run_id"}
    mode = body.get("mode") if body.get("mode") in ("campaign", "interactive") else "campaign"
    cap = session_capability()
    if not cap["available"]:
        return {"ok": False, "error": cap["reason"]}
    with _SESSIONS_LOCK:
        for s in _SESSIONS.values():
            if s.run_id == run_id and s.state in ("starting", "running"):
                return {"ok": True, "session_id": s.id, "already": True}
        sid = f"s{int(time.time())}-{len(_SESSIONS)}"
        s = AgentSession(sid, run_id, handoff, mode=mode,
                         question_timeout=body.get("question_timeout") or 0,
                         prompt_extra=str(body.get("note") or "")[:2000])
        _SESSIONS[sid] = s
    s.start()
    return {"ok": True, "session_id": sid, "handoff_path": s.handoff_path, "prompt": s.prompt()}


def get_session(sid):
    with _SESSIONS_LOCK:
        return _SESSIONS.get(sid)


def session_post(route: str, body: dict) -> dict:
    """The page's session writes. Each answers 200 with ok true/false (errors are the page's to show)."""
    if route == "/session/start":
        return start_session(body)
    sid, action = route.split("/")[2], route.split("/")[3]
    s = get_session(sid)
    if not s:
        return {"ok": False, "error": "no such session"}
    if action == "stop":
        s.stop()
        return {"ok": True, "state": s.state}
    if action == "message":
        text = str(body.get("text") or "").strip()
        if not text:
            return {"ok": False, "error": "empty message"}
        if s.state not in ("starting", "running"):
            return {"ok": False, "error": f"session is {s.state}"}
        s.send(text[:8000])
        return {"ok": True}
    return {"ok": s.answer(str(body.get("request_id") or ""), body), "request_id": body.get("request_id")}


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
        route, _, query = self.path.partition("?")
        if route == "/health":
            self._send(200, health_payload())
            return
        if route == "/sessions":
            with _SESSIONS_LOCK:
                self._send(200, {"ok": True, "sessions": [s.snapshot() for s in _SESSIONS.values()]})
            return
        m = re.match(r"^/session/([A-Za-z0-9-]+)/events$", route)
        if m:
            s = get_session(m.group(1))
            if not s:
                self._send(404, {"ok": False, "error": "no such session"})
                return
            q = dict(kv.split("=", 1) for kv in query.split("&") if "=" in kv)
            try:
                after, wait = int(q.get("after", 0)), float(q.get("wait", 0))
            except ValueError:
                self._send(400, {"ok": False, "error": "after/wait must be numbers"})
                return
            evs = s.events_after(max(0, after), wait)
            self._send(200, {"ok": True, "state": s.state, "error": s.error, "events": evs,
                             "next": after + len(evs), "pending": sorted(s.pending)})
            return
        self._send(404, {"error": "not found"})

    def do_POST(self):
        route = self.path.split("?")[0]
        session_route = route == "/session/start" or re.match(r"^/session/[A-Za-z0-9-]+/(answer|message|stop)$", route)
        if route not in ("/run", "/cancel", "/update", "/shutdown") and not session_route:
            self._send(404, {"error": "not found"})
            return
        if route in ("/update", "/shutdown") or session_route:
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
        if session_route:
            self._send(200, session_post(route, body))
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
        job_id = str(body.get("job_id") or "")
        # Watch the caller for the duration of the run: a tab that dies takes its /cancel
        # with it, and only this socket still knows. No job_id means nothing to cancel.
        stop = threading.Event()
        watcher = None
        if job_id:
            watcher = threading.Thread(target=watch_caller,
                                       args=(self.connection, job_id, stop), daemon=True)
            watcher.start()
        try:
            result = run_claude(prompt, body.get("model", "default"),
                                int(body.get("timeout", DEFAULT_TIMEOUT)),
                                job_id=job_id,
                                system=str(body.get("system") or ""))
        finally:
            stop.set()
            if watcher is not None:
                watcher.join(timeout=1)
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
    if ALLOWED_ORIGIN.startswith("http") and os.environ.get("CK_AGENT_SCHEDULE", "1") != "0":
        schedule_poller(ALLOWED_ORIGIN)
        print(f"  after-hours runs: polling {ALLOWED_ORIGIN} every {SCHEDULE_POLL_SECONDS}s")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
    print("ck-agent stopped.")


if __name__ == "__main__":
    main()
