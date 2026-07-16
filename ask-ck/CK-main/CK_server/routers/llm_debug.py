"""Read-only endpoints for LLM-request observability (debug footer + log viewer).

Debug info is served from separate GET endpoints rather than embedded in the
wizard/pytest responses, so it works uniformly for success AND failure paths
(pytest endpoints raise 502 before any response body exists; wizard endpoints
return 200-with-provenance). See ask-ck/ck-facelift/PLAN-llm-observability.md.
"""
import json

from fastapi import APIRouter, Request

import llm_debug

router = APIRouter(tags=["llm-debug"])

# Truncation cap for /recent payloads; the FULL text lives in the JSONL log
# (readable via /log or debug-log/<session>.jsonl on disk).
_TRUNC = 20_000


def _truncated(rec: dict) -> dict:
    out = dict(rec)
    for k in ("prompt", "response"):
        v = out.get(k)
        if isinstance(v, str) and len(v) > _TRUNC:
            out[k] = v[:_TRUNC] + f"\n… [truncated {len(v) - _TRUNC} chars — full text in debug-log/]"
    return out


@router.get("/recent")
async def recent(request: Request, limit: int = 20):
    """Last-K in-memory records for the caller's X-CK-Session (oldest→newest).

    Last-K rather than last-1 so the frontend can pick the newest record for
    ITS panel even when concurrent calls interleave within one session.
    """
    session_id = request.headers.get("X-CK-Session", "")
    return {"records": [_truncated(r) for r in llm_debug.recent(session_id, limit=limit)]}


@router.get("/log")
async def session_log(request: Request):
    """The caller's full per-session JSONL log — viewable without shell access.

    Missing file (no LLM calls yet this session) returns {"records": []}.
    """
    session_id = request.headers.get("X-CK-Session", "")
    path = llm_debug.session_log_path(session_id or "no-session")
    if not path.exists():
        return {"records": []}
    records = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass  # skip a torn/corrupt line rather than failing the view
    except Exception:
        pass
    return {"records": records}
