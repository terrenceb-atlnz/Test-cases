#!/usr/bin/env python3
"""Look up AlliedWare Plus CLI syntax + real sample output from ck.db.

The retrieval half of the CLI-grounding work: `harvest_cli_docs.py` fills the tables,
this reads them. Importable (the generator injects `prompt_block()` output into the
generate prompt) and runnable (spot-check a command by hand).

Grounding matters because every model in the Part 2B matrix — Opus included — invented a
`speed=1000`/`state=up` output schema the switch never prints. Real output is
`current duplex full, current speed 1000, current polarity mdix`.

NOT a validity oracle: cross-command physical constraints are absent from the source
(half duplex is impossible at >=1 Gig, but the x530 `duplex` page lists `half`
unconditionally and neither page says so). Use the ART corpus for those.

Usage:
  python3 tool/cli_lookup.py "show interface"
  python3 tool/cli_lookup.py --product x930 duplex
  python3 tool/cli_lookup.py --search "mdi polarity"
  python3 tool/cli_lookup.py --prompt-block "show interface,speed,duplex"
  python3 tool/cli_lookup.py --stats
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional

REPO = Path(__file__).resolve().parent.parent
DB = REPO / "ask-ck" / "var" / "ck.db"


def _conn() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{DB}?mode=ro", uri=True)


def lookup(command: str, product: Optional[str] = None,
           conn: Optional[sqlite3.Connection] = None) -> List[dict]:
    """Every stored variant of `command`, newest-content first.

    With `product`, returns only the variant THAT product actually ships — the point of
    the support matrix. Without it, returns all variants plus the products sharing each,
    so a caller can see (for example) that `duplex` drops `half` on x930/x950.
    """
    c = conn or _conn()
    if product:
        rows = c.execute(
            "SELECT k.content_sha, k.command, k.page, k.cmd_group, k.syntax, "
            "       k.examples, k.sample_output "
            "FROM cli_commands k JOIN cli_command_products p "
            "  ON p.content_sha = k.content_sha "
            "WHERE k.command = ? AND p.product = ?", (command, product)).fetchall()
    else:
        rows = c.execute(
            "SELECT content_sha, command, page, cmd_group, syntax, examples, "
            "       sample_output FROM cli_commands WHERE command = ?",
            (command,)).fetchall()

    out = []
    for sha, cmd, page, group, syn, ex, sample in rows:
        prods = [r[0] for r in c.execute(
            "SELECT product FROM cli_command_products WHERE content_sha = ? "
            "ORDER BY product", (sha,))]
        out.append({"command": cmd, "page": page, "cmd_group": group,
                    "syntax": json.loads(syn or "[]"),
                    "examples": json.loads(ex or "[]"),
                    "sample_output": sample, "products": prods})
    return out


def search(query: str, limit: int = 10,
           conn: Optional[sqlite3.Connection] = None) -> List[dict]:
    """FTS search over command name / group / syntax / sample output."""
    c = conn or _conn()
    terms = " OR ".join(f'"{t}"' for t in query.split() if t)
    if not terms:
        return []
    try:
        rows = c.execute(
            "SELECT k.command, k.cmd_group, k.syntax, k.sample_output "
            "FROM cli_commands_fts f JOIN cli_commands k ON k.rowid = f.rowid "
            "WHERE cli_commands_fts MATCH ? ORDER BY rank LIMIT ?",
            (terms, limit)).fetchall()
    except sqlite3.OperationalError:
        return []
    seen, out = set(), []
    for cmd, group, syn, sample in rows:
        if cmd in seen:
            continue
        seen.add(cmd)
        out.append({"command": cmd, "cmd_group": group,
                    "syntax": json.loads(syn or "[]"), "sample_output": sample})
    return out


def prompt_block(commands: List[str], product: Optional[str] = None,
                 max_output_lines: int = 14,
                 conn: Optional[sqlite3.Connection] = None) -> str:
    """Render a compact grounding block for injection into the generate prompt.

    Deliberately terse: syntax lines plus a trimmed real sample output per command. The
    generate prompt is already ~24k chars, so this must add signal, not bulk. Sample
    output is what stops the model inventing `speed=1000`, so it is never dropped in
    favour of more syntax.
    """
    c = conn or _conn()
    parts: List[str] = []
    for name in commands:
        variants = lookup(name, product, c)
        if not variants:
            continue
        # Pick the variant the MOST PRODUCT FAMILIES share, not the longest sample.
        # `show interface` has 7 variants: switch families print `Interface port1.0.1`,
        # but the TQ wireless APs print `Interface eth1` and the virtual appliances
        # `eth0`. Selecting by length handed the model the 927-char TQ router-interface
        # sample, and a re-extraction duly emitted `show interface eth1` for a switch
        # port test. Breadth of support is the better proxy for "the normal case";
        # length breaks the tie so an equally-shared variant with richer output wins.
        v = max(variants, key=lambda x: (len(x["products"]),
                                         len(x["sample_output"] or "")))
        chunk = [f"### {v['command']}"]
        for s in v["syntax"][:4]:
            chunk.append(f"    {s}")
        # flag genuine per-product syntax differences rather than silently picking one
        if not product and len(variants) > 1:
            alts = {tuple(x["syntax"]) for x in variants}
            if len(alts) > 1:
                for other in variants:
                    if other is v or tuple(other["syntax"]) == tuple(v["syntax"]):
                        continue
                    fams = ", ".join(other["products"][:6]) or "?"
                    chunk.append(f"    (on {fams}: {'; '.join(other['syntax'][:2])})")
        if v["sample_output"]:
            lines = v["sample_output"].split("\n")[:max_output_lines]
            chunk.append("  real output:")
            chunk += [f"    {ln}" for ln in lines]
        parts.append("\n".join(chunk))
    if not parts:
        return ""
    return ("REAL CLI REFERENCE (AlliedWare Plus — authoritative; match these formats "
            "exactly, do NOT invent output tokens):\n\n" + "\n\n".join(parts))


def detect_commands(text: str, limit: int = 12,
                    conn: Optional[sqlite3.Connection] = None) -> List[str]:
    """Which harvested commands does this text actually reference?

    Injecting all ~2,900 commands would swamp the prompt, so grounding is scoped to what
    the case really uses. Matching is longest-first so `show interface status` wins over
    `show interface`, and a shorter command is dropped when a longer match already covers
    the same span (otherwise every `show interface status` case would also drag in the
    generic `show interface` entry).

    Input is the case's own sequence text + reused fragment code — both already
    reviewer-approved, so this adds no new trust surface.
    """
    c = conn or _conn()
    low = " " + re.sub(r"\s+", " ", text.lower()) + " "
    try:
        names = [r[0] for r in c.execute(
            "SELECT DISTINCT command FROM cli_commands WHERE command IS NOT NULL")]
    except sqlite3.OperationalError:
        return []

    # Single ordinary English words that happen to BE command names ('state' is an AMF
    # command, 'port' an AWC wireless one) match constantly in prose and inject
    # irrelevant references. Require a multi-word command, or a single word that is
    # domain-specific enough to mean the command when it appears — verified against the
    # real T33235 sequence, which was pulling in amf_cmd/state and awc_cmd/port.
    SAFE_SINGLE = {"speed", "duplex", "polarity", "tcpdump", "ping", "traceroute",
                   "shutdown", "mtu", "bandwidth", "flowcontrol", "switchport"}

    hits: List[str] = []
    spans: List[tuple] = []
    for name in sorted(names, key=len, reverse=True):
        if len(name) < 4:                       # 'do', 'end' etc. are pure noise
            continue
        if " " not in name and name not in SAFE_SINGLE:
            continue                            # single generic word — too ambiguous
        for m in re.finditer(r"(?<![a-z0-9])" + re.escape(name) + r"(?![a-z0-9])", low):
            if any(s <= m.start() and m.end() <= e for s, e in spans):
                break                           # already covered by a longer command
            spans.append((m.start(), m.end()))
            hits.append(name)
            break
        if len(hits) >= limit:
            break
    return hits


def stats(conn: Optional[sqlite3.Connection] = None) -> dict:
    c = conn or _conn()
    q = lambda s: c.execute(s).fetchone()[0]
    try:
        meta = c.execute("SELECT v FROM meta WHERE k='cli_docs_harvest'").fetchone()
    except sqlite3.OperationalError:
        meta = None
    return {
        "unique_content_blobs": q("SELECT COUNT(*) FROM cli_commands"),
        "distinct_commands": q("SELECT COUNT(DISTINCT command) FROM cli_commands"),
        "with_sample_output": q("SELECT COUNT(*) FROM cli_commands "
                                "WHERE sample_output IS NOT NULL"),
        "product_command_rows": q("SELECT COUNT(*) FROM cli_command_products"),
        "products": q("SELECT COUNT(DISTINCT product) FROM cli_command_products"),
        "command_groups": q("SELECT COUNT(DISTINCT cmd_group) FROM cli_commands"),
        "harvest": json.loads(meta[0]) if meta else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Look up AW+ CLI syntax + sample output")
    ap.add_argument("command", nargs="?", help="exact command, e.g. 'show interface'")
    ap.add_argument("--product", help="restrict to one family, e.g. x930")
    ap.add_argument("--search", help="FTS search instead of exact lookup")
    ap.add_argument("--prompt-block", help="comma-separated commands -> prompt block")
    ap.add_argument("--detect", help="text to scan for referenced commands")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not DB.exists():
        print(f"ck.db not found at {DB}", file=sys.stderr)
        return 2
    c = _conn()

    if args.stats:
        s = stats(c)
        print(json.dumps(s, indent=2) if args.json else
              "\n".join(f"{k:<24} {v}" for k, v in s.items() if k != "harvest"))
        if not args.json and s.get("harvest"):
            h = s["harvest"]
            print(f"{'last harvest':<24} {h.get('harvested_at')} "
                  f"({h.get('fetches')} fetches, {h.get('soft_404', 0)} soft-404)")
        return 0

    if args.detect:
        found = detect_commands(args.detect, conn=c)
        print(json.dumps(found, indent=2) if args.json else
              ('\n'.join(f'  {x}' for x in found) or '(none detected)'))
        return 0

    if args.prompt_block:
        cmds = [x.strip() for x in args.prompt_block.split(",") if x.strip()]
        block = prompt_block(cmds, args.product, conn=c)
        print(block or "(no matching commands harvested)")
        return 0

    if args.search:
        hits = search(args.search, conn=c)
        if args.json:
            print(json.dumps(hits, indent=2))
        else:
            for h in hits:
                syn = h["syntax"][0] if h["syntax"] else ""
                mark = " [has output]" if h["sample_output"] else ""
                print(f"  {h['command']:<44} {h['cmd_group']:<14} {syn[:46]}{mark}")
        return 0

    if not args.command:
        ap.error("pass a command, --search, --prompt-block, or --stats")

    res = lookup(args.command, args.product, c)
    if not res:
        print(f"no harvested entry for {args.command!r}"
              + (f" on {args.product}" if args.product else ""))
        return 1
    if args.json:
        print(json.dumps(res, indent=2))
        return 0
    for v in res:
        print(f"=== {v['command']}  ({v['page']})")
        print(f"    products: {', '.join(v['products'][:12])}"
              + (f" … +{len(v['products'])-12}" if len(v["products"]) > 12 else ""))
        for s in v["syntax"]:
            print(f"    syntax: {s}")
        if v["sample_output"]:
            print("    real output:")
            for ln in v["sample_output"].split("\n")[:18]:
                print(f"      {ln}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
