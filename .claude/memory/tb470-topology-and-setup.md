---
name: tb470-topology-and-setup
description: tb470 real bench topology + the corrected tb470.setup; **2026-08-18: the two IE520s ARE A STACK (chassis-id 3439, NOT 3039), virtual-mac ENABLED (VMAC 0000.cd37.0d6f), stack on port1.0.28<->port2.0.27, resiliency link vlan4093 on port1.0.27<->port2.0.28 — and `no stackport` on 27/28 DOES stick across a reboot, correcting the old "the flag returns" claim**; both IE520s on the PDU (10.36.150.14, u4=outlet 4 "D", u5=outlet 5 "E"); the setup file had the two IE520 S/N+MAC pairs on the OPPOSITE consoles (live: u4=264A23052, u5=264A23066); ONLY 10.38.215.0/24 has upstream return path and tb470 has NO NAT (2026-08-04); DHCP on eth1+eth3; stack state churns — ALWAYS run `show stack`, and a destacked unit KEEPS its old stack ID and its port1.0.x go phantom, silently
metadata: 
  node_type: memory
  type: project
  verified: 2026-09-01
  originSessionId: 2a141e3e-5a6e-4153-b006-2e724f5ec026
  modified: 2026-08-18T08:30:00.000Z
---

Reconciling `configs/tb470.setup` (on tb470, at `/home/st-art/st-art/configs/`) against the
ACTUAL bench, because the committed file (created 2026-07-27) describes a different rig than
what is physically present. Part 3b (PLAN-pytest-testing) run can't proceed until the setup
matches reality — see [[part3-grading-session]].

**STATUS: `tb470.setup` COMPLETE as of 2026-07-30** (4970 B, terrenceb:stdept 644, parses
clean — 8 sections, outlets typed `int`). Backups in the same dir: `.bak-2026-07-30` (the
2026-07-29 3-device version), `.bak-2026-07-29` (the 681 B example-derived placeholder).

## CURRENT STATE (2026-08-18) — read this first; everything below is HISTORY

**⚠️ THE TWO IE520s ARE A STACK, and the chassis-id is now `3439` (0xd6f), NOT `3039`.**
Left this way at the end of the 17688 session. Verify with `show stack` — this bench churns.

| | member 1 | member 2 |
|---|---|---|
| console | `/dev/u5` | `/dev/u4` |
| S/N | `264A23066` | `264A23052` |
| MAC | `84e3.2787.0740` | `84e3.2787.09c0` |
| bootloader | `9.1.0` | `pauld` dev build |
| role at session end | Active Master (`awplus`) | Backup Member (`awplus-2`) |

- **`stack virtual-mac` is ENABLED** (this session enabled it) → **VMAC `0000.cd37.0d6f`**, which
  encodes the chassis-id (`0d6f` = 3439). `show stack` reads `Stack MAC address 0000.cd37.0d6f
  (Virtual MAC)`. Enabling it needs `write` + reboot.
- **Stacking link is a SINGLE pair: `port1.0.28` ↔ `port2.0.27`.**
- **Resiliency link is `vlan4093` on `port1.0.27` ↔ `port2.0.28`** (the *other* former stackport
  pair). `stack resiliencylink <vlan>` takes a **dedicated VLAN**, not a port; ports then join it
  with `switchport resiliencylink` (interface mode) and carry *only* resiliency traffic.
- **`interface vlan1 / ip address 10.38.215.20/27`** was added so a split would generate learnable
  traffic. ⚠️ **Consider removing** — while stacked it is harmless, but any future split puts
  **two units on that address**, on the only segment with an upstream return path.
- **`no stackport` was applied to `port1.0.25`, `port1.0.26`, `port1.0.27`, `port2.0.28`.**
- Both members **netboot via TFTP** from tb470 (`IE520-tb470.rel`) — member 2 as well as member 1,
  confirmed from its bootloader banner. Boot config `flash:/stack.cfg`.

**🐛 OPEN PRODUCT DEFECT — the resiliency link does not work on this build.** Whichever member
holds the **backup role** receives 100% of the master's healthcheck multicasts error-free and
never registers them: `show stack resiliencylink` reads `Failed` on the backup
(= "Not receiving any healthchecks from the Active Master") while it transmits **zero** replies.
Reproduced across **4 port pairs** (1000BASE-SX 1G, 10GBASE-SR 10G matched *and* mismatched
numbering, and the 10G copper stacking PHYs), **both units**, **both roles**, **both bootloader
builds**, and 4 reboots — so port/media/unit/bootloader are all excluded; the fault tracks the
ROLE. Consequence: pulling the stacking cables yields **TWO ACTIVE MASTERS sharing one VMAC and
one IP**, not a Disabled-Master — the neighbour switch then sees the same bridge ID on two ports
and blackholes one. **This blocks TEST 17688 steps 3–7.** Software: `IE520-tb470.rel`,
`tomahawk_ie520-continuous`, built 2026-08-10. Full evidence + verdict table:
`~/old test runs/IE520/stack-tests/after-action-17688.md`.

**✅ CORRECTION — `no stackport` DOES stick on the dedicated stackports 27/28.** The older claim
below (and in `TESTBOX-ACCESS.md` §4a) that "the flag returns after reboot on the real member's
ports" **did not reproduce**: `no stackport` on `port1.0.27` and `port2.0.28` survived a full
stack reboot, both came back as ordinary `switchport`s in vlan 1, and the stack ran normally on
the remaining pair. Two mechanics that still apply: `no stackport` needs `write` + reboot to take
effect, and `switchport resiliencylink` is **rejected** on a port while it is still a stackport
(`% The command is not available for this interface`) — so repurposing 27/28 is a two-pass job.
`stack virtual-chassis-id` still has **no `no` form** (not retested 2026-08-18).

**The 27/28 cabling hazard still stands, but scope it correctly:** it applies to **two
_standalone_ units both claiming stack ID 1 with the same chassis-id**. On a *properly formed*
stack, one 27/28 pair was repurposed as a resiliency link with no ill effect.

## CURRENT STATE (2026-08-11) — HISTORY

**✅ BOTH IE520s ARE NOW ON THE PDU.** Fitted 2026-08-11: `/dev/u4` (swi_a) = outlet **4**
(front-panel "D"), `/dev/u5` (swi_b) = outlet **5** ("E"), same PDU `10.36.150.14`. **This
retires the repeated "neither IE520 is on the PDU / the DUT cannot be power-cycled" statement
throughout the rest of this file** — it was the single thing blocking the 5700 bootloader
suites here. `tb470.setup` gained `pwr_a`/`pwr_b` + two `[powerlink]` lines (backup
`.bak-2026-08-11`). Letter→number is **A–H = 1–8**.

**⚠️ THE TWO IE520s WERE RECORDED ON THE WRONG CONSOLES.** Read from the devices 2026-08-11
(`show system serialnumber`, `show stack`):

| Console | S/N | MAC | hostname |
|---|---|---|---|
| `/dev/u4` = swi_a | `264A23052` | `84e3.2787.09c0` | `awplus` (factory-reset 2026-08-10) |
| `/dev/u5` = swi_b | `264A23066` | `84e3.2787.0740` | `u5` |

`tb470.setup` (and the 2026-07-29 console list further down this file) had those two S/N+MAC
pairs on the **opposite** consoles. The pairs are internally consistent, so it is a swap, not
a one-field typo — either the USB console cables were exchanged, or 2026-07-30 transcribed it
backwards. **Unresolved which.** The role bindings are unaffected (swi_a is still `/dev/u4`),
but swi_a is a different physical unit than the file claimed. Corrected in `tb470.setup`.

**State of `264A23066` (u5) — previously UNKNOWN, now read:** standalone, stack ID 1, Active
Master, but still carries a **Provisioned member 2**, so its phantom `port2.0.x` range is
present in `show interface brief`. `vlan1 = 10.38.215.66/27` admin-up but protocol DOWN;
`vlan100 = 192.168.100.2/24` running; no vlan1000. `port1.0.23` = `notconnect`, Type
**`not present`** (no pluggable). Both units confirm `Operational Status: Standalone unit`.

**u4 after its factory reset:** `vlan1 = 169.254.42.42/16` — **APIPA, i.e. the DHCP client is
finding no server**, because every port but `port1.0.7` is down. It is NOT still on the
`10.38.215.69` lease recorded on 2026-08-10. `port1.0.23` = `notconnect` with a 1000BASE-T
pluggable fitted. Neither unit has a `vlan1000` any more, so the old "both carry the same
static 10.38.215.67/27" hazard no longer applies.

**No tb↔DUT link is up.** `eth2` and `eth3` both report `Link detected: no`; on both IE520s
every front-panel port is down except `port1.0.7` (the inter-switch fibre, up both ends). The
`port1.0.1` copper inter-switch link is DOWN. The eth3 cable was moved on 2026-08-11 for the
5700 campaign, so `[portlink] tb-swi_a = eth3-port1.0.23` is declared but **not live**.

**IE520 TFTP boot needs a USB-Ethernet dongle — see [[ie520-tftp-boot-needs-usb-nic]].**

## CURRENT STATE (2026-08-10) — HISTORY

**Stack state on this bench CHURNS. Never trust a recorded stack state — run `show stack`.**
Between 2026-07-30 and 2026-08-10 the two IE520s were **re-stacked** into one stack
(hostname `u5`; member 1 = S/N `264A23066`, member 2 = S/N `264A23052`), directly
contradicting the "both standalone" state recorded below. Terrence then destacked the u4 unit
again mid-session for a parallel workflow.

**⚠️ THE SILENT TRAP — a destacked unit KEEPS its old stack ID.** After that destack, the unit
on `/dev/u4` (S/N `264A23052`, MAC `84e3.2787.09c0`) was standalone but still **stack ID 2**:

    ID   Pending ID  MAC address        Status  Role
    1    -           -                  -       Provisioned      <- phantom, absent member
    2    -           84e3.2787.09c0     Ready   Active Master
    Operational Status                 Standalone unit

So its REAL ports were `port2.0.x`, and the whole `port1.0.x` range was phantom:
`Hardware is Provisioned, address is 0000.0000.0000`. **This fails silently** — `show interface
brief` still lists a full `port1.0.x` range (status `provisioned`), and config naming those
ports is ACCEPTED with no error. It cost an afternoon: `ip address dhcp client-id port1.0.6`
encoded DHCP **option 61 as `00:00:00:00:00:00`**, which reads exactly like a product defect
and is not one. Verified by contrast: `port1.0.23` = `Provisioned/0000.0000.0000` while
`port2.0.23` = `Link is UP, Hardware is Ethernet` with real counters.

**⇒ Before ANY test step that names a port on a standalone unit, check `show stack` reads
ID 1.** Renumber with `stack <old-id> renumber 1` (config mode) + reboot if it does not.

**Remedy applied 2026-08-10 (with sign-off), unit `264A23052` only:** `erase startup-config`,
`stack 2 renumber 1`, `reboot`. Now: **standalone stack ID 1**, hostname `awplus`,
`port1.0.6` = `Hardware is Ethernet 84e3.2787.09c0`, `port1.0.23` = the live tb470 uplink.
Config wiped — **no SNMP, no NTP, no `vlan100`** (was `192.168.100.2/24`). Only current config
is the DHCP client: `interface vlan1 / ip address dhcp client-id port1.0.6 hostname dhcp-test`,
leasing `10.38.215.69/27` from tb470. Login is back to the `manager`/`friend` default.

**State of the OTHER IE520 (`264A23066`) is UNKNOWN** — it was stack member 1 and was not
touched after the destack. Check it before assuming anything.

**A factory-defaulted AW+ device FORCES a password change at first login.** It accepts
`manager`/`friend`, then demands `Enter new password:` before granting a prompt. Automation
that only knows `login:`/`Password:` will feed its next command into that dialog (mine typed
`enable` as the new password). Any procedure starting from factory default needs a step for it.

**tb470 host services, verified 2026-08-10 — both already configured, do not "set them up":**
- **NTP:** chrony 4.6.1 already serves the lab (`allow 10.0.0.0/8`, `local stratum 10`, bound
  `0.0.0.0:123`), synced upstream at stratum 3. A client pointed at `10.38.215.65` syncs in one
  poll and lands at stratum 4.
- **DHCP:** isc-dhcp-server is LIVE with ~14 active leases — `10.38.215.2-10` on eth1,
  `10.38.215.68-94` on eth3. **Do not add a subnet to a wire that already has a pool**; two
  subnets on one interface make dhcpd's pool selection ambiguous for every client on it.

## CURRENT STATE (2026-07-30 pm) — SUPERSEDED, kept for the de-stacking procedure

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

> **🔴 SUPERSEDED 2026-08-18 — do not act on the paragraph above.** Two of its facts are now
> wrong: (1) **`no stackport` DOES stick on 27/28** across a reboot — see CURRENT STATE
> (2026-08-18) at the top; (2) the chassis-id is **`3439`**, not `3039`, and the units are a
> **stack (ID 1 + ID 2)**, not two standalone ID-1 units. The *hazard itself* survives but only
> in its original scope: two **standalone** units both claiming ID 1 with a shared chassis-id.
> `stack virtual-chassis-id` having no `no` form was not retested and is carried forward.

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


---

## Verified on the bench 2026-09-01 — read this before trusting anything above

Everything in this section was read off the hardware today. Where it contradicts the older text,
**this section wins.**

**Membership: the 2026-08-26 unit swap was REVERTED.** The handover in
`~/old test runs/IE520/stack-tests/failover-300/SESSION-HANDOVER.md` records 264A23066 being
pulled and replaced with **264A23061**. That is no longer the bench. Live today:

| | ID 1 | ID 2 |
|---|---|---|
| S/N | **264A23066** | 264A23052 |
| MAC | `84e3.2787.0740` | `84e3.2787.09c0` |
| Console | `/dev/u5` (banner `awplus`) | `/dev/u4` (banner `awplus-2`) |
| Bootloader | `9.1.0` | `pauld` dev build |

264A23061 appears nowhere in the 2026-08-31 logs. No record of when or why it went back was
found. **So the console↔S/N mapping matches the pre-swap record again — but re-verify anyway.**

**Priority is inverted and will flip mastership on any reboot.** ID 2 is priority **1**, ID 1 is
**128**; lowest wins and there is no pre-emption, so ID 1 is master only until something reloads.
Anything assuming "master = ID 1" is wrong after one reboot. (Confirmed: a reboot at 10:32
handed mastership to ID 2.)

**Both 27/28 pairs are STACKPORTS again and the resiliency link is `Not configured`.** The
vlan4093 resiliency link described above is gone. The 17688 resiliency defect is therefore not
currently set up on this bench — it is history, not live state.

**Both units reboot on their own, roughly 1-2.5 times per day, while completely idle.** Measured
over 2026-08-21..24, a window with **zero** files modified across every campaign directory:
ID 1 = 10 events (~2.5/day), ID 2 = 6 (~1.5/day). This is the single biggest confound on this
bench: a 17.8 h test run produced ONE "failure" against an idle expectation of ~1.9. **Do not
attribute a reboot to your test without an idle control.** By contrast the AR4050S on the same
bench and PDU has been up 20+ days.

**A wedge must be confirmed against uptime / `show reboot history`, never console silence.**
The stack runs `default.cfg` since the swap, so `line con 0 / exec-timeout 0 0` is gone and the
AW+ default logout applies. A read-only console logger that never sends a byte gets timed out;
the console then emits garbled interleaved characters and goes silent — indistinguishable from a
device lockup. This produced a false "wedge reproduced" on 2026-09-01 which the device disproved
(uptime continuous, no `BootROM`, no reboot-history entry).

**The mv64xxx I2C bus-lock defect is FIXED.** `show tech-support` x6 on 2026-09-01 was 6/6 clean
— no `I2C bus locked`, no wedge, no reset — well past the iteration and time window where every
historical lock occurred (always iteration <=2, at +55..+71 s). Root cause was the single module
AT-SPTXc `A10217F213300006`, removed 2026-08-20. It is also **not** connected to the stackport
"wedge": no lock signature appears in any 38378 log, and that module was gone five days before
that run.

**Addressing and clocks (new).**

- tb470 = `10.38.215.65` (eth3), chrony **stratum 2**, `allow 10.0.0.0/8` — it will serve NTP here.
- AR4050S `4050-5g` = `10.38.215.70/27` on vlan1, now NTP-synced from tb470 and written to config.
- dhcpd pool on this /27 is `.68-.94`; **`.66/.67` are deliberately kept clear for statics**, so
  `10.38.215.66/27` is the right address for the IE520 stack. The stack currently has **no IP**.
- The IE520 stack has `clock timezone NZST` + `clock summer-time NZDT` in **startup-config**, but
  its absolute time is hand-set: a warm reboot preserves it, a power cycle does not, and there is
  no NTP until it gets an address.
- Consequence: `show reboot history` on the stack now spans **two timebases** — entries after
  2026-09-01 10:32 are NZST, everything older is UTC (+12). The whole existing evidence corpus is
  UTC.

**Cabling as measured today.** `port1.0.1` (member 1) is cabled to the **x230**, not the 4050 —
the 4050's own MAC `0000.cd40.0394` and tb470's `00f0.4d00.7718` are both learnt on `port1.0.1`.
`port2.0.1` shows link but has learnt no MACs. `port2.0.9` is unplugged. **The L2 loop is real
and was live this morning**: `0000.cd40.0394` was thrash-limiting between `port1.0.1` and
`port2.0.9` — two unaggregated paths to the 4050 — until the direct leg was unplugged at 09:09:26.
Cost measured at ~30% of a `show tech-support` collection time. **Two links to one device on this
bench must be a single LACP aggregation, or they loop.**
