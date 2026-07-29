---
name: llm-provenance-portability
description: Provenance is a permanent portability feature (paste prompt into competing LLMs); debug-log is dev-only scaffolding and its 1-for-1 match with provenance is the correctness oracle
metadata: 
  node_type: memory
  type: project
  originSessionId: 1f9e36f4-a5b5-4411-a4d1-2f252538a06b
  modified: 2026-07-19T22:18:29.360Z
---

**Terrence's intent (2026-07-20):** the per-panel "LLM Provenance" `<details>` block is a **permanent product feature**, not a debug aid. Purpose: **portability** — capture the exact rendered prompt so it can be pasted into a competing LLM for comparative analysis, or as a free-LLM fallback when out of tokens. The **debug-log/footer is dev-time scaffolding that will be REMOVED** once the tool matures.

**The correctness oracle:** provenance and debug-log must match the sent prompt **1-for-1**. Verified structurally (2026-07-20): in `synthesize_objectives`/`synthesize_steps`/`generate_coverage_gaps`, the SAME rendered string flows to (a) `_call_llm_with_meta` → LLM, (b) `_call_llm_raw` meta["prompt"] (llm.py:333) → debug-log, and (c) the provenance dict — no re-render between. So debug-log `prompt` ≡ provenance `*_prompt` ≡ what the LLM received, by construction. If they ever diverge, a re-render/mutation bug was introduced.

**Rollout (approved "everything now", 2026-07-20):** extend session provenance (NOT reuse debug-log, since provenance must survive after debug-log is gone) with `{prompt, response}` for every LLM function currently missing it:
- Generator (llm.py): `suggest_relevant_atp`/`testlink`/`zephyr`, `analyze_atp_coverage` — none store prompt/response today.
- PyTest (routers/pytest_create.py): `extract_sequence` (has response[:20000], needs prompt), `suggest_scripts`, `assess_fit`, `generate_script`, `fix_script` — provider/model only today.
- Frontend: add the `LLM Provenance` `<details>` block (like generator.js:170-189) to each panel, **with a Copy-prompt (and Copy-response) button** — Terrence chose "Prompt + a copy button". Wire via registerActions.
- Dev-time assertion: provenance.prompt == debug-log prompt for every call (guards the 1-for-1 guarantee while debug-log still exists).

Only objectives/steps/gaps had full prompt+response provenance before this. See [[user-prefers-manual-ui-testing]].

**IMPLEMENTED 2026-07-20 (uncommitted).** Terrence's final design (better than snapshot-storing): a **`dry_run` flag** — the Refresh button re-invokes the SAME endpoint with `dry_run:true`, which renders the prompt via the real context path and returns it WITHOUT sending (no tokens, not recorded to debug-log). 1-for-1 is guaranteed by construction (same code path, flag flipped) — **verified byte-identical** (dry_run prompt == direct render) and **verified no-send** (HTTP test: debug-log line count unchanged). Wiring: `dry_run` param on `_call_llm_with_meta` (llm.py, short-circuits before send) + `run_prompt` + 7 Generator fns (suggest_* return `{dry_run,prompt}` dict when flagged) + `SynthesisRequest.dry_run` field; all 6 PyTest endpoints (`_dry_run(request)`/body + `_provenance_preview`) + wizard suggest/synthesize endpoints (`_preview_from`). Frontend: shared `static/js/provenance.js` (registerProvenance/renderProvenanceBlock/seedProvenanceFromStep + provRefresh/provCopyPrompt/provCopyResponse actions), CSS in styles.css, mounted into all 9 panels (objectives/steps in generator.js; 3 suggest in db-search.js; 6 PyTest in pytest.js via mountPtProvenance). main.js imports provenance.js; cache-bust v=5→v=6. The normal (non-dry) PyTest paths now also store `prompt`+`response` in step provenance (previously provider/model only).
