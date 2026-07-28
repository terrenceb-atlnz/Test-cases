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

_ZIP_ENTRY_RX = re.compile(r"(?:^|/)([a-z0-9][a-z0-9_\-]*_cmd)/([^/]+\.html)$", re.I)
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


def parse_page(page: str, html: str) -> Optional[dict]:
    """Parsed row, or None for a soft-404 / non-command page.

    A real command page carries at least a <pre> syntax block or a validity table; pure
    index/intro pages (prose only) are skipped, matching the scrape harvester's behaviour."""
    if H._SOFT404_RX.search(html[:4000]):
        return None
    m = _ARTICLE_RX.search(html)
    region = m.group(0) if m else html   # /data/ pages are lean; article is the whole content
    blocks = H.pre_blocks(region)
    tables = extract_tables(region)
    if not blocks and not tables:
        return None
    notes = extract_notes(region)
    syntax, examples, sample = H.classify(blocks)
    body = json.dumps([blocks, tables, notes], sort_keys=True, ensure_ascii=False)
    return {
        "content_sha": hashlib.sha256(body.encode("utf-8")).hexdigest(),
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
    args = ap.parse_args()

    if not DB.exists():
        print(f"ck.db not found at {DB}", file=sys.stderr)
        return 2

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

    conn = sqlite3.connect(DB)
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
