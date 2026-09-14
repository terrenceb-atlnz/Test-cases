---
name: expected-results-deliberately-absent
description: Zephyr manual test steps deliberately carry NO expectedResult — specifying it skews testers toward producing the stated result instead of evidence of function
metadata:
  type: feedback
  verified: 2026-09-14
---

**Zephyr manual test steps are meant to have EMPTY `expectedResult`.** This is a deliberate
test-design ruling by Terrence, not an unfinished corpus. It has been re-litigated at least
once (2026-08-03) because it was never written down.

**Why:** a human reading the objective plus a *non-prescriptive* step can contextually reason
what the expected result should be. Specifying it does active harm — it skews manual results,
because a tester will perform the test in whatever way produces exactly the stated result,
rather than producing **evidence of function**. The objective already carries the expected
outcomes: rule 1a in `pt_fill_rules.jinja` (the rules block the Generate prompts share) calls the objective bullets "the AUTHORITATIVE
expected results the whole script exists to prove". A per-step expected result duplicates that
and narrows it.

`OBJECTIVE_DRAFTING_PROCESS.md` Step 2 ("`expectedResult` is typically left empty") is the
ORIGINAL and CORRECT spec. `generate_steps.jinja`'s "EVERY step must have a non-empty
expectedResult" was the deviation (reversed 2026-08-05 — the prompt now says LEAVE `expectedResult`
EMPTY) — introduced by D-12 (`f0a94af`) hours after Phase −1
(`949004f`) added a push gate asserting "a step with no expected result is not a test", then
justified by that same gate refusing the corpus. Circular: the plan's goal was "a test actually
ran" (script execution), and step drafting was swept in as an obstacle, never reviewed as a
Test Case Generator design question.

**Nothing depends on the field.** It is optional prompt context at sequence extraction and a
column in the Zephyr payload. No assertion, verdict, lint or downstream logic consumes it — see
[[cli-fabrication-originates-step2]] for what the script pipeline actually grounds on.

**How to apply:** do not treat blank `expectedResult` as a defect, and do not add checks that
score it. Everything that enforced non-empty rested on the rejected premise and is gone (re-checked
2026-09-14): the prompt rule (reversed), `upload_refined.validate_for_push`'s blank rule (deleted, not
disabled — the module says so in place) and `llm.steps_compliance()` (removed). Do not bring any back. Grounding steps in real device output ([[prompt-examples-are-the-spec]]) is a SEPARATE
and still-valid concern — do not revert that with this.
