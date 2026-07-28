"""In-memory per-case locking for the Generator wizard and the PyTest Creator.

WHY THIS EXISTS
---------------
Sessions are keyed by case only and every persist is an unconditional whole-blob
overwrite (`db._write_session`). So two people — or one person in two browser tabs —
who open the same case both read, both edit, both save, and the SECOND write silently
wins: the first person's work is gone, no error, no trace. It is a read-modify-write
across SEPARATE requests, which no event-loop serialisation prevents. See
`ask-ck/ck-facelift/PLAN-auth-and-case-locking.md` §1.2 — this is Phase 1.

The lock is held per (tool, case). The holder identity is the per-tab `X-CK-Session`
id (`llm.current_session_id`); Phase 2 upgrades that to a real user with no change here.
The `X-CK-Session` id is a correlation id, NOT a credential (§1.1 of the plan) — this
module is a data-loss guard, not a security boundary, so it accepts an explicit holder
from a caller where the transport cannot carry the header (see `navigator.sendBeacon`
release, which cannot set request headers).

SINGLE-PROCESS ASSUMPTION — READ THIS BEFORE ADDING WORKERS
-----------------------------------------------------------
The registry is an in-process dict. It is authoritative ONLY because the server runs as
ONE process today (`uvicorn CK_server.main:app … --reload`, no `--workers`; the nginx
example proxies a single upstream). ck.db is immutable by design — `tool/build_db.py`
refuses to rebuild and there is no migration path — so a durable `case_locks` table was
deliberately NOT added; that would be the repo's first in-place schema mutation of the
permanent DB. If the server is ever run multi-worker / multi-process, THIS registry
stops being shared and the overwrite bug returns silently: promote it to a shared store.
The `rev` optimistic-write backstop (`next_rev`, applied in the two persist helpers)
already covers the transient two-process window that `pytest_create._pt_get` documents.
"""

import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional

from timeutil import utc_now

log = logging.getLogger(__name__)

# D4: a lock whose heartbeat is older than this is idle and may be taken over (D5).
LOCK_IDLE_TTL = 15 * 60  # seconds

VALID_KINDS = ("wizard", "pt")


class LockError(RuntimeError):
    """Base for a session write refused to protect another editor's work. `main.py`
    registers ONE app-wide handler turning any LockError into HTTP 409, so no call site
    needs to remember (mirrors the `session_store.SessionWriteError` pattern). A DOMAIN
    error, not an HTTPException, so this leaf stays framework-free and unit-testable."""


class LockConflictError(LockError):
    """Another holder owns a live lock on this case."""

    def __init__(self, kind: str, case_key: str, holder_label: str, acquired_at: str):
        self.kind = kind
        self.case_key = case_key
        self.holder_label = holder_label
        self.acquired_at = acquired_at
        super().__init__(
            f"'{case_key}' is open in the {_tool_name(kind)} under {holder_label} "
            f"(since {acquired_at or 'earlier'}). Your changes were NOT saved — the case "
            f"is locked so it cannot be overwritten. Wait for them to finish, or take over "
            f"once the lock goes idle.")


class StaleWriteError(LockError):
    """The persisted row advanced since this copy loaded (rev CAS mismatch) — a stale
    in-memory copy (post-restart, or a second server process) tried to overwrite newer
    work. See `pytest_create._pt_get` for the two-process window this closes."""

    def __init__(self, kind: str, case_key: str):
        self.kind = kind
        self.case_key = case_key
        super().__init__(
            f"'{case_key}' was changed by another editor since you loaded it, so your "
            f"write was refused to avoid overwriting their work. Reload the case to get "
            f"the latest, then re-apply your change.")


def _tool_name(kind: str) -> str:
    return "PyTest Creator" if kind == "pt" else "Generator"


@dataclass
class _Lock:
    holder: str
    holder_label: str
    acquired_at: datetime
    heartbeat_at: datetime


_LOCKS: Dict[str, _Lock] = {}
_MUTEX = threading.Lock()   # paramiko run-threads + run_in_threadpool both touch _LOCKS


def _key(kind: str, case_key: str) -> str:
    return f"{kind}:{case_key}"


def current_holder() -> str:
    """The requesting tab's `X-CK-Session` id, from the per-request ContextVar.

    Imported lazily so this leaf does not depend on the (heavier) `llm` module at import
    time and stays trivially unit-testable. Returns '' outside a request (tool scripts,
    or unit tests that pass `holder=` explicitly) — treated as an anonymous holder.
    """
    try:
        import llm
        return llm.current_session_id.get() or ""
    except Exception:
        return ""


def _short(holder: str) -> str:
    return f"session {holder[:8]}" if holder else "another session"


def _expired(lk: _Lock, now: datetime) -> bool:
    return (now - lk.heartbeat_at) > timedelta(seconds=LOCK_IDLE_TTL)


def _state(lk: Optional[_Lock], viewer: str, now: datetime, *, acquired: bool = False) -> dict:
    """The lock's view relative to `viewer`. `by_me` is true only when the viewer owns a
    LIVE lock (a lock that is mine is never reported expired — I just heartbeated it)."""
    if lk is None:
        return {"held": False, "by_me": False, "holder": "", "holder_label": "",
                "acquired_at": None, "heartbeat_at": None, "expired": False,
                "stealable": False, "acquired": acquired}
    exp = _expired(lk, now)
    return {
        "held": True,
        "by_me": (lk.holder == viewer) and not exp,
        "holder": lk.holder,
        "holder_label": lk.holder_label,
        "acquired_at": lk.acquired_at.isoformat(),
        "heartbeat_at": lk.heartbeat_at.isoformat(),
        "expired": exp,
        "stealable": exp and lk.holder != viewer,
        "acquired": acquired,
    }


def acquire(kind: str, case_key: str, holder: Optional[str] = None,
            label: Optional[str] = None) -> dict:
    """Grant the lock to `holder` when the case is free, the current lock is idle/expired
    (an idle takeover — D5), or the holder already owns it (a refresh). Otherwise return
    the current state WITHOUT granting (`by_me=False`). Idempotent for the same holder:
    `acquired_at` is preserved on refresh so the "held since" banner stays stable."""
    holder = current_holder() if holder is None else holder
    with _MUTEX:
        now = utc_now()
        k = _key(kind, case_key)
        lk = _LOCKS.get(k)
        mine = lk is not None and lk.holder == holder
        if lk is None or mine or _expired(lk, now):
            stolen = lk is not None and not mine and _expired(lk, now)
            _LOCKS[k] = _Lock(
                holder=holder,
                holder_label=(label or _short(holder)),
                acquired_at=(lk.acquired_at if mine else now),
                heartbeat_at=now)
            if stolen:
                log.info("lock %s: %s took over an idle lock previously held by %s",
                         k, holder, lk.holder)
            return _state(_LOCKS[k], holder, now, acquired=True)
        return _state(lk, holder, now, acquired=False)


def heartbeat(kind: str, case_key: str, holder: Optional[str] = None) -> dict:
    """Refresh the idle timer if `holder` owns the lock; otherwise a no-op returning the
    current state. Long PyTest testbox runs heartbeat for their whole duration (plan §6)."""
    holder = current_holder() if holder is None else holder
    with _MUTEX:
        now = utc_now()
        lk = _LOCKS.get(_key(kind, case_key))
        if lk is not None and lk.holder == holder:
            lk.heartbeat_at = now
        return _state(_LOCKS.get(_key(kind, case_key)), holder, now)


def release(kind: str, case_key: str, holder: Optional[str] = None) -> dict:
    """Drop the lock iff `holder` owns it. A release from a prior/other holder is ignored,
    so a late `sendBeacon` from a stale tab cannot free a lock someone else now holds."""
    holder = current_holder() if holder is None else holder
    with _MUTEX:
        now = utc_now()
        k = _key(kind, case_key)
        lk = _LOCKS.get(k)
        if lk is not None and lk.holder == holder:
            del _LOCKS[k]
            return {"released": True, **_state(None, holder, now)}
        return {"released": False, **_state(lk, holder, now)}


def peek(kind: str, case_key: str, holder: Optional[str] = None) -> dict:
    """Current lock state relative to the calling holder, without mutating anything."""
    holder = current_holder() if holder is None else holder
    with _MUTEX:
        return _state(_LOCKS.get(_key(kind, case_key)), holder, utc_now())


def require_can_write(kind: str, case_key: str, holder: Optional[str] = None) -> None:
    """Raise LockConflictError iff a LIVE lock is held by someone other than `holder`.

    No lock, an idle/expired (abandoned) lock, or the holder's own lock all pass — so a
    load-case hydration write, the very first save, and a tool script (empty registry)
    are never blocked; only a live write by a NON-holder is. This one rule is the whole
    guard, enforced at the two persist choke points, not at 32 call sites."""
    holder = current_holder() if holder is None else holder
    with _MUTEX:
        now = utc_now()
        lk = _LOCKS.get(_key(kind, case_key))
        if lk is None or lk.holder == holder or _expired(lk, now):
            return
        raise LockConflictError(kind, case_key, lk.holder_label, lk.acquired_at.isoformat())


def next_rev(kind: str, case_key: str, in_memory_rev: int) -> int:
    """Optimistic compare-and-swap for the session payload `rev`.

    Returns the rev to write (`in_memory_rev + 1`) when the persisted rev still matches
    what the caller loaded; raises StaleWriteError when another writer advanced it since.
    This is the belt-and-braces the in-memory lock cannot provide: it stops a stale copy
    (post-restart, or a second process — see `pytest_create._pt_get`) from overwriting
    newer work even if a lock was bypassed or force-stolen mid-edit. A first-ever write
    (no row) and a legacy row with no `rev` both read as 0, so this is backward-compatible.
    """
    import db
    try:
        row = db.load_session(kind, case_key)
    except Exception:
        # A read failure here must NOT masquerade as a stale-write conflict; let the write
        # proceed and surface any genuine DB error from the write path instead.
        return int(in_memory_rev) + 1
    persisted = int((row or {}).get("rev", 0) or 0)
    if persisted != int(in_memory_rev):
        raise StaleWriteError(kind, case_key)
    return int(in_memory_rev) + 1


def _reset() -> None:
    """Test hook: drop all locks so a test starts from a clean registry."""
    with _MUTEX:
        _LOCKS.clear()
