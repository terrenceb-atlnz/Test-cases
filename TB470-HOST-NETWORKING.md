# tb470 host networking — DHCP, routing, and packet capture

**Scope: the tb470 Linux host itself**, not the bench it fronts and not the switches on it.
Split out of `TESTBOX-ACCESS.md` on 2026-09-02, where it had accreted under a title about
*access*: none of this is about reaching a testbox, and keeping it there meant a reader looking
for SSH mechanics had to scroll past DHCP-server repair.

Where the neighbouring facts live — **do not copy any of them back into this file**:

| Looking for | Read |
|---|---|
| what is cabled to what, PDU outlets, bench addressing | `~/claude/IE520-testing/bench-setup/bench-state.md` (source of truth) |
| how to reach a testbox and drive a console | `TESTBOX-ACCESS.md` |
| IE520 platform limits, framework traps, driver choice | `.claude/skills/orient-ie520/SKILL.md` |

Verified 2026-08-04 unless noted; the `10.38.215.0/24` finding re-confirmed 2026-09-02.

---

Came out of repairing `isc-dhcp-server` on tb470 and then tracing why a switch could not reach
the IDevID provisioning proxy. All of it is host-side; none of it touches the framework.

## 🔑 Only `10.38.215.0/24` has an upstream return path, and tb470 has NO NAT

This is the big one. `nft list ruleset` is **0 bytes** and **`iptables` is not installed**, so
`ip_forward=1` forwards lab traffic with its source address **intact** and relies entirely on
the org network knowing how to route the reply back. It knows `10.38.215.0/24`. It knows
nothing else you invent. Proof, run from tb470 itself:

```bash
dig +time=4 +tries=1 -b 10.38.215.1  @1.1.1.1 pool.ntp.org   # NOERROR, 4 answers, ~150 ms
dig +time=4 +tries=1 -b 10.37.101.1  @1.1.1.1 pool.ntp.org   # timed out
dig +time=4 +tries=1 -b 10.36.201.215 @1.1.1.1 pool.ntp.org  # NOERROR (mgmt address)
```

**⇒ Never move a lab segment off `10.38.215.0/24` without adding NAT first.** Renumbering eth3
to `10.37.101.1/27` cost every client on it all off-segment reachability, and it presents as
"DNS doesn't work" / "the service is unreachable", not as a routing error. `dig -b <addr>` is
the cheapest way to separate *destination unreachable* from *source unroutable* — the same
query differs only by source address.

`named` needs no attention across a renumber: it has no explicit `listen-on`, binds all
interfaces and re-binds within ~60 s by itself. It is **not** a usable resolver, though —
`named.conf.options` holds only `directory`, no zones and no forwarders, and it times out on
every address it listens on.

## A failing `isc-dhcp-server` hides its reason from unprivileged `journalctl`

The unit is an **LSB init wrapper** (`/etc/init.d/isc-dhcp-server`, systemd-sysv-generated), so
it only reports `Starting ISC DHCPv4 server: dhcpdcheck syslog for diagnostics. ... failed!`.
The real reason is logged by `dhcpd` itself at a privileged level:

```bash
sudo journalctl -u isc-dhcp-server --no-pager -n 40    # sudo is NOT optional here
```

**`dhcpd -t` is not a startup check.** It validates *syntax* and will pass happily on a config
that cannot start. A `subnet` declaration matching no interface address is perfectly valid and
yields `No subnet declaration for <iface> (<ip>)` → `Not configured to listen on any
interfaces!` → exit 1. To prove which interfaces a *running* dhcpd actually bound, don't trust
`ss -lunp` (it shows one `0.0.0.0:67`); read the per-interface raw sockets:

```bash
sudo ss -0 -p | grep dhcpd      # one p_raw line per interface, e.g. *:eth1  *:eth3
cat /proc/net/packet            # cross-check Iface column against /sys/class/net/<if>/ifindex
```

## A client holding a lease from a subnet you stopped serving gets WEDGED, not NAK'd

dhcpd logs `unknown lease <ip>` and **sends nothing back** — `authoritative;` only makes it NAK
for subnets it knows about, and the stale address is in none of them. The client re-REQUESTs its
dead address for minutes (unicast, then broadcast REBINDING) and only recovers when the lease
fully expires. Bounce the client instead of waiting: on AW+, `no ip address dhcp` then
`ip address dhcp` on the relevant vlan.

## Two pre-existing traps in tb470's `dhcpd.conf`

- **The eth1 pool `10.38.215.2–10` overlaps the switches' static management addresses** (the
  x230's `vlan100` is statically `.2`). dhcpd's ping-check catches it — `ICMP Echo reply while
  lease 10.38.215.2 valid` → `Abandoning IP address 10.38.215.2: pinged before offer` — but
  ping-check only sees a host that answers *at that instant*, so a rebooting device can still be
  handed an address already in static use. A plausible contributor to the mgmt-IP drift in §4a.
- **`option domain-name "example.org";`** is still the Debian sample default and is handed to
  every client, which then appends it to lookups (`…weconnecttheweb.co.nz.example.org`). A
  wasted round trip per resolution, and it breaks short-name lookups.

## Packet capture on a testbox

`tcpdump` 4.99.5 and `tshark` are both installed and sudo is passwordless. Detach the capture so
the SSH call returns immediately, and bound it with `timeout` so a forgotten capture can't fill
the disk:

```bash
CAP=/tmp/eth3-cap-$(date +%Y%m%d-%H%M%S).pcap
sudo sh -c "nohup timeout 300 tcpdump -i eth3 -nn -s0 -U -w $CAP >/tmp/cap.log 2>&1 &"
# -U flushes per packet, so the file is readable WHILE the capture runs
```

Write a real pcap rather than parsing text, so one firing of a hard-to-repeat event can be
re-analysed from several angles. Reading it back:

```bash
sudo tcpdump -nn -r "$CAP" | grep -vE 'LLDP|ARP'
sudo tshark -r "$CAP" -Y dns -T fields -e frame.time -e ip.dst -e dns.qry.name \
     -e dns.flags.response -e dns.a
sudo tshark -r "$CAP" -Y tls -T fields -e tcp.srcport -e tls.record.content_type \
     -e tls.handshake.type -e tls.alert_message.desc
```

**Read the error text as a layer indicator.** `Operation timeout` meant nothing came back — the
capture held DNS queries with zero responses and **not one TCP packet**. After the fix the same
command failed with `device is disabled`, which is a *substantive answer* and therefore proof the
whole path works: you can only be told you are disabled by a server you reached, TLS-handshook
with, and submitted to. A changed error is progress; check the layer before re-debugging the
network.

Two capture-reading notes: identify the far-end device from **LLDP** in the capture
(`-Y lldp -e lldp.port.id`) rather than guessing from the MAC — a switch's L3 interface MAC need
not match the base MAC in §2. And under **TLS 1.3 the server certificate is encrypted**, so an
absent cert subject is expected, not a failure; look for `tls.alert_message` instead, and treat
`content_type 22,20` in one record as normal middlebox-compat mode.

## IDevID installs need working time first

An AW+ device installing an IDevID resolves and syncs NTP **before** it contacts the proxy,
because certificate validity windows need a real clock. It walks `pool.ntp.org` →
`time.google.com` → `time.nist.gov`, then looks up
`proxy.idevid-test.weconnecttheweb.co.nz`. A DNS or egress fault therefore surfaces as an NTP
storm first and a proxy timeout second — fix reachability, not the IDevID config.

