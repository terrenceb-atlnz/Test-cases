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


# --- guardrails tranche 1 (PLAN-fix-units-guardrails: G1, G5, G8(a); 2026-09-14) ----------------

# The real dict: T44297 review #2 finding 5 (debug log sess-pjkmca6yz2, 2026-09-09 02:58 UTC).
# `where` says the suite setup; the evidence prose mentions TestCase_1; the fixer rewrote tc1.
FINDING_5 = {
    "severity": "low", "kind": "other", "where": "TestSet.configure", "step": "1",
    "what": "Step 1's verify (show lldp running, test port enabled tx/rx, status connected, at "
            "least one decodable LLDPDU) is folded into the suite configure() which has no "
            "pass/fail, so no verdict ever demonstrates it; TestCase_1 begins at Step 2.",
    "evidence": "configure(): dutA.cmd('lldp run') ... wait_for_port_link_up(self, dutA, [portA, "
                "portPeer])   (no self.passed/self.failed; TestCase_1 logs 'STEP 1' but its "
                "testCaseDesc is the Step 2 port-description action)",
    "suggestion": "Assert Step 1's observable conditions (show lldp running, show lldp interface "
                  "tx/rx enabled, show interface status connected, one decodable captured LLDPDU) "
                  "in a case with pass/fail rather than leaving them as un-verified setup.",
}
# The real dict: T44297 review #1 finding 3 — a FIXABLE finding on a case unit whose
# suggestion starts with "Add" (must not read as "add a case").
FINDING_R1_3 = {
    "severity": "medium", "kind": "duplicate_setup", "where": "TestCase_2.configure", "step": "4",
    "what": "Step 12 depends on a Management Address TLV appearing on the wire, but this case "
            "configures only `lldp management-address` and never selects the management-address TLV.",
    "evidence": "dutA.cmd('lldp management-address {}'.format(self.old_mgmt_addr))",
    "suggestion": "Add `dutA.cmd('lldp tlv-select management-address')` in configure() (as "
                  "TestCase_5/8/9/10 do) so the Management Address TLV is actually transmitted.",
}


def test_G1_where_is_authoritative_evidence_prose_cannot_hijack_the_target():
    assert pc._unit_id_for_finding(FINDING_5, CTX, UNITS) == "setup"          # never tc1
    # `where` names tc2; the evidence quotes the suite — where wins.
    assert pc._unit_id_for_finding({"where": "TestCase_2.main", "step": None,
                                    "evidence": "TestSet.configure() issues lldp run"},
                                   CTX, UNITS) == "tc2"
    # A `where` on the suite can NEVER yield a TestCase, whatever else the line says.
    assert pc._unit_id_for_finding({"where": "TestSet.configure vs TestCase_2", "step": None},
                                   CTX, UNITS) == "setup"


def test_G1_evidence_then_step_are_fallbacks_only_when_where_names_nothing():
    assert pc._unit_id_for_finding({"where": "(script)", "step": None,
                                    "evidence": "TestCase_2: self.failed('bad')"}, CTX, UNITS) == "tc2"
    assert pc._unit_id_for_finding({"where": "(script)", "step": "3", "evidence": ""},
                                   CTX, UNITS) == "tc1"
    assert pc._unit_id_for_finding({"where": "", "step": None, "evidence": ""}, CTX, UNITS) is None


def test_G5_a_verdict_asked_of_the_config_only_setup_is_structural():
    # D3 (2026-09-11): ALWAYS structural — the setup unit is config-only by contract.
    assert pc._structural_reason(FINDING_5, "setup")
    # The same words aimed at a TestCase are an ordinary fix.
    assert pc._structural_reason({**FINDING_5, "where": "TestCase_2.main"}, "tc2") is None


def test_G5_the_reviewers_structural_tag_and_an_add_a_case_suggestion_route_to_a_human():
    assert pc._structural_reason({"kind": "structural", "what": "x", "suggestion": ""}, "tc2")
    assert pc._structural_reason({"kind": "other", "what": "x",
                                  "suggestion": "Split this into a new TestCase for step 5"}, "tc2")
    assert pc._structural_reason({"kind": "other", "what": "x",
                                  "suggestion": "Move this check into its own case"}, "tc2")
    # "Add `dutA.cmd(...)`" and "case-specific" are not "add a case".
    assert pc._structural_reason(FINDING_R1_3, "tc2") is None
    assert pc._structural_reason({"kind": "other", "what": "x",
                                  "suggestion": "add a case-specific settle before the read"}, "tc2") is None


def test_G5_structural_findings_are_reported_with_their_reason_and_never_dispatched():
    s = _sess()
    s.step6["review"]["findings"] = [FINDING_5, FINDING_R1_3]
    r = pc._fix_reasons(s, CTX, SCRIPT)
    assert "setup" not in r["per_unit"]                                # not a target
    assert [f["where"] for f in r["per_unit"]["tc2"]["review"]] == ["TestCase_2.configure"]
    assert len(r["structural"]) == 1
    assert r["structural"][0].startswith("structural: TestSet.configure — ")
    assert "config-only suite setup" in r["structural"][0]
    assert not any(u.startswith("structural") for u in r["unmapped"])  # kept apart from unmapped
    # The endpoint refuses to dispatch on structural-only reasons and says why; and it
    # returns / records the list for the UI.
    assert 'reasons["structural"]' in FIX_UNITS
    assert "need a design" in FIX_UNITS
    assert '"structural": reasons["structural"]' in FIX_UNITS


def test_G8a_the_suites_configure_body_is_lifted_verbatim_and_dedented():
    setup_text = "\n".join(SCRIPT.split("\n")[
        _line_of("    def configure(self):") - 1:_line_of("        pass")])
    body = pc._configure_method_of(setup_text)
    assert body == "def configure(self):\n    self.dut.cmd('lldp run')"
    assert pc._configure_method_of("class X:\n    pass") == ""


def test_G8a_the_assembled_script_wins_then_the_setup_chunk_then_nothing():
    s = pc.PtSession(key="AWPTCM-T1")
    assert pc._suite_setup_body(s) == ""
    s.step6 = {"chunks": {"setup": {"status": "ok", "code":
               "    def configure(self):\n        self.dut.cmd('from chunk')\n\n    def tear_down(self):\n        pass"}}}
    assert "from chunk" in pc._suite_setup_body(s)
    s.step6["files"] = {"test": {"name": "t.py", "code": SCRIPT}}
    assert pc._suite_setup_body(s) == "def configure(self):\n    self.dut.cmd('lldp run')"
    s.step6["chunks"]["setup"]["status"] = "error"
    s.step6["files"] = {}
    assert pc._suite_setup_body(s) == ""                                # a failed chunk is not shown


def test_G8a_the_prompt_shows_the_setup_body_in_the_SHARED_half_with_the_never_undo_rule():
    ctx = {"case_key": "AWPTCM-T1", "case_title": "t", "mode": "testcase", "tc_n": 2,
           "source_n": 4, "step": {"action": "a", "verify": "v"}, "setup_steps": [],
           "blank_block": "class TestCase_2: ...", "fragments": [], "shared_fragments": [],
           "shared_tags_for_unit": [], "shared_cli_reference": "", "devices": ["dut"],
           "bound_devices": ["dut"], "bound_ports": [], "library": None,
           "library_tags_for_unit": [], "framework_surface": {}, "cli_reference": "",
           "device_note": "", "py2_flagged": False, "rules_cli_reference": False,
           "split_marker": pc._PT_PROMPT_SPLIT, "model_name": "m", "gen_date": "2026-09-14",
           "suite_setup_body": "def configure(self):\n    self.dut.cmd('lldp run')"}
    p = render_prompt("pt_generate_step.jinja", ctx)
    shared, unit_half = pc._split_unit_prompt(p)
    assert "## Given by `TestSet.configure()` — never re-issue, never undo" in shared
    assert "self.dut.cmd('lldp run')" in shared and "never undo" in shared
    assert "Given by" not in unit_half
    # The SELF-CONTAINED rule now carves the suite's state out explicitly.
    assert "OTHER TEST CASES' state, never the" in shared
    # Without a setup body there is no block, and the rule falls back to plain wording.
    p0 = render_prompt("pt_generate_step.jinja", {**ctx, "suite_setup_body": ""})
    assert "Given by" not in p0
    # The setup unit's own prompt says the block is ITS current version, not a constraint.
    ps = render_prompt("pt_generate_step.jinja", {**ctx, "mode": "setup",
                       "setup_steps": [{"n": 1, "action": "cfg"}]})
    assert "binds the test cases, not you" in pc._split_unit_prompt(ps)[1]


def test_G8a_the_fix_rule_says_a_precondition_the_suite_owns_is_not_missing():
    p = render_prompt("pt_fix_unit.jinja", {"unit_label": "TestCase_2", "kind": "testcase",
                                            "current_code": "x", "lint_errors": [],
                                            "review_findings": [], "run_result": None,
                                            "log_excerpt": ""})
    assert "neither `TestSet.configure()`" in p
    assert "Never\n  re-issue a command the suite setup issues" in p
    assert "breaks every case after this one" in p


def test_G8a_the_generation_context_carries_the_body_and_the_render_passes_it():
    body = _SRC
    ctx_fn = body[body.index("def _pt_generation_context"):body.index("def _fragments_for_unit")]
    assert '"suite_setup_body": _suite_setup_body(sess)' in ctx_fn
    render = body[body.index("def _render_unit_prompt"):body.index("def _unit_shape_ok")]
    assert '"suite_setup_body": ctx.get("suite_setup_body")' in render


# --- G4: untouched units are never written (RC3; 2026-09-14) ------------------------------------

def test_G4_only_a_hand_edited_unit_is_rewritten_the_others_keep_their_record_byte_for_byte():
    synced = pc._chunks_from_code(SCRIPT, CTX)
    stored = {uid: {"status": "ok", "code": text, "error": "", "at": f"2026-09-09T0{i}:00:00",
                    "prompt": "kept"} for i, (uid, text) in enumerate(synced.items())}
    # tc2 was hand-edited on screen (the plan's "fix targeting tc6 with a hand-edited tc9").
    edited = dict(synced); edited["tc2"] = synced["tc2"].replace("self.failed('bad')", "self.failed('worse')")
    out, changed = pc._resync_chunks(stored, edited)
    assert changed == ["tc2"]
    assert out["tc2"]["code"] == edited["tc2"] and out["tc2"]["at"] != stored["tc2"]["at"]
    assert out["tc2"]["source"] == "script" and out["tc2"]["prompt"] == "kept"   # record updated, not replaced
    assert out["tc1"] is stored["tc1"] and out["setup"] is stored["setup"]       # the very same records
    assert out["tc1"]["at"] == "2026-09-09T01:00:00"


def test_G4_a_unit_never_stored_or_stored_failed_is_synced_from_the_script():
    synced = pc._chunks_from_code(SCRIPT, CTX)
    stored = {"tc1": {"status": "error", "code": "", "error": "boom", "at": "x"}}
    out, changed = pc._resync_chunks(stored, synced)
    assert sorted(changed) == ["setup", "tc1", "tc2"]
    assert out["tc1"]["status"] == "ok" and out["tc1"]["error"] == "" and out["tc1"]["code"] == synced["tc1"]


def test_G4_nothing_changed_means_no_write_at_all():
    synced = pc._chunks_from_code(SCRIPT, CTX)
    stored = {uid: {"status": "ok", "code": text, "at": "t"} for uid, text in synced.items()}
    out, changed = pc._resync_chunks(stored, synced)
    assert changed == [] and out == stored
    # The endpoint persists the sync only when something differs or a stale fix_units
    # record needs clearing — an unchanged script is not a reason to rewrite the row.
    assert "_resync_chunks(step6.get(\"chunks\") or {}, synced)" in FIX_UNITS
    assert 'if changed or "fix_units" in step6:' in FIX_UNITS
    assert 'prev.update({"status": "ok", "code": text, "error": ""})' not in FIX_UNITS


# --- G2 + G6: verify before store (RC2, RC4; 2026-09-14) ----------------------------------------

def _unit(uid):
    return next(u for u in UNITS if u["id"] == uid)


def test_G2_the_frozen_lines_are_the_frame_lines_the_current_unit_still_carries():
    cur = pc._chunks_from_code(SCRIPT, CTX)["tc1"]
    frozen = pc._unit_frozen_lines(_unit("tc1"), cur)
    assert "class TestCase_1(ATTestCase.TestCase):" in frozen
    assert "    testCaseDesc = 'one'" in frozen and "    testCaseMethod = 'one'" in frozen
    assert "    def main(self):" in frozen
    assert "        # ART a.py:x" in frozen                      # the provenance tag, from the CURRENT unit
    assert not any("self.log" in ln or "passed" in ln for ln in frozen)   # bodies are the model's
    # A frame line the reviewer already hand-edited away is not enforced.
    edited = cur.replace("    testCaseRef = 'AWPTCM-T1'", "    testCaseRef = 'AWPTCM-T9'")
    assert "    testCaseRef = 'AWPTCM-T1'" not in pc._unit_frozen_lines(_unit("tc1"), edited)


def test_G2_a_reply_that_alters_a_frozen_line_is_refused_and_a_body_change_is_not():
    cur = pc._chunks_from_code(SCRIPT, CTX)["tc1"]
    ok, why = pc._unit_frozen_ok(cur, cur.replace("self.log('one')", "self.log('STEP 1: one')"), _unit("tc1"))
    assert ok, why
    for bad, needle in ((cur.replace("testCaseRef = 'AWPTCM-T1'", "testCaseRef = 'AWPTCM-T2'"), "testCaseRef"),
                        (cur.replace("    def main(self):", "    def main(self, x=None):"), "def main"),
                        (cur.replace("        # ART a.py:x\n", ""), "# ART a.py:x")):
        ok, why = pc._unit_frozen_ok(cur, bad, _unit("tc1"))
        assert not ok and "frozen line" in why and needle in why, (needle, why)


def test_G2_the_setup_pair_is_compared_stripped_because_assembly_rebases_its_indent():
    cur = pc._chunks_from_code(SCRIPT, CTX)["setup"]
    flush = "\n".join(ln.lstrip() if ln.lstrip().startswith("def ") else ln for ln in cur.split("\n"))
    ok, why = pc._unit_frozen_ok(cur, flush, _unit("setup"))
    assert ok, why
    ok, why = pc._unit_frozen_ok(cur, cur.replace("def tear_down(self):", "def teardown(self):"), _unit("setup"))
    assert not ok and "def tear_down" in why


def _guard_for(uid):
    s = pc.PtSession(key="AWPTCM-T1")
    s.step6 = {"files": {"test": {"name": "t.py", "code": SCRIPT}}}
    s.step2 = {"sequence": [{"n": 1, "action": "cfg", "kind": "setup"}, *TC_STEPS]}
    baseline = pc._lint_generated(s)["errors"]
    return {"current_code": pc._chunks_from_code(SCRIPT, CTX)[uid], "assembled_code": SCRIPT,
            "sess": s, "baseline_errors": baseline}


def test_G6_a_reply_that_stops_the_script_compiling_is_refused_an_unchanged_one_is_not():
    g = _guard_for("tc2")
    assert pc._unit_lint_regression(g, g["current_code"], _unit("tc2")) is None
    broken = g["current_code"].replace("self.failed('bad')", "self.failed('bad'")
    why = pc._unit_lint_regression(g, broken, _unit("tc2"))
    assert why and "introduces lint error" in why and "syntax" in why
    # A lint error the CURRENT script already carries is not held against the fix.
    assert g["baseline_errors"], "the fixture script is meant to carry baseline errors"
    assert pc._unit_lint_regression(g, g["current_code"], _unit("tc2")) is None


def test_G6_a_regression_in_ANOTHER_unit_is_not_attributed_to_this_one():
    g = _guard_for("tc2")
    # tc2's reply is fine; the error the baseline lacks lives in tc1 — not this unit's doing.
    g["baseline_errors"] = [e for e in g["baseline_errors"] if "TestCase_1" not in e]
    assert pc._unit_lint_regression(g, g["current_code"], _unit("tc2")) is None


def test_G6_the_store_path_verifies_only_when_a_guard_is_given_and_the_fix_passes_one():
    body = _CODE[_CODE.index("def _unit_call_and_store"):_CODE.index("def _dispatch_primed")]
    assert "guard: Optional[dict] = None" in body
    assert body.index("_unit_shape_ok(code, unit)") < body.index("_unit_frozen_ok(") < body.index("_unit_lint_regression(")
    assert body.index("_unit_lint_regression(") < body.index('_store({"status": "ok"')
    assert 'guards = {uid: {"current_code": synced[uid], "assembled_code": code' in FIX_UNITS
    assert '"pt_fix_unit", guards.get(uid)' in FIX_UNITS
    assert "baseline_errors = _lint_generated(sess)" in FIX_UNITS      # computed when not stored


# --- G8(b): suite-owned commands (RC6; 2026-09-14) ----------------------------------------------

# The REAL shapes: TestSet.configure()/tear_down() of the T44297 script (Management/261_…),
# and TestCase_1 as fix run 5 returned it (debug log sess-pjkmca6yz2, 2026-09-09 03:19 UTC):
# `dutA.cmd('lldp run')` added to configure(), `dutA.cmd('no lldp run')` to tear_down().
SUITE_OWNED_SCRIPT = """import sys
from framework import ATTestSet, ATTestCase


class TestSet(ATTestSet.TestSet):
    def init(self, setup):
        self.dutA = setup.init_swi('swi_a')
        self.peer = setup.init_swi('swi_b')

    def configure(self):
        dutA = self.dutA
        peer = self.peer
        portA = dutA.portA
        portPeer = dutA.portPeer
        portDut = peer.portDut
        dutA.mode(')#')
        dutA.cmd('lldp run')
        dutA.cmd('interface {},{}'.format(portA.name, portPeer.name))
        dutA.cmd('lldp transmit')
        dutA.cmd('lldp receive')
        dutA.mode('#')
        peer.mode(')#')
        peer.cmd('lldp run')
        peer.cmd('interface {}'.format(portDut.name))
        peer.cmd('lldp transmit')
        peer.mode('#')

    def tear_down(self):
        dutA = self.dutA
        peer = self.peer
        dutA.mode(')#')
        dutA.cmd('no lldp run')
        dutA.mode('#')
        peer.mode(')#')
        peer.cmd('no lldp run')
        peer.mode('#')


class TestCase_1(ATTestCase.TestCase):
    testCaseDesc = 'one'
    testCaseRef = 'AWPTCM-T44297'
    testCaseMethod = 'one'
    PORT_DESC_STR = 'lldpTlvT44297desc'

    def configure(self):
        dutA = self.testSet.dutA
        portA = dutA.portA
        dutA.mode(')#')
        dutA.cmd('lldp run')
        dutA.cmd('interface {}'.format(portA.name))
        dutA.cmd('description {}'.format(self.PORT_DESC_STR))
        dutA.cmd('lldp tlv-select port-description')
        dutA.mode('#')

    def main(self):
        # ART 1331_past_issues/test-1331.1001.py lines 760-784
        self.log('STEP 2')
        self.passed('ok')

    def tear_down(self):
        dutA = self.testSet.dutA
        portA = dutA.portA
        dutA.mode(')#')
        dutA.cmd('interface {}'.format(portA.name))
        dutA.cmd('no lldp tlv-select port-description')
        dutA.cmd('no description')
        dutA.mode(')#')
        dutA.cmd('no lldp run')
        dutA.mode('#')


class TestCase_2(ATTestCase.TestCase):
    testCaseDesc = 'two'
    testCaseRef = 'AWPTCM-T44297'
    testCaseMethod = 'two'

    def configure(self):
        dutA = self.testSet.dutA
        peer = self.testSet.peer
        portA = dutA.portA
        dutA.mode(')#')
        dutA.cmd('interface {}'.format(portA.name))
        dutA.cmd('lldp tlv-select management-address')
        dutA.cmd(f'lldp management-address {portA.name}')
        dutA.cmd('show lldp')
        peer.cmd('lldp receive')
        dutA.mode('#')

    def main(self):
        # AI
        self.log('STEP 3')
        self.passed('ok')

    def tear_down(self):
        pass


if __name__ == '__main__':
    ts = TestSet()
    ts.add_testCase(TestCase_1)
    ts.add_testCase(TestCase_2)
    ts.run(sys.argv)
"""


def test_G8b_the_lint_names_exactly_the_two_lines_tc1_gained_and_nothing_case_specific():
    import ast
    errs = pc._lint_suite_owned_commands(ast.parse(SUITE_OWNED_SCRIPT), SUITE_OWNED_SCRIPT)
    assert len(errs) == 2, errs
    reissue = next(e for e in errs if "re-issues" in e)
    undo = next(e for e in errs if "undoes" in e)
    assert "TestCase_1.configure()" in reissue and "`lldp run` on dutA" in reissue and "TestSet.configure()" in reissue
    assert "TestCase_1.tear_down()" in undo and "undoes `lldp run` (`no lldp run`) on dutA" in undo
    assert "breaks every case after this one" in undo
    # tlv-select (case-specific), `interface …` (navigation), `show`, and `lldp receive` on a
    # DIFFERENT device than the suite issued it on are all left alone.
    assert not any("tlv-select" in e or "interface" in e or "show" in e or "TestCase_2" in e for e in errs)


def test_G8b_is_a_policy_error_the_reviewer_may_override_and_the_linter_raises_it():
    import ast
    errs = pc._lint_suite_owned_commands(ast.parse(SUITE_OWNED_SCRIPT), SUITE_OWNED_SCRIPT)
    blocking, policy = pc._split_lint_errors(errs)
    assert policy == errs and blocking == []
    s = pc.PtSession(key="AWPTCM-T44297")
    s.step6 = {"files": {"test": {"name": "t.py", "code": SUITE_OWNED_SCRIPT}}}
    s.step2 = {"sequence": [{"n": 1, "action": "cfg", "kind": "setup"},
                            {"n": 2, "action": "a", "verify": "v"}, {"n": 3, "action": "b", "verify": "w"}]}
    lint = pc._lint_generated(s)
    assert [e for e in lint["errors"] if e.startswith("suite-owned:")] == errs


def test_G8b_through_G6_the_fix_run_5_reply_is_refused_and_the_current_tc1_kept():
    """The whole point, end to end: fix run 5's tc1 (the two suite-owned lines) arrives at the
    store path with a guard whose baseline is the CURRENT script (which has no such error) —
    it is refused as a lint regression, so the current chunk stays."""
    # The current script = the same file with tc1's two offending lines removed.
    current = SUITE_OWNED_SCRIPT.replace("        dutA.cmd('lldp run')\n        dutA.cmd('interface {}'.format(portA.name))\n        dutA.cmd('description",
                                         "        dutA.cmd('interface {}'.format(portA.name))\n        dutA.cmd('description")
    current = current.replace("        dutA.mode(')#')\n        dutA.cmd('no lldp run')\n        dutA.mode('#')\n\n\nclass TestCase_2",
                              "        dutA.mode('#')\n\n\nclass TestCase_2")
    assert "TestCase_1" in current and current.count("lldp run") == 4   # only the suite's four remain
    s = pc.PtSession(key="AWPTCM-T44297")
    s.step6 = {"files": {"test": {"name": "t.py", "code": current}}}
    s.step2 = {"sequence": [{"n": 1, "action": "cfg", "kind": "setup"},
                            {"n": 2, "action": "a", "verify": "v"}, {"n": 3, "action": "b", "verify": "w"}]}
    units = pc._skeleton_units(current)
    tc1 = next(u for u in units if u["id"] == "tc1")
    cur_tc1 = pc._chunks_from_code(current, {"units": units})["tc1"]
    fix5_tc1 = pc._chunks_from_code(SUITE_OWNED_SCRIPT, {"units": pc._skeleton_units(SUITE_OWNED_SCRIPT)})["tc1"]
    guard = {"current_code": cur_tc1, "assembled_code": current, "sess": s,
             "baseline_errors": pc._lint_generated(s)["errors"]}
    ok, _ = pc._unit_frozen_ok(cur_tc1, fix5_tc1, tc1)
    assert ok                                                # the frame lines were kept — G2 passes it
    why = pc._unit_lint_regression(guard, fix5_tc1, tc1)
    assert why and "suite-owned" in why and "no lldp run" in why   # G6 + G8(b) refuse it

