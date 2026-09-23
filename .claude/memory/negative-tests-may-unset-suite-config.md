---
name: negative-tests-may-unset-suite-config
description: "Terrence 2026-09-23: a case whose sequence step is flagged `negative` may unset ANY suite-owned command with no pushback from Generate/Fix/lint; outside a negative case such an unset is BANNED (blocking lint). Review only checks a later case's need for the restore"
metadata:
  type: feedback
  verified: 2026-09-23
---

Terrence's rule (2026-09-23): *"If there is a 'negative test' type of testcase, the Fix and
Generate should be able to UnSet whatever needs unsetting to test it. There should be no
pushback at any point for this. IF THEY ARE UNSETTING THINGS NOT ON A NEGATIVE TEST, IT SHOULD
BE BANNED."*

**Why:** a negative test often *is* the unset (feature off → the behaviour must stop).
Treating that as a policy smell made Generate and Fix fight the test's own purpose. Unsetting
the suite's config anywhere else silently breaks every case behind it.

**How to apply:**
- A step is negative only if it carries the `negative` flag, set with the Sequence page's
  **Neg** column. Sequence extraction proposes the flag. Never infer it from wording at lint time.
- The ban covers **suite-owned** commands only, meaning ones `TestSet.configure()` issues for
  the whole run. A case's own setup and teardown are not affected.
- Outside a negative case, the ban is a **blocking** lint error. It has no acknowledge override,
  and no prompt may soften it.
- Inside a negative case, nothing pushes back: not the lint, the unit prompt, Fix, or arrival
  refusal.
- **Restore rule:** *"Allow it, have Review check if a later case restores it. If restoring
  isnt required by a latter test case, ignore it."* Review gets a `negative_unsets` list and
  flags a missing restore only when a later case depends on the setting.
- A per-unit fact like "this case is negative" belongs in the **per-unit** half of
  `pt_generate_step.jinja`, never the cached shared half. See [[prompt-cache-needs-block-boundaries]].

Related: [[pipeline-layer-contract]], [[art-suite-shape]].
