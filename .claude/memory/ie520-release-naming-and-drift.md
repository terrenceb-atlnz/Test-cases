---
name: ie520-release-naming-and-drift
description: "IE520 releases move to awplus_main-latest + a coded date from 2026-09-02; a CHANGED BUILD DATE IS NOT DRIFT — we test the latest build at all times, and the date is the indicator"
metadata:
  node_type: memory
  type: project
  verified: 2026-09-02
---

**Terrence, 2026-09-02:** *"Release is about to be reformatted into a different title structure,
`awplus_main-latest.rel` and a coded date. Today is the last day for running Tomahawk builds. The
date will be the drift indicator in the future. Additionally, dates being updated isn't really
'drift', we are testing on the most latest build at all times."*

**Why this matters:** the orient-ie520 skill §1 frames a changed `show version` build date as a
🔥 hazard ("AN UNPLANNED REBOOT CAN SILENTLY DRIFT THE RELEASE"). That framing is now **half
wrong**. Reporting "the release has drifted" because the build date moved is noise — the bench is
*meant* to be on the newest build.

**How to apply:**

- A newer build date on its own is **expected**, not a finding. Do not open a session by
  reporting it as drift.
- What §1's hazard is still about is a build date that **differs BETWEEN the two members** —
  that splits the stack. Compare members to each other, not to a date written in a file.
- **The flash filename is deliberately CONSTANT and carries no date.** Terrence, 2026-09-02:
  *"we always load the same filename based on the test box we got it from. The `sh sys` will show
  the dated mainline build, which is the important bit."* So a build fetched via tb470 lands as
  **`IE520-tb470.rel`** on tb470's units, every time. **Do not "helpfully" copy it in under the
  dated name from the `.info`** — that breaks the convention.
- **⇒ Read the date from `show system`, NOT from `dir`.** `show system` reports
  `Software version` + `Build date` (e.g. `tomahawk_ie520-continuous`, `Sun Aug 30 23:47:03 UTC
  2026`); the `.info` beside the staged file gives the same build's full name. The filename in
  flash is *supposed* to be dateless.
- **Follows from this:** `show system`'s `Current software : IE520-tb470.rel` is the **convention
  working as intended**, not the "stale labelling" / "cosmetic oddity" that orient-ie520 §1 and
  `bench-state.md` (~line 368) call it. A *dated* filename in flash — e.g. the
  `IE520-20260825.rel` that was the boot image until 2026-09-02 — is the deviation.
- First `awplus_main` build seen: `IE520-awplus_main-20260902-1700.rel`, 41,237,559 B,
  sha256 `87c22e3762017f9b864cae74da01c678d380c7a352b511bc571df54e90e437f8`, staged
  2026-09-02 13:12 at tb470 `/tftproot/IE520-tb470.rel` (+ `.info` / `.sha256sum` beside it —
  **read the `.info` for the real filename**).
- Last `tomahawk_ie520-continuous` build run on this bench: `08/30/26 23:47:03`.

Related: [[ie520-two-bootloaders]], [[x230v2-5700-control-corpus]].
