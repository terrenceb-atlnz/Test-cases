# Part 2A — First real end-to-end walkthrough (T33234)

**Case:** `AWPTCM-T33234` — *Port - Auto MDI/MDI-X* (Zephyr `is_target`, group "Port").
**Date:** 2026-07-21.
**Backend:** org vLLM (`openai` / `auth_method=local_llm` / `model=vllm-fast`), driven
headless via the workspace LLM default. This is the pipeline's **maiden real run
against the permanent `ck.db`** (830 scripts, 83,816 embeddings).

Goal of Part 2A (per PLAN §2, Phase 1): walk all 8 PyTest Creator steps and give
each a **procedural** verdict — does it work, is it too broken up, is anything
mergeable/cuttable/fixable. Content-quality judging (LLM effectiveness, model
matrix) is Part 2B/3; noted here only where it surfaced.

---

## Headline result

The pipeline **works end-to-end through step 6** against the live DB. Steps 1–6
each returned correct, well-formed output; the generated script **compiles and
passes the Part 1 conformance lint clean**. Step 7 (run) correctly gates pending
a testbox profile (none configured yet). Live on-device execution (7–8) is
blocked only on the `tb470` profile + `.setup` prerequisite — that is Part 3b.

Getting there required fixing **three real bugs** in the LLM call/parse path,
all of which would have blocked *any* vLLM-backed run (not T33234-specific).

---

## Bugs found & fixed (all in `CK_server/llm.py`)

The org vLLM models are **reasoning models**: they spend completion tokens on
hidden chain-of-thought (returned in `message.reasoning_content`) *before*
emitting the answer in `message.content`. Every bug below traces to that.

### Bug 1 — `max_tokens=2000` too small for a reasoning model
The legacy 2000-token cap (fine for old non-reasoning models) is exhausted
*inside the reasoning phase* on any non-trivial prompt. The model stops with
`finish_reason="length"` and `content` stays **null**.
- **Symptom:** `extract_sequence` → `502 'NoneType' object is not subscriptable`.
- **Fix:** `max_out = 16000 if auth_method == "local_llm" else 2000`.

### Bug 2 — parser assumed `content` is a non-null string
`content = data["choices"][0]["message"]["content"]` crashed on `content=None`,
and even when populated could be **truncated mid-JSON** at the cap — which then
silently degraded downstream (looked like "the LLM found nothing") instead of
erroring.
- **Symptom (empty):** cryptic `NoneType` error. **Symptom (truncated):**
  `suggest_scripts` returned all 40 candidates as `coverage="unknown"` (mechanical
  fallback) because the truncated match-JSON failed to parse.
- **Fix:** guard `content`; on `finish_reason=="length"` raise a *clear* error
  (empty **or** truncated); fall back to `reasoning_content` for a
  reasoning-only-but-non-empty response.

### Bug 3 — `extract_json_block` returned a nested array instead of the outer object
The extractor tried `[` **before** `{` unconditionally. A top-level object like
`{"decision": ..., "per_step": [...]}` contains a nested array, so it balanced
and returned the inner `per_step` list — never the object.
- **Symptom:** `assess_fit` → `502 "LLM fit decision unparseable"` even though the
  LLM returned perfectly valid JSON.
- **Fix:** try whichever bracket type appears **first** in the string
  (first-occurrence order respects the true outermost structure). Verified against
  5 shapes: nested object, top-level array, prose+object, fenced object,
  array-genuinely-first.

> These three are the reason a headless vLLM run had never actually completed
> before. The health-ping (tiny prompt) always passed, masking them.

### Follow-on 4 — adopt the documented system+user message shape
`resources.md` documents the org vLLM usage as a **system + user** message split;
the code was sending **user-only**. Adopted it: `run_prompt` now sends a default
JSON-steering system message (`_JSON_SYSTEM_PROMPT`), threaded through
`_call_llm_with_meta` → `_call_llm_raw` (OpenAI path uses a `system` role;
Anthropic path uses the top-level `system` field). Overridable per call; the
health-ping still sends none.
- **Measured effect on `extract_sequence` (same prompt):** completion tokens
  7,959 → **5,141 (−35%)**, latency 45.5s → **28.9s (−37%)**, and — crucially —
  the `notes` field went from **empty to populated** (the model now honors the
  prompt's "skip physical steps & name them in notes" rule instead of burying it
  under its own reasoning). On a trivial JSON ask the reduction was ~22×.

### Follow-on 5 — guarantee no `# >>> FILL` scaffolding survives
Generation is non-deterministic: one run stripped the template's `# >>> FILL …`
guidance comments, another left all 44 in place (real code was written beside
them, but the comments remained) → lint correctly failed. Fixed two ways:
- **Server-side (deterministic):** `_strip_fill_markers` in the router removes
  every pure-comment `>>> FILL/replace/remove` line (and its two-line
  continuations) from generated code before lint/save. Verified on the failing
  run: 44 markers → 0, all real filled code (observations + verify conditions)
  preserved, result compiles.
- **Prompt (root cause):** `pt_generate_script.jinja` rule 6 is now a standalone
  imperative — "DELETE every `>>> FILL … <<<` comment once filled; the final
  script must contain ZERO `>>>` markers."
- **Re-verified end-to-end:** regenerated T33234 → 0 residual markers, lint clean,
  compiles.

---

## Per-step verdicts

| # | Endpoint | Verdict | Notes |
|---|----------|---------|-------|
| 1 | `load_case` | **KEEP** | Pulls objective + 9 Zephyr steps from DB. Step-1 "step" is a traceability pointer to the ART auto-test, not a real verify step — extract_sequence must (and does) drop it. |
| 2 | `extract_sequence` | **KEEP** | 8 Zephyr steps → 24 automatable `{action, verify, zephyr_step_idx}` entries. Well-formed. **Content flag:** several emitted steps are physical (cable swap, partner config, pluggable insert/remove) and the prompt's "skip & name in notes" rule was **not** honored — `notes` came back empty. → Part 2B prompt-tuning. |
| 3 | `suggest_scripts` | **KEEP** | Keyword top-40 is **excellent** — `legacy/5000_mdi_mdix/*` (the real MDI/MDI-X suite) scored 81–117, well clear of noise. LLM coverage stage then produced 18 real `partial` verdicts, correctly ranking the mdi_mdix suite over 5703_Speed_Duplex_Polarity. |
| 4 | `assess_fit` | **KEEP** | Decision `extend`, base = SFP straight-through exemplar, 24 per-step gap entries. Rationale cites real script content → confirms `_read_source` reads from DB correctly. **Content flag:** verdict flip-flopped `new`↔`extend` across runs (reasoning-model non-determinism). → Part 2B. |
| 5 | `gather_fragments` | **KEEP** | 5 real fragments pulled from DB (651–3231 chars, 0 dropped), each with `maps_to` step mapping + rationale. `_read_source` + loc-lookup + helper-regex paths all exercised. |
| 6 | `generate_script` | **KEEP** | 34.8KB file, **compiles + lint-clean**. Skeleton conformance perfect: TestSet(init/configure/tear_down, "NO pass/fail" comments intact) + one TestCase_N per step, each with the 3-call logging contract. Bodies contain **real CLI + real verify logic**, not empty stubs. **Content flags** (→ Part 3): (a) no `#legacy/#ART/#AI` provenance tags — the §1.5 mechanism is planned-not-built; (b) `— not yet implemented` suffix leaks into `failed()` strings (prompt artifact); (c) `configure`/`tear_down` are identical (tear_down should restore, not re-apply); (d) CLI syntax (`polarity auto`) likely not real AlliedWare Plus — Part 3b on-device will catch. |
| 7 | `run` | **KEEP (gating verified)** | Correctly returns `400 "Unknown or missing testbox profile"` — fails safe, no crash. Live run blocked on `tb470` profile + `.setup` (Part 3b prereq). |
| 8 | `validate` | **DEFERRED** | Depends on a completed run. → Part 3b. |

### "Too broken up / mergeable?" — the Phase-1 procedural question
No step is redundant or should be merged. The confirm-gate between each step
(`_require_confirmed` + `_invalidate_from`) is coherent: editing/confirming step N
un-confirms every later step, so the human review points are meaningful. The
8-step decomposition is sound as-is.

The one *content*-level "too broken up" is inside step 2's output, not the step
graph: extract_sequence expanded 8 → 24 and split some actions that a single
TestCase could combine — but that's an LLM prompt-tuning matter for Part 2B, not
a pipeline restructure.

---

## Implementation debt confirmed empirically

- **Inline source-provenance tagging (§1.5)** is *not yet implemented* — the
  generated script has zero `#legacy/#ART/#SVT/#AI` tags. Needs: prompt
  instruction + server-side re-stamp + lint check.
- **`— not yet implemented`** language leaks from the generation prompt into
  `failed()` verdict strings. Should be scrubbed or the prompt reworded.

## Prerequisites still open for Part 3b

> ✅ **RESOLVED since this was written (2026-07-21).** Both of the first two were closed within
> days: `configs/tb470.setup` exists (from 2026-07-27) and a tb470 profile is configured. The
> list below is the state on the day of this walkthrough, kept as part of its record. For the
> bench's current state read `~/claude/IE520-testing/bench-setup/bench-state.md`.

- `configs/tb470.setup` (topology; device on u5) — does not exist.
- A PyTest Creator **profile** pointing at tb470 (host, sudo, setup map) — none
  configured (`/profiles` returns `{}`).
- Confirm whether the direct single-script run path needs `config.cfg`.

---

## Artifacts
Captured under the session scratchpad `part2a/`: `01_load_case.json` …
`06_generate_script.json`, `06_generated_test.py` (the generated script),
and `llm_*.json` (raw LLM records used to diagnose the three bugs).
