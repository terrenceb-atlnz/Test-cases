# Traceability & Supporting Data for AWPTCM-T43868 ()

## Primary Decision

- **AWP-1232** – Exact: SNMPv1-Access
  - Decision confidence: high
  - Rationale: Exact: SNMPv1-Access


## Top Relevant TestLink Cases

**Primary + relevant historical TestLink cases reviewed for artefacts and context**

- **AWP-1232** — SNMPv1-Access
  - Justification: Exact primary match — SNMPv1 access via SNMP Manager, DUT SNMPv1 configuration and MIB load/compile; the happy path this manual case is restating

- **AWP-1233** — SNMPv1-Access-VCS
  - Justification: Same SNMPv1 access path under VCS/stacking — supplies the special-condition variant of the primary case without re-deriving steps

- **AWP-1234** — SNMPv2c-Access
  - Justification: SNMPv2c sibling of the primary; its step structure is the template for version-parameterised access tests and marks the v1/v2c boundary

- **AWP-17672** — SNMP - Sanity check all versions can walk get and set
  - Justification: Sanity check that all versions can walk, get and set — gives the concrete SNMP operation set (walk/get/set) the v1 access case must exercise, not just connect

- **AWP-15157** — CR00039432 - SNMP: error reading /etc/snmpd.conf authcomunity IP address when using access list
  - Justification: Negative/defect path: snmp-server community restricted by an access-list, including the /etc/snmpd.conf address-parsing failure — the main v1 community authorisation failure mode

- **AWP-27923** — V-3969:Network devices must only allow SNMP read-only access.
  - Justification: Read-only-access hardening requirement explicitly scoped to SNMPv1 — the permission/write-access negative path for v1 communities

- **AWP-4988** — SNMP -  Number of configured (v1 & v2c) community names and (v3) users.
  - Justification: Recommended maximum v1/v2c community names — boundary/limit conditions for the v1 community configuration under test

- **AWP-3824** — SNMP Manager Connection
  - Justification: SNMP Manager connection setup (interface addressing, host subnet reachability) — the prerequisite topology and reachability steps the v1 access case depends on



## Zephyr Cross-References (Step 2)
**Relevant Zephyr Scale cases identified**

These cases were reviewed from the full Zephyr database (via `data/zephyr_full/`) for objective style, step structure, and related behaviour.


1. **[AWPTCM-T15880](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T15880)** — SNMPv1-Access
   - Folder: 
   - Objective: No
   - Justification: Zephyr mirror of the primary TestLink match AWP-1232 SNMPv1-Access — same v1 community access intent and step style

1. **[AWPTCM-T15881](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T15881)** — SNMPv1-Access-VCS
   - Folder: 
   - Objective: No
   - Justification: SNMPv1-Access-VCS: identical v1 access coverage in the VCS/stacked variant (AWP-1233)

1. **[AWPTCM-T15882](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T15882)** — SNMPv2c-Access
   - Folder: 
   - Objective: No
   - Justification: SNMPv2c-Access (AWP-1234): sibling version case in the same /SNMP/SNMP Protocol suite, same community/get-set structure

1. **[AWPTCM-T15883](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T15883)** — SNMPv2c-Access-VCS
   - Folder: 
   - Objective: No
   - Justification: SNMPv2c-Access-VCS: completes the v1/v2c x standalone/VCS matrix this case belongs to

1. **[AWPTCM-T6118](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T6118)** — SNMP - Sanity check all versions can walk get and set
   - Folder: 
   - Objective: No
   - Justification: SNMP sanity check all versions can walk/get/set (AWP-17672): direct v1 walk/get/set verification overlap

1. **[AWPTCM-T15903](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T15903)** — CR00039432 - SNMP: error reading /etc/snmpd.conf authcomunity IP address when using access list
   - Folder: 
   - Objective: No
   - Justification: CR00039432 authcommunity access-list defect (AWP-15157): v1 community + access-list handling, same protocol folder

1. **[AWPTCM-T29214](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T29214)** — snmp-server community: access list
   - Folder: 
   - Objective: No
   - Justification: snmp-server community: access list — same v1 community configuration commands under test

1. **[AWPTCM-T15884](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T15884)** — SNMPv3-Access-No Authentication or Privacy
   - Folder: 
   - Objective: No
   - Justification: SNMPv3-Access-No Authentication or Privacy: same-suite access case, useful for cross-version step/style consistency


## ATPyLib Cases (Step 3)


- `1348.6001.24` — RED: ACM-1, ACM-2, AUM-1, AUM-2, AUM-3, AUM-6, CCK-1, SCM-2 - Configured SNMP user can SNMP-walk and access/alter running config

- `1348.6001.28` — RED: ACM-1, ACM-2, AUM-1, AUM-2, AUM-3, SCM-2 - Unconfigured SNMP user cannot SNMP-walk or access/alter config

- `1348.6001.27` — RED: ACM-1, ACM-2, AUM-1, AUM-2, AUM-3 - SNMP user with incorrect password cannot SNMP-walk or access/alter config

- `5701.1001.1` — SNMP MIB - System

- `5701.1001.8` — SNMP MIB - snmp

- `5701.1012.1` — SNMP MIB - SNMPv2

- `5701.1014.1` — SNMP MIB - SNMPv3


- ART string: 1348.6001.24 + 1348.6001.28 + 1348.6001.27 + 5701.1001.1 + 5701.1001.8 + 5701.1012.1 + 5701.1014.1

## Gaps Noted
The selected ART coverage exercises the SNMP user/community authorisation decision reasonably well — a configured principal being able to walk and read/alter running config, an unconfigured one being refused, and an incorrect credential being refused — plus MIB availability across the system, snmp, SNMPv2 and SNMPv3 groups, which stands in for MIB load and compile health. What it does not cover is version-specific behaviour at the v1 boundary: the automation is written around the generic user/credential model rather than an SNMPv1 community explicitly distinguished from v2c, so the v1-vs-v2c distinction and the VCS/stacking variant of the same access path are untested. Also uncovered are the community authorisation restrictions themselves — access-list-scoped communities, including the config-file address-parsing defect path — read-only enforcement as a hardening constraint rather than an incidental credential failure, and the configured-community-count limit as a boundary condition. Finally, the SNMP Manager prerequisite (interface addressing and reachability to the manager subnet) is assumed rather than asserted, and there is no observability of the manager-side view or of the diagnostics emitted when community authorisation fails, so a partial or misparsed community configuration could pass while behaving incorrectly in the field.

## Tangential Cases Reviewed
(See selections for full list.)

## ART Test Cases String
1348.6001.24 + 1348.6001.28 + 1348.6001.27 + 5701.1001.1 + 5701.1001.8 + 5701.1012.1 + 5701.1014.1

**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.