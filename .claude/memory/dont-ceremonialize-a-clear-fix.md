---
name: dont-ceremonialize-a-clear-fix
description: When removing a false/misplaced check, fix it plainly — don't frame a bug removal as "narrowing a settled design contract" that needs sign-off
metadata:
  node_type: memory
  type: feedback
  verified: 2026-09-03
---

Removing the setup unit's arrival parse (a false `IndentationError` reported against a
synthetic `class _P:` wrapper's line number nobody wrote) I framed as "deliberately narrows
PLAN §9.7's shape-checked-on-arrival contract — worth a note in the PLAN status header."

Terrence, 2026-09-03: *"i dont care if it narrows it, its a false error and doesnt belong at
that step."*

**Why:** a false or misplaced check has no contract value to preserve, so dressing its
removal up as a design tradeoff needing ceremony is noise — the design doc that described it
was describing a mistake, not an invariant. This is the *opposite* failure from the usual
"don't skip to the edit" one ([[autonomous-judgement-divergence]]): here the right call was
already made and I inflated it.

**How to apply:** when something is simply wrong or in the wrong place, fix it and say so
plainly. Reserve "this changes a settled decision, let's agree first" for changes that alter
correct, intended behaviour — not for removing a bug. Stale design-doc wording left behind
by the fix is just doc hygiene (correct it), not a tradeoff to litigate.
