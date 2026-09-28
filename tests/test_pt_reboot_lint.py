"""`.reboot(None, ...)` factory-defaults the DUT and `timeOut=-1` does not wait (2026-09-29).

Found by the tb470 sentinel reading the framework's `Switch.reboot` on the box: T33235's
TestCase_33 ("fixed speed persisted after reload") called `dut.reboot(None, timeOut=-1)`, the
corpus `deviceReboot` idiom, which sends `del force default.cfg` / `no boot config-file` /
`erase startup-config` before rebooting — on tb470 the 3-member stack would come back with no
config. Pinned: the lint fires on both halves of that shape, stays quiet on the corrected one,
is BLOCKING, is wired into `_lint_generated`, the prompts teach the corrected shape, and the
two generated scripts on disk carry no such call (memory prompt-examples-are-the-spec).
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
_FACTS = (_SERVER / "templates" / "prompts" / "_pt_domain_facts.jinja").read_text(encoding="utf-8")
# The live scripts only: `.meta/<group>/<name>/history/` holds frozen earlier iterations of them.
_GENERATED = sorted(p for p in (_REPO / "ask-ck" / "functions" / "pytest-creator" / "generated").rglob("test-*.py")
                    if ".meta" not in p.parts)

_HEAD = '''
from framework import ATTestSet, ATTestCase


class TestSet(ATTestSet.TestSet):
    def configure(self):
        dut = self.dut
        dut.cmd('copy running-config startup-config')


class TestCase_33(ATTestCase.TestCase):
'''


def _tree(body):
    return ast.parse(_HEAD + body)


def test_the_T33235_shape_fires_twice_None_and_minus_one():
    out = pc._lint_reboot_clears_config(_tree('''
    def main(self):
        dut = self.testSet.dut
        output = dut.reboot(None, timeOut=-1)
        dut.mode('#')
        self.passed('back')
'''))
    assert len(out) == 2
    assert out[0].startswith("reboot: TestCase_33.main() line") and "ERASES the startup config" in out[0]
    assert out[1].startswith("reboot: TestCase_33.main() line") and "timeOut=-1" in out[1]


def test_keyword_confFile_None_and_positional_timeOut_fire_too():
    out = pc._lint_reboot_clears_config(_tree('''
    def main(self):
        self.testSet.dut.reboot(confFile=None, timeOut=600)
        self.testSet.dut.reboot('', 0, -1)
        self.passed('back')
'''))
    assert len(out) == 2
    assert "ERASES" in out[0] and "line 14" in out[0]
    assert "timeOut=-1" in out[1] and "line 15" in out[1]


def test_the_corrected_shape_is_quiet():
    out = pc._lint_reboot_clears_config(_tree('''
    def main(self):
        dut = self.testSet.dut
        output = dut.reboot('', timeOut=900)
        dut.reboot('tb470-bench.cfg', timeOut=900)
        dut.reboot(timeOut=0)
        self.passed('back')
'''))
    assert out == []


def test_a_module_level_helper_is_named_by_function():
    out = pc._lint_reboot_clears_config(ast.parse('''
def deviceReboot(dev):
    return dev.reboot(None, timeOut=-1)
'''))
    assert len(out) == 2 and out[0].startswith("reboot: deviceReboot() line 3")


def test_both_findings_are_blocking():
    out = pc._lint_reboot_clears_config(_tree('''
    def main(self):
        self.testSet.dut.reboot(None, timeOut=-1)
'''))
    blocking, policy = pc._split_lint_errors(out)
    assert len(blocking) == 2 and policy == []


def test_the_lint_is_wired_into_lint_generated():
    import inspect
    assert "_lint_reboot_clears_config(tree)" in inspect.getsource(pc._lint_generated)


def test_the_prompts_teach_the_corrected_shape():
    assert "dev.reboot('', timeOut=900)" in _RULES
    assert "dev.reboot(None, …)" in _RULES and "factory-defaulted" in _RULES
    assert "`timeOut=-1` is NOT" in _RULES
    assert "reboot('')` keeps its config" in _FACTS and "reboot('', timeOut=900)" in _FACTS


def test_the_generated_scripts_on_disk_carry_no_such_call():
    assert _GENERATED, "no generated scripts found"
    for path in _GENERATED:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        assert pc._lint_reboot_clears_config(tree) == [], path.name
