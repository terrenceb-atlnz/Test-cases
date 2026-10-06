#!/usr/bin/env python3
"""Zephyr Templating Tool — API Upload (PLAN-zephyr-templating.md D9, D13–D15, §5b, §6, §6a).

Reads a selection (JSON on stdin). `--dry-run` prints, as JSON, the exact list of Zephyr calls an
upload would make; `--apply` makes them. For every selected template plan family, in order:

  1 clone the plan          (lands beside the template; its cycle links come with it — §6)
  2 move it to the project's plan folder
  3 clone each selected cycle, leaving its unticked cases out with the clone's `tql` (§5b P1); the
    clone joins EVERY plan the template cycle is in (§6a); its cases are checked against the ticks
  4 move each clone to the project's cycle folder
  5 unlink every template cycle from the new plan
  6 unlink every new cycle from every plan but the new one (read from the CYCLE side, §6a)
  7 rename the new plan and cycles  `<product>: <template name> (Ask-CK)`
  8 read both ends of every link back — the plan side AND the cycle side

Every request is KNOWN (§6a). All are sent with the `jira-project-id` header.

Before any write, everything is read: the target folders and their ids, every folder naming the
project in ANY version (§5b P6 — a delayed project may carry an old version), the template ids,
and the plans already in the target folder — a family whose new plan name is already there is
SKIPPED (D15). `--apply` refuses unless `--confirm-product` and `--confirm-version` equal the
selection's (P6), and writes an audit line to ask-ck/db/zt-upload-audit.jsonl before every write:
a write whose audit line cannot be written is not sent (P3). The first failed write or check
STOPS the upload and reports what was created (D14) — nothing is undone.

`--apply` prints one JSON object per line as it goes (`{"type": "step", ...}`) and a last line
`{"type": "result", ...}` (§5b P4). Auth: JIRA_KEY like zt_snapshot.py (D13); never printed.

Usage:  python3 ask-ck/tools/zt_upload.py --dry-run < selection.json
        python3 ask-ck/tools/zt_upload.py --apply --confirm-product IE570 --confirm-version 5.5.6-2 \\
            [--seat 10.33.22.18] < selection.json
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import zt_snapshot as zs  # noqa: E402
from jira_testlink_access import JIRA_BASE, JIRA_PROJECT_ID, SSL_CTX  # noqa: E402

API = "/rest/tests/1.0"
AUDIT_LOG = Path(__file__).resolve().parent.parent / "db" / "zt-upload-audit.jsonl"
CASE_KEY = re.compile(r"^[A-Z][A-Z0-9]*-T\d+$")
SLOW_READ_S = 600             # a cycle's links from the cycle side took 26–37 s, once >60 s (§6a)

Get = Callable[[str], object]
Send = Callable[[str, str, object], Tuple[int, bytes]]


def _walk(node: dict, path: str = ""):
    for c in node.get("children") or []:
        p = path + "/" + c["name"]
        yield p, c.get("id")
        yield from _walk(c, p)


def folder_ids(get: Get, kind: str) -> Dict[str, Optional[int]]:
    """Every folder path of `kind` ("testplan" | "testrun") in the project → its numeric id."""
    return dict(_walk(get(f"{API}/project/{JIRA_PROJECT_ID}/foldertree/{kind}") or {}))


def _names_project(path: str, product: Optional[str], number: Optional[str]) -> bool:
    name = path.rsplit("/", 1)[1].lower()
    return bool((number and f"project {number}".lower() in name) or (product and product.lower() in name))


def find_target(paths: List[str], version: str, middle: Optional[str], product: Optional[str],
                number: Optional[str]) -> Dict[str, object]:
    """The project's folder: a direct child of `/<version>/<middle>` (or `/<version>`) whose name
    carries `Project <number>` or the product — D5: the user creates it, the tool only finds it."""
    base = f"/{version}" + (f"/{middle}" if middle else "")
    kids = [p for p in paths if p.startswith(base + "/") and "/" not in p[len(base) + 1:]]
    hits = [p for p in kids if _names_project(p, product, number)]
    return {"base": base, "base_exists": base in paths, "path": hits[0] if len(hits) == 1 else None,
            "candidates": hits if len(hits) != 1 else [], "children": kids}


def project_folders(trees: Dict[str, Dict[str, Optional[int]]], product: Optional[str],
                    number: Optional[str]) -> List[dict]:
    """Every folder, in ANY version, whose name carries the project (§5b P6): a project that slipped
    a release can carry an old version, and this is how the page shows it."""
    return [{"kind": kind, "path": p, "version": p.split("/")[1]}
            for kind, tree in trees.items() for p in tree if _names_project(p, product, number)]


def new_name(product: Optional[str], template_name: str) -> str:
    return f"{product or '<product>'}: {template_name.strip()} (Ask-CK)"


def clone_tql(excluded: List[str]) -> str:
    """The cycle clone's filter: the project, minus the unticked cases (§5b P1, tested §6a)."""
    bad = [k for k in excluded if not CASE_KEY.match(k or "")]
    if bad:
        raise ValueError(f"not test case keys: {bad}")
    tql = f"testRun.projectId IN ({JIRA_PROJECT_ID})"
    if excluded:
        tql += " AND testCase.key NOT IN (" + ",".join(f"'{k}'" for k in excluded) + ")"
    return tql


def remove_case_body(run_id: int, kept_item_ids: List[int], deleted_item_ids: List[int]) -> dict:
    """The UI's remove-case save (§6a), kept as the known fallback to P1 — not used by the upload."""
    return {"testRunId": run_id, "addedTestRunItems": [], "updatedTestRunItems": [],
            "updatedTestRunItemsIndexes": [{"id": i, "index": n} for n, i in enumerate(kept_item_ids)],
            "deletedTestRunItems": [{"id": i} for i in deleted_item_ids], "autoReorder": False}


def _kept(p: dict) -> List[dict]:
    return [c for c in p.get("cycles") or [] if c.get("selected", True)]


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
        kept = _kept(p)
        add("clone plan", "POST", f"{API}/testplan/bulk/clone",
            {"projectId": JIRA_PROJECT_ID, "sourceIdList": [tid(P)]}, True,
            f"{P} {p.get('name', '')} → {newP}; the reply is [<its id>]; it lands in the template folder, "
            f"linked to all {len(p.get('cycles') or [])} template cycle(s)")
        add("move plan", "PUT", f"{API}/testplan", [{"folderId": plan_dir_id, "id": f"<id of {newP}>"}], True,
            f"{newP} → {plan_dir}")
        for c in kept:
            out = c.get("excluded") or []
            add("clone cycle", "POST", f"{API}/testrun/bulk/clone",
                {"projectId": JIRA_PROJECT_ID, "sourceIdList": [tid(c["key"])], "tql": clone_tql(out)}, True,
                f"{c['key']} {c.get('name', '')} → <new cycle from {c['key']}>"
                + (f" WITHOUT {', '.join(out)}" if out else "")
                + f"; the reply is [<its id>]; its cases are checked against the ticks; joins every plan "
                  f"{c['key']} is in ({P}, {newP}, any archived clone)")
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


def preview(get: Get, sel: dict) -> dict:
    """Everything the upload reads before its first write, and the call list. GET only."""
    problems: List[str] = []
    version, middle = sel.get("version"), sel.get("middle")
    product, number = sel.get("product"), sel.get("number")
    if not version:
        problems.append("no AW+ version — the target folder cannot be found")
    if not product:
        problems.append("no product — the new names and the folder match need it")
    trees = {kind: folder_ids(get, kind) for kind in ("testplan", "testrun")}
    targets = {}
    for kind in ("testplan", "testrun"):
        tree = trees[kind]
        t = find_target(list(tree), version or "?", middle, product, number) \
            if version else {"base": None, "base_exists": False, "path": None, "candidates": [], "children": []}
        t["id"] = tree.get(t["path"]) if t["path"] else None
        what = "plan" if kind == "testplan" else "cycle"
        if version and not t["base_exists"]:
            problems.append(f"the {what} folder {t['base']} does not exist in Zephyr")
        elif version and not t["path"]:
            problems.append(f"no single project {what} folder under {t['base']} names project "
                            f"{number} or {product}: {t['candidates'] or 'none'} — create it first (D5)")
        targets[kind] = t
    existing: List[str] = []
    if targets["testplan"]["path"]:
        existing = [p.get("name") or "" for p in zs._search(get, "testplan", targets["testplan"]["path"])]
    duplicates = [{"key": p["key"], "name": new_name(product, p.get("name", ""))}
                  for p in sel.get("plans") or [] if new_name(product, p.get("name", "")) in existing]
    skip = {d["key"] for d in duplicates}
    ids: Dict[str, Optional[int]] = {}
    for p in sel.get("plans") or []:
        if p["key"] in skip:
            continue
        for kind, key in [("testplan", p["key"])] + [("testrun", c["key"]) for c in p.get("cycles") or []]:
            try:
                ids[key] = (get(f"{API}/{kind}/{key}?fields=id,key") or {}).get("id")
            except Exception as e:                      # noqa: BLE001 — reported, not fatal
                ids[key] = None
                problems.append(f"could not read {key}'s id ({e})")
    todo = dict(sel, plans=[p for p in sel.get("plans") or [] if p["key"] not in skip])
    try:
        calls = plan_calls(todo, ids, targets)
    except ValueError as e:
        problems.append(str(e))
        calls = []
    return {"dry_run": True,
            "targets": {k: {x: v[x] for x in ("base", "path", "id", "candidates")} for k, v in targets.items()},
            "project_folders": project_folders(trees, product, number),
            "duplicates": duplicates, "ids": ids, "calls": calls,
            "counts": {"plans": len(todo["plans"]), "skipped": len(duplicates),
                       "cycles": sum(len(_kept(p)) for p in todo["plans"]),
                       "calls": len(calls), "writes": sum(1 for c in calls if c["op"] != "verify")},
            "problems": problems}


# --------------------------------------------------------------------------- the real upload (§5b)

class Stop(Exception):
    """The first failed write or check: the upload stops here and reports (D14)."""


def _items(get: Get, run_id: int) -> List[str]:
    d = get(f"{API}/testrun/{run_id}/testrunitems?fields=id,index,testCaseId") or {}
    if d.get("testRunItemsWithNoPermission"):
        raise Stop(f"cycle {run_id} has items this token cannot see — its cases cannot be checked")
    return sorted(((i.get("$lastTestResult") or {}).get("testCase") or {}).get("key") or "?"
                  for i in d.get("testRunItems") or [])


def _plan_links(get: Get, plan_id: int) -> Dict[int, int]:
    """A plan's links, plan side: link id → cycle id."""
    tl = (get(f"{API}/testplan/{plan_id}?fields=id,traceLinks") or {}).get("traceLinks") or []
    return {l["id"]: (l.get("testRun") or {}).get("id") for l in tl}


def _cycle_links(get_slow: Get, run_id: int) -> Dict[int, int]:
    """A cycle's links, CYCLE side (the only side that shows archived plans, §6a): link id → plan id."""
    tl = (get_slow(f"{API}/testrun/{run_id}?fields=id,traceLinks") or {}).get("traceLinks") or []
    return {l["id"]: (l.get("testPlan") or {}).get("id") for l in tl}


def apply(get: Get, get_slow: Get, send: Send, sel: dict, confirm: dict,
          audit: Callable[[dict], bool], emit: Callable[[dict], None], seat: Optional[str] = None) -> dict:
    """The real upload. `get` and `get_slow` read, `send` writes, `audit` appends one record and says
    whether it was written, `emit` reports progress. Returns the result (also emitted last)."""
    created: List[dict] = []
    done: List[str] = []
    result = {"type": "result", "outcome": None, "created": created, "done": done, "skipped": [],
              "stopped_at": None, "error": None, "problems": []}

    def finish(outcome: str, **kw) -> dict:
        result.update(outcome=outcome, **kw)
        audit({"event": "end", "outcome": outcome, "created": created, "error": result["error"]})
        emit(result)
        return result

    if (confirm.get("product") or "").strip() != (sel.get("product") or "") \
            or (confirm.get("version") or "").strip() != (sel.get("version") or "") or not sel.get("product"):
        result.update(outcome="refused", error="the typed product and version must equal the selection's (P6)")
        emit(result)
        return result
    pre = preview(get, sel)
    result["skipped"] = pre["duplicates"]
    if pre["problems"]:
        result.update(outcome="refused", problems=pre["problems"], error="nothing was written: " + "; ".join(pre["problems"]))
        emit(result)
        return result
    if not audit({"event": "start", "seat": seat, "version": sel.get("version"), "product": sel.get("product"),
                  "targets": pre["targets"], "skipped": pre["duplicates"], "selection": sel}):
        result.update(outcome="refused", error=f"the audit log {AUDIT_LOG} cannot be written — nothing was sent")
        emit(result)
        return result
    plan_dir, cycle_dir = pre["targets"]["testplan"]["id"], pre["targets"]["testrun"]["id"]
    ids, product = pre["ids"], sel.get("product")
    skip = {d["key"] for d in pre["duplicates"]}

    def step(msg: str, **kw) -> None:
        emit(dict({"type": "step", "msg": msg}, **kw))

    def write(op: str, method: str, path: str, body=None):
        if not audit({"event": "write", "op": op, "method": method, "path": path, "body": body}):
            raise Stop(f"the audit line for {op} could not be written, so it was not sent")
        status, raw = send(method, path, body)
        audit({"event": "reply", "op": op, "path": path, "status": status})
        step(f"{op}: {method} {path} → {status}", op=op, status=status)
        if status != 200:
            raise Stop(f"{op} {method} {path} answered {status}: {raw[:300].decode('utf-8', 'replace')}")
        return json.loads(raw) if raw.strip() else None

    family = None
    try:
        for p in sel.get("plans") or []:
            if p["key"] in skip:
                step(f"{p['key']} skipped — {new_name(product, p.get('name', ''))} is already in the project folder (D15)")
                continue
            family = p["key"]
            kept = _kept(p)
            step(f"{p['key']} {p.get('name', '')}: {len(kept)} cycle(s)", family=family)
            new_pid = write("clone plan", "POST", f"{API}/testplan/bulk/clone",
                            {"projectId": JIRA_PROJECT_ID, "sourceIdList": [ids[p["key"]]]})[0]
            created.append({"kind": "plan", "id": new_pid, "from": p["key"]})
            write("move plan", "PUT", f"{API}/testplan", [{"folderId": plan_dir, "id": new_pid}])
            new_cycles: Dict[str, int] = {}
            for c in kept:
                out = c.get("excluded") or []
                cid = write("clone cycle", "POST", f"{API}/testrun/bulk/clone",
                            {"projectId": JIRA_PROJECT_ID, "sourceIdList": [ids[c["key"]]], "tql": clone_tql(out)})[0]
                created.append({"kind": "cycle", "id": cid, "from": c["key"]})
                new_cycles[c["key"]] = cid
                want = sorted(set(_items(get, ids[c["key"]])) - set(out))
                got = _items(get, cid)
                if got != want:
                    raise Stop(f"the clone of {c['key']} holds {len(got)} case(s), not the {len(want)} ticked: "
                               f"missing {sorted(set(want) - set(got))}, extra {sorted(set(got) - set(want))}")
                step(f"clone of {c['key']}: {len(got)} case(s), as ticked")
                write("move cycle", "PUT", f"{API}/testrun/bulk/update", [{"folderId": cycle_dir, "id": cid}])
            mine = set(new_cycles.values())
            for link, run in _plan_links(get, new_pid).items():
                if run not in mine:
                    write("unlink", "DELETE", f"{API}/tracelink/{link}")
            for ckey, cid in new_cycles.items():
                for link, plan in _cycle_links(get_slow, cid).items():
                    if plan != new_pid:
                        write("unlink", "DELETE", f"{API}/tracelink/{link}")
            write("rename", "PUT", f"{API}/testplan/{new_pid}",
                  {"id": new_pid, "name": new_name(product, p.get("name", "")), "projectId": JIRA_PROJECT_ID})
            for c in kept:
                cid = new_cycles[c["key"]]
                write("rename", "PUT", f"{API}/testrun/{cid}",
                      {"id": cid, "name": new_name(product, c.get("name", "")), "projectId": JIRA_PROJECT_ID})
            if set(_plan_links(get, new_pid).values()) != mine:
                raise Stop(f"verify: the new plan {new_pid} does not link exactly its new cycles")
            for ckey, cid in new_cycles.items():
                if set(_cycle_links(get_slow, cid).values()) != {new_pid}:
                    raise Stop(f"verify: the new cycle {cid} (from {ckey}) does not link only the new plan")
            if set(_plan_links(get, ids[p["key"]]).values()) & mine:
                raise Stop(f"verify: template plan {p['key']} still links a new cycle")
            keys = {"plan": get(f"{API}/testplan/{new_pid}?fields=id,key").get("key"),
                    "cycles": [get(f"{API}/testrun/{cid}?fields=id,key").get("key") for cid in new_cycles.values()]}
            audit({"event": "family", "from": p["key"], "new": keys})
            step(f"{p['key']} done: {keys['plan']} → {', '.join(keys['cycles'])}", family=family, new=keys)
            done.append(p["key"])
        return finish("done")
    except Stop as e:
        return finish("stopped", stopped_at=family, error=str(e))
    except Exception as e:                                  # noqa: BLE001 — a crash is a stop too (D14)
        return finish("stopped", stopped_at=family, error=f"{type(e).__name__}: {e}")


# --------------------------------------------------------------------------- the Jira transport

def _request(token: str, method: str, path: str, body=None, timeout: int = 60) -> Tuple[int, bytes]:
    data = json.dumps(body, separators=(",", ":")).encode() if body is not None else None
    req = urllib.request.Request(JIRA_BASE + path, data=data, method=method,
                                 headers={"Authorization": "Bearer " + token, "Accept": "application/json",
                                          "Content-Type": "application/json",
                                          "jira-project-id": str(JIRA_PROJECT_ID)})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


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
    ap.add_argument("--confirm-product", default="", help="--apply: must equal the selection's product")
    ap.add_argument("--confirm-version", default="", help="--apply: must equal the selection's version")
    ap.add_argument("--seat", default=None, help="--apply: who pressed the button, for the audit line")
    a = ap.parse_args(argv)
    token = zs.jira_token()
    if not token:
        print("ERROR: no JIRA_KEY in the environment or secrets.md", file=sys.stderr)
        return 2
    sel = json.load(sys.stdin)

    def get(path):
        return zs._get(path, token)

    if a.dry_run:
        out = preview(get, sel)
        sys.stdout.write(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
        c = out["counts"]
        print(f"{c['plans']} plan(s), {c['cycles']} cycle(s), {c['skipped']} skipped: {c['calls']} call(s); "
              f"{len(out['problems'])} problem(s)", file=sys.stderr)
        return 0

    def get_slow(path):
        status, raw = _request(token, "GET", path, timeout=SLOW_READ_S)
        if status != 200:
            raise Stop(f"GET {path} answered {status}")
        return json.loads(raw)

    def emit(rec):
        sys.stdout.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
        sys.stdout.flush()

    res = apply(get, get_slow, lambda m, p, b: _request(token, m, p, b), sel,
                {"product": a.confirm_product, "version": a.confirm_version},
                _audit_to(AUDIT_LOG), emit, seat=a.seat)
    return 0 if res["outcome"] == "done" else 1


if __name__ == "__main__":
    sys.exit(main())
