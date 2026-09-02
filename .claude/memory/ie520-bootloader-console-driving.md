---
name: ie520-bootloader-console-driving
description: "Driving an IE520 bootloader menu over console — stop ticking Ctrl+B once the menu appears, and always drive 0/0/9 out in a finally block so the unit is never left parked in the bootloader. Records NO bench power/recovery facts: those live in bench-state.md"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 16d533ce-4a44-4c64-85a0-7af2c092d5db
  modified: 2026-09-02T21:30:00.000Z
  verified: 2026-09-02
---

When scripting the IE520 Boot Menu over serial (pyserial on the testbox), **stop sending `Ctrl+B`
(`\x02`) the moment the first menu byte arrives**. Continuing to tick it keeps the menu re-printing,
so a "wait until the port goes quiet" read loop never settles — the script hangs in the menu until
killed, and the unit is left **parked at the bootloader**, offline to everyone else. Terrence caught
this on tb470 u5 (2026-08-10) before I did.

Every bootloader script must have a `finally:` that drives the unit out — `0` (cancel file
selection) / `0` (return to previous menu) / `9` (quit and continue booting). **A unit parked in
the bootloader is offline to every other user of a shared bench, and the console you are already
holding is the fastest way back regardless of what other recovery exists.** Write the `finally:`
unconditionally; never make it contingent on some other recovery path being available.

Cancelling with `0` persists nothing: the bootloader only writes on "Saving settings... Complete"
after a *completed* file selection. Verify recovery by re-reading `show boot` and comparing to the
pre-test capture.

**Do not record bench power or recovery facts here.** Whether a given unit is on a PDU, and on
which outlet, is bench state that rots — it belongs in
`~/claude/IE520-testing/bench-setup/bench-state.md` (`[power]` / `[powerlink]`), the single source
of truth from which `tb470.setup` is generated. See [[tb470-topology-and-setup]] for why that file
is the authority. Read it live; do not carry a remembered answer into a run.

> **Corrected 2026-09-02.** This memory previously asserted *"neither tb470 IE520 is on the PDU,
> so there is no remote power-cycle recovery"* and made the `finally:` conditional on that. The
> claim was wrong by 2026-08-13 at the latest and stayed here for three weeks: `bench-state.md`
> §3 declares `pwr_a = (pdu, 10.36.150.14, 4)` and `pwr_b = (pdu, 10.36.150.14, 5)` for the two
> IE520s with the PDU confirmed reachable, and [[read-the-whole-function-before-judging]] records
> Terrence *asking* for an IE520 PDU power-cycle and stating *"the PDU isnt broken"*. This is
> exactly the failure the pointer above is meant to prevent — a bench fact copied into a
> mechanics memory, with nothing to invalidate it when the bench changed. The bootloader
> mechanics above are durable; the power topology never was.

This is the same failure shape as the framework bug being analysed at the time — see
[[bootloader-media-parse-bug]]: leaving a DUT stranded in the bootloader turns a 30-second
failure into an hour-long one. Note also that a power-cycle is **not** a clean substitute for
driving the menu out: [[ie520-spiflash-goes-dark]] is the case where reaching for the PDU during
a 12-minute silent SPIFlash write would have corrupted the write.
