# Traceability & Supporting Data for AWPTCM-T33247 (IPv4_ARP - Clear ARP)

## Primary Decision
- **AWP-4339** – ARP Commands: Clear ARP (Command Handler Test)
  - "ARP Commands: Clear ARP"
  - Decision confidence: high
  - Rationale: clear arp-cache removes Dynamic ARP entries (Static unaffected); affects HW and SW tables

## Top Relevant TestLink Cases
**Primary + ARP command family**
- AWP-4339 (primary) — ARP Commands: Clear ARP
- AWP-4338 — Show ARP: Command
- AWP-4340 — ARP Aging Timeout: Command
- AWP-4337 — Static ARP: CLI Help
- AWP-4341 — Static ARP: Command

## ATPyLib Cases (Step 3)
- 1351 suite covers related ARP table and neighbour table behaviour (already reviewed in T33243)

## Gaps Noted
- None significant. Primary case provides clear command behaviour for both software and hardware tables.

## Tangential Cases Reviewed
- Static ARP interoperability cases (AWP-4342, AWP-4343, AWP-4348).
- Conclusion: Primary case + related command cases provide complete coverage.

## ART Test Cases String
1351 (ARP table behaviour) + primary TestLink AWP-4339