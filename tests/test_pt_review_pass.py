"""Pass C — the holistic review returns FINDINGS, and they reach the fix loop.

WHAT THIS IS (PLAN-pytest-creator.md §9.6, built 2026-09-02)
-----------------------------------------------------------
The pipeline had exactly one failure class with no checker behind it: a test case whose
pass/fail determination does not correspond to its sequence row's `verify` text. That
script compiles, passes every structural assertion, passes pycodestyle, and passes on the
bench — for the wrong reason. §9.6: "the only one a human currently catches."

Three properties of the design are load-bearing and pinned here.

1. FINDINGS, NEVER A REWRITE. §9.6 is explicit: a rewrite pass re-emits the whole script
   (the same ~35KB in one message and the same wall clock that chunking exists to avoid)
   and it can silently undo a correct reused fragment, destroying the provenance chain
   PLAN §1.5 keeps. So `review_script` must not write `step6.files`.

2. AN UNREADABLE ANSWER IS NOT A CLEAN SCRIPT. "No findings" is a legitimate, expected
   result here, which is exactly what makes an unparseable reply dangerous — it lands on
   the same stored shape. gather_fragments learned this the hard way (twice, on 2026-07-30)
   and its guard is reproduced.

3. A REVIEW MUST NOT INVALIDATE ANYTHING. It reads the artefact and writes an opinion; the
   script is untouched. Calling `_invalidate_from` would discard a confirmation on the
   basis of having looked at it.

NOT PINNED: the prompt's wording, the finding vocabulary's exact members, or how many
findings a real model returns. Those are tuning.
"""
import re
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SERVER = _REPO / "ask-ck" / "CK-main" / "CK_server"
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(_SERVER))

from routers import pytest_create as pc  # noqa: E402

_SRC = (_SERVER / "routers" / "pytest_create.py").read_text(encoding="utf-8")

# Structural assertions read the CODE, never the prose about it. A grep over raw source
# matches the docstring EXPLAINING a rule as readily as a violation of it — and such a
# docstring necessarily names the identifiers the rule forbids. Four tests in this repo
# have failed exactly that way; strip docstrings and comments first.
_CODE = re.sub(r'#[^\n]*', '',
               re.sub(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'', '', _SRC))


SEQ = [{"n": 1, "action": "select a TLV", "verify": "the TLV shows as selected"},
       {"n": 2, "action": "clear a TLV", "verify": "the TLV shows as cleared"}]


def _sess(**over):
    s = pc.PtSession(key="AWPTCM-T1")
    s.step2 = {"sequence": SEQ}
    s.step6 = {"files": {"test": {"name": "t.py", "code": "print(1)\n"}},
               "lint": {"ok": True, "errors": [], "warnings": ["pep8 E501: long line"]}}
    for k, v in over.items():
        setattr(s, k, v)
    return s


# --- the lint findings the review is TOLD about, so it does not redo them ----------

def test_the_static_checks_are_handed_to_the_review_not_left_for_it_to_redo():
    out = pc._review_lint_findings(_sess())
    assert any("pep8 E501" in f for f in out)


def test_warnings_are_included_because_pep8_lives_there():
    # A model that cannot see the 137 E501 warnings will rediscover them and spend its
    # output saying so — which is the cost §9.6 exists to avoid.
    s = _sess()
    s.step6["lint"] = {"errors": ["boom"], "warnings": ["pep8 W293: whitespace"]}
    out = pc._review_lint_findings(s)
    assert any(f.startswith("ERROR: ") for f in out)
    assert any("W293" in f for f in out)


def test_errors_and_warnings_stay_distinguishable():
    s = _sess()
    s.step6["lint"] = {"errors": ["e1"], "warnings": ["w1"]}
    out = pc._review_lint_findings(s)
    assert "ERROR: e1" in out and "warning: w1" in out


# --- normalization ----------------------------------------------------------------

def test_a_finding_with_nothing_actionable_is_dropped():
    # No `what` is no statement of a defect; storing it as an empty row would put a
    # blank finding in front of the reviewer and inflate the count.
    out = pc._normalize_findings([{"where": "TestCase_1.main", "severity": "high"}], SEQ)
    assert out == []


def test_an_unknown_kind_keeps_the_finding_rather_than_rejecting_it():
    out = pc._normalize_findings(
        [{"what": "x", "kind": "invented_category", "severity": "high"}], SEQ)
    assert len(out) == 1 and out[0]["kind"] == "other"


def test_an_unknown_severity_folds_to_medium():
    out = pc._normalize_findings([{"what": "x", "severity": "CRITICAL"}], SEQ)
    assert out[0]["severity"] == "medium"


def test_a_step_number_outside_the_sequence_is_dropped_not_stored():
    # A finding attributed to step 99 of a 2-step case would render under a step that
    # does not exist; the finding itself is still worth keeping.
    out = pc._normalize_findings([{"what": "x", "step": 99}], SEQ)
    assert len(out) == 1 and out[0]["step"] is None
    out = pc._normalize_findings([{"what": "x", "step": 2}], SEQ)
    assert out[0]["step"] == "2"


def test_findings_come_back_most_severe_first():
    out = pc._normalize_findings(
        [{"what": "a", "severity": "low"}, {"what": "b", "severity": "high"},
         {"what": "c", "severity": "medium"}], SEQ)
    assert [f["severity"] for f in out] == ["high", "medium", "low"]


def test_a_non_list_reply_yields_no_findings_rather_than_raising():
    assert pc._normalize_findings({"findings": "oops"}, SEQ) == []
    assert pc._normalize_findings(None, SEQ) == []


# --- the fix loop actually consumes them ------------------------------------------

def test_review_findings_are_a_reason_to_fix_on_their_own():
    """A reviewed script with real findings and a GREEN lint used to 409 'nothing to fix'.

    That is the whole point of Pass C: it names defects neither the linter nor a run can
    see, so 'no lint errors and no failed run' cannot mean 'nothing to fix' any more.
    """
    src = (_SERVER / "routers" / "pytest_create.py").read_text(encoding="utf-8")
    i = src.index("async def fix_script")
    body = src[i:i + 3000]
    assert "review_findings" in body
    assert "not review_findings" in body, "the 409 gate must consider review findings"
    # and they must reach the prompt, not just the gate
    assert '"review_findings": review_findings' in body


def test_the_fix_prompt_renders_the_findings():
    tpl = (_SERVER / "templates" / "prompts" / "pt_fix_script.jinja").read_text(encoding="utf-8")
    assert "review_findings" in tpl
    assert "f.what" in tpl and "f.suggestion" in tpl


def test_a_fix_clears_the_stale_review_and_persists_the_fresh_lint():
    """A fix produces a NEW artefact, so the predecessor's review no longer describes it —
    dropped the way assemble_script drops it — and the lint recomputed on the rewritten code
    must be WRITTEN BACK to the session, not only returned, or the panel keeps rendering the
    pre-fix lint until a manual Re-lint (2026-09-04)."""
    i = _CODE.index("async def fix_script")
    j = _CODE.index("async def validate", i)
    body = _CODE[i:j]
    assert 'pop("review", None)' in body, "a fix must drop the pre-fix review"
    assert '["lint"] = lint_now' in body, "the fresh lint must be persisted to the session, not just returned"


# --- the three load-bearing design properties -------------------------------------

def test_the_review_never_writes_the_script():
    """§9.6: findings, not a rewrite. If this endpoint could write step6.files it would be
    a rewrite pass wearing a review's name, with the wall clock and the provenance risk
    that decision exists to avoid."""
    i = _CODE.index("async def review_script")
    j = _CODE.index("async def fix_script")
    body = _CODE[i:j]
    # It READS step6.files (the guard: there must be a script to review). The property
    # is that it never ASSIGNS one.
    assert not re.search(r'\["files"\]\s*=', body), "review_script must not write step6.files"
    assert 'step6_f["review"] = review' in body, "the only thing it writes is the review"
    assert "_parse_generated_blocks" not in body
    assert "_restamp_provenance" not in body


def test_the_review_does_not_invalidate_downstream_steps():
    i = _CODE.index("async def review_script")
    j = _CODE.index("async def fix_script")
    assert "_invalidate_from" not in _CODE[i:j]


def test_an_unparseable_reply_is_refused_rather_than_stored_as_no_findings():
    src = (_SERVER / "routers" / "pytest_create.py").read_text(encoding="utf-8")
    i = src.index("async def review_script")
    j = src.index("async def fix_script")
    body = src[i:j]
    assert "extract_json_block" in body
    assert "parsed is None" in body, "a reply that does not parse must not become 'clean'"


def test_the_review_persists_through_the_fresh_write_path():
    # A 600s LLM call persisting a pre-call snapshot is the 409 class fixed on 2026-09-01.
    src = (_SERVER / "routers" / "pytest_create.py").read_text(encoding="utf-8")
    i = src.index("async def review_script")
    j = src.index("async def fix_script")
    assert "_pt_persist_fresh" in src[i:j]


def test_a_script_that_has_not_been_generated_cannot_be_reviewed():
    src = (_SERVER / "routers" / "pytest_create.py").read_text(encoding="utf-8")
    i = src.index("async def review_script")
    body = src[i:i + 2000]
    assert "409" in body


# --- the prompt itself -------------------------------------------------------------

def test_the_prompt_forbids_weakening_an_assertion():
    tpl = (_SERVER / "templates" / "prompts" / "pt_review_script.jinja").read_text(encoding="utf-8")
    assert "Never propose weakening or deleting an assertion" in tpl


def test_the_prompt_makes_an_empty_result_safe_to_return():
    # Without this a model under review pressure manufactures findings, and the reviewer
    # learns to ignore the panel.
    tpl = (_SERVER / "templates" / "prompts" / "pt_review_script.jinja").read_text(encoding="utf-8")
    assert "empty `findings` list" in tpl
    assert "Do not manufacture findings" in tpl


def test_the_prompt_tells_it_not_to_redo_the_static_checks():
    tpl = (_SERVER / "templates" / "prompts" / "pt_review_script.jinja").read_text(encoding="utf-8")
    assert "do not re-report" in tpl


def test_the_prompt_puts_the_verify_text_in_front_of_the_model():
    """The primary finding class is verdict-vs-verify. It cannot be found without the
    verify text, so the prompt must carry the sequence rows, not just the code."""
    tpl = (_SERVER / "templates" / "prompts" / "pt_review_script.jinja").read_text(encoding="utf-8")
    assert "s.verify" in tpl and "s.action" in tpl


def test_the_prompt_protects_the_fixed_frame_and_the_provenance_tags():
    tpl = (_SERVER / "templates" / "prompts" / "pt_review_script.jinja").read_text(encoding="utf-8")
    assert "fixed frame" in tpl
    assert "provenance" in tpl
