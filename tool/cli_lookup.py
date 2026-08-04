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


# =============================================================================
# PHASE 4 — read-time repair of the harvested reference
#
# Everything below fixes the STORED data at READ time. It must stay that way:
# `ask-ck/var/ck.db` is the permanent single source of truth, built once and shipped via
# Git LFS. `tool/build_db.py` refuses to rebuild it, there is no migration framework, and
# 4.5's own wording is "re-classify from the data already in ck.db — no re-fetch, no
# network". So none of this normalises the database; it re-derives on the way out.
#
# The three defects, each measured against the real ck.db (2026-08-04):
#
#  1. COMMAND NAMES LOSE THEIR HYPHENS. `command` is derived from the doc-page slug, which
#     either drops a hyphen (`lockout-time` -> `lockouttime`) or turns it into an
#     underscore that then became a space (`2fa-registration` -> `2fa registration`). The
#     row's OWN `syntax` holds the correct spelling. 768 of 3,297 distinct command names
#     are recoverable this way. Consequence, on the flagship LLDP case: writing the command
#     CORRECTLY found nothing —
#         detect_commands('configure lldp tlv-select port-description') -> []
#     while the misspelling matched. Grounding rewarded getting it wrong.
#
#  2. THE PROMPT REGEX ONLY KNOWS THE HOSTNAME `awplus`. `harvest_cli_docs.classify()`
#     splits blocks on /^awplus.*[#>]/, so every page whose examples use a different
#     hostname — `Node_1(config)#`, `master_1#`, `controller-1(config)#` — has its worked
#     examples AND the device reply after them filed as *syntax*. 157 rows, 569 blocks,
#     63,064 chars; 154 of those rows have an empty `sample_output` as a direct result.
#
#  3. OUTPUT WITH NO PROMPT LINE AT ALL IS FILED AS SYNTAX. A block can be a genuine
#     device reply shown without the command above it. 735 rows hold multi-line,
#     placeholder-sparse blocks in `syntax`; 606 of them have no `sample_output`.
#
# WHY RE-DERIVE FROM `pre_blocks` RATHER THAN PATCH THE `syntax` COLUMN: `pre_blocks`
# holds every <pre> block verbatim on 6,305 of 6,323 rows, so the classification can be
# redone from the ORIGINAL input rather than un-picked from a lossy result. Rows without
# `pre_blocks` fall back to the stored columns unchanged.
#
# PRECISION OVER RECALL, DELIBERATELY. This module's own FEATURE_ALIASES comment states
# the rule: "a wrong alias injects confidently-wrong grounding, which is worse than none".
# A syntax template misread as device output would hand the model a fake output format to
# match — the exact failure Phase 4 exists to stop. So every classifier below refuses when
# unsure, and `syntax` is the fallback classification, never `sample_output`.
# =============================================================================

# A prompt line: hostname, an optional (config…) mode, then '#' or '>', then a command.
# Anchored and length-bounded so it cannot fire on prose containing '>' (a syntax
# alternation like `{a|b} > c` has no leading bare hostname token) and requires something
# after the sigil, so a bare `awplus#` trailing line is not read as a command.
_PROMPT_ANY_RX = re.compile(
    r"^[ \t]*[A-Za-z][\w.\-]{0,31}(?:\([^)\n]{0,31}\))?[ \t]*[#>][ \t]*(?=\S)", re.M)

# Placeholder metacharacters that mark a SYNTAX template rather than device output.
_PLACEHOLDER_RX = re.compile(r"[<>{}|\[\]]")

# Cache: one alias index per database path. Building it scans every row.
_ALIAS_CACHE: Dict[str, dict] = {}


def norm_cmd(s: str) -> str:
    """Hyphen- and space-insensitive normal form of a command name.

    `lockout-time`, `lockouttime` and `lockout time` all collapse to `lockouttime`, which
    is what lets a correctly-spelled command find a slug-mangled row.
    """
    return re.sub(r"[-\s_]+", "", (s or "").lower())


def real_command_name(command: str, syntax: List[str]) -> Optional[str]:
    """The correctly-spelled command name, recovered from its own syntax lines.

    Returns the SHORTEST prefix of syntax tokens whose normalised form equals the stored
    command's, or None when no prefix matches. Shortest matters: `atmf area` must not
    absorb `<area-name>` from `atmf area <area-name> password`.

    Stops at the first argument placeholder, so a command name can never be built out of
    parameter syntax.
    """
    target = norm_cmd(command)
    if not target:
        return None
    for syn in syntax or []:
        acc: List[str] = []
        for tok in (syn or "").split():
            if tok[:1] in "<{[|":          # argument syntax begins — name is complete
                break
            acc.append(tok)
            cand = " ".join(acc)
            if norm_cmd(cand) == target:
                return cand
    return None


def reclassify(pre_blocks: List[str]) -> tuple:
    """Re-split raw <pre> blocks into (syntax, examples, sample_output).

    Supersedes `harvest_cli_docs.classify()` at read time. Two differences, both defects
    2 and 3 above: any hostname counts as a prompt, and a promptless block that looks like
    device output is treated as output instead of syntax.
    """
    syntax: List[str] = []
    examples: List[dict] = []
    best: Optional[str] = None

    def _consider(text: Optional[str]) -> None:
        nonlocal best
        if text and (best is None or len(text) > len(best)):
            best = text

    for b in pre_blocks or []:
        if not b or not b.strip():
            continue
        if _PROMPT_ANY_RX.search(b):
            lines = b.split("\n")
            cmd_line = lines[0].strip()
            reply = "\n".join(lines[1:]).rstrip()
            examples.append({"cmd": cmd_line, "output": reply or None})
            _consider(reply or None)
            continue

        # No prompt anywhere. Output, or a syntax template?
        lines = [ln for ln in b.split("\n") if ln.strip()]
        if len(lines) < 3:
            syntax.append(b)                       # too short to judge — stays syntax
            continue
        dense = sum(1 for ln in lines if _PLACEHOLDER_RX.search(ln))
        if dense / len(lines) > 0.4:
            syntax.append(b)                       # placeholder-dense — a template
            continue
        _consider(b.rstrip())                      # multi-line, plain: device output

    return syntax, examples, best


def _alias_index(conn: sqlite3.Connection) -> dict:
    """{normalised name -> {"stored": [...], "real": <best real spelling>}} for every row.

    One pass over `cli_commands`, cached per database. Lets a caller write a command the
    way the CLI actually spells it and still reach the row stored under the slug spelling.
    """
    key = str(DB)
    hit = _ALIAS_CACHE.get(key)
    if hit is not None:
        return hit

    idx: Dict[str, dict] = {}
    try:
        rows = conn.execute(
            "SELECT command, syntax, pre_blocks FROM cli_commands "
            "WHERE command IS NOT NULL").fetchall()
    except sqlite3.OperationalError:
        return {}

    for cmd, syn, pre in rows:
        try:
            syn_list = json.loads(syn or "[]")
        except Exception:
            syn_list = []
        if pre:
            try:
                syn_list = reclassify(json.loads(pre))[0] or syn_list
            except Exception:
                pass
        n = norm_cmd(cmd)
        if not n:
            continue
        e = idx.setdefault(n, {"stored": [], "real": None})
        if cmd not in e["stored"]:
            e["stored"].append(cmd)
        rn = real_command_name(cmd, syn_list)
        # Prefer the spelling that actually carries hyphens; between two candidates take
        # the one with more, since the slug form is the hyphen-poor one by construction.
        if rn and (e["real"] is None or rn.count("-") > e["real"].count("-")):
            e["real"] = rn
    _ALIAS_CACHE[key] = idx
    return idx


def resolve_command(name: str, conn: Optional[sqlite3.Connection] = None) -> List[str]:
    """Stored command name(s) matching `name`, however it is hyphenated.

    `resolve_command('lldp tlv-select')` -> ['lldp tlvselect'].
    Returns [] when the reference does not know the command at all (4.3's flagging path).
    """
    c = conn or _conn()
    entry = _alias_index(c).get(norm_cmd(name))
    return list(entry["stored"]) if entry else []


def display_name(stored: str, conn: Optional[sqlite3.Connection] = None) -> str:
    """The correctly-spelled name for a stored command, for prompts and reports.

    Falls back to the stored spelling when nothing better is recoverable, so this is
    always safe to render.
    """
    c = conn or _conn()
    entry = _alias_index(c).get(norm_cmd(stored))
    return (entry.get("real") if entry else None) or stored


def lookup(command: str, product: Optional[str] = None,
           conn: Optional[sqlite3.Connection] = None) -> List[dict]:
    """Every stored variant of `command`, newest-content first.

    With `product`, returns only the variant THAT product actually ships — the point of
    the support matrix. Without it, returns all variants plus the products sharing each,
    so a caller can see (for example) that `duplex` drops `half` on x930/x950.
    """
    c = conn or _conn()
    # 4.1 — accept the command spelled the way the CLI actually spells it. The stored name
    # is slug-derived and hyphen-poor, so an exact-match lookup on `lldp tlv-select` found
    # nothing. Resolve through the alias index first, then fall back to the literal name so
    # a caller passing the stored spelling is unaffected.
    targets = resolve_command(command, c) or [command]
    ph = ",".join("?" for _ in targets)

    if product:
        rows = c.execute(
            "SELECT k.content_sha, k.command, k.page, k.cmd_group, k.syntax, "
            "       k.examples, k.sample_output, k.pre_blocks, k.tables, k.notes "
            "FROM cli_commands k JOIN cli_command_products p "
            "  ON p.content_sha = k.content_sha "
            f"WHERE k.command IN ({ph}) AND p.product = ?",
            (*targets, product)).fetchall()
    else:
        rows = c.execute(
            "SELECT content_sha, command, page, cmd_group, syntax, examples, "
            "       sample_output, pre_blocks, tables, notes FROM cli_commands "
            f"WHERE command IN ({ph})", tuple(targets)).fetchall()

    out = []
    for sha, cmd, page, group, syn, ex, sample, pre, tbls, nts in rows:
        prods = [r[0] for r in c.execute(
            "SELECT product FROM cli_command_products WHERE content_sha = ? "
            "ORDER BY product", (sha,))]
        syntax = _loads_list(syn)
        examples = _loads_list(ex)

        # 4.5 — re-classify from the verbatim <pre> blocks. The stored split used an
        # `awplus`-only prompt regex, so pages using any other hostname had their examples
        # AND the device reply filed as syntax (157 rows), and promptless output blocks
        # went the same way (735 rows). Re-deriving recovers both. `or` guards keep a
        # recovery that finds nothing from erasing what was already stored.
        if pre:
            try:
                r_syn, r_ex, r_sample = reclassify(json.loads(pre))
                syntax = r_syn or syntax
                examples = r_ex or examples
                sample = sample or r_sample
            except Exception:
                pass                            # malformed pre_blocks — keep stored values

        out.append({"command": cmd, "page": page, "cmd_group": group,
                    "display": display_name(cmd, c),
                    "syntax": syntax,
                    "examples": examples,
                    "sample_output": sample,
                    "tables": _loads_list(tbls),
                    # `notes` is a JSON OBJECT ({Overview, Default, Mode, Usage notes, …}),
                    # not an array — reading it as a list silently yielded [] on all 6,323
                    # rows and would have made 4.6 look implemented while shipping nothing.
                    "notes": _loads_obj(nts),
                    "products": prods})
    return out


def _loads_list(raw) -> list:
    """JSON array from a column, tolerating null and malformed content."""
    try:
        v = json.loads(raw or "[]")
    except Exception:
        return []
    return v if isinstance(v, list) else []


def _value_tables(tables: Optional[list]) -> List[list]:
    """The tables that are LEGAL-VALUE MATRICES, not prose laid out in cells.

    Doc pages use <table> for both. A value matrix is narrow (2–3 columns) and its cells
    are short; a prose table has one wide cell per row and would dump paragraphs into the
    prompt, which is bulk rather than signal. Keeps at most two per command.
    """
    out: List[list] = []
    for tbl in tables or []:
        if not isinstance(tbl, list) or len(tbl) < 2:
            continue
        rows = [r for r in tbl if isinstance(r, list) and r]
        if len(rows) < 2:
            continue
        widths = [len(r) for r in rows]
        if max(widths) > 3:
            continue
        longest = max((len(str(c)) for r in rows for c in r), default=0)
        if longest > 90:                    # a paragraph in a cell — prose, not values
            continue
        out.append(rows)
        if len(out) == 2:
            break
    return out


def _loads_obj(raw) -> dict:
    """JSON object from a column, tolerating null and malformed content."""
    try:
        v = json.loads(raw or "{}")
    except Exception:
        return {}
    return v if isinstance(v, dict) else {}


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


# Feature names a test engineer writes -> the command tree that implements them, plus the
# words to look for in sample output. `detect_commands()` matches literal command strings,
# so a feature described in PROSE has no lexical path to its commands: "EcoMode", "LPI" and
# "EEE" appear nowhere inside the command name `ecofriendly lpi`. No amount of matcher
# tuning bridges that — hence this table.
#
# Found via criterion-4 judging (2026-07-28): four steps across T33233/T33234 said
# "Enable EcoMode on the port" / "lpi disable on <port>" and verified with `show
# interface`. The `ecofriendly` tree — including `show ecofriendly`, whose per-port
# `Configured`/`Status` table is the only output that actually proves LPI is off — was
# harvested and present in ck.db the whole time, and never reached the prompt.
#
# Deliberately small and hand-curated: each entry is a feature whose CLI name a reader
# would not guess from the prose. Add entries as real cases surface them; do NOT try to
# auto-derive it, because a wrong alias injects confidently-wrong grounding, which is
# worse than none (see the `show interface eth1` regression).
FEATURE_ALIASES: Dict[str, dict] = {
    "ecofriendly": {
        # `ecofriendly` is the PROPER CLI terminology (Terrence, 2026-07-28). "EcoMode" is
        # SLANG — it appears in Zephyr case prose and in conversation, never in the CLI.
        # That asymmetry is the whole point of this table: slang must be RECOGNISED on the
        # input side so a case that says "Enable EcoMode" still gets grounded, while the
        # `commands` values below are real CLI only, so slang can never reach a generated
        # script. `test_slang_never_reaches_generated_code` pins that direction.
        "prose": ["ecomode", "eco mode", "eco-mode", "ecofriendly", "eco friendly",
                  "eco-friendly", "lpi", "low power idle", "low-power idle",
                  "energy efficient ethernet", "energy-efficient ethernet", "eee",
                  "802.3az", "green ethernet"],
        "commands": ["ecofriendly lpi", "show ecofriendly"],
        # What to look for in a sample output to know the field is present.
        #
        # `lpi` is DEPRECATED terminology (Terrence, 2026-07-28) — it survives in exactly
        # one command name (`ecofriendly lpi`, the only spelling the CLI accepts) and as
        # the `Configured`/`Status` VALUE in `show ecofriendly` on the standalone switch
        # families (x530/x930/x950/x330/x540-560/gs970emx/ie220-560/x320 — 14 of them)
        # AND on the chassis families, so it is the value string across the board.
        # Modern diagnostics say EEE instead (`show platform port` prints `EEE Admin
        # Status`). Deprecated-as-terminology does NOT make it wrong as the string a
        # parser must match, so it stays here: TestLink cases are several years old and
        # almost unanimously say LPI, and they are the corpus reused fragments come from.
        "output_terms": ["ecofriendly", "lpi", "energy efficient"],
        # On the `show interface` variant that prints `current/configured ecofriendly lpi`:
        # it covers x8100/x908gen2/x908gen3 and uses `port1.1.x`. Both traits track
        # CHASSIS vs standalone, NOT firmware age — x908gen3 is a current platform (x8100
        # is the old one in that generational family), and an x950 with a populated card
        # slot uses `port1.1.x` too, so the naming is a runtime hardware property rather
        # than a per-model one. Relevance ranking deliberately still prefers this variant
        # on an ecofriendly step, because it is the one that actually SHOWS the field.
        # The port-naming question is handled where it belongs — port names come from the
        # .setup topology, never hardcoded — not by second-guessing variant choice here.
    },
    "spanning-tree": {
        # ADDED 2026-08-04, Phase 4, by the criterion this table sets for itself: a real
        # case surfaced the need. `AWPTCM-T33277` is the plan's own verification target —
        # "assert T33277 resolves to show spanning-tree's 2,388 chars of real output" — and
        # de-hyphenation ALONE cannot get there. Its text names the protocol in prose
        # ("spanning-tree statistics and counters", "spanning tree can be enabled",
        # "spanning-tree diagnostic") and never once writes a command, so there is no
        # lexical path from the case to `show spanningtree`. The row was in ck.db with its
        # 2,388 chars the whole time; nothing could reach it.
        #
        # `stp` is deliberately ABSENT from `prose`. Three letters inside a corpus full of
        # protocol acronyms is exactly the ambiguous alias the header warns against, and
        # `rstp`/`mstp`/`spanning tree` already cover every real mention in the 53 cases.
        "prose": ["spanning tree", "spanning-tree", "rstp", "mstp", "802.1d", "802.1w",
                  "802.1s", "root bridge", "cist"],
        # Real CLI only, and only commands that carry recovered output worth grounding on:
        # `show spanning-tree` 2,388 chars, `statistics` 769, `brief` 484, `mst config` 275.
        "commands": ["show spanningtree", "show spanningtree brief",
                     "show spanningtree statistics", "show spanningtree mst config",
                     "spanningtree mode"],
        "output_terms": ["spanning tree", "root path cost", "root port", "bridge priority",
                         "forwarding", "blocking", "cist"],
    },
}


def feature_commands(text: str) -> tuple:
    """Commands + output terms for features `text` names in PROSE rather than by command.

    Returns `(commands, output_terms)`. Complements `detect_commands()`, which is purely
    lexical over command names; this is the semantic half. Both are needed — a step can
    name the command, the feature, or (usually) some of each.
    """
    low = " " + re.sub(r"\s+", " ", text.lower()) + " "
    cmds: List[str] = []
    terms: List[str] = []
    for spec in FEATURE_ALIASES.values():
        for phrase in spec["prose"]:
            # word-boundary match so 'eee' doesn't fire inside 'seee'/'IEEE', and 'lpi'
            # doesn't fire inside a longer token
            if re.search(r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])", low):
                cmds += [c for c in spec["commands"] if c not in cmds]
                terms += [t for t in spec["output_terms"] if t not in terms]
                break
    return cmds, terms


def prompt_block(commands: List[str], product: Optional[str] = None,
                 max_output_lines: int = 14,
                 conn: Optional[sqlite3.Connection] = None,
                 feature_terms: Optional[List[str]] = None) -> str:
    """Render a compact grounding block for injection into the generate prompt.

    Deliberately terse: syntax lines plus a trimmed real sample output per command. The
    generate prompt is already ~24k chars, so this must add signal, not bulk. Sample
    output is what stops the model inventing `speed=1000`, so it is never dropped in
    favour of more syntax.

    `feature_terms` are the feature words the step is actually about (from
    `feature_commands()`). They only break ties toward a variant that DOES show the
    field — see the selection comment below.
    """
    c = conn or _conn()
    terms = [t.lower() for t in (feature_terms or [])]
    parts: List[str] = []
    for name in commands:
        variants = lookup(name, product, c)
        if not variants:
            continue
        # Pick the variant the MOST PRODUCT FAMILIES share, not the longest sample.
        # `show interface` has 8 variants: switch families print `Interface port1.0.1`,
        # but the TQ wireless APs print `Interface eth1` and the virtual appliances
        # `eth0`. Selecting by length handed the model the 927-char TQ router-interface
        # sample, and a re-extraction duly emitted `show interface eth1` for a switch
        # port test. Breadth of support is the better proxy for "the normal case";
        # length breaks the tie so an equally-shared variant with richer output wins.
        #
        # RELEVANCE FIRST (2026-07-28): breadth alone silently hid the field under test.
        # `show interface` DOES report LPI — `current ecofriendly lpi` / `configured
        # ecofriendly lpi` — but only on 3 families (x8100, x908gen2/3), so the
        # 14-family variant won and shipped output with NO EEE field. The model was then
        # told to "match these formats exactly, do NOT invent output tokens", which left
        # asserting on link state as almost the only move — grounding steering the model
        # INTO the false green the criterion-4 judges caught. So when the step is about a
        # feature, a variant whose output actually mentions it outranks a broader one
        # that omits it. Ordering the key this way (relevance, then breadth, then length)
        # keeps the `eth1` fix intact: with no feature terms, or when no variant mentions
        # them, this degrades exactly to the previous behaviour.
        # Relevance is graded, not boolean: `show ecofriendly` has a 10-family variant
        # whose ports are ALL `off`, so it mentions the feature (the "Energy efficient"
        # header) while demonstrating none of it. The 3 richer variants each show 7 `lpi`
        # rows — the enabled state an assertion has to recognise. Counting term hits
        # prefers the output that actually exercises the field; breadth still decides
        # between equally-demonstrative variants.
        def _rank(x: dict) -> tuple:
            out_low = (x["sample_output"] or "").lower()
            hits = sum(out_low.count(t) for t in terms) if terms else 0
            return (hits, len(x["products"]), len(x["sample_output"] or ""))

        v = max(variants, key=_rank)
        # 4.1 — head the block with the CORRECT spelling, not the slug-derived one. The
        # prompt says "match these formats exactly", so showing `lldp tlvselect` above
        # syntax that reads `lldp tlv-select` hands the model two spellings and blesses the
        # wrong one.
        chunk = [f"### {v.get('display') or v['command']}"]
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
            all_lines = v["sample_output"].split("\n")
            lines = all_lines[:max_output_lines]
            # Never trim away the field the step is about. `current ecofriendly lpi` sits
            # ~line 10 of that variant, so a tighter budget could drop the exact line
            # relevance-selection just chose — the reference would then look like proof
            # the field does not exist.
            if terms:
                kept = {id(x) for x in lines}
                for ln in all_lines[max_output_lines:]:
                    if any(t in ln.lower() for t in terms) and id(ln) not in kept:
                        lines.append(ln)
            chunk.append("  real output:")
            chunk += [f"    {ln}" for ln in lines]
            # If the chosen variant shows the feature but others do NOT, say so. The
            # field is genuinely family-specific (LPI in `show interface`: 3 families of
            # 8), and a model told to match formats exactly should know the assertion may
            # need the feature-specific `show` command on other hardware.
            if terms and len(variants) > 1:
                out_low = (v["sample_output"] or "").lower()
                if any(t in out_low for t in terms):
                    missing = [x for x in variants
                               if not any(t in (x["sample_output"] or "").lower()
                                          for t in terms)
                               and x["sample_output"]]
                    if missing:
                        fams = ", ".join(
                            f for x in missing[:4] for f in x["products"][:2])
                        chunk.append(
                            f"    (NOTE: this field is family-specific — not printed on "
                            f"{fams}…; prefer the feature-specific show command there)")

        # No device output for this command? Then the worked examples ARE the grounding.
        # `lldp tlv-select` — the command the flagship LLDP case is entirely about — has
        # 0 chars of sample_output because it is a config command that prints nothing, but
        # 12 real example lines showing the correct form. prompt_block rendered NEITHER, so
        # the one command that mattered reached the model with no evidence at all.
        elif v["examples"]:
            shown = [e.get("cmd") for e in v["examples"] if e.get("cmd")][:3]
            if shown:
                chunk.append("  real usage:")
                chunk += [f"    {s}" for s in shown]

        # 4.4 — the legal-argument matrices. 5,368 rows carry them and none reached a
        # prompt. This is the per-port-type value table (`speed`: which numbers a fibre SFP
        # versus an RJ-45 copper port actually accepts), which is exactly the fabrication
        # the grounding block exists to prevent, and which no hand-written prose in the
        # prompt supplies — see the note in the Phase 4 write-up about what `tables` does
        # and does not replace.
        for tbl in _value_tables(v.get("tables")):
            chunk.append("  legal values:")
            for row in tbl[:10]:
                cells = " | ".join(str(x).strip()[:58] for x in row if str(x).strip())
                if cells:
                    chunk.append(f"    {cells}")

        # 4.6 — `Default` and `Mode` from the release notes. Deliberately only those two:
        # they are short, factual and directly assertable ("what does this read before I
        # touch it", "which config mode must the script be in"). `Overview` restates the
        # command in prose, `Example` is a lead-in sentence with no content, and
        # `Related commands` invites the model to reach for commands the case never named.
        nts = v.get("notes") or {}
        facts = [(k, nts.get(k)) for k in ("Default", "Mode") if (nts.get(k) or "").strip()]
        for k, val in facts:
            chunk.append(f"  {k.lower()}: {' '.join(str(val).split())[:160]}")

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

    # 4.1 — match the CORRECT spelling too. `command` is slug-derived and loses hyphens,
    # so scanning for stored names alone means a step that writes `lldp tlv-select`
    # properly matches nothing while the misspelling matches. Each stored name is searched
    # under every spelling that normalises to it, and the STORED name is what we return so
    # `lookup()` still resolves; use `display_name()` to render it.
    idx = _alias_index(c)
    probes: List[tuple] = []                    # (search_text, stored_name)
    for name in names:
        if not name:
            continue
        forms = {name}
        real = (idx.get(norm_cmd(name)) or {}).get("real")
        if real:
            forms.add(real)
        for f in forms:
            probes.append((f, name))

    # Longest search text first, so `show interface status` still beats `show interface`.
    probes.sort(key=lambda p: len(p[0]), reverse=True)

    hits: List[str] = []
    spans: List[tuple] = []
    for text_form, stored in probes:
        if len(text_form) < 4:                  # 'do', 'end' etc. are pure noise
            continue
        if " " not in text_form and text_form not in SAFE_SINGLE:
            continue                            # single generic word — too ambiguous
        if stored in hits:
            continue                            # already found under another spelling
        for m in re.finditer(
                r"(?<![a-z0-9])" + re.escape(text_form.lower()) + r"(?![a-z0-9])", low):
            if any(s <= m.start() and m.end() <= e for s, e in spans):
                # 4.2 — THIS WAS `break`, WHICH ABANDONED THE COMMAND ENTIRELY.
                # A first occurrence sitting inside a longer match made grounding depend on
                # SENTENCE ORDER: "show interface status; then speed on that interface"
                # dropped `show interface` from the second clause because the first was
                # covered. Keep looking for an uncovered occurrence instead.
                continue
            spans.append((m.start(), m.end()))
            hits.append(stored)
            break
        if len(hits) >= limit:
            break
    return hits


def detect(text: str, limit: int = 12,
           conn: Optional[sqlite3.Connection] = None) -> dict:
    """`detect_commands` plus the correct spellings and what could NOT be resolved.

    4.3's reporting half. `detect_commands` returns stored names for lookup; this adds the
    display spellings a prompt should show, and the abbreviations that stayed ambiguous —
    which a caller should surface rather than drop, because a silently-omitted command is
    indistinguishable from a command the reference genuinely lacks.
    """
    c = conn or _conn()
    found = detect_commands(text, limit=limit, conn=c)
    return {
        "commands": found,
        "display": [display_name(x, c) for x in found],
        "unrecognised": unresolved_abbreviations(text, conn=c),
    }


# `no <cmd>` negates, `do <cmd>` escapes to exec mode. Neither is part of the name.
_LEAD_NOISE = ("no ", "do ", "default ")


def check_commands(candidates: List[str],
                   conn: Optional[sqlite3.Connection] = None) -> dict:
    """Which candidate command strings does the reference actually know?

    4.3's flagging primitive, for callers holding explicit CLI strings (a sequence's
    command fields, a fragment's issued commands). Returns
    `{"known": {candidate: stored_name}, "unknown": [candidate, …]}`.

    Handles the two forms the plan calls out:
      * NEGATED — a leading `no`/`do`/`default` is stripped before resolving, so
        `no lldp tlv-select` resolves to the same row as `lldp tlv-select`.
      * ABBREVIATED — `sh int` resolves to `show interface` only when the expansion is
        UNIQUE across the whole reference; an ambiguous abbreviation is reported unknown
        rather than guessed, because a wrong expansion injects grounding for a command the
        script never issues.
    """
    c = conn or _conn()
    known: Dict[str, str] = {}
    unknown: List[str] = []
    for raw in candidates or []:
        cand = " ".join((raw or "").split())
        if not cand:
            continue
        probe = cand.lower()
        for lead in _LEAD_NOISE:
            if probe.startswith(lead):
                probe = probe[len(lead):].strip()
                break
        # A CLI line is `command + arguments`, so resolve the LONGEST leading token prefix
        # that is a command and let the rest be arguments: `no lldp tlv-select all` has to
        # reach `lldp tlv-select`, with `all` understood as a parameter. Longest-first so
        # `show interface status` is not shortened to `show interface`.
        toks = probe.split()
        stored = None
        for n in range(len(toks), 0, -1):
            head = " ".join(toks[:n])
            got = resolve_command(head, c)
            if got:
                stored = got[0]
                break
            got = _expand_abbreviation(head, c)
            if got:
                stored = got
                break
        if stored:
            known[cand] = stored
        else:
            unknown.append(cand)
    return {"known": known, "unknown": unknown}


def _command_token_lists(conn: sqlite3.Connection) -> List[tuple]:
    """[(stored_name, [real tokens])] for every distinct command. Cached with the index."""
    idx = _alias_index(conn)
    key = str(DB) + "::tokens"
    hit = _ALIAS_CACHE.get(key)
    if hit is not None:
        return hit["rows"]
    rows = []
    for entry in idx.values():
        for stored in entry["stored"]:
            spelling = entry.get("real") or stored
            rows.append((stored, spelling.split()))
    _ALIAS_CACHE[key] = {"rows": rows}
    return rows


def _expand_abbreviation(probe: str,
                         conn: Optional[sqlite3.Connection] = None) -> Optional[str]:
    """Stored name for an AW+ abbreviation, but only when the expansion is UNIQUE.

    Every token must be a prefix of the corresponding command token, and the abbreviation
    must have at least as many tokens as it needs to be unambiguous. Returns None on zero
    or multiple matches — see the docstring on `check_commands` for why guessing is worse
    than reporting.
    """
    toks = probe.split()
    if not toks or any(len(t) < 2 for t in toks):
        return None
    matches = []
    for stored, cmd_toks in _command_token_lists(conn or _conn()):
        if len(cmd_toks) != len(toks):
            continue
        if all(ct.lower().startswith(t) for ct, t in zip(cmd_toks, toks)):
            matches.append(stored)
            if len(matches) > 1:
                return None                      # ambiguous — refuse
    return matches[0] if len(matches) == 1 else None


def unresolved_abbreviations(text: str,
                             conn: Optional[sqlite3.Connection] = None) -> List[str]:
    """CLI-looking lines in `text` that the reference cannot resolve to any command.

    Scoped to lines that are unambiguously CLI — a quoted string or a `no`-prefixed
    directive — rather than guessing at prose, so this reports real gaps instead of
    flagging every English sentence.
    """
    c = conn or _conn()
    cands: List[str] = []
    for m in re.finditer(r"""['"]([a-z][a-z0-9 .\-]{5,60})['"]""", text or "", re.I):
        cands.append(m.group(1))
    for m in re.finditer(r"^\s*(no\s+[a-z][a-z0-9 .\-]{4,60})\s*$", text or "",
                         re.I | re.M):
        cands.append(m.group(1))
    if not cands:
        return []
    res = check_commands(cands, c)
    # Only report things that at least LOOK like a command: two or more words, and a first
    # word that some real command also starts with. Otherwise every quoted English phrase
    # in a sequence description would be flagged as a missing CLI command.
    firsts = {t[0] for _, t in _command_token_lists(c) if t}
    out: List[str] = []
    for u in res["unknown"]:
        w = u.lower().split()
        if len(w) >= 2 and (w[0] in firsts or (w[0] in ("no", "do") and len(w) >= 3)):
            if u not in out:
                out.append(u)
    return out


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
