You are selecting reusable code fragments from existing Allied Telesis test scripts to
cover a required test-step sequence. You reference fragments by symbol — you never write code.

## Required sequence (case AWPTCM-T33351)

1. action: In global configuration mode, configure the RADIUS server used for 802.1X (radius-server host with key), enable dot1x system-wide (aaa authentication dot1x), and create the data VLAN(s) that RADIUS may assign plus the Guest VLAN referenced by the test.
   verify: 'show dot1x' reports '802.1X Port-Based Authentication Enabled' and the configured 'RADIUS server address: <ip>:1812' line matches the server just configured.

2. action: Enter interface configuration for the test port and apply 'dot1x port-control auto' then 'auth host-mode single-host'.
   verify: 'show running-config' on the test port shows both 'dot1x port-control auto' and 'auth host-mode single-host'; 'show dot1x' for the test port shows 'portEnabled: true - portControl: Auto'. This confirms single-host mode is accepted and reflected in running config and operational state.

3. action: With the supplicant connected but before any 802.1X authentication is attempted, use Scapy/tcpdump on the partner to send a non-EAPOL data frame (e.g. an ARP or IP packet) from the supplicant into the test port and capture on the far side of the assigned VLAN.
   verify: The non-EAPOL frame is NOT forwarded (no capture on the egress side); 'show dot1x' for the test port reports 'portStatus: Unauthorized'. Only EAPOL frames are accepted at this stage.

4. action: Drive the supplicant through a full 802.1X (EAP) exchange against the RADIUS server (send EAPOL-Start / respond to EAP-Request Identity and method) using valid credentials.
   verify: 'show dot1x' for the test port reports 'portStatus: Authorized'; 'show auth' shows the supplicant authenticated and the assigned VLAN (RADIUS-assigned, or the Guest VLAN if RADIUS returns none). Confirms successful authentication and VLAN placement in single-host mode.

5. action: After authentication succeeds, send data traffic (ARP/IP) from the authenticated supplicant through the test port and capture on the egress side of the assigned VLAN.
   verify: The data frames are now forwarded on the assigned VLAN (captured on egress), confirming the single supplicant is granted network access consistent with the VLAN assignment.

6. action: Read the authentication show commands for the test port: 'show dot1x all' and 'show auth all'.
   verify: Output for the test port reflects single-host mode, 'portStatus: Authorized', 'portControl: Auto', and the assigned VLAN plus supplicant details are reported accurately.

7. action: From the authenticated supplicant, send an EAPOL-Logoff frame into the test port.
   verify: 'show dot1x' for the test port returns to 'portStatus: Unauthorized'; an EAP-Failure is emitted toward the supplicant (observed in the capture); the deauthorization is recorded (visible via 'show log' / 'show auth') and 'show auth' no longer lists the supplicant as authenticated.

8. action: On the single-host test port, attempt the unsupported dynamic VLAN option: 'auth dynamic-vlan-creation type multi'.
   verify: The CLI rejects the command with an error (the 'type' keyword is not accepted in single-host / on platforms that only support 'auth dynamic-vlan-creation [rule {deny|permit}]'); the running-config for the port does not contain the rejected option.

9. action: Re-verify the valid single-host configuration still functions after the rejected command by re-reading the port config and re-driving a valid supplicant authentication.
   verify: 'show running-config' still shows 'dot1x port-control auto' and 'auth host-mode single-host' unchanged; a valid supplicant again reaches 'portStatus: Authorized' in 'show dot1x'. Confirms the rejection left the working config intact.

10. action: Persist the 802.1X configuration (host-mode single-host, RADIUS server, related timeouts) with 'copy running-config startup-config', then reload the switch (or restart the relevant process where a full reload is not supported).
   verify: After restart, 'show startup-config' and 'show running-config' still contain the dot1x/single-host/RADIUS/timer settings; 'show dot1x' shows the RADIUS server and the test port's single-host auto configuration restored, and a supplicant can again authenticate — confirming persistence and restoration where supported.


## Available source symbols (from the selected scripts; class and function names with descriptions)
Each script carries its step-3 review verdicts: which sequence step(s) the reviewer chose it
for, the coverage judged there (full/partial), and why. Use them — they say what each script
was selected to contribute.

### art/1348_security/test-1348.1001.py


chosen for sequence step 1 — partial coverage — Configures RADIUS server for authentication, 802.1x/dot1x, and includes RADIUS CLI and 802.1x configuration cases directly reusable for the setup and show-dot1x verification.

chosen for sequence step 2 — partial coverage — Includes an 802.1x configuration-changes case exercising dot1x port control on a test port, directly reusable for applying and verifying port-control/host-mode settings.

chosen for sequence step 4 — partial coverage — Covers 802.1x configuration and RADIUS user login on a VLAN, the same feature and CLI area as the required EAP-against-RADIUS step.



- class TestSet: topology init (tb, stk_a, swi_a, swi_b), configure=True

- class TestCase_1: Tacacs+ user login, server online

- class TestCase_2: Tacacs+ user login with server offline

- class TestCase_3: Tacacs+ stress user login, server online

- class TestCase_4: Tacacs+ CLI commands

- class TestCase_5: SSH login from tb

- class TestCase_6: SSH deny certain users

- class TestCase_7: SSH check CLI commands

- class TestCase_8: SSH concurrent users login from tb

- class TestCase_9: Radius server online: various users logging in

- class TestCase_10: Radius CLI commands

- class TestCase_11: 802.1x configuration changes

- class TestCase_12: User login to local radius-server on a vlan

- class TestCase_common_radius_server_cli_commands: 

- class TestCase_13: Local radius-server CLI commands

- class TestCase_5646: Local radius-server CLI commands

- class TestCase_14: Radius server accounting logins

- class TestCase_15: Tacacs+ accounting server login

- class TestCase_16: Tacacs+ accounting server commands

- class TestCase_17: SSH scp copy

- class TestCase_18: SSH sftp copy

- class TestCase_19: Auth-mac authentication on port

- class TestCase_20: 802.1x/ dot1x authentication on port

- class TestCase_21: User login to local radius-server at 127.0.0.1

- class TestCase_22: SSH scp copy from dut

- class TestCase_23: Management ACLs - SSH

- class TestCase_24: Management ACLs - Telnet

- class TestCase_25: Flexible RADIUS group selection -  configuration

- class TestCase_26: Flexible RADIUS group selection - auth-mac on ports

- class TestCase_27: Flexible RADIUS group selection - 802.1X on port and VLAN

- class TestCase_28: Flexible RADIUS group selection - 802.1x on ports, multiple radius servers

- class TestCase_29: Single supplicant mode with multiple VLANs

- class TestCase_30: Warning when using default password

- class TestCase_31: openSSL TLS1.2 supported ciphers

- class TestCase_301: openSSL TLS1.2 supported ciphers

- class TestCase_32: openSSL TLS1.3 supported ciphers

- class TestCase_33: 802.1x/ dot1x authentication with dynamic vlan assignment on port

- class TestCase_34: Radius API test

- class TestCase_35: Auth-mac with auth-forward, all forwards

- class TestCase_3501: Auth-mac with auth-forward, tcp

- class TestCase_4501: Auth-mac with auth-forward, tcp, inter-vlan

- class TestCase_3502: Auth-mac with auth-forward, A.B.C.D tcp

- class TestCase_4502: Auth-mac with auth-forward, A.B.C.D tcp, inter-vlan

- class TestCase_3503: Auth-mac with auth-forward, A.B.C.D/M tcp

- class TestCase_4503: Auth-mac with auth-forward, A.B.C.D/M tcp, inter-vlan

- class TestCase_3504: Auth-mac with auth-forward, udp

- class TestCase_4504: Auth-mac with auth-forward, udp, inter-vlan

- class TestCase_3505: Auth-mac with auth-forward, A.B.C.D udp

- class TestCase_4505: Auth-mac with auth-forward, A.B.C.D udp, inter-vlan

- class TestCase_3506: Auth-mac with auth-forward, A.B.C.D/M udp

- class TestCase_4506: Auth-mac with auth-forward, A.B.C.D/M udp, inter-vlan

- class TestCase_3507: Auth-mac with auth-forward, arp

- class TestCase_3508: Auth-mac with auth-forward, dns

- class TestCase_4508: Auth-mac with auth-forward, dns, inter-vlan

- class TestCase_3509: Auth-mac with auth-forward, dhcp

- class TestCase_4509: Auth-mac with auth-forward, dhcp, inter-vlan, DHCP Relay

- class TestCase_36: Dot1x with auth-forward, all forwards

- class TestCase_3601: Dot1x with auth-forward, tcp

- class TestCase_4601: Dot1x with auth-forward, tcp, inter-vlan

- class TestCase_3602: Dot1x with auth-forward, A.B.C.D tcp

- class TestCase_4602: Dot1x with auth-forward, A.B.C.D tcp, inter-vlan

- class TestCase_3603: Dot1x with auth-forward, A.B.C.D/M tcp

- class TestCase_4603: Dot1x with auth-forward, A.B.C.D/M tcp, inter-vlan

- class TestCase_3604: Dot1x with auth-forward, udp

- class TestCase_4604: Dot1x with auth-forward, udp, inter-vlan

- class TestCase_3605: Dot1x with auth-forward, A.B.C.D udp

- class TestCase_4605: Dot1x with auth-forward, A.B.C.D udp, inter-vlan

- class TestCase_3606: Dot1x with auth-forward, A.B.C.D/M udp

- class TestCase_4606: Dot1x with auth-forward, A.B.C.D/M udp, inter-vlan

- class TestCase_3607: Dot1x with auth-forward, arp

- class TestCase_3608: Dot1x with auth-forward, dns

- class TestCase_4608: Dot1x with auth-forward, dns, inter-vlan

- class TestCase_3609: Dot1x with auth-forward, dhcp

- class TestCase_4609: Dot1x with auth-forward, dhcp, inter-vlan, DHCP Relay

- class TestCase_37: Auth-web with auth-forward, all forwards

- class TestCase_3701: Auth-web with auth-forward, tcp

- class TestCase_4701: Auth-web with auth-forward, tcp, inter-vlan

- class TestCase_3702: Auth-web with auth-forward, A.B.C.D tcp

- class TestCase_4702: Auth-web with auth-forward, A.B.C.D tcp, inter-vlan

- class TestCase_3703: Auth-web with auth-forward, A.B.C.D/M tcp

- class TestCase_4703: Auth-web with auth-forward, A.B.C.D/M tcp, inter-vlan

- class TestCase_3704: Auth-web with auth-forward, udp

- class TestCase_4704: Auth-web with auth-forward, udp, inter-vlan

- class TestCase_3705: Auth-web with auth-forward, A.B.C.D udp

- class TestCase_4705: Auth-web with auth-forward, A.B.C.D udp, inter-vlan

- class TestCase_3706: Auth-web with auth-forward, A.B.C.D/M udp

- class TestCase_4706: Auth-web with auth-forward, A.B.C.D/M udp, inter-vlan

- class TestCase_40: Port Scan - UDP and TCP ports

- class TestCase_42: Using host-mode multi-supplicant to restrict portauth VLANs by tagged or untagged status with local RADIUS

- class TestCase_43: Using host-mode multi-supplicant to restrict portauth VLANs by tagged or untagged status with remote RADIUS

- class TestCase_44: Using host-mode host-plus-voice to restrict portauth VLANs with local RADIUS

- class TestCase_45: Using host-mode host-plus-voice to restrict portauth VLANs with remote RADIUS

- class TestCase_775540: Strict User Process Control - user must enter matching passwords

- class TestCase_775541: Strict User Process Control


### art/1341_limits/test-1341.6001.py


chosen for sequence step 1 — partial coverage — Configures 802.1x/dot1x authentication with dynamic RADIUS VLAN assignment on ports, reusing the dot1x + RADIUS server + VLAN mechanics.

chosen for sequence step 6 — partial coverage — Tests 802.1x dynamic VLAN assignment on a port with supplicant verification, directly reusing dot1x show/status parsing mechanics.

chosen for sequence step 8 — partial coverage — Directly configures 802.1x dynamic vlan assignment (untagged) on a port, giving the same 'auth dynamic-vlan-creation' CLI area needed to attempt and reject the 'type multi' option.



- class TestSet: topology init (tb, stk_a, swi_a), configure=True

- class TestCase_2567: max supported VXLAN for broadcom - Max VNIs

- class TestCase_25671: max supported VXLAN for broadcom - Max VTEPs

- class TestCase_5090: 802.1x/ dot1x authentication with dynamic vlan assignment (untagged) on port

- class TestCase_5258: max supported mac-auth supplicants

- class TestCase_5346: web-auth redirects to web authentication page for max supplicants

- class TestCase_50100: max supported static aggregators

- class TestCase_50101: max supported LACP dynamic aggregators

- class TestCase_6975: max supported RADIUS proxy NAS clients

- class Generic_MRP: 

- class TestCase_73991: Maximum MRP rings, access mode

- class TestCase_73992: Maximum MRP rings, trunk mode


### art/1367_security_failover/library_1367.py


chosen for sequence step 2 — partial coverage — Supplies supplicant status parsing helpers usable to verify dot1x operational state (portEnabled/portControl).



- function resolve_addresses: 

- function checkAuthenticateClient: A method to check show auth supp brief

- function add_full_license_if_test_supported: 

- function add_license: 

- function remove_license: 

- function remove_added_licenses: 

- function get_system_module_name: 


### legacy/tools/auth_simulator/dot1x_simulator.py


chosen for sequence step 3 — partial coverage — Uses scapy to drive 802.1x supplicant/EAPOL sessions against a switch port, reusable for crafting and injecting the pre-auth frames.

chosen for sequence step 4 — partial coverage — Provides the exact supplicant-driving mechanic (scapy 802.1x EAPOL/EAP exchange) needed for the action, though it lacks the show-command verification.

chosen for sequence step 7 — partial coverage — Scapy-based 802.1x supplicant simulator that constructs and sends EAPOL frames, directly reusable for emitting the EAPOL-Logoff and observing EAP-Failure.

chosen for sequence step 9 — partial coverage — Drives 802.1x supplicant authentication sessions, providing the valid-supplicant authentication mechanic needed to reach Authorized.

chosen for sequence step 10 — partial coverage — Simulates 802.1x supplicant authentication, reusable to confirm a supplicant can again authenticate after restart.



- function cli_help: Print script arguments to the console

- function cli_parser: Check CLI parameters are present

- function main: 


### art/1367_security_failover/test-1367.1001.py


chosen for sequence step 4 — partial coverage — Tests RADIUS-based port authentication with dynamic VLAN assignment (COA) and supplicant status, reusable for RADIUS-assigned VLAN verification.



- class TestSet: topology init (tb, stk_a, swi_a, swi_b, swi_c, swi_d), configure=True

- class TestCase_1: Radius Server Auth-mac Simple Test

- class TestCase_2: Radius Server Auth-web Simple Test

- class TestCase_11: Radius COA Support

- class TestCase_21: MACSec test

- class TestCase_72373: The authenticator forwards the packet from supplicant before the response from the RADIUS server


### legacy/8003_x8100/test-9999.007.py


chosen for sequence step 5 — partial coverage — Reusable traffic-generation-and-capture pattern for sending data through the switch and confirming forwarding on a given VLAN.



- class TestSet: Check that the testbox can successfully send L3 traffic through the switch with it being routed between VLANs.

- class TestCase_1: Within a card: Card A

- class TestCase_2: Check that the testbox can successfully send L3 traffic through the switch with it being routed between VLANs.

- class TestCase_3: Within a card: Card B

- class TestCase_4: Check that the testbox can successfully send L3 traffic through the switch with it being routed between VLANs.

- class TestCase_5: Within a card: Card C

- class TestCase_6: Check that the testbox can successfully send L3 traffic through the switch with it being routed between VLANs.

- class TestCase_7: Across 2 cards, with ingress on card A

- class TestCase_8: Check that the testbox can successfully send L3 traffic through the switch with it being routed between VLANs.


### art/1348_security/test-1348.3001.py


chosen for sequence step 10 — partial coverage — Verifies authentication is restored and works after an imi process restart, the same process-restart-then-reauth pattern the step needs where full reload is unsupported.



- class TestSet: topology init (tb, stk_a, swi_a, swi_b), configure=True

- class TestCase_1: Verify web-auth service is operational

- class TestCase_2: Verify access to network is disabled for supplicant prior to web authentication

- class TestCase_3: Verify HTTP request to internet is redirected to web authentication page on DUT

- class TestCase_4: With correct credentials provided to web-auth server, confirm access is granted and network is reachable

- class TestCase_5: Verify authentication status is reset to Unauthenticated after web auth enabled link is brought down

- class TestCase_51: Verify web authentication works after port link is brought down and back up

- class TestCase_6: With incorrect credentials provided to web-auth server, confirm access is denied and network is not reachable

- class TestCase_7: Verify Auth-web page fields can be modified from configuration

- class TestCase_8: Multi user authentication test with correct credentials provided to web-auth server, confirm access is granted and network is reachable to all users

- class TestCase_9: Verify Multi user authentication works after imi process restart



## Task — per sequence step, with full accounting
Work step by step through the sequence. For EACH step, find every symbol above that could
serve it, then split them into:
  • "chosen" — the fragment(s) actually worth reusing for that step. A step may need MORE
    THAN ONE chosen fragment when they do genuinely different things (e.g. one configures,
    one verifies) — include each. Do NOT collapse genuinely-different pieces into one.
  • "redundant" — other symbols that ALSO cover the step but duplicate a chosen fragment
    (same mechanic, near-identical variant). Attach each redundant symbol to the chosen
    fragment it duplicates, with a one-line reason it is redundant to that specific choice.

Cover every step you can with at least one chosen fragment. A step with no reusable symbol
at all is a genuine gap — omit it (do not invent symbols).

## Rules (strict for repeatable output)
- Start each step at the scripts whose review verdicts name that step — the "chosen for
  sequence step N — why" lines are the reviewer's own routing. Look wider only when those
  scripts genuinely lack a usable symbol for the step.
- Every "symbol" must be an EXACT name from the lists above; "source_id" its script id.
  The server extracts real code by line range — invented names are dropped.
- A fragment may serve several steps: list them all in its "maps_to".
- "why" on a chosen fragment = why it was SELECTED (what it does for the step, what to keep/adapt).
- "why" on a redundant fragment = why it is REDUNDANT to the chosen fragment it hangs under
  (state the selection reasoning first, then the duplication).
- Output JSON ONLY, this shape:
{"steps": [
  {"n": 1, "chosen": [
     {"source_id": "art/....py", "symbol": "TestCase_2", "maps_to": [1,2],
      "why": "selected because ...",
      "redundant": [
        {"source_id": "art/....py", "symbol": "TestCase_5",
         "why": "redundant to TestCase_2 because ..."}
      ]}
  ]}
]}