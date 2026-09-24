"""S1-S4 (PLAN-pt-drive-followups-2026-09-24 §5): what the T33235 sequence work exposed.

  S1  the extract prompt still wrote mid-run pluggable swaps after the 2026-09-23 ruling that a
      fitted pluggable is a PRECONDITION (T33235's fresh extract produced two, hand-edited out);
  S2  per-step script candidates survived a re-extract keyed by the OLD step numbers;
  S3  the extract's notes kept describing steps that had been edited away;
  S4  "try every speed on every script" had to be hand-written into each sweep step.
"""
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SERVER = _REPO / "ask-ck" / "CK-main" / "CK_server"
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(_SERVER))

from routers import pytest_create as pc  # noqa: E402

_EX = (_SERVER / "templates" / "prompts" / "pt_extract_sequence.jinja").read_text(encoding="utf-8")
_SRC = (_SERVER / "routers" / "pytest_create.py").read_text(encoding="utf-8")
_CODE = re.sub(r'#[^\n]*', '', re.sub(r'"""[\s\S]*?"""', '', _SRC))
SAVE = _CODE[_CODE.index('@router.post("/save_sequence/'):_CODE.index('@router.get("/search_scripts")')]
EXTRACT = _CODE[_CODE.index('@router.post("/extract_sequence/'):_CODE.index('@router.post("/save_sequence/')]
JS = (_REPO / "ask-ck" / "frontend" / "ck-main" / "current" / "pytest-creator" / "pytest.js").read_text(encoding="utf-8")


def test_S1_a_fitted_pluggable_is_a_precondition_and_a_swap_is_written_only_when_it_is_the_subject():
    assert "**Fitted pluggables are a PRECONDITION, not a step.**" in _EX
    assert "ONLY when the step is ABOUT the insertion itself" in _EX
    # physical steps stay in scope — the rule narrows WHEN, it does not drop the kind
    assert "These are IN SCOPE — do NOT skip them." in _EX


def test_S4_every_documented_value_is_tried_with_an_accept_or_reject_verify():
    i = _EX.index("**TRY EVERY DOCUMENTED VALUE, ON EVERY SCRIPT.**")
    rule = _EX[i:_EX.index("- **HALF DUPLEX", i)]
    assert "accept-if-legal, reject-if-not" in rule and "verify the rejection instead" in rule
    assert "Never\n  drop a documented value" in rule or "Never drop a documented value" in " ".join(rule.split())


PREV = [{"n": 1, "action": "configure base"}, {"n": 2, "action": "force speed 100"},
        {"n": 3, "action": "force speed 1000"}]
STEP3 = {"step_matches": {"1": [{"id": "a"}], "2": [{"id": "b"}], "3": [{"id": "c"}]},
         "selections": {"2": ["b"], "3": ["c"]}}


def test_S2_candidates_survive_only_on_steps_whose_text_is_unchanged_and_selections_are_never_touched():
    new = [{"n": 1, "action": "configure  base"}, {"n": 2, "action": "force speed 10"}]
    step3, dropped = pc._prune_step_matches(STEP3, PREV, new)
    assert dropped == ["2", "3"]
    assert step3["step_matches"] == {"1": [{"id": "a"}]}
    assert step3["selections"] == STEP3["selections"]           # the reviewer's picks stay


def test_S2_nothing_to_prune_returns_the_very_same_object():
    same, dropped = pc._prune_step_matches(STEP3, PREV, PREV)
    assert same is STEP3 and dropped == []
    assert pc._prune_step_matches(None, PREV, []) == (None, [])


def test_S2_both_sequence_writers_prune():
    assert "_prune_step_matches(sess.step3, prev_seq, sequence)" in SAVE
    assert "_prune_step_matches(fresh.step3, prev_seq_f, sequence)" in EXTRACT


def test_S3_a_reshaped_sequence_marks_the_extract_notes_stale_and_the_page_says_so():
    assert 'sess.step2["notes_stale"] = True' in SAVE
    assert SAVE.index("reshaped = _sequence_shape(prev_seq) != _sequence_shape(sequence)") < \
        SAVE.index('sess.step2["notes_stale"] = True')
    assert "notes_stale" not in EXTRACT          # a fresh extract writes a fresh step2
    assert "(ptSession.step2 || {}).notes_stale" in JS
