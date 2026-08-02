# Traceability & Supporting Data for AWPTCM-T33303 ()

## Primary Decision

- **AWP-18509** – 802.1Q tagging on interfaces
  - Decision confidence: med
  - Rationale: 802.1Q tagging on interfaces


## Top Relevant TestLink Cases

**Primary + relevant historical TestLink cases reviewed for artefacts and context**

- **AWP-18509** — 802.1Q Tagging on Ethernet Interfaces
  - Justification: Primary match — core 802.1Q tagging configuration and running-config verification on an interface

- **AWP-17725** — AWP5-VLAN-CFG-004 - Tagged and untagged port
  - Justification: Switching-side tagged/untagged port configuration, the closest analogue to a Switching_VLAN 802.1Q case

- **AWP-18528** — Native vlan operation on an Ethernet port
  - Justification: Native/untagged VLAN behaviour alongside tagged frames — supplies the untagged happy path and the no-matching-VID negative path

- **AWP-18535** — Same 802.1Q VID on two different interfaces
  - Justification: Special condition — same VID configured on two different interfaces, a boundary case for tag assignment

- **AWP-18493** — Packets with 802.1Q tag can traverse bridge
  - Justification: Traffic-level verification that tagged frames actually traverse the DUT, giving the forwarding/pass-fail assertions

- **AWP-9216** — Forwarding on a Port belong to protocol VLAN and Tag VLAN
  - Justification: Forwarding on a port belonging to both protocol VLAN and tag VLAN — tagged-port forwarding precedence on switching hardware

- **AWP-17730** — AWP5-VLAN-CFG-011 - All VLAN tag remove
  - Justification: Removal of all VLAN tagging — teardown/cleanup path and config-removal verification



## Zephyr Cross-References (Step 2)
**Relevant Zephyr Scale cases identified**

These cases were reviewed from the full Zephyr database (via `data/zephyr_full/`) for objective style, step structure, and related behaviour.


1. **[AWPTCM-T742](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T742)** — 802.1Q Tagging on Ethernet Interfaces
   - Folder: 
   - Objective: No
   - Justification: Direct 802.1Q tagging on Ethernet interfaces — same primary TestLink decision (AWP-18509), same folder family

1. **[AWPTCM-T753](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T753)** — Same 802.1Q VID on two different interfaces
   - Folder: 
   - Objective: No
   - Justification: Same 802.1Q VID on two different interfaces (AWP-18535) — sibling case in /802.1Q Interfaces

1. **[AWPTCM-T749](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T749)** — Native vlan operation on an Ethernet port
   - Folder: 
   - Objective: No
   - Justification: Native VLAN operation on an Ethernet port (AWP-18528) — untagged/native side of the same tagging feature

1. **[AWPTCM-T18206](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T18206)** — AWP5-VLAN-CFG-004 - Tagged and untagged port
   - Folder: 
   - Objective: No
   - Justification: Tagged and untagged port (AWP-17725) — confirmed TestLink context, core tagged/untagged membership intent

1. **[AWPTCM-T14665](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T14665)** — Packets with 802.1Q tag can traverse bridge
   - Folder: 
   - Objective: No
   - Justification: Packets with 802.1Q tag can traverse bridge (AWP-18493) — tagged-frame forwarding verification

1. **[AWPTCM-T18285](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T18285)** — Forwarding on a Port belong to protocol VLAN and Tag VLAN
   - Folder: 
   - Objective: No
   - Justification: Forwarding on a port belonging to protocol VLAN and Tag VLAN (AWP-9216) — tagged-VLAN forwarding interaction

1. **[AWPTCM-T40451](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T40451)** — Check VID 0 tagged frames on access ports can be forwarded
   - Folder: 
   - Objective: No
   - Justification: VID 0 tagged frames on access ports — tagged-frame handling edge case on untagged/access interfaces

1. **[AWPTCM-T28820](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T28820)** — S2254.1.51 Ethernet interfaces enslaved to the global bridge are untagged members of VID1 and tagged members of all other VLANs (2..4094)
   - Folder: 
   - Objective: No
   - Justification: Ethernet interfaces untagged in VID1 and tagged in all other VLANs — same tagged/untagged interface membership semantics


## ATPyLib Cases (Step 3)


- `1348.6001.31` — RED: TCM-1 - VLAN 802.1Q Encapsulation (Tagged)

- `2035.6.2` — Each instance of the tagging and detagging functions that supports the EISS (6.7), and implements the optional port-and-protocol-based VLAN classification, shall implement a VID Set, each member of which associates values of a Protocol Group Identifier (6.8.2) with a VID. Each Untagged and Priority-tagged frame received is assigned a vlan_identifier equal to the VID Set value for the receiving Port and the Protocol Group Identifier selected by matching the received frame with a Protocol Template.

- `2034.6.2` — Each instance of the tagging and detagging functions that supports the EISS (6.9), and implements the optional port-and-protocol-based VLAN classification, shall implement a VID Set, each member of which associates values of a Protocol Group Identifier (6.12.2) with a VID. Each Untagged and Priority-tagged frame received is assigned a vlan_identifier equal to the VID Set value for the receiving Port and the Protocol Group Identifier selected by matching the received frame with a Protocol Template.

- `2034.6.1` — Each instance of the tagging and detagging functions that supports the EISS (6.9), and implements the optional port-and-protocol-based VLAN classification, shall implement a VID Set, each member of which associates values of a Protocol Group Identifier (6.12.2) with a VID. Each Untagged and Priority-tagged frame received is assigned a vlan_identifier equal to the VID Set value for the receiving Port and the Protocol Group Identifier selected by matching the received frame with a Protocol Template.

- `2035.18.9` — The entries in the Port Map that specify untagged transmission compose the untagged set for the VLAN


- ART string: 1348.6001.31 + 2035.6.2 + 2034.6.2 + 2034.6.1 + 2035.18.9

## Gaps Noted
The selected ART coverage addresses the core encapsulation and classification mechanics — tagged 802.1Q frame handling on a port, the untagged-set membership that defines untagged transmission, and the protocol-based VID-assignment rules that govern how untagged and priority-tagged frames are classified. What it does not reach is the configuration-and-observability layer the TestLink and Zephyr material centres on: running-config and operational-state confirmation of tagging on an interface, the removal and cleanup path when tagging is withdrawn, and native/untagged VLAN interaction with the no-matching-VID case. Also thin are the boundary conditions — the same VID applied across two different interfaces, VID 0 tagged frames arriving on access ports, and the default global-bridge membership model in which enslaved interfaces are untagged in one VLAN and tagged across the remainder. End-to-end forwarding of tagged frames through the device is only partly represented, and the precedence between protocol-VLAN and tag-VLAN membership on a shared port has no clear automated analogue.

## Tangential Cases Reviewed
(See selections for full list.)

## ART Test Cases String
1348.6001.31 + 2035.6.2 + 2034.6.2 + 2034.6.1 + 2035.18.9

**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.