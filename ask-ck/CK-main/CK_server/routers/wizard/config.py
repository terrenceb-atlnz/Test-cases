"""Generator configuration endpoints — session clear, CLI status, and LLM config.

clear_session, claude/grok CLI status, get/set LLM config, and the LLM health ping.
Split out of the monolithic routers/wizard.py (PLAN-backend-module-split.md commit 10).
"""
import time
from typing import Optional

from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from models import (
    RETIRED_AUTH_METHODS,
    SUPPORTED_AUTH_METHODS,
    LLMConfig,
    model_to_dict,
    safe_session_dict,
)
from llm import _health_ping, check_claude_cli, check_grok_cli
from local_llm_key import get_local_llm_key, set_local_llm_key
from llm_config import (
    TASK_MODEL_FIELDS,
    llm_is_active,
    load_global_llm,
    normalize_task_model,
    save_global_llm,
)
from session_store import (
    clear_persisted,
    load_persisted,
    mark_updated,
    persist_session,
    sessions,
)

router = APIRouter()

@router.post("/clear_session/{key}")
async def clear_session(key: str):
    """Clear both in-memory and persisted session state for a case.
    Useful for resetting after a bad confirm or wanting to start fresh.

    Does NOT clear the workspace LLM preference — Apply / Login still applies
    to the next case you load.
    """
    sessions.pop(key, None)
    clear_persisted(key)
    return {
        "message": f"Session for {key} cleared (workspace LLM preference kept)",
        "workspace_llm_kept": True,
    }


@router.get("/claude_cli_status")
async def claude_cli_status():
    """Report whether the Claude Code CLI is installed on the server machine.

    Used by the headless "claude_code" auth mode. Checks binary presence + version
    only (spends no tokens). Login state surfaces on first real call.
    """
    return check_claude_cli()


@router.get("/grok_cli_status")
async def grok_cli_status():
    """Report whether the xAI Grok CLI is installed (for SuperGrok/X Premium+ subscription login)."""
    return check_grok_cli()


@router.get("/llm_config")
async def get_llm_config():
    """Return the persisted workspace LLM config (no secrets) for cold page load.

    Without this, a fresh page has no way to learn the stored login, so the LLM
    status shows "No credential" until the user re-applies — even though the
    workspace default is persisted and already drives calls. The browser calls
    this on boot to render the real status (and, for local_llm, whether a key is
    stored). Credentials are never returned; only booleans/flags.
    """
    cfg = load_global_llm()
    if not cfg:
        return {"llm_config": None}
    am = (getattr(cfg, "auth_method", None) or "").lower()
    safe = {
        "provider": cfg.provider,
        "auth_method": cfg.auth_method,
        "model": cfg.model,
        "unit_model": cfg.unit_model,
        "match_model": cfg.match_model,
        "base_url": cfg.base_url,
        "has_key": llm_is_active(cfg),
    }
    if am == "local_llm":
        safe["local_llm_key_set"] = bool(get_local_llm_key())
    return {"llm_config": safe}


@router.post("/llm_health")
async def llm_health():
    """Ping the configured workspace LLM with a minimal completion to confirm it
    is reachable and answering. Exercises the exact real-call path (config
    resolution + credential + transport via _call_llm_with_meta), so it
    distinguishes 'my config is wrong' from 'the backend is down', and the ping
    is recorded in debug-log like any other call. Provider-agnostic: works for
    whatever auth_method is active, not just local_llm.
    """
    cfg = load_global_llm()
    if not cfg or not llm_is_active(cfg):
        return {"ok": False, "reason": "not_configured",
                "detail": "No active LLM configuration. Apply a provider on the Configure page first."}
    llm_cfg = model_to_dict(cfg)
    t0 = time.monotonic()
    # Tiny prompt through the same choke point every real call uses. run_prompt
    # needs a template; use a throwaway one-liner rendered inline via a literal.
    meta = await run_in_threadpool(
        _health_ping, llm_cfg,
    )
    latency_ms = int((time.monotonic() - t0) * 1000)
    if meta.get("error"):
        return {"ok": False, "reason": "call_failed",
                "auth_method": getattr(cfg, "auth_method", None),
                "model": meta.get("model"), "latency_ms": latency_ms,
                "detail": (meta.get("error_detail") or meta.get("content") or "LLM error")[:500]}
    content = (meta.get("content") or "").strip()
    return {"ok": True, "auth_method": getattr(cfg, "auth_method", None),
            "provider": meta.get("provider"), "model": meta.get("model"),
            "latency_ms": latency_ms, "reply": content[:80],
            "usage": meta.get("usage")}


@router.post("/set_llm_config")
@router.post("/set_llm_config/{key}")
async def set_llm_config(body: dict, key: Optional[str] = None):
    """Login-like endpoint. Sets the workspace LLM provider (and, when a case
    key is supplied, that case's session config too).

    The case key is OPTIONAL: applying an LLM config no longer requires a loaded
    case. Without a key, the choice is saved as the workspace default
    (sessions/_workspace_llm.json) and load_case copies it onto any case that has
    no active config.

    Only `SUPPORTED_AUTH_METHODS` are accepted, and the set is a governance control
    rather than a convenience list — see the comment on it in `models.py`:
    - "local_llm": the org's self-hosted vLLM. The default. The key is entered here and
      stored server-side; the ENDPOINT IS FIXED IN CODE and is not configurable.
    - "claude_agent": the Claude Code CLI on the user's OWN machine, via the browser
      bridge. No credential is collected; each user spends their own seat.
    - "claude_code": headless Claude Code CLI on the server host (Claude only). Same
      destination as claude_agent, but spends the SERVER's seat, shared by every user
      of the page. Offered in the UI as of 2026-08-26 — the "not offered in the UI"
      exclusion was reversed deliberately (see the claude_code entry in `models.py`
      and PLAN-llm-mode-selection.md Option A); hiding it never stopped the spend, it
      only stopped the UI from reporting the active mode honestly.
    - "grok_cli": headless Grok CLI (subscription OAuth). No credential is collected.

    REFUSED (2026-08-04): "api_key" and legacy "account", which took a caller-supplied
    key and a free-form `base_url` and so could point the tool at any third-party model
    endpoint. `api_key` / `token` / `base_url` in the request body are now IGNORED —
    no supported backend takes a browser-supplied credential or endpoint. An
    unrecognised auth_method is a 400; it used to be silently downgraded to "api_key",
    which turned a typo into an unintended backend.
    """
    sess = None
    if key:
        # Best-effort: attach to the case session when it exists, but an unknown
        # key must not block the workspace-level apply.
        sess = sessions.get(key) or load_persisted(key)

    provider = (body.get("provider") or "grok").lower().strip()
    auth_method = (body.get("auth_method") or "local_llm").lower().strip()
    model = body.get("model")

    # Checked BEFORE the coercion below. It used to sit after it, so "mock" was rewritten
    # to "grok" and this branch could never fire — a validation that read as enforced and
    # was not.
    if provider == "mock":
        raise HTTPException(400, "MOCK provider removed. Use grok, claude or openai with real auth.")
    if provider not in ("grok", "claude", "openai"):
        provider = "grok"
    if auth_method in RETIRED_AUTH_METHODS:
        raise HTTPException(
            400,
            f"auth_method '{auth_method}' is no longer supported. This tool talks only to "
            f"approved backends ({', '.join(SUPPORTED_AUTH_METHODS)}); a caller-supplied "
            f"API key or endpoint is not one of them.",
        )
    if auth_method not in SUPPORTED_AUTH_METHODS:
        raise HTTPException(
            400,
            f"unknown auth_method '{auth_method}'. Supported: {', '.join(SUPPORTED_AUTH_METHODS)}.",
        )
    if auth_method in ("claude_code", "claude_agent") and provider != "claude":
        raise HTTPException(400, "Claude Code modes are only available for the Claude provider.")
    if auth_method == "grok_cli" and provider != "grok":
        raise HTTPException(400, "Grok CLI (subscription) mode is only available for the Grok provider.")
    if auth_method == "local_llm":
        # The radio always pairs local_llm with openai; coerce rather than 400.
        provider = "openai"
        # Key (re-)entered on the Configure page: persist server-side, where it can
        # never land in cfg / the session / the response below.
        new_key = (body.get("local_llm_key") or "").strip()
        if new_key:
            set_local_llm_key(new_key)

    # Build the config. NO credential and NO endpoint is taken from the request: the
    # local_llm key went to the server-side store just above, and every other supported
    # backend authenticates through a CLI the operator logged in themselves. Anything the
    # caller sent as api_key / token / base_url is deliberately dropped on the floor.
    cfg = LLMConfig(provider=provider, auth_method=auth_method)

    # Per-task model routing (decision 6, 2026-09-07): `unit_model` / `match_model`. A field
    # PRESENT in the body is set (blank clears it); a field ABSENT is carried over from the
    # stored workspace config, so the Haiku/Sonnet/Opus toggle — which posts only `model` —
    # cannot silently wipe a routing the reviewer chose a moment earlier. Only meaningful
    # under the Claude CLI methods; stored as None for every other backend.
    previous = load_global_llm()
    for field in TASK_MODEL_FIELDS.values():
        if auth_method not in ("claude_code", "claude_agent"):
            setattr(cfg, field, None)
            continue
        if field in body:
            try:
                setattr(cfg, field, normalize_task_model(body.get(field)))
            except ValueError as e:
                raise HTTPException(400, f"{field}: {e}")
        else:
            setattr(cfg, field, getattr(previous, field, None) if previous else None)

    if model:
        cfg.model = model
    else:
        # Sensible defaults per provider
        if auth_method == "local_llm":
            cfg.model = "vllm-fast"
        elif provider == "grok" and auth_method != "grok_cli":
            cfg.model = "grok-beta"
        elif provider == "claude" and auth_method not in ("claude_code", "claude_agent"):
            cfg.model = "claude-3-5-sonnet-20241022"
        # claude_code / claude_agent / grok_cli: leave model unset so the CLI's own default is used

    # Remember as workspace default so future case loads keep this LLM choice
    save_global_llm(cfg)

    # Also apply to the case session when one is loaded/known
    if sess:
        sess.llm_config = cfg
        mark_updated(sess)
        persist_session(sess)

    # Headless mode readiness comes from the CLI install, not a stored credential
    cli_status = check_claude_cli() if auth_method == "claude_code" else None
    grok_cli_status = check_grok_cli() if auth_method == "grok_cli" else None
    # local_llm readiness = a key is stored server-side (never echo the key itself)
    local_llm_key_set = bool(get_local_llm_key()) if auth_method == "local_llm" else None

    # Return safe view (no credentials)
    safe_config = {
        "provider": cfg.provider,
        "auth_method": cfg.auth_method,
        # No `cfg.api_key or cfg.token` term any more: nothing populates them, so readiness
        # is entirely "is the CLI installed / is the server-side vLLM key stored".
        "has_key": (auth_method == "claude_code" and bool(cli_status and cli_status.get("available"))) or
                   (auth_method == "grok_cli" and bool(grok_cli_status and grok_cli_status.get("available"))) or
                   (auth_method == "local_llm" and bool(local_llm_key_set)),
        "model": cfg.model,
        "unit_model": cfg.unit_model,
        "match_model": cfg.match_model,
        "base_url": cfg.base_url,
    }
    if cli_status is not None:
        safe_config["claude_cli"] = cli_status
    if grok_cli_status is not None:
        safe_config["grok_cli"] = grok_cli_status
    if local_llm_key_set is not None:
        safe_config["local_llm_key_set"] = local_llm_key_set

    scope = "this case and the workspace default" if sess else "the workspace default"
    result = {
        "message": f"LLM config set for {provider} (saved for {scope}).",
        "llm_config": safe_config,
    }
    if sess:
        result["session"] = safe_session_dict(sess)   # redacts llm_config secrets
    return result

