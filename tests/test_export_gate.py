"""Endpoint tests for the export hardening (backlog: output-generation hardening).

The drop-in bundle (refined-cases/**/zephyr_payload.json) is exactly what marks a case
"Complete". The hardening makes /api/wizard/export REFUSE to write that bundle when the
payload fails hard validation, and report wrote_bundle=False + the issues — so a broken
bundle can never silently promote a case to Complete.

These drive the real route in-process (no mocks). They use a throwaway key that has no
refined-cases entry, so a correct run writes nothing to disk.
"""
import pathlib

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
_REFINED = _REPO_ROOT / "ask-ck" / "objective-drafting" / "refined-cases"
_THROWAWAY_KEY = "AWPTCM-T99990"


def _refined_paths_for(key):
    if not _REFINED.exists():
        return []
    return list(_REFINED.glob(f"*/{key}/*"))


def test_invalid_payload_is_blocked_and_writes_nothing(client):
    # Precondition: nothing on disk for the throwaway key.
    assert not _refined_paths_for(_THROWAWAY_KEY), "test key already has refined-cases artefacts"

    # A session with just a key produces an empty/invalid payload (no objective, no steps).
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


def test_response_shape_has_wrote_bundle_field(client):
    """Regression guard: the wrote_bundle field must exist so the UI can trust it."""
    r = client.post("/api/wizard/export", json={"session": {"key": _THROWAWAY_KEY}})
    assert "wrote_bundle" in r.json()
