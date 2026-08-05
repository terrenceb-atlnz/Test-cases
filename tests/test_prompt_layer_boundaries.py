"""Requirements must not bleed between the Test Case Generator and the PyTest Creator.

THE PIPELINE HAS TWO HALVES WITH DIFFERENT JOBS (memory `pipeline-layer-contract`):

  * Test Case Generator — `generate_objectives.jinja` (step 4), `generate_steps.jinja`
    (step 5). Produces a Zephyr MANUAL case. Deliberately NON-prescriptive: no expected
    results, no exact values, no CLI. Spec: OBJECTIVE_DRAFTING_PROCESS.md Steps 1-2.
  * PyTest Creator — `pt_extract_sequence.jinja` (step 2), `pt_generate_script.jinja`
    (step 6). Produces a runnable script. PRESCRIPTION ENTERS HERE — PLAN-pytest-creator.md
    :128 is literally "extract a PRESCRIPTIVE test-step sequence". Real CLI grounding
    belongs in both. Specs: PLAN-pytest-creator.md, TEMPLATE-SPEC.md, LOGGING-CONTRACT.md.

On 2026-08-05 four rules were reversed in `generate_steps.jinja`, all of them script-layer
requirements that had arrived one stage too early: a mandatory non-empty `expectedResult`,
"name the test data (values, counts, interfaces, timings)", "assert only on what the device
reports", and an injected CLI reference block. Three came from one autonomous commit; the
fourth was added and reverted the same day. A rule-by-rule review against the CODE passed
all four, because consistency-with-implementation cannot detect a rule from the wrong layer.

Three safeguards, deliberately different in kind:
  A. the context a Test Case Generator prompt may RECEIVE is whitelisted — this is the pipe
     device data flows through, and closing it blocks the whole class;
  B. the Test Case Generator prompts may not CONTAIN device vocabulary;
  C. every prompt carries a layer header naming its spec, so whoever edits it knows one
     exists — both 2026-08-05 failures were "didn't know there was a spec".

B AND C ARE SCOPED, AND THE SCOPE IS LOAD-BEARING: B must never be applied to the Creator
prompts. Phase 4 injects real harvested output into both, containing `awplus#`,
`awplus(config-if)#` and `port1.0.4` BY DESIGN. A device-vocabulary ban there would fail on
its first run and the "fix" would be to strip the grounding that makes generated scripts
assert against real device output — the safeguard causing the damage it exists to prevent.
"""
import pathlib
import re
import sys

import pytest

from _prose import strip_jinja_comments

REPO = pathlib.Path(__file__).resolve().parents[1]
SERVER = REPO / "ask-ck" / "CK-main" / "CK_server"
PROMPTS = SERVER / "templates" / "prompts"
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))

import llm  # noqa: E402

TEST_CASE_GENERATOR = ["generate_objectives.jinja", "generate_steps.jinja"]
PYTEST_CREATOR = ["pt_extract_sequence.jinja", "pt_generate_script.jinja"]
ALL_PROMPTS = TEST_CASE_GENERATOR + PYTEST_CREATOR


# ============================================================== A. what may come IN

# `_synthesis_context` builds these; `synthesize_steps` adds `objective`. Anything else is
# a new channel into the layer and must be a deliberate decision, not a quiet addition.
# `cli_reference` was added here on 2026-08-05 and reverted; this list is what would have
# caught it the moment it was written.
ALLOWED_CONTEXT = {
    "case_key", "primary", "testlink_selections", "zephyr_selections",
    "atp_selections", "gaps", "art_string",
}


def _capture_context(monkeypatch, which):
    """Run a synthesis call with the LLM stubbed and return the render context."""
    seen = {}

    def fake_render(name, ctx):
        seen[name] = dict(ctx)
        return "PROMPT"

    monkeypatch.setattr(llm, "render_prompt", fake_render)
    monkeypatch.setattr(llm, "_resolve_llm_runtime", lambda cfg: {
        "provider": "local_llm", "model": "test", "auth_method": "local_llm",
        "credential": None, "base_url": "http://localhost", "session_id": ""})
    monkeypatch.setattr(llm, "_call_llm_with_meta", lambda *a, **k: {
        "content": "[]", "provider": "local_llm", "model": "test",
        "auth_method": "local_llm", "error": False})
    session = {"key": "AWPTCM-T00001",
               "step4": {"objective": "<ul><li>a</li><li>b</li><li>c</li></ul>"}}
    if which == "steps":
        llm.synthesize_steps(session)
        return seen["generate_steps.jinja"]
    llm.synthesize_objectives(session)
    return seen["generate_objectives.jinja"]


def test_steps_prompt_receives_only_whitelisted_context(monkeypatch):
    """THE INJECTION PATH. A new key here is a new channel for another layer's data."""
    ctx = _capture_context(monkeypatch, "steps")
    extra = set(ctx) - (ALLOWED_CONTEXT | {"objective"})
    assert not extra, (
        f"generate_steps.jinja is being passed context nobody approved: {sorted(extra)}. "
        f"If it is device data this is a layer violation (see pipeline-layer-contract); "
        f"if it is legitimate, add it to ALLOWED_CONTEXT deliberately.")


def test_objectives_prompt_receives_only_whitelisted_context(monkeypatch):
    ctx = _capture_context(monkeypatch, "objectives")
    extra = set(ctx) - ALLOWED_CONTEXT
    assert not extra, f"generate_objectives.jinja gained context: {sorted(extra)}"


def test_the_reverted_cli_reference_key_is_specifically_absent(monkeypatch):
    """Named because it is the one that actually happened."""
    assert "cli_reference" not in _capture_context(monkeypatch, "steps")


# ========================================================= B. what may appear INSIDE

# Unambiguous device vocabulary only. Bare `show` is EXCLUDED on purpose: it is ordinary
# English, and three lexical proxies for semantic properties had to be undone on
# 2026-08-05 (a "Verify" ban, a vague-word list, a has-a-digit check), each forbidding
# something legitimate. These four appear in no reasonable manual-case prose.
#
# Self-matching caveat (cf. _prose.py): if a future rule needs to forbid one of these, it
# must DESCRIBE rather than QUOTE it — the existing "no product names, no hardcoded port
# strings" line is the precedent for how.
DEVICE_VOCABULARY = {
    "CLI prompt": re.compile(r"awplus[#>]|\(config[^)]*\)#"),
    "port literal": re.compile(r"\bport\d+\.\d+\.\d+\b"),
    "negotiated-value idiom": re.compile(r"\ba-(?:1000|100|10|full|half)\b"),
}


@pytest.mark.parametrize("name", TEST_CASE_GENERATOR)
@pytest.mark.parametrize("label,rx", sorted(DEVICE_VOCABULARY.items()))
def test_test_case_generator_prompts_carry_no_device_vocabulary(name, label, rx):
    """A manual case is platform-agnostic. Naming device output is the script's job."""
    # Layer headers are Jinja comments — never rendered, so not shipped text, and they
    # legitimately discuss what must not appear.
    body = strip_jinja_comments((PROMPTS / name).read_text(encoding="utf-8"))
    hit = rx.search(body)
    assert not hit, (
        f"{name} contains {label} ({hit.group(0)!r}). `show` output and device field names "
        f"belong in the generated SCRIPT — see memory pipeline-layer-contract.")


def test_the_creator_prompts_are_deliberately_exempt():
    """Guard against a future session 'completing' safeguard B across all four prompts.

    Phase 4 injects real harvested CLI output into the Creator prompts, so the vocabulary
    above is present there BY DESIGN. This test asserts the exemption is real, so removing
    it fails loudly rather than looking like an oversight.
    """
    creator_text = "\n".join((PROMPTS / n).read_text(encoding="utf-8") for n in PYTEST_CREATOR)
    assert "cli_reference" in creator_text, \
        "the Creator prompts lost their CLI grounding — that is Phase 4, not a layer leak"


# =========================================================== C. the layer header

@pytest.mark.parametrize("name", ALL_PROMPTS)
def test_every_prompt_declares_its_layer_and_spec(name):
    """A header naming the governing document, in a comment the model never sees."""
    src = (PROMPTS / name).read_text(encoding="utf-8")
    header = re.search(r"\{#-?(.*?)-?#\}", src, re.S)
    assert header, f"{name} has no layer header — add a {{#- ... #}} block naming its spec"
    body = header.group(1)
    assert "LAYER:" in body and "SPEC:" in body, \
        f"{name}'s header must name both LAYER and SPEC"


@pytest.mark.parametrize("name", ALL_PROMPTS)
def test_the_spec_a_prompt_names_actually_exists(name):
    """A header pointing at a moved document is worse than no header."""
    src = (PROMPTS / name).read_text(encoding="utf-8")
    header = re.search(r"\{#-?(.*?)-?#\}", src, re.S).group(1)
    paths = re.findall(r"\bask-ck/[\w./-]+\.md\b", header)
    assert paths, f"{name}'s header names no spec path"
    for rel in paths:
        assert (REPO / rel).is_file(), f"{name} names a spec that does not exist: {rel}"


@pytest.mark.parametrize("name", ALL_PROMPTS)
def test_the_header_is_never_sent_to_the_model(name):
    """It is documentation for whoever edits the file, not prompt content.

    Rendered text costs tokens and would tell the model about layer boundaries it has no
    use for. `{#- ... #}` is stripped by Jinja before the prompt is built.
    """
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(str(PROMPTS)))
    rendered = env.get_template(name).render(
        case_key="AWPTCM-T00001", primary=None, objective="<ul><li>a</li></ul>",
        testlink_selections=[], zephyr_selections=[], atp_selections=[], gaps="",
        art_string="", steps=[], sequence=[], fragments=[], skeleton="", cli_reference="",
        case_title="", file_name="x.py", device_note="", bound_devices=[],
        framework_surface={}, py2_flagged=False)
    assert "LAYER:" not in rendered and "SPEC:" not in rendered, \
        f"{name}'s layer header is being RENDERED into the prompt — make it a {{#- ... #}}"
