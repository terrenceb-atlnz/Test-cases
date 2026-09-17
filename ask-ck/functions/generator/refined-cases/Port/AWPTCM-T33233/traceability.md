# Traceability & Supporting Data for AWPTCM-T33233 ()

## Primary Decision

- **AWP-23992** – Auto/Auto negotiation; Zephyr says covered by auto-test
  - Decision confidence: low
  - Rationale: Auto/Auto negotiation; Zephyr says covered by auto-test


## Top Relevant TestLink Cases

**Primary + relevant historical TestLink cases reviewed for artefacts and context**

- **AWP-12283** — 1G_Fixed Copper_Cross / 1000 / Auto/ MDI
  - Justification: Step: Set DUT and partner device:
Speed = 1000
Duplex = Auto
Polarity = MDI / Partner device = MDI
ecofriendly lp
Connect cable to each ports lpi configured
Expected: LPI command successfully enbaled.
Confirm ports are in LPI status and configured by executing 'show ecofrienly and show interface port' command.
Check logs for appriate log messages. No error message.

- **AWP-108** — SFP Fibre-1Gig-AUTO 100/Full-Auto
  - Justification: Step: Set DUT & partner device: Speed/Duplex = AUTO 100/Full Set Polarity settings: DUT = Auto Partner = Auto
Note: Auto 100 can be configured in x81-400 / 960. This behavior was added in the Dual Rate pluggable project: https://intranet.atlnz.lc/awpwiki/index.php/Dual_Rate_Pluggable_Support_TFS#Subsequent_Targets
Expected: Command Failure for SFP port Speed setting. Link Up Speed = 1000 Duplex & Polarity as configured
For x81-400 / 960: Commands accepted. Link Up. Speed = 100 Duplex & Polarity as configured

- **AWP-98** — SFP Copper-1Gig-Cross-MDIX/MDI
  - Justification: Step: DUT & partner device: Speed & Duplex = Defaults Set Polarity settings: DUT = MDIX Partner = MDI
Expected: Command successful for SFP port Polarity setting. Link Down. Configured Speed and Configured Duplex set to "Auto" & Configured Polarity settings: DUT = MDIX Partner = MDI

- **AWP-87** — SFP Copper-1Gig-Straight-MDIX/MDI
  - Justification: Step: DUT & partner device: Speed & Duplex = Defaults Set Polarity settings: DUT = MDIX Partner = MDI
Expected: Command successful. Link Up Speed, Duplex set to "Auto"
Command failure for Polarity settings: DUT = MDIX Partner = MDI (refer to CR30879)



## Zephyr Cross-References (Step 2)
**Relevant Zephyr Scale cases identified**

These cases were reviewed from the full Zephyr database (via `data/zephyr_full/`) for objective style, step structure, and related behaviour.


1. **[AWPTCM-T46849](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T46849)** — interface: port status, speed, duplex and negotiation
   - Folder: 
   - Objective: No
   - Justification: Status: Draft | Has objective: False | Num steps: 1

1. **[AWPTCM-T33889](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T33889)** — TQrouter -  Basic function: auto negotiation on ethernet ports
   - Folder: 
   - Objective: No
   - Justification: Objective: Check auto negotiation on both eth ports working as expected.

Status: Draft | Has objective: True | Num steps: 1

1. **[AWPTCM-T32632](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T32632)** — IE220 Device Management - Auto-negotiation #127
   - Folder: 
   - Objective: No
   - Justification: Status: Draft | Has objective: False | Num steps: 1

1. **[AWPTCM-T31152](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T31152)** — Profinet: Hardware; Check of Auto-Negotiation
   - Folder: 
   - Objective: No
   - Justification: Objective: To check the mandatory functionality Auto-Negotiation, the status of the port 3 of device “B” is read. The port 3 of device “B” shall be using 100 MBit/s full duplex mode after negotiation. If at the DUT port Auto-Negotiation is deactivated or it does not support it, the duplex mode at the port of the network component is responding half duplex. Both tested cables shall work well. This test case shall be run with all devices.

Status: Draft | Has objective: True | Num steps: 1


## ATPyLib Cases (Step 3)


- `1360.1001.3` — Configure BFD links between devices and test negotiation is succesful for differing intervals


- ART string: 1360.1001.3

## Gaps Noted
The selected ART coverage (1360.1001.3) exercises negotiation only in the BFD session sense — establishing links between devices and confirming session parameters converge across differing interval settings — so it provides confidence in protocol-level negotiation and link stability, but it is a poor proxy for the physical-layer Auto/Auto behaviour this case targets. Not addressed by automation are copper and fibre PHY auto-negotiation outcomes across speed and duplex combinations (including forced 1000/Auto and Auto 100/Full pairings), MDI/MDIX polarity resolution on straight and crossed cabling for both native copper and SFP-based ports, and mismatch or fallback cases where DUT and partner advertise differing capabilities. Observability of the resulting negotiated state — port status, resolved speed, duplex and polarity as reported by the platform, and link transitions on renegotiation or cable reconnection — is likewise absent, as is any coverage of energy-efficient/LPI interaction with negotiation. The related Zephyr cross-references (AWPTCM-T46849, T33889, T32632, T31152) indicate this behaviour is validated elsewhere on a per-platform basis, but no equivalent automated check exists in the ART suite for this case, leaving the "covered by auto-test" claim weakly supported.

## Tangential Cases Reviewed
(See selections for full list.)

## ART Test Cases String
1360.1001.3

**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.