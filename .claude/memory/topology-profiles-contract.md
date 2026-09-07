---
name: topology-profiles-contract
description: "Generated tests target a PROFILE contract, never a bench .setup; spec TOPOLOGY-PROFILES.md + tool/pt_profiles.py; media is deliberately NOT machine-verifiable"
metadata: 
  node_type: memory
  type: project
  originSessionId: 55f64c5f-6b57-4d85-9f09-b5090301f55a
  modified: 2026-07-30T00:39:22.072Z
---

Terrence's design call, 2026-07-30. **Generation must never read a bench `.setup`.** A
bench-reading generator silently *weakens* a test to fit the hardware present — a 3-switch
test generated against a 2-switch bench compiles, runs, goes green, and the loss is
unfalsifiable from outside. Instead generation targets a **contract**, and a contract is not
a bench:

- generation → declares the **profile** its test needs (reads no `.setup`)
- a bench → declares the profiles it **implements**, in its own `[misc]`
- `tool/pt_profiles.py` → **matches** them, emits a shopping list

Spec: `ask-ck/pytest-create/TOPOLOGY-PROFILES.md`. Check:
`python3 tool/pt_preflight.py --setup <bench>.setup --profile all`.
**`tool/pt_profiles.py` is authoritative**; a test asserts the spec's table and `PROFILES`
list identical names, so they cannot drift (mutation-verified).

**Profiles, not one monolith** — "one canonical topology" accretes (copper/fibre/10G/PoE/hub/
traffic-gen/heat-chamber) until no bench satisfies it. Claimable in pieces; partial
conformance is normal. Defined: `base` (DUT + copper partner with verified `polarity`),
`fibre`, `tblink`, `stack`.

**Roles name LINKS, not devices** — a role is (device, link, media), because one device fills
two roles over two cables. `[misc] ck_link_copper = swi_a-swi_b:port1.0.1`; the `:port`
suffix says *which* of several links between a pair is meant. `swi_a` is always the DUT
(`ck_role_dut`). Keep link values comma-free — the framework turns a comma-bearing `[misc]`
value into a list; `ck_profile` is deliberately a comma list. `[misc]` is framework-accepted
and free-form, so adding this breaks no existing bench file.

**`stack` is NOT `base`+1 device**: stacking renames every port (`1.0.x`→`N.0.x`), leaking
into portlinks, fragments and every literal. See [[tb470-topology-and-setup]].

**Capabilities are HARDWARE-VERIFIED claims** (`ck_cap_swi_b = polarity`), never derived from
`ck.db`: `polarity` is documented for 29 products **not** including `ie520`, yet both tb470
IE520s support it. Docs absence = UNKNOWN, not unsupported.

## The limitation that matters most — media is unverifiable offline, by nature

Copper and fibre are **both** `port1.0.x`, so pointing `ck_link_copper` at a fibre port
**passes the checker**. Do not "fix" this by trusting the declaration:

- media is a property of the **pluggable**, swappable in seconds with no file change — it
  already differs in the same port number here (u4 `port1.0.1` 1000BASE-T, u5 10GBASE-TM);
- the **CLI is media-blind**: on a 1000BASE-SX port, `speed ?` still offers `10…400000` and
  `duplex ?` still offers `half`. Nothing rejects a nonsensical setting.

Consequence, and why it's worth caring: a speed matrix bound to fibre (1000 Mbps-only)
records **"DUT failed to set speed 100"** — a false failure blamed on the product — and
`polarity` on fibre is a silent no-op (MDI/MDI-X is a twisted-pair crossover concept).
So `ck_link_copper` is **intent, not a guarantee**. Pinned by
`test_media_is_NOT_verified_and_the_spec_says_so`, which will fail if the checker ever gains
media awareness — rewrite the spec's Limitations if so.

**The run-time guard is BUILT: `tool/pt_media.py`** (31 tests). `assert_role_media(out, port,
'copper')` on `show interface <port> status`. Parses the `Type` column by **column slice off
the header** — an empty cage prints the two-word `not present`, which `split()[-1]` reads as
`"present"`. Classifies `twisted_pair`/`fibre`/`direct_attach`/`absent`/`unknown` and
**refuses `unknown` rather than assuming copper**. `direct_attach` (twinax `BASE-CR`/`BASE-CX`)
is deliberately not twisted pair — copper but no MDI/MDIX. Failure messages must say
"BENCH PROBLEM, not a product defect" or they defeat the purpose. Fixtures are real captured
IE520 output; `1000BASE-T` (u4) vs `10GBASE-TM` (u5) sit on the **same port number**, which is
the standing proof media can't be inferred from a port name.
✅ **WIRED into generation 2026-07-30.** The skeleton's fixed `_ck_bind_link()` resolves
`ck_link_<role>` from `[misc]`, refuses a `(None, None)` portlink, and asserts media;
`ck_media.py` ships with every run (read from `tool/pt_media.py`, byte-identical); and a lint
makes the helper **the only** path to a bound port — a direct `setup.init_portlink()` outside
it is an error. Role via `_detect_link_role` (copper default, fibre wording detected); a wrong
role can't cause a wrong verdict because the assertion stops the run and blames the bench.

**MINIMALITY — over-declaration is now structural, not advisory.** The device set used to come
from the selected fragments' variable vocabulary, decided at render time *before any body
existed*, so it could only over-bind (T33235: 4 devices bound, 1 used). Now the device set is a
CONSEQUENCE of the topology: **one link ⇒ one partner, and the partner IS that link's far
end** — no second `init_swi()` exists to over-declare with. Extras are dropped with a
`# NOT BOUND:` comment. Safety net: using a device `init()` never bound is a lint ERROR
(`self.linkP.cmd(...)` compiles, so otherwise it dies with AttributeError mid-bench-slot).

**Media scope (Terrence, 2026-07-30):** only matters where the test asserts media-dependent
behaviour — speed/duplex/MDI-X/autoneg, and later PoE + cable diagnostics (TDR), all
copper-only. Most cases don't care, so `needs_portlink` rendering no binding for them is fine,
and self-correcting: a body that reads a port attribute without a binding errors.

**2026-09-07 — the frame now binds TWO roles, ART-shaped.** `tb` (profile `tblink`):
`(dutA.portA, tb.ethA, _tb) = self._ck_bind_link(setup, dutA, misc, 'tb')` — the helper takes
the testbox end via `self.tb` and `init_portlink(dut, tb, type1='port')`, media role `tb` has
NO media requirement (`ROLE_REQUIRES["tb"] = ()`, empty cage still fails). `copper`/`fibre`:
`(dutA.portPeer, peer_port, peer)` then `peer.portDut = peer_port` — the neighbour is `peer`,
never `dut` (ART's `dut` = the DUT's stack; a partner called `dut` made every model read
`dut.portA` as the DUT port, 59/63 unbound-port errors on T44297). `_detect_links` decides
which links from the case wording, over-inclusive on purpose. See [[art-suite-shape]].

Companion: [[preflight-topology-check]] for the script-level half.
