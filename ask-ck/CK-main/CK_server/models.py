"""
Pydantic models for the server-backed drafting tool.
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

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
    confirmed_at: Optional[datetime] = None
    none_selected: bool = False
    selections: List[Selection] = []

class LLMConfig(BaseModel):
    """Per-session LLM login config.

    - api_key: classic developer key (HTTP calls against the provider's API)
    - claude_agent: browser-brokered Claude Code CLI on the USER's own machine
      (Claude only). For a shared server: each user runs ck-agent locally and their
      prompts execute against THEIR OWN seat — seats are never shared. The current
      UI-selectable Claude mode.
    - claude_code: headless Claude Code CLI on the SERVER host (Claude only). Uses the
      server machine's own `claude` login — single-user hosting only. Retained for
      back-compat; not offered in the UI (shared use would pool one seat).
    - grok_cli: headless Grok CLI mode (Grok/xAI only). Uses the locally
      installed + logged-in `grok` CLI (SuperGrok or X Premium+ via `grok login --oauth`).
      No separate xAI API key. Auth and billing against the subscription.
    - account: legacy value from the old (non-functional) "paste a session token"
      flow; still accepted for old session files and treated like api_key.
    """
    provider: str = "grok"  # "grok", "claude", "openai" (real providers only; no mock)
    auth_method: str = "api_key"  # "api_key", "claude_code", "grok_cli", or legacy "account"
    api_key: Optional[str] = None      # Direct API key
    token: Optional[str] = None        # Legacy token field (account mode)
    base_url: Optional[str] = None
    model: Optional[str] = None

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
    updated_at: Optional[datetime] = None  # For tracking / persistence order
    llm_config: LLMConfig = LLMConfig()  # Session-scoped login (Grok / Claude)

class PtSession(BaseModel):
    """PyTest Creator per-case session (see ask-ck/pytest-create/PLAN-pytest-creator.md).

    Steps 2-8 are free-form dicts each carrying confirmed/confirmed_at, mirroring
    the wizard's step4/step5 shape. Persisted as sessions/pt-{key}.json.
      step2: {sequence: [{n, action, verify, zephyr_step_idx}], provenance, confirmed}
      step3: {matches: [{id, score, coverage, reason}], selections: [id...],
              user_inputs: str, confirmed}
      step4: {decision: reuse|extend|new, base_script, per_step: [...], confirmed}
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
    updated_at: Optional[datetime] = None


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