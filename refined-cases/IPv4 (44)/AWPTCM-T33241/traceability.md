# Traceability & Supporting Data for AWPTCM-T33241 (IP Local Loopback Address)

## Primary Decision
- **AWP-4660** – `VCS - IP Local Loopback Address is preserved after Stack Failover` (IPv4)
  - "IP Local Loopback Address is preserved and remain working correctly after Stack Failover (Master and Slave)."
  - Decision confidence: med
  - Rationale: IP local loopback address

## Top Relevant + Tangential TestLink Cases
**Primary + loopback-related cases**
- AWP-4660 (primary) — VCS - IP Local Loopback Address preserved after Stack Failover
- AWP-22594 — Log host source on loopback Interface
- SNMP Manager using Loopback as agent IP address
- Advertise loopback subnets via RIP / OSPF
- IPv6 loopback as BGP update source
- Limits on primary IP addresses for loopback interface
- Log host source selection (VLAN / loopback / eth0)

**Gap noted during review**
Basic loopback interface lifecycle cases (create, assign IP, enable/disable, delete, multiple interfaces, local processing) are under-represented in the current candidates. The list is heavily skewed toward loopback as a source address for other features.

## ATPyLib Cases (Step 3)
- `2024.19.12` / `2024.19.13` — Interface state description tests (Loopback state reporting)

## Gaps Noted
- No direct ATPyLib coverage for loopback interface creation, IP assignment, or preservation after failover.
- Existing coverage is limited to interface state reporting.

## Tangential Cases Reviewed
- All loopback-related cases from IPv4, Logging, SNMP, and Routing suites (already captured above).
- Conclusion: Primary failover case + source-address use cases provide the main coverage. Basic loopback lifecycle artefacts were added from first-principles analysis to ensure completeness.

## ART Test Cases String
2024 (interface state description)