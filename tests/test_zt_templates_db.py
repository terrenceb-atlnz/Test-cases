"""Zephyr Templating Tool, Phase 0b — the template snapshot in ck.db (PLAN-zephyr-templating.md).

`db.replace_zt_templates` imports what `ask-ck/tools/zt_snapshot.py` prints into the
`zt_template_*` tables in one transaction; `db.load_zt_templates` reads the plan -> cycle -> case
tree back; the zephyr-tool router refreshes by running the tool as a subprocess (the server never
holds the Jira token). conftest points every connection at a scratch copy of ck.db, so nothing
here can write the permanent one (test_db_isolation is the authority for that).

The snapshot is built from the REAL first template pair (fixtures zt_plan_P3248 / zt_cycle_C8451)
through the tool's own `fetch` + `assemble`, so the import is tested on the shape the tool emits.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

import db

ROOT = Path(__file__).resolve().parent.parent
FIX = Path(__file__).resolve().parent / "fixtures"
_spec = importlib.util.spec_from_file_location("zt_snapshot_for_db", ROOT / "ask-ck" / "tools" / "zt_snapshot.py")
zt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(zt)  # type: ignore[union-attr]

PLAN = json.loads((FIX / "zt_plan_P3248.json").read_text(encoding="utf-8"))
CYCLE = json.loads((FIX / "zt_cycle_C8451.json").read_text(encoding="utf-8"))
ZT_TABLES = ("zt_template_links", "zt_template_cases", "zt_template_cycles",
             "zt_template_plans", "zt_template_snapshot")


def _snapshot(plans=(PLAN,), cycles=(CYCLE,)):
    plans = {p["key"]: p for p in plans}
    cycles = {c["key"]: c for c in cycles}

    def get(path):
        if "/testplan/search" in path:
            return list(plans.values())
        if "/testrun/search" in path:
            return [c for c in cycles.values() if c["folder"] == zt.CYCLE_FOLDER]
        kind, key = path.rsplit("/", 2)[-2:]
        if kind == "testplan":
            return plans[key]
        if kind == "testrun":
            return cycles[key]
        return {"key": key, "name": f"case {key}", "folder": "/x", "status": "Draft",
                "priority": "Normal", "labels": ["l1"], "majorVersion": 2}
    return zt.assemble(zt.fetch(get))


@pytest.fixture(autouse=True)
def no_templates():
    def _drop():
        conn = db.get_connection()
        for t in ZT_TABLES:
            conn.execute(f"DROP TABLE IF EXISTS {t}")
        conn.commit()
    _drop()
    yield
    _drop()


def test_before_the_first_import_there_is_no_snapshot(client):
    assert db.load_zt_templates() is None
    assert client.get("/api/zephyr-tool/templates").json() == {"snapshot": None}
    st = client.get("/api/zephyr-tool/status").json()
    assert st["status"] == "no-templates" and "No template snapshot" in st["message"]


def test_the_real_port_pair_round_trips_as_a_tree():
    snap = _snapshot()
    assert db.replace_zt_templates(snap) == {"plans": 1, "cycles": 1, "cases": 7, "links": 8}
    tree = db.load_zt_templates()
    (plan,) = tree["plans"]
    assert (plan["key"], plan["name"], plan["folder"]) == ("AWPTCM-P3248", "Port ", zt.PLAN_FOLDER)
    (cycle,) = plan["cycles"]
    assert cycle["key"] == "AWPTCM-C8451"
    assert [c["key"] for c in cycle["cases"]] == [i["testCaseKey"] for i in CYCLE["items"]]   # Zephyr's order
    by_key = {c["key"]: c for c in cycle["cases"]}
    assert by_key["AWPTCM-T43817"]["assigned_to"] == "nings"
    assert by_key["AWPTCM-T33233"]["assigned_to"] is None
    assert by_key["AWPTCM-T33233"]["labels"] == ["l1"] and by_key["AWPTCM-T33233"]["major_version"] == 2
    assert tree["problems"] == snap["problems"] and tree["counts"] == snap["counts"]
    assert tree["unlinked_cycles"] == [] and tree["captured_at"] == snap["captured_at"]


def test_an_import_replaces_the_whole_previous_snapshot():
    db.replace_zt_templates(_snapshot())
    other = copy.deepcopy(PLAN)
    other.update(key="AWPTCM-P3249", name="Sanity Checks")
    db.replace_zt_templates(_snapshot(plans=(other,)))
    assert [p["key"] for p in db.load_zt_templates()["plans"]] == ["AWPTCM-P3249"]


def test_a_malformed_snapshot_is_refused_and_the_previous_one_kept():
    db.replace_zt_templates(_snapshot())
    for bad, word in (({"plans": [], "cycles": [], "cases": []}, "no plans"),
                      ({"plans": [{"key": "AWPTCM-C1"}], "cycles": [], "cases": []}, "bad key"),
                      ({"plans": [{"key": "AWPTCM-P1"}], "cycles": None, "cases": []}, "must be a list"),
                      ("not a snapshot", "object")):
        with pytest.raises(ValueError, match=word):
            db.replace_zt_templates(bad)
    assert [p["key"] for p in db.load_zt_templates()["plans"]] == ["AWPTCM-P3248"]


def test_a_failure_part_way_through_rolls_back():
    db.replace_zt_templates(_snapshot())
    broken = _snapshot()
    broken["cases"].append(dict(broken["cases"][0]))          # duplicate primary key: fails mid-insert
    with pytest.raises(Exception):
        db.replace_zt_templates(broken)
    tree = db.load_zt_templates()
    assert len(tree["plans"][0]["cycles"][0]["cases"]) == 7


def test_a_case_in_two_cycles_is_stored_once_and_linked_twice():
    second = copy.deepcopy(CYCLE)
    second.update(key="AWPTCM-C8465", name="Bootloader Tests (Automated)", items=CYCLE["items"][:1])
    plan = copy.deepcopy(PLAN)
    plan["testRuns"] = [{"key": "AWPTCM-C8451"}, {"key": "AWPTCM-C8465"}]
    written = db.replace_zt_templates(_snapshot(plans=(plan,), cycles=(CYCLE, second)))
    assert written["cases"] == 7 and written["links"] == 2 + 7 + 1
    c1, c2 = db.load_zt_templates()["plans"][0]["cycles"]
    assert c2["cases"][0]["key"] == c1["cases"][0]["key"]


def test_a_template_cycle_no_plan_links_is_kept_and_shown():
    orphan = copy.deepcopy(CYCLE)
    orphan.update(key="AWPTCM-C9999", name="QoS", items=[])
    db.replace_zt_templates(_snapshot(cycles=(CYCLE, orphan)))
    assert [c["key"] for c in db.load_zt_templates()["unlinked_cycles"]] == ["AWPTCM-C9999"]


# --- the router -------------------------------------------------------------------------------

def test_refresh_imports_the_tools_output(client, monkeypatch):
    from routers import zephyr_tool
    snap = _snapshot()
    monkeypatch.setattr(zephyr_tool, "_run_snapshot", lambda: snap)
    r = client.post("/api/zephyr-tool/templates/refresh")
    assert r.status_code == 200 and r.json()["written"]["cases"] == 7
    assert client.get("/api/zephyr-tool/templates").json()["snapshot"]["plans"][0]["key"] == "AWPTCM-P3248"
    st = client.get("/api/zephyr-tool/status").json()
    assert st["status"] == "templates" and "1 plans, 1 cycles, 7 cases" in st["message"]


def test_a_dry_run_writes_nothing(client, monkeypatch):
    from routers import zephyr_tool
    monkeypatch.setattr(zephyr_tool, "_run_snapshot", lambda: _snapshot())
    r = client.post("/api/zephyr-tool/templates/refresh?dry_run=true").json()
    assert r["dry_run"] is True and r["counts"] == {"plans": 1, "cycles": 1, "cases": 7}
    assert db.load_zt_templates() is None


@pytest.mark.parametrize("outcome, status", [("rc1", 502), ("notjson", 502), ("timeout", 504)])
def test_a_failed_snapshot_imports_nothing(client, monkeypatch, outcome, status):
    from routers import zephyr_tool
    db.replace_zt_templates(_snapshot())

    def fake_run(cmd, **kw):
        assert cmd[-1].endswith("zt_snapshot.py") and kw["timeout"] == zephyr_tool.SNAPSHOT_TIMEOUT_S
        if outcome == "timeout":
            raise subprocess.TimeoutExpired(cmd, kw["timeout"])
        return subprocess.CompletedProcess(cmd, 1 if outcome == "rc1" else 0,
                                           stdout="oops" if outcome == "notjson" else "", stderr="boom")
    monkeypatch.setattr(zephyr_tool.subprocess, "run", fake_run)
    r = client.post("/api/zephyr-tool/templates/refresh")
    assert r.status_code == status
    assert [p["key"] for p in db.load_zt_templates()["plans"]] == ["AWPTCM-P3248"]


def test_a_snapshot_the_import_refuses_is_a_422_and_keeps_the_old_one(client, monkeypatch):
    from routers import zephyr_tool
    db.replace_zt_templates(_snapshot())
    monkeypatch.setattr(zephyr_tool, "_run_snapshot", lambda: {"plans": [], "cycles": [], "cases": []})
    assert client.post("/api/zephyr-tool/templates/refresh").status_code == 422
    assert db.load_zt_templates()["plans"][0]["key"] == "AWPTCM-P3248"


def test_only_one_refresh_runs_at_a_time(client):
    from routers import zephyr_tool
    assert zephyr_tool._refresh_lock.acquire(blocking=False)
    try:
        assert client.post("/api/zephyr-tool/templates/refresh").status_code == 409
    finally:
        zephyr_tool._refresh_lock.release()


def test_the_server_never_handles_the_jira_token():
    from _prose import code_lines            # the docstring SAYS the token stays out; check the code
    src = (ROOT / "ask-ck" / "CK-main" / "CK_server" / "routers" / "zephyr_tool.py").read_text(encoding="utf-8")
    code = "\n".join(code_lines(src, jinja=False))
    assert "JIRA_KEY" not in code and "secrets" not in code and "Authorization" not in code
    assert "[sys.executable, str(SNAPSHOT_TOOL)]" in code
