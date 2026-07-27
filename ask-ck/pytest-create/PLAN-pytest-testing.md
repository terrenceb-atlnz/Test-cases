# PyTest Creator — Testing & Standardization Plan

> **Security note (2026-07-27):** the adversarial review hardened files this plan covers —
> `pt_exec.py` (SSH exec now `shlex`-quoted + framework-guard extended to redirection/interpreter/
> `rsync`/`install`/`cp -t`) and `routers/pytest_create.py` (`/run` `setup` path metachar-validated;
> generated library filename traversal fixed). See SERVER-README → *Security Posture* and
> `ADVERSARIAL-REVIEW-BACKLOG.md`. No change to the flow/phases below.
>
> **Follow-on (2026-07-27g, review closed):** four further changes touch this plan's surface, all
> behaviour-preserving for the documented flow — (a) the skeleton renderer escapes step text via a
> `pyliteral` filter, so a reviewer-typed newline or trailing backslash can no longer produce an
> **uncompilable** skeleton (it previously reached both the preview UI and the generate prompt);
> (b) `_restamp_provenance` no longer mis-attributes a setup-mapped fragment's tag to the wrong
> `TestCase`, and no longer deletes reviewer rationale comments that merely mention ART/SVT/legacy/AI;
> (c) restart-orphaned testbox runs are re-marked stale by `run_status`, not only by `load_case`, so
> the UI stops polling a dead run; (d) SSH host keys are pinned trust-on-first-use in `_connect`
> (`CK_SSH_TRUST_ANY=1` to opt out). Sequence step text is also whitespace-collapsed at both write
> paths.
>
> **Status: IN PROGRESS (updated 2026-07-22).** Author: Claude, at Terrence's direction.
> v2 folded in Terrence's answers to the four open questions (§5, RESOLVED) and the
> corpus evidence gathered to settle them.
> Purpose: upgrade the PyTest Creator process with a standardized code template,
> validate that the current step-by-step flow actually works against the live
> `ck.db`, and measure output quality across three known cases and several LLMs.
>
> **Progress:**
> - ✅ **Part 0** (logging contract) — done; `LOGGING-CONTRACT.md`.
> - ✅ **Part 1** (standardized template + conformance lint) — done;
>   `TEMPLATE-SPEC.md`, `templates/pt_script_template.py.jinja`.
> - ✅ **Part 2A** (first real end-to-end walkthrough on T33234) — done 2026-07-21b;
>   steps 1–6 verified against the live DB via the org vLLM, 3 vLLM-path bugs fixed.
>   Full per-step record: **`PART2A-WALKTHROUGH.md`**.
> - ✅ **§1.5 inline source-provenance tagging** — done 2026-07-22 (was tracked as
>   debt out of Part 2A); mechanical server-side re-stamp, verified on a real live
>   T33234 generate. See **§6 below** for the full bug list found while building it.
> - ✅ **Part 2B build** (comparison harness `tool/pt_model_matrix.py`) — done
>   2026-07-22; keyword-vs-LLM + 5-model matrix (vLLM-fast/thinking, Claude
>   Haiku/Sonnet/Opus) run live across all three target cases. Results:
>   `ask-ck/pytest-create/comparison/Port (7)/<CaseKey>/<step>.json`. Grok CLI
>   logged in but quota-exhausted (real 403) — omitted with reason, not silently
>   dropped, per the plan's own instruction (§2 Phase 2B).
> - ✅ **Streaming transport for the vLLM path** (the "fix #2" §7.7 flagged as the
>   real structural fix, not yet built at Part 2B) — built + verified live
>   2026-07-22b. The OpenAI-compatible call path now streams; the HTTP read
>   timeout is an inter-chunk budget, not a whole-response ceiling, so
>   `vllm-thinking` can no longer read-time-out on the largest-output step. See
>   **§8 below**. (Token-processing-over-time comparison + infographic across
>   both models in progress.)
> - ✅ **Stale-`llm_config` re-sync (§7.3 root-cause fix)** — done 2026-07-22b, both
>   routers. The active workspace default is now authoritative, so a session whose
>   stale config is a headless CLI mode re-syncs instead of silently hitting the
>   wrong backend; `_llm_is_active` left untouched. Unit-verified (8/8) + concurrency
>   reviewed. See **§9 below**. (Pre-existing dual-instance session debt logged in §9.4.)
> - ✅ **CLI grounding (§11)** — 2026-07-27h. Root-caused the fabricated `speed=1000`
>   output schema to a RESOURCING gap, not model quality (all 5 models did it, Opus
>   included). Harvested the real AlliedWare Plus command reference into `ck.db`
>   (`tool/harvest_cli_docs.py`, 73,006 fetches, 0 failures, 4,652 commands) and grounded
>   BOTH the sequence-extraction and generate prompts. Result: `key=value` fabrication
>   **13→0** in sequences and **57→0** in scripts. Also added an objective-coverage gate
>   (every Zephyr step needs ≥1 PyTest step) after a re-extraction silently dropped
>   T33234's whole MDI/MDI-X negative path.
> - 🔄 **Part 3a — mechanical half DONE** 2026-07-27 (`tool/pt_grade.py` + 21 tests):
>   criteria 1-3 and the offline half of 6, graded for all three cases. T33235's script
>   was generated this session (it had none). **C1 + C6-offline clean across all three.**
>   Results: `judging/Port (7)/<CaseKey>/mechanical.json`. See **§10 below**. Remaining:
>   criterion 4 (the two LLM judges + human review) and regenerating T33233, which is
>   stale + wrong-backend and blocked behind its unconfirmed step5 (§10.6).
> - ⏳ **Part 3b** (tb470 execution, criteria 5-6) — still blocked on
>   `configs/tb470.setup` + a testbox profile (Terrence-side physical-topology
>   prerequisite — see §5b; note the **corrected configs path** there).
>
> **Companion docs:** `PART2A-WALKTHROUGH.md` (Part 2A results + the LLM-path fixes),
> `PLAN-pytest-creator.md` (the original build, the flow it describes is the thing
> under test here), `../ck-facelift/PLAN-db-only-search.md` (the DB-only invariant
> this must respect).

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

**Static exemplar chosen:** `art/1363_ipv6/test-1363.1002.py` — a clean self-contained
static script (one `TestSet` with `init`/`configure`; two inline `TestCase_N` each with
the four attributes, device I/O, `self.log(output)` evidence, non-empty
`passed()`/`failed()`, and per-case `tear_down()`; `__main__` adds both then
`ts.run(sys.argv)`). Replaces the dynamic 6011 as the anchor. The one thing we
standardize *away* from it: its `testCaseRef = 'None'` → the AWPTCM key.

**Setup/teardown is NOT a separate script category (verified against the framework).**
ART setup — loading configs, cleaning the switch, base config, pre-test hygiene — lives
in **lifecycle methods inside the same script**, not standalone setup scripts:
- `TestSet.configure()` runs ONCE before all cases (178/ART scripts use it; content is
  base config: int/vlan/ip/switchport/spanning-tree). `TestSet.tear_down()` runs ONCE
  after (155 scripts). Per-case `TestCase.configure()/tear_down()` wrap each step.
- The framework ALSO does pre-test hygiene with **zero script code** (reboot to
  default.cfg, power-cycle, clear exception logs, check stacks well-formed) — visible
  in the real run-log preamble. The template does nothing for these; subclassing gets
  them free.
- **Consequence — the template has THREE distinct slot kinds, not to be conflated:**
  (a) `TestSet.configure()/tear_down()` = suite setup/cleanup, config commands, **NO
  pass/fail** (logging contract does NOT apply); (b) `TestCase_N.main()` = the actual
  verification steps, one per sequence entry, **logging contract applies**; (c)
  framework automatics = nothing.
- **Pipeline refinement (check in Part 2A):** Step 2 sequence extraction should
  separate *setup/precondition* actions (→ `configure()`) from *verification* steps (→
  `TestCase_N`). Forcing a precondition into a `TestCase_N` with a pass/fail is wrong.
  Verify the current `pt_extract_sequence` makes this distinction; if not, it's a gap.

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

### 1.5 Inline source-provenance tags (code-review / troubleshooting aid)

Every block of code inside a filled `main()` / `configure()` / `tear_down()` body is
tagged **in-line at the point of use** with where it came from, so a reviewer hitting a
broken block knows immediately whether it's reused real code (and exactly where to look
for context) or LLM-generated (and by which model/when):

- **Reused from a real script** — tag with the source db, id, and line range, taken
  **mechanically from the fragment metadata** (`source_id` + `loc`), NOT self-reported
  by the LLM:
  - `# ART <suite/id> <lines xx-yy>`   e.g. `# ART 1363_ipv6/test-1363.1002.py 55-78`
  - `# SVT <test name> <lines xx-yy>`
  - `# legacy <test id> <lines xx-yy>`
  (`source_id` is prefixed `art/`/`svt/`/`legacy/`, which maps 1:1 to the tag family;
  `loc` gives the lines.)
- **LLM-generated** (gap-fill with no source fragment) — tag with model + date:
  - `# AI <model> <YYYY-MM-DD>`   e.g. `# AI claude-opus-4-8 2026-07-21`
  (model comes from the generation provenance `step6.provenance.llm.model`; date is the
  generation date — both server-side, not LLM self-report.)

**Why:** on code review / troubleshooting, when a snippet is broken, the tag says where
to search for the original context (real script + lines) or flags it as synthesised
(which model, for regeneration/comparison). It also makes Part 3 criteria 2–3 (snippet
reuse / order) **mechanically auditable in-place** — the tags ARE the reuse evidence.

**Mechanism (how it's enforced, not just requested):**
- The generate prompt instructs the LLM to emit a leading provenance comment on each
  block and to copy the exact `# ART/SVT/legacy <id> <lines>` tag from the fragment
  header it adapts (the prompt already labels each fragment with its `source_id` +
  `loc`), and to tag any code it writes itself `# AI <model> <date>`.
- Because tags derived from fragments are also known server-side, a **post-generation
  pass verifies/corrects** them: reused blocks matched to a fragment get the
  authoritative `source_id`+`loc` tag stamped (LLM can't fake or drift it); untagged or
  unmatched blocks are stamped `# AI <model> <date>`. So provenance is trustworthy even
  if the model mislabels.
- Lint/judge check: every non-trivial block carries exactly one provenance tag; Part 3
  criterion-2/3 scoring reads the tags directly.

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
| 2 | Used the code snippets | **Mechanical** — match fragment code against output; corroborated by the inline `# ART/SVT/legacy <id> <lines>` provenance tags (§1.5) | exactly / partially / not at all |
| 3 | Snippet order correct | **Mechanical** — fragment order vs sequence order (read from the inline provenance tags) | right / wrong |
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
   **two LLM judges: Claude Opus + ~~vLLM-thinking~~ vLLM-***fast***** (CHANGED
   2026-07-27, Terrence's call — see §10.1), then a **human holistic review**
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

## 5b. Testbox prerequisites — `.setup` and `config.cfg` (investigated 2026-07-21)

ART runs depend on host-side config files that our tool does NOT generate — they are
**testbox environment prerequisites**. Findings (verified against `framework/` on tb470):

- **`configs/<hostname>.setup`** (e.g. `configs/tb470.setup`) — declares the TOPOLOGY
  (which devices/ports, the device on u5). Our execution path (`sudo python3 <script>
  -s <setup> -v` in `pt_exec.py`) is driven by this file. **Required.**
- **`configs/<hostname>.cfg`** (e.g. `configs/tb470.cfg`) — a per-testbox **run-control
  config** generated by `framework/config_gen.py::makeDefaultConfig()` (INI via
  configparser; one section per suite; keys `update`/`publish`/`norun`/**`noconf`**/
  `include-tests`/`exclude-tests`/`device`/`tftp-download`/`restore-licenses`). It is
  read by the **suite runners** `runAll.py`/`runTestSuite.py` — NOT by `ATTestSet`/
  `ATTestCase` directly (`config.cfg` appears nowhere in those two modules). Build it
  with `python3 framework/config_gen.py` (writes `configs/<hostname>.cfg`; refuses if
  it already exists).
- **Two run paths differ on config.cfg:** (1) suite runner → reads `<hostname>.cfg`;
  (2) direct single-script (OUR path) → driven by `-s <setup>`, appears NOT to read
  config.cfg. **To be verified empirically on the first real tb470 run (Part 2A/3b)** —
  if the direct run complains about a missing config.cfg, generate it; if it only needs
  the `.setup`, config.cfg is out of scope for our path.
- **⚠ PATH CORRECTION (verified live 2026-07-27):** the `configs/` dir is **NOT** under
  `/home/st-art/framework` — that dir has no `configs/` at all. The real location is
  **`/home/st-art/st-art/configs/`** (473 `.setup` files). Every `configs/<hostname>.setup`
  reference above should be read against that path.
- **State on tb470 now:** `configs/` has other testboxes' `.setup` files but **neither
  `tb470.setup` nor `tb470.cfg` exists yet** (re-verified 2026-07-27). Both are Terrence-side prerequisites
  (topology = physical wiring) before Part 3b can run. The tool generates the test
  SCRIPT only; setup/config are environment inputs.
- **SVT setup utilities** (`svt_scripts/.../setupSwi.py`, `libSvt/libSvtSetup.py`) are
  SVT-workflow switch-provisioning helpers — NOT part of ART single-script execution,
  not a dependency our ART-targeted generated scripts inherit.

**Device-side `.cfg` files** (`boot conf <name>.cfg`, `copy run …`, switch nvs configs)
seen in 133 corpus scripts are the SWITCH's boot config, manipulated at runtime by test
logic — unrelated to the host-side `config.cfg`/`.setup` above.

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

## 7. Session log — 2026-07-22 — §1.5 build + Part 2B run: bugs found, fixed, decisions

Continuing the plan after the vLLM read-timeout fix (SESSION_STATE.md handoff).
Before starting: verified LLM access live rather than assuming from file absence —
**Local LLM (vLLM) key is stored and works** (`secrets.local.json`), **Claude
Haiku/Sonnet/Opus are all reachable headless** via `claude -p --model <alias>`,
**Grok CLI is logged in but genuinely quota-exhausted** (real 403 from
`cli-chat-proxy.grok.com`), and **tb470 is reachable** (SSH/sudo/framework all
confirmed) but `configs/tb470.setup` genuinely does not exist yet (Terrence-side
physical-topology prerequisite, per §5b — the only real remaining external block).

### 7.1 §1.5 inline source-provenance tags — built and verified live

Implemented exactly as designed in §1.5: `_fragment_tag()` derives a mechanical
`# ART/SVT/legacy <suite/file> lines <a>-<b>` tag straight from indexed fragment
metadata (`source_id`, `loc` — never LLM self-report); `_restamp_provenance()` is
an authoritative post-generation pass that stamps the top of every
`TestCase_<n>.main()` from the server-known step→fragment `maps_to` mapping,
falling back to `# AI <model> <date>` for gap-fill steps. Wired into both
`generate_script` and `fix_script`. Lint (`_lint_generated`) gained a conformance
check: every `main()` must have a leading tag matching `# (ART|SVT|legacy|AI)`.

**Bug found while verifying live (real T33234 regenerate, not a synthetic
test):** the model does attempt its own provenance line (prompt rule 8 asks it
to), but compliance is non-deterministic in *shape*, not just content — one real
run echoed the prompt's own instruction text as a second leading comment line
("`Provenance tag for this fragment: # AI vllm-fast 2026-07-21`") *below* the
server's authoritative stamp, which a first-line-only dedup check missed,
leaving two tag-looking lines per block. **Fixed:** `_restamp_provenance` now
strips the ENTIRE leading run of comment lines matching a broader echo pattern
(`# .*\b(ART|SVT|legacy|AI)\b`, case-insensitive, matched anywhere the model put
it) before inserting exactly one authoritative tag. Re-verified on a fresh live
regenerate of T33234: exactly 14 tags for 14 TestCases, zero duplicates, zero
echo leaks, lint clean. Also fixed a smaller finding from the walkthrough while
in this template: the skeleton's placeholder `failed()` string leaked
**"— not yet implemented"** into real output (`pt_script_template.py.jinja`) —
removed.

### 7.2 `max_tokens` was never parameterized — generate_script hit the cap live

Regenerating T33234 to verify §1.5 hit a REAL failure, not caused by my changes:
`finish_reason=length` at the 16000-token default (a `generate_script` prompt
emits a whole ~25-35KB script — larger than any other step). Root cause:
`max_tokens` was hardcoded (`2000`/`16000` by auth_method) with **no override
path at all** — `run_prompt`/`_call_llm_with_meta`/`_call_llm_raw` didn't accept
it. **Fixed:** threaded an optional `max_tokens` param end-to-end (mirroring how
`timeout` already works); `generate_script` and `fix_script` now request
`max_tokens=32000` (both emit a whole script). Re-verified live: T33234
regenerated clean at 91s → 76s across two runs, lint clean, 0 truncation errors.
Unit-verified the override doesn't leak into other calls (health ping etc. keep
their smaller defaults).

### 7.3 Stale per-case `llm_config` never re-syncs to the workspace default

Driving the pipeline for T33233 via raw HTTP (no browser `X-CK-Session`, this
harness's own calls) hit `provider=claude auth_method=claude_agent
model=default base_url=https://api.anthropic.com/v1` — NOT the configured
workspace vLLM default — and `suggest_scripts` degraded to the mechanical
`coverage: unknown` fallback for all 40 candidates (a real content failure, not
a crash, so it was easy to miss).

**Root cause:** `_llm_is_active()` (shared by wizard.py and pytest_create.py)
treats `claude_agent`/`claude_code`/`grok_cli` as **unconditionally active** —
by design, since headless CLI modes have no server-side credential to check.
`_apply_workspace_llm()` only overwrites a session's `llm_config` when the
existing one is judged inactive, so a session whose `llm_config` happens to be
one of these headless modes (T33233's, left over from before Local LLM became
the default) can **never** re-sync to the workspace default, even via
`load_case`'s own per-call apply. This gap exists identically in `wizard.py` —
not fixed there either, flagged for a future session, not fixed now (broader
blast radius, not blocking today's work).

There is also **no PyTest-Creator-side endpoint to reset a case's `llm_config`
non-destructively** — `wizard.py`'s `/set_llm_config/{key}` writes to the
Generator's separate `WizardSession` store, not `pt_sessions`; the only
PyTest-side reset (`clear_session`) wipes the whole session (steps 2-8), an
unacceptable loss just to fix one field. **Workaround used (not a code
change):** loaded T33233's real `PtSession` via the app's own `db.load_session`/
`PtSession`/`db.save_session` path, corrected only `llm_config` to the workspace
default, then triggered the admin panel's `/api/admin/restart` (documented,
safe, reload-based) to clear the in-process `pt_sessions` cache so the DB fix
takes effect. Verified: `step2.confirmed` and all other state preserved,
`llm_config` now `local_llm`/`vllm-fast`.

**Suggested follow-up (not done, out of today's scope):** a PyTest-Creator
`POST /api/pytest-create/reset_llm_config/{key}` that re-applies
`_apply_workspace_llm` unconditionally (bypassing the `_llm_is_active` guard),
mirroring what the admin panel does for whole-session reset but scoped to just
this one field.

### 7.4 `confirm_step` rejected legitimate empty-list answers (steps 3/5)

Driving T33235 (whose Fit Decision correctly came back `decision: new` with
zero reusable code) hit `confirm_step/5` returning
`409 "Nothing to confirm yet for step 5 (missing fragments)"` even though step 5
HAD run and correctly returned `{"fragments": []}` — a real, valid "no reuse"
answer (`gather_fragments`'s own docstring elsewhere anticipates this case:
"steps 3-5 may legitimately be 'new script, no fragments'"). **Root cause:**
`confirm_step`'s gate was `if not content.get(required_field)`, and Python
treats an empty list as falsy — indistinguishable from "the step never ran".
This would block the ENTIRE rest of the pipeline for any case whose Fit
Decision is genuinely "new" with no matching code (not a T33235-specific
fluke — same shape would hit any similarly under-covered case). **Fixed:**
for the two list-typed required fields (`matches` at step 3, `fragments` at
step 5), the gate now checks the field is *present* (`is not None`) rather than
truthy; other steps (`sequence`/`decision`/`files`/`runs`/`validated`) keep the
original truthiness check since those are never legitimately empty-but-complete
(`validated=False` in particular must stay strict). Verified live: T33235
step 5 confirms cleanly now.

### 7.5 Claude CLI token accounting is cache-skewed, not directly comparable to vLLM

Building the Part 2B harness, `claude -p`'s reported `usage.input_tokens` for a
~700-token real prompt came back as `10` — not an error, but an artifact of
this CLI session's own long-running cache (`cache_read_input_tokens` in the
tens of thousands from the session's own tooling/system-prompt context, which
dwarfs the actual per-call prompt). **Not comparable to vLLM's `tok_in`** (vLLM
has no such caching layer) without accounting for it. **Handled:** the harness
records `tok_in`, `tok_in_cache_read`, and `tok_in_cache_creation` separately per
Claude row so the eventual model-comparison read can normalize correctly instead
of silently under-counting Claude's real input cost.

### 7.6 Setup work needed before the matrix could run at all

Part 2A only drove T33234 through the full pipeline; T33233 had only step 2
done, T33235 had nothing confirmed. Since the model matrix needs all three
target cases fully walked through steps 2-5 (so each step's `dry_run` prompt can
be captured), both were driven through for real (vLLM-fast, the workspace
default) before the matrix could start — this surfaced bugs 7.3 and 7.4 above,
which would otherwise have stayed latent (T33234 alone never exercised the
stale-config or empty-fragments paths).

### Decisions made without stopping to ask (rationale, so they can be revisited)

1. **Fixed 7.2/7.3/7.4 rather than only documenting them.** All three were
   small, narrowly-scoped, evidence-backed (each reproduced live against the
   real vLLM/DB before AND after the fix), and directly blocking the Part 2B
   run requested this session — leaving them broken would have meant the
   matrix couldn't run at all for 2 of 3 target cases. The wizard-side twin of
   7.3 was explicitly NOT fixed (bigger blast radius, not blocking).
2. **Result-file placement:** `ask-ck/pytest-create/comparison/<Group>/<CaseKey>/<step>.json`
   — invented (no `generated/` dir exists yet to mirror), but follows the same
   per-case-under-Group convention as `refined-cases/` and the planned
   `generated/` layout per §5 decision 4. Committed, not gitignored (prompts/
   outputs/tokens only, no credentials — matches the decision's own follow-on
   item).
3. **Harness bypasses router session-mutation entirely.** Rather than driving
   each model through the real stepN endpoint (which would need 5x
   save/confirm/invalidate cycles per step, repeatedly clobbering the reviewed
   session state Part 3 needs), the harness captures the exact prompt once via
   the endpoint's own `dry_run: true` (byte-identical to a real send, zero
   session writes) then calls each model directly (`llm._call_llm_raw` for
   vLLM, `claude -p --model <alias>` for Claude tiers). This keeps all three
   cases' confirmed step 2-5 state intact for Part 3.

### 7.7 Part 2B results — model matrix (75 real calls: 3 cases × 5 steps × 5 models)

Full run: 71/75 completed, 4 real (non-silent) failures. Results committed at
`ask-ck/pytest-create/comparison/Port (7)/<CaseKey>/<step>.json`.

**Per-model reliability + latency (successful calls only):**

| Model | Errors | Avg latency | Max latency | Avg tok_out |
|---|---|---|---|---|
| vllm-fast | 0/15 | 40.0s | 124.1s | 7,024 |
| vllm-thinking | **3/15** | 249.6s | 465.9s | 3,631 |
| claude-haiku | 0/15 | 60.3s | 135.4s | 8,814 |
| claude-sonnet | 0/15 | 87.8s | 248.5s | 9,565 |
| claude-opus | 1/15 | 77.5s | 215.8s | 6,264 |

**The 4 failures, all real and informative (none silent):**
- `vllm-thinking` × `generate_script` — T33233 **and** T33234 both hit
  `Read timed out. (read timeout=600)` — i.e. failed even at the RAISED 600s
  floor from this session's earlier timeout fix. T33235's `generate_script`
  on `vllm-thinking` DID complete, at 376.9s — so the model's reasoning-phase
  length is highly variable, not a fixed multiple of prompt size, and
  occasionally exceeds 600s outright on the largest-output step.
- `vllm-thinking` × `suggest_scripts` — T33233 only (T33234/35's
  `suggest_scripts` on `vllm-thinking` completed at 372.6s/366.2s). Same
  failure mode.
- `claude-opus` × `generate_script` — T33233 only, hit the **harness's own**
  hardcoded 300s CLI subprocess timeout (`call_claude_cli`), not a product
  bug — Opus's other 14 calls in the matrix all completed under 300s, and
  T33234/T33235's Opus `generate_script` calls succeeded (169.6s / 215.8s), so
  this reads as one slow outlier crossing a harness limit that was sized for
  the *typical* case, not the worst case.

**Conclusion — validates the plan's own hypothesis (SESSION_STATE.md handoff,
"fix options... most→least important"):** raising the static read-timeout
(fix #1, done this session) measurably helped but is **not sufficient** for
`vllm-thinking` on the largest-output step. **Streaming (fix #2, NOT built)
is the correct structural fix** — it would keep the socket alive through the
reasoning phase regardless of its length, rather than requiring an
ever-larger static ceiling that a sufficiently long reasoning pass can still
exceed. Recommend prioritizing streaming for `vllm-thinking` specifically
before relying on it for `generate_script`-scale prompts in production.

**Model recommendation for PyTest Creator's default:** `vllm-fast` is the
clear reliability + latency winner (0 errors, fastest by a wide margin) and
was already the workspace default going into this session — this data
confirms, rather than changes, that choice. `vllm-thinking`'s only
justification per SERVER-README is `— tok` cost transparency for Fast vs.
Thinking comparison, not a quality or reliability edge, and this matrix found
no case where `vllm-thinking`'s output was needed over `vllm-fast`'s (both
produced valid, lint-clean structures in Part 2A/this session's live runs).
Among Claude tiers, Haiku was fastest and had zero errors; Opus/Sonnet cost
much more latency per call for output that Part 3's judging (not yet run) is
better positioned to assess for quality than raw token/latency stats can.

### 7.8 Part 2B results — keyword-vs-LLM script search (Step 3)

Captured from the real (non-matrix) `suggest_scripts` calls made while setting
up T33233/T33235 for the matrix (§7.6) — these carry BOTH the mechanical
top-40 rank (`score`) and the LLM's coverage verdict per candidate in one
response, which the plan's own Phase 2B point 1 asks for directly.

- **T33233 (Port Auto Negotiation → searching for MDI/MDI-X scripts):** the
  LLM's kept/re-ranked order was **identical** to the mechanical top-5 by
  score — full agreement, no promotion or demotion. All 18 LLM-kept
  candidates verdicted `partial` (none `full`), all correctly in the
  `legacy/5000_mdi_mdix/*` family.
- **T33235 (Port Speed/Duplex/Polarity):** the LLM **genuinely re-ranked** —
  it promoted `legacy/5703_Speed_Duplex_Polarity/test-5000.1001.py` and
  `.../test-5000.1002.py` (the semantically-correct speed/duplex/polarity test
  family) into the top 2, ahead of `5000_mdi_mdix/*` scripts that scored
  higher on raw keyword overlap (MDI/MDI-X and Speed/Duplex/Polarity share a
  lot of vocabulary — port, speed, duplex, cable, straight/cross — so keyword
  scoring alone under-ranked the better-matching suite). 13 LLM-kept
  candidates, all `partial`.

**Conclusion:** this is exactly the "does the LLM promote genuinely better
scripts or just reshuffle" question Phase 2B asked, answered with two
concrete, opposite examples in the same run: **agreement when the vocabulary
is unambiguous (T33233), real correction when keyword overlap is misleading
(T33235).** Confirms the two-stage keyword→LLM design is earning its keep,
not just adding latency for the same answer.

### 7.9 Claude CLI token accounting caveat (see also §7.5)

The model-comparison table above uses each model's own reported `tok_out`
directly (output tokens are not cache-affected), but Claude's `tok_in` column
was NOT included in the summary table above because it is not comparable
across models as recorded — see §7.5. A fair input-cost comparison would need
`tok_in + tok_in_cache_read + tok_in_cache_creation` for Claude rows against
vLLM's plain `tok_in`; the raw fields for that computation are saved in every
Claude row of the result files (`tok_in_cache_read`/`tok_in_cache_creation`),
just not reduced to one number here.

## 8. Session log — 2026-07-22b — streaming transport (the §7.7 structural fix), built + verified

Implements the fix §7.7 named but left unbuilt: raising the static read timeout
helped but couldn't cover a reasoning phase of arbitrary length, so
`vllm-thinking` still read-timed-out on `generate_script` even at the 600s floor.
Streaming is the structural fix. **Committed at session close; push to main pending (env lacks GitHub SSH auth).**

### 8.1 What changed (`CK_server/llm.py`, OpenAI-compatible branch of `_call_llm_raw`)

- The vLLM/OpenAI-compatible request now sets `stream: true` +
  `stream_options: {include_usage: true}` and consumes the SSE body with
  `requests.post(..., stream=True)` + `resp.iter_lines()`. Streamed `delta.content`
  and `delta.reasoning_content` are accumulated, and the final `finish_reason` +
  usage-only chunk are captured, into the **same `(content, finish, usage)`
  triplet** the non-streamed path produced — so every downstream guard
  (finish_reason=length, null→reasoning_content fallback, mid-JSON truncation) and
  the observability token badges are byte-for-byte unchanged. A reconstructed
  `raw_response` (`{choices:[{message:{content,reasoning_content},finish_reason}],
  usage}`) keeps `normalize_usage` / debug-log / provenance identical.
- **Why this is structural, not just a bigger ceiling:** with a streamed body the
  `read` component of the `(connect, read)` timeout is the max gap *between chunks*,
  not the whole-response wall clock. vLLM emits `reasoning_content` deltas
  throughout the thinking phase, so the socket never goes silent — a reasoning pass
  of *any* length completes as long as chunks keep flowing. The prior fix's static
  600s ceiling could still be exceeded (§7.7: it was); this removes the ceiling
  entirely.
- The Anthropic native path is deliberately left non-streaming — it had no
  structural read-timeout failure in Part 2B (one *harness*-timeout outlier only),
  so its `read` component stays a whole-response budget. Streaming it later is a
  consistency nicety, not a fix.
- The `local_llm` read floor logic (`>=120 → max(.,600)`) is kept; under streaming
  it now floors the inter-chunk-gap tolerance rather than a total ceiling, which is
  generous headroom and harmless.

### 8.2 Verified live against the real org vLLM

- `vllm-fast`, trivial JSON ask: 1.0s, correct content, usage `46 in / 168 out` —
  streaming parse + `include_usage` badges both work.
- `vllm-thinking`, `generate_script`-scale prompt (max_tokens=32000): completed in
  395.6s, `finish=stop`, 15,236-char script, usage populated — a call in the class
  that failed at 600s in Part 2B now succeeds.
- **Ceiling-gone proof:** `vllm-thinking`, large output, deliberately short **30s**
  read timeout — ran **21+ minutes with no read-timeout error** (killed manually for
  time, not by failure). Under the old whole-response semantics a 30s read timeout
  aborts a multi-minute generation at ~30s; surviving 21 min proves the read budget
  is now inter-chunk.

### 8.3 Token-processing-over-time capture (in progress)

Chunk-instrumented capture of the **identical** prompt through both models (same
`max_tokens`, timeout, system) to isolate vLLM structure from model behavior.
Streamed deltas carry no per-chunk token counts, so cumulative *chars* are recorded
per chunk and converted to tokens via the authoritative final
`usage.completion_tokens` ratio (axis labelled as derived, not per-token telemetry).

- **`vllm-fast` baseline (complete):** 48.7s total; **first answer token at 21.3s**
  (the first 21.3s emit only `reasoning_content`); reasoning 15,905 chars / answer
  21,128 chars; 8,733 completion tokens; 8,731 chunks captured (~179/s).
- **`vllm-thinking` (complete, same prompt):** 2,149s total (**35.8 min — 44× slower**),
  `finish=length`, **0 answer characters emitted** — it spent the entire 32,000-token
  budget on reasoning (29,137 reasoning tokens by usage) and hit the cap before ever
  transitioning to the answer. `first_answer_token = none`.
- **Two findings, both material:**
  1. **`vllm-fast` is *also* a reasoning model** — both models reason and stream
     `reasoning_content` throughout; the difference is reasoning-phase
     *duration/volume*, not reasoning-vs-not. Same vLLM SSE structure for both. That
     is exactly why a non-streaming call blows its read timeout during the
     silent-to-the-answer window, and why streaming fixes the *transport* for both.
  2. **Streaming fixes the transport, not the model's fitness.** The 35.8-min
     `vllm-thinking` run *completed* only because streaming kept the socket alive (no
     read-timeout — the old 600s ceiling would have aborted it), **but it produced no
     answer**. So `vllm-thinking` is unfit for `generate_script`-scale generation:
     it can burn the whole token budget on reasoning and emit nothing. This
     *strengthens* the Part 2B recommendation — keep `vllm-fast` as the default;
     streaming does not make the thinking model practical for large output.
- **Infographic (both models' reasoning-vs-answer token curves on a shared token axis,
  own time axes, with hover):** self-contained HTML at
  `ask-ck/pytest-create/comparison/vllm_tokens.html`; also published as a Claude
  artifact. Token axis is derived (streamed chars × each run's final `usage` ratio) —
  labelled as such, not per-token telemetry.

### 8.4 Still deferred

Part 3a/3b. (The `wizard.py` twin of the stale-`llm_config` bug — §7.3 — is now
fixed; see §9.)

## 9. Session log — 2026-07-22b — stale-`llm_config` re-sync (the §7.3 root-cause fix, both routers)

Fixes the root cause §7.3 documented but left unfixed in code (the pytest side was
handled by a one-off data workaround, and the `wizard.py` twin was flagged and
deferred). **Committed at session close; push to main pending (env lacks GitHub SSH auth).**

### 9.1 Root cause (recap) and why the naive fix was avoided

`_llm_is_active()` answers *"can this config drive synthesis?"* — for the headless
CLI modes (`claude_code`/`claude_agent`/`grok_cli`) it returns True
**unconditionally** (correct: there is no server-side key to verify). Both
workspace-apply functions used `_llm_is_active(sess.llm_config)` as their **only**
gate ("apply the workspace default only when the session config is inactive"), so a
session whose *stale* config was a headless mode was judged active → never re-synced
→ kept silently hitting the wrong backend forever (the real T33233 `suggest_scripts`
→ `claude_agent`/Anthropic degrade in §7.3).

`_llm_is_active` is called in ~8 places (status/`has_key`, `_load_global_llm` /
`_save_global_llm` gating, health, both applies), so **changing it** would wrongly
ripple into status reporting and workspace load/save. The fix therefore leaves
`_llm_is_active` untouched and changes only the **apply** functions.

### 9.2 The fix (`routers/wizard.py` + `routers/pytest_create.py`)

Made the **active workspace default authoritative**: re-sync a session's config
whenever the case has no active config **OR** its config diverges from the workspace
default's backend. New helper `wizard._same_backend(a, b)` compares the
dispatch-selecting fields only (`auth_method`/`provider`/`model`, ignoring
credentials); `pytest_create` imports it. Both `_apply_workspace_llm_if_needed`
(wizard) and `_apply_workspace_llm` (pytest) now read the workspace default first
and return no-change only when the current config is active **and** `_same_backend`.

**Why this is safe (proven, not assumed):** every write to a case's `llm_config`
goes through `set_llm_config`, which *always* saves `cfg` as the workspace default
**and** copies the same `cfg` onto the case session — there is **no code path** that
gives a case a config that legitimately differs from the workspace default. So any
divergence is staleness, never an intentional per-case override; there is nothing to
protect. When the workspace default is inactive/absent, the apply returns no-change,
so "the workspace login persists across cases" still holds. Also naturally handles a
Fast↔Thinking switch (workspace flips to `vllm-thinking` → stale `vllm-fast` sessions
re-sync).

**Verified (unit-level, no vLLM):** stale `claude_agent` + `local_llm` workspace →
re-syncs to `vllm-fast`; matching config → no change; divergent model
(`vllm-thinking`) → re-syncs; empty config → applied; inactive/None workspace default
→ untouched; `_same_backend` equal/model-diff/None spot-checks. 8/8 pass.

### 9.3 Concurrency review (why the fix is race-safe)

The apply's read→compare→write runs synchronously in the async handler body (no
`await`/threadpool boundary inside), so it is atomic w.r.t. other coroutines; the
only real parallelism is across threadpool threads, each with its own SQLite
connection (`db.get_connection` is thread-local, WAL, `busy_timeout=5000`; session
writes are one atomic `INSERT … ON CONFLICT DO UPDATE`).

- **Different case sessions, concurrent apply** — safe: each writes its own row and
  only *reads* the shared `_workspace_llm` row.
- **Same case session, concurrent requests** — converges: whether they share the
  cached object or one loads a fresh DB copy, **both write the same value** (the
  workspace default), so ordering is irrelevant. The written value is deterministic
  (not derived from the pre-read state), so no lost-update / TOCTOU.
- **`set_llm_config` racing an apply** — improvement: the `_workspace_llm` upsert is
  atomic (never a torn read); worst case an in-flight call uses the just-previous
  default and self-corrects next call. The fix *guarantees* convergence where a
  divergent "active" config previously re-synced never.
- **Write-frequency cost** — bounded: one extra persist per divergent session, once,
  then it matches and stops. Absorbed by WAL + `busy_timeout`.

### 9.4 Pre-existing debt surfaced (NOT introduced by this fix): dual-instance sessions

`sessions[key]` (in-memory) vs a fresh `_load_persisted(key)` copy can produce **two
live object instances for one key** across concurrent requests; last-persist-wins can
then drop the *other request's unrelated* state (e.g. a confirm flag). This is a
general session-consistency gap independent of `llm_config` (which converges to the
same value, so this fix neither creates nor worsens it). Proper closure would be a
single-flight guard per session key, or a `updated_at`/version compare-and-swap on
`db.save_session`. Left as tracked debt; not a blocker for the re-sync fix.

## 10. Session log — 2026-07-27 — Part 3a kickoff: the mechanical grader

Starting Part 3 (grading). This session built the mechanical half — criteria 1-3 and the
offline half of 6 — and corrected three things the plan itself had wrong.

### 10.1 Judges CHANGED: Claude Opus + vLLM-**fast** (was Opus + vLLM-thinking)

§5 decision-3 settled on Opus + vllm-thinking ("the theoretical best of each family").
**Terrence changed this to Opus + vllm-fast on 2026-07-27.** Rationale: §8.3 measured
`vllm-thinking` burning its entire 32,000-token budget on reasoning and emitting **zero
answer characters** on a generate-scale prompt. Judging prompts are much smaller, so the
failure was not certain to recur — but vllm-fast had 0 errors across the whole Part 2B
matrix, and a judge that can return nothing is a poor judge.

**Known trade-off, recorded rather than glossed:** vllm-fast is also the *generator's*
default model, so one judge now shares the generator's model. That is a weaker
independent check than the original cross-family pairing intended. The human holistic
review (unchanged) is what carries the independence.

### 10.2 Doc corrections found by checking the live system

- **tb470 `configs/` path was wrong** — see the correction note in §5b. It is
  `/home/st-art/st-art/configs/` (473 `.setup` files), not under `framework/`.
- **`tb470.setup` still does not exist** — re-verified. **Part 3b stays blocked**;
  Part 3a does not depend on it.

### 10.3 T33235 generated (it had no script at all)

Part 3 needs three scripts; T33235's session stopped at step 5 with `decision: new` and
**zero fragments** — the pure gap-fill case, and the most interesting one for criterion 4.
Generated on vllm-fast: 70s, lint-clean, 7 TestCases for 7 verify steps.

**Criterion-4 defect to put in front of the judges:** its step 6 is a *physical*
hot-insert/hot-remove step, and the model rendered it as `shutdown` / `no shutdown` — a
link bounce, **not** a real cable/SFP removal. Physical steps are meant to prompt and wait
for a state change. The script was left exactly as generated so the judging surfaces this
rather than hiding it behind a manual fix.

### 10.4 The grader — `tool/pt_grade.py`

Reads the generated script + confirmed step2/step5 state straight from `ck.db` and emits a
per-case report. **It imports the server's own `_step_kind` / `_fragment_tag` /
`_frag_key` rather than reimplementing them**, so a change to generation can never leave
grading silently measuring something else. No LLM, no network, no hardware.

Four things it gets right that a naive version does not — each one a real wrong answer
caught against the live sessions, now pinned by `tests/test_pt_grade.py` (21 tests):

1. **Grades the reviewer-SELECTED fragment subset, not the whole pool.** T33233 has 13
   selected out of 41 gathered; grading the pool expects tags for fragments the model was
   never shown, producing a bogus "not at all". (A *missing* `selected` key still means
   "all of them" — the documented back-compat path, and why T33234's 7 legitimately
   grade 14/14.)
2. **Distinguishes STALE provenance from model failure.** If none of a script's stamped
   tags name a currently-selected fragment, the script predates a later step5 change. That
   is drift, not the model ignoring its snippets, and it now reports `stale` with an
   instruction to regenerate — instead of blaming the generator for a reviewer's edit.
3. **Does not downgrade correctly ADAPTED reuse.** T33234 stamps 14/14 correct tags at an
   average literal line overlap of **0.012** — because the model rewrote each fragment
   into the template's bound device names and the mandatory logging contract. Verbatim
   copying was never the goal (§1.4 leaves `main()` bodies free), so overlap is *reported*
   for the judges to interpret but does not move the verdict.
4. **Reads the FIRST tag in each `main()`.** `_restamp_provenance` guarantees the
   authoritative tag is inserted first, so a later model echo cannot fool the grade.

It also emits **caveats** — step5/step6 unconfirmed, step6 invalidated, or generated by a
headless-CLI `model='default'` — so no verdict is ever read at face value off a stale or
unreviewed artifact.

### 10.5 Results (criteria 1-3 + 6-offline, all three cases)

Artifacts: `ask-ck/pytest-create/judging/Port (7)/<CaseKey>/mechanical.json`.

| Case | C1 template | C2 snippets | C3 order | C6 logging (offline) |
|---|---|---|---|---|
| T33233 | **exactly** (12/12) | **stale** — regenerate | n-a | **yes** (12/12) |
| T33234 | **exactly** (14/14) | **exactly** (tags 14/14, overlap 0.012) | **right** | **yes** (14/14) |
| T33235 | **exactly** (7/7) | n-a (zero fragments) | n-a | **yes** (7/7) |

**C1 and C6-offline are clean across all three** — the Part 1 template plus the lint
conformance check are doing exactly what they were built to do: every TestCase carries the
three `testCase*` attrs, a `STEP <n>:` start log, an `OBSERVED:` evidence log, and a
non-empty verdict, with `__main__` adding every case in order.

### 10.6 Two findings worth acting on

1. **T33233's script is stale AND was generated by the wrong backend**
   (`claude_agent`/`model=default`, 2026-07-22) — so it is not comparable to the two
   vllm-fast scripts. It **cannot be regenerated until step5 is confirmed** (the router
   correctly refuses: *"Generation requires step5 to be confirmed first"*). That is a
   human-review gate, so it is Terrence's call, not something to bypass. **T33234's step5
   is likewise unconfirmed.**
2. **`_restamp_provenance` echo-strip has a residual gap** (distinct from the one §7.1
   fixed). It strips the leading *contiguous* run of comment lines, so an echo the model
   places *below* real code survives — observed on **all 7** of T33235's TestCases
   (`# Provenance tag for this fragment: AI vllm-fast 2026-07-27` sitting under a
   `self.log()`). Cosmetic only: the authoritative tag is still present and first, and the
   grader reads the first tag. T33233/T33234 (which have real fragments to anchor the
   instruction) are unaffected. **Not fixed this session** — it is a display wart in the
   generator, not a grading defect, and fixing it mid-grading would change the artifacts
   being graded.

### 10.7 Step numbering: internal keys ≠ UI numbers (gate messages fixed)

Terrence spotted that the 409 quoted in §10.6 — *"Generation requires step5 to be
confirmed first"* — is a **typo in the product**, not just in this doc. The internal
`stepN` session keys and the numbers on screen diverged when the old step 4 (Fit
Decision) was folded into Fragments:

| Internal key | UI panel (badge id) |
|---|---|
| `step2` | 2. Sequence (`pt-badge-2`) |
| `step3` | 3. Script Search (`pt-badge-3`) |
| `step4` | *(folded into Fragments; no panel)* |
| **`step5`** | **4. Fragments** (`pt-badge-5`) |
| **`step6`** | **5. Generate** (`pt-badge-6`) |
| `step7` | 6. Run (`pt-badge-7`) |
| `step8` | 7. Validate (`pt-badge-8`) |

So the message told a user blocked on **Fragments** that "step5" needed confirming — and
`step5` is the number the UI prints on **Generate**, i.e. it named the very step they were
trying to run. Maximally confusing.

**Fixed:** one `_STEP_UI_LABEL` map + `_step_label()` (accepts either a `stepN` key or the
bare int from the URL, and degrades to the raw value rather than raising inside an error
path). All 7 `_require_confirmed` call sites and both `confirm_step` messages route
through it. Verified live:

- `Generation requires '4. Fragments' to be confirmed first.`
- `Execution requires '5. Generate' to be confirmed first.`
- `Nothing to confirm yet for '6. Run' (missing runs).`

`tests/test_pt_step_labels.py` (7 tests) pins it, including one that **parses the real
`index.html`** and asserts every panel heading matches the code's label — so a future
renumber breaks a test instead of silently reintroducing wrong messages.

### 10.8 T33233 regenerated — all three cases now clean

Terrence confirmed T33233's Fragments (13 of 41) mid-session, which opened the gate; it
regenerated on **vllm-fast** (iteration 2, 29,881 chars, lint-clean). All three scripts
are now same-backend comparable, and **C2 went stale → EXACTLY** (tags 10/10, order
right). Updated `mechanical.json` written for all three.

| Case | C1 template | C2 snippets | C3 order | C6 logging (offline) |
|---|---|---|---|---|
| T33233 | exactly (12/12) | **exactly** (10/10, overlap 0.057) | **right** | yes (12/12) |
| T33234 | exactly (14/14) | exactly (14/14, overlap 0.012) | right | yes (14/14) |
| T33235 | exactly (7/7) | n-a (zero fragments) | n-a | yes (7/7) |

**Every mechanical criterion now passes on every case.** Criterion 4 (the two judges) is
what remains offline.

Correction to §10.6's second finding: the duplicate-tag wart is **not** specific to
zero-fragment cases — T33233's regenerate reproduced it on all 10 fragment-backed blocks.
Still cosmetic (the authoritative tag is first and the grader reads that), still unfixed.

### 10.9 Remaining for Part 3

- ~~Confirm step5 on T33233~~ — DONE, regenerated on vllm-fast (§10.8). **T33234's
  Fragments gate is still unconfirmed** (its script is already vllm-fast, so this is a
  review-hygiene gap, not a comparability one).
- **Criterion 4** — the two LLM judges (Opus + vllm-fast) over the gap-fill logic, then
  the human holistic review. The T33235 physical-step defect (§10.3) is the known one to
  watch for.
- **Criteria 5-6 on hardware** — still blocked on `tb470.setup`.

## 11. Session log — 2026-07-27h — CLI grounding, objective-coverage gate, re-judging

Started from Part 3a's criterion-4 result (all 9 gap-fill blocks "bad") and Terrence's
question: is the generator-prompt the problem? Five questions were asked and answered
against the live corpus + the real CLI documentation.

### 11.1 The five questions, answered with evidence

1. **Is the generated syntax correct?** Python: yes (lint-clean, real framework calls).
   CLI *commands*: yes (`speed`, `duplex`, `polarity` all verified real). CLI *output
   assertions*: **fabricated** — the whole defect.
2. **Is it a resourcing problem?** **Yes.** The generate prompt named `show interface` 27
   times and contained ZERO examples of its output (`port1.0` count 0, `awplus` 0).
3. **Different valid syntax, or hallucinated?** Hallucinated, but coherently — a
   plausible invented schema applied consistently 57 times, not random noise.
4. **Best-effort or garbage?** Best-effort. The proof is the split: fragment-backed cases
   (T33233/T33234) fabricated **zero**; only the zero-fragment case (T33235) did. Reused
   fragments already act as grounding.
5. **How many models?** 5 models × 3 cases, one run each (11/15 succeeded). **Every model
   fabricated on T33235** — vllm-fast 39, vllm-thinking 52, haiku 13, sonnet 39, **opus
   35**. A defect that survives Opus is not fixable by swapping models.

### 11.2 The source: docs.atlnz.lc (Terrence's pointer)

37 product command references, ~2,900 unique commands, ~73,000 product×command pages.
Measured facts that drove the design:
- A command page's content is **byte-identical across families ~96%** of the time
  (23/24 sampled), so content is CONTENT-ADDRESSED and stored once; per-product rows are
  a thin support matrix. Dedupe factor ~4.7x.
- Pages are ~630KB but only ~0.3% is real content (the rest is an inlined nav tree).
- `/<product>/index.html` is a META-REFRESH — `curl -L` will NOT follow it.
- **WebFetch's markdown conversion DROPS `<pre>` blocks**; raw HTML + regex is required.
- The site is mid-build and serves **soft 404s** (HTTP 200 + "may have moved in the
  latest rebuild"). Detected and counted separately so they can't poison the reference.

**Terrence's rule confirmed:** commands are standard across devices; only feature
*support* varies. The `duplex` difference (`{auto|full|half}` vs `{auto|full}`) is a
consequence of **half duplex being impossible at ≥1 Gig** — devices whose ports don't go
below 1 Gig can't offer it. **That constraint is NOT documented anywhere**; it is only
visible in the diff between families. It IS recoverable from the ART corpus, which pairs
`duplex half` with ≥1 Gig **zero times** in 830 scripts.

### 11.3 What was built

- **`tool/harvest_cli_docs.py`** — renewable harvest into `ck.db` (`cli_commands` +
  `cli_command_products` + FTS). Full run: **73,006 fetches, 58.6 min, 0 failures**,
  4,652 unique commands (993 with sample output), 61,240 product×command rows.
- **`tool/cli_lookup.py`** — retrieval + `prompt_block()` for prompt injection, and
  `detect_commands()` so only commands the case actually references are injected.
- **Grounding wired into BOTH prompts** — step 2 (`_cli_reference_for_case`, capped at 8
  output lines, 300-800 chars) and step 6 (`_cli_reference_block`, ~1.9k chars).
- **`tool/pt_compare_runs.py`** — snapshot/compare grading runs across sessions, so
  "did this help, did anything regress" is answerable without re-deriving it.

### 11.4 The fabrication originates at STEP 2, not step 6

Found while asking why the generate prompt is 26k chars. `speed=1000` lands in each
step's `verify` text at Sequence Extraction, and `_render_skeleton` stamps it into the
skeleton **4x per TestCase**. Step 6 was being *obedient*.

| Case | step2 `key=value` | step6 `key=value` |
|---|---|---|
| T33233 | 0 | 0 |
| T33234 | 0 | 0 |
| T33235 | 13 | **57** |

Perfect correlation — which is why grounding step 6 alone would have left the generator
arguing with its own skeleton.

**Prompt composition (26,043 chars):** skeleton **62%** (7,213 chars of which are
`# >>> FILL <<<` comments the model is then told to delete), framework surface 15%,
rules 12%, CLI grounding 7%. Trimming the scaffolding is a real opportunity, not done.

### 11.5 Objective-coverage gate (Terrence's invariant)

> Every objective has to link to a Zephyr step; every Zephyr step needs at least one
> PyTest step. Otherwise the objectives aren't being tested.

Prompted by a real regression: re-extracting T33234 went 14 → 9 steps and **silently
dropped source step 4** — "configure one side to Auto and the other to forced MDI/MDIX …
correct link-down behavior in incompatible combinations", i.e. the entire negative path
of an MDI/MDI-X test, which the old sequence covered with 4 dedicated entries. Nothing
absorbed it. Cause: the grounding pushed the model to reclassify partner-side config as
`physical` operator prompts, collapsing the matrix into one prompt.

**Enforced at the Confirm button** (Terrence's call — Generate still completes, because
the script is useful to look at and the reviewer may fix and regenerate):
- `_coverage_report()` — mechanical, also recorded on `extract_sequence`/`save_sequence`.
- `_coverage_gate_error()` — a 409 on `confirm_step` for **'2. Sequence'** and
  **'5. Generate'** that QUOTES each untested Zephyr step (an index alone is not
  actionable). Generate is gated too because a case can arrive with zero fragments
  (T33235), so the fragment gates prove nothing about coverage.
- Override: `{"acknowledge_coverage_gap": true}` — a recorded decision, not a silent pass.
- At Generate it also checks TestCase count vs non-setup steps, catching "the sequence
  covered it but the script skipped it".

Prompt rules added to match: coverage is mandatory; merging must not cross source steps;
a source step describing COMBINATIONS needs one entry per combination **including the
negative cases**; don't downgrade automatable partner config into an operator prompt.

### 11.6 Measured result

| | before | after |
|---|---|---|
| T33235 `key=value` in sequence | 13 | **0** |
| T33235 `key=value` in script | 57 | **0** |
| T33233 placeholder `portA` refs | 13 | **0** |
| real CLI formats quoted per case | 0 | 14-23 |
| objective coverage | unmeasured | **3/3 cases complete** |

Mechanical grades after regeneration — **all three clean**:

| Case | C1 | C2 | C3 | C6 | lint |
|---|---|---|---|---|---|
| T33233 | exactly (11/11) | exactly (9/9) | right | yes | ok |
| T33234 | exactly (12/12) | n-a (0 frags) | n-a | yes | ok |
| T33235 | exactly (6/6) | **exactly (6/6)** | **right** | yes | **fails** (see 11.7) |

T33235 is the headline: it previously had zero fragments and graded `n-a`; the grounded
sequence gave script-search better terms, so it now finds 14 fragments and grades
C2 *exactly* / C3 *right*.

### 11.7 Regressions the grounding itself caused (found + fixed, except one)

Each was caught by checking output rather than trusting the change:
1. **`speed 2000`** — an invented value. The prompt showed valid syntax but never said
   arguments must come FROM it. Fixed with an explicit argument rule; now emits
   `speed 2500 (unsupported on 1G copper)`, which is what the source step actually asks.
2. **`show interface eth1`** — `prompt_block` picked the LONGEST sample output, which was
   the TQ wireless AP's *router* interface, not a switch port. Fixed to prefer the
   variant the MOST product families share. (A caveat on "commands are standard": the
   command is, but sample OUTPUT is family-specific, and picking wrong is silent.)
3. **`self.dut.port1.0.1`** — a SyntaxError; the model used a CLI port name as a Python
   attribute. Fixed with a "port name is CLI TEXT, never an identifier" rule.
4. **`framework.ATLibrary` — FIXED 2026-07-28, and it was not a hallucination.** The
   import is valid: `ATLibrary` is a real framework package. The **lint** was wrong.
   `framework_surface` is keyed by module path only (`ATLibrary.ATTools`,
   `ATLibrary.__init__`), so a package never appears as a bare key — a plain membership
   test rejected every package import, and `from framework.ATDrivers import ATSwitch`
   was equally an error. `ATDrivers` passed *only* because it was hardcoded in an
   allowlist, though the index shape for the two packages is identical. The check now
   resolves packages from the index (`<pkg>.__init__` / dotted-key prefix) and the
   allowlist is deleted — all six formerly-exempt names are genuine keys, so they pass
   on the data. T33235 re-lints clean (0 errors, 0 warnings) with **no change to the
   generated code**; `mechanical.json` `lint_ok` corrected to True. Covered by
   `tests/test_framework_import_lint.py` (19 tests), including a source guard against a
   new allowlist and an AST check that the live helper accepts the same set.
   *Takeaway: a lint that rejects valid code reads exactly like a model defect — the
   "hallucination" label was assumed from the error text, never checked against the
   framework tree.*

### 11.8 Product debt found: writes can silently not persist

Repeatedly hit while re-extracting: the server returns **HTTP 200 with correct new data
that never reaches `ck.db`**. `db.get_connection()` caches one SQLite connection per
thread; after an external process writes to `ck.db`, those long-lived connections hold a
stale WAL snapshot, and `_pt_persist` swallows the failure into a `print` that never
fired. Symptom: endpoint returns 13 steps, DB still has 0, `updated_at` unchanged.

Workaround used: `./run.sh --restart` around any external write, then verify `updated_at`
from a fresh connection — never trust the 200. Fix candidates: drop/refresh the
thread-local cache, and make `_pt_persist` surface failures instead of printing. Related
to the §9.4 dual-instance debt but worse, because it presents as success.

---

## §12 — Feature grounding: the LPI/EcoMode false green (2026-07-28)

Closes the criterion-4 defect from §11: *"verification that checks link state but never the
feature under test."* Terrence identified the cause — the whole `ecomode` CLI command tree
was never passed to the prompt. It is **`ecofriendly`** in AW+, it was in `ck.db` all along,
and two independent defects kept it out.

### 12.1 Two defects, not one

1. **`detect_commands()` is purely lexical.** A feature named in PROSE has no path to its
   commands: "EcoMode", "LPI" and "EEE" appear nowhere inside `ecofriendly lpi`. No matcher
   tuning bridges that, so `FEATURE_ALIASES` (`tool/cli_lookup.py`) maps feature prose →
   command tree + the output terms that prove the field. Hand-curated deliberately: a wrong
   alias injects confidently-wrong grounding, which is worse than none.
2. **Variant selection hid the field under test — the sharp one.** `prompt_block()` preferred
   the variant with the most product families; only one of eight `show interface` variants
   prints `current ecofriendly lpi`. Three of the four affected steps were therefore grounded
   on authoritative output with **no** EEE field *while being told "match these formats
   exactly, do NOT invent output tokens"* — so asserting on link state was nearly the only
   move left. **The grounding steered the model into the false green.** Fixed with graded
   relevance ranking (count term hits, then breadth, then length), a family-specific NOTE
   when the chosen variant shows a field others omit, and a guarantee that the feature line
   is never trimmed away by `max_output_lines`.

Note the coupling: defect 2 is the same failure mode as the earlier `show interface eth1`
regression, and the fix for *that* one (prefer most-shared) is what caused this one. The
eth1 guard in `tests/test_cli_feature_grounding.py` is load-bearing.

### 12.2 Result (graded, same judge panel as the baseline)

| | before | after |
|---|---|---|
| T33233 gap-fill blocks | 2 of 11 (`bad×11, good×1`) | **0** — every TestCase reuses real code |
| T33234 gap-fill blocks | **12 of 12** (`bad×63, good×9`) | **1 of 14** (`bad×5, good×1`) |
| T33234 fragments selected | 0 of 7 | **11 of 23** |
| lint / C1 / C2 / C3 / C6 | — | clean / exactly / exactly / right / yes (both) |

T33234's 12→1 collapse also answers the §4 open question "is the LLM right that none of its
7 fragments are reusable?" — it was the vague sequence starving script-search, not a
selection bug. The one surviving block (TestCase_8, step 9) is unrelated to LPI: the judges
are near-unanimous that it configures the partner's `polarity mdi` but never sets the local
port to `polarity auto`. Real signal, still open.

Generated code now enters interface config mode, runs `show ecofriendly`, selects the row for
the port under test and asserts `Configured`/`Status` — not link state.

### 12.3 Terminology (from Terrence) — recorded because it was got wrong twice

- **`ecofriendly` is the proper CLI name; "ecomode" is slang.** Slang is recognised on the
  INPUT side only and never emitted, because TestLink/Zephyr authors write it.
- **`lpi` is deprecated terminology** — modern diagnostics say EEE (`show platform port`
  prints `EEE Admin Status`), and `lpi` survives in exactly one command name. It stays
  first-class regardless: it is the only spelling the config command accepts, it is the live
  `Configured`/`Status` value in `show ecofriendly`, and **TestLink cases are several years
  old and almost unanimously say LPI** — TestLink being the corpus reused fragments come
  from. Deprecated-as-terminology does not make a string wrong to match on.
- **`port1.1.x` is not "legacy".** The `show interface` variant printing
  `current ecofriendly lpi` covers x8100/x908gen2/x908gen3 and uses `port1.1.x`; both traits
  track **chassis vs standalone, not firmware age**. x908gen3 is current (x8100 is the old
  one in that generational family), and **an x950 with a populated card slot also uses
  `port1.1.x`**. Port naming is a RUNTIME hardware property. An earlier draft of this work
  called that variant "deprecated output on old families" — wrong on both counts.

### 12.4 Port names come from the topology

The skeleton seeded `port = 'portX.Y.Z'` and the generate prompt explicitly instructed *"a
string variable (`port = 'port1.0.1'`)"* — the origin of hardcoded ports, and wrong on any
chassis or populated-slot x950. Both now bind from the `.setup` topology via the attribute
`init_portlink()` binds, matching the corpus (**10,578** bound-attribute uses vs **125**
literals, and those are mostly negative-test inputs).

Backed by a comment-aware lint **warning** — warning, not error, because a deliberately
invalid literal fed to a negative test is legitimate; the reviewer decides. It caught 3 real
hardcodes on a regeneration, so the defect is live and model-dependent rather than fixed by
prompt guidance alone. (First cut of the check flagged the skeleton's own guidance comment
where it quoted an example — a warning against its own advice; comments are now skipped.)

### 12.5 Hardware-agnostic is the GOAL, not a fallback (Terrence, 2026-07-28)

An earlier draft of §12.5 framed threading the DUT platform into grounding as making it
"hardware-accurate rather than best-guess". **Both halves of that framing were wrong.**

> *"These scripts should be Hardware-Agnostic, should run on all platforms. The CLI doesn't
> deviate too terribly much between platforms, and as such the scripts should be robust
> enough to be used interchangeably."*

So `prompt_block(product=...)` is deliberately **left unpassed**. Tuning the reference to one
platform would push generated code toward platform-specific output shapes — the opposite of
interchangeable. Breadth-based variant selection is CORRECT: it picks what most families
share. Relevance ranking only breaks ties toward a variant that actually shows the field
under test, which does not narrow the platform.

The `.setup` file is the mechanism that delivers agnosticism. Ports are never named in the
script; `[portlink]` resolves them at runtime, which is exactly why the same code runs on an
x930, an AR4050S and an x530 — and yields `port1.1.x` on a chassis or a populated-slot x950
without a source change.

    [switch]
    swi_a = /dev/u0
    swi_c = /dev/u1
    swi_d = /dev/u2

    [portlink]
    tb-swi_a  = eth2-port1.0.15
    swi_a-swi_c = port1.0.1-port1.0.1,port1.0.3-port1.0.2,port1.0.5-port1.0.3

**Two layers, and conflating them broke the first generated scripts.** The lookup STRING is
the `[switch]` key; the local VARIABLE carries the role:

    dutA   = setup.init_swi('swi_a')      # 621 of ~650 corpus calls use swi_a/swi_b/...
    swiSrc = setup.init_swi('swi_c')
    (swiSrc.portTB, tb.ethSrc) = setup.init_portlink(swiSrc, tb, type1='port')

The generator emitted `init_swi('dut')` / `init_swi('linkP')` from role names, which fails
against any real `.setup`. `_setup_keys_for()` now maps roles → `swi_a/swi_b/...`
positionally, passing through names that already look like keys. Also note `[stack]` takes a
member list (`stk_a = swi_a, swi_b`), non-default stackports need `[configured_stackport]`,
and `[boot_from_flash]` is emptied when booting over TFTP.

**A guaranteed-crash bug this surfaced.** The scripts ran
`init_portlink(self.dut, ...)` three lines ABOVE `self.dut = dut` — an `AttributeError` the
moment `init()` is called, so the script could not run at all. Valid syntax, so `py_compile`
passed and no structural check caught it. Now a lint **ERROR** (not a warning: it is a
certain crash), plus the FILL slot says to use the local variables. Both cases regenerate
clean.

### 12.6 Not addressed

The one criterion-4 block still judged `bad` (T33234 TestCase_8, step 9) is unrelated to
LPI: it configures the partner's `polarity mdi` but never sets the local port to
`polarity auto`. Judges near-unanimous (5 bad / 1 good). Real signal, still open.
