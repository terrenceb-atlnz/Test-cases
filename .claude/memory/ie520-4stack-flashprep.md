---
name: ie520-4stack-flashprep
description: CONCLUDED NEGATIVE 2026-09-04 — IE520 hard-caps VCStack at 2 members, a 4-stack is impossible; proof + final state in ie520-stack-results.log
metadata: 
  node_type: memory
  type: project
  originSessionId: a6244017-fc0c-4802-b364-12f1f06cfcb6
  modified: 2026-09-04T03:54:40.244Z
---

**DONE 2026-09-04 — result NEGATIVE.** The 4-device IE520 VCStack experiment
(u2/u3/u4/u5 on tb470) is over: **the IE520 cannot form a stack of 4.** It is a
hard **product limit of 2 members** — `stack 1 renumber 3|4|8` → `% The max stack
member ID supported by this product is 2` (confirmed on S/N 264A23052 and
264A23066), and `switch 3|4 provision ie520-28` → `% Invalid switch value`. Renumber
to ID 2 IS accepted, so the ceiling is exactly 2. No CLI path raises it. The flash-prep
work (all four flashed + flash-boot) is therefore moot for its original purpose.

**Full findings + logged CLI proof: `/media/terrenceb/mnt/testbox_home/ie520-stack-results.log`**
(root of testbox_home). Facts-only, per Terrence's request.

Durable IE520 facts learned (belong conceptually in orient-ie520 §2, not yet added there):
- **VCStack max = 2 members.** A 4-stack is not configurable.
- **`shutdown` on a stackport is NOT saved to config** (`% ... "shutdown" command is
  not saved to configuration for stackports`) — it goes admin-down at runtime but any
  reboot re-enables it. So an "all stackports shut" safe state is **not durable**; make
  it durable with `no stackport` (persisted, needs a reboot) or by uncabling.
- Renumber to ID 2 renames real ports port1.0.x→port2.0.x; old range goes phantom
  (`provisioned`) — a shutdown on the pre-renumber range strands on phantom ports.

Final bench state (all standalone, every stackport admin-down, DAC cables present):
u2/264A23061=ID1 chassis3439 prio1; u3/264A23068=ID2 chassis3439; u4/264A23052=ID1
chassis3439; u5/264A23066=ID1 chassis2675. Console swap in effect: /dev/u2=…061,
/dev/u3=…068. See [[tb470-topology-and-setup]], [[ie520-release-naming-and-drift]].
