# Traceability & Supporting Data for AWPTCM-T43851 (IPv4_DHCPServer - DHCP ARP Probe)

## Primary Decision
- From `data/decisions/dec_05.json`: AWPTCM-T43851 {"m": "AWP-3596", "c": "high", "w": "Exact: DHCP server ARP probe enable/disable"}
- Zephyr title: "(27) IPv4_DHCPServer - DHCP ARP Probe"
- Folder: /New Platform Test (MASTER)/New Platform Template/IPv4
- Current Zephyr state: objective "Test for enable and disable probing in DHCP Server", with steps for probe enable/disable.

## Top Relevant TestLink Cases
Primary + closely related DHCP ARP Probe cases from DHCP / DHCP ARP Probe suite.

1. **AWP-3596** (Primary) — DHCP server - ARP Probe - Enable and disable Probing
   - Suite: DHCP / DHCP ARP Probe
   - Summary: Test for enable and disable probing in DHCP Server
   - Steps: Use command to enable/disable lease probing for DHCP pool. probe enable (enabled by default), no probe enable.
   - Justification: Direct high-confidence exact match. Core for enable/disable of ARP probing.

2. **AWP-3594** — DHCP server - Probe IP Address using ARP
   - Suite: DHCP
   - Summary: Verify that when probe parameter is set to ARP, server probes IP address using ARP
   - Justification: ARP probe behavior.

3. **AWP-3550** — DHCP server - Command line test: ARP Probe
   - Suite: DHCP
   - Summary: Test for Ping/ARP Probe commands
   - Justification: CLI for probe.

4. **AWP-3595** — DHCP server - ARP Probe - Configured number of Probe Packets
   - Suite: DHCP
   - Summary: Test Configured number of packets works correctly and verify ARP Probe packet
   - Justification: Number of probe packets.

5. **AWP-3738** — DHCP Server - Probe IP Address with wireless dhcp client
   - Suite: DHCP
   - Summary: Verify that Probing works with the wireless dhcp client.
   - Justification: Wireless support.

**Tangential Cases Reviewed (summary):** 
- AWP-3739 (with ACL ICMP block), AWP-3593 (ICMP probe remote), AWP-15611 (exploratory).
- Decision: Focused on ARP Probe family for enable/disable and config.

## ATPyLib Cases (Step 3)
- Limited direct "dhcp arp probe" hits; general DHCP lease and probing behavior in suites like 1331, 1357, 1399 (DHCP related).
- 1351 Gratuitous ARP may intersect with probe.
- Focus on TL for enable/disable and ARP probe specifics.

## Gaps Noted
- Specific enable/disable probing for DHCP server ARP probe from TL primary.
- ART covers general DHCP server behavior but detailed probing config and ARP vs ping from TL.

## ART Test Cases String
1331/1357/1399 (DHCP server/lease) + 1351 (ARP) + related.

## Synthesis Notes for Objectives
Zephyr objective: Test for enable and disable probing in DHCP Server. Enrich with TL: probe enable (default on), no probe, per pool, probe type arp, number of packets, show commands. Artefacts: probing enabled by default, configurable per pool, uses ARP for lease probing.

---
**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.

Following repeatable workflow in OBJECTIVE_DRAFTING_PROCESS.md.
