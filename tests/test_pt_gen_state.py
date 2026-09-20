"""Slice A + reset_generate (PLAN-generate-state-and-sequence-sanity, 2026-09-21).

WHY. step6 holds TWO copies of the script — the per-unit `chunks` and the assembled
`files.test.code`. Only the splice paths write both; `save_script`, `fix_script` and
`generate_script` write the assembled code alone. Afterwards the chunks are STALE, and every
re-splice (Assemble, Fix units, Apply held) silently discarded the repair — one click from it on
AWPTCM-T33234 (2026-09-17/18) with every pill green.

Pinned here:
  * `_gen_state`: a script with no matching assembly hash is DIVERGED; no script is not;
  * `_require_units_current` raises 409 while diverged, and every splice / unit-generation path
    calls it first;
  * `_rechunk_from_script` makes chunks AND frame agree with the script, drops units the script
    no longer has, and an assembly from that snapshot reproduces the script BYTE FOR BYTE;
  * the generation context trusts the snapshot only while the sequence shape matches;
  * `reset_generate` keeps steps 1-4 and {files, lint, naming}, drops everything else;
  * the review records the code hash it was made against (slice B); fix_script re-chunks itself.
Offline: real module, monkeypatched persistence. No network, no LLM, no server.
"""
import asyncio
import re
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

_REPO = Path(__file__).resolve().parents[1]
_SERVER = _REPO / "ask-ck" / "CK-main" / "CK_server"
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(_SERVER))

from routers import pytest_create as pc  # noqa: E402

_SRC = (_SERVER / "routers" / "pytest_create.py").read_text(encoding="utf-8")
_CODE = re.sub(r'#[^\n]*', '',
               re.sub(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'', '', _SRC))

KEY = "AWPTCM-TGEN1"
SEQ = [{"n": 1, "action": "a", "verify": "v1", "kind": "verify"},
       {"n": 2, "action": "b", "verify": "v2", "kind": "verify"}]

# A whole script as a Fix or a hand edit would leave it: a module-level helper the server's
# own render never emits, a TestSet with the configure/tear_down pair, two cases, a runner.
SCRIPT = '''#!/usr/bin/python3
import sys
from framework import ATTestSet, ATTestCase

HELPER = 1


def force_partner_polarity(testCase, peer, port, value):
    return HELPER


class TestSet(ATTestSet.TestSet):

    def init(self):
        pass

    def configure(self):
        self.x = 1

    def tear_down(self):
        self.x = 0


class TestCase_1(ATTestCase.TestCase):
    testCaseDesc = "a"

    def main(self):
        self.passed("ok one")


class TestCase_2(ATTestCase.TestCase):
    testCaseDesc = "b"

    def main(self):
        self.passed("ok two")


if __name__ == "__main__":
    ts = TestSet()
    ts.add_testCase(TestCase_1)
    ts.add_testCase(TestCase_2)
'''


def _step6(code=SCRIPT, **over):
    s6 = {"files": {"test": {"name": "test-9000.1.py", "code": code}},
          "lint": {"ok": True, "errors": [], "warnings": []},
          "naming": {"group": "Port", "name": "test-9000.1"}}
    s6.update(over)
    return s6


def _sess(step6):
    s = pc.PtSession(key=KEY)
    s.step2 = {"sequence": SEQ, "confirmed": True}
    s.step5 = {"fragments": [], "selected": [], "confirmed": True}
    s.step6 = step6
    return s


@pytest.fixture
def persisted(monkeypatch):
    """Route _pt_get/_pt_persist at one in-memory session; return it."""
    box = {}
    monkeypatch.setattr(pc, "_pt_get", lambda key: box["sess"])
    monkeypatch.setattr(pc, "_pt_persist", lambda sess: box.__setitem__("persisted", sess))
    def use(sess):
        box["sess"] = sess
        return box
    return use


# --- _gen_state ---------------------------------------------------------------------------

def test_no_script_is_not_diverged():
    st = pc._gen_state({})
    assert st["diverged"] is False and st["script_hash"] == "" and st["reason"] == ""


def test_a_whole_script_with_no_recorded_assembly_is_diverged():
    st = pc._gen_state(_step6())
    assert st["diverged"] is True
    assert "Re-chunk" in st["reason"]
    assert st["units"] == 0 and st["frame_snapshot"] is False


def test_a_script_whose_hash_matches_the_last_assembly_is_in_sync():
    s6 = _step6(assembled_hash=pc._code_hash(SCRIPT))
    assert pc._gen_state(s6)["diverged"] is False


def test_the_gate_raises_409_only_while_diverged():
    with pytest.raises(HTTPException) as ei:
        pc._require_units_current(_step6())
    assert ei.value.status_code == 409
    pc._require_units_current(_step6(assembled_hash=pc._code_hash(SCRIPT)))   # no raise
    pc._require_units_current({})                                              # nothing to protect


# --- re-chunk -----------------------------------------------------------------------------

def test_rechunk_makes_units_and_frame_agree_and_drops_vanished_units():
    s6 = _step6(chunks={"tc1": {"status": "ok", "code": "class TestCase_1: pass"},
                        "tc9": {"status": "ok", "code": "class TestCase_9: pass"}})
    changed, dropped = pc._rechunk_from_script(s6, SEQ)
    assert set(changed) == {"setup", "tc1", "tc2"}
    assert dropped == ["tc9"] and "tc9" not in s6["chunks"]
    assert s6["chunks"]["tc1"]["code"].startswith("class TestCase_1(")
    assert 'self.passed("ok one")' in s6["chunks"]["tc1"]["code"]
    assert s6["chunks"]["setup"]["code"].lstrip().startswith("def configure")
    assert s6["chunks"]["tc1"]["source"] == "script"
    assert s6["frame"]["code"] == SCRIPT
    assert s6["frame"]["units"] == ["setup", "tc1", "tc2"]
    assert s6["frame"]["sequence_shape"] == pc._sequence_shape(SEQ)
    assert s6["assembled_hash"] == pc._code_hash(SCRIPT)
    assert pc._gen_state(s6)["diverged"] is False
    assert pc._gen_state(s6)["frame_snapshot"] is True


def test_assembling_from_the_snapshot_reproduces_the_script_byte_for_byte():
    s6 = _step6()
    pc._rechunk_from_script(s6, SEQ)
    ctx = {"skeleton": s6["frame"]["code"], "units": pc._skeleton_units(s6["frame"]["code"])}
    code, missing = pc._assemble_units(ctx, s6["chunks"])
    assert missing == []
    assert code == SCRIPT, "the module-level helper and every unit must survive a re-splice"


def test_a_regenerated_unit_splices_into_the_snapshot_frame_not_a_fresh_render():
    s6 = _step6()
    pc._rechunk_from_script(s6, SEQ)
    new_tc2 = s6["chunks"]["tc2"]["code"].replace('"ok two"', '"ok TWO"')
    s6["chunks"]["tc2"] = {**s6["chunks"]["tc2"], "code": new_tc2}
    ctx = {"skeleton": s6["frame"]["code"], "units": pc._skeleton_units(s6["frame"]["code"])}
    code, _ = pc._assemble_units(ctx, s6["chunks"])
    assert "def force_partner_polarity" in code, "the frame's helper survives"
    assert '"ok TWO"' in code and '"ok one"' in code


def test_a_hand_edit_after_rechunk_diverges_again():
    s6 = _step6()
    pc._rechunk_from_script(s6, SEQ)
    s6["files"]["test"]["code"] = SCRIPT.replace('"ok one"', '"ok ONE"')
    assert pc._gen_state(s6)["diverged"] is True


def test_rechunk_refuses_a_script_that_does_not_split():
    with pytest.raises(HTTPException) as ei:
        pc._rechunk_from_script(_step6(code="def (broken"), SEQ)
    assert ei.value.status_code == 409 and "does not parse" in ei.value.detail
    with pytest.raises(HTTPException):
        pc._rechunk_from_script(_step6(code=""), SEQ)


def test_try_rechunk_reports_instead_of_raising():
    ok = _step6()
    assert pc._try_rechunk(ok, SEQ) is True and ok.get("frame")
    bad = _step6(code="def (broken")
    assert pc._try_rechunk(bad, SEQ) is False and "frame" not in bad


# --- wiring, read off the code -----------------------------------------------------------

def _body(start):
    i = _CODE.index(start)
    j = re.compile(r"\n(async def |def |@router\.)").search(_CODE, i + 10).start()
    return _CODE[i:j]


@pytest.mark.parametrize("fn", ["async def assemble_script(", "async def assemble_and_settle(",
                                "async def generate_units(", "async def generate_step(",
                                "async def fix_units(", "async def apply_held("])
def test_every_splice_and_unit_generation_path_is_gated(fn):
    assert "_require_units_current(" in _body(fn), f"{fn} must refuse while diverged"


def test_the_generation_context_trusts_the_snapshot_only_while_the_shape_matches():
    body = _body("def _pt_generation_context(")
    assert 'frame.get("sequence_shape") == _sequence_shape(sequence)' in body
    assert 'skeleton = frame["code"]' in body


def test_assembly_records_the_hash_and_skips_restamping_an_unchanged_snapshot():
    body = _body("def _assemble_and_store(")
    assert 'step6_f["assembled_hash"] = _code_hash(stamped)' in body
    assert 'code == frame["code"]' in body and "stamped = code" in body


def test_the_review_records_the_code_hash_it_was_made_against():
    assert '"code_hash": _code_hash(step6["files"]["test"]["code"])' in _body("async def review_script(")


def test_a_stale_review_is_reported_by_gen_state():
    s6 = _step6(assembled_hash=pc._code_hash(SCRIPT),
                review={"at": "x", "findings": [], "code_hash": pc._code_hash(SCRIPT)})
    assert pc._gen_state(s6)["review_stale"] is False
    s6["review"]["code_hash"] = "somethingelse"
    assert pc._gen_state(s6)["review_stale"] is True
    s6["review"].pop("code_hash")                     # a legacy review: cannot be proved current
    assert pc._gen_state(s6)["review_stale"] is True
    assert pc._gen_state(_step6())["review_stale"] is False   # no review at all


def test_fix_script_rechunks_itself():
    assert "_try_rechunk(step6_l" in _body("async def fix_script(")


# --- the endpoints -----------------------------------------------------------------------

def test_rechunk_endpoint_persists_and_returns_the_new_state(persisted):
    box = persisted(_sess(_step6(chunks={"tc9": {"status": "ok", "code": "x"}})))
    out = asyncio.run(pc.rechunk(KEY))
    assert out["dropped"] == ["tc9"] and set(out["changed"]) == {"setup", "tc1", "tc2"}
    assert out["gen_state"]["diverged"] is False
    assert box["persisted"].step6["frame"]["code"] == SCRIPT


def test_reset_generate_keeps_steps_one_to_four_and_the_script(persisted):
    s6 = _step6(chunks={"setup": {"status": "ok", "code": "a"}, "tc1": {"status": "ok", "code": "b"}},
                review={"at": "x", "findings": [{"what": "w"}]}, assembled_at="t", assembled_hash="h",
                assembly={"units": 2}, settle={}, fix_units={}, iterations=3, lint_history=[1],
                frame={"code": "old"}, confirmed=True)
    box = persisted(_sess(s6))
    out = asyncio.run(pc.reset_generate(KEY))
    kept = box["persisted"].step6
    assert out["dropped_units"] == ["setup", "tc1"]
    assert set(kept) == {"files", "lint", "naming", "confirmed", "reset_at", "reset_dropped"}
    assert kept["files"]["test"]["code"] == SCRIPT and kept["confirmed"] is False
    assert box["persisted"].step2["sequence"] == SEQ, "steps 1-4 untouched"
    assert box["persisted"].step5["confirmed"] is True
    assert out["gen_state"]["units"] == 0


def test_reset_generate_without_a_script_is_409(persisted):
    persisted(_sess({}))
    with pytest.raises(HTTPException) as ei:
        asyncio.run(pc.reset_generate(KEY))
    assert ei.value.status_code == 409


def test_get_session_exposes_the_state(persisted):
    persisted(_sess(_step6()))
    out = asyncio.run(pc.get_session(KEY))
    assert out["gen_state"]["diverged"] is True
