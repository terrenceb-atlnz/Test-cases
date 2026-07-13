# Traceability & Supporting Data for AWPTCM-T43858 (IPv4_UnicastRouting - BGPv4)

## Primary Decision
- From `data/decisions/dec_05.json`: AWPTCM-T43858 {"m": "AWP-7650", "c": "high", "w": "BGPv4 unicast traffic (obj match)"}
- Zephyr title: "(34) IPv4_UnicastRouting - BGPv4"
- Folder: /New Platform Test (MASTER)/New Platform Template/IPv4
- Current Zephyr state: objective "Check and verify BGPv4 for correct status and functionality.", steps for unicast traffic.

## Top Relevant TestLink Cases
Primary + closely related BGPv4 unicast traffic validation cases.

1. **AWP-7650** (Primary) — BGPv4 - Unicast Traffic
   - Suite: Validation Scenario / BGPv4
   - Summary: Check and verify BGPv4 for correct status and functionality.
   - Steps: Run background unicast traffic in the relevant scenario. => traffic passes through the scenario. Line rate traffic is achieved as expected.
   - Justification: Direct high-confidence match. Core for BGPv4 unicast traffic.

2. **AWP-14120** — BGP4+ - Unicast Traffic (similar)
   - Suite: Validation Scenario / BGP4+
   - Summary: Check and verify BGPv4 for correct status and functionality.
   - Justification: Closely related BGP unicast.

3. **AWP-7681** — IPv4 Static Routes - Unicast Traffic
   - Suite: Validation Scenario
   - Summary: Check and verify IPv4 Static Routes for correct status and functionality.
   - Justification: Related unicast traffic validation.

4. **AWP-7775** — VCS - Unicast Traffic
   - Suite: Validation Scenario
   - Summary: Check and verify VCS for correct status and functionality.
   - Justification: Unicast in stack context.

**Tangential Cases Reviewed (summary):** 
- Other unicast: VLANs, EPSR, OSPFv3, RIP.
- Decision: Focused on BGPv4 unicast traffic family.

## ATPyLib Cases (Step 3)
- 2001: BGP4 connection, Established state, routes from Update (2001.1.1-1.3).
- 2002: ORIGIN attribute, ICMP/forwarding.
- 2036: Similar BGP4 connection, Established, routes (2036.1.1-1.3), MP_REACH, TCP IPv4/IPv6.
- Validation 1330/ etc. for traffic, but BGP specific in 2001/2036.
- Limited direct "unicast traffic" in BGP suites; more protocol conformance.

## Gaps Noted
- Specific BGPv4 unicast traffic (line rate, status) from TL validation.
- ART covers BGP peering, attributes, but traffic forwarding scenarios from TL.
- Zephyr thin on steps.

## ART Test Cases String
2001.1.1/1.2/1.3 (BGP connection, Established, routes), 2036.1.1/1.2/1.3 (similar) + 2002 (attributes, forwarding).

## Synthesis Notes for Objectives
Zephyr: Check and verify BGPv4 for correct status and functionality. Enrich with TL: BGPv4 establishes, unicast traffic passes at line rate. Include peering, route learning, traffic.

---
**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.

Following repeatable workflow in OBJECTIVE_DRAFTING_PROCESS.md.
