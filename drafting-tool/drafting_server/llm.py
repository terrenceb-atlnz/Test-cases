"""
LLM integration for server-backed drafting tool.

Uses prompt templating for repeatable inputs (Jinja templates inject selections + process principles).
Post-processes LLM responses with parsers for repeatable outputs (Objectives as <ul> + steps).

Real LLM support:
- Set LLM_API_KEY and LLM_BASE_URL (OpenAI-compatible, e.g. https://api.x.ai/v1 for Grok, OpenAI, or Claude-compatible endpoints)
- Better error handling + logging of exact prompts/responses (for full provenance per SERVER-README.md)
- Capture of prompts + raw responses returned to caller for storage in session.

Parsing improved for robustness (regex + JSON fallback).
MOCK mode (LLM_API_KEY=MOCK) for testing without keys.
"""

import os
import json
import re
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
    """Backward-compatible wrapper. Prefers MOCK/env."""
    result = _call_llm_with_meta(prompt, provider="mock", model=model)
    return result.get("content", "ERROR: no content")


def _call_llm_with_meta(prompt: str, provider: str = "mock", api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "default", auth_method: str = "api_key") -> Dict[str, Any]:
    """Core LLM caller with multi-provider support.

    Supports:
    - API Key (direct key paste)
    - Account Login (token from browser account login)

    provider: "grok" | "claude" | "openai" | "mock"
    The credential (api_key param here) can come from either.

    Grok uses OpenAI-compatible format.
    Claude uses Anthropic native format.
    """
    provider = (provider or "mock").lower()
    auth_method = (auth_method or "api_key").lower()

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

    credential = api_key
    if not credential or provider == "mock":
        # MOCK: deterministic repeatable response. Tailor based on prompt content for better demo.
        # Detect steps request more reliably (prompt for steps includes "JSON steps array" instruction)
        prompt_lower = prompt.lower()
        is_steps = "produce the json array" in prompt_lower or "output as json steps array" in prompt_lower or ("steps" in prompt_lower and "description" in prompt_lower and "objective" in prompt_lower and "first step will be injected" in prompt_lower)
        if is_steps:
            mock_response = '[{"description": "Verify default behavior with no pluggable (auto polarity and reporting).", "expectedResult": ""}, {"description": "Insert supported pluggable and confirm polarity resolution + link establishment.", "expectedResult": ""}, {"description": "Test straight and crossover cables in Auto mode; verify link and status.", "expectedResult": ""}, {"description": "Verify port reports negotiated speed/duplex/polarity accurately.", "expectedResult": ""}]'
        else:
            mock_response = """<ul>
<li>The port with no pluggable defaults to automatic MDI/MDIX polarity handling.</li>
<li>Inserting a supported pluggable resolves polarity and establishes link.</li>
<li>A port configured for Auto speed and duplex establishes a link with a compliant partner.</li>
<li>The port accurately reports Auto mode together with the negotiated speed and duplex values.</li>
</ul>"""
        print(f"[LLM {provider.upper()} via {auth_method}] Prompt (first 300 chars):", prompt[:300])
        print(f"[LLM {provider.upper()}] Response (first 200):", mock_response[:200], "...")
        meta.update({
            "content": mock_response,
            "raw_response": mock_response,
            "provider": "MOCK",
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
    Improved: tries JSON first (when steps template asks for it), then robust regex.
    Note construction is now handled by build_traceability_note for repeatability.
    """
    # Try JSON first (for steps prompt which requests JSON array)
    steps = []
    try:
        # Look for a JSON array in the output
        json_match = re.search(r'\[\s*\{.*\}\s*\]', llm_output, re.DOTALL)
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
        step_lines = re.findall(r"^\s*(?:\d+[\.\)]|\-)\s*(.+)$", llm_output, re.MULTILINE)
        for line in step_lines:
            desc = line.strip()
            if desc:
                steps.append({"description": desc, "expectedResult": ""})

    # Objective: extract <ul>...</ul> or fall back to first paragraph as list
    objective_match = re.search(r"<ul>.*?</ul>", llm_output, re.DOTALL | re.IGNORECASE)
    if objective_match:
        objective = objective_match.group(0)
    else:
        # Fallback: try to find bullet-like lines and wrap
        bullets = re.findall(r"^\s*[\-\*]\s*(.+)$", llm_output, re.MULTILINE)
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
    z_list = ", ".join(z_keys)
    atp_list = ", ".join([s.get("id_or_key") or s.get("id", "") for s in atp_sels if s])

    lines = [
        f"Note: Related ART Tests linked in Traceability for {key}."
    ]

    # Add wiki/related if known pattern (can be extended)
    lines.append("https://wiki.atlnz.lc/awpwiki/index.php (see related bundles)")

    if z_keys:
        # Include example Zephyr links like real artifacts
        z_links = " ".join([f"https://jira.atlnz.lc/secure/Tests.jspa#/testCase/{k}" for k in z_keys[:3]])
        lines.append(f"Zephyr reviewed: {z_list} {z_links}")

    if atp_list:
        lines.append(f"ART: {atp_list}")

    if tl_list:
        lines.append(f"TestLink reviewed: {tl_list}")

    if primary and primary.get("m"):
        lines.append(f"Primary: {primary.get('m')} - {primary.get('w', '')}")

    if gaps:
        lines.append(f"Gaps noted: {gaps[:160]}")

    if art:
        lines.append(f"ART string: {art}")

    note = "<br />\n".join(lines)
    note += "<dl><br /></dl><br />"
    return note

def synthesize_objectives_and_steps(session: Dict[str, Any], llm_config: Optional[Dict] = None) -> Dict[str, Any]:
    """Main entry: build prompt from template, call LLM, parse to repeatable output.

    llm_config can come from the session "login" (set_llm_config endpoint) and
    takes precedence over environment variables.

    Supports Grok (OpenAI compat) and Claude (Anthropic native) + fallback MOCK.
    """
    # Build context for template (selections, case, process principles excerpt)
    context = {
        "case_key": session.get("key"),
        "primary": session.get("primary"),
        "testlink_selections": session.get("step1", {}).get("selections", []),
        "zephyr_selections": session.get("step2", {}).get("selections", []),
        "atp_selections": session.get("step3", {}).get("selections", []),
        "gaps": session.get("gaps", ""),
        "process_principles": "Objectives are declarative artefacts (what should be true). Use <ul><li>. First testScript step is notes + traceability. Cover positive/negative/special cases.",
        # Add more excerpts as needed
    }

    # Resolve effective config (session login > env > default mock)
    cfg = llm_config or {}
    provider = (cfg.get("provider") or "").lower() or "mock"
    auth_method = (cfg.get("auth_method") or "api_key").lower()
    # Support both api_key (direct) and token (from account login)
    credential = cfg.get("api_key") or cfg.get("token") or os.environ.get("LLM_API_KEY")
    base_url = cfg.get("base_url") or os.environ.get("LLM_BASE_URL")
    model = cfg.get("model") or os.environ.get("LLM_MODEL", "default")

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
    note_step = {
        "description": build_traceability_note(session),
        "expectedResult": ""
    }
    llm_steps = steps_struct.get("testScript", {}).get("steps", [])
    # Drop any generic note the LLM may have produced; use our constructed one
    if llm_steps and "Note:" in llm_steps[0].get("description", ""):
        llm_steps = llm_steps[1:]
    final_steps = [note_step] + llm_steps

    provenance = {
        "objective_prompt": objective_prompt,
        "objective_response": obj_llm,
        "steps_prompt": steps_prompt,
        "steps_response": steps_llm,
        "provider": obj_meta.get("provider", "unknown"),
        "auth_method": obj_meta.get("auth_method", "api_key"),
        "model": obj_meta.get("model", "default"),
        "error": obj_meta.get("error", False) or steps_meta.get("error", False),
    }

    return {
        "objective": structured["objective"],
        "testScript": {"type": "steps", "steps": final_steps},
        "provenance": provenance,
    }


def suggest_relevant_atp(session: Dict[str, Any], candidates: List[Dict[str, Any]], llm_config: Optional[Dict] = None) -> List[Dict[str, Any]]:
    """Use LLM to pre-select the most relevant ATPyLib tests from a list of candidates.

    Returns list of {"id": "...", "reason": "..."}
    Uses same provider/config as other LLM calls.
    """
    if not candidates:
        return []

    cfg = llm_config or {}
    provider = (cfg.get("provider") or "").lower() or "mock"
    auth_method = (cfg.get("auth_method") or "api_key").lower()
    credential = cfg.get("api_key") or cfg.get("token") or os.environ.get("LLM_API_KEY")

    # Special handling for MOCK (demo): return deterministic relevant suggestions
    if provider == "mock" or not credential:
        case_key = session.get("key", "")
        # Pick some plausible ones based on case keywords (demo only)
        mock_ids = []
        title_lower = str(session.get("primary", "")).lower() + " " + case_key.lower()
        for c in candidates[:15]:
            cid = c.get("id", "")
            desc = (c.get("description") or "").lower()
            if any(k in title_lower or k in desc for k in ["port", "auto", "mdi", "arp", "dhcp", "qos", "led", "poe", "auth"]):
                mock_ids.append(cid)
            if len(mock_ids) >= 5:
                break
        if not mock_ids:
            mock_ids = [c["id"] for c in candidates[:4]]
        return [{"id": iid, "reason": "Pre-selected by MOCK LLM based on case keywords"} for iid in mock_ids[:6]]

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

    # Try to parse JSON array from LLM response
    suggestions = []
    try:
        # Look for JSON array
        json_match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group(0))
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and item.get("id"):
                        suggestions.append({
                            "id": str(item.get("id", "")).strip(),
                            "reason": item.get("reason", "LLM selected as relevant")
                        })
    except Exception as e:
        print(f"[LLM ATP suggest] JSON parse failed: {e}")

    # Fallback: try to extract IDs mentioned
    if not suggestions:
        ids_found = re.findall(r'(\d+\.\d+(?:\.\d+)?)', content)
        for iid in ids_found[:8]:
            suggestions.append({"id": iid, "reason": "Mentioned by LLM"})

    # Dedup and limit
    seen = set()
    final = []
    for s in suggestions:
        if s["id"] not in seen:
            seen.add(s["id"])
            final.append(s)
            if len(final) >= 8:
                break

    return final
