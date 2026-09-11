# Topology Profiles — the contract between a generated test and a bench

> **Status:** ACTIVE from 2026-07-30. Machine-readable definitions live in
> [`tool/pt_profiles.py`](../../tool/pt_profiles.py) — **that file is authoritative**; the
> table below is checked against it by `tests/test_pt_profiles.py`, so the two cannot drift.
> Checker: `python3 tool/pt_preflight.py --setup <bench>.setup --profile all`

## The problem this solves

A generated script must run unchanged on any bench — it never names a port. But generation
used to pick its `.setup` role keys **positionally**, from whatever device names the selected
fragments happened to mention ([`_setup_keys_for`](../CK-main/CK_server/routers/pytest_create.py)):
"the third device I saw" became `swi_c`. Nothing had agreed that a bench would provide a
`swi_c`. That is how `3_Port_Fixed_port_test.py` came to demand a `swi_a`↔`swi_c` link **it
never uses** — 4 devices and 2 links bound in `init()`, 1 device and 1 link actually
referenced by the test bodies.

The tempting fix — let generation read the target `.setup` — is wrong. It would silently
**weaken a test to fit the hardware in front of it**: a three-switch test generated against a
two-switch bench becomes a two-switch test, goes green, and the loss is unfalsifiable from
outside. A false green is worse than a hard failure.

## The contract

Generation targets a **contract**, and a contract is not a bench:

| Who | Declares | Reads a `.setup`? |
|---|---|---|
| **Generation** | the **profile** the test needs | **No** |
| **A bench** | the profiles it **implements**, in its own `[misc]` | is the facts |
| **`tool/pt_profiles.py`** | **matches** the two, and lists what is missing | Yes |

Nothing is permitted to edit a requirement to fit a fact. When they don't match, the output
is a **shopping list** (cable this, verify that), never a downgraded test.

### Why profiles rather than one monolithic topology

"One canonical setup" accretes without bound — copper partner, fibre partner, 10G, PoE, hub,
traffic generator, heat chamber — until no real bench satisfies it, at which point
conformance is meaningless. Profiles are claimable **in pieces**, so a bench can honestly say
it implements `base` + `fibre` + `tblink` and does **not** implement `stack`. Partial
conformance is the normal case, not a failure.

### Roles name *links*, not just devices

A role is a **(device, link, media)** triple, because one device can fill two roles over two
different cables — on tb470 `swi_b` is both the copper partner (`port1.0.1`) and the fibre
partner (`port1.0.7`).

This is load-bearing, not tidiness. MDI/MDI-X is a **copper-only** feature; the framework's
`init_portlink(type1='port')` filter **cannot tell copper from fibre** (both are
`port1.0.x`); and the CLI **accepts `polarity` on a fibre port, where it silently does
nothing**. Before this file, `tb470.setup` declared

```ini
swi_a-swi_b = port1.0.1-port1.0.1, port1.0.7-port1.0.7
```

and `init_portlink` took the first not-yet-used match — so the MDI/MDI-X test bound copper
**only because copper happened to be listed first**. One comma-order edit away from setting
`polarity mdix` into the void and reporting a confident green. Asking for `link_copper` *by
name* removes that accident: the choice becomes explicit and reviewable instead of an
emergent property of value ordering. It does **not** by itself guarantee the port is copper —
see Limitations, and pair it with a run-time pluggable assertion.

## What a bench writes

`[misc]` is a section the framework already accepts and stores verbatim, so adding this
breaks no existing bench file:

```ini
[misc]
ck_profile     = base, fibre, tblink        ; comma list — the framework parses it as a list
ck_role_dut    = swi_a
ck_link_copper = swi_a-swi_b:port1.0.1      ; <devA>-<devB>:<port on devA>
ck_link_fibre  = swi_a-swi_b:port1.0.7
ck_link_tb     = tb-swi_a:eth3
ck_cap_swi_b   = polarity                   ; VERIFIED on the device — never from the docs
```

- **`swi_a` is always the DUT.** Dynamic role resolution needs one fixed anchor for "which
  device is under test", and this is it. Declared explicitly as `ck_role_dut` anyway, so the
  checker never has to assume.
- **The `:<port>` suffix disambiguates** which of several links between the same pair is
  meant. That is the whole copper/fibre fix.
- **Keep link values comma-free** — the framework turns any comma-bearing `[misc]` value into
  a list. `ck_profile` is deliberately a comma list.
- **`ck_cap_*` records hardware-verified capabilities.** It is tempting to derive these from
  `ck.db`'s `cli_command_products`, and that is **wrong**: `polarity` is documented for 29
  products **not including `ie520`**, yet both IE520s on tb470 support it (confirmed at the
  console, `polarity ?` in interface config, 2026-07-30). **Absence from the harvested CLI
  reference means UNKNOWN, never unsupported.**

## The profiles

| Profile | Requires | Why it is separate |
|---|---|---|
| `base` | `ck_role_dut`; `ck_link_copper`; the far end must have verified `polarity` | The floor for physical-layer port tests. They need a partner to negotiate against, and partner-side polarity control is what makes a crossover case **automatable** instead of a manual cable swap. |
| `fibre` | `ck_link_fibre` | Fibre has **no MDI/MDIX concept at all**, so a fibre link can never satisfy a copper requirement — and the framework's type filter cannot tell them apart. |
| `tblink` | `ck_link_tb` | A testbox↔DUT data path is independent of switch↔switch cabling: a bench can have partners but no testbox link, or the reverse. |
| `stack` | `ck_role_dut` naming a `[stack]` of ≥ 2 members | **Not `base` plus a device.** Stacking renames every port (`1.0.x` → `N.0.x`), which leaks into portlinks, fragments and every port literal — so stacked and unstacked benches are different topologies, not sub/supersets. Demonstrated live on 2026-07-30: u5's ports read `2.0.x` while stacked and `1.0.x` after. |

## How the generated frame binds these (2026-09-07, ART shape)

`TestSet.init()` binds through one helper, `_ck_bind_link(setup, dut, misc, '<role>')`,
which reads `ck_link_<role>`, refuses a `(None, None)` portlink, asserts the media, and
returns `(near_port, far_port, far_device)`. Two roles are rendered, each only when the
case's wording needs it (`_detect_links` in `routers/pytest_create.py`):

| Role | Binding in `init()` | Handles the units use |
|---|---|---|
| `tb` (profile `tblink`) | `(dutA.portA, tb.ethA, _tb) = self._ck_bind_link(setup, dutA, misc, 'tb')` — the far end is the testbox itself, so the helper calls `init_portlink(dut, self.tb, type1='port')` and never `init_swi` | `tb`, `ethA`, `portA` — capture / inject on `ethA.name`, the DUT port under test is `portA` |
| `copper` / `fibre` (profile `base` / `fibre`) | `(dutA.portPeer, peer_port, peer) = self._ck_bind_link(...)`, then `peer.portDut = peer_port`, `self.peer = peer` | `peer`, `portPeer`, `peer.portDut` — the neighbour switch, never the DUT |

This is the corpus's own topology: 111 of 188 ART tests bind `(dut.portA, tb.ethA)` and
capture on the testbox; a second switch is named by role (`swiSrc`, `dutZ`), never `dut`.
Before this the frame bound one partner, called it `dut`, and bound nothing on the testbox —
so every model wrote `tb.ethA` and `dut.portA` anyway (T44297: 59 / 63 unbound-port lint
errors, all frame-caused). The media role `tb` has **no media requirement** (`pt_media.
ROLE_REQUIRES["tb"] = ()`): any fitted pluggable passes, an empty cage is still a bench
problem. `ck_link_tb = tb-swi_a:eth3` is the declaration a bench writes.

## Limitations — read before trusting a green

1. **Media is NOT machine-verified, and no offline checker can fix that.** The checker
   confirms the named port is a real endpoint of a declared link and has the right *interface
   type* (`port` vs `eth`) — but copper and fibre are both `port1.0.x`, so pointing
   `ck_link_copper` at a fibre port **passes**.

   It is worse than a checker gap: media is a property of the **pluggable**, which anyone can
   swap in seconds without touching any file. It already differs across this bench *in the
   same port number* — u4 `port1.0.1` is a 1000BASE-T, u5 `port1.0.1` is a 10GBASE-TM. So a
   media claim in a `.setup` is stale-able by a hardware change no tool can observe.

   Treat `ck_link_copper` as **intent, not a guarantee**: it says which link the test should
   bind, which is what removes the comma-order accident. Safety comes from a **run-time
   assertion** — read the bound port's media and fail loudly before running a media-specific
   matrix. That assertion is implemented in [`tool/pt_media.py`](../../tool/pt_media.py):

   ```python
   out  = dut.cmd('show interface {} status'.format(port.name))
   ok, why = assert_role_media(out, port.name, 'copper')
   if not ok:
       self.failed(why)        # message names the BENCH as the cause, not the product
   ```

   It parses the `Type` column (column-sliced, because an empty cage reports the two-word
   `not present`), classifies to `twisted_pair` / `fibre` / `direct_attach` / `absent` /
   `unknown`, and **refuses `unknown` rather than assuming copper** — guessing the common case
   is how you get a confident wrong verdict. Validated against real captured output from both
   tb470 IE520s. Note `direct_attach` (twinax `BASE-CR`/`BASE-CX`) is deliberately *not*
   twisted pair: it is electrically copper but has no MDI/MDIX concept either, so lumping it
   in would reintroduce this bug in a new shape.

   ✅ **Wired 2026-07-30.** The skeleton's fixed `_ck_bind_link()` performs it on every bound
   link, `ck_media.py` ships into the run workdir with every run (read from `tool/pt_media.py`
   so it is byte-identical to the tested module), and a lint makes it **the only** path to a
   bound port: a direct `setup.init_portlink()` outside the helper is an error, because a port
   bound that way carries no media guarantee.

   Scope, deliberately: media only matters where the test asserts media-dependent behaviour —
   speed, duplex, MDI/MDI-X, autoneg, and later PoE and cable diagnostics (TDR), all
   copper-only. A VLAN or routing test needs a working link but not a particular medium, and
   for those `needs_portlink` may render no binding at all. That is self-correcting rather
   than silent: if such a body does read a port attribute, the same lint errors because
   nothing bound it.

   Why this is not pedantry, measured on tb470 2026-07-30: the CLI is **media-blind**. On the
   1000BASE-SX fibre port, `speed ?` still offers `10 … 400000` and `duplex ?` still offers
   `half`, identically to copper. Nothing rejects a nonsensical setting. So a speed/duplex
   matrix bound to fibre — which is 1000 Mbps-only — records **"DUT failed to set speed
   100"**, a false failure blamed on the DUT; and `polarity` on fibre is a silent no-op, since
   MDI/MDI-X is a twisted-pair crossover concept with no fibre equivalent. Both failure modes
   look like product defects and neither is.
2. **Capabilities are self-declared.** `ck_cap_*` is a claim by whoever edited the bench file.
   The policy — verify on the device, never infer from docs — is enforced by review, not by
   the tool.
3. **Conformance is not runnability.** A bench can implement `base` and still fail a specific
   script that over-declares its needs. Script-level checking is the other half:
   `pt_preflight.py --setup <bench>` without `--profile`.

## Adding a profile

1. Add a `Profile(...)` entry to `PROFILES` in [`tool/pt_profiles.py`](../../tool/pt_profiles.py).
2. Add a row to the table above. `tests/test_pt_profiles.py` asserts the table and the code
   list exactly the same profiles, so a missing row fails the gate.
3. Declare it in whichever bench files can implement it, and verify with
   `--profile <name>`.

Start narrow. A profile that nothing implements is worse than no profile, because it makes
conformance reports noisy without making any test runnable.

## tb470 as at 2026-07-30 — SUPERSEDED, kept as a worked example of the report format

> ⚠️ **This is not the current bench.** It described a de-stacked IE520 pair with copper and
> fibre links between them. The two IE520s have been ONE STACK since 2026-08-18, those links
> no longer exist, and `ck_profile` is now deliberately **empty** — the bench implements no
> generation profile at all. For current state read `~/claude/IE520-testing/bench-setup/bench-state.md`.
> The block below is retained only to show what a conformance report looks like.

```
tb470.setup claims: base, fibre, tblink

IMPLEMENTS  base      dut=swi_a; copper swi_a<->swi_b via port1.0.1; swi_b polarity verified
IMPLEMENTS  fibre     fibre swi_a<->swi_b via port1.0.7
IMPLEMENTS  tblink    tb<->swi_a via eth3
DOES NOT IMPLEMENT  stack     swi_a is not a [stack] — the two IE520s were deliberately
                              de-stacked on 2026-07-30
```

Not implemented and not currently cabled for: a **second independent partner** (no data
cabling to `swi_c`/`swi_d`), PoE, or a traffic generator. Saying so explicitly is the point —
before this, a script asked for `swi_c` and nobody could tell whether that was meaningful.
