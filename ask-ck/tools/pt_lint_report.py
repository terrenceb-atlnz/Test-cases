#!/usr/bin/env python3
"""R5 (PLAN-self-healing-generation.md): the PyTest Creator lint trend across sessions — errors
per class, the repair return rate, and the 6.4 prompt-defect / lint-text-defect alarms, so a
prompt change is judged by data instead of one run someone watched.

Read-only over `ask-ck/db/ck.db` (`file:...?mode=ro`); it never writes. Shares the one
aggregation the server serves at `GET /api/pytest-create/lint_trends` (`_pt_lint_trends`), so the
CLI and the live Summary/admin cannot drift.

Usage:
  python3 ask-ck/tools/pt_lint_report.py                 # the default trailing window (5 runs)
  python3 ask-ck/tools/pt_lint_report.py --window 10
  python3 ask-ck/tools/pt_lint_report.py --json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CK_SERVER = REPO / "ask-ck" / "CK-main" / "CK_server"
sys.path.insert(0, str(CK_SERVER))
sys.path.insert(0, str(CK_SERVER.parent))
# Read-only: point the server's db layer at a read-only URI open of the permanent DB.
os.environ.setdefault("CK_DB_PATH", str(REPO / "ask-ck" / "db" / "ck.db"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--window", type=int, default=5, help="trailing runs to aggregate (default 5)")
    ap.add_argument("--json", action="store_true", help="print the raw aggregation as JSON")
    args = ap.parse_args(argv)

    from routers import pytest_create as pc  # noqa: E402
    trends = pc._pt_lint_trends(window=args.window)

    if args.json:
        print(json.dumps(trends, indent=1, sort_keys=True))
        return 0

    runs = trends.get("runs", 0)
    if not runs:
        print("No assembly lint history recorded yet — generate and assemble a case first.")
        return 0
    print(f"Lint trend over the last {runs} assembly run(s)  ·  prompt version {trends.get('prompt_version')}")
    print(f"  units in window: {trends.get('total_units')}")
    rr = trends.get("return_rate")
    print(f"  repair return rate: {'n/a' if rr is None else f'{rr:.0%}'}")
    by_class = trends.get("by_class") or {}
    if by_class:
        print("\n  lint errors by class (assembly):")
        for cls, n in sorted(by_class.items(), key=lambda kv: -kv[1]):
            print(f"    {cls:<16} {n}")
    repair = trends.get("repair") or {}
    if repair:
        print("\n  repair by class (ok / attempts):")
        for cls, st in sorted(repair.items()):
            att = st["repaired_ok"] + st["arrival_failed"]
            print(f"    {cls:<16} {st['repaired_ok']}/{att}")
    alarms = trends.get("alarms") or []
    if alarms:
        print(f"\n  ⚠ {len(alarms)} ALARM(S):")
        for a in alarms:
            print(f"    [{a['kind']}] {a['detail']}")
    else:
        print("\n  no alarms.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
