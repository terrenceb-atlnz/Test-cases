---
name: pytest-creator-askck
description: "PyTest Creator tool in Ask CK — 5 steps ending at a saved script (Run/Validate/Testboxes retired 2026-10-12), tracker location, ART identity"
metadata:
  node_type: memory
  type: project
  originSessionId: 3813cc75-639d-4e62-abb8-fd384442d015
  modified: 2026-07-28T02:34:43.796Z
  verified: 2026-09-22
---

The **PyTest Creator** (a tool inside the Ask CK FastAPI workbench at
`ask-ck/CK-main/CK_server/`) turns refined AWPTCM cases into runnable
Allied Telesis `framework` (ATTestSet/ATTestCase) scripts.

**2026-10-12 (Terrence): it ENDS at a saved script.** 5 steps (Cases, Sequence, Script Search,
Fragments, Generate); Confirm Step 5 saves to `generated/` and pops up "Do you want to test the
new script?" (Yes → Validation, No → 1. Cases). **6. Run, 7. Validate and Testboxes are gone,
front end and server** (no `/run`, `/validate`, `/profiles`; `pt_exec.py` is only the log parser;
no paramiko). Running, repairing and finalizing a script is **Validation's** job (Test Composer
section; `ask-ck/plans/PLAN-test-validation.md`), through the seat agent's `/test-mode` session —
[[tb470-runs-go-through-test-mode]]. Cases-list *Complete* = the script is saved
(`case_registry.saved_script_case_keys`); Finalize hides the case. Old sessions' `step7`/`step8`
load but are ignored. Anything below about running on hardware from the Creator is history.

The living plan/progress tracker is `ask-ck/plans/PLAN-pytest-creator.md`
— **update it as milestones land** (user explicitly wants progress tracked there). Testing
status lives in the companion `PLAN-pytest-testing.md`.

Facts that have CHANGED since this memory was first written (2026-07-14) — do not trust the
older phrasing found in historical doc entries:

- The flow was **7 steps, not 8** after Fit Decision was removed 2026-07-23 (5 since
  2026-10-12, above). Internal `stepN` session keys are unchanged (fragments are still `step5`,
  generate `step6`).
- Generation **fills a fixed skeleton** (`templates/pt_script_template.py.jinja`); it is not
  a free compose.
- All script source comes from **`ck.db`** — the old script mount (`testsuites_art/` etc.)
  is retired and guarded against. The testbox framework dir is read-only (no runtime guard since
  2026-10-12: the server has no code path to a testbox).

Remaining as of 2026-07-28: **Part 3b** (execution judging on tb470) needs `configs/tb470.setup`
— the schema is no longer the blocker (captured in `SETUP-FILE-REFERENCE.md`), only tb470's
device list and physical wiring are. Parsing `.setup` inside `CK_server` is the outstanding
design follow-up ([[setup-file-declares-topology]]). T33234 TestCase_8 is still graded bad.

**ART identity (Terrence, 2026-09-22): `<family>.<case>.<TestCase>`.** One family per mother
folder, allocated 9001-9999 and persisted in `generated/.families.json` (authoritative over the
folder names); **9000 is reserved for libraries**. So `9001_Port/test-9001.33234.py`,
`library_9001.py`, and `9001.33234.5` is TestCase_5 inside it. Two things that are easy to get
wrong: the framework parses only TWO numbers out of the filename, so the third part lives on the
`TestCase_<n>` class (that is where `testCaseNum` comes from — 231 of 239 ART scripts never
assign it), and **no client may derive the script name** since only the server knows the family.
Plan: `ask-ck/plans/PLAN-art-family-numbering-and-prune.md`; see also [[art-suite-shape]].
Running ONE TestCase by that number is UNVERIFIED against the live framework — the legacy py2
`ATPylib` does `if str(testCase.testCaseNum) in args`, but the current py3 framework takes
`-s`/`-v` flags the legacy stub cannot parse. Confirm on tb470 before relying on it.

Conventions: `framework` is a whole library (not just the two base classes); generated
scripts go to `generated/<family>_<Group>/<Name>.py` — the name is DERIVED from the case key,
not typed (the panel's naming inputs were removed 2026-09-17);
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
  (needs clean lint; policy errors overridable with a recorded reason; since 2026-10-12 it also
  WRITES generated/ before confirming, and its overridable 409s name the field in `X-CK-Needs`). LLM steps are slow
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
`ask-ck/tools/check_memory_refs.py` does NOT flag it — the prefix makes the citation look like a file
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
