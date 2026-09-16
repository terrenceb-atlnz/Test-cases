---
name: explain-in-plain-language
description: "Lead decisions/questions with plain language; unpack internal jargon (gate, fixture, coupling) — Terrence will otherwise ask 'what does that even mean'"
metadata:
  type: feedback
  verified: 2026-09-16
---

When surfacing a problem or asking Terrence to make a decision, **lead with plain
language and unpack any internal jargon** — don't pack the ask with terms like "the gate",
"fixture coupling", "stays green through future wipes" without saying what they mean in
concrete terms.

**Why:** 2026-09-16, mid clean-slate reset, I asked (via AskUserQuestion) how to resolve
"5 zephyr-push tests that depend on a live refined-cases bundle so the gate goes green and
stays green through future wipes." Terrence rejected the tool call and replied "what does
that even mean." The content was fine; the framing assumed shared jargon it shouldn't have.
Consistent with earlier moments the same day ("i dont understand what a Tampermonkey
userscript is", "do i make a new file, or copy paste that into bash") — the preference is
for plain, unpacked explanations, not a lower technical level (he runs the lab, git, the
servers).

**How to apply:** State the situation in one plain sentence first ("the test suite I run to
check nothing's broken"), THEN the term if useful ("— the 'gate'"). When a question has real
tradeoffs, describe each option by what actually happens, not by its category name. If a
sentence would make sense only to someone already inside this codebase's vocabulary, rewrite
it. Related: [[dont-ceremonialize-a-clear-fix]], [[scoped-directives-stay-scoped]].
