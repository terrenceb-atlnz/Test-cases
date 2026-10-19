---
name: prompt-examples-are-the-spec
description: "Where a prompt's prose and its code EXAMPLE disagree, the model implements the example — so examples need testing like code"
metadata: 
  node_type: memory
  type: feedback
  verified: 2026-10-19
  originSessionId: 14818525-5627-4f16-882d-6bbbef6aed41
  modified: 2026-07-27T22:44:41.806Z
---

**In an LLM prompt, a code example is not documentation — it is the specification the model
actually implements.** Where prose and example disagree, **the model copies the example.**

Established 2026-07-28 across ~10 defects in generated test scripts. Every one came from
our own guidance, not from model weakness:

- Rule said *"assert `Configured`"*; the example tested `split()[-2:] == ['off','off']`
  (both columns). The model tested both columns → **false RED** on real hardware.
- Rule said *"never hardcode a port"*; the prose then read *"a string variable
  (`port = 'port1.0.1'`)"*. The model hardcoded ports.
- Rule said *"not `self.`"* in a FILL slot; the slot sat ABOVE the `self.<dev> = <dev>`
  block, so the model read ahead and used `self.` → **AttributeError at init**, twice.
- Rule 3b bound `port = dev.portA` (an object) while rule 4d compared `[port]` to a string
  token → never matches → **guaranteed false RED every run**. Two rules disagreeing.
- Rule 4d's example had `if/elif` and no `else` → the silent-failure case wrote no verdict
  → **false green inside the anti-false-green rule**.

**How to apply:**
1. **Test the examples.** `tests/test_prompt_examples.py` executes each prompt example
   against real harvested CLI output from `ck.db`. A wrong example fails in milliseconds
   with zero tokens spent — the `split()[-2:]` bug was a pure data check.
2. **Prefer designing the trap out over warning about it.** Moving the `self.<dev> = <dev>`
   assignments above the FILL slot made both spellings valid and ended a bug that two
   rounds of warnings had not.
3. **Add a lint when prose does not hold.** `startswith(port)` survived an explicit rule
   because the example showed only the `next()` form while the model wrote a `for` loop —
   guidance does not transfer across code shapes. Mechanical checks do.
4. **Cite evidence in the rule.** Rules asserting corpus counts get ignored (or discredited)
   when a count is unreproducible — two of mine were wrong (literals 125→350, `conf t`
   54→69). `test_prompt_corpus_counts_reproduce` now re-derives them from `ck.db`.
5. **Never gate a safety rule on optional context.** All the anti-false-green rules were
   inside `{% if cli_reference %}`, so they vanished for ~a third of cases. See
   [[checks-must-not-match-their-own-advice]] for the related prose-matching trap.

**2026-10-19 — the example must not come from the tool it teaches.** The Generator's objectives
prompt used T33234's own GENERATED objective (a six-bullet MDI/MDI-X deep-dive) as its worked
example, and T33234's exported objective matched it nearly word for word. The model was copying
its own deep-dive back as the standard, and Terrence was hand-editing every objective "because
they're unreadable for the average person". **How to apply:** never use a previous output of a
prompt as that prompt's worked example. Whose words go in instead is Terrence's call (this
time: his loopback list for the objectives; the steps example is Claude's draft, for his review). Rewrite merged 2026-10-20 (`gen-prompts-plain`); Terrence: "new objectives are MUCH better", steps "no issues". Caveat: judged first on T33241, a LOOPBACK case, the same subject as the example, and one of its steps is the example's sentence nearly verbatim; a different-feature case is the real test.
