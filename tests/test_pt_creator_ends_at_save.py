"""The PyTest Creator ends at a saved script (Terrence 2026-10-12).

Running and validating a script moved to Validation (PLAN-test-validation V4): 6. Run and
7. Validate are gone, so
  * Confirm Step 5 (internal step 6) SAVES the script to generated/ first, then confirms —
    a failed write leaves it unconfirmed;
  * the two refusals a reviewer may override say which acknowledgement they want in an
    `X-CK-Needs` header, so the page can ask for it (it never could: it always sent `{}`);
  * steps 7 and 8 cannot be confirmed any more;
  * the Cases panel's Complete = "its script is saved to generated/", read off disk.
Offline: the session store and the file writer are faked; no ck.db write, no LLM.
"""
import asyncio
import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import case_registry
from routers import pytest_create as pc

KEY = "AWPTCM-T99991"           # throwaway; never a real case


@pytest.fixture
def world(monkeypatch):
    sess = pc.PtSession(key=KEY)
    sess.step6 = {"naming": {"group": "Port", "name": "test-9001.99991"},
                  "files": {"test": {"name": "test-9001.99991.py", "code": "print(1)\n"}},
                  "lint": {"ok": True, "errors": [], "blocking_errors": [], "policy_errors": []}}
    w = SimpleNamespace(sess=sess, writes=[], persisted=[], gap="", write_error=None)

    def write(s):
        w.writes.append(bool((s.step6 or {}).get("confirmed")))   # confirmed AT write time
        if w.write_error:
            raise w.write_error
        return ["generated/9001_Port/test-9001.99991.py"]

    monkeypatch.setattr(pc, "_pt_get", lambda k: sess)
    monkeypatch.setattr(pc, "_pt_persist", lambda s: w.persisted.append(s))
    monkeypatch.setattr(pc, "_coverage_gate_error", lambda s, step: w.gap)
    monkeypatch.setattr(pc, "_persist_generated_files", write)
    return w


def confirm(step, body=None):
    return asyncio.run(pc.confirm_step(KEY, step, body or {}))


def test_confirm_step_5_saves_then_confirms(world):
    out = confirm(6)
    assert world.writes == [False], "the script is written once, BEFORE the step is confirmed"
    assert world.sess.step6["confirmed"] is True
    assert out["written"] == ["generated/9001_Port/test-9001.99991.py"]


def test_a_failed_save_leaves_step_5_unconfirmed(world):
    world.write_error = HTTPException(409, "library clash")
    with pytest.raises(HTTPException) as e:
        confirm(6)
    assert e.value.status_code == 409 and "library clash" in e.value.detail
    assert not world.sess.step6.get("confirmed") and world.persisted == []


def test_other_steps_do_not_write(world):
    world.sess.step2 = {"sequence": [{"n": 1, "action": "a", "verify": "v"}]}
    confirm(2)
    assert world.writes == [] and world.sess.step2["confirmed"] is True


@pytest.mark.parametrize("step", [7, 8])
def test_run_and_validate_cannot_be_confirmed_any_more(world, step):
    with pytest.raises(HTTPException) as e:
        confirm(step)
    assert e.value.status_code == 400


def test_a_coverage_gap_names_its_acknowledgement(world):
    world.gap = "step 3 has no PyTest step"
    with pytest.raises(HTTPException) as e:
        confirm(6)
    assert e.value.status_code == 409
    assert e.value.headers == {"X-CK-Needs": "acknowledge_coverage_gap"}
    assert world.writes == []
    confirm(6, {"acknowledge_coverage_gap": True})
    assert world.writes == [False]


def test_a_house_rule_names_its_acknowledgement_and_keeps_the_reason(world):
    world.sess.step6["lint"]["policy_errors"] = ["policy: init_portlink called directly"]
    with pytest.raises(HTTPException) as e:
        confirm(6)
    assert e.value.headers == {"X-CK-Needs": "acknowledge_lint_policy"}
    assert world.writes == []
    confirm(6, {"acknowledge_lint_policy": "the bench has no fibre"})
    assert world.sess.step6["policy_acknowledgements"][-1]["reason"] == "the bench has no fibre"
    assert world.writes == [False]


# --- Complete = saved to generated/ -----------------------------------------------------

def _save(gen, group, name, prov, script=True):
    meta = gen / ".meta" / group / name
    meta.mkdir(parents=True)
    (meta / "provenance.json").write_text(json.dumps(prov), encoding="utf-8")
    if script:
        (gen / group).mkdir(exist_ok=True)
        (gen / group / f"{name}.py").write_text("x\n", encoding="utf-8")


def test_saved_means_provenance_with_saved_at_and_the_script_on_disk(tmp_path):
    _save(tmp_path, "9001_Port", "test-9001.1", {"case_key": "AWPTCM-T1", "saved_at": "2026-10-12T00:00:00+00:00"})
    _save(tmp_path, "9001_Port", "test-9001.2", {"case_key": "AWPTCM-T2", "saved_at": "2026-10-12T00:00:00+00:00"},
          script=False)                                     # the .py was deleted
    _save(tmp_path, "9001_Port", "test-9001.3", {"case_key": "AWPTCM-T3"})            # never saved
    (tmp_path / ".meta" / "9001_Port" / "broken").mkdir()
    (tmp_path / ".meta" / "9001_Port" / "broken" / "provenance.json").write_text("{not json")
    assert case_registry.saved_script_case_keys(tmp_path) == frozenset({"AWPTCM-T1"})


def test_the_cases_panel_puts_saved_cases_in_complete(monkeypatch):
    keys = ["AWPTCM-T99991", "AWPTCM-T99992", "AWPTCM-T99993"]
    data = {"zephyr_master": {k: {"title": k, "folder": "/X/Port"} for k in keys},
            "candidates": [{"key": k, "candidates": [1]} for k in keys]}
    monkeypatch.setattr(pc, "_data", lambda request: data)
    monkeypatch.setattr(pc, "refined_complete_keys", lambda: set(keys))
    monkeypatch.setattr(pc, "saved_script_case_keys", lambda: frozenset({"AWPTCM-T99992"}))
    # a stored session that 7. Validate once passed means nothing now
    monkeypatch.setattr(pc.dbx, "list_pt_progress",
                        lambda: {"AWPTCM-T99993": {"confirms": 2, "validated": True}})
    out = asyncio.run(pc.pt_cases(None))
    flat = lambda groups: [c["key"] for g in groups for c in g["cases"]]
    assert flat(out["complete"]["grouped"]) == ["AWPTCM-T99992"]
    assert sorted(flat(out["in_progress"]["grouped"])) == ["AWPTCM-T99991", "AWPTCM-T99993"]
    assert out["in_progress"]["grouped"][0]["cases"][0]["title"].endswith("[2/5 steps]")


def test_a_case_hidden_from_the_creator_leaves_both_its_lists_and_only_those(monkeypatch):
    """Terrence 2026-10-13: T33235's script was reworked outside the Creator while it is in
    Validation, so the Creator must not offer it for re-generation; Finalize removes it later."""
    keys = ["AWPTCM-T99991", "AWPTCM-T99992"]
    data = {"zephyr_master": {k: {"title": k, "folder": "/X/Port"} for k in keys},
            "candidates": [{"key": k, "candidates": [1]} for k in keys]}
    monkeypatch.setattr(pc, "_data", lambda request: data)
    monkeypatch.setattr(pc, "refined_complete_keys", lambda: set(keys))
    monkeypatch.setattr(pc, "saved_script_case_keys", lambda: frozenset(keys))
    monkeypatch.setattr(pc.dbx, "list_pt_progress", lambda: {})
    monkeypatch.setattr(pc, "PT_CREATOR_HIDDEN_KEYS", frozenset({"AWPTCM-T99992"}))
    out = asyncio.run(pc.pt_cases(None))
    flat = lambda groups: [c["key"] for g in groups for c in g["cases"]]
    assert flat(out["complete"]["grouped"]) == ["AWPTCM-T99991"]
    assert flat(out["in_progress"]["grouped"]) == []
    assert "AWPTCM-T33235" in case_registry.PT_CREATOR_HIDDEN_KEYS
    assert not case_registry.is_hidden_case("AWPTCM-T33235", "/New Platform Test (MASTER)/Port")


def test_progress_counts_only_the_creators_five_steps(monkeypatch):
    import db
    payload = {"key": KEY, **{f"step{n}": {"confirmed": True} for n in range(2, 9)}}   # an old session
    monkeypatch.setattr(db, "_rows", lambda sql, *a, **k: [{"id": KEY, "payload": json.dumps(payload)}])
    assert db.list_pt_progress() == {KEY: {"confirms": 5}}
