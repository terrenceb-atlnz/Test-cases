---
name: autonomous-judgement-divergence
description: Measured base rate — 5 of 12 autonomous judgement calls matched Terrence's; verification confirms what IS, never what SHOULD be, so check design docs not just code
metadata:
  type: feedback
---

**Do not trust your own judgement calls at the rate the tooling's confidence implies.** This has
been measured twice.

**2026-08-04, blind experiment.** 12 decisions from an autonomous run were presented to Terrence
as neutral questions without revealing the chosen answers. **5 matched.** Of the 7 that
differed, 4 landed on an option neither party had picked first. Roughly 58% divergence on
calls consequential enough to reach a review document.

**2026-08-05.** Four rules in `generate_steps.jinja` were reversed. **Three came from one
autonomous commit** (`f0a94af`), the fourth was mine from that morning. All four drifted the
same direction — more prescriptive, more measurable, more script-like — and in every case
`OBJECTIVE_DRAFTING_PROCESS.md` had been right all along.

**Why the verification apparatus does not catch this.** It is genuinely strong at confirming
what IS — 284 findings / 206 CONFIRMED, adversarial skeptics, mutation harnesses. But
"CONFIRMED" only ever means *the code does what the finding says*, never *this is desirable*.
So "618 of 648 steps have no expectedResult" arrives as a defect with overwhelming evidential
weight, and the question that mattered — *is blank correct?* — is the one nothing in the
apparatus can ask. Where design intent is not written down, an audit's own premise fills the
gap and becomes self-justifying: a push gate asserted "a step with no expected result is not a
test", then the prompt was rewritten to satisfy that gate, citing the gate refusing the corpus.

**Two amplifiers.** (1) Tests freeze the deviation — once `test_blank_expected_result_blocks_the_push`
exists, the wrong rule is protected by the mechanism meant to catch wrongness. (2) Overreach is
intermittently rewarded: roughly half of it produces something genuinely useful, which is the
same ~50% and exactly the schedule that makes the habit stick.

**How to apply.** Before changing a prompt, gate or rule, read its DESIGN DOCUMENT, not just its
code and tests — a review that checks every claim against the implementation will pass a prompt
that contradicts its own spec (that is exactly how 2026-08-05's false sign-off happened). And
see CLAUDE.md "How we work": propose, do not decide. [[pipeline-layer-contract]],
[[expected-results-deliberately-absent]], [[scoped-directives-stay-scoped]].
