---
name: pytest-creator-askck
description: "PyTest Creator tool in Ask CK — current flow shape, tracker location, and what remains (tb470 execution, .setup parsing)"
metadata:
  node_type: memory
  type: project
  originSessionId: 3813cc75-639d-4e62-abb8-fd384442d015
  modified: 2026-07-28T02:34:43.796Z
  verified: 2026-09-04
---

The **PyTest Creator** (a tool inside the Ask CK FastAPI workbench at
`ask-ck/CK-main/CK_server/`) turns refined AWPTCM cases into runnable
Allied Telesis `framework` (ATTestSet/ATTestCase) scripts, then runs them on real hardware
over SSH and iterates via an LLM fix loop.

The living plan/progress tracker is `ask-ck/pytest-create/PLAN-pytest-creator.md`
— **update it as milestones land** (user explicitly wants progress tracked there). Testing
status lives in the companion `PLAN-pytest-testing.md`.

Facts that have CHANGED since this memory was first written (2026-07-14) — do not trust the
older phrasing found in historical doc entries:

- The flow is **7 steps, not 8** — Fit Decision was removed 2026-07-23. Internal `stepN`
  session keys are unchanged (fragments are still `step5`, generate `step6`).
- Generation **fills a fixed skeleton** (`templates/pt_script_template.py.jinja`); it is not
  a free compose.
- All script source comes from **`ck.db`** — the old script mount (`testsuites_art/` etc.)
  is retired and guarded against. The testbox framework dir is read-only, also guarded.

Remaining as of 2026-07-28: **Part 3b** (execution judging on tb470) needs `configs/tb470.setup`
— the schema is no longer the blocker (captured in `SETUP-FILE-REFERENCE.md`), only tb470's
device list and physical wiring are. Parsing `.setup` inside `CK_server` is the outstanding
design follow-up ([[setup-file-declares-topology]]). T33234 TestCase_8 is still graded bad.

Conventions: `framework` is a whole library (not just the two base classes); generated
scripts go to `generated/<Group>/<Name>.py` with names the user can edit at creation;
testbox profiles need `tb_number` + IP minimum, stored in gitignored `secrets.testboxes.json`;
server runs via `ask-ck/CK-main/run.sh` on port 8000. Reaching a device by hand:
[[testbox-console-access]].

Facts confirmed 2026-08-06 (driving the API end-to-end for the pilot trio):

- **Input source = the refined BUNDLE, not the wizard `ck.db` session.** `_find_refined_case`
  reads `refined-cases/**/zephyr_payload.json`; objective/steps come from there. So editing a case
  via the wizard is not enough — the git bundle is what PyTest Creator ingests. (They were kept in
  sync this session by persisting both.)
- **`load_case` REUSES an existing `pt-<key>` session** and only re-reads the bundle when none
  exists. To pick up changed content you MUST `clear_session/<key>` first, else you regenerate off
  stale input. (The pilot `pt-` sessions were 2026-07-29 pre-cleanup.)
- **Pipeline drive order (generate+lint, no hardware):** clear_session → load_case →
  extract_sequence → confirm_step/2 (coverage gate) → suggest_scripts → save_matches
  ({stepN:[ids]}) → confirm_step/3 → gather_fragments → save_fragments ({keep:[{source_id,symbol}]})
  → confirm_step/5 → generate_script (also runs an initial lint) → lint_script → confirm_step/6
  (needs clean lint; policy errors overridable with a recorded reason). LLM steps are slow
  (extract/generate ~60-200s on Opus/`claude_code`, 300-600s server timeouts) — run with a long
  client timeout or they read as failures.
- **`testCaseDesc`/`testCaseRef`/`testCaseMethod` stay** — they don't control LLM drift, but the
  ART corpus populates them (desc 98% / method 86% / ref 61% real of 2095 cases), the conformance
  lint requires all three (`_lint_generated`, structural error), and the template's `testCaseRef`
  = the AWPTCM key is a deliberate traceability improvement over the corpus's frequent `'None'`.
  Do not re-propose removing them without new evidence. Whether the framework harness reads
  desc/method at runtime for `TEST_CASE_*` log headers is unverifiable offline (framework tree not
  mounted here) — a hardware run settles it.


**2026-08-31 — paths above made repo-relative.** They read `copilot/Test-cases/…`; that
checkout name no longer exists (the repo is under `claude/Test-cases` now), and
`tool/check_memory_refs.py` does NOT flag it — the prefix makes the citation look like a file
on another machine, which the checker deliberately skips. Repo-relative paths cannot rot that
way. Four other memories still carry `copilot/` citations, left alone because this session did
not use them: `bootloader-media-parse-bug`, `db-only-single-source`,
`run-attribution-5700-campaign`, and `grep-shim-honors-gitignore` (whose occurrences are
example DATA inside a recorded measurement — rewriting them would falsify it).

**Per-step flow gates closed 2026-08-31** — see [[llm-provenance-portability]] and
[[old-sessions-are-not-coverage]]. Step 3 is confirmable from the per-step picker
(`step_matches` / `selections`), records its own provenance, and step 6 has
`POST /save_naming/{key}` so naming persists before a first successful generate.


**2026-09-02 — step 6 no longer makes ONE call.** Generation is per unit: `_skeleton_units()`
splits the rendered frame by AST into one unit per `TestCase_<n>` plus configure/tear_down as a
single `setup` unit, each gets its own LLM call, and `_assemble_units()` splices the replies
back byte-exactly. **Assembly runs no LLM** — splice, re-stamp, lint. `generate_script` still
exists; the per-unit path is `POST generate_units/{key}` (batch) or `generate_step/{key}` (one),
then `assemble_script/{key}`. Unit ids are `setup` / `tc1`…`tcN` and are **not** sequence step
numbers — `_split_sequence` renumbers, so sequence step 31 can be `TestCase_29`.

Why, with the numbers: the single whole-script call for T44297 was 672.9 s / 104,962 in /
58,715 out / **$1.5846**, and 39 % of its output was the model retyping a frame we render
deterministically. Per unit measures ~$0.45, so 30 units is ~$13.5 — it buys parallelism,
per-step retry and an editable prompt, NOT money. Do not fan it out from the browser as N
requests: [[browser-fanout-connection-ceiling]].

**Pass C** (`POST review_script/{key}`) is a holistic review returning findings as JSON; it
persists to `step6["review"]`, writes no files, invalidates no downstream step, and
`fix_script` accepts `review_findings` as a fix reason.
