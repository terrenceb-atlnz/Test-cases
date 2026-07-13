"""Test Composer — backend stub.

Paired with the "Test Composer" sidebar section in the Ask CK UI.
Tool-specific assets will live under ask-ck/test-composer/.
"""

from fastapi import APIRouter

router = APIRouter(tags=["test-composer"])


@router.get("/status")
async def status():
    return {
        "tool": "test-composer",
        "status": "stub",
        "message": "Test Composer backend not implemented yet.",
    }
