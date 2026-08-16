---
name: read-the-transcripts-before-driving-hardware
description: "Terrence, 2026-08-12: don't probe hardware by trial and error when prior run logs and the framework source already document the exact send/expect dialogue — read those FIRST"
metadata:
  node_type: memory
  type: feedback
---

While reproducing bootloader menu behaviour on tb470 u4, I drove the Boot Menu by trial and
error — guessing bare-keypress vs `\r`, guessing prompt defaults — and burned several hardware
cycles plus a wrong result (accidentally triggering YMODEM instead of TFTP). Terrence:

> *"are you just muddling your way through the menus instead of following the Log of previous
> executions, which literally tell you what to expect at every menu?"*

He was right. Everything I "discovered" was already written down in two places I had open:

1. **The framework source** — `ATBootLoader.py::perform_one_off_boot_from_alternate_source_with_output()`
   encodes the exact sequence: `send('1')` bare for menu options, `send(options[source])` bare for
   the media choice, `send('{}\r\n'.format(selection))` **with** `\r\n` for the file selection,
   plus the literal gate keyword lists. `runRestoreFactorySettings()` likewise does
   `dut.send('7', ...)` then `dut.send('y', ...)` — both bare.
2. **The prior run transcripts** — `swi_a_*.log` are full console captures of the framework
   driving these same menus end to end, prompt by prompt.

**Why it matters:** hardware cycles are slow (a reboot + 44 MB TFTP load is minutes), each blind
keystroke can land on the wrong menu item, and a stray character can select something destructive.
I typed `x540-tb470.rel` into a device menu and the `4` in it selected **YMODEM**, which then hung
until it timed out. Guessing on hardware is not cheap and is not safe.

**How to apply:** before driving any interactive device menu, read the framework function that
already automates it and the prior `swi_a_*.log` for the same case. Extract the send/expect pairs
from those, then replicate. Probe the device only for what genuinely is not recorded anywhere.
Same instinct as [[checks-must-not-match-their-own-advice]] and the divergence-vs-rot rule in
[[x230v2-5700-control-corpus]]: the corpus answers the question before the hardware does.

**The specific facts I should have read rather than rediscovered** (IE520 Boot Menu):
- Menu options and Y/N confirmations take a **bare keypress**; a trailing `\r` leaks into the
  *next* prompt. `7\r` selects "Restore Bootloader factory settings" and then immediately answers
  its own "Are you sure? (Y/N)" as no.
- Only the file-selection prompt takes Enter — it says so: *"press enter"*.
- Top-level Boot Menu `0` is **RESTART**, not "back" — see [[ie520-bootloader-console-driving]].

Related: [[bootloader-media-parse-bug]], [[orient-ie520 skill in testbox_home/.claude/skills]].
