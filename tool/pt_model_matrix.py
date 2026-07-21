#!/usr/bin/env python3
"""PyTest Creator — Part 2B model-comparison harness.

Runs the SAME rendered prompt for a given (case, step) through each model in
the comparison matrix and records a structured result row per (model, step,
case): {model, step, case, prompt_hash, output, tok_in, tok_out, latency_ms,
error}. See ask-ck/pytest-create/PLAN-pytest-testing.md §2 Phase 2B.

Design:
- The exact prompt is captured ONCE per (case, step) via the real running
  server's `dry_run: true` flag on the step's own endpoint (e.g.
  POST /api/pytest-create/extract_sequence/{key}). This reuses the real
  context-building path (fragments/sequence/etc already reviewed+confirmed in
  that case's session) so the prompt is byte-identical to what a real send
  would transmit -- the same guarantee the UI's Provenance "Refresh" button
  relies on. It does NOT mutate the session (dry_run short-circuits before any
  session write).
- Each model in the matrix is then called DIRECTLY (bypassing the router
  entirely), so the comparison run never touches PyTest Creator session state.
  vLLM goes through llm._call_llm_raw (same call path production uses,
  including the (connect, read) timeout split and reasoning-model max_tokens
  handling fixed this session). Claude tiers go through the verified headless
  `claude -p --model <alias>` CLI (this project's confirmed-live Claude access
  path; see SESSION_STATE.md decisions log).
- Grok is a matrix member per the plan, but this seat's Grok CLI login is
  live and genuinely out of quota (403 "used all available credits" from
  cli-chat-proxy.grok.com, verified 2026-07-22) -- omitted with a logged
  reason rather than silently skipped, per the plan's own instruction.

Usage:
    python3 tool/pt_model_matrix.py --case AWPTCM-T33234 --step extract_sequence
    python3 tool/pt_model_matrix.py --case AWPTCM-T33234 --all-steps
    python3 tool/pt_model_matrix.py --all-cases --all-steps

Results land at ask-ck/pytest-create/comparison/<Group>/<CaseKey>/<step>.json
(per-case layout, mirroring refined-cases/ and generated/ -- PLAN §5 decision 4).
Committed, not gitignored: prompts/outputs/tokens only, no credentials.
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
CK_SERVER_DIR = REPO_ROOT / "ask-ck" / "CK-main" / "CK_server"
sys.path.insert(0, str(CK_SERVER_DIR))

import llm  # noqa: E402  (CK_server flat-module layout)

SERVER = "http://localhost:8000"
RESULTS_ROOT = REPO_ROOT / "ask-ck" / "pytest-create" / "comparison"

# Steps in the model matrix (PLAN §2 Phase 2B) with their endpoint + the
# provider/model each would use by default (vLLM path) -- we override per run.
STEPS = ["extract_sequence", "suggest_scripts", "assess_fit", "gather_fragments", "generate_script"]

TARGET_CASES = ["AWPTCM-T33233", "AWPTCM-T33234", "AWPTCM-T33235"]

# --- Model matrix -----------------------------------------------------------
# Each entry: (label, kind, spec). kind="vllm" calls the org endpoint directly
# via llm._call_llm_raw; kind="claude_cli" shells out to the verified headless
# `claude -p --model <alias>` path.
MODEL_MATRIX = [
    ("vllm-fast", "vllm", "vllm-fast"),
    ("vllm-thinking", "vllm", "vllm-thinking"),
    ("claude-haiku", "claude_cli", "claude-haiku-4-5-20251001"),
    ("claude-sonnet", "claude_cli", "sonnet"),
    ("claude-opus", "claude_cli", "opus"),
]
# Grok CLI is logged in but returned a real 403 quota-exhausted error from
# cli-chat-proxy.grok.com on 2026-07-22 -- omitted, not silently dropped.
OMITTED_MODELS = [
    {"label": "grok-cli", "reason": "logged in, but account quota/spending limit exhausted "
                                     "(403 from cli-chat-proxy.grok.com, verified 2026-07-22)"},
]


def _prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


def get_dry_run_prompt(case_key: str, step: str) -> Dict[str, Any]:
    """Fetch the exact rendered prompt for (case, step) via the real endpoint's
    dry_run flag -- does not touch session state (dry_run short-circuits
    before any write in the router)."""
    resp = requests.post(f"{SERVER}/api/pytest-create/{step}/{case_key}",
                         json={"dry_run": True}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    prov = data.get("provenance", {})
    if not prov.get("prompt"):
        raise RuntimeError(f"dry_run for {step}/{case_key} returned no prompt: {data}")
    return prov


def call_vllm(prompt: str, model: str, max_tokens: Optional[int] = None) -> Dict[str, Any]:
    key = llm.get_local_llm_key()
    if not key:
        return {"error": "no local_llm key stored (secrets.local.json)"}
    start = time.monotonic()
    meta = llm._call_llm_raw(
        prompt, provider="", api_key=key, model=model, auth_method="local_llm",
        timeout=300, system=llm._JSON_SYSTEM_PROMPT, max_tokens=max_tokens,
    )
    latency_ms = int((time.monotonic() - start) * 1000)
    usage = (meta.get("raw_response") or {}).get("usage") or {}
    return {
        "error": meta.get("content") if meta.get("error") else None,
        "output": meta.get("content") if not meta.get("error") else None,
        "tok_in": usage.get("prompt_tokens"),
        "tok_out": usage.get("completion_tokens"),
        "latency_ms": latency_ms,
    }


def call_claude_cli(prompt: str, model_alias: str) -> Dict[str, Any]:
    start = time.monotonic()
    try:
        proc = subprocess.run(
            ["claude", "-p", prompt, "--model", model_alias, "--output-format", "json"],
            capture_output=True, text=True, timeout=300,
        )
    except subprocess.TimeoutExpired:
        return {"error": "claude CLI call timed out after 300s"}
    latency_ms = int((time.monotonic() - start) * 1000)
    if proc.returncode != 0:
        return {"error": f"claude CLI exit {proc.returncode}: {proc.stderr[:500]}"}
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"error": f"claude CLI returned non-JSON: {proc.stdout[:500]}"}
    usage = data.get("usage") or {}
    # claude -p's `input_tokens` is only the UNCACHED portion -- this harness's
    # own long-running CLI session accumulates a large cache_read/creation
    # baseline that dwarfs the actual per-call prompt, so it is NOT comparable
    # to vLLM's tok_in (which has no caching layer) on its own. Record the full
    # breakdown and let the comparison read cache_read+cache_creation+input as
    # the effective prompt cost, not input_tokens alone.
    return {
        "error": data.get("result") if data.get("is_error") else None,
        "output": data.get("result") if not data.get("is_error") else None,
        "tok_in": usage.get("input_tokens"),
        "tok_in_cache_read": usage.get("cache_read_input_tokens"),
        "tok_in_cache_creation": usage.get("cache_creation_input_tokens"),
        "tok_out": usage.get("output_tokens"),
        "latency_ms": latency_ms,
        "cost_usd": data.get("total_cost_usd"),
    }


def run_one(case_key: str, step: str, group_display: str) -> Dict[str, Any]:
    prov = get_dry_run_prompt(case_key, step)
    prompt = prov["prompt"]
    phash = _prompt_hash(prompt)
    # generate_script/fix_script need the raised completion cap (Part 2B found
    # the 16000 default truncates a real generate_script call this session).
    max_tokens = 32000 if step == "generate_script" else None

    rows: List[Dict[str, Any]] = []
    for label, kind, spec in MODEL_MATRIX:
        print(f"  [{case_key}/{step}] {label} ...", flush=True)
        if kind == "vllm":
            result = call_vllm(prompt, spec, max_tokens=max_tokens)
        elif kind == "claude_cli":
            result = call_claude_cli(prompt, spec)
        else:
            result = {"error": f"unknown model kind {kind}"}
        rows.append({
            "case": case_key, "step": step, "model": label,
            "prompt_hash": phash, **result,
        })
        status = "ERROR" if result.get("error") else "ok"
        print(f"    -> {status}  tok_in={result.get('tok_in')} tok_out={result.get('tok_out')} "
              f"latency_ms={result.get('latency_ms')}", flush=True)

    out = {
        "case": case_key, "step": step, "group": group_display,
        "prompt_hash": phash, "prompt": prompt,
        "rows": rows, "omitted": OMITTED_MODELS,
    }
    out_dir = RESULTS_ROOT / group_display / case_key
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{step}.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"  saved -> {out_path}")
    return out


def group_for(case_key: str) -> str:
    resp = requests.post(f"{SERVER}/api/pytest-create/load_case/{case_key}",
                         json={}, timeout=30)
    resp.raise_for_status()
    sess = resp.json().get("session") or {}
    return sess.get("group") or "Ungrouped"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", help="single case key, e.g. AWPTCM-T33234")
    ap.add_argument("--all-cases", action="store_true", help="run all three target cases")
    ap.add_argument("--step", choices=STEPS, help="single step")
    ap.add_argument("--all-steps", action="store_true", help="run all model-matrix steps")
    args = ap.parse_args()

    cases = TARGET_CASES if args.all_cases else ([args.case] if args.case else [])
    steps = STEPS if args.all_steps else ([args.step] if args.step else [])
    if not cases or not steps:
        ap.error("specify --case/--all-cases AND --step/--all-steps")

    for case_key in cases:
        group_display = group_for(case_key)
        for step in steps:
            print(f"=== {case_key} / {step} ===")
            try:
                run_one(case_key, step, group_display)
            except Exception as e:
                print(f"  FAILED: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
