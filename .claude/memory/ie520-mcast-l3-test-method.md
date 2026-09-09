---
name: ie520-mcast-l3-test-method
description: How to run IGMP/MLD-snooping and directed-broadcast test cases on tb470 with ONE host NIC on the u4/u5 fabric (scapy receiver + u5-ping source); the gotchas that cost debugging
metadata: 
  node_type: memory
  type: reference
  originSessionId: 49dcf692-ded5-46ac-ab73-fffb9e6ddec8
  modified: 2026-09-09T02:01:22.596Z
---

Method proven 2026-09-09 running AWPTCM multicast + directed-broadcast cases on tb470
(logs: `old test runs/IE520/switching/{38135,38136,38137,38425,38422,38423,38424,5519,5520}.log`).

**The binding constraint on this bench:** only ONE usable host NIC on the u4/u5 fabric —
`tb eth2 -> u4 port1.0.2`. `eth1 -> u2` is a dead-end (u2 has 0 LLDP neighbours; its only
fabric cabling was the RX-faulty ring ports). u5 has NO host NIC. Fabric = host—u4—[2 links]—u5,
no loopback plugs, no spare cabled ports. So a second HOST capture port is impossible.

**The working pattern (no hairpin needed):**
- DUT/querier = **u4**; multicast **SOURCE = u5's CLI `ping`**; **RECEIVER = the tb470 host**
  (real scapy-crafted IGMP/MLD reports, receipt counted by tcpdump). Source and receiver are
  then genuinely different ports on different devices.
- Loop-safety: run one vlan10 trunk `u4 port1.0.24 <-> u5 port2.0.24` and **shut the 2nd link
  port*.0.26** (RSTP is disabled on these units; don't rely on loop-protection).
- Driver = `console.py` (md5 af85058…) via `/tmp/ckorient/*.py` (tmpfs, not the lab tree).

**Gotchas that each cost a debug cycle:**
1. **IGMP source-address check** is ON by default (`show ip igmp interface` → "Source Address
   checking is enabled"). scapy `sendp` sets IP.src=0.0.0.0 → the report is silently dropped
   and the group never registers. **Set IP.src to a real on-subnet host IP** in the report.
2. scapy IGMP needs `pkt[IGMP].igmpize()` (scapy 2.6, no args) to get a valid checksum +
   router-alert + TTL 1. MLDv1/v2 classes are in `scapy.all` (ICMPv6MLReport/MLDone/
   MLReport2/MLDMultAddrRec); MLD reports source from the host **link-local**.
3. A switch (u5) only sources multicast if it has **`ip[v6] multicast-routing`** — else
   `ping <group>` has no route and never hits the wire. IPv4: `ping <grp> source <svi-ip>`.
   **IPv6 `ping ipv6` syntax = `ping ipv6 <grp> interface vlan10 repeat N`** (interface BEFORE
   repeat; NO `source`, NO `interval` keyword).
4. To make `show ip igmp groups` / `show ipv6 mld groups` populate (what the cases check),
   enable full L3 **`ip igmp` / `ipv6 mld`** on the DUT SVI, not just snooping-querier.
5. `show platform table ipmulti` stays at its baseline 224.0.0.0/24 link entry for same-VLAN
   tests — the group is L2-bridged by snooping, NOT an L3 (S,G) mroute. Don't call that a fail.
6. Leave residue: IGMPv2/v3 leave clears `show...groups` immediately (1 in-flight frame). MLD
   Done clears L3 state at once but the **L2 snooping entry ages out over the last-member
   window** (no fast-leave) → a few residual frames; that's correct, not a defect. IGMPv1 has
   **no leave at all** — group persists until querier group-timeout.
7. **Directed-broadcast tests need FULLY-TAGGED host subinterfaces** (`eth2.<vid>`), not a
   trunk native-vlan: native-vlan untagged broke the vlan10 path here. `ip directed-broadcast`
   goes on the DUT's *egress/target* SVI; disabled = dropped (good control). Remote/off-link
   case: source from a 2nd router (u5) whose off-link subnet SVI is up (add that vlan to an
   up trunk port so the SVI comes up), routed over a /30 transit to the DUT.

See [[tb470-topology-and-setup]] for where bench facts live; [[ckdb-cli-command-hyphen-collapse]]
for reading exact CLI tokens out of ck.db.

**Port-authentication cases (auth-mac / web-auth), added 2026-09-09** (logs:
`old test runs/IE520/authentication/{30142,19223}.log`):
- Use the IE520's **on-box local RADIUS** — no external server: `radius-server local` /
  `server enable` / `nas 127.0.0.1 key K`; `radius-server host 127.0.0.1 key K`;
  `aaa authentication {auth-mac|auth-web|dot1x} default group radius`. (dot1x accepts only a
  RADIUS group — **802.1X-via-TACACS+ is not an AW+ capability**.)
- **auth-mac**: the MAC-auth username the switch sends defaults to hyphen-lowercase
  (`00-f0-4d-00-77-17`); the exact string is in `show radius local-server statistics` →
  "Users NOT present". Register it as `user <mac> password <mac>` to authorise. Unauthenticated
  state: `show auth interface` → `portStatus: Unauthorized`, `packetForwarding: none`; prove the
  block by the peer switch (u5) never learning the MAC / no ARP, and pings 100% loss.
- **web-auth**: `auth-web enable` + `auth-web-server ipaddress <svi>`. Drive it headless with
  curl: unauth HTTP returns `307 -> http://<svi>/`; the portal form POSTs to
  `http://<svi>/index.cgi` with `USERNAME`/`PASSWORD`/`ACTION=login`. On success
  `show auth interface` → `portStatus: Authorized`.
- **Internal DHCP server**: `service dhcp-server` + `ip dhcp pool` (`network`, `range`,
  `default-router`, `lease`); web-auth permits DHCP pre-auth. Test it with a scapy
  Discover/Request (keeps the host's own routing untouched); confirm `show ip dhcp binding`.
- Guest-vlan L3 forwarding cases (T28126-129) need **two supplicant ports + line rate** →
  not doable on this one-host-NIC bench; VCS/tri-auth needs a working 2-member stack.
