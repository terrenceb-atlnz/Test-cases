# Traceability & Supporting Data for AWPTCM-T33236 (Port - Fixed Full or half Duplex)

## Primary Decision
- **AWP-22510** – `CR-53726 - Half/Full Duplex configuration on ETH/VLAN ports with LED` (Port Speed, Duplex and Polarity)
  - "Confirm that changing the duplex configuration of an ETH or switchport would not cause the port LED to be OFF."
  - Decision confidence: med
  - Rationale: Half/Full duplex configuration

## Top Relevant TestLink Cases
**Primary + half-duplex matrix cases (Port Speed, Duplex and Polarity suite)**
- AWP-22510 (primary, LED behavior on duplex config change)
- AWP-26792 (Fixed Copper -2.5G/5G - 10Mb/Half-Duplex)
- AWP-26793 (Fixed Copper -2.5G/5G - 100Mb/Half-Duplex)
- AWP-83, AWP-57, AWP-75, AWP-82, AWP-49 (various Fixed Copper 1Gig 10/Half and 100/Half with MDI/MDIX variants)

**Related duplex / port config cases**
- Other entries in the same suite covering full/half combinations and polarity.

## ATPyLib Cases (Step 3)
- `1346.*` – Confirm link comes up at speed 10/100/1000/... across duplex modes (half + full). Verifies link-up behavior for fixed duplex settings.
- `1342.*` – Command Execution: Duplex Bundle (half duplex, full duplex, auto, shutdown interleaving).
- `1370.*` – Ansible playbook configuration of switchport as full duplex + speed + port up confirmation.

## Gaps Noted
- Primary TestLink case specifically validates LED state is unaffected by duplex changes.
- ATPyLib provides solid coverage for link establishment under fixed duplex but limited explicit coverage of LED observability or duplex mismatch error reporting.
- Show command accuracy for duplex reporting is implicit in the link-up and config cases.

## Tangential Cases Reviewed
- Speed/duplex matrix cases from the same suite.
- "No pluggable" defaults and hot-swap behavior from related Port cases.
- Conclusion: Primary + half-duplex siblings + 1346/1342/1370 cases cover the core artefacts; LED-specific requirement adds one distinct bullet.

## ART Test Cases String
1346 (fixed speed + duplex link-up) + 1342 (duplex command bundle) + 1370 (Ansible duplex config)