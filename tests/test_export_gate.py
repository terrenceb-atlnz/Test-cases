"""Endpoint tests for the export hardening (backlog: output-generation hardening).

The drop-in bundle (refined-cases/**/zephyr_payload.json) is exactly what marks a case
"Complete". Two layers stop a bad bundle from silently promoting a case:

  1. The AUTHORITY + CONFIRM gate (adversarial-review batch A, 2026-07-27g) — export
     resolves the session server-side only (404 if absent, never the client's copy) and
     requires all three DB reviews confirmed (400 otherwise).
  2. The VALIDATION gate — a session that passes (1) but produces a payload failing hard
     validation is refused with wrote_bundle=False + the issues.

These drive the real route in-process (no mocks). They use a throwaway key that has no
refined-cases entry, so a correct run writes nothing to disk.
"""
import pathlib

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
_REFINED = _REPO_ROOT / "ask-ck" / "objective-drafting" / "refined-cases"
_THROWAWAY_KEY = "AWPTCM-T99990"


def _refined_paths_for(key):
    if not _REFINED.exists():
        return []
    return list(_REFINED.glob(f"*/{key}/*"))


@pytest.fixture
def confirmed_session():
    """Register a server-side session with all three DB reviews confirmed.

    Needed because export no longer accepts a client-supplied session — reaching the
    VALIDATION gate now requires getting past the AUTHORITY + CONFIRM gate first.
    Yields the key; removes the session afterwards so no state leaks between tests.
    """
    from routers.wizard import sessions
    from session_store import clear_persisted
    from models import WizardSession

    sess = WizardSession(key=_THROWAWAY_KEY)
    for step in (sess.step1, sess.step2, sess.step3):
        step.confirmed = True
    # Pre-set gaps so export skips its generate_coverage_gaps() LLM round-trip —
    # these tests must stay offline.
    sess.gaps = "(test fixture — gaps pre-set to avoid an LLM call)"
    sessions[_THROWAWAY_KEY] = sess
    try:
        yield _THROWAWAY_KEY
    finally:
        # Clear BOTH layers — the endpoint persists to ck.db, so an in-memory-only
        # pop leaves a throwaway row in the permanent source of truth and leaks
        # session state into later tests.
        sessions.pop(_THROWAWAY_KEY, None)
        clear_persisted(_THROWAWAY_KEY)


def test_invalid_payload_is_blocked_and_writes_nothing(client, confirmed_session):
    # Precondition: nothing on disk for the throwaway key.
    assert not _refined_paths_for(_THROWAWAY_KEY), "test key already has refined-cases artefacts"

    # Reviews confirmed but no objective/steps -> passes the confirm gate, fails validation.
    r = client.post("/api/wizard/export", json={"session": {"key": _THROWAWAY_KEY}})
    assert r.status_code == 200
    d = r.json()

    # The gate must fire: nothing written, and the reason surfaced.
    assert d["wrote_bundle"] is False
    assert d["saved_to"] is None
    assert (d.get("validation") or {}).get("valid") is False
    assert (d.get("validation") or {}).get("issues"), "expected validation issues to be reported"
    msg = (d.get("message") or "").lower()
    assert "blocked" in msg
    # No prior bundle on disk for this throwaway key, so the message must say NOT Complete
    # (the stale-bundle-aware branch must pick the correct arm — adversarial-review finding A).
    assert "not marked complete" in msg, msg
    assert "still on disk" not in msg, "wrongly claimed a stale bundle exists"

    # Filesystem invariant: the refusal actually prevented a write.
    assert not _refined_paths_for(_THROWAWAY_KEY), "blocked export still wrote to disk"


def test_response_shape_has_wrote_bundle_field(client, confirmed_session):
    """Regression guard: the wrote_bundle field must exist so the UI can trust it."""
    r = client.post("/api/wizard/export", json={"session": {"key": _THROWAWAY_KEY}})
    assert "wrote_bundle" in r.json()
