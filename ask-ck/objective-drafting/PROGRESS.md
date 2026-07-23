# PROGRESS.md — Ask CK Workbench (Server-Backed)

**Purpose**: This file exists so future sessions can quickly understand exactly where we are, what has been built, what the priorities are, and how to continue seamlessly.

**Last Updated**: 2026-07-23 (by Claude)

## Latest session (2026-07-23) — PyTest Creator UX revision + adversarial-review worklist (physical steps, provenance fix)

**Focus: a large hands-on revision of the PyTest Creator while Terrence tested it, then a step-by-step pass through the T33233 adversarial-review worklist. All committed + pushed this session.**

**UX / flow changes (steps 1–4):**
- **1. Cases** split into **Open/Partial** + **Complete** dropdowns by PyTest work state; partials auto-sorted to top (`pt_cases` endpoint, `cases.js`).
- **2. Sequence** shows current steps + the LLM's extracted execution order with **drag-and-drop reorder** and a static `from`/source column; the extractor now also classifies each step's **kind**.
- **3. Script Search** rebuilt to a **per-step page-within-a-page carousel** (one step/screen, Prev/Next + green-✓/yellow-✗ step-pill nav); per-step candidate→chosen tables; selections stored per step (`{stepN:[ids]}`) and flattened downstream. Whole-sequence LLM field removed.
- **4. Fit Decision REMOVED** (moot under the fixed skeleton); visible steps 5–8 renumbered 4–7, internal `stepN` keys unchanged.
- **4. Fragments** rebuilt per-step, **no cap**, selected/not-selected split, chosen/redundant accounting (redundant nested faint-red under the chosen it duplicates), and a collapsible **assembled-artefact preview**.
- **Generator load perf:** `load_case` was ~64s because it fired a blocking `analyze_atp_coverage` LLM call; removed it → ~2.4s (data-display only).
- **Case hiding:** ART Limits Test + 4 ART Testsuites cases + Bootloader/GRUB Bootloader categories hidden from the Generator case lists (display-only, DB untouched).

**Adversarial-review worklist (T33233) — went step-by-step:**
- **#1 device-name reconciliation — DONE.** Bind the device names the reused fragments actually reference (`_detect_fragment_devices`); reconciliation note surfaced in preview + Generate prompt.
- **#2 physical-step handling — DONE.** 4-kind taxonomy (**setup/verify/physical/manual**) in `pt_extract_sequence.jinja`; single `_step_kind()` classifier; `_split_sequence` made non-mutating. Template branches: physical → operator-prompt + poll-`show interface status` for the state change (**SVT 3009 `waitForReplugEvent`**), manual → `yesNo()`, setup → `configure()`, verify → normal. **Physical plug/unplug steps are in scope, not skipped.**
- **#3 fragment quality — PARTIAL.** Cross-step dedupe already handled; **added `maps_to` phantom-step validation** (`_clean_maps`). Line-vs-class extraction + per-step cap deferred → `NEXT_SESSION_DECISIONS.md`.
- **#4 provenance divergence — FIXED + unit-verified.** `_restamp_provenance` now takes the sequence and remaps original-step → `TestCase_<n>` class number before stamping; previously a dropped setup step shifted the numbering and the wrong fragment's tag landed on the wrong TestCase. Both call sites (generate + fix) pass the sequence.
- **#5 guaranteed-fail default — no change needed;** lint already rejects `if False:`/`output=''`/`>>> FILL` in a saved script.
- **#7 zero-reuse marker — ADDED.** Verify steps with no fragment carry a positive `# ===== NO REUSE … =====` in the preview (physical/manual excluded).

**Open decisions for next session:** `NEXT_SESSION_DECISIONS.md` (repo root) — D1 fragment granularity, D2 per-step cap, D3 Py2 contamination.

**Verification:** provenance remap unit test; all 4 step kinds render + `py_compile`; preview gap-marker test (1 NO-REUSE on the uncovered verify, none on physical); routers import clean; all jinja templates parse; guards green; `/health` 200.

## Latest session (2026-07-22d) — Claude-agent token reporting + Haiku/Sonnet/Opus selector + Traceability-gaps decoupling

**Focus: (1) decoupled the Traceability-gaps LLM call from Objective synthesis (committed `8503cea`); (2) made the per-user Claude agent report token usage + cost and added a three-way model selector. Docs synced + committed this session.**

- **Traceability gaps decoupled from Objective synthesis (`8503cea`).** Step 4 (`synthesize_objectives`, `llm.py`) used to make a *second* LLM call (`generate_coverage_gaps`) just to inject an "Automation gaps (Traceability context)" block into `generate_objectives.jinja`. That block didn't meaningfully shape the declarative objective bullets, and gaps are already generated independently at **export time** when `traceability.md` is rendered (`/api/wizard/export`, `if not gaps: generate_coverage_gaps`). Removed the gaps block from the template and the internal gaps call — **Step 4 is now a single self-contained objective call**, and dry-run preview == real send byte-for-byte. `traceability.md` and its gaps are unchanged (still built at export). Existing cases already carry their gaps on disk → unaffected. Prompted by a two-model comparison where the gaps call added noise + tokens with no benefit.
- **Why "— tok" was showing (root cause, from the debug-log).** The user compared two Objective runs; one showed `937 in / 2,971 out`, the other "— tok". The debug-log (`CK_server/debug-log/`, which was **not** empty — an earlier diagnosis wrongly said so; the check used a flaky relative path + wrong template filter) showed the first was **vLLM** (`local_llm`) and the second was **Claude via the agent bridge** (`claude_agent`). The agent bridge simply wasn't forwarding token usage, so `normalize_usage` returned `None` and the badge honestly showed "— tok". The content rendered fine in both — observability gap only, not a truncated answer.
- **Claude-agent token usage + cost (this commit).** Four-file passthrough, all in-repo: `ask-ck/agent/ck_agent.py` now lifts `usage` + `total_cost_usd` from the `claude -p --output-format json` envelope and returns them from `/run`; `static/js/agent.js` (`ckBrokerLoop`) forwards them in the `/api/agent/result` POST; `routers/agent_bridge.py` passes `total_cost_usd` through; `agent_jobs.py` `deliver()` stores both on the job result in the exact shape `llm_debug.normalize_usage` expects (usage sub-dict + top-level `total_cost_usd`). Server side + `normalize_usage` were already ready — server-side `claude_code` reports tokens for the same reason (it keeps the envelope). Verified end-to-end with a simulated deliver (cache tokens fold into input, cost surfaces, no-usage still → honest `None`). **The ck-agent runs on the user's machine → they must restart it (`cd ask-ck/agent && ./run-agent.sh`) to enable this.**
- **Haiku / Sonnet / Opus model selector (this commit).** Mirrors the vLLM Fast/Thinking toggle: new `claudeAgentRow` radio group in `index.html` (shown only when `claude_agent` is selected, default **Sonnet**); `static/js/llm.js` wires Apply (`setLLMConfig`), a live-persist toggle (`applyClaudeMode`), restore-on-reload, the status line (`Claude — my local machine · <Model>`), and `main.js` binds the radios. The model flows `llm_config.model` → `job.model` → ck-agent → `claude --model <name>` (CLI aliases `haiku`/`sonnet`/`opus`). A model typed in the free-text field still overrides.
- **Guards green** (`guard_db_only`, `guard_framework_readonly`); `/health` 200.

## Latest session (2026-07-22c) — Push-to-Zephyr button + all 43 refined cases pushed to Zephyr v2.0

**Focus: built a "Push to Zephyr" button in the Generator's export step (shells out to `tool/upload_refined.py`), added title-cleanup + version-2 handling, then pushed all 43 Complete cases to the live Zephyr Scale (Server/DC) instance and audited them for consistency. Uncommitted at write time; committing + pushing to main this session.**

- **`tool/upload_refined.py` — new Zephyr-write capabilities:**
  - `--fix-title`: strips a leading `(N)`/`(…)` group from the case **Name** (e.g. `(4) Auto MDI/MDI-X` → `Auto MDI/MDI-X`); name-only PUT.
  - `--new-version`: **idempotent toward v2.0** — bumps 1.0→2.0 via the internal `POST /rest/tests/1.0/testcase/{id}/newversion` (reverse-engineered from a devtools HAR of the UI "New Version" → Accept), but does NOTHING if already at v2.0+ (never produces 3.0). New helpers `create_new_version` + `get_case_version_info`. Order per Terrence's spec: **fix-title → new-version → payload PUT** (atm PUT-by-key lands on the new latest version).
  - **Attachment de-dup (replace semantics):** `attach_file` now deletes any existing same-named attachment before uploading (the API has no update; repeated pushes were accumulating duplicate `traceability.md`). New `get_attachments` + `delete_attachment` (DELETE → 204).
  - **Looser link parser:** `parse_atpylib_links` now reads **un-backticked** ART suite IDs from the ATPyLib Cases section (most files author them in prose), filters year tokens (19xx/20xx), de-dupes per-suite, and skips a reviewed non-suite denylist (`1024`).
  - **Repathed discovery** to `ask-ck/objective-drafting/refined-cases/` (was still on the pre-2026-07-13 root path → found 0 cases). Fixed the misleading `Summary: 0 ok` counter (success was only counted on the web-links branch).
- **Server + UI:** new `POST /api/wizard/push_to_zephyr/{key}?dry_run=…` (`routers/wizard.py`) shells out to the CLI — the **server never handles the JIRA token** (the CLI loads it from `secrets.md`). "Preview Push (dry-run)" + "Push to Zephyr" buttons in the Generator step-6 export actions (`static/js/generator.js` + `styles.css`).
- **`_backfill_from_refined` (load fix, `routers/wizard.py`):** loading a previously-Complete case showed empty objective/steps because its runtime session in `ck.db` had empty step4/step5 (cases refined before the session captured them). Load now rehydrates step4/step5 from the canonical on-disk `zephyr_payload.json` (guard_db_only allows that read) and self-heals the DB session.
- **Push does NOT export-first (important):** an early version re-exported the bundle before pushing, which **degraded** a backfilled case's `traceability.md` (the incomplete session lacks step1–3 selections). Removed — Push now operates on the canonical on-disk bundle; click **Export Repeatable Bundle** first if you edited. One case (T33241) was hit + fully repaired (restored file, re-attached, `2024` link re-added).
- **Live outcome — all 43 Complete cases pushed + independently verified:** 43/43 at **v2.0**, 43/43 titles **clean** (32 had a `(N)` prefix stripped), 43/43 **exactly one** `traceability.md` (7 had duplicates, cleaned), **40** have ART web-links (3 have none — no ART IDs in their traceability.md, by design), step 0 is 39 identical + 4 intentionally richer (kept). Zephyr instance is Jira Server v9.4.3 / Adaptavist ATM; internal `tests/1.0` API accepts the Bearer PAT.
- **Guards green** (`guard_db_only`, `guard_framework_readonly`).

## Latest session (2026-07-22b) — vLLM streaming transport + stale-`llm_config` re-sync

**Focus: (1) built the streaming transport that Part 2B §7.7 named as the real fix for `vllm-thinking` read-timing-out on `generate_script`; (2) fixed the §7.3 stale-`llm_config` root cause in both routers. Committed at session close; push to main pending (this environment lacks GitHub SSH auth — Terrence to push).** Living doc: `ask-ck/pytest-create/PLAN-pytest-testing.md` §8 (streaming) + §9 (re-sync).

- **Streaming the vLLM path (`llm.py`).** The OpenAI-compatible branch of `_call_llm_raw` now sends `stream: true` + `stream_options: {include_usage: true}` and consumes the SSE body, accumulating `content`/`reasoning_content` deltas + final `finish_reason`/usage into the **same triplet** the non-streamed path produced — so every guard (length/null/truncation) and the token-usage badges are unchanged. **Why structural, not a bigger ceiling:** with a streamed body the HTTP `read` timeout is the gap *between* chunks, not the whole-response wall clock; vLLM streams `reasoning_content` throughout the thinking phase, so a reasoning pass of any length completes as long as chunks keep flowing. The prior static 600s floor could still be exceeded (§7.7: it was); this removes the ceiling. Anthropic native path left non-streaming (no such failure).
- **Verified live (real org vLLM):** `vllm-fast` trivial ask 1.0s + correct badges; `vllm-thinking` `generate_script`-scale prompt completed at 395.6s (`finish=stop`, was failing at 600s in Part 2B); **ceiling-gone proof** — a `vllm-thinking` call with a deliberately short **30s** read timeout ran **21+ min with no timeout** (killed for time, not failure), proving the read budget is now inter-chunk.
- **Token-processing-over-time capture (in progress).** Identical prompt through both models, chunk-instrumented. **`vllm-fast` baseline:** 48.7s, **first answer token at 21.3s** (21s of reasoning-only first), 8,733 completion tokens, 8,731 chunks. **Key finding: `vllm-fast` is *also* a reasoning model** — both reason and both stream `reasoning_content`; the difference is reasoning-phase *duration*, not reasoning-vs-not. The vLLM SSE structure is identical for both. **`vllm-thinking` on the same prompt: 2,149s (35.8 min, 44× slower), `finish=length`, ZERO answer emitted** — it spent the entire 32k-token budget on reasoning (29,137 reasoning tokens) and never transitioned to the answer. **Streaming fixed the transport (the 35.8-min call completed with no read-timeout — the 600s ceiling would have aborted it) but NOT the model's fitness:** `vllm-thinking` is unfit for `generate_script`-scale generation. Strengthens the vllm-fast-default recommendation. Infographic (token curves over time, both models): `ask-ck/pytest-create/comparison/vllm_tokens.html` (+ published artifact).
- **Stale-`llm_config` re-sync (`routers/wizard.py` + `routers/pytest_create.py`, §9).** Fixed the §7.3 root cause: both workspace-apply functions gated only on `_llm_is_active`, which reports headless CLI modes (`claude_agent`/`claude_code`/`grok_cli`) active unconditionally — so a session whose *stale* config was a headless mode could never re-sync to the workspace default and kept silently hitting the wrong backend. Now the **active workspace default is authoritative**: re-sync whenever the session config is inactive OR diverges from it (new `_same_backend` helper compares auth_method/provider/model). `_llm_is_active` left untouched (its status/`has_key` uses are correct as-is). Safe because `set_llm_config` is the only writer of a case's config and always writes it === the workspace default — no legitimate per-case divergence exists. Unit-verified 8/8 (no vLLM) + concurrency-reviewed. **Surfaced pre-existing debt (§9.4):** dual-instance sessions (in-memory cache vs fresh DB load) can drop unrelated state under concurrency — logged, not this fix's fault, not a blocker.
- **Still deferred:** Part 3a/3b (the `wizard.py` twin bug is now fixed).

## Latest session (2026-07-22) — vLLM read-timeout fix + §1.5 provenance tags + Part 2B model matrix

**Focus: continued the plan after the standing "fix next session" vLLM read-timeout note. All work uncommitted at session end — Terrence commits himself.** Living doc: `ask-ck/pytest-create/PLAN-pytest-testing.md` §7 (full bug-by-bug log with rationale).

- **vLLM read-timeout fixed (`llm.py`).** The two HTTP calls hardcoded `timeout=120`, ignoring every caller's requested timeout entirely — the actual cause of the `suggest_zephyr`/`synthesize_objectives` failures logged in the prior handoff. Now a `(connect=10, read=<caller's timeout>)` split, with the `local_llm` read floor raised to 600s (only when the caller asked for ≥120s, so the health-ping's 30s still fails fast). Verified against real requests.
- **§1.5 inline source-provenance tags — built** (was tracked debt from Part 2A). `# ART/SVT/legacy <suite/file> lines a-b` tags derived mechanically from fragment metadata, or `# AI <model> <date>` for gap-fill; stamped authoritatively server-side after generation (never trusting LLM self-report). Verified on a real live T33234 regenerate — found and fixed a real duplicate-tag bug along the way (model echoed the prompt's instruction text as a second comment line; fixed by stripping the whole leading comment run, not just the first line). Also scrubbed a `— not yet implemented` string leaking into the skeleton's placeholder `failed()` text.
- **`max_tokens` was never overridable — found live.** Verifying §1.5 hit a real `finish_reason=length` on `generate_script` at the 16000-token default (a full generated script is the biggest-output step). Threaded an optional `max_tokens` param end-to-end (`run_prompt`→`_call_llm_with_meta`→`_call_llm_raw`); `generate_script`/`fix_script` now request 32000.
- **Two more real bugs found and fixed while setting up Part 2B** (both blocked the pipeline, not cosmetic): (1) a session's stale `llm_config` (leftover `claude_agent`) never re-syncs to the workspace default because `_llm_is_active()` treats headless-CLI auth methods as unconditionally active — same latent gap exists in `wizard.py`, left unfixed there (bigger blast radius); (2) `confirm_step` rejected a legitimate `fragments: []`/`matches: []` answer (empty list is a valid "no reuse needed" result, e.g. a `decision: new` case) because Python falsy-checks an empty list the same as "never ran" — blocked the ENTIRE rest of the pipeline for any case with a genuinely empty Fit Decision. Both fixed narrowly, verified live.
- **Part 2B built and run for real** (`tool/pt_model_matrix.py`, new): 75 real LLM calls (3 target cases × 5 LLM-bearing steps × vLLM-fast/thinking + Claude Haiku/Sonnet/Opus). Grok CLI is logged in but genuinely quota-exhausted (real 403) — logged as an omission, not silently dropped. Results committed at `ask-ck/pytest-create/comparison/Port (7)/<CaseKey>/<step>.json`. **Headline finding: `vllm-fast` is the clear reliability+latency winner (0/15 errors); `vllm-thinking` failed 3/15 — including `generate_script` timing out even at the raised 600s floor** — confirms the plan's own hypothesis that streaming, not just a bigger static timeout, is the real fix needed for the thinking model on large-output steps. Keyword-vs-LLM step-3 search: one case showed full agreement with mechanical rank, the other showed the LLM genuinely promoting a better-matching script the keyword scorer under-ranked (misleading vocabulary overlap between two suite families) — both real, useful signal.
- **Verified LLM access live before assuming blocks:** vLLM key present + working, Claude Haiku/Sonnet/Opus all reachable via `claude -p --model <alias>`, Grok logged in but quota-exhausted, tb470 reachable (SSH/sudo/framework) but `configs/tb470.setup` genuinely absent (Terrence-side physical-topology prerequisite — the one real remaining block, per §5b).
- **Still pending:** Part 3a (offline judging, criteria 1-4, two LLM judges) and Part 3b (tb470 execution, criteria 5-6) — gated only on `configs/tb470.setup` + a stored testbox profile.

## Latest session (2026-07-21b) — PyTest Creator Part 2A: first real vLLM walkthrough + vLLM-path hardening

**Focus: Part 2A — first real end-to-end walkthrough of the 8-step PyTest Creator flow on T33234 (`AWPTCM-T33234`, Port Auto MDI/MDI-X), driven headless via the org vLLM against the permanent `ck.db`. All committed + pushed to main (`e6c0d64`, `1ccf1a7`).** Full record: `ask-ck/pytest-create/PART2A-WALKTHROUGH.md`.

- **Pipeline works end-to-end steps 1–6.** load_case → extract_sequence → suggest_scripts → assess_fit → gather_fragments → generate_script all return correct output against the live DB; the generated ~24–35 KB script **compiles + passes conformance lint**. Step 7 (run) correctly gates with a clean `400` when no testbox profile exists (fails safe). Every step verdict: **KEEP**; the 8-step decomposition + confirm-gating is sound, nothing mergeable. Live execution (7–8) is blocked only on the `tb470` profile + `.setup` prereq (Part 3b).
- **Three real vLLM-path bugs found + fixed (`e6c0d64`, all in `llm.py`).** All rooted in the org models being **reasoning models** (chain-of-thought in `message.reasoning_content` before the answer in `message.content`): (1) `max_tokens=2000` exhausted mid-reasoning → `content` null → raised to 16000 for `local_llm`; (2) parser assumed non-null string — crashed on `None` and silently degraded on cap-truncated JSON → now guards + raises a clear `finish_reason=length` error + falls back to `reasoning_content`; (3) `extract_json_block` tried `[` before `{` so a top-level object with a nested array returned the inner array → now picks whichever bracket appears first. The health-ping's tiny prompt had masked all three — no headless vLLM run had ever completed before.
- **Adopted the documented vLLM system+user shape + FILL-marker guarantee (`1ccf1a7`).** `resources.md` documents system+user; the code sent user-only. `run_prompt` now prepends a default JSON-only steer (`_JSON_SYSTEM_PROMPT`), threaded through `_call_llm_with_meta`→`_call_llm_raw` (OpenAI: system role; Anthropic: top-level `system` field). Measured on `extract_sequence`: completion tokens 7959→5141 (−35%), latency 45.5s→28.9s (−37%), and the `notes` field went **empty→populated** (model now honors the skip-and-note rule). Separately, generation non-determinism left `# >>> FILL` scaffolding comments in one run (lint caught it) → fixed with a deterministic server-side `_strip_fill_markers` (44→0, filled code preserved) **and** a strengthened `pt_generate_script.jinja` rule.
- **Content findings for Part 2B/3 (not pipeline breaks):** extract_sequence initially over-expanded + ignored the skip-and-note rule (fixed by the system message); assess_fit verdict flip-flops `new`↔`extend` (reasoning-model non-determinism); **inline provenance tags (§1.5) confirmed NOT emitted** by the model (prompted, not enforced); a `— not yet implemented` string leaks into `failed()` reasons; generated CLI syntax (e.g. `polarity auto`) needs on-device validation.
- **Still pending (next):** Part 2B (keyword-vs-LLM + model matrix: vLLM fast/thinking, Claude Haiku/Sonnet/Opus, logged per-case), Part 3a/3b (judging + tb470 execution). Guards green; `/health` ok (830 scripts, 83816 embeddings).

## Latest session (2026-07-21) — PyTest Creator: DB-only source fix, framework read-only guard, standardized template (Part 1)

**Focus: planning + building the PyTest Creator standardization/testing effort. All committed + pushed to main.** Living plan: `ask-ck/pytest-create/PLAN-pytest-testing.md`.

- **Fixed a live DB-only violation (`c29f53e`).** `routers/pytest_create.py::_read_source` was reading script source off the retired `testsuites_art/` mount (`Path(rec["path"]).read_text()`), which no longer exists on disk. Now reads from `ck.db` (`rec["source_text"]` / `db.get_script_source`); `rec["path"]` is provenance-only. A 4-agent full audit of all 17 `CK_server/*.py` confirmed this was the ONLY live violation; cleaned up dead scaffolding (removed `DATA_DIR`/`PT_DATA_DIR` anchors, vestigial `SESSIONS_DIR`/`_session_path`/`GLOBAL_LLM_PATH`, stale comments). **Extended `tool/guard_db_only.py`** from 1 to 4 detected shapes (retired corpus JSON; script source off disk; retired mount roots; retired corpus-dir anchors).
- **Testbox framework dir is READ-ONLY (`152e86b`).** `/home/st-art/framework` (profile `framework_path`) must never be written/edited/mutated; copy locally to edit. Enforced in `pt_exec.py` (`_assert_write_allowed` on SFTP targets, `_assert_command_allowed` on remote commands, source-vs-dest aware) + new runnable `tool/guard_framework_readonly.py` (15 cases).
- **Part 0 — logging contract (`ca90ff8`).** `ask-ck/pytest-create/LOGGING-CONTRACT.md`: the required per-step log format, verified against the framework source on tb470 + a real 101-case log + the tool's `parse_framework_log` (all three agree). Gotchas: empty `passed()/failed()` emits no marker; results are 4-valued (PASS/FAIL/ERROR/UNSUPPORTED).
- **Part 1 — standardized script template (latest commit).** Generation now **fills a fixed skeleton** (`templates/pt_script_template.py.jinja`) instead of composing freely: data-driven `init` (switches/stacks/portlink detected from sequence+fragments), suite `configure`/`tear_down` (no pass/fail), one `TestCase_<n>` per verification step with the logging contract + per-case `tear_down`, `__main__` footer. `pt_generate_script.jinja` rewritten to fill-not-compose; `_lint_generated` extended for template/logging-contract conformance. Static exemplar chosen: `art/1363_ipv6/test-1363.1002.py` (replaces the dynamic 6011). Inline source-provenance tags planned (§1.5: `# ART/SVT/legacy <id> <lines>` / `# AI <model> <date>`). Docs: `TEMPLATE-SPEC.md`.
- **ART execution chain documented** (`ask-ck/test-composer/ART-EXECUTION-CHAIN.md`) — the full ATPyLib run chain in dependency order (`<hostname>.cfg` → `.setup` → build load → `runAll` → `runTestSuite` → `test-*.py` → log → parse), the two entry points (suite runner vs our direct single-script path), and what Test Composer should reuse vs emulate. Finding: our direct `-s <setup>` path likely does NOT need `config.cfg` (a suite-runner concern) — to verify on the first real tb470 run.
- **Testbox reachable this seat:** `ssh tb470` (device on u5, passwordless sudo, framework present). Neither `configs/tb470.setup` nor `tb470.cfg` exists yet — prerequisites before Part 3b execution.
- **Still pending (next):** Part 2A (first real end-to-end walkthrough on T33234), Part 2B (model-comparison harness), Part 3a/3b (judging + tb470 execution). Guards green; `/health` ok.

## Latest session (2026-07-20c) — ck.db is the PERMANENT single source of truth

**`ck.db` committed to the repo via Git LFS; courier/source files deleted; rebuild removed. All pushed to main.**

- **DB is now THE data, not a cache.** `ck.db` (412 MB) + its ~84k vectors + the bundled offline embedding model are committed via Git LFS (`.gitignore` un-ignores them; `/var/` rule anchored so it no longer shadows `ask-ck/var/`). A fresh clone gets a populated, semantically-searchable DB with **zero build step**.
- **Couriers/intermediates DELETED** (148 files): `zephyr_cases.jsonl`, `index.json`, `slim_index.json`, `zephyr_master.json`, `testlink_awp.json`, `test_id_description.json`+`.csv`, `candidates.json`, `decisions/*` (14), ~120 `suite_*_enriched.json` + `all_test_suites.json`, `scripts_index.json`, `scripts_slim_index.json`, `scripts_sources.jsonl`, `scripts_index_enrich.jsonl`, `framework_surface.json`, `scripts_index.meta.json`. **Kept:** the raw Zephyr XML export (immutable provenance root).
- **No rebuild / no APIs / no re-fetch.** `tool/build_db.py` is provenance-only and refuses to run (would delete the committed DB). Admin panel Rebuild-DB + Rebuild-embeddings removed (`routers/admin.py`, `admin.js`, `index.html`); reset-session + restart kept. `setup.sh` verifies the shipped DB instead of building it.
- **Verified after teardown:** server boots + all searches (keyword/semantic/hybrid/code) work with couriers GONE; `/health` ok, vectors on, 83816 embeddings; guard green; `build_db --fresh` correctly refuses. Order was safe: committed+pushed+fsck-verified the DB *before* any deletion.
- Docs synced: README, SERVER-README, this file, PLAN-db-only-search (final-state header). Memory: `db-is-permanent-source`.

## Latest session (2026-07-20b) — Strict DB-only Phase 1 + script-code + semantic embeddings

**Read next for design:** `ask-ck/ck-facelift/PLAN-db-only-search.md` (Phase 1 now ✅). Committed this session.

- **Literal script source code ingested.** `build_script_index.py` → `scripts_sources.jsonl` (830 files / 5,782 code chunks); `build_db.py --fresh` filled `scripts.source_text` + `script_chunks` + `chunks_fts`. `db.search_code` / `search_code_hybrid` return real line-scoped code.
- **Semantic embeddings populated.** `build_db.py --embed` → **~84k vectors** across all 5 entities incl. `vec_chunks` (was 0). `/health` reports `vector_search:true, embeddings:83816`.
- **Embedding model is now stand-alone.** Bundled under `ask-ck/var/models/`, forced `HF_HUB_OFFLINE`/`TRANSFORMERS_OFFLINE` in `db.py` + `run.sh` — zero external dependency (the org vLLM LLM is the tool's function, not an external dep).
- **Strict DB-only runtime (Phase 1 DONE).** `data.py` + `pytest_create.py` source every corpus/reference from `db.*`; dead `load_json_safe`/`load_json_abs` removed; `main.py` **fails fast** if `ck.db` absent; **`tool/guard_db_only.py`** fails if a corpus JSON read reappears under `CK_server/` (verified it catches a regression).
- **Three latent bugs fixed:** (1) `build_db.py embed()` checked `db.HAS_VEC` before opening the connection that sets it → `--embed` had never run. (2) `db._vector_hits` ran the sqlite-vec KNN as a JOIN → sqlite-vec rejects it → error swallowed → semantic/hybrid silently returned keyword-only. (3) huggingface load-time ping (above).
- Docs synced (README, SERVER-README, both DB plans). ck.db gitignored = derived rebuildable cache (documented rationale).

## Latest session (2026-07-20) — LLM observability + Local LLM + admin panel + fast restart

**All committed + pushed (`47833de`, on top of `66fb289`).** Nothing pending.

- **LLM observability (`PLAN-llm-observability.md`, DONE).** Per-panel "Last LLM request" debug footer + token badges (honest `— tok` where a transport reports no usage); per-session JSONL log in gitignored `CK_server/debug-log/`; `GET /api/llm/recent` + `/log`. Backend: `llm._call_llm_with_meta` split into `_call_llm_raw` + instrumented wrapper; ContextVars `current_panel_id`/`current_request_path` set by main.py middleware from `X-CK-Panel`/path; recorder in `llm_debug.py` (credential-whitelisted). New: `CK_server/llm_debug.py`, `routers/llm_debug.py`, `static/js/llm-debug.js`.
- **Local LLM (org vLLM) login mode.** Third radio `local_llm` → OpenAI-compatible `http://vllm.ai.atlnz.lc/v1`, rides the existing OpenAI HTTP path; **Fast/Thinking toggle** (`vllm-fast`/`vllm-thinking`) applies live (no Apply click). Key stored server-side in gitignored `CK_server/secrets.local.json` (0600; env `LOCAL_LLM_KEY` fallback), never in browser/cfg/session/response/debug-log. `local_llm` is now the **default** radio. New: `CK_server/local_llm_key.py`.
- **Cold-load status:** `GET /api/wizard/llm_config` (no secrets) so a fresh page shows the real login, not "No credential". **Cache-Control: no-cache on `/static/js/*`** so bare-specifier ES-module imports always revalidate (was: stale child module shadowing new code even after a `?v=` bump).
- **Admin panel + fast restart.** Hidden admin panel (**double-click CK's face**): reset current-case / workspace / ALL sessions, rebuild embeddings + rebuild DB (background jobs polled at `/api/admin/job`), restart server (touches a watched `.py` so `--reload` fires). `routers/admin.py` at `/api/admin/*`; `static/js/admin.js`. **Localhost/single-user — no auth.** `run.sh --bg` (prompt-free bg start) / `--restart`; a plain restart needs only `run.sh`, NOT `setup.sh` (which rebuilds the DB).
- Also: earlier this window, an adversarial review (verify agents died on a session limit → findings adjudicated by hand) drove 6 fixes; see the plan's handoff header.

## Latest session (2026-07-16) — SQLite migration DONE + DB-only-search direction planned

**Read next:** `ask-ck/ck-facelift/PLAN-db-only-search.md` — the phased plan + testbox checklist for the next session.

- **DB migration COMPLETE (`PLAN-db-migration.md`).** All four commits landed: **A `6cb97ca`**, **B `bdb2043`**, **C `14cf4ad`**, **D `1a0ef2a`**. Corpora + sessions now live in `ask-ck/var/ck.db` (gitignored, rebuildable via `python3 tool/build_db.py --fresh --verify`). Server reads corpora from the DB (per-request `zephyr_cases.jsonl` scan + ~50 MB boot RAM gone); FTS5 keyword search (parity 79/80 vs live scorer) + sqlite-vec hybrid/semantic (`mode=keyword|hybrid|semantic`). **Vector `--embed` runs only where `enable_load_extension` exists (Linux / `pysqlite3-binary`)** — not mac system Python; keyword degrades gracefully.
- **Two feature branches built — STAGED, UNCOMMITTED, unit-verified, DB-rebuild pending:**
  - **Scripts literal-code** — the DB had only enrichment/tags/signatures; now captures actual `.py` source: `scripts.source_text` + `script_chunks` (per test-case/helper, loc-sliced) + `chunks_fts` + `vec_chunks`; `db.search_code`/`search_code_hybrid`. `build_script_index.py` emits `scripts_sources.jsonl` (courier), `build_db` ingests it (graceful if absent).
  - **Zephyr enrichment** — fixes two silent-drop bugs (`<details>` plain bodies → `script_text`, ~1,300; per-step `<testData>`, ~1,285) + adds `issues` (JSON, ~480) & `attachments` (filenames, ~250) as nullable columns; `script_text`+`refs_text` into `zephyr_fts` recall only (results unchanged).
- **DIRECTION DECISION — strict DB-only search:** `ck.db` is the SOLE search + runtime-reference source; server reads ZERO JSON; originals ingest direct-to-DB; JSON survives only as a build courier for remote sources (testbox/APIs), never searched. Phase 1 (repoint the ~5 remaining `data.py`/`pytest_create.py` runtime JSON reads to existing `db.*` getters) is the small first step. **Not started — for a future session.**
- **Pending single rebuild:** the two branches + the real extractions (Zephyr XML re-extract, scripts on the testbox) all land in ONE coordinated `build_db --fresh --verify` (+ `--embed`) — see the plan's testbox checklist.

## Latest session (2026-07-14) — PyTest Creator built + UI polish

- **PyTest Creator fully implemented** (was a 501 stub). 8-step gated flow turning a Complete refined case into a runnable Allied Telesis `framework` (ATTestSet/ATTestCase) test script, executed on a real testbox, iterated via an LLM fix loop to Final Validation. Plan + living tracker: **`ask-ck/pytest-create/PLAN-pytest-creator.md`** (start there for PyTest Creator work).
  - Sidebar steps: 1. Cases / 2. Sequence / 3. Script Search / 4. Fit Decision / 5. Fragments / 6. Generate / 7. Run / 8. Validate, plus a **Testboxes** panel.
  - New files: `tool/build_script_index.py` + `tool/enrich_script_index.py` (script index: 999 files across testsuites_art/svt_scripts/test_scripts + 55-module `framework_surface.json`; outputs to `ask-ck/pytest-create/data/`); `CK_server/pt_exec.py` (testbox profiles in gitignored `secrets.testboxes.json`, framework-log parser, threaded paramiko SSH runner); full rewrite of `routers/pytest_create.py`; 7 prompt templates (`pt_*.jinja`, `enrich_script_index.jinja`); `models.py` `PtSession`; `llm.py` `run_prompt`/`extract_json_block` + `timeout` param.
  - Robustness fix: LLM replies that come back as a bare JSON array (instead of the wrapped object) are now tolerated across sequence/matches/fragments parsing.
- **Export path fix**: the Generator's *Export Repeatable Bundle* wrote to the pre-restructure `ask-ck/refined-cases/` (didn't exist). Now uses the `REFINED_DIR` anchor → `ask-ck/objective-drafting/refined-cases/`. Verified by exporting T33233 (complete count 42 → 43).
- **UI**: new **Help → Main** splash page (default landing) with the CK photo, welcome blurb, and collapsible per-tool guides in inverse-sidebar order (Generator open, PyTest Creator, then Test Composer / Zephyr as TBD); CK photo added to the sidebar "Ask CK" logo line; buttons/dropdowns/search bars no longer stretch full-width; Generator panels gained an "Objective / Test Case Generator" eyebrow header above the dynamic case title.
- **Docs**: root `README.md` (hero CK image + per-tool guides matching Main), `SERVER-README.md` (PyTest Creator section), `SESSION_STATE.md`, and this file updated. `ckc.jpg` copied into `CK_server/static/` so it serves at `/static/ckc.jpg`.

**Remaining for PyTest Creator** (needs credentials/hardware): run `tool/enrich_script_index.py` with a logged-in CLI then rebuild; first real-LLM walkthrough (suggested case AWPTCM-T33234); first real-testbox SSH run; gitignore/LFS decision for the regenerable `ask-ck/pytest-create/data/`.

---

**Prior session theme (2026-07-13)**:
- **Repo restructure**: `drafting-tool/` → `ask-ck/CK-main/` (server code in `CK_server/`, was `drafting_server/`); root `data/`, `refined-cases/`, and process docs → `ask-ck/objective-drafting/`; per-tool dirs pre-staged (`ask-ck/pytest-create/`, `test-composer/`, `zephyr-tool/`).
- **Repathing**: new `CK_server/paths.py` single source of truth (DATA_DIR, REFINED_DIR, PROCESS_MD); `data.py`, `wizard.py`, `main.py`, `run.sh` fixed for the new layout. Boot-verified (410 cases: 368 open / 42 complete / 3 in progress).
- **Ask CK multi-tool facelift** (see `ask-ck/ck-facelift/PLAN-facelift.md`): app renamed **Ask CK**; sidebar sections (top→bottom) LLM (+ **Configure** panel), **Zephyr Templating Tool** (4 stub steps), **Test Composer** (1 stub step), **PyTest Creator** (Cases wired + Creator stub), **Objective/Test Case Generator** (the full wizard, visible steps renumbered **1–6**, display-only).
- LLM login UI moved out of old Step 0 into a main-area **Configure** panel (all element ids preserved; `showLLMConfig`/`#llmCredential`/`#llm-config-card` dead code removed).
- New navigation: `goToPanel(panelId)` primitive + `goToStep()` wrapper; `PANEL_META` page-header registry; ✓ nav-badges scoped to `#nav-generator`.
- Backend stubs: `routers/zephyr_tool.py`, `routers/test_composer.py`, `routers/pytest_create.py` (`/api/zephyr-tool|test-composer|pytest-create/status`; pytest `generate/{key}` → 501).

**Prior session (2026-07-13, Grok)**: load_case zrefs verify; relevance-ranked external Zephyr; dual case dropdowns; Search+Suggest Steps; table/stack-overflow fixes; workspace LLM persistence; gaps moved to synth/export; favicon; `git lfs migrate`.

---

## 1. High-Level Status

| Area | Status | Notes |
|------|--------|-------|
| Architecture Decision | Complete | Server-backed (FastAPI), multi-tool workbench (Ask CK) |
| Project Structure | Restructured 2026-07-13 | All work under `ask-ck/`; anchors in `CK_server/paths.py` |
| Core Backend | Strong | Gates, file sessions, search/suggest for TL/Zephyr/ATP, relevance zrefs, workspace LLM file |
| LLM Integration | Complete | Three login modes via sidebar Configure: **Local LLM** (org vLLM, OpenAI-compatible, Fast/Thinking, default), Claude Code CLI (per-user agent), Grok CLI; workspace default in the sessions table (`id='_workspace_llm'`); real-only (no MOCK). Per-request observability: debug footer + token badges + `CK_server/debug-log/` JSONL (2026-07-20) |
| Admin / restart | **Complete (2026-07-20)** | Hidden admin panel (double-click CK's face): reset sessions, rebuild embeddings/DB (background jobs), restart server. Fast restart: `run.sh --bg` / `--restart` (setup.sh only for first-time/rebuild). Localhost/single-user; `/api/admin/*` |
| Data Integration (Generator steps 2–4) | Implemented | Real TL candidates; external Zephyr ranked; ATP scored; Search/Suggest merge on all three |
| Repeatable Outputs | Advanced | Templates + note construction; export → `objective-drafting/refined-cases/`; gaps generated at synth/export |
| Process Enforcement | Implemented | Server-side confirms (domain steps 1–3) before synthesize |
| Frontend UI | Advanced (multi-tool) | Ask CK sidebar: Help→Main splash + tool sections; Generator + PyTest Creator full; Test Composer/Zephyr stubs; `goToPanel` navigation |
| PyTest Creator | **Complete (2026-07-14)** | 8-step gated flow (Cases→Validate) + Testboxes; script index + framework-surface; SSH execution; LLM fix loop. Tracker: `ask-ck/pytest-create/PLAN-pytest-creator.md`. Pending: enrichment run, real-LLM/testbox shakeout |
| Test Composer / Zephyr Templating | Scaffolded (TBD) | Placeholder panels + router stubs only |
| Documentation | Updated 2026-07-13 | PROGRESS / SERVER-README / LESSONS / READMEs / BoS-EoS prompts repathed |
| Hosting / nginx | Ready | Example config (paths may need the CK-main update) |
| Persistence | File-based | Per-case `CK_server/sessions/<key>.json` + workspace LLM JSON + refined-cases export |
| Polish & Completeness | Good | Facelift verified (boot + endpoints + served UI); manual E2E smoke still recommended |

**Overall Phase**: Usable. Generator and PyTest Creator both runnable end-to-end (PyTest Creator awaiting first real-LLM/testbox shakeout); Test Composer and Zephyr Templating remain scaffolds awaiting design/implementation.

---

## 2. Key Decisions & Rationale (Carry Forward)

- **Ask CK is the umbrella**: one server (`CK_server`), one UI (`static/index.html`), multiple sidebar tools. Future tool = card div + `PANEL_META` entry + sidebar item + router module (+ `include_router` in `main.py`).
- **Numeric step scheme is load-bearing and display-decoupled**: `data-step` 0–5, panel ids `step-0..step-5`, badge ids `#step1-badge..#step5-badge`, session keys `step1..step5`, and `confirm_step/{key}/{1|2|3}` are UNCHANGED. Sidebar labels 1–6 are display-only. Never bulk-replace "Step N".
- **Paths live in `CK_server/paths.py`** — anchor all data/output/doc references there, never CWD-relative.
- **Server-backed is required** (LLM synthesis, growing data, nginx host, extensibility).
- **Repeatability**: Jinja prompt templates + structured parse/output templates + server-built first testScript note.
- **Process gates must be real** (server-side confirms before synthesis).
- **All Ask CK work stays under `ask-ck/`**.
- **Gaps are not a review-step form field**: user confirms ATP selections only; LLM writes Gaps for Traceability at synthesize/export (`generate_gaps.jinja`).
- **LLM preference is workspace-scoped**: Apply/Login (Configure panel) persists the workspace default to the sessions table (`id='_workspace_llm'` — migrated off the old `sessions/_workspace_llm.json` file in the 2026-07-16 DB migration; any lingering `.json` is legacy). load_case copies onto cases without active config. `set_llm_config` no longer requires a case — keyless `POST /api/wizard/set_llm_config` saves the workspace default; with a key it also stores onto that case's session. `GET /api/wizard/llm_config` returns it (no secrets) for cold-load status.
- **PyTest Creator selection is isolated**: `ptCase` global + `#ptCaseSelOpen/#ptCaseSelDone`; must never touch `currentKey` / `#caseSel` / page header.
- **Complete vs open cases**: Complete = `refined-cases/**/AWPTCM-Txxxx/zephyr_payload.json` exists; partials (session progress) listed first in Open dropdown.

---

## 3. Current File Structure

```
ask-ck/
├── ck-facelift/PLAN-facelift.md    # 2026-07-13 facelift plan (as executed)
├── CK-main/
│   ├── SERVER-README.md            # Operational manual
│   ├── run.sh                      # PYTHONPATH=CK-main, uvicorn CK_server.main:app
│   ├── nginx-drafting-server.conf.example
│   ├── (design assets + legacy single-file index.html)
│   └── CK_server/
│       ├── main.py                 # Ask CK title; favicon; /process; 4 routers
│       ├── paths.py                # DATA_DIR / REFINED_DIR / PROCESS_MD anchors
│       ├── data.py                 # loads from objective-drafting/data/
│       ├── llm.py                  # gaps gen, suggest TL/Zephyr/ATP, analyze rank-only
│       ├── models.py
│       ├── routers/
│       │   ├── wizard.py           # Generator API (/api/wizard)
│       │   ├── zephyr_tool.py      # stub (/api/zephyr-tool)
│       │   ├── test_composer.py    # stub (/api/test-composer)
│       │   └── pytest_create.py    # stub (/api/pytest-create; generate → 501)
│       ├── static/index.html       # Ask CK multi-tool UI
│       ├── static/favicon.svg
│       ├── templates/prompts/      # generate_objectives/steps/gaps, suggest_*, analyze_atp_coverage
│       ├── templates/outputs/traceability.md.jinja
│       └── sessions/               # _workspace_llm.json + AWPTCM-Txxxx.json
├── objective-drafting/             # THIS DIR: PROGRESS, LESSONS, PLAN, PROCESS, README
│   ├── data/                       # zephyr_master, candidates, decisions, suites, zephyr_full (LFS)
│   └── refined-cases/<Group>/AWPTCM-Txxxx/
├── pytest-create/                  # (empty) future PyTest Creator assets
├── test-composer/                  # (empty) future Test Composer assets
└── zephyr-tool/                    # (empty) future Zephyr Templating Tool assets
```

---

## 4. What Is Currently Implemented (Working)

### Backend
- Data load anchored via `paths.py`: zephyr_master, candidates, decisions, slim_index, test_id_desc, testlink (boot-verified counts).
- **Step 2 zrefs**: relevance scoring over slim_index (keywords, hard anchors, omit current Cases list + primary); batch JSONL enrichment for top hits; returns `score` + `justification`.
- LLM: CLI modes `grok_cli` / `claude_code`; Jinja prompts; provenance; no MOCK.
- **generate_coverage_gaps** at synthesize (+ export if gaps empty).
- **Workspace LLM**: `_workspace_llm.json` on Apply/Login; applied on load when case has no active config.
- **GET /api/wizard/cases**: dual lists + counts; search + suggest endpoints for TL/Zephyr/ATP.
- Export: writes to `objective-drafting/refined-cases/<Group>/AWPTCM-Txxxx/`; validation hooks.
- **Tool stubs**: `/api/zephyr-tool/status`, `/api/test-composer/status`, `/api/pytest-create/status` + `POST /api/pytest-create/generate/{key}` → 501.

### Frontend (Ask CK UI)
- **Sidebar** (always expanded): LLM status + **Configure**; Zephyr Templating Tool (1. Info / 2. Test Plan / Cycle / Cases / 3. Link Test Scripts / 4. TBD); Test Composer (1. TBD); PyTest Creator (1. Cases / 2. Creator); **Objective/Test Case Generator** (1. Cases … 6. Test Steps (LLM)).
- **Navigation**: `goToPanel(panelId)` toggles `.tool-panel` cards + section-aware active state; `goToStep()` wrapper keeps all wizard flows; `PANEL_META` drives page header (tool panels get static titles; Generator shows `KEY — Title`).
- **LLM Configure panel**: relocated login chunk (radios, Check Grok/Claude CLI, model, Apply/Login, instructions) — ids preserved; `updateLLMStatus` still dual-writes inline + sidebar status.
- **PyTest Creator Cases**: **Complete cases only** (`#ptCaseSelDone`), fed by the same `/api/wizard/cases` fetch inside `refreshCaseSelects`; `handleCasePairChange` shared helper; selection isolated in `ptCase`; Creator panel shows selected case.
- Placeholder panels (dashed `.placeholder-panel`, theme-aware) — zt-info and tc panels fetch stub `/status` messages.
- ✓ nav-badges scoped to `#nav-generator`; heading badges + confirm/synthesis flows unchanged.
- Prior batch retained: dual case dropdowns, Search+Suggest toolbars, cols-5/cols-6 tables, editors, review summary, post-synth teal **Export Repeatable Bundle** + **Edit / Revise Steps** guard, favicon.

---

## 5. What Is Not Yet Implemented (Priorities)

### High Priority (Next Session Focus)
1. **Manual E2E smoke on the facelift** — S  
   - Browser pass: Generator Load → confirm 2/3/4 → synthesize 5/6 → export; Apply/Login from Configure panel; PyTest Cases isolation; theme toggle on new panels. (Automated checks passed: boot, endpoints, served HTML, JS syntax.)
2. **Output generation hardening** — M  
   - Edge cases: empty selections, thin ATP, re-export after edit; stricter pre-write validation vs real `refined-cases` exemplars; confirm first-step note + Gaps quality.
3. **Real CLI smoke on full UI path** — S (0.25–0.5 session)  
   - Grok + Claude live synthesis; Claude Team previously often only faked CLI.
4. **Error handling + loading UX** — M  
   - load_case ATP rank can be slow (LLM); clearer spinners/timeouts; surface synthesis/export errors in-page.

### Medium Priority
- **Design first real step of a new tool** (likely PyTest Creator → Creator, or Zephyr Templating → Info) (M).
- `tool/` scripts (e.g. `upload_refined.py`, extract/build scripts) — verify/repath for `ask-ck/objective-drafting/` layout (S).
- Process Reference page: full markdown + deep links; its hardcoded "Step 1..4" anchor text now drifts from the 1–6 sidebar labels (S–M).
- `requirements.txt` / pyproject + simple setup (S).
- Server-side indexing for full jsonl/suites search quality (M).

### Lower / Future
- Hash routing / deep links (refresh currently lands on Generator Cases) (S–M).
- Multi-user auth (L).
- Advanced LLM (critique loop, few-shot from past refined cases) (L).
- Automated tests + CI (M).
- One-command nginx setup (S–M).

---

## 6. How to Resume Work (For Future Sessions)

1. Read this **PROGRESS.md** completely.  
2. Read **`ask-ck/CK-main/SERVER-README.md`** (run + workflow).  
3. Skim **LESSONS_LEARNED.md** (esp. 2026-07-13 entries).  
4. Start server from repo root:
   ```bash
   ./ask-ck/CK-main/run.sh
   # → http://localhost:8000/
   ```
5. Apply LLM once (sidebar **LLM → Configure**) — preference persists in `_workspace_llm.json`.  
6. Use **Open / partial** for unfinished work; **Complete** for refined payloads.  
7. Do not reintroduce review-step gaps editing or MOCK paths; do not renumber the internal step scheme.

---

## 7. Important Context to Remember

- Main goals: **repeatable process** + **repeatable outputs** with user review gates and templated LLM.  
- Ask CK is becoming multi-use: Generator is the mature tool; PyTest Creator / Test Composer / Zephyr Templating Tool are scaffolds with matching `ask-ck/<tool>/` dirs for future assets.  
- Legacy single-file tool (`CK-main/index.html`) is reference only.  
- Gaps belong in Traceability artefact (LLM-authored at completion), not as a mid-wizard free-text gate.

---

## 8. Technical Debt & Known Issues

### Technical Debt
- LLM parsing still regex/JSON fallback — could use stricter structured output later.
- Full zephyr_cases.jsonl not fully indexed for search (keyword scan + slim_index scoring only).
- No automated tests / requirements.txt.
- zrefs scoring ~1.5s over 45k slim_index — acceptable but not optimized.
- load_case still runs ATP LLM ranking (latency); gaps no longer on load (good).
- `tool/` scripts not yet verified against the 2026-07-13 restructure paths.

### Known Issues / Limitations
- Shared multi-tenant server pooling one CLI login is unsupported (per-user local host intended).
- Grok CLI may still emit preamble; stripping helps but is imperfect.
- GitHub: large sources must stay LFS in **all** history commits (use `git lfs migrate` if reintroducing big files). The `ask-ck/` tree is currently **untracked** — first commit after restructure should confirm LFS patterns still match the moved `data/zephyr_full/` files.
- `/process` page anchor text ("Step 1..4") predates the 1–6 sidebar renumber; links were never live (no hash routing).
- Some older session JSON may still hold stale Step 3 gap text; synth/export overwrites for Traceability.

---

## 9. Prioritized Backlog with Effort Estimates

| Priority | Item | Effort | Notes |
|----------|------|--------|-------|
| High | Manual E2E smoke of facelift (browser) | S | Generator flow + Configure panel + PyTest isolation |
| High | Output generation hardening | M | Post gaps-at-synth validation |
| High | Real Grok+Claude E2E UI smoke | S | Provenance + refined-cases check |
| High | Error/loading UX | M | Especially load_case + synthesize |
| Medium | First real new-tool step (design + build) | M | PyTest Creator or Zephyr Templating |
| Medium | Repath/verify `tool/` scripts | S | upload_refined.py etc. |
| Medium | Process page + deep links | S–M | Fix step-label drift |
| Medium | requirements.txt / setup | S | |
| Medium | Full data indexing | M | |
| Low | Hash routing, tests/CI, multi-user, advanced LLM | M–L | |

**Completed this session (2026-07-13, Claude)**:
- Repo restructure support: `paths.py` + repath of data.py / wizard.py / main.py / run.sh (boot-verified)  
- Ask CK facelift: rename, sidebar multi-tool sections, 1–6 display renumber, `goToPanel`/`PANEL_META` navigation  
- LLM Configure panel relocation + dead-code cleanup (`showLLMConfig`, `#llmCredential`, `#llm-config-card`)  
- New tool scaffolds: 7 placeholder panels + 3 router stubs; PyTest Creator Cases wired (isolated selection)  
- Nav-badge scoping to Generator  
- Docs repathed: root README, this file, SERVER-README, LESSONS, READMEs, BoS/EoS prompts, SESSION_STATE entry

---

## 10. Cross-References

- Root `README.md` — project framing; Ask CK summary  
- Root `SESSION_STATE.md` — broader history (2026-07-13 entries)  
- `OBJECTIVE_DRAFTING_PROCESS.md` (this directory) — process source of truth  
- `ask-ck/ck-facelift/PLAN-facelift.md` — facelift plan as executed  
- External `AGENTS.md` — machine/CLI environment if present  

---

## 11. Session Handoff Checklist

When starting a new session:
- [ ] Read `ask-ck/objective-drafting/PROGRESS.md` (this file)
- [ ] Read `ask-ck/CK-main/SERVER-README.md`
- [ ] Skim `ask-ck/objective-drafting/LESSONS_LEARNED.md` (2026-07-13)
- [ ] Run `./ask-ck/CK-main/run.sh`; hard-refresh browser
- [ ] Confirm Ask CK sidebar: LLM Configure + 4 tool sections; Generator "1. Cases" active
- [ ] Apply LLM once (Configure panel); switch cases — status must stick
- [ ] Load open case → Search/Suggest steps 2–4 → confirms → synthesize (5/6) → check Gaps in traceability → export
- [ ] PyTest Creator case selection does NOT change the Generator's loaded case
- [ ] Review steps have **no** gaps textarea
- [ ] At end: update PROGRESS + LESSONS + SERVER-README; append root SESSION_STATE if impactful

---

**This file is the primary handoff document.** Keep it updated after every significant session.
