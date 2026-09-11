# Traceability & Supporting Data for AWPTCM-T43859 (IPv4_UnicastRouting - VRF-Lite)

## Primary Decision
- From `data/decisions/dec_05.json`: AWPTCM-T43859 {"m": "AWP-4286", "c": "high", "w": "Exact: VRF-Lite traceroute"}
- Zephyr title: "(35) IPv4_UnicastRouting - VRF-Lite"
- Folder: /New Platform Test (MASTER)/New Platform Template/IPv4
- Current Zephyr state: objective "VRF-Lite support traceroute operation", steps for traceroute vrf and global.

## Top Relevant TestLink Cases
Primary + closely related VRF-Lite traceroute and utility cases from VRF-Lite suite.

1. **AWP-4286** (Primary) — VRF Lite Traceroute
   - Suite: VRF-Lite / VRF Utility Commands
   - Summary: VRF-Lite support traceroute operation
   - Steps: From a VRF instance Run traceroute vrf <name> x.x.x.x. From the global VRF Run traceroute x.x.x.x. Expect: Trace route output should show network hops from source VRF to destination network.
   - Justification: Direct high-confidence exact match. Core for VRF-Lite traceroute support.

2. **AWP-10990** — VRF_Lite and Stack Management Vlan
   - Suite: VRF-Lite
   - Summary: To operate VRF lite on a stack and confirm that there is no defect in the way VRF-Lite handles the stack management Vlan.
   - Justification: VRF-Lite with stack management.

3. **AWP-11451** — VRF-Lite - Unicast Traffic
   - Suite: Validation Scenario
   - Summary: Check and verify VRF-Lite for correct status and functionality.
   - Justification: Unicast traffic in VRF-Lite.

4. **AWP-4144** — VRF Lite Telnet command
   - Suite: VRF-Lite
   - Summary: To test Telnet operation to the default vlan To test Telnet opertion to an interface within a VRF.
   - Justification: VRF-Lite utility commands.

**Tangential Cases Reviewed (summary):** 
- Inactive traceroute cases, VRF route to resiliency, DHCP Relay VRF.
- Decision: Focused on VRF-Lite traceroute and related utilities.

## ATPyLib Cases (Step 3)
- 1330: 1330.7001.1 VRF-lite, IPv4_unicast, power_cycle (VRF-lite forwarding resilience).
- 1346: 1346.1013.1 VRF-Lite isolation (traffic cannot cross between VRF instances).
- Limited direct "traceroute vrf" in enriched data; more on VRF isolation and forwarding.

## Gaps Noted
- Specific VRF-Lite traceroute command support (from VRF vs global) from TL primary.
- ART covers VRF-Lite isolation and unicast forwarding resilience, but exact traceroute behavior from TL.
- Zephyr has objective.

## ART Test Cases String
1330.7001.1 (VRF-lite IPv4 unicast power_cycle) + 1346.1013.1 (VRF-Lite isolation) + related VRF suites (1330/1346).

## Synthesis Notes for Objectives
Zephyr objective: VRF-Lite support traceroute operation. Enrich with TL: From VRF instance, traceroute vrf <name> shows correct network hops from source VRF to destination; from global VRF, standard traceroute works. Include distinction.

---
**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.

Following repeatable workflow in OBJECTIVE_DRAFTING_PROCESS.md.
