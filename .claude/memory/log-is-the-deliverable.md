---
name: log-is-the-deliverable
description: For lab test runs the per-case `<case-id>.log` IS the deliverable — do NOT write an after-action-<id>.md for every test; produce a write-up only when Terrence asks for one
metadata:
  node_type: memory
  type: feedback
---

Terrence, 2026-08-18, after a run of five IE520 stack test cases: *"we dont need write-ups
for everything, the .log is enough."*

So the default deliverable for a hardware test case is a well-structured
`<case-id>.log` in the run directory — nothing else. An `after-action-<id>.md` is written
**only when explicitly requested** (as it was for 17688, which was a multi-round defect
investigation worth summarising).

**Why:** the `.log` already carries the whole evidence chain — config applied, commands
issued, raw device output, controls, measurements and verdict. A second document restates
it in prose and is work that was not asked for. This is the same over-production failure as
[[autonomous-judgement-divergence]]: producing artefacts on my own initiative rather than
on request.

**How to apply:** write results into the case `.log` as the run proceeds, with the same
rigour a write-up would have had — headline verdict, per-step results, the control that
makes each result interpretable, and any measurement traps hit along the way. Then *offer*
a write-up in a sentence rather than producing one. When asked for one, write it.

Note this **qualifies** the `orient-ie520` skill's §8 line that "the deliverable convention
is `after-action-<suite>.md` in that run's directory" — that still holds for a **campaign**
(a whole suite, or an investigation spanning many rounds), but not for each individual test
case. Related: [[user-prefers-manual-ui-testing]] — the same preference for less
scaffolding and fewer unrequested artefacts.
