"""R1 (PLAN-self-healing-generation.md): fragment dependency closure.

A fragment offered "to adapt" may call a name defined at its source suite's module level or in
its `library_<suite>.py` (`LLDP_PHONE_PKT` in 1332_lldp_med/library_1332.py). The model adapts the
fragment and keeps the name; if nothing ships it, that is a NameError on the bench (fix run's
tc28; 7 units in the 2026-09-08 pass). Closure ships those definitions in OUR library so
"call it by name, never paste" is true.
"""
import builtins
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main" / "CK_server"))

from routers import pytest_create as pc  # noqa: E402
import db as dbmod  # noqa: E402

_HAS_DB = (_REPO / "ask-ck" / "db" / "ck.db").exists()


def test_fragment_loaded_names_are_the_free_names():
    code = "def f(a):\n    b = a + LLDP_PHONE_PKT\n    return helper(b, c)\n"
    names = pc._fragment_loaded_names(code)
    assert "LLDP_PHONE_PKT" in names and "helper" in names and "c" in names
    assert "a" not in names and "b" not in names and "f" not in names   # bound


def test_find_top_level_def_returns_verbatim_source_or_none():
    src = "import os\nX = 1 + 2\n\ndef helper(z):\n    return z\n\nclass C:\n    pass\n"
    assert pc._find_top_level_def("X", src).strip() == "X = 1 + 2"
    assert pc._find_top_level_def("helper", src).startswith("def helper(z):")
    assert pc._find_top_level_def("C", src).startswith("class C:")
    assert pc._find_top_level_def("nope", src) is None
    assert pc._find_top_level_def("X", "def (bad syntax") is None


def test_framework_star_imports_are_extracted():
    src = "import sys\nfrom framework.ATPackets import *\nfrom framework import ATTestSet\nfrom os import path\n"
    assert pc._framework_star_imports_of(src) == ["from framework.ATPackets import *"]


def test_close_deps_ships_a_module_level_constant_and_not_scapy_or_framework(monkeypatch):
    # A fragment (no db needed): the source defines HELPER_PKT at module level; the fragment uses
    # it plus a scapy name (Ether) and a framework layer (lldp_basic).
    src_id = "x/suite/test.py"
    source = ("from framework.ATPackets import *\n"
              "HELPER_PKT = Ether() / lldp_basic()\n"
              "def other():\n    return 1\n")

    frag = {"source_id": src_id, "loc": [1, 2], "code":
            "def main(self):\n    sendp(HELPER_PKT, iface=x)\n    other()\n"}
    data = {"scripts_index_by_id": {src_id: {"suite_dir": "suite", "db": "x"}}}
    monkeypatch.setattr(pc, "_fragment_source_text", lambda sid: source)
    monkeypatch.setattr(pc.dbx, "get_suite_library", lambda sd, db=None: "")
    already = set(builtins.__dict__) | pc._SCAPY_STAR_NAMES
    deps, imports = pc._close_fragment_deps([frag], data, already, set())
    syms = {m["symbol"] for m in deps}
    assert "HELPER_PKT" in syms                       # module-level constant is shipped
    assert "other" in syms                             # a called helper is shipped too
    assert "Ether" not in syms and "sendp" not in syms  # scapy names are never shipped
    assert "lldp_basic" not in syms                    # a framework layer is never shipped
    assert "from framework.ATPackets import *" in imports
    assert deps and deps[0]["tag"].startswith("# AI: dependency")
    assert deps[0].get("auto") is True


def test_close_deps_never_ships_a_framework_class(monkeypatch):
    src_id = "x/suite/test.py"
    source = "class lldp_basic(Packet):\n    fields_desc = []\n"
    monkeypatch.setattr(pc, "_fragment_source_text", lambda sid: source)
    monkeypatch.setattr(pc.dbx, "get_suite_library", lambda sd, db=None: "")
    frag = {"source_id": src_id, "loc": [1, 2], "code": "def main(self):\n    x = lldp_basic()\n"}
    data = {"scripts_index_by_id": {src_id: {"suite_dir": "suite", "db": "x"}}}
    deps, _ = pc._close_fragment_deps([frag], data, set(builtins.__dict__), {"lldp_basic"})
    assert all(m["symbol"] != "lldp_basic" for m in deps), "a framework layer must not be shadowed"


@pytest.mark.skipif(not _HAS_DB, reason="ck.db absent")
def test_the_real_lldp_phone_pkt_dependency_is_closed_from_the_corpus():
    src_id = "art/1332_lldp_med/test-1332.1001.py"
    frag = {"source_id": src_id, "loc": [359, 487],
            "code": "def main(self):\n    sendp(LLDP_PHONE_PKT, iface=ethA.name, verbose=0)\n"}
    data = {"scripts_index_by_id": {src_id: dbmod.get_script(src_id)}}
    deps, imports = pc._close_fragment_deps([frag], data,
                                            set(builtins.__dict__) | pc._SCAPY_STAR_NAMES, set())
    phone = next((m for m in deps if m["symbol"] == "LLDP_PHONE_PKT"), None)
    assert phone is not None and phone["code"].startswith("LLDP_PHONE_PKT =")
    assert "from framework.ATPackets import *" in imports


@pytest.mark.skipif(not _HAS_DB, reason="ck.db absent")
def test_get_suite_library_finds_the_sibling_library():
    lib = dbmod.get_suite_library("1332_lldp_med", "art")
    assert lib and "LLDP_PHONE_PKT" in lib
    assert dbmod.get_suite_library("", None) is None


def test_build_library_ships_the_closed_dependency(monkeypatch):
    src_id = "x/suite/test.py"
    source = ("from framework.ATPackets import *\n"
              "HELPER_PKT = Ether() / lldp_basic()\n")
    monkeypatch.setattr(pc, "_fragment_source_text", lambda sid: source)
    monkeypatch.setattr(pc.dbx, "get_suite_library", lambda sd, db=None: "")
    # a method-body fragment (offered to adapt) that uses HELPER_PKT
    frag = {"source_id": src_id, "loc": [1, 2], "symbol": "main",
            "code": "def main(self):\n    sendp(HELPER_PKT, iface=x)\n"}
    data = {"scripts_index_by_id": {src_id: {"suite_dir": "suite", "db": "x", "imports": []}}}
    lib = pc._build_library("AWPTCM-T1", [frag], data, surface={})
    assert lib and "HELPER_PKT =" in lib["code"], "the dependency is shipped in the library file"
    assert "# AI: dependency `HELPER_PKT`" in lib["code"]
    assert "from framework.ATPackets import *" in lib["code"]
    assert any(m.get("auto") and m["symbol"] == "HELPER_PKT" for m in lib["members"])
