"""ask-ck/tools/zt_upload.py — API Upload (PLAN-zephyr-templating.md D9, D13–D15, §5b, §6, §6a).

Offline. `FakeZephyr` behaves the way Zephyr was MEASURED to on IE570 (§6, §6a): a plan clone lands
in the template folder still linked to the template's cycles; a cycle clone joins EVERY plan its
template is in — archived ones included, which only the cycle side shows; a cycle clone's `tql`
leaves out `testCase.key NOT IN (...)`; a link is one record seen from both ends; moves and renames
answer 200 with no body. The folder names are IE570's real ones (2026-10-05).
"""
from __future__ import annotations

import copy
import importlib.util
import io
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "ask-ck" / "tools" / "zt_upload.py"
spec = importlib.util.spec_from_file_location("zt_upload", TOOL)
zu = importlib.util.module_from_spec(spec)
sys.modules["zt_upload"] = zu
spec.loader.exec_module(zu)  # type: ignore[union-attr]

API = "/rest/tests/1.0"
PATHS = ["/5.5.6-2", "/5.5.6-2/Tomahawk", "/5.5.6-2/Tomahawk/Project 3001: IE570",
         "/5.5.6-2/Tomahawk/Project 3296: IE520", "/5.5.6-2/Other", "/5.5.6-1", "/5.5.6-1/Tomahawk",
         "/5.5.6-1/Tomahawk/Project 3001: IE570 (old)", "/Platform Testing", "/Platform Testing/TEMPLATES"]
SEL = {"version": "5.5.6-2", "middle": "Tomahawk", "product": "IE570", "number": "3001", "plans": [
    {"key": "AWPTCM-P3256", "name": "Bootloader Tests", "cycles": [
        {"key": "AWPTCM-C8459", "name": "Bootloader Tests (Manual)", "selected": True, "excluded": ["AWPTCM-T1"]},
        {"key": "AWPTCM-C8465", "name": "Bootloader Tests (Automated)", "selected": False, "excluded": []}]}]}
CONFIRM = {"product": "IE570", "version": "5.5.6-2"}


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


def _folder_id(paths, path):
    return dict(zu._walk(_tree(paths)))[path]


class FakeZephyr:
    """Plans, cycles, cases and links, with Zephyr's measured clone behaviour (§6, §6a)."""

    def __init__(self, paths=PATHS):
        self.paths = paths
        tpl_plans, tpl_cycles = _folder_id(paths, "/Platform Testing/TEMPLATES"), _folder_id(paths, "/Platform Testing/TEMPLATES")
        self.plans = {3256: {"key": "AWPTCM-P3256", "name": "Bootloader Tests", "folder": tpl_plans, "archived": False}}
        self.cycles = {8459: {"key": "AWPTCM-C8459", "name": "Bootloader Tests (Manual)", "folder": tpl_cycles,
                              "cases": ["AWPTCM-T1", "AWPTCM-T2", "AWPTCM-T3"]},
                       8465: {"key": "AWPTCM-C8465", "name": "Bootloader Tests (Automated)", "folder": tpl_cycles,
                              "cases": []}}
        self.links = {1: (3256, 8459), 2: (3256, 8465)}
        self.next_id, self.reads, self.writes = 90000, [], []
        self.fail = None            # (op-matching substring of "METHOD path", status) to fail on

    def _new(self):
        self.next_id += 1
        return self.next_id

    def by_key(self, key):
        for table in (self.plans, self.cycles):
            for i, o in table.items():
                if o["key"] == key:
                    return i
        raise KeyError(key)

    # ---- reads
    def get(self, path):
        self.reads.append(path)
        if "/foldertree/" in path:
            return _tree(self.paths)
        if path.startswith("/rest/atm/1.0/testplan/search"):
            folder = re.search(r'folder%20%3D%20%22(.*?)%22', path).group(1)
            from urllib.parse import unquote
            folder = unquote(folder)
            fid = _folder_id(self.paths, folder)
            return [{"key": p["key"], "name": p["name"]} for p in self.plans.values()
                    if p["folder"] == fid and not p["archived"]]
        m = re.match(rf"{API}/testrun/(\d+)/testrunitems", path)
        if m:
            c = self.cycles[int(m.group(1))]
            return {"total": len(c["cases"]), "testRunItemsWithNoPermission": [],
                    "testRunItems": [{"id": n, "index": n, "$lastTestResult": {"testCase": {"key": k}}}
                                     for n, k in enumerate(c["cases"])]}
        m = re.match(rf"{API}/(testplan|testrun)/([^?]+)\?fields=(.*)", path)
        kind, ident, fields = m.groups()
        table = self.plans if kind == "testplan" else self.cycles
        rid = int(ident) if ident.isdigit() else self.by_key(ident)
        if rid not in table:
            raise KeyError(path)
        out = {"id": rid, "key": table[rid]["key"]}
        if "traceLinks" in fields:
            if kind == "testplan":
                out["traceLinks"] = [{"id": l, "testRun": {"id": c, "key": self.cycles[c]["key"]}}
                                     for l, (p, c) in self.links.items() if p == rid]
            else:
                out["traceLinks"] = [{"id": l, "testPlan": {"id": p, "key": self.plans[p]["key"],
                                                            "archived": self.plans[p]["archived"]}}
                                     for l, (p, c) in self.links.items() if c == rid]
        return out

    # ---- writes
    def send(self, method, path, body):
        self.writes.append((method, path, copy.deepcopy(body)))
        if self.fail and self.fail[0] in f"{method} {path}":
            return self.fail[1], b'{"errorMessages":["no"]}'
        if (method, path) == ("POST", f"{API}/testplan/bulk/clone"):
            src = body["sourceIdList"][0]
            new = self._new()
            self.plans[new] = dict(self.plans[src], key=f"AWPTCM-P{new}", name=self.plans[src]["name"] + " (cloned)")
            for p, c in list(self.links.values()):
                if p == src:
                    self.links[self._new()] = (new, c)
            return 200, json.dumps([new]).encode()
        if (method, path) == ("POST", f"{API}/testrun/bulk/clone"):
            src = body["sourceIdList"][0]
            out = re.findall(r"'([^']+)'", body["tql"].split("NOT IN", 1)[1]) if "NOT IN" in body["tql"] else []
            new = self._new()
            self.cycles[new] = dict(self.cycles[src], key=f"AWPTCM-C{new}", name=self.cycles[src]["name"] + " (cloned)",
                                    cases=[k for k in self.cycles[src]["cases"] if k not in out])
            for p, c in list(self.links.values()):
                if c == src:
                    self.links[self._new()] = (p, new)
            return 200, json.dumps([new]).encode()
        if (method, path) == ("PUT", f"{API}/testplan"):
            for x in body:
                self.plans[x["id"]]["folder"] = x["folderId"]
            return 200, b""
        if (method, path) == ("PUT", f"{API}/testrun/bulk/update"):
            for x in body:
                self.cycles[x["id"]]["folder"] = x["folderId"]
            return 200, b""
        m = re.match(rf"{API}/tracelink/(\d+)$", path)
        if method == "DELETE" and m:
            self.links.pop(int(m.group(1)))
            return 200, b""
        m = re.match(rf"{API}/(testplan|testrun)/(\d+)$", path)
        if method == "PUT" and m:
            (self.plans if m.group(1) == "testplan" else self.cycles)[int(m.group(2))]["name"] = body["name"]
            return 200, b""
        raise AssertionError(f"unexpected write {method} {path}")


def _run(z, sel=SEL, confirm=CONFIRM, audit_ok=True):
    events, records = [], []

    def audit(rec):
        records.append(rec)
        return audit_ok if callable(audit_ok) is False else audit_ok(rec)
    res = zu.apply(z.get, z.get, z.send, copy.deepcopy(sel), confirm, audit, events.append, seat="10.0.0.9")
    return res, events, records


def _sel_get(paths=PATHS):
    return FakeZephyr(paths).get


# ------------------------------------------------------------------ the dry run

def test_the_target_folder_is_the_child_naming_the_project_number_or_product():
    t = zu.find_target(PATHS, "5.5.6-2", "Tomahawk", "IE570", "3001")
    assert t["path"] == "/5.5.6-2/Tomahawk/Project 3001: IE570" and t["base_exists"]
    t = zu.find_target(PATHS, "5.5.6-2", "Tomahawk", "IE5", None)      # matches two → none chosen
    assert t["path"] is None and len(t["candidates"]) == 2
    assert zu.find_target(PATHS, "5.5.7", "Tomahawk", "IE570", "3001")["base_exists"] is False


def test_the_call_list_follows_the_measured_order():
    d = zu.preview(_sel_get(), SEL)
    ops = [c["op"] for c in d["calls"]]
    assert ops == ["clone plan", "move plan", "clone cycle", "move cycle", "unlink", "unlink", "unlink",
                   "rename", "rename", "verify", "verify"]
    assert "AWPTCM-C8465" not in " ".join(c["about"] for c in d["calls"] if c["op"] == "clone cycle")   # unticked: not cloned
    assert any("AWPTCM-C8465" in c["path"] for c in d["calls"] if c["op"] == "unlink")              # …but unlinked
    renames = [c["body"]["name"] for c in d["calls"] if c["op"] == "rename"]
    assert renames == ["IE570: Bootloader Tests (Ask-CK)", "IE570: Bootloader Tests (Manual) (Ask-CK)"]
    assert d["targets"]["testplan"]["path"] == "/5.5.6-2/Tomahawk/Project 3001: IE570" and d["problems"] == []


def test_every_call_is_known_and_carries_the_captured_request():
    d = zu.preview(_sel_get(), SEL)
    assert all(c["known"] for c in d["calls"])
    by = {c["op"]: c for c in d["calls"]}
    assert (by["clone plan"]["method"], by["clone plan"]["path"]) == ("POST", f"{API}/testplan/bulk/clone")
    assert by["clone plan"]["body"] == {"projectId": 15310, "sourceIdList": [3256]}           # the template's id
    assert by["clone cycle"]["body"] == {"projectId": 15310, "sourceIdList": [8459],
                                         "tql": "testRun.projectId IN (15310) AND testCase.key NOT IN ('AWPTCM-T1')"}
    plan_dir, cycle_dir = d["targets"]["testplan"]["id"], d["targets"]["testrun"]["id"]
    assert isinstance(plan_dir, int) and isinstance(cycle_dir, int)
    assert (by["move plan"]["method"], by["move plan"]["path"]) == ("PUT", f"{API}/testplan")
    assert by["move plan"]["body"][0]["folderId"] == plan_dir                                 # a folder ID, not a path
    assert (by["move cycle"]["method"], by["move cycle"]["path"]) == ("PUT", f"{API}/testrun/bulk/update")
    assert by["move cycle"]["body"][0]["folderId"] == cycle_dir
    assert "remove case" not in by                                                           # P1: left out at the clone
    assert d["counts"] == {"plans": 1, "skipped": 0, "cycles": 1, "calls": 11, "writes": 9}


def test_the_clone_filter_leaves_out_unticked_cases_and_refuses_anything_but_case_keys():
    assert zu.clone_tql([]) == "testRun.projectId IN (15310)"
    assert zu.clone_tql(["AWPTCM-T1", "AWPTCM-T22"]) == \
        "testRun.projectId IN (15310) AND testCase.key NOT IN ('AWPTCM-T1','AWPTCM-T22')"
    for bad in (["AWPTCM-T1') OR ('x"], ["AWPTCM-C8459"], [""]):
        with pytest.raises(ValueError):
            zu.clone_tql(bad)


def test_the_remove_case_fallback_is_the_captured_body():
    assert zu.remove_case_body(54276, [997176, 997178], [997174]) == {
        "testRunId": 54276, "addedTestRunItems": [], "updatedTestRunItems": [],
        "updatedTestRunItemsIndexes": [{"id": 997176, "index": 0}, {"id": 997178, "index": 1}],
        "deletedTestRunItems": [{"id": 997174}], "autoReorder": False}


def test_the_new_cycle_is_unlinked_from_every_plan_but_its_own_and_checked_from_its_side():
    d = zu.preview(_sel_get(), SEL)
    unlink = [c for c in d["calls"] if c["op"] == "unlink" and "new cycle from AWPTCM-C8459" in c["path"]]
    assert len(unlink) == 1 and "not to <new plan from AWPTCM-P3256>" in unlink[0]["path"]
    assert "archived" in unlink[0]["about"]
    verify = [c["path"] for c in d["calls"] if c["op"] == "verify"]
    assert any(p.startswith(f"{API}/testrun/<id of new cycle from AWPTCM-C8459>") for p in verify)


def test_the_page_sees_every_folder_naming_the_project_in_any_version():
    """P6: a delayed project may carry an old version — show where else it has folders."""
    d = zu.preview(_sel_get(), SEL)
    seen = {(f["kind"], f["path"]) for f in d["project_folders"]}
    assert ("testplan", "/5.5.6-1/Tomahawk/Project 3001: IE570 (old)") in seen
    assert ("testrun", "/5.5.6-2/Tomahawk/Project 3001: IE570") in seen
    assert {f["version"] for f in d["project_folders"]} == {"5.5.6-1", "5.5.6-2"}
    assert not any("IE520" in f["path"] for f in d["project_folders"])


def test_a_family_already_in_the_project_folder_is_skipped():
    z = FakeZephyr()
    z.plans[777] = {"key": "AWPTCM-P777", "name": "IE570: Bootloader Tests (Ask-CK)",
                    "folder": _folder_id(PATHS, "/5.5.6-2/Tomahawk/Project 3001: IE570"), "archived": False}
    d = zu.preview(z.get, SEL)
    assert d["duplicates"] == [{"key": "AWPTCM-P3256", "name": "IE570: Bootloader Tests (Ask-CK)"}]
    assert d["calls"] == [] and d["counts"]["skipped"] == 1


def test_a_missing_project_folder_is_a_problem_not_a_guess():
    d = zu.preview(_sel_get(["/5.5.6-2", "/5.5.6-2/Tomahawk", "/Platform Testing", "/Platform Testing/TEMPLATES"]), SEL)
    assert any("create it first" in p for p in d["problems"])
    assert d["targets"]["testplan"]["path"] is None
    assert any("<plan folder not found>" in c["about"] for c in d["calls"] if c["op"] == "move plan")


def test_the_dry_run_only_reads():
    z = FakeZephyr()
    zu.preview(z.get, SEL)
    assert z.writes == []
    src = TOOL.read_text(encoding="utf-8")
    assert src.count("urlopen(") == 1                       # one transport, `_request`, used only by --apply
    assert "def preview(get: Get, sel: dict)" in src        # the preview is never handed a writer


# ------------------------------------------------------------------ the real upload

def test_an_upload_clones_moves_unlinks_renames_and_verifies():
    z = FakeZephyr()
    res, events, records = _run(z)
    assert res["outcome"] == "done", res
    new_plan = next(i for i, p in z.plans.items() if p["name"] == "IE570: Bootloader Tests (Ask-CK)")
    new_cycle = next(i for i, c in z.cycles.items() if c["name"] == "IE570: Bootloader Tests (Manual) (Ask-CK)")
    assert z.plans[new_plan]["folder"] == _folder_id(PATHS, "/5.5.6-2/Tomahawk/Project 3001: IE570")
    assert z.cycles[new_cycle]["folder"] == _folder_id(PATHS, "/5.5.6-2/Tomahawk/Project 3001: IE570")
    assert z.cycles[new_cycle]["cases"] == ["AWPTCM-T2", "AWPTCM-T3"]                 # T1 left out at the clone
    assert sorted(z.links.values()) == sorted([(3256, 8459), (3256, 8465), (new_plan, new_cycle)])
    assert z.cycles[8459]["cases"] == ["AWPTCM-T1", "AWPTCM-T2", "AWPTCM-T3"]           # the template untouched
    assert [r["event"] for r in records][0] == "start" and records[-1] == dict(records[-1], event="end", outcome="done")
    assert res["done"] == ["AWPTCM-P3256"] and events[-1] is res


def test_an_archived_clone_of_the_template_is_cut_off_from_the_new_cycle():
    """§6a: P3264 — an archived plan still linked to the template cycle pulls every clone into it."""
    z = FakeZephyr()
    z.plans[3264] = {"key": "AWPTCM-P3264", "name": "Bootloader Tests (cloned)", "folder": 1, "archived": True}
    z.links[3] = (3264, 8459)
    res, _, _ = _run(z)
    assert res["outcome"] == "done"
    new_cycle = next(i for i, c in z.cycles.items() if c["name"].startswith("IE570: "))
    assert 3264 not in [p for p, c in z.links.values() if c == new_cycle]
    assert (3264, 8459) in z.links.values()                                          # the template's own link: not ours to touch


def test_every_write_has_an_audit_line_before_it():
    z = FakeZephyr()
    _, _, records = _run(z)
    writes = [r for r in records if r["event"] == "write"]
    assert len(writes) == len(z.writes) and [(w["method"], w["path"]) for w in writes] == [(m, p) for m, p, _ in z.writes]


def test_a_write_whose_audit_line_fails_is_not_sent():
    z = FakeZephyr()
    res, _, _ = _run(z, audit_ok=lambda rec: rec["event"] != "write" or rec["op"] != "move plan")
    assert res["outcome"] == "stopped" and "audit" in res["error"]
    assert [m + " " + p for m, p, _ in z.writes] == [f"POST {API}/testplan/bulk/clone"]   # the move was never sent


def test_no_audit_log_means_nothing_is_written():
    z = FakeZephyr()
    res, _, _ = _run(z, audit_ok=lambda rec: False)
    assert res["outcome"] == "refused" and z.writes == []


def test_a_failed_write_stops_the_upload_and_reports_what_exists():
    """D14: stop and report — nothing more is written and nothing is undone."""
    z = FakeZephyr()
    z.fail = (f"PUT {API}/testrun/bulk/update", 500)
    res, _, records = _run(z)
    assert res["outcome"] == "stopped" and res["stopped_at"] == "AWPTCM-P3256" and "500" in res["error"]
    assert [c["kind"] for c in res["created"]] == ["plan", "cycle"]
    assert z.writes[-1][:2] == ("PUT", f"{API}/testrun/bulk/update")                 # nothing after the failure
    assert records[-1]["event"] == "end" and records[-1]["outcome"] == "stopped"


def test_a_clone_holding_the_wrong_cases_stops_before_it_is_moved():
    z = FakeZephyr()
    real = z.send

    def ignores_tql(method, path, body):
        if path.endswith("/testrun/bulk/clone"):
            body = dict(body, tql="testRun.projectId IN (15310)")
        return real(method, path, body)
    res = zu.apply(z.get, z.get, ignores_tql, copy.deepcopy(SEL), CONFIRM, lambda r: True, lambda e: None)
    assert res["outcome"] == "stopped" and "extra ['AWPTCM-T1']" in res["error"]
    assert not any(p.endswith("/testrun/bulk/update") for _, p, _ in z.writes)


def test_the_typed_product_and_version_must_match_the_selection():
    """P6: no URL edit turns a preview into writes — and a stale version is caught by the person."""
    for confirm in ({"product": "IE570", "version": "5.5.6-1"}, {"product": "IE520", "version": "5.5.6-2"},
                    {"product": "", "version": ""}, {}):
        z = FakeZephyr()
        res, _, records = _run(z, confirm=confirm)
        assert res["outcome"] == "refused" and z.writes == [] and records == []


def test_a_selection_with_problems_writes_nothing():
    z = FakeZephyr(["/5.5.6-2", "/5.5.6-2/Tomahawk", "/Platform Testing", "/Platform Testing/TEMPLATES"])
    res, _, _ = _run(z)
    assert res["outcome"] == "refused" and "create it first" in res["error"] and z.writes == []


def test_a_skipped_family_is_reported_and_the_rest_uploads():
    z = FakeZephyr()
    z.plans[777] = {"key": "AWPTCM-P777", "name": "IE570: Bootloader Tests (Ask-CK)",
                    "folder": _folder_id(PATHS, "/5.5.6-2/Tomahawk/Project 3001: IE570"), "archived": False}
    res, events, _ = _run(z)
    assert res["outcome"] == "done" and res["done"] == [] and res["skipped"][0]["key"] == "AWPTCM-P3256"
    assert z.writes == [] and any("skipped" in e.get("msg", "") for e in events)


def test_the_command_line_needs_a_mode(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(SEL)))
    with pytest.raises(SystemExit):
        zu.main([])
    with pytest.raises(SystemExit):
        zu.main(["--dry-run", "--apply"])


def test_the_audit_log_is_not_committed():
    """It records production writes and the whole selection (P3) — it lives with the other audit log."""
    rel = zu.AUDIT_LOG.relative_to(ROOT).as_posix()
    assert rel == "ask-ck/db/zt-upload-audit.jsonl"
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "ask-ck/db/*" in ignore and f"!{rel}" not in ignore
