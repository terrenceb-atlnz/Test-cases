---
name: expected-results-deliberately-absent
description: Zephyr manual test steps deliberately carry NO expectedResult — specifying it skews testers toward producing the stated result instead of evidence of function
metadata:
  type: feedback
---

**Zephyr manual test steps are meant to have EMPTY `expectedResult`.** This is a deliberate
test-design ruling by Terrence, not an unfinished corpus. It has been re-litigated at least
once (2026-08-03) because it was never written down.

**Why:** a human reading the objective plus a *non-prescriptive* step can contextually reason
what the expected result should be. Specifying it does active harm — it skews manual results,
because a tester will perform the test in whatever way produces exactly the stated result,
rather than producing **evidence of function**. The objective already carries the expected
outcomes: `pt_generate_script.jinja` rule 1a calls the objective bullets "the AUTHORITATIVE
expected results the whole script exists to prove". A per-step expected result duplicates that
and narrows it.

`OBJECTIVE_DRAFTING_PROCESS.md` Step 2 ("`expectedResult` is typically left empty") is the
ORIGINAL and CORRECT spec. `generate_steps.jinja`'s "EVERY step must have a non-empty
expectedResult" is the deviation — introduced by D-12 (`f0a94af`) hours after Phase −1
(`949004f`) added a push gate asserting "a step with no expected result is not a test", then
justified by that same gate refusing the corpus. Circular: the plan's goal was "a test actually
ran" (script execution), and step drafting was swept in as an obstacle, never reviewed as a
Test Case Generator design question.

**Nothing depends on the field.** It is optional prompt context at sequence extraction and a
column in the Zephyr payload. No assertion, verdict, lint or downstream logic consumes it — see
[[cli-fabrication-originates-step2]] for what the script pipeline actually grounds on.

**How to apply:** do not treat blank `expectedResult` as a defect, and do not add checks that
score it. Anything enforcing non-empty rests on the rejected premise: the prompt rule,
`upload_refined.validate_for_push`'s blank rule, and `llm.steps_compliance()`'s `compliant`
flag. Grounding steps in real device output ([[prompt-examples-are-the-spec]]) is a SEPARATE
and still-valid concern — do not revert that with this.
