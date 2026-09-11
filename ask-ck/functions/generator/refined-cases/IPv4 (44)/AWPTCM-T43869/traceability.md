# Traceability & Supporting Data for AWPTCM-T43869 ()

## Primary Decision

- **AWP-1234** – Exact: SNMPv2c-Access
  - Decision confidence: high
  - Rationale: Exact: SNMPv2c-Access


## Top Relevant TestLink Cases

**Primary + relevant historical TestLink cases reviewed for artefacts and context**

- **AWP-1234** — SNMPv2c-Access
  - Justification: Exact primary match — SNMPv2c access to DUT via SNMP manager over IPv4; supplies the canonical setup/verify step text

- **AWP-20411** — snmp-server SNMPv2c
  - Justification: Base `snmp-server` enable command coverage for SNMPv2c — the prerequisite config step

- **AWP-20412** — snmp-server CommunityName SNMPv2c
  - Justification: Community-name parameter coverage; community string is the SNMPv2c credential the access test depends on

- **AWP-20413** — snmp-server RO/RW SNMPv2c
  - Justification: RO/RW access-mode variants — the two happy paths (get vs set) the access case must exercise

- **AWP-20414** — snmp-server view SNMPv2c
  - Justification: `snmp-server view` coverage — OID-subtree restriction, i.e. the in-scope/out-of-scope negative path for a permitted community

- **AWP-20415** — snmp-server LISTNUM SNMPv2c
  - Justification: LISTNUM (access-list) binding on the community — source-address restriction happy/negative path over IPv4

- **AWP-22457** — RFC3418(SNMPv2-MIB) Traps - authenticationFailure Trap - v2c IPv4
  - Justification: authenticationFailure trap, v2c over IPv4 — reporting/notification behaviour when access is attempted with a bad community

- **AWP-15157** — CR00039432 - SNMP: error reading /etc/snmpd.conf authcomunity IP address when using access list
  - Justification: Known defect condition: authcommunity/access-list interaction in snmpd.conf — special condition to assert while combining community + access list



## Zephyr Cross-References (Step 2)
**Relevant Zephyr Scale cases identified**

These cases were reviewed from the full Zephyr database (via `data/zephyr_full/`) for objective style, step structure, and related behaviour.


1. **[AWPTCM-T15882](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T15882)** — SNMPv2c-Access
   - Folder: 
   - Objective: No
   - Justification: Exact title match to the primary TestLink decision AWP-1234 (SNMPv2c-Access) — same intent and feature

1. **[AWPTCM-T20876](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T20876)** — snmp-server SNMPv2c
   - Folder: 
   - Objective: No
   - Justification: Exact counterpart of confirmed AWP-20411 'snmp-server SNMPv2c' — core SNMPv2c server enable coverage over IPv4

1. **[AWPTCM-T20877](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T20877)** — snmp-server CommunityName SNMPv2c
   - Folder: 
   - Objective: No
   - Justification: Exact counterpart of confirmed AWP-20412 'snmp-server CommunityName SNMPv2c' — community-name access under IPv4

1. **[AWPTCM-T20878](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T20878)** — snmp-server RO/RW SNMPv2c
   - Folder: 
   - Objective: No
   - Justification: Exact counterpart of confirmed AWP-20413 'snmp-server RO/RW SNMPv2c' — read-only/read-write community access

1. **[AWPTCM-T20879](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T20879)** — snmp-server view SNMPv2c
   - Folder: 
   - Objective: No
   - Justification: Exact counterpart of confirmed AWP-20414 'snmp-server view SNMPv2c' — MIB view scoping of v2c access

1. **[AWPTCM-T20880](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T20880)** — snmp-server LISTNUM SNMPv2c
   - Folder: 
   - Objective: No
   - Justification: Exact counterpart of confirmed AWP-20415 'snmp-server LISTNUM SNMPv2c' — access-list-restricted v2c access

1. **[AWPTCM-T15883](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T15883)** — SNMPv2c-Access-VCS
   - Folder: 
   - Objective: No
   - Justification: VCS variant of the same SNMPv2c-Access case — same steps and verification style on a stacked topology

1. **[AWPTCM-T29214](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T29214)** — snmp-server community: access list
   - Folder: 
   - Objective: No
   - Justification: Covers 'snmp-server community: access list', the same community+ACL interaction as confirmed defect case AWP-15157


## ATPyLib Cases (Step 3)


- `1348.6001.24` — RED: ACM-1, ACM-2, AUM-1, AUM-2, AUM-3, AUM-6, CCK-1, SCM-2 - Configured SNMP user can SNMP-walk and access/alter running config

- `1348.6001.27` — RED: ACM-1, ACM-2, AUM-1, AUM-2, AUM-3 - SNMP user with incorrect password cannot SNMP-walk or access/alter config

- `1348.6001.28` — RED: ACM-1, ACM-2, AUM-1, AUM-2, AUM-3, SCM-2 - Unconfigured SNMP user cannot SNMP-walk or access/alter config

- `1336.108.3` — Software IP ACL, SNMP

- `5701.1012.1` — SNMP MIB - SNMPv2

- `5701.1001.8` — SNMP MIB - snmp

- `1331.2001.41668` — CR41668 - Significant reduction in SNMP MIBS returned by SNMP WALK.

- `2029.99.2` — channelMatches ACCESS feature testing for read-only counter object


- ART string: 1348.6001.24 + 1348.6001.27 + 1348.6001.28 + 1336.108.3 + 5701.1012.1 + 5701.1001.8 + 1331.2001.41668 + 2029.99.2

## Gaps Noted
The selected ART coverage addresses the core community-credentialled access paths over IPv4 — read and write access for a correctly configured community, plus rejection of an incorrect community string and of an entirely unconfigured one — alongside SNMPv2-MIB and snmp MIB object retrieval, a MIB-walk completeness regression, read-only object enforcement, and generic software IP ACL interaction with SNMP. The notification side is not covered: authenticationFailure trap emission as the reported consequence of a rejected access attempt has no automated counterpart, so denial is only ever observable as an absent response rather than as an emitted event. OID-subtree scoping through snmp-server view (permitted community, in-scope versus out-of-scope objects) and access-list binding on the community itself are similarly absent as first-class conditions — the ACL coverage present is generic software-ACL behaviour, not the community-to-LISTNUM association and its source-address restriction. The known authcommunity/access-list interaction in the rendered snmpd.conf falls outside all selected automation because it requires inspecting generated configuration state rather than protocol responses, as do the stacked/VCS variant of the access case and the enable/disable transition of the base snmp-server function.

## Tangential Cases Reviewed
(See selections for full list.)

## ART Test Cases String
1348.6001.24 + 1348.6001.27 + 1348.6001.28 + 1336.108.3 + 5701.1012.1 + 5701.1001.8 + 1331.2001.41668 + 2029.99.2

**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.