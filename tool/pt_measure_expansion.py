#!/usr/bin/env python3
"""Re-measure the generation size gate's constants against RECOVERED output.

PHASE 7.4. Every published figure for "how much the model delivers" was measured on
`_parse_generated_blocks` output, and that parser was discarding whole continuation
messages (see `gen_assembly`). `_FILL_EXPANSION = 1.95` and the answer-budget arithmetic in
`_size_overflow` are therefore fitted to truncated data.

This tool recomputes them from the stored generation replies, assembling each reply with
the fixed recoverer first. Offline: reads a debug-log JSONL, sends nothing, writes nothing.

    python3 tool/pt_measure_expansion.py [--log PATH] [--json]

`expansion` is delivered_chars / skeleton_chars — the multiplier `_size_overflow` applies to
the skeleton to predict how much output a generation needs.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "ask-ck", "CK-main", "CK_server"))

import gen_assembly  # noqa: E402

DEFAULT_LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "ask-ck", "CK-main", "CK_server", "debug-log", "no-session.jsonl")

# The prompt embeds the skeleton under its own heading, inside a fenced block.
_SKELETON_RX = re.compile(
    r"##\s*The skeleton to fill[^\n]*\n+```(?:python)?\s*\n(.*?)\n```", re.DOTALL)


def skeleton_of(prompt: str):
    m = _SKELETON_RX.search(prompt or "")
    return m.group(1) if m else None


def measure(log_path: str):
    rows = []
    with open(log_path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh):
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if not isinstance(rec, dict) or rec.get("template") != "pt_generate_script.jinja":
                continue
            reply = rec.get("response")
            reply = reply if isinstance(reply, str) else json.dumps(reply)
            skeleton = skeleton_of(rec.get("prompt") or "")
            if not skeleton or not reply:
                continue
            out = gen_assembly.recover_script(reply)
            code = out["test_code"] or ""
            manifest = gen_assembly.manifest_check(code)
            rows.append({
                "line": lineno,
                "ts": rec.get("ts"),
                "skeleton_chars": len(skeleton),
                "skeleton_classes": skeleton.count("class TestCase"),
                "reply_chars": len(reply),
                "recovered_chars": len(code),
                "recovered_classes": len(re.findall(r"^class TestCase", code, re.MULTILINE)),
                "parts": out["report"]["parts"],
                "parses": out["report"]["parses"],
                "manifest_ok": manifest["ok"],
                "expansion": round(len(code) / len(skeleton), 3) if skeleton else None,
            })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=DEFAULT_LOG)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.log):
        print(f"no debug log at {args.log}", file=sys.stderr)
        return 2
    rows = measure(args.log)
    if not rows:
        print("no generation replies found", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0

    print(f"{'ts':<22}{'parts':>6}{'skel':>9}{'recovered':>11}{'exp':>7}"
          f"{'skelTC':>8}{'gotTC':>7}  ok")
    for r in rows:
        print(f"{str(r['ts'])[:19]:<22}{r['parts']:>6}{r['skeleton_chars']:>9,}"
              f"{r['recovered_chars']:>11,}{r['expansion']:>7}"
              f"{r['skeleton_classes']:>8}{r['recovered_classes']:>7}"
              f"  {'y' if r['parses'] and r['manifest_ok'] else 'N'}")
    exps = sorted(r["expansion"] for r in rows if r["expansion"])
    multi = [r for r in rows if r["parts"] > 1]
    print(f"\nn={len(exps)}  min={exps[0]}  median={exps[len(exps) // 2]}  max={exps[-1]}")
    print(f"multi-part replies: {len(multi)} of {len(rows)} "
          f"({', '.join(str(r['parts']) for r in multi)} parts)")
    print("\nNOTE: every published expansion figure was measured on PARSER output, which "
          "dropped\nwhole continuation messages. Any constant fitted to those numbers is "
          "fitted to truncated data.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
