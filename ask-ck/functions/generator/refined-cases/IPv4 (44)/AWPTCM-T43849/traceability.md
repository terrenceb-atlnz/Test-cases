# Traceability & Supporting Data for AWPTCM-T43849 (IPv4_ARP - Local Proxy ARP: Functionality)

## Primary Decision
- From `data/decisions/dec_05.json`: AWPTCM-T43849 {"m": "AWP-4357", "c": "high", "w": "Exact: Local Proxy ARP functionality"}
- Zephyr title: "(24) IPv4_ARP - Local Proxy ARP: Functionality"
- Folder: /New Platform Test (MASTER)/New Platform Template/IPv4
- Current Zephyr state: objective "Command \"ip local-proxy-arp\" functionality test", with detailed steps.

## Top Relevant TestLink Cases
Primary + closely related Local Proxy ARP and Proxy ARP cases from ARP suite.

1. **AWP-4357** (Primary) — Local Proxy ARP: Functionality
   - Suite: ARP / Proxy ARP
   - Summary: Command "ip local-proxy-arp" functionality test
   - Steps: Configure DUT and BackupSW on VLAN 23, enable ip local-proxy-arp on DUT, ping from BackupSW to 23.1.1.3. Expect: ping fails but ARP uses DUT MAC.
   - Justification: Direct high-confidence exact match. Core for local proxy ARP functionality.

2. **AWP-4356** — Local Proxy ARP: Command
   - Suite: ARP
   - Summary: Test "ip local-proxy-arp" command
   - Justification: Command acceptance and show in config.

3. **AWP-4358** — Local Proxy ARP: Off by Default
   - Suite: ARP
   - Summary: Confirm that local-proxy-arp is off by default
   - Justification: Default behavior.

4. **AWP-4355** — Proxy ARP: Functionality
   - Suite: ARP
   - Summary: Proxy ARP functions. ARP request outside the network will be replaced by DUT's address.
   - Justification: Related standard proxy ARP for context.

5. **AWP-4370** — ARPs on Static LAGs
   - Suite: ARP
   - Summary: DUT responds to ARPs over Static LAG
   - Justification: LAG interaction.

**Tangential Cases Reviewed (summary):** 
- VRRP interop with local proxy ARP (AWP-11490, 11484).
- ARPs on dynamic LAGs.
- Decision: Focused on local proxy ARP family + standard proxy ARP.

## ATPyLib Cases (Step 3)
- 6201: 6201.1008.1 Check Proxy ARP behavior, 6201.1008.2 Check Proxy ARP with Static IP behaviour, 6201.1031.1 Check Proxy ARP - Transmit unlearned ARP packet behavior.
- 1351 Gratuitous ARP: related ARP behavior.
- Limited direct "local proxy arp" (ip local-proxy-arp); general proxy ARP in 6201.

## Gaps Noted
- Specific local proxy ARP functionality (one-armed router, respond for other hosts on interface) from TL primary.
- ART covers general proxy ARP behavior but local proxy config and exact response (DUT MAC for remote host on same interface) is TL-driven.
- Zephyr has objective but we're enriching.

## ART Test Cases String
6201.1008.1 (Proxy ARP behavior), 6201.1008.2 (with Static IP), 6201.1031.1 (unlearned ARP) + 1351 (gratuitous ARP) + related.

## Synthesis Notes for Objectives
Zephyr objective: Command "ip local-proxy-arp" functionality test. Enrich with TL: DUT responds to ARPs for other IP hosts on same interface (e.g. private VLANs). Positive: responds with DUT MAC for remote host. Negative: off by default. Include LAG variants.

---
**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.

Following repeatable workflow in OBJECTIVE_DRAFTING_PROCESS.md.
