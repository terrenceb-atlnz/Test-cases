# PyTest Creator — Testing & Standardization Plan

> **Status: DRAFT v2 for review (2026-07-21).** Author: Claude, at Terrence's direction.
> v2 folds in Terrence's answers to the four open questions (see §5, now RESOLVED)
> and the corpus evidence gathered to settle them.
> Purpose: upgrade the PyTest Creator process with a standardized code template,
> validate that the current step-by-step flow actually works against the live
> `ck.db`, and measure output quality across three known cases and several LLMs.
> Nothing here is executed yet — this is the plan to agree on first.
>
> **Companion docs:** `PLAN-pytest-creator.md` (the original build, the flow it
> describes is the thing under test here), `../ck-facelift/PLAN-db-only-search.md`
> (the DB-only invariant this must respect).

---

## 0. Premises verified before writing this plan

These were checked against the live system, not assumed:

- **All three target cases are Complete and rich enough to generate from** — all in
  the `Port (7)` group:
  | Case | Objective | Steps |
  |------|-----------|-------|
  | AWPTCM-T33233 | 742 chars | 7 |
  | AWPTCM-T33234 | 942 chars | 9 |
  | AWPTCM-T33235 | 739 chars | 7 |
- **Script source now lives only in `ck.db`** (`scripts.source_text`, 830 scripts).
  The old `testsuites_art/` mount is gone; the router bug that still read it was
  fixed in commit `c29f53e` and the DB-only guard now catches that whole class.
  **Consequence for this plan: the template and every code reference are built from
  the DB, never from a filesystem tree.**
- **Framework logging surface confirmed** (from `framework_surface` in the DB):
  `ATTestCase.TestCase` exposes `log()`, `passed()`, `failed()`, `has_failed()`;
  `ATTestSet.TestSet` exposes `log()` and `create_log_file()`. These are the calls
  that produce the per-step logged output Part 3 requires.
- **The canonical exemplar today is `art/6011_simul_fail/test-6011.1000.py`** — but
  it is a *dynamic* TestSet (it manufactures TestCases at runtime from a companion
  library). That is a legitimate ART pattern but the **opposite** of the static,
  one-class-per-step shape we want to standardize on (see Part 1).

---

## 1. Part 1 — the standardized code template

### 1.1 The problem with today's generation

`templates/prompts/pt_generate_script.jinja` gives the LLM (a) one full exemplar
script as a *soft style anchor*, (b) the reusable fragments, (c) a framework-surface
slice, and (d) seven prose "hard requirements", then asks it to compose the whole
script freely. There is **no fixed scaffold** — so:

- output structure varies run-to-run and model-to-model (impossible to standardize);
- Part 3's question *"did it use the template exactly/partially/not at all"* has no
  meaningful answer, because there is nothing concrete to conform to;
- log output format is left to the model's discretion, so *"does it log each step as
  we require"* is not guaranteed by construction.

### 1.2 What we build instead

A **hard scaffold** — a concrete Python skeleton with fixed, labelled slots — that
the generator fills rather than reinvents. The LLM's job shrinks from "write an ART
script" to "fill these specific gaps in this specific structure." Standardization
becomes measurable because the frame is fixed.

The template is **derived deterministically from the ART corpus in `ck.db`**, not
hand-written from one example. Method:

1. **Corpus analysis pass** (new throwaway/repeatable script, DB-only): over the ~239
   ART scripts in `ck.db`, mechanically extract the common structure — import block,
   `TestSet(ATTestSet.TestSet)` with `FEATURES`/`init`/`configure`/`tear_down`, the
   `TestCase_N(ATTestCase.TestCase)` shape (`testCaseDesc`/`testCaseRef`/
   `testCaseMethod`/`main`), the `self.log()`/`self.passed()`/`self.failed()` idiom,
   and the `ts = TestSet(); ts.run(sys.argv)` footer. Produce a frequency-ranked
   picture of what "standard" actually is, so the template reflects the corpus.
2. **Pick/synthesize a STATIC exemplar** — a clean one-class-per-step example (either
   an existing simple ART script that matches, or a synthesized canonical one). This
   replaces 6011 as the anchor for the standardized shape.
3. **Author the template** as `templates/pt_script_template.py.jinja` (a real
   skeleton, not a prompt) with explicit slots:
   - fixed header (shebang, `import sys`, `from framework import ATTestSet, ATTestCase`,
     dynamic extra imports slot)
   - `TestSet` block with `init`/`configure`/`tear_down` slots
   - one `TestCase_<n>` block **per sequence step**, each with the four required
     attributes and a `main()` whose body is the fill slot
   - fixed `__main__` block that adds every case in order and calls `ts.run(sys.argv)`
   - **mandatory logging contract** in every `main()` (see 1.3)

### 1.3 The logging contract (Part 0 of the whole effort — do this FIRST)

The single most important Part-3 criterion is *"does it give us a logged output of
each test step as we require."* That cannot be verified after the fact if it wasn't
designed in. So before the template is written we pin the **required log format**:

- derive the exact log line shape from the framework's own log writer
  (`ATTestSet`/`ATTestCase` log methods in the DB) + real ART `.log` samples if any
  are reachable;
- define the standard: every TestCase `main()` must (a) `self.log()` a step-start
  line naming the step, (b) `self.log()` the observed result, (c) end with exactly one
  `self.passed(reason)` or `self.failed(reason)`. This yields the
  `>> test-... / PASS:/!!FAIL: / << ... RESULT (numPassed/numFailed)` structure the
  existing `parse_framework_log()` already knows how to read.
- the template **bakes these calls in as fixed lines**, so a conformant fill can't
  omit them.

**Deliverable of Part 1:** `templates/pt_script_template.py.jinja` + a short
`TEMPLATE-SPEC.md` documenting the slots and the logging contract, plus a rewritten
`pt_generate_script.jinja` that instructs the model to **fill the template** and emit
it, rather than compose freely. The generator's structural lint
(`_lint_generated`) is extended to check **template conformance** (all slots present,
required log calls present) — turning "did it follow the template" into a mechanical
pass/fail.

### 1.4 Rigidity — RESOLVED by corpus evidence

Terrence asked to compare real test structures before fixing the rigidity level. Done
— analyzed **1,828 ART `main()` bodies** in `ck.db`:

- **Body length varies enormously:** min 2, p25 13, median 37, p75 62, max 3,141
  lines. The test *logic* inside `main()` does **not** standardize — templating it
  tightly would fight the corpus.
- **The structural skeleton is highly consistent:** `self.log()` in 72%,
  `self.passed()/failed()` in 72%, device I/O via `.cmd()/.mode()` in 62%, some
  helper/function call in 100%. (The ~28% without inline log/assert are the
  dynamic/library-driven cases where the assertion is inherited or in a helper.)

**Decision: tighten the skeleton, leave the body free.** The template *mandates* the
structural calls — a step-start `self.log()`, a result `self.log()`, and exactly one
`self.passed()/failed()` (making the 72% pattern universal by construction) — but the
`main()` logic between them is a free fill slot. This is tighter than "rigid frame +
free body" (we now enforce the internal logging calls, not just the outer frame) yet
does not straitjacket the genuinely variable test logic. It is the evidence-backed
middle that makes Part 3's conformance check mechanical.

- **Static vs dynamic scripts.** The template standardizes the *static* one-class-per-
  step shape. Inherently dynamic cases (like 6011) won't fit — acceptable; the three
  target cases are step-based. Flag if any target turns out to need dynamic generation.

---

## 2. Part 2 — does the current process actually work?

### Phase 2A — Procedural check (also the first real end-to-end run)

Per `PLAN-pytest-creator.md`, **the first full real-LLM walkthrough has never
completed** (it was blocked by the LLM-config dispatch bug, since fixed). So this
phase is not just a design critique — it is the maiden voyage of the pipeline
against the live `ck.db`. Walk all 8 steps for one case (start with T33234 — its
MDI/MDIX content is the best-covered by the mechanical script search) and record, per
step:

- does the step produce what the *next* step actually needs?
- is the human-review artifact at each gate useful or noise?
- latency and failure modes against the real DB.

Then answer the merge question. **Early hypothesis to test:** steps 3→4→5 (Script
Search → Fit Decision → Fragments) are three LLM round-trips over heavily overlapping
context and are the prime candidates to merge — likely Fit + Fragments into one step.
Steps 2 (Sequence) and 6 (Generate) are clearly distinct and should stay separate.
Deliverable: a per-step "keep / merge / cut / fix" verdict with rationale.

### Phase 2B — Content check (search efficacy + model comparison)

Two independent comparisons, both **logged for side-by-side analysis**:

1. **Keyword vs LLM search** at the two search-bearing steps (Step 3 script search;
   and by analogy the Generator's evidence steps if relevant). Mechanical scoring
   already runs first and LLM re-ranks the top-40 — so we can capture *both* rankings
   for the same query and compare: precision of the top-N, whether the LLM promotes
   genuinely better scripts or just reshuffles, and where each misses.
2. **Model matrix** across the LLM-bearing steps (Sequence, Search-suggest, Fit,
   Fragments, Generate) for: **vLLM-fast, vLLM-thinking, Claude Haiku, Claude Sonnet,
   Claude Opus**. For each (step × model): capture output, token in/out, latency, and
   a quality score.

**Infrastructure that already exists** (lean on it, don't rebuild):
- `dry_run` provenance renders the exact prompt per step with **zero tokens** — use it
  to snapshot identical prompts across models.
- the debug-log already records `N in / M out` per request per session — the token
  accounting is done.
- `_llm_cfg` now resolves the configured backend correctly at dispatch (the bug fix),
  so switching models per run is reliable.

**Gap to build — the comparison runner.** Today it's one model at a time through the
UI. Part 2B needs a small **offline harness** that, given a case + step, runs the same
rendered prompt through each model in the matrix and writes a structured result row
(model, step, case, prompt_hash, output, tok_in, tok_out, latency, score) to a results
file under `ask-ck/pytest-create/data/` (or `.meta/`). This is a build item, scoped as
part of Part 2B, not free.

**Model-access note (confirmed direction):** the matrix includes Claude Haiku/Sonnet/
Opus via CLI/API alongside vLLM. Verify the reachable auth path (CLI agent vs
`api_key`) as the harness's first step; if a tier isn't reachable, drop it and log the
omission rather than silently skipping.

---

## 3. Part 3 — judging the output

Run the full pipeline (with the Part 1 template in place) for **T33233, T33234,
T33235** and score each generated script on this rubric. Criteria are split by how
they're measured so nothing subjective creeps into what can be checked mechanically.

| # | Criterion | How measured | Scale |
|---|-----------|--------------|-------|
| 1 | Used the template | **Mechanical** — diff structure vs `pt_script_template.py.jinja` slots | exactly / partially / not at all |
| 2 | Used the code snippets | **Mechanical** — match fragment code against output | exactly / partially / not at all |
| 3 | Snippet order correct | **Mechanical** — fragment order vs sequence order | right / wrong |
| 4 | Generated the missing steps | **Human** — quality of the gap-fill logic | exceptional / good / bad / not at all |
| 5 | **Code executes** ⭐ | **tb470** — real run, exit code 0 (raw), + judge interpretation | yes / no |
| 6 | **Logs each step as required** ⭐⭐ | **tb470 + parser** — `parse_framework_log` sees one PASS/FAIL block per step matching the logging contract (raw), + judge interpretation | yes / partial / no |

Criteria 1-3 become an automated report (no human judgment). Criteria 4-6 feed the
judging process below.

### Judging process — RESOLVED (two LLM judges + human holistic review)

Terrence's decision: **both mechanical and judged elements are used, and the judged
criteria (4, and the interpretation of 5-6) are graded by TWO LLM judges — Claude
Opus and vLLM-thinking — the theoretical best of each family.** Then a **human review**
looks at *both LLM judges' grades of each script side by side, together with the actual
log the script produced*, for a final holistic verdict. Rationale: two strong,
independent judges surface disagreement (the interesting signal), and the human
adjudicates with the real execution log in hand rather than trusting either model
blind. The mechanical criteria (1-3, and the raw execute/parse booleans of 5-6) are
ground truth the judges and human both see.

Per script, the judging artifact therefore contains: the mechanical report (1-3),
each of the two LLM judges' grades + rationale for criteria 4-6, the raw testbox run
result and parsed per-step log, and a human verdict field.

### Testbox — RESOLVED (live this session)

**`ssh tb470` is reachable from this seat**, verified: connects, passwordless sudo
works, framework present at `/home/st-art/framework`, device under test on **u5**. So
criteria 5-6 are **in scope this session** — this will also be the first-ever real
PyTest Creator testbox run. We still split the work for clean sequencing, but both
halves are executable now:
- **Part 3a (offline):** criteria 1-4 for all three cases.
- **Part 3b (on tb470):** criteria 5-6 — add a tb470 testbox profile, run each
  generated script over SSH, parse the framework log.

---

## 4. Phasing / order of work

1. **Part 0 — logging contract spec** (offline, small). Pin the required log format
   from the framework + samples. *Blocks Part 1.*
2. **Part 1 — template** (offline). Corpus analysis → static exemplar → template +
   spec → rewrite `pt_generate_script.jinja` → extend lint for conformance.
3. **Part 2A — procedural walkthrough** (needs a working LLM, no hardware). First real
   end-to-end run; per-step keep/merge/cut/fix verdict.
4. **Part 2B — content + model comparison** (needs LLM access; build the harness).
   Keyword-vs-LLM + model matrix, all logged.
5. **Part 3a — offline judging** (criteria 1-4) for the three cases.
6. **Part 3b — execution judging** (criteria 5-6) on **tb470** — add the profile, run
   each generated script, parse logs. First real testbox run of the tool.
7. **Judging** — two LLM judges (Opus + vLLM-thinking) grade each script; human
   holistic review over both grades + the real logs.

Parts 0/1 and the Part 2B harness are pure build; 2A/3a are runs; 3b is the testbox
run (now unblocked — tb470 is live).

## 5. Decisions (RESOLVED 2026-07-21)

1. **Template rigidity** → tighten the *skeleton* (enforce the log-start / log-result /
   single pass-fail calls), leave `main()` *bodies* free. Backed by the 1,828-body
   corpus analysis in §1.4 (bodies vary wildly; structure is consistent).
2. **Testbox access** → **tb470 is live this session** (device on u5; sudo + framework
   verified). Part 3b is in scope now, not deferred.
3. **Quality judging** → **both** mechanical and judged. Judged criteria graded by
   **two LLM judges: Claude Opus + vLLM-thinking**, then a **human holistic review**
   over both judges' grades and the real per-script log (§3, "Judging process").
4. **Results layout** → results committed, organized **per test case, the same way
   objective-drafting does** (`refined-cases/<Group>/AWPTCM-Txxxx/…`). The generated
   Python tests and their comparison/judging artifacts sort by case so they relate
   back to the source case for later reference. (Concretely: results under
   `ask-ck/pytest-create/generated/<Group>/` and `.meta/<Group>/<Name>/` already key
   by case; the Part 2B/3 comparison + judging files join that per-case structure and
   are committed, not gitignored.)

### Follow-on items surfaced by these decisions
- Comparison/judging artifacts are **committed** — confirm they contain no secrets
  (they won't; prompts/outputs/logs only) and no credentials from tb470.
- tb470 profile stores in the gitignored `secrets.testboxes.json` (password write-only)
  — the profile itself is never committed, only the run results.

## 6. Standing constraint — the testbox framework dir is READ-ONLY

**`/home/st-art/framework` on the testbox (profile `framework_path`) is read-only for
this project.** Nothing in PyTest Creator may write into it, edit a file under it, or
run a mutating command against it. If a framework file genuinely needs changing, it is
**copied into the run workdir and edited there** — an explicit exception, out of scope
as a general rule.

Enforced in code (added 2026-07-21):
- `pt_exec._assert_write_allowed()` — every SFTP write target (run workdir + each
  uploaded file) is checked; a target at/under the framework dir raises
  `FrameworkReadOnlyError` before the write.
- `pt_exec._assert_command_allowed()` — the remote run command is scanned per
  sub-command (`&&`/`||`/`;`); a mutating verb (`rm mv cp touch mkdir chmod ln dd
  truncate tee sed -i patch …`) whose write TARGET is under the framework dir is
  refused. Read-only references pass: `test -d <fw>`, `PYTHONPATH=<fw>`, copying/
  symlinking FROM the framework, and `ln -s <fw> framework` (pointing a workdir
  symlink AT it — the current run path).
- `tool/guard_framework_readonly.py` — runnable check (15 cases) proving the guards
  block every framework mutation and allow the legit read/copy/run path. Run it
  alongside `tool/guard_db_only.py` before committing execution-path changes.
