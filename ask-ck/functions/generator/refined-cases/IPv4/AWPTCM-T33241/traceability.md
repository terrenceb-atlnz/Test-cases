# Traceability & Supporting Data for AWPTCM-T33241 ()

## Primary Decision

- **AWP-4660** – IP local loopback address
  - Decision confidence: med
  - Rationale: IP local loopback address


## Top Relevant TestLink Cases

**Primary + relevant historical TestLink cases reviewed for artefacts and context**

- **AWP-10240** — Loopback
  - Justification: Step: loopback (zero length cable) ena test cable po=x sh test cable po=x
Expected: confirm loopback discovered.



## Zephyr Cross-References (Step 2)
**Relevant Zephyr Scale cases identified**

These cases were reviewed from the full Zephyr database (via `data/zephyr_full/`) for objective style, step structure, and related behaviour.


1. **[AWPTCM-T31014](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T31014)** — The RX loopback will attempt to send a loopback packet every 10 seconds
   - Folder: 
   - Objective: No
   - Justification: Status: Approved | Has objective: False | Num steps: 0

1. **[AWPTCM-T31016](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T31016)** — The RX loopback will check the TX packet counter to see if a loopback packet was successfully transmitted every 10 seconds
   - Folder: 
   - Objective: No
   - Justification: Status: Approved | Has objective: False | Num steps: 0

1. **[AWPTCM-T31019](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T31019)** — The RX loopback will consider it a RX fail if loopback packets were transmitted AND NO packets have been received in 6 checks
   - Folder: 
   - Objective: No
   - Justification: Status: Approved | Has objective: False | Num steps: 0


## ATPyLib Cases (Step 3)



## Gaps Noted
No ATPyLib (ART) automated tests were selected for AWPTCM-T33241, so there is currently no automated coverage of the IP local loopback address behaviour (AWP-4660) or of the related loopback behaviours. The manual intent from TestLink AWP-10240, which uses a zero-length cable loopback test to confirm the loopback is discovered, and the Zephyr timing and fail-detection behaviours remain entirely manual. These include:

- AWPTCM-T31014: loopback packet transmission every 10 seconds
- AWPTCM-T31016: TX packet counter checks every 10 seconds to confirm successful transmission
- AWPTCM-T31019: RX fail declared when packets were transmitted but none received across 6 consecutive checks

Edge cases and observability are also uncovered, such as:

- timing accuracy and jitter of the 10-second interval
- counter behaviour when transmission fails
- recovery after an RX fail
- the exact threshold boundary at the 6th check
- how discovery and failure states are surfaced to the operator

Automation should be added to cover these before the case can be considered traceable to ART.

## Tangential Cases Reviewed
(See selections for full list.)

## ART Test Cases String


**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.