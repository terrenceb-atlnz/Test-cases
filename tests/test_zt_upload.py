"""ask-ck/tools/zt_upload.py — API Upload, DRY RUN ONLY (PLAN-zephyr-templating.md D9, §6).

Offline: `preview` takes the `get` it reads through. The folder names are IE570's real ones
(`/5.5.6-2/Tomahawk/Project 3001: IE570`, 2026-10-05) and the call order is the one measured by
hand on IE570: clone the plan first, so each cycle clone joins the new plan as well as the template
plan; then the two kinds of unlink; then the renames the UI capture proved. The clone, move and
remove-case bodies are the ones captured from the UI on 2026-10-07 (Factory Tests → IE570, §6a).
"""
from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "ask-ck" / "tools" / "zt_upload.py"
spec = importlib.util.spec_from_file_location("zt_upload", TOOL)
zu = importlib.util.module_from_spec(spec)
sys.modules["zt_upload"] = zu
spec.loader.exec_module(zu)  # type: ignore[union-attr]

PATHS = ["/5.5.6-2", "/5.5.6-2/Tomahawk", "/5.5.6-2/Tomahawk/Project 3001: IE570",
         "/5.5.6-2/Tomahawk/Project 3296: IE520", "/5.5.6-2/Other"]
SEL = {"version": "5.5.6-2", "middle": "Tomahawk", "product": "IE570", "number": "3001", "plans": [
    {"key": "AWPTCM-P3256", "name": "Bootloader Tests", "cycles": [
        {"key": "AWPTCM-C8459", "name": "Bootloader Tests (Manual)", "selected": True, "excluded": ["AWPTCM-T1"]},
        {"key": "AWPTCM-C8465", "name": "Bootloader Tests (Automated)", "selected": False, "excluded": []}]}]}


def _tree(paths):
    root = {"children": []}
    n = 26600
    for p in paths:
        node = root
        for part in p.strip("/").split("/"):
            kid = next((c for c in node["children"] if c["name"] == part), None)
            if kid is None:
                n += 1
                kid = {"name": part, "id": n, "children": []}
                node["children"].append(kid)
            node = kid
    return root


def _get(paths=PATHS):
    seen = []

    def get(path):
        seen.append(path)
        if "/foldertree/" in path:
            return _tree(paths)
        key = path.split("/")[-1].split("?")[0]
        return {"id": 1000 + int(key.split("-")[1][1:]), "key": key}
    return get, seen


def test_the_target_folder_is_the_child_naming_the_project_number_or_product():
    t = zu.find_target(PATHS, "5.5.6-2", "Tomahawk", "IE570", "3001")
    assert t["path"] == "/5.5.6-2/Tomahawk/Project 3001: IE570" and t["base_exists"]
    t = zu.find_target(PATHS, "5.5.6-2", "Tomahawk", "IE5", None)      # matches two → none chosen
    assert t["path"] is None and len(t["candidates"]) == 2
    assert zu.find_target(PATHS, "5.5.7", "Tomahawk", "IE570", "3001")["base_exists"] is False


def test_the_call_list_follows_the_measured_order():
    d = zu.preview(_get()[0], SEL)
    ops = [c["op"] for c in d["calls"]]
    assert ops == ["clone plan", "move plan", "clone cycle", "move cycle", "unlink", "unlink", "unlink",
                   "remove case", "rename", "rename", "verify", "verify"]
    assert "AWPTCM-C8465" not in " ".join(c["about"] for c in d["calls"] if c["op"] == "clone cycle")   # unticked: not cloned
    assert any("AWPTCM-C8465" in c["path"] for c in d["calls"] if c["op"] == "unlink")              # …but unlinked
    renames = [c["body"]["name"] for c in d["calls"] if c["op"] == "rename"]
    assert renames == ["IE570: Bootloader Tests (Ask-CK)", "IE570: Bootloader Tests (Manual) (Ask-CK)"]
    assert d["targets"]["testplan"]["path"] == "/5.5.6-2/Tomahawk/Project 3001: IE570" and d["problems"] == []


def test_every_call_is_known_and_carries_the_captured_request():
    d = zu.preview(_get()[0], SEL)
    assert all(c["known"] for c in d["calls"])
    by = {c["op"]: c for c in d["calls"]}
    assert (by["clone plan"]["method"], by["clone plan"]["path"]) == ("POST", "/rest/tests/1.0/testplan/bulk/clone")
    assert by["clone plan"]["body"] == {"projectId": 15310, "sourceIdList": [4256]}           # the template's id
    assert by["clone cycle"]["body"] == {"projectId": 15310, "sourceIdList": [9459],
                                         "tql": "testRun.projectId IN (15310)"}
    plan_dir, cycle_dir = d["targets"]["testplan"]["id"], d["targets"]["testrun"]["id"]
    assert isinstance(plan_dir, int) and isinstance(cycle_dir, int)
    assert (by["move plan"]["method"], by["move plan"]["path"]) == ("PUT", "/rest/tests/1.0/testplan")
    assert by["move plan"]["body"][0]["folderId"] == plan_dir                                 # a folder ID, not a path
    assert (by["move cycle"]["method"], by["move cycle"]["path"]) == ("PUT", "/rest/tests/1.0/testrun/bulk/update")
    assert by["move cycle"]["body"][0]["folderId"] == cycle_dir
    rm = by["remove case"]
    assert (rm["method"], rm["path"]) == ("PUT", "/rest/tests/1.0/testrunitem/bulk/save")
    assert rm["body"]["deletedTestRunItems"] == [{"id": "<item id of AWPTCM-T1>"}]            # ITEM ids, not case ids
    assert d["counts"] == {"plans": 1, "cycles": 1, "calls": 12, "writes_known": 10, "writes_not_captured": 0}


def test_cases_leave_a_cycle_in_one_save_and_an_untouched_cycle_sends_none():
    sel = json.loads(json.dumps(SEL))
    sel["plans"][0]["cycles"][0]["excluded"] = ["AWPTCM-T1", "AWPTCM-T2"]
    rm = [c for c in zu.preview(_get()[0], sel)["calls"] if c["op"] == "remove case"]
    assert len(rm) == 1 and len(rm[0]["body"]["deletedTestRunItems"]) == 2
    sel["plans"][0]["cycles"][0]["excluded"] = []
    assert not [c for c in zu.preview(_get()[0], sel)["calls"] if c["op"] == "remove case"]


def test_the_new_cycle_is_unlinked_from_every_plan_but_its_own_and_checked_from_its_side():
    """A cycle clone joins every plan its template is in, archived clones included, and an archived
    plan shows only from the cycle side (§6a: P3264 on 2026-10-07)."""
    d = zu.preview(_get()[0], SEL)
    unlink = [c for c in d["calls"] if c["op"] == "unlink" and "new cycle from AWPTCM-C8459" in c["path"]]
    assert len(unlink) == 1 and "not to <new plan from AWPTCM-P3256>" in unlink[0]["path"]
    assert "archived" in unlink[0]["about"]
    verify = [c["path"] for c in d["calls"] if c["op"] == "verify"]
    assert any(p.startswith("/rest/tests/1.0/testrun/<id of new cycle from AWPTCM-C8459>") for p in verify)


def test_a_missing_project_folder_is_a_problem_not_a_guess():
    d = zu.preview(_get(["/5.5.6-2", "/5.5.6-2/Tomahawk"])[0], SEL)
    assert any("create it first" in p for p in d["problems"])
    assert d["targets"]["testplan"]["path"] is None
    assert any("<plan folder not found>" in c["about"] for c in d["calls"] if c["op"] == "move plan")


def test_it_only_reads_and_apply_is_refused(monkeypatch, capsys):
    get, seen = _get()
    zu.preview(get, SEL)
    assert all("/foldertree/" in p or "?fields=id,key" in p for p in seen)
    src = TOOL.read_text(encoding="utf-8")
    assert "urlopen" not in src and "Request(" not in src          # every read goes through zt_snapshot._get (GET only)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(SEL)))
    assert zu.main(["--apply"]) == 2 and zu.main([]) == 2
    assert "only --dry-run exists" in capsys.readouterr().err
