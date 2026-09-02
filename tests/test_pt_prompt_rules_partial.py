"""The fill rules were EXTRACTED, not rewritten — the whole-script prompt is unchanged.

WHY THIS TEST EXISTS (2026-09-02)
---------------------------------
Per-unit generation needs the same slot-filling rules the whole-script prompt uses. Two
copies would drift, and the drift would be invisible: both prompts would keep working, on
diverging rules, and the difference would surface as inconsistent generated code months
later. So lines 50-251 of `pt_generate_script.jinja` were lifted verbatim into
`pt_fill_rules.jinja` and both templates now `{% include %}` it.

An extraction that changes the rendered output is not an extraction. CLAUDE.md is explicit
that a prompt change needs its design document read first; this was deliberately NOT a
prompt change, and this test is what makes that claim checkable rather than asserted.

It caught a real error on the first attempt: two blank lines vanished. Jinja here runs with
`trim_blocks=False`, so the newline after the preceding `{% endif %}` is real output, and
with `keep_trailing_newline=False` the partial's own trailing newline is stripped — so the
blank line before `## Output format` has to live in the parent, not the partial. Neither is
obvious from reading the diff, and neither would have been noticed without rendering both.

SNAPSHOT UPDATED ONCE, DELIBERATELY (2026-09-02, Terrence's call)
-----------------------------------------------------------------
Three lines were reworded — rules 4b, 4b-ii and 5 said "the REAL CLI REFERENCE above" /
"injected above" / "the reference above". Position words cannot live in a SHARED partial:
pt_generate_script.jinja puts the CLI reference before the rules, pt_generate_step.jinja
puts it after, so "above" was false for one caller. They now read "in this prompt", "was
injected" and "the CLI reference". Meaning is unchanged; only the pointer is.

Why it mattered enough to touch the rules at all: the per-unit prompt is ordered so that
everything invariant precedes everything that varies, which is what lets prompt caching
reuse a shared prefix across a case's 30 unit calls. The wording was the only thing forcing
the varying CLI reference above the 14,794-char rules block, and that placement halved the
measured shared prefix — 11,143 chars down to 5,663. The diff was verified to be these
three lines and nothing else before the snapshot was regenerated.

Everything below still holds: the rules live in one file, and any FURTHER change to the
rendered whole-script prompt must be as deliberate as this one was.
"""
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SERVER = _REPO / "ask-ck" / "CK-main" / "CK_server"
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(_SERVER))

from llm import render_prompt  # noqa: E402

# The rules reference these context keys; the values only have to exercise the branches.
CTX = {
    "case_key": "K", "case_title": "T", "file_name": "f.py",
    "skeleton": "class TestCase_1:\n    pass\n",
    "fragments": [{"source_id": "a.py", "symbol": "s", "maps_to": [1], "tag": "# ART a.py",
                   "why": "w", "code": "def s():\n    pass\n", "py2_flagged": False}],
    "framework_surface": {"ATTestSet": {"classes": {"TestSet": {"methods": [{"name": "log"}]}},
                                        "functions": [{"name": "yesNo"}]}},
    "cli_reference": "CLI reference\nshow lldp",
    "device_note": "dut is swi_a", "py2_flagged": True,
    "bound_devices": ["tb", "swi_a"], "model_name": "opus", "gen_date": "2026-09-02",
}

# The rendered whole-script prompt for this context. Regenerated only when the rules are
# deliberately changed — design document first (CLAUDE.md), diff reviewed line by line,
# then the snapshot updated knowingly. Done exactly once so far; see the module docstring.
_SNAPSHOT = _REPO / "tests" / "data" / "pt_generate_script_rendered.txt"


def test_the_partial_exists_and_both_prompts_include_it():
    D = _SERVER / "templates" / "prompts"
    assert (D / "pt_fill_rules.jinja").exists()
    for t in ("pt_generate_script.jinja", "pt_generate_step.jinja"):
        assert "{% include 'pt_fill_rules.jinja' %}" in (D / t).read_text(encoding="utf-8")


def test_the_rules_live_in_exactly_one_place():
    D = _SERVER / "templates" / "prompts"
    marker = "## Rules for filling the slots"
    holders = [t.name for t in D.glob("*.jinja") if marker in t.read_text(encoding="utf-8")]
    assert holders == ["pt_fill_rules.jinja"], f"the rules heading appears in {holders}"


def test_the_whole_script_prompt_renders_exactly_as_it_did_before_the_extraction():
    got = render_prompt("pt_generate_script.jinja", CTX)
    if not _SNAPSHOT.exists():                      # first run writes the baseline
        _SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        _SNAPSHOT.write_text(got, encoding="utf-8")
        return
    want = _SNAPSHOT.read_text(encoding="utf-8")
    assert got == want, (
        "the whole-script prompt changed. If that was deliberate, read the design doc "
        "first (CLAUDE.md) and then update tests/data/pt_generate_script_rendered.txt.")


def test_the_per_unit_prompt_renders_and_carries_the_rules():
    out = render_prompt("pt_generate_step.jinja", {
        **CTX, "mode": "testcase", "tc_n": 1, "source_n": 3,
        "step": {"n": 3, "action": "select a TLV", "verify": "it shows as selected"},
        "setup_steps": [], "blank_block": "class TestCase_1:\n    pass",
        "devices": ["tb", "swi_a"],
    })
    assert "## Rules for filling the slots" in out
    assert "TestCase_1" in out and "sequence step 3" in out
    assert "it shows as selected" in out


def test_the_per_unit_prompt_renders_for_the_setup_unit_too():
    out = render_prompt("pt_generate_step.jinja", {
        **CTX, "mode": "setup", "tc_n": None, "source_n": None, "step": {},
        "setup_steps": [{"n": 1, "action": "baseline config"}],
        "blank_block": "    def configure(self):\n        pass",
        "devices": ["swi_a"],
    })
    assert "suite setup" in out
    assert "baseline config" in out
    assert "no `passed()`" in out
