"""
LLM integration for server-backed drafting tool.

Uses prompt templating for repeatable inputs (Jinja templates inject selections + process principles).
Post-processes LLM responses with parsers for repeatable outputs (Objectives as <ul> + steps).

Real LLM support:
- Per-session login (set via /set_llm_config):
  - "api_key": direct keys
  - "claude_code": local Claude Code CLI (Team subscription)
  - "grok_cli": local Grok CLI (SuperGrok / X Premium+ subscription via OAuth at x.ai)
- No separate API key needed for the CLI modes; auth lives with the locally logged-in CLI.
- Set LLM_API_KEY / LLM_BASE_URL env as fallback (OpenAI-compatible for Grok etc., Anthropic native for Claude)
- Better error handling + logging of exact prompts/responses (for full provenance per SERVER-README.md)
- Capture of prompts + raw responses returned to caller for storage in session.

Parsing improved for robustness (regex + JSON fallback).
Real LLM only (no MOCK/demo fallbacks). Requires valid credentials or configured subscription CLI login (grok_cli / claude_code).
"""

import os
import json
import re
import shutil
import subprocess
import contextvars
import time
from jinja2 import Environment, FileSystemLoader
from typing import Dict, Any, List, Optional
import requests  # fallback, or use openai litellm for more providers later

import llm_debug
from local_llm_key import get_local_llm_key

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

        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
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


def _call_claude_code_headless(prompt: str, model: str, meta: Dict[str, Any], timeout: int = 180) -> Dict[str, Any]:
    """Call the locally logged-in Claude Code CLI in headless print mode.

    Auth model: each user hosts this tool locally and has logged the CLI in with
    their own Claude Team seat ('claude' -> /login). The server passes the fully
    templated prompt on stdin ('claude -p --output-format json') and parses the
    JSON wrapper. No API key or token is stored server-side; provenance records
    auth_method="claude_code" so exports are honest about the transport.
    """
    cli = shutil.which("claude")
    if not cli:
        err_msg = ("ERROR: LLM call failed (claude via claude_code): Claude Code CLI not found on PATH. "
                   "Install Claude Code and log in ('claude' then /login) with your Team account.")
        print(err_msg)
        meta.update({"content": err_msg, "raw_response": {"error": "claude CLI not on PATH"}, "error": True})
        return meta

    cmd = [cli, "-p", "--output-format", "json"]
    if model and model != "default":
        cmd += ["--model", model]

    try:
        # Prompt via stdin: templated prompts can exceed argv limits.
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=timeout)
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()[:500] or f"exit code {proc.returncode}"
            raise RuntimeError(detail)

        raw = proc.stdout.strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = None

        if isinstance(data, dict) and data.get("result") is not None:
            content = data["result"]
            if data.get("is_error"):
                raise RuntimeError(str(content)[:500])
        else:
            # Fallback: treat plain stdout as the response text
            content = raw
            data = {"stdout": raw}

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


def _call_claude_agent(prompt: str, model: str, meta: Dict[str, Any], session_id: str, timeout: int) -> Dict[str, Any]:
    """Route a Claude call to the USER's own machine via the browser-brokered agent.

    The server does not run `claude`; it enqueues the prompt for `session_id` and
    blocks until that user's browser (which talks to their local ck-agent) posts the
    completion back. This is what makes a shared server use each user's own seat.
    See ask-ck/CK-main/PLAN-per-user-agent.md.
    """
    from agent_jobs import registry  # local import avoids a hard dep at module load
    session_id = session_id or current_session_id.get("")
    if not session_id:
        meta.update({"content": ("ERROR: Claude-agent mode needs a browser session id but none was "
                                 "provided. Reload the Ask CK page."), "error": True})
        return meta
    result = registry.submit(session_id, prompt, model, timeout)
    meta.update({"content": result.get("content", ""), "raw_response": result,
                 "error": bool(result.get("error")), "provider": "claude"})
    return meta


def _call_llm_with_meta(prompt: str, provider: str = "", api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "default", auth_method: str = "api_key", timeout: int = 180, session_id: str = "", template: str = "", dry_run: bool = False, system: str = "", max_tokens: Optional[int] = None) -> Dict[str, Any]:
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
    start = time.monotonic()
    meta = _call_llm_raw(prompt, provider=provider, api_key=api_key, base_url=base_url,
                         model=model, auth_method=auth_method, timeout=timeout,
                         session_id=session_id, system=system, max_tokens=max_tokens)
    duration_ms = int((time.monotonic() - start) * 1000)
    meta["template"] = template
    meta["usage"] = llm_debug.normalize_usage(meta.get("auth_method", auth_method),
                                              meta.get("raw_response"))
    llm_debug.record(meta, duration_ms)
    return meta


def _call_llm_raw(prompt: str, provider: str = "", api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "default", auth_method: str = "api_key", timeout: int = 180, session_id: str = "", system: str = "", max_tokens: Optional[int] = None) -> Dict[str, Any]:
    """Core LLM caller with multi-provider support. Real use only - no MOCK or demo fallbacks.

    Supports multiple login styles (chosen in the UI):
    - "api_key": classic developer API key (HTTP calls).
    - "claude_agent": browser-brokered local Claude Code CLI on the USER's machine
      (shared-server safe — each user spends their own seat; needs session_id).
    - "claude_code": headless Claude Code CLI on the SERVER host (single-user hosting only).
    - "grok_cli": headless Grok CLI (SuperGrok / X Premium+ subscription via OAuth).
      No key/token stored by server; auth lives in the local CLI's login.
    - "local_llm": the organization's self-hosted vLLM endpoint (OpenAI-compatible).
      Key is server-resolved (Configure page -> secrets.local.json, env fallback);
      never supplied by the browser. Model = vllm-fast | vllm-thinking.

    provider: "grok" | "claude" | "openai" (no "mock")
    If no valid credential and not using a supported headless CLI auth_method, the call will error.
    """
    provider = (provider or "").lower()
    auth_method = (auth_method or "api_key").lower()

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
        return _call_claude_agent(prompt, model, meta, session_id=session_id, timeout=timeout)
    if provider == "claude" and auth_method == "claude_code":
        return _call_claude_code_headless(prompt, model, meta, timeout=timeout)
    if provider == "grok" and auth_method == "grok_cli":
        return _call_grok_cli_headless(prompt, model, meta, timeout=timeout)

    credential = api_key
    if not credential:
        if auth_method == "local_llm":
            err_msg = ("ERROR: LLM call failed (local_llm): no Local LLM key is stored on the server. "
                       "Enter your key on the LLM Configure page (or export LOCAL_LLM_KEY) and retry.")
        else:
            err_msg = f"ERROR: LLM call failed ({provider} via {auth_method}): No credential provided and not using headless CLI mode. Set LLM_API_KEY or use grok_cli / claude_code auth_method with local login."
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
            with requests.post(endpoint, headers=headers, json=payload,
                               timeout=http_timeout, stream=True) as resp:
                resp.raise_for_status()
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
                        if delta.get("reasoning_content"):
                            reasoning_parts.append(delta["reasoning_content"])
                        if ch.get("finish_reason"):
                            finish = ch["finish_reason"]
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

    # Fallback regex for numbered steps (handles markdown too)
    if not steps:
        step_lines = re.findall(r"^\s*(?:\d+[\.\)]|\-)\s*(.+)$", cleaned, re.MULTILINE)
        for line in step_lines:
            desc = line.strip()
            if desc and not desc.lower().startswith(('thinking', 'project', 'note:')):
                steps.append({"description": desc, "expectedResult": ""})

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
        "testScript": {"type": "steps", "steps": steps}
    }


# Canonical first testScript step. Full TL/Zephyr/ART mappings live only in
# traceability.md — they do not belong in the Zephyr payload note.
MINIMAL_TRACEABILITY_NOTE = "Note: Related ART Tests linked in Traceability."


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
        if not first_desc.strip().startswith("Note: Related ART Tests linked in Traceability"):
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
    auth_method = (cfg.get("auth_method") or "api_key").lower()
    credential = cfg.get("api_key") or cfg.get("token") or os.environ.get("LLM_API_KEY")
    base_url = cfg.get("base_url") or os.environ.get("LLM_BASE_URL")
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
    auth_method = (cfg.get("auth_method") or "api_key").lower()
    credential = cfg.get("api_key") or cfg.get("token") or os.environ.get("LLM_API_KEY")
    base_url = cfg.get("base_url") or os.environ.get("LLM_BASE_URL")
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
        "auth_method": obj_meta.get("auth_method", "api_key"),
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
    if llm_steps and (
        "Note:" in llm_steps[0].get("description", "")
        or "Traceability" in llm_steps[0].get("description", "")
    ):
        llm_steps = llm_steps[1:]
    final_steps = [note_step] + llm_steps

    provenance = {
        "steps_prompt": steps_prompt,
        "steps_response": steps_llm,
        "objective_used": obj,
        "provider": steps_meta.get("provider", "unknown"),
        "auth_method": steps_meta.get("auth_method", "api_key"),
        "model": steps_meta.get("model", "default"),
        "error": steps_meta.get("error", False),
        "phase": "steps",
    }

    core = {
        "objective": obj,
        "testScript": {"type": "steps", "steps": final_steps},
        "provenance": provenance,
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
    auth_method = (cfg.get("auth_method") or "api_key").lower()
    credential = cfg.get("api_key") or cfg.get("token") or os.environ.get("LLM_API_KEY")

    context = {
        "case_key": session.get("key"),
        "primary": session.get("primary"),
        "testlink_selections": session.get("step1", {}).get("selections", []),
        "zephyr_selections": session.get("step2", {}).get("selections", []),
        "gaps": session.get("gaps", ""),
        "candidates": candidates,
    }

    base_url = cfg.get("base_url") or os.environ.get("LLM_BASE_URL")
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
    auth_method = (cfg.get("auth_method") or "api_key").lower()
    credential = cfg.get("api_key") or cfg.get("token") or os.environ.get("LLM_API_KEY")
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
        base_url=cfg.get("base_url") or os.environ.get("LLM_BASE_URL"),
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
    auth_method = (cfg.get("auth_method") or "api_key").lower()
    credential = cfg.get("api_key") or cfg.get("token") or os.environ.get("LLM_API_KEY")
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
        base_url=cfg.get("base_url") or os.environ.get("LLM_BASE_URL"),
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
    auth_method = (cfg.get("auth_method") or "api_key").lower()
    credential = cfg.get("api_key") or cfg.get("token") or os.environ.get("LLM_API_KEY")
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
            base_url=cfg.get("base_url") or os.environ.get("LLM_BASE_URL"),
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
