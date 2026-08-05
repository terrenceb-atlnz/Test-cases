---
name: pipeline-layer-contract
description: What each pipeline stage is FOR — the Test Case Generator drafts platform-agnostic manual cases, the PyTest script proves them with real CLI; rules must not migrate between layers
metadata:
  type: project
---

**The two halves of this pipeline have different jobs, and rules keep migrating between them.**
Three of the four drift items reversed on 2026-08-05 were layer violations — a rule correct at
one stage applied at another.

**The one-line version: the manual case is deliberately NON-prescriptive, and Creator step 2 is
where prescription is supposed to enter** (`PLAN-pytest-creator.md:128` — *"extract a
**prescriptive** test-step sequence from a completed case"*). Every bleedover reversed on
2026-08-05 was prescription arriving one stage too early.

| Stage | Produces | Is FOR | Must NOT | Spec |
|---|---|---|---|---|
| Wizard step 4 — objective | `<ul>` of artefact bullets | declarative END STATES, platform-agnostic, reusable across similar cases | procedure, values, device specifics | `OBJECTIVE_DRAFTING_PROCESS.md` Step 1 |
| Wizard step 5 — steps | Zephyr manual `testScript` | a PROCEDURE a human executes; high-level enough to be reusable, specific enough to be testable | expected results ([[expected-results-deliberately-absent]]), exact values/counts/timings, CLI commands, device registers | `OBJECTIVE_DRAFTING_PROCESS.md` Step 2 |
| Creator step 2 — sequence | `[{n, action, verify, kind, zephyr_step_idx}]` | making the case PRESCRIPTIVE and automatable; classifies each step setup/verify/physical/manual | lose coverage — each entry covers exactly ONE `zephyr_step_idx`, merging must not drop a source step | `PLAN-pytest-creator.md` :128, :37, :189 |
| Creator step 6 — script | runnable `framework` script | filling the fixed frame's free slots so a run emits ONE clean PASS/FAIL block per step; `show` output is the OBSERVED evidence inside a marker | alter the fixed frame; put `passed()`/`failed()` in `configure()`/`tear_down()` (setup, not a test); empty `passed()`/`failed()` (emits no marker); hand-write timestamps / `>>` / `TEST_CASE_*` blocks (the framework's — duplicating corrupts parsing) | `TEMPLATE-SPEC.md`, `LOGGING-CONTRACT.md` |

**Step 6's job is the MARKERS, not the CLI.** `LOGGING-CONTRACT.md` §2: *"The script's job is
only to emit the right PASS/FAIL markers inside each case."* A script with perfect `show`
capture and an empty `passed()` produces no per-step evidence at all and fails criterion 6.

**Terrence, 2026-08-05:** *"Show commands should be baked into the scripts in order to prove
that the step was taken. How do we know the link came up if we dont look at sh int status
output? Still a very useful command to use, but NOT in the Test Case Generator module."*

So `show` output, exact speeds/timings and CLI field names belong in the generated SCRIPT.
Phase 4's CLI grounding is correctly scoped to `pt_extract_sequence.jinja` and
`pt_generate_script.jinja` — **do not extend it to the wizard prompts.** That was tried on
2026-08-05 (a `cli_grounding.py` leaf module) and reverted wholesale: the fabricated
"advertised-capability counter" it was built to prevent only existed because the steps prompt
had been told to state measurable outcomes, which is the script's job. Removing the demand
removed the need for the grounding.

**The authority for the wizard layer is `ask-ck/objective-drafting/OBJECTIVE_DRAFTING_PROCESS.md`**,
Steps 1 and 2 — not the prompt files. Its banner disclaims only the data-access paths and
explicitly vouches for the METHOD, and on every point checked so far the doc was right and
`generate_steps.jinja` had drifted. See [[scoped-directives-stay-scoped]].
