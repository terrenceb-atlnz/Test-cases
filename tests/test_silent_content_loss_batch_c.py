"""Regression tests for adversarial-review batch C (2026-07-27g) — silent content loss.

One theme: content silently deleted or corrupted by a too-loose match or too-loose
interpolation, where the correct idiom already existed a few lines away in the same file.

  - llm.py:941 — the traceability-note strip used unanchored `"Traceability" in ...`,
    but "Traceability" is domain vocabulary the prompt itself uses. A legitimate first
    step ("Verify Traceability of the ART logs to the test report") was DELETED before
    note_step is prepended, so it was lost outright — and validate_zephyr_payload only
    needs >=2 steps, so the case exported to Zephyr a step short with no warning.
  - pt_script_template.py.jinja — 13 slots interpolated step text into single-quoted
    Python literals sanitized only with replace("'",""). A typed newline or trailing
    backslash produced an UNCOMPILABLE skeleton, shown straight to the user on the
    preview path and fed to the model on the generate path as the structure to copy.
  - pytest_create.py:743 — _restamp_provenance's identity fallback mapped a SETUP step's
    maps_to onto whichever TestCase shared its number, overwriting that class's correct
    tag, so the authoritative provenance line pointed at the wrong source script.
  - pytest_create.py:765 — the echo regex stripped ANY leading comment mentioning
    ART/SVT/legacy/AI, deleting real reviewer rationale from the saved script.

No network, no LLM, no testbox.
"""
import pathlib

import pytest
from jinja2 import Environment, FileSystemLoader

from llm import _is_traceability_note, MINIMAL_TRACEABILITY_NOTE
from routers.pytest_create import (
    _collapse_step_text,
    _fragment_tag,
    _is_provenance_echo,
    _restamp_provenance,
)

_TEMPLATES = (pathlib.Path(__file__).resolve().parents[1]
              / "ask-ck" / "CK-main" / "CK_server" / "templates")


# --- llm.py:941 — the traceability-note strip -----------------------------------
@pytest.mark.parametrize("desc", [
    "Verify Traceability of the ART logs to the test report",
    "Verify the Traceability matrix export completes",
    "Note: ensure the DUT is powered before starting",
    "Verify port link comes up at 1000M full duplex",
])
def test_real_steps_are_not_mistaken_for_the_note(desc):
    """Legitimate first steps must survive. Each of these was silently deleted."""
    assert not _is_traceability_note(desc)


@pytest.mark.parametrize("desc", [
    MINIMAL_TRACEABILITY_NOTE,
    "Note: Related ART Tests linked in Traceability",
    "  Note: Related ART Tests linked in Traceability.  ",
    "Note: Related ART Tests linked in Traceability — see AWPTCM-T1",
])
def test_the_real_note_is_still_recognized(desc):
    """The echoed note must still be stripped, or it would be duplicated."""
    assert _is_traceability_note(desc)


def test_note_predicate_handles_empty_and_none():
    assert not _is_traceability_note("")
    assert not _is_traceability_note(None)


def test_synthesize_steps_keeps_a_traceability_named_first_step():
    """End-to-end on the real assembly logic: the note is prepended, nothing dropped."""
    llm_steps = [
        {"description": "Verify Traceability of the ART logs", "expectedResult": "match"},
        {"description": "Verify link is up", "expectedResult": "up"},
    ]
    # Mirrors llm.py's assembly: strip only a genuine echoed note, then prepend.
    kept = llm_steps[1:] if _is_traceability_note(llm_steps[0]["description"]) else llm_steps
    final = [{"description": MINIMAL_TRACEABILITY_NOTE, "expectedResult": ""}] + kept
    assert len(final) == 3, "a real verification step was dropped"
    assert final[1]["description"] == "Verify Traceability of the ART logs"


# --- pt_script_template.py.jinja — the 13 string-literal slots -------------------
def _render(action, verify, kind="verify"):
    """Render via the REAL skeleton env, so the pyliteral filter under test is the
    one production uses (a bare Environment would not have it registered)."""
    from routers.pytest_create import _skeleton_env
    return _skeleton_env.get_template("pt_script_template.py.jinja").render(
        case_key="AWPTCM-T1",
        steps=[{"n": 1, "action": action, "verify": verify, "kind": kind}],
        switches=["dut"],
    )


@pytest.mark.parametrize("kind", ["verify", "physical", "manual"])
@pytest.mark.parametrize("text", [
    "Enable RSTP on port1.0.1\nthen save config",   # the reported newline case
    "Set the path to C:\\",                          # trailing backslash
    "Use the 'show' command",                        # single quote
    'Use the "show" command',                        # double quote
    "It's a \"mixed\" case\nwith C:\\ path",        # all of it at once
    "Verify link up",                                # plain control
])
def test_skeleton_always_compiles(kind, text):
    """A reviewer's typed text must never produce an uncompilable skeleton.

    The preview path returns this straight to the UI with no LLM and no compile check,
    and the generate path feeds it to the model as the structure to reproduce.
    """
    compile(_render(text, text, kind), "<skeleton>", "exec")


def test_apostrophes_are_preserved_not_stripped():
    """The old replace("'","") mangled legitimate text; tojson keeps it intact."""
    out = _render("Check the port's state", "the port's LED is green")
    assert "port's state" in out


def test_template_has_no_replace_quote_slots_left():
    """Drift guard: the fragile idiom must not come back."""
    src = (_TEMPLATES / "pt_script_template.py.jinja").read_text(encoding="utf-8")
    assert 'replace("\'", "")' not in src, (
        "a step-text slot still strips quotes instead of using | pyliteral")
    # Every step-text interpolation must go through the escaping filter.
    assert "| pyliteral }}" in src


def test_generated_literals_are_readable():
    """pyliteral (repr) over tojson: same escaping, but no \\u0027 noise.

    These scripts are read and edited by a human reviewer, so legibility is part of
    the artefact's job.
    """
    out = _render("Check the port's state", "ok")
    assert "\\u0027" not in out, "apostrophes were JSON-escaped into unreadable output"


def test_collapse_step_text_normalizes_write_path():
    """Belt-and-braces: multi-line step text is collapsed when stored."""
    step = {"n": 1, "action": "line one\nline two", "verify": "  a   b  "}
    _collapse_step_text(step)
    assert step["action"] == "line one line two"
    assert step["verify"] == "a b"


def test_collapse_step_text_leaves_non_strings_alone():
    step = {"n": 1, "action": None, "verify": 42}
    _collapse_step_text(step)
    assert step["action"] is None and step["verify"] == 42


# --- pytest_create.py:743 — setup-step provenance mis-attribution ----------------
def test_setup_mapped_fragment_does_not_clobber_a_real_tag():
    """The reported scenario: a setup step ahead of the verifies shifts the numbering.

    Fragment A maps to setup step 1 (no TestCase of its own); fragment B maps to orig
    step 2, which becomes TestCase_1. The identity fallback let A overwrite B's tag.
    """
    sequence = [
        {"n": 1, "kind": "setup", "action": "configure VLAN 10"},
        {"n": 2, "kind": "verify", "action": "a", "verify": "x"},
        {"n": 3, "kind": "verify", "action": "b", "verify": "y"},
    ]
    fragments = [
        {"source_id": "art/foo.py", "loc": (10, 20), "maps_to": [1]},   # setup
        {"source_id": "art/bar.py", "loc": (30, 40), "maps_to": [2]},   # -> TestCase_1
    ]
    code = ("class TestCase_1(ATTestCase.TestCase):\n"
            "    def main(self):\n"
            "        self.log('hi')\n")
    out = _restamp_provenance(code, fragments, "m", sequence=sequence)
    tags = [l.strip() for l in out.splitlines() if l.strip().startswith("#")]
    assert tags, "no provenance tag was stamped"
    assert "bar.py" in tags[0], f"wrong fragment attributed: {tags[0]}"
    assert "foo.py" not in tags[0]


def test_legacy_identity_path_still_works():
    """With no sequence (legacy callers) the numbers coincide — keep identity."""
    fragments = [{"source_id": "art/baz.py", "loc": (1, 2), "maps_to": [1]}]
    code = ("class TestCase_1(ATTestCase.TestCase):\n"
            "    def main(self):\n"
            "        self.log('hi')\n")
    out = _restamp_provenance(code, fragments, "m", sequence=None)
    assert "baz.py" in out


# --- pytest_create.py:765 — the provenance-echo strip ----------------------------
@pytest.mark.parametrize("comment", [
    "        # SVT 3009 replug pattern: poll until the operator reseats the module",
    "        # legacy CLI parsing retained: this firmware has no 'show pluggable detail'",
    "        # AI-generated helper below needs review",
    "        # configure the port for 1000M full duplex",
])
def test_reviewer_rationale_survives(comment):
    """Real commentary that merely mentions a tag family must NOT be deleted."""
    code = ("class TestCase_1(ATTestCase.TestCase):\n"
            "    def main(self):\n"
            f"{comment}\n"
            "        self.log('x')\n")
    out = _restamp_provenance(code, [], "m", sequence=None)
    assert comment.strip() in out, "a legitimate rationale comment was deleted"


@pytest.mark.parametrize("comment", [
    "        # ART suite/foo.py lines 10-20",
    "        # AI vllm-fast 2026-07-27",
    "        # Provenance tag for this fragment: # AI x",
])
def test_model_echoed_tags_are_still_stripped(comment):
    """The echo must still go, or it duplicates alongside the authoritative stamp."""
    code = ("class TestCase_1(ATTestCase.TestCase):\n"
            "    def main(self):\n"
            f"{comment}\n"
            "        self.log('x')\n")
    out = _restamp_provenance(code, [], "m", sequence=None)
    assert comment.strip() not in out


def test_the_real_emitted_tag_shape_is_recognized_as_an_echo():
    """Whatever _fragment_tag emits must be strippable — else re-runs duplicate it.

    fix_script re-runs _restamp_provenance over already-stamped code, so this is the
    property that keeps a revision from accumulating tags.
    """
    assert _is_provenance_echo("        " + _fragment_tag("art/suite/foo.py", (10, 20)))
    assert _is_provenance_echo("        " + _fragment_tag("svt/x/bar.py", None))


def test_restamp_is_idempotent():
    """Re-running over stamped output must not accumulate tags (the fix_script path)."""
    fragments = [{"source_id": "art/foo.py", "loc": (10, 20), "maps_to": [1]}]
    code = ("class TestCase_1(ATTestCase.TestCase):\n"
            "    def main(self):\n"
            "        self.log('hi')\n")
    once = _restamp_provenance(code, fragments, "m", sequence=None)
    twice = _restamp_provenance(once, fragments, "m", sequence=None)
    assert once == twice
    assert once.count("# ART") == 1


def test_echo_strip_is_capped():
    """A long run of comments is documentation, not an echo — only the cap is dropped."""
    body = "\n".join([
        "        # ART a/b.py lines 1-2",
        "        # ART c/d.py lines 3-4",
        "        # ART e/f.py lines 5-6",
    ])
    code = ("class TestCase_1(ATTestCase.TestCase):\n"
            "    def main(self):\n"
            f"{body}\n"
            "        self.log('x')\n")
    out = _restamp_provenance(code, [], "m", sequence=None)
    assert "e/f.py" in out, "strip ran past the cap"


# --- pt_generate_script.jinja:54 — the Py2 marker the model was told to look for --
def test_py2_marker_reaches_the_generate_prompt():
    """Rule 4 tells the model Py2 fragments are 'marked ⚠ PYTHON 2' — so they must be.

    The marker was only ever emitted inside the SKELETON (_render_skeleton), never in
    the prompt's 'Reviewer-approved fragments' section, so the rule pointed at something
    the model could not see and the steer was inert.
    """
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader(str(_TEMPLATES / "prompts")))
    out = env.get_template("pt_generate_script.jinja").render(
        fragments=[
            {"source_id": "legacy/a.py", "symbol": "f1", "maps_to": [1],
             "tag": "# legacy a.py", "why": "w", "code": "print 1", "py2_flagged": True},
            {"source_id": "art/b.py", "symbol": "f2", "maps_to": [2],
             "tag": "# ART b.py", "why": "w", "code": "print(1)", "py2_flagged": False},
        ],
        py2_flagged=True, case_key="T1", case_title="t", steps=[], skeleton="",
        device_note="", framework_surface={}, exemplar="", switches=[],
    )
    headings = [l for l in out.splitlines() if l.startswith("### From")]
    assert "⚠ PYTHON 2" in headings[0], "flagged fragment carries no marker"
    assert "⚠ PYTHON 2" not in headings[1], "clean fragment was wrongly marked"
