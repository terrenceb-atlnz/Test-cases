# Traceability & Supporting Data for AWPTCM-T44333 ()

## Primary Decision

- **AWP-29525** – OpenFlow conn interruption non-rule-expired
  - Decision confidence: med
  - Rationale: OpenFlow conn interruption non-rule-expired


## Top Relevant TestLink Cases

(No TestLink selections)


## Zephyr Cross-References (Step 2)
**Relevant Zephyr Scale cases identified**

These cases were reviewed from the full Zephyr database (via `data/zephyr_full/`) for objective style, step structure, and related behaviour.



## ATPyLib Cases (Step 3)



## Gaps Noted
No ART automated tests were selected as related coverage for AWPTCM-T44333, so automation does not currently address the OpenFlow connection-interruption behaviour tied to AWP-29525 (mapped with medium confidence). No confirmed TestLink artefacts or Zephyr cross-references are available either, so this gap cannot be offset or clarified by historical intent. The main uncovered behaviours are controller connection loss and recovery where flow entries are not removed by rule expiry (idle/hard timeout), including whether those entries persist through the interruption. Also uncovered are fail-mode handling during the outage, re-synchronisation of flow state after reconnection, and observability of connection-state transitions and flow-table consistency. Edge cases such as repeated or prolonged interruptions, and interruptions that coincide with flow modifications, also lack automated validation and remain dependent on manual execution.

## Tangential Cases Reviewed
(See selections for full list.)

## ART Test Cases String


**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.