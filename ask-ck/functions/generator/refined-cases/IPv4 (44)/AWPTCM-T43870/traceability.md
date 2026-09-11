# Traceability & Supporting Data for AWPTCM-T43870 ()

## Primary Decision

- **AWP-1237** – SNMPv3 access
  - Decision confidence: med
  - Rationale: SNMPv3 access


## Top Relevant TestLink Cases

**Primary + relevant historical TestLink cases reviewed for artefacts and context**

- **AWP-1237** — SNMPv3-Access-Authentication only
  - Justification: Primary match: SNMPv3 access with authentication only — the decision's named case

- **AWP-1236** — SNMPv3-Access-No Authentication or Privacy
  - Justification: Sibling security level (noAuthNoPriv) — the baseline/negative path for the same access flow

- **AWP-1238** — SNMPv3-Access-Authentication and Privacy
  - Justification: Sibling security level (authPriv) — completes the SNMPv3 access matrix with privacy

- **AWP-20419** — snmp-server auth sha SNMPv3
  - Justification: IPv4 CLI coverage for snmp-server auth sha — the exact commands behind authNoPriv

- **AWP-20423** — snmp-server auth sha priv aes SNMPv3
  - Justification: IPv4 CLI coverage for snmp-server auth sha priv aes — auth+priv command variant

- **AWP-20424** — snmp-server view SNMPv3
  - Justification: IPv4 snmp-server view CLI — view/access scoping needed to make SNMPv3 user access meaningful

- **AWP-20434** — RFC3411-3415 (SNMPv3-MIB) - Functional
  - Justification: RFC3411-3415 SNMPv3-MIB functional case with full config steps (IP interface, snmp-server, user) — best source of real setup/verify sequence

- **AWP-6675** — Configure SNMPv3 with a view policy to allow standard user to see all object except AT-VLAN-MIB
  - Justification: Special condition: SNMPv3 user with a view policy restricting OIDs — negative/permission-boundary verification



## Zephyr Cross-References (Step 2)
**Relevant Zephyr Scale cases identified**

These cases were reviewed from the full Zephyr database (via `data/zephyr_full/`) for objective style, step structure, and related behaviour.


1. **[AWPTCM-T15885](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T15885)** — SNMPv3-Access-Authentication only
   - Folder: 
   - Objective: No
   - Justification: Direct Zephyr counterpart of the primary decision AWP-1237 — SNMPv3 access with authentication only

1. **[AWPTCM-T15884](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T15884)** — SNMPv3-Access-No Authentication or Privacy
   - Folder: 
   - Objective: No
   - Justification: Sibling SNMPv3 access level (noAuthNoPriv) from confirmed AWP-1236; same suite, same style

1. **[AWPTCM-T15886](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T15886)** — SNMPv3-Access-Authentication and Privacy
   - Folder: 
   - Objective: No
   - Justification: Sibling SNMPv3 access level (authPriv) from confirmed AWP-1238; completes the three-level access matrix

1. **[AWPTCM-T20884](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T20884)** — snmp-server auth sha SNMPv3
   - Folder: 
   - Objective: No
   - Justification: Zephyr counterpart of confirmed AWP-20419 — snmp-server auth sha SNMPv3 configuration/verification

1. **[AWPTCM-T20888](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T20888)** — snmp-server auth sha priv aes SNMPv3
   - Folder: 
   - Objective: No
   - Justification: Zephyr counterpart of confirmed AWP-20423 — snmp-server auth sha priv aes SNMPv3

1. **[AWPTCM-T20889](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T20889)** — snmp-server view SNMPv3
   - Folder: 
   - Objective: No
   - Justification: Zephyr counterpart of confirmed AWP-20424 — snmp-server view with SNMPv3, the view-policy angle also seen in AWP-6675

1. **[AWPTCM-T15888](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T15888)** — VCS-SNMPv3-Access-Authentication only
   - Folder: 
   - Objective: No
   - Justification: VCS variant of the same authentication-only access test; useful for step wording and expected-output style


## ATPyLib Cases (Step 3)


- `5701.1014.1` — SNMP MIB - SNMPv3

- `1348.6001.24` — RED: ACM-1, ACM-2, AUM-1, AUM-2, AUM-3, AUM-6, CCK-1, SCM-2 - Configured SNMP user can SNMP-walk and access/alter running config

- `1348.6001.27` — RED: ACM-1, ACM-2, AUM-1, AUM-2, AUM-3 - SNMP user with incorrect password cannot SNMP-walk or access/alter config

- `1348.6001.28` — RED: ACM-1, ACM-2, AUM-1, AUM-2, AUM-3, SCM-2 - Unconfigured SNMP user cannot SNMP-walk or access/alter config

- `1348.6001.25` — RED: AUM-4 - Privilege level 15 user can change SNMP user passwords and privileges

- `1348.6001.26` — RED: AUM-4 - Privilege level 1 user cannot change SNMP user passwords and privileges

- `1348.2001.20` — Check that only SNMPv3 is allowed in secure-mode

- `1348.2001.2` — Check that only SNMPv3 is allowed in secure-mode


- ART string: 5701.1014.1 + 1348.6001.24 + 1348.6001.27 + 1348.6001.28 + 1348.6001.25 + 1348.6001.26 + 1348.2001.20 + 1348.2001.2

## Gaps Noted
The selected ART coverage addresses the core SNMPv3 access contract at protocol level: a configured user can walk the MIB and reach running configuration, an incorrect-credential or unconfigured user is refused, privilege level governs who may alter SNMP user credentials, and secure-mode admits only SNMPv3. It does not separate the three security levels into independently asserted outcomes, so the authentication-only level named by this case is exercised only implicitly alongside noAuthNoPriv and authPriv, and there is no automated distinction between an authentication algorithm and a privacy algorithm being in force — the sha and sha-plus-aes command variants carried by AWP-20419 and AWP-20423 have no direct counterpart in the ART set. View-based access control is the largest gap: neither the snmp-server view scoping of AWP-20424 nor the restricted-view condition of AWP-6675, where a user is expected to reach all objects except one named MIB subtree, is represented, leaving OID-level permission boundaries and their negative outcomes unautomated; stacked/VCS access as tracked by AWPTCM-T15888 is similarly absent. Observability is thin — the automated tests report reachability outcomes rather than the configuration-state rendering of user, group and view definitions, or the failure reporting (rejected-authentication indications, logging and notification of denied access) that the RFC3411-3415 functional material and the manual cases depend on.

## Tangential Cases Reviewed
(See selections for full list.)

## ART Test Cases String
5701.1014.1 + 1348.6001.24 + 1348.6001.27 + 1348.6001.28 + 1348.6001.25 + 1348.6001.26 + 1348.2001.20 + 1348.2001.2

**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.