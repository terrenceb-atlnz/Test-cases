"""G7 / G14 / G8 (PLAN-pt-drive-followups-2026-09-24 §4): the family library is the helper source.

AWPTCM-T33235 (2026-09-24): the fragments step selected legacy `library_5000` helpers whose
names already exist in the group's `library_9001.py` with DIFFERENT contracts —
`configurePort`'s sixth argument is an expected outcome in one and a settle time in the other.
Assembly rebuilt the session library from those fragments, so every re-assembly re-introduced
six colliding helpers and the save's clash guard (G3) refused them each time.

Pinned: a fragment whose name the family file defines is not shipped, and is recorded so the
unit prompt drops it from the code to adapt; the family's public helpers reach the prompt by
signature; the library the session stores is the family file plus only the new members, so a
second merge changes nothing (G14); both generation paths read the family file; and a script
that adds nothing still ships the module its frame imports. G8: the family `_field` returns
None for a field it has no pattern for instead of raising KeyError.
"""
import importlib.util
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SERVER = _REPO / "ask-ck" / "CK-main" / "CK_server"
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(_SERVER))

from llm import render_prompt  # noqa: E402
from routers import pytest_create as pc  # noqa: E402

_SRC = (_SERVER / "routers" / "pytest_create.py").read_text(encoding="utf-8")

FAMILY = '''# Helper library for the Port group — ART family 9001.
import re
import time


def configurePort(testCase, device, port, setting, value, settle=0):
    """Apply '<setting> <value>' under 'interface <port>'; True when it reads back."""
    return True


def _private(x):
    return x
'''
DATA = {"scripts_index_by_id": {"legacy/5000/library_5000.py": {"imports": ["time"]}}}
LEGACY_CONFIGURE = {"source_id": "legacy/5000/library_5000.py", "symbol": "configurePort", "loc": [1, 3],
                    "why": "", "code": "def configurePort(testCase, device, port, setting, value, expect):\n    return expect\n"}
NEW_HELPER = {"source_id": "legacy/5000/library_5000.py", "symbol": "sweepSpeeds", "loc": [5, 7],
              "why": "", "code": "def sweepSpeeds(testCase, device, port):\n    return []\n"}


def test_a_fragment_the_family_already_defines_is_not_shipped_and_is_recorded():
    lib = pc._build_library("Port", 9001, [LEGACY_CONFIGURE, NEW_HELPER], DATA, family_code=FAMILY)
    assert [m["symbol"] for m in lib["members"]] == ["sweepSpeeds"]
    assert lib["family_replaced"] == [{"tag": pc._fragment_tag("legacy/5000/library_5000.py", [1, 3], False),
                                       "names": ["configurePort"]}]
    assert lib["family_tags"] == {lib["family_replaced"][0]["tag"]}
    assert lib["code"].count("def configurePort(") == 1
    assert "def configurePort(testCase, device, port, setting, value, settle=0):" in lib["code"]
    assert "def sweepSpeeds(" in lib["code"]


def test_the_family_helpers_reach_the_prompt_by_signature_public_only():
    lib = pc._build_library("Port", 9001, [NEW_HELPER], DATA, family_code=FAMILY)
    assert lib["family_members"] == [{"name": "configurePort",
                                      "signature": "configurePort(testCase, device, port, setting, value, settle=0)",
                                      "doc": "Apply '<setting> <value>' under 'interface <port>'; True when it reads back."}]


def test_G14_the_stored_library_is_the_family_file_plus_new_members_so_a_re_merge_changes_nothing():
    lib = pc._build_library("Port", 9001, [LEGACY_CONFIGURE, NEW_HELPER], DATA, family_code=FAMILY)
    assert lib["code"].startswith(FAMILY.rstrip("\n"))
    assert pc._merge_library_code(lib["code"], lib["code"]) == lib["code"]
    # the save merges the session copy into the file on disk: no clash, same result
    assert pc._merge_library_code(FAMILY, lib["code"]) == lib["code"]


def test_a_script_adding_nothing_still_gets_the_family_module_its_frame_imports():
    lib = pc._build_library("Port", 9001, [LEGACY_CONFIGURE], DATA, family_code=FAMILY)
    assert lib["members"] == [] and lib["stem"] == "library_9001" and lib["code"] == FAMILY
    sk = pc._render_skeleton("AWPTCM-T99999", "probe", [{"n": 1, "action": "a", "verify": "v"}],
                             [], [], "", lib)
    assert "from library_9001 import *" in sk


def test_without_a_family_file_nothing_changes():
    assert pc._build_library("Port", 9001, [LEGACY_CONFIGURE], DATA)["members"][0]["symbol"] == "configurePort"
    method = {"source_id": "x.py", "symbol": "m", "loc": [1, 2], "code": "    def main(self):\n        pass\n"}
    assert pc._build_library("Port", 9001, [method], DATA) is None


def test_both_generation_paths_read_the_family_file_and_both_store_paths_ship_the_module():
    assert _SRC.count("family_code=_read_family_library(") == 2
    assert _SRC.count('.get("members")') == 0     # a library ships whenever it has code and a stem


def test_the_unit_prompt_drops_family_replaced_fragments_and_lists_the_family_helpers():
    seg = _SRC[_SRC.index("def _render_unit_prompt("):_SRC.index("def _unit_shape_ok(")]
    assert 'set(lib.get("family_tags") or ())' in seg
    lib = pc._build_library("Port", 9001, [LEGACY_CONFIGURE, NEW_HELPER], DATA, family_code=FAMILY)
    ctx = {"case_key": "K", "case_title": "T", "setup_steps": [], "blank_block": "class TestCase_1:\n    pass",
           "devices": ["dut"], "bound_devices": ["dut"], "fragments": [], "framework_surface": {},
           "cli_reference": "", "model_name": "m", "gen_date": "d", "mode": "testcase", "tc_n": 1,
           "source_n": 2, "step": {"n": 2, "action": "a", "verify": "v"}, "library": lib}
    out = render_prompt("pt_generate_step.jinja", ctx)
    assert "The group's own helpers" in out
    assert "`configurePort(testCase, device, port, setting, value, settle=0)`" in out
    assert "NOT shipped because the group's module already defines their names" in out
    whole = render_prompt("pt_generate_script.jinja", {**ctx, "skeleton": "x", "file_name": "f.py"})
    assert "The group's own helpers" in whole


def test_G8_the_family_field_reader_returns_None_for_a_field_it_has_no_pattern_for():
    path = _REPO / "ask-ck" / "functions" / "pytest-creator" / "generated" / "9001_Port" / "library_9001.py"
    spec = importlib.util.spec_from_file_location("library_9001_under_test", path)
    lib = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lib)
    body = "configured duplex auto, configured speed 100, configured polarity auto\n"
    assert lib.getConfiguredValue(body, "no") is None          # configurePort(..., 'no', 'speed')
    assert lib.getConfiguredValue(body, "speed") == "100"


def test_a_dependency_the_family_already_defines_is_not_pulled_in(monkeypatch):
    """R1's closure ships a free name a fragment reads, from its source script. When the family
    file defines that name, the family's version is the one in scope — shipping the source's copy
    would put a second definition (the G3 clash) back into the library."""
    uses = {"source_id": "legacy/5000/test-5000.1.py", "symbol": "sweepSpeeds", "loc": [9, 10], "why": "",
            "code": "def sweepSpeeds(testCase, device, port):\n    return configurePort(testCase, device, port, 'speed', 10, 1)\n"}
    source = LEGACY_CONFIGURE["code"] + "\n\n" + uses["code"]
    monkeypatch.setattr(pc, "_fragment_source_text", lambda sid: source)
    monkeypatch.setattr(pc.dbx, "get_suite_library", lambda *a, **k: "")
    without = pc._build_library("Port", 9001, [uses], DATA)
    assert "configurePort" in [m["symbol"] for m in without["members"]]      # R1 would ship it
    lib = pc._build_library("Port", 9001, [uses], DATA, family_code=FAMILY)
    assert [m["symbol"] for m in lib["members"]] == ["sweepSpeeds"]
    assert lib["code"].count("def configurePort(") == 1
