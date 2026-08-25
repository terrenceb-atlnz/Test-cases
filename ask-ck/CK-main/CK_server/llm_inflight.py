"""In-flight LLM call registry: live progress + true server-side cancellation.

Why (2026-08-26, Terrence): every LLM button showed a spinner but gave no sense
of progress and no way out — a wrong click on Generate meant waiting minutes for
tokens nobody wanted. "Stop" here is REAL: it kills the CLI process group /
closes the vLLM stream / abandons the agent job, so the spend stops and nothing
persists. A UI-only abort (browser stops waiting, server finishes and persists
anyway) was explicitly rejected as dishonest.

Mechanics: the browser generates an id per LLM call and sends it as the
`X-CK-LLM-Call` header; middleware binds it to a ContextVar; `_call_llm_with_meta`
registers the call here (dry-runs never register — nothing is sent); each
transport attaches a cancel handle and, where it streams, progress counters.
`GET /api/llm/inflight/{id}` serves the live snapshot the busy button polls;
`POST /api/llm/cancel/{id}` fires the handle.

In-memory and single-process — same authority model as `locks.py` (see the
multi-worker caveat there). A registry entry is small and always removed in the
`finally` of the one caller, but `register` also garbage-collects anything older
than _MAX_AGE_S as a leak backstop. Never raises into the LLM path.
"""
import threading
import time
from typing import Any, Callable, Dict, Optional

_LOCK = threading.Lock()
_CALLS: Dict[str, Dict[str, Any]] = {}
_MAX_AGE_S = 2 * 3600   # leak backstop only; finish() is the real cleanup


def register(call_id: str, template: str = "", auth_method: str = "") -> None:
    if not call_id:
        return
    now = time.monotonic()
    with _LOCK:
        for k in [k for k, v in _CALLS.items() if now - v["started"] > _MAX_AGE_S]:
            _CALLS.pop(k, None)
        _CALLS[call_id] = {"started": now, "template": template,
                           "auth_method": auth_method, "chars": 0, "events": 0,
                           "cancel": None, "cancelled": False}


def set_cancel(call_id: str, fn: Optional[Callable[[], None]]) -> None:
    """Attach the transport's cancel handle. If cancel() already fired before the
    handle existed (a race the CLI path can hit between register and Popen), fire
    it immediately so the click is never lost."""
    if not call_id:
        return
    fire = False
    with _LOCK:
        c = _CALLS.get(call_id)
        if not c:
            return
        c["cancel"] = fn
        fire = c["cancelled"] and fn is not None
    if fire:
        try:
            fn()
        except Exception:
            pass


def add_progress(call_id: str, chars: int = 0, events: int = 0) -> None:
    if not call_id:
        return
    with _LOCK:
        c = _CALLS.get(call_id)
        if c:
            c["chars"] += chars
            c["events"] += events


def is_cancelled(call_id: str) -> bool:
    if not call_id:
        return False
    with _LOCK:
        c = _CALLS.get(call_id)
        return bool(c and c["cancelled"])


def cancel(call_id: str) -> bool:
    """Mark cancelled and fire the transport handle. True if the call was live."""
    with _LOCK:
        c = _CALLS.get(call_id)
        if not c:
            return False
        c["cancelled"] = True
        fn = c["cancel"]
    if fn is not None:
        try:
            fn()
        except Exception:
            pass
    return True


def finish(call_id: str) -> None:
    if not call_id:
        return
    with _LOCK:
        _CALLS.pop(call_id, None)


def snapshot(call_id: str) -> Optional[Dict[str, Any]]:
    with _LOCK:
        c = _CALLS.get(call_id)
        if not c:
            return None
        return {"elapsed_ms": int((time.monotonic() - c["started"]) * 1000),
                "chars": c["chars"], "events": c["events"],
                "template": c["template"], "auth_method": c["auth_method"],
                "cancelled": c["cancelled"]}
