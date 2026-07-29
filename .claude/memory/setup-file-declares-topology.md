---
name: setup-file-declares-topology
description: "Terrence: stack membership, stackports and testbox cabling are DECLARED in the .setup file — never infer them from case text"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: abd89457-f2c0-4012-98a9-43e0e61a4c45
  modified: 2026-07-29T01:19:40.272Z
---

Terrence, 2026-07-28, after I built a prose alias set to detect "is this a stack case" for
the Generate prompt: *"Did we just add a stack identification when that already exists in
the tbxxx.setup file?"* He was right; it was reverted.

The `.setup` file states these as fact, and `DeviceSkrips/framework/Setup.py` parses them:

- `[stack] stk_a = swi_a, swi_b` — stack membership
- `[configured_stackport]` — the ports a test must never touch (non-default stack links)
- `[portlink] tb-swi_a = eth2-port1.0.15` — testbox NIC ↔ switch port cabling
- `[switch] swi_a = /dev/u0` — the console device ([[testbox-console-access]])

**Why:** this is the same mistake the project already recorded once for port naming — *a
RUNTIME hardware property; take it from the .setup, do not guess from the platform*. The
measurement made it concrete: the literal matcher hit 192/195 corpus scripts that call
`init_stk` but **0/4** stack cases written in prose, so a prose gate would have failed
silently on exactly the new cases it was built for.

**How to apply:** when a rule needs a topology fact, the answer is to PARSE the `.setup`, not
to infer it. Nothing in `CK_server` parses `.setup` today — that is the outstanding follow-up,
and it would make the stackport lint exact instead of heuristic. Schema and a real worked
example are checked in at `ask-ck/pytest-create/SETUP-FILE-REFERENCE.md` (written because
this format kept being re-derived). Related: [[pytest-creator-askck]].

**Caveat found 2026-07-29 — `.setup` is declarative, not verified.** It is still the right
source for *what the topology is meant to be*, but the `[switch] = /dev/uN` console lines rot
as hardware is recabled. On tb105, `tb105.setup` declared the 8-member `c2_core_stk` x950 stack
on `u16, u10, u24, u5, u17, u23, u6, u18` — but live, `u16/u17/u18` fronted **C1-x930-STK**,
`u23` fronted **D1-x540-STK-2**, and `u24` did not exist. Only 3 of 8 were right.

So: parse `.setup` for membership/stackports/cabling, but **before driving real consoles,
validate the console map against the hardware.** The reliable per-unit identifier is the
console's *login banner*, not the prompt: on an AWP+ VCStack every member's logged-in prompt
shows the shared stack hostname (`x950-MAX#`), while the banner shows the unit's own name —
`x950-MAX-5 login:` = member 5, a bare `x950-MAX login:` = the master. `0009_simple_repeated_
Master_reboot.py::get_master_id()` uses exactly this trick, sending `quit` to force the banner.
Sweep all of `/dev/u*`, don't trust the declared subset. See [[legacy-scripts-vs-framework]].
