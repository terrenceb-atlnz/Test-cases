# Traceability & Supporting Data for AWPTCM-T35370 ()

## Primary Decision

- (No primary decision recorded)


## Top Relevant TestLink Cases

**Primary + relevant historical TestLink cases reviewed for artefacts and context**

- **AWP-3698** — DHCP client– command line test: ip address dhcp client-id <IFNAME>
  - Justification: Primary command coverage: `ip address dhcp client-id <IFNAME>` is the DHCP client identifier command the case is about, with normal/abnormal command-line variants

- **AWP-17338** — AWP5-DHCP-CLT-FUN-006 - AWP-3698:DHCP client command line test: ip address dhcp client-id <IFNAME>
  - Justification: AWP5 suite restatement of AWP-3698 (DHCP-CLT-FUN-006) — gives the newer test-suite framing and step numbering for the same client-id command

- **AWP-20768** — CR00041149: Part of the ClientID in "show ip dhcp binding" is incorrect value.
  - Justification: Reporting/verification path: how the ClientID renders in `show ip dhcp binding`, including a known defect in that field — informs the show-output assertions

- **AWP-26628** — CLI: New command - ip dhcp-client vendor-identifying-class
  - Justification: Extended client identification via option 124 (`ip dhcp-client vendor-identifying-class`) — closest match to the 'extended ID' aspect of the title

- **AWP-26629** — CLI: New command - ip dhcp-client request vendor-identifying-specific
  - Justification: Companion extended-ID option (`ip dhcp-client request vendor-identifying-specific`), verified via `show dhcp lease` and `sh run` — packet-option and config-persistence checks

- **AWP-18452** — DHCPv4 - DHCP Client
  - Justification: Baseline DHCPv4 client happy path on a VLAN interface — the precondition/setup the extended-ID case builds on

- **AWP-15614** — DHCP Client Lease Acceptance
  - Justification: DHCP client lease acceptance against a real server — confirms the client with a configured identifier actually obtains and installs a lease

- **AWP-23701** — Check DHCP client works on an interface within a vrf instance
  - Justification: Special condition: DHCP client on an interface inside a VRF instance — non-default context for client-id behaviour



## Zephyr Cross-References (Step 2)
**Relevant Zephyr Scale cases identified**

These cases were reviewed from the full Zephyr database (via `data/zephyr_full/`) for objective style, step structure, and related behaviour.


1. **[AWPTCM-T4610](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T4610)** — DHCP client– command line test: ip address dhcp client-id <IFNAME>
   - Folder: 
   - Objective: No
   - Justification: Exact TestLink counterpart (AWP-3698) for the DHCP client-id command-line test — the closest intent match to DHCP Extended ID

1. **[AWPTCM-T4621](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T4621)** — AWP5-DHCP-CLT-FUN-006 - AWP-3698:DHCP client command line test: ip address dhcp client-id <IFNAME>
   - Folder: 
   - Objective: No
   - Justification: AWP5-DHCP-CLT-FUN-006 / AWP-3698 client-id <IFNAME> test — same feature, DC2552XS functionality variant

1. **[AWPTCM-T20545](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T20545)** — CR00041149: Part of the ClientID in "show ip dhcp binding" is incorrect value.
   - Folder: 
   - Objective: No
   - Justification: CR00041149 confirmed in TestLink context — ClientID value shown in 'show ip dhcp binding', directly about client-id encoding

1. **[AWPTCM-T2171](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T2171)** — CLI: New command - ip dhcp-client vendor-identifying-class
   - Folder: 
   - Objective: No
   - Justification: ip dhcp-client vendor-identifying-class — DHCP client extended-identifier option CLI, from confirmed AWP-26628

1. **[AWPTCM-T2172](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T2172)** — CLI: New command - ip dhcp-client request vendor-identifying-specific
   - Folder: 
   - Objective: No
   - Justification: ip dhcp-client request vendor-identifying-specific — companion extended-identifier option CLI, from confirmed AWP-26629

1. **[AWPTCM-T4618](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T4618)** — AWP5-DHCP-CLT-FUN-003 - AWP-2262:DHCP client - show commands
   - Folder: 
   - Objective: No
   - Justification: DHCP client show commands — the verification style used to inspect client-id/binding state

1. **[AWPTCM-T4613](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T4613)** — AWP5-DHCP-CLT-CFG-001 - Test : Assign and Delete the switch an IPv4 management address obtained from
   - Folder: 
   - Objective: No
   - Justification: DHCP client configuration test assigning/deleting a DHCP-obtained management address — same client configure/verify pattern

1. **[AWPTCM-T4619](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T4619)** — AWP5-DHCP-CLT-FUN-004 - AWP-2474:DHCP client - IP address retrieval with user created VLAN
   - Folder: 
   - Objective: No
   - Justification: DHCP client IP retrieval on a user-created VLAN — same client-interface scoping used when client-id is per-IFNAME


## ATPyLib Cases (Step 3)


- `2003.6.6` — If the client used a 'client identifier' to obtain its address, the client MUST use the same 'client identifier' in the If the client supplies a 'client identifier', the client MUST use the same 'client identifier' in all subsequent messages DHCPREQUEST message

- `2003.5.15` — If the client used a 'client identifier' when it obtained the lease, it MUST use the same 'client identifier' in the DHCPRELEASE message If the client supplies a 'client identifier', the client MUST use the same 'client identifier' in all subsequent messages

- `2003.5.14` — The client identifies the lease to be released with its 'client identifier', or 'chaddr' and network address in the DHCPRELEASE message

- `2004.12.12` — The server MAY choose to return the 'vendor class identifier' used to determine the parameters in the DHCPOFFER message to assist the client in selecting which DHCPOFFER to accept

- `2003.5.3` — The client broadcasts a DHCPREQUEST message that MUST include the 'server identifier' option to indicate which server it has selected

- `2003.2.1` — A DHCP client must be prepared to receive multiple responses to a request for configuration parameters (Note: If the 'xid' of an arriving DHCPOFFER message does not match the 'xid' of the most recent DHCPDISCOVER message, the DHCPOFFER message must be silently discarded.)


- ART string: 2003.6.6 + 2003.5.15 + 2003.5.14 + 2004.12.12 + 2003.5.3 + 2003.2.1

## Gaps Noted
DHCP client identifier behaviour is reasonably well covered at the protocol level by the selected ART work: identifier persistence across the DHCP message sequence (DISCOVER/REQUEST, and again in RELEASE), lease identification by client-id versus chaddr, server-identifier handling in the selected-offer path, tolerance of multiple concurrent offers, and vendor-class identifier echo in the offer. What automation does not reach is the configuration and observability surface the manual case turns on — CLI acceptance and rejection of the interface-name form of the client identifier, its persistence in running configuration, and how the identifier is rendered in the client's own lease and binding output (including the known malformed-ClientID field). Also uncovered are the extended-identification options (vendor-identifying class and the request for vendor-identifying-specific information) as configurable, packet-observable, config-persistent features rather than as an incidental server-side echo, and the non-default contexts the Zephyr set exercises: user-created VLAN interfaces, management-address assignment and deletion, and a client interface inside a VRF instance.

## Tangential Cases Reviewed
(See selections for full list.)

## ART Test Cases String
2003.6.6 + 2003.5.15 + 2003.5.14 + 2004.12.12 + 2003.5.3 + 2003.2.1

**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.