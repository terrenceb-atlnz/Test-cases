#!/usr/bin/env python3
"""Compare a PyTest Creator grading run against the previous one.

Built so the next session can answer "did the CLI-grounding change actually help, and did
anything regress?" without re-deriving it by hand. Reads the committed judging artifacts
(`mechanical.json` / `criterion4.json`) plus a snapshot of the prior run, and prints a
per-criterion before/after with regressions called out.

Snapshots live in `ask-ck/pytest-create/judging/_runs/<label>/` — a full copy of the
per-case artifacts, so a comparison never depends on git history or on the DB still
holding that session's state (it does not: re-extraction overwrites it).

Usage:
  python3 tool/pt_compare_runs.py --snapshot 2026-07-27-grounded   # save current as a run
  python3 tool/pt_compare_runs.py --list
  python3 tool/pt_compare_runs.py --against 2026-07-27-pre-grounding
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional

REPO = Path(__file__).resolve().parent.parent
JUDGING = REPO / "ask-ck" / "pytest-create" / "judging" / "Port (7)"
RUNS = REPO / "ask-ck" / "pytest-create" / "judging" / "_runs"

# Verdict ordering for "did this get better or worse" (higher index = worse).
SCALE = ["exceptional", "good", "bad", "not at all"]


def case_dirs(root: Path) -> List[Path]:
    return sorted(p for p in root.glob("AWPTCM-*") if p.is_dir())


def read(p: Path) -> Optional[dict]:
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def snapshot(label: str) -> int:
    dest = RUNS / label
    if dest.exists():
        print(f"snapshot {label!r} already exists — pick another label", file=sys.stderr)
        return 2
    dest.mkdir(parents=True)
    n = 0
    for cd in case_dirs(JUDGING):
        out = dest / cd.name
        out.mkdir()
        for f in cd.glob("*.json"):
            shutil.copy2(f, out / f.name)
            n += 1
    print(f"snapshotted {n} artifact(s) from {len(case_dirs(JUDGING))} case(s) -> {dest}")
    return 0


def mech_summary(d: dict) -> Dict[str, str]:
    c = d.get("criteria") or {}
    g = lambda k: (c.get(k) or {}).get("verdict", "—")
    return {
        "C1 template": g("1_template_used"),
        "C2 snippets": g("2_snippets_used"),
        "C3 order": g("3_snippet_order"),
        "C6 logging": g("6_logging_contract_offline"),
        "lint_ok": str((d.get("script") or {}).get("lint_ok")),
        "TestCases": str((c.get("1_template_used") or {}).get("testcase_classes", "—")),
    }


def crit4_summary(d: dict) -> Dict[str, str]:
    rows = [r for r in (d.get("results") or []) if "judges" in r]
    if not rows:
        return {}
    dist: Dict[str, int] = {}
    unstable = 0
    for r in rows:
        for j in r["judges"]:
            v = j.get("verdict") or "error"
            dist[v] = dist.get(v, 0) + 1
        sc = r.get("self_consistency") or {}
        if any(not m.get("stable") for m in sc.values()):
            unstable += 1
    return {
        "gap-fill blocks": str(len(rows)),
        "verdicts": ", ".join(f"{k}={v}" for k, v in sorted(dist.items())),
        "blocks w/ unstable judge": str(unstable),
    }


def compare(prev_label: str) -> int:
    prev_root = RUNS / prev_label
    if not prev_root.exists():
        print(f"no snapshot {prev_label!r} under {RUNS}", file=sys.stderr)
        return 2

    regressions: List[str] = []
    print(f"comparing CURRENT vs snapshot {prev_label!r}\n")

    for cd in case_dirs(JUDGING):
        key = cd.name
        print(f"{'='*74}\n{key}\n{'='*74}")
        for fname, summarize in (("mechanical.json", mech_summary),
                                 ("criterion4.json", crit4_summary)):
            cur = read(cd / fname)
            old = read(prev_root / key / fname)
            if cur is None and old is None:
                continue
            print(f"\n  {fname}")
            cs = summarize(cur) if cur else {}
            os_ = summarize(old) if old else {}
            for field in sorted(set(cs) | set(os_)):
                a, b = os_.get(field, "—"), cs.get(field, "—")
                mark = "  " if a == b else "->"
                print(f"    {field:<26} {a:<22} {mark} {b}")
                # flag a criterion that moved the wrong way
                if a in SCALE and b in SCALE and SCALE.index(b) > SCALE.index(a):
                    regressions.append(f"{key} {field}: {a} -> {b}")
                if field == "lint_ok" and a == "True" and b == "False":
                    regressions.append(f"{key} lint_ok: True -> False")
                for good, bad in (("exactly", "partially"), ("exactly", "not at all"),
                                  ("right", "wrong"), ("yes", "partial"), ("yes", "no")):
                    if a == good and b == bad:
                        regressions.append(f"{key} {field}: {a} -> {b}")
        print()

    print("=" * 74)
    if regressions:
        print(f"REGRESSIONS ({len(regressions)}):")
        for r in dict.fromkeys(regressions):
            print(f"  ! {r}")
    else:
        print("no regressions detected on the compared fields")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare grading runs across sessions")
    ap.add_argument("--snapshot", metavar="LABEL", help="save current artifacts as a run")
    ap.add_argument("--against", metavar="LABEL", help="compare current vs a saved run")
    ap.add_argument("--list", action="store_true", help="list saved runs")
    args = ap.parse_args()

    if args.list:
        if not RUNS.exists():
            print("(no snapshots yet)")
            return 0
        for d in sorted(RUNS.iterdir()):
            if d.is_dir():
                n = sum(1 for _ in d.rglob("*.json"))
                print(f"  {d.name:<32} {n} artifact(s)")
        return 0
    if args.snapshot:
        return snapshot(args.snapshot)
    if args.against:
        return compare(args.against)
    ap.error("pass --snapshot, --against, or --list")


if __name__ == "__main__":
    sys.exit(main())
