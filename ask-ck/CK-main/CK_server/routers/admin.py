"""Admin panel endpoints (hidden UI behind double-clicking CK's face).

Local single-user convenience — reset session state and restart the server,
without dropping to a terminal. "Restart" works by touching a watched .py file
so uvicorn's --reload picks it up (no supervisor needed).

DB REBUILD IS DELIBERATELY ABSENT. ck.db is the permanent single source of truth,
built once from the provided data; the courier/source files it was built from have
been retired, so there is no rebuild path (and nothing may wipe/refill the DB from
the UI). Sessions and the server process are the only mutable things here.

SAFETY: these actions (process restart, session reset) are intended for a local,
single-user instance bound to localhost. Do NOT expose this router on a
shared/public deployment without adding auth.
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException

import db
from paths import DB_PATH

router = APIRouter(tags=["admin"])


@router.get("/status")
async def status():
    """Panel header: DB readiness."""
    try:
        chk = db.startup_check()
    except Exception as e:
        chk = {"ok": False, "error": str(e)}
    return {"tool": "admin", "db": chk, "db_path": str(DB_PATH)}


@router.post("/reset-session")
async def reset_session(body: dict):
    """Clear session state without touching the process or DB corpora.

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
                db.delete_session("pt", key)   # PT sessions use kind "pt" (see db._session_id), not "pytest"
                cleared.append(f"session:{key}")
        if scope in ("workspace", "all"):
            db.delete_session("wizard", "_workspace_llm")
            cleared.append("workspace_llm")
        if scope == "all":
            # Wipe every wizard AND pytest session row (leaves corpora untouched).
            # Wizard and PT sessions live under different kinds ("wizard" vs "pt") and
            # different progress maps — the old code iterated only the wizard map with
            # kind "pytest", so it deleted nothing on the PT side and mis-kinded the
            # wizard side. Enumerate each from its own map with its own kind.
            for k in list((db.list_session_progress() or {}).keys()):
                db.delete_session("wizard", k)
            for k in list((db.list_pt_progress() or {}).keys()):
                db.delete_session("pt", k)
            cleared.append("all_sessions")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"reset failed: {e}")
    return {"ok": True, "cleared": cleared, "scope": scope}


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
