"""The generated frame emulates the ART suite shape (2026-09-07, all eight divergences).

Why. Six ART scripts read in full plus a census over all 188 (2,085 TestCase classes):
the corpus binds `(dut.portA, tb.ethA) = setup.init_portlink(dutA, tb, type1='port')` in
111 of them — the TESTBOX is the traffic partner — and names a second switch by role
(swiSrc, dutZ), never `dut`. Our frame bound one partner switch, called it `dut`, and gave
the testbox no interface, so both models on T44297 wrote `tb.ethA` in every capture unit
and `dut.portA` for the DUT port: 59 / 63 unbound-port lint errors, every one frame-caused.
The other divergences: no per-case configure(), no shortcut block, one-line testCaseMethod,
"exactly one verdict" where ART emits checkpoints, no suite library, ATPackets layers
invisible in the prompt. These tests pin the closed shape.
"""
import ast
import re
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SERVER = _REPO / "ask-ck" / "CK-main" / "CK_server"
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(_SERVER))
sys.path.insert(0, str(_REPO / "tool"))

from llm import render_prompt  # noqa: E402
from routers import pytest_create as pc  # noqa: E402
import pt_media  # noqa: E402

models = pytest.importorskip("models")

CAPTURE_SEQ = [
    {"n": 1, "action": "enable lldp on the DUT port", "verify": "", "kind": "setup"},
    {"n": 2, "action": "select the port-description TLV",
     "verify": "capture LLDPDUs with tcpdump on the testbox and confirm the TLV is present",
     "kind": "verify"},
]
PEER_SEQ = [{"n": 1, "action": "read the neighbour table on the partner switch",
             "verify": "show lldp neighbors on the partner lists the DUT", "kind": "verify"}]
BOTH_SEQ = CAPTURE_SEQ + [dict(PEER_SEQ[0], n=3)]
NONE_SEQ = [{"n": 1, "action": "show version", "verify": "the build string is reported",
             "kind": "verify"}]
FRAGS = [{"code": "self.dutA.cmd('lldp run')\n"}]


def render(seq, frags=FRAGS, library=None):
    return pc._render_skeleton("AWPTCM-T1", "t", seq, [], frags, "", library)


def init_body(code):
    return re.search(r"def init\(self, setup\):.*?\n    def configure", code, re.S).group(0)


# ----------------------------------------------------------------- 1. which links the frame binds

def test_capture_wording_binds_the_testbox_link():
    assert pc._detect_links(CAPTURE_SEQ, []) == {"tb": True, "peer": False}


def test_neighbour_wording_binds_the_peer_link():
    assert pc._detect_links(PEER_SEQ, []) == {"tb": False, "peer": True}


def test_a_case_can_need_both_links():
    assert pc._detect_links(BOTH_SEQ, []) == {"tb": True, "peer": True}


def test_no_link_wording_binds_nothing():
    assert pc._detect_links(NONE_SEQ, []) == {"tb": False, "peer": False}


def test_a_physical_step_binds_the_testbox_link():
    seq = [{"n": 1, "action": "unplug the cable", "verify": "link goes down", "kind": "physical"}]
    assert pc._detect_links(seq, [])["tb"] is True


def test_fragment_code_using_tb_eth_binds_the_testbox_link():
    assert pc._detect_links(NONE_SEQ, [{"code": "subProc = tb.start_tcpdump(ethA.name, 'x.pcap', '')"}])["tb"]


def test_legacy_portlink_wording_alone_means_the_peer_link():
    seq = [{"n": 1, "action": "bring up the port link", "verify": "link up", "kind": "verify"}]
    assert pc._detect_links(seq, []) == {"tb": False, "peer": True}


# ----------------------------------------------------------------- 2. the frame's init()

def test_testbox_link_is_bound_in_the_art_shape():
    body = init_body(render(CAPTURE_SEQ))
    assert "(dutA.portA, tb.ethA, _tb) = self._ck_bind_link(setup, dutA, misc, 'tb')" in body
    assert "portPeer" not in body and "ck_far_port" not in body


def test_peer_link_is_bound_by_role_and_never_called_dut():
    body = init_body(render(PEER_SEQ))
    assert "(dutA.portPeer, peer_port, peer) = self._ck_bind_link(" in body
    assert "peer.portDut = peer_port" in body and "self.peer = peer" in body
    assert "tb.ethA" not in body
    assert not re.search(r"\bdut\b\s*=", body), "the partner must not be named `dut`"


def test_both_links_bind_two_distinct_dut_ports():
    body = init_body(render(BOTH_SEQ))
    assert "dutA.portA, tb.ethA" in body and "dutA.portPeer, peer_port, peer" in body


def test_bind_helper_takes_the_testbox_end_without_init_swi():
    sk = render(CAPTURE_SEQ)
    helper = re.search(r"def _ck_bind_link.*?\n    def init", sk, re.S).group(0)
    assert "if far_key == 'tb':" in helper
    assert "far = self.tb" in helper
    assert "setup.init_portlink(dut, far, type1='port')\n" in helper     # no type2 for an Eth


def test_atpackets_is_imported_only_when_the_testbox_link_exists():
    assert "from framework.ATPackets import *" in render(CAPTURE_SEQ)
    assert "from framework.ATPackets import *" not in render(PEER_SEQ)


def test_bound_devices_and_ports_are_read_back_off_the_frame():
    sk = render(BOTH_SEQ)
    assert pc._skeleton_bound_devices(sk, "dutA") == ["dutA", "tb", "peer"]
    assert pc._skeleton_bound_ports(sk) == [
        {"role": "tb", "near": "dutA.portA", "far": "tb.ethA"},
        {"role": "copper", "near": "dutA.portPeer", "far": "peer.portDut"},
    ]


def test_the_frame_compiles_in_every_link_shape():
    for seq in (CAPTURE_SEQ, PEER_SEQ, BOTH_SEQ, NONE_SEQ):
        compile(render(seq), "frame.py", "exec")


# ----------------------------------------------------------------- 3/4. per-case configure + shortcuts

def test_every_testcase_has_configure_main_and_tear_down():
    sk = render(BOTH_SEQ)
    tree = ast.parse(sk)
    cases = [c for c in tree.body if isinstance(c, ast.ClassDef) and c.name.startswith("TestCase_")]
    assert cases
    for c in cases:
        names = [n.name for n in c.body if isinstance(n, ast.FunctionDef)]
        assert names == ["configure", "main", "tear_down"], names


def test_every_method_opens_with_the_shortcut_block():
    sk = render(BOTH_SEQ)
    tree = ast.parse(sk)
    want_case = ["tb = self.testSet.tb", "dutA = self.testSet.dutA", "ethA = tb.ethA",
                 "portA = dutA.portA", "peer = self.testSet.peer", "portPeer = dutA.portPeer"]
    want_set = [w.replace("self.testSet.", "self.") for w in want_case]
    for c in tree.body:
        if not isinstance(c, ast.ClassDef):
            continue
        for fn in c.body:
            if not isinstance(fn, ast.FunctionDef) or fn.name not in ("configure", "main", "tear_down"):
                continue
            src = ast.get_source_segment(sk, fn)
            want = want_case if c.name.startswith("TestCase_") else want_set
            for w in want:
                assert w in src, f"{c.name}.{fn.name} lacks `{w}`"


def test_main_opens_with_a_provenance_placeholder_the_restamp_treats_as_an_echo():
    sk = render(CAPTURE_SEQ)
    main = re.search(r"    def main\(self\):\n(.*?)\n", sk).group(1)
    assert ">>>" in main and pc._is_provenance_echo(main)


def test_the_physical_step_acts_on_the_bound_port_not_a_fill_slot():
    seq = [{"n": 1, "action": "unplug the cable", "verify": "link goes down", "kind": "physical"}]
    sk = render(seq)
    assert "port = portA" in sk and "init_portlink() attribute" not in sk
    assert "dutA.cmd('show interface {} status'.format(port.name), log=False)" in sk


# ----------------------------------------------------------------- 6. class attributes

def test_testcase_method_is_the_art_multi_line_form():
    sk = render(CAPTURE_SEQ)
    assert "    testCaseMethod  = 'select the port-description TLV\\n'\n" in sk
    assert "    testCaseMethod += 'Verify: capture LLDPDUs" in sk
    assert "testCaseRef = 'AWPTCM-T1'" in sk
    assert "testCaseExcl" not in sk, "platform lists are hardware-verified, never generated"


# ----------------------------------------------------------------- 5. verdict rule (checkpoints)

def test_fill_rules_allow_checkpoints_and_forbid_silent_branches():
    rules = (_SERVER / "templates" / "prompts" / "pt_fill_rules.jinja").read_text(encoding="utf-8")
    assert "at least one non-empty" in rules and "exactly one" not in rules
    assert "CHECKPOINTS ARE THE ART STYLE" in rules
    assert "self.supported = False" in rules and "testCaseExcl" in rules


def test_lint_still_requires_a_verdict_but_accepts_several():
    code = FRAME_HEAD + (
        "class TestCase_1(ATTestCase.TestCase):\n"
        "    testCaseDesc = 'd'\n    testCaseRef = 'K'\n    testCaseMethod = 'm'\n"
        "    def main(self):\n"
        "        # AI x 2026-09-07\n"
        "        self.log('STEP 1: x')\n"
        "        out = self.testSet.dutA.cmd('show lldp')\n"
        "        self.log('OBSERVED: ' + out)\n"
        "        if not out:\n            self.failed('no output')\n            return\n"
        "        self.passed('frames captured')\n"
        "        if 'x' in out:\n            self.passed('TLV present')\n"
        "        else:\n            self.failed('TLV absent')\n"
    ) + RUNNER
    errs = lint_errors(code)
    assert not [e for e in errs if "contract:" in e], errs


# ----------------------------------------------------------------- lint: config-only hooks, bound ports

FRAME_HEAD = (
    "import sys\nfrom framework import ATTestSet, ATTestCase\n"
    "class TestSet(ATTestSet.TestSet):\n"
    "    def _ck_bind_link(self, setup, dut, misc, role):\n"
    "        import ck_media\n"
    "        (a, b) = setup.init_portlink(dut, dut, type1='port')\n"
    "        return a, b, dut\n"
    "    def init(self, setup):\n"
    "        tb = setup.init_tb()\n"
    "        misc = setup.get_all_misc()\n"
    "        dutA = setup.init_swi(misc.get('ck_role_dut', 'swi_a'))\n"
    "        self.tb = tb\n        self.dutA = dutA\n"
    "        (dutA.portA, tb.ethA, _tb) = self._ck_bind_link(setup, dutA, misc, 'tb')\n"
    "        (dutA.portPeer, peer_port, peer) = self._ck_bind_link(setup, dutA, misc, 'copper')\n"
    "        peer.portDut = peer_port\n        self.peer = peer\n"
    "    def configure(self):\n        pass\n"
    "    def tear_down(self):\n        pass\n"
)
RUNNER = "if __name__ == '__main__':\n    ts = TestSet()\n    ts.add_testCase(TestCase_1())\n    ts.run(sys.argv)\n"


def lint_errors(code: str):
    sess = models.PtSession(
        key="AWPTCM-T00000", group="", payload={}, traceability="",
        step2={}, step3={}, step4={}, step5={},
        step6={"files": {"test": {"name": "t.py", "code": code}}})
    return pc._lint_generated(sess)["errors"]


def test_a_verdict_in_a_testcase_configure_is_a_lint_error():
    code = FRAME_HEAD + (
        "class TestCase_1(ATTestCase.TestCase):\n"
        "    testCaseDesc = 'd'\n    testCaseRef = 'K'\n    testCaseMethod = 'm'\n"
        "    def configure(self):\n        self.failed('nope')\n"
        "    def main(self):\n        # AI x 2026-09-07\n        self.log('STEP 1: x')\n"
        "        self.passed('ok')\n"
        "    def tear_down(self):\n        self.passed('clean')\n"
    ) + RUNNER
    errs = lint_errors(code)
    hits = [e for e in errs if "config only; the verdict belongs in main()" in e]
    assert len(hits) == 2 and "TestCase_1.configure()" in hits[0] and "TestCase_1.tear_down()" in hits[1]
    blocking, policy = pc._split_lint_errors(hits)
    assert policy == hits and not blocking          # a house rule: the reviewer's call


def test_bench_lint_accepts_the_four_bound_ports_and_rejects_others():
    code = FRAME_HEAD + (
        "class TestCase_1(ATTestCase.TestCase):\n"
        "    def main(self):\n"
        "        tb = self.testSet.tb\n        dutA = self.testSet.dutA\n"
        "        peer = self.testSet.peer\n"
        "        a = dutA.portA.name; b = tb.ethA.name; c = dutA.portPeer.name; d = peer.portDut.name\n"
        "        bad = dutA.portB.name\n"
    )
    tree = ast.parse(code)
    errors, _w = pc._lint_bench_integration(tree, code, {})
    assert len(errors) == 1 and "reads `dutA.portB`" in errors[0], errors
    assert "`dutA.portA`, `dutA.portPeer`" in errors[0]


def test_a_library_syntax_error_is_a_blocking_lint_error():
    sess = models.PtSession(
        key="AWPTCM-T00000", group="", payload={}, traceability="",
        step2={}, step3={}, step4={}, step5={},
        step6={"files": {"test": {"name": "t.py", "code": FRAME_HEAD + RUNNER},
                         "library": {"name": "library_awptcm_t1.py", "code": "def x(:\n"}}})
    errs = pc._lint_generated(sess)["errors"]
    hit = [e for e in errs if e.startswith("syntax: library_awptcm_t1.py")]
    assert hit
    blocking, policy = pc._split_lint_errors(hit)
    assert blocking == hit


# ----------------------------------------------------------------- media role for the testbox link

def test_the_testbox_link_has_no_media_requirement_but_needs_a_pluggable():
    ok, why = pt_media.satisfies("tb", pt_media.TWISTED_PAIR)
    assert ok and "no media requirement" in why
    ok, _ = pt_media.satisfies("tb", pt_media.FIBRE)
    assert ok
    ok, why = pt_media.satisfies("tb", pt_media.ABSENT)
    assert not ok and "BENCH PROBLEM" in why
    ok, why = pt_media.satisfies("nonsense", pt_media.TWISTED_PAIR)
    assert not ok and "unknown media role" in why


# ----------------------------------------------------------------- 7. the suite library

DATA = {"scripts_index_by_id": {
    "art/1332_lldp_med/library_1332.py": {"imports": ["framework.ATPackets", "sys", "time"]},
    "art/1332_lldp_med/test-1332.1001.py": {"imports": ["framework.ATTestCase", "sys"]},
}}
HELPER = {"source_id": "art/1332_lldp_med/library_1332.py", "symbol": "check_lldp_lag",
          "loc": [18, 41], "why": "the LAG TLV check",
          "code": "def check_lldp_lag(testCase, eth, tb):\n    return True\n"}
METHOD = {"source_id": "art/1332_lldp_med/test-1332.1001.py", "symbol": "TestCase_1.main",
          "loc": [53, 115], "why": "capture",
          "code": "    def main(self):\n        pass\n"}
CONST = {"source_id": "art/1332_lldp_med/library_1332.py", "symbol": "LLDP_PHONE_PKT",
         "loc": [7, 7], "why": "", "code": "LLDP_PHONE_PKT = Ether() / lldp_end_tlv()\n"}


def test_library_holds_standalone_helpers_and_constants_not_methods():
    lib = pc._build_library("AWPTCM-T44297", [HELPER, METHOD, CONST], DATA)
    assert lib["name"] == "library_awptcm_t44297.py" and lib["stem"] == "library_awptcm_t44297"
    assert [m["symbol"] for m in lib["members"]] == ["check_lldp_lag", "LLDP_PHONE_PKT"]
    assert "from framework.ATPackets import *" in lib["code"] and "import time" in lib["code"]
    assert "import sys" not in lib["code"]
    assert "# ART 1332_lldp_med/library_1332.py lines 18-41" in lib["code"]
    assert "def check_lldp_lag(testCase, eth, tb):" in lib["code"]
    compile(lib["code"], lib["name"], "exec")
    assert pc._fragment_tag(HELPER["source_id"], HELPER["loc"]) in lib["tags"]


def test_no_library_when_nothing_qualifies():
    assert pc._build_library("AWPTCM-T1", [METHOD], DATA) is None
    assert pc._build_library("AWPTCM-T1", [], DATA) is None


def test_the_frame_imports_the_library_when_one_exists():
    lib = pc._build_library("AWPTCM-T1", [HELPER], DATA)
    sk = render(CAPTURE_SEQ, library=lib)
    assert "from library_awptcm_t1 import *" in sk
    assert "from library_awptcm_t1" not in render(CAPTURE_SEQ)


# ----------------------------------------------------------------- 8. ATPackets layers in the surface

def test_surface_slice_turns_atpackets_classes_into_layers_with_fields(monkeypatch):
    monkeypatch.setattr(pc.dbx, "script_layer_fields",
                        lambda layers: {l: (["lldp_med_cap", "lldp_med_dev"] if l == "lldp_cap_tlv" else [])
                                        for l in layers})
    pc._atpackets_layer_fields.cache_clear()
    data = {"framework_surface": {
        "ATPackets": {"classes": {"lldp_cap_tlv": {"methods": [{"name": "guess_payload_class"}]},
                                  "lldp_end_tlv": {"methods": []}},
                      "functions": []},
        "ATTestCase": {"classes": {"TestCase": {"methods": [{"name": "log"}]}}, "functions": []}}}
    out = pc._framework_surface_slice(data, [])
    assert out["ATPackets"]["layers"] == {"lldp_cap_tlv": ["lldp_med_cap", "lldp_med_dev"],
                                          "lldp_end_tlv": []}
    assert out["ATPackets"]["classes"] == {}
    pc._atpackets_layer_fields.cache_clear()


@pytest.mark.skipif(not (_REPO / "ask-ck" / "var" / "ck.db").exists(), reason="ck.db absent")
def test_corpus_field_mining_finds_the_lldp_med_fields():
    got = pc.dbx.script_layer_fields(["lldp_cap_tlv", "lldp_lacp_tlv"])
    assert "lldp_med_cap" in got["lldp_cap_tlv"] and "lldp_med_dev" in got["lldp_cap_tlv"]
    assert "lldp_lacp_status" in got["lldp_lacp_tlv"]


# ----------------------------------------------------------------- the prompt says all of this

PROMPT_CTX = {
    "case_key": "K", "case_title": "T", "mode": "testcase", "tc_n": 1, "source_n": 2,
    "step": {"n": 2, "action": "select a TLV", "verify": "it is on the wire"},
    "setup_steps": [], "blank_block": "class TestCase_1:\n    pass",
    "fragments": [], "shared_fragments": [], "shared_tags_for_unit": [], "shared_cli_reference": "",
    "devices": ["dutA", "tb", "peer"], "bound_devices": ["dutA", "tb", "peer"],
    "bound_ports": [{"role": "tb", "near": "dutA.portA", "far": "tb.ethA"},
                    {"role": "copper", "near": "dutA.portPeer", "far": "peer.portDut"}],
    "framework_surface": {"ATPackets": {"classes": {}, "functions": [],
                                        "layers": {"lldp_cap_tlv": ["lldp_med_cap"]}},
                          "ATDrivers.ATTestBox": {"classes": {"TestBox": {"methods": [
                              {"name": "start_tcpdump", "args": ["iface", "fileName", "optionStr"]}]}}}},
    "cli_reference": "", "device_note": "", "py2_flagged": False, "rules_cli_reference": False,
    "split_marker": pc._PT_PROMPT_SPLIT, "model_name": "m", "gen_date": "2026-09-07",
    "library": None, "library_tags_for_unit": [],
}


def test_the_unit_prompt_names_the_bound_ports_and_the_layers():
    p = render_prompt("pt_generate_step.jinja", PROMPT_CTX)
    assert "`dutA.portA` <-> `tb.ethA`" in p and "`dutA.portPeer` <-> `peer.portDut`" in p
    assert "the testbox (a TestBox" in p and "the neighbour switch" in p
    assert "lldp_cap_tlv(lldp_med_cap)" in p
    assert "start_tcpdump(iface, fileName, optionStr)" in p
    assert "KEEP those lines" in p
    assert "THREE methods to fill" in p
    # everything above is case-level and must sit in the cached (system) half
    shared, unit = pc._split_unit_prompt(p)
    assert "`dutA.portA` <-> `tb.ethA`" in shared and "lldp_cap_tlv(lldp_med_cap)" in shared


def test_the_unit_prompt_presents_the_library_as_callable_not_pastable():
    lib = pc._build_library("AWPTCM-T1", [HELPER], DATA)
    p = render_prompt("pt_generate_step.jinja", {**PROMPT_CTX, "library": lib,
                                                 "library_tags_for_unit": [HELPER and pc._fragment_tag(HELPER["source_id"], HELPER["loc"])]})
    assert "Suite library `library_awptcm_t1.py`" in p and "CALL these, never paste them" in p
    assert "def check_lldp_lag(testCase, eth, tb):" in p
    assert "Library helpers the reviewer mapped to THIS unit" in p
    shared, unit = pc._split_unit_prompt(p)
    assert "def check_lldp_lag" in shared and "def check_lldp_lag" not in unit


# ----------------------------------------------------------------- 7b. import-time hazards (real T44297 selection)

LAYER_COPY = {"source_id": "legacy/5003_feature_limits/test-5003.0014-LLDP/lldp_class.py",
              "symbol": "lldp_cap_tlv", "loc": [102, 136], "why": "",
              "code": "class lldp_cap_tlv(Packet):\n    name = 'x'\n"}
BAD_DEFAULT = {"source_id": "svt/libSvt/portCoToCsv.py", "symbol": "checkPortCoErrors",
               "loc": [103, 118], "why": "",
               "code": "def checkPortCoErrors(csvName = defaultCsvName):\n    return csvName\n"}
STAR_CONST = {"source_id": "art/1332_lldp_med/library_1332.py", "symbol": "LLDP_PHONE_PKT",
              "loc": [7, 7], "why": "", "code": "LLDP_PHONE_PKT = Ether() / lldp_end_tlv()\n"}
SURFACE = {"ATPackets": {"classes": {"lldp_cap_tlv": {}, "lldp_end_tlv": {}}}}
DATA2 = {"scripts_index_by_id": {**DATA["scripts_index_by_id"],
                                 "svt/libSvt/portCoToCsv.py": {"imports": ["csv", "os"]}}}


def test_a_fragment_that_copies_a_framework_layer_is_not_shipped_but_is_named():
    lib = pc._build_library("AWPTCM-T1", [HELPER, LAYER_COPY], DATA2, surface=SURFACE)
    assert [m["symbol"] for m in lib["members"]] == ["check_lldp_lag"]
    assert lib["framework_dupes"] == ["lldp_cap_tlv"]
    assert "class lldp_cap_tlv" not in lib["code"]
    assert pc._fragment_tag(LAYER_COPY["source_id"], LAYER_COPY["loc"]) in lib["framework_tags"]


def test_only_dupes_means_no_library_file_but_the_prompt_still_hears_about_them():
    lib = pc._build_library("AWPTCM-T1", [LAYER_COPY], DATA2, surface=SURFACE)
    assert lib["members"] == [] and lib["stem"] == "" and lib["framework_dupes"] == ["lldp_cap_tlv"]
    assert "from library_" not in render(CAPTURE_SEQ, library=lib)
    p = render_prompt("pt_generate_step.jinja", {**PROMPT_CTX, "library": lib})
    assert "duplicate `framework.ATPackets` — NOT shipped" in p and "lldp_cap_tlv" in p
    assert "Suite library `" not in p


def test_a_default_argument_the_library_cannot_resolve_excludes_the_member(monkeypatch):
    monkeypatch.setattr(pc, "_fragment_source_text", lambda sid: "")
    lib = pc._build_library("AWPTCM-T1", [HELPER, BAD_DEFAULT, STAR_CONST], DATA2, surface=SURFACE)
    assert [m["symbol"] for m in lib["members"]] == ["check_lldp_lag", "LLDP_PHONE_PKT"]
    assert lib["skipped"] == ["checkPortCoErrors: needs defaultCsvName at import time"]
    # the star-imported source makes `Ether` / `lldp_end_tlv` resolvable, so the constant stays
    assert "LLDP_PHONE_PKT = Ether() / lldp_end_tlv()" in lib["code"]
    assert "from framework.ATPackets import *" in lib["code"]


def test_a_source_module_global_in_a_default_is_skipped_even_when_the_source_star_imports(monkeypatch):
    """svt/libSvt/portCoToCsv.py star-imports framework modules AND defines `defaultCsvName`
    at module level; the star import cannot supply that name, so the member must go."""
    monkeypatch.setattr(pc, "_fragment_source_text",
                        lambda sid: "from framework.ATTools import *\ndefaultCsvName = 'x.csv'\n")
    data = {"scripts_index_by_id": {"svt/libSvt/portCoToCsv.py": {"imports": ["framework.ATLibrary.ATTools", "csv"]}}}
    lib = pc._build_library("AWPTCM-T1", [BAD_DEFAULT], data, surface=SURFACE)
    assert lib is None or lib["members"] == []


def test_frame_class_fragments_are_neither_members_nor_framework_dupes():
    ts = {"source_id": "art/1332_lldp_med/test-1332.1001.py", "symbol": "TestSet", "loc": [8, 41],
          "why": "", "code": "class TestSet(ATTestSet.TestSet):\n    pass\n"}
    tc = {"source_id": "art/1332_lldp_med/test-1332.1001.py", "symbol": "TestCase_1", "loc": [44, 114],
          "why": "", "code": "class TestCase_1(ATTestCase.TestCase):\n    pass\n"}
    surface = {"ATTestSet": {"classes": {"TestSet": {}, "TestCase_0": {}}}, "ATTestCase": {"classes": {"TestCase": {}}}}
    assert pc._build_library("AWPTCM-T1", [ts, tc], DATA, surface=surface) is None
