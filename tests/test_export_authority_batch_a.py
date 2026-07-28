"""Regression tests for adversarial-review batch A (2026-07-27g) — export authority.

Four findings, one theme: the bundle that MARKS A CASE COMPLETE
(refined-cases/**/zephyr_payload.json) could be written from state that never
authorized it.

  1. wizard.py:1939 — export fell back to the client-supplied req.session when the key
     was absent server-side, so a stale browser tab could resurrect a deleted session.
  2. wizard.py:1936 — export had no _can_synthesize gate, so a hand-pasted objective +
     steps could be exported as Complete with zero DB reviews confirmed.
  3. wizard.py:1381 — confirm_step never invalidated step4/step5, so re-confirming an
     upstream review with DIFFERENT selections left a bundle whose payload (old
     generation) contradicted its own traceability.md (new selections).
  4. wizard.py:2166 — the Complete marker was written before the largest, most
     failure-prone write, so a mid-loop I/O error left a case Complete + push-eligible
     while the API reported wrote_bundle=False.

Plus the migration guard: _backfill_from_refined must satisfy the new confirm gate, or
the 43 existing on-disk bundles would 400 on re-export for reviews already done.

All in-process — no network, no testbox, no writes outside a tmp_path.
"""
import json
import pathlib

import pytest

from models import WizardSession, Selection
from routers.wizard import (
    _backfill_from_refined,
    _can_synthesize,
    _clear_persisted,
    _invalidate_downstream,
    _selection_fingerprint,
    sessions,
)

_THROWAWAY_KEY = "AWPTCM-T99991"


def _redirect_refined_dir(monkeypatch, tmp_path):
    """Point EVERY reader of refined-cases/ at tmp_path, not just wizard's.

    `from paths import REFINED_DIR` binds the value into each importing module, so
    patching one module redirects only that module's reads. Since
    PLAN-backend-module-split.md commit 8 there are two readers: `case_registry` owns the
    Complete/backfill lookups (refined_payload_path, refined_complete_keys) and
    `routers.wizard` still owns the export WRITE path. Patching wizard alone left backfill
    reading the REAL tree — two of these tests went red, and a third
    (test_backfill_noop_leaves_gate_closed) kept passing for the wrong reason: its key
    genuinely has no bundle on disk, so "no backfill" was true either way.

    Anything added here must be patched wherever the name is BOUND, which is why this is
    one helper rather than a monkeypatch line per test.
    """
    import case_registry
    import routers.wizard as wiz

    monkeypatch.setattr(wiz, "REFINED_DIR", tmp_path)
    monkeypatch.setattr(case_registry, "REFINED_DIR", tmp_path)


def _sess(key=_THROWAWAY_KEY, confirmed=False):
    s = WizardSession(key=key)
    if confirmed:
        for step in (s.step1, s.step2, s.step3):
            step.confirmed = True
    # Pre-set gaps so export short-circuits its generate_coverage_gaps() LLM round-trip
    # (`if not (sess_dict.get("gaps") or "").strip()`). Keeps these tests offline — no
    # network, matching the no-LLM discipline of the rest of the suite.
    s.gaps = "(test fixture — gaps pre-set to avoid an LLM call)"
    return s


@pytest.fixture
def clean_session():
    """Guarantee no leftover server-side session for the throwaway key.

    Must clear BOTH layers: the in-memory `sessions` dict AND the persisted row in
    ck.db. Endpoints call _persist_session, so a session created by one test is
    otherwise resurrected by _authoritative_session -> _load_persisted in the next —
    which silently turned the "client-supplied session is rejected" test green-in-
    isolation but wrong in a full run. Also keeps test keys out of ck.db, which is the
    permanent source of truth.
    """
    _purge(_THROWAWAY_KEY)
    try:
        yield _THROWAWAY_KEY
    finally:
        _purge(_THROWAWAY_KEY)


def _purge(key):
    sessions.pop(key, None)
    _clear_persisted(key)


# --- Finding 1: no client-supplied session as a write source --------------------
def test_export_rejects_client_supplied_session(client, clean_session):
    """The exact reported path: server session deleted, stale tab POSTs its own copy.

    A fully-populated client session that would have passed validation must NOT be
    accepted — export 404s because no authoritative session exists.
    """
    resurrected = {
        "key": _THROWAWAY_KEY,
        "step1": {"confirmed": True, "selections": []},
        "step2": {"confirmed": True, "selections": []},
        "step3": {"confirmed": True, "selections": []},
        "step4": {
            "objective": "<ul><li>one</li><li>two</li><li>three</li></ul>",
            "confirmed": True,
        },
        "step5": {"testScript": {"type": "steps", "steps": [
            {"description": "Note: Related ART Tests linked in Traceability", "expectedResult": ""},
            {"description": "do a thing", "expectedResult": "it happened"},
        ]}},
    }
    r = client.post("/api/wizard/export", json={"session": resurrected})
    assert r.status_code == 404, (
        f"client-supplied session was accepted as a write source (got {r.status_code})"
    )


def test_export_requires_a_key(client):
    """A keyless session never reaches the handler — WizardSession.key is required,
    so Pydantic rejects it at the model boundary (422). Either way it cannot write."""
    r = client.post("/api/wizard/export", json={"session": {}})
    assert r.status_code == 422


def test_key_shape_guard_runs_before_the_confirm_gate(client):
    """Guard ordering regression.

    The confirm gate added here shares the handler with the pre-existing path-traversal
    guard. When the confirm gate ran first, a traversal key returned the confirm-gate
    400 and the traversal guard was never exercised — the security test kept passing
    while testing nothing. Pin the order: a malformed key must fail on its SHAPE.
    """
    r = client.post("/api/wizard/export", json={"session": {"key": "../../../tmp/evil"}})
    assert r.status_code == 400
    assert "invalid case key" in r.json().get("detail", "").lower()


# --- Finding 2: the three-DB-review confirm gate --------------------------------
def test_export_blocked_when_reviews_unconfirmed(client, clean_session):
    """Hand-pasted objective + steps must not export as Complete without the reviews.

    save_objective/save_steps have no confirm gate, so this is a straightforward user
    path, not a crafted request.
    """
    sess = _sess(confirmed=False)
    sess.step4 = {"objective": "<ul><li>a</li><li>b</li><li>c</li></ul>", "confirmed": True}
    sess.step5 = {"testScript": {"type": "steps", "steps": [
        {"description": "Note: Related ART Tests linked in Traceability", "expectedResult": ""},
        {"description": "hand-authored", "expectedResult": "ok"},
    ]}}
    sessions[_THROWAWAY_KEY] = sess

    r = client.post("/api/wizard/export", json={"session": {"key": _THROWAWAY_KEY}})
    assert r.status_code == 400
    assert "three databases" in r.json().get("detail", "").lower()


def test_export_gate_passes_when_reviews_confirmed(client, clean_session):
    """Positive control: the gate must not block a properly confirmed session.

    Asserts only that we get PAST the confirm gate (not 400/404) — the payload itself
    is empty here, so the downstream validation gate legitimately refuses the write.
    """
    sessions[_THROWAWAY_KEY] = _sess(confirmed=True)
    r = client.post("/api/wizard/export", json={"session": {"key": _THROWAWAY_KEY}})
    assert r.status_code == 200, "confirm gate wrongly blocked a confirmed session"
    assert r.json()["wrote_bundle"] is False  # empty payload still fails validation


# --- Data integrity: every shipped bundle must be readable ----------------------
def test_every_refined_bundle_is_valid_json():
    """A Complete bundle that cannot be parsed cannot be backfilled or re-exported.

    AWPTCM-T37861 shipped with a Python-style `\\'` escape (valid in a Python literal,
    invalid per RFC 8259) from its very first commit, so it silently failed backfill and
    400ed on re-export. It was the only one of the 43; this keeps it that way.
    """
    import json
    import pathlib

    refined = (pathlib.Path(__file__).resolve().parents[1]
               / "ask-ck" / "objective-drafting" / "refined-cases")
    if not refined.exists():
        pytest.skip("refined-cases/ not present")

    broken = []
    for p in sorted(refined.rglob("zephyr_payload.json")):
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            broken.append(f"{p.parent.name}: {e}")
    assert not broken, "unparseable Complete bundle(s):\n  " + "\n  ".join(broken)


def test_every_refined_bundle_passes_the_export_gate():
    """Every Complete case must remain re-exportable through the batch-A confirm gate."""
    import pathlib

    refined = (pathlib.Path(__file__).resolve().parents[1]
               / "ask-ck" / "objective-drafting" / "refined-cases")
    if not refined.exists():
        pytest.skip("refined-cases/ not present")

    blocked = []
    for key in sorted({p.parent.name for p in refined.rglob("zephyr_payload.json")}):
        sess = WizardSession(key=key)
        _backfill_from_refined(sess)
        if not _can_synthesize(sess):
            blocked.append(key)
    assert not blocked, f"cases that can no longer be re-exported: {blocked}"


# --- Migration guard: backfilled cases satisfy the new gate ---------------------
def test_backfill_marks_reviews_confirmed(tmp_path, monkeypatch):
    """The 43 existing bundles must stay re-exportable.

    A Complete on-disk bundle means the reviews WERE done; that history just isn't in
    the runtime session. Without this, the new gate 400s every legacy re-export.
    """
    key = "AWPTCM-T99992"
    payload_dir = tmp_path / "Group" / key
    payload_dir.mkdir(parents=True)
    (payload_dir / "zephyr_payload.json").write_text(json.dumps({
        key: {
            "objective": "<ul><li>a</li><li>b</li><li>c</li></ul>",
            "testScript": {"type": "steps", "steps": [{"description": "x", "expectedResult": "y"}]},
        }
    }), encoding="utf-8")
    _redirect_refined_dir(monkeypatch, tmp_path)

    sess = WizardSession(key=key)
    assert not _can_synthesize(sess)          # precondition: gate would block

    assert _backfill_from_refined(sess) is True
    assert _can_synthesize(sess), "backfilled case cannot pass the export confirm gate"
    assert sess.step1.backfilled is True      # provenance distinguishable from a real confirm
    assert sess.step4.get("objective")


def test_unreadable_bundle_reports_the_real_cause(client, tmp_path, monkeypatch):
    """A Complete-but-unreadable bundle must not be blamed on unconfirmed reviews.

    One real bundle (AWPTCM-T37861) ships invalid JSON (a bad \\' escape), so backfill
    can't restore its reviews. Telling the user to "confirm all three databases" would
    be both wrong and unactionable — the message must name the unreadable file.
    """
    key = "AWPTCM-T99994"
    payload_dir = tmp_path / "Group" / key
    payload_dir.mkdir(parents=True)
    (payload_dir / "zephyr_payload.json").write_text("{ not valid json ", encoding="utf-8")
    _redirect_refined_dir(monkeypatch, tmp_path)

    _purge(key)
    sessions[key] = WizardSession(key=key)
    try:
        r = client.post("/api/wizard/export", json={"session": {"key": key}})
        assert r.status_code == 400
        detail = r.json().get("detail", "").lower()
        assert "could not be read" in detail, detail
        assert "zephyr_payload.json" in detail
    finally:
        _purge(key)


def test_backfill_noop_leaves_gate_closed(tmp_path, monkeypatch):
    """No on-disk bundle → no synthetic confirms. The gate must stay shut."""
    import case_registry

    _redirect_refined_dir(monkeypatch, tmp_path)
    # Prove the redirect is actually in force before drawing a conclusion from "not
    # found". T99993 has no bundle in the REAL tree either, so without this the test
    # passes whether or not case_registry was redirected — it would report "backfill
    # correctly did nothing" while reading the production refined-cases/ directory.
    assert case_registry.refined_complete_keys() == set(), (
        "refined-cases was not redirected to tmp_path; this test would pass vacuously")

    sess = WizardSession(key="AWPTCM-T99993")
    assert _backfill_from_refined(sess) is False
    assert not _can_synthesize(sess), "backfill invented confirms with no bundle on disk"


# --- Finding 3: the invalidation cascade ----------------------------------------
def _synthesized(confirmed_obj=True):
    s = _sess(confirmed=True)
    s.step1.selections = [Selection(id_or_key="TL-1", title="one")]
    s.step4 = {"objective": "<ul><li>x</li></ul>", "confirmed": confirmed_obj}
    s.step5 = {"testScript": {"type": "steps", "steps": [{"description": "d", "expectedResult": "e"}]}}
    return s


def test_changed_selections_invalidate_downstream():
    s = _synthesized()
    out = _invalidate_downstream(s, changed=True)
    assert out == {"step4": True, "step5": True}
    assert s.step4["confirmed"] is False
    assert s.step4["stale"] is True
    assert s.step5["stale"] is True
    # Content is preserved — only the review claim is withdrawn.
    assert s.step4["objective"]
    assert s.step5["testScript"]["steps"]


def test_unchanged_selections_preserve_downstream():
    """Re-clicking Confirm on the same shortlist must not destroy a good objective."""
    s = _synthesized()
    out = _invalidate_downstream(s, changed=False)
    assert out == {"step4": False, "step5": False}
    assert s.step4["confirmed"] is True
    assert "stale" not in s.step4


def test_fingerprint_is_order_insensitive():
    """Reordering the shortlist is not a content change and must not invalidate."""
    a = _sess()
    a.step1.selections = [Selection(id_or_key="TL-1", title="one"),
                          Selection(id_or_key="TL-2", title="two")]
    b = _sess()
    b.step1.selections = [Selection(id_or_key="TL-2", title="two"),
                          Selection(id_or_key="TL-1", title="one")]
    assert _selection_fingerprint(a, 1) == _selection_fingerprint(b, 1)


def test_fingerprint_detects_swapped_selection():
    """The reported scenario: swap the TestLink case the objective was written around."""
    a = _sess()
    a.step1.selections = [Selection(id_or_key="TL-1", title="one")]
    b = _sess()
    b.step1.selections = [Selection(id_or_key="TL-9", title="nine")]
    assert _selection_fingerprint(a, 1) != _selection_fingerprint(b, 1)


def test_fingerprint_detects_none_selected_toggle():
    a = _sess()
    b = _sess()
    b.step1.none_selected = True
    assert _selection_fingerprint(a, 1) != _selection_fingerprint(b, 1)


def test_confirm_step_endpoint_invalidates(client, clean_session):
    """End-to-end through the real route: swapping a selection flags the objective stale."""
    sessions[_THROWAWAY_KEY] = _synthesized()
    r = client.post(
        f"/api/wizard/confirm_step/{_THROWAWAY_KEY}/1",
        json={"selections": [{"id_or_key": "TL-DIFFERENT", "title": "swapped"}]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["invalidated"] == {"step4": True, "step5": True}
    assert body["session"]["step4"]["stale"] is True
    assert body["session"]["step4"]["confirmed"] is False


def test_confirm_step_endpoint_no_change_preserves(client, clean_session):
    """Re-confirming the identical shortlist through the route preserves the objective."""
    sessions[_THROWAWAY_KEY] = _synthesized()
    r = client.post(
        f"/api/wizard/confirm_step/{_THROWAWAY_KEY}/1",
        json={"selections": [{"id_or_key": "TL-1", "title": "one"}]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["invalidated"] == {"step4": False, "step5": False}
    assert body["session"]["step4"]["confirmed"] is True


def test_reconfirm_objective_clears_stale(client, clean_session):
    """Staleness must be escapable — an explicit re-confirm clears the flag."""
    s = _synthesized()
    s.step4 = {**s.step4, "confirmed": False, "stale": True}
    sessions[_THROWAWAY_KEY] = s
    r = client.post(f"/api/wizard/confirm_objectives/{_THROWAWAY_KEY}", json={})
    assert r.status_code == 200
    assert "stale" not in r.json()["session"]["step4"]


# --- Finding 4: atomic bundle write ---------------------------------------------
def test_complete_marker_is_written_last():
    """zephyr_payload.json is the Complete marker, so it must be the final commit point.

    Guards the ordering directly: if a future edit moves the payload back ahead of the
    session dump, a mid-write failure could again leave a case Complete with a partial
    bundle.
    """
    src = pathlib.Path(__file__).resolve().parents[1] / (
        "ask-ck/CK-main/CK_server/routers/wizard.py")
    text = src.read_text(encoding="utf-8")
    block = text.split("files_written = [", 1)[1].split("]", 1)[0]
    order = [line for line in block.splitlines() if '("' in line or '(f"' in line]
    assert "zephyr_payload.json" in order[-1], (
        "the Complete marker must be written last; got order:\n" + "\n".join(order))


def test_export_write_is_staged_via_os_replace():
    """The write must stage to a temp sibling and os.replace, not write in place."""
    src = pathlib.Path(__file__).resolve().parents[1] / (
        "ask-ck/CK-main/CK_server/routers/wizard.py")
    text = src.read_text(encoding="utf-8")
    assert "os.replace(tmp, final)" in text, "bundle write is no longer atomic"
    assert "tmp.unlink(missing_ok=True)" in text, "partial temp files are not cleaned up"
