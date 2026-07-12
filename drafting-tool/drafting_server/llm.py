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
from jinja2 import Environment, FileSystemLoader
from typing import Dict, Any, List, Optional
import requests  # fallback, or use openai litellm for more providers later

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPTS_DIR = os.path.join(BASE_DIR, "templates", "prompts")

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


def _call_grok_cli_headless(prompt: str, model: str, meta: Dict[str, Any]) -> Dict[str, Any]:
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

        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
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
        err_msg = "ERROR: LLM call failed (grok via grok_cli): CLI call timed out after 180s"
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


def _call_claude_code_headless(prompt: str, model: str, meta: Dict[str, Any]) -> Dict[str, Any]:
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
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=180)
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
        err_msg = "ERROR: LLM call failed (claude via claude_code): CLI call timed out after 180s"
        print(err_msg)
        meta.update({"content": err_msg, "raw_response": {"error": "timeout"}, "error": True})
        return meta
    except Exception as e:
        err_msg = f"ERROR: LLM call failed (claude via claude_code): {str(e)}"
        print(err_msg)
        meta.update({"content": err_msg, "raw_response": {"error": str(e)}, "error": True})
        return meta


def _call_llm_with_meta(prompt: str, provider: str = "", api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "default", auth_method: str = "api_key") -> Dict[str, Any]:
    """Core LLM caller with multi-provider support. Real use only - no MOCK or demo fallbacks.

    Supports multiple login styles (chosen in the UI):
    - "api_key": classic developer API key (HTTP calls).
    - "claude_code": headless Claude Code CLI (Claude Team subscription).
    - "grok_cli": headless Grok CLI (SuperGrok / X Premium+ subscription via OAuth).
      No key/token stored by server; auth lives in the local CLI's login.

    provider: "grok" | "claude" | "openai" (no "mock")
    If no valid credential and not using a supported headless CLI auth_method, the call will error.
    """
    provider = (provider or "").lower()
    auth_method = (auth_method or "api_key").lower()

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
    if provider == "claude" and auth_method == "claude_code":
        return _call_claude_code_headless(prompt, model, meta)
    if provider == "grok" and auth_method == "grok_cli":
        return _call_grok_cli_headless(prompt, model, meta)

    credential = api_key
    if not credential:
        err_msg = f"ERROR: LLM call failed ({provider} via {auth_method}): No credential provided and not using headless CLI mode. Set LLM_API_KEY or use grok_cli / claude_code auth_method with local login."
        print(err_msg)
        meta.update({
            "content": err_msg,
            "raw_response": {"error": "no credential"},
            "error": True,
        })
        return meta

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
                "max_tokens": 2000,
                "temperature": 0.2,
                "messages": [{"role": "user", "content": prompt}],
            }
            resp = requests.post(f"{base_url}/messages", headers=headers, json=payload, timeout=120)
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

            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 2000,
            }
            endpoint = f"{base_url}/chat/completions"
            resp = requests.post(endpoint, headers=headers, json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]

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
        print(err_msg)
        meta.update({
            "content": err_msg,
            "raw_response": {"error": str(e)},
            "error": True,
        })
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

    # Try JSON first (for steps prompt which requests JSON array)
    steps = []
    try:
        # Look for a JSON array in the output
        json_match = re.search(r'\[\s*\{.*\}\s*\]', cleaned, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group(0))
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
            objective = "<ul>\n" + "\n".join(f"<li>{b.strip()}</li>" for b in bullets[:10]) + "\n</ul>"
        else:
            objective = "<ul><li>TODO - parse failed (no structured output found)</li></ul>"

    return {
        "objective": objective,
        "testScript": {"type": "steps", "steps": steps}
    }


def build_traceability_note(session: Dict[str, Any]) -> str:
    """Server-side construction of the repeatable first traceability note step.
    Guarantees consistent first step per OBJECTIVE_DRAFTING_PROCESS (minimal note + links).
    Matches shapes seen in refined-cases/*/zephyr_payload.json.
    Produces a concise note that starts with the required "Note: Related ART Tests..." and
    incorporates Primary + reviewed items for full traceability.
    This is always injected as step 0 and overrides any LLM-generated note for repeatability.
    """
    key = session.get("key", "unknown")
    primary = session.get("primary") or {}

    tl_sels = session.get("step1", {}).get("selections", []) or []
    z_sels = session.get("step2", {}).get("selections", []) or []
    atp_sels = session.get("step3", {}).get("selections", []) or []
    gaps = (session.get("gaps") or "").strip()
    art = (session.get("art_string") or "").strip()

    tl_list = ", ".join([s.get("id_or_key") or s.get("key", "") for s in tl_sels if s])
    z_keys = [s.get("key") or s.get("id_or_key", "") for s in z_sels if s]
    # Always include the primary case key itself for traceability (even though
    # Step 2 Zephyr table now omits all current/Cases-list entries and only shows
    # external cross-refs).
    if key and key not in z_keys:
        z_keys = [key] + z_keys
    z_list = ", ".join(z_keys)
    atp_list = ", ".join([s.get("id_or_key") or s.get("id", "") for s in atp_sels if s])

    parts = [f"Note: Related ART Tests linked in Traceability for {key}."]

    if primary and primary.get("m"):
        w = (primary.get("w") or "").strip()
        parts.append(f"Primary: {primary.get('m')} ({w})" if w else f"Primary: {primary.get('m')}")

    if tl_list:
        parts.append(f"TestLink: {tl_list}")

    if z_list:
        parts.append(f"Zephyr: {z_list}")

    if atp_list:
        parts.append(f"ART: {atp_list}")

    if art:
        parts.append(f"ART string: {art}")

    if gaps:
        parts.append(f"Gaps: {gaps[:120]}")

    # Zephyr links (first few) + wiki
    if z_keys:
        z_links = " ".join([f"https://jira.atlnz.lc/secure/Tests.jspa#/testCase/{k}" for k in z_keys[:3]])
        parts.append(z_links)

    parts.append("https://wiki.atlnz.lc/awpwiki/index.php (see related bundles)")

    # Format to closely match historical refined-cases first-step style (using <br /> and trailing dl)
    note = "<br />\n".join(parts)
    note += "<br /><dl><br /></dl><br />"
    return note


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


def synthesize_objectives_and_steps(session: Dict[str, Any], llm_config: Optional[Dict] = None) -> Dict[str, Any]:
    """Main entry: build prompt from template, call LLM, parse to repeatable output.

    llm_config can come from the session "login" (set_llm_config endpoint) and
    takes precedence over environment variables.

    Supports Grok (OpenAI compat) and Claude (Anthropic native). Real credentials or CLI required.

    Gaps analysis is generated here (not edited in Step 3) for Traceability + the note step.
    """
    # Resolve effective config (session login > env). No mock default.
    cfg = llm_config or {}
    provider = (cfg.get("provider") or "").lower()
    auth_method = (cfg.get("auth_method") or "api_key").lower()
    # Support api_key or token (from Subscription Account / session login flow)
    credential = cfg.get("api_key") or cfg.get("token") or os.environ.get("LLM_API_KEY")
    base_url = cfg.get("base_url") or os.environ.get("LLM_BASE_URL")
    model = cfg.get("model") or os.environ.get("LLM_MODEL", "default")

    # Gaps for Traceability — generated at process completion, not a Step 3 form field
    gaps_result = generate_coverage_gaps(session, llm_config=cfg)
    gaps_text = gaps_result.get("gaps") or ""
    # Mutate working session copy so note + prompts see the same gaps
    session = {**session, "gaps": gaps_text}

    # Build context for template (selections, case, process principles excerpt)
    context = {
        "case_key": session.get("key"),
        "primary": session.get("primary"),
        "testlink_selections": session.get("step1", {}).get("selections", []),
        "zephyr_selections": session.get("step2", {}).get("selections", []),
        "atp_selections": session.get("step3", {}).get("selections", []),
        "gaps": gaps_text,
        "art_string": session.get("art_string", ""),
        "process_principles": "Objectives are declarative artefacts (what should be true). Use <ul><li>. First testScript step is notes + traceability. Cover positive/negative/special cases.",
    }

    # Step 1: generate objective
    objective_prompt = render_prompt("generate_objectives.jinja", context)
    obj_meta = _call_llm_with_meta(objective_prompt, provider=provider, api_key=credential, base_url=base_url, model=model, auth_method=auth_method)
    obj_llm = obj_meta.get("content", "")
    structured = parse_llm_to_structured(obj_llm, context.get("case_key", "unknown"))

    # Step 2: generate steps (LLM focuses on verification steps after the note)
    steps_prompt = render_prompt("generate_steps.jinja", {**context, "objective": structured["objective"]})
    steps_meta = _call_llm_with_meta(steps_prompt, provider=provider, api_key=credential, base_url=base_url, model=model, auth_method=auth_method)
    steps_llm = steps_meta.get("content", "")
    steps_struct = parse_llm_to_structured(steps_llm, context.get("case_key", "unknown"))

    # Always build server-side repeatable note and place it first.
    # This guarantees the traceability note uses confirmed selections (repeatable output).
    note_desc = build_traceability_note(session)
    note_step = {
        "description": note_desc,
        "expectedResult": ""
    }
    llm_steps = steps_struct.get("testScript", {}).get("steps", [])
    # Drop any generic note the LLM may have produced; use our constructed one
    if llm_steps and ("Note:" in llm_steps[0].get("description", "") or "Traceability" in llm_steps[0].get("description", "")):
        llm_steps = llm_steps[1:]
    final_steps = [note_step] + llm_steps

    provenance = {
        "gaps_prompt": (gaps_result.get("provenance") or {}).get("gaps_prompt"),
        "gaps_response": (gaps_result.get("provenance") or {}).get("gaps_response"),
        "objective_prompt": objective_prompt,
        "objective_response": obj_llm,
        "steps_prompt": steps_prompt,
        "steps_response": steps_llm,
        "provider": obj_meta.get("provider", "unknown"),
        "auth_method": obj_meta.get("auth_method", "api_key"),
        "model": obj_meta.get("model", "default"),
        "error": obj_meta.get("error", False) or steps_meta.get("error", False) or (gaps_result.get("provenance") or {}).get("error", False),
    }

    core = {
        "objective": structured["objective"],
        "testScript": {"type": "steps", "steps": final_steps},
        "gaps": gaps_text,
        "provenance": provenance,
    }

    # Attach lightweight validation (used by export and for audit)
    validation = validate_zephyr_payload({session.get("key", "unknown"): core})

    return {
        **core,
        "validation": validation,
    }


def _parse_suggest_id_list(content: str, id_patterns: Optional[List[str]] = None) -> List[Dict[str, str]]:
    """Parse LLM JSON array of {id, reason}; optional regex fallbacks for bare IDs."""
    suggestions: List[Dict[str, str]] = []
    try:
        json_match = re.search(r'\[\s*\{.*\}\s*\]', content or "", re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group(0))
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


def suggest_relevant_atp(session: Dict[str, Any], candidates: List[Dict[str, Any]], llm_config: Optional[Dict] = None) -> List[Dict[str, Any]]:
    """Use LLM to pre-select the most relevant ATPyLib tests from a list of candidates.

    Returns list of {"id": "...", "reason": "..."}
    Uses same provider/config as other LLM calls.
    """
    if not candidates:
        return []

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
    meta = _call_llm_with_meta(prompt, provider=provider, api_key=credential, base_url=base_url, model=model, auth_method=auth_method)
    content = meta.get("content", "")
    return _parse_suggest_id_list(content, id_patterns=[r'(\d+\.\d+(?:\.\d+)?)'])


def suggest_relevant_testlink(
    session: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    llm_config: Optional[Dict] = None,
    case_title: str = "",
) -> List[Dict[str, Any]]:
    """LLM pre-select TestLink cases. Returns [{"id","reason"}, ...]."""
    if not candidates:
        return []
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
    prompt = render_prompt("suggest_testlink.jinja", context)
    meta = _call_llm_with_meta(
        prompt,
        provider=provider,
        api_key=credential,
        base_url=cfg.get("base_url") or os.environ.get("LLM_BASE_URL"),
        model=cfg.get("model") or os.environ.get("LLM_MODEL", "default"),
        auth_method=auth_method,
    )
    return _parse_suggest_id_list(meta.get("content", ""), id_patterns=[r'(AWP-\d+)'])


def suggest_relevant_zephyr(
    session: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    llm_config: Optional[Dict] = None,
    case_title: str = "",
) -> List[Dict[str, Any]]:
    """LLM pre-select external Zephyr cases. Returns [{"id","reason"}, ...] (id = key)."""
    if not candidates:
        return []
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
    prompt = render_prompt("suggest_zephyr.jinja", context)
    meta = _call_llm_with_meta(
        prompt,
        provider=provider,
        api_key=credential,
        base_url=cfg.get("base_url") or os.environ.get("LLM_BASE_URL"),
        model=cfg.get("model") or os.environ.get("LLM_MODEL", "default"),
        auth_method=auth_method,
    )
    return _parse_suggest_id_list(meta.get("content", ""), id_patterns=[r'(AWPTCM-T\d+)'])


def analyze_atp_coverage(session: Dict[str, Any], candidates: List[Dict[str, Any]], llm_config: Optional[Dict] = None) -> Dict[str, Any]:
    """Score/rank ATP candidates for Step 3 review (no gaps text — gaps are synthesis/export only).

    Returns: {"ranked": [{"id": "...", "score": 0.91, "reason": "..."}, ...]}
    """
    if not candidates:
        return {"ranked": []}

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

    try:
        prompt = render_prompt("analyze_atp_coverage.jinja", context)
        meta = _call_llm_with_meta(
            prompt,
            provider=provider,
            api_key=credential,
            base_url=cfg.get("base_url") or os.environ.get("LLM_BASE_URL"),
            model=cfg.get("model") or os.environ.get("LLM_MODEL", "default"),
            auth_method=auth_method
        )
        content = meta.get("content", "")

        # Parse the JSON response
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group(0))
            ranked = parsed.get("ranked", [])[:10]
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

    # Fallback
    top = candidates[:6]
    return {
        "ranked": [{"id": c.get("id"), "score": 0.7, "reason": "Selected via fallback keyword matching"} for c in top],
    }

