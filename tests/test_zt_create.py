"""ask-ck/tools/zt_create.py — create new cases, a plan and a cycle from a draft. Offline: the tool
reads through the `get` it is handed and writes through the `send` it is handed, and these tests
hand it a fake Zephyr that keeps what is written and answers the reads from it.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import sys
import urllib.parse
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "ask-ck" / "tools"
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("zt_create", TOOLS / "zt_create.py")
zc = importlib.util.module_from_spec(spec)
sys.modules["zt_create"] = zc
spec.loader.exec_module(zc)  # type: ignore[union-attr]

PLAN_DIR = "/9.9.9-0/Team/Project 9999: FEAT"
CASE_DIR = "/9.9.9-0/Team/FEAT"


def _case(i, folder=CASE_DIR + "/Sub A"):
    return {"draftId": f"D-{i}", "name": f"FEAT - case {i}", "folder": folder, "status": "Draft",
            "priority": "Normal", "labels": ["FEAT"], "objective": f"<ul><li>end state {i}</li></ul>",
            "precondition": "Topology T1.",
            "testScript": {"type": "STEP_BY_STEP", "steps": [
                {"description": "Notes / traceability: spec", "expectedResult": ""},
                {"description": f"Do thing {i}.", "expectedResult": ""}]}}


def _draft(n=3, items=None):
    cases = [_case(i, CASE_DIR + ("/Sub A" if i % 2 else "/Sub B/Deep")) for i in range(n)]
    return {"testPlan": {"name": "FEAT - Plan", "folder": PLAN_DIR, "status": "Draft", "objective": "<p>x</p>"},
            "testCycle": {"name": "FEAT - Cycle", "folder": PLAN_DIR, "status": "Not Executed",
                          "description": "all", "items": items if items is not None else [c["draftId"] for c in cases]},
            "testCases": cases}


def _tree(paths):
    root = {"children": []}
    for p in sorted(paths):
        node = root
        for part in p.strip("/").split("/"):
            kid = next((k for k in node["children"] if k["name"] == part), None)
            if kid is None:
                kid = {"name": part, "id": len(paths) + len(node["children"]), "children": []}
                node["children"].append(kid)
            node = kid
    return root


class FakeZephyr:
    """Folder trees, searches and objects; POSTs create objects that later GETs return."""

    def __init__(self, case_dirs=(CASE_DIR,), plan_dirs=(PLAN_DIR,), run_dirs=(PLAN_DIR,)):
        self.dirs = {"testcase": set(case_dirs), "testplan": set(plan_dirs), "testrun": set(run_dirs)}
        for kind in self.dirs:  # a tree holds every ancestor of its folders
            self.dirs[kind] |= {a for d in list(self.dirs[kind]) for a in zc._ancestors(d)}
        self.objs = {"testcase": {}, "testplan": {}, "testrun": {}}
        self.sent, self.n, self.fail_on = [], 0, None
        self.mangle = None  # (key, field, value) applied when that object is read back

    def get(self, path):
        if "/foldertree/" in path:
            return _tree(self.dirs[path.rsplit("/", 1)[1]])
        kind = path.split("/rest/atm/1.0/")[1].split("/")[0]
        if "/search?" in path:
            q = urllib.parse.unquote(path.split("query=")[1].split("&")[0])
            folder = q.split('folder = "')[1].rstrip('"')
            return [o for o in self.objs[kind].values() if o["folder"] == folder]
        o = copy.deepcopy(self.objs[kind][path.rsplit("/", 1)[1]])
        if self.mangle and self.mangle[0] == o["key"]:
            o[self.mangle[1]] = self.mangle[2]
        return o

    def send(self, method, path, body):
        self.sent.append((method, path, copy.deepcopy(body)))
        kind = path.rsplit("/", 1)[1]
        if self.fail_on and self.fail_on(kind, body):
            return 400, b'{"errorMessages":["no"]}'
        if kind == "folder":
            self.dirs["testcase"].add(body["name"])
            return 201, b'{"id": 1}'
        self.n += 1
        prefix = {"testcase": "T", "testplan": "P", "testrun": "C"}[kind]
        key = f"FAKE-{prefix}{self.n}"
        o = dict(copy.deepcopy(body), key=key)
        if kind == "testcase":
            o["testScript"]["steps"] = [dict(s, index=i) for i, s in enumerate(o["testScript"]["steps"])]
        if kind == "testrun":
            self.objs["testplan"][body["testPlanKey"]].setdefault("testRuns", []).append({"key": key})
        self.objs[kind][key] = o
        return 201, json.dumps({"id": self.n, "key": key}).encode()

    def add(self, kind, body):
        status, raw = self.send("POST", f"/rest/atm/1.0/{kind}", body)
        self.sent.pop()
        return json.loads(raw)["key"]


def _apply(z, draft, audit=None, **kw):
    log = []
    res = zc.apply(z.get, z.send, audit or (lambda rec: log.append(rec) or True), draft, lambda r: None,
                   kw.get("folder", draft["testPlan"]["folder"]), kw.get("cases", len(draft["testCases"])))
    return res, log


def test_validate_flags_bad_drafts():
    d = _draft()
    d["testCases"][1]["objective"] = ""
    d["testCases"][2]["name"] = d["testCases"][0]["name"]
    d["testCases"][2]["folder"] = d["testCases"][0]["folder"]
    d["testCases"][0]["testScript"] = {"type": "steps", "steps": []}
    d["testCycle"]["items"] = ["D-0", "D-9", "D-0"]
    probs = " | ".join(zc.validate(d))
    for want in ("has no objective", "same name twice", "STEP_BY_STEP", "D-9", "repeats a draft id"):
        assert want in probs
    assert zc.validate(_draft()) == []


def test_preview_creates_missing_case_folders_parent_first():
    out = zc.preview(FakeZephyr().get, _draft())
    assert out["problems"] == []
    folders = [c["body"]["name"] for c in out["calls"] if c["op"] == "folder"]
    assert folders == [CASE_DIR + "/Sub A", CASE_DIR + "/Sub B", CASE_DIR + "/Sub B/Deep"]
    assert all(c["body"]["type"] == "TEST_CASE" for c in out["calls"] if c["op"] == "folder")
    assert [c["op"] for c in out["calls"]][-2:] == ["plan", "cycle"]


def test_preview_refuses_shallow_anchor_and_missing_plan_folder():
    z = FakeZephyr(case_dirs=("/9.9.9-0/Team",), plan_dirs=())
    probs = " | ".join(zc.preview(z.get, _draft())["problems"])
    assert "too shallow" in probs and "the plan folder" in probs


def test_preview_reuses_existing_case_and_plan_and_refuses_existing_cycle():
    z = FakeZephyr(case_dirs=(CASE_DIR + "/Sub A", CASE_DIR + "/Sub B/Deep"))
    d = _draft()
    case_key = z.add("testcase", zc.case_body(d["testCases"][1]))
    plan_key = z.add("testplan", zc.plan_body(d["testPlan"]))
    out = zc.preview(z.get, d)
    assert out["reuse"] == {"case:1": case_key, "plan": plan_key}
    assert [c["op"] for c in out["calls"]] == ["case", "case", "cycle"]
    z.add("testrun", zc.cycle_body(d["testCycle"], plan_key, [case_key]))
    assert "already exists" in " ".join(zc.preview(z.get, d)["problems"])


def test_apply_refuses_without_matching_confirmations():
    z = FakeZephyr()
    with pytest.raises(zc.Stop):
        _apply(z, _draft(), folder="/wrong")
    with pytest.raises(zc.Stop):
        _apply(z, _draft(), cases=99)
    assert z.sent == []


def test_apply_sends_nothing_when_the_audit_cannot_be_written():
    z = FakeZephyr()
    with pytest.raises(zc.Stop):
        _apply(z, _draft(), audit=lambda rec: False)
    assert z.sent == []
    calls = []
    res, _ = _apply(z, _draft(), audit=lambda rec: calls.append(rec) or rec.get("event") != "write")
    assert res["outcome"] == "stopped" and z.sent == []


def test_apply_order_cycle_links_plan_and_cases_and_read_back_passes():
    z = FakeZephyr()
    d = _draft(4, items=["D-3", "D-0", "D-2", "D-1"])
    res, log = _apply(z, d)
    assert res["outcome"] == "done", res["problems"]
    kinds = [p.rsplit("/", 1)[1] for _, p, _ in z.sent]
    assert kinds == ["folder"] * 3 + ["testcase"] * 4 + ["testplan", "testrun"]
    cyc = z.sent[-1][2]
    assert cyc["testPlanKey"] == res["created"]["plan"]
    assert [i["testCaseKey"] for i in cyc["items"]] == [res["created"][x] for x in ["D-3", "D-0", "D-2", "D-1"]]
    writes = [r for r in log if r["event"] == "write"]
    assert len(writes) == len(z.sent)  # one audit line before every write


def test_apply_stops_at_the_first_failed_write():
    z = FakeZephyr()
    z.fail_on = lambda kind, body: kind == "testcase" and body["name"].endswith("case 1")
    res, log = _apply(z, _draft())
    assert res["outcome"] == "stopped" and "answered 400" in res["problems"][0]
    assert not any(p.endswith("testplan") or p.endswith("testrun") for _, p, _ in z.sent)
    assert list(res["created"]) == ["D-0"]
    assert log[-1]["event"] == "end"


def test_rerun_after_a_stop_reuses_what_was_created():
    z = FakeZephyr()
    z.fail_on = lambda kind, body: kind == "testrun"
    first, _ = _apply(z, _draft())
    assert first["outcome"] == "stopped"
    z.fail_on, z.sent = None, []
    second, _ = _apply(z, _draft())
    assert second["outcome"] == "done"
    assert [p.rsplit("/", 1)[1] for _, p, _ in z.sent] == ["testrun"]


def test_read_back_reports_a_difference():
    z = FakeZephyr()
    d = _draft()
    first = None

    def send(method, path, body):
        nonlocal first
        status, raw = FakeZephyr.send(z, method, path, body)
        if path.endswith("testcase") and first is None:
            first = json.loads(raw)["key"]
            z.mangle = (first, "priority", "High")
        return status, raw

    res = zc.apply(z.get, send, lambda rec: True, d, lambda r: None, PLAN_DIR, len(d["testCases"]))
    assert res["outcome"] == "verify-failed"
    assert any(p.startswith(first) and "priority differs" in p for p in res["problems"])
