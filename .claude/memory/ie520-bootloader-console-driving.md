---
name: ie520-bootloader-console-driving
description: "POINTER — IE520 bootloader-menu driving mechanics live in the orient-ie520 skill §3 (stop ticking Ctrl+B once the menu appears; drive 0/0/9 out in an unconditional finally). This memory holds no facts, only the provenance and the reason it was emptied."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 16d533ce-4a44-4c64-85a0-7af2c092d5db
  modified: 2026-09-02T23:59:00.000Z
  verified: 2026-09-02
---

**The mechanics now live in `.claude/skills/orient-ie520/SKILL.md` §3** — bootloader-menu
keypress conventions (menu options and Y/N take a *bare* keypress; only file selection takes
Enter, and AW+ CLI `(y/n)` wants `y\r`), the `Ctrl+B` rule, and the unconditional `0`/`0`/`9`
`finally:`. Read it there; do not restate it here.

**Provenance, which is why this file still exists.** Terrence caught a script parked in the boot
menu on tb470 `u5`, 2026-08-10, before I did — a scripted `Ctrl+B` tick that never stopped, so
the menu re-printed forever, the read loop never settled, and the unit was left offline to
everyone else.

**Why it was emptied, 2026-09-02.** This file also asserted *"neither tb470 IE520 is on the
PDU, so there is no remote power-cycle recovery"* — a **bench** fact in a **mechanics** memory,
with nothing to invalidate it when the bench changed. It was wrong by 2026-08-13 and stayed
here three weeks, and it had been used to justify making the `finally:` conditional. Measured
2026-09-02 through the framework's own power path: `(10.36.150.14, 4): status is ON`.

The rule that came out of it, and the reason this is a `feedback` memory rather than a deleted
file: **bench facts belong in `bench-state.md`, operating mechanics in the orient skill, and a
memory should carry a pointer plus the provenance — never a third copy.**
See [[tb470-topology-and-setup]] for the same treatment.
