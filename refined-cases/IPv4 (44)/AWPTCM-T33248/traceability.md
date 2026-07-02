# Traceability & Supporting Data for AWPTCM-T33248 (IPv4_ARP - Static ARP)

## Primary Decision
- **AWP-4341** – Static ARP: Command (Command Handler Test)
  - "Static ARP: Command"
  - Decision confidence: high
  - Rationale: Static ARP command behaviour, not replaced by dynamic, remove/re-add behaviour

## Top Relevant TestLink Cases
**Core + Static ARP suite**
- AWP-4341 (primary) — Static ARP: Command
- AWP-4336 — Static ARP: CLI Test
- AWP-4337 — Static ARP: CLI Help
- AWP-4342 — Static ARP: Over Restart and Failover
- AWP-4343 — Static ARP: On Hotswap
- AWP-4348 — Static ARP: Not Replaced by Dynamic ARP
- AWP-22934 — Static ARP - with gratuitous ARP and flushing (CR53378)
- AWP-24474 — Not rewrite Static ARP l2ifindex by GARP
- AWP-4351 — Static ARP and Static MAC Interoperability
- AWP-13586 — Overwrite static arp with a different port

## ATPyLib Cases (Step 3)
- 1351 suite covers related ARP table behaviour

## Gaps Noted
- None significant. Full Static ARP suite provides comprehensive coverage.

## Tangential Cases Reviewed
- VRF, NLB, and PBR-related static ARP cases.
- Conclusion: Core command + persistence + GARP/MAC interoperability cases provide complete coverage.

## ART Test Cases String
1351 (ARP table behaviour) + primary TestLink AWP-4341 and Static ARP suite cases