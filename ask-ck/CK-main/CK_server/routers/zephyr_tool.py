"""Zephyr Templating Tool — backend (ask-ck/plans/PLAN-zephyr-templating.md).

Paired with the "Zephyr Templating Tool" sidebar section in the Ask CK UI. Tool-specific assets
live under ask-ck/functions/zephyr-tool/ (mirroring how ask-ck/functions/generator/ backs the
Objective/Test Case Generator).

Phase 0b (2026-10-05): the TEMPLATE SNAPSHOT. The template plans -> cycles -> cases Terrence
authors in Zephyr are read by `ask-ck/tools/zt_snapshot.py` (GET only) and imported into ck.db's
`zt_template_*` tables by `db.replace_zt_templates`. The server runs the tool as a subprocess, the
same way `push_to_zephyr` runs `upload_refined.py`, so the Jira token stays with the command-line
tool (`JIRA_KEY` from its environment or secrets.md) and the server never holds it.

Phases 3-4 (2026-10-05, §5a): the ANALYSIS behind the single page. `POST /analyse` starts a job and
returns its id; the page polls `GET /analyse/{id}` (one request + polling — the browser connection
ceiling). The job reads the project's wiki pages by running `ask-ck/tools/zt_wiki.py` (a live,
read-only read — the accepted exception D12), asks the seat's LLM Q1–Q4 once per template plan and
Q5 + AI Notes once per project, and keeps only what `zt_analysis` lets through. `POST
/upload/preview` runs `ask-ck/tools/zt_upload.py --dry-run` — the call list, never a write (D9).
"""

import asyncio
import json
import subprocess
import sys
import threading
import time
import uuid
from collections import OrderedDict
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

import db
import zt_analysis as za
from llm import extract_json_result, run_prompt
from llm_config import effective_llm_config
from paths import ASKCK_ROOT

router = APIRouter(tags=["zephyr-tool"])

SNAPSHOT_TOOL = ASKCK_ROOT / "tools" / "zt_snapshot.py"
SNAPSHOT_TIMEOUT_S = 180          # a full snapshot took 15 s on 2026-10-05 (14 plans, 396 cases)
_refresh_lock = threading.Lock()  # one refresh at a time: two would race on the same tables

WIKI_TOOL = ASKCK_ROOT / "tools" / "zt_wiki.py"
WIKI_TIMEOUT_S = 120              # IE520 + IE570 read in ~5 s each on 2026-10-05
UPLOAD_TOOL = ASKCK_ROOT / "tools" / "zt_upload.py"
UPLOAD_TIMEOUT_S = 120
LLM_TIMEOUT_S = 600
LLM_MAX_TOKENS = 16000
JSON_RETRIES = 1                  # a reply with no usable JSON is asked once more
PLAN_CALLS_AT_ONCE = 4            # per analysis; the seat's backend queues the rest
JOBS_KEPT = 20                    # finished analyses kept for polling, oldest dropped first


@router.get("/status")
async def status():
    """A one-line summary of the imported templates (`message`)."""
    tree = db.load_zt_templates()
    if tree is None:
        msg = "No template snapshot imported yet — refresh the templates first."
    else:
        c = tree.get("counts") or {}
        msg = (f"Templates imported {tree.get('imported_at', '')[:16].replace('T', ' ')} UTC: "
               f"{c.get('plans', 0)} plans, {c.get('cycles', 0)} cycles, {c.get('cases', 0)} cases.")
    return {"tool": "zephyr-tool", "status": "templates" if tree else "no-templates", "message": msg}


@router.get("/templates")
async def templates():
    """The imported template tree (plan -> cycle -> case), or `{"snapshot": null}` before the
    first refresh."""
    tree = db.load_zt_templates()
    return {"snapshot": tree}


def _run_snapshot() -> dict:
    proc = subprocess.run([sys.executable, str(SNAPSHOT_TOOL)], cwd=str(ASKCK_ROOT.parent),
                          capture_output=True, text=True, timeout=SNAPSHOT_TIMEOUT_S)
    if proc.returncode != 0:
        raise HTTPException(status_code=502, detail={
            "error": "the template snapshot tool failed; nothing was imported",
            "returncode": proc.returncode, "stderr": (proc.stderr or "")[-2000:]})
    try:
        return json.loads(proc.stdout)
    except ValueError as e:
        raise HTTPException(status_code=502, detail={
            "error": f"the template snapshot tool printed something that is not JSON ({e}); "
                     "nothing was imported", "stderr": (proc.stderr or "")[-2000:]})


@router.post("/templates/refresh")
async def refresh_templates(dry_run: bool = False):
    """Read the templates from Zephyr (read only) and replace the ck.db snapshot with them.
    `dry_run=true` returns what would be imported and writes nothing."""
    if not _refresh_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="a template refresh is already running")
    try:
        try:
            snap = await run_in_threadpool(_run_snapshot)
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=504,
                                detail=f"template snapshot timed out ({SNAPSHOT_TIMEOUT_S}s); nothing was imported")
        if dry_run:
            return {"dry_run": True, "counts": snap.get("counts"), "problems": snap.get("problems"),
                    "snapshot": snap}
        try:
            written = await run_in_threadpool(db.replace_zt_templates, snap)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=f"snapshot refused, previous templates kept: {e}")
        return {"dry_run": False, "written": written, "problems": snap.get("problems") or [],
                "captured_at": snap.get("captured_at")}
    finally:
        _refresh_lock.release()


# --------------------------------------------------------------------------- the analysis (Phase 3)

_jobs: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
_jobs_lock = threading.Lock()


class AnalyseRequest(BaseModel):
    url: str


def _run_tool(cmd: List[str], timeout: int, what: str, stdin: Optional[str] = None) -> dict:
    """Run one of the zt_* tools and return its JSON, or raise RuntimeError saying why not."""
    try:
        proc = subprocess.run([sys.executable] + cmd, cwd=str(ASKCK_ROOT.parent), input=stdin,
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"{what} timed out after {timeout}s")
    if proc.returncode != 0:
        raise RuntimeError(f"{what} failed: {(proc.stderr or '').strip()[-600:]}")
    try:
        return json.loads(proc.stdout)
    except ValueError as e:
        raise RuntimeError(f"{what} printed something that is not JSON ({e})")


def _public(job: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in job.items() if not k.startswith("_")}


def _ask(template: str, context: dict, llm_config: dict):
    """One model call -> (parsed JSON or None, error or None). A reply with no usable JSON is asked
    once more: on 2026-10-05 two of IE570's fourteen plan replies came back malformed (the two
    largest plans) and the page could only leave them fully ticked."""
    status = "none"
    for _ in range(1 + JSON_RETRIES):
        meta = run_prompt(template, context, llm_config=llm_config, timeout=LLM_TIMEOUT_S,
                          max_tokens=LLM_MAX_TOKENS)
        if meta.get("error"):
            return None, str(meta.get("content") or meta.get("error"))[:600]
        parsed, status = extract_json_result(meta.get("content") or "")
        if status == "ok":
            return parsed, None
    return None, f"the model's reply held no usable JSON ({status}), twice"


async def _analyse_plan(job: Dict[str, Any], plan: dict, sem: asyncio.Semaphore) -> None:
    slot = job["plans"][plan["key"]]
    async with sem:
        if job["_cancel"]:
            slot["state"] = "skipped"
            return
        slot["state"] = "running"
        try:
            reply, err = await run_in_threadpool(_ask, "zt_analyse_plan.jinja",
                                                 za.plan_context(job["_wiki"], plan), job["_llm"])
        except Exception as e:                                  # noqa: BLE001 — shown on the page
            reply, err = None, f"{type(e).__name__}: {e}"
        if err:
            slot.update(state="error", error=err)              # the plan stays fully ticked
            return
        slot.update(state="done", **za.check_plan_reply(reply, plan))


async def _analyse_gaps(job: Dict[str, Any], tree: dict, sem: asyncio.Semaphore) -> None:
    slot = job["gaps"]
    async with sem:
        if job["_cancel"]:
            slot["state"] = "skipped"
            return
        slot["state"] = "running"
        try:
            reply, err = await run_in_threadpool(_ask, "zt_gaps.jinja", za.gaps_context(job["_wiki"], tree),
                                                 job["_llm"])
        except Exception as e:                                  # noqa: BLE001
            reply, err = None, f"{type(e).__name__}: {e}"
        if err:
            slot.update(state="error", error=err)
            return
        slot.update(state="done", **za.check_gaps_reply(reply))


async def _run_job(job: Dict[str, Any], tree: dict) -> None:
    try:
        wiki = await run_in_threadpool(_run_tool, [str(WIKI_TOOL), job["url"]], WIKI_TIMEOUT_S,
                                       "reading the wiki pages")
    except Exception as e:                                      # noqa: BLE001
        job.update(state="error", error=str(e), finished=time.time())
        return
    job["_wiki"] = wiki
    tps = wiki.get("tps") or {}
    job.update(project=za.version_and_product(wiki), pages=wiki.get("pages"),
               wiki_problems=wiki.get("problems") or [],
               feature_page=(wiki.get("feature_page") or {}).get("status"),
               tps_rows={k: len(tps.get(k + "_features") or []) for k in ("sid", "prd", "tested")},
               state="analysing" if not job["_cancel"] else "cancelled")
    if job["_cancel"]:
        job["finished"] = time.time()
        return
    sem = asyncio.Semaphore(PLAN_CALLS_AT_ONCE)
    await asyncio.gather(_analyse_gaps(job, tree, sem),
                         *[_analyse_plan(job, p, sem) for p in tree.get("plans") or []])
    job.update(state="cancelled" if job["_cancel"] else "done", finished=time.time())


@router.post("/analyse")
async def analyse(req: AnalyseRequest):
    """Start an analysis of one project page; poll `GET /analyse/{id}`."""
    url = (req.url or "").strip()
    if not url:
        raise HTTPException(status_code=422, detail="paste the project's wiki page URL")
    tree = db.load_zt_templates()
    if tree is None:
        raise HTTPException(status_code=409, detail="no template snapshot imported yet — refresh the templates first")
    job: Dict[str, Any] = {
        "id": uuid.uuid4().hex[:12], "url": url, "state": "reading", "started": time.time(), "finished": None,
        "error": None, "templates_imported_at": tree.get("imported_at"), "project": None, "pages": None,
        "wiki_problems": [], "feature_page": None, "tps_rows": None,
        "plans": {p["key"]: {"state": "queued", "deselect": [], "notes": [], "dropped": [], "error": None}
                  for p in tree.get("plans") or []},
        "gaps": {"state": "queued", "gaps": [], "notes": [], "dropped": [], "error": None},
        "_cancel": False, "_llm": effective_llm_config(None), "_wiki": None,
    }
    with _jobs_lock:
        _jobs[job["id"]] = job
        while len(_jobs) > JOBS_KEPT:
            _jobs.popitem(last=False)
    job["_task"] = asyncio.create_task(_run_job(job, tree))    # copies the request's seat context
    return {"id": job["id"]}


@router.get("/analyse/{job_id}")
async def analyse_status(job_id: str):
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="no such analysis (the server may have restarted)")
    return _public(job)


@router.post("/analyse/{job_id}/cancel")
async def analyse_cancel(job_id: str):
    """Stops calls not yet started; a call already with the model finishes and is kept."""
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="no such analysis")
    job["_cancel"] = True
    return {"id": job_id, "cancelling": job["state"] in ("reading", "analysing")}


# --------------------------------------------------------------------------- API Upload, dry run (D9)

class UploadPreviewRequest(BaseModel):
    version: Optional[str] = None
    middle: Optional[str] = None
    product: Optional[str] = None
    number: Optional[str] = None
    plans: List[Dict[str, Any]]


@router.post("/upload/preview")
async def upload_preview(req: UploadPreviewRequest):
    """The exact calls an upload would make for this selection. Writes nothing (D9)."""
    if not req.plans:
        raise HTTPException(status_code=422, detail="nothing is selected")
    try:
        return await run_in_threadpool(_run_tool, [str(UPLOAD_TOOL), "--dry-run"], UPLOAD_TIMEOUT_S,
                                       "the upload preview", json.dumps(req.model_dump()))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
