"""Test Composer + Validation — the server half (ask-ck/plans/PLAN-agent-sessions.md P1,
PLAN-test-validation.md, PLAN-test-composer.md).

The seat runs the session (D7: the page hands the hand-off to the seat's ck-agent, which runs
/test-mode under the seat's own login); THIS router owns the run record: it builds and stores the
hand-off, takes the events the page relays, folds them into results, mails notices (D5) and the
finish, serves the campaign's device-testing logs read-only, re-grades, and runs Feedback.
Records are files (tc_runs.py); nothing here touches ck.db's schema.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import FileResponse

import tc_campaign
import tc_finalize
import tc_mail
import tc_projects
import tc_runs
from llm_config import effective_llm_config

router = APIRouter(tags=["test-composer"])


def _seat(request: Request) -> str:
    return (request.headers.get("X-CK-Seat") or (request.client.host if request.client else "") or "?")[:80]


def _link(request: Request, run_id: str) -> str:
    base = str(request.base_url).rstrip("/")
    return f"{base}/?panel=tc-runs&run={run_id}"


def _bad(e: Exception, code: int = 422):
    raise HTTPException(status_code=code, detail=str(e))


@router.get("/status")
async def status():
    # dt_root: the device-testing checkout this server reads campaign logs from. A seat agent
    # runs its session there when the seat can see that path (ck_agent.session_dt_root).
    return {"tool": "test-composer", "status": "ok",
            "message": "Validation and Test Composer: runs launch on your seat's ck-agent (PLAN-agent-sessions).",
            "dt_root": str(tc_campaign.dt_root())}


# ------------------------------------------------------------------ inputs

@router.get("/scripts")
async def scripts():
    return {"scripts": tc_runs.list_scripts()}


@router.get("/templates")
async def templates(plans: str = ""):
    return {"templates": tc_projects.templates_with_counts([p for p in plans.split(",") if p])}


@router.get("/requirements")
async def requirements():
    return tc_projects.requirements_aggregate()


@router.get("/projects")
async def projects():
    return {"projects": tc_projects.templated_projects()}


@router.post("/projects/from-wiki")
async def project_from_wiki(body: Dict[str, Any] = Body(...)):
    url = str(body.get("url") or "").strip()
    if not url:
        _bad("paste the project's wiki page URL")
    try:
        return await asyncio.to_thread(tc_projects.from_wiki, url)
    except tc_projects.ProjectError as e:
        _bad(e)


@router.get("/projects/tree")
async def project_tree(plans: str):
    keys = [p for p in plans.split(",") if p]
    if not keys:
        _bad("name at least one plan")
    try:
        return await asyncio.to_thread(tc_projects.live_tree, keys)
    except tc_projects.ProjectError as e:
        _bad(e, 502)


# ------------------------------------------------------------------ runs

@router.post("/runs")
async def create_run(request: Request, body: Dict[str, Any] = Body(...)):
    """Build and store the hand-off. The PAGE then hands it to its own seat agent."""
    try:
        return tc_runs.create_run(body, _seat(request))
    except tc_runs.RunError as e:
        _bad(e)


@router.get("/runs")
async def runs(kind: Optional[str] = None, limit: int = 50):
    return {"runs": tc_runs.list_runs(limit=min(max(limit, 1), 200), kind=kind)}


@router.get("/scheduled")
async def scheduled(request: Request):
    """The seat agent's poll (D3): this seat's scheduled runs that are due now."""
    return {"due": tc_runs.due_runs(_seat(request))}


@router.post("/runs/{run_id}/claim")
async def claim(request: Request, run_id: str):
    """The seat agent claims a due run once and gets its hand-off to start."""
    try:
        return {"handoff": tc_runs.claim(run_id, _seat(request))}
    except tc_runs.RunError as e:
        raise HTTPException(status_code=409, detail=str(e)) from None
    except KeyError:
        raise HTTPException(status_code=404, detail="no such run") from None


@router.get("/runs/{run_id}")
async def run(run_id: str):
    try:
        r = tc_runs.load(run_id)
    except (KeyError, tc_runs.RunError):
        raise HTTPException(status_code=404, detail="no such run") from None
    return {"record": r, "handoff": tc_runs.load_handoff(run_id), "table": tc_runs.results_table(r),
            "counts": tc_runs.verdict_counts(r)}


@router.get("/runs/{run_id}/events")
async def run_events(run_id: str, after: int = -1):
    try:
        tc_runs.load(run_id)
    except (KeyError, tc_runs.RunError):
        raise HTTPException(status_code=404, detail="no such run") from None
    return {"events": tc_runs.read_events(run_id, after)}


@router.post("/runs/{run_id}/events")
async def relay_events(request: Request, run_id: str, body: Dict[str, Any] = Body(...)):
    """The page relays the seat session's events here (idempotent by seq)."""
    events = body.get("events") or []
    if not isinstance(events, list):
        _bad("events must be a list")
    try:
        out = tc_runs.apply_events(run_id, events[:2000], session_id=body.get("session_id"))
    except (KeyError, tc_runs.RunError):
        raise HTTPException(status_code=404, detail="no such run") from None
    record = out["record"]
    to = [e for e in str((tc_runs.load_handoff(run_id).get("options") or {}).get("email") or "").split(",") if e.strip()]
    mailed = []
    if to:
        if out["new_notices"]:
            subject, text = tc_mail.notice_mail(record, out["new_notices"], _link(request, run_id))
            mailed.append({"what": f"{len(out['new_notices'])} notice(s)", "error": await asyncio.to_thread(tc_mail.send, to, subject, text)})
        if out["finished"]:
            subject, text = tc_mail.finish_mail(record, tc_runs.table_counts(record), _link(request, run_id))
            mailed.append({"what": "finished", "error": await asyncio.to_thread(tc_mail.send, to, subject, text)})
        if mailed:
            record = tc_runs.mark(run_id, mailed=(record.get("mailed") or []) + mailed)
    return {"ok": True, "state": record["state"], "last_seq": record["last_seq"], "mailed": mailed}


@router.post("/runs/{run_id}/regrade")
async def regrade(request: Request, run_id: str, body: Dict[str, Any] = Body(...)):
    try:
        r = tc_runs.regrade(run_id, str(body.get("case") or ""), str(body.get("verdict") or ""),
                            str(body.get("note") or ""), _seat(request))
    except tc_runs.RunError as e:
        _bad(e)
    except KeyError:
        raise HTTPException(status_code=404, detail="no such run") from None
    return {"ok": True, "table": tc_runs.results_table(r)}


@router.post("/runs/{run_id}/accept")
async def accept(request: Request, run_id: str):
    """Accept results. Deleting the campaign's work/ folders is device-testing's to do (the write
    boundary): this records the acceptance; the seat's next session (or the peer) acts on it."""
    try:
        r = tc_runs.mark(run_id, accepted_by=_seat(request), accepted_at=tc_runs._now().isoformat(timespec="seconds"))
    except (KeyError, tc_runs.RunError):
        raise HTTPException(status_code=404, detail="no such run") from None
    return {"ok": True, "record": r, "note": "work/ folders are kept until device-testing acts on the acceptance"}


# ------------------------------------------------------------------ the campaign's logs (read-only)

@router.get("/runs/{run_id}/campaign")
async def campaign(run_id: str):
    return await asyncio.to_thread(tc_campaign.campaign, run_id)


@router.get("/runs/{run_id}/file")
async def campaign_file(run_id: str, path: str, before: Optional[int] = None):
    try:
        return await asyncio.to_thread(tc_campaign.read_chunk, run_id, path, before)
    except FileNotFoundError as e:
        _bad(e, 404)
    except PermissionError as e:
        _bad(e, 403)


@router.get("/runs/{run_id}/download")
async def campaign_download(run_id: str, path: str):
    try:
        p = tc_campaign.file_path(run_id, path)
    except FileNotFoundError as e:
        _bad(e, 404)
    except PermissionError as e:
        _bad(e, 403)
    return FileResponse(p, filename=p.name, media_type="text/plain")


# ------------------------------------------------------------------ Validation: a repaired copy

@router.get("/runs/{run_id}/repaired")
async def repaired(run_id: str, path: str, case: str):
    """The repaired COPY device-testing reported (`REPAIRED <case> <path>`), beside the saved original,
    for the page to compare before approving. Approval itself goes through the PyTest Creator's own
    save (POST /api/pytest-create/save_script/{key}), so the units⇄script binding reports the edit."""
    try:
        p = tc_campaign.file_path(run_id, path)
        r = tc_runs.load(run_id)
    except FileNotFoundError as e:
        _bad(e, 404)
    except PermissionError as e:
        _bad(e, 403)
    except (KeyError, tc_runs.RunError):
        raise HTTPException(status_code=404, detail="no such run") from None
    original = next((c.get("script") for c in r.get("cases") or [] if c["key"] == case), None)
    if not original:
        _bad(f"{case} is not a script case of this run")
    return {"case": case, "path": path, "code": p.read_text(encoding="utf-8", errors="replace"),
            "original": open(original, encoding="utf-8").read()}


# ------------------------------------------------------------------ Validation: Finalize

@router.post("/runs/{run_id}/finalize/{case}")
async def finalize(request: Request, run_id: str, case: str):
    """PLAN-test-validation §6. Refuses (409) with the reason until every precondition holds; while
    V0 is open (the Zephyr new-version request is not captured) it always refuses before writing."""
    try:
        r = tc_runs.load(run_id)
        events = tc_runs.read_events(run_id)
    except (KeyError, tc_runs.RunError):
        raise HTTPException(status_code=404, detail="no such run") from None
    c = next((x for x in r.get("cases") or [] if x["key"] == case and x["kind"] == "script"), None)
    if not c:
        _bad(f"{case} is not a script case of this run")
    blockers = []
    if r.get("state") != "done":
        blockers.append("the run has not finished cleanly")
    lines = [e.get("line") or "" for e in events if e.get("kind") == "marker"]
    if not any(ln.startswith(f"REVIEWED {case}") for ln in lines):
        blockers.append("the review has not been written (REVIEWED)")
    if blockers:
        raise HTTPException(status_code=409, detail="; ".join(blockers))
    script_rel = str(Path(c["script"]).resolve().relative_to(tc_runs.generated_dir().resolve()))
    link = f"{str(request.base_url).rstrip('/')}/?panel=composer&script={script_rel}"
    try:
        out = await asyncio.to_thread(tc_finalize.finalize, case, script_rel, run_id, _seat(request),
                                      tc_runs.generated_dir(), link, get_case=None, put_case=None,
                                      new_version=None, audit=lambda e: True)
    except tc_finalize.FinalizeBlocked as e:
        raise HTTPException(status_code=409, detail=str(e)) from None
    return out


# ------------------------------------------------------------------ Feedback

FEEDBACK_SYSTEM = ("You are reviewing one automated AlliedWare Plus test-case run for the Test Engineer. "
                   "Be concrete and brief. The framework's verdict stands — do not re-grade it; analyse it.")


def feedback_prompt(run_id: str, case: str) -> str:
    r = tc_runs.load(run_id)
    row = next((x for x in tc_runs.results_table(r) if x["case"] == case), None)
    if not row:
        raise tc_runs.RunError(f"{case} is not in this run")
    script = next((c.get("script") for c in r.get("cases") or [] if c["key"] == case), None)
    script_text = ""
    if script:
        try:
            script_text = open(script, encoding="utf-8").read()[:60000]
        except OSError:
            script_text = "(script not readable)"
    log = ""
    camp = tc_campaign.campaign(run_id)
    if camp["found"]:
        logs = [f["path"] for f in camp["files"] if f.get("case") and case.endswith(str(f["case"]).split("-")[-1])]
        if logs:
            log = tc_campaign.read_chunk(run_id, sorted(logs)[-1])["data"][-40000:]
    return ("Give feedback on this run: root cause of any failure or error, whether the script tested what "
            "the case asks for, script improvements, and anything else worth knowing ('by the ways').\n\n"
            f"Case: {case}\nVerdict: {row['verdict']} — {row['reason']}\n\n"
            f"--- script ---\n{script_text}\n\n--- log tail ---\n{log or '(no log found)'}\n")


@router.post("/runs/{run_id}/feedback/{case}")
async def feedback(run_id: str, case: str):
    from llm import run_prompt_text  # noqa: PLC0415 — heavy import, only when used
    try:
        prompt = await asyncio.to_thread(feedback_prompt, run_id, case)
    except tc_runs.RunError as e:
        _bad(e)
    except KeyError:
        raise HTTPException(status_code=404, detail="no such run") from None
    cfg = effective_llm_config(None)
    meta = await asyncio.to_thread(run_prompt_text, prompt, llm_config=cfg, timeout=900,
                                   system=FEEDBACK_SYSTEM, template="(tc-feedback)")
    text = meta.get("content") or ""
    error = meta.get("error")
    fb = {"case": case, "text": text, "error": error, "at": tc_runs._now().isoformat(timespec="seconds")}
    r = tc_runs.load(run_id)
    tc_runs.mark(run_id, feedback={**(r.get("feedback") or {}), case: fb})
    return fb
