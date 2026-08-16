---
name: awplus-cli-confirmations-need-enter
description: "AW+ CLI (y/n) confirmations need `y` + ENTER; only the BOOTLOADER Boot Menu takes a bare keypress. Applying the bootloader rule to the CLI left `reload` sitting unanswered - silent, no reboot, uptime unchanged - and I misdiagnosed it as serial flow control"
metadata:
  node_type: memory
  type: feedback
---

Two `reload` attempts on the tb470 IE520 stack (2026-08-13, test 17554) produced **no reboot and
zero console output**. Uptime proved nothing had restarted. Terrence took the console and both
units reloaded *immediately*:

> *"looks like you didnt send a carriage return after reload"*

**The cause.** The AW+ CLI prompt `Are you sure you want to reboot the whole stack? (y/n):`
requires **`y` then Enter**. I sent a bare `y`, because
[[read-the-transcripts-before-driving-hardware]] records that IE520 **Boot Menu** options and Y/N
confirmations take a bare keypress with no `\r`. That rule is real — **but it belongs to the
bootloader menus, not the AW+ CLI.** I generalised one interface's input convention onto a
different interface without checking.

```python
s.write(b'y\r')     # AW+ CLI confirmation  -> needs the CR
s.write(b'y')       # bootloader Boot Menu  -> bare keypress, a CR would answer the NEXT prompt
```

**Why it hid for so long:** an unanswered confirmation is *silent*. The device is not hung, not
rebooting, and still serving the session — it is simply waiting. Every symptom (no output, no
uptime change, console alive) reads like a stalled or dead box.

**How to apply:**

- CLI `(y/n)` → `y\r`. Bootloader menu → bare key. Never carry a convention across the two.
- After sending a confirmation, **verify the state change** (uptime, prompt, boot output) rather
  than assuming the keystroke landed. A confirmation that was never accepted looks identical to
  an operation that never started.
- Log console bytes **as they arrive**, not on success. Both attempts read into a buffer that was
  only written out when the expected pattern matched, so a timeout discarded exactly the
  transcript needed to diagnose it.

**A related serial fact, and a warning about how I used it.** In pyserial, `dsrdtr=True` enables
**DSR/DTR hardware flow control** — it does *not* mean "leave DTR alone". I set it to stop the
port-open DTR drop from sending a BREAK, which was wrong on its own terms. To avoid the DTR drop,
clear HUPCL instead: `stty -F /dev/ttyUSBn -hupcl`.

Also: **a `sysrq: HELP :` banner when you open an IE520 console means a BREAK was just sent** (the
DTR drop), and the following character was consumed as an unrecognised sysrq key. That is a live
hazard — after a BREAK, a plain letter is a sysrq *command* (`b` = immediate reboot). Always send
a harmless `\r` first and drain before sending any word.

**I then blamed the flow-control setting for the stalled reload and said so confidently. That was
wrong** — the missing CR explains it completely. Third overclaim of the same session; see
[[read-the-whole-function-before-judging]]. State the mechanism you can demonstrate, not the one
you find plausible.
