"""Which LLM a request goes to: the SEAT's choice, else the site default.

One idea, in one place. Since 2026-09-10 (PLAN-seat-setup-and-per-seat-llm.md §5) the
backend a request is dispatched to is decided PER SEAT: the browser stores the user's
choice and sends it on every `/api` call as the `X-CK-LLM` header; `effective_llm_config`
reads it (validated against the governance allowlist), falls back to the site default (the
`_workspace_llm` row in ck.db) for a seat that has never chosen, and only then to whatever
a stored session carries. Nothing here writes a session any more: a per-case `llm_config`
is a legacy copy, never a source of truth — on a shared server two seats work the same case
with different backends, so the case cannot own the choice.

Before that date the `_workspace_llm` row was authoritative for everyone and
`apply_workspace_llm` re-synced every session to it at dispatch — which is exactly how one
seat picking a backend on demo day flipped every other seat (`PLAN-llm-mode-selection.md`
§5 named the hazard). That function is gone; `effective_llm_config` is its replacement and
the ONLY dispatch-config resolver, imported by both routers.

Extracted from `routers/wizard.py` (PLAN-backend-module-split.md commit 8) for a specific
reason: `routers/pytest_create.py` imported `_load_global_llm`, `_llm_is_active` and
`_same_backend` out of a sibling router, and kept a hand-copied `_apply_workspace_llm`
whose docstring said "Mirrors wizard…". Both routers now import from here, so the two
tools cannot silently disagree about which LLM they are talking to — which they already
did once (the 2026-07-20 bug where PyTest Creator endpoints used the wrong backend).

`effective_llm_config` is deliberately untyped in its `sess` parameter: it serves a
`WizardSession` and a `PtSession` alike (it only ever READS `sess.llm_config`), so one
duck-typed function serves both routers and there is nothing left to drift.

A leaf: imports `db`, `models` and `local_llm_key` only. It must never import `routers.*`.
"""

import contextvars
import logging
from typing import Any, Optional

import db
from local_llm_key import get_local_llm_key
from models import RETIRED_AUTH_METHODS, SUPPORTED_AUTH_METHODS, LLMConfig, model_to_dict

log = logging.getLogger(__name__)

# --- the seat's choice -----------------------------------------------------------------
#
# The browser sends its stored LLM choice on every /api call as
#     X-CK-LLM: <auth_method>;<model>;<unit_model>;<match_model>
# (trailing fields optional). main.py's middleware validates it (400 on a bad value) and
# binds the raw string here for the duration of the request; ContextVars propagate into
# run_in_threadpool, the same mechanism llm.current_session_id relies on. Empty for
# non-browser callers and for a seat that has never chosen — those get the site default.
SEAT_LLM_HEADER = "X-CK-LLM"
current_seat_llm: "contextvars.ContextVar[str]" = contextvars.ContextVar("ck_seat_llm", default="")

_PROVIDER_FOR = {"local_llm": "openai", "claude_agent": "claude"}


def parse_seat_llm(raw: str) -> Optional[LLMConfig]:
    """`X-CK-LLM` header -> LLMConfig, or None for an empty header.

    Raises ValueError for anything outside the governance allowlist — the header is
    client-supplied, so the same closed set `set_llm_config` enforces is enforced here, and
    a retired method is named as retired rather than "unknown".
    """
    raw = (raw or "").strip()
    if not raw:
        return None
    parts = [p.strip() for p in raw.split(";")]
    parts += [""] * (4 - len(parts))
    auth_method, model, unit_model, match_model = (p.lower() for p in parts[:4])
    if auth_method in RETIRED_AUTH_METHODS:
        raise ValueError(f"auth_method '{auth_method}' is no longer supported")
    if auth_method not in SUPPORTED_AUTH_METHODS:
        raise ValueError(f"unknown auth_method '{auth_method}'. Supported: {', '.join(SUPPORTED_AUTH_METHODS)}")
    if len(raw) > 200:
        raise ValueError("header too long")
    cfg = LLMConfig(provider=_PROVIDER_FOR[auth_method], auth_method=auth_method)
    if model:
        cfg.model = model
    elif auth_method == "local_llm":
        cfg.model = "vllm-fast"
    if auth_method in _ROUTED_AUTH_METHODS:
        cfg.unit_model = normalize_task_model(unit_model)      # ValueError on a non-alias
        cfg.match_model = normalize_task_model(match_model)
    return cfg


def seat_llm_config() -> Optional[LLMConfig]:
    """The requesting seat's choice, or None when the request carried no (valid) header."""
    try:
        return parse_seat_llm(current_seat_llm.get(""))
    except ValueError as e:              # the middleware already 400s; belt and braces
        log.warning("ignoring invalid %s header: %s", SEAT_LLM_HEADER, e)
        return None


def effective_llm_config(sess: Any = None) -> dict:
    """The dispatch config for THIS request: seat header, else site default, else the
    session's own stored config, else {} (the transport's default backend).

    Never mutates `sess` — that was `apply_workspace_llm`'s job and it is what made one
    seat's choice leak into every other seat's requests through the shared case row.
    Duck-typed over WizardSession and PtSession (anything with an `llm_config`).
    """
    seat = seat_llm_config()
    if seat is not None:
        return model_to_dict(seat)
    site = load_global_llm()
    if site is not None:
        return model_to_dict(site)
    own = getattr(sess, "llm_config", None) if sess is not None else None
    if llm_is_active(own):
        return model_to_dict(own)
    return {}


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
    if am == "claude_agent":
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
# Measured on AWPTCM-T44297 (docs/TOKEN-EFFICIENCY-REPORT-2026-09-04.md §5): Sonnet 5 matched
# Opus on 4 of 5 sampled unit fills at ~59% of the cost and returned the same step-match
# shortlist at under half. The reviewer therefore gets to route those two call classes to a
# cheaper alias while Review and Fix stay on the toggle model. The routing travels with the
# backend choice — on the SEAT's X-CK-LLM header, else on the site-default row — and is
# applied here at dispatch, so a per-case `llm_config` copy (a legacy value, never a source
# of truth) cannot carry a stale routing either.

CLAUDE_MODEL_ALIASES = ("haiku", "sonnet", "opus")
TASK_MODEL_FIELDS = {"unit_fill": "unit_model", "step_match": "match_model"}
_ROUTED_AUTH_METHODS = ("claude_agent",)


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
    alias. Returns a copy; `cfg` is untouched.

    Where the routing comes from: the SEAT's header when the request carries one (a seat
    pays for its own aliases, and a seat that chose "same" must get its own model, not the
    site default's routing), else the site default row. Only under a Claude CLI method —
    the routing fields are Claude aliases and mean nothing to the vLLM.
    `workspace` is injectable for tests; a per-case session copy is never consulted.
    """
    out = dict(cfg or {})
    field = TASK_MODEL_FIELDS.get(task)
    if not field:
        raise KeyError(f"unknown routed task '{task}'; known: {sorted(TASK_MODEL_FIELDS)}")
    if (out.get("auth_method") or "").lower() not in _ROUTED_AUTH_METHODS:
        return out
    seat = seat_llm_config()
    if seat is not None:
        source = seat
    else:
        source = workspace if workspace is not None else load_global_llm()
    routed = getattr(source, field, None) if source else None
    if routed and routed in CLAUDE_MODEL_ALIASES:
        out["model"] = routed
    return out


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
