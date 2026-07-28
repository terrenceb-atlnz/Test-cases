"""confirm_step must reject a malformed selections payload, not silently drop it.

The bug: three copies of

    try:    sess.stepN.selections = [Selection(**s) for s in body["selections"]]
    except Exception: pass
    sess.stepN.confirmed = True

A single bad entry made the whole comprehension raise, so the assignment never
happened and the session silently kept its PREVIOUS selections — then the handler
marked the step confirmed and returned can_synthesize: true anyway. The user was told
the confirm worked, then synthesized an objective against selections they had just
replaced. Same family as 9afdf97's silent session data-loss bug.

Rejecting the whole payload rather than keeping the good entries is deliberate: a
partial confirm is the same silent divergence in a smaller costume.
"""
import asyncio

import pytest
from fastapi import HTTPException

from models import Selection, WizardSession
from routers.wizard import (
    _parse_selections,
    confirm_step,
    sessions,
)
from session_store import clear_persisted

_KEY = "AWPTCM-T99993"          # throwaway; never a real case
_GOOD = {"id_or_key": "AWP-1", "title": "Alpha", "justification": "why", "order": 0}


@pytest.fixture
def sess():
    """A session pre-loaded with one existing selection per step, then cleaned up."""
    s = WizardSession(key=_KEY)
    for state in (s.step1, s.step2, s.step3):
        state.selections = [Selection(id_or_key="PRE-EXISTING", title="Kept")]
    sessions[_KEY] = s
    yield s
    sessions.pop(_KEY, None)
    clear_persisted(_KEY)


def _confirm(step, body):
    return asyncio.run(confirm_step(_KEY, step, body, data={}))


# --- the regression itself ---------------------------------------------------

@pytest.mark.parametrize("step", [1, 2, 3])
def test_malformed_selection_400s_and_confirms_nothing(sess, step):
    """The whole point: a bad payload must NOT report success."""
    state = getattr(sess, f"step{step}")
    assert not state.confirmed

    with pytest.raises(HTTPException) as exc:
        _confirm(step, {"selections": [_GOOD, {"title": "no id_or_key"}]})

    assert exc.value.status_code == 400
    # The step must be left unconfirmed...
    assert state.confirmed is False, "a rejected confirm must not mark the step confirmed"
    # ...and the previous selections untouched, not half-replaced.
    assert [s.id_or_key for s in state.selections] == ["PRE-EXISTING"]


def test_error_detail_names_the_offending_index_and_field(sess):
    with pytest.raises(HTTPException) as exc:
        _confirm(1, {"selections": [_GOOD, {"title": "missing the id"}]})
    detail = str(exc.value.detail)
    assert "[1]" in detail, "should identify WHICH entry failed"
    assert "id_or_key" in detail, "should identify the failing field"
    assert "NOTHING was confirmed" in detail


def test_a_rejected_confirm_does_not_unlock_synthesis(sess):
    """can_synthesize must not creep forward off a failed confirm."""
    for step in (1, 2):
        _confirm(step, {"selections": [_GOOD]})
    with pytest.raises(HTTPException):
        _confirm(3, {"selections": [{"nope": 1}]})
    assert sess.step3.confirmed is False


@pytest.mark.parametrize(
    "payload",
    ["not-a-list", 42, {"id_or_key": "x", "title": "y"}, None],
    ids=["str", "int", "dict", "none"],
)
def test_non_list_selections_400s(sess, payload):
    with pytest.raises(HTTPException) as exc:
        _confirm(1, {"selections": payload})
    assert exc.value.status_code == 400
    assert "must be a list" in str(exc.value.detail)


def test_non_object_entries_are_reported_not_swallowed(sess):
    with pytest.raises(HTTPException) as exc:
        _confirm(2, {"selections": [_GOOD, "a bare string", 7]})
    detail = str(exc.value.detail)
    assert "2 of 3" in detail
    assert "expected an object" in detail


# --- the happy paths must be untouched --------------------------------------

@pytest.mark.parametrize("step", [1, 2, 3])
def test_valid_selections_still_confirm(sess, step):
    out = _confirm(step, {"selections": [_GOOD]})
    state = getattr(sess, f"step{step}")
    assert state.confirmed is True
    assert [s.id_or_key for s in state.selections] == ["AWP-1"]
    assert state.confirmed_at is not None
    assert out["session"]["key"] == _KEY


def test_omitting_selections_confirms_without_touching_them(sess):
    """A body with no `selections` key keeps the existing list (prior behaviour)."""
    _confirm(1, {})
    assert sess.step1.confirmed is True
    assert [s.id_or_key for s in sess.step1.selections] == ["PRE-EXISTING"]


def test_empty_list_is_valid_and_clears_the_selections(sess):
    """Distinct from omitting the key — an explicit [] means "none chosen"."""
    _confirm(1, {"selections": []})
    assert sess.step1.confirmed is True
    assert sess.step1.selections == []


def test_step1_still_honours_none_selected(sess):
    _confirm(1, {"selections": [], "none": True})
    assert sess.step1.none_selected is True


def test_step3_still_autobuilds_art_string(sess):
    _confirm(3, {"selections": [
        {"id_or_key": "1336.1", "title": "a"},
        {"id_or_key": "1336.2", "title": "b"},
    ]})
    assert sess.art_string == "1336.1 + 1336.2"


def test_step3_explicit_art_string_wins(sess):
    _confirm(3, {"selections": [_GOOD], "art_string": "hand written"})
    assert sess.art_string == "hand written"


@pytest.mark.parametrize("step", [0, 4, 99, -1])
def test_invalid_step_400s(sess, step):
    with pytest.raises(HTTPException) as exc:
        _confirm(step, {"selections": [_GOOD]})
    assert exc.value.status_code == 400
    assert "Invalid step" in str(exc.value.detail)


# --- _parse_selections in isolation -----------------------------------------

def test_parse_selections_accepts_the_browser_payload_shape():
    """chosen.js toEntry sends exactly these four fields; all must validate."""
    rows = [{"id_or_key": "A", "title": "t", "justification": "", "order": 0}]
    assert [s.id_or_key for s in _parse_selections(rows, 1)] == ["A"]


def test_parse_selections_tolerates_extra_and_missing_optional_fields():
    rows = [{"id_or_key": "A", "title": "t", "unexpected": "ignored"}]
    out = _parse_selections(rows, 1)
    assert out[0].justification == ""
    assert out[0].order is None


def test_parse_selections_caps_the_reported_problem_list():
    """Twelve bad rows must not produce a twelve-clause error string."""
    with pytest.raises(HTTPException) as exc:
        _parse_selections([{"bad": i} for i in range(12)], 1)
    detail = str(exc.value.detail)
    assert "12 of 12" in detail
    assert "+7 more" in detail
