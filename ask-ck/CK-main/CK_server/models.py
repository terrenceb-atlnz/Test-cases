"""
Pydantic models for the server-backed drafting tool.
"""

from pydantic import BaseModel, BeforeValidator
from typing import Annotated, List, Optional, Dict, Any
from datetime import datetime

from timeutil import as_utc


def _coerce_utc(v: Any) -> Any:
    """Normalize a timestamp to timezone-aware UTC at validation time.

    `ck.db` holds NAIVE stamps written by the pre-cutover `datetime.utcnow()`. Coercing on
    the way IN means a loaded session can never carry a naive datetime, so no comparison
    downstream can raise "can't compare offset-naive and offset-aware datetimes" — the
    failure mode that makes a tz-aware migration risky. A naive value is read as UTC,
    which is what `utcnow()` always meant.

    Anything `as_utc` cannot read is passed through untouched so pydantic reports the real
    validation error instead of a confusing None.

    Not called with None: on an `Optional[UtcDatetime]` field pydantic resolves the None
    member of the union before reaching this validator, and an omitted field uses the
    default without validating at all. Verified — a `None` branch here would be dead code.
    """
    if isinstance(v, (datetime, str)):
        return as_utc(v) or v
    return v


# Every persisted timestamp uses this, so "aware UTC" is an invariant of the models
# rather than something each call site has to remember.
UtcDatetime = Annotated[datetime, BeforeValidator(_coerce_utc)]


class Selection(BaseModel):
    id_or_key: str
    title: str
    justification: Optional[str] = ""
    # Insertion order in the "chosen" shortlist (two-table review UI). Optional so
    # sessions persisted before this field still deserialize; the frontend falls
    # back to saved-list order when absent.
    order: Optional[int] = None

class StepState(BaseModel):
    confirmed: bool = False
    confirmed_at: Optional[UtcDatetime] = None
    none_selected: bool = False
    selections: List[Selection] = []
    # True when `confirmed` was inferred from a Complete on-disk bundle
    # (_backfill_from_refined) rather than set by an explicit in-session confirm.
    # Lets the export gate honour reviews the user did before step1-3 state was
    # captured, while keeping the two provenances distinguishable.
    backfilled: bool = False

# The BACKENDS THIS TOOL MAY TALK TO. Anything not on this list is refused outright —
# `set_llm_config` 400s and `_call_llm_raw` errors without dispatching.
#
# This is a GOVERNANCE CONTROL, not a convenience list (added 2026-08-04 for the AI
# governance review). Every entry has a fixed, known destination:
#   local_llm    -> the org's self-hosted vLLM. Internal. No data leaves the org.
#   claude_agent -> the Claude CLI on the USER's own workstation, via the browser bridge.
#                   Each user spends their own seat; the server holds no credential.
#   claude_code  -> the SAME Claude CLI, run directly on the SERVER host. Exists because
#                   claude_agent is browser-brokered and therefore CANNOT run headless —
#                   batch tooling has no tab to relay through (see the note on it below).
#                   Same destination as claude_agent (Anthropic), so no new egress.
#   grok_cli     -> the locally logged-in Grok CLI (subscription OAuth).
#
# REMOVED 2026-08-04: "api_key" and legacy "account". They accepted a caller-supplied key
# and a free-form base_url, so the tool could be pointed at an arbitrary third-party model
# endpoint — a capability we do not want and do not want to imply we have. The paired
# LLM_API_KEY / LLM_BASE_URL environment fallbacks went with them. Old persisted sessions
# naming a removed method are refused at call time rather than silently downgraded.
SUPPORTED_AUTH_METHODS = ("local_llm", "claude_agent", "claude_code", "grok_cli")

# Auth methods that once worked and are now deliberately refused. Kept NAMED (rather than
# just absent) so the refusal can say what happened instead of "unknown auth method".
RETIRED_AUTH_METHODS = ("api_key", "account")


class LLMConfig(BaseModel):
    """Per-session LLM login config.

    The permitted backends are `SUPPORTED_AUTH_METHODS` above; see that comment for what
    each one talks to and why the set is closed.

    - local_llm: the organization's self-hosted vLLM (OpenAI-compatible). The DEFAULT.
      Key is resolved server-side (Configure page -> secrets.local.json) and never
      supplied by the browser; the endpoint is fixed in code, not configurable.
    - claude_agent: browser-brokered Claude Code CLI on the USER's own machine
      (Claude only). For a shared server: each user runs ck-agent locally and their
      prompts execute against THEIR OWN seat — seats are never shared.
    - claude_code: headless Claude Code CLI on the SERVER host (Claude only). Uses the
      server machine's own `claude` login.

      UI EXCLUSION REVERSED 2026-08-26, deliberately, at Terrence's direction
      (PLAN-llm-mode-selection.md Option A). This entry used to read "NOT offered in
      the UI — interactive use would spend the SERVER's seat, the very thing
      claude_agent exists to avoid". That reasoning still describes the trade-off
      correctly, but keeping the mode out of the UI did not prevent the spend — it
      only stopped the UI from telling the truth about it. `restoreLLMConfigUI` mapped
      claude_code onto the claude_agent radio, so a server on claude_code showed a
      checked "my local machine", offered a local-agent check that could not work, and
      started a browser broker loop that could never be handed a job; every remote
      seat's Apply then wrote the broken value back for everybody. claude_code is now a
      first-class radio ("Claude Code CLI (this server)") whose panel states plainly
      that it spends this server's shared seat. Server-seat spending is therefore a
      normal, visible affordance rather than an out-of-band curl.

      It is NOT dead back-compat, and deleting it would break working tooling. It predates
      claude_agent (2026-07-13 vs 07-15) but acquired a distinct job when claude_agent took
      over the UI: claude_agent is brokered through a browser tab, so it cannot run
      HEADLESS at all. Any unattended process — the autopilot batch driver, the corpus
      enrichment tool, a shell run — has no tab to relay through, and
      tool/enrich_script_index.py explicitly rewrites claude_agent -> claude_code for
      exactly that reason. Transport contract pinned by tests/test_claude_cli_transport.py.
    - grok_cli: headless Grok CLI mode (Grok/xAI only). Uses the locally
      installed + logged-in `grok` CLI (SuperGrok or X Premium+ via `grok login --oauth`).
      No separate xAI API key. Auth and billing against the subscription.
    """
    provider: str = "grok"  # "grok", "claude", "openai" (real providers only; no mock)
    auth_method: str = "local_llm"  # must be one of SUPPORTED_AUTH_METHODS
    # api_key / token / base_url are INERT. Nothing populates them any more — no supported
    # auth method takes a caller-supplied credential or endpoint. They remain declared so
    # sessions persisted before 2026-08-04 still deserialize; their values are never used
    # (local_llm overwrites base_url with the fixed org endpoint, and the CLI modes need
    # no credential at all). Do not reintroduce a code path that reads them.
    api_key: Optional[str] = None
    token: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    # PER-TASK MODEL ROUTING (2026-09-07, token-efficiency decision 6). Same backend, a
    # different Claude model alias for the two fan-out call classes: `unit_model` drives
    # per-unit generation and per-unit Fix, `match_model` drives per-step script matching.
    # None/"" means "same as `model`". Honoured only under the two Claude CLI methods and
    # only for the three aliases the toggle offers (haiku|sonnet|opus) — this is not a new
    # backend and not a free-form model name, so the governance allowlist above is
    # unaffected. Read from the WORKSPACE row at dispatch (llm_config.cfg_for_task), never
    # from a per-case copy, because the workspace default is the single source of truth.
    unit_model: Optional[str] = None
    match_model: Optional[str] = None


# Secret fields on llm_config that must NEVER be serialized to the browser or to disk.
_LLM_SECRET_FIELDS = ("api_key", "token")


def redact_llm_config(cfg: Any) -> Any:
    """Return a copy of an llm_config dict with secret fields masked to a bool-ish marker.
    Mirrors the /llm_config `has_key` convention: callers learn whether a credential is
    present without receiving it. Accepts a dict (mutates a copy) or passes through None."""
    if not isinstance(cfg, dict):
        return cfg
    out = dict(cfg)
    for f in _LLM_SECRET_FIELDS:
        if f in out and out[f]:
            out[f] = None
            out[f + "_set"] = True
    return out


def model_to_dict(obj: Any) -> dict:
    """Plain-dict view of a pydantic model; dicts pass through as a shallow copy.

    Replaces the `obj.dict() if hasattr(obj, "dict") else obj.model_dump()` hedge that
    was copied to 19 call sites. That hedge was written for pydantic v1/v2 portability
    but is INVERTED on v2: `BaseModel.dict()` still exists there (as a deprecated alias
    for `model_dump`), so `hasattr(obj, "dict")` was always True and every one of those
    sites took the v1 path — emitting a DeprecationWarning and relying on an alias that
    pydantic removes in v3. The `else` branches were unreachable.

    ORDER IS THE WHOLE FIX. `model_dump` is tried FIRST, so a pydantic v2 model never
    reaches `.dict()`. The `.dict()` fallback is kept, because that is what the hedge was
    reaching for and a genuine pydantic v1 model has `.dict()` and NO `model_dump` — but
    it is now last-resort instead of first-choice. Removing it outright broke redaction
    for `.dict()`-only objects (caught by test_safe_session_dict_redacts_nested_llm_config).

    This is the ONLY place in the codebase allowed to call `.dict()`; call sites use this
    helper, and tests/test_pydantic_v2_and_logging.py enforces that.
    """
    dump = getattr(obj, "model_dump", None)
    if callable(dump):
        return dump()
    if isinstance(obj, dict):
        return dict(obj)
    legacy = getattr(obj, "dict", None)  # pydantic v1 model, or a .dict()-shaped object
    if callable(legacy):
        return legacy()
    return {}


def safe_session_dict(sess: Any) -> dict:
    """Serialize a WizardSession/PtSession (or dict) for return to the browser or writing
    to disk, with llm_config secrets redacted. Use this ANYWHERE a full session is exposed
    outside the server — GET /session, wizard step responses, the exported *-session.json.
    The raw api_key/token stay only in the server-side session store."""
    d = model_to_dict(sess)
    if isinstance(d.get("llm_config"), dict):
        d["llm_config"] = redact_llm_config(d["llm_config"])
    return d


class WizardSession(BaseModel):
    key: str  # AWPTCM-Txxxx
    primary: Optional[Dict] = None
    step1: StepState = StepState()  # TestLink + Decisions
    step2: StepState = StepState()  # Zephyr Cross-Ref
    step3: StepState = StepState()  # ATPyLib (scored) — user confirms selections only
    # Step 4: Objective synthesis (LLM) — user reviews/edits, then confirms before steps
    # Shape: {objective, provenance?, confirmed?, confirmed_at?}
    step4: Dict[str, Any] = {}
    # Step 5: Test-step synthesis (LLM) — uses finalized step4.objective + selections
    # Shape: {testScript: {type, steps}, provenance?}
    # Legacy sessions may still hold testScript under step4; export/UI resolve both.
    step5: Dict[str, Any] = {}
    gaps: str = ""  # LLM-generated at objective synthesis/export for Traceability (not Step 3 UI)
    art_string: str = ""
    full_session: Dict[str, Any] = {}  # For provenance
    updated_at: Optional[UtcDatetime] = None  # For tracking / persistence order
    # Monotonic write counter for the optimistic-write backstop (locks.next_rev). Rides
    # inside the payload JSON — no ck.db schema change. Optional/defaulted so sessions
    # persisted before it deserialize as rev=0. See PLAN-auth-and-case-locking.md Phase 1.
    rev: int = 0
    llm_config: LLMConfig = LLMConfig()  # Session-scoped login (Grok / Claude)

class PtSession(BaseModel):
    """PyTest Creator per-case session (see ask-ck/pytest-create/PLAN-pytest-creator.md).

    Steps 2-8 are free-form dicts each carrying confirmed/confirmed_at, mirroring
    the wizard's step4/step5 shape. Persisted as sessions/pt-{key}.json.
      step2: {sequence: [{n, action, verify, zephyr_step_idx}], provenance, confirmed}
      step3: {matches: [{id, score, coverage, reason}], selections: [id...],
              user_inputs: str, confirmed}
      step4: RETIRED (Fit Decision). Kept as a field only so legacy sessions that
             still carry a step4 dict deserialize; not produced or read anymore.
      step5: {fragments: [{source_id, symbol, loc, code, maps_to, why}], confirmed}
      step6: {naming: {group, name}, files: {test: {name, code}, library}, iterations,
              provenance, confirmed}
      step7: {profile, setup, runs: [{run_id, status, log_file, parsed, ...}], confirmed}
      step8: {validated, validated_at, run_id}
    """
    key: str  # AWPTCM-Txxxx
    group: str = ""              # refined-cases group dir (e.g. "Port (7)")
    payload: Dict[str, Any] = {}  # snapshot of zephyr_payload.json content
    traceability: str = ""        # snapshot of traceability.md
    step2: Dict[str, Any] = {}
    step3: Dict[str, Any] = {}
    step4: Dict[str, Any] = {}
    step5: Dict[str, Any] = {}
    step6: Dict[str, Any] = {}
    step7: Dict[str, Any] = {}
    step8: Dict[str, Any] = {}
    llm_config: LLMConfig = LLMConfig()
    updated_at: Optional[UtcDatetime] = None
    # Optimistic-write backstop counter; see WizardSession.rev and locks.next_rev.
    rev: int = 0


class SynthesisRequest(BaseModel):
    session: WizardSession
    use_llm: bool = True
    dry_run: bool = False  # render-only provenance preview (no LLM send, no tokens)

class ExportResponse(BaseModel):
    traceability_md: str
    zephyr_payload: Dict[str, Any]
    session_json: Dict[str, Any]
    validation: Optional[Dict[str, Any]] = None  # Added for complete repeatable output validation (priority #1)
    # Primary destination: drop-in refined-cases path written by the server (not browser Downloads)
    saved_to: Optional[str] = None
    saved_files: Optional[List[str]] = None
    message: Optional[str] = None
    # True only when the drop-in bundle (the artefact that makes a case "Complete") was
    # actually written. False when hard validation issues blocked the write — the client
    # must surface `validation.issues` and NOT treat the case as Complete.
    wrote_bundle: bool = False