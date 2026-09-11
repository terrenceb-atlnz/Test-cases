# Traceability & Supporting Data for AWPTCM-T43817 (Port - Cable Diagnostics)

## Primary Decision
- **AWP-17987** – VCT Basic Feature Test (Virtual Cable Tester)
  - "VCT cable diagnostics"
  - Decision confidence: med
  - Rationale: Core VCT commands, link behavior during test, results display, clear, and combo-port support

## Top Relevant TestLink Cases
**Primary + Virtual Cable Tester suite cases**
- AWP-17987 (primary) — VCT Basic Feature Test
- AWP-18180 — VCT 5.4.5 Release Test
- AWP-17988 — VCT Unsupported Testing
- AWP-18010 — VCT Stack Support
- AWP-18011 — VCT Length Testing
- AWP-18012 — VCT Status Testing
- AWP-26881 — VCT on PoE Ports connecting to a PoE capable device
- AWP-26882 — VCT on PoE ports connected to another switch

## ATPyLib Cases (Step 3)
- None identified. No suites contain cable-diagnostics, VCT, or TDR coverage.

## Gaps Noted
- Complete absence of ATPyLib automation for VCT / cable-diagnostics TDR testing.
- All coverage comes from historical TestLink manual cases.

## Tangential Cases Reviewed
- AWP-24026 (Interop:VCT on combo port)
- Older "Cable Test - diagnostic" cases (AWP-10239 No Cable, AWP-10241 Disable Test, AWP-10242 Reset) and generic cable-related cases.
- Conclusion: The Virtual Cable Tester suite + combo interop case provide complete coverage. No additional artefacts required from tangential cases.

## ART Test Cases String
None (manual-only feature)