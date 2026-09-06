"""Per-unit Fix and the two-tier Review gate (token-efficiency decision 7, 2026-09-07).

The whole-script Fix re-emits the entire file — on T44297 it changed 9 of 38 classes at 64k
output tokens and could perturb the other 29. Every finding we hold names a class or a line,
i.e. a UNIT, and a unit can be re-generated alone under the same cached system half its
generation used, then spliced back by the same assembly. Findings that name nothing stay
with the whole-script Fix and are reported as `unmapped`, never guessed at.

Two-tier Review: Review refuses (409) while lint has BLOCKING errors. Policy errors are the
reviewer's call and style warnings gate nothing.

Pinned: the mapping rules; the reasons composition; the fix prompt reuses the generation's
shared half verbatim (that identity IS the cache); the chain waits for every unit and then
re-assembles through the one assembly implementation; the gate.
"""
import asyncio
import re
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SERVER = _REPO / "ask-ck" / "CK-main" / "CK_server"
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(_SERVER))

from llm import render_prompt  # noqa: E402
from routers import pytest_create as pc  # noqa: E402

_SRC = (_SERVER / "routers" / "pytest_create.py").read_text(encoding="utf-8")
_CODE = re.sub(r'#[^\n]*', '', re.sub(r'"""[\s\S]*?"""', '', _SRC))
FIX_UNITS = _CODE[_CODE.index('@router.post("/fix_units/'):_CODE.index('@router.post("/review_script/')]
REVIEW = _CODE[_CODE.index('@router.post("/review_script/'):_CODE.index('@router.post("/fix_script/')]
_A0 = _CODE.index('@router.post("/assemble_script/')
ASSEMBLE = _CODE[_A0:_A0 + 1500]                       # the endpoint is a thin caller now

SCRIPT = '''#!/usr/bin/python3
import sys
from framework import ATTestSet, ATTestCase


class TestSet(ATTestSet.TestSet):
    def init(self, setup):
        self.dut = setup.init_swi('swi_a')

    def configure(self):
        self.dut.cmd('lldp run')

    def tear_down(self):
        pass


class TestCase_1(ATTestCase.TestCase):
    testCaseDesc = 'one'
    testCaseRef = 'AWPTCM-T1'
    testCaseMethod = 'one'

    def main(self):
        # ART a.py:x
        self.log('one')
        self.passed('ok')


class TestCase_2(ATTestCase.TestCase):
    testCaseDesc = 'two'
    testCaseRef = 'AWPTCM-T1'
    testCaseMethod = 'two'

    def main(self):
        # AI
        self.log('two')
        self.failed('bad')


if __name__ == '__main__':
    ts = TestSet()
    ts.add_testCase(TestCase_1)
    ts.add_testCase(TestCase_2)
    ts.run(sys.argv)
'''
UNITS = pc._skeleton_units(SCRIPT)
TC_STEPS = [{"n": 3, "action": "a", "verify": "v"}, {"n": 4, "action": "b", "verify": "w"}]
CTX = {"units": UNITS, "tc_steps": TC_STEPS, "setup_steps": [{"n": 1, "action": "cfg"}]}


def _line_of(text: str) -> int:
    return SCRIPT.split("\n").index(text) + 1


# --- mapping ---------------------------------------------------------------------------------

def test_a_class_name_maps_to_its_unit():
    assert pc._unit_id_for_text("structure: TestCase_2 missing testCaseDesc", UNITS) == "tc2"
    assert pc._unit_id_for_text("contract: TestCase_1.main() has no self.log()", UNITS) == "tc1"


def test_a_line_number_maps_through_the_assembled_scripts_ranges():
    ln = _line_of("        self.failed('bad')")
    assert pc._unit_id_for_text(f"line {ln}: uses device `x` but init() never binds it", UNITS) == "tc2"
    assert pc._unit_id_for_text(f"pep8 E501: t.py:{ln}: line too long", UNITS) == "tc2"


def test_the_setup_pair_is_named_by_testset_or_its_methods():
    assert pc._unit_id_for_text("TestSet.configure() issues no commands", UNITS) == "setup"
    assert pc._unit_id_for_text("configure() must not call passed()", UNITS) == "setup"


def test_a_class_name_wins_over_a_setup_word_in_the_same_line():
    assert pc._unit_id_for_text("TestCase_1 duplicates what configure() did", UNITS) == "tc1"


def test_nothing_recognisable_maps_to_nothing():
    assert pc._unit_id_for_text("structure: missing ts.run(sys.argv) __main__ entry", UNITS) is None
    assert pc._unit_id_for_text("imports: framework module 'x' not found", UNITS) is None
    assert pc._unit_id_for_text("line 2: shebang", UNITS) is None      # outside every unit


def test_a_review_finding_maps_by_where_then_by_step():
    assert pc._unit_id_for_finding({"where": "TestCase_2.main", "step": None}, CTX, UNITS) == "tc2"
    # step 4 is the SECOND tc row (renumbering: tc2 implements sequence step 4)
    assert pc._unit_id_for_finding({"where": "(script)", "step": "4"}, CTX, UNITS) == "tc2"
    assert pc._unit_id_for_finding({"where": "(script)", "step": None}, CTX, UNITS) is None


# --- reasons ---------------------------------------------------------------------------------

def _sess():
    s = pc.PtSession(key="AWPTCM-T1")
    s.step6 = {"files": {"test": {"name": "t.py", "code": SCRIPT}},
               "lint": {"ok": False, "errors": [
                   "structure: TestCase_2 missing testCaseDesc",
                   f"line {_line_of('        self.passed(\'ok\')')}: something in tc1",
                   "structure: missing ts.run(sys.argv) __main__ entry"],
                   "warnings": ["pep8 E501: long"]},
               "review": {"findings": [
                   {"severity": "high", "kind": "verdict_mismatch", "where": "TestCase_1.main",
                    "step": "3", "what": "asserts the wrong thing", "evidence": "self.passed('ok')",
                    "suggestion": "assert x"},
                   {"severity": "low", "kind": "other", "where": "(script)", "step": None,
                    "what": "imports unused module", "evidence": "", "suggestion": ""}]}}
    s.step7 = {"runs": [{"parsed": {"cases": [
        {"name": "TestCase_1", "result": "PASS", "fail_msgs": []},
        {"name": "TestCase_2", "result": "FAIL", "fail_msgs": ["bad"]},
        {"name": "TestCase_9", "result": "FAIL", "fail_msgs": ["ghost"]}]}, "log_file": ""}]}
    return s


def test_reasons_land_on_their_units_and_the_rest_is_reported_unmapped():
    r = pc._fix_reasons(_sess(), CTX, SCRIPT)
    per = r["per_unit"]
    assert set(per) == {"tc1", "tc2"}
    assert per["tc2"]["lint"] == ["structure: TestCase_2 missing testCaseDesc"]
    assert per["tc2"]["run"]["result"] == "FAIL" and per["tc2"]["excerpt"] == ""
    assert len(per["tc1"]["lint"]) == 1 and per["tc1"]["review"][0]["where"] == "TestCase_1.main"
    assert per["tc1"]["run"] is None                      # a PASS is not a reason
    assert [u[:6] for u in r["unmapped"]] == ["lint: ", "review", "run: T"]


def test_a_session_with_nothing_wrong_yields_nothing():
    s = pc.PtSession(key="AWPTCM-T1")
    s.step6 = {"files": {"test": {"name": "t.py", "code": SCRIPT}}, "lint": {"ok": True, "errors": []}}
    r = pc._fix_reasons(s, CTX, SCRIPT)
    assert r["per_unit"] == {} and r["unmapped"] == []


def test_chunks_are_resynced_from_the_script_on_screen():
    synced = pc._chunks_from_code(SCRIPT, CTX)
    assert set(synced) == {"setup", "tc1", "tc2"}
    assert synced["tc2"].startswith("class TestCase_2(") and "self.failed('bad')" in synced["tc2"]
    assert synced["setup"].lstrip().startswith("def configure(self):")
    # Round trip: splicing the synced chunks back reproduces the script exactly.
    chunks = {k: {"status": "ok", "code": v} for k, v in synced.items()}
    code, missing = pc._assemble_units({"skeleton": SCRIPT, "units": UNITS}, chunks)
    assert missing == [] and code == SCRIPT


# --- the prompt ------------------------------------------------------------------------------

def test_the_fix_prompt_keeps_the_generations_shared_half_byte_for_byte(monkeypatch):
    gen = "SHARED HALF\nrules...\n\n" + pc._PT_PROMPT_SPLIT + "\n\n## Your unit: TestCase_2\nblank block"
    monkeypatch.setattr(pc, "_render_unit_prompt", lambda *a, **k: gen)
    unit = next(u for u in UNITS if u["id"] == "tc2")
    reasons = {"lint": ["structure: TestCase_2 missing testCaseDesc"],
               "review": [{"severity": "high", "where": "TestCase_2.main", "what": "wrong verdict",
                           "evidence": "self.failed('bad')", "suggestion": "assert y"}],
               "run": {"result": "FAIL", "fail_msgs": ["bad"]}, "excerpt": "LOG LINE"}
    p = pc._fix_unit_prompt("AWPTCM-T1", {}, pc.PtSession(key="AWPTCM-T1"), CTX, unit,
                            "class TestCase_2: CURRENT", reasons)
    shared, user = pc._split_unit_prompt(p)
    assert shared == pc._split_unit_prompt(gen)[0]                 # the cache key
    assert p.count(pc._PT_PROMPT_SPLIT) == 1
    assert user.startswith("## Your unit: TestCase_2")             # the generation's unit half first
    for needle in ("FIX PASS for TestCase_2", "class TestCase_2: CURRENT",
                   "missing testCaseDesc", "wrong verdict", "assert y", "FAIL", "LOG LINE",
                   "Never weaken or delete an assertion", "SELF-CONTAINED"):
        assert needle in user, needle


def test_the_setup_pair_is_asked_for_as_a_pair():
    p = render_prompt("pt_fix_unit.jinja", {"unit_label": "TestSet.configure / tear_down",
                                            "kind": "setup", "current_code": "x",
                                            "lint_errors": [], "review_findings": [],
                                            "run_result": None, "log_excerpt": ""})
    assert "`configure()` / `tear_down()` pair" in p
    assert "Bench result" not in p and "Static check errors" not in p


# --- the chain --------------------------------------------------------------------------------

def test_run_primed_and_wait_runs_first_alone_then_the_rest_together_and_waits():
    ev = []

    async def run(uid, dt):
        ev.append(("start", uid)); await asyncio.sleep(dt); ev.append(("end", uid))

    asyncio.run(pc._run_primed_and_wait([("a", 0.01), ("b", 0.01), ("c", 0.01)], run))
    assert ev[:2] == [("start", "a"), ("end", "a")]
    assert set(ev[2:4]) == {("start", "b"), ("start", "c")}
    assert len(ev) == 6, "it must WAIT for the fan-out — the chain re-assembles afterwards"


def test_the_endpoint_syncs_dispatches_primed_waits_and_reassembles_through_the_one_assembly():
    for needle in ("_fix_reasons(sess, ctx, code)", "_chunks_from_code(code, ctx)",
                   "asyncio.create_task(_chain())", "await _run_primed_and_wait(prepared, _one)",
                   "_assemble_and_store, key, fresh, ctx, group, name", '"pt_fix_unit"',
                   '"unmapped": reasons["unmapped"]', 'step6_f["fix_units"] = record',
                   'Semaphore(_PT_UNIT_DISPATCH_MAX)', "await run_in_threadpool(_unit_call_and_store"):
        assert needle in FIX_UNITS, needle
    assert "_parse_generated_blocks" not in FIX_UNITS, "shape-check/store stays in _unit_call_and_store"
    assert "_assemble_and_store(key, sess, ctx, group, name)" in ASSEMBLE, \
        "assemble_script and the fix chain must share one assembly implementation"


def test_the_unit_call_records_which_template_it_served():
    body = _CODE[_CODE.index("def _unit_call_and_store"):_CODE.index("def _dispatch_primed")]
    assert 'template: str = "(verbatim)"' in body and "template=template" in body


# --- the gate ---------------------------------------------------------------------------------

def test_review_refuses_while_lint_has_blocking_errors():
    msg = pc._lint_blocks_review({"lint": {"errors": ["structure: TestCase_2 missing testCaseDesc"]}})
    assert msg and "blocking" in msg and "Fix units" in msg
    assert "_lint_blocks_review(step6)" in REVIEW and "409" in REVIEW


def test_policy_errors_and_warnings_do_not_gate_review():
    assert pc._lint_blocks_review({"lint": {"errors": ["contract: TestCase_1.main() has no self.log()"],
                                            "warnings": ["pep8 E501: long"]}}) is None
    assert pc._lint_blocks_review({"lint": {"errors": []}}) is None
    assert pc._lint_blocks_review({}) is None
