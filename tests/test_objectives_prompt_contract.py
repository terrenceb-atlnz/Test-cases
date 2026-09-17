"""`generate_objectives.jinja` must carry its rules where the MODEL can read them.

Measured 2026-09-16 across three consecutive raw syntheses (T33234/35/36): **21, 20 and 18
bullets** averaging 163 characters, against a SPEC that says "typically 1-10" and a worked
example whose bullets average ~90. Two causes, both pinned here:

  1. The MUST NOT list ("no procedure, no exact values, no device specifics") lived only in
     the template's `{# ... #}` header, which Jinja never renders and the model therefore
     never saw. Objectives came back reading "a fixed 1G copper port ... (10, 100, 1000
     Mbps)" -- exactly what the invisible comment forbade. A rule in a comment is not a rule.

  2. Nothing told the model where this case ENDS. Evidence is gathered broadly and each
     source case describes a whole matrix at once ("Fixed Copper-1Gig-Cross-10/Half-MDI to
     MDI" is speed AND duplex AND cabling AND polarity), so the model unioned it. The proof
     was symmetric: T33234 (MDI/MDI-X) was handed an ATP *Duplex* bundle and produced duplex
     bullets; T33236 (duplex) was handed the *Polarity* bundle and produced four polarity
     bullets. Each wrote its neighbour's objective.

Per `prompt-examples-are-the-spec` the example is what the model implements, so the example
is checked hardest -- and ONLY the example is scanned for banned phrasing, because the
prose legitimately names every antipattern it forbids (`_prose` exists for that trap).

Offline: no network, no LLM, no server.
"""
import pathlib
import re
import sys

import pytest
from jinja2 import Environment, FileSystemLoader

from _prose import flat, strip_jinja_comments

REPO = pathlib.Path(__file__).resolve().parents[1]
PROMPTS = REPO / "ask-ck" / "CK-main" / "CK_server" / "templates" / "prompts"
TPL = PROMPTS / "generate_objectives.jinja"
SPEC = REPO / "ask-ck" / "functions" / "generator" / "OBJECTIVE_DRAFTING_PROCESS.md"

TEXT = TPL.read_text(encoding="utf-8")
BODY = strip_jinja_comments(TEXT)          # what actually reaches the model
FLAT = flat(BODY)                          # newline-proof for phrase checks

SIBLINGS = [{"key": "AWPTCM-T33233", "title": "Port - Auto Negotiation"},
            {"key": "AWPTCM-T33236", "title": "(4) Port - Fixed Full or half Duplex"}]


def _render(**over):
    ctx = {"case_key": "AWPTCM-T33234", "case_title": "Port - Auto MDI/MDI-X",
           "siblings": SIBLINGS, "primary": {"w": "Auto/Full/MDI-MDIX negotiation"},
           "testlink_selections": [], "zephyr_selections": [], "atp_selections": []}
    ctx.update(over)
    env = Environment(loader=FileSystemLoader(str(PROMPTS)), keep_trailing_newline=True)
    return env.get_template(TPL.name).render(**ctx)


def _example_bullets(text):
    """The <li> items of the worked example — the part the model actually copies."""
    return [re.sub(r"\s+", " ", b).strip()
            for b in re.findall(r"<li>(.*?)</li>", text, re.S)]


# --- 1. the rules must RENDER, not sit in a comment ---------------------------------

@pytest.mark.parametrize("rule", [
    "procedural language",      # no "Verify that..."
    "do NOT enumerate exact values",
    "between 1 and 10 bullets",
])
def test_every_constraint_lives_in_the_rendered_body(rule):
    assert rule.lower() in FLAT.lower(), (
        f"{rule!r} is missing from the RENDERED prompt. If it only appears in the "
        f"{{# #}} header it is documentation, not a rule — the model never sees it.")


def test_the_header_comment_is_still_stripped_by_the_check():
    # Guards the guard: if strip_jinja_comments stopped working, every test above would
    # pass on comment text alone and the regression would be invisible again.
    assert "LAYER: Test Case Generator" in TEXT
    assert "LAYER: Test Case Generator" not in BODY


# --- 2. prompt and SPEC must agree on the bullet range ------------------------------

def test_bullet_range_matches_the_design_doc():
    spec = SPEC.read_text(encoding="utf-8")
    m = re.search(r"number of bullets varies per case \(typically (\d+)\s*[–-]\s*(\d+)\)", spec)
    assert m, "SPEC no longer states a 'typically N-M' bullet range — re-sync this test."
    lo, hi = m.group(1), m.group(2)
    assert re.search(rf"between\s+{lo}\s+and\s+{hi}\s+bullets", FLAT), (
        f"SPEC says typically {lo}-{hi} bullets; the prompt must state the same range. "
        f"This drifted silently once — the prompt said only 'count is not fixed'.")


# --- 3. the worked example must obey the rules it teaches ---------------------------

def test_example_is_within_the_bullet_range():
    n = len(_example_bullets(_render()))
    assert 1 <= n <= 10, f"example shows {n} bullets — it teaches breaking the stated range"


def test_example_bullets_are_declarative_not_procedural():
    bad = re.compile(r"^\s*(verify|check|configure|set|ensure|confirm|apply|run)\b", re.I)
    for b in _example_bullets(_render()):
        assert not bad.match(b), f"example bullet is procedural, not an artefact: {b!r}"


def test_example_bullets_carry_no_device_specifics_or_value_lists():
    # Scanned ONLY over the example — the prose above it necessarily quotes these to ban them.
    banned = re.compile(r"\b(1G\b|1-Gigabit|10/100|1000 Mbps|port\d+\.\d+\.\d+|x9\d0|IE\d{3})", re.I)
    for b in _example_bullets(_render()):
        assert not banned.search(b), f"example bullet names a device specific/value list: {b!r}"


def test_example_bullets_respect_the_length_guidance():
    for b in _example_bullets(_render()):
        assert len(b) <= 140, f"example bullet is {len(b)} chars, over the stated guidance: {b!r}"


# --- 4. the scope boundary must actually reach the model ----------------------------

def test_siblings_are_named_and_marked_out_of_scope():
    out = _render()
    for s in SIBLINGS:
        assert s["key"] in out and s["title"] in out, f"sibling {s['key']} not rendered"
    assert "own the adjacent subjects" in flat(out).lower()


def test_subject_of_this_case_is_stated():
    out = flat(_render())
    assert "Port - Auto MDI/MDI-X" in out, "the case's own title must anchor the boundary"
    assert "only for that subject" in out.lower()


def test_no_siblings_degrades_to_guidance_not_breakage():
    out = _render(siblings=[])
    assert "No sibling cases were found" in out
    assert "AWPTCM-T33233" not in out          # no stale boundary block
    assert "<ul>" in out                        # the example survives


def test_dependency_on_a_sibling_is_allowed_as_a_condition():
    # Without this the boundary would forbid legitimate preconditions ("a duplex setting
    # needs a link"), pushing the model to drop real artefacts rather than reframe them.
    assert "condition the" in FLAT.lower()


# --- 5. the sibling lookup itself ---------------------------------------------------

@pytest.fixture
def dbmod():
    for p in (REPO / "ask-ck" / "CK-main", REPO / "ask-ck" / "CK-main" / "CK_server"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    import db
    return db


def test_folder_siblings_exclude_the_case_itself(dbmod):
    key = "AWPTCM-T33234"
    if not dbmod.get_case(key):
        pytest.skip("corpus case absent in this checkout")
    sibs = dbmod.get_folder_siblings(key)
    assert sibs, "expected folder siblings for a curated target case"
    assert all(s["key"] != key for s in sibs), "a case must never be its own sibling"
    assert all(s.get("title") for s in sibs), "a titleless sibling teaches nothing"


def test_folder_siblings_degrade_quietly_for_an_unknown_key(dbmod):
    # A missing boundary must cost precision, never raise into the user's generation.
    assert dbmod.get_folder_siblings("AWPTCM-TNOPE999") == []


def test_folder_siblings_are_bounded(dbmod):
    key = "AWPTCM-T33234"
    if not dbmod.get_case(key):
        pytest.skip("corpus case absent in this checkout")
    assert len(dbmod.get_folder_siblings(key, limit=2)) <= 2
