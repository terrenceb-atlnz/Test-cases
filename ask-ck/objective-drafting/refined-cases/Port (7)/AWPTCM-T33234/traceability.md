# Traceability & Supporting Data for AWPTCM-T33234 (Port - Auto MDI/MDI-X)

## Primary Decision
- **AWP-12285** – `Auto_Fixed Copper_Straight / Auto / Full / MDI-MDIX` (Green Features (Ecofriendly) / EEE)
  - "Verify LPI works with Auto/ Full / MDI-MDIX settings"
  - Decision confidence: med
  - Rationale: Auto/Full/MDI-MDIX negotiation

## Top Relevant TestLink Cases
**Primary + High-ranking EEE/LPI + polarity cases**
- AWP-12285 (primary)
- AWP-12283
- AWP-12286
- AWP-12282
- AWP-12292

**Core historical Port Speed, Duplex and Polarity matrix tests**
- AWP-104 – SFP Fibre-1Gig-MDIX/MDI
- AWP-112 – SFP Fibre-100M-MDIX/MDI
- AWP-35 – Fixed Copper-1Gig-Straight-MDIX/MDI
- AWP-38 – Fixed Copper-1Gig-Straight-MDI/MDIX

## Zephyr Cross-References (Step 3)
**Relevant Zephyr Scale cases identified**

These cases were reviewed from the full Zephyr database (via `data/zephyr_full/`) for objective style, step structure, and related behaviour.

1. **[AWPTCM-T33233](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T33233)** — Port - Auto Negotiation
   - Folder: /New Platform Test (MASTER)/New Platform Template/Port
   - Objective: Yes (7 declarative bullets covering defaults, pluggable insert, link partner interop, reporting, LPI)
   - Steps: 7
   - Justification: Direct sibling in the same Port area. Shares the same family of concerns (no pluggable default, hot-swap, reporting, LPI). Used for consistency of artefact language and step ordering.

2. **[AWPTCM-T24](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T24)** — VRF: Check operation/performance of 1008 PIM-SM interfaces across 63 VRF's
   - Folder: /PIM-SM/PIM-SMv4/2111 1024 PIM Interfaces
   - Objective: Yes ("Per VRF: 1 Upstream interface 15 downstream interfaces")
   - Steps: 6
   - Justification: Strong exemplar of structured per-group objective bullets and systematic verification of commands + isolation behaviour. Useful pattern when documenting reporting and configuration effects.

## ATPyLib Cases (Step 4)
- `1342.301.13` – Command Execution: Polarity Bundle (mdi / auto). Analysed=True, Result=PASS.

## Gaps Noted
- Limited behavioural link-up testing with explicit MDI/MDIX in ATPyLib (mostly CLI/command execution).
- "No pluggable" defaults, straight/cross success with forced MDI/MDIX, and reporting are primarily covered by TestLink cases.
- LPI + polarity interaction has only partial automated coverage.

## Tangential Cases Reviewed
- "No Pluggins" series (AWP-2348, AWP-2349, AWP-2355, AWP-2356, etc.)
- "Defaults-*-Polarity auto" cases
- Conclusion: Adequately covered by existing artefacts (no new bullets needed).

## ART Test Cases String
1342.301.13 + relevant link-up cases from 1346_swi_misc
