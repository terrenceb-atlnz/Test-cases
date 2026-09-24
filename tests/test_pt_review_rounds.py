"""P1 / D-A (PLAN-pt-drive-followups-2026-09-24 §1): the tool review loop had no bound and no cost.

T33235 (2026-09-24): four tool reviews of one script, ~355-375k prompt characters each on Opus,
the last two of a script already hand-merged, with nothing on screen saying which round it was
or what it cost. Terrence: "we are already two-reviews past what i want the tool to actually do."

Pinned: a stored review is counted and logged with its prompt size; after the free rounds the
endpoint refuses (409, before any prompt is rendered or sent) unless `extra_round` is set; a dry
run is never refused; reset_generate starts the count again; the count reaches the UI.
"""
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SERVER = _REPO / "ask-ck" / "CK-main" / "CK_server"
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(_SERVER))

from routers import pytest_create as pc  # noqa: E402

_SRC = (_SERVER / "routers" / "pytest_create.py").read_text(encoding="utf-8")
_CODE = re.sub(r'#[^\n]*', '', re.sub(r'"""[\s\S]*?"""', '', _SRC))
REVIEW = _CODE[_CODE.index('@router.post("/review_script/'):_CODE.index('@router.post("/fix_script/')]
RESET = _CODE[_CODE.index('@router.post("/reset_generate/'):_CODE.index('@router.post("/assemble_script/')]


def _review(n=3):
    return {"at": f"2026-09-24T1{n}:00", "code_hash": "abc", "findings": [{}] * n,
            "provenance": {"llm": {"model": "claude-opus-5-5"}}}


def test_a_stored_review_is_counted_and_logged_with_its_size():
    s6 = {}
    pc._record_review_round(s6, _review(2), 360000)
    pc._record_review_round(s6, _review(1), None)
    assert s6["review_rounds"] == 2
    assert s6["review_log"][0] == {"at": "2026-09-24T12:00", "code_hash": "abc", "prompt_chars": 360000,
                                   "model": "claude-opus-5-5", "findings": 2}
    assert s6["review_log"][1]["prompt_chars"] is None


def test_the_free_rounds_pass_and_the_next_one_needs_extra_round():
    s6 = {}
    for _ in range(pc._PT_REVIEW_ROUNDS_FREE):
        assert pc._review_round_gate(s6, False) is None
        pc._record_review_round(s6, _review(), 372000)
    why = pc._review_round_gate(s6, False)
    assert why and why.startswith("review round cap:")
    assert f"{pc._PT_REVIEW_ROUNDS_FREE} tool review(s)" in why and "~372k" in why and "claude-opus-5-5" in why
    assert pc._review_round_gate(s6, True) is None


def test_the_cap_is_two():
    """D-A, Claude's pick for review: two tool rounds, then confirm-to-continue."""
    assert pc._PT_REVIEW_ROUNDS_FREE == 2


def test_the_endpoint_refuses_BEFORE_rendering_or_sending_and_never_refuses_a_dry_run():
    gate = REVIEW.index("_review_round_gate(step6, extra_round)")
    assert gate < REVIEW.index("run_prompt")
    assert "None if dry_run else _review_round_gate(" in REVIEW
    assert REVIEW.index("_lint_blocks_review(step6)") < gate          # lint gate still first


def test_both_store_paths_count_the_round():
    assert _CODE.count("_record_review_round(step6_f, review,") == 2


def test_reset_generate_starts_the_count_again():
    # reset keeps only files/lint/naming, so review_log goes with the rest
    assert 'for k in ("files", "lint", "naming")' in RESET


def test_gen_state_carries_the_count_to_the_ui():
    st = pc._gen_state({"review_log": [{}, {}, {}]})
    assert st["review_rounds"] == 3 and st["review_rounds_free"] == pc._PT_REVIEW_ROUNDS_FREE
