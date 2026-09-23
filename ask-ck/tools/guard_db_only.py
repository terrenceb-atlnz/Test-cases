#!/usr/bin/env python3
"""Guard: the running server must read corpora ONLY from ck.db, never from JSON.

Ask CK is strictly DB-only at runtime (PLAN-db-only-search Phase 1): every corpus
— Zephyr, TestLink, ATP, scripts (incl. literal source code), candidates, decisions,
framework surface — is served from ask-ck/db/ck.db. This guard fails if any
CK_server/*.py source reaches for that data anywhere other than ck.db, so a second,
divergent source of truth can't silently creep back in. It catches four shapes:
  1. Reading a retired corpus JSON/JSONL file at runtime (FORBIDDEN / decisions).
  2. Reading script SOURCE off a filesystem path (Path(rec["path"]).read_text()) —
     source lives in scripts.source_text (db.get_script_source), never on disk.
  3. Referencing a retired script mount root (testsuites_art/ svt_scripts/ …) in an FS call.
  4. Defining or dereferencing a retired corpus-dir anchor (DATA_DIR / PT_DATA_DIR).

Legitimate NON-corpus file reads are allowed and intentionally NOT flagged:
  - secrets:            secrets.local.json, secrets.testboxes.json
  - static assets:      index.html, PROCESS.md
  - per-case exports:   refined-case zephyr_payload.json, provenance.json
  - debug logs / sftp:  llm-debug/*.jsonl, remote script writes

Usage:  python3 ask-ck/tools/guard_db_only.py        # exit 0 = clean, 1 = violation
"""
import re
import sys
from pathlib import Path

CK_SERVER = Path(__file__).resolve().parent.parent / "CK-main" / "CK_server"   # ask-ck/tools/ -> ask-ck/

# Retired corpus sources — the DB is now the only runtime home for these. A read
# of any of these names inside CK_server/ is a regression.
FORBIDDEN = [
    "zephyr_cases.jsonl", "zephyr_master.json", "slim_index.json", "index.json",
    "testlink_awp.json", "test_id_description.json", "all_test_suites.json",
    "scripts_index.json", "scripts_slim_index.json", "scripts_sources.jsonl",
    "framework_surface.json", "scripts_index.meta.json", "candidates.json",
]
# Any read of a file under a data/decisions dir is also forbidden (decisions live
# in the DB now). Matches os.listdir / open on that path.
DECISIONS_RX = re.compile(r"decisions.*\.json|data/decisions")

# Script SOURCE must come from ck.db (scripts.source_text via db.get_script_source),
# never off a filesystem path. Two regressions to catch:
#   1. Reading a script record's `path` field from disk (the record carries the
#      original repo path as provenance only; it is NOT a live handle).
#   2. Any reference to the retired script mount roots.
SOURCE_PATH_RX = re.compile(r"""(?x)
    (Path\(\s*rec\[["']path["']\]\s*\)) |            # Path(rec["path"])
    (rec\[["']path["']\]\s*\)?\s*\.read_text) |      # rec["path"].read_text / .read_text via Path
    (rec\.get\(["']path["']\).*read_text)
""")
RETIRED_MOUNT_RX = re.compile(r"testsuites_art|svt_scripts|/mnt/testbox_home/.*framework")

# Retired corpus-dir anchors. The corpus JSON dirs (objective-drafting/data,
# pytest-create/data) are gone — their data lives in ck.db. A DATA_DIR / PT_DATA_DIR
# anchor (or a fresh `.../ "data"` corpus path) used to reach the filesystem is a
# regression; PT_GENERATED_DIR / REFINED_DIR / DEBUG_LOG_DIR remain legitimate.
CORPUS_ANCHOR_RX = re.compile(r"\bDATA_DIR\b|\bPT_DATA_DIR\b")

# Lines matching these are known-legitimate and skipped even if they look filey. The match
# runs on the CODE part of a line only (comments stripped by `_code_lines`): this list used to
# carry "# ", so any line with a trailing comment was skipped whole — adding a comment to a
# corpus read defeated invariant #2 (pipeline plan 12.4, fixed 2026-09-23).
ALLOW_RX = re.compile(
    r"secrets|provenance\.json|zephyr_payload\.json|index\.html|PROCESS|"
    r"llm-debug|debug-log|session_log|sftp\.open")


def _code_lines(text: str):
    """(line_no, code) for every line, with `#` comments removed by the tokenizer, so a comment
    can neither hide a read nor fake one. A file that does not tokenize falls back to the raw
    lines — the guard then over-reports rather than under-reports."""
    import io
    import tokenize
    lines = text.splitlines()
    cut: dict = {}
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type == tokenize.COMMENT:
                cut[tok.start[0]] = min(cut.get(tok.start[0], 10 ** 9), tok.start[1])
    except (tokenize.TokenError, IndentationError, SyntaxError):
        cut = {}
    for n, line in enumerate(lines, 1):
        yield n, (line[:cut[n]] if n in cut else line)


def scan(root: Path) -> list:
    """Every violation under `root` (a CK_server tree), as printable lines."""
    violations = []
    for py in sorted(root.rglob("*.py")):
        for n, line in _code_lines(py.read_text(encoding="utf-8")):
            stripped = line.strip()
            if not stripped or ALLOW_RX.search(line):
                continue
            try:
                rel = py.relative_to(root.parent.parent.parent)
            except ValueError:
                rel = py
            hit = next((f for f in FORBIDDEN if f in line), None)
            if hit or DECISIONS_RX.search(line):
                # Only care about actual reads, not mentions in strings/comments.
                if re.search(r"open\(|json\.load\(|listdir\(|read_text\(|Path\(", line):
                    violations.append(f"  {rel}:{n}: {stripped}  [{hit or 'decisions'}]")

            # Script source must come from ck.db, not a filesystem path.
            if SOURCE_PATH_RX.search(line):
                violations.append(f"  {rel}:{n}: {stripped}  [script source read off disk — use db.get_script_source]")
            # Retired mount roots, but only when actually used to reach the FS
            # (a mention inside a quoted human-facing string is fine).
            if RETIRED_MOUNT_RX.search(line) and re.search(r"open\(|read_text|listdir|Path\(|os\.environ", line):
                m = RETIRED_MOUNT_RX.search(line)
                violations.append(f"  {rel}:{n}: {stripped}  [retired mount '{m.group(0)}' — source lives in ck.db]")
            # Retired corpus-dir anchors (defining or dereferencing one).
            if CORPUS_ANCHOR_RX.search(line):
                m = CORPUS_ANCHOR_RX.search(line)
                violations.append(f"  {rel}:{n}: {stripped}  [retired corpus anchor '{m.group(0)}' — corpora live in ck.db]")

    return violations


def main() -> int:
    violations = scan(CK_SERVER)
    if violations:
        print("GUARD FAIL — runtime corpus JSON read(s) found in CK_server/ "
              "(corpora must come from ck.db via db.*):")
        print("\n".join(violations))
        print(f"\n{len(violations)} violation(s). Repoint to a db.* getter.")
        return 1
    print("GUARD OK — no runtime corpus JSON reads in CK_server/; DB is the sole source.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
