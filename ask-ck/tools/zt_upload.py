#!/usr/bin/env python3
"""Zephyr Templating Tool — API Upload, DRY RUN ONLY (PLAN-zephyr-templating.md D9, §6, §6a).

Reads a selection (JSON on stdin) and prints, as JSON, the exact list of Zephyr calls a real upload
would make, in order, for every selected template plan and cycle:

  1 clone the plan          (lands beside the template; its cycle links come with it — §6)
  2 move it to the project's plan folder
  3 clone each selected cycle (each clone joins EVERY plan the template cycle is in: the template
                               plan, the new plan, and any archived clone of the template — §6a)
  4 move each clone to the project's cycle folder
  5 unlink every template cycle from the new plan
  6 unlink every new cycle from every plan but the new one
  7 take unticked cases out of the new cycles (one bulk save per cycle, by ITEM id — §6a)
  8 rename the new plan and cycles  `<product>: <template name> (Ask-CK)`
  9 read both ends of every link back — the plan side AND the cycle side (an archived plan is
    visible only from the cycle side)

Every request is KNOWN: unlink and rename were used on IE570 2026-10-05; clone, move and
remove-case were captured from the UI on 2026-10-07 (Factory Tests → IE570). All are sent with the
`jira-project-id` header. Ids that only exist after a clone are shown as such.

READ ONLY: the reads are GETs — the project's folder trees (to find the target folders under
`/<version>/<middle>/` by the project number or product, and their ids) and the templates' numeric
ids. `--apply` is refused: the real upload is not built. Auth: JIRA_KEY like zt_snapshot.py; never
printed.

Usage:  python3 ask-ck/tools/zt_upload.py --dry-run < selection.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import zt_snapshot as zs  # noqa: E402
from jira_testlink_access import JIRA_PROJECT_ID  # noqa: E402

API = "/rest/tests/1.0"


def _walk(node: dict, path: str = ""):
    for c in node.get("children") or []:
        p = path + "/" + c["name"]
        yield p, c.get("id")
        yield from _walk(c, p)


def folder_ids(get: Callable[[str], object], kind: str) -> Dict[str, Optional[int]]:
    """Every folder path of `kind` ("testplan" | "testrun") in the project → its numeric id."""
    return dict(_walk(get(f"{API}/project/{JIRA_PROJECT_ID}/foldertree/{kind}") or {}))



def find_target(paths: List[str], version: str, middle: Optional[str], product: Optional[str],
                number: Optional[str]) -> Dict[str, object]:
    """The project's folder: a direct child of `/<version>/<middle>` (or `/<version>`) whose name
    carries `Project <number>` or the product — D5: the user creates it, the tool only finds it."""
    base = f"/{version}" + (f"/{middle}" if middle else "")
    kids = [p for p in paths if p.startswith(base + "/") and "/" not in p[len(base) + 1:]]
    def fits(p: str) -> bool:
        name = p.rsplit("/", 1)[1].lower()
        return bool((number and f"project {number}".lower() in name) or (product and product.lower() in name))
    hits = [p for p in kids if fits(p)]
    return {"base": base, "base_exists": base in paths, "path": hits[0] if len(hits) == 1 else None,
            "candidates": hits if len(hits) != 1 else [], "children": kids}


def new_name(product: Optional[str], template_name: str) -> str:
    return f"{product or '<product>'}: {template_name.strip()} (Ask-CK)"


def plan_calls(sel: dict, ids: Dict[str, Optional[int]], targets: Dict[str, dict]) -> List[dict]:
    """The ordered call list. Pure: `ids` maps template keys to numeric ids (None if unread)."""
    calls: List[dict] = []
    product = sel.get("product")
    plan_dir = targets["testplan"].get("path") or "<plan folder not found>"
    cycle_dir = targets["testrun"].get("path") or "<cycle folder not found>"
    plan_dir_id = targets["testplan"].get("id") or f"<id of {plan_dir}>"
    cycle_dir_id = targets["testrun"].get("id") or f"<id of {cycle_dir}>"

    def add(op, method, path, body, known, about):
        calls.append({"n": len(calls) + 1, "op": op, "method": method, "path": path, "body": body,
                      "known": known, "about": about})

    def tid(key):
        return ids.get(key) if ids.get(key) is not None else f"<id of {key}>"

    for p in sel.get("plans") or []:
        P, newP = p["key"], f"<new plan from {p['key']}>"
        kept = [c for c in p.get("cycles") or [] if c.get("selected", True)]
        add("clone plan", "POST", f"{API}/testplan/bulk/clone",
            {"projectId": JIRA_PROJECT_ID, "sourceIdList": [tid(P)]}, True,
            f"{P} {p.get('name', '')} → {newP}; the reply is [<its id>]; it lands in the template folder, "
            f"linked to all {len(p.get('cycles') or [])} template cycle(s)")
        add("move plan", "PUT", f"{API}/testplan", [{"folderId": plan_dir_id, "id": f"<id of {newP}>"}], True,
            f"{newP} → {plan_dir}")
        for c in kept:
            add("clone cycle", "POST", f"{API}/testrun/bulk/clone",
                {"projectId": JIRA_PROJECT_ID, "sourceIdList": [tid(c["key"])],
                 "tql": f"testRun.projectId IN ({JIRA_PROJECT_ID})"}, True,
                f"{c['key']} {c.get('name', '')} → <new cycle from {c['key']}>; the reply is [<its id>]; "
                f"same cases, its own items; joins every plan {c['key']} is in ({P}, {newP}, any archived clone)")
            add("move cycle", "PUT", f"{API}/testrun/bulk/update",
                [{"folderId": cycle_dir_id, "id": f"<id of new cycle from {c['key']}>"}], True,
                f"<new cycle from {c['key']}> → {cycle_dir}")
        for c in p.get("cycles") or []:
            add("unlink", "DELETE", f"{API}/tracelink/<id of {newP} ↔ {c['key']}>", None, True,
                f"template cycle {c['key']} off the new plan (link id read after the clone)")
        for c in kept:
            add("unlink", "DELETE", f"{API}/tracelink/<id of each link on new cycle from {c['key']} not to {newP}>",
                None, True,
                f"the new cycle off template plan {P} and off any archived clone of it — read from the "
                f"CYCLE side, where archived plans show (§6a); the template's updatedOn moves (§6)")
        for c in kept:
            out = c.get("excluded") or []
            if out:
                add("remove case", "PUT", f"{API}/testrunitem/bulk/save",
                    {"testRunId": f"<id of new cycle from {c['key']}>", "addedTestRunItems": [],
                     "updatedTestRunItems": [],
                     "updatedTestRunItemsIndexes": "<[{id, index}] of every item kept, re-indexed from 0>",
                     "deletedTestRunItems": [{"id": f"<item id of {t}>"} for t in out], "autoReorder": False},
                    True, f"{', '.join(out)} out of <new cycle from {c['key']}> — ITEM ids, read from "
                          f"GET {API}/testrun/<id>/testrunitems after the clone (the template keeps its own items)")
        add("rename", "PUT", f"{API}/testplan/<id of {newP}>",
            {"id": f"<id of {newP}>", "name": new_name(product, p.get("name", "")), "projectId": JIRA_PROJECT_ID},
            True, f"{newP} (template {P} is id {tid(P)})")
        for c in kept:
            add("rename", "PUT", f"{API}/testrun/<id of new cycle from {c['key']}>",
                {"id": f"<id of new cycle from {c['key']}>", "name": new_name(product, c.get("name", "")),
                 "projectId": JIRA_PROJECT_ID}, True, f"new cycle from {c['key']} (template id {tid(c['key'])})")
        add("verify", "GET", f"{API}/testplan/<id of {newP}>?fields=id,key,traceLinks", None, True,
            f"{newP} links only its new cycles; {P} links only its template cycles")
        for c in kept:
            add("verify", "GET", f"{API}/testrun/<id of new cycle from {c['key']}>?fields=id,traceLinks", None, True,
                f"the new cycle links only {newP} — the cycle side shows archived plans too; slow (~30 s)")
    return calls


def preview(get: Callable[[str], object], sel: dict) -> dict:
    problems: List[str] = []
    version, middle = sel.get("version"), sel.get("middle")
    if not version:
        problems.append("no AW+ version — the target folder cannot be found")
    targets = {}
    for kind in ("testplan", "testrun"):
        tree = folder_ids(get, kind) if version else {}
        t = find_target(list(tree), version or "?", middle, sel.get("product"), sel.get("number")) \
            if version else {"base": None, "base_exists": False, "path": None, "candidates": [], "children": []}
        t["id"] = tree.get(t["path"]) if t["path"] else None
        what = "plan" if kind == "testplan" else "cycle"
        if version and not t["base_exists"]:
            problems.append(f"the {what} folder {t['base']} does not exist in Zephyr")
        elif version and not t["path"]:
            problems.append(f"no single project {what} folder under {t['base']} names project "
                            f"{sel.get('number')} or {sel.get('product')}: "
                            f"{t['candidates'] or 'none'} — create it first (D5)")
        targets[kind] = t
    ids: Dict[str, Optional[int]] = {}
    for p in sel.get("plans") or []:
        for kind, key in [("testplan", p["key"])] + [("testrun", c["key"]) for c in p.get("cycles") or []]:
            try:
                ids[key] = (get(f"{API}/{kind}/{key}?fields=id,key") or {}).get("id")
            except Exception as e:                      # noqa: BLE001 — reported, not fatal
                ids[key] = None
                problems.append(f"could not read {key}'s id ({e})")
    calls = plan_calls(sel, ids, targets)
    known = sum(1 for c in calls if c["known"] and c["op"] != "verify")
    return {"dry_run": True, "targets": {k: {x: v[x] for x in ("base", "path", "id", "candidates")} for k, v in targets.items()},
            "calls": calls,
            "counts": {"plans": len(sel.get("plans") or []),
                       "cycles": sum(1 for p in sel.get("plans") or [] for c in p.get("cycles") or [] if c.get("selected", True)),
                       "calls": len(calls), "writes_known": known,
                       "writes_not_captured": sum(1 for c in calls if not c["known"])},
            "problems": problems}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dry-run", action="store_true", help="print the call list (the only mode)")
    ap.add_argument("--apply", action="store_true", help="refused: the real upload is not built (D9)")
    a = ap.parse_args(argv)
    if a.apply or not a.dry_run:
        print("ERROR: only --dry-run exists; the real upload is not built yet (D9)",
              file=sys.stderr)
        return 2
    token = zs.jira_token()
    if not token:
        print("ERROR: no JIRA_KEY in the environment or secrets.md", file=sys.stderr)
        return 2
    sel = json.load(sys.stdin)
    out = preview(lambda path: zs._get(path, token), sel)
    sys.stdout.write(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    c = out["counts"]
    print(f"{c['plans']} plan(s), {c['cycles']} cycle(s): {c['calls']} call(s), {c['writes_not_captured']} "
          f"not captured yet; {len(out['problems'])} problem(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
