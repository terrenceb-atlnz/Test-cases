"""`generate_steps.jinja` must ask for procedures with stated outcomes.

PHASE 2. The old prompt said *"expectedResult usually empty or brief"* and its only example
was `{"description": "...", "expectedResult": ""}`. The model did what the example showed:
**618 of 648 verification steps across the 53 committed bundles have no expected result**,
which is why the Phase -1 Zephyr gate now refuses every one of them.

It also said *"One or a few steps per major objective bullet"* and *"Use 'Verify...'"*, and
got exactly that: AWPTCM-T33303 contains the objective bullet with the word "Verify"
prepended, at 0.98 similarity, with an empty expectedResult. An objective bullet is a
declarative end state; a step must be an executable procedure.

Per `prompt-examples-are-the-spec`, the example is what the model implements, so the
example is what these tests check — not the prose beside it. `_prose` helpers keep a check
from matching the very sentence that forbids the thing.
"""
import json
import pathlib
import re

import pytest

from _prose import code_fences, flat

REPO = pathlib.Path(__file__).resolve().parents[1]
STEPS_TPL = REPO / "ask-ck" / "CK-main" / "CK_server" / "templates" / "prompts" / "generate_steps.jinja"
SERVER = REPO / "ask-ck" / "CK-main" / "CK_server"

TEXT = STEPS_TPL.read_text(encoding="utf-8")


def _example_steps():
    """The JSON array the prompt shows as its output specification."""
    match = re.search(r"\[\s*\{.*?\}\s*\]", TEXT, re.DOTALL)
    assert match, "the steps prompt no longer shows a JSON example — the example IS the spec"
    return json.loads(match.group(0))


# ------------------------------------------------------------------ the example is the spec

def test_every_example_step_has_a_non_empty_expected_result():
    """The defect, pinned. The old example's only expectedResult was the empty string."""
    steps = _example_steps()
    assert steps, "the example must contain at least one step"
    empty = [s["description"][:40] for s in steps if not (s.get("expectedResult") or "").strip()]
    assert not empty, f"example steps with no expectedResult teach the model to omit it: {empty}"


def test_example_expected_results_state_an_observable_value():
    """"Passes" / "works as expected" are not outcomes. Each example must show a real one."""
    vague = ("as expected", "works correctly", "is correct", "passes", "successful",
             "no errors", "behaves properly")
    for step in _example_steps():
        result = step["expectedResult"].lower()
        assert not any(v in result for v in vague), \
            f"vague expectedResult in the example: {step['expectedResult']!r}"
        # something measurable: a number, a bound, or a named observable
        assert re.search(r"\d", result), \
            f"expectedResult with no measurable value: {step['expectedResult']!r}"


def test_example_steps_are_procedures_not_restated_end_states():
    """A step must be executable. The old prompt's own rule produced "Verify <bullet>"."""
    for step in _example_steps():
        desc = step["description"].strip()
        assert not desc.lower().startswith("verify "), (
            f"the example opens a step with 'Verify ' — that is the grammatical "
            f"transposition Phase 2 exists to stop: {desc[:60]!r}")


def test_example_steps_name_their_test_data():
    """Test data (values, counts, timings) must appear in the example, not just the prose."""
    with_data = [s for s in _example_steps() if re.search(r"\d", s["description"])]
    assert len(with_data) >= 2, \
        "the example must demonstrate concrete test data in the step description"


def test_example_is_valid_json_in_the_shape_the_parser_expects():
    """The server parses this into {'description','expectedResult'} objects."""
    for step in _example_steps():
        assert set(step) == {"description", "expectedResult"}, \
            f"unexpected keys in an example step: {sorted(step)}"
        assert isinstance(step["description"], str) and step["description"].strip()


def test_example_does_not_hardcode_a_port_or_a_product():
    """Scripts must be hardware-agnostic; the steps they come from must be too."""
    for step in _example_steps():
        blob = f"{step['description']} {step['expectedResult']}"
        assert not re.search(r"\bport\d+\.\d+\.\d+\b", blob), \
            f"the example hardcodes a port name: {blob[:80]!r}"
        for product in ("x230", "x950", "IE520", "AR4050"):
            assert product.lower() not in blob.lower(), \
                f"the example names a product: {product}"


# ------------------------------------------------------------------------ the prose contract

def test_the_usually_empty_instruction_is_gone():
    """The single sentence that produced 618 empty expected results."""
    assert "usually empty" not in flat(TEXT).lower(), \
        "the prompt still tells the model expectedResult is usually empty"


def test_prose_requires_a_non_empty_expected_result():
    assert "non-empty expectedresult" in flat(TEXT).lower(), \
        "the prompt must state the expectedResult requirement, not only demonstrate it"


def test_prose_distinguishes_an_end_state_from_a_procedure():
    body = flat(TEXT).lower()
    assert "end state" in body and "procedure" in body, \
        "the prompt must explain why restating an objective bullet is not a step"


def test_prompt_no_longer_asks_for_one_step_per_bullet():
    """That rule is what made steps track bullets 1:1 at 0.98 similarity."""
    assert "one or a few steps per major objective bullet" not in flat(TEXT).lower()


# ------------------------------------------------------ 2.2: the corpus context is rendered

@pytest.mark.parametrize("field", ["testlink_selections", "zephyr_selections",
                                   "atp_selections", "gaps"])
def test_steps_prompt_renders_the_context_the_server_already_builds(field):
    """`_synthesis_context` builds these for every call; the steps prompt ignored all four.

    The objective prompt renders them, so step synthesis was working from strictly less
    evidence than the stage before it — for no reason other than the template never
    referencing the variables.
    """
    assert "{{ " + field in TEXT or "{% for s in " + field in TEXT or "{% if " + field in TEXT, \
        f"generate_steps.jinja never renders {field}, which the server builds for it"


def test_the_rendered_context_fields_exist_in_synthesis_context():
    """Guard against rendering a variable the server does not supply (always empty)."""
    source = (SERVER / "llm.py").read_text(encoding="utf-8")
    block = source[source.index("def _synthesis_context"):]
    block = block[:block.index("\ndef ", 1)]
    for field in ("testlink_selections", "zephyr_selections", "atp_selections", "gaps"):
        assert f'"{field}"' in block, \
            f"the steps prompt renders {field} but _synthesis_context does not build it"


def test_template_renders_without_any_optional_context():
    """A sparse case (no selections, no gaps) must still produce a valid prompt."""
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(str(STEPS_TPL.parent)))
    out = env.get_template(STEPS_TPL.name).render(
        case_key="AWPTCM-T00001", primary=None, objective="<ul><li>a thing</li></ul>",
        testlink_selections=[], zephyr_selections=[], atp_selections=[], gaps="")
    assert "AWPTCM-T00001" in out
    assert "a thing" in out
    # empty section headers must not be emitted at all
    assert "## TestLink selections" not in out
    assert "## Known coverage gaps" not in out


def test_template_renders_the_sections_when_context_is_present():
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(str(STEPS_TPL.parent)))
    out = env.get_template(STEPS_TPL.name).render(
        case_key="AWPTCM-T00001", primary={"w": "LLDP"}, objective="<ul><li>a thing</li></ul>",
        testlink_selections=[{"id_or_key": "TL-1", "title": "an exemplar"}],
        zephyr_selections=[{"key": "Z-1", "title": "a zephyr case"}],
        atp_selections=[{"id_or_key": "ART-1", "title": "art coverage"}],
        gaps="nothing covers the negative path")
    for expected in ("TL-1", "an exemplar", "Z-1", "ART-1",
                     "nothing covers the negative path", "LLDP"):
        assert expected in out, f"{expected!r} missing from the rendered steps prompt"
