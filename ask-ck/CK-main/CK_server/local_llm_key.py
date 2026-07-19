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
import stat
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
    """Persist a (re-)entered key from the Configure page (keys expire).

    Written 0600 (owner-only) so the credential isn't world-readable by other
    local accounts on a shared host. Permissions are set before the key is
    written by opening with a restrictive mode via os.open.
    """
    fd = os.open(str(LOCAL_LLM_SECRETS), os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
                 stat.S_IRUSR | stat.S_IWUSR)  # 0600
    try:
        with os.fdopen(fd, "w") as f:
            f.write(json.dumps({"local_llm_key": key}))
    except Exception:
        os.close(fd)  # only if fdopen itself failed; otherwise the with closed it
        raise
    # Re-assert mode in case the file pre-existed with looser perms.
    try:
        os.chmod(str(LOCAL_LLM_SECRETS), stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass
