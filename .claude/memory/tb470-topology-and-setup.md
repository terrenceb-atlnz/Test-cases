---
name: tb470-topology-and-setup
description: "ROUTING MEMORY for tb470 — where every kind of tb470 fact lives, and the rule that keeps them from being copied. bench facts -> bench-state.md (source of truth, GENERATES tb470.setup); IE520 operating knowledge -> orient-ie520 skill; reaching a box + launching a run -> TESTBOX-ACCESS.md; host DHCP/routing/pcap -> TB470-HOST-NETWORKING.md. Holds no bench facts itself, by design."
metadata: 
  node_type: memory
  type: project
  originSessionId: 2a141e3e-5a6e-4153-b006-2e724f5ec026
  modified: 2026-09-02T23:59:00.000Z
  verified: 2026-09-02
---

## Where each kind of tb470 fact lives

**One fact, one home; everywhere else links.** Copying a fact into a second file gives it no way
to be invalidated when the bench changes — that is what produced a three-week-wrong PDU claim and
an `after-action-17688.md` path broken in three files simultaneously.

| Kind of fact | Home |
|---|---|
| What is cabled to what, PDU outlets, addressing, stack membership, loopback plugs, **open product defects on this bench** | `~/claude/IE520-testing/bench-setup/bench-state.md` |
| IE520 platform limits, framework traps, **which console driver to use**, split-stack diagnosis and recovery, bench hygiene | `.claude/skills/orient-ie520/SKILL.md` (run `/orient-ie520`) |
| SSH auth from this host, which console is which unit, launching a framework or legacy run | `TESTBOX-ACCESS.md` |
| tb470 host DHCP, routing, no-NAT, packet capture | `TB470-HOST-NETWORKING.md` |

## The two rules that outlive any particular fact

- **`bench-state.md` GENERATES `/home/st-art/st-art/configs/tb470.setup`** (`bench_setup.py
  apply`; every fenced ` ```setup ` block concatenated in document order). **Never hand-edit the
  `.setup` on the box** — the next apply discards it silently — and never write a `.bak` beside
  it; history is `bench-setup/backups/`. Prose *outside* the fences never reaches the testbox, so
  editing it needs no apply. Check drift with `bench_setup.py check`.
- **Don't interrogate the hardware for facts the file format already answers** (Terrence,
  2026-07-30: *"this is a `.setup` input, not an interrogation"*). Probe hardware when the fact
  genuinely changes file content and cannot be derived — otherwise read the format.

## What is NOT here any more, and where it went (2026-09-02)

- The **open resiliency-link defect** → `bench-state.md` "Open items". It is a property of this
  bench's software, so it belongs with the bench record.
- **Stack-state churn, phantom ports on a destacked unit, factory-default forced password
  change, never-invent-a-`[portlink]`** → the orient skill (§1, §3, §4).
- Pointers this file used to carry into `TESTBOX-ACCESS.md` **§4a/§4b are dead** — those sections
  moved to the orient skill and `TB470-HOST-NETWORKING.md` respectively.

**Bench state churns — always run `show stack`, never trust a recorded state**, including
anything recorded here. Related: [[ie520-bootloader-console-driving]], [[ie520-two-bootloaders]],
[[ie520-tftp-boot-needs-usb-nic]], [[topology-profiles-contract]], [[i2c-stress-tooling]].
