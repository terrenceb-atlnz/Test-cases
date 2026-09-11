# Traceability & Supporting Data for AWPTCM-T33304 ()

## Primary Decision

- (No primary decision recorded)


## Top Relevant TestLink Cases

**Primary + relevant historical TestLink cases reviewed for artefacts and context**

- **AWP-4800** — CR30675 : Private-vlan - Sanity test of functionality of private vlan
  - Justification: Primary sanity/functional coverage of private VLAN with the full CLI config sequence (vlan database, private-vlan primary/secondary, port assignment) — the baseline happy path for the artefact

- **AWP-9206** — Combination Test - Private VLAN and Port-based VLAN
  - Justification: Direct 'Multiple VLAN' combination test: private VLAN alongside port-based VLAN, with concrete primary/secondary VLAN creation and 1.0.1-1.0.4 port assignment matching this case's shape

- **AWP-9207** — Combination Test - Private VLAN and Tagged-based VLAN
  - Justification: Same combination family for tagged/trunk membership — supplies the multiple-VLAN-per-port tagging steps a private-VLAN trunk artefact needs

- **AWP-4757** — Private-vlan - Be able to create max number of private vlans
  - Justification: Scale/limit path for the 'multiple' aspect — creating the maximum number of private VLANs, plus the no-config reboot and console setup preamble

- **AWP-4689** — Private-vlan CLI - show vlan private & show vlan private trunk
  - Justification: Reporting/verification commands: show vlan private and show vlan private trunk, including isolated vs community and trunk-port variants

- **AWP-4690** — Private-vlan Secondary ports have native vlan of none
  - Justification: Special-condition/negative path: secondary ports must have native vlan of none, catching a defect class the happy path misses

- **AWP-4767** — Private-vlan - configure native vlan on trunked private vlan
  - Justification: Native VLAN on a trunked private VLAN — configuration variant plus the technique of suppressing extra packets to avoid misleading results

- **AWP-9210** — Private VLAN with DHCP
  - Justification: Traffic-isolation validation of multiple private VLANs via DHCP reachability (only PC1 should get an address), giving a concrete pass/fail assertion rather than a prose expectation



## Zephyr Cross-References (Step 2)
**Relevant Zephyr Scale cases identified**

These cases were reviewed from the full Zephyr database (via `data/zephyr_full/`) for objective style, step structure, and related behaviour.


1. **[AWPTCM-T18145](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T18145)** — CR30675 : Private-vlan - Sanity test of functionality of private vlan
   - Folder: 
   - Objective: No
   - Justification: Exact Zephyr mirror of confirmed TestLink AWP-4800 (CR30675 private-VLAN sanity) — core functionality baseline for this case

1. **[AWPTCM-T18304](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T18304)** — Combination Test - Private VLAN and Port-based VLAN
   - Folder: 
   - Objective: No
   - Justification: Exact mirror of confirmed AWP-9206; private VLAN combined with port-based VLAN is the 'multiple VLAN' intent of this case

1. **[AWPTCM-T18305](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T18305)** — Combination Test - Private VLAN and Tagged-based VLAN
   - Folder: 
   - Objective: No
   - Justification: Exact mirror of confirmed AWP-9207; private VLAN combined with tagged-based VLAN, same multi-VLAN coexistence intent

1. **[AWPTCM-T18135](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T18135)** — Private-vlan - Be able to create max number of private vlans
   - Folder: 
   - Objective: No
   - Justification: Exact mirror of confirmed AWP-4757; creating the max number of private VLANs is the multiple-private-VLAN scale case

1. **[AWPTCM-T18132](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T18132)** — Private-vlan CLI - show vlan private & show vlan private trunk
   - Folder: 
   - Objective: No
   - Justification: Exact mirror of confirmed AWP-4689; show vlan private / show vlan private trunk supplies the verification CLI and output format

1. **[AWPTCM-T18133](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T18133)** — Private-vlan Secondary ports have native vlan of none
   - Folder: 
   - Objective: No
   - Justification: Exact mirror of confirmed AWP-4690; secondary-port native-VLAN-none behaviour constrains multi-VLAN private configs

1. **[AWPTCM-T18143](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T18143)** — Private-vlan - configure native vlan on trunked private vlan
   - Folder: 
   - Objective: No
   - Justification: Exact mirror of confirmed AWP-4767; native VLAN on a trunked private VLAN — multiple VLANs sharing one private-VLAN trunk

1. **[AWPTCM-T18306](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T18306)** — Combination Test - Private VLAN and IP subnet-based VLAN
   - Folder: 
   - Objective: No
   - Justification: Completes the private-VLAN combination series (IP subnet-based VLAN) alongside T18304/T18305, same coexistence style and folder


## ATPyLib Cases (Step 3)


- `1331.1001.30675` — Private VLAN does not work on 534, related to CR30322.

- `1341.2001.5003` — max supported private VLANs

- `1331.1001.42563` — Node which belong to secondary port of Private VLAN can communicate other VLAN when each ARP information are registered.

- `1331.1001.27095` — x600 is crashed by private vlan setting on aggregation port


- ART string: 1331.1001.30675 + 1341.2001.5003 + 1331.1001.42563 + 1331.1001.27095

## Gaps Noted
Private VLAN isolation and scale have real automated coverage in ART: the sanity/functional path is exercised, the maximum-number-of-private-VLANs limit is covered, and there are defect-derived cases around secondary-port reachability into other VLANs and platform instability when private VLAN is applied to an aggregated port. What automation does not reach is the "multiple VLAN" intent that drives this case — the coexistence of private VLAN with port-based, tagged/trunk, and IP-subnet-based VLAN membership on the same ports, and the trunked private-VLAN variants including native-VLAN handling on trunk ports. The special-condition requirement that secondary ports carry a native VLAN of none is likewise unautomated, as is the observability layer: the private-VLAN and private-VLAN-trunk reporting output that distinguishes isolated from community VLANs and shows trunk-port membership. The ART scale case confirms a count limit but not the per-port combination and tagging semantics, and the reachability cases assert connectivity outcomes without the traffic-shaping technique of suppressing extraneous packets that the manual artefacts rely on to keep results unambiguous. Net effect: automation guards the base feature and known regressions, while combination behaviour, trunk/native-VLAN configuration variants, and CLI-visible state remain manual.

## Tangential Cases Reviewed
(See selections for full list.)

## ART Test Cases String
1331.1001.30675 + 1341.2001.5003 + 1331.1001.42563 + 1331.1001.27095

**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.