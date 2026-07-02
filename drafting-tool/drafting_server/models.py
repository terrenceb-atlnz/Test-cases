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
    """Per-session LLM login config. Supports both API Key and Account Logins for Grok and Claude."""
    provider: str = "mock"  # "grok", "claude", "openai", "mock"
    auth_method: str = "api_key"  # "api_key" or "account"
    api_key: Optional[str] = None      # Direct API key
    token: Optional[str] = None        # Token from account login (OAuth/session/etc.)
    base_url: Optional[str] = None
    model: Optional[str] = None

class WizardSession(BaseModel):
    key: str  # AWPTCM-Txxxx
    primary: Optional[Dict] = None
    step1: StepState = StepState()  # TestLink + Decisions
    step2: StepState = StepState()  # Zephyr Cross-Ref
    step3: StepState = StepState()  # ATPyLib + Gaps
    step4: Dict[str, Any] = {}        # Drafted objective + steps (after LLM or manual)
    gaps: str = ""
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