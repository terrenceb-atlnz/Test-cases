#!/usr/bin/env python3
"""Load the AlliedWare Plus CLI reference into ck.db from the AUTHORITATIVE per-device ZIP
archives at docs.atlnz.lc/preview/data/<device>.zip — REPLACING the rows that
tool/harvest_cli_docs.py produced by scraping the live HTML.

WHY replace the scrape: the live-page scrape kept only <pre> blocks, which dropped the
per-port-type speed VALIDITY TABLE and the Overview/Default/Usage-notes prose — exactly the
boundary context the PyTest logic-gate needs ("all supported speeds" = the CLI-defined
permutation set, bounded by media). The /data/ zips are the clean, complete, per-DEVICE
build of every command page (~17 KB each, not the 630 KB nav-bloated live pages), so they
carry those tables + notes AND the per-platform command variants a single global scrape
blurred (e.g. one platform's `duplex {auto|full|half}` vs another's `{auto|full}`).

`cli_commands` is a RENEWABLE reference table — content-addressed, with its own writer, and
NOT one of the built-once corpora — so replacing it in place does NOT touch the ck.db
immutability invariant (that governs zephyr/testlink/atp/scripts). This loader DROPs +
recreates cli_commands / cli_command_products / _fts with two ADDED columns, `tables` (JSON)
and `notes` (JSON), repopulates content-addressed, and rebuilds FTS.

It reuses harvest_cli_docs.py's pre_blocks / classify / command_name unchanged, so
`syntax` / `examples` / `sample_output` stay byte-identical to what cli_lookup, the generate
prompts, and the CLI-docs tests already expect. The FTS column set is left identical too
(command, cmd_group, syntax, sample_output) so search behaviour does not shift.

CAVEAT unchanged (memory: awplus-speed-duplex-constraint): cross-command physical rules
(half-duplex impossible >=1 Gig) are NOT in this source and never will be — under the
best-effort permutation model that is fine, the device reveals it at runtime.

Usage:
  python3 tool/load_cli_docs_from_zips.py --download --all       # fetch 37 zips + load all
  python3 tool/load_cli_docs_from_zips.py --zip-dir DIR --all    # load from local zips
  python3 tool/load_cli_docs_from_zips.py --download --products x530,x930
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parent.parent
DB = REPO / "ask-ck" / "var" / "ck.db"
DATA_BASE = "https://docs.atlnz.lc/preview/data"

# Reuse the scrape harvester's proven parsers so downstream output is identical.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import harvest_cli_docs as H  # noqa: E402

# `_cmds?`, not `_cmd` (2026-09-08): the doc build names two groups `ping_cmds/` and
# `sflow_cmds/` — 36 command pages, `ping` and `traceroute` among them, that a `_cmd`-only
# match skipped silently in every load before this one.
_ZIP_ENTRY_RX = re.compile(r"(?:^|/)([a-z0-9][a-z0-9_\-]*_cmds?)/([^/]+\.html)$", re.I)
# "This command is available on AR1050, AR3050, ... x908Gen3 and x980." — every page of the
# combined build carries this sentence; it is the per-product membership the per-device zips
# encoded in their file names.
_AVAILABLE_ON_RX = re.compile(r"available on\s+(.+?)\.(?:\s|<|$)", re.S | re.I)
_PRODUCT_TOKEN_RX = re.compile(r"[a-z]{1,6}\d[a-z0-9\-]*")
_NO_DIGIT_PRODUCTS = {"vaa", "vfw"}
ALL_PRODUCTS = "*"          # "This command is available on all products." — expanded at load time
# The combined build renders one long output as an HTML table with ONE <pre> PER ROW, so a
# 40-line `show lldp local-info` reply arrives as seven blocks and `classify` (longest block
# wins) hands the prompt the ETS section instead of the labelled LLDP block. Consecutive
# <pre> blocks separated by nothing but cell/row boundaries are one output. 315 of 3,462
# pages in awplus-cmdref-combined.zip are chunked this way (2026-09-08).
# At least ONE cell break is required (`+`, not `*`). With whitespace-only separators
# allowed as well, 2,845 pairs of adjacent SYNTAX variants glued into one block — 25 of them
# long and placeholder-sparse enough that `reclassify` read them as device output (`debug
# lldp`, `terminal monitor`, `clear mac-filter counter`...). Measured 2026-09-08: every one of
# the 280 genuine output rejoins sits behind a cell break. Four pages DO abut real output
# across whitespace alone (show counter dhcp-server, both show scada modbus pages, show
# profinet interface); they stay split — as the July per-device build also left them — and
# the longest piece is still the sample. The other whitespace-only candidates were prompt
# lines the harvest regex misses (a mode name over 31 chars) and wrapped syntax.
_CELL_BREAK_RX = re.compile(r"^\s*(?:</td>\s*</tr>\s*<tr[^>]*>\s*<td[^>]*>\s*)+$", re.S | re.I)
# The opening <pre ...> tag, matched AT a position so its class attribute can be read.
_PRE_OPEN_RX = re.compile(r"<pre([^>]*)>", re.I)
# Per-product visibility class the doc build stamps on a <pre> (and on some table cells):
# `ss-on-x930 ss-on-x950 …`. The one non-product token is `ss-on-none` — a syntax form that
# exists in the schema but ships on no current product; it is dropped, never grounded on.
_SSON_RX = re.compile(r"ss-on-([a-z0-9]+)")
# Syntax <pre> blocks carry this class; examples and device output do not. It is what lets the
# combined build's per-product syntax split (`duplex {auto|full}` on the chassis families vs
# `duplex {auto|full|half}` on the rest) be recovered as separate variant rows.
_SYNTAX_CLASS = "zccmdnamesyntax"


def _pre_blocks_annotated(region: str) -> List[Tuple[str, bool, Optional[frozenset]]]:
    """Merged <pre> blocks as (text, is_syntax, products).

    `products` is a frozenset of the real product names the block's `ss-on-*` classes name
    (with `none` removed), or None when the block carries no `ss-on` class at all — i.e. it
    is shared by every product on the page. A block whose ONLY `ss-on` token was `none`
    yields an EMPTY frozenset, so the caller can tell "shown to no product" from "shared".

    The join rule is identical to `_pre_blocks_merged` (only non-prompt output merges across a
    table-cell break); merged pieces union their product sets and OR their syntax flag.
    """
    out: List[list] = []            # [text, is_syntax, products]
    prev_end: Optional[int] = None
    for m in H._PRE_RX.finditer(region):
        openm = _PRE_OPEN_RX.match(region, m.start())
        attrs = openm.group(1) if openm else ""
        has_sson = "ss-on-" in attrs
        names = set(_SSON_RX.findall(attrs))
        names.discard("none")
        prods = frozenset(names) if has_sson else None
        is_syn = _SYNTAX_CLASS in attrs
        text = unescape(H._TAG_RX.sub("", m.group(1))).strip()
        # Only OUTPUT joins output. A block that is (or contains) a command line is an
        # example step, and gluing it to its neighbour makes `classify` read the next
        # command as this one's reply — measured on the first load: 2,029 rows whose
        # "sample output" was nothing but `awplus(config)# ...` lines.
        joinable = (out and prev_end is not None
                    and _CELL_BREAK_RX.match(region[prev_end:m.start()])
                    and not H._PROMPT_ANY_RX.search(text)
                    and not H._PROMPT_ANY_RX.search(out[-1][0]))
        if joinable:
            out[-1][0] = out[-1][0] + "\n" + text
            a = out[-1][2]
            if a is None and prods is None:
                merged = None
            elif a is None:
                merged = prods
            elif prods is None:
                merged = a
            else:
                merged = a | prods
            out[-1][2] = merged
            out[-1][1] = out[-1][1] or is_syn
        else:
            out.append([text, is_syn, prods])
        prev_end = m.end()
    return [(t, s, p) for t, s, p in out]


def _pre_blocks_merged(region: str) -> List[str]:
    """H.pre_blocks(), but joining a run of <pre> blocks that the build split across table
    rows back into the single output it was. The flat text list; `_pre_blocks_annotated`
    carries the per-block syntax/product metadata the combined-zip split needs."""
    return [t for t, _, _ in _pre_blocks_annotated(region)]


def _available_on(region: str) -> List[str]:
    """Lower-cased product names the page says the command is available on; [] if absent."""
    txt = unescape(re.sub(r"<[^>]+>", " ", region))
    m = _AVAILABLE_ON_RX.search(txt)
    if not m:
        return []
    if re.match(r"\s*all\s+products", m.group(1), re.I):
        return [ALL_PRODUCTS]
    out: List[str] = []
    for part in re.split(r",\s*|\s+and\s+", m.group(1)):
        t = part.strip().lower().rstrip(".")
        if (t and (_PRODUCT_TOKEN_RX.fullmatch(t) or t in _NO_DIGIT_PRODUCTS)) and t not in out:
            out.append(t)
    return out
_ARTICLE_RX = re.compile(r"<article\b.*?</article>", re.S | re.I)
_TABLE_RX = re.compile(r"<table\b.*?</table>", re.S | re.I)
_TR_RX = re.compile(r"<tr\b.*?</tr>", re.S | re.I)
_CELL_RX = re.compile(r"<t[hd]\b.*?</t[hd]>", re.S | re.I)
_P_RX = re.compile(r"<p\b[^>]*>(.*?)</p>", re.S | re.I)
_SECTION_RX = re.compile(r"<section\b[^>]*>(.*?)</section>", re.S | re.I)
_H2_RX = re.compile(r"<h2\b[^>]*>(.*?)</h2>", re.S | re.I)

# Sections whose body IS the <pre> blocks we already capture via classify(); keep the rest
# (Overview / Mode / Default / Usage notes / Related commands / Command changes …) as notes.
_SKIP_SECTIONS = {"syntax", "examples"}


SCHEMA = """
DROP TABLE IF EXISTS cli_commands_fts;
DROP TABLE IF EXISTS cli_command_products;
DROP TABLE IF EXISTS cli_commands;
CREATE TABLE cli_commands (
  content_sha   TEXT PRIMARY KEY,   -- sha256 of [pre_blocks, tables, notes] (dedupe key)
  command       TEXT,               -- 'show interface status'
  page          TEXT,               -- 'int_cmd/show_interface_status.html' (product-relative)
  cmd_group     TEXT,               -- 'int_cmd'
  syntax        TEXT,               -- JSON array of syntax lines
  examples      TEXT,               -- JSON array of {cmd, output}
  sample_output TEXT,               -- richest output block, for prompt injection
  pre_blocks    TEXT,               -- JSON array: every <pre> block, verbatim
  n_blocks      INTEGER,
  tables        TEXT,               -- NEW: JSON array of tables (rows of cell text) — validity/parameter tables
  notes         TEXT,               -- NEW: JSON object {section heading: prose text}
  harvested_at  TEXT
);
CREATE TABLE cli_command_products (
  page        TEXT NOT NULL,
  product     TEXT NOT NULL,
  content_sha TEXT NOT NULL,
  PRIMARY KEY (page, product)
);
CREATE INDEX idx_cli_cmd_page ON cli_commands(page);
CREATE INDEX idx_cli_cmd_command ON cli_commands(command);
CREATE INDEX idx_cli_prod_sha ON cli_command_products(content_sha);
-- FTS column set kept IDENTICAL to the scrape build so search behaviour does not shift.
CREATE VIRTUAL TABLE cli_commands_fts USING fts5(
  command, cmd_group, syntax, sample_output,
  content='cli_commands', content_rowid='rowid',
  tokenize="unicode61 remove_diacritics 2 tokenchars '.-+'", prefix='2 3'
);
"""


# --------------------------------------------------------------------------- parse

def _clean(fragment: str) -> str:
    return re.sub(r"\s+", " ", unescape(H._TAG_RX.sub(" ", fragment))).strip()


def _cell_text(cell: str) -> str:
    """A table cell's text. Multi-value cells hold one <p> per value (auto/10/100/1000);
    join them with ', ' so the value list survives for the logic-gate to parse."""
    ps = _P_RX.findall(cell)
    parts = [_clean(p) for p in ps] if ps else [_clean(cell)]
    return ", ".join(p for p in parts if p)


def extract_tables(region: str) -> List[List[List[str]]]:
    out: List[List[List[str]]] = []
    for tb in _TABLE_RX.findall(region):
        rows = []
        for tr in _TR_RX.findall(tb):
            cells = [_cell_text(c) for c in _CELL_RX.findall(tr)]
            if any(cells):
                rows.append(cells)
        if rows:
            out.append(rows)
    return out


def extract_notes(region: str) -> Dict[str, str]:
    notes: Dict[str, str] = {}
    for sec in _SECTION_RX.findall(region):
        h = _H2_RX.search(sec)
        if not h:
            continue
        title = _clean(h.group(1))
        if not title or title.lower() in _SKIP_SECTIONS:
            continue
        body = sec[h.end():]
        body = re.sub(r"<pre\b.*?</pre>", " ", body, flags=re.S | re.I)
        body = re.sub(r"<table\b.*?</table>", " ", body, flags=re.S | re.I)
        txt = _clean(body)
        if txt:
            notes[title] = txt
    return notes


def _row_from(page: str, blocks: List[str], tables: list, notes: dict,
              products: List[str]) -> dict:
    """Assemble one cli_commands row from a set of <pre> blocks + tables + notes.

    `content_sha` is over [blocks, tables, notes], so two product-groups that differ only in
    their syntax block get distinct rows (and distinct shas), while identical content across
    products still dedupes to one row in `store()`."""
    syntax, examples, sample = H.classify(blocks)
    body = json.dumps([blocks, tables, notes], sort_keys=True, ensure_ascii=False)
    return {
        "content_sha": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "products": products,
        "command": H.command_name(page),
        "page": page,
        "cmd_group": page.split("/")[0],
        "syntax": syntax,
        "examples": examples,
        "sample_output": sample,
        "pre_blocks": blocks,
        "tables": tables,
        "notes": notes,
    }


def parse_page(page: str, html: str) -> Optional[dict]:
    """Parsed row, or None for a soft-404 / non-command page.

    A real command page carries at least a <pre> syntax block or a validity table; pure
    index/intro pages (prose only) are skipped, matching the scrape harvester's behaviour.
    Per-device path: the whole page is one row; `products` is the page's 'available on'
    sentence (the per-device caller overrides it with the zip's own device)."""
    if H._SOFT404_RX.search(html[:4000]):
        return None
    m = _ARTICLE_RX.search(html)
    region = m.group(0) if m else html   # /data/ pages are lean; article is the whole content
    blocks = _pre_blocks_merged(region)
    tables = extract_tables(region)
    if not blocks and not tables:
        return None
    notes = extract_notes(region)
    return _row_from(page, blocks, tables, notes, _available_on(region))


def combined_page_rows(page: str, html: str) -> List[dict]:
    """The combined build's rows for one page: ONE row per product-group.

    A page whose syntax is uniform across its products yields a single row (the common case,
    incl. `show interface`). A page that ships a different syntax form per product family
    (`duplex`: `{auto|full}` on the chassis families, `{auto|full|half}` on the rest) yields
    one row per distinct family group, so the per-family variant comparison the read path and
    prompts rely on is preserved — the same shape the July per-device zips produced.

    Grouping is by product-specific SYNTAX blocks only (`zccmdnamesyntax` + `ss-on-*`). Every
    group also carries the page's shared blocks (examples, device output, non-`ss-on` syntax)
    and the shared tables + notes; product-specific NON-syntax blocks and per-product table
    cells are treated as shared (see the plan's deferred B2). A syntax block shown to no
    product (`ss-on-none` only) is dropped.
    """
    if H._SOFT404_RX.search(html[:4000]):
        return []
    m = _ARTICLE_RX.search(html)
    region = m.group(0) if m else html
    ann = _pre_blocks_annotated(region)
    # Drop blocks shown to no product (an ss-on class that was `none`-only -> empty set).
    ann = [(t, s, p) for (t, s, p) in ann if not (p is not None and len(p) == 0)]
    tables = extract_tables(region)
    if not ann and not tables:
        return []
    notes = extract_notes(region)
    avail = _available_on(region)

    # Indices of the product-specific syntax blocks, and the products they name.
    spec = [(i, p) for i, (t, s, p) in enumerate(ann) if s and p]     # p is a non-empty set
    if not spec:
        blocks = [t for t, _, _ in ann]
        return [_row_from(page, blocks, tables, notes, avail)]        # single row, unchanged

    shared_idx = [i for i, (t, s, p) in enumerate(ann) if (i not in {j for j, _ in spec})]
    named = frozenset().union(*[p for _, p in spec])
    # "available on all products" (or no sentence) alongside a split: the ss-on classes are
    # the only concrete product list, so the named union IS the universe.
    universe = named if (avail == [ALL_PRODUCTS] or not avail) else (frozenset(avail) | named)

    groups: Dict[tuple, set] = {}
    for prod in named:
        vis = tuple(i for i, p in spec if prod in p)                  # which variant(s) it sees
        groups.setdefault(vis, set()).add(prod)

    # Products the page lists as available but that NO syntax block tags (thrash-limiting
    # names 29 in its sentence, 25 on the block). A syntax-less row for them would be worse
    # than the common form, so fold them into the largest variant group — the best single
    # guess at the default. Deferred refinement: attribute them from a per-product table.
    extra = universe - named
    if extra:
        biggest = max(groups, key=lambda v: len(groups[v]))
        groups[biggest] |= extra

    rows: List[dict] = []
    for vis, prods in groups.items():
        idxs = sorted(set(vis) | set(shared_idx))
        blocks = [ann[i][0] for i in idxs]
        rows.append(_row_from(page, blocks, tables, notes, sorted(prods)))
    return rows


# --------------------------------------------------------------------------- zip I/O

def list_zip_products() -> List[str]:
    r = subprocess.run(["curl", "-sS", "--max-time", "30", f"{DATA_BASE}/"],
                       capture_output=True, text=True)
    names = re.findall(r'href="([A-Za-z0-9_\-]+)\.zip"', r.stdout or "")
    return sorted(set(names))


def download_zip(product: str, zip_dir: Path) -> Optional[Path]:
    dest = zip_dir / f"{product}.zip"
    if dest.exists() and dest.stat().st_size > 1000:
        return dest
    r = subprocess.run(["curl", "-sS", "--max-time", "180", "-L", "-o", str(dest),
                        f"{DATA_BASE}/{product}.zip"], capture_output=True, text=True)
    if r.returncode != 0 or not dest.exists() or dest.stat().st_size < 1000:
        print(f"  ! download failed: {product} ({r.stderr.strip()[:120]})")
        return None
    return dest


def parse_zip(product: str, path: Path) -> List[dict]:
    rows: List[dict] = []
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            m = _ZIP_ENTRY_RX.search(name)
            if not m:
                continue
            page = f"{m.group(1)}/{m.group(2)}"   # product-relative: 'swi_cmd/speed_ak.html'
            try:
                html = z.read(name).decode("utf-8", errors="replace")
            except Exception:
                continue
            parsed = parse_page(page, html)
            if parsed:
                rows.append(parsed)
    return rows


def parse_combined_zip(path: Path) -> List[dict]:
    """Every page of the combined archive, flattened to one row per product-group.

    Single-syntax pages keep the page's 'available on' `products` (`['*']` / [] / explicit),
    so main()'s universe/fallback expansion still applies to them; split pages arrive with a
    concrete per-group product list already resolved."""
    rows: List[dict] = []
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            m = _ZIP_ENTRY_RX.search(name)
            if not m:
                continue
            page = f"{m.group(1)}/{m.group(2)}"
            try:
                html = z.read(name).decode("utf-8", errors="replace")
            except Exception:
                continue
            rows.extend(combined_page_rows(page, html))
    return rows


# --------------------------------------------------------------------------- store

def store(conn: sqlite3.Connection, rows: List[Tuple[str, dict]]) -> Tuple[int, int]:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    seen = set()
    n_content = 0
    for product, p in rows:
        if p["content_sha"] not in seen:
            seen.add(p["content_sha"])
            conn.execute(
                "INSERT OR REPLACE INTO cli_commands (content_sha, command, page, cmd_group, "
                "syntax, examples, sample_output, pre_blocks, n_blocks, tables, notes, "
                "harvested_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (p["content_sha"], p["command"], p["page"], p["cmd_group"],
                 json.dumps(p["syntax"]), json.dumps(p["examples"]), p["sample_output"],
                 json.dumps(p["pre_blocks"]), len(p["pre_blocks"]),
                 json.dumps(p["tables"], ensure_ascii=False),
                 json.dumps(p["notes"], ensure_ascii=False), now))
            n_content += 1
        conn.execute(
            "INSERT OR REPLACE INTO cli_command_products (page, product, content_sha) "
            "VALUES (?,?,?)", (p["page"], product, p["content_sha"]))
    return n_content, len(rows)


# --------------------------------------------------------------------------- driver

def main() -> int:
    ap = argparse.ArgumentParser(description="Load the AW+ CLI reference into ck.db from the /data/ zips")
    ap.add_argument("--products", help="comma-separated device names (default: all in the index)")
    ap.add_argument("--all", action="store_true", help="every device zip in the index")
    ap.add_argument("--zip-dir", default=None, help="where zips are / will be cached")
    ap.add_argument("--download", action="store_true", help="fetch missing zips from the data index")
    ap.add_argument("--combined-zip", default=None,
                    help="ONE combined reference archive (a single <group>_cmd/<page>.html tree, "
                         "no per-device split, e.g. awplus-cmdref-combined.zip). Hard-overwrites "
                         "cli_commands with its pages; product membership is read from each "
                         "page's 'This command is available on ...' sentence. Same entry regex "
                         "and parsers as the per-device path, so the row shape is identical. "
                         "Trade-off: a combined build is SINGLE-VARIANT (one page per command), "
                         "so the per-family variant comparison the per-device zips fed is gone.")
    ap.add_argument("--product-fallback", default="awplus",
                    help="--combined-zip: label for a page with no 'available on' sentence")
    ap.add_argument("--db", default=None, help=f"database to write (default {DB}); a scratch copy for a dry run")
    args = ap.parse_args()
    db_path = Path(args.db) if args.db else DB

    if not db_path.exists():
        print(f"ck.db not found at {db_path}", file=sys.stderr)
        return 2

    if args.combined_zip:
        cz = Path(args.combined_zip)
        if not cz.exists():
            print(f"combined zip not found at {cz}", file=sys.stderr)
            return 2
        rows = parse_combined_zip(cz)            # one row per product-group per page
        if not rows:
            print("no rows parsed — nothing written")
            return 1
        universe = sorted({p for r in rows for p in r.get("products") or [] if p != ALL_PRODUCTS})
        pairs = []
        n_fallback = n_all = 0
        for r in rows:
            prods = r.get("products") or []
            if prods == [ALL_PRODUCTS]:
                prods, n_all = universe, n_all + 1
            elif not prods:
                prods, n_fallback = [args.product_fallback], n_fallback + 1
            pairs += [(prod, r) for prod in prods]
        products = sorted({prod for prod, _ in pairs})
        print(f"  {cz.name}: {len(rows)} command pages, {len(products)} products; "
              f"{n_all} page(s) 'available on all products' -> all {len(universe)}, "
              f"{n_fallback} page(s) with no sentence -> {args.product_fallback!r}")
        conn = sqlite3.connect(db_path)
        conn.executescript(SCHEMA)               # DROP + recreate: the hard overwrite
        n_content, n_pairs = store(conn, pairs)
        conn.execute("INSERT INTO cli_commands_fts(cli_commands_fts) VALUES('rebuild')")
        stamp = {
            "loaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": f"combined archive {cz.name} ({cz.stat().st_size} bytes)",
            "single_variant": False,
            "products": products,
            "product_fallback": args.product_fallback,
            "note": "one combined reference build (no per-device split); cli_commands hard-"
                    "overwritten; product membership parsed from each page's 'available on' "
                    "sentence. Per-family syntax variants are RECOVERED from the build's "
                    "ss-on-<product> classes: a page ships one row per syntax group (duplex "
                    "-> {auto|full} on 8 chassis families, {auto|full|half} on 25).",
        }
        conn.execute("INSERT OR REPLACE INTO meta (k, v) VALUES ('cli_docs_load', ?)",
                     (json.dumps(stamp),))
        conn.commit()
        n_cmd = conn.execute("SELECT COUNT(*) FROM cli_commands").fetchone()[0]
        n_dc = conn.execute("SELECT COUNT(DISTINCT command) FROM cli_commands").fetchone()[0]
        n_out = conn.execute("SELECT COUNT(*) FROM cli_commands WHERE sample_output IS NOT NULL AND sample_output != ''").fetchone()[0]
        n_map = conn.execute("SELECT COUNT(*) FROM cli_command_products").fetchone()[0]
        conn.close()
        print(f"\nhard-overwrote cli_commands in {db_path.name} from {cz.name}:")
        print(f"  cli_commands          {n_cmd:>6} content blobs, {n_dc} distinct commands, {n_out} with sample output")
        print(f"  cli_command_products  {n_map:>6} product×command rows over {len(products)} products")
        return 0

    zip_dir = Path(args.zip_dir) if args.zip_dir else (REPO / "ask-ck" / "var" / "cli_zips")
    zip_dir.mkdir(parents=True, exist_ok=True)

    if args.products:
        products = [p.strip() for p in args.products.split(",") if p.strip()]
    elif args.all or args.download:
        products = list_zip_products()
        print(f"index lists {len(products)} device zip(s)")
    else:
        ap.error("pass --products <list> or --all")
        return 2

    all_rows: List[Tuple[str, dict]] = []
    devices_loaded = 0
    for prod in products:
        path = download_zip(prod, zip_dir) if args.download else (zip_dir / f"{prod}.zip")
        if not path or not path.exists():
            print(f"  {prod:<12} MISSING (pass --download, or check --zip-dir)")
            continue
        rows = parse_zip(prod, path)
        print(f"  {prod:<12} {len(rows):>5} command pages")
        all_rows += [(prod, r) for r in rows]
        devices_loaded += 1

    if not all_rows:
        print("no rows parsed — nothing written")
        return 1

    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    n_content, n_pairs = store(conn, all_rows)
    conn.execute("INSERT INTO cli_commands_fts(cli_commands_fts) VALUES('rebuild')")
    stamp = {
        "loaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": f"{DATA_BASE}/<device>.zip",
        "devices": devices_loaded,
        "products": products,
        "note": "authoritative per-device zips; replaced the live-HTML scrape (adds tables+notes)",
    }
    conn.execute("INSERT OR REPLACE INTO meta (k, v) VALUES ('cli_docs_load', ?)",
                 (json.dumps(stamp),))
    conn.commit()

    n_cmd = conn.execute("SELECT COUNT(*) FROM cli_commands").fetchone()[0]
    n_map = conn.execute("SELECT COUNT(*) FROM cli_command_products").fetchone()[0]
    n_out = conn.execute("SELECT COUNT(*) FROM cli_commands WHERE sample_output IS NOT NULL").fetchone()[0]
    n_tab = conn.execute("SELECT COUNT(*) FROM cli_commands WHERE tables IS NOT NULL AND tables != '[]'").fetchone()[0]
    n_note = conn.execute("SELECT COUNT(*) FROM cli_commands WHERE notes IS NOT NULL AND notes != '{}'").fetchone()[0]
    conn.close()
    print(f"\nloaded {devices_loaded} device(s), {n_pairs} product×command pairs")
    print(f"  cli_commands          {n_cmd:>6} unique content blobs "
          f"({n_out} with sample output, {n_tab} with tables, {n_note} with notes)")
    print(f"  cli_command_products  {n_map:>6} product×command rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
