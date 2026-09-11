# Traceability & Supporting Data for AWPTCM-T47871 (Port - Link Health Monitoring)

## Primary Decision
- **AWP-27508** – SD-WAN - Historic data for probes (SD-WAN)
  - "Link health monitoring (linkmon probe)"
  - Decision confidence: med
  - Rationale: Linkmon probe configuration and historic data

## Top Relevant TestLink Cases
**Primary + Linkmon probe / trigger cases**
- AWP-27508 (primary) — SD-WAN - Historic data for probes
- AWP-28975 (focus) — Create Trigger using Linkmon Probe (DS-Lite project)
  - Covers probe config, trigger binding to bad/good/unreachable states, profiles (latency / consecutive lost probes), activation logging

## ATPyLib Cases (Step 3)
- None identified. No suites contain linkmon or link health monitoring coverage.

## Gaps Noted
- Complete absence of ATPyLib automation for linkmon probe + trigger integration.
- All coverage comes from historical TestLink manual cases (primarily SD-WAN and DS-Lite link monitoring projects).

## Tangential Cases Reviewed
- Other SD-WAN probe and trigger cases (AWP-26585 CLI Probe, AWP-27470/27471 source/interface control, AWP-28835 dynamic config).
- Conclusion: AWP-28975 + AWP-27508 provide the core artefacts for probe creation, state-based triggering, and history. No additional artefacts required.

## ART Test Cases String
None (manual-only feature)