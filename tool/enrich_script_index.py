#!/usr/bin/env python3
"""LLM enrichment pass for the PyTest Creator script index (resumable).

Reads the mechanical scripts_index.json, batches unenriched records through the
enrich_script_index.jinja prompt (via the Ask CK LLM layer — Grok CLI or Claude
Code CLI, whichever the workspace is logged into), and appends results to
scripts_index_enrich.jsonl keyed by file sha1. Re-runs skip already-enriched
sha1s, so the pass can be stopped and resumed at any time.

After enriching, re-run build_script_index.py (no flags) to merge the results
into scripts_index.json / scripts_slim_index.json.

Usage:
    ./enrich_script_index.py [--limit N] [--batch 10]
    ./build_script_index.py --enrich [N]      # same thing + rebuild
"""
import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PT_DATA_DIR = REPO_ROOT / "ask-ck" / "pytest-create" / "data"
CK_SERVER = REPO_ROOT / "ask-ck" / "CK-main" / "CK_server"
ENRICH_JSONL = PT_DATA_DIR / "scripts_index_enrich.jsonl"

sys.path.insert(0, str(CK_SERVER))


def _load_workspace_llm() -> dict:
    """Resolve an LLM config usable from THIS standalone (no-browser) process.

    The UI's workspace default may be "claude_agent" (browser-brokered) — that only
    works with a live browser tab, so it's useless here. This tool runs `claude`/`grok`
    directly, so we normalize claude_agent -> claude_code (server-local CLI) and keep
    grok_cli / api_key as-is. Env override: CK_ENRICH_PROVIDER / CK_ENRICH_AUTH.
    """
    path = CK_SERVER / "sessions" / "_workspace_llm.json"
    cfg = {}
    if path.exists():
        try:
            cfg = json.load(open(path, encoding="utf-8"))
        except Exception:
            cfg = {}
    # Browser-only mode can't run headless — use the local CLI directly instead.
    if (cfg.get("auth_method") or "").lower() == "claude_agent":
        cfg["auth_method"] = "claude_code"
    # Explicit overrides for running against a chosen backend from the shell.
    if os.environ.get("CK_ENRICH_PROVIDER"):
        cfg["provider"] = os.environ["CK_ENRICH_PROVIDER"]
    if os.environ.get("CK_ENRICH_AUTH"):
        cfg["auth_method"] = os.environ["CK_ENRICH_AUTH"]
    if not cfg:
        # No stored config: default to the locally logged-in Claude Code CLI.
        cfg = {"provider": "claude", "auth_method": "claude_code"}
    return cfg


def _seen_sha1s() -> set:
    seen = set()
    if ENRICH_JSONL.exists():
        for line in ENRICH_JSONL.read_text(encoding="utf-8").splitlines():
            try:
                seen.add(json.loads(line)["sha1"])
            except Exception:
                continue
    return seen


def run_enrichment(limit: int = 50, batch_size: int = 10) -> int:
    from llm import run_prompt, extract_json_block  # CK_server import

    index_path = PT_DATA_DIR / "scripts_index.json"
    if not index_path.exists():
        sys.exit("scripts_index.json missing — run build_script_index.py first.")
    records = json.load(open(index_path, encoding="utf-8"))
    seen = _seen_sha1s()
    todo = [r for r in records if r["sha1"] not in seen]
    print(f"{len(records)} indexed, {len(seen)} already enriched, "
          f"{len(todo)} remaining; enriching up to {limit} this run", file=sys.stderr)
    todo = todo[:limit]
    if not todo:
        return 0

    llm_cfg = _load_workspace_llm()
    if not llm_cfg:
        print("NOTE: no workspace LLM login found (sessions/_workspace_llm.json); "
              "falling back to LLM_API_KEY env / default provider.", file=sys.stderr)

    done = 0
    with open(ENRICH_JSONL, "a", encoding="utf-8") as out:
        for i in range(0, len(todo), batch_size):
            chunk = todo[i:i + batch_size]
            slim_records = [{k: r.get(k) for k in
                             ("id", "kind", "suite_dir", "parse_error", "imports",
                              "docstring", "test_cases", "helpers")} for r in chunk]
            meta = run_prompt("enrich_script_index.jinja",
                              {"records": slim_records}, llm_config=llm_cfg, timeout=300)
            if meta.get("error"):
                print(f"LLM error on batch {i // batch_size}: "
                      f"{meta.get('content', '')[:200]}", file=sys.stderr)
                break  # resumable — stop cleanly, rerun later
            parsed = extract_json_block(meta.get("content", ""))
            # Tolerate both {"enriched": [...]} and a bare [...] array from the LLM.
            if isinstance(parsed, list):
                rows = parsed
            elif isinstance(parsed, dict):
                rows = parsed.get("enriched") or []
            else:
                rows = []
            by_id = {e.get("id"): e for e in rows if isinstance(e, dict)}
            sha_by_id = {r["id"]: r["sha1"] for r in chunk}
            for rid, sha in sha_by_id.items():
                e = by_id.get(rid)
                if not e:
                    print(f"  missing enrichment for {rid} (will retry next run)", file=sys.stderr)
                    continue
                row = {"sha1": sha, "id": rid,
                       "summary": e.get("summary", ""),
                       "feature_tags": e.get("feature_tags", []),
                       "covered_actions": e.get("covered_actions", [])}
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
                out.flush()
                done += 1
            print(f"  batch {i // batch_size + 1}: {done} enriched so far", file=sys.stderr)
    print(f"enriched {done} records -> {ENRICH_JSONL}", file=sys.stderr)
    if done:
        print("Re-run build_script_index.py to merge into the index files.", file=sys.stderr)
    return done


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=50, help="max files to enrich this run")
    ap.add_argument("--batch", type=int, default=10, help="records per LLM call")
    args = ap.parse_args()
    run_enrichment(limit=args.limit, batch_size=args.batch)


if __name__ == "__main__":
    main()
