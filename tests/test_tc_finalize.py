"""Validation's Finalize (PLAN-test-validation §6), built as far as V0 allows. What these pin:
the addendum is the agreed sentence on the line after step 1's text, added once; nothing is
written while V0 (the Zephyr new-version request) is open; with the Zephyr calls supplied the
order is step 1 → version → marker, and a failed write leaves NO marker (the case stays on the
lists); a marked case leaves BOTH lists, and deleting the marker brings it back.
"""
import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main" / "CK_server"))

import case_registry  # noqa: E402
import tc_finalize  # noqa: E402

CASE = {"testScript": {"type": "STEP_BY_STEP", "steps": [
    {"description": "Attachments: see the template.", "expectedResult": ""}, {"description": "two"}]}}


@pytest.fixture
def gen(tmp_path):
    meta = tmp_path / ".meta" / "9001_Port" / "test-9001.33234"
    meta.mkdir(parents=True)
    (meta / "provenance.json").write_text(json.dumps({"case_key": "AWPTCM-T33234"}))
    return tmp_path


def test_the_addendum_is_the_agreed_sentence_on_the_next_line_and_added_once():
    t = tc_finalize.addendum("test-9001.33234", "http://ck/?panel=composer&script=9001_Port/test-9001.33234.py")
    assert t == ("This test is now automatable. use script test-9001.33234 in the ask-ck tool. "
                 "http://ck/?panel=composer&script=9001_Port/test-9001.33234.py")
    once = tc_finalize.step1_with_addendum(CASE["testScript"], t)
    assert once["steps"][0]["description"] == "Attachments: see the template.<br />" + t
    assert tc_finalize.step1_with_addendum(once, t) == once
    assert once["steps"][1] == {"description": "two"} and CASE["testScript"]["steps"][0]["description"].endswith("template.")


def test_nothing_is_written_while_v0_is_open(gen):
    writes = []
    with pytest.raises(tc_finalize.FinalizeBlocked, match="V0"):
        tc_finalize.finalize("AWPTCM-T33234", "9001_Port/test-9001.33234.py", "r", "s", gen, "L",
                             get_case=lambda k: CASE, put_case=lambda k, ts: writes.append(k), new_version=None,
                             audit=lambda e: True)
    assert writes == [] and "finalized_at" not in json.loads((gen / ".meta/9001_Port/test-9001.33234/provenance.json").read_text())


def test_zephyr_first_then_the_marker_and_a_failed_write_leaves_no_marker(gen):
    order = []
    out = tc_finalize.finalize("AWPTCM-T33234", "9001_Port/test-9001.33234.py", "r1", "seat", gen, "L",
                               get_case=lambda k: CASE, put_case=lambda k, ts: order.append(("step1", k)),
                               new_version=lambda k: order.append(("version", k)), audit=lambda e: order.append(e["event"]) or True)
    assert [o if isinstance(o, str) else o[0] for o in order] == ["finalize-step1", "step1", "finalize-version", "version", "finalized"]
    assert out["finalized_at"]
    gen2 = gen.parent / "g2"
    (gen2 / ".meta" / "9001_Port" / "test-9001.33234").mkdir(parents=True)
    (gen2 / ".meta" / "9001_Port" / "test-9001.33234" / "provenance.json").write_text(json.dumps({"case_key": "AWPTCM-T33234"}))
    def boom(k):
        raise RuntimeError("Zephyr answered 500")
    with pytest.raises(RuntimeError):
        tc_finalize.finalize("AWPTCM-T33234", "9001_Port/test-9001.33234.py", "r2", "seat", gen2, "L",
                             get_case=lambda k: CASE, put_case=lambda k, ts: None, new_version=boom, audit=lambda e: True)
    assert case_registry.finalized_case_keys(gen2) == frozenset()


def test_a_finalized_case_leaves_both_lists_and_comes_back_when_the_marker_goes(gen, monkeypatch):
    tc_finalize.mark_finalized(gen, "9001_Port/test-9001.33234.py", "r1", "seat")
    assert case_registry.finalized_case_keys(gen) == frozenset({"AWPTCM-T33234"})
    monkeypatch.setattr(case_registry, "PT_GENERATED_DIR", gen)
    monkeypatch.setitem(case_registry._FINALIZED, "at", 0.0)
    assert case_registry.is_hidden_case("AWPTCM-T33234") is True        # both lists filter through this
    pp = gen / ".meta/9001_Port/test-9001.33234/provenance.json"
    prov = json.loads(pp.read_text()); prov.pop("finalized_at"); pp.write_text(json.dumps(prov))
    monkeypatch.setitem(case_registry._FINALIZED, "at", 0.0)
    assert case_registry.is_hidden_case("AWPTCM-T33234") is False


def test_both_case_lists_filter_through_is_hidden_case():
    for f in ("routers/pytest_create.py", "routers/wizard/reviews.py"):
        assert "and not is_hidden_case(" in (_REPO / "ask-ck/CK-main/CK_server" / f).read_text(encoding="utf-8"), f
