"""Unit tests for llm.validate_zephyr_payload — the gate that decides whether an
exported bundle is repeatable/complete. These lock in every branch so a future edit
to the validator can't silently loosen the Complete-case contract.

Run: PYTHONNOUSERSITE=1 .venv/bin/pytest -q tests/test_validate_payload.py
"""
import llm


def _good_payload():
    """A minimal payload that SHOULD pass every rule."""
    note = ("Note: Related ART Tests linked in Traceability. "
            "See traceability.md for the full mapping.")
    return {
        "AWPTCM-T12345": {
            "objective": "<ul><li>Artefact one</li><li>Artefact two</li><li>Artefact three</li></ul>",
            "testScript": {
                "type": "steps",
                "steps": [
                    {"description": note, "expectedResult": ""},
                    {"description": "Verify the port comes up", "expectedResult": "link up"},
                ],
            },
        }
    }


def test_good_payload_is_valid():
    v = llm.validate_zephyr_payload(_good_payload())
    assert v["valid"] is True, v["issues"]
    assert v["issues"] == []


def test_top_level_must_be_single_key():
    assert llm.validate_zephyr_payload({})["valid"] is False
    two = {"AWPTCM-T1": {}, "AWPTCM-T2": {}}
    assert llm.validate_zephyr_payload(two)["valid"] is False
    assert llm.validate_zephyr_payload([])["valid"] is False  # not a dict


def test_non_awptcm_key_is_a_warning_not_an_issue():
    p = _good_payload()
    content = p.pop("AWPTCM-T12345")
    p["WEIRD-KEY"] = content
    v = llm.validate_zephyr_payload(p)
    # A bad key name is advisory (warning), not a hard block, as long as the shape is good.
    assert any("does not follow" in w for w in v["warnings"])
    assert v["valid"] is True


def test_objective_must_be_ul_with_three_items():
    p = _good_payload()
    p["AWPTCM-T12345"]["objective"] = "<ul><li>only one</li></ul>"
    v = llm.validate_zephyr_payload(p)
    assert v["valid"] is False
    assert any("at least 3 <li>" in i for i in v["issues"])


def test_objective_must_start_with_ul():
    p = _good_payload()
    p["AWPTCM-T12345"]["objective"] = "<li>a</li><li>b</li><li>c</li>"
    v = llm.validate_zephyr_payload(p)
    assert v["valid"] is False
    assert any("must start with <ul>" in i for i in v["issues"])


def test_first_step_must_be_traceability_note():
    p = _good_payload()
    p["AWPTCM-T12345"]["testScript"]["steps"][0]["description"] = "Configure the switch"
    v = llm.validate_zephyr_payload(p)
    assert v["valid"] is False
    assert any("traceability note" in i for i in v["issues"])


def test_needs_at_least_one_verification_step_after_note():
    p = _good_payload()
    # Drop the verification step, leaving only the note.
    p["AWPTCM-T12345"]["testScript"]["steps"] = p["AWPTCM-T12345"]["testScript"]["steps"][:1]
    v = llm.validate_zephyr_payload(p)
    assert v["valid"] is False
    # Fewer than 2 steps trips the list-length rule.
    assert any("at least one verification step" in i for i in v["issues"])


def test_step_missing_description_is_flagged():
    p = _good_payload()
    p["AWPTCM-T12345"]["testScript"]["steps"].append({"expectedResult": "no description key"})
    v = llm.validate_zephyr_payload(p)
    assert v["valid"] is False
    assert any("missing 'description'" in i for i in v["issues"])
