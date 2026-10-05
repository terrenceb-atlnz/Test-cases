"""Zephyr Templating Tool — the analysis (PLAN-zephyr-templating.md §5a, Phase 3).

Pure functions over two inputs, so every rule here is testable offline:
  * `wiki` — what `ask-ck/tools/zt_wiki.py` prints for a project page (version, product, the TPS's
    feature rows, the Test Strategy, the Feature Page, `problems`);
  * `tree` — the template plan -> cycle -> case tree (`db.load_zt_templates()`).

The model answers Q1–Q4 once per template PLAN (`plan_context` -> `zt_analyse_plan.jinja`) and Q5 +
the project's AI Notes once per project (`gaps_context` -> `zt_gaps.jinja`). It may only PROPOSE:
`check_plan_reply` / `check_gaps_reply` keep a proposal only if it names a key in that plan's tree
and carries a reason and a source, so a model that answers badly can only fail to untick things —
the cautious direction `docs/zephyr.txt` asks for ("erring on the side of caution"). A "Maybe"
feature is never a reason to untick (D8), and a whole PLAN is cut (Q1) only when the source is the
Test Strategy — the design's "refer to test strategy for details"; on 2026-10-05 the model cut
IE570's whole Advanced Management plan from four TPS rows.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

QUESTIONS = {"Q1": "plan", "Q2": "cycle", "Q3": "case", "Q4": "case"}

# What each prompt carries. The caps keep a call well inside a local model's window; a capped
# section says so in the text, so the model knows it saw a cut.
SECTION_CAP = 3000
STRATEGY_CAP = 10000
TPS_DEVICE_CAP = 14000
FEATURE_PAGE_CAP = 6000

# Test Strategy sections that are bookkeeping, not scope.
_STRATEGY_SKIP = ("approval", "critical reviewers", "information only", "risks table", "tools",
                  "test pool", "global involvement", "schedule", "references", "validation")
# TPS sections that describe the DEVICE (what it has, what it lacks), by title prefix, subsections
# included. The feature tables travel separately, as rows.
_TPS_DEVICE = ("overview of", "functions and operation", "major functional components",
               "new software features", "features that aren't going to be implemented",
               "external interfaces", "accessories and related products", "items in prd not supported")


# --------------------------------------------------------------------------- text

def plain(body: str) -> str:
    """Wikitext a model can read: no comments, markup or table syntax; one line per line."""
    t = re.sub(r"<!--.*?-->", "", body or "", flags=re.S)
    t = re.sub(r"\{\{\s*Incr\|[^}]*\}\}", "", t)
    t = re.sub(r"\{\{\{[^|{}]*\|([^{}]*)\}\}\}", r"\1", t)
    t = re.sub(r"<br\s*/?>", " ", t, flags=re.I)
    t = re.sub(r"</?[a-zA-Z][^>]*>", "", t)
    t = re.sub(r"\[\[(?:File|Image|Category):[^\]]*\]\]", "", t, flags=re.I)
    t = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", t)
    t = re.sub(r"\[https?://\S+\s+([^\]]*)\]", r"\1", t)
    t = t.replace("'''", "").replace("''", "")
    out = []
    for line in t.splitlines():
        s = line.strip()
        if s.startswith(("{|", "|}", "|-", "|+")):
            continue
        s = re.sub(r"^[|!]\s*", "", s)
        s = re.sub(r'\s*(\|\||!!)\s*', " | ", s)
        s = re.sub(r'\b(?:style|class|rowspan|colspan|align|width)="[^"]*"\s*\|?', "", s)
        s = re.sub(r"\s+", " ", s).strip(" |")
        if s:
            out.append(s)
    return "\n".join(out)


def _cut(text: str, cap: int) -> str:
    return text if len(text) <= cap else text[:cap].rstrip() + "\n[… cut at %d characters]" % cap


def _subtree(secs: List[dict], i: int) -> List[dict]:
    j = i + 1
    while j < len(secs) and secs[j]["level"] > secs[i]["level"]:
        j += 1
    return secs[i:j]


def _digest(secs: List[dict], cap: int, doc: str) -> str:
    """Sections as `### <doc> §<number> <title>` — the document is named on every heading, or the
    model cites a Strategy section as the TPS's (it did, 2026-10-05, IE570: "TPS §3.3 Feature
    Coverage")."""
    parts = []
    for s in secs:
        text = plain(s.get("body", ""))
        if text:
            parts.append(f"### {doc} §{s['number']} {s['title']}\n{_cut(text, SECTION_CAP)}")
    return _cut("\n\n".join(parts), cap)


def strategy_digest(wiki: dict) -> str:
    secs = ((wiki.get("strategy") or {}).get("sections")) or []
    keep = [s for s in secs if not s["title"].lower().startswith(_STRATEGY_SKIP)]
    return _digest(keep, STRATEGY_CAP, "Test Strategy") or "(the project has no Test Strategy page)"


def tps_device_digest(wiki: dict) -> str:
    secs = ((wiki.get("tps") or {}).get("sections")) or []
    keep, seen = [], set()
    for i, s in enumerate(secs):
        if s["title"].lower().startswith(_TPS_DEVICE) and s["number"] not in seen:
            for x in _subtree(secs, i):
                if x["number"] not in seen:
                    seen.add(x["number"])
                    keep.append(x)
    return _digest(keep, TPS_DEVICE_CAP, "TPS") or "(no device sections found in the TPS)"


def feature_page_digest(wiki: dict) -> str:
    fp = wiki.get("feature_page") or {}
    if fp.get("status") in (None, "missing"):
        return "(the Feature Page has not been created)"
    if fp.get("status") == "not written":
        return "(the Feature Page exists but is still the empty template — nothing written)"
    written = set(fp.get("written") or [])
    return _digest([s for s in fp.get("sections") or [] if s["title"] in written], FEATURE_PAGE_CAP, "Feature Page")


def feature_line(row: dict) -> str:
    """One TPS feature row as a citable line: `TPS §11.4 | Port | Continuous POE (HANP) | NO`."""
    if "item" in row:                                       # PRD-style
        what = " | ".join(x for x in (row.get("item"), row.get("specification")) if x)
        val = row.get("supported_raw") or ""
        extra = row.get("note") or ""
    else:                                                    # SID-style / tested
        what = " | ".join(x for x in (row.get("group"), row.get("feature")) if x)
        val = row.get("release") or row.get("supported_raw") or row.get("ranking") or ""
        extra = row.get("comment") or ""
    line = f"TPS §{row.get('section', '?')} | {what} | {val}"
    return line + (f" | {extra}" if extra else "")


def feature_lists(wiki: dict) -> Dict[str, List[str]]:
    """The TPS rows as lines, split by the reader's verdict: supported / unsupported / undecided.
    Duplicates (the same feature in two PRD parts) are kept once per distinct line."""
    tps = wiki.get("tps") or {}
    rows = (tps.get("sid_features") or []) + (tps.get("prd_features") or [])
    if not rows:
        rows = tps.get("tested_features") or []
    out: Dict[str, List[str]] = {"supported": [], "unsupported": [], "undecided": []}
    for r in rows:
        key = {True: "supported", False: "unsupported", None: "undecided"}[r.get("supported")]
        line = feature_line(r)
        if line not in out[key]:
            out[key].append(line)
    return out


# --------------------------------------------------------------------------- version + product

def version_and_product(wiki: dict) -> Dict[str, Any]:
    """What Version / What Product. The version is the Strategy's target path's first level when it
    has one — that is where the tests go (IE570: the project page says 5.5.6, the tests live under
    5.5.6-2) — else the project page's; `project_version` is kept beside it when they differ."""
    proj = wiki.get("project") or {}
    path = ((wiki.get("strategy") or {}).get("target_path") or {}).get("parts") or []
    page_v = proj.get("version")
    if path and re.match(r"^\d+\.\d+\.\d+(?:-\d+)?$", path[0]):
        version, source = path[0], "Test Strategy target path"
    else:
        version, source = page_v, "project page"
    return {"version": version, "version_source": source,
            "project_version": page_v if page_v and page_v != version else None,
            "product": proj.get("product"), "middle": path[1] if len(path) > 1 else None,
            "number": proj.get("number"), "title": proj.get("title")}


# --------------------------------------------------------------------------- per-plan call (Q1-Q4)

def plan_keys(plan: dict) -> Dict[str, str]:
    """Every key in one plan's tree -> its kind ("plan", "cycle", "case")."""
    keys = {plan["key"]: "plan"}
    for c in plan.get("cycles") or []:
        keys[c["key"]] = "cycle"
        for t in c.get("cases") or []:
            keys[t["key"]] = "case"
    return keys


def plan_context(wiki: dict, plan: dict) -> Dict[str, Any]:
    """The `zt_analyse_plan.jinja` context for one template plan."""
    vp = version_and_product(wiki)
    feats = feature_lists(wiki)
    return {"project": vp, "plan": plan, "strategy": strategy_digest(wiki),
            "tps_device": tps_device_digest(wiki), "feature_page": feature_page_digest(wiki),
            "unsupported": feats["unsupported"], "undecided": feats["undecided"]}


def _text(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v)).strip() if isinstance(v, (str, int, float)) else ""


def check_plan_reply(reply: Any, plan: dict) -> Dict[str, List[dict]]:
    """The guardrail. Keeps a deselection only if its key is in this plan's tree, its question fits
    the key's kind, and it has a reason and a source — and never one that rests on a "Maybe" row
    (D8). Notes may name a key in the tree or none. Everything refused goes to `dropped` with why."""
    keys = plan_keys(plan)
    out: Dict[str, List[dict]] = {"deselect": [], "notes": [], "dropped": []}
    if not isinstance(reply, dict):
        out["dropped"].append({"item": reply, "why": "the reply is not a JSON object"})
        return out
    seen = set()
    for d in reply.get("deselect") or []:
        if not isinstance(d, dict):
            out["dropped"].append({"item": d, "why": "not an object"})
            continue
        key, q = _text(d.get("key")), _text(d.get("question")).upper()
        reason, source = _text(d.get("reason")), _text(d.get("source"))
        why = None
        if key not in keys:
            why = "key is not in this plan's template tree"
        elif q not in QUESTIONS:
            why = "question is not Q1-Q4"
        elif QUESTIONS[q] != keys[key]:
            why = f"{q} is about a {QUESTIONS[q]}, but {key} is a {keys[key]}"
        elif not reason or not source:
            why = "no reason or no source"
        elif q == "Q1" and "strategy" not in source.lower():
            why = "a whole plan is cut only on the Test Strategy's word (docs/zephyr.txt Q1)"
        elif re.search(r"\bmaybe\b", f"{reason} {source}", flags=re.I):
            why = "rests on a 'Maybe' feature, which keeps its tests (D8)"
        elif key in seen:
            why = "duplicate"
        if why:
            out["dropped"].append({"item": d, "why": why})
            continue
        seen.add(key)
        out["deselect"].append({"key": key, "kind": keys[key], "question": q, "reason": reason, "source": source})
    for n in reply.get("notes") or []:
        if isinstance(n, str) and _text(n):
            out["notes"].append({"key": None, "note": _text(n)})
        elif isinstance(n, dict) and _text(n.get("note")):
            key = _text(n.get("key")) or None
            if key and key not in keys:
                out["dropped"].append({"item": n, "why": "note names a key not in this plan's tree"})
                continue
            out["notes"].append({"key": key, "note": _text(n.get("note"))})
    return out


# --------------------------------------------------------------------------- project call (Q5 + AI Notes)

def template_outline(tree: dict) -> List[str]:
    """Plan / cycle / case names, one line each, for the gap check."""
    lines = []
    for p in tree.get("plans") or []:
        lines.append(f"PLAN {p['key']} {p.get('name') or ''}".rstrip())
        for c in p.get("cycles") or []:
            lines.append(f"  CYCLE {c['key']} {c.get('name') or ''}".rstrip())
            for t in c.get("cases") or []:
                lines.append(f"    {t['key']} {t.get('name') or ''}".rstrip())
    return lines


def gaps_context(wiki: dict, tree: dict) -> Dict[str, Any]:
    vp = version_and_product(wiki)
    feats = feature_lists(wiki)
    return {"project": vp, "strategy": strategy_digest(wiki), "tps_device": tps_device_digest(wiki),
            "feature_page": feature_page_digest(wiki), "supported": feats["supported"],
            "undecided": feats["undecided"], "templates": template_outline(tree)}


def check_gaps_reply(reply: Any) -> Dict[str, List[dict]]:
    """Gaps need a requirement and a source; notes are free text. Report-only (D11): nothing here
    ever changes a tick."""
    out: Dict[str, List[dict]] = {"gaps": [], "notes": [], "dropped": []}
    if not isinstance(reply, dict):
        out["dropped"].append({"item": reply, "why": "the reply is not a JSON object"})
        return out
    for g in reply.get("gaps") or []:
        if isinstance(g, dict) and _text(g.get("requirement")) and _text(g.get("source")):
            out["gaps"].append({"requirement": _text(g["requirement"]), "source": _text(g["source"]),
                                "why": _text(g.get("why"))})
        else:
            out["dropped"].append({"item": g, "why": "a gap needs a requirement and a source"})
    for n in reply.get("notes") or []:
        t = _text(n.get("note")) if isinstance(n, dict) else _text(n)
        if t:
            out["notes"].append({"note": t})
    return out
