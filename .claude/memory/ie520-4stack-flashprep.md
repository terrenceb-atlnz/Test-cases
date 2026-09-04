---
name: ie520-4stack-flashprep
description: Active task — 4-device IE520 stack flash-prep; where the handoff lives and current state
metadata: 
  node_type: memory
  type: project
  originSessionId: a6244017-fc0c-4802-b364-12f1f06cfcb6
  modified: 2026-09-04T00:42:02.277Z
---

Active experimental task (started 2026-09-04): prove/enable a **4-device IE520 VCStack**
(u2,u3,u4,u5). TFTP-netboot only supports 2 concurrent units, so we flash the current
`IE520-tb470.rel` into each unit's local flash and switch each bootloader to flash-boot (user
does the bootloader side), then strip configs + renumber to unique stack IDs so a real 4-way
stack can form. The feature is unproven — existing commands may not allow it.

**Full state + tooling + gotchas: `claude/IE520-testing/IE520-4stack-flashprep-HANDOFF.md`.**
Read it after `/orient-ie520` — this is a *temporary* topology, not the two-unit bench orient
describes.

As of the handoff: **all four flashed** (u5/u2/u4 also on flash-boot; u3 flashed+verified at
41107895 B, bootloader switch pending user). Remaining: user sets u3 bootloader, then one
**strip + renumber** pass — blocked on a user decision (ID→unit mapping). Root cause of
the 4-way failure = all four share Virtual Chassis ID `0xa66` with duplicate stack IDs
(duplicate-master / "Neighbor incompatible"), i.e. leftover config, not hardware.
