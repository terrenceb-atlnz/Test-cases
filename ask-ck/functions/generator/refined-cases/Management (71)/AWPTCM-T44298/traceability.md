# Traceability & Supporting Data for AWPTCM-T44298 ()

## Primary Decision

- **AWP-11529** – NTP over IPv6 as server
  - Decision confidence: med
  - Rationale: NTP over IPv6 as server


## Top Relevant TestLink Cases

**Primary + relevant historical TestLink cases reviewed for artefacts and context**

- **AWP-11529** — NTP over IPv6 - Operating as an NTP server.
  - Justification: Step: Ensure DUT clock synronized via NTP
Expected: NTP Status is synconised

Step: Start NTP client devices.
Note their NTP association and status
Expected: NTP Clients show a valid and association with the DUT as master.



## Zephyr Cross-References (Step 2)
**Relevant Zephyr Scale cases identified**

These cases were reviewed from the full Zephyr database (via `data/zephyr_full/`) for objective style, step structure, and related behaviour.


1. **[AWPTCM-T10517](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T10517)** — NTP over IPv6 - Operating as an NTP server.
   - Folder: 
   - Objective: No
   - Justification: Objective: NTP will respond to any NTP packets (unless the ingress packets are blocked by other processes - i.e. clasifiers)
NTP will respond appropriatly regardless what transport protocol the packets arrive on.

Precondition: DUT configured with several IPv6 and IPv4 interfaces.
Oher devices configured to use the DUT as an NTP server via IPv6 and/or IPv4.
DUT configured to us 1 or more external NTP servers via IPv6.

Status: Approved | Has objective: True | Num steps: 3 | Labels: Operational

Steps:
1. Ensure DUT clock synronized via NTP
2. Start NTP client devices.
Note their NTP association and status
3. check show command

1. **[AWPTCM-T33633](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T33633)** — NTP on VRF - Check that NTP client/server associations work when configured over a VRF
   - Folder: 
   - Objective: No
   - Justification: Objective: client server - both ends configured with NTP over a VRF vlan

Precondition: Wire as follows: [Client]----[DUT]----[NTP server] Configure appropriate IP addressing and routing on each of the devices above Ensure that the L3 interfaces on DUT are in a named VRF Configure NTP server as a server by using the "ntp master" command. Use the "ntp server [IP address of DUT]" command on "Client"

Status: Approved | Has objective: True | Num steps: 1

Steps:
1. use the command "ntp server vrf [VRF name] [IP address of NTP server]" on the DUT


## ATPyLib Cases (Step 3)



## Gaps Noted
No ATPyLib (ART) automated tests have been identified as covering this case, leaving the NTP-over-IPv6 server role entirely without automation coverage. The manual intent captured in AWPTCM-T44298 and its related artefacts (AWPTCM-T10517, AWPTCM-T33633) spans DUT clock synchronisation status verification, multi-client NTP association behaviour, and NTP operation over a VRF context, none of which are exercised by automation at present. Key gaps include observability of NTP synchronisation state transitions, correctness of client association reporting across multiple simultaneous clients, and the interaction between IPv6 NTP server behaviour and VRF-scoped configurations. Given the medium weighting of this decision, this represents a moderate but unaddressed risk area requiring either new automated test development or continued reliance on manual execution.

## Tangential Cases Reviewed
(See selections for full list.)

## ART Test Cases String


**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.