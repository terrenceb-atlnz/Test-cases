---
name: run-attribution-5700-campaign
description: "Naming for 5700 test runs — only the 2026-08-07/08 campaign is bidhanc's; every run from 2026-08-10 on is OURS, and the TestCases are never anyone's"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 16d533ce-4a44-4c64-85a0-7af2c092d5db
  modified: 2026-08-10T22:12:16.978Z
---

When discussing the `test-5700.200x` work, keep the attribution clean:

- **bidhanc's run** = the FIRST campaign only, `2026-08-07/08` on tb504 (the logs Terrence inherited).
  Call it "the baseline" or "the 2026-08-07 run".
- **our runs** = everything from `2026-08-10` onward, in `copilot/run-20260810/`.
- **The TestCases themselves are neither.** They belong to the suite. "2002.70" is never
  "bidhanc's case 70" — say "case 70 in the baseline" vs "case 70 in our run".

**Why:** Terrence corrected this directly (2026-08-11) — talking about runs after the first as "his"
is confusing, and it muddles who is responsible for a given result. It also matters for the
write-up going to his superiors: the baseline is the inherited evidence, our runs are the validation.

**How to apply:** default the subject of any results statement to OUR run, and reference the
baseline only as an explicit comparison. Don't reach back into the baseline logs as the primary
source once our own run covers the same ground.

Related: [[bootloader-media-parse-bug]].
