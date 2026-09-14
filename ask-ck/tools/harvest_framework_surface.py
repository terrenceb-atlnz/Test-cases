#!/usr/bin/env python3
"""Re-harvest the `framework_surface` document — the framework vocabulary the PyTest Creator's
prompts and lints read from ck.db (`json_docs.framework_surface`) — and add the one thing the
original harvest never recorded: the FIELDS of every scapy layer in `framework.ATPackets`.

WHY (D4 of ask-ck/plans/PLAN-fix-units-guardrails.md, 2026-09-15): fix run 5's tc6 read
`getattr(basicLayer, 'port_desc', None)` off `lldp_basic`, a layer with no such field. The
default made the read silently None and the test passed on nothing. The surface doc knew the
layer only as a class with one `guess_payload_class` method, so no check could tell a real
field from a fabricated one. Every `Packet` subclass in ATPackets declares its fields in an
AST-extractable `fields_desc = [ Field('name', …), … ]`, so the list is cheap and authoritative.
`_lint_layer_fields` in routers/pytest_create.py reads `classes[<layer>].fields` from the doc
and stays silent for any layer that has no list.

SOURCE. The surface has always been harvested from the human-owned NFS clone of the framework
(`build_script_index.FRAMEWORK_DIR` = <testbox_home>/DeviceSkrips/framework) — never from a
testbox: `/home/st-art/framework` exists only on the boxes. On 2026-09-14 that clone's
`ATPackets.py` was byte-identical to tb470's (md5 0d0828393885c098…), while its `ATTestSet.py`
lagged the box by seven months. So pass `--framework` explicitly when the source matters, and
treat the clone as authoritative only where a checksum says so.

WRITING. The doc is a RENEWABLE reference (the same class as `cli_commands`, see
load_cli_docs_from_zips.py), not one of the built-once corpora, so replacing it does not touch
the ck.db immutability invariant. But ck.db is WAL-mode and the hosted server holds it open:
**stop the service, write, start it** (`ck off` → this tool → `ck on`), never write under a
running server (the 2026-09-10 corruption chain). `--write` therefore requires an explicit
`--db`; the default action is a read-only diff against the current doc.

Usage:
  python3 ask-ck/tools/harvest_framework_surface.py                    # diff vs the current doc, read-only
  python3 ask-ck/tools/harvest_framework_surface.py --out /tmp/x.json  # also dump the new payload
  python3 ask-ck/tools/harvest_framework_surface.py --framework /path/to/framework
  python3 ask-ck/tools/harvest_framework_surface.py --write --db ask-ck/db/ck.db   # SERVER STOPPED
"""
from __future__ import annotations

import argparse
import ast
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[1]                                   # ask-ck/tools/ -> repo root
DEFAULT_DB = REPO / "ask-ck" / "db" / "ck.db"
sys.path.insert(0, str(TOOLS))
import build_script_index as bsi  # noqa: E402  (the same extraction the original harvest used)

DOC_NAME = "framework_surface"


def fields_desc_of(cls: ast.ClassDef) -> Optional[List[str]]:
    """The field names a scapy `fields_desc` declares, in declaration order — or None when the
    class has no `fields_desc`, or it is not a plain list of `Field('name', …)` calls (a computed
    list would need scapy to evaluate, and a guessed list would make the lint lie)."""
    for node in cls.body:
        if not (isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "fields_desc" for t in node.targets)):
            continue
        if not isinstance(node.value, (ast.List, ast.Tuple)):
            return None
        out: List[str] = []
        for el in node.value.elts:
            if (isinstance(el, ast.Call) and el.args and isinstance(el.args[0], ast.Constant)
                    and isinstance(el.args[0].value, str)):
                out.append(el.args[0].value)
            else:
                return None                              # one unresolvable entry → no list at all
        return out
    return None


def layer_fields_from_source(source: str) -> Dict[str, List[str]]:
    """{class: [fields]} for every top-level class with an extractable `fields_desc`."""
    out: Dict[str, List[str]] = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.ClassDef):
            fields = fields_desc_of(node)
            if fields is not None:
                out[node.name] = fields
    return out


def harvest(framework_dir: Path) -> dict:
    """The original surface (classes + methods + functions per module) plus `fields` on every
    class that declares a `fields_desc`."""
    bsi.FRAMEWORK_DIR = framework_dir
    surface = bsi.build_framework_surface()
    if not surface:
        raise SystemExit(f"nothing harvested from {framework_dir} — is that the framework tree?")
    for mod, rec in surface.items():
        if rec.get("parse_error"):
            continue
        path = framework_dir / (mod.replace(".", "/") + ".py")
        try:
            fields = layer_fields_from_source(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError):
            continue
        for cls, flist in fields.items():
            if cls in rec.get("classes", {}):
                rec["classes"][cls]["fields"] = flist
    return surface


def current_doc(db_path: Path) -> Optional[dict]:
    if not db_path.exists():
        return None
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        row = conn.execute("SELECT payload FROM json_docs WHERE name=?", (DOC_NAME,)).fetchone()
    finally:
        conn.close()
    return json.loads(row[0]) if row else None


def describe_diff(old: Optional[dict], new: dict) -> List[str]:
    lines: List[str] = []
    old = old or {}
    added = sorted(set(new) - set(old))
    gone = sorted(set(old) - set(new))
    lines.append(f"modules: {len(old)} -> {len(new)}"
                 + (f"; added {added}" if added else "") + (f"; GONE {gone}" if gone else ""))
    n_fields = sum(1 for rec in new.values() for c in rec.get("classes", {}).values() if c.get("fields"))
    lines.append(f"classes with a field list: {n_fields}")
    for mod in sorted(set(old) & set(new)):
        oc, nc = old[mod].get("classes", {}), new[mod].get("classes", {})
        if set(oc) != set(nc):
            lines.append(f"  {mod}: classes {sorted(set(oc) ^ set(nc))} differ")
        for cls in sorted(set(oc) & set(nc)):
            om = [m["name"] for m in oc[cls].get("methods", [])]
            nm = [m["name"] for m in nc[cls].get("methods", [])]
            if om != nm:
                lines.append(f"  {mod}.{cls}: methods changed")
            if (oc[cls].get("fields") or None) != (nc[cls].get("fields") or None):
                lines.append(f"  {mod}.{cls}: fields {len(oc[cls].get('fields') or [])} -> "
                             f"{len(nc[cls].get('fields') or [])}")
    return lines


def write_doc(db_path: Path, payload: dict) -> str:
    stamp = datetime.now().isoformat()
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("INSERT OR REPLACE INTO json_docs (name, payload, updated_at) VALUES (?, ?, ?)",
                     (DOC_NAME, json.dumps(payload), stamp))
        conn.commit()
    finally:
        conn.close()
    return stamp


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--framework", type=Path, default=bsi.FRAMEWORK_DIR,
                    help=f"framework tree to read (default: {bsi.FRAMEWORK_DIR})")
    ap.add_argument("--db", type=Path, default=None,
                    help=f"ck.db to diff against (read-only; default {DEFAULT_DB}); REQUIRED with --write")
    ap.add_argument("--out", type=Path, help="also dump the new payload as JSON here")
    ap.add_argument("--write", action="store_true",
                    help="replace json_docs.framework_surface in --db. The hosted server MUST be stopped.")
    args = ap.parse_args(argv)

    if not args.framework.is_dir():
        print(f"framework tree not found: {args.framework}", file=sys.stderr)
        return 2
    new = harvest(args.framework)
    db = args.db or DEFAULT_DB
    old = current_doc(db)
    print(f"harvested {args.framework}")
    for line in describe_diff(old, new):
        print(line)
    if args.out:
        args.out.write_text(json.dumps(new, indent=1, sort_keys=True))
        print(f"payload written to {args.out}")
    if args.write:
        if args.db is None:
            print("--write needs an explicit --db (the hosted server must be stopped first)", file=sys.stderr)
            return 2
        stamp = write_doc(args.db, new)
        print(f"json_docs.{DOC_NAME} replaced in {args.db} (updated_at {stamp})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
