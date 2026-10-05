"""ask-ck/tools/zt_snapshot.py — the Zephyr template set, read-only, discovered by folder.

The fixtures are the real API responses for the first template pair (2026-10-05):
`AWPTCM-P3248` "Port " (plan) -> `AWPTCM-C8451` "Port" (cycle, 7 cases). Everything here is
offline: `fetch` takes the `get` it reads through, and these tests hand it a dict.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import sys
import urllib.error
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "ask-ck" / "tools" / "zt_snapshot.py"
spec = importlib.util.spec_from_file_location("zt_snapshot", TOOL)
zt = importlib.util.module_from_spec(spec)
sys.modules["zt_snapshot"] = zt
spec.loader.exec_module(zt)  # type: ignore[union-attr]

FIX = Path(__file__).resolve().parent / "fixtures"
PLAN = json.loads((FIX / "zt_plan_P3248.json").read_text(encoding="utf-8"))
CYCLE = json.loads((FIX / "zt_cycle_C8451.json").read_text(encoding="utf-8"))
CASE_KEYS = [i["testCaseKey"] for i in CYCLE["items"]]


def _world(plans=(PLAN,), cycles=(CYCLE,), missing=()):
    """A fake Zephyr: search by folder, GET by key, and a log of every path read."""
    plans = {p["key"]: p for p in plans}
    cycles = {c["key"]: c for c in cycles}
    seen = []

    def get(path):
        seen.append(path)
        if "/testplan/search" in path:
            return [p for p in plans.values() if p["folder"] == zt.PLAN_FOLDER]
        if "/testrun/search" in path:
            return [c for c in cycles.values() if c["folder"] == zt.CYCLE_FOLDER]
        kind, key = path.rsplit("/", 2)[-2:]
        if kind == "testplan":
            return plans[key]
        if kind == "testrun":
            return cycles[key]
        if key in missing:
            raise urllib.error.HTTPError(path, 404, "nf", {}, None)
        return {"key": key, "name": f"Port - {key}", "folder": "/New Platform Test (MASTER)/New Platform Template/Port",
                "status": "Draft", "priority": "Normal", "labels": [], "majorVersion": 2, "objective": "x"}
    return get, seen


def test_the_real_port_template_pair_snapshots_as_one_plan_one_cycle_seven_cases():
    get, seen = _world()
    snap = zt.assemble(zt.fetch(get))
    assert snap["counts"] == {"plans": 1, "cycles": 1, "cases": 7}
    assert snap["plans"][0] == {"key": "AWPTCM-P3248", "name": "Port ", "folder": zt.PLAN_FOLDER,
                                "status": "Draft", "cycles": ["AWPTCM-C8451"]}
    assert snap["cycles"][0]["cases"] == CASE_KEYS
    assert sorted(c["key"] for c in snap["cases"]) == sorted(CASE_KEYS)
    assert set(snap["cases"][0]) == set(zt.CASE_FIELDS)          # no objective / script in the snapshot
    json.dumps(snap)                                                # it is the JSON the import takes


def test_its_three_real_problems_are_reported():
    get, _ = _world()
    probs = zt.assemble(zt.fetch(get))["problems"]
    assert any("AWPTCM-T43817 is assigned to 'nings'" in p for p in probs)
    assert any("AWPTCM-T47871 is assigned to 'JIRAUSER17403'" in p for p in probs)
    assert any("plan AWPTCM-P3248 name 'Port ' has stray whitespace" in p for p in probs)
    assert len(probs) == 3


def test_discovery_is_by_folder_and_reads_each_object_once():
    get, seen = _world()
    zt.fetch(get)
    searches = [p for p in seen if "/search?" in p]
    assert len(searches) == 2 and all("Platform%20Testing" in p for p in searches)
    assert seen.count("/rest/atm/1.0/testrun/AWPTCM-C8451") == 1    # found by folder AND by the plan link
    assert len([p for p in seen if "/testcase/" in p]) == 7


def test_an_orphan_cycle_a_misplaced_cycle_and_an_unreadable_case_are_problems():
    orphan = copy.deepcopy(CYCLE)
    orphan.update(key="AWPTCM-C9999", name="QoS", items=[])
    misplaced = copy.deepcopy(CYCLE)
    misplaced.update(key="AWPTCM-C9998", folder="/Somewhere Else", items=[])
    plan = copy.deepcopy(PLAN)
    plan["testRuns"].append({"key": "AWPTCM-C9998"})
    get, _ = _world(plans=(plan,), cycles=(CYCLE, orphan, misplaced), missing=("AWPTCM-T33233",))
    probs = zt.assemble(zt.fetch(get))["problems"]
    assert any("AWPTCM-C9999 'QoS' is in the template folder but no template plan links it" in p for p in probs)
    assert any("AWPTCM-C9998" in p and "lives in '/Somewhere Else'" in p for p in probs)
    assert any("case AWPTCM-T33233 could not be read (HTTP 404)" in p for p in probs)


def test_a_plan_with_no_cycle_is_a_problem():
    bare = copy.deepcopy(PLAN)
    bare.update(key="AWPTCM-P9999", name="IPv4", testRuns=[])
    get, _ = _world(plans=(PLAN, bare))
    assert any("plan AWPTCM-P9999 'IPv4' links no cycle" in p for p in zt.assemble(zt.fetch(get))["problems"])


def test_it_is_read_only_and_never_touches_ck_db():
    with pytest.raises(ValueError, match="read-only"):
        zt._get("/rest/atm/1.0/testplan/X", "t", method="POST")
    src = TOOL.read_text(encoding="utf-8")
    assert "sqlite3" not in src and 'method="GET"' in src
