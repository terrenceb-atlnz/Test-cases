"""The `noform:` lint from the live T33234 run on tb470 (device-testing sentinel, 2026-09-29).

(A power-cycle guard was drafted the same morning and WITHDRAWN before commit — Terrence:
"thats not the worst type of behavior. I dont mind that restart"; the framework's post-failure
restart stays as it is.)

`noform:` (WARNING) — a `no <cmd>` whose CLI-reference syntax documents no `no` form.
   `no polarity` is refused on the IE520 and the x230 (`polarity {auto|mdi|mdix}`), failed STEP 1
   of every case, and each failure power-cycled the bench. A warning because the reference is
   incomplete (`no duplex` is undocumented and accepted) and the DUT decides.

Pinned: the lint fires on the shape seen and is quiet on the corrected one, is wired, the
prompts teach the corrected shape, and the scripts and library on disk are clean (memory
prompt-examples-are-the-spec).
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
_GEN = _REPO / "ask-ck" / "functions" / "pytest-creator" / "generated"
_ON_DISK = sorted(p for p in _GEN.rglob("*.py") if ".meta" not in p.parts and "__pycache__" not in p.parts)

_HEAD = '''
from framework import ATTestSet, ATTestCase


class TestSet(ATTestSet.TestSet):
    def configure(self):
        pass


'''


def _tree(body):
    return ast.parse(_HEAD + body)


# --- noform -----------------------------------------------------------------------------------

_FAKE = {
    ("polarity",): ["polarity {auto|mdi|mdix}"],
    ("duplex",): ["duplex {auto|full|half}"],
    ("speed",): ["speed {10|100|1000}", "speed auto", "no speed"],
    ("shutdown",): ["shutdown", "no shutdown"],
    ("lldp", "run"): ["lldp run", "no lldp run"],
}


def _fake_forms(words):
    return _FAKE.get(tuple(words))


def test_no_polarity_warns_directly_and_from_a_loop_tuple(monkeypatch):
    monkeypatch.setattr(pc, "_cli_syntax_forms", _fake_forms)
    out = pc._lint_undocumented_no_form(_tree('''
class TestCase_1(ATTestCase.TestCase):
    def configure(self):
        dut = self.testSet.dut
        for cmd in ('interface {}'.format(dut.portA.name), 'duplex auto', 'no polarity', 'no shutdown'):
            dut.cmd(cmd)

    def tear_down(self):
        self.testSet.dut.cmd('no polarity')
        self.testSet.dut.cmd('no speed')
        self.testSet.dut.cmd('no lldp run')
'''))
    assert len(out) == 1 and out[0].startswith("noform: line") and "`no polarity`" in out[0]
    assert "polarity auto" in out[0]


def test_an_unknown_command_and_a_documented_negation_are_quiet(monkeypatch):
    monkeypatch.setattr(pc, "_cli_syntax_forms", _fake_forms)
    out = pc._lint_undocumented_no_form(_tree('''
class TestCase_1(ATTestCase.TestCase):
    def tear_down(self):
        dut = self.testSet.dut
        dut.cmd('no speed')
        dut.cmd('no shutdown')
        dut.cmd('no frobnicate')
        dut.cmd('polarity auto')
'''))
    assert out == []


def test_noform_is_wired():
    import inspect
    assert "_lint_undocumented_no_form(tree)" in inspect.getsource(pc._lint_generated)


def test_the_real_reference_documents_no_no_form_for_polarity():
    forms = pc._cli_syntax_forms(["polarity"])
    assert forms and not any(f.lower().startswith("no ") for f in forms)
    assert any(f.lower().startswith("no speed") for f in pc._cli_syntax_forms(["speed"]))


# --- prompts + disk ---------------------------------------------------------------------------

def test_the_prompts_teach_the_default_value_form():
    assert "`polarity {auto|mdi|mdix}`" in _RULES and "`no polarity` is REFUSED" in _RULES
    assert "`no polarity` is refused; the default form is `polarity auto`" in _FACTS


def test_the_scripts_and_library_on_disk_are_clean():
    assert _ON_DISK
    for path in _ON_DISK:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        assert pc._lint_undocumented_no_form(tree) == [], path.name
        assert "'no polarity'" not in path.read_text(encoding="utf-8"), path.name
