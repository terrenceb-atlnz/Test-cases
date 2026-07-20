# PyTest Creator — Implementation Plan & Progress Tracker

> Living tracker for the PyTest Creator build-out. Update the checklist and Progress Log
> as milestones land (same convention as `ck-facelift/PLAN-facelift.md`).
> Approved: 2026-07-14.

## Status Checklist

- [x] **Phase 0 — Plan tracker:** this file saved to `ask-ck/pytest-create/` (2026-07-14)
- [x] **Phase A — Index** (no hardware/UI) — DONE 2026-07-14
  - [x] `tool/build_script_index.py` mechanical AST pass over the 3 script roots (999 files: art 188 tests + 51 libs, svt 77 files, legacy 683 files; 120 py2-vintage regex fallbacks)
  - [x] `--framework` pass → `framework_surface.json` (55 modules from `DeviceSkrips/framework`)
  - [x] `paths.py` / `data.py` loading + real `GET /api/pytest-create/status`
  - [x] Verified counts + `loc` slicing via `GET /script_source` (test-1332.1001 record checked incl. `+=` method accumulation)
  - [x] LLM enrichment pass (`tool/enrich_script_index.py`, resumable via sha1 jsonl; `--mechanical-only` flag on the builder) — **script ready; enrichment itself not yet run (needs CLI login); index works unenriched**
- [x] **Phase B — Steps 1–6** (no hardware) — DONE 2026-07-14
  - [x] `PtSession` model + `sessions/pt-{key}.json` persistence + confirm gates (+ downstream invalidation)
  - [x] Step 2: sequence extraction (`pt_extract_sequence.jinja`) + save/edit
  - [x] Step 3: mechanical search + LLM suggest (`pt_match_scripts.jinja`) + free search + source viewer
  - [x] Step 4: fit assessment (`pt_assess_fit.jinja`) with real source slices
  - [x] Step 5: fragment gathering (`pt_gather_fragments.jinja`, mechanical loc resolution, invented symbols dropped)
  - [x] Step 6: generation (`pt_generate_script.jinja` + exemplar + framework surface) + editable Group/Name + `lint_script` (py_compile/structure/framework-import checks)
  - [x] Frontend panels: Sequence / Script Search / Fit Decision / Fragments / Generate (+ Run / Validate / Testboxes)
  - [ ] Milestone: reviewed, lint-clean script at `generated/<Group>/<Name>.py` — **pending first real LLM walkthrough (needs grok/claude CLI login)**
- [x] **Phase C — Execution** (code complete; awaiting real-testbox shakeout) — 2026-07-14
  - [x] Testbox profiles CRUD + `secrets.testboxes.json` (0600, password write-only/redacted; CRUD round-trip tested)
  - [x] `pt_exec.py` (paramiko SSH/SFTP, threaded runs, per-stage status persistence, stale-marking on restart)
  - [x] `parse_framework_log()` + offline fixture-log unit test (PASS/FAIL/crash-mid-case all covered)
  - [x] Run panel (testbox dropdown labeled `name — tb<NN> (IP)` + "➕ Add new testbox…", setup picker, check connection, 4s poll, PASS/FAIL chips, raw log tail)
  - [ ] First execution against a real testbox — **pending hardware access**
- [x] **Phase D — Validation loop** (code complete) — 2026-07-14
  - [x] `pt_fix_script.jinja` fix loop + `history/iter-N/` archiving + step 6/7 confirm resets
  - [x] Final Validation gate (`POST /validate` checks: run done, cases parsed, all PASS, zero fails, exit 0 + human confirm step 8)
  - [x] Promotion messaging + provenance stamping (validated_at / run_id / profile name, no credentials)
  - [x] SERVER-README update (PyTest Creator section)

### Remaining / next session
1. Run the enrichment pass with a logged-in CLI: `tool/enrich_script_index.py --limit 100` (repeat to taste), then `tool/build_script_index.py` to merge.
2. First full walkthrough of steps 2–6 with a real LLM on `AWPTCM-T33234` (Port — Auto MDI/MDI-X; the mechanical search already surfaces `legacy/5000_mdi_mdix/*` as top hits).
3. Add a real testbox in the Testboxes panel, `Check Connection`, and shake out the SSH run path end-to-end.
4. Consider `.gitignore`/LFS treatment for `ask-ck/pytest-create/data/` (~2.6 MB regenerable index files) — currently untracked.

## Script index status (as of 2026-07-15) — COMPLETE

- **Index: 830 scripts, 100% enriched** (art 239, svt 77, legacy 514). Final composition after excluding a nested vendored SQLAlchemy copy (235 files) found bundled inside `legacy/tools/memory_leak_tools/` — added `"sqlalchemy"` to `EXCLUDES` (7 genuine memory-leak tooling files in that dir remain indexed). Also earlier widened the legacy filter to include numeric suite dirs (e.g. `5003_feature_limits`) and excluded `a1c_playwright` (Playwright web-UI tests, not framework scripts).
- **Enrichment completed across 3 resumed runs** (150 → 370 → 930 → 1000 → 830 after the vendor exclusion), hit and recovered from one Claude seat 429 rate limit mid-way; fully resumable via the sha1-keyed jsonl, zero data loss.
- **Verified the fix works**: mechanical scoring for the MDI/MDIX case now returns **art: 13, svt: 11, legacy: 25** matches (was 0/0/10 before enrichment) — confirms the "art/svt score zero" symptom is resolved.
- To rebuild later (e.g. after script repos change): `cd tool && ./build_script_index.py --mechanical-only` then `./enrich_script_index.py --limit 2000` (only re-enriches new/changed files, sha1-keyed) then `./build_script_index.py` to merge.

## Progress Log

- **2026-07-20** — First live LLM walkthrough attempt exposed and fixed a **dangerous config bug**: every PyTest LLM endpoint resolved `_llm_cfg(sess)` raw and only `load_case` applied the workspace login, so a stale/inactive session silently used the default backend (`claude_agent`/`model=default`) instead of the configured `local_llm`. Caught by the new LLM debug-log (a real `extract_sequence` on T33233 recorded `auth=claude_agent` + a timeout). **Fixed** by folding the workspace-apply into `_llm_cfg` itself (impossible for any endpoint to forget). Also this session: **prompt trim** of `pt_extract_sequence.jinja` (−46%; dropped the reviewer-facing traceability dump — objective + Zephyr steps are the authoritative inputs), and **LLM Provenance + dry-run preview** wired into all PyTest panels (sequence/search/fit/fragments/generate) — a copyable, live-refreshable prompt preview that renders 1-for-1 without sending (see SERVER-README "LLM Provenance"); the normal (non-dry) endpoints now also store the sent `prompt`+`response` in step provenance (were provider/model only). All uncommitted at session end. **The Phase B milestone (first reviewed lint-clean generated script) is still pending** — the config bug blocked the first real walkthrough; retry on T33234/T33233 with `local_llm`/`vllm-thinking` now that dispatch resolves correctly.
- **2026-07-15** — Enrichment fully completed (830/830 scripts, 100%) across 3 resumed background runs; found and excluded a nested vendored SQLAlchemy copy (235 files) inside `legacy/tools/memory_leak_tools/` that the LLM correctly refused to tag with networking vocabulary. Verified fix: MDI/MDIX mechanical matching now returns art 13 / svt 11 / legacy 25 (was 0/0/10). Also fixed step-3 UI: per-database result sections, scrollable lists, no horizontal overflow (generalized `.table` overflow guard), and reworked the search/guidance layout (keyword box vs LLM-suggestion box). Confirmed all three DBs are swept by the mechanical scorer — the original zero results for art/svt were purely a 0%-enrichment + numeric-dir-naming issue, not a sweep bug.
- **2026-07-14** — Plan approved; tracker created.
- **2026-07-14** — Full implementation landed in one session:
  - `tool/build_script_index.py` + `tool/enrich_script_index.py` (index: 999 files, 55 framework modules).
  - `CK_server`: `paths.py`/`data.py` index loading; `models.py` `PtSession`; `llm.py` gained `timeout` threading + generic `run_prompt`/`extract_json_block`; `pt_exec.py` (profiles/secrets, log parser, SSH runner); `routers/pytest_create.py` full rewrite (status, load_case/session/clear, confirm gates 2–8, extract/save sequence, search/suggest/save matches, script_source, assess/save fit, gather/save fragments, generate/save/lint script, profiles CRUD+check, run + run_status, fix_script, validate).
  - 7 prompt templates (`pt_*.jinja`, `enrich_script_index.jinja`).
  - Frontend: PyTest Creator sidebar expanded to 8 steps + Testboxes; panels with confirm gates + ✓ badges (`data-pt-step`, separate from the Generator's `data-step`).
  - Verified without hardware: server boots + loads index; load_case snapshots the refined payload (traceability step skipped); mechanical search returns the mdi_mdix suite for T33234; gates 409 correctly; log-parser unit tests pass; profile CRUD redacts + chmods + is gitignored; JS syntax-checked; served page contains all panels.

---

## Context

Ask CK (`copilot/Test-cases/ask-ck/CK-main/CK_server/`) is a self-hosted FastAPI test-engineering workbench. Its mature tool (the Objective/Test Case Generator) refines AWPTCM manual test cases; ~42 completed cases exist under `ask-ck/objective-drafting/refined-cases/<Group>/AWPTCM-Txxxx/` with Zephyr-ready steps in `zephyr_payload.json`.

**Goal:** build the **PyTest Creator** — currently a stub (`CK_server/routers/pytest_create.py` returns 501; the "Cases" sidebar step already lists Complete cases) — into a guided pipeline: extract a prescriptive test-step sequence from a completed case → search a new index of the three script databases for full/partial/no coverage → decide reuse vs new → gather reusable fragments → LLM-generate the composite script using the Allied Telesis `framework` library → execute on a real testbox selected from a stored dropdown → parse the framework log → LLM-fix and repeat until Final Validation. Every step has a human review/confirm gate, mirroring the existing wizard.

**Framework scope note:** `framework` is a whole library — `ATTestSet`/`ATTestCase` are the required base classes, but real scripts draw on many other parts (`ATDrivers.ATSwitch/ATStack/ATIxia/ATTestBox/ATBootLoader/ATPower/...`, `ATLibrary.ATTools/ATDHCP/ATRadius/ATSecurity/ATMulticast/...`, `Setup`, `ATPackets`). The indexer, matching, and generation prompts must treat the full framework surface as the vocabulary, not just those two classes.

### Established facts (verified)

- **Target style** = testsuites_art anatomy: `TestSet(ATTestSet.TestSet)` with `init(setup)/configure()/tear_down()`; `TestCase_N(ATTestCase.TestCase)` with `testCaseDesc/testCaseRef/testCaseMethod` + `main()` asserting via `self.passed()/self.failed()`; `__main__` does `ts.add_testCase(...)`, `ts.run(sys.argv)`; invoked `sudo python3 test-X.Y.py -s <topology>.setup -v`. Framework log format: timestamped lines, `>> test-<name>` / `TEST_CASE_*` header blocks, `PASS:` / `!!FAIL:` lines, `<< test-<name>: RESULT (numPassed: p numFailed: f)` footers; log named after the script basename.
- **Script databases (no index exists):** `testsuites_art/` (189 tests + 52 `library_*.py`; ignore vendored `1371_trex_traffic_tests/trex_libs/`), `svt_scripts/` (~70 real scripts + `libSvt/`; ignore vendored `3009_pluggable_qualifications/Python-3.9.19/`), `test_scripts/` (~828 py, mixed vintage; `6901–6914`/`TestSuite/` ATPyLib-training dirs are canonical templates).
- **Framework source** readable at `DeviceSkrips/framework/` on this mount; runtime symlink `/home/st-art/framework` exists only on real testboxes.
- **Patterns to mirror (verified line refs):** wizard session persistence `wizard.py:115-149`, confirm gates `wizard.py:1348+`, mechanical scoring `wizard.py:291-409` (`_score_zephyr_candidate` at 316), suggest flow `wizard.py:1165+`, complete-case resolution `_refined_complete_keys` `wizard.py:740`. LLM CLI invocation in `llm.py` (`render_prompt`, `_call_llm_with_meta`; hardcoded 180s subprocess timeouts at `llm.py:131,186`). Secrets convention: `.gitignore` ignores `secrets.*`; loader precedent `tool/upload_refined.py::_find_secrets_file()`. paramiko 2.9.3 is installed.

### User decisions

1. **Indexing:** hybrid — re-runnable offline pipeline: mechanical AST extraction + LLM enrichment → index JSONs loaded at startup.
2. **Testing:** the tool executes generated scripts on a testbox. The UI presents a **dropdown of stored testboxes (IP address and tb number at minimum)** plus an **"Add new testbox…" option** that opens a form to populate the dropdown for repeated use.
3. **Output:** function-based names organized by the refined-cases group structure — `ask-ck/pytest-create/generated/<Group>/<FunctionName>.py` (e.g. `generated/Port/MDIX_test.py`). At creation the tool proposes a group + name and **prompts the user to edit the naming** before saving. Promotion to testsuites_art is manual after validation.
4. **Plan tracking:** this file is the living progress tracker.

---

## 1. Indexer pipeline — new `Test-cases/tool/build_script_index.py`

Standalone script following `tool/` conventions (`#!/usr/bin/env python3`, argv output path).

**Sources/excludes:**
```python
ROOTS = {"art": ".../testsuites_art", "svt": ".../svt_scripts", "legacy": ".../test_scripts"}
EXCLUDES = ["1371_trex_traffic_tests", "trex_libs", "3009_pluggable_qualifications/Python-3.9.19", "__pycache__"]
```

**Pass 1 — mechanical AST extraction** over `test-*.py`, `library_*.py`, `lib*.py`, `test_scripts/tools/*.py`. `ast.parse`; on `SyntaxError` (py2 vintage) regex fallback + `"parse_error": true`. Per-file record: id (`art/1332_lldp_med/test-1332.1001.py`), db, path, suite_dir, kind (test|library|tool), imports, testset info (init devices, portlinks, has_configure/tear_down, FEATURES), `test_cases[]` with `{class, desc, ref, method, loc:[start,end]}` (capture `testCaseMethod +=` accumulation; `loc` makes fragment resolution mechanical, not hallucinated), helpers, loc_total, sha1, mtime.

**Pass 2 — LLM enrichment (resumable):** reuse `llm.render_prompt` + `llm._call_llm_with_meta` via `sys.path` insert of `CK_server/`. New template `templates/prompts/enrich_script_index.jinja`: batches of ~10 mechanical records (never full source) → `{summary, feature_tags[], covered_actions[]}` per id. Append to `pytest-create/data/scripts_index_enrich.jsonl` keyed by sha1; reruns skip seen sha1s. `--mechanical-only` flag so Phase A completes without LLM.

**Outputs** in `ask-ck/pytest-create/data/`: `scripts_index.json` (full records), `scripts_slim_index.json` (`{id, db, suite_dir, kind, title, feature_tags, summary, n_cases}` — the search corpus), `scripts_index.meta.json` (build info, enrichment coverage %).

**Framework surface index (same script, `--framework` pass):** walk `DeviceSkrips/framework/` (`ATTestSet.py`, `ATTestCase.py`, `Setup.py`, `ATPackets.py`, `ATDrivers/*.py`, `ATLibrary/*.py`) and emit `framework_surface.json` — per module: classes, public methods (name, args, first docstring line). This is the vocabulary the matching and generation prompts use, so generated code can call any part of the library (drivers, helpers, packet builders), not just the two base classes. Mechanical `imports` extraction in Pass 1 records which framework modules each existing script actually uses — a strong matching signal (e.g. a case needing PoE points at scripts importing `ATDrivers.ATPower`/Sifos helpers).

**Loading:** `paths.py` adds `PYTEST_CREATE_ROOT`, `PT_DATA_DIR`, `PT_GENERATED_DIR`; `data.py::load_all_data` adds `scripts_index`/`scripts_slim` with graceful degradation when absent (index is built out-of-band).

## 2. Backend — rewrite `CK_server/routers/pytest_create.py`

### Session model (`models.py`)
`PtSession`: key, payload snapshot (zephyr_payload.json), group, `step2..step8` dicts (each with `confirmed`/`confirmed_at`), `llm_config`, `updated_at`. Persist to `CK_server/sessions/pt-{key}.json` (`pt-` prefix avoids wizard collision). Local helpers `_pt_session_path/_pt_persist/_pt_load/_pt_clear` mirroring `wizard._persist_session` etc.; reuse/factor `_apply_workspace_llm_if_needed`/`_load_global_llm` so the workspace LLM login flows in. Confirming step N invalidates downstream confirmations.

Step shapes: step2 sequence `[{n, action, verify, zephyr_step_idx}]`; step3 matches `[{id, score, coverage: full|partial|none, reason}]` + selections + user_inputs; step4 `{decision: reuse|extend|new, base_script, per_step[]}`; step5 fragments `[{source_id, symbol, loc, code, maps_to[], why}]`; step6 `{naming:{group, name}, files:{test,library}, iterations, history[], provenance}`; step7 `{profile, runs[]}` where each run has run_id, status (queued|running|done|error), log_file, `parsed:{cases:[{name,result,fail_msgs}], numPassed, numFailed}`; step8 `{validated, validated_at, run_id}`.

**Generated output layout:** script at `PT_GENERATED_DIR/<Group>/<Name>.py` (Group defaults to the case's refined-cases group, e.g. `Port`; Name is a function-based proposal from the case title, e.g. `MDIX_test`). Both are shown to the user as editable fields at creation (`POST /save_script` body `{group, name, code, ...}` — server slug-validates and rejects path traversal). Per-test metadata (provenance.json, sequence.md, `history/iter-N/`, `runs/<run_id>/`) lives in a sidecar: `PT_GENERATED_DIR/.meta/<Group>/<Name>/`, keeping the group folders clean single-file scripts as requested. The session (keyed by AWPTCM case) records the case→script mapping in `step6.naming` and provenance.

### Endpoints
| Endpoint | Flow step | Notes |
|---|---|---|
| `GET /status` | — | real: index counts, enrichment %, profile count |
| `POST /load_case/{key}`, `GET /session/{key}`, `POST /clear_session/{key}` | 1 | group via `REFINED_DIR` glob (like `_refined_complete_keys`), snapshot payload + traceability.md; mark stale `running` runs |
| `POST /confirm_step/{key}/{step}` | 2–8 | single gate endpoint, mirrors `wizard.confirm_step` |
| `POST /extract_sequence/{key}` + `POST /save_sequence/{key}` | 2 | LLM extract; save = user edits before confirm |
| `GET /search_scripts?q=&db=&limit=` | 3 | mechanical scoring only |
| `POST /suggest_scripts/{key}` | 3 | LLM re-rank of top-40 mechanical candidates |
| `GET /script_source?id=&start=&end=` | 3/5 | source slice; path validated against index, never raw paths |
| `POST /assess_fit/{key}` | 4 | LLM over selected scripts' loc-sliced blocks |
| `POST /gather_fragments/{key}` + `POST /save_fragments/{key}` | 5 | LLM proposes `{source_id, symbol, maps_to, why}`; backend resolves symbol→loc→code mechanically |
| `POST /generate_script/{key}` + `POST /save_script/{key}` | 6 | generate proposes `{group, name}` (editable in UI); save validates naming and writes `<Group>/<Name>.py` + sidecar `.meta/<Group>/<Name>/{provenance.json, sequence.md}` |
| `POST /lint_script/{key}` | 6 | `py_compile` + import smoke with `PYTHONPATH=.../DeviceSkrips` + structural checks (TestSet class, `ts.run(sys.argv)`, every case has desc/ref/method) |
| `GET/POST/DELETE /profiles...` + `POST /profiles/{name}/check` | 7 | CRUD; check = SSH connect + framework dir test + `sudo -n true` |
| `POST /run/{key}` + `GET /run_status/{key}/{run_id}` | 7 | background execution + polling |
| `POST /fix_script/{key}` | loop | LLM fix from failures + log excerpts; archive to `.meta/<Group>/<Name>/history/iter-N/`; reset step6/7 confirms |
| `POST /validate/{key}` | 8 | machine validation; human still confirms via gate |

Use `request.app.state.app_data`, not wizard's per-request `load_all_data()` inefficiency.

### Prompt templates (`templates/prompts/`, style of `generate_steps.jinja`: context → strict rules → JSON-only)
`pt_extract_sequence.jinja` (objective + steps, skip traceability step 0 → sequence JSON), `pt_match_scripts.jinja` (sequence + top-40 slim candidates + user inputs → coverage verdicts), `pt_assess_fit.jinja` (→ reuse/extend/new + per-step mapping), `pt_gather_fragments.jinja` (→ fragment refs, no code in output), `pt_generate_script.jinja` (sequence + resolved fragment code + one ART exemplar + one ATPyLib-training template as style anchors + framework contract rules + a relevant slice of `framework_surface.json` so the model can use the full library — drivers, ATLibrary helpers, packet builders — not just the base classes; required elements: `ATTestSet.TestSet`/`ATTestCase.TestCase` subclassing, per-case desc/ref/method with `testCaseRef = '{key}'`, `ts.run(sys.argv)`; filename from the user-confirmed `<Group>/<Name>.py` → fenced python), `pt_fix_script.jinja` (code + parsed failures + bounded log excerpts → revised files), `enrich_script_index.jinja` (indexer).

### Matching/scoring (steps 3–4)
Two-stage like the wizard: mechanical scoring first, LLM on a bounded top-40. Adapt `_zephyr_tokens`/`_specific_tokens`/`_score_zephyr_candidate` (wizard.py:298-409): tokenize sequence actions + title; weight feature_tags 12/token, suite_dir leaf 10, summary+title substring 6; require one specific signal; `_PT_GENERIC_TOKENS` stoplist ("test", "verify", "check", "switch", "port"…).

### Testbox profiles + secrets
Store at `Test-cases/secrets.testboxes.json` (auto-covered by existing `secrets.*` gitignore rule; discovery per `upload_refined.py::_find_secrets_file()`):
```json
{"profiles": {"lab-box-3": {"tb_number": "tb105", "host": "10.36.x.y", "port": 22, "user": "st-art",
  "auth": "key|password", "key_path": "~/.ssh/id_rsa", "password": null,
  "framework_path": "/home/st-art/framework", "remote_workdir": "/home/st-art/pytest-create",
  "setups": {"default": "/home/st-art/setups/box3.setup"}, "sudo": "passwordless"}}}
```
`tb_number` and `host` (IP) are the minimum required fields — they label the dropdown entries.
`GET /profiles` redacts password (`has_password: true`); credentials never in sessions, provenance, or logs. Prefer key auth.

### Remote execution — new module `CK_server/pt_exec.py`
paramiko SSH + SFTP. Per run_id: (1) mkdir remote `{workdir}/{key}/{run_id}`, SFTP put the script (+ library) and chosen `.setup` (remote path from profile or UI-uploaded content); (2) `cd … && sudo python3 ./<Name>.py -s {setup} -v` with hard timeout (default 1800s, profile-configurable); (3) SFTP get the framework log (named after the script basename, e.g. `MDIX_test.log`, per `ATTestSet.create_log_file`) into `.meta/<Group>/<Name>/runs/{run_id}/`; (4) parse + persist. Background = `threading.Thread` (not FastAPI BackgroundTasks — must survive the response and be pollable); status transitions persisted at each stage so restarts leave honest "stale" state; one active run per key (409 otherwise).

**Log parser:** pure `parse_framework_log(text) -> dict` — regex over `>> test-<name>`, `TEST_CASE_*` blocks, `PASS:`/`!!FAIL:`, `<< test-<name>: RESULT (numPassed: p numFailed: f)`, stripping timestamp prefixes. Unit-testable offline against a fixture log.

## 3. Frontend — `static/index.html`

Extend PyTest Creator sidebar (~line 1325) to: `1. Cases` (exists) / `2. Sequence` / `3. Script Search` / `4. Fit Decision` / `5. Fragments` / `6. Generate` / `7. Run` / `8. Validate` / `Testboxes`. Use `data-pt-step` + own `updatePtBadges()` fed from session `stepN.confirmed` — do NOT use `data-step` (badge loop is scoped to `#nav-generator` per PLAN-facelift 1h). Repurpose `panel-pt-creator` as `panel-pt-seq`; add panels `panel-pt-search/-fit/-frag/-gen/-run/-validate/-testbox`; register in `PANEL_META` (~line 2674) and dispatch in `goToPanel` (~line 2635). Keep `ptCase` global; add `ptSession` refreshed via `POST /load_case` then `GET /session/{key}`.

Common panel skeleton: "Run LLM" → spinner → editable result (sequence table, match/fragment checklists, code textarea) → "Confirm step N". Generate panel additionally shows editable **Group** and **Script name** fields (pre-filled with the proposal, path preview `generated/<Group>/<Name>.py`) before save. Run panel: **testbox dropdown** listing stored profiles labeled `name — tb<NN> (IP)`, with a final **"Add new testbox…"** entry that opens the add form inline (populating the dropdown on save); then setup picker + "Check connection" + "Run on Testbox" → poll `/run_status` → per-case PASS/FAIL chips + raw-log toggle. Validate panel: summary; "Fix with LLM" (on failure) returns to Generate with before/after view; "Final Validate + Confirm" when all-PASS. Testboxes panel: full profile list/add/edit (password write-only)/delete/check — the same form the dropdown's "Add new" opens.

## 4. Validation loop

Run → parse → failures feed `POST /fix_script` (archives prior code to `history/iter-N/`, bumps iterations, resets step6/7 confirms so revised code is re-reviewed and re-run) → repeat. **Final Validation (concrete):** latest run `done`, ≥1 parsed case block, every case PASS, `numFailed == 0`, no stray `!!FAIL:`, exit code 0 → `step8.validated = true`; then the human gate `confirm_step/{key}/8`; UI shows manual promotion instructions (copy into `testsuites_art/<suite>/`) and stamps `provenance.json` (validated_at, run_id, profile name — no credentials).

## 5. Phasing

- **Phase 0 — Plan tracker:** this file. All progress updates go here.
- **Phase A — Index** (no hardware/UI): mechanical pass + framework-surface pass + paths/data loading + real `GET /status`; then enrichment. Verify counts (~189 art tests, 52 art libs, ~70 svt, ~828 legacy minus excludes); spot-check `loc` slicing via `GET /script_source`.
- **Phase B — Steps 1–6** (no hardware): session/gates, sequence, search/suggest, fit, fragments, generate + naming prompt + lint, all panels except Run/Validate. Milestone: reviewed, lint-clean script at `generated/<Group>/<Name>.py`.
- **Phase C — Execution:** profiles + secrets, `pt_exec.py`, log parser (built offline against a fixture log), Run panel. Only the final SSH round-trip needs a real testbox.
- **Phase D — Validation loop:** fix prompt, history/iterations, final gate, promotion messaging, SERVER-README update.

## 6. Verification

- Indexer: run `--mechanical-only`, compare per-root counts against known totals; open a few `GET /script_source` slices and confirm they match the real files.
- Log parser: unit test against a fixture log synthesized from the framework's `_start_logs`/`_finish_logs` format (or a real testbox `.log`).
- Steps 1–6 end-to-end on the dev mount: pick a completed case (e.g. `refined-cases/Port (7)/AWPTCM-T33234/`), walk the wizard to a lint-clean generated script; lint uses `PYTHONPATH=.../DeviceSkrips` import smoke.
- Phase C/D end-to-end: configure a real testbox profile, `/check`, run a generated script, watch parsed PASS/FAIL, exercise the fix loop to Final Validation.

## 7. Risks / open issues

- Framework absent on dev mount → lint via `DeviceSkrips` copy; execution only testable against a real box.
- Testbox sudo assumed passwordless (probed by `/check`); piping sudo passwords is a security downgrade — a profile requirement, not a feature.
- LLM context: never send full index; slim → top-40 → loc slices. Generation prompts may exceed llm.py's 180s hardcoded timeouts (`llm.py:131,186`) — add a backward-compatible `timeout` param.
- py2/legacy scripts break `ast.parse` → regex fallback, still searchable.
- Thread-based runs die on server restart → persisted per-stage status, marked stale on `load_case`.
- Generated-file suite numbering vs testsuites_art conventions resolved at manual promotion; step-4 fit decision recorded in provenance as the suggestion.

### Critical files
- `copilot/Test-cases/ask-ck/CK-main/CK_server/routers/pytest_create.py` (rewrite)
- `copilot/Test-cases/ask-ck/CK-main/CK_server/routers/wizard.py` (mirror: 115-149, 291-409, 740, 1165+, 1348+)
- `copilot/Test-cases/ask-ck/CK-main/CK_server/{llm.py, models.py, data.py, paths.py}` (small additions)
- `copilot/Test-cases/ask-ck/CK-main/CK_server/pt_exec.py` (new)
- `copilot/Test-cases/ask-ck/CK-main/CK_server/templates/prompts/pt_*.jinja` + `enrich_script_index.jinja` (new)
- `copilot/Test-cases/ask-ck/CK-main/CK_server/static/index.html` (~1325, ~2627-2700)
- `copilot/Test-cases/tool/build_script_index.py` (new)
