"""Phase 2 — a non-compliant step generation must be visible where it happens.

`generate_steps.jinja` requires a non-empty `expectedResult` on every verification step.
Nothing checked whether the reply obeyed:

  * `parse_llm_to_structured`'s numbered-list fallback sets `expectedResult` to `""` for
    every step, unconditionally, and used to return them indistinguishably from a compliant
    JSON parse — so "the model ignored the requested format" and "the model complied" gave
    byte-identical output;
  * `validate_zephyr_payload` reads shape, the traceability note and the step count, and
    never looks at `expectedResult` at all;
  * the only real gate is `upload_refined.validate_for_push`, a whole pipeline stage later.

That ordering matters for Phase 2.4, which regenerates 53 bundles: without a signal at
generation, the way to learn a regeneration was blank is to push it. Cf. the
silent-degradation audit (2026-07-30) — an unparseable reply must never read as a
well-formed empty one.

These are advisory checks BY DESIGN. `validate_zephyr_payload` is the shared push gate and
a generation-time report must not move what the push refuses; a test below pins that.

Pure unit tests — no network, no LLM call.
"""
import llm


NOTE = "Note: Related ART Tests linked in Traceability."

JSON_REPLY = """[
  {"description": "Set the LLDP transmit interval to 5 seconds on the DUT test port.",
   "expectedResult": "The running configuration reports a transmit interval of 5 seconds."}
]"""

# The same answer, in the format the prompt explicitly forbids. Reasoning models do this.
NUMBERED_REPLY = """1. Set the LLDP transmit interval to 5 seconds on the DUT test port.
2. Capture LLDPDUs on the partner port for 30 seconds and count the frames received.
3. Set the transmit interval to 0, which is below the supported minimum."""


# ------------------------------------------------------- the parser says how it parsed

def test_a_json_reply_is_reported_as_json():
    out = llm.parse_llm_to_structured(JSON_REPLY, "AWPTCM-T00001")
    assert out["steps_source"] == "json"
    assert out["testScript"]["steps"][0]["expectedResult"].strip()


def test_the_numbered_list_fallback_announces_itself():
    """THE REGRESSION. Three steps, every expectedResult blank, and previously no signal."""
    out = llm.parse_llm_to_structured(NUMBERED_REPLY, "AWPTCM-T00001")
    steps = out["testScript"]["steps"]
    assert len(steps) == 3
    assert all(s["expectedResult"] == "" for s in steps), \
        "the fallback cannot carry an expectedResult — if it can, this test is obsolete"
    assert out["steps_source"] == "numbered_list", \
        "a fallback parse that blanks every expectedResult must be distinguishable"


def test_an_unparseable_reply_reports_no_source():
    out = llm.parse_llm_to_structured("The model refused to answer.", "AWPTCM-T00001")
    assert out["testScript"]["steps"] == []
    assert out["steps_source"] == "none"


# ------------------------------------------------------------- the compliance audit

def _steps(*expected_results):
    """A final step list: the server-injected note, then one step per given result."""
    return [{"description": NOTE, "expectedResult": ""}] + [
        {"description": f"step {i}", "expectedResult": e}
        for i, e in enumerate(expected_results, start=1)]


def test_the_traceability_note_is_not_counted_against_compliance():
    """Step 0 is server-injected and legitimately carries no expectedResult."""
    c = llm.steps_compliance(_steps("6 +/- 1 LLDPDUs are received"))
    assert c["verification_steps"] == 1
    assert c["blank_expected_results"] == 0
    assert c["compliant"] is True


def test_blank_expected_results_are_counted_and_located():
    c = llm.steps_compliance(_steps("a real outcome", "", "another outcome", ""))
    assert c["verification_steps"] == 4
    assert c["blank_expected_results"] == 2
    # 1-based among the VERIFICATION steps, so the note does not shift the numbering.
    assert c["blank_step_numbers"] == [2, 4]
    assert c["compliant"] is False


def test_whitespace_is_not_an_expected_result():
    c = llm.steps_compliance(_steps("   \n  "))
    assert c["blank_expected_results"] == 1 and c["compliant"] is False


def test_a_note_only_payload_is_not_compliant():
    """No verification step at all must not read as a clean sweep."""
    c = llm.steps_compliance([{"description": NOTE, "expectedResult": ""}])
    assert c["verification_steps"] == 0 and c["compliant"] is False


def test_empty_input_is_handled():
    assert llm.steps_compliance([])["compliant"] is False
    assert llm.steps_compliance(None)["verification_steps"] == 0


# ------------------------------------------- the push gate's verdict must not have moved

def test_blank_expected_results_still_do_not_fail_validate_zephyr_payload():
    """Advisory by design.

    `validate_zephyr_payload` is imported by `upload_refined` and used at export. Making
    the generation-time report change its verdict would silently re-scope the push gate,
    which is a decision of its own and not this one.
    """
    payload = {"AWPTCM-T00001": {
        "objective": "<ul><li>One</li><li>Two</li><li>Three</li></ul>",
        "testScript": {"type": "steps", "steps": _steps("", "")},
    }}
    v = llm.validate_zephyr_payload(payload)
    assert v["valid"] is True, v["issues"]
    # And the real refusal still lives at push time, where it always did.
    assert llm.steps_compliance(payload["AWPTCM-T00001"]["testScript"]["steps"])["compliant"] is False


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


def test_synthesize_steps_reports_a_compliant_generation(monkeypatch):
    out = _synthesize(monkeypatch, JSON_REPLY)
    q = out["steps_quality"]
    assert q["steps_source"] == "json"
    assert q["compliant"] is True and q["blank_expected_results"] == 0


def test_synthesize_steps_reports_the_blank_fallback(monkeypatch):
    """The case Phase 2.4 must be able to see: every step blank, and why."""
    out = _synthesize(monkeypatch, NUMBERED_REPLY)
    q = out["steps_quality"]
    assert q["steps_source"] == "numbered_list"
    assert q["compliant"] is False
    assert q["blank_expected_results"] == q["verification_steps"] == 3


def test_the_signal_is_persisted_with_provenance(monkeypatch):
    """The router writes provenance to step5 / full_session.llm_steps, so a batch
    regeneration can be audited per case without re-reading every payload."""
    out = _synthesize(monkeypatch, NUMBERED_REPLY)
    assert out["provenance"]["steps_quality"] == out["steps_quality"]
