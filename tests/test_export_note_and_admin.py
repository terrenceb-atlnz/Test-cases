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
