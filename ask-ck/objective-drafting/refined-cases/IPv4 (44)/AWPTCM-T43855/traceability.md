# Traceability & Supporting Data for AWPTCM-T43855 (IPv4_UnicastRouting - IPv4 Static)

## Primary Decision
- From `data/decisions/dec_05.json`: AWPTCM-T43855 {"m": "AWP-24184", "c": "high", "w": "IPv4 static routes supported (obj match)"}
- Zephyr title: "(31) IPv4_UnicastRouting - IPv4 Static"
- Folder: /New Platform Test (MASTER)/New Platform Template/IPv4
- Current Zephyr state: objective "Check IPv4 static routes will be supported", thin steps.

## Top Relevant TestLink Cases
Primary + closely related cases for IPv4 static routes support from ATMF / Functions support by ATMF containers and Validation Scenario.

1. **AWP-24184** (Primary) — Check IPv4 static routes will be supported
   - Suite: ATMF / Functions support by ATMF containers
   - Summary: Check IPv4 static routes will be supported
   - Steps: Check IPv4 static routes will be supported => confirm IPv4 static routes are supported
   - Justification: Direct high-confidence exact match. Core for IPv4 static routes support.

2. **AWP-7681** — IPv4 Static Routes - Unicast Traffic
   - Suite: Validation Scenario
   - Summary: Check and verify IPv4 Static Routes for correct status and functionality.
   - Justification: Unicast traffic with static routes.

3. **AWP-25826** — ECMP routing with interface name will be supported for IPv4
   - Suite: IPv4
   - Summary: ECMP routing with interface name for IPv4.
   - Justification: Related static/ECMP IPv4.

4. **AWP-20439** — Field Issue IPv4 Multicast Routes
   - Suite: Validation Scenario
   - Summary: Field issue for Static IPv4 multicast routes.
   - Justification: Related static routes (multicast).

**Tangential Cases Reviewed (summary):** 
- IPv6 static (AWP-24185), Ping (AWP-24173), SSH (AWP-24175/24176).
- Decision: Focused on IPv4 static routes support and traffic.

## ATPyLib Cases (Step 3)
- 1330: 1330.4001.1 IPv4 static routes, power_cycle; 1330.4001.7 IPv4 static routes, rolling_reboot.
- Other routing in 1335/1355/ etc. for IPv4 static routes convergence, ECMP.
- Limited direct "check supported" but functional static routes in validation/platform tests.

## Gaps Noted
- Specific support for IPv4 static routes (config and functionality) from TL primary (ATMF context).
- ART covers static routes in failover/reboot scenarios, but basic support and show from TL.
- Zephyr thin (objective present but steps empty).

## ART Test Cases String
1330.4001.1/7 (static routes power_cycle/rolling_reboot) + related routing suites (1335, 1355 for IPv4 static/ECMP).

## Synthesis Notes for Objectives
Zephyr objective: Check IPv4 static routes will be supported. Enrich with TL: IPv4 static routes are supported, configurable, visible in show, and forward unicast traffic correctly. Include basic config, verification, traffic.

---
**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.

Following repeatable workflow in OBJECTIVE_DRAFTING_PROCESS.md.
