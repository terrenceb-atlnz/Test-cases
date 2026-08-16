---
name: ie520-tftp-boot-needs-usb-nic
description: The IE520 has NO onboard management ethernet — `show interface eth0` says "% Can't find interface eth0". The `eth0` a .setup names for TFTP boot is a USB-to-Ethernet dongle (ASIX) in the switch's USB port, visible ONLY to the bootloader; without it fitted, a bootloader TFTP-boot suite cannot run at all
metadata:
  node_type: memory
  type: project
---

On the AT-IE520-28GSX there is **no onboard out-of-band management port**. Confirmed on both
tb470 units 2026-08-11:

    awplus> show interface eth0
    % Can't find interface eth0

The `eth0` that a 5700 bootloader `.setup` names —

    [hub]
    hub_a = tb, swi_a
    [portlink]
    hub_a-tb    = eth2
    hub_a-swi_a = eth0

— is **not an AW+ interface at all**. It is a USB-to-Ethernet adapter in the switch's USB
port, enumerated and used only by the bootloader. Verbatim from the tb504 campaign capture
(`run-20260810/swi_a_2002.log`), at the "one-off boot from alternate source" prompt:

    Bus usb@50000: USB EHCI 1.00
    scanning bus usb@50000 for devices... 5 USB Device(s) found
    This device can boot off the following interfaces:
    eth0 asix_eth (08:be:ac:4b:8c:d9)
    Please enter an ethernet interface to download from (eth0-eth0) [eth0]:

`asix_eth` is the ASIX USB NIC driver, and the MAC is an ASIX one — not the switch's own
`84e3.27xx.xxxx`. `library_5700.py` derives the whole TFTP boot config around it:
`ipDevice = tb_eth_a.get_ipv4_addr(2 + int(dut.ttyNumber))` and
`AWP_TFTP_Bootloader_Settings(interface=testSet.port, ...)` where `port` is literally `eth0`.

**Consequences:**

- **The dongle is a hard prerequisite, not an accessory.** Cabling a front-panel port to the
  testbox does NOT give the bootloader a download path. The RJ45 that must reach the testbox
  eth port is the **dongle's**.
- **You cannot check for it from the AW+ CLI** — it does not appear in `show interface brief`
  or `show ip interface`. The bootloader's own interface list is the only confirmation, and
  reaching that needs a power-cycle plus Ctrl+B.
- **🔑 THE LINK IS ONLY UP DURING BOOT** (Terrence, 2026-08-11). The dongle is enumerated by
  the bootloader and goes away once AW+ is running, so the testbox-side NIC reads
  `Link detected: no` for as long as the DUT is booted and idle. **Carrier on the testbox eth
  port is therefore NOT a valid pre-flight check on this bench** — a correctly cabled,
  fully working TFTP boot path looks identical to an unplugged one until the moment the DUT
  is power-cycled. Do not diagnose "the cable isn't in" from `ethtool`; confirm at the
  bootloader instead.

Relates to [[tb470-topology-and-setup]] and [[bootloader-media-parse-bug]].
