"""Slice C (PLAN-generate-state-and-sequence-sanity, 2026-09-21): the extractor checks itself.

WHY. On AWPTCM-T33234 the step-5 physics error ("forced DUT vs auto partner" written as a
negative) and the step 6-vs-7 contradiction (the same crossover cable, two different
"matched pair" claims) were BORN at Extract Sequence and treated as axioms by every later
stage — generate, review, fix all built on them, and they were only found at the THIRD review
round, by a human. Terrence's shape: the extraction call also checks the sequence against a
maintained domain-facts block plus the CLI reference, every state-changing step carries a
`claim`, contradictions come back as `sanity` flags, and the Sequence page shows them.
WARN, never block.

Pinned here:
  * the domain-facts include exists, carries the load-bearing facts, and both the extraction
    and the review prompt render it;
  * the extraction prompt asks for the sanity pass and the extended output shape;
  * `extract_sequence` stores normalised claims on steps and the sanity flags on step2;
  * `save_sequence` carries `kind` / `claim` over from the stored row (the UI never sent
    them, so a setup step came back as a TestCase), but not across a re-ordered row, and drops
    the flags once the shape changes.
Offline: real module, monkeypatched run_prompt + persistence.
"""
import asyncio
import re
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SERVER = _REPO / "ask-ck" / "CK-main" / "CK_server"
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(_SERVER))

from routers import pytest_create as pc  # noqa: E402

_PROMPTS = _SERVER / "templates" / "prompts"
FACTS = (_PROMPTS / "_pt_domain_facts.jinja").read_text(encoding="utf-8")
KEY = "AWPTCM-TSAN1"


def _render(name, **ctx):
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(str(_PROMPTS)))
    base = {"case_key": KEY, "case_title": "t", "objective": "o", "steps": [{"description": "d"}],
            "cli_reference": "", "file_name": "f.py", "code": "x", "sequence": [], "lint_findings": [],
            "library_name": "", "library_code": ""}
    base.update(ctx)
    return env.get_template(name).render(**base)


# --- the facts ---------------------------------------------------------------------------

@pytest.mark.parametrize("fact", [
    "auto-MDI/MDI-X port adapts",           # the T33234 step-5 error
    "STRAIGHT-THROUGH cable (MDI ↔ MDI-X)",  # pairing by cable
    "Fibre has no MDI/MDI-X",
    "`configured` line and a `current` line",
    "Half duplex is impossible at 1 Gigabit",
    "never reports the literal `auto`",
])
def test_the_domain_facts_carry_each_load_bearing_fact(fact):
    assert fact in FACTS


def test_the_facts_block_has_a_layer_header_that_never_renders():
    assert "LAYER: PyTest Creator" in FACTS and "SPEC:" in FACTS
    assert "LAYER:" not in _render("pt_extract_sequence.jinja")


def test_both_prompts_render_the_facts():
    assert "## Domain facts" in _render("pt_extract_sequence.jinja")
    assert "## Domain facts" in _render("pt_review_script.jinja")


def test_the_extraction_prompt_asks_for_the_sanity_pass_and_the_shape():
    out = _render("pt_extract_sequence.jinja")
    assert "## Sanity pass" in out
    assert '"claim": {"cable"' in out and '"sanity": [' in out
    flat = " ".join(out.split())
    assert "cannot expect `down`" in flat               # forced DUT vs auto partner
    assert "force the PARTNER" in flat
    # the older rules the grounding tests pin are still there, un-moved
    assert "show ecofriendly" in out and "COVERAGE IS MANDATORY" in out


# --- normalisers -------------------------------------------------------------------------

def test_claims_are_normalised_to_the_four_keys_or_dropped():
    assert pc._normalize_claim({"cable": " crossover ", "dut": "mdix", "partner": "mdi",
                                "expect": "down", "junk": 1}) == \
        {"cable": "crossover", "dut": "mdix", "partner": "mdi", "expect": "down"}
    assert pc._normalize_claim({"cable": "", "expect": None}) is None
    assert pc._normalize_claim("crossover") is None
    assert pc._normalize_claim(None) is None


def test_sanity_flags_keep_only_in_range_steps_and_non_empty_issues():
    flags = pc._sanity_flags([{"steps": [7, 6, "6", 99, -1], "issue": "  two   claims disagree "},
                              {"steps": 3, "issue": "single"},
                              {"steps": [1], "issue": ""},
                              "garbage", None], 10)
    assert flags == [{"steps": [6, 7], "issue": "two claims disagree"},
                     {"steps": [3], "issue": "single"}]
    assert pc._sanity_flags(None, 3) == [] and pc._sanity_flags("x", 3) == []


# --- extract_sequence stores them -------------------------------------------------------

REPLY = {"sequence": [
    {"n": 1, "action": "set both ends to auto", "verify": "", "kind": "setup", "zephyr_step_idx": 1},
    {"n": 2, "action": "force DUT mdix, partner mdi over crossover", "verify": "link is down",
     "kind": "verify", "zephyr_step_idx": 2,
     "claim": {"cable": "crossover", "dut": "mdix", "partner": "mdi", "expect": "down"}},
    {"n": 3, "action": "read show interface", "verify": "current polarity present", "kind": "verify",
     "zephyr_step_idx": 2, "claim": "not a dict"},
], "sanity": [{"steps": [2, 3], "issue": "step 3 asserts a current value on a link step 2 expects down"}],
    "notes": "n"}


@pytest.fixture
def extraction(monkeypatch):
    sess = pc.PtSession(key=KEY)
    box = {"sess": sess}
    monkeypatch.setattr(pc, "_pt_get", lambda key: box["sess"])
    monkeypatch.setattr(pc, "_pt_persist", lambda s: box.__setitem__("persisted", s))

    def fake_fresh(key, apply_fn, attempts=0):
        apply_fn(box["sess"]); box["persisted"] = box["sess"]; return box["sess"]
    monkeypatch.setattr(pc, "_pt_persist_fresh", fake_fresh)
    monkeypatch.setattr(pc, "_data", lambda request: {})
    monkeypatch.setattr(pc, "_case_payload_fields", lambda s: {
        "objective": "o", "steps": [{"description": "s1"}, {"description": "s2"}]})
    monkeypatch.setattr(pc, "_case_title", lambda data, key: "t")
    monkeypatch.setattr(pc, "_cli_reference_for_case", lambda fields: "")
    monkeypatch.setattr(pc, "run_prompt", lambda *a, **k: {"content": __import__("json").dumps(REPLY),
                                                           "prompt": "p", "provider": "x", "model": "m"})

    async def no_dry(request):
        return False
    monkeypatch.setattr(pc, "_dry_run", no_dry)
    return box


def test_extract_sequence_stores_normalised_claims_and_the_flags(extraction):
    out = asyncio.run(pc.extract_sequence(KEY, request=None))
    seq = out["sequence"]
    assert seq[1]["claim"] == {"cable": "crossover", "dut": "mdix", "partner": "mdi", "expect": "down"}
    assert "claim" not in seq[0] and "claim" not in seq[2], "an unusable claim is dropped, not stored"
    assert out["sanity"] == [{"steps": [2, 3], "issue": "step 3 asserts a current value on a link step 2 expects down"}]
    assert extraction["persisted"].step2["sanity"] == out["sanity"]
    assert extraction["persisted"].step2["sequence"][1]["claim"]["expect"] == "down"


# --- save_sequence carries kind / claim over, drops the flags on a re-shape -----------------

@pytest.fixture
def saved(monkeypatch):
    sess = pc.PtSession(key=KEY)
    sess.step2 = {"sequence": [dict(s) for s in REPLY["sequence"][:2]],
                  "sanity": [{"steps": [1, 2], "issue": "i"}], "confirmed": True}
    sess.step2["sequence"][1]["claim"] = {"cable": "crossover", "dut": "mdix", "partner": "mdi", "expect": "down"}
    box = {"sess": sess}
    monkeypatch.setattr(pc, "_pt_get", lambda key: box["sess"])
    monkeypatch.setattr(pc, "_pt_persist", lambda s: box.__setitem__("persisted", s))
    monkeypatch.setattr(pc, "_case_payload_fields", lambda s: {"objective": "o", "steps": [{"description": "s1"}, {"description": "s2"}]})
    return box


def test_a_ui_save_that_only_edits_verify_text_keeps_kind_and_claim(saved):
    rows = [{"n": 1, "action": "set both ends to auto", "verify": "", "zephyr_step_idx": 1},
            {"n": 2, "action": "force DUT mdix, partner mdi over crossover", "verify": "link is DOWN (edited)", "zephyr_step_idx": 2}]
    out = asyncio.run(pc.save_sequence(KEY, body={"sequence": rows}))
    assert out["sequence"][0]["kind"] == "setup", "the setup step must not come back as a TestCase"
    assert out["sequence"][1]["kind"] == "verify"
    assert out["sequence"][1]["claim"]["expect"] == "down"
    assert out["sanity"] == [{"steps": [1, 2], "issue": "i"}], "same shape: flags kept"


def test_a_reordered_row_does_not_inherit_another_steps_kind_or_claim(saved):
    rows = [{"n": 1, "action": "force DUT mdix, partner mdi over crossover", "verify": "link is down", "zephyr_step_idx": 2},
            {"n": 2, "action": "set both ends to auto", "verify": "", "zephyr_step_idx": 1}]
    out = asyncio.run(pc.save_sequence(KEY, body={"sequence": rows}))
    assert "claim" not in out["sequence"][1]
    assert "kind" not in out["sequence"][0]
    assert out["sanity"] == [], "the shape changed: step-numbered flags would point at the wrong rows"


def test_a_row_the_ui_sends_with_kind_and_claim_keeps_its_own(saved):
    rows = [{"n": 1, "action": "set both ends to auto", "verify": "", "kind": "setup"},
            {"n": 2, "action": "brand new step", "verify": "v", "kind": "verify",
             "claim": {"cable": "straight", "dut": "mdi", "partner": "auto", "expect": "up", "x": 1}}]
    out = asyncio.run(pc.save_sequence(KEY, body={"sequence": rows}))
    assert out["sequence"][1]["claim"] == {"cable": "straight", "dut": "mdi", "partner": "auto", "expect": "up"}
    assert out["sequence"][1]["kind"] == "verify"
