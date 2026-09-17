# Traceability & Supporting Data for AWPTCM-T33234 ()

## Primary Decision

- **AWP-12285** – Auto/Full/MDI-MDIX negotiation
  - Decision confidence: med
  - Rationale: Auto/Full/MDI-MDIX negotiation


## Top Relevant TestLink Cases

**Primary + relevant historical TestLink cases reviewed for artefacts and context**

- **AWP-12285** — Auto_Fixed Copper_Straight / Auto / Full / MDI-MDIX
  - Justification: Step: Set DUT and partner device:
Speed = Auto
Duplex = Full
Polarity = MDI / Partner device = MDIX
ecofriendly lpi
Connect cable to each ports lpi configured
Expected: LPI command successfully enbaled.
Confirm ports are in LPI status and configured by executing 'show ecofrienly and show interface port' command.
Check logs for appriate log messages. No error message.

- **AWP-104** — SFP Fibre-1Gig-MDIX/MDI
  - Justification: Step: DUT & partner device: Speed & Duplex = Defaults Set Polarity settings: DUT = MDIX Partner = MDI
Expected: Command Failure for SFP port Polarity setting. Link Up Speed, Duplex & Polarity set to "Auto"



## Zephyr Cross-References (Step 2)
**Relevant Zephyr Scale cases identified**

These cases were reviewed from the full Zephyr database (via `data/zephyr_full/`) for objective style, step structure, and related behaviour.


1. **[AWPTCM-T13268](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T13268)** — SFP Copper-1Gig-Straight-MDIX/MDI
   - Folder: 
   - Objective: No
   - Justification: Objective: Version2: AW+ 5.4.1 onwards
SFP Copper - 1Gig & Straight Through Cable - Speed/Duplex = Auto & MDIX/MDI mix DUT Port Type: SFP Copper - 1 Gig Partner Port Type: Any Copper - 1 Gig Cable Type: Straight Through Steps:
1. DUT and partner device ports connected with correct cable and powered up.
2. Run through each test case by varying the configuration of both devices as specified. NOTE: configure ports in following order; SPEED, DUPLEX then POLARITY.
3. For each setting check the link status is as expected using command "sho int port......" on both devices.

Precondition: Device must have SFP slot
Note: Not Supported on AR2050V

Status: Approved | Has objective: True | Num steps: 1 | Labels: Operational

Steps:
1. DUT & partner device: Speed & Duplex = Defaults Set Polarity settings: DUT = MDIX Partner = MDI


## ATPyLib Cases (Step 3)


- `1342.301.13` — Command Execution: Polarity Bundle polarity mdi polarity auto shutdown polarity mdi polarity auto

- `1342.301.14` — Command Execution: Duplex Bundle duplex half duplex auto shutdown duplex half duplex auto


- ART string: 1342.301.13 + 1342.301.14

## Gaps Noted
The selected ART coverage (1342.301.13 and 1342.301.14) exercises the command-execution surface for polarity and duplex settings, including the mdi/auto and half/auto bundles across shutdown transitions, so CLI acceptance, persistence of configured values, and basic interface-state handling for these attributes are reasonably addressed. What remains uncovered is the negotiated outcome itself: the manual case (AWP-12285) depends on a live link between a DUT configured for Auto speed, Full duplex and MDI polarity and a partner set to MDIX, with EEE/low-power-idle enabled on both ends, and the automation does not establish or observe that paired-endpoint result — link establishment, resolved speed/duplex/polarity after negotiation, and cable-type (straight) sensitivity are all outside its scope. Media-specific behaviour is likewise absent, notably the expected rejection of polarity configuration on SFP ports and the fibre/copper SFP variants implied by AWP-104 and AWPTCM-T13268. Observability of the negotiated and EEE-active state on both devices, rather than the configuration command alone, is the principal gap, so the manual case retains value for cross-device interoperability and media-dependent error handling.

## Tangential Cases Reviewed
(See selections for full list.)

## ART Test Cases String
1342.301.13 + 1342.301.14

**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.