"""The workspace LLM login: what it is, whether it can drive a request, and applying it.

One idea, in one place. The workspace default (the `_workspace_llm` row in ck.db) is the
single source of truth for which backend a request goes to; a per-case `llm_config` that
diverges from it is a STALE leftover from a previous default, never an intentional
override. Everything here exists to keep that true — deciding whether a config is usable
(`llm_is_active`), whether two configs mean the same backend (`same_backend`), and
re-syncing a session that has drifted (`apply_workspace_llm`).

Extracted from `routers/wizard.py` (PLAN-backend-module-split.md commit 8) for a specific
reason: `routers/pytest_create.py` imported `_load_global_llm`, `_llm_is_active` and
`_same_backend` out of a sibling router, and kept a hand-copied `_apply_workspace_llm`
whose docstring said "Mirrors wizard…". Both routers now import from here, so the two
tools cannot silently disagree about which LLM they are talking to — which they already
did once (the 2026-07-20 bug where PyTest Creator endpoints used the wrong backend).

`apply_workspace_llm` is deliberately untyped in its `sess` parameter. wizard's and
pytest_create's copies were byte-identical bodies differing ONLY in the annotation
(`WizardSession` vs `PtSession`), and the body touches nothing but `sess.llm_config` —
so one duck-typed function serves both, and there is nothing left to drift.

A leaf: imports `db`, `models` and `local_llm_key` only. It must never import `routers.*`.
"""

import logging
from typing import Any, Optional

import db
from local_llm_key import get_local_llm_key
from models import SUPPORTED_AUTH_METHODS, LLMConfig, model_to_dict

log = logging.getLogger(__name__)


def llm_is_active(cfg: Optional[LLMConfig]) -> bool:
    """True when the config can actually drive synthesis (CLI mode or stored key).

    A config naming a backend outside `SUPPORTED_AUTH_METHODS` is NOT active, even if it
    carries a credential. Before 2026-08-04 a stored `api_key`/`token` alone made a config
    "active"; a session persisted back then would otherwise report ready here and be
    refused at the transport, which reads as an outage rather than as a retired backend.
    """
    if not cfg:
        return False
    am = (getattr(cfg, "auth_method", None) or "").lower()
    if am not in SUPPORTED_AUTH_METHODS:
        return False
    if am in ("claude_code", "claude_agent", "grok_cli"):
        return True
    if am == "local_llm":
        # Key lives server-side (secrets.local.json), never on the config.
        return bool(get_local_llm_key())
    return False


def same_backend(a: Optional[LLMConfig], b: Optional[LLMConfig]) -> bool:
    """True when two configs would hit the SAME LLM backend — compares the
    dispatch-selecting fields (auth_method / provider / model) only, ignoring
    credentials. Used to decide whether a case session's config still matches the
    workspace default or is a stale leftover from a previous default."""
    if not a or not b:
        return False
    f = lambda c, k: (getattr(c, k, None) or "").lower()
    return all(f(a, k) == f(b, k) for k in ("auth_method", "provider", "model"))


def load_global_llm() -> Optional[LLMConfig]:
    """Load last-applied workspace LLM config (shared across all cases). Commit C:
    from the sessions table (id='_workspace_llm')."""
    try:
        raw = db.load_workspace_llm()
        if not raw:
            return None
        cfg = LLMConfig(**raw)
        return cfg if llm_is_active(cfg) else None
    except Exception as e:
        log.warning("failed to load workspace LLM config: %s", e)
        return None


def save_global_llm(cfg: LLMConfig) -> None:
    """Persist workspace LLM preference when the user applies a login/config."""
    if not cfg or not llm_is_active(cfg):
        return
    try:
        data = model_to_dict(cfg)
        db.save_workspace_llm(data)
    except Exception as e:
        log.warning("failed to save workspace LLM config: %s", e)


# --- per-task model routing (token-efficiency decision 6, 2026-09-07) ---------------
#
# Measured on AWPTCM-T44297 (TOKEN-EFFICIENCY-REPORT-2026-09-04.md §5): Sonnet 5 matched
# Opus on 4 of 5 sampled unit fills at ~59% of the cost and returned the same step-match
# shortlist at under half. The reviewer therefore gets to route those two call classes to a
# cheaper alias while Review and Fix stay on the toggle model. The routing lives on the
# WORKSPACE config (the same `_workspace_llm` row as the backend choice) and is applied here
# at dispatch, so a per-case `llm_config` copy — which `apply_workspace_llm` documents as
# never a legitimate override — cannot carry a stale routing either.

CLAUDE_MODEL_ALIASES = ("haiku", "sonnet", "opus")
TASK_MODEL_FIELDS = {"unit_fill": "unit_model", "step_match": "match_model"}
_ROUTED_AUTH_METHODS = ("claude_code", "claude_agent")


def normalize_task_model(value: Any) -> Optional[str]:
    """"" / None / "same" -> None (inherit `model`); a known alias -> itself; else ValueError."""
    v = (str(value).strip().lower() if value is not None else "")
    if v in ("", "same", "default"):
        return None
    if v not in CLAUDE_MODEL_ALIASES:
        raise ValueError(f"unknown Claude model alias '{value}'. "
                         f"Allowed: {', '.join(CLAUDE_MODEL_ALIASES)} or blank (same as model).")
    return v


def cfg_for_task(cfg: dict, task: str, workspace: Optional[LLMConfig] = None) -> dict:
    """The dispatch config for one call class: `cfg` with `model` swapped for the routed
    alias when the WORKSPACE says so. Returns a copy; `cfg` is untouched.

    Only under a Claude CLI method — the routing fields are Claude aliases and mean nothing
    to the vLLM or the Grok CLI. `workspace` is injectable for tests; production reads the
    stored workspace row so a per-case copy can never drift from it.
    """
    out = dict(cfg or {})
    field = TASK_MODEL_FIELDS.get(task)
    if not field:
        raise KeyError(f"unknown routed task '{task}'; known: {sorted(TASK_MODEL_FIELDS)}")
    if (out.get("auth_method") or "").lower() not in _ROUTED_AUTH_METHODS:
        return out
    ws = workspace if workspace is not None else load_global_llm()
    routed = getattr(ws, field, None) if ws else None
    if routed and routed in CLAUDE_MODEL_ALIASES:
        out["model"] = routed
    return out


def apply_workspace_llm(sess: Any) -> bool:
    """Re-sync this session's LLM config to the active workspace default.

    Returns True if the session was updated (caller should persist).

    Takes any session object with an `llm_config` attribute — a WizardSession or a
    PtSession. It was two identical functions before commit 8, one per router, differing
    only in that annotation.

    The active workspace default is the single source of truth: `set_llm_config`
    always writes a case's config === the workspace default (there is no code path
    that gives a case a config that legitimately differs), so any divergence is a
    STALE leftover from a previous default, not an intentional per-case override.
    We therefore re-sync whenever the case has no active config OR its config no
    longer matches the workspace default's backend. This fixes the bug where a
    session whose stale config was a headless CLI mode (claude_agent/claude_code/
    grok_cli — which `llm_is_active` reports active unconditionally, since there
    is no server-side key to check) could NEVER re-sync and kept silently hitting
    the wrong backend. `llm_is_active` is intentionally left unchanged (it is also
    used for status/`has_key` reporting, where headless=active is correct).

    When there is no active workspace default we leave the session untouched, so
    "the workspace login persists across cases" still holds.
    """
    global_cfg = load_global_llm()
    if not global_cfg:
        return False
    cur = getattr(sess, "llm_config", None)
    if llm_is_active(cur) and same_backend(cur, global_cfg):
        return False
    # Fresh copy so case sessions do not share the same object instance
    raw = model_to_dict(global_cfg)
    sess.llm_config = LLMConfig(**raw)
    return True


def preview_from(result) -> dict:
    """Shape a dry_run function result ({dry_run, prompt, ...}) into the standard
    provenance-preview HTTP response. dry_run reuses the endpoint's real path so
    the previewed prompt is 1-for-1 with what a real send would transmit."""
    r = result if isinstance(result, dict) else {}
    return {"provenance": {
        "prompt": r.get("prompt", ""),
        "provider": r.get("provider"),
        "model": r.get("model"),
        "auth_method": r.get("auth_method"),
        "note": r.get("note"),
        "dry_run": True,
    }}
