"""Per-request LLM telemetry: token-usage normalization + per-session request log.

Every LLM transport funnels through llm._call_llm_with_meta, which calls
record() here after each request (success OR failure). Records go to:
  1) an in-memory per-session ring buffer, served by GET /api/llm/recent, and
  2) DEBUG_LOG_DIR/<session>.jsonl (one line per request; FULL prompt/response).

Telemetry must never break an LLM call: every public function traps its own
errors and degrades to None / no-op.

SECURITY: record() builds each record from an explicit WHITELIST of meta keys
(_META_WHITELIST). Credentials (api_key / token / llm_config) are never in that
list and must never be added. The Local LLM key never enters meta at all — it
is resolved server-side in llm.py (see local_llm_key.py).

Log growth: full prompts can run 10-50 KB (generate_script embeds source
fragments); a heavy session reaches a few MB of JSONL. Acceptable for a debug
aid; rotation is deliberately out of scope. The record schema is kept flat and
columnar so the pending SQLite migration (PLAN-db-migration.md) can absorb it
as a table later — do not nest it further.
"""
import json
import re
import threading
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from paths import DEBUG_LOG_DIR


# --- token-usage normalization -------------------------------------------------

def normalize_usage(auth_method: str, raw_response: Any) -> Optional[Dict[str, Any]]:
    """Map a transport's raw response to {input_tokens, output_tokens, total_tokens, cost_usd}.

    Shapes handled:
    - Anthropic HTTP + Claude Code CLI JSON envelope: usage.input_tokens/output_tokens
      (cache_read/creation_input_tokens folded into input; total_cost_usd -> cost_usd).
    - OpenAI-compatible (Grok HTTP, org vLLM local_llm): usage.prompt_tokens/
      completion_tokens/total_tokens.
    - Agent bridge: tolerant probe of raw["usage"] (either shape) when the
      out-of-repo ck-agent starts reporting it.

    Returns None when the transport doesn't report usage (grok CLI plain text,
    agent bridge without usage) — callers must show that honestly ("— tok"),
    never estimate. Future: investigate `grok --output-format json` for usage.
    """
    try:
        if not isinstance(raw_response, dict):
            return None
        usage = raw_response.get("usage")
        if not isinstance(usage, dict):
            return None
        # Anthropic / Claude Code CLI shape
        if "input_tokens" in usage or "output_tokens" in usage:
            inp = int(usage.get("input_tokens") or 0)
            # Cache reads/creation are still input the provider processed, so they stay
            # folded into input_tokens (every consumer of that number is unchanged) — and
            # since 2026-09-07 they are ALSO kept apart. Folding alone hid the fact that
            # the T44297 pass read zero tokens from cache on every call; that had to be
            # inferred from the price (decision 8). With the split, "did it cache?" is a
            # field, not a calculation.
            cache_read = int(usage.get("cache_read_input_tokens") or 0)
            cache_write = int(usage.get("cache_creation_input_tokens") or 0)
            inp += cache_read + cache_write
            out = int(usage.get("output_tokens") or 0)
            cost = raw_response.get("total_cost_usd")
            return {
                "input_tokens": inp,
                "output_tokens": out,
                "total_tokens": inp + out,
                "cost_usd": float(cost) if cost is not None else None,
                "cache_read_input_tokens": cache_read,
                "cache_creation_input_tokens": cache_write,
            }
        # OpenAI-compatible shape
        if "prompt_tokens" in usage or "completion_tokens" in usage:
            inp = int(usage.get("prompt_tokens") or 0)
            out = int(usage.get("completion_tokens") or 0)
            total = int(usage.get("total_tokens") or (inp + out))
            return {"input_tokens": inp, "output_tokens": out,
                    "total_tokens": total, "cost_usd": None}
        return None
    except Exception:
        return None


# --- per-session ring buffer + JSONL log ----------------------------------------

_lock = threading.Lock()
_recent: Dict[str, deque] = {}   # session_id -> deque of records (newest last)
_MAX_RECORDS_PER_SESSION = 20
_MAX_SESSIONS = 50

# meta keys copied into a record. Credentials (api_key / token / llm_config)
# are deliberately NOT listed and must never be added.
_META_WHITELIST = ("template", "provider", "auth_method", "model", "base_url",
                   "prompt", "system", "error", "error_detail", "usage")


def session_log_path(session_id: str) -> Path:
    """Filesystem-safe per-session JSONL path under DEBUG_LOG_DIR."""
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", session_id or "")[:80] or "no-session"
    return DEBUG_LOG_DIR / f"{safe}.jsonl"


def record(meta: Dict[str, Any], duration_ms: int) -> Optional[Dict[str, Any]]:
    """Build a debug record from whitelisted meta, append it to the session's
    JSONL file, and push it into the in-memory ring buffer. Never raises."""
    try:
        import llm as _llm  # late import: llm imports this module (avoid cycle)
        session_id = _llm.current_session_id.get("") or "no-session"

        rec: Dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "request_id": uuid.uuid4().hex[:12],
            "session_id": session_id,
            "panel": _llm.current_panel_id.get(""),
            "endpoint": _llm.current_request_path.get(""),
            "duration_ms": int(duration_ms),
        }
        for k in _META_WHITELIST:
            rec[k] = meta.get(k)
        rec["error"] = bool(rec.get("error"))
        rec["response"] = meta.get("content")               # full text (or error message)
        rec["content_chars"] = len(meta.get("content") or "")

        # 1) JSONL append — per-session file, O_APPEND single-line writes.
        try:
            DEBUG_LOG_DIR.mkdir(parents=True, exist_ok=True)
            with open(session_log_path(session_id), "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
        except Exception as e:
            print(f"[llm_debug] JSONL append failed: {e}")

        # 2) in-memory ring buffer for /api/llm/recent.
        with _lock:
            dq = _recent.get(session_id)
            if dq is None:
                if len(_recent) >= _MAX_SESSIONS:
                    # dicts preserve insertion order -> first key is oldest session
                    _recent.pop(next(iter(_recent)), None)
                dq = _recent[session_id] = deque(maxlen=_MAX_RECORDS_PER_SESSION)
            dq.append(rec)
        return rec
    except Exception as e:
        print(f"[llm_debug] record failed: {e}")
        return None


def recent(session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """This session's in-memory records, oldest→newest, capped at `limit`."""
    try:
        with _lock:
            dq = _recent.get(session_id or "no-session")
            items = list(dq or ())
        n = max(1, min(int(limit or 20), _MAX_RECORDS_PER_SESSION))
        return items[-n:]
    except Exception:
        return []
