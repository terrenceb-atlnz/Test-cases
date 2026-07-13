# Traceability & Supporting Data for AWPTCM-T33274 (Switching_EPSR - EPSR Mib)

## Primary Decision
- **AWP-3991** – EPSR Mib Support (EPSR - SNMP / EPSR, EPSR+, EPSR++)
  - "EPSR Mib Support"
  - Decision confidence: high
  - Rationale: EPSR Mib Support

## Top Relevant TestLink Cases
**EPSR MIB / SNMP family**
- AWP-3991 (primary) — EPSR Mib Support
- AWP-1498 — AT-EPSRv2-MIB - Functional
- AWP-10347 — EPSR-SLP MIBs & Notifications
- AWP-4009 — SNMP - EPSR Transit Node Trap
- AWP-4010 — SNMP - EPSR Master Node Trap
- AWP-1310 — AT-EPSRv2-MIB TRAPS/NOTIFICATIONS - all epsr
- AWP-25021 — atEpsrv2VariablesTable
- AWP-1494–1497 (AT-EPSRv2-MIB Walk, NEXT, BULK, GET for SNMP compliance)

## ATPyLib Cases (Step 3)
- 5704.1006.1 – SNMP MIB - AT-EPSRv2 - MIB (unanalysed; no execution history)
- 1334.1001.1 – Trap and send hello packets, confirm EPSR status is complete (general EPSR trap behavior)

## Gaps Noted
- Primary TestLink case (AWP-3991) is minimal ("atr-MIB supported"). Detailed expectations for variables, tables, and trap bindings come from the broader EPSR MIB/SNMP family.
- ART has a stub for AT-EPSRv2 MIB (5704) but it has not been analysed or executed.
- MIB-specific verification (OID consistency, exact trap bindings, SLP flags) has limited or no direct automated coverage; relies on historical TestLink.

## Tangential Cases Reviewed
- Broader keyword search across ~375 EPSR-related TestLink cases (ring operation, recovery, interop with LAG/STP/IPv6, etc.) was performed.
- Conclusion: These cases exercise EPSR functional behaviour but do not introduce new artefacts specific to MIB support, variable tables, or SNMP trap content. No expansion of scope needed for this MIB-focused manual case.

## ART Test Cases String
5704 (AT-EPSRv2 MIB) + 1334 (EPSR trap/functional) + primary TestLink EPSR MIB family cases
