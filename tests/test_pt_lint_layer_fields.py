"""D4 of PLAN-fix-units-guardrails (2026-09-15): a field read off a `framework.ATPackets` layer
must be one the layer declares.

The defect this catches is fix run 5's tc6 (T44297): `getattr(basicLayer, 'port_desc', None)`
off `lldp_basic`, whose fields are chassis_id … ttl_val. The default made the read silently None
and the case passed on nothing. The field lists come from `classes[<layer>].fields` in the
surface doc, which `ask-ck/tools/harvest_framework_surface.py` extracts from each layer's
`fields_desc`; without them the lint is silent.
"""
import ast
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main" / "CK_server"))
sys.path.insert(0, str(_REPO / "ask-ck" / "tools"))

from routers import pytest_create as pc  # noqa: E402
from models import PtSession  # noqa: E402
import harvest_framework_surface as hfs  # noqa: E402

# The real lists, as `fields_desc` declares them in ATPackets.py (identical on tb470, 2026-09-14).
LLDP_BASIC = ["chassis_id", "chassis_len", "chassis_subtype", "system_mac_addr", "port_id", "port_len",
              "port_subtype", "port_val", "ttl_id", "ttl_len", "ttl_val"]
LLDP_MAN = ["TLV_type", "lldp_man_len", "oui", "lldp_med_subtype", "lldp_man_val"]
FIELDS = {"lldp_basic": LLDP_BASIC, "lldp_man_tlv": LLDP_MAN}

# The surface doc AFTER the harvest: fields on two layers, the legacy shape on a third.
SURFACE = {"ATPackets": {"classes": {
    "lldp_basic": {"bases": ["Packet"], "methods": [{"name": "guess_payload_class"}], "fields": LLDP_BASIC},
    "lldp_man_tlv": {"bases": ["Packet"], "methods": [], "fields": LLDP_MAN},
    "lldp_end_tlv": {"bases": ["Packet"], "methods": []},           # no list → cannot be judged
}, "functions": []},
    "ATTestSet": {"classes": {"TestSet": {}}, "functions": []},
    "ATTestCase": {"classes": {"TestCase": {}}, "functions": []}}

# tc6's real main() body, verbatim from history/iter-14 lines 826–836 (indentation reduced).
TC6 = '''
class TestCase_6(ATTestCase.TestCase):
    def main(self):
        for idx, pkt in enumerate(recPktList):
            pktNum = idx + 1
            if pkt.haslayer(lldp_basic) and pkt[lldp_basic].chassis_id and pkt[lldp_basic].port_id and pkt[lldp_basic].ttl_val is not None:
                self.log('ok {} {}'.format(pkt[lldp_basic].chassis_id, pkt[lldp_basic].port_id))
            basicLayer = pkt[lldp_basic] if pkt.haslayer(lldp_basic) else None
            hasPortDesc = basicLayer is not None and getattr(basicLayer, 'port_desc', None) is not None
            hasSysName = basicLayer is not None and getattr(basicLayer, 'sys_name', None) is not None
            hasSysDesc = basicLayer is not None and getattr(basicLayer, 'sys_desc', None) is not None
            hasMgmtAddr = pkt.haslayer(lldp_man_tlv)
            self.log('{}'.format(pkt[lldp_man_tlv].lldp_man_val if hasMgmtAddr else None))
'''


def _lint(code, fields=FIELDS):
    return pc._lint_layer_fields(ast.parse(code), fields)


def _fields_of(errors):
    return [e.split("`")[1] for e in errors]


# --- the defect ------------------------------------------------------------------------------

def test_tc6s_three_phantom_reads_are_flagged_and_its_real_reads_are_not():
    errs = _lint(TC6)
    assert _fields_of(errs) == ["port_desc", "sys_name", "sys_desc"]
    for e in errs:
        assert "in TestCase_6" in e and "`lldp_basic` has no such field" in e
        assert "declared: chassis_id, chassis_len" in e and "observes nothing" in e
    assert "line 9" in errs[0]                        # the getattr line, not the bind line


def test_a_direct_read_and_a_getlayer_bind_are_judged_too():
    errs = _lint("x = pkt[lldp_basic].sys_name\ny = pkt.getlayer(lldp_man_tlv)\nz = y.mgmt_ip\nw = hasattr(y, 'oui')")
    assert _fields_of(errs) == ["sys_name", "mgmt_ip"]           # `oui` IS a field of lldp_man_tlv


def test_the_new_error_is_blocking():
    blocking, policy = pc._split_lint_errors(_lint(TC6))
    assert len(blocking) == 3 and policy == []


# --- what it must NOT flag ------------------------------------------------------------------

def test_scapy_packet_attributes_and_private_names_pass():
    code = "l = pkt[lldp_basic]\nl.show()\nprint(l.payload, l.time, l.fields_desc, l._private, pkt[lldp_basic].summary())"
    assert _lint(code) == []


def test_a_layer_without_a_field_list_and_an_unknown_layer_are_silent():
    assert _lint("a = pkt[lldp_end_tlv].anything\nb = pkt[SomethingElse].whatever") == []
    assert _lint("getattr(pkt[lldp_end_tlv], 'nope', None)") == []


def test_a_name_also_bound_from_something_else_is_ambiguous_and_not_judged():
    code = ("def f(layer):\n    return layer.keys\n"
            "layer = pkt[lldp_basic]\nfor layer in things:\n    layer.items()\n"
            "other = pkt[lldp_basic]\nother = {}\nother.keys()")
    assert _lint(code) == []
    # ...but `x = None` before the real bind does not make it ambiguous
    assert _fields_of(_lint("x = None\nif ok:\n    x = pkt[lldp_basic]\nx.bogus")) == ["bogus"]


def test_a_name_bound_from_two_layers_is_judged_against_the_union():
    code = "l = pkt[lldp_basic]\nl = pkt[lldp_man_tlv]\na = l.chassis_id\nb = l.lldp_man_val\nc = l.nothing"
    errs = _lint(code)
    assert _fields_of(errs) == ["nothing"] and "`lldp_basic/lldp_man_tlv`" in errs[0]


def test_no_field_lists_means_no_lint(monkeypatch):
    assert _lint(TC6, {}) == []
    legacy = {"ATPackets": {"classes": {"lldp_basic": {"bases": ["Packet"], "methods": []}}, "functions": []}}
    assert pc._surface_layer_fields(legacy) == {}
    assert pc._surface_layer_fields(SURFACE) == FIELDS
    monkeypatch.setattr(pc, "_framework_surface_doc", lambda: legacy)
    assert pc._lint_layer_fields(ast.parse(TC6)) == []


# --- wired in --------------------------------------------------------------------------------

def test_it_runs_inside_lint_generated_after_the_suite_owned_lint(monkeypatch):
    src = Path(pc.__file__).read_text(encoding="utf-8")
    body = src[src.index("def _lint_generated("):]
    assert body.index("_lint_suite_owned_commands(") < body.index("_lint_layer_fields(tree)")
    monkeypatch.setattr(pc, "_framework_surface_doc", lambda: SURFACE)
    code = ("#!/usr/bin/python3\nimport sys\nfrom framework import ATTestSet, ATTestCase\n"
            "from framework.ATPackets import *\n\n\nclass TestSet(ATTestSet.TestSet):\n"
            "    def init(self, setup, misc):\n        self.tb = setup.init_tb('tb')\n\n"
            "    def configure(self):\n        pass\n\n    def tear_down(self):\n        pass\n\n\n"
            "class TestCase_1(ATTestCase.TestCase):\n    testCaseDesc = 'd'\n    testCaseRef = 'r'\n\n"
            "    def main(self):\n        # ART x/y.py lines 1-2\n        self.log('STEP 1')\n"
            "        recPktList = []\n        for pkt in recPktList:\n"
            "            layer = pkt[lldp_basic]\n            v = getattr(layer, 'sys_name', None)\n"
            "        self.passed('OBSERVED: {}'.format(v))\n\n\nif __name__ == '__main__':\n"
            "    ts = TestSet()\n    ts.run(sys.argv)\n")
    sess = PtSession(key="AWPTCM-T00001")
    sess.step2 = {"sequence": [{"n": 1, "action": "a", "verify": "b"}]}
    sess.step6 = {"files": {"test": {"code": code}}}
    r = pc._lint_generated(sess)
    hits = [e for e in r["errors"] if e.startswith("unknown field:")]
    assert len(hits) == 1 and "`sys_name`" in hits[0] and "in TestCase_1" in hits[0]


def test_g6_refuses_a_fix_that_introduces_a_phantom_field(monkeypatch):
    """The store-path check (G6(b)) runs the whole-file lint on the spliced reply, so a fix that
    reads a field the layer lacks is refused and the current unit kept."""
    monkeypatch.setattr(pc, "_framework_surface_doc", lambda: SURFACE)
    from test_pt_fix_units import SCRIPT as _S, CTX, _unit  # noqa: E402  (the shared real-shape fixtures)
    # that fixture's frame does not star-import ATPackets; the real frame does, so add it here
    SCRIPT = _S.replace("from framework import ATTestSet, ATTestCase",
                        "from framework import ATTestSet, ATTestCase\nfrom framework.ATPackets import *")
    assert SCRIPT != _S
    chunks = pc._chunks_from_code(SCRIPT, CTX)
    cur = chunks["tc2"]
    sess = PtSession(key="AWPTCM-T00001")
    sess.step2 = {"sequence": [{"n": i, "action": "a", "verify": "b"} for i in (1, 2, 3)]}
    sess.step6 = {"files": {"test": {"code": SCRIPT}}}
    baseline = pc._lint_generated(sess)["errors"]
    guard = {"current_code": cur, "assembled_code": SCRIPT, "sess": sess, "baseline_errors": baseline}
    bad = cur.replace("self.log('two')", "self.log('two')\n        for pkt in []:\n"
                      "            p = getattr(pkt[lldp_basic], 'sys_desc', None)")
    assert "sys_desc" in bad
    why = pc._unit_lint_regression(guard, bad, _unit("tc2"))
    assert why and "unknown field" in why and "sys_desc" in why
    good = cur.replace("self.log('two')", "self.log('two')\n        for pkt in []:\n"
                       "            p = pkt[lldp_basic].chassis_id")
    assert pc._unit_lint_regression(guard, good, _unit("tc2")) is None


# --- the harvest ------------------------------------------------------------------------------

SAMPLE = '''
from scapy.all import *

class lldp_basic(Packet):
    name = "lldp_basic"
    fields_desc = [ ShortField("chassis_id", 0x0207), ByteField("chassis_len", 0), MACField("system_mac_addr", None) ]
    def guess_payload_class(self, payload):
        return lldp_end_tlv

class computed(Packet):
    fields_desc = make_fields()          # not a literal list → no claim

class partial(Packet):
    fields_desc = [ ByteField("a", 0), *extra ]   # one unresolvable entry → no claim

class NotALayer:
    pass
'''


def test_fields_desc_extraction_keeps_declaration_order_and_refuses_to_guess():
    got = hfs.layer_fields_from_source(SAMPLE)
    assert got == {"lldp_basic": ["chassis_id", "chassis_len", "system_mac_addr"]}


@pytest.mark.skipif(not (Path(hfs.bsi.FRAMEWORK_DIR) / "ATPackets.py").exists(),
                    reason="the NFS framework clone is not mounted here")
def test_the_real_atpackets_declares_all_28_layers_and_lldp_basic_has_no_port_desc():
    src = (Path(hfs.bsi.FRAMEWORK_DIR) / "ATPackets.py").read_text(encoding="utf-8", errors="replace")
    got = hfs.layer_fields_from_source(src)
    assert len(got) == 28
    assert got["lldp_basic"] == LLDP_BASIC
    assert not {"port_desc", "sys_name", "sys_desc"} & set(got["lldp_basic"])
    assert got["lldp_man_tlv"] == LLDP_MAN


def test_harvest_adds_fields_beside_the_existing_class_record(tmp_path):
    fw = tmp_path / "framework"
    (fw / "ATDrivers").mkdir(parents=True)
    (fw / "ATLibrary").mkdir()
    (fw / "ATPackets.py").write_text(SAMPLE)
    (fw / "ATTestSet.py").write_text("class TestSet:\n    def run(self, argv):\n        pass\n")
    surface = hfs.harvest(fw)
    assert surface["ATPackets"]["classes"]["lldp_basic"]["fields"] == ["chassis_id", "chassis_len", "system_mac_addr"]
    assert surface["ATPackets"]["classes"]["lldp_basic"]["methods"][0]["name"] == "guess_payload_class"
    assert "fields" not in surface["ATPackets"]["classes"]["computed"]
    assert "fields" not in surface["ATPackets"]["classes"]["NotALayer"]
    assert surface["ATTestSet"]["classes"]["TestSet"]["methods"][0]["name"] == "run"
    assert pc._surface_layer_fields(surface) == {"lldp_basic": ["chassis_id", "chassis_len", "system_mac_addr"]}
    lines = hfs.describe_diff({"ATPackets": {"classes": {"lldp_basic": {"methods": []}}, "functions": []}}, surface)
    assert any("fields 0 -> 3" in ln for ln in lines) and lines[0].startswith("modules: 1 -> 2")


def test_write_goes_to_the_db_it_is_given_only(tmp_path):
    import sqlite3, json
    db = tmp_path / "scratch.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE json_docs (name TEXT PRIMARY KEY, payload TEXT NOT NULL, updated_at TEXT)")
    conn.commit(); conn.close()
    payload = {"ATPackets": {"classes": {"lldp_basic": {"fields": ["a"]}}, "functions": []}}
    hfs.write_doc(db, payload)
    assert hfs.current_doc(db) == payload
    # --write without an explicit --db is refused (the hosted server would have to be stopped first)
    fw = tmp_path / "fw"; (fw / "ATDrivers").mkdir(parents=True); (fw / "ATLibrary").mkdir()
    (fw / "ATPackets.py").write_text(SAMPLE)
    assert hfs.main(["--framework", str(fw), "--write"]) == 2
