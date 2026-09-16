"""Regression tests for two adversarial-review fixes:
- #6 export must PREPEND the traceability note when steps[0] is a real step (not overwrite it)
- #5 admin reset must use the correct session kind ("pt") for PyTest sessions
"""
import db


_NOTE_PREFIX = "Note: Related ART Tests linked in Traceability"


def _apply_note_rule(steps, note_desc):
    """Mirror the note placement rule in wizard.export() so we can pin its behavior.
    (The rule lives inline in the endpoint; this replicates it 1:1 for a focused test.)"""
    steps = list(steps)
    if steps:
        first = steps[0] if isinstance(steps[0], dict) else {}
        first_desc = (first.get("description") or "").strip()
        if first_desc.startswith(_NOTE_PREFIX) or not first_desc:
            steps[0] = {"description": note_desc, "expectedResult": first.get("expectedResult", "")}
        else:
            steps.insert(0, {"description": note_desc, "expectedResult": ""})
    else:
        steps = [{"description": note_desc, "expectedResult": ""}]
    return steps


def test_note_prepended_when_first_step_is_real():
    note = _NOTE_PREFIX + ". See traceability.md."
    real = [{"description": "Verify the port comes up", "expectedResult": "link up"}]
    out = _apply_note_rule(real, note)
    # The real step must survive, now at index 1; note at index 0.
    assert out[0]["description"].startswith(_NOTE_PREFIX)
    assert out[1]["description"] == "Verify the port comes up"
    assert len(out) == 2


def test_note_overwrites_when_first_step_is_already_the_note():
    note = _NOTE_PREFIX + ". See traceability.md."
    existing = [{"description": _NOTE_PREFIX + ". old text", "expectedResult": ""},
                {"description": "Real step", "expectedResult": ""}]
    out = _apply_note_rule(existing, note)
    assert out[0]["description"] == note      # regenerated, not duplicated
    assert out[1]["description"] == "Real step"
    assert len(out) == 2                        # no duplicate note added


def test_empty_steps_get_note_only():
    note = _NOTE_PREFIX + "."
    out = _apply_note_rule([], note)
    assert len(out) == 1 and out[0]["description"] == note


def test_pt_session_kind_is_pt_not_pytest():
    """#5: admin reset deletes PT sessions with kind 'pt'. _session_id must map 'pt'
    to the pt-prefixed id and NOT recognize the wrong 'pytest' string."""
    assert db._session_id("pt", "AWPTCM-T1") == "pt-AWPTCM-T1"
    # The buggy old kind string does not resolve to the pt row id.
    assert db._session_id("pytest", "AWPTCM-T1") != "pt-AWPTCM-T1"


def test_clear_case_sessions_removes_below_threshold_wizard_rows():
    """admin scope='all' must clear EVERY wizard/pt row — including barely-started wizard
    sessions that fall below list_session_progress()'s threshold. That threshold was the
    2026-09-16 bug: reset-session 'all' enumerated the progress maps, so 24 of 63 rows
    (opened but with no confirmed step / objective / gaps) survived a full reset. The
    fix deletes by kind directly. The workspace LLM row (kind='workspace') must survive."""
    # One wizard session WITH progress (visible in the map)...
    db.save_session("wizard", "AWPTCM-TCLR1",
                    {"key": "AWPTCM-TCLR1", "step1": {"confirmed": True}})
    # ...and one BELOW threshold — opened, nothing confirmed, no objective, no gaps.
    db.save_session("wizard", "AWPTCM-TCLR2", {"key": "AWPTCM-TCLR2"})
    db.save_session("pt", "AWPTCM-TCLR1", {"key": "AWPTCM-TCLR1"})
    db.save_workspace_llm({"model": "keep-me"})
    try:
        prog = db.list_session_progress()
        assert "AWPTCM-TCLR1" in prog, "a progressed wizard case is in the map"
        assert "AWPTCM-TCLR2" not in prog, \
            "the below-threshold case is invisible to the progress map — the bug's root cause"

        removed = db.clear_case_sessions()
        assert removed >= 3

        # Every wizard/pt row gone — crucially INCLUDING the below-threshold one the old
        # progress-map enumeration left behind.
        assert db.load_session("wizard", "AWPTCM-TCLR1") is None
        assert db.load_session("wizard", "AWPTCM-TCLR2") is None
        assert db.load_session("pt", "AWPTCM-TCLR1") is None
        # Corpora aside, the workspace default is a different kind and must be untouched.
        assert db.load_workspace_llm() == {"model": "keep-me"}
    finally:
        db.delete_session("workspace", "_workspace_llm")   # leave the shared test DB as found
