# PyTest Creator — Testing & Standardization Plan

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
> - ⏳ **Part 3a/3b** (judging + tb470 execution) — pending. Part 3b gated on
>   `configs/tb470.setup` + a testbox profile (Terrence-side physical-topology
>   prerequisite — see §5b).
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
- **State on tb470 now:** `configs/` has other testboxes' `.setup` files but **neither
  `tb470.setup` nor `tb470.cfg` exists yet.** Both are Terrence-side prerequisites
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
