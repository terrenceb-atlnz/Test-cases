#!/usr/bin/env python3
"""PyTest Creator — Part 3a criterion-4 judging harness (PLAN-pytest-testing.md §3).

Criterion 4 — "Generated the missing steps" — grades the code the model had to INVENT
(no fragment to copy), on `exceptional / good / bad / not at all`. Two independent LLM
judges score each gap-fill block; the harness records both verdicts plus their
disagreement, and leaves a `human_verdict` field for the final holistic review.

Judges: **Claude Opus + vLLM-fast** (Terrence, 2026-07-27 — the plan's §5 decision-3
originally said Opus + vllm-thinking; §8.3 measured vllm-thinking burning its whole
token budget on reasoning and emitting nothing, so it was swapped. See §10.1.)

WHICH BLOCKS ARE JUDGED: exactly those whose authoritative provenance tag is
`# AI <model> <date>` rather than `# ART/SVT/legacy <source> lines a-b`. The tags are
server-stamped (§1.5) and cannot be faked, so they are the trustworthy split between
"reused" and "invented". A case with zero gap-fill steps (T33234) is correctly a no-op.

The judges are deliberately given the STEP'S OWN intent (action + verify text) and told
to grade whether the code actually achieves it — not whether it looks like valid Python.
The mechanical criteria already prove the structure is right; the whole point of
criterion 4 is to catch code that is structurally perfect and semantically wrong.

PROMPT NEUTRALITY (deliberate): we already expect one specific defect — T33235 step 6
renders a physical cable/SFP hot-swap as an administrative `shutdown`/`no shutdown` link
bounce. The prompt must NOT name it. An earlier draft spelled that substitution out as
an example of a "bad" grade, which would have made the judges' agreement on it worthless
as evidence — they would only be echoing the instruction. The prompt therefore raises the
general question ("if the action cannot be carried out by code, is the substitute
faithful?") and leaves the specific call to the judge. Keep it that way: a judge that
finds this unaided is informative; one that is told the answer is not.

Usage:
  python3 tool/pt_judge.py                          # all cases with gap-fill blocks
  python3 tool/pt_judge.py AWPTCM-T33235            # one case
  python3 tool/pt_judge.py --dry-run                # print prompts, call nothing
  python3 tool/pt_judge.py --judges opus            # a subset of judges
  python3 tool/pt_judge.py --out "ask-ck/pytest-create/judging/Port (7)"
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

REPO = Path(__file__).resolve().parent.parent
DB = REPO / "ask-ck" / "var" / "ck.db"

sys.path.insert(0, str(REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(REPO / "ask-ck" / "CK-main" / "CK_server"))
sys.path.insert(0, str(REPO / "tool"))

# Reuse the mechanical grader's parsing + the matrix harness's verified call paths
# rather than re-implementing either (same reason pt_grade imports the server helpers).
import pt_grade  # noqa: E402
from pt_model_matrix import call_vllm, call_claude_cli  # noqa: E402

SCALE = ["exceptional", "good", "bad", "not at all"]

JUDGES = {
    # id            kind          model/alias    label for the record
    "opus":       ("claude_cli", "opus",        "claude-opus"),
    "vllm-fast":  ("vllm",       "vllm-fast",   "vllm-fast"),
    # vllm-fast repeated N times on the same block, to measure its own consistency.
    # Motivated by a real observation: on T33235's physical hot-swap step it returned
    # "bad" three times and "good" once, explicitly defending the shutdown/no-shutdown
    # substitution as "standard" — so a single vote from it is not trustworthy on the
    # judgements that matter most. Registered as pseudo-judges so each repeat is an
    # independent call recorded in full, not an averaged-away number.
    **{f"vllm-fast-{i}": ("vllm", "vllm-fast", f"vllm-fast#{i}") for i in range(1, 6)},
}

PROMPT = """You are grading ONE block of auto-generated Python from an Allied Telesis ART \
test script. This block is GAP-FILL: no existing real script covered this step, so the \
model had to invent the logic. Your job is criterion 4 of a review rubric: \
"Generated the missing steps — quality of the gap-fill logic".

## The test case
{case_key} — {case_title}

## The step this block must implement
Step {step_n} action: {action}
Step {step_n} verification required: {verify}

## The generated code
```python
{code}
```

## How to grade
Grade ONLY whether this code genuinely achieves the step's stated intent on a real \
switch. Do NOT reward it for being syntactically valid, for following the template, or \
for having the right logging calls — those are graded mechanically elsewhere and are \
already known to pass. Assume the surrounding framework works.

Ask yourself:
- Does it perform the action the step actually describes, or a superficially similar \
but materially different one?
- Does the assertion verify the thing the step says to verify, or something weaker?
- Are the CLI commands and the output strings it matches on plausible for an Allied \
Telesis switch?
- Could this pass while the feature under test is broken (a false green)?

A block that is structurally perfect but tests the wrong thing is "bad", not "good".
If the step's action cannot actually be carried out by the code shown (for example it \
describes a change to the physical setup), judge whether what the code does instead is \
a faithful substitute or a materially weaker one.

Scale (choose exactly one):
- "exceptional" — correctly implements the step, and handles a real subtlety \
(timing, error path, precise state check) a competent engineer would have to think about
- "good" — correctly implements the step; a reviewer would accept it with at most minor edits
- "bad" — runs, but tests the wrong thing, verifies too weakly, or could pass while broken
- "not at all" — does not attempt the step's actual intent

## Output
Reply with ONLY a JSON object, no prose around it:
{{"verdict": "<one of: exceptional | good | bad | not at all>",
  "confidence": "<high | medium | low>",
  "rationale": "<2-4 sentences: what it does, and why that does or does not satisfy the step>",
  "concrete_problem": "<the single most important defect, or null if none>"}}
"""


# --------------------------------------------------------------------------- extraction


def gap_fill_blocks(code: str, sequence: List[dict]) -> List[dict]:
    """Every TestCase whose authoritative provenance tag is `# AI ...` (i.e. invented).

    The TestCase_<n> number is the CONTIGUOUS 1..N index over VERIFY steps, while the
    sequence's own `n` is the original step number — they diverge whenever a setup step
    is dropped. Map back through the same verify-step list the generator used so the
    judge is shown the step the block actually implements.
    """
    tree = ast.parse(code)
    verify_steps = [s for s in sequence if pt_grade._step_kind(s) != "setup"] or list(sequence)

    out = []
    for cls in pt_grade.testcase_classes(tree):
        fn = pt_grade.method(cls, "main")
        if fn is None:
            continue
        tag = pt_grade.leading_tag(code, fn)
        if not tag or not re.match(r"#\s*AI\b", tag, re.IGNORECASE):
            continue                                    # reused, not gap-fill
        class_n = int(cls.name.split("_")[1])
        step = verify_steps[class_n - 1] if class_n <= len(verify_steps) else {}
        attrs = pt_grade.class_attrs(cls)
        out.append({
            "testcase": cls.name,
            "class_n": class_n,
            "step_n": step.get("n", class_n),
            "action": (step.get("action") or attrs.get("testCaseDesc") or "").strip(),
            "verify": (step.get("verify") or "").strip(),
            "tag": tag,
            "code": pt_grade.main_body_source(code, fn),
        })
    return out


def build_prompt(case_key: str, case_title: str, block: dict) -> str:
    return PROMPT.format(
        case_key=case_key, case_title=case_title,
        step_n=block["step_n"],
        action=block["action"] or "(no action text recorded)",
        verify=block["verify"] or "(no verification text recorded)",
        code=block["code"],
    )


# --------------------------------------------------------------------------- judging


def parse_verdict(raw: str) -> dict:
    """Pull the JSON verdict out of a judge reply, tolerating fences/prose.

    Uses the server's own hardened extractor (string-and-escape aware, fence-tolerant —
    the 2026-07-27e fix) rather than a fresh regex that would repeat the bugs it fixed.
    """
    if not raw:
        return {"parse_error": "empty response"}
    try:
        import llm
        obj = llm.extract_json_block(raw)
    except Exception:                                    # extractor unavailable
        obj = None
    if not isinstance(obj, dict):
        return {"parse_error": "no JSON object in response", "raw_excerpt": raw[:400]}

    verdict = str(obj.get("verdict", "")).strip().lower()
    if verdict not in SCALE:
        # Judges occasionally answer "not-at-all"/"none"; normalise before failing.
        norm = verdict.replace("-", " ").replace("_", " ")
        verdict = norm if norm in SCALE else ""
    return {
        "verdict": verdict or None,
        "confidence": obj.get("confidence"),
        "rationale": obj.get("rationale"),
        "concrete_problem": obj.get("concrete_problem"),
        "unparsed_verdict": None if verdict else obj.get("verdict"),
    }


def run_judge(judge_id: str, prompt: str) -> dict:
    kind, model, label = JUDGES[judge_id]
    # llm.py narrates each call to stdout ("[LLM ...] Provider: ..."). That is useful
    # progress on a terminal but corrupts --json, so send it to stderr for the duration
    # of the call instead of changing the shared server module's logging.
    with contextlib.redirect_stdout(sys.stderr):
        res = call_vllm(prompt, model) if kind == "vllm" else call_claude_cli(prompt, model)
    row = {"judge": label, "model": model,
           "latency_ms": res.get("latency_ms"),
           "tok_in": res.get("tok_in"), "tok_out": res.get("tok_out")}
    if res.get("error"):
        # An errored judge is recorded, never silently dropped (plan §2 Phase 2B rule).
        row["error"] = res["error"]
        row["verdict"] = None
        return row
    row.update(parse_verdict(res.get("output") or ""))
    return row


def agreement(verdicts: List[Optional[str]]) -> str:
    got = [v for v in verdicts if v]
    if len(got) < 2:
        return "insufficient"                            # a judge errored
    if len(set(got)) == 1:
        return "agree"
    # adjacent on the scale (good vs exceptional) is a softer split than good vs bad
    idx = sorted(SCALE.index(v) for v in got)
    return "near-miss" if idx[-1] - idx[0] == 1 else "disagree"


def self_consistency(judged: List[dict]) -> dict:
    """How stable is a repeated judge on THIS block?

    With vllm-fast run N times, an unstable verdict is itself a finding: it means a
    single vote from that judge cannot be trusted here. Reported per model rather than
    collapsed to one number, so the human review sees the spread.
    """
    by_model: Dict[str, List[str]] = {}
    for j in judged:
        v = j.get("verdict")
        if v:
            by_model.setdefault(j.get("model", "?"), []).append(v)
    out = {}
    for model, votes in by_model.items():
        if len(votes) < 2:
            continue
        counts: Dict[str, int] = {}
        for v in votes:
            counts[v] = counts.get(v, 0) + 1
        top, n = max(counts.items(), key=lambda kv: kv[1])
        out[model] = {
            "runs": len(votes),
            "distinct": len(counts),
            "majority": top,
            "majority_share": f"{n}/{len(votes)}",
            "stable": len(counts) == 1,
            "votes": votes,
        }
    return out


# --------------------------------------------------------------------------- driver


def judge_case(conn: sqlite3.Connection, case_key: str, judge_ids: List[str],
               dry_run: bool = False) -> dict:
    payload = pt_grade.load_case(conn, case_key)
    if payload is None:
        return {"case_key": case_key, "error": "no pt session"}
    _, code = pt_grade.script_of(payload)
    if not code:
        return {"case_key": case_key, "error": "no generated script (step 6 not run)"}

    sequence = (payload.get("step2") or {}).get("sequence") or []
    title = _case_title(conn, case_key)
    blocks = gap_fill_blocks(code, sequence)

    if not blocks:
        return {"case_key": case_key, "gap_fill_blocks": 0,
                "note": "no gap-fill steps — every TestCase reuses a real fragment, so "
                        "criterion 4 does not apply to this case",
                "results": []}

    results = []
    for b in blocks:
        prompt = build_prompt(case_key, title, b)
        if dry_run:
            results.append({**{k: b[k] for k in ("testcase", "step_n", "action")},
                            "prompt": prompt, "prompt_chars": len(prompt)})
            continue
        judged = [run_judge(j, prompt) for j in judge_ids]
        results.append({
            "testcase": b["testcase"],
            "step_n": b["step_n"],
            "action": b["action"],
            "verify": b["verify"],
            "tag": b["tag"],
            "judges": judged,
            "agreement": agreement([j.get("verdict") for j in judged]),
            "self_consistency": self_consistency(judged),
            # filled in by the human holistic review (plan §3)
            "human_verdict": None,
            "human_note": None,
        })

    return {
        "case_key": case_key,
        "case_title": title,
        "criterion": "4 — generated the missing steps (gap-fill quality)",
        "scale": SCALE,
        "judges": [JUDGES[j][2] for j in judge_ids],
        "judged_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "gap_fill_blocks": len(blocks),
        "total_testcases": len(pt_grade.testcase_classes(ast.parse(code))),
        "results": results,
    }


def _case_title(conn: sqlite3.Connection, case_key: str) -> str:
    row = conn.execute(
        "SELECT title FROM zephyr_cases WHERE key=?", (case_key,)).fetchone()
    return (row[0] if row and row[0] else case_key)


def print_report(r: dict) -> None:
    if r.get("error"):
        print(f"  {r['case_key']}: ERROR — {r['error']}")
        return
    print(f"\n=== {r['case_key']} — {r.get('case_title','')} ===")
    if not r.get("gap_fill_blocks"):
        print(f"  {r.get('note')}")
        return
    print(f"  {r['gap_fill_blocks']} gap-fill of {r.get('total_testcases','?')} TestCases"
          f" | judges: {', '.join(r.get('judges', []))}")
    for res in r["results"]:
        if "prompt" in res:                              # dry run
            print(f"\n  --- {res['testcase']} (step {res['step_n']}), "
                  f"{res['prompt_chars']} chars ---")
            print(res["prompt"])
            continue
        flag = {"agree": "  ", "near-miss": "~ ", "disagree": "! ",
                "insufficient": "? "}[res["agreement"]]
        print(f"\n{flag}{res['testcase']} (step {res['step_n']}) — {res['agreement'].upper()}")
        print(f"    step: {res['action'][:100]}")
        for j in res["judges"]:
            if j.get("error"):
                print(f"    {j['judge']:<14} ERROR — {str(j['error'])[:90]}")
                continue
            v = j.get("verdict") or f"UNPARSED({j.get('unparsed_verdict')})"
            print(f"    {j['judge']:<14} {v:<12} ({j.get('confidence','?')})"
                  f"  {(j.get('rationale') or '')[:120]}")
            if j.get("concrete_problem"):
                print(f"    {'':<14} → {str(j['concrete_problem'])[:120]}")


def summarize(reports: List[dict]) -> None:
    rows = [res for r in reports for res in r.get("results", []) if "judges" in res]
    if not rows:
        return
    print(f"\n{'='*70}\nCriterion 4 summary — {len(rows)} gap-fill block(s) judged")
    for label in ("agree", "near-miss", "disagree", "insufficient"):
        n = sum(1 for x in rows if x["agreement"] == label)
        if n:
            print(f"  {label:<13} {n}")
    print("\n  verdict distribution per judge:")
    judges = [j["judge"] for j in rows[0]["judges"]]
    for ji, jname in enumerate(judges):
        dist: Dict[str, int] = {}
        for x in rows:
            v = x["judges"][ji].get("verdict") or "error/unparsed"
            dist[v] = dist.get(v, 0) + 1
        print(f"    {jname:<14} " + ", ".join(f"{k}={v}" for k, v in sorted(dist.items())))
    flagged = [x for x in rows if x["agreement"] in ("disagree", "insufficient")]
    if flagged:
        print("\n  needs your attention first (judges split or a judge failed):")
        for x in flagged:
            print(f"    - {x['testcase']} step {x['step_n']}: "
                  + " vs ".join(str(j.get('verdict') or 'ERROR') for j in x["judges"]))
    print("\n  Every block still needs a human_verdict — the judges advise, you decide.")


def main() -> int:
    ap = argparse.ArgumentParser(description="Part 3a criterion-4 judging (gap-fill quality)")
    ap.add_argument("case_keys", nargs="*", help="AWPTCM-Txxxxx (default: all pt sessions)")
    ap.add_argument("--judges", default="opus,vllm-fast",
                    help=f"comma-separated subset of {list(JUDGES)}")
    ap.add_argument("--dry-run", action="store_true",
                    help="render prompts and call nothing (zero tokens)")
    ap.add_argument("--json", action="store_true", help="emit JSON to stdout")
    ap.add_argument("--out", metavar="DIR", help="write <case>/criterion4.json under DIR")
    args = ap.parse_args()

    judge_ids = [j.strip() for j in args.judges.split(",") if j.strip()]
    unknown = [j for j in judge_ids if j not in JUDGES]
    if unknown:
        print(f"unknown judge(s): {unknown}; known: {list(JUDGES)}", file=sys.stderr)
        return 2
    if not DB.exists():
        print(f"ck.db not found at {DB}", file=sys.stderr)
        return 2

    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    keys = args.case_keys or pt_grade.all_case_keys(conn)
    reports = [judge_case(conn, k, judge_ids, args.dry_run) for k in keys]

    if args.json:
        print(json.dumps(reports, indent=2))
    else:
        print(f"PyTest Creator — criterion 4 (gap-fill quality), {len(reports)} case(s)")
        for r in reports:
            print_report(r)
        if not args.dry_run:
            summarize(reports)
        print()

    if args.out and not args.dry_run:
        n = stale = 0
        for r in reports:
            if r.get("error"):
                continue
            d = Path(args.out) / r["case_key"]
            target = d / "criterion4.json"
            # A case with zero gap-fill blocks must still be WRITTEN, not skipped.
            # Skipping left a previous run's file in place — observed live: T33235 kept a
            # 13:43 file claiming 7 judged blocks long after regeneration made every
            # TestCase fragment-backed (0 gap-fill). A stale artifact that looks current
            # is worse than none, because the next session compares against it.
            if not r.get("gap_fill_blocks"):
                if target.exists():
                    target.unlink()
                    stale += 1
                d.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(r, indent=2))
                n += 1
                continue
            d.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(r, indent=2))
            n += 1
        msg = f"wrote criterion4.json for {n} case(s) under {args.out}"
        if stale:
            msg += f" (replaced {stale} stale no-gap-fill artifact(s))"
        print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
