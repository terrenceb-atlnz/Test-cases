"""Regression tests for the Part 3a mechanical grader (`tool/pt_grade.py`).

The grader turns PLAN-pytest-testing.md §3 criteria 1-3 + the offline half of 6 into a
mechanical verdict, so a wrong grade silently corrupts the judging record. These pin the
behaviours that were actually got wrong while building it against the real sessions:

  - grading the whole fragment pool instead of the reviewer-SELECTED subset
    (T33233: 41 pooled vs 13 selected -> bogus "not at all")
  - scoring a script whose tags predate a later step5 change as model failure
    rather than STALE provenance drift
  - downgrading correctly-ADAPTED reuse because literal line overlap is near zero
    (T33234: tags 14/14, overlap 0.012 -> still "exactly")
  - being fooled by a duplicate tag line the restamp pass left mid-body (T33235)

Pure unit tests — no DB, no network, no LLM.
"""
import ast
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tool"))

pt_grade = pytest.importorskip("pt_grade")


# --------------------------------------------------------------------------- helpers

def _script(n_cases=2, ref="AWPTCM-T1", tag_lines=None, extra_in_main=""):
    """A minimal template-conformant script with `n_cases` TestCases."""
    tag_lines = tag_lines or {}
    out = [
        "#!/usr/bin/python3",
        "import sys",
        "from framework import ATTestSet, ATTestCase",
        "",
        "class TestSet(ATTestSet.TestSet):",
        "    FEATURES = ['ALL']",
        "    def init(self, setup):",
        "        self.swi_a = setup.init_swi('swi_a')",
        "    def configure(self):",
        "        pass",
        "    def tear_down(self):",
        "        pass",
        "",
    ]
    for i in range(1, n_cases + 1):
        out += [
            f"class TestCase_{i}(ATTestCase.TestCase):",
            f"    testCaseDesc = 'step {i}'",
            f"    testCaseRef = '{ref}'",
            f"    testCaseMethod = 'do step {i}'",
            "    def main(self):",
            f"        {tag_lines.get(i, '# AI vllm-fast 2026-07-27')}",
            f"        self.log('STEP {i}: do it')",
            "        output = self.testSet.swi_a.cmd('show foo')",
            "        self.log('OBSERVED: {}'.format(output))",
        ]
        if extra_in_main:
            out.append(f"        {extra_in_main}")
        out += [
            "        if 'up' in output:",
            "            self.passed('it worked')",
            "        else:",
            "            self.failed('it did not')",
            "    def tear_down(self):",
            "        pass",
            "",
        ]
    out += ["if __name__ == '__main__':", "    ts = TestSet()"]
    for i in range(1, n_cases + 1):
        out.append(f"    ts.add_testCase(TestCase_{i}())")
    out.append("    ts.run(sys.argv)")
    return "\n".join(out)


def _seq(n, kind="verify"):
    return [{"n": i, "action": f"step {i}", "verify": "check it", "kind": kind}
            for i in range(1, n + 1)]


def _frag(source_id, loc, maps_to, code="x = 1"):
    return {"source_id": source_id, "symbol": "TestCase_1", "loc": loc,
            "maps_to": maps_to, "code": code}


# --------------------------------------------------------------------------- C1

def test_c1_exact_when_frame_and_counts_match():
    code = _script(2)
    r = pt_grade.grade_c1(code, ast.parse(code), _seq(2), "AWPTCM-T1")
    assert r["verdict"] == "exactly", r["findings"]


def test_c1_partial_when_testcase_count_differs_from_verify_steps():
    code = _script(2)
    r = pt_grade.grade_c1(code, ast.parse(code), _seq(3), "AWPTCM-T1")
    assert r["verdict"] == "partially"
    assert any("2 TestCase classes vs 3 verify steps" in f for f in r["findings"])


def test_c1_flags_wrong_testcaseref():
    code = _script(1, ref="WRONG-KEY")
    r = pt_grade.grade_c1(code, ast.parse(code), _seq(1), "AWPTCM-T1")
    assert r["verdict"] == "partially"
    assert any("testCaseRef" in f for f in r["findings"])


def test_c1_setup_steps_do_not_count_as_testcases():
    # setup steps render into TestSet.configure(), not a TestCase -- so 1 TestCase
    # against [setup, verify] is CORRECT, not a count mismatch.
    code = _script(1)
    seq = [{"n": 1, "action": "prep", "verify": "", "kind": "setup"},
           {"n": 2, "action": "check", "verify": "yes", "kind": "verify"}]
    r = pt_grade.grade_c1(code, ast.parse(code), seq, "AWPTCM-T1")
    assert r["verify_steps"] == 1
    assert r["verdict"] == "exactly", r["findings"]


def test_c1_not_at_all_without_the_frame():
    code = "print('hello')\n"
    r = pt_grade.grade_c1(code, ast.parse(code), _seq(1), "AWPTCM-T1")
    assert r["verdict"] == "not at all"


# --------------------------------------------------------------------------- C2/C3

def test_c2_uses_selected_subset_not_the_whole_pool():
    """The bug that produced a bogus 'not at all' on T33233."""
    payload = {"step5": {
        "fragments": [_frag("legacy/a.py", [1, 9], [1]), _frag("legacy/b.py", [1, 9], [2])],
        "selected": [{"source_id": "legacy/a.py", "symbol": "TestCase_1"}],
    }}
    got = pt_grade.selected_fragments(payload)
    assert [f["source_id"] for f in got] == ["legacy/a.py"]


def test_c2_missing_selected_key_falls_back_to_whole_pool():
    """Documented back-compat: no `selected` key at all == everything is in play
    (this is why T33234's 7 fragments legitimately grade 14/14)."""
    payload = {"step5": {"fragments": [_frag("legacy/a.py", [1, 9], [1])]}}
    assert len(pt_grade.selected_fragments(payload)) == 1


def test_c2_empty_selected_list_means_none_selected():
    payload = {"step5": {"fragments": [_frag("legacy/a.py", [1, 9], [1])], "selected": []}}
    assert pt_grade.selected_fragments(payload) == []


def test_c2_exactly_when_every_mapped_step_carries_the_right_tag():
    frags = [_frag("legacy/a.py", [10, 20], [1])]
    tag = pt_grade._fragment_tag("legacy/a.py", [10, 20])
    code = _script(2, tag_lines={1: tag})
    c2, c3 = pt_grade.grade_c2_c3(code, ast.parse(code), frags, _seq(2))
    assert c2["verdict"] == "exactly"
    assert c2["tags_matched"] == "1/1"
    assert c3["verdict"] == "right"


def test_c2_low_code_overlap_does_not_downgrade_adapted_reuse():
    """T33234: tags all correct, literal overlap ~0.01 because the model adapted the
    fragment to bound device names + the logging contract. Still 'exactly'."""
    frags = [_frag("legacy/a.py", [10, 20], [1],
                   code="dut = self.dut\nportA = dut.portA\nremote = self.remote")]
    tag = pt_grade._fragment_tag("legacy/a.py", [10, 20])
    code = _script(1, tag_lines={1: tag})
    c2, _ = pt_grade.grade_c2_c3(code, ast.parse(code), frags, _seq(1))
    assert c2["verdict"] == "exactly"
    assert c2["avg_code_overlap"] == 0.0


def test_c2_stale_when_tags_reference_a_since_changed_selection():
    """T33233: the script's tags name fragments no longer selected -> provenance drift,
    NOT the model ignoring its snippets."""
    frags = [_frag("legacy/current.py", [1, 9], [1])]
    old_tag = pt_grade._fragment_tag("legacy/removed.py", [55, 66])
    code = _script(1, tag_lines={1: old_tag})
    c2, c3 = pt_grade.grade_c2_c3(code, ast.parse(code), frags, _seq(1))
    assert c2["verdict"] == "stale"
    assert c3["verdict"] == "n-a"


def test_c2_na_when_no_fragments_selected():
    code = _script(2)
    c2, c3 = pt_grade.grade_c2_c3(code, ast.parse(code), [], _seq(2))
    assert c2["verdict"] == "n-a"
    assert c3["verdict"] == "n-a"


def test_c3_wrong_when_fragment_order_does_not_follow_sequence():
    a = pt_grade._fragment_tag("legacy/a.py", [1, 9])
    b = pt_grade._fragment_tag("legacy/b.py", [1, 9])
    frags = [_frag("legacy/a.py", [1, 9], [1]), _frag("legacy/b.py", [1, 9], [2])]
    code = _script(2, tag_lines={1: b, 2: a})          # swapped
    _, c3 = pt_grade.grade_c2_c3(code, ast.parse(code), frags, _seq(2))
    assert c3["verdict"] == "wrong"


def test_maps_to_remap_survives_a_dropped_setup_step():
    """maps_to uses ORIGINAL step numbers; TestCase_<n> is contiguous after setup steps
    drop out. A fragment mapped to original step 2 must expect TestCase_1."""
    frags = [_frag("legacy/a.py", [1, 9], [2])]
    tag = pt_grade._fragment_tag("legacy/a.py", [1, 9])
    code = _script(1, tag_lines={1: tag})
    seq = [{"n": 1, "action": "prep", "verify": "", "kind": "setup"},
           {"n": 2, "action": "check", "verify": "yes", "kind": "verify"}]
    c2, _ = pt_grade.grade_c2_c3(code, ast.parse(code), frags, seq)
    assert c2["verdict"] == "exactly", c2


def test_first_tag_wins_over_a_later_duplicate_echo():
    """T33235: the model echoed the prompt's instruction below a self.log(), which the
    restamp's leading-run strip does not reach. The authoritative tag is still first."""
    tag = pt_grade._fragment_tag("legacy/a.py", [1, 9])
    frags = [_frag("legacy/a.py", [1, 9], [1])]
    code = _script(1, tag_lines={1: tag},
                   extra_in_main="# Provenance tag for this fragment: AI vllm-fast 2026-07-27")
    c2, _ = pt_grade.grade_c2_c3(code, ast.parse(code), frags, _seq(1))
    assert c2["verdict"] == "exactly"
    assert c2["per_step"][0]["duplicate_tag_lines"] > 1   # detected, but not fatal


# --------------------------------------------------------------------------- C6

def test_c6_yes_when_every_main_meets_the_logging_contract():
    code = _script(3)
    r = pt_grade.grade_c6_offline(code, ast.parse(code))
    assert r["verdict"] == "yes"
    assert r["conformant"] == "3/3"


def test_c6_flags_an_empty_verdict_string():
    """An empty passed()/failed() emits no log marker -> no per-step evidence."""
    code = _script(1).replace("self.passed('it worked')", "self.passed('')") \
                     .replace("self.failed('it did not')", "self.failed('')")
    r = pt_grade.grade_c6_offline(code, ast.parse(code))
    assert r["verdict"] == "no"
    assert any("non-empty" in w for w in r["per_testcase"][0]["why"])


def test_c6_flags_a_missing_observed_log():
    code = _script(1).replace("        self.log('OBSERVED: {}'.format(output))\n", "")
    r = pt_grade.grade_c6_offline(code, ast.parse(code))
    assert r["verdict"] == "no"
    assert any("OBSERVED" in w for w in r["per_testcase"][0]["why"])


def test_c6_partial_when_only_some_cases_conform():
    code = _script(2).replace("self.passed('it worked')", "self.passed('')", 1) \
                     .replace("self.failed('it did not')", "self.failed('')", 1)
    r = pt_grade.grade_c6_offline(code, ast.parse(code))
    assert r["verdict"] == "partial"
    assert r["conformant"] == "1/2"


# --------------------------------------------------------------------------- caveats

def test_caveats_flag_unconfirmed_and_wrong_backend():
    payload = {"step5": {"confirmed": False}, "step6": {
        "confirmed": False, "provenance": {"llm": {"model": "default"}}}}
    cav = pt_grade._caveats(payload)
    assert any("step5" in c for c in cav)
    assert any("headless-CLI default" in c for c in cav)


def test_no_caveats_on_a_clean_confirmed_case():
    payload = {"step5": {"confirmed": True}, "step6": {
        "confirmed": True, "provenance": {"llm": {"model": "vllm-fast"}}}}
    assert pt_grade._caveats(payload) == []
