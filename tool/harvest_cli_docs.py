#!/usr/bin/env python3
"""Harvest the AlliedWare Plus CLI command reference into ck.db as a renewable resource.

WHY: the PyTest Creator generate prompt names `show interface` 27 times but shows ZERO
examples of its output, so every model in the Part 2B matrix — Opus included — invented a
`speed=1000`/`state=up` key=value schema that the switch never prints. Real output is:

    current duplex full, current speed 1000, current polarity mdix

This tool gives generation the real syntax + sample output to ground on.

SOURCE: https://docs.atlnz.lc/preview/ — 37 product command references, ~2,900 unique
commands, ~73,000 product×command pages. Measured facts driving the design:
  - a command page's content is byte-identical across product families ~96% of the time
    (23/24 in a 6-family sample), so content is CONTENT-ADDRESSED and stored once; the
    per-product rows are a thin support matrix. Dedupe factor ~4.7x.
  - pages are ~630KB each but only ~0.3% is real content — the rest is an inlined nav
    tree. Only the <pre> blocks are kept.
  - `/<product>/index.html` is a META-REFRESH (curl -L will NOT follow it).
  - WebFetch's markdown conversion DROPS <pre> blocks; raw HTML + regex is required.

CAVEAT (documented in memory: awplus-speed-duplex-constraint): cross-command physical
constraints are NOT in this source. Half duplex is impossible at >=1 Gig, but the x530
page lists `half` unconditionally and neither the speed nor duplex page mentions it. Such
rules must come from the ART corpus (which encodes them implicitly) or be hand-written.
Do not treat this table as a complete validity oracle — it is a syntax/output reference.

RENEWABLE: re-run any time. Rows are replaced per (product, command) and the harvest
stamps `meta` with when it ran and what it saw. --since-hours skips a recent harvest.

Usage:
  python3 tool/harvest_cli_docs.py --products x530,x930      # a subset
  python3 tool/harvest_cli_docs.py --all                     # every command reference
  python3 tool/harvest_cli_docs.py --all --dry-run           # enumerate, fetch nothing
  python3 tool/harvest_cli_docs.py --all --jobs 12
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parent.parent
DB = REPO / "ask-ck" / "var" / "ck.db"
BASE = "https://docs.atlnz.lc/preview"
TOC = "_bookmap_files/frontmatter/cmdref_Introduction.html"

_PRE_RX = re.compile(r"<pre[^>]*>(.*?)</pre>", re.S | re.I)
# The preview site is mid-build and serves SOFT 404s: HTTP 200 with a "the file isn't
# there, it may have moved in the latest rebuild" body. Recording those as "command exists
# but has no examples" would silently poison the reference, so they are detected and
# counted separately from pages that legitimately carry no <pre> block (index pages,
# introductions, and cross-references like `undebug aaa`).
_SOFT404_RX = re.compile(r"Mostly harmless|isn't there|may have moved in the latest",
                         re.I)
_CMDPAGE_RX = re.compile(r"([a-z0-9\-]+_cmd/[A-Za-z0-9_\-.]+\.html)")
_TAG_RX = re.compile(r"<[^>]+>")
# A CLI prompt line marks a worked example; the switch's reply follows it.
_PROMPT_RX = re.compile(r"^\s*awplus[^\n]*[#>]", re.M)
# Phase 4.5: ANY hostname, not just `awplus`. Doc pages use `Node_1(config)#`, `master_1#`
# and `controller-1(config)#`, and the awplus-only form filed all of those as syntax.
# Kept byte-identical to cli_lookup._PROMPT_ANY_RX — a test pins that they agree.
_PROMPT_ANY_RX = re.compile(
    r"^[ \t]*[A-Za-z][\w.\-]{0,31}(?:\([^)\n]{0,31}\))?[ \t]*[#>][ \t]*(?=\S)", re.M)
# Placeholder metacharacters that mark a SYNTAX template rather than device output.
_PLACEHOLDER_RX = re.compile(r"[<>{}|\[\]]")


SCHEMA = """
CREATE TABLE IF NOT EXISTS cli_commands (
  content_sha   TEXT PRIMARY KEY,   -- sha256 of the extracted content (dedupe key)
  command       TEXT,               -- 'show interface status'
  page          TEXT,               -- 'int_cmd/show_interface_status.html'
  cmd_group     TEXT,               -- 'int_cmd'
  syntax        TEXT,               -- JSON array of syntax lines
  examples      TEXT,               -- JSON array of {cmd, output}
  sample_output TEXT,               -- the richest output block, for prompt injection
  pre_blocks    TEXT,               -- JSON array: every <pre> block, verbatim
  n_blocks      INTEGER,
  harvested_at  TEXT
);
CREATE TABLE IF NOT EXISTS cli_command_products (
  page        TEXT NOT NULL,        -- joins cli_commands.page
  product     TEXT NOT NULL,        -- 'x530'
  content_sha TEXT NOT NULL,        -- which variant THIS product has
  PRIMARY KEY (page, product)
);
CREATE INDEX IF NOT EXISTS idx_cli_cmd_page ON cli_commands(page);
CREATE INDEX IF NOT EXISTS idx_cli_cmd_command ON cli_commands(command);
CREATE INDEX IF NOT EXISTS idx_cli_prod_sha ON cli_command_products(content_sha);
CREATE VIRTUAL TABLE IF NOT EXISTS cli_commands_fts USING fts5(
  command, cmd_group, syntax, sample_output,
  content='cli_commands', content_rowid='rowid',
  tokenize="unicode61 remove_diacritics 2 tokenchars '.-+'", prefix='2 3'
);
"""


# --------------------------------------------------------------------------- fetch


def fetch(url: str, timeout: int = 60, retries: int = 2) -> str:
    """GET a URL via curl. Returns '' on failure (never raises — a dead page must not
    abort a 73k-page harvest)."""
    for attempt in range(retries + 1):
        try:
            r = subprocess.run(["curl", "-sS", "--max-time", str(timeout), url],
                               capture_output=True, text=True)
            if r.returncode == 0 and r.stdout:
                return r.stdout
        except Exception:
            pass
        if attempt < retries:
            time.sleep(1 + attempt)
    return ""


def list_products() -> List[str]:
    """Product families that are real command references (not guides/reviews)."""
    html = fetch(f"{BASE}/", 30)
    cands = sorted(set(re.findall(r'href=["\']([A-Za-z0-9_\-]+)/index\.html["\']', html)))
    # guides/user-guide reviews use a different layout; the cmdref redirect identifies
    # the real ones without hardcoding a product list that will age.
    out = []
    for p in cands:
        idx = fetch(f"{BASE}/{p}/index.html", 20)
        if "cmdref_Introduction" in idx:
            out.append(p)
    return out


def list_pages(product: str) -> List[str]:
    toc = fetch(f"{BASE}/{product}/{TOC}", 90)
    return sorted(set(_CMDPAGE_RX.findall(toc)))


# --------------------------------------------------------------------------- parse


def pre_blocks(html: str) -> List[str]:
    return [unescape(_TAG_RX.sub("", m.group(1))).strip() for m in _PRE_RX.finditer(html)]


def command_name(page: str) -> str:
    """'int_cmd/show_interface_status.html' -> 'show interface status'.

    Filenames carry a trailing disambiguator on some pages (`speed_ak`, `duplex_ak`,
    `show_interface_memory_ad`) — a 2-letter suffix that is not part of the command.
    Strip it, then underscores become spaces.
    """
    stem = page.rsplit("/", 1)[-1].removesuffix(".html")
    stem = re.sub(r"_[a-z]{2}$", "", stem)
    return stem.replace("_", " ").strip()


def classify(blocks: List[str]) -> Tuple[List[str], List[dict], Optional[str]]:
    """Split <pre> blocks into syntax lines, worked examples, and the best sample output.

    Shapes observed on real pages:
      - syntax:  `duplex {auto|full|half}`            (no prompt line)
      - example: `awplus# configure terminal ...`     (prompt lines only)
      - output:  `awplus#show interface` + the switch's multi-line reply
      - output:  a bare multi-line reply with NO command line above it

    PHASE 4.5 — this used to require the literal hostname `awplus` and treated every other
    block as syntax, which stranded real device output in the `syntax` column on 735 rows
    (606 of them ending up with no `sample_output` at all). Two causes: doc pages that use
    a different hostname (`Node_1(config)#`, `master_1#`, `controller-1(config)#`), and
    output shown without the command above it.

    THE LIVE PATH DOES NOT DEPEND ON THIS FIX. `ask-ck/var/ck.db` is built once and never
    rebuilt, so the rows already stored keep their old split; `cli_lookup.reclassify()`
    re-derives at READ time from the verbatim `pre_blocks` column. This is fixed so a
    future harvest cannot reintroduce the defect, and the two implementations are pinned
    to agree by `tests/test_cli_grounding_phase4.py`.
    """
    from typing import Optional as _Opt  # local: keep the module's import block untouched
    syntax: List[str] = []
    examples: List[dict] = []
    best = None

    for b in blocks:
        if not b or not b.strip():
            continue
        if _PROMPT_ANY_RX.search(b):
            lines = b.split("\n")
            cmd_line = lines[0].strip()
            reply = "\n".join(lines[1:]).rstrip()
            examples.append({"cmd": cmd_line, "output": reply or None})
            # the richest reply is the most useful thing to show a generator
            if reply and (best is None or len(reply) > len(best)):
                best = reply
            continue

        lines = [ln for ln in b.split("\n") if ln.strip()]
        if len(lines) < 3:
            syntax.append(b)
            continue
        dense = sum(1 for ln in lines if _PLACEHOLDER_RX.search(ln))
        if dense / len(lines) > 0.4:
            syntax.append(b)
            continue
        text = b.rstrip()
        if best is None or len(text) > len(best):
            best = text
    return syntax, examples, best


def parse_page(page: str, html: str) -> Optional[dict]:
    """Parsed row, or a marker string for the two non-content outcomes.

    Returns 'soft404' when the site served a rebuild placeholder (HTTP 200, no content),
    'no-pre' for a page that legitimately has no example blocks, else the parsed dict.
    The caller counts these separately — conflating them would hide how much of the
    reference is temporarily missing from a mid-build preview.
    """
    if _SOFT404_RX.search(html[:4000]):
        return "soft404"
    blocks = pre_blocks(html)
    if not blocks:
        return "no-pre"
    body = "\n".join(blocks)
    syntax, examples, sample = classify(blocks)
    return {
        "content_sha": hashlib.sha256(body.encode()).hexdigest(),
        "command": command_name(page),
        "page": page,
        "cmd_group": page.split("/")[0],
        "syntax": syntax,
        "examples": examples,
        "sample_output": sample,
        "pre_blocks": blocks,
    }


# --------------------------------------------------------------------------- store


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def store(conn: sqlite3.Connection, rows: List[Tuple[str, dict]]) -> Tuple[int, int]:
    """rows = [(product, parsed), ...]. Content is written once per unique sha."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    seen_sha = set()
    n_content = 0
    for product, p in rows:
        if p["content_sha"] not in seen_sha:
            seen_sha.add(p["content_sha"])
            cur = conn.execute(
                "INSERT OR REPLACE INTO cli_commands (content_sha, command, page, "
                "cmd_group, syntax, examples, sample_output, pre_blocks, n_blocks, "
                "harvested_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (p["content_sha"], p["command"], p["page"], p["cmd_group"],
                 json.dumps(p["syntax"]), json.dumps(p["examples"]),
                 p["sample_output"], json.dumps(p["pre_blocks"]),
                 len(p["pre_blocks"]), now))
            if cur.rowcount:
                n_content += 1
        conn.execute(
            "INSERT OR REPLACE INTO cli_command_products (page, product, content_sha) "
            "VALUES (?,?,?)", (p["page"], product, p["content_sha"]))
    conn.commit()
    return n_content, len(rows)


def rebuild_fts(conn: sqlite3.Connection) -> None:
    conn.execute("INSERT INTO cli_commands_fts(cli_commands_fts) VALUES('rebuild')")
    conn.commit()


# --------------------------------------------------------------------------- driver


def harvest(products: List[str], jobs: int, dry_run: bool, limit: Optional[int],
            group_filter: Optional[set] = None) -> int:
    print(f"enumerating {len(products)} product reference(s)…")
    plan: List[Tuple[str, str]] = []
    for prod in products:
        pages = list_pages(prod)
        if limit is not None and limit > 0:
            pages = pages[:limit]
        if group_filter:
            pages = [p for p in pages if p.split("/")[0] in group_filter]
        print(f"  {prod:<12} {len(pages):>5} pages")
        plan += [(prod, pg) for pg in pages]

    uniq_pages = len({pg for _, pg in plan})
    print(f"\n{len(plan)} product×page fetches, {uniq_pages} distinct pages")
    if dry_run:
        print("dry run — nothing fetched")
        return 0

    conn = sqlite3.connect(DB)
    ensure_schema(conn)

    t0 = time.monotonic()
    done = fetch_fail = soft404 = no_pre = 0
    soft404_pages: set = set()
    batch: List[Tuple[str, dict]] = []
    n_content = 0

    def work(job):
        prod, page = job
        html = fetch(f"{BASE}/{prod}/{page}", 45)
        if len(html) < 500:
            return prod, page, None
        return prod, page, parse_page(page, html)

    with ThreadPoolExecutor(max_workers=jobs) as ex:
        for prod, page, parsed in ex.map(work, plan):
            done += 1
            if parsed is None:
                fetch_fail += 1
            elif parsed == "soft404":
                soft404 += 1
                soft404_pages.add(page)
            elif parsed == "no-pre":
                no_pre += 1
            else:
                batch.append((prod, parsed))
            if len(batch) >= 400:
                c, _ = store(conn, batch)
                n_content += c
                batch = []
            if done % 500 == 0:
                el = time.monotonic() - t0
                rate = done / el if el else 0
                eta = (len(plan) - done) / rate if rate else 0
                print(f"  {done}/{len(plan)}  {rate:.0f}/s  eta {eta/60:.0f}m  "
                      f"soft404 {soft404}  no-pre {no_pre}  fetch-fail {fetch_fail}",
                      flush=True)

    if batch:
        c, _ = store(conn, batch)
        n_content += c

    print("\nrebuilding FTS index…")
    rebuild_fts(conn)

    stamp = {
        "harvested_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": BASE,
        "products": products,
        "fetches": len(plan),
        "fetch_failed": fetch_fail,
        # a mid-build preview serves 200-with-placeholder; tracked so a later harvest can
        # tell "this command has no examples" from "the site hadn't rebuilt it yet"
        "soft_404": soft404,
        "soft_404_pages": sorted(soft404_pages)[:200],
        "no_example_blocks": no_pre,
    }
    conn.execute("INSERT OR REPLACE INTO meta (k, v) VALUES ('cli_docs_harvest', ?)",
                 (json.dumps(stamp),))
    conn.commit()

    n_cmd = conn.execute("SELECT COUNT(*) FROM cli_commands").fetchone()[0]
    n_map = conn.execute("SELECT COUNT(*) FROM cli_command_products").fetchone()[0]
    n_out = conn.execute("SELECT COUNT(*) FROM cli_commands "
                         "WHERE sample_output IS NOT NULL").fetchone()[0]
    el = time.monotonic() - t0
    print(f"\ndone in {el/60:.1f}m — {done} fetched")
    print(f"  soft-404 (site mid-build) {soft404:>6}  over {len(soft404_pages)} distinct pages")
    print(f"  no example blocks         {no_pre:>6}  (index/intro/cross-ref pages)")
    print(f"  fetch failures            {fetch_fail:>6}")
    print(f"  cli_commands          {n_cmd:>6} unique content blobs "
          f"({n_out} with sample output)")
    print(f"  cli_command_products  {n_map:>6} product×command rows")
    conn.close()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Harvest the AW+ CLI reference into ck.db")
    ap.add_argument("--products", help="comma-separated (default: all command references)")
    ap.add_argument("--all", action="store_true", help="every command reference")
    ap.add_argument("--jobs", type=int, default=10, help="concurrent fetches (default 10)")
    ap.add_argument("--limit", type=int, help="cap pages per product (smoke test)")
    ap.add_argument("--groups", help="comma-separated command groups, e.g. int_cmd,swi_cmd")
    ap.add_argument("--dry-run", action="store_true", help="enumerate only")
    args = ap.parse_args()

    if not DB.exists():
        print(f"ck.db not found at {DB}", file=sys.stderr)
        return 2
    if args.products:
        products = [p.strip() for p in args.products.split(",") if p.strip()]
    elif args.all:
        print("discovering command references…")
        products = list_products()
        print(f"  found {len(products)}")
    else:
        ap.error("pass --products <list> or --all")
    groups = {g.strip() for g in args.groups.split(',')} if args.groups else None
    return harvest(products, args.jobs, args.dry_run, args.limit, groups)


if __name__ == "__main__":
    sys.exit(main())
