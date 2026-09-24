"""Three framework facts the units got wrong on T33235 (PLAN-pt-drive-followups-2026-09-24 §2).

Read from `/home/st-art/framework/ATTestCase.py` on tb470, 2026-09-24:

  G11  the result is decided by COUNTING verdicts — `self.supported = False` needs a
       `self.failed()` to read UNSUPPORTED; on its own it reports ERROR. The fill rules
       taught the ERROR shape, and T33235 had 18 such paths.
  G12  `show system pluggable` lists `1.0.x` without the `port` prefix on some releases, so a
       row lookup on `port.name` finds nothing (five T33235 units).
  G13  `confCheck` compares the running-config after each case's tear_down() with the
       TestSet's, so a case that leaves a change behind fails.

Pinned: each lint fires on the shape seen, stays quiet on the corrected shape, and the prompt
teaches the corrected shape (the example is the spec — memory prompt-examples-are-the-spec).
"""
import ast
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SERVER = _REPO / "ask-ck" / "CK-main" / "CK_server"
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(_SERVER))

from routers import pytest_create as pc  # noqa: E402

_RULES = (_SERVER / "templates" / "prompts" / "pt_fill_rules.jinja").read_text(encoding="utf-8")
_GEN = (_SERVER / "templates" / "prompts" / "pt_generate_step.jinja").read_text(encoding="utf-8")

_HEAD = '''
from framework import ATTestSet, ATTestCase


class TestSet(ATTestSet.TestSet):
    def configure(self):
        dut = self.dut
        dut.cmd('lldp run')


class TestCase_1(ATTestCase.TestCase):
'''


def _tree(body):
    return ast.parse(_HEAD + body)


# --- G11 --------------------------------------------------------------------------------------

def test_G11_the_flag_with_only_a_log_is_an_ERROR_path():
    out = pc._lint_unsupported_without_failure(_tree('''
    def main(self):
        if not self.testSet.fibre_supported:
            self.supported = False
            self.log('INFO: no fibre link; not applicable')
            return
        self.passed('ok')
'''))
    assert len(out) == 1 and out[0].startswith("unsupported: TestCase_1.main()")
    assert "ERROR" in out[0]


def test_G11_the_flag_followed_by_a_fail_is_UNSUPPORTED_and_accepted():
    assert pc._lint_unsupported_without_failure(_tree('''
    def main(self):
        if not self.testSet.fibre_supported:
            self.supported = False
            self.failed('no fibre link on this bench')
            return
        self.passed('ok')
''')) == []


def test_G11_a_fail_elsewhere_in_main_does_not_excuse_the_branch():
    """The fail must be on the SAME path: a later product check failing is not the reason."""
    out = pc._lint_unsupported_without_failure(_tree('''
    def main(self):
        if not self.testSet.fibre_supported:
            self.supported = False
            return
        if 1:
            self.failed('product check')
'''))
    assert len(out) == 1


def test_G11_the_flag_in_configure_needs_main_to_report_it():
    bad = pc._lint_unsupported_without_failure(_tree('''
    def configure(self):
        if not self.testSet.fibre_supported:
            self.supported = False
            return

    def main(self):
        self.passed('ok')
'''))
    assert len(bad) == 1 and "TestCase_1.configure()" in bad[0] and "main() runs anyway" in bad[0]
    assert pc._lint_unsupported_without_failure(_tree('''
    def configure(self):
        if not self.testSet.fibre_supported:
            self.supported = False
            return

    def main(self):
        if not self.supported:
            self.failed('no fibre link on this bench')
            return
        self.passed('ok')
''')) == []


def test_G11_is_blocking():
    msg = pc._lint_unsupported_without_failure(_tree('''
    def main(self):
        self.supported = False
        return
'''))[0]
    blocking, policy = pc._split_lint_errors([msg])
    assert blocking == [msg] and policy == []


def test_G11_the_prompt_teaches_the_flag_PLUS_a_fail():
    i = _RULES.index("3d. **CAPABILITY GATING")
    example = _RULES[i:_RULES.index("```", _RULES.index("```python", i) + 3)]
    assert "self.supported = False" in example and "self.failed(" in example
    assert "self.log('INFO:" not in example        # the old ERROR shape
    assert "reports **ERROR**" in _RULES
    # the per-role note in the unit prompt says the same
    assert "(`self.supported = False`; log; return)" not in _GEN
    assert "then `self.failed('<why>')`" in _GEN


# --- G12 --------------------------------------------------------------------------------------

def test_G12_a_pluggable_row_keyed_on_port_name_warns():
    code = _HEAD + '''
    def main(self):
        out = self.testSet.dut.cmd('show system pluggable')
        row = next((ln for ln in out.splitlines() if ln.split()[:1] == [portCuSfp.name]), None)
        self.passed('x')
'''
    out = pc._lint_pluggable_port_key(ast.parse(code), code)
    assert len(out) == 1 and out[0].startswith("pluggable: TestCase_1.main()")


def test_G12_ck_media_or_a_stripped_prefix_is_quiet():
    for body in ('''
    def main(self):
        import ck_media
        in_cage = ck_media.pluggable_ports(self.testSet.dut.cmd('show system pluggable'))
        self.passed(str(ck_media.is_pluggable(portCuSfp.name, in_cage)))
''', '''
    def main(self):
        out = self.testSet.dut.cmd('show system pluggable')
        bare = portCuSfp.name[len('port'):]
        self.passed(str(bare in out))
'''):
        code = _HEAD + body
        assert pc._lint_pluggable_port_key(ast.parse(code), code) == []


def test_G12_the_prompt_points_at_ck_media():
    assert "ck_media.pluggable_ports(dut.cmd('show system pluggable'))" in _RULES
    assert "ck_media.is_pluggable(port.name, in_cage)" in _RULES


# --- G13 --------------------------------------------------------------------------------------

def test_G13_a_speed_left_forced_warns():
    out = pc._lint_config_not_restored(_tree('''
    def main(self):
        dut = self.testSet.dut
        dut.cmd('speed 100')
        self.passed('x')

    def tear_down(self):
        dut = self.testSet.dut
        dut.cmd('no shutdown')
'''))
    assert len(out) == 1 and "`speed 100` on dut" in out[0]


def test_G13_restored_directly_through_a_loop_or_a_helper_is_quiet():
    for td in ('''
    def tear_down(self):
        dut = self.testSet.dut
        dut.cmd('no speed')
''', '''
    def tear_down(self):
        for dev in (self.testSet.dut,):
            dev.cmd('no speed')
''', '''
    def tear_down(self):
        dut = self.testSet.dut
        configureDefaultPort(self, dut, dut.portPeer)
'''):
        assert pc._lint_config_not_restored(_tree('''
    def main(self):
        dut = self.testSet.dut
        dut.cmd('speed 100')
        self.passed('x')
''' + td)) == [], td


def test_G13_a_final_no_form_suite_command_and_show_are_not_judged():
    assert pc._lint_config_not_restored(_tree('''
    def configure(self):
        dut = self.testSet.dut
        dut.cmd('shutdown')

    def main(self):
        dut = self.testSet.dut
        dut.cmd('no shutdown')
        dut.cmd('lldp run')
        dut.cmd('show interface')
        dut.cmd('clear counters')
        self.passed('x')

    def tear_down(self):
        pass
''')) == []


def test_G13_the_prompt_names_the_check_and_the_negation():
    i = _RULES.index("3e. **Every case must leave the configuration")
    rule = _RULES[i:_RULES.index("3f.", i)]
    assert "confCheck" in rule and "`no speed`, not `speed auto`" in rule


def test_the_three_lints_are_wired_into_the_lint():
    import inspect
    seg = inspect.getsource(pc._lint_generated)
    for fn in ("_lint_unsupported_without_failure(tree)", "_lint_pluggable_port_key(tree, code)",
               "_lint_config_not_restored(tree)"):
        assert fn in seg


def test_G11_a_helper_handed_the_testcase_may_report_the_fail_and_is_not_refused():
    """A blocking error must not fire on what the lint cannot see: `reportUnsupported(self, why)`
    may call `self.failed()` itself."""
    assert pc._lint_unsupported_without_failure(_tree('''
    def main(self):
        if not self.testSet.fibre_supported:
            self.supported = False
            reportUnsupported(self, 'no fibre link')
            return
        self.passed('ok')
''')) == []
