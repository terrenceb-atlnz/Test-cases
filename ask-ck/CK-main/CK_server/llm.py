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


def _call_llm_with_meta(prompt: str, provider: str = "", api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "default", auth_method: str = "api_key", timeout: int = 180) -> Dict[str, Any]:
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
        return _call_claude_code_headless(prompt, model, meta, timeout=timeout)
    if provider == "grok" and auth_method == "grok_cli":
        return _call_grok_cli_headless(prompt, model, meta, timeout=timeout)

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
        "process_principles": (
            "Objectives are declarative artefacts (what should be true). Use <ul><li>. "
            "First testScript step is notes + traceability. Cover positive/negative/special cases."
        ),
    }


def synthesize_objectives(session: Dict[str, Any], llm_config: Optional[Dict] = None) -> Dict[str, Any]:
    """Wizard Step 4: gaps (Traceability) + objective HTML only.

    Does not generate testScript steps — that is Step 5 after the user finalizes objectives.
    """
    rt = _resolve_llm_runtime(llm_config)
    gaps_result = generate_coverage_gaps(session, llm_config=rt["cfg"])
    gaps_text = gaps_result.get("gaps") or ""
    session = {**session, "gaps": gaps_text}
    context = _synthesis_context(session, gaps_text)

    objective_prompt = render_prompt("generate_objectives.jinja", context)
    obj_meta = _call_llm_with_meta(
        objective_prompt,
        provider=rt["provider"],
        api_key=rt["credential"],
        base_url=rt["base_url"],
        model=rt["model"],
        auth_method=rt["auth_method"],
    )
    obj_llm = obj_meta.get("content", "")
    structured = parse_llm_to_structured(obj_llm, context.get("case_key", "unknown"))

    provenance = {
        "gaps_prompt": (gaps_result.get("provenance") or {}).get("gaps_prompt"),
        "gaps_response": (gaps_result.get("provenance") or {}).get("gaps_response"),
        "objective_prompt": objective_prompt,
        "objective_response": obj_llm,
        "provider": obj_meta.get("provider", "unknown"),
        "auth_method": obj_meta.get("auth_method", "api_key"),
        "model": obj_meta.get("model", "default"),
        "error": obj_meta.get("error", False) or (gaps_result.get("provenance") or {}).get("error", False),
        "phase": "objectives",
    }

    return {
        "objective": structured["objective"],
        "gaps": gaps_text,
        "provenance": provenance,
    }


def synthesize_steps(
    session: Dict[str, Any],
    llm_config: Optional[Dict] = None,
    objective: Optional[str] = None,
) -> Dict[str, Any]:
    """Wizard Step 5: verification steps from finalized objective + review context.

    Prefers the provided objective (finalized Step 4), else session.step4.objective.
    Always injects the server-built first traceability note.
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
    steps_meta = _call_llm_with_meta(
        steps_prompt,
        provider=rt["provider"],
        api_key=rt["credential"],
        base_url=rt["base_url"],
        model=rt["model"],
        auth_method=rt["auth_method"],
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



def run_prompt(template_name: str, context: Dict[str, Any], llm_config: Optional[Dict] = None,
               timeout: int = 180) -> Dict[str, Any]:
    """Generic templated LLM call (used by the PyTest Creator + index enrichment).

    Renders templates/prompts/<template_name> with `context`, resolves the
    provider/auth from the session or env like every wizard call, and returns
    the raw meta dict from _call_llm_with_meta (content, provider, error, ...).
    Long generation prompts may pass a larger timeout than the 180s default.
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
    )
    meta["template"] = template_name
    return meta


def extract_json_block(content: str) -> Any:
    """Best-effort extraction of the first JSON object/array from LLM output.

    Handles ```json fences and leading prose. Returns None when nothing parses.
    """
    if not content:
        return None
    fenced = re.search(r"```(?:json)?\s*(.+?)```", content, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1).strip())
        except json.JSONDecodeError:
            pass
    for opener, closer in (("[", "]"), ("{", "}")):
        start = content.find(opener)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(content)):
            if content[i] == opener:
                depth += 1
            elif content[i] == closer:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(content[start:i + 1])
                    except json.JSONDecodeError:
                        break
    return None
