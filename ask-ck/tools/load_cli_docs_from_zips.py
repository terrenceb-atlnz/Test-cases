#!/usr/bin/env python3
"""Load the AlliedWare Plus CLI reference into ck.db from the AUTHORITATIVE per-device ZIP
archives at docs.atlnz.lc/preview/data/<device>.zip — REPLACING the rows that
ask-ck/tools/harvest_cli_docs.py produced by scraping the live HTML.

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
  python3 ask-ck/tools/load_cli_docs_from_zips.py --download --all       # fetch 37 zips + load all
  python3 ask-ck/tools/load_cli_docs_from_zips.py --zip-dir DIR --all    # load from local zips
  python3 ask-ck/tools/load_cli_docs_from_zips.py --download --products x530,x930
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

REPO = Path(__file__).resolve().parents[2]  # ask-ck/tools/ -> repo root
DB = REPO / "ask-ck" / "db" / "ck.db"
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
    """Merged <pre> blocks as (text, is_syntax, products) — `_pre_blocks_full` without the
    section."""
    return [(t, s, p) for t, s, p, _ in _pre_blocks_full(region)]


def _pre_blocks_full(region: str) -> List[Tuple[str, bool, Optional[frozenset], Optional[str]]]:
    """Merged <pre> blocks as (text, is_syntax, products, section).

    `section` is the heading of the page section the block sits in ("Syntax", "Example",
    "Output", …), or None before any heading. It is what `classify` uses to keep an example
    reply, a mode prompt or device output out of `syntax` (2026-09-24: ~500 such blocks were
    filed as syntax by the shape heuristic alone). A merged block keeps its first piece's.

    `products` is a frozenset of the real product names in force for the block — its own
    `ss-on-*` classes, else its nearest scoped container's — with `none` removed, or None when
    neither is scoped, i.e. it is shared by every product on the page. A block whose only
    token was `none` yields an EMPTY frozenset, so the caller can tell "shown to no product"
    from "shared".

    The join rule is identical to `_pre_blocks_merged` (only non-prompt output merges across a
    table-cell break); merged pieces union their product sets and OR their syntax flag.
    """
    out: List[list] = []            # [text, is_syntax, products, section]
    heads = [(h.start(), _clean(h.group(1))) for h in _H2_RX.finditer(region)]
    scopes = _element_scopes(region, "pre")
    prev_end: Optional[int] = None
    for m in H._PRE_RX.finditer(region):
        section = next((t for pos, t in reversed(heads) if pos <= m.start()), None)
        openm = _PRE_OPEN_RX.match(region, m.start())
        attrs = openm.group(1) if openm else ""
        # The block's own class, else its container's (2026-09-24): 5,200 blocks are scoped
        # only by a wrapping <div>/<section>, and read as shared they put router-only examples
        # and output in front of every product.
        scope = scopes.get(m.start())
        prods = frozenset(scope - {"none"}) if scope is not None else None
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
            out.append([text, is_syn, prods, section])
        prev_end = m.end()
    return [(t, s, p, sec) for t, s, p, sec in out]


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
  pre_sections  TEXT,               -- JSON array: the page-section heading of each block (2026-09-24)
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


# Any opening tag, so an element's class attribute can be read wherever it sits in a table.
_OPEN_TAG_RX = re.compile(r"<([a-z][a-z0-9]*)\b([^>]*)>", re.I)


def _none_only(attrs: str) -> bool:
    """True when an element's `ss-on-*` classes name NO real product (only `ss-on-none`)."""
    names = set(_SSON_RX.findall(attrs))
    return bool(names) and names == {"none"}


def _element_end(fragment: str, tag: str, pos: int) -> int:
    """Index just past the `</tag>` that closes an element whose opening tag ends at `pos`
    (same-name nesting counted). An unclosed element runs to the end of the fragment."""
    rx = re.compile(rf"<(/?){tag}\b[^>]*>", re.I)
    depth = 1
    for m in rx.finditer(fragment, pos):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return m.end()
    return len(fragment)


def _drop_none_only(fragment: str) -> str:
    """The fragment with every element shown to no product removed, content and all.

    The build keeps a parameter that ships on no current product in the table, tagged
    `ss-on-none` and labelled "[Not available on any product]" — on a whole table, a row, or
    a value inside a cell. Flattened, it read as a legal value, and three such tables reached
    the prompt. Syntax blocks shown to no product were already dropped; this is the same rule
    for tables."""
    out: List[str] = []
    i = 0
    while True:
        m = _OPEN_TAG_RX.search(fragment, i)
        if not m:
            out.append(fragment[i:])
            return "".join(out)
        if _none_only(m.group(2)):
            out.append(fragment[i:m.start()])
            i = _element_end(fragment, m.group(1).lower(), m.end())
        else:
            out.append(fragment[i:m.end()])
            i = m.end()


_ANY_TAG_RX = re.compile(r"<(/?)([a-z][a-z0-9]*)\b([^>]*)>", re.I)
_VOID_TAGS = {"br", "img", "col", "hr", "input", "meta", "link", "wbr", "area", "source"}


def _element_scopes(region: str, tag: str) -> Dict[int, Optional[frozenset]]:
    """{start of each <tag> -> the `ss-on-*` names in force there, or None if unscoped}.

    An element's product scope is its OWN class, else the nearest enclosing element's. The
    loader used to read only the element's own class, and flattening lost the rest: 454 tables
    and 5,200 <pre> blocks take their scope from a wrapping <div> or <section> (2026-09-24).
    """
    scopes: Dict[int, Optional[frozenset]] = {}
    stack: List[Tuple[str, Optional[frozenset]]] = []
    for m in _ANY_TAG_RX.finditer(region):
        close, name, attrs = m.group(1), m.group(2).lower(), m.group(3)
        if name in _VOID_TAGS or attrs.rstrip().endswith("/"):
            continue
        if close:
            while stack and stack[-1][0] != name:
                stack.pop()
            if stack:
                stack.pop()
            continue
        own = frozenset(_SSON_RX.findall(attrs)) or None
        if name == tag:
            scopes[m.start()] = own or next((s for _, s in reversed(stack) if s), None)
        stack.append((name, own))
    return scopes


def _table_scopes(region: str) -> Dict[int, Optional[frozenset]]:
    return _element_scopes(region, "table")


def product_label(products) -> str:
    """The build's own attribution style: "[On ar3050, ar4050, arx200]"."""
    return "[On " + ", ".join(sorted(products)) + "]"


def extract_tables(region: str, available: Optional[List[str]] = None) -> List[List[List[str]]]:
    """Every table as rows of cell text.

    A table the build scopes to a subset of products gets a first row holding a product label
    (2026-09-24). Flattening had dropped that scope: `bandwidth` (wireless AP radio) showed a
    20/40/80 MHz table and a 20/40/80/160 MHz table with nothing to say which products take
    160. No label when the scope is the page's whole availability (`available`), and none when
    the table's first cell already carries one. A table scoped to no product is dropped."""
    out: List[List[List[str]]] = []
    scopes = _table_scopes(region)
    page_set = frozenset(available or []) - {ALL_PRODUCTS}
    for m in _TABLE_RX.finditer(region):
        scope = scopes.get(m.start())
        real = (scope or frozenset()) - {"none"}
        if scope and not real:
            continue                                # shown to no product
        tb = _drop_none_only(m.group(0))
        rows = []
        for tr in _TR_RX.findall(tb):
            cells = [_cell_text(c) for c in _CELL_RX.findall(tr)]
            if any(cells):
                rows.append(cells)
        if rows and real and real != page_set and not rows[0][0].startswith("[On "):
            rows.insert(0, [product_label(real)])
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
              products: List[str], sections: Optional[List[Optional[str]]] = None) -> dict:
    """Assemble one cli_commands row from a set of <pre> blocks + tables + notes.

    `content_sha` is over [blocks, tables, notes], so two product-groups that differ only in
    their syntax block get distinct rows (and distinct shas), while identical content across
    products still dedupes to one row in `store()`. `sections` (one heading per block) is
    stored as `pre_sections` and steers `classify`; it is not part of the sha — a page's
    blocks always sit in the same sections."""
    syntax, examples, sample = H.classify(blocks, sections)
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
        "pre_sections": list(sections) if sections is not None else None,
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
    full = _pre_blocks_full(region)
    blocks = [t for t, _, _, _ in full]
    avail = _available_on(region)
    tables = extract_tables(region, avail)
    if not blocks and not tables:
        return None
    notes = extract_notes(region)
    return _row_from(page, blocks, tables, notes, avail, [s for _, _, _, s in full])


def combined_page_rows(page: str, html: str) -> List[dict]:
    """The combined build's rows for one page: ONE row per product-group.

    A page with no product-scoped block yields a single row (the common case). A page that
    ships different content per product family (`duplex`: `{auto|full}` on the chassis
    families, `{auto|full|half}` on the rest; `show interface`: `port1.0.1` vs `eth1` output)
    yields one row per distinct family group, so the per-family variant comparison the read
    path and prompts rely on is preserved — the same shape the July per-device zips produced.

    Grouping is by EVERY product-scoped block (2026-09-24; syntax only before): each product
    sees the shared blocks plus the scoped ones naming it, and products that see the same set
    share a row. The scope is a block's own `ss-on-*` class or, for 5,200 blocks, its
    container's. Before, a scoped example or output block was treated as shared, so a
    router-only `eth1` example reached every switch. Shared tables + notes ride on every row.
    A block or table element shown to no product (`ss-on-none` only) is dropped.
    """
    if H._SOFT404_RX.search(html[:4000]):
        return []
    m = _ARTICLE_RX.search(html)
    region = m.group(0) if m else html
    full = _pre_blocks_full(region)
    # Drop blocks shown to no product (an ss-on class that was `none`-only -> empty set).
    full = [b for b in full if not (b[2] is not None and len(b[2]) == 0)]
    ann = [(t, s, p) for t, s, p, _ in full]
    secs = [sec for _, _, _, sec in full]
    avail = _available_on(region)
    tables = extract_tables(region, avail)
    if not ann and not tables:
        return []
    notes = extract_notes(region)

    # Every product-scoped block, split into syntax (the build's syntax class, or a block in a
    # Syntax section) and the rest (examples, output).
    spec = [(i, p) for i, (t, s, p) in enumerate(ann) if p]           # p is a non-empty set
    if not spec:
        blocks = [t for t, _, _ in ann]
        return [_row_from(page, blocks, tables, notes, avail, secs)]  # single row, unchanged

    def _syntaxy(i: int) -> bool:
        return ann[i][1] or "syntax" in (secs[i] or "").lower()

    spec_syn = [(i, p) for i, p in spec if _syntaxy(i)]
    spec_oth = [(i, p) for i, p in spec if not _syntaxy(i)]
    shared_idx = [i for i, (t, s, p) in enumerate(ann) if p is None]
    named = frozenset().union(*[p for _, p in spec])
    # "Available on all products" alongside a split: every product the classes do not name
    # sees the shared blocks, so they join as ALL_PRODUCTS and main() expands that to the
    # build's products not already on another row of this page. (Taking only the named union,
    # as before, dropped 367 page×product pairs once every scoped block split rows.) No
    # sentence at all: the named union is the only product list there is.
    if avail == [ALL_PRODUCTS]:
        universe = named | {ALL_PRODUCTS}
    elif not avail:
        universe = named
    else:
        universe = frozenset(avail) | named

    # Which scoped syntax form(s) each product sees. Products that NO scoped syntax block tags
    # (thrash-limiting names 29 in its sentence, 25 on the block) take the commonest form: a
    # syntax-less row for them would be worse than the default guess.
    syn_named = frozenset().union(*[p for _, p in spec_syn]) if spec_syn else frozenset()
    syn_vis = {prod: tuple(i for i, p in spec_syn if prod in p) for prod in universe}
    if spec_syn:
        counts: Dict[tuple, int] = {}
        for prod in syn_named:
            counts[syn_vis[prod]] = counts.get(syn_vis[prod], 0) + 1
        common = max(counts, key=lambda v: (counts[v], v))
        for prod in universe - syn_named:
            syn_vis[prod] = common

    groups: Dict[tuple, set] = {}
    for prod in sorted(universe):
        oth = tuple(i for i, p in spec_oth if prod in p)
        groups.setdefault(tuple(sorted(set(syn_vis[prod]) | set(oth))), set()).add(prod)

    rows: List[dict] = []
    for vis, prods in groups.items():
        idxs = sorted(set(vis) | set(shared_idx))
        blocks = [ann[i][0] for i in idxs]
        rows.append(_row_from(page, blocks, tables, notes, sorted(prods),
                              [secs[i] for i in idxs]))
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
                "syntax, examples, sample_output, pre_blocks, pre_sections, n_blocks, tables, "
                "notes, harvested_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (p["content_sha"], p["command"], p["page"], p["cmd_group"],
                 json.dumps(p["syntax"]), json.dumps(p["examples"]), p["sample_output"],
                 json.dumps(p["pre_blocks"]),
                 json.dumps(p["pre_sections"]) if p.get("pre_sections") is not None else None,
                 len(p["pre_blocks"]),
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
        # Products each page's rows name explicitly, so an ALL_PRODUCTS row can take the rest.
        named_on: Dict[str, set] = {}
        for r in rows:
            named_on.setdefault(r["page"], set()).update(
                p for p in r.get("products") or [] if p != ALL_PRODUCTS)
        pairs = []
        n_fallback = n_all = 0
        for r in rows:
            prods = r.get("products") or []
            if ALL_PRODUCTS in prods:
                explicit = [p for p in prods if p != ALL_PRODUCTS]
                prods = sorted(set(explicit) | (set(universe) - named_on[r["page"]]))
                n_all += 1
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

    zip_dir = Path(args.zip_dir) if args.zip_dir else (REPO / "ask-ck" / "db" / "cli_zips")
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
