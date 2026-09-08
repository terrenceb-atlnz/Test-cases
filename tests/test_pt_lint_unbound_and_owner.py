"""Three lint checks the first ART-frame pass proved necessary (AWPTCM-T44297, 2026-09-08).

The pass linted CLEAN — 0 errors against 59 and 63 on the old frame — and would still have
died on the bench three ways nothing looked for: `analyse_lldp_packets` called in 7 units and
defined nowhere, `re` used in 4 units the frame never imported, `LLDP_PHONE_PKT` lifted from
an ART test script that was never offered. All three are a NameError on first use, invisible
to py_compile. A fourth finding runs but tests the wrong thing: the suite setup configured
`portPeer` — the DUT's end of the neighbour link — ON THE NEIGHBOUR. And six verdicts quoted
the step's verify text verbatim as their reason.

These call the shipped `_lint_generated`, so they fail if it changes.
"""
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main" / "CK_server"))

from routers import pytest_create as pc  # noqa: E402
from models import PtSession  # noqa: E402

SURFACE = {"ATPackets": {"classes": {"lldp_basic": {}, "lldp_man_tlv": {}},
                         "functions": [{"name": "make_lldp"}]},
           "ATTestSet": {"classes": {"TestSet": {}}, "functions": []},
           "ATTestCase": {"classes": {"TestCase": {}}, "functions": []},
           # a PACKAGE: known only through its submodules, the way the surface doc records it
           "ATLibrary.ATTools": {"classes": {"ATTools": {}}, "functions": [{"name": "wait_for"}]},
           "ATLibrary.ATLimits": {"classes": {"ATLimits": {}}, "functions": []}}

FRAME = '''#!/usr/bin/python3
import sys
import time
{extra_imports}
from framework import ATTestSet, ATTestCase
from framework.ATPackets import *
{lib_import}


class TestSet(ATTestSet.TestSet):
    def init(self, setup, misc):
        dutA = setup.init_swi('swi_a')
        self.dutA = dutA
        self.tb = setup.init_tb('tb')
        self.peer = setup.init_swi('swi_b')

    def configure(self):
        dutA = self.dutA
        peer = self.peer
        portPeer = dutA.portPeer
        portDut = peer.portDut
        {setup_body}

    def tear_down(self):
        pass


class TestCase_1(ATTestCase.TestCase):
    testCaseDesc = 'select the TLV'
    testCaseRef = 'AWPTCM-T1'

    def configure(self):
        pass

    def main(self):
        # ART 1332_lldp_med/test-1332.1001.py lines 1-2
        tb = self.testSet.tb
        dutA = self.testSet.dutA
        ethA = tb.ethA
        portA = dutA.portA
        peer = self.testSet.peer
        portPeer = dutA.portPeer
        stk_a = self.testSet.stk_a
        self.log('STEP 1: select the TLV')
        output = dutA.cmd('show lldp interface {{}}'.format(portA.name))
        self.log('OBSERVED: {{}}'.format(output))
        {main_body}

    def tear_down(self):
        pass


if __name__ == '__main__':
    ts = TestSet()
    ts.add_testCase(TestCase_1())
    ts.run(sys.argv)
'''

SEQUENCE = [{"n": 1, "action": "select the TLV",
             "verify": "A captured LLDPDU decodes a Port Description TLV."}]


def _lint(monkeypatch, main_body="self.passed('Pd listed: {}'.format(output))",
          setup_body="pass", extra_imports="", library=None):
    monkeypatch.setattr(pc, "_framework_surface_doc", lambda: SURFACE)
    lib_import = f"from {Path(library['name']).stem} import *" if library else ""
    code = FRAME.format(extra_imports=extra_imports, lib_import=lib_import,
                        setup_body=setup_body, main_body=main_body)
    sess = PtSession(key="AWPTCM-T00001")
    sess.step2 = {"sequence": SEQUENCE}
    sess.step6 = {"files": {"test": {"code": code},
                            **({"library": library} if library else {})}}
    return pc._lint_generated(sess)


def _unbound(result):
    return [e for e in result["errors"] if e.startswith("unbound name:")]


# --- unbound names -----------------------------------------------------------------------

def test_a_helper_called_but_defined_nowhere_is_an_error(monkeypatch):
    r = _lint(monkeypatch, main_body="analyse_lldp_packets(self, [])\n        self.passed('ok')")
    hits = _unbound(r)
    assert len(hits) == 1 and "`analyse_lldp_packets`" in hits[0] and "TestCase_1" in hits[0]
    blocking, policy = pc._split_lint_errors(hits)
    assert blocking == hits, "a NameError is never the reviewer's call"


def test_re_without_an_import_is_an_error_and_import_re_clears_it(monkeypatch):
    body = "m = re.search('Pd', output)\n        self.passed('Pd: {}'.format(bool(m)))"
    assert any("`re`" in e for e in _unbound(_lint(monkeypatch, main_body=body)))
    assert _unbound(_lint(monkeypatch, main_body=body, extra_imports="import re")) == []


def test_a_constant_lifted_from_an_art_test_script_is_an_error(monkeypatch):
    body = "sendp(LLDP_PHONE_PKT, iface=ethA.name, verbose=0)\n        self.passed('sent')"
    hits = _unbound(_lint(monkeypatch, main_body=body))
    assert [h.split("`")[1] for h in hits] == ["LLDP_PHONE_PKT"], hits
    # `sendp` comes from scapy through ATPackets' star import and is NOT reported.


def test_a_name_the_suite_library_defines_is_bound(monkeypatch):
    lib = {"name": "library_awptcm_t00001.py",
           "code": "from framework.ATPackets import *\n\n"
                   "def analyse_lldp_packets(self, recPktList):\n    return len(recPktList)\n"}
    r = _lint(monkeypatch, main_body="analyse_lldp_packets(self, [])\n        self.passed('ok')",
              library=lib)
    assert _unbound(r) == []


def test_a_star_import_of_a_framework_PACKAGE_binds_its_submodules_names(monkeypatch):
    """The corpus libraries do `from framework.ATLibrary import *`. The first version of the
    check went silent on that (an unknown export list), which on the real T44297 pass hid the
    one unbound name that remained. A package binds the union of its submodules' names."""
    lib = {"name": "library_awptcm_t00001.py",
           "code": "from framework.ATLibrary import *\nfrom framework.ATLibrary.ATTools import *\n\n"
                   "def helper(self):\n    return wait_for(ATTools, ATLimits)\n"}
    body = "helper(self)\n        sendp(LLDP_PHONE_PKT, iface=ethA.name, verbose=0)\n        self.passed('ok')"
    hits = _unbound(_lint(monkeypatch, main_body=body, library=lib))
    assert [h.split("`")[1] for h in hits] == ["LLDP_PHONE_PKT"], hits


def test_at_layer_names_from_the_surface_are_bound(monkeypatch):
    body = "ok = all(p.haslayer(lldp_basic) for p in [])\n        self.passed('ok {}'.format(ok))"
    assert _unbound(_lint(monkeypatch, main_body=body)) == []


def test_the_check_stays_silent_behind_a_star_import_it_cannot_see_through(monkeypatch):
    """An unknown module could define anything; a guess would train reviewers to ignore it."""
    body = "mystery(output)\n        self.passed('ok')"
    r = _lint(monkeypatch, main_body=body, extra_imports="from somewhere.else import *")
    assert _unbound(r) == []


def test_the_clean_frame_reports_no_unbound_names(monkeypatch):
    assert _unbound(_lint(monkeypatch)) == []


# --- a port on the wrong switch ------------------------------------------------------------

def _owner(result):
    return [e for e in result["errors"] if "'s port, on " in e]


def test_the_duts_end_of_the_link_configured_on_the_neighbour_is_flagged(monkeypatch):
    r = _lint(monkeypatch, setup_body="peer.cmd('interface {}'.format(portPeer.name))")
    hits = _owner(r)
    assert len(hits) == 1 and "`portPeer`" in hits[0] and "dutA's port, on peer" in hits[0]
    blocking, policy = pc._split_lint_errors(hits)
    assert policy == hits, "runs, tests the wrong thing: the reviewer's call"


def test_each_switch_configuring_its_own_end_is_fine(monkeypatch):
    r = _lint(monkeypatch, setup_body="dutA.cmd('interface {}'.format(portPeer.name))\n"
                                      "        peer.cmd('interface {}'.format(portDut.name))")
    assert _owner(r) == []


def test_the_attribute_form_and_the_fstring_form_are_seen(monkeypatch):
    r = _lint(monkeypatch, setup_body="peer.cmd('interface {}'.format(dutA.portPeer.name))\n"
                                      "        peer.cmd(f'interface {portPeer.name}')")
    assert len(_owner(r)) == 2


def test_a_stack_handle_configuring_a_members_port_is_not_flagged(monkeypatch):
    """`stk_a` is the stack the DUT belongs to; `dutA.portA` is legitimately its port."""
    r = _lint(monkeypatch, main_body="stk_a.cmd('interface {}'.format(portA.name))\n"
                                     "        self.passed('ok')")
    assert _owner(r) == []


# --- a verdict that restates the expectation -----------------------------------------------

def test_a_verdict_reason_equal_to_the_verify_text_is_a_warning(monkeypatch):
    r = _lint(monkeypatch,
              main_body="self.passed('A captured LLDPDU decodes a Port Description TLV.')")
    hits = [w for w in r["warnings"] if "verbatim" in w]
    assert len(hits) == 1 and "verify text" in hits[0] and "TestCase_1.main()" in hits[0]


def test_a_reason_carrying_evidence_is_not_a_warning(monkeypatch):
    r = _lint(monkeypatch, main_body="self.passed('Pd decoded in 3 of 3 LLDPDUs from {}'.format(portA.name))")
    assert [w for w in r["warnings"] if "verbatim" in w] == []
