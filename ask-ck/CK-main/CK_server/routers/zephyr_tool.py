"""Zephyr Templating Tool — backend (ask-ck/plans/PLAN-zephyr-templating.md).

Paired with the "Zephyr Templating Tool" sidebar section in the Ask CK UI. Tool-specific assets
live under ask-ck/functions/zephyr-tool/ (mirroring how ask-ck/functions/generator/ backs the
Objective/Test Case Generator).

Phase 0b (2026-10-05): the TEMPLATE SNAPSHOT. The template plans -> cycles -> cases Terrence
authors in Zephyr are read by `ask-ck/tools/zt_snapshot.py` (GET only) and imported into ck.db's
`zt_template_*` tables by `db.replace_zt_templates`. The server runs the tool as a subprocess, the
same way `push_to_zephyr` runs `upload_refined.py`, so the Jira token stays with the command-line
tool (`JIRA_KEY` from its environment or secrets.md) and the server never holds it.
"""

import json
import subprocess
import sys
import threading

from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

import db
from paths import ASKCK_ROOT

router = APIRouter(tags=["zephyr-tool"])

SNAPSHOT_TOOL = ASKCK_ROOT / "tools" / "zt_snapshot.py"
SNAPSHOT_TIMEOUT_S = 180          # a full snapshot took 15 s on 2026-10-05 (14 plans, 396 cases)
_refresh_lock = threading.Lock()  # one refresh at a time: two would race on the same tables


@router.get("/status")
async def status():
    """The Info panel shows `message` (shared/main.js loadToolStatus)."""
    tree = db.load_zt_templates()
    if tree is None:
        msg = "No template snapshot imported yet. The rest of the tool is not built yet."
    else:
        c = tree.get("counts") or {}
        msg = (f"Templates imported {tree.get('imported_at', '')[:16]}: {c.get('plans', 0)} plans, "
               f"{c.get('cycles', 0)} cycles, {c.get('cases', 0)} cases. "
               f"The rest of the tool is not built yet.")
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
