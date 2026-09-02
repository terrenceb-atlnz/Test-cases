---
name: tb470-topology-and-setup
description: "**tb470 bench topology is NOT recorded here any more** — the source of truth is `~/claude/IE520-testing/bench-setup/bench-state.md`, from which `/home/st-art/st-art/configs/tb470.setup` is GENERATED (`bench_setup.py apply`); never hand-edit the .setup on the box and never write a .bak beside it. What survives here: 🐛 the OPEN resiliency-link defect (the BACKUP member registers zero healthchecks, so a cable pull gives TWO ACTIVE MASTERS, not a Disabled-Master — blocks TEST 17688 steps 3-7); STACK STATE CHURNS, always run `show stack`; a destacked unit KEEPS its old stack ID and its port1.0.x go phantom, SILENTLY; a factory-default AW+ device FORCES a password change at first login; never invent a [portlink]"
metadata: 
  node_type: memory
  type: project
  originSessionId: 2a141e3e-5a6e-4153-b006-2e724f5ec026
  modified: 2026-09-01T13:30:00.000Z
  verified: 2026-09-02
---

## Where tb470 bench state lives — read this before recording any bench fact

**`~/claude/IE520-testing/bench-setup/bench-state.md`** is the source of truth for what is
cabled to what, which console fronts which device, stack membership, PDU outlets and bench
addressing. `/home/st-art/st-art/configs/tb470.setup` is **generated** from it: every fenced
` ```setup ` block in that document is concatenated in order to form the file.

    edit bench-state.md  ->  ./bench_setup.py apply  ->  tb470.setup written IN PLACE
                                                         previous content -> backups/

- **Never hand-edit `tb470.setup` on the box.** The next `apply` discards the edit silently.
  (`apply` refuses if the live file has drifted from `tb470.setup.current`, so it will catch
  someone else's hand-edit — but not before the edit has already gone unrecorded.)
- **Never write a `.bak` beside the live file.** History is `bench-setup/backups/`. The old
  scheme accumulated four `tb470.setup.bak-*` in `configs/` before it was cleaned up
  2026-09-01, and nothing recorded which was current.
- **The old editing mechanics recorded here are OBSOLETE** — `scp` a `.new` alongside,
  `cp -p` a dated `.bak`, `mv -f` over the original. Do not do that any more.
- `~/claude/IE520-testing/bench-setup/bench-state.md` also carries the **evidence** for each line and, separately, what is
  **inferred rather than measured** (currently: which LAG leg pairs with which, and the
  `swi_d <-> swi_c` link, which is by elimination). Treat those two as unproven.

Everything below is what that file deliberately does NOT carry: DUT defects and
behavioural traps, not bench wiring.

## 🐛 OPEN PRODUCT DEFECT — the resiliency link does not work on this build

Whichever member holds the **backup role** receives 100% of the master's healthcheck
multicasts error-free and registers none of them: `show stack resiliencylink` reads `Failed`
on the backup while it transmits **zero** replies. Reproduced across **4 port pairs**
(1000BASE-SX 1G, 10GBASE-SR 10G matched *and* mismatched numbering, and the 10G copper
stacking PHYs), **both units**, **both roles**, **both bootloader builds**, 4 reboots — so
port, media, unit and bootloader are all excluded; the fault tracks the ROLE.

Consequence: pulling the stacking cables yields **TWO ACTIVE MASTERS sharing one VMAC and one
IP**, not a Disabled-Master; the neighbour switch then sees the same bridge ID on two ports and
blackholes one. **Blocks TEST 17688 steps 3-7.** Software `IE520-tb470.rel`,
`tomahawk_ie520-continuous`. Full evidence + verdict table:
`~/old test runs/IE520/stack-tests/resiliency-link/after-action-17688.md`.

## Traps that have each cost bench time

**STACK STATE CHURNS — never trust a recorded stack state, run `show stack`.** Found
re-stacked on 2026-08-10, contradicting a "both standalone" note four days old; de-stacked
again mid-session; stacked again since. This is why bench state moved out of memory and into a
file that is applied to the hardware.

**A destacked unit KEEPS its old stack ID, and this fails SILENTLY.** The unit is standalone
but still member ID 2, so its real ports are `port2.0.x` while the entire `port1.0.x` range is
phantom (`Hardware is Provisioned, address is 0000.0000.0000`). `show interface brief` still
lists the phantom range, and config naming those ports is **accepted with no error**. It cost
an afternoon: `ip address dhcp client-id port1.0.6` encoded DHCP **option 61 as
`00:00:00:00:00:00`**, which reads exactly like a product defect and is not one. Verify by
contrast against the same port in the other range before believing any port-scoped result.
The same hazard applies to a *stacked* member — see that document's §1, trap 2.

**A factory-defaulted AW+ device FORCES a password change at first login.** It accepts
`manager`/`friend`, then demands `Enter new password:` before granting a prompt. Automation
that only knows `login:`/`Password:` feeds its next command into that dialog (mine typed
`enable` as the new password). Any procedure starting from factory default needs a step for it.

**Never invent a `[portlink]`** — a wrong one is hardware-specific fabrication, and
`Setup.init_portlink()` returns `(None, None)` **silently** when no link matches, so the
script then builds CLI against `None` and the missing *cable* grades as a *script* defect.
Check with `tool/pt_preflight.py` before booking bench time.

**Don't interrogate the hardware for facts the file format already answers** (Terrence,
2026-07-30: *"this is a `.setup` input, not an interrogation"*). The letter-vs-number PDU
outlet question was settled by one grep of `Setup.py`; pinging the PDU and curling its web UI
added nothing. Probe hardware only when the fact genuinely changes file content and cannot be
derived.

## Pointers rather than copies

- **tb470 host networking** — DHCP pools and their traps, the no-NAT / `10.38.215.0/24`
  return-path constraint, packet capture: `TESTBOX-ACCESS.md` §4b. Already served, both
  `chrony` and `isc-dhcp-server`; do not "set them up".
- **Driving these consoles** — `TESTBOX-ACCESS.md` §2/§2a and [[testbox-console-access]]. Use
  the framework's own driver and `console.mode('#')` before any `cmd()`.
- **De-stacking lessons and the 27/28 cabling hazard** — `TESTBOX-ACCESS.md` §4a, scoped
  correctly in the bench-state document: the hazard is two **standalone** units both claiming ID 1
  with a shared chassis-id, not a properly formed stack.

Related: [[ie520-two-bootloaders]], [[ie520-tftp-boot-needs-usb-nic]],
[[ie520-bootloader-console-driving]], [[topology-profiles-contract]], [[i2c-stress-tooling]].
