---
name: topology-profiles-contract
description: "RETIRED 2026-09-21 — the [misc] role contract (ck_profile / ck_role_dut / ck_link_<role>, pt_profiles.py) is GONE; a generated script binds the framework's swi_a slot, discovers cables via get_all_port_links() and reads media from the DUT; [misc] is never a lookup layer"
metadata:
  node_type: memory
  type: project
  verified: 2026-09-23
  originSessionId: 55f64c5f-6b57-4d85-9f09-b5090301f55a
  modified: 2026-09-23
---

**Terrence's ruling, 2026-09-21:** *"I dont want the [misc] section to be callable as a
workaround for not using the existing framework commands. We have a suite of 'show' commands
that identify whatever we need to, the information shouldnt require pre-loading variables to
know it."* This memory used to specify that contract (2026-07-30). It now records that it is
retired and what replaced it — do not rebuild it.

**Why it was wrong, verified against the 827-script corpus (`ck.db`, read-only):**
- `swi_a` / `swi_b` / `stk_a` ARE the framework's portable role slots — 297 / 168 / 192
  `init_*` lookups; a role-named key (`init_swi('dutA')`) appears **0** times. `dutA`, `swiSrc`,
  `tb` are script-local variables. Every bench maps the slots to its own hardware, so
  `init_swi('swi_b')` is not bench-specific. `ck_role_dut` duplicated this.
- A link partner is **any `[switch]` with a `[portlink]` to the DUT** that is not the testbox and
  not one of the DUT's own stack members. `dev.get_all_port_links()` returns every cable with its
  far device; `isinstance(far, ATTestBox.TestBox)` tells the testbox apart (the framework's own
  `library_5712._get_swi_tb_link` does exactly this). `ck_link_<role>` duplicated this.
- Media is a fact the device reports — `show interface <port> status` (Type column), `show
  system pluggable` — and a declaration of it goes stale the moment a module is swapped.
  The one real gap the layer covered (two cables of different media between one pair, where
  `init_portlink` hands out the first unused) is closed by **asking the device**, not tagging
  the file.

**What the frame does now** (`pt_script_template.py.jinja`, plan
`archive/plans/PLAN-frame-framework-discovery.md`, spec `TOPOLOGY-PROFILES.md` rewritten):
`dut = init_swi('swi_a')` stays the command handle, and when `get_stack()` reports a stack the
frame ALSO binds `dut_stack = init_stk(_stk.name)` for ports. This is ART's own shape: 103 of 239
ART scripts bind both, and Terrence's rule is *"Copy what they do, because it works."* **Never
re-assign `dut` to the Stack.** The framework's `Stack` has no `cmd`. The frame did exactly that
until 2026-09-23, which would have killed every command on tb470's stacked DUT.
`_ck_discover(dut, unit)` walks the ports' owner's `get_all_port_links()`,
skips stack members, takes the TestBox far end as `tb`, and classifies each partner link from
the DUT's show output — twisted pair in a cage (`show system pluggable` lists it) = `cusfp`,
fixed twisted pair = `copper`, `fibre`, `not present` = `absent`. **An empty cage is no role**
("cages themselves aren't fibre or copper cause they're empty"): a pluggable role needs its
module fitted at `init()` or its cases report UNSUPPORTED. `_ck_bind_link(setup, dut, role,
optional=False)` hands out one link per role, pluggables before copper, a partner initialised
once; required roles abort as BENCH PROBLEM. Far ports are role-specific (`peer.portDut`,
`fibre_peer.portFibre`, `cusfp_peer.portCuSfp`) — a shared `.portDut` collides when both
pluggables land on one partner switch, which is tb470's shape. No `init_portlink`, no
`get_all_misc`.

**Preflight** (`pt_preflight.py`) reads `_ck_bind_link(..., '<role>')` demands, matches
REQUIRED roles before optional ones (offline every partner link looks alike — source order let
an optional pluggable eat the copper cable and printed a confident wrong UN-RUNNABLE on tb470),
and says plainly that media is read from the DUT at run time. `[misc]` is not parsed;
`--profile` is gone.

**Still true from 2026-07-30 and still load-bearing:** generation never reads a bench file (a
bench-reading generator silently weakens a test to fit the hardware present); the CLI is
media-blind (`speed ?` offers `10…400000` on a 1000BASE-SX port, `polarity` on fibre is a silent
no-op) so a media-specific test must classify the port it binds and refuse `unknown`
(`pt_media.py`, real IE520 fixtures, `direct_attach` is not twisted pair); failure messages say
"BENCH PROBLEM, not a product defect"; minimality — the partner IS the far end of a discovered
link, extras are `# NOT BOUND`.

**LAG member links ARE partner ports (Terrence, 2026-09-23):** *"the LAG member links can
absolutely be partner ports."* The preflight already treats them that way, so no change was
needed. **T33234 differs from the frame on empty cages.** It was hand-edited on 2026-09-23
(Terrence: no regenerate) to bind an empty cage for its insertion case. It prefers a matching
fitted module, and falls back to a declared link with an empty cage, whose media the insertion
case checks. The frame template still treats an empty cage as no role.
**Still Terrence's:** the inert `[misc] ck_*` lines in `tb470.setup` (his file, via
device-testing's `bench-state.md` §2).

See [[preflight-topology-check]], [[art-suite-shape]], [[frame-binds-two-roles-only]],
[[scripts-must-be-hardware-agnostic]], [[tb470-topology-and-setup]].
