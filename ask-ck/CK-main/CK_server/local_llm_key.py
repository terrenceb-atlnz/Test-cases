"""Storage for the Local LLM (org vLLM) API key.

The key is resolved SERVER-SIDE only: set from the Configure page (persisted to
the gitignored secrets.local.json next to this file), with the LOCAL_LLM_KEY
env var as a headless/CI fallback. It must never enter a session config, an
HTTP response, or the debug-log — llm.py injects it at request time via
get_local_llm_key() when auth_method == "local_llm".

Deliberately NOT the human-authored repo-root secrets.md (that file stays
user-owned; the server never reads or writes it). Future central/multi-seat
deploy: flip the Configure field to browser localStorage + per-request key,
and whitelist that field OUT of the debug-log recorder.
"""
import json
import os
from typing import Optional

from paths import LOCAL_LLM_SECRETS


def get_local_llm_key() -> Optional[str]:
    """File first (Configure-page managed), env var fallback. None when unset."""
    try:
        if LOCAL_LLM_SECRETS.exists():
            key = (json.loads(LOCAL_LLM_SECRETS.read_text()) or {}).get("local_llm_key")
            if key:
                return key
    except Exception:
        pass  # unreadable/corrupt file -> fall back to env
    return os.environ.get("LOCAL_LLM_KEY") or None


def set_local_llm_key(key: str) -> None:
    """Persist a (re-)entered key from the Configure page (keys expire)."""
    LOCAL_LLM_SECRETS.write_text(json.dumps({"local_llm_key": key}))
