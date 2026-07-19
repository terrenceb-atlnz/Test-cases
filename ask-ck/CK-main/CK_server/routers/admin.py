"""Admin panel endpoints (hidden UI behind double-clicking CK's face).

Local single-user convenience — reset session state, rebuild search vectors,
rebuild the whole DB, and restart the server, without dropping to a terminal.
The heavy rebuilds run as background subprocesses (tool/build_db.py) with a
tiny in-memory job tracker polled by the panel. "Restart" works by touching a
watched .py file so uvicorn's --reload picks it up (no supervisor needed).

SAFETY: these actions are powerful (DB rebuild, process restart). This is
intended for a local, single-user instance bound to localhost. Do NOT expose
this router on a shared/public deployment without adding auth.
"""
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

import db
from paths import ASKCK_ROOT, DB_PATH

router = APIRouter(tags=["admin"])

REPO_ROOT = ASKCK_ROOT.parent
BUILD_DB = REPO_ROOT / "tool" / "build_db.py"

# --- tiny background-job tracker -----------------------------------------------
# One job at a time for the heavy rebuilds; the panel polls /admin/job.
_lock = threading.Lock()
_job: Dict[str, Any] = {"name": None, "state": "idle", "started": None,
                        "finished": None, "returncode": None, "tail": ""}


def _run_job(name: str, args: list) -> None:
    """Run tool/build_db.py <args> in a thread, capturing a short output tail."""
    with _lock:
        _job.update({"name": name, "state": "running", "started": time.time(),
                     "finished": None, "returncode": None, "tail": ""})
    try:
        proc = subprocess.run(
            ["python3", str(BUILD_DB), *args],
            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=3600,
        )
        tail = ((proc.stdout or "") + (proc.stderr or ""))[-4000:]
        with _lock:
            _job.update({"state": "done" if proc.returncode == 0 else "failed",
                         "finished": time.time(), "returncode": proc.returncode,
                         "tail": tail})
    except Exception as e:
        with _lock:
            _job.update({"state": "failed", "finished": time.time(),
                         "returncode": -1, "tail": f"{type(e).__name__}: {e}"})


def _start_job(name: str, args: list) -> bool:
    """Start a job unless one is already running. True if started."""
    with _lock:
        if _job["state"] == "running":
            return False
    threading.Thread(target=_run_job, args=(name, args), daemon=True).start()
    return True


@router.get("/status")
async def status():
    """Panel header: DB readiness + current job state."""
    try:
        chk = db.startup_check()
    except Exception as e:
        chk = {"ok": False, "error": str(e)}
    with _lock:
        job = dict(_job)
    return {"tool": "admin", "db": chk, "job": job, "db_path": str(DB_PATH)}


@router.get("/job")
async def job_status():
    """Poll target for the panel while a rebuild runs."""
    with _lock:
        return dict(_job)


@router.post("/reset-session")
async def reset_session(body: dict):
    """Clear session state without touching the process or DB.

    body: {"scope": "case"|"workspace"|"all", "key": "<case key, for scope=case>"}
    """
    scope = (body.get("scope") or "case").lower()
    cleared = []
    try:
        if scope in ("case", "all"):
            key = body.get("key")
            if scope == "case" and not key:
                raise HTTPException(400, "scope=case needs a case key")
            if key:
                db.delete_session("wizard", key)
                db.delete_session("pytest", key)
                cleared.append(f"session:{key}")
        if scope in ("workspace", "all"):
            db.delete_session("wizard", "_workspace_llm")
            cleared.append("workspace_llm")
        if scope == "all":
            # Wipe every wizard/pytest session row (leaves corpora untouched).
            for kind in ("wizard", "pytest"):
                for k in list((db.list_session_progress() or {}).keys()):
                    db.delete_session(kind, k)
            cleared.append("all_sessions")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"reset failed: {e}")
    return {"ok": True, "cleared": cleared, "scope": scope}


@router.post("/rebuild-embeddings")
async def rebuild_embeddings():
    """Background: tool/build_db.py --embed (semantic search vectors)."""
    if not _start_job("rebuild-embeddings", ["--embed"]):
        raise HTTPException(409, "A rebuild job is already running.")
    return {"ok": True, "started": "rebuild-embeddings"}


@router.post("/rebuild-db")
async def rebuild_db(body: Optional[dict] = None):
    """Background: full DB re-ingest. tool/build_db.py --fresh --verify --sessions
    (sessions re-imported so a fresh rebuild doesn't lose them); optional --embed.
    """
    body = body or {}
    args = ["--fresh", "--verify", "--sessions"]
    if body.get("embed"):
        args.append("--embed")
    if not _start_job("rebuild-db", args):
        raise HTTPException(409, "A rebuild job is already running.")
    return {"ok": True, "started": "rebuild-db", "args": args}


@router.post("/restart")
async def restart():
    """Trigger a uvicorn --reload restart by touching a watched .py file.

    The dev server runs with --reload; bumping a source file's mtime makes it
    reload the app in-process. The browser reconnects after ~2s. If the server
    is NOT running under --reload, this is a harmless no-op (nothing reloads).
    """
    try:
        # Touch this very module — it's inside the reload watch tree.
        Path(__file__).touch()
    except Exception as e:
        raise HTTPException(500, f"could not trigger reload: {e}")
    return {"ok": True, "restarting": True,
            "note": "Server reloading (if running under --reload). Reconnecting…"}
