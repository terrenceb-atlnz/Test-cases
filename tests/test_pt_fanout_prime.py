"""The unit fan-out is PRIMED: one call alone, then the rest together (decision 4, 2026-09-07).

A prompt-cache entry is readable only after the request that wrote it has been processed.
Eight units fired at once therefore all write the shared system half and none reads it —
with decision 8 (shared half as the system prompt) that is the last wave of full-price input
in a pass. Pinned: the first item completes before any other starts; the rest DO overlap
(this must not degrade into a sequential loop); the endpoint still returns without waiting;
and the response names the primed unit so the UI can explain the pause.
"""
import asyncio
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SERVER = _REPO / "ask-ck" / "CK-main" / "CK_server"
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(_SERVER))

from routers import pytest_create as pc  # noqa: E402

_SRC = (_SERVER / "routers" / "pytest_create.py").read_text(encoding="utf-8")
_CODE = re.sub(r'#[^\n]*', '', re.sub(r'"""[\s\S]*?"""', '', _SRC))
BATCH = _CODE[_CODE.index('@router.post("/generate_units/'):_CODE.index('@router.get("/units_status/')]


def _drive(n_items: int):
    events = []

    async def run(uid, dt):
        events.append(("start", uid))
        await asyncio.sleep(dt)
        events.append(("end", uid))

    async def main():
        items = [(f"u{i}", 0.01) for i in range(n_items)]
        t = asyncio.create_task(pc._dispatch_primed(items, run))
        await t
        # let the fanned-out tasks finish
        await asyncio.sleep(0.05)
    asyncio.run(main())
    return events


def test_the_first_unit_finishes_before_any_other_starts():
    ev = _drive(5)
    assert ev[0] == ("start", "u0") and ev[1] == ("end", "u0")
    assert all(uid != "u0" for kind, uid in ev[2:])


def test_the_rest_overlap_rather_than_running_one_by_one():
    ev = _drive(5)
    rest = ev[2:]
    starts = [i for i, (k, _) in enumerate(rest) if k == "start"]
    ends = [i for i, (k, _) in enumerate(rest) if k == "end"]
    # every one of the four starts before any of them ends
    assert max(starts) < min(ends), rest


def test_a_single_unit_just_runs():
    assert _drive(1) == [("start", "u0"), ("end", "u0")]


def test_nothing_to_dispatch_is_a_no_op():
    asyncio.run(pc._dispatch_primed([], lambda *a: None))


def test_the_endpoint_uses_the_primed_dispatcher_and_still_returns_immediately():
    assert "asyncio.create_task(_dispatch_primed(prepared, _one))" in BATCH
    assert "await _dispatch_primed" not in BATCH, "awaiting it is the six-connection deadlock again"
    assert '"primed":' in BATCH
