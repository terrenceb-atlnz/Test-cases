---
verified: 2026-09-23
---
# Topology — what a bench cables, and how the generated frame finds it

> **Status:** REWRITTEN 2026-09-21. The `[misc]` *role contract* this file specified from
> 2026-07-30 (`ck_profile`, `ck_role_dut`, `ck_link_<role>`, `ck_cap_*`, the profile table and
> `ask-ck/tools/pt_profiles.py`) is **retired**. Terrence, 2026-09-21: *"I dont want the [misc]
> section to be callable as a workaround for not using the existing framework commands. We have
> a suite of 'show' commands that identify whatever we need to, the information shouldnt require
> pre-loading variables to know it."* The old text is in git history (`f354f14^`); the retired
> commits are `e022e1c` / `6ada916` (reverted in `b96255c` / `f354f14`). Plan:
> `archive/plans/PLAN-frame-framework-discovery.md`. Checker: `python3 ask-ck/tools/pt_preflight.py --setup <bench>.setup`.

## The two facts a generated script must not carry

A generated script runs unchanged on any bench. It therefore **names no port and no partner**.
Both come from somewhere else at run time, and the framework already provides that somewhere:

| need | the framework already answers it | corpus uses (827 scripts in `ck.db`) |
|---|---|---|
| the DUT | `setup.init_swi('swi_a')`, `setup.init_stk('stk_a')` — `swi_a`/`stk_a` **are** the framework's portable DUT slots; every bench maps them to its own hardware | 297 / 192 (`init_swi('dutA')` or any other role-named key: **0**) |
| the DUT's stack | `swi.get_stack()` (None when standalone), `stack.all_members()` | 270 / 139 |
| every cable on a device | `dev.get_all_port_links()` → `{far_device: [(local_port, far_port), …]}` | 38 |
| the testbox among them | `isinstance(far, ATTestBox.TestBox)` | `library_5712._get_swi_tb_link` |
| what is in a port | `show interface <port> status` (Type column), `show system pluggable` | 34 scripts |

So a **link partner is any device with a `[portlink]` to the DUT that is not the testbox and
is not one of the DUT's own stack members.** It is not a declared range. The framework's own
sample (`raw-data/test_scripts/5712_Release_Testing_Transceivers/sample.stack_and_peer.setup`)
declares `stk_a = swi_a, swi_b`, a peer `swi_c`, and one line
`swi_c-swi_b = port1.0.25-port2.0.25`; `init_portlink(stk, swiDst)` finds it by walking the
stack's members. Nothing tags `swi_c` as "the partner": having a cable to the DUT is what makes
it one.

The **media** in a port is a property of the pluggable, swappable in seconds with no file change
(on tb470 the same port number differs between units: u4 `port1.0.1` 1000BASE-T, u5
`10GBASE-TM`). A declaration of it goes stale the moment someone swaps a module. The device
knows; the file cannot. That is the whole reason nothing is pre-declared.

## What a bench writes

Only what the framework already reads: `[switch]`, `[stack]`, `[portlink]` (plus power and
consoles as usual). **`[misc]` is not read by the frame or the preflight.** A bench that wants
to host a test cables it and declares the cable:

```ini
[switch]
swi_a = /dev/u2          ; the DUT slot (or a member of the DUT stack)
swi_e = /dev/u1          ; a partner — any name, it is a partner because of the cable below

[stack]
stk_a = swi_a, swi_b, swi_c, swi_d

[portlink]
tb-swi_c    = eth1-port3.0.2         ; testbox <-> DUT (a stack member)
swi_a-swi_e = port1.0.2-port1.0.2    ; DUT (member) <-> partner
swi_d-swi_e = port4.0.2-port1.0.4    ; a second DUT <-> partner cable
```

## The roles, and how `init()` binds them

`_detect_links()` (`routers/pytest_create.py`) decides from the case wording and the slice-C
`claim`s **how many links of which media the case needs** — a role set. The frame then binds
one link per role, discovered at run time:

| role | DUT-side port is | required? | handles the units use |
|---|---|---|---|
| `tb` | the far end is the `TestBox` | yes — aborts | `tb`, `ethA`, `portA`; capture / inject on `ethA.name` |
| `copper` | twisted pair in a **fixed** port (falls back to a copper SFP only if no fixed one is left) | yes — aborts | `peer`, `portPeer`, `peer.portDut` |
| `fibre` | a **fitted** fibre module | optional — `self.fibre_supported` | `fibre_peer`, `portFibre`, `fibre_peer.portFibre` |
| `cusfp` | twisted pair **in a cage** (listed by `show system pluggable`) | optional — `self.cusfp_supported` | `cusfp_peer`, `portCuSfp`, `cusfp_peer.portCuSfp` |

`TestSet.init()` (fixed frame, `pt_script_template.py.jinja`):

```python
tb  = setup.init_tb()
dut = setup.init_swi('swi_a')
_stk = dut.get_stack()                  # ART's shape: commands -> dut (Switch), ports -> dut_stack
dut_stack = setup.init_stk(_stk.name) if _stk is not None else None
self.dut_stack = dut_stack
self._ck_topo = self._ck_discover(dut, dut_stack)   # one pass over the port owner's links
(dut.portA, tb.ethA, _tb)               = self._ck_bind_link(setup, dut, 'tb')
(dut.portCuSfp, cusfp_port, cusfp_peer) = self._ck_bind_link(setup, dut, 'cusfp', optional=True)
(dut.portFibre, fibre_port, fibre_peer) = self._ck_bind_link(setup, dut, 'fibre', optional=True)
(dut.portPeer, peer_port, peer)         = self._ck_bind_link(setup, dut, 'copper')
```

**Never re-bind `dut` to the Stack** (corrected 2026-09-23). The framework's `Stack` has no
`cmd`, and the frame did exactly that from 2026-09-21, so every command would have died on a
stacked DUT. 103 of 239 ART scripts bind both handles, and the frame now does the same.

`_ck_discover(dut, unit)` walks `unit.get_all_port_links()` (the stack when there is one, else
`dut`), skips stack members, takes the `TestBox`
far end as the testbox link, and for every other link runs `show interface <port> status` and
`show system pluggable` on the DUT side: twisted pair in a cage → `cusfp`, twisted pair fixed →
`copper`, fibre → `fibre`, `not present` → `absent`. **An empty cage is `absent` and is never a
role** — Terrence: *"cages themselves aren't 'fibre' or 'copper' cause they're empty."* A
pluggable role is satisfied only by a module **fitted at `init()`**; otherwise the flag is
False, the handles are None, and the cases that need it report UNSUPPORTED
(`self.supported = False`) instead of failing. Insertion steps therefore start from a fitted
module (remove, verify down, re-fit, verify up) and re-check media afterwards with the frame's
module-level `assert_role_media_now(testCase, dut, port, role)`.

`_ck_bind_link(setup, dut, role, optional=False)` hands out one discovered link per role,
pluggable roles first so `copper` cannot consume a copper SFP, never the same link twice, and
initialises a partner switch once however many links go to it. A **required** role with no link
raises `RuntimeError("BENCH PROBLEM, not a product defect: …")` naming the links it did find —
"this bench cannot host this test" is not a test result. Far ports are **role-specific**
(`peer.portDut`, `fibre_peer.portFibre`, `cusfp_peer.portCuSfp`) because two pluggable links
usually land on the same partner switch, and a shared `.portDut` would be overwritten.

There is **no `init_portlink()`** in the frame: the tuples from `get_all_port_links()` already
hold the port objects, and choosing by media is exactly what `init_portlink`'s first-unused
matching could not do (the 2026-07-30 "copper only because it was listed first" accident).
The lint makes this the only path: `init_portlink()` outside a legacy `_ck_bind_link` body, or
`init_swi()`/`init_stk()` outside `TestSet.init()`, is an error (policy class).

## Media identification (`ask-ck/tools/pt_media.py`, shipped as `ck_media.py`)

The CLI is **media-blind**, measured on an IE520 2026-07-30: on a 1000BASE-SX port `speed ?`
still offers `10 … 400000` and `duplex ?` still offers `half`. A speed matrix bound to fibre
records "DUT failed to set speed 100" — a false failure blamed on the product — and `polarity`
on fibre is a silent no-op (MDI/MDI-X is a twisted-pair crossover concept). So the frame asks
the device and classifies: `twisted_pair` / `fibre` / `direct_attach` / `absent` / `unknown`,
**refusing `unknown` rather than assuming copper**. `direct_attach` (twinax `BASE-CR`/`BASE-CX`)
is deliberately not twisted pair: electrically copper, no MDI/MDIX. `pluggable_ports()` reads
`show system pluggable` in both first-column spellings (`1.0.25` and `port1.0.25`). Fixtures
are real captured IE520 output.

## Limitations — read before trusting a verdict

1. **Offline, only cables are knowable.** `pt_preflight.py` confirms a testbox↔DUT link exists
   for `tb` and that enough unused DUT↔partner `port` links exist for the partner roles; it
   matches required roles before optional ones and says, for every satisfied partner role,
   that *whether that link IS copper / fibre / cusfp is read from the DUT at run time*. An
   optional role with no link is a note (UNSUPPORTED), not a problem.
2. **A cable the bench uses for something else still counts as a cable.** On tb470 the two
   stack↔`swi_e` links are legs of one LAG carrying vlan10; the preflight reports them as
   takeable partner links because the file says nothing else. Whether they may serve a
   physical-layer test is a bench decision (Terrence's), not the tool's.
3. **Discovery costs show commands at `init()`** — one `show system pluggable` plus one
   `show interface <port> status` per partner link. A bench with many declared links pays for
   each; none is repeated.
4. **A partner reached over its console only** (a case with no link at all) is still bound
   positionally as `swi_b`, because there is no cable to discover it from.

## tb470 on 2026-09-21, for the record

> The bench has been rebuilt since — on 2026-09-23 it became a three-member stack plus a
> standalone IE520, with new partner links (`bench-state.md` in device-testing is the current
> shape). The preflight verdict below has not been re-run against it.

`tb470.setup.current` declares three testbox links and two stack↔`swi_e` links, no `[misc]`
that anything reads. The discovery frame rendered for AWPTCM-T33234's real sequence is
RUNNABLE there offline: `tb` via `tb-swi_c`, `copper` + `cusfp` via the two `swi_e` links (media
to be read on the bench), `fibre` UNSUPPORTED. Whether the frame's run-time classification
agrees is the manual check that follows.
