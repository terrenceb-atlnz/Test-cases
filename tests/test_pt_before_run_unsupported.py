"""Not-applicable cases are skipped BEFORE they run (ask-ck/plans/PLAN-unsupported-gating.md).

A case that learns inside its own main() that it does not apply reports UNSUPPORTED, and the
framework then power-cycles every device on the bench (~4 min on tb470; T33235 run 1 paid five
cycles, run 4 one). The TestSet runs a case only while its `supported` is True (read from
`/home/st-art/framework/ATTestSet.py` on tb470, 2026-10-02), so a case marked before its turn
is skipped with no cycle. Until 2026-10-02 that existed only as hand edits (T33234 `d9a08dd`,
T33235 `3454bc0` / `056114d`); now the generator emits it:

  kind A   a link the bench lacks  -> the frame sets `dut.has_<role>_link`; the case carries a
           `testCasePlatformWithPropertyIncl` gate (BLOCKING lint `rolegate:`)
  kind B1  a published value is None -> the producer's `publish_value(self, name, None)` marks
           every case whose class lists it in `ckNeeds` (BLOCKING lint `needs:`)
  kind B2  a condition on an earlier result -> the producer's `mark_cases_unsupported(...)`
           (WARNING lint `marks:`, Review check)
  and the run reader reports a skipped case as UNSUPPORTED, not run — not as a missing case.

Pinned against real shapes: the rendered frame, its helpers executed against stand-in
TestSet/TestCase objects, both real generated scripts, and the T33234 run-3 log (14 cases
dropped by the marking pass) trimmed into tests/fixtures/.
"""
import ast
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SERVER = _REPO / "ask-ck" / "CK-main" / "CK_server"
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(_SERVER))

from llm import render_prompt  # noqa: E402
from routers import pytest_create as pc  # noqa: E402
import pt_exec  # noqa: E402

_P = _SERVER / "templates" / "prompts"
_GEN = _REPO / "ask-ck" / "functions" / "pytest-creator" / "generated" / "9001_Port"
_FIX = Path(__file__).resolve().parent / "fixtures"


def _flat(s):
    return " ".join(s.split())


# --- the frame ------------------------------------------------------------------------------

_SEQ_PUB = [
    {"n": 1, "action": "find the highest speed S on the fibre module and the copper SFP with the "
                       "neighbour switch", "verify": "S found", "kind": "verify",
     "publishes": [{"name": "speedS", "shape": "int Mbps"}]},
    {"n": 2, "action": "force S on the fibre module", "verify": "link up at S", "kind": "verify"},
]


def _skeleton(seq):
    return pc._render_skeleton("AWPTCM-T99999", "probe", [dict(s) for s in seq], [], [])


def test_the_frame_defines_both_helpers_only_when_the_sequence_publishes():
    sk = _skeleton(_SEQ_PUB)
    compile(sk, "sk.py", "exec")
    tops = {n.name for n in ast.parse(sk).body if isinstance(n, ast.FunctionDef)}
    assert {"mark_cases_unsupported", "publish_value"} <= tops
    plain = _skeleton([{"n": 1, "action": "read the port", "verify": "x", "kind": "verify"}])
    assert "def publish_value" not in plain and "def mark_cases_unsupported" not in plain


def test_init_sets_the_role_properties_the_gates_read():
    sk = _skeleton(_SEQ_PUB)
    init = sk[sk.index("    def init(self, setup):"):sk.index("    def configure(self)")]
    assert "dut.has_fibre_link = self.fibre_supported" in init
    assert "dut.has_cusfp_link = self.cusfp_supported" in init
    props = pc._init_device_properties(ast.parse(sk))
    assert props["has_fibre_link"] == {"attr": "dut", "roles": {"fibre"}}
    assert props["has_cusfp_link"] == {"attr": "dut", "roles": {"cusfp"}}


class _TS:
    def __init__(self, cases):
        self.testCaseList = cases
        for c in cases:
            c.testSet = self


class _TC:
    supported = True
    hasBeenRun = False

    def __init__(self):
        self.logged = []

    def log(self, msg):
        self.logged.append(msg)


def _helpers():
    """The helper functions exactly as the frame renders them."""
    tree = ast.parse(_skeleton(_SEQ_PUB))
    mod = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)
                           and n.name in ("mark_cases_unsupported", "publish_value")], type_ignores=[])
    ns = {}
    exec(compile(mod, "helpers", "exec"), ns)
    return ns


def _cases():
    TestCase_1 = type("TestCase_1", (_TC,), {})
    TestCase_2 = type("TestCase_2", (_TC,), {"ckNeeds": ["speedS"]})
    TestCase_3 = type("TestCase_3", (_TC,), {})
    TestCase_4 = type("TestCase_4", (_TC,), {"ckNeeds": ["speedS"]})
    cs = [TestCase_1(), TestCase_2(), TestCase_3(), TestCase_4()]
    _TS(cs)
    return cs


def test_publishing_None_marks_every_case_that_needs_it_and_nothing_else():
    h = _helpers()
    c1, c2, c3, c4 = _cases()
    c4.hasBeenRun = True                 # already ran (run-priority order): never re-marked
    h["publish_value"](c1, "speedS", None)
    assert c1.testSet.speedS is None
    assert (c2.supported, c3.supported, c4.supported) == (False, True, True)
    assert c1.logged == ["INFO: TestCase_2 marked unsupported before it runs: "
                         "speedS was not established by TestCase_1"]


def test_publishing_a_value_marks_nothing():
    h = _helpers()
    c1, c2, c3, c4 = _cases()
    h["publish_value"](c1, "speedS", 1000)
    assert c1.testSet.speedS == 1000 and all(c.supported for c in (c2, c3, c4)) and not c1.logged


def test_marking_names_explicit_cases_once():
    h = _helpers()
    c1, c2, c3, _ = _cases()
    h["mark_cases_unsupported"](c1, ["TestCase_3"], "the sweep recorded no rejected speed")
    h["mark_cases_unsupported"](c1, ["TestCase_3"], "again")
    assert not c3.supported and c2.supported and len(c1.logged) == 1


def test_the_frames_log_line_is_the_one_the_run_reader_parses():
    h = _helpers()
    c1, *_ = _cases()
    h["publish_value"](c1, "speedS", None)
    log = ">> test-9001.1.1\n" + "\n".join(c1.logged) + \
          "\n<< test-9001.1.1: FAIL (numPassed: 0 numFailed: 1)\n"
    r = pt_exec.parse_framework_log(log, expected_cases=4)
    assert r["not_run_cases"] == ["9001.1.2", "9001.1.4"]


# --- kind A: the class gate ---------------------------------------------------------------------

_INIT = '''
class TestSet(ATTestSet.TestSet):
    def init(self, setup):
        dut = setup.init_swi('swi_a')
        self.dut = dut
        fibre_peer = None
        self.fibre_supported = fibre_peer is not None
        dut.has_fibre_link = self.fibre_supported
        dut.has_monitored_link = self.cusfp_supported or self.fibre_supported


'''

_GUARDED_MAIN = '''
    def main(self):
        fibre_peer = self.testSet.fibre_peer
        portFibre = self.testSet.dut.portFibre
        if not self.testSet.fibre_supported or fibre_peer is None:
            self.supported = False
            self.failed('no fibre link')
            return
        self.passed('ok')
'''


def _gate(attrs, main=_GUARDED_MAIN):
    return pc._lint_before_run_gate(ast.parse(_INIT + "class TestCase_1(ATTestCase.TestCase):\n"
                                              + attrs + main))


def test_A_a_fibre_guard_without_the_gate_is_blocking():
    errs, _ = _gate("    testCaseRef = 'K'\n")
    assert len(errs) == 1 and errs[0].startswith("rolegate: TestCase_1.main() line")
    assert "has_fibre_link" in errs[0]


def test_A_the_gate_the_fill_rules_teach_is_clean():
    rules = _flat((_P / "pt_fill_rules.jinja").read_text(encoding="utf-8"))
    taught = "testCasePlatformWithPropertyIncl = {'<dut>': [(['.*'], ['has_fibre_link'])]}"
    assert taught in rules
    attrs = ("    " + taught.replace("'<dut>'", "'dut'") + "\n    skipIfExcl = True\n")
    assert _gate(attrs) == ([], [])


def test_A_a_property_init_computes_from_the_role_flag_counts():
    attrs = ("    testCasePlatformWithPropertyIncl = {'dut': [(['.*'], ['has_monitored_link'])]}\n"
             "    skipIfExcl = True\n")
    errs, _ = _gate(attrs)
    assert errs == []


def test_A_a_gate_the_framework_cannot_use_is_blocking():
    for attrs, word in (
            ("    testCasePlatformWithPropertyIncl = {'swi_a': [(['.*'], ['has_fibre_link'])]}\n"
             "    skipIfExcl = True\n", "getattr(testSet, key)"),
            ("    testCasePlatformWithPropertyIncl = {'dut': [(['.*'], ['has_fibre'])]}\n"
             "    skipIfExcl = True\n", "never sets on a device"),
            ("    testCasePlatformWithPropertyIncl = {'dut': [(['IE520'], ['has_fibre_link'])]}\n"
             "    skipIfExcl = True\n", "suite owners"),
            ("    testCasePlatformWithPropertyIncl = {'dut': [(['.*'], ['has_fibre_link'])]}\n",
             "skipIfExcl = True"),
            ("    testCasePlatformWithPropertyIncl = PROPS\n    skipIfExcl = True\n", "shape")):
        errs, _ = _gate(attrs)
        assert any(word in e for e in errs), (attrs, errs)


def test_A_a_case_gated_on_a_link_it_never_uses_warns():
    attrs = ("    testCasePlatformWithPropertyIncl = {'dut': [(['.*'], ['has_fibre_link'])]}\n"
             "    skipIfExcl = True\n")
    main = ("\n    def main(self):\n        fibre_peer = self.testSet.fibre_peer\n"
            "        self.passed('copper only')\n")
    errs, warns = _gate(attrs, main)
    assert errs == [] and len(warns) == 1 and warns[0].startswith("rolegate: TestCase_1 is gated")


def test_A_both_hand_finished_scripts_already_satisfy_it():
    for f in ("test-9001.33234.py", "test-9001.33235.py"):
        errs, warns = pc._lint_before_run_gate(ast.parse((_GEN / f).read_text(encoding="utf-8")))
        assert errs == [] and warns == [], (f, errs, warns)


# --- kind B: published values ---------------------------------------------------------------

_PUB = [{"name": "speedS", "shape": "int", "tc_n": 1, "orig_n": 2}]


def _marks(body, published=_PUB, contributors=None):
    return pc._lint_before_run_marks(ast.parse(body), published, contributors)


_PRODUCER = ("class TestCase_1:\n    def main(self):\n"
             "        publish_value(self, 'speedS', None)\n\n\n")


def test_B1_a_producer_that_never_publishes_through_the_helper_is_blocking():
    errs, _ = _marks("class TestCase_1:\n    def main(self):\n        self.testSet.speedS = 100\n")
    assert len(errs) == 1 and errs[0].startswith("needs: TestCase_1 publishes `speedS`")


def test_B1_a_consumer_without_ckNeeds_is_blocking_and_with_it_is_clean():
    errs, _ = _marks(_PRODUCER + "class TestCase_2:\n    def main(self):\n"
                     "        x = self.testSet.speedS\n")
    assert len(errs) == 1 and errs[0].startswith("needs: TestCase_2 line")
    errs, warns = _marks(_PRODUCER + "class TestCase_2:\n    ckNeeds = ['speedS']\n    skipIfExcl = True\n\n"
                         "    def main(self):\n        x = self.testSet.speedS\n")
    assert errs == [] and warns == []


def test_B1_a_contributor_that_fills_the_value_in_is_not_a_consumer():
    """T33235: steps 3-13 each add their speed to `speedMap` (`.setdefault(...)`). Skipping them
    when the first producer publishes None would throw away measurements they can still make."""
    pub = [{"name": "speedMap", "shape": "dict", "tc_n": 1}]
    body = ("class TestCase_1:\n    def main(self):\n        publish_value(self, 'speedMap', {})\n\n\n"
            "class TestCase_2:\n    def main(self):\n"
            "        self.testSet.speedMap.setdefault('p', {})['100'] = True\n")
    assert _marks(body, pub, {"speedMap": {1, 2}}) == ([], [])
    errs, _ = _marks(body, pub, {"speedMap": {1}})
    assert len(errs) == 1 and "TestCase_2" in errs[0]


def test_B1_ckNeeds_must_name_an_earlier_published_value_and_carry_skipIfExcl():
    for attrs, word in (("    ckNeeds = ['speedT']\n    skipIfExcl = True\n", "no step publishes"),
                        ("    ckNeeds = ['speedS']\n", "without `skipIfExcl = True`"),
                        ("    ckNeeds = NEEDS\n    skipIfExcl = True\n", "literal list")):
        errs, _ = _marks(_PRODUCER + "class TestCase_2:\n" + attrs + "\n    def main(self):\n        pass\n")
        assert any(word in e for e in errs), (attrs, errs)
    errs, _ = _marks("class TestCase_1:\n    ckNeeds = ['speedS']\n    skipIfExcl = True\n\n"
                     "    def main(self):\n        publish_value(self, 'speedS', 1)\n")
    assert any("does not run before this case" in e for e in errs)


def test_B2_marks_must_name_later_cases_and_the_marked_case_carries_skipIfExcl():
    body = ("SPEED_S_CASES = ['TestCase_3']\n\n\n"
            "class TestCase_2:\n    def main(self):\n"
            "        mark_cases_unsupported(self, SPEED_S_CASES, 'no S')\n"
            "        mark_cases_unsupported(self, ['TestCase_1', 'TestCase_9'], 'x')\n\n\n"
            "class TestCase_1:\n    pass\n\n\nclass TestCase_3:\n    pass\n")
    errs, warns = _marks(body, [])
    assert [w.split("`")[1] for w in warns] == ["TestCase_1", "TestCase_9"]
    assert len(errs) == 1 and errs[0].startswith("needs: TestCase_3 is marked unsupported by TestCase_2")


def test_B_T33235_reads_as_the_hand_finished_file_it_is():
    """Its stored sequence publishes `speedMap` (steps 3-13); the file predates the helpers, so
    the producer and the three real consumers (TC19-21) are reported — and only those."""
    seq = [{"n": 1, "action": "setup", "verify": "", "kind": "setup"}] + [
        {"n": i, "action": "a", "verify": "v", "kind": "verify",
         **({"publishes": [{"name": "speedMap", "shape": "dict"}]} if 3 <= i <= 13 else {})}
        for i in range(2, 36)]
    tree = ast.parse((_GEN / "test-9001.33235.py").read_text(encoding="utf-8"))
    errs, warns = pc._lint_before_run_marks(tree, pc._published_values(seq), pc._value_contributors(seq))
    named = sorted(re.match(r"needs: (TestCase_\d+)", e).group(1) for e in errs)
    assert named == ["TestCase_19", "TestCase_2", "TestCase_20", "TestCase_21"], errs
    assert warns == []


def test_both_lints_run_in_the_lint_and_their_errors_are_blocking():
    src = (_SERVER / "routers" / "pytest_create.py").read_text(encoding="utf-8")
    assert "_gate_errors, _gate_warnings = _lint_before_run_gate(tree)" in src
    assert "tree, _published_values(_seq), _value_contributors(_seq))" in src
    blocking, policy = pc._split_lint_errors(["rolegate: TestCase_1.main() line 3 x",
                                              "needs: TestCase_2 line 4 x"])
    assert len(blocking) == 2 and policy == []


# --- the prompts teach it --------------------------------------------------------------------

def test_the_fill_rules_teach_when_decides_how():
    rules = _flat((_P / "pt_fill_rules.jinja").read_text(encoding="utf-8"))
    for want in ("WHEN a case can know it does not apply decides HOW it says so",
                 "`ckNeeds = ['<name>']` with `skipIfExcl = True`",
                 "`publish_value(self, '<name>', value)`",
                 "`mark_cases_unsupported(self, ['TestCase_<m>'], '<why>')`",
                 "something only THIS case can find out (the probe above) — the in-`main()` pair"):
        assert want in rules, want


def _unit(**kw):
    base = {"case_key": "K", "case_title": "T", "setup_steps": [], "blank_block": "class TestCase_1:\n    pass",
            "devices": ["tb", "dut", "fibre_peer"], "bound_devices": ["tb", "dut"], "fragments": [],
            "framework_surface": {}, "cli_reference": "", "model_name": "m", "gen_date": "d",
            "mode": "testcase", "source_n": 2, "step": {"n": 2, "action": "a", "verify": "v"},
            "publishes_here": [], "published_before": []}
    return _flat(render_prompt("pt_generate_step.jinja", {**base, **kw}))


def test_the_unit_prompt_tells_producer_consumer_and_contributor_apart():
    pub = [{"name": "speedS", "shape": "int", "tc_n": 1}]
    prod = _unit(tc_n=1, publishes_here=pub)
    assert "Publish it with `publish_value(self, '<name>', <value>)`" in prod
    assert "with `None` on every path where it could not" in prod
    cons = _unit(tc_n=2, published_before=pub)
    assert "Name each one this class reads in `ckNeeds = ['<name>', ...]`" in cons
    assert "Not so for" not in cons
    contrib = _unit(tc_n=2, published_before=pub, contributes_here=["speedS"])
    assert "Not so for `speedS`: this step fills it in too" in contrib
    assert "carries the `has_fibre_link` class gate (rule 3)" in prod


def test_the_unit_renderer_passes_the_contributed_names():
    src = (_SERVER / "routers" / "pytest_create.py").read_text(encoding="utf-8")
    seg = src[src.index("def _render_unit_prompt("):src.index("def _unit_shape_ok(")]
    assert '"contributes_here": sorted(' in seg


def test_the_review_checks_B2_and_asks_for_publish_value():
    rv = _flat((_P / "pt_review_script.jinja").read_text(encoding="utf-8"))
    assert "`publish_value(self, '<name>', <value>)` by the producer" in rv
    assert "never calls `mark_cases_unsupported(self, ['TestCase_<m>'], '<why>')`" in rv
    assert "`self.testSet.<name> = <value>` by the producer" not in rv


# --- the run reader --------------------------------------------------------------------------

def test_a_run_whose_every_case_was_dropped_before_running_is_all_UNSUPPORTED_not_NO_RESULTS():
    """T33234 run 3 (tb470, 2026-09-29): the marking pass dropped all 14 cases. Before
    2026-10-02 the reader called this 'NO RESULTS ... NOT a pass'."""
    text = (_FIX / "framework_run_marked_unsupported.log").read_text(encoding="utf-8")
    r = pt_exec.parse_framework_log(text, expected_cases=14)
    assert r["status"] == "ok" and r["results_complete"]
    assert r["counts"] == {"PASS": 0, "FAIL": 0, "UNSUPPORTED": 14, "ERROR": 0}
    assert r["not_run_cases"] == [f"9001.33234.{n}" for n in range(1, 15)]
    first = r["cases"][0]
    assert first["ran"] is False and "has_fixed_copper_port" in first["reason"]
    assert r["verdict"].startswith("cases: 0 passed, 0 failed, 14 unsupported (14 not run) (of 14)")


def test_a_marked_case_that_ran_anyway_keeps_its_own_result():
    """Under -u a marked case runs (skipIfExcl fails it without its methods): its `<<` wins."""
    log = ("Test case 2 has been marked as unsupported on .* platform without property p, for device swi_a\n"
           ">> test-9001.1.1\n<< test-9001.1.1: PASS (numPassed: 1 numFailed: 0)\n"
           ">> test-9001.1.2\n!!FAIL: Skipping TestCase methods because skipIfExcl is set\n"
           "<< test-9001.1.2: UNSUPPORTED (numPassed: 0 numFailed: 1)\n")
    r = pt_exec.parse_framework_log(log, expected_cases=2)
    assert r["not_run_cases"] == [] and [c["result"] for c in r["cases"]] == ["PASS", "UNSUPPORTED"]
    assert "ran" not in r["cases"][1]


def test_a_run_without_marks_reads_exactly_as_before():
    text = (_FIX / "framework_run_pass.log").read_text(encoding="utf-8")
    r = pt_exec.parse_framework_log(text)
    assert r["not_run_cases"] == [] and "not run" not in r["verdict"]


def test_the_run_panel_shows_why_a_case_did_not_run():
    js = (_REPO / "ask-ck" / "frontend" / "ck-main" / "current" / "pytest-creator" / "pytest.js").read_text(
        encoding="utf-8")
    assert "c.ran === false" in js and "'not run: '" in js

