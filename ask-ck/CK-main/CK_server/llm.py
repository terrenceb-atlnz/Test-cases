"""
LLM integration for server-backed drafting tool.

Uses prompt templating for repeatable inputs (Jinja templates inject selections + process principles).
Post-processes LLM responses with parsers for repeatable outputs (Objectives as <ul> + steps).

Real LLM support — the permitted backends are `models.SUPPORTED_AUTH_METHODS`, and that
set is a governance control (see the comment on it). Set via /set_llm_config:
  - "local_llm": the org's self-hosted vLLM. The default. Endpoint fixed in code.
  - "claude_agent": Claude Code CLI on the USER's own machine, via the browser bridge.
  - "claude_code": headless Claude Code CLI on the server host (Team subscription).
  - "grok_cli": local Grok CLI (SuperGrok / X Premium+ subscription via OAuth at x.ai)
- No separate API key needed for the CLI modes; auth lives with the locally logged-in CLI.
- There is NO caller-supplied-key mode and NO configurable endpoint. "api_key"/"account"
  and the LLM_API_KEY / LLM_BASE_URL environment fallbacks were removed 2026-08-04: they
  let the tool be pointed at an arbitrary third-party model provider. Do not re-add them.
- Better error handling + logging of exact prompts/responses (for full provenance per SERVER-README.md)
- Capture of prompts + raw responses returned to caller for storage in session.

Parsing improved for robustness (regex + JSON fallback).
Real LLM only (no MOCK/demo fallbacks). Requires valid credentials or configured subscription CLI login (grok_cli / claude_code).
"""

import os
import itertools
import json
import re
import shutil
import subprocess
import tempfile
import threading

import llm_inflight
import contextvars
import time
from jinja2 import Environment, FileSystemLoader
from typing import Dict, Any, List, Optional
import requests  # fallback, or use openai litellm for more providers later

import llm_debug
from local_llm_key import get_local_llm_key
from models import RETIRED_AUTH_METHODS, SUPPORTED_AUTH_METHODS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPTS_DIR = os.path.join(BASE_DIR, "templates", "prompts")

# Per-request browser session id, set by middleware from the X-CK-Session header.
# Used to route claude_agent jobs to the right user's browser/agent without
# persisting the (ephemeral, per-tab) id in any session config file.
current_session_id: "contextvars.ContextVar[str]" = contextvars.ContextVar("ck_session_id", default="")
# Per-request debug attribution (same middleware, same lifecycle): the browser
# panel that triggered the call (X-CK-Panel) and the API path being served.
# Read only by llm_debug.record(); never persisted to session configs.
current_panel_id: "contextvars.ContextVar[str]" = contextvars.ContextVar("ck_panel_id", default="")
current_request_path: "contextvars.ContextVar[str]" = contextvars.ContextVar("ck_request_path", default="")
# X-CK-LLM-Call — a browser-generated id for ONE LLM call, so the UI can poll live
# progress and fire a true server-side cancel. Bound by the same middleware as the
# ContextVars above; empty for non-browser callers. See llm_inflight.py.
current_llm_call_id: "contextvars.ContextVar[str]" = contextvars.ContextVar("ck_llm_call_id", default="")

env = Environment(loader=FileSystemLoader(PROMPTS_DIR))

def render_prompt(template_name: str, context: Dict[str, Any]) -> str:
    """Render a Jinja prompt template with context (selections, process excerpts, etc.)."""
    template = env.get_template(template_name)
    return template.render(**context)

def call_llm(prompt: str, model: str = "default") -> str:
    """Backward-compatible wrapper. Now requires real provider/credential (no MOCK)."""
    result = _call_llm_with_meta(prompt, provider="", model=model)
    return result.get("content", "ERROR: no content")


def check_claude_cli() -> Dict[str, Any]:
    """Report whether the Claude Code CLI is installed on this machine.

    Used by the headless "claude_code" auth mode. Only checks binary presence +
    version (no tokens are spent). Login state can't be verified without making
    a real call, so login problems surface as errors on first use instead.
    """
    path = shutil.which("claude")
    if not path:
        return {
            "available": False,
            "path": None,
            "version": None,
            "hint": ("Claude Code CLI not found on PATH for the user running this server. "
                     "Install Claude Code, then run 'claude' in a terminal and log in with "
                     "your Claude Team account before using headless mode."),
        }
    try:
        out = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=15)
        version = (out.stdout or out.stderr or "").strip() or "unknown"
    except Exception as e:
        version = f"unknown ({e})"
    return {"available": True, "path": path, "version": version, "hint": None}


def check_grok_cli() -> Dict[str, Any]:
    """Report whether the Grok CLI (xAI) is installed on this machine.

    Used by the headless "grok_cli" auth mode for SuperGrok / X Premium+
    subscriptions. Checks binary presence + version. Login state is verified
    on first real call (via the CLI's cached OAuth session).
    """
    # Prefer "grok" in PATH; fall back to the common user install location.
    path = shutil.which("grok")
    if not path:
        user_bin = os.path.expanduser("~/.grok/bin/grok")
        if os.path.isfile(user_bin) and os.access(user_bin, os.X_OK):
            path = user_bin
    if not path:
        return {
            "available": False,
            "path": None,
            "version": None,
            "hint": ("Grok CLI not found on PATH or ~/.grok/bin/grok. "
                     "Install with the script from x.ai, then run 'grok login --oauth' "
                     "with your SuperGrok or X Premium+ account."),
        }
    try:
        out = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=15)
        version = (out.stdout or out.stderr or "").strip() or "unknown"
    except Exception as e:
        version = f"unknown ({e})"
    return {"available": True, "path": path, "version": version, "hint": None}


_CANCEL_MSG = "cancelled by user (stopped from the UI; no result kept)"


def _run_cli(cmd, input_text=None, timeout: int = 180, cwd: Optional[str] = None):
    """Run a headless LLM CLI with live progress and a true cancel handle.

    `cwd` (2026-09-04): the directory the CLI starts in decides what it silently injects
    into every call — see `_cli_neutral_cwd`. Callers that want a completion pass that;
    `None` keeps the server's own cwd for anything else.

    Replaces the transports' blocking `subprocess.run` (2026-08-26, Terrence):
    that call exposed nothing until the CLI exited — no way to stop a wrong
    click (the tokens kept spending) and no way to show progress. Semantics are
    preserved exactly where the transports depend on them:

      * returns a CompletedProcess (cmd, returncode, stdout, stderr), text mode;
      * raises subprocess.TimeoutExpired after killing the process on deadline
        (subprocess.run kills the child the same way);
      * prompt via stdin when `input_text` is given — fed from a thread because
        templated prompts exceed the 64 KiB pipe buffer, and a blocking write
        alongside a blocking read is the classic feed deadlock communicate()
        exists to avoid;
      * raises RuntimeError(_CANCEL_MSG) when the in-flight registry killed it.

    What it adds: `start_new_session=True` so cancel/timeout can kill the WHOLE
    process group (the claude CLI spawns children); a stdout reader thread that
    counts stream-json lines/chars into llm_inflight as they arrive (the CLI
    streams events live — buffering them was subprocess.run's doing, not the
    CLI's); and a cancel handle (SIGTERM to the group, SIGKILL 5s later if
    ignored) registered under the browser's call id.
    """
    import os
    import signal

    call_id = current_llm_call_id.get("")
    proc = subprocess.Popen(cmd,
                            stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, start_new_session=True, cwd=cwd)

    def _kill(sig):
        try:
            os.killpg(os.getpgid(proc.pid), sig)
        except (ProcessLookupError, PermissionError, OSError):
            pass

    if call_id:
        def _cancel():
            _kill(signal.SIGTERM)
            t = threading.Timer(5.0, lambda: proc.poll() is None and _kill(signal.SIGKILL))
            t.daemon = True
            t.start()
        llm_inflight.set_cancel(call_id, _cancel)

    out_parts: list = []
    err_parts: list = []

    # context-free: pipe pump — touches only proc + the closed-over buffers;
    # progress goes to llm_inflight keyed by call_id captured in the parent.
    def _feed():
        try:
            proc.stdin.write(input_text)
            proc.stdin.close()
        except Exception:
            pass  # CLI died early — its returncode/stderr carry the story

    def _read_out():
        try:
            for line in proc.stdout:
                out_parts.append(line)
                llm_inflight.add_progress(call_id, chars=len(line), events=1)
        except Exception:
            pass

    def _read_err():
        try:
            err_parts.append(proc.stderr.read())
        except Exception:
            pass

    threads = [threading.Thread(target=_read_out, daemon=True),   # context-free: pipe pump (see _feed note)
               threading.Thread(target=_read_err, daemon=True)]  # context-free: pipe pump (see _feed note)
    if input_text is not None:
        threads.append(threading.Thread(target=_feed, daemon=True))  # context-free: pipe pump (see _feed note)
    for t in threads:
        t.start()
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill(signal.SIGKILL)   # subprocess.run also kills on timeout
        proc.wait()
        for t in threads:
            t.join(timeout=2)
        raise
    finally:
        if call_id:
            llm_inflight.set_cancel(call_id, None)
    for t in threads:
        t.join(timeout=5)
    if llm_inflight.is_cancelled(call_id):
        raise RuntimeError(_CANCEL_MSG)
    return subprocess.CompletedProcess(cmd, proc.returncode,
                                       "".join(out_parts), "".join(err_parts))


def _call_grok_cli_headless(prompt: str, model: str, meta: Dict[str, Any], timeout: int = 180) -> Dict[str, Any]:
    """Call the locally logged-in Grok CLI in single-turn headless mode.

    Auth model: the hosting user has run `grok login --oauth` (SuperGrok or
    X Premium+). We use --prompt-file for long prompts and read stdout.
    No API key is involved; usage counts against the subscription.
    """
    cli = shutil.which("grok")
    if not cli:
        user_bin = os.path.expanduser("~/.grok/bin/grok")
        if os.path.isfile(user_bin) and os.access(user_bin, os.X_OK):
            cli = user_bin
    if not cli:
        err_msg = ("ERROR: LLM call failed (grok via grok_cli): Grok CLI not found. "
                   "Run 'grok login' with your subscription account.")
        print(err_msg)
        meta.update({"content": err_msg, "raw_response": {"error": "grok CLI not on PATH"}, "error": True})
        return meta

    import tempfile
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(prompt)
            tmp = f.name

        cmd = [cli, "--prompt-file", tmp, "--output-format", "plain", "--no-memory", "--no-plan"]
        if model and model not in ("", "default"):
            cmd += ["--model", model]

        proc = _run_cli(cmd, timeout=timeout)
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()[:500] or f"exit code {proc.returncode}"
            raise RuntimeError(detail)

        content = (proc.stdout or "").strip() or (proc.stderr or "").strip()

        print(f"[LLM GROK via grok_cli] model={model or 'cli-default'}")
        print("[LLM GROK] Prompt (first 300):", prompt[:300])
        print("[LLM GROK] Response (first 300):", str(content)[:300], "...")

        meta.update({"content": content, "raw_response": {"stdout": content}, "provider": "grok"})
        return meta

    except subprocess.TimeoutExpired:
        err_msg = f"ERROR: LLM call failed (grok via grok_cli): CLI call timed out after {timeout}s"
        print(err_msg)
        meta.update({"content": err_msg, "raw_response": {"error": "timeout"}, "error": True})
        return meta
    except Exception as e:
        err_msg = f"ERROR: LLM call failed (grok via grok_cli): {str(e)}"
        print(err_msg)
        meta.update({"content": err_msg, "raw_response": {"error": str(e)}, "error": True})
        return meta
    finally:
        if tmp and os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except Exception:
                pass


# A headless CLI backend gets ONE shot at the whole response: the subprocess either
# returns complete JSON or it is killed. So the caller's `timeout` is a whole-response
# budget here — whereas on the streaming vLLM path the same number bounds only the GAP
# BETWEEN CHUNKS (the 2026-07-22b streaming fix), and a 30s read timeout there survived a
# 21-minute response. Every timeout the callers pass was tuned against that streaming
# meaning, so handing the identical number to a subprocess silently asks a reasoning model
# to finish a whole artefact in a gap-sized budget.
#
# Measured on the 2026-07-30 Opus batch, against refined cases of 30-45 Zephyr steps:
# sequence extraction 375s (caller asked 180, then 600), fragment gathering >300s (caller
# asked 300). Both failed with the CLI's own "timed out after Ns" text, which reads as a
# model or transport fault and sends you tuning the wrong dial.
#
# So: floor the CLI budget, in ONE place, rather than re-tuning five call sites for one
# backend. Precedent is right above in _call_llm_raw, which already floors local_llm's read
# timeout to 600s for the same class of reason. This is a ceiling on pathology, not an
# expected duration — a healthy call still returns in seconds, and 1800s matches the
# framework-run timeout already used as this lab's "long but bounded".
_CLI_WHOLE_RESPONSE_FLOOR = 1800

# Thinking and the answer share ONE MESSAGE's output budget (`maxOutputTokens`, 32,000 on
# the CLI and not raisable). These are reasoning models, so uncapped thinking silently
# starves the artefact — measured at 31,100 thinking tokens with zero answer text emitted.
# 2048 leaves ~30,000 of each message for the answer.
#
# THIS IS NOT A CEILING ON THE ANSWER. A long reply simply continues into further assistant
# messages, which `_parse_cli_stream` concatenates and `gen_assembly` reassembles: the four
# stored multi-message generations used 34,966-67,326 output tokens and every one is a
# complete script. The earlier claim here — that 30,000 "covers a ~44-TestCase script" and
# that larger cases need chunked generation as "a real limit" — came from
# FINDINGS-generation-size-ceiling.md, which measured a defective parser's output and
# attributed it to the model. Phase 7.4 refutes it; see the note above _size_estimate.
_CLI_MAX_THINKING_TOKENS = 2048


# THE CLI IS A HARNESS, AND THE HARNESS IS MOST OF THE BILL (measured 2026-09-04).
#
# `claude -p` wraps every prompt in Claude Code's own context: its "you are an interactive
# coding agent" system prompt (~2.6k tokens) plus everything it auto-discovers from the
# directory it is started in — every CLAUDE.md up the tree and the project's memory index.
# Started from this repo, that is ~13.5k tokens per call that no completion needs, and it
# is paid at the 1-hour cache-WRITE premium (~2x base input) on every call, because the
# harness prompt also contains per-invocation content, so no call can ever read the
# previous call's cache. Probe, same 39.7k-char unit prompt, two identical calls each:
#
#   production flags, repo cwd            32,378 tokens/call, cache read 0        $0.37 both
#   + --exclude-dynamic-system-prompt…    32,269 tokens/call, cache read 1,059    $0.34 both
#   + --system-prompt <one line>          29,676 tokens/call, 2nd call read ALL   $0.42 → $0.14
#   + neutral cwd + --no-session-persist  16,525 tokens/call, 2nd call read ALL   $0.27 → $0.11
#   --bare                                fails: needs ANTHROPIC_API_KEY, never OAuth
#
# A per-unit generate re-sends the same shared prefix 38 times, so this is the difference
# between the 2026-09-02 prompt-prefix reorder doing something and doing nothing.
# Three consequences, all applied in `_call_claude_code_headless` and mirrored in the
# per-user agent (ask-ck/agent/ck_agent.py):
#
#   * `--system-prompt` REPLACES the harness prompt with the caller's steer (or the one-line
#     default below). It was `--append-system-prompt` on the theory that the harness prompt
#     "carries context the CLI needs to function"; with `--tools ""` there is nothing for
#     that context to drive, and keeping it is what defeated caching.
#   * the subprocess starts in `_cli_neutral_cwd()` — a directory with no CLAUDE.md in any
#     ancestor and no project memory, so nothing is auto-injected.
#   * `--no-session-persistence`: a completion is not a session; without it every unit of a
#     fan-out left a transcript in ~/.claude/projects (66 in one day).
_DEFAULT_CLI_SYSTEM_PROMPT = (
    "You are a precise generator. Follow the user's instructions exactly and return only "
    "what they ask for."
)


def _cli_neutral_cwd() -> str:
    """A directory the CLI can start in without auto-discovering anything.

    Under the system temp dir, NOT under the repo or the lab home: both carry a CLAUDE.md
    that the CLI would fold into every call (and, from the repo, the memory index too —
    ~13.5k tokens, see above). Created on demand; nothing is ever written into it because
    the CLI runs with `--tools ""` and `--no-session-persistence`.
    """
    path = os.path.join(tempfile.gettempdir(), "askck-cli-cwd")
    os.makedirs(path, exist_ok=True)
    return path


def _is_long_call(timeout: int) -> bool:
    """Does this caller expect a big answer? Keyed on its requested timeout.

    The one place that decides. Two behaviours hang off it — the whole-response floor and
    the thinking cap — and both must agree, because applying either to a deliberately SHORT
    call breaks it: the health ping asks for 30s precisely so a dead backend fails fast, and
    it must neither hang for half an hour nor pay the ~7x latency of forced thinking.
    """
    return timeout >= 120


def _cli_timeout(timeout: int) -> int:
    """Whole-response floor for EVERY non-streaming headless CLI backend.

    Applies wherever that CLI runs -- on this server (`claude_code`, `grok_cli`) or on
    the user's own machine behind the browser bridge (`claude_agent`). What earns the
    floor is the transport's shape, not its location: one shot at the whole response,
    no stream to keep the budget honest. `claude_agent` was left out for months and was
    the only path where a caller's number was a real wall clock -- see _call_claude_agent.

    Short calls stay short (see _is_long_call). Mirrors the local_llm guard.
    """
    return max(timeout, _CLI_WHOLE_RESPONSE_FLOOR) if _is_long_call(timeout) else timeout


def _parse_cli_stream(raw: str):
    """(content, envelope) from `claude -p --output-format stream-json` stdout.

    Returns the model's FULL answer — every `assistant` text block concatenated in order —
    plus the terminal `result` event as the envelope (usage, cost, is_error).

    Why not just read `result`: it holds only the final assistant message. When the answer
    spans several messages the earlier ones are silently dropped, which on a long script
    means losing the beginning and keeping a mid-class tail. Concatenating is what makes the
    transport carry a whole artefact.

    Tolerant by construction, because the alternative to a partial answer must never be NO
    answer: unparseable lines are skipped, and if no assistant text is found at all it falls
    back to `result`, then to raw stdout. Also still accepts a single-object `json` payload,
    so an older CLI (or a caller that changes the format back) keeps working.
    """
    texts, envelope, message_ids, synthesized = [], {}, [], []
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
            # KEEP THE CLI'S OWN ERROR TEXT OUT OF THE ARTEFACT. When a run hits the
            # output cap the CLI appends a SYNTHESIZED assistant message carrying
            # "API Error: Claude's response exceeded the N output token maximum...".
            # It is not model output, and concatenating it put English prose on the end
            # of the generated script, where the assembler would treat it as code.
            # Real API messages are id'd `msg_...`; the synthesized one carries a UUID.
            #
            # FAIL OPEN. A message with NO id is kept: dropping real model output is far
            # worse than keeping one line of CLI error text, and this class of filter is
            # exactly where an over-eager rule silently eats an artefact. Only an id that
            # is present AND not a `msg_` id marks a message as synthesized.
            msg_id = str(message.get("id") or "")
            if msg_id and not msg_id.startswith("msg_"):
                synthesized.extend(chunks)
                continue
            texts.extend(chunks)
            message_ids.append(message.get("id"))
        elif kind == "result":
            envelope = evt
        elif kind is None and evt.get("result") is not None:
            envelope = evt            # single-object `json` output format

    # PHASE 7.1 — DO NOT DISCARD THE TRUNCATION SIGNAL.
    #
    # Both HTTP backends raise when a reply stops on `max_tokens`; this path read no
    # completion signal at all, so a generation that ran out of output budget returned
    # HTTP 200 and was stamped, linted, persisted and written to disk exactly like a
    # complete one. With nothing to the contrary, a truncated script is indistinguishable
    # from a short one.
    #
    # THE SIGNAL IS NOT WHERE YOU WOULD EXPECT IT. Captured live against CLI 2.1.207
    # (`CLAUDE_CODE_MAX_OUTPUT_TOKENS=200`, a deliberately over-long prompt): `stop_reason`
    # is `null` on EVERY genuine assistant message, including the ones that actually hit
    # the cap. The only truthy value in the whole stream sits on the CLI's synthesized
    # error message, and it reads "stop_sequence", not "max_tokens". Reading assistant
    # `stop_reason` therefore detects nothing — the first version of this fix did exactly
    # that and was dead code.
    #
    # What the CLI does emit, on the terminal `result` event:
    #     is_error: true, terminal_reason: "api_error",
    #     result: "API Error: Claude's response exceeded the 200 output token maximum..."
    # so that is what we read.
    if envelope:
        envelope = dict(envelope)
        result_text = str(envelope.get("result") or "")
        envelope["truncated"] = bool(
            envelope.get("is_error")
            and (envelope.get("terminal_reason") == "api_error"
                 or "output token maximum" in result_text))

    if texts:
        joined = "".join(texts)
        # Text-BLOCK seams, recorded for forensics. Deliberately not called message
        # boundaries: one assistant message can carry several text blocks (a thinking
        # block plus a text block share an id), so these are block offsets, and
        # `message_count` counts distinct message ids.
        env = dict(envelope) if envelope else {"result": joined}
        env["text_block_count"] = len(texts)
        env["message_count"] = len(set(mid for mid in message_ids if mid))
        env["text_block_boundaries"] = list(itertools.accumulate(len(t) for t in texts))[:-1]
        if synthesized:
            env["cli_error_text"] = "".join(synthesized)[:2000]
        return joined, env
    if envelope.get("result") is not None:
        return envelope["result"], envelope
    if synthesized:
        # No model text and no result event, but the CLI said something: surface THAT
        # rather than the raw stdout, which is where its diagnosis would otherwise die.
        return "", {"stdout": raw, "cli_error_text": "".join(synthesized)[:2000]}
    return raw, {"stdout": raw}


def _call_claude_code_headless(prompt: str, model: str, meta: Dict[str, Any], timeout: int = 180,
                               system: str = "", cap_thinking: bool = False) -> Dict[str, Any]:
    """Call the locally logged-in Claude Code CLI in headless print mode.

    Auth model: each user hosts this tool locally and has logged the CLI in with
    their own Claude Team seat ('claude' -> /login). The server passes the fully
    templated prompt on stdin ('claude -p --output-format stream-json') and parses the
    event stream. No API key or token is stored server-side; provenance records
    auth_method="claude_code" so exports are honest about the transport.

    TWO THINGS THIS MUST DO THAT IT ORIGINALLY DID NOT (both found 2026-07-30):

    `--tools ""` — **`claude -p` is an agentic coding CLI, not a completion endpoint.**
    Invoked bare it may call tools and loop for many turns, and the JSON wrapper reports
    only the aggregate. A 65k-token generate prompt consumed **2,670,565 input tokens over
    ~23 minutes for $4.65 and returned an EMPTY result** — `is_error` false, so the router
    reported the polite, misleading "LLM returned no python code block". A second attempt
    cost $5.24 the same way. With tools disabled the identical prompt ran ONE turn. The
    reason this survived: for the small JSON steps the agentic path happens to return
    usable output, so the transport looks healthy until an artefact is large.

    `system` — the caller's system message was being DROPPED here entirely. `run_prompt`
    resolves one for every call (a JSON-only steer by default, a code steer for the two
    script-emitting templates) and the HTTP backends send it; this path silently discarded
    it, so the CLI transport alone ran with no steer at all.

    It was then passed as `--append-system-prompt`, on the theory that replacing the CLI's
    own harness prompt "would strip context the CLI needs to function". Measured on
    2026-09-04, that theory was wrong and expensive: the harness prompt is what made every
    call a cache MISS, and the directory the CLI started in added ~13.5k tokens of CLAUDE.md
    + memory index per call. Now: `--system-prompt` (replace), a neutral cwd, and
    `--no-session-persistence`. The full measurement is above `_DEFAULT_CLI_SYSTEM_PROMPT`.
    """
    cli = shutil.which("claude")
    if not cli:
        err_msg = ("ERROR: LLM call failed (claude via claude_code): Claude Code CLI not found on PATH. "
                   "Install Claude Code and log in ('claude' then /login) with your Team account.")
        print(err_msg)
        meta.update({"content": err_msg, "raw_response": {"error": "claude CLI not on PATH"}, "error": True})
        return meta

    # `--tools ""` is the CLI's documented "disable all tools". Keep it unconditional:
    # every call through here wants one completion, never an agent session.
    # `stream-json` rather than `json`, because the single `result` field DOES NOT CONTAIN THE
    # WHOLE ANSWER when the model emits it across more than one message. Measured on the same
    # prompt, same model: concatenating the streamed assistant text blocks yields a script
    # that begins correctly at `#!/usr/bin/python3`, while `result` alone begins MID-CLASS at
    # `    def tear_down(self):` — the head is simply gone. A mid-class fragment is still
    # syntactically plausible Python, so it lints as an IndentationError rather than as a
    # truncation, and nothing points at the transport. `--verbose` is required to use
    # stream-json in print mode.
    cmd = [cli, "-p", "--output-format", "stream-json", "--verbose", "--tools", "",
           "--no-session-persistence"]
    if model and model != "default":
        cmd += ["--model", model]
    # REPLACE the harness prompt, never append to it — see _DEFAULT_CLI_SYSTEM_PROMPT for
    # the measurement. Always present: an absent flag means the harness prompt is back.
    cmd += ["--system-prompt", system or _DEFAULT_CLI_SYSTEM_PROMPT]
    # THE OUTPUT BUDGET IS SHARED BETWEEN THINKING AND THE ANSWER, and these are reasoning
    # models. Uncapped, thinking eats it: a live generate was observed at 31,100 thinking
    # tokens with ZERO answer text emitted yet, against a hard `maxOutputTokens` of 32,000
    # (not raisable — CLAUDE_CODE_MAX_OUTPUT_TOKENS=64000 leaves it at 32,000). The answer
    # then arrives truncated, and because a truncated reply still looks like a reply, it
    # surfaces as "no python code block" / an unparseable fragment JSON rather than as
    # "ran out of room".
    #
    # So cap thinking to leave the artefact its room. This is a floor on USABLE OUTPUT, not
    # an opinion about how much reasoning is good: on a task whose answer is ~26k tokens,
    # every thinking token is one the answer cannot have.
    #
    # ONLY on long-artefact calls, because passing the flag at all TURNS EXTENDED THINKING
    # ON: the same trivial prompt measured 2,242ms bare and 16,426ms with the flag present.
    # Applied unconditionally it made every small call ~7x slower and pushed the 30s health
    # ping into a timeout — i.e. the guard against silent truncation broke the one check
    # whose whole job is to fail fast. `cap_thinking` is derived from the caller's ORIGINAL
    # timeout by _call_llm_raw, the same signal the whole-response floor uses, so "this is a
    # long call" is decided in one place rather than guessed twice.
    if cap_thinking:
        cmd += ["--max-thinking-tokens", str(_CLI_MAX_THINKING_TOKENS)]

    try:
        # Prompt via stdin: templated prompts can exceed argv limits. _run_cli is
        # subprocess.run with a kill handle + live stream-json progress (llm_inflight).
        proc = _run_cli(cmd, input_text=prompt, timeout=timeout, cwd=_cli_neutral_cwd())
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()[:500] or f"exit code {proc.returncode}"
            raise RuntimeError(detail)

        raw = proc.stdout.strip()
        content, data = _parse_cli_stream(raw)
        # PHASE 7.1 — say WHICH failure this was. `data["result"]` carries the CLI's own
        # diagnosis ("API Error: Claude's response exceeded the N output token maximum");
        # `content` is the answer text, so raising on `content` first showed 500 characters
        # of the artefact and hid the reason entirely. Prefer the diagnosis, and name the
        # budget case explicitly so it cannot be read as a model or prompt fault.
        if data.get("truncated"):
            raise RuntimeError(
                f"the model ran out of output budget after {len(content or ''):,} characters "
                f"across {data.get('message_count', 1)} message(s) — the answer is "
                f"incomplete. CLI reported: "
                f"{str(data.get('result') or data.get('cli_error_text') or '')[:300]}")
        if data.get("is_error"):
            raise RuntimeError(str(data.get("result") or content)[:500])

        print(f"[LLM CLAUDE via claude_code] model={model or 'cli-default'}")
        print("[LLM CLAUDE] Prompt (first 300):", prompt[:300])
        print("[LLM CLAUDE] Response (first 300):", str(content)[:300], "...")
        meta.update({"content": content, "raw_response": data, "provider": "claude"})
        return meta

    except subprocess.TimeoutExpired:
        err_msg = f"ERROR: LLM call failed (claude via claude_code): CLI call timed out after {timeout}s"
        print(err_msg)
        meta.update({"content": err_msg, "raw_response": {"error": "timeout"}, "error": True})
        return meta
    except Exception as e:
        err_msg = f"ERROR: LLM call failed (claude via claude_code): {str(e)}"
        print(err_msg)
        meta.update({"content": err_msg, "raw_response": {"error": str(e)}, "error": True})
        return meta


def _call_claude_agent(prompt: str, model: str, meta: Dict[str, Any], session_id: str, timeout: int,
                       system: str = "") -> Dict[str, Any]:
    """Route a Claude call to the USER's own machine via the browser-brokered agent.

    The server does not run `claude`; it enqueues the prompt for `session_id` and
    blocks until that user's browser (which talks to their local ck-agent) posts the
    completion back. This is what makes a shared server use each user's own seat.
    See ask-ck/CK-main/PLAN-per-user-agent.md.

    `system` (2026-09-04) rides with the job so the user's ck-agent can pass it as the
    CLI's `--system-prompt`, exactly as the server-side transport does. Until then this
    path dropped the steer entirely — the same defect `_call_claude_code_headless` had
    fixed on 2026-07-30 — and ran under the CLI's full harness prompt with tools enabled,
    which is how one unit call went agentic for 20 turns and 528k input tokens (09-02).
    """
    from agent_jobs import registry  # local import avoids a hard dep at module load
    session_id = session_id or current_session_id.get("")
    if not session_id:
        meta.update({"content": ("ERROR: Claude-agent mode needs a browser session id but none was "
                                 "provided. Reload the Ask CK page."), "error": True})
        return meta
    # True cancel (2026-08-26): the job's Event is the one thing submit blocks
    # on, so cancelling = stamp a cancelled result and set the Event. The user's
    # local agent may still finish its call on their own machine, but the result
    # is discarded (the job is gone from the registry when it posts back).
    _cid = current_llm_call_id.get("")
    def _on_start(job):
        def _cancel():
            job.result = {"content": f"ERROR: LLM call failed (claude via claude_agent): {_CANCEL_MSG}",
                          "error": True, "cancelled": True}
            job.event.set()
        llm_inflight.set_cancel(_cid, _cancel)
    # The whole-response floor, which this path never had (2026-09-01).
    #
    # `claude_agent` is a headless `claude` CLI exactly like `claude_code` -- it just runs
    # on the user's machine instead of this one. It gets ONE shot at the whole response and
    # there is no stream to keep the socket honest, so the caller's `timeout` is a wall
    # clock here. Every other transport was already protected: `claude_code`/`grok_cli` are
    # floored by `_cli_timeout` inside `_call_*_headless`, and `local_llm` streams, so its
    # number bounds the gap between chunks rather than the total. This path alone took the
    # caller's raw value, which is why `gather_fragments` died at a hard 300s on 2026-08-27
    # (AWPTCM-T44191) and why `generate_script` -- measured at 297-778s on real cases and
    # rising with the fragment count, not the step count -- dies at 600s on a large one.
    #
    # Flooring HERE rather than at each call site is deliberate: the same argument
    # `_CLI_WHOLE_RESPONSE_FLOOR` already makes -- fix the backend that mis-reads the
    # number, do not re-tune five callers for one transport.
    #
    # The floored value is what `submit` waits on AND what is handed to the browser, which
    # passes it to the local ck-agent as its `subprocess.run` budget (agent.js -> ck_agent.py).
    # Server and agent must stay on ONE number or the loser's work is discarded -- that
    # sharing is the 2026-08-27 fix (3224629) and flooring before `submit` preserves it.
    timeout = _cli_timeout(timeout)
    result = registry.submit(session_id, prompt, model, timeout,
                             on_start=_on_start if _cid else None,
                             system=system or _DEFAULT_CLI_SYSTEM_PROMPT)
    llm_inflight.set_cancel(_cid, None)
    meta.update({"content": result.get("content", ""), "raw_response": result,
                 "error": bool(result.get("error")), "provider": "claude"})
    return meta


def _call_llm_with_meta(prompt: str, provider: str = "", api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "default", auth_method: str = "local_llm", timeout: int = 180, session_id: str = "", template: str = "", dry_run: bool = False, system: str = "", max_tokens: Optional[int] = None) -> Dict[str, Any]:
    """Instrumented wrapper around _call_llm_raw (same signature + `template`).

    Times the call, normalizes token usage from the raw response
    (llm_debug.normalize_usage), and records the request — success or failure —
    to the per-session debug log (llm_debug.record). Keeps the original
    never-raises contract: _call_llm_raw never raises, and the recorder
    swallows its own errors. All pre-existing callers hit this wrapper
    unchanged and are auto-instrumented.

    dry_run: render-only preview. The caller has already built `prompt` through
    the exact real context path, so returning it here (WITHOUT sending to the
    LLM) yields a provenance prompt that is byte-identical to what a real send
    would transmit — that is the whole point: the "Refresh" provenance preview
    reuses the same call path with this flag flipped, so 1-for-1 is guaranteed
    by construction, not by re-implementing context-building. No send, no tokens,
    and NOT written to debug-log (it was never a real request).
    """
    if dry_run:
        return {
            "content": "", "prompt": prompt, "provider": provider,
            "model": model, "auth_method": auth_method, "template": template,
            "usage": None, "error": False, "dry_run": True,
        }
    # Register with the in-flight registry (progress polling + true cancel).
    # Placed AFTER the dry_run return above: a dry run sends nothing, so there
    # is nothing to watch or stop. Registered even with no browser call id —
    # register() no-ops on "" — so this stays zero-cost for headless callers.
    call_id = current_llm_call_id.get("")
    llm_inflight.register(call_id, template=template, auth_method=auth_method)
    start = time.monotonic()
    try:
        meta = _call_llm_raw(prompt, provider=provider, api_key=api_key, base_url=base_url,
                             model=model, auth_method=auth_method, timeout=timeout,
                             session_id=session_id, system=system, max_tokens=max_tokens)
        if llm_inflight.is_cancelled(call_id):
            meta["cancelled"] = True
    finally:
        llm_inflight.finish(call_id)
    duration_ms = int((time.monotonic() - start) * 1000)
    meta["template"] = template
    meta["usage"] = llm_debug.normalize_usage(meta.get("auth_method", auth_method),
                                              meta.get("raw_response"))
    llm_debug.record(meta, duration_ms)
    return meta


def _call_llm_raw(prompt: str, provider: str = "", api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "default", auth_method: str = "local_llm", timeout: int = 180, session_id: str = "", system: str = "", max_tokens: Optional[int] = None) -> Dict[str, Any]:
    """Core LLM caller with multi-provider support. Real use only - no MOCK or demo fallbacks.

    Supports the approved login styles only — `models.SUPPORTED_AUTH_METHODS`, enforced
    below. There is no caller-supplied-key mode and no configurable endpoint.
    - "claude_agent": browser-brokered local Claude Code CLI on the USER's machine
      (shared-server safe — each user spends their own seat; needs session_id).
    - "claude_code": the same Claude CLI run directly on the SERVER host. Not in the UI
      (interactive use would spend the server's seat) but NOT dead: claude_agent needs a
      browser tab to relay through, so it cannot run headless — this is the path every
      unattended batch run takes. See the note in models.LLMConfig.
    - "grok_cli": headless Grok CLI (SuperGrok / X Premium+ subscription via OAuth).
      No key/token stored by server; auth lives in the local CLI's login.
    - "local_llm": the organization's self-hosted vLLM endpoint (OpenAI-compatible).
      Key is server-resolved (Configure page -> secrets.local.json); never supplied by
      the browser, and there is no env fallback. Model = vllm-fast | vllm-thinking.

    provider: "grok" | "claude" | "openai" (no "mock")
    If no valid credential and not using a supported headless CLI auth_method, the call will error.
    """
    provider = (provider or "").lower()
    auth_method = (auth_method or "local_llm").lower()

    # THE BACKEND ALLOWLIST — enforced here, at the transport, not only at the endpoint
    # that sets the config. `set_llm_config` already 400s on a retired method, but a
    # session persisted before 2026-08-04 can still carry `auth_method: "api_key"`, and
    # loading one must not quietly resume calling a third-party endpoint. Refuse it
    # instead: the operator re-picks a backend on the Configure page.
    if auth_method not in SUPPORTED_AUTH_METHODS:
        if auth_method in RETIRED_AUTH_METHODS:
            err_msg = (
                f"ERROR: LLM call refused — auth_method '{auth_method}' was retired on "
                f"2026-08-04. This tool talks only to approved backends "
                f"({', '.join(SUPPORTED_AUTH_METHODS)}). Choose one on the LLM Configure page."
            )
        else:
            err_msg = (
                f"ERROR: LLM call refused — unknown auth_method '{auth_method}'. "
                f"Supported: {', '.join(SUPPORTED_AUTH_METHODS)}."
            )
        print(err_msg)
        return {
            "prompt": prompt, "model": model, "provider": provider,
            "auth_method": auth_method, "content": err_msg,
            "raw_response": {"error": "unsupported auth_method"}, "error": True,
        }

    if auth_method == "local_llm":
        # Org-hosted vLLM (OpenAI-compatible) — rides the standard OpenAI HTTP
        # path below. Forced here centrally so every caller is covered; the key
        # NEVER comes from cfg/browser (see local_llm_key.py). If no key is
        # stored, the normal no-credential guard below errors cleanly.
        provider = "openai"
        base_url = "http://vllm.ai.atlnz.lc/v1"
        if not model or model == "default":
            model = "vllm-fast"
        api_key = get_local_llm_key()

    if provider == "mock":
        err_msg = "ERROR: MOCK provider is no longer supported. Use a real provider (grok/claude/openai) with credentials or CLI auth_method."
        print(err_msg)
        meta = {"content": err_msg, "raw_response": {"error": "mock removed"}, "error": True, "provider": "mock"}
        return meta

    if not provider:
        provider = "grok"  # sensible default for subscription use

    # Defaults
    if provider == "grok":
        base_url = base_url or "https://api.x.ai/v1"
        model = model or "grok-beta"
    elif provider == "claude":
        base_url = base_url or "https://api.anthropic.com/v1"
        model = model or "claude-3-5-sonnet-20241022"
    else:
        base_url = base_url or "https://api.openai.com/v1"
        model = model or "gpt-4o-mini"

    meta = {
        "prompt": prompt,
        "model": model,
        "base_url": base_url,
        "provider": provider,
        "auth_method": auth_method,
    }

    # Headless CLI modes (subscription accounts) need no credential here.
    if provider == "claude" and auth_method == "claude_agent":
        # NOT given the floor below: this timeout also bounds the agent-bridge long-poll a
        # user's browser is holding open, so stretching it to half an hour degrades the one
        # path with a human waiting on the other end.
        return _call_claude_agent(prompt, model, meta, session_id=session_id, timeout=timeout,
                                  system=system)
    if provider == "claude" and auth_method == "claude_code":
        # `_is_long_call(timeout)` is the single "this call expects a big answer" signal:
        # it both floors the subprocess budget and caps thinking. Deriving both from one
        # predicate keeps them from disagreeing about which calls are the long ones.
        return _call_claude_code_headless(prompt, model, meta, timeout=_cli_timeout(timeout),
                                          system=system,
                                          cap_thinking=_is_long_call(timeout))
    if provider == "grok" and auth_method == "grok_cli":
        return _call_grok_cli_headless(prompt, model, meta, timeout=_cli_timeout(timeout))

    credential = api_key
    if not credential:
        if auth_method == "local_llm":
            err_msg = ("ERROR: LLM call failed (local_llm): no Local LLM key is stored on the server. "
                       "Enter your key on the LLM Configure page (or export LOCAL_LLM_KEY) and retry.")
        else:
            err_msg = (f"ERROR: LLM call failed ({provider} via {auth_method}): no credential and "
                       f"not a headless CLI mode. Pick a backend on the LLM Configure page "
                       f"({', '.join(SUPPORTED_AUTH_METHODS)}) — there is no environment-key fallback.")
        print(err_msg)
        meta.update({
            "content": err_msg,
            "raw_response": {"error": "no credential"},
            "error": True,
        })
        return meta

    # HTTP timeout is a (connect, read) pair, not one scalar. The org models are
    # REASONING models that emit a long message.reasoning_content phase BEFORE the
    # answer. The OpenAI-compatible path below now STREAMS (stream=True): with a
    # streamed body, the `read` component is the max gap BETWEEN chunks, not a
    # whole-response wall clock. vLLM emits reasoning_content deltas throughout the
    # thinking phase, so the socket never goes silent — this is the structural fix
    # for `vllm-thinking` timing out on the largest-output step (generate_script),
    # which a static read ceiling could still be exceeded by (Part 2B: failed even
    # at the 600s floor). See PLAN-pytest-testing §7.7.
    #
    # A single hardcoded 120s (the bug two fixes ago) ignored the caller's
    # `timeout`; the interim fix honored it as a whole-response ceiling. With
    # streaming the same (connect, read) pair now bounds connect + inter-chunk gap,
    # which is generous headroom regardless of total generation length. The
    # non-streamed Anthropic path below still treats `read` as the whole-response
    # budget (it had no structural read-timeout failure — one harness-timeout
    # outlier only).
    connect_timeout = 10
    read_timeout = timeout
    # Floor the read budget for the reasoning vLLM path — but ONLY when the caller
    # asked for a real (>=120s) budget. A deliberately short timeout (the health
    # ping passes 30s and wants to fail fast on a dead backend) is respected as-is.
    # Under streaming this floors the inter-chunk gap tolerance, not a total ceiling.
    if auth_method == "local_llm" and read_timeout >= 120:
        read_timeout = max(read_timeout, 600)
    http_timeout = (connect_timeout, read_timeout)

    # Real calls
    try:
        if provider == "claude":
            # Anthropic native API (not OpenAI compatible)
            headers = {
                "x-api-key": credential,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            payload = {
                "model": model,
                "max_tokens": max_tokens or 2000,
                "temperature": 0.2,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system:
                payload["system"] = system  # Anthropic: top-level field, not a message role
            resp = requests.post(f"{base_url}/messages", headers=headers, json=payload, timeout=http_timeout)
            resp.raise_for_status()
            data = resp.json()
            # Anthropic returns content as list of blocks
            content = ""
            for block in data.get("content", []):
                if block.get("type") == "text":
                    content += block.get("text", "")
            # Mirror the OpenAI branch's guards (see below). Without them this path
            # reported success for two real failures: an empty content array (or one
            # holding only thinking blocks) returned content="" with error unset, and a
            # response truncated at the max_tokens cap was accepted as complete — so
            # downstream JSON parsing failed and looked like "the LLM found nothing".
            stop_reason = data.get("stop_reason")
            cap = max_tokens or 2000
            if not content:
                if stop_reason == "max_tokens":
                    raise ValueError(
                        "model hit the token cap during reasoning and returned no "
                        f"answer (stop_reason=max_tokens, max_tokens={cap}). "
                        "Raise max_tokens or shorten the prompt."
                    )
                # Thinking-only response: prefer its text over failing outright.
                content = "".join(
                    b.get("thinking", "") or b.get("text", "")
                    for b in data.get("content", []) if b.get("type") != "text"
                )
                if not content:
                    raise ValueError(
                        f"provider returned an empty completion (stop_reason={stop_reason})."
                    )
            elif stop_reason == "max_tokens":
                raise ValueError(
                    "model output was truncated at the token cap "
                    f"(stop_reason=max_tokens, max_tokens={cap}); the answer is "
                    "incomplete. Raise max_tokens or reduce the prompt size."
                )
            print(f"[LLM CLAUDE via {auth_method}] model={model}")
            print("[LLM CLAUDE] Prompt (first 300):", prompt[:300])
            print("[LLM CLAUDE] Response (first 300):", content[:300], "...")
            meta.update({"content": content, "raw_response": data, "provider": "claude"})
            return meta

        else:
            # Grok / OpenAI compatible
            headers = {
                "Authorization": f"Bearer {credential}",
                "Content-Type": "application/json",
            }
            # Grok sometimes prefers x-api-key too, but Bearer works for most
            if provider == "grok":
                headers["x-api-key"] = credential  # some Grok setups prefer this

            # max_tokens covers the WHOLE completion. The org vLLM models are
            # reasoning models: they spend completion tokens on hidden
            # chain-of-thought (returned in message.reasoning_content) BEFORE
            # emitting the answer in message.content. A small cap (the legacy
            # 2000) is exhausted mid-reasoning, so the model stops with
            # finish_reason="length" and content stays null; a moderate cap lets
            # short answers through but truncates long structured ones (e.g. a
            # 40-candidate match table) mid-JSON. Give reasoning models generous
            # headroom so real answers complete. Callers with unusually large
            # expected output (e.g. pt_generate_script, which emits a whole
            # standardized script) pass an explicit `max_tokens` override —
            # confirmed necessary empirically: a real generate_script run hit
            # finish_reason=length at the 16000 default (Part 2B, 2026-07-22).
            max_out = max_tokens or (16000 if auth_method == "local_llm" else 2000)
            # A system message steers these reasoning models toward the terse,
            # JSON-only answer the callers want, and sharply curbs the runaway
            # chain-of-thought that otherwise burns the token budget (measured
            # ~22x fewer completion tokens on a trivial JSON ask). Matches the
            # documented vLLM usage shape (system + user) in resources.md.
            messages = ([{"role": "system", "content": system}] if system else []) \
                + [{"role": "user", "content": prompt}]
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": max_out,
                # STREAM the response. For reasoning models this keeps the socket
                # alive through the (arbitrarily long) chain-of-thought phase, so
                # the read timeout bounds the gap between chunks rather than the
                # total generation time — the structural fix for vllm-thinking
                # timing out on generate_script even at the 600s floor (§7.7).
                "stream": True,
                # Streamed OpenAI responses omit `usage` unless asked; without this
                # the observability token badges (normalize_usage → prompt_tokens/
                # completion_tokens) would go blank for every streamed call. vLLM
                # honors include_usage and sends a final usage-only chunk.
                "stream_options": {"include_usage": True},
            }
            endpoint = f"{base_url}/chat/completions"
            # Accumulate the streamed deltas into the same (content, finish, usage)
            # triplet the non-streamed path produced, so all the guards + the
            # reconstructed raw_response below are byte-for-byte equivalent.
            content_parts: list = []
            reasoning_parts: list = []
            finish = None
            usage = None
            _cid = current_llm_call_id.get("")
            with requests.post(endpoint, headers=headers, json=payload,
                               timeout=http_timeout, stream=True) as resp:
                resp.raise_for_status()
                # True cancel (2026-08-26): closing the response tears the SSE
                # stream down mid-generation, so the line iterator raises on its
                # next read and the cancelled check below names the reason. vLLM
                # stops generating when the client goes away.
                llm_inflight.set_cancel(_cid, resp.close)
                # SSE responses are Content-Type: text/event-stream, and requests'
                # get_encoding_from_headers maps ANY "text" type to ISO-8859-1 (RFC 2616
                # default) — so decode_unicode below would build a latin-1 decoder and
                # mojibake every non-ASCII byte: "port — 1 µs" arrives as "port â 1 Âµs".
                # It corrupts silently (no replacement char) and the result is still
                # valid JSON, so it flows through into the stored objective/steps and on
                # to Zephyr. Em-dashes and micro signs are routine in this output.
                # Found by a skeptic while refuting the narrower chunk-boundary claim
                # (backlog llm.py:494 — that one really is a non-issue; the incremental
                # decoder handles split sequences correctly).
                resp.encoding = "utf-8"
                for line in resp.iter_lines(decode_unicode=True):
                    if not line:
                        continue  # SSE keep-alive / blank separator line
                    if line.startswith("data:"):
                        line = line[len("data:"):].strip()
                    if line == "[DONE]":
                        break
                    try:
                        chunk = json.loads(line)
                    except (ValueError, TypeError):
                        continue  # SSE comment (":...") or partial frame — skip
                    # The final include_usage chunk carries usage with empty choices.
                    if chunk.get("usage"):
                        usage = chunk["usage"]
                    for ch in (chunk.get("choices") or []):
                        delta = ch.get("delta") or {}
                        if delta.get("content"):
                            content_parts.append(delta["content"])
                            llm_inflight.add_progress(_cid, chars=len(delta["content"]), events=1)
                        if delta.get("reasoning_content"):
                            reasoning_parts.append(delta["reasoning_content"])
                            llm_inflight.add_progress(_cid, chars=len(delta["reasoning_content"]), events=1)
                        if ch.get("finish_reason"):
                            finish = ch["finish_reason"]
                    if llm_inflight.is_cancelled(_cid):
                        raise RuntimeError(_CANCEL_MSG)
            llm_inflight.set_cancel(_cid, None)
            content = "".join(content_parts)
            reasoning_content = "".join(reasoning_parts)
            # Reconstruct the non-streamed response shape so downstream (usage
            # normalization, debug log, provenance) sees an identical structure.
            data = {
                "choices": [{
                    "message": {"content": content, "reasoning_content": reasoning_content},
                    "finish_reason": finish,
                }],
            }
            if usage is not None:
                data["usage"] = usage
            message = data["choices"][0]["message"]
            # `content` is "" (falsy) when nothing streamed — the guards below
            # treat that identically to the non-streamed path's JSON `null`.
            # Reasoning models can leave content null when the answer was
            # squeezed out by the reasoning budget. Distinguish the failure
            # shapes so the debug log says WHY, instead of a cryptic
            # "'NoneType' object is not subscriptable".
            if not content:
                if finish == "length":
                    raise ValueError(
                        "model hit the token cap during reasoning and returned no "
                        f"answer (finish_reason=length, max_tokens={max_out}). "
                        "Raise max_tokens or shorten the prompt."
                    )
                # A reasoning-only response (content empty, thoughts present):
                # fall back to reasoning_content rather than fail outright.
                content = message.get("reasoning_content") or ""
                if not content:
                    raise ValueError(
                        f"provider returned an empty completion (finish_reason={finish})."
                    )
            # Non-empty BUT truncated at the cap: the answer (often JSON) is cut
            # off mid-token. Downstream JSON parsing would then silently fail and
            # degrade to a fallback that looks like "the LLM found nothing".
            # Surface it as a real error so the cause is visible.
            elif finish == "length":
                raise ValueError(
                    "model output was truncated at the token cap "
                    f"(finish_reason=length, max_tokens={max_out}); the answer is "
                    "incomplete. Raise max_tokens or reduce the prompt size."
                )

            print(f"[LLM {provider.upper()} via {auth_method}] Provider: {base_url} model={model}")
            print("[LLM] Prompt (first 300):", prompt[:300])
            print("[LLM] Response (first 300):", content[:300], "...")

            meta.update({
                "content": content,
                "raw_response": data,
                "provider": provider,
            })
            return meta

    except Exception as e:
        # A user-cancelled stream can surface as the transport's own teardown
        # exception (resp.close() makes iter_lines raise mid-read) — name the
        # real cause instead of a ChunkedEncodingError nobody asked for.
        if llm_inflight.is_cancelled(current_llm_call_id.get("")):
            e = RuntimeError(_CANCEL_MSG)
        err_msg = f"ERROR: LLM call failed ({provider} via {auth_method}): {str(e)}"
        # Preserve the provider's HTTP error body (quota / rate-limit reasons
        # etc. were previously discarded — only str(e) survived). Full body goes
        # to error_detail for the debug log; the first ~300 chars are folded
        # into the content message so wizard provenance / pytest 502 details
        # surface the reason too.
        error_detail = ""
        if isinstance(e, requests.HTTPError) and getattr(e, "response", None) is not None:
            try:
                error_detail = (e.response.text or "")[:2000]
            except Exception:
                error_detail = ""
        if error_detail:
            err_msg += " | provider said: " + error_detail[:300]
        print(err_msg)
        meta.update({
            "content": err_msg,
            "raw_response": {"error": str(e)},
            "error": True,
        })
        if error_detail:
            meta["error_detail"] = error_detail
        return meta

def parse_llm_to_structured(llm_output: str, case_key: str) -> Dict[str, Any]:
    """Parse LLM output into repeatable objective + testScript.
    Improved for real LLM (Grok CLI etc.): strips common preamble/thinking text,
    tries JSON first (when steps template asks for it), then robust regex.
    Note construction is now handled by build_traceability_note for repeatability.
    """
    # Strip common real-LLM preamble (Grok CLI often emits "Thinking..." or project notes even with --no-plan)
    # Remove lines that look like thinking, notes, or non-content before the actual output.
    cleaned = llm_output
    # Remove leading "thinking" blocks or similar
    cleaned = re.sub(r'^(Thinking|Project|Note|Summary|I will|Let me).*?(\n\n|\Z)', '', cleaned, flags=re.IGNORECASE | re.DOTALL).strip()
    # Remove any remaining leading non-relevant paragraphs (stop at first <ul> or [ or number)
    if '<ul>' not in cleaned.lower() and not re.search(r'^\s*[\[\d]', cleaned, re.MULTILINE):
        # Keep only from the first structural marker
        marker = re.search(r'(<ul>|\[\s*\{|\d+[\.\)]|\-\s)', cleaned, re.IGNORECASE)
        if marker:
            cleaned = cleaned[marker.start():]

    # Try JSON first (for steps prompt which requests JSON array). Use the shared
    # string-aware extractor rather than a greedy `\[\s*\{.*\}\s*\]` regex, which spanned
    # across two arrays / into trailing prose and dropped all steps (adversarial-review).
    steps = []
    steps_source = "none"
    try:
        parsed = extract_json_block(cleaned)
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict) and "description" in item:
                    steps.append({
                        "description": item.get("description", "").strip(),
                        "expectedResult": item.get("expectedResult", "")
                    })
    except Exception:
        pass
    if steps:
        steps_source = "json"

    # Fallback regex for numbered steps (handles markdown too).
    #
    # THIS PATH IS A DEGRADED PARSE, so it has to announce itself. The model was asked for a
    # JSON array; a numbered list means it ignored that, and the regex recovers descriptions
    # only — any structure the reply carried beyond the description text is silently lost.
    #
    # NOT flagged because the recovered steps have a blank `expectedResult`: blank is the
    # intended shape (see `steps_report`). Flagged because an unparseable reply used to be
    # indistinguishable from a well-formed one, which is the silent-degradation pattern from
    # the 2026-07-30 audit — a parse failure must never read as a clean result.
    if not steps:
        step_lines = re.findall(r"^\s*(?:\d+[\.\)]|\-)\s*(.+)$", cleaned, re.MULTILINE)
        for line in step_lines:
            desc = line.strip()
            if desc and not desc.lower().startswith(('thinking', 'project', 'note:')):
                steps.append({"description": desc, "expectedResult": ""})
        if steps:
            steps_source = "numbered_list"

    # Objective: extract <ul>...</ul> or fall back to first paragraph as list
    objective_match = re.search(r"<ul>.*?</ul>", cleaned, re.DOTALL | re.IGNORECASE)
    if objective_match:
        objective = objective_match.group(0)
    else:
        # Fallback: try to find bullet-like lines and wrap (skip preamble)
        bullets = re.findall(r"^\s*[\-\*]\s*(.+)$", cleaned, re.MULTILINE)
        if bullets:
            # No [:10] cap — objective bullet count is not fixed (process principle);
            # capping here would truncate a valid long objective that came back as
            # markdown bullets instead of <ul>.
            objective = "<ul>\n" + "\n".join(f"<li>{b.strip()}</li>" for b in bullets) + "\n</ul>"
        else:
            objective = "<ul><li>TODO - parse failed (no structured output found)</li></ul>"

    return {
        "objective": objective,
        "testScript": {"type": "steps", "steps": steps},
        # How the steps were obtained: "json" (the format the prompt asks for),
        # "numbered_list" (the fallback — guaranteed blank expectedResults), "none".
        "steps_source": steps_source,
    }


def steps_report(steps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Describe synthesized steps. Deliberately does NOT score `expectedResult`.

    THIS FUNCTION USED TO SCORE BLANK EXPECTED RESULTS AS NON-COMPLIANT. That was wrong,
    and the reason is a design ruling that had never been written down (memory
    `expected-results-deliberately-absent`):

        A Zephyr manual step is MEANT to leave `expectedResult` empty. A human reading the
        objective plus a non-prescriptive step can reason out what should happen. Stating
        it does active harm — the tester then performs the test in whatever way produces
        exactly that stated result, instead of producing EVIDENCE OF FUNCTION.

    The objective already carries the expected outcomes; `pt_generate_script.jinja` rule 1a
    calls its bullets "the AUTHORITATIVE expected results the whole script exists to prove".
    A per-step expected result duplicates that and narrows it.

    How the old behaviour got here, since it looked well-founded: Phase −1 (`949004f`) added
    a push gate asserting "a step with no expected result is not a test"; hours later D-12
    (`f0a94af`) rewrote the prompt to satisfy that gate, justified by the gate refusing the
    corpus. Circular — and the governing plan's goal was "a test actually ran", i.e. script
    execution, so step drafting was swept in as an obstacle rather than reviewed as a Test
    Case Generator design question.

    What IS still worth reporting is parse integrity (`steps_source`, set by the caller) and
    invented device mechanisms — neither depends on `expectedResult` being filled in.

    `steps` is the FINAL list including the server-injected traceability note at index 0.
    """
    verification = [s for s in (steps or [])[1:] if isinstance(s, dict)]
    return {"verification_steps": len(verification)}


# Canonical first testScript step. Full TL/Zephyr/ART mappings live only in
# traceability.md — they do not belong in the Zephyr payload note.
MINIMAL_TRACEABILITY_NOTE = "Note: Related ART Tests linked in Traceability."
# The stable prefix of the note (the constant ends in '.', but a stored/edited step may
# not, and export appends detail after it). Single source for every "is this THE note?"
# test — the literal was previously spelled out in three places.
TRACEABILITY_NOTE_PREFIX = "Note: Related ART Tests linked in Traceability"


def _is_traceability_note(description: str) -> bool:
    """True only for the canonical server-injected first step.

    Anchored on purpose: an unanchored 'Traceability' / 'Note:' substring test matches
    legitimate verification steps ("Verify Traceability of the ART logs...") and silently
    deletes them.
    """
    return (description or "").strip().startswith(TRACEABILITY_NOTE_PREFIX)


def build_traceability_note(session: Dict[str, Any] = None) -> str:
    """Server-side first testScript step: minimal Traceability pointer only.

    Intentionally does NOT list Primary TestLink, related TL, ART IDs, Zephyr keys,
    Gaps, or URLs — that detail is in the Traceability artefact, not this step.
    Always injected as step 0 for repeatability (export + synthesize_steps).
    """
    # session accepted for API compatibility; unused by design
    return MINIMAL_TRACEABILITY_NOTE


def validate_zephyr_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validate that the generated zephyr_payload matches the repeatable shape expected
    by refined-cases/ and upload tools.

    Returns: { "valid": bool, "issues": [...], "warnings": [...] }
    This provides the validation required for priority #1 (output generation).
    Enforces:
    - Correct top-level shape
    - <ul> objective with multiple declarative <li> items
    - First step is always the server-built traceability note
    - At least one verification step after the note
    """
    issues: List[str] = []
    warnings: List[str] = []

    if not isinstance(payload, dict) or len(payload) != 1:
        issues.append("Top level must be a dict with exactly one AWPTCM-Txxxx key")
        return {"valid": False, "issues": issues, "warnings": warnings}

    case_key, content = next(iter(payload.items()))
    if not isinstance(case_key, str) or not case_key.startswith("AWPTCM-"):
        warnings.append(f"Case key '{case_key}' does not follow AWPTCM-Txxxx convention")

    if not isinstance(content, dict):
        issues.append("Case content must be an object with objective + testScript")
        return {"valid": False, "issues": issues, "warnings": warnings}

    objective = (content.get("objective") or "").strip()
    if not objective.startswith("<ul>"):
        issues.append("objective must start with <ul>")
    li_count = objective.count("<li>")
    if li_count < 3:
        issues.append(f"objective should contain at least 3 <li> items for meaningful coverage (found {li_count})")
    if "<li>" not in objective:
        issues.append("objective must contain one or more <li> items")

    ts = content.get("testScript") or {}
    steps = ts.get("steps") or []
    if not isinstance(steps, list) or len(steps) < 2:
        issues.append("testScript.steps must be a list with the traceability note + at least one verification step")
    else:
        first_desc = (steps[0] or {}).get("description", "") or ""
        if not _is_traceability_note(first_desc):
            issues.append("First test step must be the server-generated traceability note starting with 'Note: Related ART Tests linked in Traceability'")
        if "Traceability" not in first_desc:
            issues.append("First test step must reference 'Traceability'")
        # Ensure later steps are present (verification)
        non_note_steps = [s for s in steps[1:] if (s or {}).get("description")]
        if len(non_note_steps) < 1:
            issues.append("Must include at least one verification step after the traceability note")

        for idx, step in enumerate(steps):
            if not isinstance(step, dict) or "description" not in step:
                issues.append(f"Step {idx} is missing 'description' field")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
    }


def generate_coverage_gaps(session: Dict[str, Any], llm_config: Optional[Dict] = None) -> Dict[str, Any]:
    """Generate Gaps analysis for the Traceability artefact (not a Step 3 user edit).

    Called at synthesis/export time from confirmed TestLink / Zephyr / ATPyLib selections.
    Returns: {"gaps": str, "provenance": {...optional...}}
    """
    context = {
        "case_key": session.get("key"),
        "primary": session.get("primary"),
        "testlink_selections": session.get("step1", {}).get("selections", []) or [],
        "zephyr_selections": session.get("step2", {}).get("selections", []) or [],
        "atp_selections": session.get("step3", {}).get("selections", []) or [],
        "art_string": session.get("art_string", "") or "",
    }
    cfg = llm_config or {}
    provider = (cfg.get("provider") or "").lower()
    auth_method = (cfg.get("auth_method") or "local_llm").lower()
    credential = cfg.get("api_key") or cfg.get("token")
    base_url = cfg.get("base_url")
    model = cfg.get("model") or os.environ.get("LLM_MODEL", "default")

    try:
        prompt = render_prompt("generate_gaps.jinja", context)
        meta = _call_llm_with_meta(
            prompt,
            provider=provider,
            api_key=credential,
            base_url=base_url,
            model=model,
            auth_method=auth_method,
            session_id=cfg.get("session_id", ""),
            template="generate_gaps",
        )
        content = (meta.get("content") or "").strip()
        # Strip accidental fences / labels
        content = re.sub(r"^```(?:text|markdown)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
        content = re.sub(r"^(Gaps?\s*(Noted)?\s*:?\s*)", "", content, flags=re.I).strip()
        if not content or meta.get("error"):
            content = (
                "Automation coverage was reviewed against selected ATPyLib tests; "
                "explicit residual gaps could not be generated (LLM unavailable or empty response). "
                "Review selected ART IDs in Traceability against TestLink artefacts."
            )
        return {
            "gaps": content,
            "provenance": {
                "gaps_prompt": prompt,
                "gaps_response": meta.get("content", ""),
                "provider": meta.get("provider"),
                "auth_method": meta.get("auth_method"),
                "model": meta.get("model"),
                "error": meta.get("error", False),
            },
        }
    except Exception as e:
        print(f"[LLM gaps] failed: {e}")
        return {
            "gaps": (
                "Gaps analysis unavailable. Review selected ATPyLib coverage against "
                "confirmed TestLink and Zephyr artefacts when finalizing Traceability."
            ),
            "provenance": {"error": True, "message": str(e)},
        }


def _resolve_llm_runtime(llm_config: Optional[Dict] = None) -> Dict[str, Any]:
    """Resolve provider/auth/credential/model from session login or env (no MOCK)."""
    cfg = llm_config or {}
    provider = (cfg.get("provider") or "").lower()
    auth_method = (cfg.get("auth_method") or "local_llm").lower()
    credential = cfg.get("api_key") or cfg.get("token")
    base_url = cfg.get("base_url")
    model = cfg.get("model") or os.environ.get("LLM_MODEL", "default")
    return {
        "cfg": cfg,
        "provider": provider,
        "auth_method": auth_method,
        "credential": credential,
        "base_url": base_url,
        "model": model,
        "session_id": cfg.get("session_id") or "",
    }


def _synthesis_context(session: Dict[str, Any], gaps_text: str = "") -> Dict[str, Any]:
    """Shared template context from confirmed review selections + gaps."""
    return {
        "case_key": session.get("key"),
        "primary": session.get("primary"),
        "testlink_selections": session.get("step1", {}).get("selections", []) or [],
        "zephyr_selections": session.get("step2", {}).get("selections", []) or [],
        "atp_selections": session.get("step3", {}).get("selections", []) or [],
        "gaps": gaps_text or session.get("gaps") or "",
        "art_string": session.get("art_string", ""),
        # process_principles was dropped: it duplicated the header of
        # generate_objectives.jinja verbatim and no template references it now.
    }


def synthesize_objectives(session: Dict[str, Any], llm_config: Optional[Dict] = None, dry_run: bool = False) -> Dict[str, Any]:
    """Wizard Step 4: objective HTML only (single LLM call).

    Does not generate testScript steps — that is Step 5 after the user finalizes objectives.
    Does not generate Traceability gaps — those belong to the Traceability artefact and are
    generated at export time (traceability.md). Keeps the objective prompt self-contained.
    dry_run: render the objective prompt and return it without sending — provenance preview,
    no tokens (byte-identical to the real send).
    """
    rt = _resolve_llm_runtime(llm_config)
    if dry_run:
        context = _synthesis_context(session)
        objective_prompt = render_prompt("generate_objectives.jinja", context)
        return {"dry_run": True, "prompt": objective_prompt,
                "provider": rt["provider"], "model": rt["model"], "auth_method": rt["auth_method"]}
    # Traceability gaps belong to the Traceability artefact (traceability.md), which is
    # rendered at export time and generates its own gaps there. The objective prompt no
    # longer consumes gaps, so we no longer make the extra generate_coverage_gaps call here.
    context = _synthesis_context(session)

    objective_prompt = render_prompt("generate_objectives.jinja", context)
    obj_meta = _call_llm_with_meta(
        objective_prompt,
        provider=rt["provider"],
        api_key=rt["credential"],
        base_url=rt["base_url"],
        model=rt["model"],
        auth_method=rt["auth_method"],
        session_id=rt["session_id"],
        template="generate_objectives",
    )
    obj_llm = obj_meta.get("content", "")
    structured = parse_llm_to_structured(obj_llm, context.get("case_key", "unknown"))

    provenance = {
        "objective_prompt": objective_prompt,
        "objective_response": obj_llm,
        "provider": obj_meta.get("provider", "unknown"),
        "auth_method": obj_meta.get("auth_method", "local_llm"),
        "model": obj_meta.get("model", "default"),
        "error": obj_meta.get("error", False),
        "phase": "objectives",
    }

    return {
        "objective": structured["objective"],
        "provenance": provenance,
    }


def synthesize_steps(
    session: Dict[str, Any],
    llm_config: Optional[Dict] = None,
    objective: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Wizard Step 5: verification steps from finalized objective + review context.

    Prefers the provided objective (finalized Step 4), else session.step4.objective.
    Always injects the server-built first traceability note.
    dry_run: render the steps prompt from the (real) resolved context and return
    it without sending — provenance preview, no tokens.
    """
    rt = _resolve_llm_runtime(llm_config)
    # Finalized objective: explicit arg > step4.objective > empty
    step4 = session.get("step4") or {}
    obj = (objective or step4.get("objective") or "").strip()
    if not obj:
        raise ValueError(
            "No finalized objective available. Complete Step 4 (Objective Synthesis) first."
        )

    gaps_text = (session.get("gaps") or "").strip()
    # Working copy so note builder sees objective-related art/gaps
    session = {**session, "gaps": gaps_text}
    # Keep step4.objective in sync for note/export helpers that read it
    session = {
        **session,
        "step4": {**(step4 if isinstance(step4, dict) else {}), "objective": obj},
    }
    context = _synthesis_context(session, gaps_text)
    context["objective"] = obj

    steps_prompt = render_prompt("generate_steps.jinja", context)
    if dry_run:
        return {"dry_run": True, "prompt": steps_prompt,
                "provider": rt["provider"], "model": rt["model"], "auth_method": rt["auth_method"]}
    steps_meta = _call_llm_with_meta(
        steps_prompt,
        provider=rt["provider"],
        api_key=rt["credential"],
        base_url=rt["base_url"],
        model=rt["model"],
        auth_method=rt["auth_method"],
        session_id=rt["session_id"],
        template="generate_steps",
    )
    steps_llm = steps_meta.get("content", "")
    steps_struct = parse_llm_to_structured(steps_llm, context.get("case_key", "unknown"))

    note_desc = build_traceability_note(session)
    note_step = {"description": note_desc, "expectedResult": ""}
    llm_steps = steps_struct.get("testScript", {}).get("steps", []) or []
    # Drop a note the model echoed back despite being told not to generate one — but
    # ONLY when it really is that note. This used to be an unanchored substring test
    # ("Note:" in ... or "Traceability" in ...), and "Traceability" is domain vocabulary
    # the prompt itself uses, so a legitimate first step like "Verify Traceability of the
    # ART logs to the test report" or "Note: ensure the DUT is powered first" was silently
    # DELETED (dropped before note_step is prepended, so lost outright). Nothing catches
    # it: validate_zephyr_payload only needs >=2 steps and >=1 non-note step, so the case
    # exports to Zephyr a step short with no warning. Anchor on the canonical note, the
    # way the validator already does (validate_zephyr_payload, :717).
    if llm_steps and _is_traceability_note(llm_steps[0].get("description", "")):
        llm_steps = llm_steps[1:]

    # A ZEPHYR MANUAL STEP CARRIES NO EXPECTED RESULT. Terrence's design ruling, recorded in
    # memory `expected-results-deliberately-absent`: a tester reading the objective plus a
    # non-prescriptive step reasons out what should happen, and STATING it does active harm —
    # they then perform the test in whatever way produces exactly that result, instead of
    # producing evidence of function. The objective already carries the expected outcomes.
    #
    # Enforced HERE rather than only asked for in the prompt, because a prompt rule is a
    # request and this is a requirement: D-12 showed how easily the field creeps back once
    # something downstream starts wanting it. The key is kept (the Zephyr payload schema is
    # {description, expectedResult}) and always empty.
    llm_steps = [{**s, "expectedResult": ""} for s in llm_steps]
    final_steps = [note_step] + llm_steps

    # Describe what came back. Nothing here scores `expectedResult` — a blank one is the
    # DESIGN (see steps_report), so grading it would be grading the intended outcome.
    # `steps_source` is parse integrity only: "numbered_list" means the model ignored the
    # requested JSON and the regex fallback ran, so structure was lost in parsing. An
    # unparseable reply must never read as a well-formed one.
    quality = {**steps_report(final_steps),
               "steps_source": steps_struct.get("steps_source", "none")}

    provenance = {
        "steps_prompt": steps_prompt,
        "steps_response": steps_llm,
        "objective_used": obj,
        "provider": steps_meta.get("provider", "unknown"),
        "auth_method": steps_meta.get("auth_method", "local_llm"),
        "model": steps_meta.get("model", "default"),
        "error": steps_meta.get("error", False),
        "phase": "steps",
        # Persisted with the session (step5.provenance / full_session.llm_steps), so a
        # batch regeneration can be audited per case without re-reading every payload.
        "steps_quality": quality,
    }

    core = {
        "objective": obj,
        "testScript": {"type": "steps", "steps": final_steps},
        "provenance": provenance,
        "steps_quality": quality,
    }
    validation = validate_zephyr_payload({session.get("key", "unknown"): {
        "objective": obj,
        "testScript": core["testScript"],
    }})
    return {**core, "validation": validation}


def synthesize_objectives_and_steps(session: Dict[str, Any], llm_config: Optional[Dict] = None) -> Dict[str, Any]:
    """Legacy combined path: Step 4 then Step 5 in one call (kept for compatibility).

    Prefer synthesize_objectives + synthesize_steps for the split wizard UX.
    """
    obj_out = synthesize_objectives(session, llm_config=llm_config)
    session_with_obj = {
        **session,
        "gaps": obj_out.get("gaps") or session.get("gaps") or "",
        "step4": {
            **(session.get("step4") or {}),
            "objective": obj_out.get("objective"),
            "provenance": obj_out.get("provenance"),
        },
    }
    steps_out = synthesize_steps(
        session_with_obj,
        llm_config=llm_config,
        objective=obj_out.get("objective"),
    )
    # Merge provenance for audit
    provenance = {
        **(obj_out.get("provenance") or {}),
        **(steps_out.get("provenance") or {}),
        "phase": "combined",
    }
    core = {
        "objective": obj_out.get("objective"),
        "testScript": steps_out.get("testScript"),
        "gaps": obj_out.get("gaps") or "",
        "provenance": provenance,
        # Same signal as the split path, so the legacy combined call is not the one
        # place a non-compliant generation stays invisible.
        "steps_quality": steps_out.get("steps_quality"),
    }
    validation = steps_out.get("validation") or validate_zephyr_payload(
        {session.get("key", "unknown"): core}
    )
    return {**core, "validation": validation}


def _parse_suggest_id_list(content: str, id_patterns: Optional[List[str]] = None) -> List[Dict[str, str]]:
    """Parse LLM JSON array of {id, reason}; optional regex fallbacks for bare IDs."""
    suggestions: List[Dict[str, str]] = []
    try:
        parsed = extract_json_block(content or "")   # shared string-aware extractor
        # The suggest prompt asks for a JSON array; if the model wrapped it in an object
        # (e.g. {"suggestions": [...]}), accept the first list value inside.
        if isinstance(parsed, dict):
            parsed = next((v for v in parsed.values() if isinstance(v, list)), None)
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict) and item.get("id"):
                    suggestions.append({
                        "id": str(item.get("id", "")).strip(),
                        "reason": item.get("reason", "LLM selected as relevant"),
                    })
    except Exception as e:
        print(f"[LLM suggest] JSON parse failed: {e}")

    if not suggestions and id_patterns:
        for pat in id_patterns:
            for m in re.findall(pat, content or ""):
                iid = m if isinstance(m, str) else (m[0] if m else "")
                if iid:
                    suggestions.append({"id": iid, "reason": "Mentioned by LLM"})

    seen = set()
    final = []
    for s in suggestions:
        if s["id"] and s["id"] not in seen:
            seen.add(s["id"])
            final.append(s)
            if len(final) >= 8:
                break
    return final


def suggest_relevant_atp(session: Dict[str, Any], candidates: List[Dict[str, Any]], llm_config: Optional[Dict] = None, dry_run: bool = False):
    """Use LLM to pre-select the most relevant ATPyLib tests from a list of candidates.

    Returns list of {"id": "...", "reason": "..."}
    Uses same provider/config as other LLM calls.

    dry_run: return {"dry_run": True, "prompt": <rendered>} instead of sending —
    a provenance preview of the exact prompt that would be transmitted.
    """
    if not candidates:
        return {"dry_run": True, "prompt": "", "note": "no candidates"} if dry_run else []

    # Omit non-functional tests
    candidates = [c for c in candidates if "(not a functional test)" not in ((c.get("description") or "") + c.get("id", "")).lower() ]

    cfg = llm_config or {}
    provider = (cfg.get("provider") or "").lower()
    auth_method = (cfg.get("auth_method") or "local_llm").lower()
    credential = cfg.get("api_key") or cfg.get("token")

    context = {
        "case_key": session.get("key"),
        "primary": session.get("primary"),
        "testlink_selections": session.get("step1", {}).get("selections", []),
        "zephyr_selections": session.get("step2", {}).get("selections", []),
        "gaps": session.get("gaps", ""),
        "candidates": candidates,
    }

    base_url = cfg.get("base_url")
    model = cfg.get("model") or os.environ.get("LLM_MODEL", "default")

    prompt = render_prompt("suggest_atp.jinja", context)
    meta = _call_llm_with_meta(prompt, provider=provider, api_key=credential, base_url=base_url, model=model, auth_method=auth_method, session_id=cfg.get("session_id", ""), template="suggest_atp", dry_run=dry_run)
    if dry_run:
        return {"dry_run": True, "prompt": meta.get("prompt", prompt), "provider": provider, "model": model, "auth_method": auth_method}
    content = meta.get("content", "")
    return _parse_suggest_id_list(content, id_patterns=[r'(\d+\.\d+(?:\.\d+)?)'])


def suggest_relevant_testlink(
    session: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    llm_config: Optional[Dict] = None,
    case_title: str = "",
    dry_run: bool = False,
):
    """LLM pre-select TestLink cases. Returns [{"id","reason"}, ...].

    dry_run: return {"dry_run": True, "prompt": <rendered>} without sending.
    """
    if not candidates:
        return {"dry_run": True, "prompt": "", "note": "no candidates"} if dry_run else []
    cfg = llm_config or {}
    provider = (cfg.get("provider") or "").lower()
    auth_method = (cfg.get("auth_method") or "local_llm").lower()
    credential = cfg.get("api_key") or cfg.get("token")
    context = {
        "case_key": session.get("key"),
        "primary": session.get("primary"),
        "case_title": case_title or "",
        "candidates": candidates,
    }
    model = cfg.get("model") or os.environ.get("LLM_MODEL", "default")
    prompt = render_prompt("suggest_testlink.jinja", context)
    meta = _call_llm_with_meta(
        prompt,
        provider=provider,
        api_key=credential,
        base_url=cfg.get("base_url"),
        model=model,
        auth_method=auth_method,
        session_id=cfg.get("session_id", ""),
        template="suggest_testlink",
        dry_run=dry_run,
    )
    if dry_run:
        return {"dry_run": True, "prompt": meta.get("prompt", prompt), "provider": provider, "model": model, "auth_method": auth_method}
    return _parse_suggest_id_list(meta.get("content", ""), id_patterns=[r'(AWP-\d+)'])


def suggest_relevant_zephyr(
    session: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    llm_config: Optional[Dict] = None,
    case_title: str = "",
    dry_run: bool = False,
):
    """LLM pre-select external Zephyr cases. Returns [{"id","reason"}, ...] (id = key).

    dry_run: return {"dry_run": True, "prompt": <rendered>} without sending.
    """
    if not candidates:
        return {"dry_run": True, "prompt": "", "note": "no candidates"} if dry_run else []
    cfg = llm_config or {}
    provider = (cfg.get("provider") or "").lower()
    auth_method = (cfg.get("auth_method") or "local_llm").lower()
    credential = cfg.get("api_key") or cfg.get("token")
    context = {
        "case_key": session.get("key"),
        "primary": session.get("primary"),
        "case_title": case_title or "",
        "testlink_selections": session.get("step1", {}).get("selections", []) or [],
        "candidates": candidates,
    }
    model = cfg.get("model") or os.environ.get("LLM_MODEL", "default")
    prompt = render_prompt("suggest_zephyr.jinja", context)
    meta = _call_llm_with_meta(
        prompt,
        provider=provider,
        api_key=credential,
        session_id=cfg.get("session_id", ""),
        base_url=cfg.get("base_url"),
        model=model,
        auth_method=auth_method,
        template="suggest_zephyr",
        dry_run=dry_run,
    )
    if dry_run:
        return {"dry_run": True, "prompt": meta.get("prompt", prompt), "provider": provider, "model": model, "auth_method": auth_method}
    return _parse_suggest_id_list(meta.get("content", ""), id_patterns=[r'(AWPTCM-T\d+)'])


def analyze_atp_coverage(session: Dict[str, Any], candidates: List[Dict[str, Any]], llm_config: Optional[Dict] = None, dry_run: bool = False) -> Dict[str, Any]:
    """Score/rank ATP candidates for Step 3 review (no gaps text — gaps are synthesis/export only).

    Returns: {"ranked": [{"id": "...", "score": 0.91, "reason": "..."}, ...]}
    dry_run: return {"dry_run": True, "prompt": <rendered>} without sending.
    """
    if not candidates:
        return {"dry_run": True, "prompt": "", "note": "no candidates"} if dry_run else {"ranked": []}

    cfg = llm_config or {}
    provider = (cfg.get("provider") or "").lower()
    auth_method = (cfg.get("auth_method") or "local_llm").lower()
    credential = cfg.get("api_key") or cfg.get("token")
    headless = (provider == "claude" and auth_method == "claude_code") or (provider == "grok" and auth_method == "grok_cli")

    # Real LLM path only. Falls through to keyword fallback on error.
    # Real LLM path
    context = {
        "case_key": session.get("key"),
        "primary": session.get("primary"),
        "testlink_selections": session.get("step1", {}).get("selections", []),
        "zephyr_selections": session.get("step2", {}).get("selections", []),
        "candidates": [
            {
                "id": c.get("id"),
                "description": c.get("description", c.get("title", ""))[:180],
                "suite": c.get("suite", "")
            }
            for c in candidates[:20]
        ]
    }

    _model = cfg.get("model") or os.environ.get("LLM_MODEL", "default")
    if dry_run:
        prompt = render_prompt("analyze_atp_coverage.jinja", context)
        return {"dry_run": True, "prompt": prompt, "provider": provider, "model": _model, "auth_method": auth_method}
    try:
        prompt = render_prompt("analyze_atp_coverage.jinja", context)
        meta = _call_llm_with_meta(
            prompt,
            provider=provider,
            api_key=credential,
            base_url=cfg.get("base_url"),
            model=_model,
            auth_method=auth_method,
            session_id=cfg.get("session_id", ""),
            template="analyze_atp_coverage",
        )
        content = meta.get("content", "")

        # Parse the JSON response via the shared string-aware extractor (a greedy
        # `\{.*\}` regex latched onto a prose brace before the real object and dropped
        # the whole ranking — adversarial-review finding).
        parsed = extract_json_block(content)
        if isinstance(parsed, dict):
            # No backend truncation: the prompt now asks for every genuinely
            # relevant candidate, ranked. The scrollable table shows them in order
            # (a UI "show more" can page through) — capping here would silently
            # drop the LLM's ranking/reasoning for lower-ranked-but-relevant hits.
            ranked = parsed.get("ranked", [])
            # Normalize scores to float 0-1
            for item in ranked:
                if "score" in item:
                    try:
                        item["score"] = float(item["score"])
                    except Exception:
                        item["score"] = 0.5
            return {"ranked": ranked}
    except Exception as e:
        print(f"[LLM ATP analyze] failed: {e}")

    # Fallback (LLM unavailable): return the keyword candidates as-is. They arrive
    # already relevance-ranked from db.search_atp_hybrid (bounded by its own limit),
    # so no extra cap here — the scrollable table shows them in score order.
    return {
        "ranked": [{"id": c.get("id"), "score": 0.7, "reason": "Selected via fallback keyword matching"} for c in candidates],
    }



# Every PyTest Creator / enrichment template ends with "Output JSON ONLY".
# A system message that says the same thing up front steers the reasoning
# models to skip the prose/scratchpad and emit the JSON directly — measured
# ~22x fewer completion tokens on a trivial ask, and it is the message shape
# the org vLLM docs (resources.md) demonstrate. Callers can override per-call.
_JSON_SYSTEM_PROMPT = (
    "You are a precise API that returns machine-readable output only. "
    "Respond with exactly the JSON the user's instructions specify — no prose, "
    "no explanation, no markdown fences, and no step-by-step thinking before it."
)

# NOT every template asks for JSON — pt_generate_script.jinja and pt_fix_script.jinja ask
# for a FENCED PYTHON BLOCK, and _parse_generated_blocks requires the fence to find the
# code at all (no unfenced fallback: without it `test_code` is None and the router answers
# 502 "LLM returned no python code block"). Those two steps were nevertheless getting
# _JSON_SYSTEM_PROMPT, whose text forbids the very fences the parser needs — two
# authorities in the same request telling the model opposite things, on every backend.
#
# Separately, a headless coding CLI's instinct on a large artefact is to WRITE IT TO DISK
# rather than emit it: measured 2026-07-30, Opus answered a 53-TestCase generate with
# "Continuing by writing the artifact to disk in pieces rather than one oversized message"
# plus a narrated Write call. Hence the explicit no-tools/no-chunking clauses — they are
# load-bearing for the CLI transport, harmless on the HTTP ones.
_CODE_SYSTEM_PROMPT = (
    "You are a code generator. Return the COMPLETE artefact inline, as a single fenced "
    "```python block, and nothing else — no prose before or after it, no plan, no summary. "
    "You have NO tools and NO filesystem: never write, save or 'continue in pieces', and "
    "never describe doing so. If the artefact is long, emit all of it anyway in that one "
    "block; a truncated or narrated answer is useless to the caller."
)


def run_prompt(template_name: str, context: Dict[str, Any], llm_config: Optional[Dict] = None,
               timeout: int = 180, dry_run: bool = False,
               system: Optional[str] = None, max_tokens: Optional[int] = None) -> Dict[str, Any]:
    """Generic templated LLM call (used by the PyTest Creator + index enrichment).

    Renders templates/prompts/<template_name> with `context`, resolves the
    provider/auth from the session or env like every wizard call, and returns
    the raw meta dict from _call_llm_with_meta (content, provider, error, ...).
    Long generation prompts may pass a larger timeout than the 180s default.

    system: system message. Defaults to a JSON-only steer (see
    _JSON_SYSTEM_PROMPT) since every current template asks for JSON; pass a
    different string to override, or "" to send none.

    max_tokens: override the completion cap (default 16000 for local_llm /
    2000 otherwise — see _call_llm_raw). Pass a larger value for callers whose
    expected output is unusually large (e.g. pt_generate_script.jinja, which
    emits a whole standardized script and can exceed the default cap).

    dry_run: render the prompt and return it WITHOUT sending (provenance
    preview). The template + context are exactly those a real call uses, so the
    previewed prompt is 1-for-1 with what would be transmitted.
    """
    rt = _resolve_llm_runtime(llm_config)
    prompt = render_prompt(template_name, context)
    meta = _call_llm_with_meta(
        prompt,
        provider=rt["provider"],
        api_key=rt["credential"],
        base_url=rt["base_url"],
        model=rt["model"],
        auth_method=rt["auth_method"],
        timeout=timeout,
        session_id=rt["session_id"],
        template=template_name,
        dry_run=dry_run,
        system=_JSON_SYSTEM_PROMPT if system is None else system,
        max_tokens=max_tokens,
    )
    return meta


def run_prompt_text(prompt: str, llm_config: Optional[Dict] = None,
                    timeout: int = 180, dry_run: bool = False,
                    system: Optional[str] = None, max_tokens: Optional[int] = None,
                    template: str = "(verbatim)") -> Dict[str, Any]:
    """Send an ALREADY-RENDERED prompt, bypassing the template step.

    Same runtime resolution, same `_call_llm_with_meta` choke point, so the call is
    resolved, timed, token-counted and debug-logged exactly like a templated one — this is
    not a side door around the instrumentation, only around Jinja.

    Why it exists (2026-09-02): per-unit generation shows the reviewer the prompt for each
    unit in an EDITABLE frame, and the button sends what is on screen. Re-rendering from a
    template at dispatch would silently discard their edit, which defeats the point of
    showing it. `template` is recorded in the debug log as the provenance of a prompt that
    did not come from a template file.
    """
    rt = _resolve_llm_runtime(llm_config)
    return _call_llm_with_meta(
        prompt,
        provider=rt["provider"],
        api_key=rt["credential"],
        base_url=rt["base_url"],
        model=rt["model"],
        auth_method=rt["auth_method"],
        timeout=timeout,
        session_id=rt["session_id"],
        template=template,
        dry_run=dry_run,
        system=_JSON_SYSTEM_PROMPT if system is None else system,
        max_tokens=max_tokens,
    )


def _health_ping(llm_config: Optional[Dict] = None) -> Dict[str, Any]:
    """Minimal completion to confirm the configured LLM is reachable and answering.

    Uses the same runtime resolution + _call_llm_with_meta choke point as every
    real call (so it validates config/credential/transport end-to-end and is
    recorded in debug-log), with a tiny prompt and short timeout. Returns the raw
    meta dict; the caller decides ok/not-ok from meta["error"].
    """
    rt = _resolve_llm_runtime(llm_config)
    return _call_llm_with_meta(
        "Reply with the single word: OK",
        provider=rt["provider"],
        api_key=rt["credential"],
        base_url=rt["base_url"],
        model=rt["model"],
        auth_method=rt["auth_method"],
        timeout=30,
        session_id=rt["session_id"],
        template="health_ping",
    )


def _scan_balanced_json(content: str, opener: str, closer: str, start: int) -> Optional[Any]:
    """Scan from `start` for a balanced opener..closer run, IGNORING opener/closer
    characters that appear inside a JSON string literal (and honoring backslash escapes).
    Returns the parsed value, or None if nothing balanced/valid is found from `start`.

    This is the correctness fix for the old depth counter, which counted braces/brackets
    inside string values — so valid JSON like {"x": "a } b"} closed early and failed.
    """
    depth = 0
    in_str = False
    escaped = False
    for i in range(start, len(content)):
        ch = content[i]
        if in_str:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(content[start:i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def extract_json_block(content: str) -> Any:
    """Best-effort extraction of the first JSON object/array from LLM output.

    Robust against: ```json fences (tries EACH fenced block, not just the first, since an
    LLM may emit an illustrative non-JSON fence before the real one); leading/trailing prose;
    and braces/brackets INSIDE string values (string-aware balanced scan). Returns None when
    nothing parses. This is the single shared extractor — all JSON-bearing LLM parsers route
    through it rather than ad-hoc greedy regexes (adversarial-review finding cluster).
    """
    if not content:
        return None
    # 1) Try every fenced block in order; accept the first that actually parses as JSON.
    for m in re.finditer(r"```(?:json)?\s*(.+?)```", content, re.DOTALL):
        body = m.group(1).strip()
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            # Fenced block wasn't pure JSON (e.g. a pseudocode example) — try to extract a
            # balanced structure from within it before moving on.
            got = _extract_first_balanced(body)
            if got is not None:
                return got
    # 2) No usable fence — scan the whole content for the OUTERMOST structure, choosing
    #    whichever bracket type opens first (an object with a nested array must not return
    #    the inner array).
    return _extract_first_balanced(content)


def _extract_first_balanced(content: str) -> Any:
    """Return the first balanced {..} or [..] that parses as JSON, scanning by POSITION
    left-to-right across BOTH bracket types. Walking every opener of one type before the
    other could return a nested object (inside a later array) instead of that array; by
    position order the outer structure — whose opener comes first — is tried first.
    A string-aware scan is used so brackets inside string values don't mislead."""
    openers = {"{": "}", "[": "]"}
    # Collect every opener position (both types), skipping ones inside string literals.
    positions = []
    in_str = escaped = False
    for i, ch in enumerate(content):
        if in_str:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in openers:
            positions.append(i)
    for pos in positions:
        opener = content[pos]
        got = _scan_balanced_json(content, opener, openers[opener], pos)
        if got is not None:
            return got
    return None
