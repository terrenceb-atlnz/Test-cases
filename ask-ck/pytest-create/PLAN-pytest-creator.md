# PyTest Creator — Implementation Plan & Progress Tracker

> Living tracker for the PyTest Creator build-out. Update the checklist and Progress Log
> as milestones land (same convention as `ck-facelift/PLAN-facelift.md`).
> Approved: 2026-07-14.
>
> **Data-layer note (2026-07-20)**: the script-index build described here
> (`build_script_index.py` → `scripts_index.json` / `scripts_slim_index.json` /
> `scripts_sources.jsonl` / `framework_surface.json` / `scripts_index_enrich.jsonl`) is now
> **provenance-only**. Those files have been **deleted**; the script index, literal source code,
> code chunks, and framework surface all live in **`ask-ck/var/ck.db`** (permanent single source of
> truth). The running PyTest Creator reads only the DB via `db.py` (`db.search_scripts`,
> `db.search_code`, `db.get_json_doc("framework_surface")`). Rebuild instructions below are historical.
>
> **Objective-in-Generate note (2026-07-29)**: the Generate step now bakes the refined objective
> into the skeleton as a `# ==== OBJECTIVE ====` header (rides into both the emitted `.py` and the
> Generate prompt via the embedded skeleton), and generate-prompt rule 1a grounds each verdict in
> the objective slice its step covers. Validated by a 5-model matrix + opus/vllm-fast judging
> (`tool/pt_matrix_judge.py`): T33233/T33235 → "good". The next generation bottleneck is
> **sequence-step `kind` misclassification** (T33234), tracked in
> `ck-facelift/PLAN-permutation-expander.md`.
>
> **Generation note (2026-07-21)**: Step 6 (Generate) no longer composes a script freely from a
> style exemplar — it **fills a standardized skeleton** (`templates/pt_script_template.py.jinja`)
> rendered from the reviewed sequence (one `TestCase` per verification step, mandatory logging
> contract, suite + per-case `tear_down`, data-driven topology), and the lint enforces template +
> logging-contract conformance. All fragment **source code comes from `ck.db`** (`db.get_script_source`);
> the old script mount is retired (guarded). The testbox framework dir is **read-only** (guarded).
> Design + status live in the separate testing plan **`PLAN-pytest-testing.md`** (Part 1 done; Parts
> 2–3 pending) with `TEMPLATE-SPEC.md` + `LOGGING-CONTRACT.md`; this tracker's Step-6 body below
> describes the original free-compose approach (historical).

> **Per-step flow completed its own gates (2026-08-31)**: the 2026-08-26 move to a
> per-sequence-step Script Search left three server-side assumptions behind, each found by
> driving a real case (`AWPTCM-T33351`) rather than by the suite. `confirm_step` still
> demanded `step3.provenance` or `step3.matches` — neither of which the per-step picker
> writes — so step 3 could not be confirmed and step 4 was unreachable; step 3 stored no
> provenance at all, so its panel was permanently blank; and its provenance mount was still
> the last frontend reference to the retired whole-case `/suggest_scripts`. All three closed.
> `confirm_step` now also accepts `step_matches` or `selections`; `suggest_scripts_step`
> records `{llm, prompt, response, step_n}` (one slot — the payload is a permanent `ck.db`
> row); the panel targets `/suggest_scripts_step/{key}/{n}`, resolved at click time.
> Step 6 gained `POST /save_naming/{key}` so the Group / script-name fields persist before a
> first successful generation, and `_group_display` now sanitises to `_GROUP_RX` — it had been
> handing the UI a default the server's own validator rejected. **Every session in `ck.db`
> predating 2026-08-26 still carries `matches`, which is why the suite stayed green through
> all of it**: a corpus of old sessions is not coverage of a new flow.

> **Flow revision (2026-07-23)**: the visible flow is now **7 steps, not 8** — the former
> **Step 4 (Fit Decision) was removed** (the fixed skeleton makes reuse/extend/new moot). Internal
> `stepN` session keys are UNCHANGED (fragments still `step5`, generate `step6`, etc.); only the
> sidebar numbers shifted. Script Search + Fragments are now **per-step carousels**; Cases split
> into Open/Partial + Complete. The Sequence extractor classifies each step **setup/verify/physical/
> manual**, and Generate emits an **operator-prompt + wait-for-state-change** pattern for physical
> steps (SVT 3009) and `yesNo()` for manual — physical steps are in scope. Provenance re-stamping was
> fixed to remap original-step → `TestCase_<n>` class number (a setup-drop divergence bug).
> The Step-6 checklist items below predate these changes; treat them as historical where they conflict.
>
> **Fragment resolver + Py2 (2026-07-27, D1/D3 — the follow-ups formerly in the now-deleted
> `NEXT_SESSION_DECISIONS.md`, resolved)**: `_resolve_symbol_code` now bounds symbols by exact
> index `loc` (`_resolve_end`: `loc[1]` → next-unit-start−1 → `loc_total`), replacing a blind
> `loc[0]+60` that mis-captured ~18% of legacy `test_case` entries; helpers resolve by real `loc`.
> Py2 legacy fragments are deterministically modernized via stdlib `lib2to3` at resolve time
> (`_translate_py2`; `translated` ⇒ guaranteed valid Py3 via `expandtabs(8)` + `ast` self-verify;
> untranslatable ships as-is with a ⚠ banner + a conditional Generate-prompt steer; provenance
> gets a `(py2→py3)` suffix). D2 (per-step fragment cap) resolved as **keep no cap**. Rationale in
> memory `d1-fragment-resolver-boundaries` / `d3-py2-fragment-translation`; details in SERVER-README
> Step-4 and PROGRESS 2026-07-27.
>
> **Hardware-informed corrections (2026-07-28d, from a live 8-member x950 stack)**: the rule
> that *"the FIRST index of `portA.B.C` is the chassis/slot"* was **wrong** and is corrected
> wherever it appeared (generate prompt, the port-hardcode lint's comment, the grounding
> test's docstring) — **A is the STACK MEMBER**, B is the bay (0 = base board, 1+ = a
> populated expansion slot). Step-5 Lint gained two warnings for hazards only visible on real
> hardware: `interface eth0` under config (eth0 is the out-of-band management port —
> `Vlan: none`, in no VLAN — yet appears in `show interface status` as an ordinary connected
> row), and enumerate-then-configure with no `stackport` exclusion (stack links appear in
> that table with `stackport` in the Vlan column, so such a loop can split the stack
> mid-run). A prose-based stack detector was built and **reverted**: the `.setup` file
> already DECLARES stack membership, stackports and cabling — see `SETUP-FILE-REFERENCE.md`.
> Parsing `.setup` (nothing in `CK_server` does) is the outstanding follow-up.

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
5. **Server-side setup templates — designed 2026-09-01, not built. See §8.** Storage decided
   (shared committed + personal gitignored), `[misc]` profile claims mandatory, run wiring is
   a one-branch change because `_run` already SFTPs arbitrary files. Four open questions in §8.8.
6. **Chunked generation + holistic final pass — designed 2026-09-01, not built. See §9.**
   Terrence's ask after a Generate timeout. **§9.3 is the section to read**: duration is bought
   with OUTPUT tokens (corr +0.995 over 44 generations, 11.0 s per 1k on claude), so step count
   — one `TestCase` per verify step — is what drives it, and a 30-step case projects to
   541-1,316s against a 1800s ceiling two real runs have already reached 77% and 88% of. It is
   also permanently a 2-4 assistant-message reply (32k output tokens per message), which is an
   argument for deliberate seams that does not depend on the timeout at all. §9.2 retires the
   stale "output ceiling" argument (refuted 2026-08-03). §9.8 has the build order: Pass C
   first, chunking after.

## Script index status (as of 2026-07-15) — COMPLETE

- **Index: 830 scripts, 100% enriched** (art 239, svt 77, legacy 514). Final composition after excluding a nested vendored SQLAlchemy copy (235 files) found bundled inside `legacy/tools/memory_leak_tools/` — added `"sqlalchemy"` to `EXCLUDES` (7 genuine memory-leak tooling files in that dir remain indexed). Also earlier widened the legacy filter to include numeric suite dirs (e.g. `5003_feature_limits`) and excluded `a1c_playwright` (Playwright web-UI tests, not framework scripts).
- **Enrichment completed across 3 resumed runs** (150 → 370 → 930 → 1000 → 830 after the vendor exclusion), hit and recovered from one Claude seat 429 rate limit mid-way; fully resumable via the sha1-keyed jsonl, zero data loss.
- **Verified the fix works**: mechanical scoring for the MDI/MDIX case now returns **art: 13, svt: 11, legacy: 25** matches (was 0/0/10 before enrichment) — confirms the "art/svt score zero" symptom is resolved.
- To rebuild later (e.g. after script repos change): `cd tool && ./build_script_index.py --mechanical-only` then `./enrich_script_index.py --limit 2000` (only re-enriches new/changed files, sha1-keyed) then `./build_script_index.py` to merge.

## Progress Log

- **2026-09-01b** — **Generate's 600s wall closed, and the generated script's STYLE is now
  checked at all** (`eb1f66d`). Terrence hit a Generate timeout and offered three fixes; two
  shipped, the third is specified in §9 and deliberately not built.
  - **The timeout was one transport's wall, not a global one.** `claude_agent` — the
    workspace default — was the only backend where a caller's `timeout` was a whole-response
    wall clock: `claude_code`/`grok_cli` are floored to 1800s by `_cli_timeout`, and
    `local_llm` streams, so its number bounds the inter-chunk gap. The same `timeout=600`
    therefore meant "30 minutes", "no total limit", and "hard kill", depending on the radio
    button. `_call_claude_agent` now floors through the same helper, before `registry.submit`
    (submit's value is what the browser hands its local ck-agent, so flooring after it would
    desynchronise the two ends — the 2026-08-27 defect, `3224629`). The 2026-08-03 exemption
    was retired on evidence: its stated reason, that the job timeout bounds the agent-bridge
    long-poll, is false — `next_job` bounds itself by its own `wait` (25s, capped at 55s) —
    and that fact is now pinned so the exemption cannot return on the same reasoning.
  - **Two measurements, and the second corrected the first.** Prompt size does not track step
    count (T33234 is 20 steps / 72 KB, T33233 is 11 steps / 130 KB; fragments are 38-56% with
    **zero** byte-duplicate bodies) — but Terrence pushed back that a 10-step case still took
    minutes, and he was right that this missed the point. **Duration is bought with OUTPUT
    tokens: corr +0.995 across all 44 recorded generations, against +0.829 for input, and
    `in=177,126 -> 326s` versus `in=94,342 -> 666s` settles it directly.** The rate is a tight
    constant — 11.0 s per 1k output tokens on claude, 5.8 on vLLM — and output is one
    `TestCase` per verify step, so **step count IS the driver**. Corrected in §9.3; the
    input-cost objection to chunking is withdrawn in §9.4, since input buys money, not
    seconds.
  - **PEP 8, which nothing had ever checked.** `_lint_generated` was entirely about whether
    the artefact WORKS. pycodestyle (reference implementation, pure Python, offline) at 120
    chars — measured: 732 of the 3,121 lines in `generated/` exceed 79 and 171 exceed 120, so
    79 would emit ~120 findings on a healthy script and 120 emits 21, all genuinely
    unreadable. Findings are WARNINGS, never blocking (whitespace must not need a policy
    override); a missing pycodestyle reports "style NOT checked" rather than an empty list.
    Declared in `requirements.txt`, not `-dev`: the SERVER lints.


- **2026-09-01** — **Server-side setup templates SPECIFIED (§8), not built.** Terrence's ask:
  keep several templated `.setup` files on the CK server and choose which one loads onto a
  designated testbox, rather than one file per box edited in place. Found that the plan
  already specified this half — §2 says the run SFTPs the chosen setup as *"remote path from
  profile or UI-uploaded content"* — and that `RunManager._run` already SFTPs any
  `{filename: code}` entry into the guarded workdir, so the transport needs no change. Three
  decisions taken: storage is BOTH a committed `ask-ck/pytest-create/setups/` and a personal
  `ask-ck/var/setups/` (already gitignored, no `.gitignore` edit); every template must carry
  its `[misc]` profile claims so `pt_profiles`/`pt_preflight` can answer "which template fits
  this case" and "will this script bind" offline; and the design lands in writing before code.
  Recorded the boundary that matters: this is RUN-time only — generation must still never read
  a bench file.

- **2026-08-26** — **Step-3 results became durable and context-bearing.** Per-step LLM
  suggestions persist (`step3.step_matches`, merge-by-id/newest-wins) and chosen rows carry
  whitelisted record snapshots (`step3.records`) — previously only the whole-case suggest
  persisted, and once its button left the UI a reload lost all candidates and degraded chosen
  rows to `other`/`?`. New **"Suggest all steps (LLM)"** in the coverage bar: the per-step
  suggest for every step, sequentially (never the retired whole-case prompt), persisting per
  step, with a true in-flight Stop. The step-3 coverage/why verdicts now reach the
  `pt_gather_fragments` prompt per script ("chosen for sequence step N — coverage — why");
  fragment `why` already reached Generate, closing the review-context chain. Per-step LLM
  errors are now loud 502s (were silent `matches: []`). Suggest does NOT unconfirm step 3 or
  invalidate fragments — candidates are not selections. **Confirmed on a real
  case the same afternoon** ("suggest-all works, info stays retained"); the per-step Suggest
  button removal is now **deferred at Terrence's direction** ("we can remove the button
  later") — UI-only when it happens; the endpoint stays.
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
- **Patterns to mirror:** wizard session persistence (`_persist_session`/`_load_persisted`),
  confirm gates (`confirm_step`), suggest flow (`suggest_*` endpoints), complete-case
  resolution (`_refined_complete_keys`). For mechanical scoring mirror **`db.search_*` +
  `db._relevance_score`**, NOT the wizard — its private `_score_zephyr_candidate` was deleted
  in `4578030` (see *Matching/scoring* below). LLM CLI invocation in `llm.py` (`render_prompt`,
  `_call_llm_with_meta`; hardcoded 180s subprocess timeouts). Secrets convention: `.gitignore`
  ignores `secrets.*`; loader precedent `tool/upload_refined.py::_find_secrets_file()`.
  paramiko 2.9.3 is installed.
  > ⚠ **CORRECTED 2026-08-03:** that sentence was a fact about ONE machine, not a declaration —
  > `paramiko` was in **no requirements file**, so on any fresh venv the whole "6. Run" step was
  > dead. Because `import paramiko` sits inside `pt_exec._connect()`, the profile probe answered
  > `"SSH connection failed: No module named 'paramiko'"`, which reads as a testbox/network
  > fault. Now declared in `requirements.txt`, and `tests/test_dependencies_declared.py` asserts
  > every third-party import in `CK_server/` is declared so the next one cannot hide this way.
  > Line numbers were deliberately dropped here (2026-07-28): they were labelled "verified"
  > but had drifted, and `wizard.py` shrank ~170 lines in `4578030`. Grep the symbol — a stale
  > line ref is worse than none, because it reads as authoritative.

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
Two-stage: mechanical scoring first, LLM on a bounded top-40.

> **UPDATED 2026-07-28 (`4578030`) — do NOT copy the wizard's old bespoke scorer.**
> This section used to say "adapt `_zephyr_tokens`/`_specific_tokens`/`_score_zephyr_candidate`
> (wizard.py:298-409)". **`_score_zephyr_candidate` no longer exists.** It was deleted: it
> hand-rolled a 45k-row full-corpus Python scan that cost a measured 2.7 s bare on the event
> loop, and its output was ~81 % score-ties broken alphabetically by title. `db.search_zephyr`
> already did the same job via FTS + the shared `db._relevance_score`.
>
> **Mirror `db.search_*` + `db._relevance_score` instead** (`db.py:143`), which is the single
> source of truth for keyword relevance across all four corpora and is FTS-backed. If PyTest
> matching needs a domain heuristic the shared scorer lacks, add it there as an **opt-in
> parameter** — the pattern `area_words` established (`db.py:143`, defaults to `()`, only
> `search_zephyr` opts in, so other callers are provably unchanged). Never fork a private
> scorer into a router; that fork is exactly what was just removed.
>
> Two hard-won lessons worth inheriting: (1) a binary specific/generic stoplist cannot express
> "too common to rank on, but still real area signal" — for a case titled "Port - Auto
> Negotiation", stripping "port"/"auto" left a single token and an arbitrary result order;
> (2) don't pre-filter the query before handing it to `db.search_*` — it does its own
> specific/generic split and needs the raw words. The rule: **the caller decides which TEXT is
> relevant, `db` decides how to WEIGHT it.**

Still applicable: tokenize sequence actions + title; weight feature_tags 12/token, suite_dir
leaf 10, summary+title substring 6; require one specific signal; `_PT_GENERIC_TOKENS` stoplist
("test", "verify", "check", "switch", "port"…) — noting that a stoplist alone has the
single-token failure mode described above.

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

---

## 8. Server-side setup templates — DESIGN, NOT BUILT (specified 2026-09-01)

**Status: design agreed with Terrence 2026-09-01, no code written.** Three decisions were
taken before drafting and are settled: templates live in **both** a shared committed folder
and a personal local one; every template **must** declare its topology-profile claims; and
the design is written down before anything is built.

### 8.1 The problem

Today a run's `.setup` is a **path on the testbox**, chosen from `profile["setups"]`. Three
consequences:

1. **A bench file is shared mutable state, and it is being mutated.** `tb470` carries
   `tb470.setup.bak-2026-07-29`, `.bak-2026-07-30` and `.bak-2026-08-31` — three in-place
   rewrites of one file that 480 other setups sit beside in
   `/home/st-art/st-art/configs/`. Two people cannot run different topologies against the
   same bench at the same time, and a rewrite is invisible to anyone who did not make it.
2. **One file per box cannot express several test topologies.** The realistic automation
   shape is a handful of *templates* — a stacked pair, an unstacked copper pair, a fibre
   pair, a tb-linked single — which between them cover the whole suite. That does not fit
   "the box has a `.setup`".
3. **It was always meant to work the other way.** §2 of this plan (`Remote execution`)
   specifies the run as SFTP putting the script, library and chosen `.setup` — *"remote path
   from profile **or UI-uploaded content**"*. Only the remote-path half was built.

### 8.2 What this is NOT

- **Not overwriting `tb470.setup` on the box.** The chosen template is uploaded into the
  per-run workdir and `-s` points at it there. Identical effect, no shared-state mutation,
  concurrent runs with different topologies, and each run records which template it used.
- **Not a generation input.** `TOPOLOGY-PROFILES.md` is emphatic: generation targets a
  **profile** and must never read a bench file, because a test silently weakened to fit the
  hardware in front of it still goes green and the false green is unfalsifiable from
  outside. This facility is **run-time only**. Nothing in steps 2–5 may read a template.
- **Not a `ck.db` change.** `ck.db` is the permanent, non-rebuildable source of truth; an
  in-place schema addition was explicitly rejected once already (`case_locks`, see
  `auth-and-case-locking-plan`). Templates are files.

### 8.3 Storage — two locations, both plain files

| Origin | Path | Tracked? |
|---|---|---|
| **shared** | `ask-ck/pytest-create/setups/<name>.setup` | committed — diffable, reviewable, travels with the tool |
| **personal** | `ask-ck/var/setups/<name>.setup` | already gitignored by the existing `ask-ck/var/*` rule — **no `.gitignore` change needed** |

- A template is identified by `(origin, name)`, never by name alone, so a personal
  `ie520-pair` and a shared `ie520-pair` are two distinct entries and neither shadows the
  other. The picker labels origin; the run record stores both.
- Names follow the existing profile-name rule (`^[A-Za-z0-9][A-Za-z0-9_\-\. ]{0,40}$`) so a
  name can never escape its directory. The uploaded filename is `<name>.setup`.
- **No "default".** Same ruling as the testbox `setups` map (2026-09-01): on a shared server
  a default lets whoever saved last choose for everyone.

### 8.4 Every template declares its profile claims

A template carries the `[misc]` block `TOPOLOGY-PROFILES.md` §"What a bench writes" defines:

```ini
[misc]
ck_profile     = base, fibre        ; comma list
ck_role_dut    = swi_a
ck_link_copper = swi_a-swi_b:port1.0.1
ck_cap_swi_b   = polarity           ; HARDWARE-VERIFIED, never doc-derived
```

This is what makes a *set* of templates checkable rather than aspirational, and it is where
the value is:

- `pt_profiles.check_profile(bench, name)` answers **"which of my templates can run this
  case?"** — and the useful inverse, **"which profiles does nothing I have implement?"**,
  which is the shopping list for the next bench build.
- `pt_preflight.parse_script(code)` + `check(script, bench)` answers **"will this generated
  script actually bind on this template?"** — the guard against `init_portlink` returning
  `(None, None)` silently and a cabling gap reading as a script defect.

Both are **pure and text-based** (`Bench.from_text`, `parse_script(text)`), so the whole
match runs server-side against stored template text and the generated code, with **no
hardware, no network and no LLM**. A template with no `[misc]` claims is still storable and
runnable, but is listed as *"claims nothing — cannot be matched"* rather than silently
treated as compatible.

### 8.5 API sketch

All under the existing `/api/pytest-create` prefix. None of these touch `ck.db`.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/setups` | list `{origin, name, claims, problems, updated_at}` for both locations |
| `GET` | `/setups/{origin}/{name}` | full text, for the editor |
| `POST` | `/setups/{origin}/{name}` | create/replace; parses before writing and **refuses** a file `Bench.from_text` cannot read |
| `DELETE` | `/setups/{origin}/{name}` | remove |
| `POST` | `/setups/{origin}/{name}/match/{case_key}` | profile match + `pt_preflight` against that case's generated script |
| `POST` | `/setups/{origin}/{name}/verify` | compare the declaration against the **real bench** (see 8.7) |

### 8.6 Run wiring — the smallest part

`RunManager._run` already SFTPs every entry of `files = {filename: code}` into the workdir
and then runs `cd <workdir> && … -s <setup_remote>`. So:

```python
files[f"{template_name}.setup"] = <stored template text>
setup_remote = f"{template_name}.setup"      # bare name, resolved inside the workdir
```

No change to `_run` at all. The bare filename already satisfies `run/{key}`'s explicit-path
regex `^[A-Za-z0-9_./\-]+$`, `_assert_write_allowed` already refuses a workdir under the
read-only framework, and `-s` is already `shlex.quote`d. `run/{key}` gains one branch:
`body["setup_template"] = {origin, name}` alongside today's `setup` (profile key or remote
path). **The remote-path route stays** — a bench file that genuinely lives on the box is
still legitimate.

The run record must store which template ran, and its **text hash**, so a result can be
traced to the exact topology it was produced on after the template is edited.

### 8.7 Verify against the real bench — the rot guard

A `.setup` is a *declaration about cabling*, and declarations rot: on tb105, 2026-07-29,
only **3 of 8** declared consoles were correct and one device did not exist
(`TESTBOX-ACCESS.md` §2). Templates make it cheap to spread one stale topology to four
boxes instead of one, so `verify` is not optional polish:

- SSH to the designated box and sweep `/dev/u*` for login banners, matching declared
  `[switch]` consoles against the units actually on them (the banner is the reliable
  identifier; the prompt is not, since every VCStack member serves the stack-wide CLI).
- Report per-device agree/disagree. **Never rewrite the template from the bench** — that
  would be inferring topology from hardware, the mistake `SETUP-FILE-REFERENCE.md` records
  having been made twice.
- `ck_cap_*` stays hardware-verified and human-entered: absence from `ck.db`'s CLI reference
  means UNKNOWN, never unsupported.

### 8.8 Open questions

1. **Editor or upload?** A textarea with parse-on-save is the smaller build and keeps
   templates reviewable; file upload is friendlier for a 5 KB file someone already has.
2. **Does a template pin a testbox?** A template naming `/dev/u4` is bench-specific in
   practice even though nothing declares it. Options: a free `applies_to` hint, a hard
   binding, or nothing and let `verify` catch it.
3. **Where does the picker live?** Run panel only (consistent with "no default"), or also a
   per-case remembered choice on the session.
4. **Promotion.** Is a personal template ever promoted to shared, and by whom?

### 8.9 Invariants this must not break

- `ck.db` unchanged — templates are files, never rows.
- `/home/st-art/framework` read-only; the workdir guard already covers the upload target.
- Generation never reads a bench file (8.2).
- Tests/smoke must not write the permanent `ck.db` — template work is filesystem-only, so a
  test needs `tmp_path`, not the scratch server.

---

## 9. Chunked generation + a holistic final pass — **BUILT 2026-09-02**

**Status: BUILT 2026-09-02** — per-unit generation, batch dispatch, no-LLM assembly and
Pass C all shipped; §9.5's Pass A was deliberately NOT built (the frame is rendered, not
generated). The paragraph below is the ask as it stood on 2026-09-01 and is kept as the
record of why this was built; §9.8 carries the sequencing that was actually followed and
§9.10 what remains unmeasured.

> *Status at the time: Terrence's ask, 2026-09-01. No code written. Read §9.8 before building
> any of it — the change that shipped the same day may remove most of the motivation, and
> that is measurable rather than arguable.*

### 9.1 The ask

> *"Split the prompt into a few sections, return each one individually, combine them as a
> final result, then have a final prompt sent to do a holistic check-over of that completed
> 'script' to ensure it passes lint and PEP 8 or whatever current python best-practice
> exists, as well as sanity check each step to ensure they make sense."*

Given alongside two others: review the prompt for bloat, and raise the timeout to 30 minutes.
Both of those shipped in `eb1f66d`. This one did not, because it is a change to the shape of
generation rather than to a number, and because the measurements below move its premise.

### 9.2 One stale motivation to retire first

Chunked generation already exists in this repo's history as the recommended fix for a *"hard
output ceiling of ~15 TestCase classes"* — see `FINDINGS-generation-size-ceiling.md` and
`PLAN-pytest-testing.md` §"chunked generation removes the ceiling but is real work".

**That premise was refuted on 2026-08-03 and the document carries the refutation in its own
header.** The measurements were `_parse_generated_blocks`' output, not the model's: the CLI
splits a long answer across assistant messages that each re-open a ```` ```python ```` fence,
and the old non-greedy regex stopped at the *continuation's* opening fence. On the five stored
replies it kept 21 of 40 classes, 16/17, 9/11, 6/6 and 0/6 — and every reply was complete,
each ending in `ts.run(sys.argv)`. `gen_assembly.recover_script` now reassembles them.

So **chunking would not be lifting a model ceiling; there isn't one.** Anyone who builds this
citing the ceiling is citing a retracted finding. The live motivations are different and
narrower, and they are the ones to hold it to:

1. **Wall clock per call.** A 30-minute single call is a 30-minute single point of failure.
2. **Partial progress.** Today a generation that dies at minute 12 yields nothing.
3. **Review quality.** A model asked for one 35 KB artefact reasons about each step less than
   one asked for four steps at a time. This is the least measured and possibly the largest.

### 9.3 What actually costs the wall clock — measured, and NOT what this section first claimed

**Corrected 2026-09-01 after Terrence pushed back.** The first version measured what drives
PROMPT size and reported that step count does not track it. That is true, and it is beside the
point: **prompt size is not what the timeout is made of.**

Across all 44 generations in `debug-log/` carrying token accounting:

| | correlation with duration |
|---|---|
| **output tokens** | **+0.995** |
| input tokens | +0.829 (confounded — a big case has more of both) |

The direct disproof of the input story is in the data: `in=177,126 -> 326s` against
`in=94,342 -> 666s`. Input nearly doubled while duration halved, because output moved the other
way (34,966 vs 57,188). Wall clock is bought with output tokens and almost nothing else.

**The rate is a tight per-backend constant:**

| backend | s per 1k output tokens | n | range |
|---|---|---|---|
| `local_llm` (vLLM) | **5.8** | 34 | 5.7-6.4 |
| `claude_code` / `claude_agent` | **11.0** | 10 | 9.2-11.7 |

Output is the script, and the script is **one `TestCase` class per non-setup sequence step**.
So **step count IS the driver of duration** — Terrence's original premise. Measured output per
verify step on claude: 2,048 (T33233), 3,221-4,274 (T33351), and 5,828-16,825 across repeated
regenerations of T44297, where the spread is model verbosity on one fixed case rather than
anything about its size.

**Projection for a 30-step case** (~24-28 verify steps) at 11.0 s/k-token:

| verbosity | 24 verify steps | 28 verify steps |
|---|---|---|
| lean (2,048 tok/step) | 49,152 tok, **2 msgs**, 541s | 57,344 tok, 2 msgs, 631s |
| mid (3,221) | 77,304 tok, **3 msgs**, 850s | 90,188 tok, 3 msgs, 992s |
| rich (4,274) | 102,576 tok, **4 msgs**, 1,128s | 119,672 tok, 4 msgs, **1,316s** |

Under the new 1800s ceiling — but the rich end is 73% of it, and two real generations already
on record sit at **77% and 88%** (132,127 tok / 1,395s; 138,619 tok / 1,576s). A 30-step case
is not comfortably inside the budget; it is inside it by a margin that model verbosity alone
can eat.

**And every one of those rows is a multi-message reply.** One assistant message carries 32,000
output tokens and that cap is not raisable; beyond it the CLI continues into further messages
that `gen_assembly` must stitch. So a 30-step case lives permanently in the 2-4 message regime
— exactly where `_recovery_failure`, `_resolve_duplicates` and seam-line loss live. **That is a
second argument for chunking, independent of the timeout: deliberate chunks around a known
frame are easier to reassemble correctly than accidental ones split mid-token by an output
cap.**

**Still true from the first version, and still useful — just not a timeout fix.** Prompt
composition is fragments 38-56%, skeleton 21-29%, static rules 10-17%; there is **zero**
byte-duplicate fragment content; and T33233 carries nine near-clone `TestCase_N` blocks from
four sibling scripts. That remains the cheapest available prompt reduction and it is a step 3-4
selection question. It just buys tokens and money, not seconds.

### 9.4 The cost side — real, but it is money, not time

**Corrected 2026-09-01 alongside §9.3.** The first version argued chunking "makes the prompt
problem worse in aggregate", because the skeleton, the ~14 KB rules block and the framework
surface must be re-sent with every chunk. The re-sending is real; the conclusion was wrong,
because it priced input in seconds.

Input costs almost no wall clock. The largest run on record sent **4,170,363 input tokens** and
took 1,576s — a duration fully explained by its 138,619 output tokens at the 11.0 s/k rate. So
paying for the shared context N times costs **tokens and money, not the thing that is timing
out**.

- **Money.** At K=4, roughly 3 extra copies of ~40 KB of shared context. Against measured
  per-generation costs of $1.25 (T33351) that is a modest multiple, not an order.
- **Wall clock.** Total output is roughly conserved — the same script gets written either way —
  so total time should be roughly flat plus per-call overhead. What changes is that no single
  call carries all of it, and a failure costs one chunk instead of everything.
- **Fragments do not multiply at all.** Each declares `maps_to`, so a chunk covering steps 5-8
  needs only the fragments serving those steps. On T33233 that is the 56% of the prompt, split
  rather than copied.

The genuine costs of chunking are elsewhere and are not about size: cross-chunk incoherence
(§9.6), keeping a frame later chunks cannot contradict (§9.5), and chain-level Stop (§9.7).

### 9.5 Where to cut — the manifest is already the seam — **BUILT 2026-09-02, WITHOUT Pass A**

> **2026-09-04 — setup-unit re-indent at assembly, and a reachable Fix.** The `setup` unit is
> the only unit that is a class-body fragment (a `TestSet` method pair at indent 4), not a
> top-level class, so the model consistently flush-lefts a `def` and the byte-exact splice made
> an `IndentationError` that failed lint + `manifest_check`. `_assemble_units` now re-indents the
> setup pair to the frame slot (`_reindent_setup_pair`/`_setup_slot_indents`: def→4, body→8
> independently, idempotent); TestCase units are still verbatim. Separately, the **Fix** loop
> (§9.6) is now reachable from the Summary/Generate step (`ptFixFromSummary`), not only step 7 —
> a blocking lint error bars Confirm with no override, so an unparseable script was otherwise
> deadlocked. See `CHANGELOG.md` 2026-09-04 and memory `setup-unit-reindent-at-assembly`.

The machinery a chunked generation needs mostly exists, because reassembling a multi-part
reply is the same problem as assembling deliberate chunks:

- `gen_assembly.split_fenced_parts` / `stitch_parts` / `_resolve_duplicates` — joining parts,
  including dropping partial lines at seams and refusing two comparable definitions of one
  name (`_DUPLICATE_OBVIOUS_FACTOR`).
- `gen_assembly.manifest_check` — reads `ts.add_testCase(...)` from the **AST** and reports
  registered-but-undefined and defined-without-`main()`. This is *"the one completeness signal
  in the artefact that does not come from the parser."*
- `_recovery_failure` — the refusal that keeps an incompletely assembled script from being
  stamped, linted and persisted.

That suggests the natural shape:

- **Pass A — the frame.** Imports, the `TestSet` class with `init()`, shared helpers
  (including `_ck_bind_link`), **the full `ts.add_testCase(...)` manifest for every step**, and
  the `__main__` runner. No `TestCase` bodies. Small, fast, and it fixes device names and
  helper signatures once so later chunks cannot disagree about them.
- **Pass B(i) — TestCase bodies, K steps at a time.** Given the frame verbatim, the sequence
  rows for those steps, only the fragments whose `maps_to` covers them, and only the
  `cli_reference` entries for their commands. Emits `class TestCase_N` definitions only.
- **Assembly.** Frame + all B outputs through the existing `stitch_parts` /
  `_resolve_duplicates` path, then `manifest_check` against Pass A's manifest. **Pass A's
  manifest becomes a contract written before the bodies exist**, which is strictly stronger
  than today's check of a manifest the same reply wrote.
- **Pass C — the holistic review.** See §9.6.

### 9.6 The final pass — two halves, and only one of them needs an LLM — **BUILT 2026-09-02**

Terrence's final pass names two jobs. They are not the same job and should not be one prompt.

**The lint/PEP 8 half is mechanical and now fully exists.** `_lint_generated` runs
`py_compile`, the structural and contract assertions, the objective-coverage check, and — as
of `eb1f66d` — **pycodestyle at 120 characters**. Asking a model to *"ensure it passes lint"*
is asking it to approximate a checker that is already deterministic, offline and free. The
right wiring is: run the existing lint on the assembled script, and feed **its findings** to
the model, rather than asking the model to find them.

**The "does each step make sense" half is the real LLM job, and nothing checks it today.**
Specifically the failures that chunking itself introduces, which no existing check would see:

- a helper used in chunk 3 with a signature chunk 1 did not define;
- a device or port attribute named differently across a seam;
- two chunks independently implementing the same setup;
- a step's verdict that does not correspond to its sequence row's *verify* text — the one
  failure mode the whole pipeline exists to prevent, and the only one a human currently
  catches.

**Pass C must return FINDINGS, not a rewritten script.** A rewrite pass re-introduces the
whole-script output that chunking existed to avoid — the same 35 KB in one message, with the
same wall clock — and it can silently undo a correct reused fragment, destroying the
provenance chain PLAN §1.5 exists to keep. Findings route into the existing `fix_script` loop,
where a change is a recorded, reviewable action.

### 9.7 Invariants and existing contracts this must not break

- **`ck.db` unchanged.** Chunks are fields on the existing session payload, never new tables
  (the `case_locks` precedent — see `auth-and-case-locking-plan`).
- **Provenance stays one slot.** Step 3 taught this: N per-step payloads in a permanent
  `ck.db` row is unbounded growth, so it stores one. A 6-chunk generation must not store six
  85 KB prompts. Store Pass A's prompt in full plus a per-chunk digest (steps covered,
  fragment ids, char counts, duration), which is what a reviewer actually needs.
- **`_recovery_failure` still governs.** An assembly that fails `manifest_check` must be
  refused — but recorded first, under its own key, so refusing does not destroy the evidence
  (the 2026-08-04 defect).
- **Every `TestCase.main()` keeps its leading `# ART/SVT/legacy/AI` provenance tag** (PLAN
  §1.5), which the lint enforces per class and which a chunk boundary must not drop.
- **The objective-coverage check runs on the ASSEMBLED script**, not per chunk — it compares
  `TestCase` count against non-setup sequence steps, and per chunk it would always fail.
- **Stop must cancel the whole chain.** The live-progress/true-Stop work (2026-08-26b)
  cancels one in-flight call; a chunk chain needs a chain-level abort, or Stop will look like
  it worked while the next chunk starts. Nothing may persist from a cancelled chain.
- **Generation still never reads a bench file** (`TOPOLOGY-PROFILES.md`, and §8.2 here).

### 9.8 Sequencing — revised 2026-09-01 after the duration analysis

The first version of this section said "do not build §9 until the 1800s floor has been tried",
on the reasoning that a 2.3x headroom increase probably removes the motivation. **§9.3 weakens
that considerably.** The corrected picture:

1. **1800s probably holds for 30 steps — by a thin margin.** Projected 541-1,316s, against
   real generations already recorded at 1,395s and 1,576s. The margin is model verbosity wide,
   and verbosity is the least predictable term (measured 2.7x spread on one fixed case).
2. **The multi-message argument does not depend on the timeout at all.** A 30-step case is
   always a 2-4 message reply because of the 32,000-token per-message cap. Chunking replaces
   accidental seams — chosen by an output cap, landing mid-token — with deliberate ones around
   a stable frame. `gen_assembly` exists precisely because the accidental seams are hard, and
   its whole failure surface (`_recovery_failure`, `_resolve_duplicates`, dropped seam lines)
   shrinks when the seams are chosen.
3. **The input-cost objection is withdrawn** (§9.4). Chunking costs money, not wall clock.

So the revised sequence:

1. ~~**Re-run the 30-step case on the 1800s ceiling and record output tokens + duration.**~~
   **DONE 2026-09-01, and the tripwire did NOT trip.** AWPTCM-T44297, 31 sequence steps,
   34 selected fragments from 16 source scripts, `claude / opus / claude_agent`:

   | | |
   |---|---|
   | duration | **672.9s** (37% of the 1800s floor) |
   | tokens | 104,962 in / **58,715 out** / 163,677 total |
   | cost | $1.58 |
   | rate | **11.46 s per 1k output tokens** — against the 11.0 s/1k measured over the earlier n=44 |
   | artefact | 1,442 lines / 83,453 chars; `parts: 1`, manifest ok, lint ok, 0 blocking errors |

   Three things follow, and the first one weakens the case this section was building:

   - **672.9s is half the 1,300s tripwire**, and inside §9.3's projected 541–1,316s band. On
     the evidence available today the 1800s floor is *not* a ceiling the corpus is growing
     into. Chunking's urgency is LOWER than this section assumed when it was written.
   - **§9.3's cost model is confirmed to within 4%.** Duration is bought with output tokens,
     at ~11.5 s/1k. Any change that does not reduce OUTPUT does not reduce wall clock.
   - **39% of the output was the frame retyped.** Line-diffing the artefact against the
     rendered blank skeleton: 529 of 1,442 lines came back byte-identical to input the server
     already held (32,582 of 83,454 chars). That is the measured size of the Pass A/B prize —
     worth roughly 115s here, ~17%. Real, but not the order of magnitude the wall-clock
     framing implied. Note the measurement: an earlier guess of 68% was wrong, so use the
     diff, not intuition.

   Recorded because §9.8 step 1 asked for exactly this number and a later reader would
   otherwise re-decide from a stale premise.
2. ~~**Build Pass C first (§9.6), independently.**~~ **DONE 2026-09-02.**
   `POST /api/pytest-create/review_script/{key}` + `templates/prompts/pt_review_script.jinja`
   + a "Review (LLM)" button on the Generate panel. As specified: it returns findings and
   never a rewrite (`review_script` cannot assign `step6["files"]`, pinned by test); the
   existing lint's findings — errors AND warnings, since PEP 8 lives there — are handed IN
   as "do not re-report" rather than left to be rediscovered; findings persist to
   `step6.review` through `_pt_persist_fresh`; and `fix_script` now takes them as a THIRD
   independent reason to fix, so a reviewed script with real findings and a green lint no
   longer 409s "nothing to fix". A review never calls `_invalidate_from` — it reads the
   artefact and writes an opinion, so discarding a confirmation for having looked would be
   wrong. Tests: `tests/test_pt_review_pass.py` (21), `js-tests/pt-review-panel.spec.js` (11).
   **Not yet exercised against a real model** — the wiring is proved, the finding QUALITY is
   not, and that needs a run on a script with a known verdict/verify mismatch.
3. ~~**Then chunking**, with §9.9's open questions answered.~~ **DONE 2026-09-02.**

   **Pass A was not built, and should not be.** §9.5 proposed asking an LLM for the frame —
   imports, `TestSet` with `init()`, shared helpers, the full `ts.add_testCase(...)` manifest
   and the runner. `_render_skeleton()` already emits all of it deterministically, so Pass A
   asked a model to reproduce something exact, and to reproduce it CONSISTENTLY across N
   calls. Terrence's framing ("recompiled here into the template") removed a call and a
   failure mode. The manifest is still the contract §9.5 wanted, and more strongly: it is
   written by the renderer before any unit exists.

   **What shipped:**
   - `_skeleton_units()` splits the rendered frame into fillable units **by AST** — one per
     `TestCase_<n>`, plus `configure()`/`tear_down()` as ONE unit (a matched pair; split
     across two calls the halves disagree about what was configured). On AWPTCM-T44297:
     31 sequence steps → 1 setup + 29 TestCase units.
   - Unit ids are `setup` / `tc1`…`tcN`, **not sequence numbers** — `_split_sequence`
     renumbers, so sequence step 31 is `TestCase_29` and step-keyed chunks would mis-file
     every unit on any case with a setup step.
   - `GET /step_prompts/{key}` renders every unit's prompt without sending. Prompts are
     re-rendered, not stored (§9.7); an EDITED prompt is kept on its chunk.
   - `POST /generate_step/{key}/{unit_id}` sends the reviewer's prompt **verbatim** via new
     `llm.run_prompt_text()` — same `_call_llm_with_meta` choke point, so timing, usage and
     debug-logging are unchanged; it bypasses Jinja, not the instrumentation.
   - Replies are shape-checked **on arrival**: a TestCase unit parses, has exactly one
     class, the right class name, and a `main()`. The setup unit is checked only
     **structurally** — did both `configure()` and `tear_down()` come back (by regex) —
     because parsing a bare method pair needed a synthetic `class _P:` wrapper whose line
     numbers are unmappable to anything the reviewer sees ("line 38" of code nobody wrote).
     Its syntax/indentation is judged at the assemble step's `py_compile`, which reports real
     line numbers (2026-09-03; earlier this parsed on arrival and flagged a false indent).
     Every refusal records before raising.
   - `POST /assemble_script/{key}` splices locally, re-stamps provenance, `manifest_check`s
     and lints. **No LLM.** Splicing is back-to-front so a longer unit cannot shift the line
     ranges of units not yet spliced; round-trip against the real 781-line T44297 frame is
     byte-identical.
   - The fill rules were extracted to `pt_fill_rules.jinja`, shared by the whole-script and
     per-unit prompts. `tests/test_pt_prompt_rules_partial.py` pins the whole-script prompt
     against a verified PRE-extraction render — the extraction changed nothing.
   - **The broker is concurrent.** `agent_jobs` and `ck_agent.py` always were; `agent.js` was
     the single serial component. Now N workers (default 4, `localStorage.ckBrokerWorkers`,
     clamped 1-16), with liveness as two signals — a recent poll OR a job in flight — because
     with every worker inside a long job nobody polls.
   - UI: pills per unit (red / yellow / green) plus a Summary pill that is red until every
     unit is back and only green once assembled and lint-clean. Each unit page shows the
     returned code above and the **editable prompt** below; the button sends what is on
     screen. "Generate all" dispatches every unit at once (`Promise.allSettled`).

   **Open:** none of this has run against a real model. The wiring is proved
   (`tests/test_pt_per_unit.py` 31, `js-tests/pt-per-unit-ui.spec.js` 20,
   `tests/test_pt_prompt_rules_partial.py` 5, broker concurrency 8); per-unit output
   QUALITY, and whether 30 units beat one 673s call in wall clock, are unmeasured.

**What is NOT a reason to build it:** the "hard output ceiling of ~15 TestCase classes"
(§9.2). That finding is retracted and generations of 40+ classes are on record.

### 9.9 Open questions — ANSWERED 2026-09-02 (Terrence)

1. ~~**Chunk size K**~~ **K = 1: one call per TestCase**, plus one for the setup pair.
   Neither of the options as posed — the unit that maps onto the template's own slot
   structure is a class, so splicing is exact and retry granularity is per test case.
   Measured on T44297: 29 classes, median 42 lines / 2,465 chars, 2.7x spread.
2. ~~**Retry granularity.**~~ **No automatic retry.** A failed unit's pill stays red, an
   error naming the unit appears the moment it lands, its prompt stays on screen, and the
   reviewer re-runs it. Deliberately not a loop: a model failing deterministically on one
   awkward step would retry forever, and with an 1800s floor per call that is a long time to
   look hung.
3. ~~**Mode or the path?**~~ **The path.** Every case goes through the pills; there is no
   threshold to key on anything measured or projected. The single-call generate survives
   behind a `<details>` on the Summary page while per-unit generation is unproven on
   hardware — it writes the same `step6.files`, so it is a fallback, not a second mode.
4. ~~**Pass C mandatory or a button?**~~ **A button**, and additionally the step the Summary
   pill's green depends on: units back → yellow, assembled + lint-clean → green. So it is
   skippable but visibly not done.
5. **Still open: does the manifest become authoritative for objective-coverage?** Unchanged
   so far. `manifest_check` (registered vs defined) and the coverage check (TestCase count vs
   non-setup sequence steps) answer different questions, and folding one into the other loses
   a signal. Worth revisiting only if they ever disagree in practice.

### 9.10 What is still unmeasured

- **Per-unit output quality.** No unit has been generated by a real model.
- **Whether 30 units beat one call.** Measured fit over n=69 `claude_agent` calls:
  `duration ≈ 8.4s + 11.31s per 1k output tokens`. Sequential, 30 units is a REGRESSION
  (~600-930s vs 672.9s) because total output does not fall and each call adds ~8.4s. The win
  depends entirely on the concurrent broker, and the honest projection at 4 workers is
  roughly 8 waves — call it 200-300s — with the per-unit prompts costing more input in total
  (money, not wall clock, per §9.4).
- **The cost of pre-rendering every prompt on page load.** 30 prompts, each carrying only its
  own step's fragments; Terrence's note: "we will see what sort of impact (if any) it has on
  the ui times."
- **Whether the reviewer's editable prompt gets used**, which is the feature most likely to
  change how the whole step feels and the least predictable from here.
### 9.11 Prompt-prefix caching — MEASURED AND APPLIED 2026-09-02

> **2026-09-04 addendum — none of this cached until the transport was fixed.** The CLI's own
> harness system prompt sat in front of this prompt and varied per invocation, so the shared
> prefix measured below was never read from cache on any call (verified from the CLI
> transcripts' `cache_read_input_tokens`: 0 or a constant ~2.5k head). `llm.py` now passes
> `--system-prompt` (replacing the harness prompt), starts the CLI in a neutral cwd (the repo
> cwd was injecting both CLAUDE.md files and the memory index, ~13.5k tokens/call) and
> `--no-session-persistence`. Separately, the `device_note` deferred in §9.9 was moved out of
> the shared rules to below the line: it ended the prefix at byte 10,934, and the shared
> prefix on the 38 real prompts is now 19,447 chars (48%). Full measurement:
> `TOKEN-EFFICIENCY-REPORT-2026-09-04.md` (repo root). The 21.7 % / 11,143-char figures below
> are the 2026-09-02 state and are left as written.

Splitting one call into 30 re-sends every invariant block 30 times. Across T44297's 30 real
unit prompts (1,543,763 chars total) the input divides as **fragments 44 %, fill rules 29 %,
CLI reference 11 %** — so nearly a third of the entire spend is one paragraph, paid for
thirty times.

Prompt caching can only reuse a literal shared **prefix**, and the first ordering put the
14,794-char fill rules LAST, leaving a shared prefix of **343 characters — 0.7 %**.
`pt_generate_step.jinja` is now ordered invariant-first (intro, Case, framework surface,
devices, fill rules) with everything per-unit below the line. **Measured: 11,143 chars,
21.7 %.**

Two constraints found while doing it, both worth not rediscovering:

- **`cli_reference` is not invariant**, however much it looks it: `_cli_reference_block(
  text_rows, frags)` derives it from the unit's own step text and fragments, and T44297's 30
  blocks all differ. It must stay below the line. Putting it above halves the prefix —
  11,143 → 5,663, measured, not estimated.
- **A shared partial cannot contain a position word.** `pt_fill_rules.jinja` is included by
  both prompts, which place the CLI reference on opposite sides of it; rules 4b / 4b-ii / 5
  saying "above" was false for the per-unit caller and was the only thing forcing the
  reference into the prefix. Those three lines are now position-neutral, the whole-script
  render was diffed line by line before `tests/data/pt_generate_script_rendered.txt` was
  regenerated, and a guard test fails if a position word returns.

**Still on the table, deferred by Terrence pending real cost figures** — both would extend the
prefix toward the full 20,336 invariant chars, and both change what a unit is *told*:

- `device_note` (rules line 72) is built from THIS unit's fragments, which caps the prefix at
  11,143. Making it case-level would tell every unit about devices its own fragments never
  touch.
- Rule 4b branches on whether a CLI reference exists, which would cap a case at 6,489. It does
  not bite on T44297, where all 30 units have one. Resolving it means telling some unit to
  match a reference that is not in its prompt.

### 9.12 Token-efficiency decisions 2–8 — BUILT 2026-09-07

The 2026-09-04 investigation (`TOKEN-EFFICIENCY-REPORT-2026-09-04.md`, repo root) left eight
decisions. Terrence ordered them 6, 8, 4, 3, 5, 7, 2 and asked for one combined pass to test
them ("I can't physically afford to incrementally test every single change"). All seven landed
the same day, each as its own commit with its own test module; the first real 38-unit pass on
the result is Terrence's re-run and had not happened at the time of writing.

- **Decision 1 was done that morning** (the 38-unit pass on the fixed transport): median input
  23,278 → 16,396 tokens per unit call, cost $0.369 → $0.304, and **zero cache reads** — every
  call priced at the cache-WRITE rate. That is what exposed decision 8.
- **8 — shared half as the SYSTEM prompt.** The API matches a cache only at content-block
  boundaries; a shared prefix inside one differing user block never hits (probe: 0 read vs
  7,879 of 8,059 read as `--system-prompt`). `pt_generate_step.jinja` renders a split marker;
  the server splits there. The §9.11 constraints about `device_note` and rule 4b are resolved
  by making both flags CASE-level for this template — the shared half must be byte-identical.
- **4 — primed fan-out**, **3 — self-contained-unit rule**, **5 — shared appendix (≥ 50% of
  units)**, **7 — per-unit Fix + hard lint gate on Review**, **2 — bench-integration lint**,
  **6 — per-task model routing** (`unit_model` / `match_model` on the workspace config).
  Details, rationale and measurements: SERVER-README "Per-unit generation — token-efficiency
  changes (2026-09-07)" and `CHANGELOG.md` 2026-09-07.
- §9.6's "Pass C must return FINDINGS, not a rewritten script" still holds; the per-unit Fix
  consumes those findings and re-generates units, it does not let Review write code.
- §9.7 unchanged: chunks stay fields on the session payload; `step6.fix_units` is one more.

