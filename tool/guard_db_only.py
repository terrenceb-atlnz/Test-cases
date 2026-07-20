#!/usr/bin/env python3
"""Guard: the running server must read corpora ONLY from ck.db, never from JSON.

Ask CK is strictly DB-only at runtime (PLAN-db-only-search Phase 1): every corpus
— Zephyr, TestLink, ATP, scripts, candidates, decisions, framework surface — is
served from ask-ck/var/ck.db. This guard fails if any CK_server/*.py source reads
one of the retired corpus JSON/JSONL files at runtime, so the file-read path can't
silently creep back in and re-introduce a second, divergent source of truth.

Legitimate NON-corpus file reads are allowed and intentionally NOT flagged:
  - secrets:            secrets.local.json, secrets.testboxes.json
  - static assets:      index.html, PROCESS.md
  - per-case exports:   refined-case zephyr_payload.json, provenance.json
  - debug logs / sftp:  llm-debug/*.jsonl, remote script writes

Usage:  python3 tool/guard_db_only.py        # exit 0 = clean, 1 = violation
"""
import re
import sys
from pathlib import Path

CK_SERVER = Path(__file__).resolve().parent.parent / "ask-ck" / "CK-main" / "CK_server"

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

# Lines matching these are known-legitimate and skipped even if they look filey.
ALLOW_RX = re.compile(
    r"secrets|provenance\.json|zephyr_payload\.json|index\.html|PROCESS|"
    r"llm-debug|debug-log|session_log|\.py\b|sftp\.open|# ")


def main() -> int:
    violations = []
    for py in sorted(CK_SERVER.rglob("*.py")):
        for n, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#") or ALLOW_RX.search(line):
                continue
            hit = next((f for f in FORBIDDEN if f in line), None)
            if hit or DECISIONS_RX.search(line):
                # Only care about actual reads, not mentions in strings/comments.
                if re.search(r"open\(|json\.load\(|listdir\(|read_text\(|Path\(", line):
                    rel = py.relative_to(CK_SERVER.parent.parent.parent)
                    violations.append(f"  {rel}:{n}: {stripped}  [{hit or 'decisions'}]")

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
