---
name: testbox-console-access
description: "How to reach a lab device console from a testbox (ssh tbNNN, the uN alias, /dev/uN) and how to drive it non-interactively"
metadata: 
  node_type: memory
  type: reference
  originSessionId: abd89457-f2c0-4012-98a9-43e0e61a4c45
  modified: 2026-07-28T02:34:08.905Z
---

Lab devices are reached through their **testbox**, not directly by IP: `ssh tb105` (bare
hostname, key auth, passwordless sudo), then the device alias `u5`.

`uN` is a shell alias defined in `/etc/profile.d/minicom-aliases.sh` — it expands to
`minicom --wrap -D /dev/uN`. `/dev/uN` is a udev symlink onto some `/dev/ttyUSBnn` (the
mapping is not sequential: on tb105, `/dev/u5` → `/dev/ttyUSB20`). The `[switch]` section of
a `.setup` file uses this same namespace (`swi_a = /dev/u0`), which is how topology ties to
consoles — see [[setup-file-declares-topology]].

**Minicom needs a TTY, so it cannot be driven from one-shot commands.** Talk to the same
serial device directly instead — pyserial is present on the testboxes (3.4 on tb105): open
`/dev/uN` at 115200, write the command + `\r`, read until the prompt regex matches, and
answer `--More--` with a space. `terminal length 0` disables paging for the session and is
display-only, not config. Check the port is free first (`fuser`/`lsof`, no `minicom`
processes, no `/var/lock/LCK..*`) so you don't displace someone.

Generated ART scripts do **not** need any of this — the framework handles `--More--` itself
(`ATDrivers/AWPConsoleCore.py`) and `ATLibrary/ATTools.py` sends `terminal length 0`. The
pyserial route is only for driving a console by hand.
