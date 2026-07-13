"""Zephyr Templating Tool — backend stub.

Paired with the "Zephyr Templating Tool" sidebar section in the Ask CK UI.
Tool-specific assets will live under ask-ck/zephyr-tool/ (mirroring how
ask-ck/objective-drafting/ backs the Objective/Test Case Generator).
"""

from fastapi import APIRouter

router = APIRouter(tags=["zephyr-tool"])


@router.get("/status")
async def status():
    return {
        "tool": "zephyr-tool",
        "status": "stub",
        "message": "Zephyr Templating Tool backend not implemented yet.",
    }
