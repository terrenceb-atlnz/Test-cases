"""Test Composer step 1–2 data: projects, variants, the live project tree, templates and what is
runnable on each (ask-ck/plans/PLAN-test-composer.md §2.1–2.2). Reads only: the wiki (GET
action=parse), Zephyr (GET, zt_snapshot's read-only accessor), and this repo's files.

Projects come two ways (Terrence, 2026-10-09 — "backwards-compatible"):
  * **Templated Project** — every family ZTT uploaded, from ask-ck/db/zt-uploads.jsonl (written by
    zt_upload.py since 2026-10-09) and, for uploads before that, rebuilt from the audit log.
  * **Zephyr Project Link** — a project's wiki page. Its "Test Results:" cell is a row of
    `{{Test Status v2|<version>|<project id>}}` calls, one per VARIANT; each renders a status block
    whose report links name the variant's plans (`testPlan.key_IN_('AWPTCM-P2903')`, `title=…`).
    Variants are often different hardware, so the page shows them as a checklist for THIS run.
"""
from __future__ import annotations

import html as _html
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import unquote_plus

from paths import ASKCK_ROOT, DB_DIR

import tc_runs

TOOLS = ASKCK_ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

STATUS_CALL_RE = re.compile(r"\{\{\s*Test Status v2\s*\|\s*([^|}]+?)\s*\|\s*([^|}]+?)\s*\}\}")
PLAN_LINK_RE = re.compile(r"testPlan\.key_IN_\(([^)]*)\)[^\"'\s]*?&title=([^&\"'\s]*)")
KNOWN_STATUS = ("On Target", "At Risk", "Not Started", "In Progress", "Passed", "Tested", "Testing",
                "Complete", "Completed", "Blocked", "Late", "Failed", "Cancelled")


class ProjectError(ValueError):
    pass


def uploads_path() -> Path:
    return Path(os.environ.get("CK_ZT_UPLOADS") or (DB_DIR / "zt-uploads.jsonl"))


def audit_path() -> Path:
    return Path(os.environ.get("CK_ZT_AUDIT") or (DB_DIR / "zt-upload-audit.jsonl"))


# ------------------------------------------------------------------ templated projects

def _from_audit(path: Path) -> List[Dict[str, Any]]:
    """Upload records rebuilt from the audit log (start → family events of one run)."""
    out, sel = [], None
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return out
    for line in lines:
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("event") == "start":
            sel = e.get("selection") if isinstance(e.get("selection"), dict) else None
            if sel is None and isinstance(e.get("selection"), str):
                sel = None
            sel = sel or {"version": e.get("version"), "product": e.get("product")}
        elif e.get("event") == "family" and sel:
            new = e.get("new") or {}
            out.append({"ts": e.get("ts"), "version": sel.get("version"), "middle": sel.get("middle"),
                        "product": sel.get("product"), "number": sel.get("number"),
                        "from_plan": e.get("from"), "plan": new.get("plan"), "cycles": new.get("cycles") or [],
                        "source": "audit"})
    return out


def upload_records() -> List[Dict[str, Any]]:
    recs = []
    try:
        for line in uploads_path().read_text(encoding="utf-8").splitlines():
            try:
                recs.append(json.loads(line))
            except ValueError:
                continue
    except OSError:
        pass
    have = {r.get("plan") for r in recs}
    recs += [r for r in _from_audit(audit_path()) if r.get("plan") not in have]
    return recs


def templated_projects() -> List[Dict[str, Any]]:
    groups: Dict[str, Dict[str, Any]] = {}
    for r in upload_records():
        if not r.get("plan"):
            continue
        pid = f"{r.get('product')}|{r.get('version')}|{r.get('number') or ''}"
        g = groups.setdefault(pid, {"id": pid, "product": r.get("product"), "version": r.get("version"),
                                    "middle": r.get("middle"), "number": r.get("number"), "plans": [],
                                    "last_upload": None})
        if r["plan"] not in g["plans"]:
            g["plans"].append(r["plan"])
        g["last_upload"] = max(filter(None, [g["last_upload"], r.get("ts")]), default=None)
    return sorted(groups.values(), key=lambda g: g["last_upload"] or "", reverse=True)


# ------------------------------------------------------------------ Zephyr Project Link (wiki)

def page_title(url_or_title: str) -> str:
    import zt_wiki  # noqa: PLC0415
    return zt_wiki.page_title(url_or_title)


def status_calls(wikitext: str) -> List[Dict[str, str]]:
    """The `{{Test Status v2|version|id}}` calls of the page's "Test Results:" cell, in order."""
    i = wikitext.find("Test Results")
    scope = wikitext[i:] if i >= 0 else wikitext
    j = scope.find("\n|")              # the cell ends at the next table row/cell
    cell = scope[: j if j > 0 else len(scope)]
    return [{"version": v.strip(), "project": p.strip()} for v, p in STATUS_CALL_RE.findall(cell)]


def parse_status_block(html: str) -> Dict[str, Any]:
    """One rendered `{{Test Status v2}}` → {status, title, plans:[{key, name}]}. The rendered hrefs
    are HTML-escaped (`&#39;`, `&amp;`); the overall link lists every plan, each plan's own link
    carries its name — so names come from the single-plan links, the order from wherever first."""
    html = _html.unescape(html or "")
    order: List[str] = []
    names: Dict[str, str] = {}
    overall = None
    for keys, title in PLAN_LINK_RE.findall(html):
        ks = re.findall(r"AWPTCM-P\d+", keys)
        name = unquote_plus(title)
        for k in ks:
            if k not in order:
                order.append(k)
        if len(ks) == 1:
            names.setdefault(ks[0], name)
        elif len(ks) > 1 and overall is None:
            overall = name
    plans = {k: names.get(k, "") for k in order}
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or ""))
    status = None
    m = re.search(r"TB\s+\w{3}\s+\d{1,2}-\w{3}-\d{4}:", text)
    after = text[m.end():m.end() + 80] if m else text[:200]
    for s in KNOWN_STATUS:
        if re.search(r"\b" + re.escape(s) + r"\b", after):
            status = s
            break
    return {"status": status, "title": overall, "plans": [{"key": k, "name": n} for k, n in plans.items()]}


def from_wiki(url: str, wiki_get: Optional[Callable] = None) -> Dict[str, Any]:
    import zt_wiki  # noqa: PLC0415
    get = wiki_get or zt_wiki._get
    title = zt_wiki.page_title(url)
    page = zt_wiki._parse(get, title)
    if page is None:
        raise ProjectError(f"no wiki page {title!r}")
    wt = page.get("wikitext")
    wt = wt.get("*") if isinstance(wt, dict) else (wt or "")
    calls = status_calls(wt)
    if not calls:
        raise ProjectError("the page has no Test Results cell with {{Test Status v2|…}} entries")
    variants = []
    for c in calls:
        d = get({"action": "parse", "text": f"{{{{Test Status v2|{c['version']}|{c['project']}}}}}",
                 "contentmodel": "wikitext", "prop": "text", "title": title})
        p = d.get("parse") or {}
        html = p.get("text", {}).get("*") if isinstance(p.get("text"), dict) else (p.get("text") or "")
        block = parse_status_block(html)
        variants.append({"version": c["version"], "project": c["project"], **block})
    return {"title": title, "variants": variants}


# ------------------------------------------------------------------ the live project tree (Zephyr GET)

def _zephyr_get() -> Callable[[str], Any]:
    import zt_snapshot  # noqa: PLC0415
    token = zt_snapshot.jira_token()
    if not token:
        raise ProjectError("no JIRA_KEY in the environment or secrets.md — the live tree needs it")
    return lambda path: zt_snapshot._get(path, token)


def live_tree(plan_keys: List[str], get: Optional[Callable[[str], Any]] = None) -> Dict[str, Any]:
    """What is actually IN the project's plans now: plan → cycle → case, GET only."""
    for k in plan_keys:
        if not re.match(r"^AWPTCM-P\d+$", k):
            raise ProjectError(f"bad plan key {k!r}")
    get = get or _zephyr_get()
    plans = []
    case_keys: List[str] = []
    for k in plan_keys:
        p = get(f"/rest/atm/1.0/testplan/{k}") or {}
        cycles = []
        for r in p.get("testRuns") or []:
            c = get(f"/rest/atm/1.0/testrun/{r['key']}") or {}
            keys = [i.get("testCaseKey") for i in c.get("items") or [] if i.get("testCaseKey")]
            case_keys += keys
            cycles.append({"key": r["key"], "name": c.get("name"), "cases": [{"key": x} for x in keys]})
        plans.append({"key": k, "name": p.get("name"), "folder": p.get("folder"), "cycles": cycles})
    names: Dict[str, Dict[str, Any]] = {}

    def one(key):
        try:
            c = get(f"/rest/atm/1.0/testcase/{key}") or {}
            return key, {"name": c.get("name"), "majorVersion": c.get("majorVersion")}
        except Exception as e:  # noqa: BLE001
            return key, {"name": None, "error": str(e)[:100]}

    with ThreadPoolExecutor(max_workers=8) as ex:
        for key, info in ex.map(one, list(dict.fromkeys(case_keys))):
            names[key] = info
    for p in plans:
        for c in p["cycles"]:
            for t in c["cases"]:
                t.update(names.get(t["key"], {}))
    return {"plans": plans}


# ------------------------------------------------------------------ templates and runnable counts

def _script_text(s: Dict[str, Any]) -> str:
    return (tc_runs.generated_dir() / s["path"]).read_text(encoding="utf-8")


def templates_with_counts(plan_keys: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Each template with the saved scripts it can run (pt_preflight against its .setup) and the
    manual cases it declares (cases.txt). An EMPTY template runs nothing and says so."""
    import pt_preflight  # noqa: PLC0415
    scripts = [s for s in tc_runs.list_scripts() if s.get("case_key")]
    out = []
    for t in tc_runs.list_templates():
        runnable, problems = [], {}
        setup = tc_runs.TEMPLATES_DIR / t["name"] / t["setup"] if t["setup"] else None
        text = setup.read_text(encoding="utf-8") if setup else ""
        if text.strip():
            for s in scripts:
                rep = pt_preflight.preflight_text(_script_text(s), text, s["path"], t["setup"])
                if rep.get("runnable"):
                    runnable.append(s["case_key"])
                else:
                    problems[s["case_key"]] = [p["message"] for p in rep.get("problems") or []][:3]
        out.append({**t, "runnable_scripts": sorted(set(runnable)), "not_runnable": problems,
                    "runnable_count": len(set(runnable)) + len(t["manual_cases"]),
                    "note": None if text.strip() else "empty template — fill its .setup to run anything"})
    return out


def requirements_aggregate() -> Dict[str, Any]:
    """Every saved script's topology demands, unioned — the shopping list for a template."""
    import pt_preflight  # noqa: PLC0415
    roles: Dict[str, List[str]] = {}
    links: Dict[str, List[str]] = {}
    power: List[str] = []
    for s in tc_runs.list_scripts():
        try:
            d = pt_preflight.parse_script(_script_text(s), Path(s["path"]))
        except (SyntaxError, OSError):
            continue
        who = s.get("case_key") or s["path"]
        for role, kind in d.roles.items():
            roles.setdefault(f"{role} ({kind})", []).append(who)
        for rd in d.role_links:
            links.setdefault(str(getattr(rd, "__dict__", rd)), []).append(who)
        for ld in d.links:
            links.setdefault(str(getattr(ld, "__dict__", ld)), []).append(who)
        if d.power:
            power.append(who)
    return {"roles": roles, "links": links, "power": sorted(set(power))}
