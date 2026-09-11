# Traceability & Supporting Data for AWPTCM-T33235 (Port - Fixed port Speed)

## Primary Decision
- **AWP-25122** – `Fixed Copper-1Gig-Straight- 1000/Full-Polarity auto` (Port Speed, Duplex and Polarity / 1G_Copper_Fixed)
  - "Fixed Fixed - 1Gig & Straight Cable - Speed/Duplex = 1000/Full & Polarity auto"
  - Decision confidence: low
  - Rationale: Fixed 1G copper fixed-speed

## Top Relevant TestLink Cases
**Primary + sibling fixed-speed matrix cases (Port Speed, Duplex and Polarity suite)**
- AWP-25122 (primary, 1000/Full)
- AWP-25123 (Fixed Copper-1Gig-Straight- Auto/Full-Polarity auto)
- AWP-12294 (Fixed Copper_Unsupported Speed)

**Related fixed-speed / port config cases**
- AWP-35, AWP-38 (earlier Fixed Copper MDI/MDIX matrix)
- AWP-104, AWP-112 (SFP fibre fixed speed variants)

## ATPyLib Cases (Step 3)
- `1346.*` – Confirm link comes up at speed 10/100/1000 (and higher speeds where supported). Verifies link-up + packet forwarding at exact configured fixed rates across duplex modes.
- `1342.*` – Command Execution: Speed Bundle (fixed speed 100/auto, shutdown interleaving). Command execution and config restoration verification.
- `1370.*` – Ansible playbook configuration of fixed speed=1000 / full duplex + port up confirmation.

## Gaps Noted
- Primary TestLink case focuses narrowly on 1000/Full straight cable; broader speed matrix and unsupported speeds are covered by siblings.
- ATPyLib provides strong coverage for positive link-up at fixed rates but no direct coverage for unsupported speed failure modes or hot-insert while fixed.
- Show command / status reporting accuracy is only implicit in the link-up cases.

## Tangential Cases Reviewed
- "Unsupported speed" (AWP-12294) and LPI/ecofriendly fixed-speed interactions.
- Hot-swap cases (XEM/LIF level).
- "No pluggable" / default configuration cases from the Port matrix.
- Conclusion: Existing primary + siblings + 1346 link-up cases adequately cover the core artefacts; no new bullets required.

## ART Test Cases String
1346 (fixed-speed link-up) + 1342 (speed command bundle) + 1370 (Ansible fixed config)