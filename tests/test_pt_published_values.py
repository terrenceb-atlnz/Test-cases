"""G6 / G15 / G10 (PLAN-pt-drive-followups-2026-09-24 §1, §3): values one case passes to another.

AWPTCM-T33235 (2026-09-24): independently generated units invented three schemas for the same
shared record — TestCase_28 wrote `{status_duplex, ...}`, TC29 read `{row, current}`, TC30 read
`{duplex, speed, current}` — so TC29 would fail every port and TC30 compared nothing; 15 units
hard-coded '100'/'1000' instead of reading step 14's S; and when step 14 found no S, 15 units
crashed or sent `speed None`. Nothing declared the value.

Pinned: a sequence step declares `publishes: [{name, shape}]`; it is normalised on extract and
survives a Sequence save; the frame declares it `self.<name> = None` in TestSet.init (and does
not count it as a device); the producer's unit is told to set it; every LATER unit gets its
shape and the None -> UNSUPPORTED rule; the review lists it. G10: each code shape the review
prompt tells a suggestion to use passes the lint.
"""
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SERVER = _REPO / "ask-ck" / "CK-main" / "CK_server"
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(_SERVER))

from llm import render_prompt  # noqa: E402
from routers import pytest_create as pc  # noqa: E402

_P = _SERVER / "templates" / "prompts"
_SRC = (_SERVER / "routers" / "pytest_create.py").read_text(encoding="utf-8")

SEQ = [
    {"n": 1, "action": "base config", "verify": "", "kind": "setup",
     "publishes": [{"name": "nope", "shape": "setup cannot publish"}]},
    {"n": 2, "action": "find the highest common speed S", "verify": "S found", "kind": "verify",
     "publishes": [{"name": "speedS", "shape": "int Mbps: the highest speed both ends accepted"}]},
    {"n": 3, "action": "force S on both ends", "verify": "link up at S", "kind": "verify"},
    {"n": 4, "action": "re-measure", "verify": "x", "kind": "verify",
     "publishes": [{"name": "speedS", "shape": "a second producer is ignored"}]},
]


def test_normalise_accepts_the_shapes_a_model_sends_and_drops_the_rest():
    n = pc._normalize_publishes
    assert n({"name": "speedS", "shape": " int  Mbps "}) == [{"name": "speedS", "shape": "int Mbps"}]
    assert n("baseline") == [{"name": "baseline", "shape": ""}]
    assert n([{"name": "Speed"}, {"name": "x"}, {"name": "dut"}, {"name": "has space"},
              {"name": "ok1"}, {"name": "ok1"}, 7, None]) == [{"name": "ok1", "shape": ""}]
    assert n(None) == [] and n("") == []


def test_published_values_are_TestCase_numbered_and_the_first_producer_wins():
    pub = pc._published_values(SEQ)
    assert pub == [{"name": "speedS", "shape": "int Mbps: the highest speed both ends accepted",
                    "tc_n": 1, "orig_n": 2}]


def test_the_frame_declares_it_in_init_and_does_not_call_it_a_device():
    sk = pc._render_skeleton("AWPTCM-T99999", "probe", [dict(s) for s in SEQ], [], [])
    init = sk[sk.index("    def init(self, setup):"):sk.index("    def configure(self)")]
    assert "self.speedS = None  # set by TestCase_1: int Mbps: the highest speed both ends accepted" in init
    assert "self.nope" not in sk
    assert "speedS" not in pc._skeleton_bound_devices(sk, "dut")
    compile(sk, "sk.py", "exec")


def test_the_producer_is_told_to_set_it_and_later_units_to_read_it_or_report_UNSUPPORTED():
    base = {"case_key": "K", "case_title": "T", "setup_steps": [], "blank_block": "class TestCase_1:\n    pass",
            "devices": ["tb", "dut"], "bound_devices": ["tb", "dut"], "fragments": [],
            "framework_surface": {}, "cli_reference": "", "model_name": "m", "gen_date": "d",
            "mode": "testcase", "source_n": 2, "step": {"n": 2, "action": "a", "verify": "v"}}
    pub = pc._published_values(SEQ)
    prod = render_prompt("pt_generate_step.jinja", {**base, "tc_n": 1, "publishes_here": pub,
                                                     "published_before": []})
    assert "publishes for later cases" in prod and "`self.testSet.speedS`" in prod
    assert "leave it `None` when the step could not" in prod
    cons = render_prompt("pt_generate_step.jinja", {**base, "tc_n": 2, "publishes_here": [],
                                                     "published_before": pub})
    assert "values earlier cases publish" in cons and "(set by TestCase_1)" in cons
    assert "`self.failed('<name> was not established by" in cons
    neither = render_prompt("pt_generate_step.jinja", {**base, "tc_n": 1, "publishes_here": [],
                                                        "published_before": []})
    assert "publishes for later cases" not in neither and "values earlier cases publish" not in neither


def test_the_unit_renderer_splits_before_and_here_by_TestCase_number():
    seg = _SRC[_SRC.index("def _render_unit_prompt("):_SRC.index("def _unit_shape_ok(")]
    assert '"publishes_here": [p for p in published if tc_n is not None and p["tc_n"] == tc_n]' in seg
    assert '"published_before": [p for p in published if tc_n is not None and p["tc_n"] < tc_n]' in seg


def test_extract_teaches_it_and_both_sequence_paths_normalise_and_keep_it():
    ex = (_P / "pt_extract_sequence.jinja").read_text(encoding="utf-8")
    assert '**"publishes"**' in ex and '"publishes": [{"name": "speedS"' in ex
    assert _SRC.count('pubs = _normalize_publishes(s.get("publishes"))') == 2
    assert '("kind", "claim", "zephyr_step_idx", "negative", "publishes")' in _SRC


def test_the_review_lists_published_values_and_checks_their_consumers():
    out = render_prompt("pt_review_script.jinja", {"case_key": "K", "file_name": "f.py", "code": "x",
                                                   "sequence": [], "published": pc._published_values(SEQ)})
    assert "CHECK THEIR CONSUMERS" in out and "`self.testSet.speedS` — set by TestCase_1" in out
    assert '"published": _published_values(sequence)' in _SRC


# --- G10: the shapes the review prompt tells a suggestion to use pass the lint -----------------

_FRAME = '''#!/usr/bin/python3
import sys
from framework import ATTestSet, ATTestCase


class TestSet(ATTestSet.TestSet):
    def init(self, setup):
        tb = setup.init_tb()
        dut = setup.init_swi('swi_a')
        self.tb = tb
        self.dut = dut
        self.speedS = None  # set by TestCase_1

    def configure(self):
        pass

    def tear_down(self):
        pass


class TestCase_1(ATTestCase.TestCase):
    testCaseDesc = 'one'
    testCaseRef = 'AWPTCM-T1'
    testCaseMethod = 'one'

    def main(self):
        # AI m d
        dut = self.testSet.dut
        self.log('STEP 2: find S')
        output = dut.cmd('show interface')
        self.log('OBSERVED: {}'.format(output))
        if 'Invalid input' in output:
            self.supported = False
            self.failed('show interface refused: {}'.format(output[:40]))
            return
        self.testSet.speedS = 1000
        self.passed('S is {}'.format(self.testSet.speedS))


class TestCase_2(ATTestCase.TestCase):
    testCaseDesc = 'two'
    testCaseRef = 'AWPTCM-T1'
    testCaseMethod = 'two'

    def main(self):
        # AI m d
        dut = self.testSet.dut
        self.log('STEP 3: force S')
        speed = self.testSet.speedS
        if speed is None:
            self.supported = False
            self.failed('speedS was not established by TestCase_1')
            return
        dut.mode(')#')
        dut.cmd('speed {}'.format(speed))
        dut.mode('#')
        output = dut.cmd('show interface')
        self.log('OBSERVED: {}'.format(output))
        if 'configured speed {}'.format(speed) in output:
            self.passed('configured speed {}'.format(speed))
        else:
            self.failed('configured speed not {}: {}'.format(speed, output[:60]))

    def tear_down(self):
        dut = self.testSet.dut
        dut.mode(')#')
        dut.cmd('no speed')
        dut.mode('#')


if __name__ == '__main__':
    ts = TestSet()
    ts.add_testCase(TestCase_1())
    ts.add_testCase(TestCase_2())
    ts.run(sys.argv)
'''


def test_G10_every_shape_the_review_asks_for_passes_the_lint():
    rv = (_P / "pt_review_script.jinja").read_text(encoding="utf-8")
    for shape in ("`self.supported = False` then `self.failed('<why>')`",
                  "`self.testSet.<name> = <value>`", "undone in the same case's `tear_down()`"):
        assert shape in rv
    s = pc.PtSession(key="AWPTCM-T1")
    s.step6 = {"files": {"test": {"name": "t.py", "code": _FRAME}}}
    s.step2 = {"sequence": [{"n": 1, "action": "a", "verify": "v"}, {"n": 2, "action": "b", "verify": "w"}]}
    lint = pc._lint_generated(s)
    bad = [e for e in lint["errors"] if not e.startswith("coverage")]
    assert bad == [], bad
    assert not [w for w in lint["warnings"] if w.startswith(("confcheck:", "pluggable:"))]


# --- C7: a consumer that never checks a published value for None ------------------------------

_PUB = [{"name": "speedS", "shape": "int", "tc_n": 1, "orig_n": 2}]


def _lint_pub(body):
    import ast
    return pc._lint_published_unguarded(ast.parse(
        "class TestCase_1:\n    def main(self):\n        self.testSet.speedS = 100\n\n\n"
        "class TestCase_2:\n" + body), _PUB)


def test_C7_an_unguarded_read_warns_and_the_producer_is_not_judged():
    out = _lint_pub("    def main(self):\n        dut.cmd('speed {}'.format(self.testSet.speedS))\n")
    assert len(out) == 1 and out[0].startswith("published: TestCase_2.main()")


def test_C7_every_guard_shape_is_accepted():
    for guard in ("        s = self.testSet.speedS\n        if s is None:\n            return\n",
                  "        if self.testSet.speedS is None:\n            return\n",
                  "        s = self.testSet.speedS\n        if not s:\n            return\n",
                  "        if self.testSet.speedS:\n            pass\n"):
        body = "    def main(self):\n" + guard + "        dut.cmd('speed {}'.format(self.testSet.speedS))\n"
        assert _lint_pub(body) == [], guard


def test_C7_runs_in_the_lint_as_a_warning_and_is_silent_without_publishes():
    assert "warnings.extend(_lint_published_unguarded(" in _SRC
    import ast
    assert pc._lint_published_unguarded(ast.parse("class TestCase_2:\n    def main(self):\n"
                                                  "        x = self.testSet.speedS\n"), []) == []
    assert pc._lint_published_unguarded(ast.parse(_FRAME), [{"name": "speedS", "tc_n": 1}]) == []


def test_C7_T33235s_own_guards_count_isinstance_and_compound_conditions():
    """The hand-finished T33235 guards monitoredBaseline with `isinstance(store, dict)` and a
    compound `if`; neither is an unguarded read."""
    for guard in ("        store = self.testSet.speedS\n        x = store.get('a') if isinstance(store, dict) else None\n",
                  "        ref = self.testSet.speedS\n        if isinstance(ref, int) and ref > 10:\n            pass\n"):
        assert _lint_pub("    def main(self):\n" + guard) == [], guard
