"""Per-case lock endpoints (PLAN-auth-and-case-locking.md Phase 1).

The frontend acquires a lock on case load, heartbeats it on a timer (and for the whole
duration of a testbox run), and releases it on tab close. All state lives in the
in-process `locks` registry — this router is a thin HTTP surface over it.

The holder is normally the per-tab `X-CK-Session` id (read from the ContextVar inside
`locks`). `acquire`/`heartbeat`/`release` also accept an explicit `holder` in the body:
`navigator.sendBeacon` (the release-on-unload transport) CANNOT set request headers, so
the beacon carries the id in its JSON body. This is a correctness/UX mechanism, not a
security control — the id is a correlation id, not a credential (plan §1.1).
"""

from fastapi import APIRouter, Body, HTTPException

import locks

router = APIRouter()


def _check_kind(kind: str) -> None:
    if kind not in locks.VALID_KINDS:
        raise HTTPException(400, f"Unknown lock kind {kind!r} (expected {'|'.join(locks.VALID_KINDS)}).")


@router.post("/{kind}/{case_key}/acquire")
async def acquire(kind: str, case_key: str, body: dict = Body(default={})):
    _check_kind(kind)
    b = body or {}
    return locks.acquire(kind, case_key, holder=b.get("holder") or None, label=b.get("label") or None)


@router.post("/{kind}/{case_key}/heartbeat")
async def heartbeat(kind: str, case_key: str, body: dict = Body(default={})):
    _check_kind(kind)
    return locks.heartbeat(kind, case_key, holder=(body or {}).get("holder") or None)


@router.post("/{kind}/{case_key}/release")
async def release(kind: str, case_key: str, body: dict = Body(default={})):
    _check_kind(kind)
    return locks.release(kind, case_key, holder=(body or {}).get("holder") or None)


@router.get("/{kind}/{case_key}")
async def state(kind: str, case_key: str):
    _check_kind(kind)
    return locks.peek(kind, case_key)
