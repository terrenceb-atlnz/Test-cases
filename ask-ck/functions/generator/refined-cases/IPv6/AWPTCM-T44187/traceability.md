# Traceability & Supporting Data for AWPTCM-T44187 ()

## Primary Decision

- **AWP-6511** – SSH server via IPv6
  - Decision confidence: med
  - Rationale: SSH server via IPv6


## Top Relevant TestLink Cases

**Primary + relevant historical TestLink cases reviewed for artefacts and context**

- **AWP-6511** — check SSH server via IPv6
  - Justification: Step: Connect to server(DUT) via IPv6:
DUT(config-if)#ipv6 add 3000:1::1/64
DUT(config-if)#exit
Client#ssh ipv6 username@3000:1::1
Expected: Client can login successfully

- **AWP-5821** — SSH: SSH Client to SSH Server
  - Justification: Step: Configure 4 devices with ipv6 address
Configure SSH server to DUT-1
Connect to DUT-1 using SSH connection from DUT-2
Note:
You may use the network diagram and configuration attached
Expected: Confirm SSH connection established in DUT-2 to DUT-1

- **AWP-5823** — SSH: SW-2 to DUT-1 - Kill SSH session
  - Justification: Step: Configure 4 devices with ipv6 address
Configure SSH server to DUT-1
Connect to DUT-1 using SSH connection from SW-2
Kill SSH session of SW-2 in DUT-1
Note:
You may use the network diagram and configuration attached
Expected: Confirm SSH connection established in SWITCH-2 to DUT-1
Confirm SSH connection of SW-2 killed via DUT-1

- **AWP-6512** — SSH server allow/deny users for IPv6
  - Justification: Step: ssh server allow-users/deny-users must match against IPv6 addresses
ssh server allow-users - ssh access restricted to listed users
* Add/create new users
username user1 priv 15 pass test1
username user2 priv 15 pass test1
username user3 priv 15 pass test1
username user4 priv 15 pass test1
username user5 priv 15 pass test1
* Allow users user1-user3 in the SSH server
ssh server allow user1
ssh server allow user2
ssh server allow user3
Expected: Client can connect if client used a user registered in the allow-users list
Client cannot connect if client used a user not registered in the allow-users list

- **AWP-24175** — Check SSH server (IPv4 and IPv6) will be supported
  - Justification: Step: Check SSH server (IPv4 and IPv6) will be supported
Expected: Confirm SSH server (IPv4 and IPv6) will be supported

- **AWP-5824** — SSH: SW-1 to DUT-1 - Disable SSH server
  - Justification: Step: Configure 4 devices with ipv6 address
Disable SSH service in DUT-1
Note:
You may use the network diagram and configuration attached
Expected: Confirm SW-1 cannot perform SSH connection to DUT-1

- **AWP-5825** — SSH: Max Session
  - Justification: Step: Configure 4 devices with ipv6 address
Configure SSH server to DUT-1
Configure line vty 0 32 to establish maximum session
Note:
You may use the network diagram and configuration attached
Expected: Confirm connection to DUT-1 to DUT-2 established
Confirm on the 33th time connection cannot establish
Confirm 33 user are connected to DUT-1 'sh ssh | grep -c server'

- **AWP-6485** — enable/disable ssh server
  - Justification: Step: 1. On DUT, enable ssh server then make an ssh session from client to DUT
DUT#conf t
DUT(config)# service ssh
Client# ssh [username]@192.168.1.1
2. Disable ssh server on the DUT
DUT#conf t
DUT(config)#no service ssh
Client# ssh [username]@192.168.1.1
Expected: 1. Verify client can connect to device when ssh service is enabled
2. Verify client cannot connect to device when ssh service is disabled



## Zephyr Cross-References (Step 2)
**Relevant Zephyr Scale cases identified**

These cases were reviewed from the full Zephyr database (via `data/zephyr_full/`) for objective style, step structure, and related behaviour.


1. **[AWPTCM-T8386](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T8386)** — SSH: SW-2 to DUT-1 - Kill SSH session
   - Folder: 
   - Objective: No
   - Justification: Objective: Test for SSH command from SW-2 to DUT-1 (Kill SSH session on DUT-1)

Status: Approved | Has objective: True | Num steps: 1 | Labels: Functional

Steps:
1. Configure 4 devices with ipv6 address
Configure SSH server to DUT-1
Connect to DUT-1 using SSH connection from SW-2
Kill SSH session of SW-2 in DUT-1
Note:
You may use the network diagram and configuration attached

1. **[AWPTCM-T16080](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T16080)** — SSH server allow/deny users for IPv6
   - Folder: 
   - Objective: No
   - Justification: Objective: SSH Server Tests
Verify that SSH server allow/deny users works on an IPv6 SSH session

Precondition: On DUT, add a management IPv6 address then enable ssh service by ganerating hostkey (RSA or DSA)
awplus(config)#crypto key generate hostkey rsa
awplus(config)#crypto key generate hostkey dsa
awplus(config)#service ssh
Add ssh user:
awplus(config)#ssh server allow-users [USERNAME-PATTERN]
Note: make sure that IPv6 forwarding is enabled on both server and client

Status: Approved | Has objective: True | Num steps: 1 | Labels: Operational, Platform-Test

Steps:
1. ssh server allow-users/deny-users must match against IPv6 addresses
ssh server allow-users - ssh access restricted to listed users
* Add/create new users
username user1 priv 15 pass test1
username user2 priv 15 pass test1
username user3 priv 15 pass test1
username user4 priv 15 pass test1
username user5 priv 15 pass test1
* Allow users user1-user3 in the SSH server
ssh server allow user1
ssh server allow user2
ssh server allow user3

1. **[AWPTCM-T8387](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T8387)** — SSH: SW-1 to DUT-1 - Disable SSH server
   - Folder: 
   - Objective: No
   - Justification: Has objective: None | Num steps: None

1. **[AWPTCM-T16079](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T16079)** — check SSH server via IPv6
   - Folder: 
   - Objective: No
   - Justification: Has objective: None | Num steps: None

1. **[AWPTCM-T2641](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T2641)** — Check SSH server (IPv4 and IPv6) will be supported
   - Folder: 
   - Objective: No
   - Justification: Has objective: None | Num steps: None

1. **[AWPTCM-T46118](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T46118)** — SSH: ipv6 client and server
   - Folder: 
   - Objective: No
   - Justification: Has objective: None | Num steps: None

1. **[AWPTCM-T16067](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T16067)** — enable/disable ssh server
   - Folder: 
   - Objective: No
   - Justification: Has objective: None | Num steps: None

1. **[AWPTCM-T8388](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T8388)** — SSH: Max Session
   - Folder: 
   - Objective: No
   - Justification: Objective: Test for SSH Max Session per switch

Precondition: When testing IPv6 addresses: Please use only valid IPv6 address.
e.g. avoid using 2002::/16 prefix is used for 6to4, which requires the next 32 bits (after the 16 bit prefix) to be a global unicast IPv4 address.
see: http://www.iana.org/assignments/ipv6-unicast-address-assignments/ipv6-unicast-address-assignments.xhtml

Status: Approved | Has objective: True | Num steps: 1 | Labels: Functional

Steps:
1. Configure 4 devices with ipv6 address
Configure SSH server to DUT-1
Configure line vty 0 32 to establish maximum session
Note:
You may use the network diagram and configuration attached


## ATPyLib Cases (Step 3)


- `1348.1001.5` — SSH login from tb

- `1348.1001.6` — SSH deny certain users

- `5049.4009.1` — Basic SSH connectivity Test

- `5049.3130.1` — Basic SSH connectivity Test

- `5049.2030.1` — Basic SSH connectivity Test

- `1348.1001.8` — SSH concurrent users login from tb

- `1348.1001.7` — SSH check CLI commands


- ART string: 1348.1001.5 + 1348.1001.6 + 5049.4009.1 + 5049.3130.1 + 5049.2030.1 + 1348.1001.8 + 1348.1001.7

## Gaps Noted
The selected ART tests give reasonable confidence in core SSH server behaviour — successful login from a client, concurrent/multi-user sessions, CLI usability within an established session, and user-based access restriction — across several platform variants. However, that coverage is predominantly IPv4-oriented and does not exercise the IPv6 transport path that is the focus of this case, including connections to a link-local or global IPv6 address, allow-users/deny-users matching against IPv6 address patterns, and the combined IPv4/IPv6 server support expectation. Also thinly covered are the session lifecycle and administrative controls described in the manual material: enabling and disabling the SSH service and the resulting client-side behaviour, terminating an established session from the server side, and the enforcement boundary and rejection behaviour when the configured maximum VTY session count is exceeded. Finally, automation provides limited observability of server-side session state and connection accounting, so failures in IPv6 negotiation or session teardown would likely surface only as a generic connectivity failure rather than an identifiable defect.

## Tangential Cases Reviewed
(See selections for full list.)

## ART Test Cases String
1348.1001.5 + 1348.1001.6 + 5049.4009.1 + 5049.3130.1 + 5049.2030.1 + 1348.1001.8 + 1348.1001.7

**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.