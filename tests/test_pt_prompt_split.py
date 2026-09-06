"""The unit prompt is TWO blocks: a case-constant system half and a per-unit user half.

WHY (token-efficiency decision 8, 2026-09-07)
--------------------------------------------
After the 2026-09-04 transport fix the 38 unit prompts of AWPTCM-T44297 shared their first
19,456 characters and the cache still read ZERO tokens on every call — sequential or
parallel. The API matches a prompt cache only at content-block boundaries and the client's
breakpoints; the Claude CLI sets those on the system prompt and on the user message. A
shared prefix inside one user block whose tail differs can never hit. Probe, same day: the
shared half inside the user block -> 0 read on the second call; the same half as
--system-prompt -> 7,879 of 8,059 read, at one twelfth of the price.

So the rendered prompt carries a visible SPLIT MARKER after the fill rules. The server sends
everything above it as the system prompt (behind the code steer) and everything below as the
user message. The reviewer still sees and edits ONE prompt; an edit that drops the marker is
sent whole as the user turn — correct, merely uncached.

Pinned here: exactly one marker, placed after the rules and before the unit; the shared half
is byte-identical across units that differ in everything per-unit (including the two flags
the rules branch on, which are now CASE-level); the call sends the halves to the right
parameters; and the debug log keeps the raw cache fields so "did it cache?" is a field.
"""
import os
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SERVER = _REPO / "ask-ck" / "CK-main" / "CK_server"
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(_SERVER))

import llm_debug  # noqa: E402
from llm import render_prompt  # noqa: E402
from routers import pytest_create as pc  # noqa: E402

_SRC = (_SERVER / "routers" / "pytest_create.py").read_text(encoding="utf-8")
_CODE = re.sub(r'#[^\n]*', '', re.sub(r'"""[\s\S]*?"""', '', _SRC))

BASE = {
    "case_key": "AWPTCM-T00001", "case_title": "A case",
    "setup_steps": [{"n": 1, "action": "configure"}],
    "devices": ["dut", "tb"],
    "framework_surface": {"framework.ATLibrary": {"classes": {}, "functions": []}},
    "model_name": "m", "gen_date": "2026-09-07",
    # the CASE-level flags the shared half branches on
    "py2_flagged": True, "rules_cli_reference": True,
    "split_marker": pc._PT_PROMPT_SPLIT,
}
UNIT_A = {**BASE, "mode": "case", "tc_n": 1, "source_n": 1,
          "device_note": "Reused fragments reference these device names: dut.",
          "step": {"action": "act one", "verify": "ver one"},
          "blank_block": "class TestCase_1:\n    pass\n",
          "fragments": [{"source_id": "a.py", "symbol": "x", "code": "c", "why": "w",
                         "tag": "t", "py2_flagged": True}],
          "cli_reference": "REAL CLI REFERENCE\nshow lldp neighbors"}
UNIT_B = {**BASE, "mode": "case", "tc_n": 24, "source_n": 26,
          "device_note": "",
          "step": {"action": "act two", "verify": "ver two"},
          "blank_block": "class TestCase_24:\n    pass\n",
          "fragments": [],
          "cli_reference": ""}                       # this unit has NO reference block


def _render(ctx):
    return render_prompt("pt_generate_step.jinja", ctx)


# --- the marker -----------------------------------------------------------------------

def test_exactly_one_marker_after_the_rules_and_before_the_unit():
    p = _render(UNIT_A)
    assert p.count(pc._PT_PROMPT_SPLIT) == 1
    i = p.index(pc._PT_PROMPT_SPLIT)
    assert p.index("## Rules for filling the slots") < i < p.index("## Your unit")
    # On a line of its own, so a line-wise split finds it.
    assert re.search(rf"(?m)^{re.escape(pc._PT_PROMPT_SPLIT)}$", p)


def test_the_shared_half_is_byte_identical_for_units_that_differ_in_everything_else():
    """A and B disagree on fragments, device note, and whether a CLI reference exists —
    exactly the values that used to leak into the rules and end the shared prefix early."""
    a, b = _render(UNIT_A), _render(UNIT_B)
    n = len(os.path.commonprefix([a, b]))
    assert n >= a.index(pc._PT_PROMPT_SPLIT) + len(pc._PT_PROMPT_SPLIT)
    sa, _ = pc._split_unit_prompt(a)
    sb, _ = pc._split_unit_prompt(b)
    assert sa == sb
    # And it is the whole invariant region, not a stub: the rules are in it.
    assert "## Rules for filling the slots" in sa and "NEVER invent CLI output" in sa


def test_the_rules_cli_flag_is_case_level_not_this_units_block():
    """B has no per-unit reference, yet the rules half still carries 4b because the CASE
    has one. The per-unit block below the line is still per unit."""
    b = _render(UNIT_B)
    shared, unit = pc._split_unit_prompt(b)
    assert "NEVER invent CLI output" in shared
    assert "## REAL CLI REFERENCE" not in unit
    a = _render(UNIT_A)
    _, unit_a = pc._split_unit_prompt(a)
    assert "show lldp neighbors" in unit_a


# --- the split -------------------------------------------------------------------------

def test_split_returns_the_two_halves_clean():
    p = _render(UNIT_A)
    shared, unit = pc._split_unit_prompt(p)
    assert pc._PT_PROMPT_SPLIT not in shared and pc._PT_PROMPT_SPLIT not in unit
    assert shared.startswith("You are filling ONE unit")
    assert unit.startswith("## Your unit: TestCase_1")
    assert not shared.endswith("\n")


def test_a_prompt_without_the_marker_goes_whole_as_the_user_turn():
    assert pc._split_unit_prompt("just text\nno marker") == ("", "just text\nno marker")
    assert pc._split_unit_prompt("") == ("", "")


def test_the_system_prompt_is_the_code_steer_then_the_shared_half():
    sysp = pc._unit_system_prompt("SHARED")
    assert sysp.startswith(pc._CODE_SYSTEM_PROMPT) and sysp.endswith("\n\nSHARED")
    assert pc._unit_system_prompt("") == pc._CODE_SYSTEM_PROMPT


# --- the call ----------------------------------------------------------------------------

UNIT = {"id": "tc1", "kind": "testcase", "tc_n": 1, "label": "TestCase_1",
        "block": "class TestCase_1(ATTestCase.TestCase):\n    def main(self):\n        pass"}
REPLY = "```python\nclass TestCase_1(ATTestCase.TestCase):\n    def main(self):\n        pass\n```"


def _capture(monkeypatch):
    seen = {}

    def fake(prompt, llm_config=None, timeout=0, dry_run=False, system=None,
             max_tokens=None, template="(verbatim)"):
        seen.update(prompt=prompt, system=system)
        return {"content": REPLY, "error": False, "usage": None,
                "provider": "claude", "model": "opus", "auth_method": "claude_code"}
    monkeypatch.setattr(pc, "run_prompt_text", fake)
    monkeypatch.setattr(pc, "_pt_persist_fresh", lambda *a, **k: None)
    return seen


def test_the_call_sends_the_shared_half_as_system_and_the_unit_half_as_the_prompt(monkeypatch):
    seen = _capture(monkeypatch)
    p = _render(UNIT_A)
    out = pc._unit_call_and_store("AWPTCM-T00001", "tc1", p, False, UNIT, {})
    assert out["status"] == "ok", out
    shared, unit = pc._split_unit_prompt(p)
    assert seen["prompt"] == unit
    assert seen["system"] == pc._CODE_SYSTEM_PROMPT + "\n\n" + shared


def test_an_edited_prompt_that_lost_the_marker_is_sent_whole_uncached(monkeypatch):
    seen = _capture(monkeypatch)
    edited = _render(UNIT_A).replace(pc._PT_PROMPT_SPLIT, "")
    pc._unit_call_and_store("AWPTCM-T00001", "tc1", edited, True, UNIT, {})
    assert seen["prompt"] == edited
    assert seen["system"] == pc._CODE_SYSTEM_PROMPT


def test_the_context_answers_the_rule_flags_once_per_case():
    body = _CODE[_CODE.index("def _pt_generation_context"):_CODE.index("def _fragments_for_unit")]
    assert '"case_py2_flagged"' in body and '"case_cli_reference"' in body
    render = _CODE[_CODE.index("def _render_unit_prompt"):_CODE.index("def _unit_shape_ok")]
    assert 'ctx["case_py2_flagged"]' in render and 'ctx["case_cli_reference"]' in render
    assert 'any(f.get("py2_flagged") for f in frags)' not in render


# --- the evidence -------------------------------------------------------------------------

def test_the_debug_log_keeps_the_raw_cache_fields_and_still_folds_them():
    u = llm_debug.normalize_usage("claude_code", {
        "usage": {"input_tokens": 1, "cache_creation_input_tokens": 180,
                  "cache_read_input_tokens": 7879, "output_tokens": 8},
        "total_cost_usd": 0.0065})
    assert u["input_tokens"] == 8060 and u["total_tokens"] == 8068
    assert u["cache_read_input_tokens"] == 7879
    assert u["cache_creation_input_tokens"] == 180


def test_the_debug_record_carries_the_system_text():
    assert "system" in llm_debug._META_WHITELIST
    src = (_SERVER / "llm.py").read_text(encoding="utf-8")
    fn = src[src.index("def _call_llm_with_meta"):src.index("def _call_llm_raw")]
    assert 'meta["system"] = system' in fn
    assert '"system": system' in fn                      # the dry-run preview too
