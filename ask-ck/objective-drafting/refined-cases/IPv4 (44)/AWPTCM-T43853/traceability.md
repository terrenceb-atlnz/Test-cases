# Traceability & Supporting Data for AWPTCM-T43853 (IPv4_DHCPServer - DHCP 120-day lease)

## Primary Decision
- From `data/decisions/dec_05.json`: AWPTCM-T43853 {"m": "AWP-3578", "c": "high", "w": "DHCP server 120-day lease"}
- Zephyr title: "(25) IPv4_DHCPServer - DHCP 120-day lease"
- Folder: /New Platform Test (MASTER)/New Platform Template/IPv4
- Current Zephyr state: empty objective, thin steps.

## Top Relevant TestLink Cases
Primary + closely related DHCP lease cases from DHCP Server / DHCP Client suites.

1. **AWP-3578** (Primary) — DHCP server - 120 day lease configured
   - Suite: DHCP / DHCP Server
   - Summary: Test for DHCP server to offer 120 day lease time to a DHCP Client.
   - Steps: Configure DUT as DHCP Server. Create a DHCP Pool with 120 day lease time (lease 120 0 0). Verify config. Client obtains 120 day lease.
   - Justification: Direct high-confidence exact match. Core for 120-day lease on server side.

2. **AWP-3579** — DHCP client - correctly obtain 120 day lease time
   - Suite: DHCP / DHCP Client
   - Summary: Test for DHCP Client if it correctly obtained the 120 day lease time from the DHCP Server.
   - Justification: Client side verification of 120 day lease.

3. **AWP-9771** — DHCP Snooping - log - lease deleted
   - Suite: DHCP Snooping / Debug & Log messages
   - Summary: Log message when lease deleted should be seen at user level.
   - Justification: Related logging for lease operations.

4. **AWP-15615** — DHCP Client Lease Renewal
   - Suite: Exploratory Tests
   - Summary: (exploratory for lease renewal).
   - Justification: Lease renewal context.

5. **AWP-2475** — DHCP client - Lease time
   - Suite: DHCP / DHCP Client
   - Summary: Test for DHCP client if it correctly refresh the IP address based on the configured lease time.
   - Justification: General lease time behavior.

**Tangential Cases Reviewed (summary):** 
- AWP-9770 log new lease, AWP-2271 1 minute lease, exploratory lease acceptance.
- Decision: Focused on 120-day lease family for server/client.

## ATPyLib Cases (Step 3)
- 1331: 1331.1001.54492 dhcp-server crash when offering infinite lease time (related lease handling).
- 1357/1399/1333: DHCP server lease, binding, ACK/RELEASE, snooping interactions.
- General DHCP lease assignment and client behavior in DHCP suites.
- Limited direct 120-day; more on lease times, bindings, infinite/edge cases.

## Gaps Noted
- Specific 120-day lease on server (lease 120 0 0) and client obtaining 120 days from TL primary.
- ART covers general lease behavior, bindings, crashes for infinite, but exact 120-day from TL.
- Zephyr thin (empty objective).

## ART Test Cases String
1331.1001.54492 (infinite lease crash) + 1357/1399 (DHCP server lease/binding) + 1333 (snooping lease) + related DHCP suites.

## Synthesis Notes for Objectives
Zephyr thin. Enrich with TL: DHCP server configured with 120 day lease (lease 120 0 0) offers it. Client obtains correct 120 day lease. Include config in running, client verification via show dhcp lease or binding. Contrast with other leases if relevant.

---
**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.

Following repeatable workflow in OBJECTIVE_DRAFTING_PROCESS.md.
