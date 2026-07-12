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

class StepState(BaseModel):
    confirmed: bool = False
    confirmed_at: Optional[datetime] = None
    none_selected: bool = False
    selections: List[Selection] = []

class LLMConfig(BaseModel):
    """Per-session LLM login config.

    - api_key: classic developer key (HTTP calls against the provider's API)
    - claude_code: headless Claude Code CLI mode (Claude only). Uses the locally
      installed + logged-in `claude` CLI, so a Claude Team subscription seat is
      used directly — no key/token is entered or stored by this server.
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
    step4: Dict[str, Any] = {}        # Drafted objective + steps (after LLM or manual)
    gaps: str = ""  # LLM-generated at synthesis/export for Traceability (not Step 3 UI)
    art_string: str = ""
    full_session: Dict[str, Any] = {}  # For provenance
    updated_at: Optional[datetime] = None  # For tracking / persistence order
    llm_config: LLMConfig = LLMConfig()  # Session-scoped login (Grok / Claude)

class SynthesisRequest(BaseModel):
    session: WizardSession
    use_llm: bool = True

class ExportResponse(BaseModel):
    traceability_md: str
    zephyr_payload: Dict[str, Any]
    session_json: Dict[str, Any]
    validation: Optional[Dict[str, Any]] = None  # Added for complete repeatable output validation (priority #1)