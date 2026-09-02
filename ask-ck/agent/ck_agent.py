#!/usr/bin/env python3
"""ck-agent — Ask CK per-user local LLM agent.

Runs on the USER's OWN machine so their Ask CK LLM requests execute against
THEIR OWN locally-logged-in Claude Code CLI seat, never a shared one. The
shared Ask CK server never runs `claude`; instead the user's browser tab brokers
prompts from the server to this agent and posts completions back. See
ask-ck/CK-main/PLAN-per-user-agent.md.

Stdlib only — no pip install. Run it, leave it running, open the shared Ask CK
page, and choose "Claude Code CLI (my local machine)" in LLM -> Configure.

    python3 ck_agent.py                         # binds 127.0.0.1:8765
    CK_AGENT_PORT=9000 python3 ck_agent.py       # custom port
    CK_AGENT_ORIGIN=http://ck-box.lan:8000 python3 ck_agent.py   # lock CORS to your server

Security model (per signed-off plan): binds 127.0.0.1 ONLY (never 0.0.0.0), and
CORS is restricted to the Ask CK server origin. No token. Any process on THIS
machine could call it, but it can only ever spend THIS user's own Claude seat.
"""
import json
import os
import shutil
import signal
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("CK_AGENT_PORT", "8765"))
# Allowed browser origin (the shared Ask CK server). "*" echoes the caller's
# origin — convenient for local testing; set CK_AGENT_ORIGIN in real use.
ALLOWED_ORIGIN = os.environ.get("CK_AGENT_ORIGIN", "*")
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


def _find_claude():
    cli = shutil.which("claude")
    if cli:
        return cli
    guess = os.path.expanduser("~/.claude/local/claude")
    return guess if os.path.isfile(guess) and os.access(guess, os.X_OK) else None


def run_claude(prompt: str, model: str = "default", timeout: int = DEFAULT_TIMEOUT,
               job_id: str = "") -> dict:
    """Run `claude -p --output-format json` on this machine's own login.

    Mirrors the server's _call_claude_code_headless parsing exactly so behaviour
    is identical whether Claude runs here (agent) or server-side (single-user mode).
    """
    cli = _find_claude()
    if not cli:
        return {"content": ("ERROR: Claude Code CLI not found on this machine. Install it and run "
                            "'claude' then /login with your Claude account before using the agent."),
                "error": True}
    cmd = [cli, "-p", "--output-format", "json"]
    if model and model != "default":
        cmd += ["--model", model]
    try:
        # Popen, not subprocess.run: a run this agent cannot stop is a run that keeps
        # spending the user's seat after they pressed Stop (see _RUNNING). start_new_session
        # puts the CLI in its own process group so cancel_job can take its children too.
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, start_new_session=True)
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
            detail = (err or out or "").strip()[:500] or f"exit code {proc.returncode}"
            return {"content": f"ERROR: claude CLI failed: {detail}", "error": True}
        raw = (out or "").strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = None
        usage = None
        cost = None
        if isinstance(data, dict) and data.get("result") is not None:
            content = data["result"]
            if data.get("is_error"):
                return {"content": f"ERROR: {str(content)[:500]}", "error": True}
            # Forward the CLI envelope's token accounting so the shared server's
            # debug-log + token badges populate for agent-brokered calls too
            # (mirrors server-side claude_code, which keeps the same envelope).
            usage = data.get("usage")
            cost = data.get("total_cost_usd")
        else:
            content = raw
        result = {"content": content, "error": False}
        if usage is not None:
            result["usage"] = usage
        if cost is not None:
            result["total_cost_usd"] = cost
        return result
    except Exception as e:  # noqa: BLE001 — surface anything as a clean error to the browser
        return {"content": f"ERROR: {e}", "error": True}


class Handler(BaseHTTPRequestHandler):
    server_version = "ck-agent/1.0"

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
            cli = _find_claude()
            self._send(200, {
                "ok": True,
                "agent": "ck-agent",
                "claude_cli": bool(cli),
                "claude_path": cli,
                "hint": None if cli else "Install Claude Code and run 'claude' -> /login.",
            })
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        route = self.path.split("?")[0]
        if route not in ("/run", "/cancel"):
            self._send(404, {"error": "not found"})
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
        prompt = body.get("prompt", "")
        if not prompt:
            self._send(400, {"content": "ERROR: no prompt", "error": True})
            return
        result = run_claude(prompt, body.get("model", "default"),
                            int(body.get("timeout", DEFAULT_TIMEOUT)),
                            job_id=str(body.get("job_id") or ""))
        self._send(200, result)

    def log_message(self, fmt, *args):  # quieter default logging
        sys.stderr.write("ck-agent: " + (fmt % args) + "\n")


def main():
    cli = _find_claude()
    print(f"ck-agent starting on http://127.0.0.1:{PORT}")
    print(f"  claude CLI: {'found at ' + cli if cli else 'NOT FOUND — install + log in first'}")
    print(f"  CORS origin: {ALLOWED_ORIGIN}")
    print("  Leave this running; select 'Claude Code CLI (my local machine)' in Ask CK.")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
