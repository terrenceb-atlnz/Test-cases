"""Browser <-> server bridge for the per-user Claude agent.

The user's browser tab long-polls /next for prompt jobs the server queued for its
session, runs each on the user's own machine (ck-agent), and POSTs the result to
/result. This is the transport that lets a shared Ask CK server use each user's own
local Claude seat. See ask-ck/CK-main/PLAN-per-user-agent.md.
"""
import asyncio

from fastapi import APIRouter, Body, HTTPException, Header, Request

from agent_jobs import registry

router = APIRouter(tags=["agent-bridge"])


# Browser session ids are short generated tokens; anything longer is not a real tab.
_MAX_SESSION_ID_LEN = 128


def _resolve_session(header_session: str, param_session: str) -> str:
    """Prefer the per-tab X-CK-Session header (set by the browser's fetch wrapper) as
    the authoritative session identity; fall back to an explicit param only when the
    header is absent. This binds job claim/deliver to the requesting tab's own session
    instead of an arbitrary caller-supplied value (adversarial-review finding).

    The value is still client-supplied and becomes a dict key in the job registry, so
    cap its length — an unbounded header would let a caller pin arbitrarily large keys
    in memory between gc runs."""
    value = (header_session or param_session or "").strip()
    return value[:_MAX_SESSION_ID_LEN]


@router.get("/next")
async def next_job(session: str = "", wait: float = 25.0,
                   x_ck_session: str = Header(default="")):
    """Long-poll: return the next queued prompt job for this browser session.

    Blocks up to `wait` seconds for a job to appear (so the browser doesn't hammer
    the server), then returns {job: null} if still empty. The session identity is the
    per-tab X-CK-Session header (authoritative); the `session` query param is a
    legacy fallback only.
    """
    session = _resolve_session(x_ck_session, session)
    if not session:
        raise HTTPException(400, "session required")
    deadline = asyncio.get_event_loop().time() + max(0.0, min(wait, 55.0))
    while True:
        job = registry.next_job(session)
        if job:
            job_id, prompt, model = job
            return {"job": {"job_id": job_id, "prompt": prompt, "model": model}}
        if asyncio.get_event_loop().time() >= deadline:
            return {"job": None}
        await asyncio.sleep(0.4)


@router.post("/result")
async def deliver_result(body: dict = Body(...), x_ck_session: str = Header(default="")):
    """Browser posts a completion (or error) back for a claimed job.

    The delivering session must OWN the job: `deliver` rejects a job_id that belongs to a
    different X-CK-Session, so a caller can't post a result for another session's in-flight
    job by guessing its id (adversarial-review finding). When no session header is present
    (legacy client), delivery falls back to job_id-only behavior.
    """
    job_id = body.get("job_id")
    if not job_id:
        raise HTTPException(400, "job_id required")
    session = (x_ck_session or "").strip() or None
    ok = registry.deliver(job_id, body.get("content", ""), bool(body.get("error", False)),
                          body.get("usage"), body.get("total_cost_usd"), session_id=session)
    if not ok:
        # Job already timed out server-side, unknown id, or NOT owned by this session.
        return {"delivered": False, "reason": "job not awaiting (timed out, unknown, or not yours)"}
    return {"delivered": True}


@router.get("/status")
async def status(session: str = ""):
    """Lightweight status for the Configure panel."""
    return {
        "tool": "agent-bridge",
        "session_active": registry.session_active(session) if session else False,
        "pending": registry.pending_count(session) if session else 0,
    }
