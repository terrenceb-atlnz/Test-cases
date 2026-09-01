# `.setup` File Reference — the testbox topology declaration

> **Why this file exists.** The `.setup` is the one hard dependency of every ART run
> (`sudo python3 <script>.py -s <setup> -v`), and its schema had never been written down —
> `ART-EXECUTION-CHAIN.md` carried an open TODO to *"capture a working example"* and the
> format kept being re-derived from scratch. It is captured here once, from a real testbox,
> so it can be reused instead of rediscovered.
>
> **Authoritative parser:** `DeviceSkrips/framework/Setup.py` (READ-ONLY on the testbox —
> see the framework-read-only guard). Where this doc and `Setup.py` disagree, `Setup.py` wins.
>
> **The `.setup` is a DECLARATION, not something to infer.** Stack membership, stack ports,
> and testbox cabling are all stated here as fact. Do not guess them from case text, platform
> names, or CLI output — that mistake has now been made twice in this project (once for port
> naming, once for stack detection, 2026-07-28).

## Worked example — a real three-device testbox

```ini
###
### swi_a = x930
### swi_c = AR4050S
### swi_d = x530
###

[power]
pwr_a = (pdu, 10.36.230.112, 1)
pwr_b = (pdu, 10.36.230.112, 2)
pwr_c = (pdu, 10.36.230.112, 3)

[switch]
swi_a = /dev/u0
swi_c = /dev/u1
swi_d = /dev/u2

[stack]
stk_a = swi_a

[powerlink]
swi_a = pwr_a
swi_c = pwr_b
swi_d = pwr_c

[boot_from_flash]
swi_a = True
swi_c = True
swi_d = True

[portlink]
tb-swi_a = eth2-port1.0.15
tb-swi_c = eth3-port1.0.5
tb-swi_d = eth4-port1.0.14
swi_a-swi_c = port1.0.1-port1.0.1,port1.0.3-port1.0.2,port1.0.5-port1.0.3
swi_a-swi_d = port1.0.8-port1.0.1,port1.0.10-port1.0.15,port1.0.12-port1.0.24
swi_c-swi_d = port1.0.6-port1.0.20,port1.0.7-port1.0.7,port1.0.8-port1.0.8
```

Note the header comment naming which physical model each `swi_*` key is. It is a comment,
not parsed — but it is the only place that mapping is recorded, so keep writing it.

## The sections that matter most

### `[switch]` — device name → console
```ini
swi_a = /dev/u0
```
Maps the `.setup` device key to its **USB serial console**. This is the same `uN` namespace
as the shell aliases on a testbox (`u5` is `minicom --wrap -D /dev/u5`, and `/dev/u5` is a
udev symlink onto some `/dev/ttyUSBnn`). Older setups in the corpus use a bare integer
(`swi_dorm_a = 0`) for the same field — both forms are in the wild.

The KEY (`swi_a`, `swi_b`, …) is what `init_swi('swi_a')` looks up; 621 of ~650 corpus calls
use that convention. The local variable carries the ROLE (`dutA = setup.init_swi('swi_a')`) —
never put a role name inside `init_swi()`.

### `[stack]` — which devices form a stack
```ini
stk_a = swi_a, swi_b        # a two-member stack
```
A comma-separated member list. **This is the authoritative answer to "is the DUT a stack".**
Bound by `init_stk()`; 195 of the 830 corpus scripts use it.

### `[configured_stackport]` — non-default stack links
```ini
[configured_stackport]
swi_a = port1.0.25, port1.0.26
swi_b = port2.0.25, port2.0.26
```
Only needed when the stacking ports are **not** the platform defaults. Place it **above**
`[portlink]`. Parsed by `Setup.py:508-514`; consumed by real ART scripts
(`1331_past_issues`, `1338_cont_reboot`, `1346_swi_misc`, `6008_ART_runup_ext`).

This is the declarative source for "ports a test must never configure" — shutting a stack
link splits the stack, and the run then reports a product failure that is really a test bug.

### `[portlink]` — physical cabling
```ini
tb-swi_a    = eth2-port1.0.15                                   # testbox NIC -> switch port
swi_a-swi_c = port1.0.1-port1.0.1,port1.0.3-port1.0.2           # switch -> switch
```
`<devA>-<devB> = <portOnA>-<portOnB>`, comma-separated for multiple links. The literal
device `tb` means **the testbox itself**, so `tb-swi_a = eth2-port1.0.15` declares that the
testbox's `eth2` is cabled to that switch's `port1.0.15`. Nine `.setup` files in the corpus
declare `tb-` links.

This is what makes a generated script hardware-agnostic: `init_portlink()` resolves the real
port names at run time, so the same source runs on an x930, an AR4050S or an x530 unchanged,
and yields `port1.1.x` on a chassis. **Never hardcode a port name in a script** — take it
from here.

### `[boot_from_flash]`
```ini
swi_a = True
```
When booting over **TFTP instead of flash, remove the entries entirely** — do not set them
`False`.

### `[power]` / `[powerlink]`
`[power]` declares outlets as `(type, ip, outlet)` — `pdu` and `sentry` both appear in the
corpus. `[powerlink]` maps each device to its outlet, which is what lets a test power-cycle
a device.

## Every section `Setup.py` accepts

From `Setup.py:342` — anything else is ignored:

```
power, wireless, switch, hub, stack, profile, peripheral, powerlink, portlink,
breakout, no_switchport, namemap, configured_stackport, reslink, ixia, heatchamber,
baudrates, atmf, atmf_areas, misc, email, ixia_tx_pkt_rate, ixia_rx_pkt_rate,
ixia_tx_bit_rate, ixia_rx_bit_rate, database, feature_map_file_location,
management, boot_from_flash
```

`[reslink]` declares resiliency-link ports; `[ixia]` declares traffic-generator ports as
`<card>, <user>`.

## Authoring checklist

1. Comment the model behind each `swi_*` key at the top of the file.
2. `[switch]` — one line per device, pointing at its `/dev/uN` console.
3. `[stack]` — list **all** members: `stk_a = swi_a, swi_b`.
4. `[configured_stackport]` — only if the stack ports are non-default; place above `[portlink]`.
5. `[portlink]` — `tb-swi_X` lines first, then inter-switch links.
6. `[boot_from_flash]` — drop the entries when booting over TFTP.
7. Live examples: `raw data/test_scripts/5712_Release_Testing_Transceivers/sample.*.setup`
   (single switch / multi-switch / stack-and-peer) and
   `raw data/test_scripts/5053_validation_kochi/kochi_uni_tb105.setup` (large, no `tb-` links).

## Where this is used

- **PyTest Creator step 6 (Run)** picks a `.setup` from the testbox profile and passes it as
  `-s <path>`. Nothing in `CK_server` parses `.setup` today — it is uploaded and handed to
  the framework verbatim. Parsing it would let the lint check a generated script against the
  real topology (e.g. "this configures a port `[configured_stackport]` declares a stack link").
- **`configs/<hostname>.setup`** is the default location the suite runners resolve via
  `Setup.get_default_setup_file()`. `configs/tb470.setup` **exists** (it did from 2026-07-27,
  and Part 3b was unblocked on 2026-07-29 — an earlier version of this line said otherwise and
  was stale). For tb470 it is **generated** from
  `~/claude/IE520-testing/bench-setup/bench-state.md`, which is the source of truth for that
  bench; read that for state, and this document for the format.
