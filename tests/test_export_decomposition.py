"""Unit tests for the pieces export() was split into (PLAN-backend-module-split.md c11).

export() was 351 lines doing gating, an LLM round-trip, payload assembly, validation, Jinja
templating and staged atomic writes. All of it was reachable only through the endpoint, so
the parts that are pure logic had no direct test — including two that encode real bugs
previously fixed:

  * `_build_test_script` decides whether the server-built traceability note OVERWRITES
    steps[0] or is PREPENDED. It used to overwrite unconditionally, destroying a genuine
    first verification step on any manually-edited or backfilled testScript.
  * `_write_bundle` commits the files in the order it is given, and the LAST one is
    zephyr_payload.json — the marker that makes a case Complete. Its behaviour under a
    mid-write failure is covered in test_export_authority_batch_a.py; here we pin the
    success path and the staging mechanics.

Pure: no TestClient, no LLM, no network, no writes outside tmp_path.
"""
import json

import pytest

from models import WizardSession

NOTE_PREFIX = "Note: Related ART Tests"


@pytest.fixture(scope="module")
def wiz():
    import routers.wizard as wizard
    return wizard


# --- _build_test_script ------------------------------------------------------

def test_the_note_is_prepended_when_step_one_is_a_real_step(wiz):
    """The regression this function exists for: never destroy a genuine first step."""
    step5 = {"testScript": {"type": "steps", "steps": [
        {"description": "Set the port to Auto", "expectedResult": "link up"},
        {"description": "second", "expectedResult": ""},
    ]}}
    out = wiz._build_test_script({}, step5, {"key": "AWPTCM-T99991"})
    assert len(out["steps"]) == 3, "a real first step was consumed by the note"
    assert out["steps"][1]["description"] == "Set the port to Auto"
    assert out["steps"][1]["expectedResult"] == "link up", "its expectedResult must survive"
    assert out["steps"][2]["description"] == "second"


def test_an_existing_note_is_regenerated_in_place(wiz):
    """Re-exporting must not stack a second note on top of the first."""
    step5 = {"testScript": {"type": "steps", "steps": [
        {"description": f"{NOTE_PREFIX} linked in Traceability\n\nplus older detail",
         "expectedResult": "keep me"},
        {"description": "real", "expectedResult": ""},
    ]}}
    out = wiz._build_test_script({}, step5, {"key": "AWPTCM-T99991"})
    assert len(out["steps"]) == 2, "the note was prepended instead of regenerated"
    assert out["steps"][0]["expectedResult"] == "keep me", (
        "regenerating the note keeps the existing expectedResult")
    assert out["steps"][1]["description"] == "real"


def test_a_step_that_merely_mentions_traceability_is_not_mistaken_for_the_note(wiz):
    """The note test is ANCHORED (startswith) on purpose. An unanchored substring match on
    "Traceability" / "Note:" matches legitimate verification steps — "Verify Traceability of
    the ART logs..." — and this function would then DELETE them."""
    for desc in ("Verify Traceability of the ART logs against the suite",
                 f"stale preamble\n\n{NOTE_PREFIX} linked in Traceability"):
        step5 = {"testScript": {"steps": [{"description": desc, "expectedResult": "e"}]}}
        out = wiz._build_test_script({}, step5, {"key": "AWPTCM-T99991"})
        assert len(out["steps"]) == 2, f"a real step was overwritten: {desc!r}"
        assert out["steps"][1]["description"] == desc


def test_a_blank_first_step_is_replaced_not_pushed_down(wiz):
    step5 = {"testScript": {"type": "steps", "steps": [
        {"description": "   ", "expectedResult": ""},
        {"description": "real", "expectedResult": ""},
    ]}}
    out = wiz._build_test_script({}, step5, {"key": "AWPTCM-T99991"})
    assert len(out["steps"]) == 2
    assert out["steps"][1]["description"] == "real"


def test_an_empty_script_still_gets_the_note(wiz):
    out = wiz._build_test_script({}, {}, {"key": "AWPTCM-T99991"})
    assert len(out["steps"]) == 1 and out["steps"][0]["description"]
    assert out["type"] == "steps"


def test_step5_wins_over_the_legacy_step4_location(wiz):
    step4 = {"testScript": {"steps": [{"description": "LEGACY"}]}}
    step5 = {"testScript": {"steps": [{"description": "CURRENT"}]}}
    out = wiz._build_test_script(step4, step5, {"key": "AWPTCM-T99991"})
    assert any(s["description"] == "CURRENT" for s in out["steps"])
    assert not any(s.get("description") == "LEGACY" for s in out["steps"])


def test_the_legacy_step4_script_is_used_when_step5_is_empty(wiz):
    step4 = {"testScript": {"steps": [{"description": "LEGACY"}]}}
    out = wiz._build_test_script(step4, {}, {"key": "AWPTCM-T99991"})
    assert any(s["description"] == "LEGACY" for s in out["steps"])


def test_a_non_dict_first_step_does_not_raise(wiz):
    """Real on-disk data is uniform, but this reads unvalidated session JSON."""
    step5 = {"testScript": {"steps": ["not a dict", {"description": "real"}]}}
    out = wiz._build_test_script({}, step5, {"key": "AWPTCM-T99991"})
    assert out["steps"][0]["description"], "the note must still be produced"


# --- _build_payload ----------------------------------------------------------

def test_payload_has_the_exact_refined_cases_shape(wiz):
    """upload_refined.py and all 43 on-disk bundles depend on this shape."""
    step4 = {"objective": "<ul><li>a</li></ul>"}
    step5 = {"testScript": {"steps": [{"description": "d", "expectedResult": "e"}]}}
    out = wiz._build_payload("AWPTCM-T99991", step4, step5, {"key": "AWPTCM-T99991"})
    assert list(out) == ["AWPTCM-T99991"]
    assert set(out["AWPTCM-T99991"]) == {"objective", "testScript"}
    assert set(out["AWPTCM-T99991"]["testScript"]) == {"type", "steps"}


def test_payload_sanitizes_the_objective(wiz):
    """Defence in depth on the artefact itself — it is rendered in the browser and pushed
    to Zephyr."""
    out = wiz._build_payload("AWPTCM-T99991",
                             {"objective": "<ul><li>ok</li></ul><script>alert(1)</script>"},
                             {}, {"key": "AWPTCM-T99991"})
    assert "<script>" not in out["AWPTCM-T99991"]["objective"]


def test_payload_falls_back_to_a_placeholder_objective(wiz):
    """Documented, and it is why step4 must stay a plain dict: SURVEY-step4-step5.md
    measured that typing it makes the isinstance guard here take its else branch and write
    this placeholder into the PUBLISHED bundle."""
    out = wiz._build_payload("AWPTCM-T99991", {}, {}, {"key": "AWPTCM-T99991"})
    assert "not yet synthesized" in out["AWPTCM-T99991"]["objective"]

    typed = wiz._build_payload("AWPTCM-T99991", "not a dict", {}, {"key": "AWPTCM-T99991"})
    assert "not yet synthesized" in typed["AWPTCM-T99991"]["objective"], (
        "the non-dict branch is the exact hazard that got commit 6 dropped")


def test_payload_derives_art_string_for_the_traceability_template(wiz):
    """A deliberate side effect: _render_traceability reads sess_dict['art_string'], so
    _build_payload must run first. Capped at six for cleanliness."""
    sess = {"key": "AWPTCM-T99991", "step3": {"selections": [
        {"id_or_key": f"ART-{i}"} for i in range(9)]}}
    wiz._build_payload("AWPTCM-T99991", {}, {}, sess)
    assert sess["art_string"] == " + ".join(f"ART-{i}" for i in range(6))


def test_payload_never_overwrites_an_existing_art_string(wiz):
    sess = {"key": "AWPTCM-T99991", "art_string": "hand written",
            "step3": {"selections": [{"id_or_key": "ART-1"}]}}
    wiz._build_payload("AWPTCM-T99991", {}, {}, sess)
    assert sess["art_string"] == "hand written"


# --- _render_traceability ----------------------------------------------------

def test_traceability_renders_the_real_template_with_the_selections(wiz):
    sess = {
        "key": "AWPTCM-T99991",
        "primary": {"m": "AWP-1", "w": "why"},
        "step1": {"selections": [{"id_or_key": "AWP-1", "title": "TL one"}]},
        "step2": {"selections": [{"key": "AWPTCM-T2", "title": "Z two", "folder": "/Port"}]},
        "step3": {"selections": [{"id_or_key": "ART-3", "title": "ATP three"}]},
        "gaps": "a coverage gap",
        "art_string": "ART-3",
    }
    md = wiz._render_traceability("AWPTCM-T99991", sess)
    for expected in ("AWPTCM-T99991", "AWP-1", "AWPTCM-T2", "ART-3", "a coverage gap"):
        assert expected in md, f"{expected!r} missing from the rendered traceability.md"


def test_traceability_normalizes_zephyr_rows_that_use_id_or_key(wiz):
    """UI rows arrive with `key` or `id_or_key` depending on which table produced them."""
    sess = {"step2": {"selections": [{"id_or_key": "AWPTCM-T7", "title": "seven"}]}}
    assert "AWPTCM-T7" in wiz._render_traceability("AWPTCM-T99991", sess)


def test_traceability_falls_back_to_plain_text_rather_than_failing_the_export(wiz,
                                                                             monkeypatch):
    """A template error must degrade the artefact, not 500 the export."""
    class _Boom:
        def get_template(self, name):
            raise RuntimeError("template is broken")

    monkeypatch.setattr(wiz, "OUTPUTS_ENV", _Boom())
    md = wiz._render_traceability("AWPTCM-T99991", {"gaps": "g", "art_string": "a"})
    assert "AWPTCM-T99991" in md and "## Gaps" in md and "g" in md


def test_traceability_tolerates_a_session_with_nothing_in_it(wiz):
    assert wiz._render_traceability("AWPTCM-T99991", {})


# --- _write_bundle -----------------------------------------------------------

def test_write_bundle_commits_every_file_and_leaves_no_temp(wiz, tmp_path):
    target = tmp_path / "Group (1)" / "AWPTCM-T99991"
    written = wiz._write_bundle(target, [
        ("traceability.md", "# md"),
        ("AWPTCM-T99991-session.json", "{}"),
        ("zephyr_payload.json", json.dumps({"AWPTCM-T99991": {}})),
    ])
    assert written == ["traceability.md", "AWPTCM-T99991-session.json", "zephyr_payload.json"]
    assert (target / "zephyr_payload.json").read_text() == '{"AWPTCM-T99991": {}}'
    assert (target / "traceability.md").read_text() == "# md"
    assert not list(target.glob(".*.tmp")), "staged temp files were left behind"


def test_write_bundle_creates_the_group_directory(wiz, tmp_path):
    target = tmp_path / "deep" / "Group (1)" / "AWPTCM-T99991"
    wiz._write_bundle(target, [("zephyr_payload.json", "{}")])
    assert (target / "zephyr_payload.json").exists()


def test_write_bundle_overwrites_a_previous_export(wiz, tmp_path):
    """Re-export must replace, not append or fail — os.replace onto an existing file."""
    target = tmp_path / "AWPTCM-T99991"
    wiz._write_bundle(target, [("zephyr_payload.json", "OLD")])
    wiz._write_bundle(target, [("zephyr_payload.json", "NEW")])
    assert (target / "zephyr_payload.json").read_text() == "NEW"


# --- the handler is actually decomposed --------------------------------------

def test_export_is_no_longer_a_monolith(wiz):
    """The point of the commit. It was 351 lines; keep it from growing back.

    A generous ceiling — this is a regression guard, not a style rule. The steps it
    delegates to are each well under a screen.
    """
    import ast
    import inspect

    src = inspect.getsource(wiz)
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.AsyncFunctionDef) and n.name == "export")
    length = fn.end_lineno - fn.lineno + 1
    assert length < 140, f"export() is back up to {length} lines; keep the steps extracted"
