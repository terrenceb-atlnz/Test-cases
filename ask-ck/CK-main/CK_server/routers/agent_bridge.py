"""Browser <-> server bridge for the per-user Claude agent.

The user's browser tab long-polls /next for prompt jobs the server queued for its
session, runs each on the user's own machine (ck-agent), and POSTs the result to
/result. This is the transport that lets a shared Ask CK server use each user's own
local Claude seat. See ask-ck/CK-main/PLAN-per-user-agent.md.
"""
import asyncio

from fastapi import APIRouter, Body, HTTPException

from agent_jobs import registry

router = APIRouter(tags=["agent-bridge"])


@router.get("/next")
async def next_job(session: str, wait: float = 25.0):
    """Long-poll: return the next queued prompt job for this browser session.

    Blocks up to `wait` seconds for a job to appear (so the browser doesn't hammer
    the server), then returns {job: null} if still empty. The session id is minted
    per browser tab client-side and identifies whose agent should run the job.
    """
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
async def deliver_result(body: dict = Body(...)):
    """Browser posts a completion (or error) back for a claimed job."""
    job_id = body.get("job_id")
    if not job_id:
        raise HTTPException(400, "job_id required")
    ok = registry.deliver(job_id, body.get("content", ""), bool(body.get("error", False)),
                          body.get("usage"), body.get("total_cost_usd"))
    if not ok:
        # Job already timed out server-side, or unknown id — not fatal to the browser.
        return {"delivered": False, "reason": "job not awaiting (timed out or unknown)"}
    return {"delivered": True}


@router.get("/status")
async def status(session: str = ""):
    """Lightweight status for the Configure panel."""
    return {
        "tool": "agent-bridge",
        "session_active": registry.session_active(session) if session else False,
        "pending": registry.pending_count(session) if session else 0,
    }
