#!/usr/bin/env python3
"""Snapshot the Zephyr TEMPLATE set — plans, the cycles they link, the cases those cycles hold.

Zephyr Templating Tool, step 1 (Terrence, 2026-10-05). The template plans and cycles are authored
in Zephyr (`AWPTCM-P3248` "Port" plan -> `AWPTCM-C8451` "Port" cycle -> the 7 Port cases), and the
UI offers no export for plans or cycles, so this reads them through the public Zephyr Scale API.
The result is destined for a `ck.db` table (Terrence: "ck.db table is a better idea"); ck.db is
written only by the server, so THIS TOOL NEVER WRITES IT — it prints JSON (or writes `--out`), and
the server-side import is a separate step.

READ ONLY: every request is a GET (`_get` refuses anything else). Nothing in Zephyr changes.

Discovery is by FOLDER, never by a key list, so a newly authored family is picked up on the next
run:  plans  = every test plan in --plan-folder
      cycles = every cycle in --cycle-folder, plus any cycle a template plan links from elsewhere
      cases  = every case a template cycle holds (name, folder, status, priority, labels, version)
`problems` lists what a later clone would trip on: a plan linking no cycle, a template cycle no
plan links, a cycle outside the cycle-template folder, a name with stray whitespace, a template
item already assigned to someone (a clone would inherit it), a case the API cannot read.

Usage:
  python3 ask-ck/tools/zt_snapshot.py                 # JSON to stdout
  python3 ask-ck/tools/zt_snapshot.py --out <file>    # JSON to a file (keep it out of the lab tree)
Auth: JIRA_KEY from the environment, else the `JIRA_KEY=` line of the repo's secrets.md (the same
order as `upload_refined.py`). The token is never printed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jira_testlink_access import JIRA_BASE, JIRA_PROJECT_KEY, SSL_CTX  # noqa: E402

PLAN_FOLDER = "/Platform Testing/Test Plan TEMPLATES"
CYCLE_FOLDER = "/Platform Testing/Test Cycle TEMPLATES"
REPO_ROOT = Path(__file__).resolve().parents[2]

# The case fields a template tree needs. The full case (objective, script) is ck.db's
# zephyr_cases; this keeps the snapshot to what the templates THEMSELVES assert.
CASE_FIELDS = ("key", "name", "folder", "status", "priority", "labels", "majorVersion")


def jira_token() -> Optional[str]:
    env = os.environ.get("JIRA_KEY", "").strip()
    if env:
        return env
    secrets = REPO_ROOT / "secrets.md"
    if secrets.is_file():
        for line in secrets.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("JIRA_KEY="):
                return line.split("=", 1)[1].strip() or None
    return None


def _get(path: str, token: str, method: str = "GET"):
    """One read. Refuses any method but GET: this tool must not be able to change Zephyr."""
    if method != "GET":
        raise ValueError("zt_snapshot is read-only")
    req = urllib.request.Request(JIRA_BASE + path, method="GET",
                                 headers={"Authorization": "Bearer " + token,
                                          "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60, context=SSL_CTX) as r:
        return json.loads(r.read() or b"null")


def _search(get: Callable[[str], object], kind: str, folder: str) -> List[dict]:
    q = urllib.parse.quote(f'projectKey = "{JIRA_PROJECT_KEY}" AND folder = "{folder}"')
    out, start = [], 0
    while True:
        page = get(f"/rest/atm/1.0/{kind}/search?query={q}&maxResults=200&startAt={start}") or []
        out.extend(page)
        if len(page) < 200:
            return out
        start += len(page)


def fetch(get: Callable[[str], object], plan_folder: str = PLAN_FOLDER,
          cycle_folder: str = CYCLE_FOLDER) -> Dict[str, dict]:
    """Every raw object the snapshot is built from: {"plans": {key: obj}, "cycles": ..., "cases": ...,
    "unreadable": {key: why}}. `get(path)` returns parsed JSON; injected so tests run offline."""
    raw: Dict[str, dict] = {"plans": {}, "cycles": {}, "cases": {}, "unreadable": {}}
    for p in _search(get, "testplan", plan_folder):
        raw["plans"][p["key"]] = get(f"/rest/atm/1.0/testplan/{p['key']}")
    wanted = [c["key"] for c in _search(get, "testrun", cycle_folder)]
    for p in raw["plans"].values():
        wanted += [r["key"] for r in (p.get("testRuns") or [])]
    for key in dict.fromkeys(wanted):
        raw["cycles"][key] = get(f"/rest/atm/1.0/testrun/{key}")
    case_keys = [i["testCaseKey"] for c in raw["cycles"].values() for i in (c.get("items") or [])
                 if i.get("testCaseKey")]
    for key in dict.fromkeys(case_keys):
        try:
            raw["cases"][key] = get(f"/rest/atm/1.0/testcase/{key}")
        except urllib.error.HTTPError as e:
            raw["unreadable"][key] = f"HTTP {e.code}"
    return raw


def assemble(raw: Dict[str, dict], plan_folder: str = PLAN_FOLDER,
             cycle_folder: str = CYCLE_FOLDER) -> dict:
    """The snapshot: the plan -> cycle -> case tree in Zephyr's own order, plus `problems`."""
    problems: List[str] = []
    linked = set()
    plans = []
    for key, p in sorted(raw["plans"].items()):
        cycles = [r["key"] for r in (p.get("testRuns") or [])]
        linked.update(cycles)
        if not cycles:
            problems.append(f"plan {key} {p.get('name')!r} links no cycle")
        plans.append({"key": key, "name": p.get("name"), "folder": p.get("folder"),
                      "status": p.get("status"), "cycles": cycles})
    cycles = []
    for key, c in sorted(raw["cycles"].items()):
        items = c.get("items") or []
        if key not in linked:
            problems.append(f"cycle {key} {c.get('name')!r} is in the template folder but no template plan links it")
        if c.get("folder") != cycle_folder:
            problems.append(f"cycle {key} {c.get('name')!r} is linked by a template plan but lives in "
                            f"{c.get('folder')!r}, not {cycle_folder!r}")
        for i in items:
            if i.get("assignedTo"):
                problems.append(f"cycle {key} item {i.get('testCaseKey')} is assigned to {i['assignedTo']!r} "
                                f"— a clone would inherit the assignee")
        cycles.append({"key": key, "name": c.get("name"), "folder": c.get("folder"),
                       "status": c.get("status"), "cases": [i.get("testCaseKey") for i in items],
                       "assigned": {i["testCaseKey"]: i["assignedTo"] for i in items if i.get("assignedTo")}})
    cases = [{f: raw["cases"][k].get(f) for f in CASE_FIELDS} for k in sorted(raw["cases"])]
    for kind, rows in (("plan", plans), ("cycle", cycles), ("case", cases)):
        for r in rows:
            n = r.get("name") or ""
            if n != n.strip() or "  " in n:
                problems.append(f"{kind} {r['key']} name {n!r} has stray whitespace")
    for key, why in sorted(raw["unreadable"].items()):
        problems.append(f"case {key} could not be read ({why})")
    return {"captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source": {"jira": JIRA_BASE, "project": JIRA_PROJECT_KEY,
                       "plan_folder": plan_folder, "cycle_folder": cycle_folder},
            "counts": {"plans": len(plans), "cycles": len(cycles), "cases": len(cases)},
            "plans": plans, "cycles": cycles, "cases": cases, "problems": problems}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--plan-folder", default=PLAN_FOLDER)
    ap.add_argument("--cycle-folder", default=CYCLE_FOLDER)
    ap.add_argument("--out", help="write the JSON here instead of stdout")
    a = ap.parse_args(argv)
    token = jira_token()
    if not token:
        print("ERROR: no JIRA_KEY in the environment or secrets.md", file=sys.stderr)
        return 2
    snap = assemble(fetch(lambda path: _get(path, token), a.plan_folder, a.cycle_folder),
                    a.plan_folder, a.cycle_folder)
    text = json.dumps(snap, indent=2, ensure_ascii=False) + "\n"
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    c = snap["counts"]
    print(f"{c['plans']} plan(s), {c['cycles']} cycle(s), {c['cases']} case(s); "
          f"{len(snap['problems'])} problem(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
