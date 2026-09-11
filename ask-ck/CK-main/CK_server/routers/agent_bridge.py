"""Browser <-> server bridge for the per-user Claude agent.

The user's browser tab long-polls /next for prompt jobs the server queued for its
session, runs each on the user's own machine (ck-agent), and POSTs the result to
/result. This is the transport that lets a shared Ask CK server use each user's own
local Claude seat. See archive/plans/PLAN-per-user-agent.md.
"""
import asyncio
import hashlib
import re

from fastapi import APIRouter, Body, HTTPException, Header, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from agent_jobs import registry
from paths import ASKCK_ROOT

router = APIRouter(tags=["agent-bridge"])

# ---------------------------------------------------------------------------
# Served seat setup — `/setup/...` (mounted from main.py)
#
# The seat side of the same transport: a Windows or Ubuntu seat has NO copy of this repo,
# only the URL. So the server serves the two setup scripts and the two agents straight
# from `ask-ck/agent/` (the single source of truth — no `dist/` copies to drift), plus a
# manifest of sha256 hashes the setup scripts use to decide whether to re-download and
# whether a running agent is stale. Allowlisted names only; README, __pycache__ and
# anything else in that folder are never served. The server's own origin is templated
# into the setup scripts at serve time (`__CK_SERVER__`) so the one-liner needs no
# argument and the same file works if the host moves. Design:
# ask-ck/ck-facelift/PLAN-seat-setup-and-per-seat-llm.md §3.
# ---------------------------------------------------------------------------
setup_router = APIRouter(tags=["seat-setup"])

AGENT_DIR = ASKCK_ROOT / "agent"
SETUP_FILES = {
    "setup.ps1": "text/plain; charset=utf-8",
    "setup.sh": "text/plain; charset=utf-8",
    "ck-agent.ps1": "text/plain; charset=utf-8",
    "ck_agent.py": "text/plain; charset=utf-8",
}
_TEMPLATED = ("setup.ps1", "setup.sh")
_PLACEHOLDER = "__CK_SERVER__"
_VERSION_RE = re.compile(r'^AGENT_VERSION\s*=\s*"([^"]+)"', re.M)


def agent_version() -> str:
    """The version both agents declare (a gate test pins them equal)."""
    m = _VERSION_RE.search((AGENT_DIR / "ck_agent.py").read_text(encoding="utf-8"))
    return m.group(1) if m else "unknown"


def _server_origin(request: Request) -> str:
    # Behind nginx the Host header is the public one; without a proxy it is what the
    # browser typed. Either way it is the origin the seat can actually reach us on.
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
    scheme = request.headers.get("x-forwarded-proto") or request.url.scheme or "http"
    return f"{scheme}://{host}".rstrip("/") if host else str(request.base_url).rstrip("/")


def _file_bytes(name: str, origin: str = "") -> bytes:
    data = (AGENT_DIR / name).read_bytes()
    if name in _TEMPLATED and origin:
        data = data.replace(_PLACEHOLDER.encode(), origin.encode())
    return data


@setup_router.get("/manifest.json")
async def setup_manifest(request: Request):
    """agent_version + sha256 of every served file. The AGENT files are hashed as served
    (they carry no template), so a seat can verify a download byte for byte; the setup
    scripts are hashed AFTER templating for this origin."""
    origin = _server_origin(request)
    files = {name: hashlib.sha256(_file_bytes(name, origin)).hexdigest() for name in SETUP_FILES}
    return JSONResponse({"agent_version": agent_version(), "server": origin, "files": files,
                         "one_liners": {
                             "windows": f"irm {origin}/setup/setup.ps1 | iex",
                             "ubuntu": f"curl -fsSL {origin}/setup/setup.sh | bash"}})


@setup_router.get("/{name}")
async def setup_file(name: str, request: Request):
    if name not in SETUP_FILES:
        raise HTTPException(status_code=404, detail="not a served setup file")
    body = _file_bytes(name, _server_origin(request))
    return PlainTextResponse(content=body, media_type=SETUP_FILES[name],
                            headers={"Cache-Control": "no-cache",
                                     "Content-Disposition": f'inline; filename="{name}"'})


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
            job_id, prompt, model, job_timeout, system = job
            # `timeout` is the budget THIS server is waiting on. The browser passes it
            # straight to its ck-agent so both ends stop at the same moment; before this
            # it hard-coded 600s of its own and could outlive the server's patience,
            # finishing work whose job had already been discarded.
            # `system` is the steer the agent passes as the CLI's --system-prompt
            # (2026-09-04) — see llm._DEFAULT_CLI_SYSTEM_PROMPT for why it must replace
            # the harness prompt rather than append to it.
            return {"job": {"job_id": job_id, "prompt": prompt, "model": model,
                            "timeout": job_timeout, "system": system}}
        if asyncio.get_event_loop().time() >= deadline:
            return {"job": None}
        await asyncio.sleep(0.4)


@router.get("/job_wanted/{job_id}")
async def job_wanted(job_id: str):
    """Does a caller still want this job's result?

    Polled by the browser WHILE it runs a job, so a cancelled or timed-out job can be
    abandoned immediately instead of blocking the broker loop for the rest of its budget
    (see AgentJobRegistry.is_wanted). Deliberately unauthenticated and session-free like
    the rest of this bridge, and it leaks nothing: a boolean about an opaque job id the
    caller must already possess.
    """
    return {"wanted": registry.is_wanted(job_id)}


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
