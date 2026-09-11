# PLAN — Restructure the Ask-CK tree ahead of the Svelte front-end branch (2026-09-11)

> ## Status (read first)
>
> **EXECUTED 2026-09-11, batches 0–9 incl. 6b ✅ (21 commits, gate green after every sweep). `pt_media.py` stays in `ask-ck/tools/` (Terrence, §7); `upload_refined.py` and `cli_lookup.py` sit in their page directories. Also done the same day, Terrence's files: the root lab `CLAUDE.md` (two paths), the stray-script hook's message, and device-testing's `grep-shim-honors-gitignore` memory still name `tool/` / `ask-ck/var/`.** Originally IN PROGRESS from 2026-09-11 (server stopped by Terrence's go). Every decision below is
> Terrence's, taken in conversation on 2026-09-11 from a full inventory (git last-commit dates,
> live references, server anchors). §6's three questions were answered: Q-a move + symlink,
> Q-b `functions/test-composer/`, Q-c the batch-7 table as written. Batch progress is marked
> ✅ on each heading as its sweep commit lands. This file moves to `ask-ck/plans/` in
> batch 4 and is the authority for the pointer sweep that follows every batch.
>
> **Method:** one PURE-MOVE commit per batch (`git mv`, no content edits), then one SWEEP commit
> that fixes anchors and pointers, then the gate. Git records old→new for every file, so
> nothing depends on this document being complete. Archive = still tracked, under `archive/`
> mirroring the original sub-path. Delete = `git rm`; history and LFS objects remain.

## 1. Rules Terrence set

- **Usage test:** last commit ≥ 2026-08-28, or referenced by live code / a skill / CLAUDE.md.
- **A `.py` called from a page button** (UI → router → import or subprocess) lives under
  `ask-ck/frontend/ck-main/current/<page>/`. **A `.py` used by more than one page, or not called
  by any button, lives in `ask-ck/tools/`** — one central home, easy to trace.
- Page directory names: `generator` (Objective/Test Case Generator), `pytest-creator`,
  `test-composer`, `zephyr-tool`, `llm-config`, `admin`. Front-end modules shared by several
  pages go in `current/shared/`.
- Four function directories (data, results, docs) → `ask-ck/functions/<page>/` — reading **B**:
  separate from the front-end tree so Vite never watches 130 MB of runtime data.
- All plans → `ask-ck/plans/`; plans whose status header says complete → `archive/plans/`.
- `var/` → `db/`. Lowercase `frontend/ck-main`. `archive/` at the repo root.
- Delete: the 16 MB zip, the 121 MB raw extracts (LFS), the four pre-server drafting tools,
  runtime leftovers. Design-system files → archive. Svelte = Vite + Svelte 5, JavaScript.

## 2. Anchors that do NOT move (and why)

| path | reason |
|---|---|
| `ask-ck/CK-main/run.sh`, `ask-ck/CK-main/CK_server/` (code) | systemd `ask-ck.service` and `~/.local/bin/ck` hard-code them (outside the repo) |
| `ask-ck/agent/` | served live at `/setup/` from `ASKCK_ROOT/agent` |
| `.claude/` | harness slugs point at its absolute path; 12 relative symlinks assume its depth |
| `run.sh`, `setup.sh`, `COPYRIGHT`, `secrets.*`, `package.json`, lock, `vitest.config.js`, `playwright.config.js`, `pytest.ini`, `CLAUDE.md`, `README.md`, `CHANGELOG.md`, `SESSION_STATE.md` | root wrappers, bootstrap, ignored creds read by tooling, tool-convention configs, entry docs |
| `tests/*.py` (81 files) | keep depth so 57 `parents[N]` repo-root anchors survive |
| `tool/` as a directory name | **removed** — everything in it moves (see batch 6); the gate scripts go to `ask-ck/tools/` too, per Terrence: "all .py not called by a button should go to /tools/" |

## 3. The mapping

### ✅ Batch 0 — deletes (`git rm`; `.gitattributes` + `.gitignore` edited in the same commit)
- `awplus-cmdref-combined.zip` (tracked 2026-09-09 against plan decision C; corpus is in ck.db)
- `ask-ck/objective-drafting/data/` (121 MB LFS raw extracts; `paths.py` declares them retired)
- `ask-ck/pytest-create/data/scripts_sources.jsonl` (LFS; same)
- `tool/build_drafting_tool.py`, `tool/build_review_html.py`, `tool/render_batches.py`, `tool/draft_stub.py` (pre-server drafting tools, 2026-07-02)
- untracked junk: `.ck-server.log`, `.ck-server.pid`, `.ck-server-scratch.log`, `idev.log`, `.DS_Store` ×2, `tool/__pycache__`, `ask-ck/agent/__pycache__`; add `.pytest_cache/` to `.gitignore`
- `ask-ck/zephyr-tool/` is an EMPTY directory (0 tracked files) — nothing to move; the page dir is created fresh under `functions/`

### ✅ Batch 1 — `archive/` (mirrors original sub-paths)
- `archive/tool/`: `build_db.py` (the record of how ck.db was built — stays cited as history), `build_candidates.py`, `build_refined_viewer.py`, `extract_testlink.py`, `extract_zephyr.py`, `extract_zephyr_xml.py`, `pt_compare_runs.py`, `pt_measure_expansion.py`
- `archive/pytest-create/{autopilot,comparison,judging}/` — result records of tooling retired 2026-09-11 (last real change 2026-07-29)
- `archive/records/`: `pytest-create/ADVERSARIAL-REVIEW-BACKLOG.md`, `NEXT-SESSION-REVIEW.md`, `FINDINGS-generation-size-ceiling.md`, `FINDINGS-step3-gate-and-fragments-timeout.md`; `objective-drafting/BoS-prompt.md`, `EoS-prompt.md`, `ENRICHMENT_QUALITY_ANALYSIS.md`, `VALIDATION_RESULTS.md`, `PLAN-server-backed.md`; `ck-facelift/SURVEY-step4-step5.md`
- `archive/CK-main/`: `index.html` (4.5 MB pre-server single-file app, 2026-07-13, nothing serves it), `nginx-drafting-server.conf.example`, `CK_server/nginx.conf.example`, `sample-session-T33234.json`, `design-tokens.css`, `STYLE-GUIDELINES.md`, `design-guidelines-showcase.html`, `design-guidelines-files/`
- `archive/CK_server/sessions/` — 35 JSON files, frozen pre-migration backups (2026-07-16, per `session_store.py`)
- `archive/plans/` (completed, per each status header): `PLAN-es-module-split`, `PLAN-backend-module-split`, `PLAN-db-migration`, `PLAN-db-only-search`, `PLAN-facelift`, `PLAN-frontend-unit-tests`, `PLAN-playwright-e2e`, `PLAN-llm-observability`, `PLAN-cli-corpus-combined-followups`, `CK-main/PLAN-per-user-agent`, `CK-main/PLAN-llm-mode-selection`

### ✅ Batch 2 — `docs/` (repo-level documents)
`REVIEWER-ONBOARDING.md`, `TOKEN-EFFICIENCY-REPORT-2026-09-04.md`, `resources.md`, `MEMORY-SPLIT-INVENTORY.md`, `ask-ck/Fragments_prompt.md`, `ask-ck/WIKI-Ask-ck.wiki` (a single file). `TESTBOX-ACCESS.md` / `TB470-HOST-NETWORKING.md`: see §6 Q-a.

### ✅ Batch 3 — tests consolidated under `tests/`
`js-tests/` → `tests/js/`; `e2e/` → `tests/e2e/`. Sweep: `vitest.config.js` include, `playwright.config.js` testDir, `.gitignore` e2e lines, `package.json` e2e:report path, `run_tests.sh` → its new home.

### ✅ Batch 4 — `ask-ck/plans/`
`ask-ck/ck-facelift/` → `ask-ck/plans/` (rename), plus `pytest-create/PLAN-*.md` (4), `CK-main/PLAN-*.md` (2, unless archived above), this file. `DECISIONS-FOR-REVIEW.md` and `demo-2026-09-11/` ride along. Sweep: `ask-ck/*/PLAN-*.md` globs in both skills → `ask-ck/plans/PLAN-*.md`; CLAUDE.md working-notes line; memories citing `ck-facelift/`.

### ✅ Batch 5 — `ask-ck/functions/<page>/`
`objective-drafting/` → `functions/generator/`; `pytest-create/` → `functions/pytest-creator/`; `test-composer/` → `functions/test-composer/`; new empty `functions/zephyr-tool/` (with a README stub). Sweep: `paths.py` (5 anchors), `main.py` comments, `models.py:205`, the PROGRESS.md path in CLAUDE.md / both skills / README / memories, the process-doc path in the `pipeline-layer-contract` memory.

### Batch 6 — `ask-ck/tools/` and the page script dirs  *(server stopped)*
| from `tool/` | to |
|---|---|
| `upload_refined.py` | `frontend/ck-main/current/generator/` (Export/Upload button → `wizard/export.py` subprocess) |
| `cli_lookup.py`, `pt_media.py` | `frontend/ck-main/current/pytest-creator/` (Generate/Fix prompt render; assemble copies `pt_media`) |
| `pt_profiles.py`, `jira_testlink_access.py` (renamed from `common.py` 2026-09-11 at Terrence's request: Jira/Zephyr + TestLink endpoints, scope, TLS context, credential getter — `upload_refined.py` imports it; the gate caught its wrongful archiving in batch 1), `pt_preflight.py`, `pt_grade.py`, `build_script_index.py`, `load_cli_docs_from_zips.py`, `harvest_cli_docs.py` | `ask-ck/tools/` |
| `run_tests.sh`, `guard_db_only.py`, `guard_framework_readonly.py`, `run_scratch_server.sh`, `ckdb_signature.py`, `ckdb_scratch.py`, `check_memory_links.py`, `check_memory_refs.py`, `db_wal_recover.sh`, `DB-WAL-RECOVERY.md` | `ask-ck/tools/` |

Sweep: `pytest_create.py:1477` (`_MEDIA_HELPER_SRC`), `:2010` (`tool_dir` for `cli_lookup`), `wizard/export.py:492`, `pt_exec.py`/`case_registry.py` docstrings, `pt_media`/`pt_preflight` imports of `pt_profiles`, `tool/`-relative paths in the 14 test files, `./tool/run_tests.sh` in CLAUDE.md / README / both skills / memories → `./ask-ck/tools/run_tests.sh`; the guards' `CK_SERVER` anchor depth; `run_tests.sh` self-location.

### ✅ Batch 7 — `ask-ck/frontend/ck-main/current/`  *(server stopped)*
`CK_server/static/{index.html,styles.css,ckc.jpg,favicon.svg}` → `current/`; `static/js/README.md` → `current/README.md`; the 23 modules sorted:

| page dir | modules |
|---|---|
| `generator/` | `generator.js`, `db-search.js`, `chosen.js`, `tables.js` (DB search is a section of the Generator page — confirm, §6 Q-c) |
| `pytest-creator/` | `pytest.js` |
| `llm-config/` | `llm.js`, `agent.js` |
| `admin/` | `admin.js` |
| `shared/` | `main.js`, `actions.js`, `nav.js`, `state.js`, `session.js`, `session-restore.js`, `cases.js`, `dom-helpers.js`, `llm-debug.js`, `llm-progress.js`, `locks.js`, `provenance.js`, `theme.js`, `version.js` |

Sweep: relative imports in all 23 modules and `index.html`'s `<script type=module>`; `main.py` StaticFiles mount + index path; 24 Vitest specs' import paths; `tests/e2e/pages`; `vitest.config.js`; the module map in the moved README.

### ✅ Batch 8 — `ask-ck/var/` → `ask-ck/db/`  *(server stopped; WAL checkpointed by the clean stop)*
`git mv ask-ck/var ask-ck/db` (ck.db + models/; the -wal/-shm side files are ignored and move with a plain `mv` if present). Sweep: `paths.py` `VAR_DIR`, `.gitattributes` (2 LFS lines), `.gitignore` (var block), `run_tests.sh` messages, `ckdb_signature.py`, `db_wal_recover.sh`, `run_scratch_server.sh`, tests, CLAUDE.md invariant 1 and root CLAUDE.md line, README, SERVER-README, 10 memory citations, `check_memory_refs.py` ALLOW if any.

### ✅ Batch 9 — Svelte scaffold
`cd ask-ck/frontend/ck-main && npm create vite@latest svelte -- --template svelte && cd svelte && npm install`. Adds `svelte` 5.57, `vite` 8.3, `@sveltejs/vite-plugin-svelte` in its own `package.json`; `.gitignore` gets `ask-ck/frontend/ck-main/svelte/node_modules/` and `dist/`. Serving the built `dist/` from FastAPI is the design branch's first task, not this plan's.

### Final sweep
`check_memory_refs.py`, both skills, CLAUDE.md, README doc map, `ARCHITECTURE.md`, SERVER-README paths, `paths.py` docstring tree, CHANGELOG entry, PROGRESS entry. Then Terrence restarts the server (`ck`) and pushes.

## 4. Order and the server window
Batches 0–5 are safe with the server running (docs, archive, tests, plans, functions — batch 5
edits `paths.py`, which hot-reloads; the function dirs are read at request time, so do batch 5
inside the stop window too if Terrence prefers). **Batches 6–8 need the server stopped** (code
anchors, the static mount, the open ck.db). Gate after every sweep; `ck.db` never staged.

## 5. What Terrence does
Stop the server before batch 6 (or 5), restart after the final sweep, push after each session.
`systemd`/`ck` need no edit — nothing they name moves.

## 6. Open interpretation questions (answer before "go")
- **Q-a. Hardware docs.** device-testing has NO copy of `TESTBOX-ACCESS.md` or
  `TB470-HOST-NETWORKING.md`, yet **8 device-testing files cite them** (both skills, 3 memories,
  3 handovers) by their Test-cases path. So the other repo requires them and they were never
  moved. Proposal: move both to device-testing's root, commit there (authorised), and leave
  relative symlinks here so Ask-CK's Part 3b and the 8 citations keep resolving. Alternative
  (Terrence's fallback): keep them here under `docs/` and add a reference memory.
- **Q-b. test-composer scripts.** "Put them in test-composer" — read as
  `functions/test-composer/` (they move with their parent; bench scripts that import the testbox
  framework, not front-end code). Confirm, or `frontend/ck-main/current/test-composer/`.
- **Q-c. JS sort.** Confirm the table in batch 7, in particular `shared/` as the name for the
  14 multi-page modules and `db-search.js`/`chosen.js`/`tables.js` under `generator/`.

## 7. ✅ Batch 6b — the page-button scripts (DONE 2026-09-11: Terrence took the recommendation — `pt_media` stays in tools)

The plan's rule sends `upload_refined.py` to `frontend/ck-main/current/generator/` and
`cli_lookup.py` + `pt_media.py` to `frontend/ck-main/current/pytest-creator/`. Executing 6a
surfaced one coupling the plan missed: **`pt_profiles.py` (tools) imports `parse_link_ref` from
`pt_media.py`**, so placing `pt_media` in a page directory makes a shared tool import from a page
— the reverse of the natural direction (`upload_refined` → `jira_testlink_access` is page → tools).
Recommendation put to Terrence: `pt_media.py` → `tools/` (two consumers: the assemble step and the
profiles contract), leaving `upload_refined.py` and `cli_lookup.py` as the only page-directory
scripts. Anchors that move with 6b: `wizard/export.py:492` (subprocess path),
`pytest_create.py` `_MEDIA_HELPER_SRC` and the `cli_lookup` import site, `tests/test_media_assertion_wiring.py`,
`tests/test_zephyr_push_validation.py`, `tests/test_security_hardening_batch_e.py`, `tests/test_sqlite_single_library.py`,
the `sys.path` inserts in the tests that import these modules, and `upload_refined`'s own import
of `jira_testlink_access` (needs a `sys.path` insert of `ask-ck/tools` once it leaves that dir).
