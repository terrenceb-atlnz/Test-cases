# Traceability & Supporting Data for AWPTCM-T44296 ()

## Primary Decision

- **AWP-5512** – show lldp (neighbor info)
  - Decision confidence: med
  - Rationale: show lldp (neighbor info)


## Top Relevant TestLink Cases

**Primary + relevant historical TestLink cases reviewed for artefacts and context**

- **AWP-5512** — Command Line Handler: show lldp
  - Justification: Primary match: the 'show lldp' / 'show lldp interface' command handler case named by the decision — current and default LLDP settings

- **AWP-5518** — Command Line Handler: sh lldp neighbors interface
  - Justification: Neighbor-information display path ('show lldp neighbors' and per-interface variant) that the case's 'neighbor info' wording points at

- **AWP-5517** — Command Line Handler: show lldp neighbors detail interface
  - Justification: Detailed neighbor output ('show lldp neighbors detail [interface]') — the per-TLV verification depth for the same reporting surface

- **AWP-5515** — Command Line Handler: show lldp interface
  - Justification: Interface-scoped 'show lldp interface' config/settings display; supplies the if-range argument coverage for the primary command

- **AWP-5513** — Command Line Handler: show lldp statistics
  - Justification: 'show lldp statistics' counters — the companion reporting command whose output format and global/per-port split mirror the primary case

- **AWP-5506** — Command Line Handler: lldp run
  - Justification: 'lldp run' enable/disable — the precondition step and the negative path where show output must reflect LLDP disabled

- **AWP-5500** — Command Line Handler: clear lldp table
  - Justification: 'clear lldp table' — negative/empty-table path: after clearing, neighbor info must be gone from the show output

- **AWP-5547** — Enabled LLDP on a port to receive only
  - Justification: Receive-only port with a real neighbor connected, verified via 'sh lldp neighbor' and 'sh lldp statistics' — happy-path setup that actually populates the neighbor info



## Zephyr Cross-References (Step 2)
**Relevant Zephyr Scale cases identified**

These cases were reviewed from the full Zephyr database (via `data/zephyr_full/`) for objective style, step structure, and related behaviour.


1. **[AWPTCM-T9724](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T9724)** — Command Line Handler: show lldp
   - Folder: 
   - Objective: No
   - Justification: Direct external counterpart of the primary decision AWP-5512 'show lldp' — same command, same Command Line Handler style

1. **[AWPTCM-T9729](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T9729)** — Command Line Handler: show lldp neighbors detail interface
   - Folder: 
   - Objective: No
   - Justification: Counterpart of confirmed AWP-5517 'show lldp neighbors detail interface' — neighbor-info display, same folder/style

1. **[AWPTCM-T9730](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T9730)** — Command Line Handler: sh lldp neighbors interface
   - Folder: 
   - Objective: No
   - Justification: Counterpart of confirmed AWP-5518 'sh lldp neighbors interface' — per-interface neighbor info

1. **[AWPTCM-T9727](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T9727)** — Command Line Handler: show lldp interface
   - Folder: 
   - Objective: No
   - Justification: Counterpart of confirmed AWP-5515 'show lldp interface' — sibling show-command coverage

1. **[AWPTCM-T9725](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T9725)** — Command Line Handler: show lldp statistics
   - Folder: 
   - Objective: No
   - Justification: Counterpart of confirmed AWP-5513 'show lldp statistics' — sibling show-command coverage

1. **[AWPTCM-T9718](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T9718)** — Command Line Handler: lldp run
   - Folder: 
   - Objective: No
   - Justification: Counterpart of confirmed AWP-5506 'lldp run' — the enable step any show-lldp neighbor test depends on

1. **[AWPTCM-T47624](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T47624)** — CLI: show lldp neighbors detail
   - Folder: 
   - Objective: No
   - Justification: Modern (5.5.6-0) 'CLI: show lldp neighbors detail' — same neighbor-info intent with current-release output expectations

1. **[AWPTCM-T47623](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T47623)** — CLI: show lldp local-info
   - Folder: 
   - Objective: No
   - Justification: Modern 'CLI: show lldp local-info' — paired show-output verification alongside neighbor info


## ATPyLib Cases (Step 3)


- `1332.1001.8` — Check that the information contained in the LLDP frames are consistent with the CLI

- `1341.1001.6835` — This test checks the maximum number LLDP neighbours that can be supported on the switch

- `1332.1001.7` — This test checks the maximum number neighbours that can be supported on the switch

- `1331.2001.27875` — CR27875 - LLDP - SNMP Protocol Ids (Annex F) are not aligned with local info on the switch

- `1331.1001.26525` — LLDP - The system capabilities TLV does not advertise the correct information

- `2015.5.1` — 1) statsAgeoutsTotal: A count of the times that a neighbor's information is deleted from the LLDP remote systems MIB because of rxInfoTTL timer expiration (10.5.2).

- `2016.5.1` — 1) statsAgeoutsTotal: A count of the times that a neighbor's information is deleted from the LLDP remote systems MIB because of rxInfoTTL timer expiration (10.5.2).

- `6000.1002.1` — Use LLDP to discover links between all switches in the setup


- ART string: 1332.1001.8 + 1341.1001.6835 + 1332.1001.7 + 1331.2001.27875 + 1331.1001.26525 + 2015.5.1 + 2016.5.1 + 6000.1002.1

## Gaps Noted
The selected ART coverage is protocol- and MIB-centred: it exercises agreement between transmitted LLDP frame contents and the switch's own local information, TLV correctness for system capabilities and for Annex F protocol identifiers, maximum-neighbour scaling limits, remote-systems ageout accounting on rxInfoTTL expiry, and neighbour discovery across a multi-device setup — so the underlying data that the reporting commands draw on is reasonably well guarded. What automation does not reach is the command-line handler surface itself: the composition and layout of the show lldp, show lldp interface, show lldp neighbors, show lldp neighbors detail, show lldp local-info and show lldp statistics displays, the global-versus-per-port split of the counter output, and the presentation of default settings on an otherwise unconfigured system. Argument handling for the interface-scoped forms is likewise unaddressed — port ranges, single-port scoping, and malformed or out-of-range arguments together with the resulting error reporting. The negative and transitional states are the widest gap: LLDP administratively disabled, and the emptied neighbour table following a table clear, where the expected observation is the absence of neighbour information rather than a counter value the automated suite already samples; the receive-only port mode's effect on what the reporting commands present sits in the same category. Statistics other than the ageout counter, and the human-readable per-TLV depth of the detailed neighbour output, therefore remain manual observations.

## Tangential Cases Reviewed
(See selections for full list.)

## ART Test Cases String
1332.1001.8 + 1341.1001.6835 + 1332.1001.7 + 1331.2001.27875 + 1331.1001.26525 + 2015.5.1 + 2016.5.1 + 6000.1002.1

**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.