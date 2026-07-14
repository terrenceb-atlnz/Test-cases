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
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("CK_AGENT_PORT", "8765"))
# Allowed browser origin (the shared Ask CK server). "*" echoes the caller's
# origin — convenient for local testing; set CK_AGENT_ORIGIN in real use.
ALLOWED_ORIGIN = os.environ.get("CK_AGENT_ORIGIN", "*")
DEFAULT_TIMEOUT = int(os.environ.get("CK_AGENT_TIMEOUT", "600"))


def _find_claude():
    cli = shutil.which("claude")
    if cli:
        return cli
    guess = os.path.expanduser("~/.claude/local/claude")
    return guess if os.path.isfile(guess) and os.access(guess, os.X_OK) else None


def run_claude(prompt: str, model: str = "default", timeout: int = DEFAULT_TIMEOUT) -> dict:
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
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=timeout)
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()[:500] or f"exit code {proc.returncode}"
            return {"content": f"ERROR: claude CLI failed: {detail}", "error": True}
        raw = (proc.stdout or "").strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict) and data.get("result") is not None:
            content = data["result"]
            if data.get("is_error"):
                return {"content": f"ERROR: {str(content)[:500]}", "error": True}
        else:
            content = raw
        return {"content": content, "error": False}
    except subprocess.TimeoutExpired:
        return {"content": f"ERROR: claude CLI timed out after {timeout}s", "error": True}
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
        if self.path.split("?")[0] != "/run":
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._send(400, {"content": "ERROR: bad JSON body", "error": True})
            return
        prompt = body.get("prompt", "")
        if not prompt:
            self._send(400, {"content": "ERROR: no prompt", "error": True})
            return
        result = run_claude(prompt, body.get("model", "default"),
                            int(body.get("timeout", DEFAULT_TIMEOUT)))
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
