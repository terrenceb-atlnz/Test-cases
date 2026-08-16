---
name: read-the-whole-function-before-judging
description: "Terrence, 2026-08-13: read a function to its END before judging behaviour from it, and never substitute a hand-rolled probe for the code path you are making a claim about — I read 25 lines of _pdu_cmd, curl'd the PDU, got a 401, and reported the bench as broken"
metadata:
  node_type: memory
  type: feedback
---

Asked to power-cycle an IE520 via the tb470 PDU, I read `ATPower.PduPower.on()/off()` and then
only the **first ~25 lines** of `PowerGroup._pdu_cmd()` — far enough to see it read
`username`/`password` off `pList[0]`, not far enough to see how it actually authenticates. The
setup files carry a 3-field power line, so I concluded the credentials were empty, tested with
**curl**, got HTTP 401, and reported that *framework power control on the bench was broken*.

Terrence:

> *"the PDU isnt broken, your understanding of how it is controlled, is"*
> *"i think it would pay to read the entirety of a function before making a judgement. that just
> seems like sloppy behavior. theres unfortunately a lot of context in some functions, and some
> of it is coded deeper than 25 lines."*

**Why:** two separate faults, and the second is the worse one.

1. **Partial read, whole-function claim.** These framework functions carry real context past the
   first screen — retry loops, fallbacks, alternate endpoints. Judging from the top of one is
   guessing with extra steps.
2. **A substitute probe is not evidence about the real path.** I never executed the framework's
   control path. A 401 from *my curl* is evidence that *my curl* was wrong; I reported it as
   evidence the *system* was wrong, and escalated it to "this will bite the stacking run."

**How to apply:**

- Read the function to its end — and the helpers it calls — before asserting what it does or
  concluding that it fails.
- To claim a code path is broken, **run that code path**. If you reach for curl/an ad-hoc script
  instead, you are testing your reconstruction, not the system; say so explicitly, or don't make
  the claim.
- A negative result from a probe you wrote is a hypothesis about your probe first, the system
  second.
- **Credentials: use the lab default in `secrets.md`** (which is the public AlliedWare Plus
  default) — it applies to the **PDU** too, not just switch consoles. I guessed `admin:admin` and
  `snmp:1234` while the working answer sat unread in that file. Credentials belong in
  `secrets.md`, never in a memory.

Sibling of [[read-the-transcripts-before-driving-hardware]] (read the existing record before
improvising on hardware) and [[mutate-before-you-claim]] (verify before writing up a diagnosis).
Same root failure: acting on a reconstruction when the real thing was available to read or run.
