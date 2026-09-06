"""Bench-integration lint (token-efficiency decision 2, 2026-09-07).

Three defect classes made the T44297 per-unit script unrunnable until an LLM Review found
them — and every one is deterministic given the assembled script and the framework surface,
so it is lint's job (about 40% of what Review reported was this):

  1. a port attribute init() never assigned (`dut.portA` when init() bound `dut.portB`);
  2. a method the framework class does not define, or a keyword its signature rejects
     (`start_tcpdump(..., filter=...)` copied from a library fragment's local helper);
  3. a capture started and stopped with nothing between.

1 and 2 are errors: they fail on the bench, every time. 3 is a warning: a human decides.
"""
import ast
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SERVER = _REPO / "ask-ck" / "CK-main" / "CK_server"
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(_SERVER))

from routers import pytest_create as pc  # noqa: E402

SURFACE = {
    "ATDrivers.ATSwitch": {"classes": {
        "Switch": {"methods": [{"name": "cmd", "args": ["command", "mode", "timeOut"]},
                               {"name": "mode", "args": ["mode"]},
                               {"name": "reboot", "args": []}]},
        "Stack": {"methods": [{"name": "cmd", "args": ["command"]}]}}},
    "ATDrivers.ATTestBox": {"classes": {
        "TestBox": {"methods": [{"name": "start_tcpdump", "args": ["interface", "count"]},
                                {"name": "stop_tcpdump", "args": []},
                                {"name": "cmd", "args": ["command"]}]}}},
}

FRAME = '''
from framework import ATTestSet, ATTestCase


class TestSet(ATTestSet.TestSet):
    def init(self, setup):
        tb = setup.init_tb()
        misc = setup.get_all_misc()
        dutA = setup.init_swi(misc.get('ck_role_dut', 'swi_a'))
        self.tb = tb
        self.dutA = dutA
        (dutA.portA, self.ck_far_port, dut) = self._ck_bind_link(setup, dutA, misc, 'copper')
        self.dut = dut
        (dutA.portB, self.ck_far_port_b, _far_b) = self._ck_bind_link(setup, dutA, misc, 'copper')
        self.dut.portB = self.ck_far_port_b

    def configure(self):
        self.dutA.cmd('lldp run')

    def tear_down(self):
        pass


class TestCase_1(ATTestCase.TestCase):
    def main(self):
BODY
'''


def _lint(body: str, surface=SURFACE):
    code = FRAME.replace("BODY", "\n".join("        " + ln for ln in body.strip("\n").split("\n")))
    return pc._lint_bench_integration(ast.parse(code), code, surface)


# --- 1. unbound port attributes ---------------------------------------------------------

def test_a_port_init_never_assigned_is_an_error_naming_what_is_bound():
    errs, _ = _lint("port = self.testSet.dut.portA\nself.log(port)")
    assert len(errs) == 1
    assert "reads `dut.portA`" in errs[0] and "`dut.portB` only" in errs[0]
    assert "interface None" in errs[0]


def test_bound_ports_pass_including_tuple_bound_and_self_assigned_ones():
    errs, _ = _lint("a = self.testSet.dutA.portA\nb = self.testSet.dutA.portB\nc = self.testSet.dut.portB")
    assert errs == []


def test_a_testbox_eth_that_was_never_bound_is_an_error():
    errs, _ = _lint("cap = self.testSet.tb.ethB")
    assert len(errs) == 1 and "reads `tb.ethB`" in errs[0] and "no port on `tb`" in errs[0]


def test_each_unbound_port_is_reported_once_per_class_so_every_unit_gets_fixed():
    errs, _ = _lint("a = self.testSet.dut.portA\nb = self.testSet.dut.portA\nc = self.testSet.dut.portA")
    assert len(errs) == 1 and errs[0].startswith("TestCase_1 line ")
    # The per-unit Fix maps a lint line to its unit by class name; a defect shared by many
    # units must therefore be reported in EACH of them, not once for the script.
    code = FRAME.replace("BODY", "        a = self.testSet.dut.portA") + \
        "\n\nclass TestCase_2(ATTestCase.TestCase):\n    def main(self):\n        b = self.testSet.dut.portA\n"
    errs, _ = pc._lint_bench_integration(ast.parse(code), code, SURFACE)
    assert [e.split(" line ")[0] for e in errs] == ["TestCase_1", "TestCase_2"]


# --- 2. call shape against the surface --------------------------------------------------

def test_a_method_the_framework_class_lacks_is_an_error():
    errs, _ = _lint("self.testSet.dutA.frobnicate('x')")
    assert len(errs) == 1
    assert "`dutA.frobnicate()`" in errs[0] and "Switch class defines no `frobnicate`" in errs[0]


def test_a_keyword_the_signature_rejects_is_an_error():
    errs, _ = _lint("self.testSet.tb.start_tcpdump(self.testSet.dutA.portA, filter='ether proto 0x88cc')")
    assert len(errs) == 1
    assert "`tb.start_tcpdump(...)`" in errs[0] and "`filter`" in errs[0]
    assert "start_tcpdump(interface, count)" in errs[0]


def test_a_known_method_with_accepted_keywords_passes():
    errs, warns = _lint("self.testSet.dutA.cmd('show lldp', mode='exec')\nself.testSet.tb.start_tcpdump(self.testSet.dutA.portA, count=10)")
    assert errs == [] and warns == []


def test_too_many_positionals_is_only_a_warning():
    errs, warns = _lint("self.testSet.dutA.reboot(1, 2)")
    assert errs == [] and len(warns) == 1 and "2 positional" in warns[0]


def test_a_partner_may_be_a_switch_or_the_testbox():
    # `dut` came out of _ck_bind_link: Switch AND TestBox methods are both acceptable.
    errs, _ = _lint("self.testSet.dut.cmd('x')\nself.testSet.dut.start_tcpdump(self.testSet.dut.portB)")
    assert errs == []


def test_no_surface_means_no_call_shape_judgement():
    errs, _ = _lint("self.testSet.dutA.frobnicate()", surface={})
    assert errs == []


# --- 3. capture with no wait -----------------------------------------------------------

def test_a_capture_stopped_immediately_is_a_warning():
    _, warns = _lint("self.testSet.tb.start_tcpdump(self.testSet.dutA.portA)\nself.testSet.tb.stop_tcpdump()")
    assert len(warns) == 1 and "captures nothing" in warns[0]


def test_a_settle_between_start_and_stop_is_fine():
    _, warns = _lint("self.testSet.tb.start_tcpdump(self.testSet.dutA.portA)\ntime.sleep(35)\nself.testSet.tb.stop_tcpdump()")
    assert warns == []


def test_a_capture_never_stopped_in_the_function_is_not_judged():
    _, warns = _lint("self.testSet.tb.start_tcpdump(self.testSet.dutA.portA)")
    assert warns == []


# --- wiring ----------------------------------------------------------------------------------

def test_the_checks_run_inside_the_assembled_script_lint():
    src = (_SERVER / "routers" / "pytest_create.py").read_text(encoding="utf-8")
    i = src.index("def _lint_generated")
    body = src[i:i + 60000]                                # _split_lint_errors precedes it
    assert "_lint_bench_integration(tree, code, _framework_surface_doc())" in body


def test_a_script_without_our_frame_is_left_alone():
    code = "class TestSet(ATTestSet.TestSet):\n    def init(self, setup):\n        pass\n"
    assert pc._lint_bench_integration(ast.parse(code), code, SURFACE) == ([], [])
