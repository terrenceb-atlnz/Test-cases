#!/usr/bin/env python3
"""Report memory files that cite a repo path which no longer exists.

WHY THIS EXISTS
---------------
On 2026-08-17 six memories were found citing `routers/wizard.py` and line numbers
inside it. That file stopped existing on 2026-07-29 when it became the
`routers/wizard/` package. A memory is supposed to read as CURRENT truth — unlike
SESSION_STATE.md or a PLAN body, which are frozen history — so a dead path in one
does not merely age, it actively misleads the next session.

WHAT IT DOES NOT DO
-------------------
It cannot catch the other half of the problem, and pretending otherwise would be
worse than useless. The same day, three documents claimed per-case locking was
unbuilt and the two-tab overwrite bug was "live today". `locks.py` existed and had
since 2026-07-29. Nothing was missing; a *sentence* had stopped being true. That is
semantic, and only a reader who knows the subsystem catches it — which is why
`/wrap` §5 asks you to re-verify the memories you actually relied on this session.
This script is the cheap mechanical half, not the whole job.

WHY IT IS ADVISORY, NOT PART OF THE GATE
----------------------------------------
A first pass over 64 memories produced 130 raw hits, of which ONE was a real defect.
Memories legitimately name files on other machines (the read-only `framework` tree,
testboxes), files deliberately deleted and cited AS history, artifact names as
deployed rather than as stored, and proposals that were reverted before shipping. A
blocking check with that signal-to-noise trains everyone to ignore it — the exact
failure `tests/_prose.py` was written to prevent. So: `/wrap` runs it, a human reads
it, and it is deliberately NOT in `tool/run_tests.sh`. Memory rot misleads a future
session; it does not break the software.

    ./tool/check_memory_refs.py            # report
    ./tool/check_memory_refs.py --verbose  # also show what was skipped, and why

Exit 0 = nothing unexplained. Exit 1 = at least one citation needs attention (fix it,
mark it, or allowlist it below). Non-zero here must never block a commit on its own.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MEM_DIR = REPO / ".claude" / "memory"

FILE_EXT = (".py", ".js", ".md", ".sh", ".json", ".jsonl", ".jinja",
            ".db", ".html", ".css", ".txt", ".sql", ".yaml", ".yml")

# Where a memory's bare path is likely rooted. Order matters only for reporting.
PREFIXES = [
    "", "ask-ck/", "ask-ck/var/", "ask-ck/CK-main/", "ask-ck/CK-main/CK_server/",
    "ask-ck/CK-main/CK_server/routers/", "ask-ck/CK-main/CK_server/templates/",
    "ask-ck/CK-main/CK_server/templates/prompts/", "ask-ck/CK-main/CK_server/static/",
    "ask-ck/CK-main/CK_server/static/js/", "ask-ck/objective-drafting/",
    "ask-ck/pytest-create/", "ask-ck/ck-facelift/", "tool/", "tests/", "js-tests/",
    ".claude/memory/", ".claude/skills/",
]

# A citation is INTENTIONALLY dead when its own line says so. This is the escape
# hatch: state that the thing is gone and the check stops asking about it.
GONE_MARKERS = re.compile(
    r"no longer exist|does not exist|doesn't exist|\bdelet|retired|removed|"
    r"\bgone\b|never shipped|never existed|reverted|supersed|was renamed|"
    r"became the|is now the|used to |formerly|line number is dead|as-of |"
    r"scaffolding|pre-migration|frozen",
    re.I,
)

# Whole classes that are legitimately not files in this repo, by shape.
ALLOW_PATTERNS = [
    (re.compile(r"^claude/"),
     "sibling directory in the lab home, outside this repo"),
    (re.compile(r"^(x\d{3}|[a-z]+_cmd)/.*\.html$"),
     "docs.atlnz.lc URL path, not a file"),
]

# The courier / intermediate corpora deliberately DELETED on 2026-07-20b once ck.db
# became the permanent source. Memories cite them constantly and correctly, as the
# thing that was retired — see [[db-is-permanent-source]].
COURIERS = {
    "zephyr_cases.jsonl", "zephyr_full/index.json", "slim_index.json",
    "zephyr_master.json", "testlink_awp.json", "test_id_description.json",
    "candidates.json", "scripts_index.json", "scripts_sources.jsonl",
    "framework_surface.json", "scripts_index.meta.json", "all_test_suites.json",
    "zephyr_api_updates.json",
}

# Legitimately absent from this repo, with the reason. Keep this SHORT — every entry
# is a place the checker has been told to stop thinking, so each needs to earn it.
ALLOW = {
    # --- the read-only framework tree + testbox filesystems (never in this repo) ---
    "ATSwitch.py": "framework tree (/home/st-art/framework), read-only, not in repo",
    "Setup.py": "framework tree, read-only, not in repo",
    "DeviceSkrips/framework/Setup.py": "framework tree, read-only, not in repo",
    "ATDrivers/AWPConsoleCore.py": "framework tree, read-only, not in repo",
    "ATLibrary/ATTools.py": "framework tree, read-only, not in repo",
    "ATBootLoader.py": "framework tree, read-only, not in repo",
    "svt/3007_ixnetwork/ixNetworkTestBase.py": "legacy corpus script, lives in ck.db",
    "svt/3009_pluggable_qualifications/libPluggableAutomate.py": "legacy corpus script, lives in ck.db",
    "0009_..._Master_reboot.py": "legacy corpus script (elided name), lives in ck.db",
    "library_5700.py": "testbox-side 5700 suite, outside this repo",
    "test-5700.200x.py": "testbox-side 5700 suite, outside this repo",
    "launch.sh": "testbox-side, outside this repo",
    ".atpylib_publisher.json": "testbox-side, outside this repo",
    # --- named as DEPLOYED rather than as stored ---
    "ck_media.py": "name on the testbox; stored here as tool/pt_media.py (byte-identical)",
    # --- abbreviations of a real file ---
    "PROCESS.md": "shorthand for OBJECTIVE_DRAFTING_PROCESS.md (paths.py: PROCESS_MD)",
    # --- documentation website, not files ---
    "_bookmap_files/frontmatter/cmdref_Introduction.html": "docs.atlnz.lc URL path, not a file",
}

TOKEN_RE = re.compile(r"`([^`\n]+)`")
LINE_CITE_RE = re.compile(r"^([A-Za-z0-9_./-]+\.(?:py|js|md|sh|jinja)):\d+(?:-\d+)?$")


def _repo_has(name: str) -> str | None:
    """Resolve a bare-ish path against the known prefixes, then by basename."""
    for pre in PREFIXES:
        if (REPO / (pre + name)).exists():
            return pre + name
    base = os.path.basename(name)
    for dirpath, dirnames, filenames in os.walk(REPO):
        dirnames[:] = [d for d in dirnames
                       if d not in (".venv", ".git", "node_modules", "__pycache__")]
        if base in filenames:
            return os.path.relpath(os.path.join(dirpath, base), REPO)
    return None


def _skip_reason(tok: str) -> str | None:
    """Why this token is not a repo-relative file citation at all."""
    if tok.startswith(("/", "~")):
        return "absolute path (another machine)"
    if tok.startswith(("http", "tftp", "flash:", "git@", "ssh://")):
        return "URL / scheme"
    if "*" in tok or "<" in tok or ">" in tok:
        return "glob or placeholder"
    if " " in tok:
        return "not a path"
    if tok.startswith(".") and "/" not in tok:
        return "bare extension / filename suffix"
    if not tok.endswith(FILE_EXT):
        return "no file extension"
    if tok in COURIERS:
        return "retired courier corpus (deleted 2026-07-20b), cited as history"
    for pat, why in ALLOW_PATTERNS:
        if pat.search(tok):
            return why
    return None


def scan(verbose: bool = False) -> int:
    if not MEM_DIR.is_dir():
        print(f"!! no memory directory at {MEM_DIR}", file=sys.stderr)
        print("   ~/.claude/projects/*/memory should symlink to it — see /orient §4.",
              file=sys.stderr)
        return 1

    findings: list[tuple[str, int, str, str]] = []
    line_cites: list[tuple[str, int, str]] = []
    skipped: list[tuple[str, str, str]] = []
    n_mem = 0

    for path in sorted(MEM_DIR.glob("*.md")):
        n_mem += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.split("\n")
        seen: set[str] = set()

        for m in TOKEN_RE.finditer(text):
            raw = m.group(1).strip()
            lineno = text[: m.start()].count("\n") + 1
            line = lines[lineno - 1] if lineno <= len(lines) else ""

            # A file:LINE citation is always latent rot, even when it resolves today.
            if LINE_CITE_RE.match(raw):
                line_cites.append((path.name, lineno, raw))

            tok = re.sub(r":\d+(-\d+)?$", "", raw).split("::")[0]
            if tok in seen:
                continue
            seen.add(tok)

            why = _skip_reason(tok)
            if why:
                skipped.append((path.name, raw, why))
                continue
            if tok in ALLOW:
                skipped.append((path.name, raw, f"allowlisted — {ALLOW[tok]}"))
                continue
            if GONE_MARKERS.search(line):
                skipped.append((path.name, raw, "line states it is gone"))
                continue
            if _repo_has(tok) is None:
                findings.append((path.name, lineno, raw, line.strip()[:110]))

    print(f"Scanned {n_mem} memories in {MEM_DIR.relative_to(REPO)}\n")

    if findings:
        print(f"{len(findings)} citation(s) name a repo file that does not exist, "
              f"with nothing on the line saying so:\n")
        cur = None
        for name, lineno, raw, line in findings:
            if name != cur:
                print(f"  {name}")
                cur = name
            print(f"      :{lineno:<5} `{raw}`")
            print(f"             {line}")
        print("\n  Fix one of three ways:")
        print("    * correct the path (the usual answer — grep the symbol, it probably moved)")
        print("    * say on that line that it is gone ('no longer exists', 'was deleted', …)")
        print("    * add it to ALLOW in this script, WITH a reason")
    else:
        print("No unexplained dead path citations.")

    if line_cites:
        print(f"\n{len(line_cites)} file:LINE citation(s) — these rot silently even while "
              f"the file exists.\nPrefer the symbol name; a line number is right for one commit:\n")
        for name, lineno, raw in line_cites:
            print(f"  {name}:{lineno}  `{raw}`")

    if verbose and skipped:
        print(f"\n--- skipped ({len(skipped)}) ---")
        for name, raw, why in skipped:
            print(f"  {name:44} `{raw}`  [{why}]")

    return 1 if findings else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verbose", "-v", action="store_true",
                    help="also list every skipped token and why it was skipped")
    args = ap.parse_args()
    sys.exit(scan(verbose=args.verbose))
