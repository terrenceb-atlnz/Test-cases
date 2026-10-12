# Traceability & Supporting Data for AWPTCM-T33242 ()

## Primary Decision

- **AWP-9996** – ICMP echo reply (ICMP suite)
  - Decision confidence: med
  - Rationale: ICMP echo reply (ICMP suite)


## Top Relevant TestLink Cases

**Primary + relevant historical TestLink cases reviewed for artefacts and context**

- **AWP-9996** — The IP source address in an ICMP Echo Reply
  - Justification: Step: 1.1 Configure VLAN1 IP address on DUT (192.168.1.1)
1.2. Ping DUT ip address (192.168.1.1)
Expected: ICMP echo request must be the same with ICMP echo reply.

- **AWP-21047** — ATMF VM : The IP source address in an ICMP Echo Reply
  - Justification: Step: 1.1 Configure VLAN1 IP address on DUT (192.168.1.1)
1.2. Ping DUT ip address (192.168.1.1)
Test with IPv4 and IPv6 address
Expected: ICMP echo request must be the same with ICMP echo reply.



## Zephyr Cross-References (Step 2)
**Relevant Zephyr Scale cases identified**

These cases were reviewed from the full Zephyr database (via `data/zephyr_full/`) for objective style, step structure, and related behaviour.


1. **[AWPTCM-T2068](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T2068)** — ATMF VM : The IP source address in an ICMP Echo Reply
   - Folder: 
   - Objective: No
   - Justification: Objective: ICMP echo request must be the same with ICMP echo reply.

Precondition: 192.168.1.1/24
--------------
| DUT |
--------------

Status: Approved | Has objective: True | Num steps: 1 | Labels: Operational

Steps:
1. 1.1 Configure VLAN1 IP address on DUT (192.168.1.1)
1.2. Ping DUT ip address (192.168.1.1)
Test with IPv4 and IPv6 address

1. **[AWPTCM-T7540](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T7540)** — The IP source address in an ICMP Echo Reply
   - Folder: 
   - Objective: No
   - Justification: Objective: ICMP echo request must be the same with ICMP echo reply.

Precondition: 192.168.1.1/24
--------------
| DUT |
--------------

Status: Approved | Has objective: True | Num steps: 1 | Labels: Operational

Steps:
1. 1.1 Configure VLAN1 IP address on DUT (192.168.1.1)
1.2. Ping DUT ip address (192.168.1.1)


## ATPyLib Cases (Step 3)


- `2010.3.2` — The IP source address in an ICMP Echo Reply MUST be the same as the specific-destination address of the corresponding ICMP Echo Request

- `2002.3.2` — The IP source address in an ICMP Echo Reply MUST be the same as thespecific-destination address of the corresponding ICMP Echo Request

- `2005.10.1` — The source address of an Echo Reply sent in response to a unicast Echo Request message MUST be the same as the destination address of that Echo Request message


- ART string: 2010.3.2 + 2002.3.2 + 2005.10.1

## Gaps Noted
The selected ART coverage (2010.3.2, 2002.3.2, 2005.10.1) reasonably addresses the core RFC conformance behaviour: the source address of an ICMP Echo Reply matches the specific destination address of the corresponding unicast Echo Request, for both ICMPv4 and ICMPv6. The coverage is less clear on device-specific context from the TestLink and Zephyr artefacts, namely replies sourced from an address configured on the default VLAN1 interface rather than a generic test interface. Dual-stack validation on the same interface, as called out in AWP-21047, also lacks explicit coverage. The ATMF VM variant (AWP-21047 / AWPTCM-T2068) has no evident automated counterpart, so behaviour on virtualised ATMF platforms remains unverified. Edge conditions are also not clearly exercised, including multiple or secondary addresses on the same interface, replies when the destination is a non-primary address, and any interaction with management or VRF contexts.

## Tangential Cases Reviewed
(See selections for full list.)

## ART Test Cases String
2010.3.2 + 2002.3.2 + 2005.10.1

**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.