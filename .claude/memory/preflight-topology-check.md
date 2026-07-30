---
name: preflight-topology-check
description: "tool/pt_preflight.py checks a generated script's topology demands against a bench .setup offline, because init_portlink fails SILENTLY"
metadata: 
  node_type: memory
  type: project
  originSessionId: 55f64c5f-6b57-4d85-9f09-b5090301f55a
  modified: 2026-07-30T00:09:29.447Z
---

`tool/pt_preflight.py` (built 2026-07-30) answers "can this bench run this script?" offline —
no LLM, no network, no hardware. Reads the script with `ast`, the bench with `configparser`.

**Why it must exist:** `Setup.init_portlink()` returns **`(None, None)`** when the bench
declares no matching link (`sys.exit(2)` is reserved for fatal misconfig — null device,
tb-to-tb, unknown device, bad eth name). The skeleton unpacks that straight into port
attributes, so both ends become `None` and the script builds CLI against `None`. On
`3_Port_Fixed_port_test.py` it doesn't even fail subtly: `portA.name` raises
`AttributeError` and all 7 TestCases die identically — reading as a *script* defect when the
cause is *bench cabling*. Exactly the false signal Part 3b criteria 5-6 must not ingest.

Models the framework's real semantics, all mutation-verified: links are **consumed** (one
cable serves one `init_portlink` call), **either orientation** matches, empty `type1`/`type2`
match any interface, a **stack** stands in for any member. Two problem classes: `LINK` and
`POWER` (power-cycling a device with no `[powerlink]`).

Usage: `scp tb470:/home/st-art/st-art/configs/tb470.setup /tmp/` then
`python3 tool/pt_preflight.py --setup /tmp/tb470.setup`. Exit 0/1/2.
`--profile <name>|all` switches to bench-conformance mode — see
[[topology-profiles-contract]].

**Testing discipline that made it worth anything:** a checker that returned "unsatisfiable"
unconditionally would have produced the correct 0/3 verdict for the real scripts and been
worthless. So every "cannot" assertion in `tests/test_pt_preflight.py` is **paired with a
mutation** that makes the demand satisfiable and requires the verdict to flip; the tool was
also mutated six ways (always-fail, always-succeed, no consumption, no type filter, no stack
expansion, no power check) and every mutation is caught. See [[mutate-before-you-claim]].

**Root cause it exposed, still open:** generation over-declares. T33235 binds 4 devices and 2
links, uses **1 device and 1 link** — `_setup_keys_for` hands out `swi_a/swi_b/swi_c`
positionally from fragment device names, so "the third name I saw" became a `swi_c` demand
nothing needed. Fix is minimality (no bound device or link unused; role keys contiguous from
`swi_a`), NOT bench-awareness — see [[topology-profiles-contract]].

Fixture note: `tests/test_pt_preflight.py` keeps `BENCH_STACKED` as an explicitly **synthetic**
bench (the tool must still handle stack semantics) plus `TB470_LIVE` for the real current
shape. Don't let the synthetic one drift into claiming it mirrors tb470.
