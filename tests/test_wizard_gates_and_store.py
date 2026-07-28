"""Unit tests for the Generator's state machine, backfill, and session store.

PLAN-backend-module-split.md commit 9 moved these out of `routers/wizard.py` into
`CK_server/wizard/gates.py`, `CK_server/wizard/backfill.py` and
`CK_server/session_store.py`. They are the rules that make the Generator a gated wizard
rather than a form, and until the move nothing could call them without a TestClient.

The gate logic is worth direct coverage for a specific reason recorded in
SURVEY-step4-step5.md: every one of these predicates guards on `isinstance(sess.step4,
dict)`, and if step4/step5 were ever typed as pydantic models each guard would silently
take its `else` branch — killing the invalidation cascade and the Step-5 gate — with the
entire suite still green. That was measured, and it is why commit 6 was dropped. These
tests assert the branches those guards select, so the behaviour is pinned by more than the
fields' current type.

Pure: no TestClient, no LLM, no network, no writes outside tmp_path. `session_store`'s db
calls are monkeypatched, so nothing here touches even the isolated ck.db copy.
"""
import json

import pytest

from models import Selection, WizardSession


def _confirmed(sess=None):
    sess = sess or WizardSession(key="AWPTCM-T99991")
    for step in (sess.step1, sess.step2, sess.step3):
        step.confirmed = True
    return sess


# --- gates -------------------------------------------------------------------

def test_objective_synthesis_needs_all_three_reviews():
    from wizard.gates import can_synthesize

    sess = WizardSession(key="AWPTCM-T99991")
    assert not can_synthesize(sess)
    sess.step1.confirmed = sess.step2.confirmed = True
    assert not can_synthesize(sess), "two of three must not open the gate"
    sess.step3.confirmed = True
    assert can_synthesize(sess)


def test_step_five_needs_the_reviews_AND_an_objective():
    """Both conditions, and in that order — the ordering is what makes the 400 messages
    actionable (a user with no reviews should not be told to write an objective)."""
    from wizard.gates import can_synthesize_steps

    sess = WizardSession(key="AWPTCM-T99991")
    sess.step4 = {"objective": "<ul><li>a</li></ul>"}
    assert not can_synthesize_steps(sess), "objective alone must not open the gate"

    sess = _confirmed()
    assert not can_synthesize_steps(sess), "confirmed reviews alone must not open the gate"
    sess.step4 = {"objective": "<ul><li>a</li></ul>"}
    assert can_synthesize_steps(sess)


def test_an_unconfirmed_objective_still_opens_step_five():
    """Deliberate: a re-run after synthesize_objectives must work without an extra click.
    The UI still prompts to confirm."""
    from wizard.gates import can_synthesize_steps

    sess = _confirmed()
    sess.step4 = {"objective": "<ul><li>a</li></ul>", "confirmed": False}
    assert can_synthesize_steps(sess)


def test_objective_reader_trims_and_tolerates_every_empty_shape():
    from wizard.gates import session_has_objective, session_objective

    sess = WizardSession(key="AWPTCM-T99991")
    assert session_objective(sess) == "" and not session_has_objective(sess)
    sess.step4 = {"objective": "  <ul><li>a</li></ul>  "}
    assert session_objective(sess) == "<ul><li>a</li></ul>"
    assert session_has_objective(sess)
    sess.step4 = {"objective": "   "}
    assert not session_has_objective(sess), "whitespace is not an objective"
    sess.step4 = {"objective": None}
    assert session_objective(sess) == ""


def test_objective_reader_returns_empty_for_a_non_dict_step4():
    """The isinstance guard's else branch. If step4 were ever a pydantic model this is the
    path every gate would take — see the module docstring and SURVEY-step4-step5.md."""
    from wizard.gates import session_objective

    sess = WizardSession(key="AWPTCM-T99991")
    sess.step4 = "not a dict"
    assert session_objective(sess) == ""


# --- selection fingerprint ---------------------------------------------------

def test_fingerprint_ignores_order_and_justification_but_not_the_ids():
    """It exists to tell a real change from a harmless re-confirm, so re-clicking Confirm
    never throws away a good objective."""
    from wizard.gates import selection_fingerprint

    a, b = WizardSession(key="AWPTCM-T99991"), WizardSession(key="AWPTCM-T99991")
    a.step1.selections = [Selection(id_or_key="X", title="x", justification="one", order=0),
                          Selection(id_or_key="Y", title="y", order=1)]
    b.step1.selections = [Selection(id_or_key="Y", title="Y RENAMED", order=9),
                          Selection(id_or_key="X", title="x", justification="two", order=3)]
    assert selection_fingerprint(a, 1) == selection_fingerprint(b, 1)

    b.step1.selections.append(Selection(id_or_key="Z", title="z"))
    assert selection_fingerprint(a, 1) != selection_fingerprint(b, 1)


def test_fingerprint_distinguishes_none_selected_from_nothing_chosen():
    """"I reviewed and nothing applies" is a decision; "not looked at yet" is not."""
    from wizard.gates import selection_fingerprint

    a, b = WizardSession(key="AWPTCM-T99991"), WizardSession(key="AWPTCM-T99991")
    b.step1.none_selected = True
    assert selection_fingerprint(a, 1) != selection_fingerprint(b, 1)


def test_fingerprint_of_a_nonexistent_step_is_empty():
    from wizard.gates import selection_fingerprint
    assert selection_fingerprint(WizardSession(key="AWPTCM-T99991"), 99) == ()


# --- invalidation cascade ----------------------------------------------------

def test_invalidation_only_fires_on_a_real_change():
    from wizard.gates import invalidate_downstream

    sess = WizardSession(key="AWPTCM-T99991")
    sess.step4 = {"objective": "<ul><li>a</li></ul>", "confirmed": True}
    out = invalidate_downstream(sess, changed=False)
    assert out == {"step4": False, "step5": False}
    assert sess.step4["confirmed"] is True, "an unchanged re-confirm must not invalidate"


def test_invalidation_keeps_the_content_and_clears_only_the_review_claim():
    """The user may want to edit rather than regenerate, so the generated text stays."""
    from wizard.gates import invalidate_downstream

    sess = WizardSession(key="AWPTCM-T99991")
    sess.step4 = {"objective": "<ul><li>a</li></ul>", "confirmed": True,
                  "confirmed_at": "2026-01-01T00:00:00+00:00"}
    sess.step5 = {"testScript": {"type": "steps", "steps": [{"description": "d"}]},
                  "confirmed": True}
    out = invalidate_downstream(sess, changed=True)

    assert out == {"step4": True, "step5": True}
    assert sess.step4["objective"] == "<ul><li>a</li></ul>", "content must survive"
    assert sess.step5["testScript"]["steps"], "content must survive"
    assert sess.step4["confirmed"] is False and sess.step4["confirmed_at"] is None
    assert sess.step5["confirmed"] is False
    assert sess.step4["stale"] is True and sess.step5["stale"] is True, (
        "the `stale` flag is what generator.js:158-161 uses to stop a contradictory bundle "
        "reaching export — it is transient, so no census of stored data can see it")


def test_an_unconfirmed_objective_is_not_invalidated_again():
    """Nothing to withdraw: it was never claimed as reviewed."""
    from wizard.gates import invalidate_downstream

    sess = WizardSession(key="AWPTCM-T99991")
    sess.step4 = {"objective": "<ul><li>a</li></ul>", "confirmed": False}
    assert invalidate_downstream(sess, changed=True)["step4"] is False
    assert "stale" not in sess.step4


def test_empty_test_steps_are_not_marked_stale():
    from wizard.gates import invalidate_downstream

    sess = WizardSession(key="AWPTCM-T99991")
    sess.step5 = {"testScript": {"type": "steps", "steps": []}}
    assert invalidate_downstream(sess, changed=True)["step5"] is False


# --- legacy migration --------------------------------------------------------

def test_legacy_test_script_migrates_step4_to_step5_without_destroying_it():
    from wizard.gates import migrate_legacy_step4_to_step5

    ts = {"type": "steps", "steps": [{"description": "d", "expectedResult": "e"}]}
    sess = WizardSession(key="AWPTCM-T99991")
    sess.step4 = {"objective": "o", "testScript": ts}
    assert migrate_legacy_step4_to_step5(sess) is True
    assert sess.step5["testScript"] == ts
    assert sess.step4["testScript"] == ts, "non-destructive: the legacy copy stays"
    assert migrate_legacy_step4_to_step5(sess) is False, "idempotent"


def test_migration_never_overwrites_a_current_step5():
    from wizard.gates import migrate_legacy_step4_to_step5

    sess = WizardSession(key="AWPTCM-T99991")
    sess.step4 = {"testScript": {"steps": [{"description": "OLD"}]}}
    sess.step5 = {"testScript": {"steps": [{"description": "NEW"}]}}
    assert migrate_legacy_step4_to_step5(sess) is False
    assert sess.step5["testScript"]["steps"][0]["description"] == "NEW"


# --- backfill ----------------------------------------------------------------

def _bundle(tmp_path, key, payload):
    d = tmp_path / "Group (1)" / key
    d.mkdir(parents=True)
    (d / "zephyr_payload.json").write_text(
        payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")


@pytest.fixture
def refined(tmp_path, monkeypatch):
    import case_registry
    monkeypatch.setattr(case_registry, "REFINED_DIR", tmp_path)
    return tmp_path


def test_backfill_restores_both_fields_and_confirms_the_reviews(refined):
    """A Complete bundle proves the three reviews were done, so the export gate must open —
    otherwise all 43 existing bundles 400 on re-export for work already finished."""
    from wizard.backfill import backfill_from_refined
    from wizard.gates import can_synthesize

    key = "AWPTCM-T99992"
    _bundle(refined, key, {key: {
        "objective": "<ul><li>a</li><li>b</li></ul>",
        "testScript": {"type": "steps", "steps": [{"description": "d", "expectedResult": "e"}]},
    }})
    sess = WizardSession(key=key)
    assert backfill_from_refined(sess) is True
    assert sess.step4["objective"].startswith("<ul>")
    assert sess.step5["testScript"]["steps"]
    assert can_synthesize(sess), "backfilled case cannot pass the export confirm gate"
    for step in (sess.step1, sess.step2, sess.step3):
        assert step.confirmed and step.backfilled, (
            "`backfilled` must distinguish these from fresh in-session confirms")
    assert sess.step4["backfilled"] is True and sess.step5["backfilled"] is True


def test_backfill_sanitizes_the_objective_it_reads_from_disk(refined):
    """Legacy bundles predate objective sanitization, and this is a stored-XSS path: the
    objective is rendered in the browser."""
    from wizard.backfill import backfill_from_refined

    key = "AWPTCM-T99992"
    _bundle(refined, key, {key: {
        "objective": "<ul><li>ok</li></ul><script>alert(1)</script>",
        "testScript": {"steps": [{"description": "d"}]},
    }})
    sess = WizardSession(key=key)
    assert backfill_from_refined(sess) is True
    assert "<script>" not in sess.step4["objective"]


def test_backfill_is_a_noop_when_the_session_already_has_the_synthesis(refined):
    """Otherwise it would re-fire on every /load_case for all 43 Complete cases and clobber
    the session's own objective — the hazard that helped get commit 6 dropped."""
    from wizard.backfill import backfill_from_refined

    key = "AWPTCM-T99992"
    _bundle(refined, key, {key: {"objective": "<ul><li>DISK</li></ul>",
                                 "testScript": {"steps": [{"description": "disk"}]}}})
    sess = WizardSession(key=key)
    sess.step4 = {"objective": "<ul><li>SESSION</li></ul>"}
    sess.step5 = {"testScript": {"steps": [{"description": "session"}]}}
    assert backfill_from_refined(sess) is False
    assert "SESSION" in sess.step4["objective"]


def test_backfill_accepts_the_direct_inner_shape(refined):
    """Two shapes exist on disk: keyed by case, and {objective, testScript} at top level."""
    from wizard.backfill import backfill_from_refined

    key = "AWPTCM-T99992"
    _bundle(refined, key, {"objective": "<ul><li>a</li></ul>",
                           "testScript": {"steps": [{"description": "d"}]}})
    sess = WizardSession(key=key)
    assert backfill_from_refined(sess) is True


def test_backfill_refuses_an_unreadable_bundle_without_confirming_anything(refined):
    """One real bundle (AWPTCM-T37861) ships invalid JSON. It must not half-confirm."""
    from wizard.backfill import backfill_from_refined
    from wizard.gates import can_synthesize

    key = "AWPTCM-T99992"
    _bundle(refined, key, "{ not valid json ")
    sess = WizardSession(key=key)
    assert backfill_from_refined(sess) is False
    assert not can_synthesize(sess), "an unreadable bundle must not open the export gate"


def test_backfill_does_nothing_without_a_bundle(refined):
    from wizard.backfill import backfill_from_refined
    from wizard.gates import can_synthesize

    sess = WizardSession(key="AWPTCM-T99993")
    assert backfill_from_refined(sess) is False
    assert not can_synthesize(sess), "backfill invented confirms with no bundle on disk"


def test_backfill_leaves_an_already_confirmed_step_alone(refined):
    """A real in-session confirm must not be relabelled as backfilled — that is the only
    thing distinguishing the two provenances."""
    from wizard.backfill import backfill_from_refined

    key = "AWPTCM-T99992"
    _bundle(refined, key, {key: {"objective": "<ul><li>a</li></ul>",
                                 "testScript": {"steps": [{"description": "d"}]}}})
    sess = WizardSession(key=key)
    sess.step1.confirmed = True
    assert backfill_from_refined(sess) is True
    assert not sess.step1.backfilled, "a genuine confirm was overwritten as backfilled"
    assert sess.step2.backfilled and sess.step3.backfilled


# --- session store -----------------------------------------------------------

def test_the_router_and_the_store_share_one_sessions_dict():
    """`from session_store import sessions` binds the same object. Rebinding it in the
    router (sessions = {}) would give it a private copy and silently detach persistence
    from the cache — an entire class of "my confirm vanished" bug."""
    import routers.wizard as wizard
    import session_store

    assert wizard.sessions is session_store.sessions


def test_persist_stamps_updated_at_as_aware_utc(monkeypatch):
    import session_store as store

    monkeypatch.setattr(store.db, "save_session", lambda *a, **k: None)
    sess = WizardSession(key="AWPTCM-T99994")
    store.persist_session(sess)
    assert sess.updated_at.tzinfo is not None


def test_persist_swallows_a_failure_but_records_it_as_a_lost_write(monkeypatch, caplog):
    """Deliberately different from pytest_create._pt_persist, which RAISES 500.

    Both are intentional and the asymmetry is documented in session_store's docstring: the
    pt side was changed to raise because a 200 with no write had made "never trust the 200"
    a documented workaround. If this is ever unified, it is a behaviour decision, not a
    refactor — so pin what this half does today.
    """
    import logging

    import session_store as store

    def _boom(*a, **k):
        raise RuntimeError("database is locked")

    monkeypatch.setattr(store.db, "save_session", _boom)
    with caplog.at_level(logging.DEBUG, logger="session_store"):
        store.persist_session(WizardSession(key="AWPTCM-T99994"))   # must not raise

    rec = [r for r in caplog.records if "AWPTCM-T99994" in r.getMessage()]
    assert rec and rec[0].levelno == logging.ERROR
    assert rec[0].exc_info is not None, "keep the traceback"


def test_load_returns_none_rather_than_raising_on_an_invalid_stored_row(monkeypatch):
    """A row that no longer validates against WizardSession must degrade to "no session",
    not 500 the case list."""
    import session_store as store

    monkeypatch.setattr(store.db, "load_session",
                        lambda kind, key: {"key": key, "step1": "not a step state"})
    assert store.load_persisted("AWPTCM-T99994") is None
    monkeypatch.setattr(store.db, "load_session", lambda kind, key: None)
    assert store.load_persisted("AWPTCM-T99994") is None


def test_the_store_addresses_the_wizard_kind(monkeypatch):
    """kind is the discriminator on the shared sessions table; 'pt' rows belong to the
    PyTest Creator and must never be read or clobbered through here."""
    import session_store as store

    seen = []
    monkeypatch.setattr(store.db, "save_session", lambda kind, key, data: seen.append(kind))
    monkeypatch.setattr(store.db, "load_session", lambda kind, key: seen.append(kind))
    monkeypatch.setattr(store.db, "delete_session", lambda kind, key: seen.append(kind))
    store.persist_session(WizardSession(key="AWPTCM-T99994"))
    store.load_persisted("AWPTCM-T99994")
    store.clear_persisted("AWPTCM-T99994")
    assert seen == ["wizard", "wizard", "wizard"]
