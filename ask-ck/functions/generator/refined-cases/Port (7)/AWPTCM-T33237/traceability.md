# Traceability & Supporting Data for AWPTCM-T33237 (Port - Active Fiber Monitoring)

## Primary Decision
- **AWP-21596** – `Disable fiber-monitoring` (Active Fiber Monitoring)
  - "Verify that fiber-monitoring can be disabled"
  - Decision confidence: med
  - Rationale: Active fiber-monitoring core test

## Top Relevant TestLink Cases
**Primary + core cases (Active Fiber Monitoring suite)**
- AWP-21596 (primary) — Disable fiber-monitoring
- AWP-21547 — Fiber monitoring is turned off by default
- AWP-21881 — Fiber Monitoring - Configured on a provisioned port
- AWP-21631 — Fiber Monitoring: Debug Command
- AWP-21855 — Fiber Monitoring - Non-AT hardware
- AWP-21853 — Show tech support includes Show fiber-mon command
- AWP-21632 — Fiber Monitoring: Debug messages
- AWP-21854 — Log messages for unsupported hardware
- AWP-21851 — Set sensitivity by DB
- AWP-21549 — Configurable period for moving average

## ATPyLib Cases (Step 3)
- `5704.1013.1` — SNMP MIB - AT-PLUGGABLE-DIAGNOSTICS-MIB
- `6100.1002.*` — Collect data on all pluggables using management/switch port

## Gaps Noted
- No direct ATPyLib coverage for the fiber-monitoring CLI feature itself (enable/disable, sensitivity, moving average, threshold logging, unsupported module handling).
- Existing ATPyLib cases are only tangentially related to general pluggable diagnostics.

## Tangential Cases Reviewed
- All additional cases from the same suite (already captured in the relevant list).
- Related pluggable/DDM behavior and unsupported module handling (covered within the suite cases).
- Conclusion: Primary + relevant suite siblings provide complete coverage for the core behaviour.

## ART Test Cases String
5704 (pluggable diagnostics MIB) + 6100 (pluggable data collection)