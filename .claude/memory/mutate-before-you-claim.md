---
name: mutate-before-you-claim
description: "Run mutation checks BEFORE writing up a diagnosis — twice in one session a mutation disproved a \"bug fix\" claim I had already written"
metadata: 
  verified: 2026-08-31
  node_type: memory
  type: feedback
  originSessionId: 5eff94ba-b305-4e2c-8e60-efda5ba8e420
  modified: 2026-07-28T00:28:21.593Z
---

Run the mutation checks **before** writing the commit message or telling the user what a
change fixes — not after. A green test proves nothing about the diagnosis; only a mutation
that fails to turn it red exposes a wrong claim.

**Why:** on 2026-07-28 this caught two overclaims in one session, both already written up
as bug fixes:

1. `_pt_get`'s stamp comparison — I wrote that switching from string compare to parsed
   compare fixed a live data-loss path. Reverting to the string compare left every test
   green. Enumerating the 8 reachable stamp shapes showed the two strategies **agree**
   once the model coerces stamps to aware; it was defence-in-depth, not a fix.
2. `_coerce_utc(None)` — a mutation making it fabricate a stamp stayed green, because
   pydantic resolves `None` on an `Optional[...]` union *before* the annotated member's
   `BeforeValidator` runs, and an omitted field skips validation entirely. The branch was
   unreachable dead code.

A mutation that stays green is the *valuable* result, not a nuisance: both times it
pointed at something real (an overclaim, and dead code).

**How to apply:** for each behavioural claim, revert exactly that behaviour and re-run the
targeted tests. If green, the claim is wrong or the code is unreachable — investigate which
before writing prose. When measurement contradicts a plan document, fix the document too;
see [[generator-steps-uniform-deferred-load]] for the plan whose own dead-code list was
wrong. Related: [[checks-must-not-match-their-own-advice]] (prefer AST over grep when the
target is Python, since docstrings explaining an antipattern contain it).
