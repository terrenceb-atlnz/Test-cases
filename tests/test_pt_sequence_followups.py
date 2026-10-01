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


# --- A4 (2026-09-28): the DUT decides — every port and every device gets the same treatment --
# Terrence reversed R1 ("a fixed copper port must accept 10/100"): some products do not go
# that slow, and the sweep's job is to MAP what the device accepts. The rule lives in the
# extract prompt (it writes the verify text), the fact behind it in the shared domain facts
# (extract + review), and T33235 is the first script written to it.

_DF = (_SERVER / "templates" / "prompts" / "_pt_domain_facts.jinja").read_text(encoding="utf-8")
_T33235 = (_REPO / "ask-ck" / "functions" / "pytest-creator" / "generated" / "9001_Port"
           / "test-9001.33235.py").read_text(encoding="utf-8")


def test_A4_the_extract_prompt_says_the_dut_decides_and_the_record_is_published():
    i = _EX.index("**THE DUT DECIDES — EVERY PORT AND EVERY DEVICE GETS THE SAME TREATMENT.**")
    rule = " ".join(_EX[i:_EX.index("- **TRY EVERY DOCUMENTED VALUE", i)].split())
    assert "never as the verdict" in " ".join(_EX[:i].split())        # the table = which values to TRY
    assert "A rejection is a verified result, never a failure" in rule
    assert "declare it in `publishes`" in rule and "speedMap" in rule
    assert "never a table or a port-type guess" in rule
    # the old shape must be gone from the prompt: the table as the source of legality
    assert "take unsupported-value choices from there" not in _EX


def test_A4_the_domain_fact_names_the_hardware_reason_and_the_false_red():
    i = _DF.index("**Which speeds a port accepts is decided by the DUT")
    fact = " ".join(_DF[i:_DF.index("- **A negotiated port never reports", i)].split())
    assert "some fixed copper ports do not go below 1000" in fact
    assert "a copper SFP reads `1000BASE-T`" in fact
    assert '"a fixed copper port must accept 10/100" is a FALSE RED' in fact


def test_A4_T33235_records_every_sweep_answer_and_never_fails_a_rejection_by_port_type():
    # Every sweep case (TC2-TC12) records the DUT's answer; no verdict is drawn from a table.
    assert _T33235.count("self.testSet.speedMap.setdefault(name, {})[") == 11
    assert "self.speedMap = {}" in _T33235
    for word in ("legal-values", "legal values", "expect_supported", "legal_2500", "lists_5000",
                 "tenGigLegal", "legal_40g", "legal_100g", "is_100m", "expectLegal"):
        assert word not in _T33235, word
    # the consumers read the record, guarded, and report UNSUPPORTED when it is empty: TC19,
    # TC20, and TC21 ("only if step 21 ran", Terrence 2026-10-01)
    assert _T33235.count("recorded = (self.testSet.speedMap or {}).get(") == 3
    assert "bad_speed = rejected[-1]" in _T33235
    # no case fails the DUT for an answer that disagrees with a port-type classification
    bad = [ln.strip() for ln in _T33235.splitlines() if "self.failed(" in ln and "although" in ln
           and any(w in ln for w in ("table", "port type", "its type", "lists ", "is a 40G", "not a QSFP"))]
    assert bad == [], bad
