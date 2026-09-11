# Sequence — AWPTCM-T33351

1. In global configuration mode, configure the RADIUS server used for 802.1X (radius-server host with key), enable dot1x system-wide (aaa authentication dot1x), and create the data VLAN(s) that RADIUS may assign plus the Guest VLAN referenced by the test.
   verify: 'show dot1x' reports '802.1X Port-Based Authentication Enabled' and the configured 'RADIUS server address: <ip>:1812' line matches the server just configured.
2. Enter interface configuration for the test port and apply 'dot1x port-control auto' then 'auth host-mode single-host'.
   verify: 'show running-config' on the test port shows both 'dot1x port-control auto' and 'auth host-mode single-host'; 'show dot1x' for the test port shows 'portEnabled: true - portControl: Auto'. This confirms single-host mode is accepted and reflected in running config and operational state.
3. With the supplicant connected but before any 802.1X authentication is attempted, use Scapy/tcpdump on the partner to send a non-EAPOL data frame (e.g. an ARP or IP packet) from the supplicant into the test port and capture on the far side of the assigned VLAN.
   verify: The non-EAPOL frame is NOT forwarded (no capture on the egress side); 'show dot1x' for the test port reports 'portStatus: Unauthorized'. Only EAPOL frames are accepted at this stage.
4. Drive the supplicant through a full 802.1X (EAP) exchange against the RADIUS server (send EAPOL-Start / respond to EAP-Request Identity and method) using valid credentials.
   verify: 'show dot1x' for the test port reports 'portStatus: Authorized'; 'show auth' shows the supplicant authenticated and the assigned VLAN (RADIUS-assigned, or the Guest VLAN if RADIUS returns none). Confirms successful authentication and VLAN placement in single-host mode.
5. After authentication succeeds, send data traffic (ARP/IP) from the authenticated supplicant through the test port and capture on the egress side of the assigned VLAN.
   verify: The data frames are now forwarded on the assigned VLAN (captured on egress), confirming the single supplicant is granted network access consistent with the VLAN assignment.
6. Read the authentication show commands for the test port: 'show dot1x all' and 'show auth all'.
   verify: Output for the test port reflects single-host mode, 'portStatus: Authorized', 'portControl: Auto', and the assigned VLAN plus supplicant details are reported accurately.
7. From the authenticated supplicant, send an EAPOL-Logoff frame into the test port.
   verify: 'show dot1x' for the test port returns to 'portStatus: Unauthorized'; an EAP-Failure is emitted toward the supplicant (observed in the capture); the deauthorization is recorded (visible via 'show log' / 'show auth') and 'show auth' no longer lists the supplicant as authenticated.
8. On the single-host test port, attempt the unsupported dynamic VLAN option: 'auth dynamic-vlan-creation type multi'.
   verify: The CLI rejects the command with an error (the 'type' keyword is not accepted in single-host / on platforms that only support 'auth dynamic-vlan-creation [rule {deny|permit}]'); the running-config for the port does not contain the rejected option.
9. Re-verify the valid single-host configuration still functions after the rejected command by re-reading the port config and re-driving a valid supplicant authentication.
   verify: 'show running-config' still shows 'dot1x port-control auto' and 'auth host-mode single-host' unchanged; a valid supplicant again reaches 'portStatus: Authorized' in 'show dot1x'. Confirms the rejection left the working config intact.
10. Persist the 802.1X configuration (host-mode single-host, RADIUS server, related timeouts) with 'copy running-config startup-config', then reload the switch (or restart the relevant process where a full reload is not supported).
   verify: After restart, 'show startup-config' and 'show running-config' still contain the dot1x/single-host/RADIUS/timer settings; 'show dot1x' shows the RADIUS server and the test port's single-host auto configuration restored, and a supplicant can again authenticate — confirming persistence and restoration where supported.
