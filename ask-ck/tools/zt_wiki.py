#!/usr/bin/env python3
"""Read a project's wiki pages for the Zephyr Templating Tool — version, product, TPS, Strategy, Feature Page.

Zephyr Templating Tool, Phase 2 (PLAN-zephyr-templating.md §4a). The user pastes a project page URL
(e.g. `Project:3296_IE520_Software`); this reads that page and the three templated pages it links:

  project page   version (`[[5.5.6-2 Release|…]]`, `{{Test Status v2|5.5.6-2|3296}}`, the version
                 category), product (the remaining category), project number, the three links
  TPS            every section, plus the two feature tables as rows: §11.3 *Supported features
                 (Ref. SID …)* ranked `M`/`-` and §11.4 *Supported features (Ref. PRD …)* marked
                 `YES`/`NO`/`-`. Only `M` / `YES` count as supported — a `-` means "not supported or
                 N/A" (Terrence, 2026-10-05, D4)
  Test Strategy  every section, plus the target path its "Test Cases" section names
                 ("stored in Jira under 5.5.6-2 ---> Tomahawk ---> IE520", D5)
  Feature Page   written / not written, section by section: a section still equal to the page's
                 preload template (`{{TODO|…}}` boilerplate) is not written (D6) — often none is

Sections and tables are found by TITLE, never by number: a TPS revision can renumber them.
The reader REPORTS — disagreements (two versions, a path naming another product) go in `problems`;
nothing here decides what to test.

READ ONLY: every request is a GET of `api.php?action=parse` (`_get` refuses anything else), and the
wiki answers it without a login. Nothing on the wiki changes.

Usage:
  python3 ask-ck/tools/zt_wiki.py <project page URL or title>              # JSON to stdout
  python3 ask-ck/tools/zt_wiki.py <url> --out <file>                       # keep it out of the lab tree
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jira_testlink_access import SSL_CTX  # noqa: E402

WIKI = "https://wiki.atlnz.lc/awpwiki"
API = WIKI + "/api.php"
FEATURE_PRELOAD = "Template:FeatureDocumentation/Preload"
SID_TABLE = "Supported features (Ref. SID"      # TPS §11.3, title prefix
PRD_TABLE = "Supported features (Ref. PRD"      # TPS §11.4, title prefix
NS_MAIN, NS_TEST = 0, 102
_VERSION = re.compile(r"^\d+\.\d+\.\d+(?:-\d+)?$")

Get = Callable[[Dict[str, str]], dict]


# --------------------------------------------------------------------------- access

def _get(params: Dict[str, str], method: str = "GET") -> dict:
    """One read of api.php. Refuses any method but GET and any action but parse: read only."""
    if method != "GET" or params.get("action") != "parse":
        raise ValueError("zt_wiki is read-only (GET action=parse only)")
    url = API + "?" + urllib.parse.urlencode({**params, "format": "json"})
    req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60, context=SSL_CTX) as r:
        return json.loads(r.read() or b"null")


def _parse(get: Get, title: str) -> Optional[dict]:
    """The page's wikitext, sections, rendered links and categories; None if it does not exist."""
    d = get({"action": "parse", "page": title, "redirects": "1",
             "prop": "wikitext|sections|links|categories"})
    if "error" in d:
        if d["error"].get("code") == "missingtitle":
            return None
        raise RuntimeError(f"wiki: {title}: {d['error'].get('info') or d['error']}")
    return d["parse"]


def page_title(url_or_title: str) -> str:
    """`https://wiki.atlnz.lc/awpwiki/index.php/Project:3296_IE520_Software`, the `?title=` form, or a
    bare title -> `Project:3296 IE520 Software`."""
    s = url_or_title.strip()
    if "://" in s:
        u = urllib.parse.urlsplit(s)
        if u.netloc != urllib.parse.urlsplit(WIKI).netloc:
            raise ValueError(f"not a page on {WIKI}: {s}")
        q = urllib.parse.parse_qs(u.query).get("title")
        if q:
            s = q[0]
        elif "/index.php/" in u.path:
            s = urllib.parse.unquote(u.path.split("/index.php/", 1)[1])
        else:
            raise ValueError(f"no page title in {s}")
    else:
        s = urllib.parse.unquote(s.split("#", 1)[0])
    s = s.replace("_", " ").strip()
    if not s:
        raise ValueError("empty page title")
    return s


# --------------------------------------------------------------------------- wikitext

def _clean(text: str) -> str:
    """Cell / line text as a reader sees it: links by label, no markup, one line."""
    t = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    t = re.sub(r"\{\{\{[^|{}]*\|([^{}]*)\}\}\}", r"\1", t)       # a preload's {{{1|default}}}
    t = re.sub(r"<br\s*/?>", " ", t, flags=re.I)
    t = re.sub(r"</?[a-zA-Z][^>]*>", "", t)
    t = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", t)
    t = re.sub(r"\[https?://\S+\s+([^\]]*)\]", r"\1", t)
    t = t.replace("'''", "").replace("''", "")
    return re.sub(r"\s+", " ", t).strip()


def sections(wikitext: str) -> List[dict]:
    """[{number, level, title, body}], numbered as MediaWiki's table of contents numbers them; `body`
    is the section's own text up to the next heading. Text before the first heading is dropped."""
    text = re.sub(r"<!--.*?-->", "", wikitext, flags=re.S)
    heads = list(re.finditer(r"^(={1,6})\s*(.+?)\s*\1\s*$", text, flags=re.M))
    out, stack = [], []          # stack of [level, count]
    for i, m in enumerate(heads):
        level = len(m.group(1))
        popped = None
        while stack and stack[-1][0] > level:
            popped = stack.pop()
        if stack and stack[-1][0] == level:
            stack[-1][1] += 1
        else:
            stack.append([level, popped[1] + 1 if popped else 1])
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        out.append({"number": ".".join(str(c) for _, c in stack), "level": level,
                    "title": _clean(m.group(2)), "body": text[m.end():end].strip("\n")})
    return out


def _find(secs: List[dict], prefix: str) -> Optional[dict]:
    return next((s for s in secs if s["title"].lower().startswith(prefix.lower())), None)


def _split(line: str, sep: str) -> List[str]:
    """Split on `sep` (`||`, `!!` or `|`) outside `{{…}}` and `[[…]]`."""
    parts, buf, depth, i = [], [], 0, 0
    while i < len(line):
        two = line[i:i + 2]
        if two in ("{{", "[[", "}}", "]]"):
            depth += 1 if two in ("{{", "[[") else -1 if depth else 0
            buf.append(two)
            i += 2
        elif depth == 0 and line.startswith(sep, i):
            parts.append("".join(buf))
            buf, i = [], i + len(sep)
        else:
            buf.append(line[i])
            i += 1
    parts.append("".join(buf))
    return parts


def _cell(raw: str, header: bool) -> dict:
    """`style="x" rowspan="2" |text` -> {text, rowspan, colspan, header}."""
    attrs, text = "", raw
    parts = _split(raw, "|")
    if len(parts) > 1 and "=" in parts[0]:
        attrs, text = parts[0], raw[len(parts[0]) + 1:]

    def span(k: str) -> int:
        m = re.search(k + r'\s*=\s*"?(\d+)', attrs)
        return int(m.group(1)) if m else 1
    return {"text": text, "rowspan": span("rowspan"), "colspan": span("colspan"), "header": header}


def wikitable(body: str) -> Tuple[List[str], List[List[str]]]:
    """The first `{| … |}` table in `body` as (column labels, rows of cell text), with rowspan and
    colspan expanded so every row has one cell per column. Header rows are the leading rows made
    only of `!` cells; a column's label joins its distinct header texts with " / "."""
    start = body.find("{|")
    if start < 0:
        return [], []
    end = body.find("\n|}", start)
    lines = body[start:end if end > 0 else len(body)].split("\n")[1:]
    rows: List[List[dict]] = [[]]
    for line in lines:
        s = line.strip()
        if s.startswith("|-"):
            rows.append([])
        elif s.startswith("|+"):
            continue
        elif s.startswith("!"):
            rows[-1] += [_cell(c, True) for h in _split(s[1:], "!!") for c in _split(h, "||")]
        elif s.startswith("|"):
            rows[-1] += [_cell(c, False) for c in _split(s[1:], "||")]
        elif rows[-1]:
            rows[-1][-1]["text"] += "\n" + line
    rows = [r for r in rows if r]
    grid: List[List[dict]] = []
    carry: Dict[int, Tuple[dict, int]] = {}             # column -> (cell, rows still to fill)
    for r in rows:
        out: List[dict] = []
        ci = col = 0
        while ci < len(r) or col in carry:
            if col in carry:
                c, left = carry.pop(col)
                if left > 1:
                    carry[col] = (c, left - 1)
                out.append(c)
                col += 1
                continue
            c, ci = r[ci], ci + 1
            for _ in range(c["colspan"]):
                if c["rowspan"] > 1:
                    carry[col] = (c, c["rowspan"] - 1)
                out.append(c)
                col += 1
        grid.append(out)
    n_head = 0
    while n_head < len(grid) and all(c["header"] for c in grid[n_head]):
        n_head += 1
    width = max((len(g) for g in grid), default=0)
    labels = []
    for col in range(width):
        seen: List[str] = []
        for g in grid[:n_head]:
            t = _clean(g[col]["text"]) if col < len(g) else ""
            if t and t not in seen:
                seen.append(t)
        labels.append(" / ".join(seen))
    data = [[_clean(c["text"]) for c in g] + [""] * (width - len(g)) for g in grid[n_head:]]
    return labels, data


def _column(labels: List[str], *starts: str) -> List[int]:
    return [i for i, l in enumerate(labels) if any(l.lower().startswith(s.lower()) for s in starts)]


def _joined(row: List[str], cols: List[int]) -> str:
    vals: List[str] = []
    for i in cols:
        if row[i] and row[i] not in vals:
            vals.append(row[i])
    return " / ".join(vals)


# --------------------------------------------------------------------------- the pages

def sid_features(sec: Optional[dict]) -> List[dict]:
    """TPS §11.3 rows: {group, feature, ranking, supported, comment}; supported = ranking `M`."""
    if not sec:
        return []
    labels, rows = wikitable(sec["body"])
    rank, group, feat, comment = (_column(labels, k) for k in ("Ranking", "Feature Group", "Feature", "Comment"))
    feat = [i for i in feat if i not in group]
    out = []
    for r in rows:
        ranking = _joined(r, rank)
        out.append({"group": _joined(r, group), "feature": _joined(r, feat), "ranking": ranking,
                    "supported": ranking.upper() == "M", "comment": _joined(r, comment)})
    return out


def prd_features(sec: Optional[dict]) -> List[dict]:
    """TPS §11.4 rows: {item, specification, priority, supported_raw, supported, note};
    supported = `YES`."""
    if not sec:
        return []
    labels, rows = wikitable(sec["body"])
    item, spec, prio, sup, note = (_column(labels, k) for k in ("Item", "Specification", "Priority", "Supported", "Note"))
    out = []
    for r in rows:
        raw = _joined(r, sup)
        out.append({"item": _joined(r, item), "specification": _joined(r, spec), "priority": _joined(r, prio),
                    "supported_raw": raw, "supported": raw.upper() == "YES", "note": _joined(r, note)})
    return out


def target_path(sec: Optional[dict]) -> Optional[dict]:
    """The Strategy's "stored in Jira under A ---> B ---> C" line -> {line, parts}."""
    if not sec:
        return None
    for line in sec["body"].splitlines():
        m = re.search(r"\bJira under\s+(.+)", _clean(line), flags=re.I)
        if m:
            parts = [p.strip(" .") for p in re.split(r"-+>", m.group(1)) if p.strip(" .")]
            return {"line": _clean(line), "parts": parts}
    return None


def feature_page_state(secs: List[dict], preload: str) -> dict:
    """{status, written: [titles], unwritten: [titles]}: a section is written when its body has a
    line the preload template does not (the preload's `$1` matches anything). A page created from
    the preload gets its `<includeonly>` text and none of its `<noinclude>` text."""
    preload = re.sub(r"<noinclude>.*?</noinclude>", "", preload, flags=re.S)
    preload = re.sub(r"</?includeonly>", "", preload)
    pats =[re.compile("^" + ".*?".join(re.escape(p) for p in ln.split("$1")) + "$")
            for ln in (re.sub(r"\s+", " ", x).strip() for x in preload.splitlines()) if ln]
    written, unwritten = [], []
    for s in secs:
        lines = [re.sub(r"\s+", " ", x).strip() for x in s["body"].splitlines()]
        lines = [x for x in lines if x]
        if not lines:
            continue
        own = [x for x in lines if not any(p.match(x) for p in pats)]
        (written if own else unwritten).append(s["title"])
    status = ("not written" if not written else "written" if not unwritten else "partly written")
    return {"status": status, "written": written, "unwritten": unwritten}


def _links(parsed: dict) -> List[Tuple[int, str, bool]]:
    return [(l["ns"], l["*"], "exists" in l) for l in parsed.get("links") or []]


def _pick(links, problems: List[str], what: str, ok: Callable[[int, str], bool]) -> Optional[dict]:
    hits = [(t, e) for ns, t, e in links if ok(ns, t)]
    if not hits:
        problems.append(f"the project page links no {what}")
        return None
    if len(hits) > 1:
        problems.append(f"the project page links more than one {what}: {[t for t, _ in hits]} — using the first")
    t, e = hits[0]
    return {"title": t, "exists": e, "url": f"{WIKI}/index.php/{urllib.parse.quote(t.replace(' ', '_'))}"}


def read_project(get: Get, url_or_title: str) -> dict:
    """Everything the analysis needs from the wiki, plus `problems`. `get(params)` returns api.php's
    parsed JSON; injected so tests run offline."""
    problems: List[str] = []
    title = page_title(url_or_title)
    proj = _parse(get, title)
    if proj is None:
        raise ValueError(f"no wiki page {title!r}")
    text = proj["wikitext"]["*"]
    cats = [c["*"].replace("_", " ") for c in proj.get("categories") or []]

    found: Dict[str, List[str]] = {}
    for v in re.findall(r"\[\[\s*([\w.\-]+) Release\s*\|", text):
        found.setdefault(v, []).append("release link")
    status = re.search(r"\{\{\s*Test Status v2\s*\|\s*([^|}]+?)\s*\|\s*([^|}]+?)\s*\}\}", text)
    if status:
        found.setdefault(status.group(1), []).append("Test Status")
    for c in cats:
        if _VERSION.match(c):
            found.setdefault(c, []).append("category")
    found = {v: srcs for v, srcs in found.items() if _VERSION.match(v)}
    if len(found) > 1:
        problems.append(f"the project page names more than one version: {found}")
    version = max(found, key=lambda v: len(found[v])) if found else None
    if not version:
        problems.append("the project page names no AW+ version")
    products = [c for c in cats if c != "Project" and not _VERSION.match(c)]
    if len(products) != 1:
        problems.append(f"cannot tell the product from the project page's categories {cats}")
    num = re.match(r"Project:\s*(\d+)", proj["title"]) or (status and re.match(r"(\d+)$", status.group(2)))
    number = num.group(1) if num else None

    links = _links(proj)
    pages = {
        "tps": _pick(links, problems, "TPS / TFS",
                     lambda ns, t: ns == NS_MAIN and (t.endswith(" TPS") or t.endswith(" TFS"))),
        "strategy": _pick(links, problems, "Test Strategy",
                          lambda ns, t: ns == NS_TEST and re.match(r"Test:\s*\d+ Test Strategy", t) is not None),
        "feature": _pick(links, problems, "Feature Page",
                         lambda ns, t: ns == NS_MAIN and t.endswith(" - Feature Page")),
    }
    got: Dict[str, Optional[dict]] = {}
    for key, p in pages.items():
        if p and p["exists"]:
            got[key] = _parse(get, p["title"])
            if got[key] is None:
                p["exists"] = False
        if p and not p["exists"]:
            problems.append(f"{p['title']!r} has not been created yet")

    tps = None
    if got.get("tps"):
        secs = sections(got["tps"]["wikitext"]["*"])
        sid, prd = _find(secs, SID_TABLE), _find(secs, PRD_TABLE)
        for sec, name in ((sid, SID_TABLE), (prd, PRD_TABLE)):
            if not sec:
                problems.append(f"the TPS has no section {name + '…)'!r}")
        tps = {"sections": secs, "sid_features": sid_features(sid), "prd_features": prd_features(prd),
               "sid_section": sid and sid["number"], "prd_section": prd and prd["number"]}

    strategy = None
    if got.get("strategy"):
        secs = sections(got["strategy"]["wikitext"]["*"])
        path = target_path(_find(secs, "Test Cases"))
        if not path:
            problems.append("the Test Strategy's \"Test Cases\" section names no target path")
        else:
            if version and path["parts"] and path["parts"][0] != version:
                problems.append(f"the Test Strategy's target path starts {path['parts'][0]!r}, "
                                f"the project page says {version!r}")
            if len(products) == 1 and path["parts"] and products[0] not in path["parts"][-1]:
                problems.append(f"the Test Strategy's target path ends {path['parts'][-1]!r}, "
                                f"not the product {products[0]!r}")
        strategy = {"sections": secs, "target_path": path}

    feature = {"status": "missing", "written": [], "unwritten": []}
    if got.get("feature"):
        pre = _parse(get, FEATURE_PRELOAD)
        feature = feature_page_state(sections(got["feature"]["wikitext"]["*"]),
                                     pre["wikitext"]["*"] if pre else "")
        if not pre:
            problems.append(f"{FEATURE_PRELOAD} is missing — every Feature Page section reads as written")
        feature["sections"] = sections(got["feature"]["wikitext"]["*"]) if feature["written"] else []

    return {"fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "project": {"title": proj["title"], "url": f"{WIKI}/index.php/{urllib.parse.quote(proj['title'].replace(' ', '_'))}",
                        "number": number, "version": version, "version_sources": found,
                        "product": products[0] if len(products) == 1 else None, "categories": cats},
            "pages": pages, "tps": tps, "strategy": strategy, "feature_page": feature,
            "problems": problems}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("project", help="the project page's URL or title")
    ap.add_argument("--out", help="write the JSON here instead of stdout")
    a = ap.parse_args(argv)
    r = read_project(_get, a.project)
    text = json.dumps(r, indent=2, ensure_ascii=False) + "\n"
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    p, t = r["project"], r["tps"] or {}
    print(f"{p['title']}: version {p['version']}, product {p['product']}; TPS §11.3 "
          f"{len(t.get('sid_features') or [])} rows, §11.4 {len(t.get('prd_features') or [])} rows; "
          f"Feature Page {r['feature_page']['status']}; {len(r['problems'])} problem(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
