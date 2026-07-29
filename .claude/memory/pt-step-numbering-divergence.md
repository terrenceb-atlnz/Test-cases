---
name: pt-step-numbering-divergence
description: "PyTest Creator internal stepN keys ≠ the UI's step numbers — step5 is \"4. Fragments\", step6 is \"5. Generate\""
metadata: 
  node_type: memory
  type: project
  originSessionId: da9b3bee-f2e0-4c80-972d-0db43518083d
  modified: 2026-07-27T01:30:11.264Z
---

In PyTest Creator the internal `stepN` session keys and the numbers shown on screen
**diverged** when the old step 4 (Fit Decision) was folded into Fragments:

| Internal key | UI panel (badge id) |
|---|---|
| step2 | 2. Sequence |
| step3 | 3. Script Search |
| step4 | *(folded into Fragments; no panel)* |
| **step5** | **4. Fragments** |
| **step6** | **5. Generate** |
| step7 | 6. Run |
| step8 | 7. Validate |

**Why:** error messages that quoted the raw key were actively misleading — "Generation
requires step5 to be confirmed first" told a user blocked on *Fragments* to confirm
"step5", which is the number the UI prints on *Generate*, the very step they were running.
Terrence caught this 2026-07-27.

**How to apply:** never put a raw `stepN` key or bare step int in user-facing text — use
`_step_label()` in `routers/pytest_create.py` (accepts `'step5'` or `5`). When reading or
writing session payloads, remember the DB keys are the INTERNAL numbering. Pinned by
`tests/test_pt_step_labels.py`, which parses the real `index.html` so a renumber breaks a
test. See [[part3-grading-session]].
