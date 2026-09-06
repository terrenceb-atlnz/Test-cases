"""Case-common fragments and CLI entries are HOISTED into the shared half (decision 5), and
every unit is told it is self-contained (decision 3). Both 2026-09-07.

Decision 5: on T44297 fragments were 27% of all prompt text; one 6,282-char fragment went to
32 of 38 units and the four fragments used by >= 23/38 units were 63% of fragment bytes sent.
Anything used by at least half the units now renders ONCE, above the split marker, where it
is read from cache; each unit names by tag which of the shared items apply to it. Below the
threshold a fragment stays per-unit — giving every unit all 38 fragments was the quality
risk the report flagged. A single-unit case shares nothing.

Decision 3: 6 of 38 units on the same pass failed because they relied on state an earlier
TestCase had set up and its tear_down had undone. The rule lives in the per-unit template
ONLY: for the whole-script prompt, cross-case dependence is a legitimate design.
"""
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SERVER = _REPO / "ask-ck" / "CK-main" / "CK_server"
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(_SERVER))

from llm import render_prompt  # noqa: E402
from routers import pytest_create as pc  # noqa: E402

_TPL = _SERVER / "templates" / "prompts"

UNITS = [{"id": "setup", "kind": "setup", "tc_n": None, "label": "TestSet.configure / tear_down", "block": "x"},
         {"id": "tc1", "kind": "testcase", "tc_n": 1, "label": "TestCase_1", "block": "x"},
         {"id": "tc2", "kind": "testcase", "tc_n": 2, "label": "TestCase_2", "block": "x"},
         {"id": "tc3", "kind": "testcase", "tc_n": 3, "label": "TestCase_3", "block": "x"}]
TC_STEPS = [{"n": 1, "action": "select tlv", "verify": "shown"},
            {"n": 2, "action": "capture", "verify": "seen"},
            {"n": 3, "action": "clear", "verify": "gone"}]
FRAGS = [  # A: 3 of 4 units, B: 1 of 4, S: the setup only
    {"source_id": "lib.py", "symbol": "analyse", "maps_to": [1, 2, 3], "code": "A", "why": "w"},
    {"source_id": "t.py", "symbol": "TestCase_8", "maps_to": [2], "code": "B", "why": "w"},
    {"source_id": "s.py", "symbol": "cfg", "maps_to": [9], "code": "S", "why": "w"},
]
CLI = {  # per unit: which command sections the grounding would return
    "setup": "",
    1: "REAL CLI REFERENCE (AW+):\n### tcpdump\n    tcpdump ...\n### lldp tlv-select\n    lldp tlv-select ...",
    2: "REAL CLI REFERENCE (AW+):\n### tcpdump\n    tcpdump ...\n### show lldp\n    show lldp ...",
    3: "REAL CLI REFERENCE (AW+):\n### tcpdump\n    tcpdump ...",
}


def _ctx(units=UNITS):
    return {"fragments": FRAGS, "setup_steps": [{"n": 9, "action": "configure"}],
            "tc_steps": TC_STEPS, "units": units}


def _fake_cli(rows, frags):
    if not rows:
        return ""
    n = rows[0].get("n")
    return CLI.get("setup" if n == 9 else n, "")


# --- the CLI block splits and rejoins --------------------------------------------------

def test_cli_sections_round_trip():
    h, secs = pc._split_cli_sections(CLI[1])
    assert h == "REAL CLI REFERENCE (AW+):"
    assert [c for c, _ in secs] == ["tcpdump", "lldp tlv-select"]
    assert pc._join_cli_sections(h, secs) == CLI[1]
    assert pc._split_cli_sections("") == ("", [])
    assert pc._join_cli_sections(h, []) == ""


# --- the plan ------------------------------------------------------------------------------

def test_items_used_by_at_least_half_the_units_are_hoisted(monkeypatch):
    monkeypatch.setattr(pc, "_cli_reference_block", _fake_cli)
    plan = pc._shared_plan(_ctx())
    assert [f["symbol"] for f in plan["shared_fragments"]] == ["analyse"]     # 3/4
    assert plan["shared_cmds"] == {"tcpdump"}                                  # 3/4
    assert "show lldp" not in plan["shared_cli"] and "tcpdump" in plan["shared_cli"]
    assert plan["shared_cli"].startswith("REAL CLI REFERENCE shared by most units of this case")


def test_below_the_threshold_stays_per_unit(monkeypatch):
    monkeypatch.setattr(pc, "_cli_reference_block", _fake_cli)
    plan = pc._shared_plan(_ctx())
    tc2 = plan["per_frags"]["tc2"]
    assert {f["symbol"] for f in tc2} == {"analyse", "TestCase_8"}
    assert "TestCase_8" not in {f["symbol"] for f in plan["shared_fragments"]}
    assert "cfg" not in {f["symbol"] for f in plan["shared_fragments"]}      # setup-only


def test_a_single_unit_case_shares_nothing(monkeypatch):
    monkeypatch.setattr(pc, "_cli_reference_block", _fake_cli)
    plan = pc._shared_plan(_ctx(units=UNITS[1:2]))
    assert plan["shared_fragments"] == [] and plan["shared_cmds"] == set()
    assert plan["shared_cli"] == ""


def test_the_plan_is_computed_once_per_context(monkeypatch):
    calls = []

    def counting(rows, frags):
        calls.append(1)
        return _fake_cli(rows, frags)
    monkeypatch.setattr(pc, "_cli_reference_block", counting)
    ctx = _ctx()
    a = pc._shared_plan(ctx)
    b = pc._shared_plan(ctx)
    assert a is b and len(calls) == len(UNITS)


# --- what the units see ------------------------------------------------------------------

BASE = {"case_key": "AWPTCM-T00001", "case_title": "A case", "setup_steps": [], "devices": ["dut"],
        "framework_surface": {}, "model_name": "m", "gen_date": "2026-09-07",
        "py2_flagged": False, "rules_cli_reference": True, "split_marker": pc._PT_PROMPT_SPLIT,
        "mode": "case", "tc_n": 2, "source_n": 2, "device_note": "",
        "step": {"action": "capture", "verify": "seen"}, "blank_block": "class TestCase_2:\n    pass\n"}
SHARED = [{"source_id": "lib.py", "symbol": "analyse", "code": "SHARED-CODE", "why": "w",
           "tag": "ART lib.py:analyse", "py2_flagged": False}]


def test_shared_items_render_above_the_marker_and_the_unit_names_its_tags():
    p = render_prompt("pt_generate_step.jinja", {
        **BASE, "shared_fragments": SHARED, "shared_tags_for_unit": ["ART lib.py:analyse"],
        "shared_cli_reference": "REAL CLI REFERENCE shared by most units of this case (AW+):\n### tcpdump\n    tcpdump ...",
        "fragments": [{"source_id": "t.py", "symbol": "TestCase_8", "code": "OWN-CODE", "why": "w",
                       "tag": "ART t.py:TestCase_8", "py2_flagged": False}],
        "cli_reference": "REAL CLI REFERENCE (AW+):\n### show lldp\n    show lldp ..."})
    shared, unit = pc._split_unit_prompt(p)
    assert "SHARED-CODE" in shared and "SHARED-CODE" not in unit
    assert "### tcpdump" in shared and "### tcpdump" not in unit
    assert "OWN-CODE" in unit and "OWN-CODE" not in shared
    assert "### show lldp" in unit
    assert "mapped to THIS unit — adapt it here: `ART lib.py:analyse`" in unit
    assert "for THIS unit only" in unit


def test_a_unit_with_only_shared_code_is_not_told_it_has_none():
    p = render_prompt("pt_generate_step.jinja", {
        **BASE, "shared_fragments": SHARED, "shared_tags_for_unit": ["ART lib.py:analyse"],
        "shared_cli_reference": "", "fragments": [], "cli_reference": ""})
    _, unit = pc._split_unit_prompt(p)
    assert "None of the reviewer's selected fragments" not in unit
    assert "`ART lib.py:analyse`" in unit


def test_a_unit_with_nothing_at_all_is_still_told_so():
    p = render_prompt("pt_generate_step.jinja", {
        **BASE, "shared_fragments": [], "shared_tags_for_unit": [],
        "shared_cli_reference": "", "fragments": [], "cli_reference": ""})
    _, unit = pc._split_unit_prompt(p)
    assert "None of the reviewer's selected fragments" in unit


def test_the_render_uses_the_plan_not_a_second_derivation():
    src = (_SERVER / "routers" / "pytest_create.py").read_text(encoding="utf-8")
    body = src[src.index("def _render_unit_prompt"):src.index("def _unit_shape_ok")]
    assert "_shared_plan(ctx)" in body
    assert "_cli_reference_block(" not in body, "the CLI block is looked up once, in the plan"


# --- decision 3: the self-contained rule -------------------------------------------------

def test_the_self_contained_rule_is_in_the_shared_half_of_the_unit_prompt_only():
    p = render_prompt("pt_generate_step.jinja", {
        **BASE, "shared_fragments": [], "shared_tags_for_unit": [],
        "shared_cli_reference": "", "fragments": [], "cli_reference": ""})
    shared, unit = pc._split_unit_prompt(p)
    assert "EVERY UNIT IS SELF-CONTAINED" in shared
    assert "ESTABLISH that" in shared and "tear_down()" in shared
    assert "SELF-CONTAINED" not in unit
    # Not a shared rule: whole-script generation may legitimately chain cases.
    for name in ("pt_fill_rules.jinja", "pt_generate_script.jinja"):
        assert "SELF-CONTAINED" not in (_TPL / name).read_text(encoding="utf-8")
