# Traceability & Supporting Data for AWPTCM-T33302 ()

## Primary Decision

- (No primary decision recorded)


## Top Relevant TestLink Cases

**Primary + relevant historical TestLink cases reviewed for artefacts and context**

- **AWP-6402** — Remove VLAN - Port removed from VLAN. Only FDB entries for that vlan on that port should be flushed
  - Justification: Closest primary match for port VLAN membership: removing a port from a VLAN and verifying only that VLAN/port's FDB entries flush — the core port-to-VLAN binding behaviour

- **AWP-6651** — VLAN Packet Counter instance on one port -  untagged member of the vlan
  - Justification: Happy path for an untagged port member of a VLAN with traffic ingress verification — supplies the untagged-membership + traffic-forwarding assertions

- **AWP-27191** — VLAN
  - Justification: Negative/boundary path for VLAN identity: vlan 0 rejected, vlan 1 default, valid 1-4094 range — gives the VLAN ID validation steps

- **AWP-23330** — Add IPv6 vlan classifier  to a port
  - Justification: Per-port VLAN assignment via classifier group applied to an interface — shows the interface-level VLAN attach/detach command shape (ignore the IPv6 proto specifics)

- **AWP-14859** — IP Subnet VLAN and Broadcast
  - Justification: Subnet-based VLAN and broadcast containment — contrast case that establishes the broadcast-domain isolation expected of a port VLAN

- **AWP-13704** — Able to configure a shutdown VLAN
  - Justification: Special condition: VLAN in shutdown state, for verifying port members follow VLAN admin state

- **AWP-6663** — Configure VLAN statistics counter on a port then change the port to a mirrored port
  - Justification: Special condition: changing a VLAN member port's role (to mirrored) after configuration, covering reconfiguration-while-in-VLAN reporting



## Zephyr Cross-References (Step 2)
**Relevant Zephyr Scale cases identified**

These cases were reviewed from the full Zephyr database (via `data/zephyr_full/`) for objective style, step structure, and related behaviour.


1. **[AWPTCM-T18076](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T18076)** — Deleting and creating port based VLAN
   - Folder: 
   - Objective: No
   - Justification: Deleting and creating port based VLAN — direct port-VLAN lifecycle coverage in /VLAN/_General, closest match to the case intent

1. **[AWPTCM-T18055](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T18055)** — Command Line Handler - switchport access vlan
   - Folder: 
   - Objective: No
   - Justification: switchport access vlan CLI handling — the exact command surface for assigning a port to a port VLAN

1. **[AWPTCM-T9352](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T9352)** — Remove VLAN - Port removed from VLAN. Only FDB entries for that vlan on that port should be flushed
   - Folder: 
   - Objective: No
   - Justification: Matches confirmed TestLink AWP-6402 (port removed from VLAN, per-vlan/per-port FDB flush)

1. **[AWPTCM-T18166](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T18166)** — VLAN Packet Counter instance on one port -  untagged member of the vlan
   - Folder: 
   - Objective: No
   - Justification: Matches confirmed TestLink AWP-6651 (VLAN packet counter on an untagged member port)

1. **[AWPTCM-T8354](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T8354)** — Able to configure a shutdown VLAN
   - Folder: 
   - Objective: No
   - Justification: Matches confirmed TestLink AWP-13704 (shutdown VLAN); switching-domain copy, unlike the IPv6-folder duplicate

1. **[AWPTCM-T18208](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T18208)** — AWP5-VLAN-CFG-006 - VLAN deletion
   - Folder: 
   - Objective: No
   - Justification: VLAN deletion configuration case — same create/delete/membership verification style

1. **[AWPTCM-T18288](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T18288)** — Subnet VLAN dynamic reconfiguration
   - Folder: 
   - Objective: No
   - Justification: Related VLAN-classification coverage aligning with TestLink AWP-14859 (IP subnet VLAN) and dynamic membership reconfiguration


## ATPyLib Cases (Step 3)


- `2034.16.1` — Static filtering information is added to, modified, and removed from the FDB only under explicit management control.. It shall not be automatically removed by any ageing mechanism.


- ART string: 2034.16.1

## Gaps Noted
The selected ART coverage (2034.16.1) exercises only the static-FDB lifecycle — that statically configured filtering entries are added, modified and removed solely under explicit management control and are exempt from ageing — so it substantiates the deterministic, management-driven half of the forwarding-database behaviour underlying a port VLAN. It does not reach the port-to-VLAN membership semantics that are the substance of this case: selective flushing scoped to just the affected VLAN/port pair when a port leaves a VLAN (AWP-6402, AWPTCM-T9352), untagged-member forwarding with per-port per-VLAN traffic accounting (AWP-6651, AWPTCM-T18166), and broadcast-domain containment as the observable outcome of membership (AWP-14859). Also unautomated are the identity and command-surface boundaries — rejection of an invalid VLAN identifier, the reserved default, and the valid range (AWP-27191, AWPTCM-T18055) — along with the interface-level attach/detach shape drawn from AWP-23330 and the create/delete cycle in AWPTCM-T18076 / AWPTCM-T18208. The state-dependent and reconfiguration-under-load conditions are entirely outside automation: member-port behaviour while the VLAN is administratively shut down (AWP-13704, AWPTCM-T8354), role change of a counted member port to a mirroring role (AWP-6663), and dynamic reconfiguration of an already-populated VLAN (AWPTCM-T18288). Observability is the weakest dimension overall, since the ART item asserts nothing about per-VLAN counter instances or the scope of FDB flush events, both of which currently depend on manual inspection.

## Tangential Cases Reviewed
(See selections for full list.)

## ART Test Cases String
2034.16.1

**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.