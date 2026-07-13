# Traceability & Supporting Data for AWPTCM-T33249 (IPv4_ARP - ARP Logging)

## Primary Decision
- **AWP-4397** – ARP Log: Functionality (ARP Function)
  - "ARP Log: Functionality"
  - Decision confidence: med
  - Rationale: ARP Logging correctly

## Top Relevant TestLink Cases
**ARP Log family**
- AWP-4397 (primary) — ARP Log: Functionality
- AWP-4396 — ARP Log: Command

## ATPyLib Cases (Step 3)
- No direct coverage of the "arp log" CLI command or ARP event logging behavior was found in the enriched ATPyLib suites.
- Related ARP table and neighbour operations are exercised in suite 1351 (gratuitous_arp) and various cases in 1331 / 1346, but these do not verify log output or the logging configuration itself.

## Gaps Noted
- The dedicated ARP logging feature (enable/disable, mac-address-format, and logging of create/age/static/move events) has no direct automated coverage in the reviewed suites.
- All detailed behavioural expectations come from the historical TestLink cases.

## Tangential Cases Reviewed
- None (omitted per review).

## ART Test Cases String
No direct ART coverage for ARP logging. General ARP table behaviour covered by 1351 + 1331 suites.
