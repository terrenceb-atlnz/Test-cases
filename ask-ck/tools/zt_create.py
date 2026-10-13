#!/usr/bin/env python3
"""Zephyr — create NEW test cases, one test plan and one test cycle from a draft JSON file.

The other Zephyr writers change what exists: `upload_refined.py` updates existing cases and
`zt_upload.py` clones template plans and cycles. This one creates a feature's authored set from
scratch (first used for Project 3301 FRER, 2026-10-14). The draft file is

    {"testPlan":  {"name", "folder", "status", "objective"?, "labels"?},
     "testCycle": {"name", "folder", "status", "description"?, "items"?: [draftId, ...]},
     "testCases": [{"draftId"?, "name", "folder", "status", "priority", "labels"?, "objective",
                    "precondition"?, "testScript": {"type": "STEP_BY_STEP", "steps": [...]}}]}

`--dry-run` reads only and prints, as JSON, every call an apply would make. `--apply` makes them,
in this order: missing case folders (parent first), the cases, the plan, then the cycle, which is
created linked to the plan with the cases as its items (in `testCycle.items` order when given).

Safety, as zt_upload.py (PLAN-zephyr-templating §5b):
  - everything is read before any write: the three folder trees and the names already in every
    target folder;
  - the plan and cycle folders must already exist (D5: the user creates them). A missing case
    folder is created only beneath an existing folder at least three levels deep
    (`/<version>/<team>/<folder>`), so a typo cannot create a new version or team folder;
  - a case or plan whose name already exists in its target folder is REUSED, not created again,
    so a run that stopped part-way can be re-run; a cycle that already exists stops the run;
  - `--apply` refuses unless `--confirm-plan-folder` and `--confirm-cases` equal the draft's;
  - an audit line goes to ask-ck/db/zt-create-audit.jsonl (gitignored) before every write, and a
    write whose audit line cannot be written is not sent;
  - the first failed write stops the run and reports what was created; nothing is undone;
  - everything created or reused is read back and compared with the draft.

Auth: JIRA_KEY like zt_snapshot.py; never printed.

Usage:  python3 ask-ck/tools/zt_create.py --dry-run DRAFT.json
        python3 ask-ck/tools/zt_create.py --apply DRAFT.json \\
            --confirm-plan-folder "/5.5.6-2/Tomahawk/Project 3301: FRER" --confirm-cases 43
"""
from __future__ import annotations

import argparse
import datetime as _dt
import html
import json
import re
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import zt_snapshot as zs  # noqa: E402
from jira_testlink_access import JIRA_PROJECT_KEY  # noqa: E402
from zt_upload import _request, folder_ids  # noqa: E402

ATM = "/rest/atm/1.0"
AUDIT = Path(__file__).resolve().parent.parent / "db" / "zt-create-audit.jsonl"
MIN_EXISTING_DEPTH = 3  # a created folder's nearest existing ancestor: /<version>/<team>/<folder>

Get = Callable[[str], object]
Send = Callable[[str, str, Optional[dict]], Tuple[int, bytes]]


class Stop(Exception):
    """The run cannot go on; the message says why."""


# --------------------------------------------------------------------------- the draft

def validate(draft: dict) -> List[str]:
    """Problems with the draft itself, before anything is read from Zephyr."""
    out: List[str] = []
    plan, cycle, cases = draft.get("testPlan"), draft.get("testCycle"), draft.get("testCases")
    for label, obj in (("testPlan", plan), ("testCycle", cycle)):
        if not isinstance(obj, dict):
            out.append(f"{label} is missing")
            continue
        for k in ("name", "folder", "status"):
            if not str(obj.get(k) or "").strip():
                out.append(f"{label} has no {k}")
    if not isinstance(cases, list) or not cases:
        return out + ["testCases is missing or empty"]
    seen, ids = set(), set()
    for i, c in enumerate(cases):
        tag = f"testCases[{i}] {c.get('name')!r}"
        for k in ("name", "folder", "status", "priority", "objective"):
            if not str(c.get(k) or "").strip():
                out.append(f"{tag} has no {k}")
        if not str(c.get("folder") or "").startswith("/"):
            out.append(f"{tag}: folder must be an absolute path")
        ts = c.get("testScript") or {}
        if ts.get("type") != "STEP_BY_STEP" or not isinstance(ts.get("steps"), list) or not ts["steps"]:
            out.append(f"{tag}: testScript must be STEP_BY_STEP with at least one step")
        key = (c.get("folder"), c.get("name"))
        if key in seen:
            out.append(f"{tag}: the same name twice in one folder")
        seen.add(key)
        if c.get("draftId"):
            ids.add(c["draftId"])
    items = (cycle or {}).get("items")
    if items is not None:
        missing = [d for d in items if d not in ids]
        if missing:
            out.append(f"testCycle.items names draft ids that are not cases: {missing}")
        if len(set(items)) != len(items):
            out.append("testCycle.items repeats a draft id")
    return out


def _cycle_order(draft: dict) -> List[int]:
    """Case indexes in cycle order: testCycle.items when given, else the draft's order."""
    items = draft["testCycle"].get("items")
    if items is None:
        return list(range(len(draft["testCases"])))
    pos = {c.get("draftId"): i for i, c in enumerate(draft["testCases"])}
    return [pos[d] for d in items]


def case_body(c: dict) -> dict:
    body = {"projectKey": JIRA_PROJECT_KEY, "name": c["name"], "folder": c["folder"],
            "status": c["status"], "priority": c["priority"], "labels": list(c.get("labels") or []),
            "objective": c["objective"],
            "testScript": {"type": "STEP_BY_STEP",
                           "steps": [{"description": s.get("description", ""),
                                      "expectedResult": s.get("expectedResult", "")}
                                     for s in c["testScript"]["steps"]]}}
    if c.get("precondition"):
        body["precondition"] = c["precondition"]
    return body


def plan_body(p: dict) -> dict:
    body = {"projectKey": JIRA_PROJECT_KEY, "name": p["name"], "folder": p["folder"], "status": p["status"]}
    for k in ("objective", "labels"):
        if p.get(k):
            body[k] = p[k]
    return body


def cycle_body(cy: dict, plan_key: str, case_keys: List[str]) -> dict:
    body = {"projectKey": JIRA_PROJECT_KEY, "name": cy["name"], "folder": cy["folder"],
            "status": cy["status"], "testPlanKey": plan_key,
            "items": [{"testCaseKey": k} for k in case_keys]}
    if cy.get("description"):
        body["description"] = cy["description"]
    return body


# --------------------------------------------------------------------------- pre-flight (reads only)

def _ancestors(path: str) -> List[str]:
    parts = path.strip("/").split("/")
    return ["/" + "/".join(parts[:i]) for i in range(1, len(parts))]


def _names_in(get: Get, kind: str, folder: str) -> Dict[str, str]:
    """name -> key of the `kind` objects directly in `folder`."""
    return {r["name"]: r["key"] for r in zs._search(get, kind, folder)}


def preview(get: Get, draft: dict) -> dict:
    """Every read, then the calls an apply would make. Never writes."""
    problems = validate(draft)
    if problems:
        return {"problems": problems, "calls": [], "reuse": {}, "counts": {}}
    plan, cycle, cases = draft["testPlan"], draft["testCycle"], draft["testCases"]
    trees = {k: folder_ids(get, k) for k in ("testcase", "testplan", "testrun")}
    for label, kind, folder in (("plan", "testplan", plan["folder"]), ("cycle", "testrun", cycle["folder"])):
        if folder not in trees[kind]:
            problems.append(f"the {label} folder {folder!r} does not exist (create it in Zephyr first)")

    new_folders: List[str] = []
    for folder in sorted({c["folder"] for c in cases}):
        if folder in trees["testcase"]:
            continue
        chain = _ancestors(folder) + [folder]
        existing = [a for a in chain if a in trees["testcase"]]
        anchor = existing[-1] if existing else None
        if anchor is None or anchor.count("/") < MIN_EXISTING_DEPTH:
            problems.append(f"case folder {folder!r}: its nearest existing folder is {anchor!r}, which is "
                            f"too shallow to create beneath (create the parent in Zephyr first)")
            continue
        for a in chain[chain.index(anchor) + 1:]:
            if a not in new_folders:
                new_folders.append(a)

    reuse: Dict[str, str] = {}
    existing_cases: Dict[str, Dict[str, str]] = {}
    for folder in sorted({c["folder"] for c in cases} - set(new_folders)):
        existing_cases[folder] = _names_in(get, "testcase", folder)
    plan_key = None
    if not problems:
        plan_key = _names_in(get, "testplan", plan["folder"]).get(plan["name"])
        if _names_in(get, "testrun", cycle["folder"]).get(cycle["name"]):
            problems.append(f"a cycle named {cycle['name']!r} already exists in {cycle['folder']!r}")

    calls: List[dict] = []
    for f in new_folders:
        calls.append({"op": "folder", "method": "POST", "path": f"{ATM}/folder",
                      "body": {"projectKey": JIRA_PROJECT_KEY, "name": f, "type": "TEST_CASE"}})
    for i, c in enumerate(cases):
        key = existing_cases.get(c["folder"], {}).get(c["name"])
        if key:
            reuse[f"case:{i}"] = key
        else:
            calls.append({"op": "case", "index": i, "method": "POST", "path": f"{ATM}/testcase",
                          "body": case_body(c)})
    if plan_key:
        reuse["plan"] = plan_key
    else:
        calls.append({"op": "plan", "method": "POST", "path": f"{ATM}/testplan", "body": plan_body(plan)})
    calls.append({"op": "cycle", "method": "POST", "path": f"{ATM}/testrun",
                  "body": cycle_body(cycle, "<plan key>", [f"<case {i} key>" for i in _cycle_order(draft)])})
    counts = {"folders": len(new_folders), "cases_new": sum(c["op"] == "case" for c in calls),
              "cases_reused": sum(k.startswith("case:") for k in reuse), "plan_new": not plan_key,
              "cycle_items": len(cases), "writes": len(calls)}
    return {"problems": problems, "calls": calls, "reuse": reuse, "counts": counts}


# --------------------------------------------------------------------------- read-back

def _norm(v) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(v or ""))).strip()


def check_case(got: dict, want: dict) -> List[str]:
    """Differences between a case read back from Zephyr and the draft case."""
    out = []
    for k in ("name", "folder", "status", "priority", "objective", "precondition"):
        if _norm(got.get(k)) != _norm(want.get(k)):
            out.append(f"{k} differs")
    if set(got.get("labels") or []) != set(want.get("labels") or []):
        out.append("labels differ")
    gs = sorted((got.get("testScript") or {}).get("steps") or [], key=lambda s: s.get("index", 0))
    ws = want["testScript"]["steps"]
    if [_norm(s.get("description")) for s in gs] != [_norm(s.get("description")) for s in ws]:
        out.append(f"steps differ ({len(gs)} read back, {len(ws)} in the draft)")
    return out


def verify(get: Get, draft: dict, case_keys: List[str], plan_key: str, cycle_key: str) -> List[str]:
    out = []
    for key, c in zip(case_keys, draft["testCases"]):
        out += [f"{key}: {p}" for p in check_case(get(f"{ATM}/testcase/{key}") or {}, c)]
    plan = get(f"{ATM}/testplan/{plan_key}") or {}
    for k in ("name", "folder"):
        if _norm(plan.get(k)) != _norm(draft["testPlan"][k]):
            out.append(f"{plan_key}: plan {k} differs")
    if cycle_key not in {r.get("key") for r in plan.get("testRuns") or []}:
        out.append(f"{plan_key}: the plan does not link {cycle_key}")
    cy = get(f"{ATM}/testrun/{cycle_key}") or {}
    for k in ("name", "folder"):
        if _norm(cy.get(k)) != _norm(draft["testCycle"][k]):
            out.append(f"{cycle_key}: cycle {k} differs")
    want_items = [case_keys[i] for i in _cycle_order(draft)]
    if [i.get("testCaseKey") for i in cy.get("items") or []] != want_items:
        out.append(f"{cycle_key}: the cycle's cases differ from the draft's")
    return out


# --------------------------------------------------------------------------- apply

def _key(raw: bytes) -> Optional[str]:
    try:
        return (json.loads(raw or b"null") or {}).get("key")
    except ValueError:
        return None


def apply(get: Get, send: Send, audit: Callable[[dict], bool], draft: dict, emit: Callable[[dict], None],
          confirm_plan_folder: str, confirm_cases: int) -> dict:
    """Make the writes. Returns {outcome, created, reused, problems}; never undoes anything."""
    if confirm_plan_folder != draft.get("testPlan", {}).get("folder") or confirm_cases != len(draft.get("testCases") or []):
        raise Stop("--confirm-plan-folder and --confirm-cases must equal the draft's plan folder and case count")
    pre = preview(get, draft)
    if pre["problems"]:
        raise Stop("pre-flight: " + "; ".join(pre["problems"]))
    created: Dict[str, str] = {}
    case_keys: List[Optional[str]] = [None] * len(draft["testCases"])
    for k, v in pre["reuse"].items():
        if k.startswith("case:"):
            case_keys[int(k[5:])] = v
    plan_key = pre["reuse"].get("plan")
    if not audit({"event": "start", "plan": draft["testPlan"]["name"], "counts": pre["counts"]}):
        raise Stop("the audit log cannot be written; nothing was sent")

    def write(call: dict) -> bytes:
        if not audit({"event": "write", "op": call["op"], "method": call["method"], "path": call["path"],
                      "body": call["body"]}):
            raise Stop(f"the audit log cannot be written; {call['op']} was not sent")
        status, raw = send(call["method"], call["path"], call["body"])
        audit({"event": "status", "op": call["op"], "status": status})
        if status not in (200, 201):
            raise Stop(f"{call['op']} {call['path']} answered {status}: {raw[:300]!r}")
        return raw

    outcome, problems = "done", []
    try:
        for call in pre["calls"]:
            if call["op"] == "cycle":
                call = dict(call, body=cycle_body(draft["testCycle"], plan_key,
                                                  [case_keys[i] for i in _cycle_order(draft)]))
            raw = write(call)
            if call["op"] == "folder":
                emit({"type": "step", "op": "folder", "name": call["body"]["name"]})
                continue
            key = _key(raw)
            if not key:
                raise Stop(f"{call['op']} was created but its key could not be read: {raw[:300]!r}")
            if call["op"] == "case":
                case_keys[call["index"]] = key
                created[draft["testCases"][call["index"]].get("draftId") or f"case {call['index']}"] = key
            elif call["op"] == "plan":
                plan_key = created["plan"] = key
            else:
                created["cycle"] = key
            emit({"type": "step", "op": call["op"], "key": key})
        problems = verify(get, draft, case_keys, plan_key, created["cycle"])
        if problems:
            outcome = "verify-failed"
    except Stop as e:
        outcome, problems = "stopped", [str(e)]
    audit({"event": "end", "outcome": outcome, "created": created, "problems": problems})
    return {"outcome": outcome, "created": created, "reused": pre["reuse"], "problems": problems}


def _audit_to(path: Path) -> Callable[[dict], bool]:
    def audit(rec: dict) -> bool:
        try:
            line = json.dumps(dict({"ts": _dt.datetime.now(_dt.timezone.utc).isoformat()}, **rec), default=str)
            with open(path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
            return True
        except OSError:
            return False
    return audit


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="print the call list; reads only")
    mode.add_argument("--apply", action="store_true", help="make the calls (needs both --confirm-*)")
    ap.add_argument("draft", help="the draft JSON file")
    ap.add_argument("--confirm-plan-folder", default="", help="--apply: must equal the draft's plan folder")
    ap.add_argument("--confirm-cases", type=int, default=-1, help="--apply: must equal the draft's case count")
    a = ap.parse_args(argv)
    token = zs.jira_token()
    if not token:
        print("ERROR: no JIRA_KEY in the environment or secrets.md", file=sys.stderr)
        return 2
    draft = json.loads(Path(a.draft).read_text(encoding="utf-8"))

    def get(path):
        return zs._get(path, token)

    if a.dry_run:
        out = preview(get, draft)
        sys.stdout.write(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
        c = out["counts"]
        print(f"{len(out['problems'])} problem(s); " + (", ".join(f"{k} {v}" for k, v in c.items()) if c else ""),
              file=sys.stderr)
        return 1 if out["problems"] else 0

    def send(method, path, body):
        return _request(token, method, path, body)

    def emit(rec):
        print(json.dumps(rec), flush=True)

    try:
        res = apply(get, send, _audit_to(AUDIT), draft, emit, a.confirm_plan_folder, a.confirm_cases)
    except Stop as e:
        emit({"type": "result", "outcome": "refused", "problems": [str(e)]})
        return 1
    emit(dict({"type": "result"}, **res))
    return 0 if res["outcome"] == "done" else 1


if __name__ == "__main__":
    sys.exit(main())
