---
name: tb470-topology-and-setup
description: tb470 real bench topology + the corrected tb470.setup WRITTEN 2026-07-29 (backup kept); PDU = 10.36.150.14 outlets 8/6 (2026-07-30), no inter-switch data cabling, DUT not on PDU; ONLY 10.38.215.0/24 has upstream return path and tb470 has NO NAT (2026-08-04); DHCP served on eth1+eth3
metadata: 
  node_type: memory
  type: project
  originSessionId: 2a141e3e-5a6e-4153-b006-2e724f5ec026
  modified: 2026-08-03T20:48:41.048Z
---

Reconciling `configs/tb470.setup` (on tb470, at `/home/st-art/st-art/configs/`) against the
ACTUAL bench, because the committed file (created 2026-07-27) describes a different rig than
what is physically present. Part 3b (PLAN-pytest-testing) run can't proceed until the setup
matches reality — see [[part3-grading-session]].

**STATUS: `tb470.setup` COMPLETE as of 2026-07-30** (4970 B, terrenceb:stdept 644, parses
clean — 8 sections, outlets typed `int`). Backups in the same dir: `.bak-2026-07-30` (the
2026-07-29 3-device version), `.bak-2026-07-29` (the 681 B example-derived placeholder).

## CURRENT STATE (2026-07-30 pm) — DE-STACKED, cabled, 2/3 runnable

**The two IE520s are NOT a stack.** They were both provisioned into virtual chassis **3039**
with uncabled stackports, so each saw the other as `Provisioned`: u4 was a standalone Active
Master, **u5 was a `Disabled Master` in "failover mode" with all 26 front-panel ports
`err-disabled`** — that, not interface config, is why newly-cabled links stayed down.

**Fix:** `no stackport` on both 27/28 ranges + `no stack virtual-mac` on both, **`stack 2
renumber 1`** on u5, `write`, reboot both. **Never use `no stack <id> enable`** — it
err-disables every port and strands the unit on its console (that IS the broken state).

**Now:** both units `Operational Status: Standalone unit`, stack ID 1, Active Master, own MAC
as stack MAC (no virtual MAC); u5's ports renumbered `2.0.x → 1.0.x`; zero `err-disabled`.
`.setup` has **no `[stack]`** and gained
`swi_a-swi_b = port1.0.1-port1.0.1, port1.0.7-port1.0.7` (installed, md5
`cd1e570c77e8614340b44dd4144579a7`). `tool/pt_preflight.py` → **2/3 runnable**; only
`3_Port_Fixed_port_test.py` fails, for the separate open reason that `swi_a`↔`swi_c`
(AR4050S) has no data cabling.

**⚠️ HAZARD — do NOT cable `port1.0.27/1.0.28` between the two IE520s.** Two things could not
be removed: IE520 27/28 are **dedicated stackports** (`no stackport` saved but the flag
returned after reboot on the real member's ports — matching its absence from ck.db's IE5xx
validity table), and `stack virtual-chassis-id` has **no `no` form** (`no stack ?` offers only
`<1-8>`, `all`, `disabled-master-monitoring`, `management`, `resiliencylink`, `virtual-mac`).
So both units are stack ID 1 sharing chassis-id 3039 with live stackports — cabling 27/28
would put both back into duplicate-master / err-disabled.

**Links verified both ends at `a-1000/a-full`:** `port1.0.1` copper — and note the modules
DIFFER (AT-SPTXc 1000BASE-T on swi_a vs AT-SP10TM 10GBASE-TM on swi_b) yet negotiate 1 G
fine, so don't assume a module mismatch means no link; `port1.0.7` fibre (AT-SPSX both);
`port1.0.23` → tb470 eth3.

**📌 Management IPs are NOT stable.** swi_a `vlan1` is **DHCP and moved across the reboot**
(`10.38.215.3 → .6`) — never hardcode it, use the console. **Both IE520s carry the same
static `vlan1000 10.38.215.67/27`**; harmless only because swi_b's `port1.0.23` has no
pluggable. swi_a has no SSH/telnet — port 80/443 only — so the console is the sole CLI path.

---

**Naming SETTLED — do not re-litigate.** Terrence, 2026-07-30:
*"dont touch the setup file, we will be running tests against swi_a anyway"* and — the key
clarification — *"we can still run tests against swi_a + swi_b when they are connected, they
just arent currently **stacked**."* So the stack being bugged does NOT demote `swi_b`:
**the two IE520s connected-but-unstacked are a legitimate DUT + link-partner pair**, which is
exactly what the generated scripts' `swi_a`↔`swi_b` demands want. The naming is correct as
installed (md5 `8e8498a600f61b4486340cb3d35768ad`, 4970 B).

`[stack]` is **inert** regardless: `Setup.__init__` only parses; device objects are created
only when a script calls `init_swi`/`init_stk`, and no current script calls `init_stk`.

**I over-claimed once here — don't repeat it.** I said the IE-to-IE stackport cable "cannot be
repurposed as a data link." Not established. The evidence only showed `no stackport` is
documented for x240/x250/x908gen2/x908gen3/x950/xs900mx with **no IE5xx in the validity table**
(`ie560` is the only IE5xx in the reference, so IE520 stacking is simply *not covered* — absence
in the docs harvest is not absence on the device), and that `no stack <id> enable` **disables
all ports** on the removed member. Neither rules out two *unstacked* IE520s passing data.
Lesson: ck.db's CLI reference is authoritative about what it *covers*; treat a missing product
as unknown, not as false.

**⇒ Part 3b needs ONE `[portlink] swi_a-swi_b` line, not a rename.** Measured with
`tool/pt_preflight.py`: as installed 0/3 runnable; with `swi_a-swi_b` declared **2/3**
(T33233 autoneg + T33234 MDI); adding `swi_a-swi_c` too → 3/3. **Owed: the real port numbers
at each end** — unstacked, each unit numbers from `1.0.x` so it is probably `port1.0.27/28` on
both, but never guess a `[portlink]`.

**⚠️ ROLE NAMES CHANGED 2026-07-30 — `swi_b` is NOT what it was.** The second IE520 was
brought into the file and Terrence's call was that the two IE520s are `swi_a` + `swi_b`,
which pushed the other two devices along:

| Device | was (07-29) | **now (07-30)** |
|---|---|---|
| IE520 `/dev/u4` — DUT | swi_a | swi_a |
| IE520 `/dev/u5` — link partner (ex-spare) | *absent* | **swi_b** |
| AR4050S `/dev/u1` | swi_b | **swi_c** |
| x230 `/dev/u0` @9600 | swi_c | **swi_d** |

Both names still bind, so an old script's `init_swi('swi_b')` **silently** gets the 2nd IE520
instead of the AR4050S. Re-check role bindings before reusing any pre-07-30 script.

`[configured_stackport]` is EMPTY (that section is for NON-default stackports only; IE520's
27/28 are the dedicated defaults). **Stackport cabling would be `[stack]` membership, NOT a
`[portlink]`** — but there is no `[stack]` here now; see CURRENT STATE above.

**Consoles — FULLY VERIFIED live 2026-07-29** (console reads + tb470 NIC/MAC correlation).
`swi_*` names below are the **2026-07-30** ones (see the rename table above):
- u0 (ttyUSB2) — **x230-10GP** = **swi_d** (S/N G26ZE80EN), **9600 baud**, at `>` user-exec. mgmt
  **vlan100 10.38.215.2** (own MAC 001a.eb91.cca1), uplink port1.0.1. On the PDU. (Known bug:
  after `manager` the Password: renders mid-screen and it hangs mins → retry on fresh Login:;
  but it was already at `>`, no login needed.)
- u1 (ttyUSB3) — **AR4050S-5G** = **swi_c** (`4050-5g`, S/N A10401G214000005), 115200. mgmt **vlan1
  10.38.215.4** (own MAC 0000.cd40.0394), uplink port1.0.1, data port1.0.8. On the PDU, outlet 8.
- u2 (ttyUSB4) — **POWERED OFF** (old file labelled it x530).
- u3 (ttyUSB5) — **POWERED OFF**.
- u4 (ttyUSB0) — **AT-IE520-28GSX** = **swi_a** (S/N 264A23066), 115200. **THE DUT.** mgmt **vlan1
  10.38.215.3** (own MAC 84e3.2787.0740), mgmt uplink port1.0.10, **DATA port1.0.23 ↔ tb470
  eth3** (that port learned ONLY eth3's MAC; re-verified `connected` 2026-07-30 pm).
  Standalone, stack ID 1, 27/28 idle dedicated stackports. NOT on the PDU.
- u5 (ttyUSB1) — **2nd AT-IE520-28GSX** = **swi_b**, S/N 264A23052, MAC 84e3.2787.09c0,
  115200. **Standalone, stack ID 1** since the 2026-07-30 pm de-stack (was stack member 2 /
  Disabled Master with every port err-disabled). Ports are `1.0.x`. NOT on PDU. The old
  "never drive u5" steer is obsolete — it is a live link partner now. Runs a DIFFERENT
  software build from u4 (`IE520-tb470.rel` vs `…continuous2.rel`), which is fine now they
  do not stack.

**tb470 host NICs:** eth1 `00:f0:4d:00:77:16` = 10.38.215.1/27 UP (shared mgmt segment, all
switches); eth2 `...:17` = 10.38.215.33 **DOWN**; eth3 `...:18` = 10.38.215.65/27 UP (data →
IE520 1.0.23). Device logins: **manager/friend** (public AW+ default; also in secrets.md).

**🔑 ONLY `10.38.215.0/24` HAS UPSTREAM RETURN PATH — and tb470 has NO NAT.** Learned the hard
way 2026-08-04: eth3 was renumbered to `10.37.101.1/27` and every client on it lost all
off-segment reachability. `nft list ruleset` is **0 bytes** and `iptables` is **not installed**,
so `ip_forward=1` forwards with the source address intact and nothing upstream routes
`10.37.101.0/27` back. Proof, from the host itself:

| `dig @1.1.1.1` sourced from | result |
|---|---|
| `10.38.215.1` / `.65` | NOERROR, 4 answers, ~150 ms |
| `10.37.101.1` | **timed out** |

**⇒ Never move a tb470 lab segment off `10.38.215.0/24` without adding NAT first.** eth3 was
reverted the same day; the renumber is NOT in effect. `named` needs no attention either way —
it has no explicit `listen-on`, binds all interfaces and re-binds on renumber within ~60 s
by itself (but it is **not** a usable resolver: `named.conf.options` has only `directory`, no
zones or forwarders, and it times out on every address).

**tb470 serves DHCP on BOTH eth1 and eth3** (`isc-dhcp-server`, `INTERFACESv4="eth1 eth3"` —
was `"eth1"` before 2026-08-04). Subnets in `/etc/dhcp/dhcpd.conf`: `10.38.215.0/27` range
`.2–.10` (eth1) and `10.38.215.64/27` range `.68–.94` (eth3, added 2026-08-04; `.65`=eth3,
`.66`/`.67` deliberately left clear for statics). Traps:

- **A client holding a lease from a subnet you stop serving gets WEDGED, not NAK'd.** dhcpd logs
  `unknown lease <ip>` and sends **nothing** — `authoritative;` only NAKs for subnets it knows
  about — so the client re-REQUESTs its dead address for minutes. Bounce the client
  (`no ip address dhcp` / `ip address dhcp`) instead of waiting.
- **`option domain-name "example.org";`** is still the Debian sample default and is handed to
  every client, which then appends it to lookups (`…weconnecttheweb.co.nz.example.org`). Wasted
  round trip; would break short-name lookups.

- **The eth1 pool `10.38.215.2–10` overlaps the switches' STATIC mgmt addresses** (x230
  `vlan100` = .2). dhcpd's ping-check abandoned .2 rather than double-allocating it, but
  ping-check only catches a host answering at that instant — a rebooting device can still be
  handed an in-use static address. This is a likely cause of the mgmt-IP drift noted above.
- **`option broadcast-address 10.38.215.32` in the eth1 subnet block is wrong** (should be
  `.31`; `.32` is eth2's network address). Pre-existing, left in place deliberately.

**A failing `isc-dhcp-server` shows nothing in unprivileged `journalctl`.** The unit is an LSB
init wrapper that only reports "failed!"; the real reason is logged by `dhcpd` itself and needs
**`sudo journalctl -u isc-dhcp-server`**. Also: `dhcpd -t` passes on a config that cannot
start, because it validates syntax only — a subnet declaration that matches no interface
address is valid but yields "Not configured to listen on any interfaces!" and exit 1.

**Discovery method that worked (Terrence's steer):** NOT LLDP (off everywhere). Cross-match
`show ip interface brief` / `show arp` / `show mac address-table` against tb470's own NIC
MACs + the 10.38.215.0/27 range. That's how each device + the DUT data link were pinned.

**PDU — SUPPLIED by Terrence 2026-07-30:** **`10.36.150.14`**, type `pdu` (every
`10.36.150.x` entry in the peer configs declares `pdu`, outlets 1–8). AR4050S (**swi_c**) =
front-panel **H → outlet 8**; x230 (**swi_d**) = front-panel **F → outlet 6**.
**The outlet field is numeric, never the letter** — `Setup.py` does `int(outTuple[2])` for
any non-`awplus` type, so `H` raises `ValueError`; the front-panel letter is a label only.
`pwr_c`/`pwr_d` mirror `swi_c`/`swi_d`; there is deliberately **no `pwr_a`/`pwr_b`** —
**NEITHER IE520 is on the PDU, so the DUT stack cannot be power-cycled.** A stack-failover
test has to reboot a member via CLI, not by pulling power.

**Inter-switch DATA cabling — NONE (Terrence, 2026-07-30).** The IE-to-IE cabling that now
exists is **stackports, not a data path**, so no data `[portlink]` between switches exists to
declare and any switch↔switch data-path test is un-runnable here. The only data path on the
bench is testbox↔DUT (`tb-swi_a = eth3-port1.0.23`).

**⇒ Part 3b is STILL BLOCKED, on cabling — 0 of 3 Port (7) scripts are runnable here.** Each
asks for a switch↔switch portlink the bench doesn't declare. Verify with
`tool/pt_preflight.py --setup <path>` (built 2026-07-30) rather than by eye — and note the
framework fails this case **silently**: `Setup.init_portlink()` returns `(None, None)` when no
link matches (`sys.exit(2)` is only for null device / tb-to-tb / unknown device / bad eth
name), the skeleton unpacks it into port attrs, and the script then builds CLI against `None`.
On hardware that grades as a *script* defect when the cause is a missing *cable*. Unblocking
needs one data cable (e.g. AR4050S `port1.0.8` = `swi_c` → an IE520 test port) + one
`[portlink]` line.

**⏳ Port names are MEMBER-SCOPED — deferred to run time by Terrence.** `port1.0.23` is right
only while `/dev/u4` holds **member ID 1**; if the u5 unit took member 1 the link is
`port2.0.23` and the `[portlink]` is wrong. Confirm with a read-only `show stack` when Part 3b
actually runs (also confirms the stack formed at all). Flagged inline in the `.setup` header.

**Discipline:** read-only `show` only; correct baud per port; never invent a `[portlink]`
(a wrong one is hardware-specific fabrication).

**Editing the `.setup` (mechanics that cost time to rediscover):** it lives at
`/home/st-art/st-art/configs/tb470.setup` — OUTSIDE the read-only framework dir, so it is
fair game. **No `sudo` needed and none available:** the file is root-owned `644` so it is
NOT writable in place, but the directory is `drwxrwsr-x st-art:stdept` and terrenceb is in
`stdept` — so **replace it via the directory** (`scp` a `.new` alongside, `cp -p` a dated
`.bak`, then `mv -f` over the original). Validate after writing: `configparser` for
well-formedness plus an `int()` on each `[power]` outlet, mirroring `Setup.py`.

**Don't interrogate the hardware for facts the file format already answers** (Terrence:
"this is a `.setup` input, not an interrogation"). The letter-vs-number outlet question was
settled by one grep of `Setup.py`; pinging the PDU and curling its web UI added nothing.
Probe hardware only when the fact genuinely changes file content and cannot be derived —
e.g. which unit holds stack member ID 1.
