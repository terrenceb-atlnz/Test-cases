---
name: tb470-ie520-flash-boot-reboots-ok
description: "As of 2026-09-11 the tb470 IE520s (u2/u3 stack + u4/u5) default-boot from a flash .rel (set in the bootloader), so `reload` is safe and no longer TFTP-hangs — BUT verify `show boot` image exists first; a stale boot-image pointer will still fail to come back"
metadata:
  node_type: memory
  type: project
  originSessionId: 49dcf692-ded5-46ac-ab73-fffb9e6ddec8
  modified: 2026-09-10T21:15:00.109Z
---

**Change (2026-09-11, Terrence):** he pushed a `.rel` to each IE520's flash and set the
**default boot to Flash from the bootloader config** on all devices (u2/u3 stack + u4/u5). So a
normal `reload` now boots from local flash — reboot-based tests (failover, `stack virtual-mac`,
service-restart) are back on the table. This RELAXES the old blanket "never reboot on tb470" rule.

**Still true / the nuance:** the *bootloader*-level TFTP path still needs the USB NIC dongle they
don't have (see [[ie520-tftp-boot-needs-usb-nic]]) — flash boot just means you never drop to TFTP
on a clean `reload`. Autoboot is `disabled`; boot config = `flash:/default.cfg`.

**The gotcha I hit (verify BEFORE any reload):** `show boot` on the u2/u3 stack read
`Current boot image : flash:/IE520-tomahawk_ie520-20260831-43.rel (file not found)` while the
system was actually *running* `IE520-tb470.rel`. Rebooting with a dangling boot-image pointer can
leave it unable to find an image. Fix = `configure terminal; boot system flash:/<the .rel that
exists>` (here `flash:/IE520-tb470.rel`), confirm `show boot` shows `(file exists)`, then reload.
On a stack `boot system` **synchronises the 40 MB image to the other member** — the console goes
dark for ~10-12 min ([[ie520-spiflash-goes-dark]]); wait it out.

**How to apply:** before rebooting any tb470 IE520, run `show boot` and confirm `Current boot
image` ends in `(file exists)`; `dir flash:` to see the real `.rel` names; fix `boot system` if the
pointer is stale. Reboot the stack with `reload` (answers `Are you sure you want to reboot the
whole stack? (y/n):` with `y`); a single member with `reload stack-member <id>`. Related:
[[tb470-topology-and-setup]], [[ie520-two-bootloaders]], [[awplus-cli-confirmations-need-enter]].
