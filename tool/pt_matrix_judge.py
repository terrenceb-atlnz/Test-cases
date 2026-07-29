#!/usr/bin/env python3
"""PyTest Creator — model-matrix side-by-side judging (companion to pt_model_matrix.py).

pt_model_matrix.py generates each case's script on every model in the matrix; this tool
grades each of those scripts HOLISTICALLY against the case objective + step sequence, with
two judges (Claude Opus + vLLM-fast), and emits a case x generating-model comparison.

Holistic (whole script vs objective) rather than pt_judge's criterion-4-per-block, because
matrix outputs are raw model responses with no server-restamped `# AI` provenance tags — but
the grading philosophy is the same (false-green-focused, don't reward mechanics). Use pt_judge
for the single ck.db script's per-block criterion 4; use THIS for "which model generates the
best script for this case".

Reads   ask-ck/pytest-create/comparison/<Group>/<Case>/generate_script.json  (the matrix)
Writes  ...generate_script.judged.json  next to each, and prints the comparison table.

Operational lessons baked in (learned 2026-07-29, see part3-grading-session memory):
- `claude -p` on a ~25KB judge prompt under concurrency needs > the 300s pt_model_matrix cap;
  we use 600s and cap concurrency at 3.
- vLLM-fast is a REASONING model — a small max_tokens makes it spend the whole budget on
  reasoning and return nothing (finish_reason=length); the judge call uses max_tokens=16000.

Usage:
  python3 tool/pt_matrix_judge.py --all-cases
  python3 tool/pt_matrix_judge.py --case AWPTCM-T33234
"""
from __future__ import annotations
import argparse
import json
import re
import sqlite3
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tool"))
sys.path.insert(0, str(REPO / "ask-ck" / "CK-main" / "CK_server"))
import pt_model_matrix as M          # call_vllm, MODEL_MATRIX, _prompt_hash
import pt_judge as J                 # parse_verdict, SCALE

DB = REPO / "ask-ck" / "var" / "ck.db"
COMP = REPO / "ask-ck" / "pytest-create" / "comparison"
DEFAULT_CASES = ["AWPTCM-T33233", "AWPTCM-T33234", "AWPTCM-T33235"]
JUDGES = ["claude-opus", "vllm-fast"]
CLAUDE_TIMEOUT = 600
VLLM_JUDGE_MAX_TOKENS = 16000
MAX_WORKERS = 3

HOLISTIC = """You are grading a COMPLETE auto-generated Allied Telesis ART test script, \
produced by an LLM from a test case's objective and step sequence. Judge how well the \
SCRIPT AS A WHOLE tests the objective on a real switch.

## The test case
{case_key} — {case_title}

## Objective (what the script must demonstrate)
{objective}

## The step sequence it should cover
{steps}

## The generated script
```python
{code}
```

## How to grade
Grade whether the script genuinely and completely tests the objective on real hardware. Do \
NOT reward syntactic validity, template conformance, or logging calls — those are graded \
mechanically elsewhere and already pass. Assume the framework works. Consider:
- Does every part of the objective get exercised by some TestCase's action + assertion?
- Do assertions verify the feature under test, or merely that the link survived (a false green)?
- Are the CLI commands and matched output strings plausible for an Allied Telesis switch, or invented?
- Where a step needs a physical action (cable/SFP swap), is the substitute faithful or a materially weaker administrative stand-in?

Scale (choose exactly one):
- "exceptional" — correct + complete, and handles a real subtlety (timing, error path, precise state check) a competent engineer would weigh
- "good" — correct + complete; a reviewer would accept it with at most minor edits
- "bad" — runs, but tests the wrong thing, verifies too weakly, or could pass while broken
- "not at all" — does not test the objective

## Output — reply with ONLY a JSON object, no prose:
{{"verdict":"<exceptional|good|bad|not at all>","confidence":"<high|medium|low>",\
"rationale":"<2-4 sentences>","concrete_problem":"<single most important defect, or null>"}}
"""


def strip_html(s: str) -> str:
    s = (s or "").replace("&nbsp;", " ").replace("<li>", "\n- ")
    return re.sub(r"<[^>]+>", " ", s).strip()


def extract_py(raw: str) -> str:
    if not raw:
        return ""
    m = re.search(r"```(?:python)?\s*\n(.*?)```", raw, re.S)
    return (m.group(1) if m else raw).strip()


def case_context(conn: sqlite3.Connection, key: str):
    row = conn.execute("SELECT payload FROM sessions WHERE kind='pt' AND case_key=?", (key,)).fetchone()
    if not row:
        return key, "", ""
    p = json.loads(row[0])
    body = (p.get("payload") or {}).get(key) or {}
    objective = strip_html(body.get("objective", ""))
    seq = (p.get("step2") or {}).get("sequence") or []
    steps = "\n".join(f"{s.get('n')}. {s.get('action','')}  -> verify: {s.get('verify','')}" for s in seq)
    return (body.get("title") or key), objective, steps


def call_claude(prompt: str, alias: str) -> dict:
    try:
        proc = subprocess.run(["claude", "-p", prompt, "--model", alias, "--output-format", "json"],
                              capture_output=True, text=True, timeout=CLAUDE_TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"error": f"claude CLI timed out after {CLAUDE_TIMEOUT}s"}
    if proc.returncode != 0:
        return {"error": f"claude exit {proc.returncode}: {proc.stderr[:200]}"}
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"error": f"claude non-JSON: {proc.stdout[:200]}"}
    return {"error": data.get("result") if data.get("is_error") else None,
            "output": data.get("result") if not data.get("is_error") else None}


def judge(prompt: str, judge_id: str) -> dict:
    if judge_id == "vllm-fast":
        res = M.call_vllm(prompt, "vllm-fast", max_tokens=VLLM_JUDGE_MAX_TOKENS)
    else:  # claude-opus
        res = call_claude(prompt, "opus")
    if res.get("error"):
        return {"verdict": None, "error": (res["error"] or "")[:200]}
    return J.parse_verdict(res.get("output") or "")


def main() -> int:
    ap = argparse.ArgumentParser(description="Side-by-side holistic judging of the model matrix")
    ap.add_argument("--case", help="single case key")
    ap.add_argument("--all-cases", action="store_true", help="all target cases")
    args = ap.parse_args()
    cases = [args.case] if args.case else (DEFAULT_CASES if args.all_cases else None)
    if not cases:
        ap.error("pass --case <key> or --all-cases")
    if not DB.exists():
        print(f"ck.db not found at {DB}", file=sys.stderr); return 1

    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    order = [m[0] for m in M.MODEL_MATRIX]
    per_case, tasks = {}, []
    for key in cases:
        title, objective, steps = case_context(conn, key)
        cfiles = list(COMP.glob(f"*/{key}/generate_script.json"))
        if not cfiles:
            print(f"!! no matrix output for {key} — run pt_model_matrix first", file=sys.stderr); continue
        data = json.loads(cfiles[0].read_text())
        per_case[key] = {"file": cfiles[0], "models": {}}
        for row in data.get("rows", []):
            gm = row["model"]
            if row.get("error"):
                per_case[key]["models"][gm] = {"gen_error": (row["error"] or "")[:160]}
                continue
            code = extract_py(row.get("output"))
            per_case[key]["models"][gm] = {"chars": len(code)}
            prompt = HOLISTIC.format(case_key=key, case_title=title, objective=objective, steps=steps, code=code)
            for jid in JUDGES:
                tasks.append((key, gm, jid, prompt))

    print(f"judging {len(tasks)} (case x gen-model x judge) tasks, max_workers={MAX_WORKERS} ...", flush=True)
    def run(t):
        key, gm, jid, prompt = t
        return key, gm, jid, judge(prompt, jid)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        for key, gm, jid, v in ex.map(run, tasks):
            per_case[key]["models"][gm][jid] = v
            print(f"  {key}/{gm}/{jid}: {v.get('verdict') or ('ERR:' + (v.get('error') or '')[:40])}", flush=True)

    for key, pc in per_case.items():
        out = {"case": key, "judges": JUDGES, "models": pc["models"]}
        (pc["file"].parent / "generate_script.judged.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    print("\n================ SIDE-BY-SIDE — holistic grade of each model's script ================")
    hdr = f"{'case':<16}{'gen-model':<16}{'opus-judge':<13}{'vllm-fast-judge':<17}chars"
    print(hdr); print("-" * len(hdr))
    for key in cases:
        if key not in per_case:
            continue
        for gm in order:
            cell = per_case[key]["models"].get(gm)
            if not cell:
                continue
            if cell.get("gen_error"):
                print(f"{key:<16}{gm:<16}{'(gen error)':<30}"); continue
            ov = (cell.get("claude-opus") or {}).get("verdict") or "?"
            vv = (cell.get("vllm-fast") or {}).get("verdict") or ("ERR" if (cell.get("vllm-fast") or {}).get("error") else "?")
            print(f"{key:<16}{gm:<16}{str(ov):<13}{str(vv):<17}{cell.get('chars')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
