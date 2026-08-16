---
name: ie520-spiflash-goes-dark
description: IE520 flash is SPIFlash and is incredibly slow — a 41 MB flash-to-flash copy took ~12 min. During it the unit goes COMPLETELY dark: console silent even to a CR, and ping/ARP fail too. That is normal, not a hang; do not diagnose a crash or start a recovery
metadata:
  node_type: memory
  type: project
---

Terrence, 2026-08-11: *"the flash is SPIFlash, its incredibly slow."* Measured the same day on
tb470's IE520 (`/dev/u4`):

| operation | 41 MB file | elapsed |
|---|---|---|
| `copy tftp://…/IE520-tb470.rel flash:/mainrelease.rel` | download + write | **~6 min** |
| `copy mainrelease.rel backuprelease.rel` | flash-to-flash (read **and** write) | **~12 min** |

**The trap is not the slowness, it is that the unit goes completely dark while it works.**
During the local copy:

- the console emitted **nothing at all** — not a progress dot, and no response to a bare CR,
  for 100 s of continuous reading;
- `ping` to its management address got **100% loss** and the ARP entry went `FAILED`.

So every cheap liveness check says "dead" while the device is in fact working normally. I went
looking for a netboot in the interface counters and started reaching for the PDU before it came
back on its own with a clean `swi_a_5700_2002#` prompt.

**⇒ Wait it out. Budget ~15 min for a 41 MB flash operation and do not power-cycle**, which on
a unit mid-write is how a partly-written image or a corrupted UBI volume gets made. This is the
same root cause as the RCA's under-budgeted `2003.10` / `2003.11` / `2005.3` (a full 128 MB
erase exceeded 780 s); the new part is the total console + control-plane silence.

Practical consequences:

- A framework `cmd()` on a copy returns as soon as it sees `Copying...`; it does **not** wait
  for completion and does **not** verify the file landed. Check `dir` yourself afterwards.
- Prefer a local `copy a.rel b.rel` over a second TFTP pull only if you want fewer moving
  parts — it is not faster; it was twice as slow here.
- Tool-call timeouts need to allow for it: poll in short bounded reads rather than one long
  blocking read, or the harness kills the call before the device answers.

Relates to [[ie520-tftp-boot-needs-usb-nic]] and [[bootloader-media-parse-bug]].
