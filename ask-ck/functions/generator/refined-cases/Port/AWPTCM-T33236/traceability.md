# Traceability & Supporting Data for AWPTCM-T33236 ()

## Primary Decision

- **AWP-22510** – Half/Full duplex configuration
  - Decision confidence: med
  - Rationale: Half/Full duplex configuration


## Top Relevant TestLink Cases

**Primary + relevant historical TestLink cases reviewed for artefacts and context**

- **AWP-83** — Fixed Copper-1Gig-Cross-10/Half-MDI to MDI
  - Justification: Step: Set DUT & partner device:
Speed: 10
Duplex: HALF
Polarity: DUT = MDI, Partner = MDI
Expected: Link Up Speed, Duplex & Polarity as configured
NOTE: Half-Duplex not supported on x930

- **AWP-57** — Fixed Copper-1Gig-Straight- 10/Half-MDI to MDI
  - Justification: Step: Set DUT & partner device:
Speed: 10
Duplex: HALF
Polarity: DUT = MDI, Partner = MDI
Expected: Link is Down. Speed, duplex and polarity set as configured.

- **AWP-75** — Fixed Copper-1Gig-Cross-100/Half-MDI to MDI
  - Justification: Step: Set DUT & partner device:
Speed: 100
Duplex: HALF
Polarity: DUT = MDI, Partner = MDI
Expected: Link Up Speed, Duplex & Polarity as configured



## Zephyr Cross-References (Step 2)
**Relevant Zephyr Scale cases identified**

These cases were reviewed from the full Zephyr database (via `data/zephyr_full/`) for objective style, step structure, and related behaviour.


1. **[AWPTCM-T13202](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T13202)** — Fixed Copper-1Gig-Straight-1000/Half-MDIX to MDIX
   - Folder: 
   - Objective: No
   - Justification: Objective: Fixed Copper - 1Gig & Straight Through Cable - Speed/Duplex = AUTO 1000/Half & MDIX both ends DUT Port Type: Fixed Copper - 1 Gig Partner Port Type: Any Copper - 1 Gig Cable Type: Straight Through Steps:
1. DUT and partner device ports connected with correct cable and powered up.
2. Run through each test case by varying the configuration of both devices as specified. NOTE: configure ports in following order; SPEED, DUPLEX then POLARITY.
3. For each setting check the link status is as expected using command "sho int port......" on both devices.

Status: Approved | Has objective: True | Num steps: 1 | Labels: Operational

Steps:
1. Set DUT & partner device:
Speed: 1000
Duplex: Half
Polarity: DUT = MDIX, Partner = MDIX

1. **[AWPTCM-T13243](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T13243)** — Fixed Copper-1Gig-Cross- 1000/Half-MDIX to MDIX
   - Folder: 
   - Objective: No
   - Justification: Objective: Fixed Copper - 1Gig & Cross Over Cable - Speed/Duplex = AUTO 1000/Half & MDIX both ends DUT Port Type: Fixed Copper - 1 Gig Partner Port Type: Any Copper - 1 Gig Cable Type: Cross Over Steps:
1. DUT and partner device ports connected with correct cable and powered up.
2. Run through each test case by varying the configuration of both devices as specified. NOTE: configure ports in following order; SPEED, DUPLEX then POLARITY.
3. For each setting check the link status is as expected using command "sho int port......" on both devices.

Status: Approved | Has objective: True | Num steps: 1 | Labels: Operational

Steps:
1. Set DUT & partner device:
Speed: 1000
Duplex: Half
Polarity: DUT = MDIX, Partner = MDIX


## ATPyLib Cases (Step 3)


- `1342.301.13` — Command Execution: Polarity Bundle polarity mdi polarity auto shutdown polarity mdi polarity auto


- ART string: 1342.301.13

## Gaps Noted
The selected ART coverage (1342.301.13) exercises polarity-related command execution — MDI and auto polarity settings applied and re-applied across a shutdown boundary — so it reasonably addresses CLI acceptance, configuration persistence, and basic polarity state handling on a fixed copper interface. It does not, however, drive the half-duplex dimension that defines this case: the manual TestLink and Zephyr artefacts pair explicit speed and duplex forcing (10/Half, 100/Half, 1000/Half) with fixed MDI-to-MDI and MDIX-to-MDIX polarity combinations on both DUT and partner, which the automation neither configures nor observes. Consequently the negative-link expectation seen in the straight-cable 10/Half MDI-to-MDI scenario, and the corresponding link-up-with-matching-speed/duplex/polarity outcomes on the crossover variants, remain unautomated, as does any confirmation that the negotiated operational state on the link partner agrees with the forced local configuration. Cabling topology (straight versus crossover) and the presence of a correctly configured partner device are likewise outside the automated harness, leaving duplex-mismatch and polarity-mismatch interactions to manual execution.

## Tangential Cases Reviewed
(See selections for full list.)

## ART Test Cases String
1342.301.13

**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.