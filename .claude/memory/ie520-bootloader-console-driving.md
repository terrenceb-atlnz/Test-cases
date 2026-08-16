---
name: ie520-bootloader-console-driving
description: "Driving an IE520 bootloader menu over console — stop ticking Ctrl+B once the menu appears, and always drive 0/0/9 out in a finally block; tb470 IE520s have NO PDU so the console is the only recovery path"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 16d533ce-4a44-4c64-85a0-7af2c092d5db
  modified: 2026-08-09T23:29:02.601Z
---

When scripting the IE520 Boot Menu over serial (pyserial on the testbox), **stop sending `Ctrl+B`
(`\x02`) the moment the first menu byte arrives**. Continuing to tick it keeps the menu re-printing,
so a "wait until the port goes quiet" read loop never settles — the script hangs in the menu until
killed, and the unit is left **parked at the bootloader**, offline to everyone else. Terrence caught
this on tb470 u5 (2026-08-10) before I did.

Every bootloader script must have a `finally:` that drives the unit out — `0` (cancel file
selection) / `0` (return to previous menu) / `9` (quit and continue booting) — because
**neither tb470 IE520 is on the PDU** (see [[tb470-topology-and-setup]]), so there is no remote
power-cycle recovery. The console you are holding is the only way back.

Cancelling with `0` persists nothing: the bootloader only writes on "Saving settings... Complete"
after a *completed* file selection. Verify recovery by re-reading `show boot` and comparing to the
pre-test capture.

This is the same failure shape as the framework bug being analysed at the time — see
[[bootloader-media-parse-bug]]: leaving a DUT stranded in the bootloader turns a 30-second
failure into an hour-long one.
