---
name: ie520-two-bootloaders
description: "TWO IE520 bootloaders exist and behave differently at every gate — check `show system` -> Bootloader version FIRST; '9.1.0' leaks raw U-Boot, 'pauld' suppresses it but is SILENT where the AT messages should be"
metadata:
  node_type: memory
  type: project
  verified: 2026-09-01
---

As of **2026-08-12** there are two IE520 bootloaders in the lab, and the 5700 suite behaves
differently on each. **Establish which one is loaded before applying any bootloader knowledge:**

```
show system   ->   Bootloader version :
```

| | `9.1.0` | `pauld` |
|---|---|---|
| console banner | raw `U-Boot 2025.01-04843-g6eaac4e1fcad` | `Bootloader pauld loaded` (AT form) |
| provenance | the shipped behaviour | `IE520-bootloader-pauld.kwb`, developer **`-dirty`** build, tb470:`/tftproot`, 2026-08-12 10:41, from `/usr/src/output/IE520/u-boot/new/install/`; still U-Boot 2025.01 underneath |

**`pauld` is NOT a released fix.** Treat `9.1.0` as the shipped behaviour until told otherwise.

## What changed on the pauld build (tested live, tb470 u4)

**FIXED — the raw-U-Boot leak (root cause A0).** All 11 leaked strings measure 0:
`U-Boot 2025.01` 995→0, `Verifying Hash Integrity` 495→0, `Saving Environment to SPIFlash` 142→0,
plus `Booting image` / `Using … configuration` / `Trying … subimage` / `Probing SPI flash` /
`Waiting for Ethernet` / `Using asix_eth` / `TFTP from server` / `Bytes transferred`.
**So the leak was a SUPPRESSION problem and is fixable without changing the U-Boot base.**

**FIXED — D2** (file listing is now byte-for-byte the x230v2 format, on both USB and flash — even
the original buggy parse would work), **D3** (`Saving settings... Complete` contiguous), **D4**
(`Restoring default settings... Complete` contiguous).

**STILL BROKEN — D1 and D5, and they are one gap:** the noise was removed but the Allied Telesis
status messages were never added in its place, on *either* path.

- **D1 (success):** the window between `Loading …` and the AW+ banner is now **silent** —
  `Verifying release` = 0, `Booting...` = 0.
- **D5 (failure):** a foreign release is correctly refused with **no output at all** — silent
  countdown, reset, normal reboot. **This is worse than 9.1.0**, which at least printed
  `ERROR -2: can't get kernel image!` and failed only on case sensitivity. Now the post-reset
  banner prints `Allied Telesis Inc.` / `Mounting` / `Initializing`, all in case 30's **good**
  keyword list, so `send()` matches one and the test concludes the foreign release **BOOTED**.

**The ask is therefore singular:** restore `Verifying release... OK` and
`Error: This release file is not intended for this device.`

## Consequences to watch for

- **`BOOT_MARKERS` is broken on the pauld build** — 3 of 4 anchors dead
  (`Verifying Hash Integrity`, `Booting kernel`, `Starting kernel` all 0); only `login:` survives,
  which is the last line of a completed boot, so all early detection is lost. `Mounting` (5) and
  `Initializing` (1) are present — what the RCA originally recommended. **Not yet changed in the tree.**
- **`show system` reports `Bootloader version : pauld`** — a developer name where 2002 case 70
  asserts a version.
- **Boot Menu option 7 (restore factory settings) has two side effects:** it reverts the console to
  **9600** (the factory default; a non-default rate is a stored setting via option 4) and **waits
  for you to follow it down**; and it **clears the stored network settings**, so the one-off-boot
  TFTP dialogue loses its defaults (`[eth0]` → `[]`) and a bare Enter then ABORTS instead of
  accepting. That is exactly the state 2005 cases 2 and 3 leave behind.
- **Case 30's `testCaseMethod` says "one off TFTP boot"** but the code omits `source`, defaulting to
  `'flash'`. Docstring and behaviour disagree.
- The DUT's **AW+ side may have no route to the TFTP server** (`% Network is unreachable`) even
  though the *bootloader's* USB-NIC path works — the IE520 has no onboard mgmt port, so AW+ TFTP
  needs a front-panel VLAN up. See [[ie520-tftp-boot-needs-usb-nic]].

Full write-up and per-item captures:
`claude/IE520-testing/automated-bootloader/ie520-5700-edit-inventory-2026-08-12.txt` (Part A) and
`new-bootloader-pauld-20260812/`. Method for classifying any of this:
[[x230v2-5700-control-corpus]]. Before driving these menus:
[[read-the-transcripts-before-driving-hardware]].
