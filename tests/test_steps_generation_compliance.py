"""What the steps stage reports about a generation — and what it deliberately does NOT.

A BLANK `expectedResult` IS THE DESIGN, not a defect. Terrence's ruling, recorded in memory
`expected-results-deliberately-absent`: a human reading the objective plus a
*non-prescriptive* step can reason out what should happen, and stating it does active harm —
the tester then performs the test in whatever way produces exactly that stated result,
instead of producing EVIDENCE OF FUNCTION. The objective already carries the expected
outcomes (`pt_generate_script.jinja` rule 1a calls its bullets "the AUTHORITATIVE expected
results the whole script exists to prove").

This file previously asserted the opposite, because an earlier version of `steps_report`
scored blanks as non-compliant. That came from D-12 (`f0a94af`) rewriting the prompt to
satisfy a push gate added hours earlier in the same stream (`949004f`), justified by that
gate refusing the corpus — circular, and never reviewed as a Test Case Generator design
question. `test_blank_expected_results_are_not_scored` below is the regression guard.

What IS still worth reporting, and neither depends on `expectedResult`:
  * parse integrity — an unparseable reply must not read as a clean one;
  * invented device mechanisms — an assertion on an observable the device does not expose.

Pure unit tests — no network, no LLM call.
"""
import llm


NOTE = "Note: Related ART Tests linked in Traceability."

JSON_REPLY = """[
  {"description": "Set the LLDP transmit interval to 5 seconds on the DUT test port.",
   "expectedResult": ""}
]"""

# The same answer, in the format the prompt explicitly forbids. Reasoning models do this.
NUMBERED_REPLY = """1. Set the LLDP transmit interval to 5 seconds on the DUT test port.
2. Capture LLDPDUs on the partner port for 30 seconds and count the frames received.
3. Set the transmit interval to 0, which is below the supported minimum."""


def _steps(*expected_results):
    """A final step list: the server-injected note, then one step per given result."""
    return [{"description": NOTE, "expectedResult": ""}] + [
        {"description": f"step {i}", "expectedResult": e}
        for i, e in enumerate(expected_results, start=1)]


# ------------------------------------------------------ the ruling, pinned

def test_blank_expected_results_are_not_scored():
    """THE REGRESSION GUARD. Blank is intended; nothing may grade it.

    If this fails, someone has re-introduced expectedResult scoring — read
    `.claude/memory/expected-results-deliberately-absent.md` before "fixing" it.
    """
    report = llm.steps_report(_steps("", "", ""))
    banned = {"blank_expected_results", "blank_step_numbers", "compliant"}
    assert not (banned & set(report)), \
        f"expectedResult is scored again: {sorted(banned & set(report))}"


def test_an_all_blank_generation_is_reported_the_same_as_a_filled_one():
    """The two must be indistinguishable to the report — that is the point."""
    assert llm.steps_report(_steps("", "")) == llm.steps_report(_steps("a value", "another"))


def test_the_traceability_note_is_not_counted_as_a_verification_step():
    assert llm.steps_report(_steps("", ""))["verification_steps"] == 2


def test_empty_input_is_handled():
    assert llm.steps_report([])["verification_steps"] == 0
    assert llm.steps_report(None)["verification_steps"] == 0


# ------------------------------------------------------- parse integrity

def test_a_json_reply_is_reported_as_json():
    out = llm.parse_llm_to_structured(JSON_REPLY, "AWPTCM-T00001")
    assert out["steps_source"] == "json"


def test_the_numbered_list_fallback_announces_itself():
    """A degraded parse must not read as a clean one — the silent-degradation pattern.

    Note what is NOT asserted here: that the blank expectedResults are a problem. The
    fallback is flagged because structure was LOST in parsing, not because the recovered
    steps lack a field they are not supposed to carry.
    """
    out = llm.parse_llm_to_structured(NUMBERED_REPLY, "AWPTCM-T00001")
    assert len(out["testScript"]["steps"]) == 3
    assert out["steps_source"] == "numbered_list"


def test_an_unparseable_reply_reports_no_source():
    out = llm.parse_llm_to_structured("The model refused to answer.", "AWPTCM-T00001")
    assert out["testScript"]["steps"] == []
    assert out["steps_source"] == "none"


# ------------------------------------------- the push gate's verdict must not have moved

def test_validate_zephyr_payload_still_accepts_blank_expected_results():
    """It always has, and on this design it must continue to.

    `validate_zephyr_payload` is imported by `upload_refined`. The separate blank-blocking
    rule in `upload_refined.validate_for_push` rests on the rejected premise and is named
    in the memory as needing review — but it is a production-facing push behaviour, so it
    is not changed here by a side effect of this file.
    """
    payload = {"AWPTCM-T00001": {
        "objective": "<ul><li>One</li><li>Two</li><li>Three</li></ul>",
        "testScript": {"type": "steps", "steps": _steps("", "")},
    }}
    assert llm.validate_zephyr_payload(payload)["valid"] is True


# --------------------------------------- the signal survives the call the router makes

def _session():
    return {"key": "AWPTCM-T00001",
            "step4": {"objective": "<ul><li>One</li><li>Two</li><li>Three</li></ul>"}}


def _synthesize(monkeypatch, reply):
    """Run synthesize_steps against a canned model reply. No network."""
    monkeypatch.setattr(llm, "_resolve_llm_runtime", lambda cfg: {
        "provider": "local_llm", "model": "test", "auth_method": "local_llm",
        "credential": None, "base_url": "http://localhost", "session_id": ""})
    monkeypatch.setattr(llm, "_call_llm_with_meta", lambda *a, **k: {
        "content": reply, "provider": "local_llm", "model": "test",
        "auth_method": "local_llm", "error": False})
    return llm.synthesize_steps(_session())


def test_synthesize_steps_reports_parse_source(monkeypatch):
    out = _synthesize(monkeypatch, JSON_REPLY)
    assert out["steps_quality"]["steps_source"] == "json"
    assert out["steps_quality"]["verification_steps"] == 1


def test_synthesize_steps_reports_the_degraded_parse(monkeypatch):
    out = _synthesize(monkeypatch, NUMBERED_REPLY)
    assert out["steps_quality"]["steps_source"] == "numbered_list"


def test_synthesize_steps_does_not_grade_blank_expected_results(monkeypatch):
    """End to end: a wholly blank generation carries no defect signal."""
    out = _synthesize(monkeypatch, JSON_REPLY)          # its one step has expectedResult ""
    q = out["steps_quality"]
    assert "compliant" not in q and "blank_expected_results" not in q


def test_the_signal_is_persisted_with_provenance(monkeypatch):
    """The router writes provenance to step5 / full_session.llm_steps, so a batch
    regeneration can be audited per case without re-reading every payload."""
    out = _synthesize(monkeypatch, NUMBERED_REPLY)
    assert out["provenance"]["steps_quality"] == out["steps_quality"]
