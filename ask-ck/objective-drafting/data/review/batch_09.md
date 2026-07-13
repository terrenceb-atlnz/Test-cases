# Rerank batch 09  (cases 270..299)

### AWPTCM-T44271  |  area: Authentication Security IEEE 802.1XEncryptionType  |  feature: EAP-LEAP
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-6778    0.387 [Port Authentication   ] EAP Forwarding Tests                                    :: [Note] On 5.4.5-0.x, try this test on interface mode or auth-config mode. Verify switch action when EAP forwarding is enabled or d
  - AWP-142     0.382 [Customer Scenario     ] EAP support                                             :: Confirm that dot1authentications is possible. (all kinds of eap supported on AW+) | step1: Do dot1 authentication on each eap type
  - AWP-6786    0.353 [Port Authentication   ] Authentication message exchange                         :: Confirm that an authenticator exchanges authentication messages between the supplicant and Radius server. | step1: 1. Configure DU
  - AWP-5435    0.324 [RADIUS                ] Local Radius & VCS / Web Auth / EAP-MD5                 :: Behavior of EAP-MD5 Authentication: Confirm that a client can be authenticated through Web Authentication using EAP-MD5 Challenge 
  - AWP-6787    0.315 [Port Authentication   ] Packet Format on Authenticator port                     :: Confirm the Packet format that the protocol used for port-based access control is the IETF standard Extensible Authentication Prot
  - AWP-5396    0.314 [RADIUS                ] Local Radius behavior of EAP-MD5 authentication Dot1x   :: Confirm that a client can be authenticated with EAP-MD5, and this client should be moved to the group’s vlan by dynamic vlan. | st
  - AWP-5410    0.311 [RADIUS                ] Local Radius & VCS / Dot1x Auth / EAP-MD5               :: Dot1X authentication by EAP-MD5: Confirm that a client can be authenticated with EAP-MD5, and this client should be moved to the g
  - AWP-5398    0.310 [RADIUS                ] Local Radius behavior of EAP-TLS authentication Dot1x   :: Confirm that a client can be authenticated with EAP-TLS, and this client should be moved to the group’s vlan by dynamic vlan. | st

### AWPTCM-T44272  |  area: Authentication Security IEEE 802.1XEncryptionType  |  feature: EAP-OTP
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-6778    0.387 [Port Authentication   ] EAP Forwarding Tests                                    :: [Note] On 5.4.5-0.x, try this test on interface mode or auth-config mode. Verify switch action when EAP forwarding is enabled or d
  - AWP-142     0.382 [Customer Scenario     ] EAP support                                             :: Confirm that dot1authentications is possible. (all kinds of eap supported on AW+) | step1: Do dot1 authentication on each eap type
  - AWP-6786    0.353 [Port Authentication   ] Authentication message exchange                         :: Confirm that an authenticator exchanges authentication messages between the supplicant and Radius server. | step1: 1. Configure DU
  - AWP-5435    0.324 [RADIUS                ] Local Radius & VCS / Web Auth / EAP-MD5                 :: Behavior of EAP-MD5 Authentication: Confirm that a client can be authenticated through Web Authentication using EAP-MD5 Challenge 
  - AWP-6787    0.315 [Port Authentication   ] Packet Format on Authenticator port                     :: Confirm the Packet format that the protocol used for port-based access control is the IETF standard Extensible Authentication Prot
  - AWP-5396    0.314 [RADIUS                ] Local Radius behavior of EAP-MD5 authentication Dot1x   :: Confirm that a client can be authenticated with EAP-MD5, and this client should be moved to the group’s vlan by dynamic vlan. | st
  - AWP-5410    0.311 [RADIUS                ] Local Radius & VCS / Dot1x Auth / EAP-MD5               :: Dot1X authentication by EAP-MD5: Confirm that a client can be authenticated with EAP-MD5, and this client should be moved to the g
  - AWP-5398    0.310 [RADIUS                ] Local Radius behavior of EAP-TLS authentication Dot1x   :: Confirm that a client can be authenticated with EAP-TLS, and this client should be moved to the group’s vlan by dynamic vlan. | st

### AWPTCM-T44273  |  area: Authentication Security DynamicVlan  |  feature: Single Dynamic VLAN
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-9529    0.506 [Roaming Authentication] Roaming Auth - Single-mode, no guest VLAN, per port, no :: Authentication works correctly with single-mode, no guest VLAN, per port and no dynamic VLAN | step1: Single-Mode / no GuestVLAN /
  - AWP-9497    0.500 [Roaming Authentication] Auth+ LAG Static - Single-mode, no guest VLAN, per port :: Test that authentication works correctly with single-mode, no guest VLAN, per port and no dynamic VLAN | step1: Single-Mode / no G
  - AWP-9500    0.499 [Roaming Authentication] Auth+ LAG Static - Single-mode, guest VLAN, per port, d :: Test that authentication works with single-mode, guest VLAN, per port, dynamic VLAN | step1: Single-Mode / GuestVLAN / per port / 
  - AWP-9499    0.494 [Roaming Authentication] Auth+ LAG Static - Single-mode, guest VLAN, per port, n :: Test that authentication works with single-mode, guest VLAN, per port, dynamic VLAN | step1: Single-Mode / GuestVLAN / per port / 
  - AWP-9498    0.493 [Roaming Authentication] Auth+ LAG Static - Single-mode, no guest VLAN, per port :: Test that authentication works with single-mode, no guest VLAN, per port, dynamic VLAN | step1: Single-Mode / no GuestVLAN / per p
  - AWP-9516    0.485 [Roaming Authentication] Auth+ LAG LACP - Single-mode, guest VLAN, per port, dyn :: Check that authentication works with single-mode, guest VLAN, per port, dynamic VLAN | step1: Single-Mode / GuestVLAN / per port /
  - AWP-9515    0.481 [Roaming Authentication] Auth+ LAG LACP - Single-mode, guest VLAN, per port, no  :: Check that authentication works with single-mode, guest VLAN, per port, dynamic VLAN | step1: Single-Mode / GuestVLAN / per port /
  - AWP-9532    0.467 [Roaming Authentication] Roaming Auth -Single-mode, guest VLAN, per port, dynami :: Authentication works with single-mode, guest VLAN, per port, dynamic VLAN | step1: Single-Mode / GuestVLAN / per port / DynamicVLA

### AWPTCM-T44274  |  area: Authentication Security WebAuthentication  |  feature: Multiple Authentication
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-27197   0.379 [AWC-lite              ] security                                                :: | step1: security <configured security id> Confirm that ID of security for network setting are configured on router.
  - AWP-28452   0.367 [Port Authentication   ] single-supplicant mode with multiple VLAN and re-authen :: Confirm re-authentication works correctly without deleting FDB. | step1: After authed, confirm re-authentication start => FDB shou
  - AWP-5762    0.365 [Port Security (Intrusi] enable port authentication                              :: port security ignores supplicant mac addresses | step1: enable port authentication (802.1x), enable port-security on port1.0.1. =>
  - AWP-27204   0.352 [AWC-lite              ] security                                                :: | step1: security <configured security id> Confirm that ID of security for WDS setting are configured on router.
  - AWP-15312   0.284 [Customer Scenario     ] Tri-Authentication                                      :: Confirm that dot1,MAC,Web authentications is possible.When the cable is removed, the switch doesn't influence the state of authent
  - AWP-27228   0.275 [AWC-lite              ] authentication                                          :: | step1: authentication open-system Confirm that authentication method is configured on router.
  - AWP-5748    0.269 [Port Security (Intrusi] CLI to enable port security                             :: Command line test | step1: int port1.0.23 (no) switchport port-security => Tab can be use to complete the command. The no command 
  - AWP-6322    0.261 [Storm Control         ] multiple loop test                                      :: Device handles multiple loop condition. | step1: Enable loop protection and create multiple loops . => Switch behaves as expected 

### AWPTCM-T44275  |  area: Authentication Security WebAuthentication  |  feature: Proxy Server for Web Authentication
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-19525   0.455 [Web Authentication    ] without proxy setting                                   :: If there is no Proxy set, authentication screen must be displayed | step1: Configure auth-web-server intercept-port any command. =
  - AWP-15360   0.445 [Web Authentication    ] Web Authentication and External DHCP Server             :: Web Authentication and External DHCP Server | step1: Refer to 4.3.2.doc => Refer to 4.3.2.doc
  - AWP-15359   0.425 [Web Authentication    ] Web Authentication and Internal DHCP Server             :: Web Authentication and Internal DHCP Server | step1: Refer to 4.3.1.doc => Refer to 4.3.1.doc
  - AWP-15362   0.361 [Web Authentication    ] Web Authentication and Untagged port                    :: Web Authentication and Untagged port | step1: Refer to 4.6.doc => Refer to 4.6.doc
  - AWP-13758   0.357 [Web Authentication    ] Blocking-mode / Web Authentication and External DHCP Se :: Web Authentication and External DHCP Server | step1: Please refer to the attached document. => Please refer to the attached docume
  - AWP-19526   0.350 [Web Authentication    ] In case of correct proxy setting                        :: When correct proxy setting is used on supplicant, authenticator should be displayed web-auth page. Then, supplicant can authentica
  - AWP-18317   0.349 [Web Authentication    ] show auth-web-server page                               :: show auth-web-server command is operation correctly. | step1: Input "show auth-web-server page" command. => Displayed following in
  - AWP-15361   0.338 [Web Authentication    ] Web Authentication and Tagged port (Other Port)         :: Web Authentication and Tagged port (Other Port) | step1: Refer to 4.5.1.doc => Refer to 4.5.1.doc

### AWPTCM-T44276  |  area: Authentication Security WebAuthentication  |  feature: DHCP Server for Web Authentication
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-15360   0.668 [Web Authentication    ] Web Authentication and External DHCP Server             :: Web Authentication and External DHCP Server | step1: Refer to 4.3.2.doc => Refer to 4.3.2.doc
  - AWP-15359   0.638 [Web Authentication    ] Web Authentication and Internal DHCP Server             :: Web Authentication and Internal DHCP Server | step1: Refer to 4.3.1.doc => Refer to 4.3.1.doc
  - AWP-13758   0.536 [Web Authentication    ] Blocking-mode / Web Authentication and External DHCP Se :: Web Authentication and External DHCP Server | step1: Please refer to the attached document. => Please refer to the attached docume
  - AWP-13757   0.504 [Web Authentication    ] Blocking-mode / Web Authentication and Internal DHCP Se :: Blocking-mode / Web Authentication and Internal DHCP Server | step1: Please refer to the attached document. => Please refer to the
  - AWP-6849    0.474 [Port Authentication   ] Port Authentication and External DHCP Server            :: Port Authentication and External DHCP Server | step1: Refer to 4.2.2.doc => Refer to 4.2.2.doc Confirm the external DHCP server an
  - AWP-6848    0.451 [Port Authentication   ] Port Authentication and Internal DHCP Server            :: Port Authentication and Internal DHCP Server | step1: Refer to 4.2.1.doc => Refer to 4.2.1.doc Confirm the internal DHCP server an
  - AWP-18078   0.449 [Web Authentication    ] DHCP Mode on - authentication via https                 :: Objective: To verify auth-web DHCP behavior with HTTPS authentication Expected Outcome: DHCP should work properly for valid logins
  - AWP-15417   0.447 [Web Authentication    ] CLI Test - auth-web-server dhcp                         :: DHCP Mode | step1: Command handler test: auth-web-server dhcp ipaddress interface-address no auth-web-server dhcp ip address auth-

### AWPTCM-T44277  |  area: Authentication Security  |  feature: Supplicant MAC
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-5762    0.554 [Port Security (Intrusi] enable port authentication                              :: port security ignores supplicant mac addresses | step1: enable port authentication (802.1x), enable port-security on port1.0.1. =>
  - AWP-6751    0.418 [Port Authentication   ] MAC Authentication session logging when Link down MAC-a :: [Note] On 5.4.5-0.x, try this test on interface mode or auth-config mode. Using a MAC Authentication, Link down MAC-authed supplic
  - AWP-6704    0.372 [Port Authentication   ] MAC Authentication Log - no auth log auth-mac failure   :: Confirm that the MAC authenticator log is output correctly. | step1: Specify parameter : failure Command : no auth log auth-mac fa
  - AWP-27197   0.371 [AWC-lite              ] security                                                :: | step1: security <configured security id> Confirm that ID of security for network setting are configured on router.
  - AWP-6705    0.363 [Port Authentication   ] MAC Authentication Log - no auth log auth-mac success   :: Confirm that the MAC authenticator log is output correctly. | step1: Specify parameter : success Command : no auth log auth-mac su
  - AWP-6728    0.357 [Port Authentication   ] MAC Authentication log with VCS - no auth log auth-mac  :: Confirm that the MAC authenticator log is output correctly. | step1: Specify parameter : failure Command : no auth log auth-mac fa
  - AWP-6706    0.356 [Port Authentication   ] MAC Authentication Log - no auth log auth-mac failure l :: Confirm that the MAC authenticator log is output correctly. | step1: Specify parameter : failure and logoff Condition of generatin
  - AWP-6713    0.355 [Port Authentication   ] MAC Authentication Log - Disabled MAC Authentication    :: Confirm that the MAC authenticator log is output correctly. | step1: Disable MAC Authentication Specify parameter : all (default b

### AWPTCM-T44278  |  area: Authentication Security  |  feature: Auto order option
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-27197   0.291 [AWC-lite              ] security                                                :: | step1: security <configured security id> Confirm that ID of security for network setting are configured on router.
  - AWP-27204   0.270 [AWC-lite              ] security                                                :: | step1: security <configured security id> Confirm that ID of security for WDS setting are configured on router.
  - AWP-5712    0.244 [LLDP                  ] Security: Mandatory TLV packet in wrong order           :: Test for the LLDP security after Mandatory TLV packet was received from the switch in wrong order | step1: Configure DUT ena conf 
  - AWP-5762    0.228 [Port Security (Intrusi] enable port authentication                              :: port security ignores supplicant mac addresses | step1: enable port authentication (802.1x), enable port-security on port1.0.1. =>
  - AWP-18386   0.216 [DHCPv6                ] ip dhcp-relay agent-option for new field: subscriber-id :: Confirm new command: ip dhcp-relay agent-option subscriber-id-auto-mac | step1: Issue "ip dhcp-relay agent-option subscriber-id-au
  - AWP-5748    0.207 [Port Security (Intrusi] CLI to enable port security                             :: Command line test | step1: int port1.0.23 (no) switchport port-security => Tab can be use to complete the command. The no command 
  - AWP-25709   0.203 [PIM-SM                ] no debug all                                            :: CLI Test | step1: Ensure that all commands have correct context sensitive help tab auto-complete and check vrf option works correc
  - AWP-13634   0.199 [Bootloader            ] Bootloader - Security Level 1 - Clearing the Password/S :: Check option Security Level 1 if it clears and recovers the switch when the admin password is lost | step1: Reboot the device and 

### AWPTCM-T44279  |  area: Authentication Security  |  feature: Tri-Authentication
folder:/New Platform Template/Authentication & Security  steps:0  obj:True
ZEPHYR: OBJ: Confirm that dot1,MAC authentications is possible. ||
  - AWP-15312   0.606 [Customer Scenario     ] Tri-Authentication                                      :: Confirm that dot1,MAC,Web authentications is possible.When the cable is removed, the switch doesn't influence the state of authent
  - AWP-9611    0.443 [Roaming Authentication] Multi-supplicant, tri-auth, tag                         :: Test multi-supplicant, tri-auth, tag | step1: Multi-Supplicant + Tri-Auth + Tag => Tag +port authentication should work as expecte
  - AWP-6726    0.437 [Port Authentication   ] Tri-Auth Authentication Log                             :: [Note] On 5.4.5-0.x, try this test on interface mode or auth-config mode. Confirm that the tri-auth logs outputs correctly. | step
  - AWP-6750    0.428 [Port Authentication   ] Tri-Auth with VCS- Authentication Log                   :: Confirm that the tri-auth logs outputs correctly. [Note] On 5.4.5-0.x, try this test on interface mode or auth-config mode. | step
  - AWP-6777    0.419 [Port Authentication   ] Tri-Auth with VCS failover - Authentication Log         :: Confirm that the tri-auth logs outputs correctly. [Note] On 5.4.5-0.x, try this test on interface mode or auth-config mode. | step
  - AWP-9613    0.418 [Roaming Authentication] Multi-supplicant, tri-auth, tag, lag                    :: Test multi-supplicant, tri-auth, tag, lag | step1: Multi-Supplicant + Tri-Auth + Tag + LAG => Tag +port authentication should work
  - AWP-9612    0.390 [Roaming Authentication] Multi-supplicant, tri-auth, tag with roaming auth       :: Test multi-supplicant, tri-auth, tag with roaming auth | step1: Multi-Supplicant + Tri-Auth + Tag with Roaming auth => Tag +port a
  - AWP-9614    0.372 [Roaming Authentication] Multi-supplicant, tri-auth , tag, lag with roaming auth :: Test multi-supplicant, tri-auth , tag, lag with roaming auth | step1: Multi-Supplicant + Tri-Auth + Tag + LAG with Roaming auth =>

### AWPTCM-T44280  |  area: Authentication Security  |  feature: Auth fail VLAN
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-6895    0.553 [Port Authentication   ] Auth-fail VLAN - MAC-auth / Auth-fail vlan on / ACL on  :: [Note] On 5.4.5-0.x, try this test on interface mode or auth-config mode. MAC-auth / Auth-fail vlan on / ACL on / | step1: MAC-aut
  - AWP-6893    0.511 [Port Authentication   ] Auth-fail VLAN - MAC-auth / Auth-fail vlan on / ACL off :: [Note] On 5.4.5-0.x, try this test on interface mode or auth-config mode. MAC-auth / Auth-fail vlan on / ACL off / | step1: MAC-au
  - AWP-15416   0.493 [Web Authentication    ] Web-auth / Auth-fail vlan on / ACL off                  :: Auth-fail vlan | step1: Web-auth / Auth-fail vlan on / ACL off / * Meaning of authentication failure : Rejection by RADIUS server.
  - AWP-9305    0.493 [Web Authentication    ] Web-auth / Auth-fail vlan on / ACL on                   :: Auth-fail vlan Auth-fail vlan without VCS (x900 only) | step1: Web-auth Auth-fail vlan on / ACL on Note: Meaning of authentication
  - AWP-9307    0.476 [Web Authentication    ] Web-auth / Auth-fail vlan on / ACL on / guest-vlan on   :: Auth-fail vlan Auth-fail vlan without VCS | step1: Web-auth Auth-fail vlan on / ACL on guest-vlan on Note: Meaning of authenticati
  - AWP-6896    0.476 [Port Authentication   ] Auth-fail VLAN - 802.1X / Auth-fail vlan on / ACL on /  :: [Note] On 5.4.5-0.x, try this test on interface mode or auth-config mode. 802.1X / Auth-fail vlan on / ACL on / | step1: 802.1X / 
  - AWP-6902    0.475 [Port Authentication   ] Auth-fail VLAN with VCS -MAC-auth / Auth-fail vlan on / :: [Note] On 5.4.5-0.x, try this test on interface mode or auth-config mode. MAC-auth / Auth-fail vlan on / ACL on / * Meaning of aut
  - AWP-6897    0.466 [Port Authentication   ] Auth-fail VLAN - MAC+802.1X / Auth-fail vlan on / ACL o :: [Note] On 5.4.5-0.x, try this test on interface mode or auth-config mode. MAC+802.1X / Auth-fail vlan on / ACL on / | step1: MAC+8

### AWPTCM-T44281  |  area: Authentication Security  |  feature: Auth Multi-VLAN-session
folder:/New Platform Template/Authentication & Security  steps:2  obj:True
ZEPHYR: OBJ: ER-2981.1.27 Enabling/disabling multiple-vlan-session of Port Authentication on an interface will be supported. (Note: c || set auth multi-vlan-session | delete auth multi-vlan-session
  - AWP-9533    0.345 [Roaming Authentication] Roaming Auth - Multi-mode, no guest VLAN, per port, no  :: Authentication works with multi-mode, no guest VLAN, per port, no dynamic VLAN | step1: Multi-Mode / no GuestVLAN / per port / no 
  - AWP-9536    0.341 [Roaming Authentication] Roaming Auth - Multi-mode, guest VLAN, per port, dynami :: Authentication works with multi-mode, guest VLAN, per port, dynamic VLAN | step1: Multi-Mode / GuestVLAN / per port / DynamicVLAN 
  - AWP-9501    0.341 [Roaming Authentication] Auth+ LAG Static - Multi-mode, no guest VLAN, per port, :: Test that authentication works with multi-mode, no guest VLAN, per port, no dynamic VLAN | step1: Multi-Mode / no GuestVLAN / per 
  - AWP-9541    0.340 [Roaming Authentication] Roaming Auth - Multi-host, no guest VLAN, per port, no  :: Authentication works with multi-host, no guest VLAN, per port, no dynamic VLAN | step1: Multi-host / no GuestVLAN / per port / no 
  - AWP-9542    0.340 [Roaming Authentication] Roaming Auth - Multi-host, no guest VLAN, per port, dyn :: Authentication works with multi-host, no guest VLAN, per port, dynamic VLAN | step1: Multi-host / no GuestVLAN / per port / Dynami
  - AWP-9543    0.340 [Roaming Authentication] Roaming Auth - Multi-host, guest VLAN, per port, no dyn :: Authentication works with multi-host, guest VLAN, per port, no dynamic VLAN | step1: Multi-host / GuestVLAN / per port / no Dynami
  - AWP-9502    0.339 [Roaming Authentication] Auth+ LAG Static - Multi-mode, no guest VLAN, per port, :: Test that authentication works with multi-mode, no guest VLAN, per port, dynamic VLAN | step1: Multi-Mode / no GuestVLAN / per por
  - AWP-9534    0.338 [Roaming Authentication] Roaming Auth - Multi-mode, no guest VLAN, per port, dyn :: Authentication works with multi-mode, no guest VLAN, per port, dynamic VLAN | step1: Multi-Mode / no GuestVLAN / per port / Dynami

### AWPTCM-T44282  |  area: Authentication Security  |  feature: Auth Profile
folder:/New Platform Template/Authentication & Security  steps:5  obj:True
ZEPHYR: OBJ: This command and mode are creating from 5.4.5-0.x. Confirm that the function works correctly. || After Authentication configuration enables, input following | Input following command, and input "
  - AWP-19434   0.956 [Port Authentication   ] auth profile NAME                                       :: This command and mode are creating from 5.4.5-0.x. Confirm that the function works correctly. | step1: After Authentication config
  - AWP-14773   0.467 [Port Authentication   ] auth two-step enable                                    :: Confirm that "auth two-step enable" command can be configured correctly. | step1: Input "auth two-step enable" on configuration mo
  - AWP-9493    0.357 [Roaming Authentication] Authentication commands                                 :: Test that authentication commands can be executed and works correctly. Also, confirm that auth-profile which is in use cannot be d
  - AWP-15502   0.357 [RADIUS                ] auth radius send vlan-id                                :: Confirm that "auth radius send vlan-id" command can be configured dynamically.and the setting remain after DUT rebooted. | step1: 
  - AWP-6699    0.354 [Port Authentication   ] Show Portauth Command                                   :: Confirm that DUT shows the correct authentication status. (Some CLI are change from 5.4.5-0.x) | step1: Configure DUT for dot1x/ma
  - AWP-15972   0.351 [Port Authentication   ] auth-mac password                                       :: Confirm that "auth-mac password" command can be configured correctly CR00040819 | step1: Input "auth-mac password" on configuratio
  - AWP-18318   0.339 [Web Authentication    ] auth-web-server login-url                               :: auth-web-server login-url (auto/default/hidden) command is configured correctly. Also, all of parameter remain after rebooted. | s
  - AWP-18316   0.336 [Web Authentication    ] auth-web-server page success-message                    :: auth-web-server page success-message (auto/default/hidden) command is configured correctly. Also, all of parameter remain after re

### AWPTCM-T44283  |  area: Authentication Security  |  feature: L3 Mode Enhanced Guest VLAN
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-145     0.439 [Customer Scenario     ] EPSR enhanced recovery mode                             :: Confirm Enhanced Recovery mode works correctly. | step1: Confirm ESPR status. => Enhanced Recovery mode works correctly.
  - AWP-5086    0.424 [Limits                ] IP host (L3) entries (Enhanced Mode Nexthop)            :: Determine max number of ARP entries. | step1: - using static arp to populate the ip host table => - confirm that there is 5060 ip 
  - AWP-15506   0.331 [RADIUS                ] RADIUS packet on Guest VLAN                             :: Confirm that VLAN ID is included in RADIUS packet when authentication port is assigned Guest VLAN. | step1: Execute Authentication
  - AWP-6881    0.316 [Port Authentication   ] Guest VLAN routing mode - MAC-auth / Routing mode on /  :: MAC-auth / Routing mode on / ACL on / | step1: MAC-auth / Routing mode on / ACL on / Guest vlan's behavior is routing mode. 1. Bef
  - AWP-9500    0.315 [Roaming Authentication] Auth+ LAG Static - Single-mode, guest VLAN, per port, d :: Test that authentication works with single-mode, guest VLAN, per port, dynamic VLAN | step1: Single-Mode / GuestVLAN / per port / 
  - AWP-9502    0.315 [Roaming Authentication] Auth+ LAG Static - Multi-mode, no guest VLAN, per port, :: Test that authentication works with multi-mode, no guest VLAN, per port, dynamic VLAN | step1: Multi-Mode / no GuestVLAN / per por
  - AWP-9534    0.314 [Roaming Authentication] Roaming Auth - Multi-mode, no guest VLAN, per port, dyn :: Authentication works with multi-mode, no guest VLAN, per port, dynamic VLAN | step1: Multi-Mode / no GuestVLAN / per port / Dynami
  - AWP-9529    0.314 [Roaming Authentication] Roaming Auth - Single-mode, no guest VLAN, per port, no :: Authentication works correctly with single-mode, no guest VLAN, per port and no dynamic VLAN | step1: Single-Mode / no GuestVLAN /

### AWPTCM-T44284  |  area: Authentication Security SecurityCertificate  |  feature: Common Criteria
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-27197   0.244 [AWC-lite              ] security                                                :: | step1: security <configured security id> Confirm that ID of security for network setting are configured on router.
  - AWP-27204   0.227 [AWC-lite              ] security                                                :: | step1: security <configured security id> Confirm that ID of security for WDS setting are configured on router.
  - AWP-15090   0.219 [Web Control           ] Match criteria based on IPv4 address in URL             :: URL request may pass with an IPv4 address instead of a domain/host name. The different IPv4 based URL requests are able to be filt
  - AWP-15206   0.214 [Web Control           ] Maximum of 50 match criteria are supported              :: User defined Web Control supports a maximum of 50 user defined match criteria. That is: Up to 50 match criteria must be supported.
  - AWP-15265   0.205 [Web Control           ] User can add match criteria to provider categories      :: User defined match criteria can be added to existing provider category names. That is, when the provider's category name (string) 
  - AWP-15205   0.202 [Web Control           ] User Defined match criteria overrides Dynamic categoris :: If the HTTP request's URL matches a user defined match criteria and so gains one or more categories by static categorization, then
  - AWP-7614    0.197 [Policy Based Routing  ] PBR with traffic match criteria                         :: Confirm that PBR is enforced to a particular traffic class when the traffic matches all match criteria | step1: 1.1 Config Hardwar
  - AWP-25214   0.193 [URL Filter            ] URL Filter: HTTPS Requests to blacklisted domains are b :: HTTPS request to a domain that has a matching domain entry in a blacklist are blocked The matching is achieved by extracting the d

### AWPTCM-T44285  |  area: Authentication Security SecurityCertificate  |  feature: FIPS
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-28038   0.359 [JITC Certification    ] V-55153:The network device must use FIPS 140-2 approved :: ---- Warning ---- TestLink Warning test case name is too long (112 chars) > 100 => has been truncated Original name V-55153:The ne
  - AWP-28045   0.304 [JITC Certification    ] V-55167:The network device must generate unique session :: ---- Warning ---- TestLink Warning test case name is too long (120 chars) > 100 => has been truncated Original name V-55167:The ne
  - AWP-28088   0.296 [JITC Certification    ] V-55265:The network devices must use FIPS-validated Key :: ---- Warning ---- TestLink Warning test case name is too long (177 chars) > 100 => has been truncated Original name V-55265:The ne
  - AWP-27859   0.290 [JITC Certification    ] V-3196:The network device must use SNMP Version 3 Secur :: ---- Warning ---- TestLink Warning test case name is too long (148 chars) > 100 => has been truncated Original name V-3196:The net
  - AWP-27919   0.290 [JITC Certification    ] V-3196:The network device must use SNMP Version 3 Secur :: ---- Warning ---- TestLink Warning test case name is too long (148 chars) > 100 => has been truncated Original name V-3196:The net
  - AWP-27197   0.269 [AWC-lite              ] security                                                :: | step1: security <configured security id> Confirm that ID of security for network setting are configured on router.
  - AWP-27851   0.266 [JITC Certification    ] V-3069:Management connections to a network device must  :: ---- Warning ---- TestLink Warning test case name is too long (141 chars) > 100 => has been truncated Original name V-3069:Managem
  - AWP-27910   0.266 [JITC Certification    ] V-3069:Management connections to a network device must  :: ---- Warning ---- TestLink Warning test case name is too long (141 chars) > 100 => has been truncated Original name V-3069:Managem

### AWPTCM-T44286  |  area: Authentication Security SecurityCertificate  |  feature: UC-LAP
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-27197   0.270 [AWC-lite              ] security                                                :: | step1: security <configured security id> Confirm that ID of security for network setting are configured on router.
  - AWP-27204   0.252 [AWC-lite              ] security                                                :: | step1: security <configured security id> Confirm that ID of security for WDS setting are configured on router.
  - AWP-5762    0.212 [Port Security (Intrusi] enable port authentication                              :: port security ignores supplicant mac addresses | step1: enable port authentication (802.1x), enable port-security on port1.0.1. =>
  - AWP-22533   0.209 [ARP                   ] arp-reply-bc-dmac : CLI - Enable / Disable              :: Confirm Enable and Disable behavior works functionally. | step1: 1-1. Enable arp-reply-bc-dmac. 1-2. Perform Ping from DUT to Host
  - AWP-5748    0.192 [Port Security (Intrusi] CLI to enable port security                             :: Command line test | step1: int port1.0.23 (no) switchport port-security => Tab can be use to complete the command. The no command 
  - AWP-5752    0.181 [Port Security (Intrusi] CLI to display port security status on an interface     :: Command line test | step1: show port-security interface port1.0.1 => Displays port security status tab key complete the command "?
  - AWP-5726    0.165 [Port Security (Intrusi] CLI to set maximum port security on an interface        :: Port Secuity | step1: Set Mac address learn limit to 10 interface port1.0.1 switchport port-security switchport port-security maxi
  - AWP-9867    0.164 [DHCP Snooping         ] ARP Security and malformed packets                      :: Confirm that ARP Security is stable | step1: ARP Security and malformed ARP packets => ARP Security is stable

### AWPTCM-T44287  |  area: Authentication Security CyptSecureMode  |  feature: Disable Telnet, SNMPv1/v2, All privilege levels except 1 and 15, Weak cryptographic algorithms e.g. MD5, RSA1, DSA, etc
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-7861    0.305 [User Login            ] User Login - Number of privilege levels available       :: Check number of privilege levels available | step1: - Create Users with different privilege levels - Check number of privilege lev
  - AWP-4652    0.269 [User Login            ] Different users with different privilege levels         :: Create users with different privilege levels | step1: ** Applicable in 5.4.1-1.5 release User <name> privilege <number> password <
  - AWP-4654    0.256 [User Login            ] Perform commands that require higher privilege levels   :: Try and perform commands that are only available to users that have a higher privilege levels | step1: ** Applicable in 5.4.1-1.5 
  - AWP-5828    0.255 [IPv6 Management       ] SSH: RSA1 algorithm                                     :: Test for SSH session using RSA1 algorithm | step1: Configure SSH server using RSA1 algorithm key Connect to DUT-1 via DUT-2 using 
  - AWP-7807    0.243 [User Login            ] User Login - Telnet to device, login with user priv 15  :: Check that users with privilege level 15 can login via Telnet | step1: Add user with privilege level 15 Telnet to device, login wi
  - AWP-6465    0.239 [SSH                   ] Command Line Handler - crypto                           :: Verify valid crypto commands are handled correctly in the DUT. | step1: Command Handler - crypto (including show, no, clear and de
  - AWP-5826    0.226 [IPv6 Management       ] SSH: DSA algorithm                                      :: Test for SSH session using DSA algorithm | step1: Configure SSH server using DSA algorithm key Connect to DUT-1 via DUT-2 using us
  - AWP-7856    0.216 [User Login            ] User Login - Privilege level 15 EXEC commands           :: Verify list of available commands and execute sample on each privilage levels i.e. Level 15 | step1: - User with privilege level 1

### AWPTCM-T44289  |  area: Management EnhancedOperationManagement  |  feature: Findme
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-21920   0.550 [QoS                   ] Findme trigger with VCS                                 :: Test that the findme trigger works as expected on VCS setup. | step1: Set an attachment config file. Start ixia traffic. => Confor
  - AWP-21919   0.465 [QoS                   ] Findme trigger with VCS + LAG                           :: Test that the findme trigger works as expected on VCS and LAG setup. Tests both static and lacp. | step1: Set an attachment config
  - AWP-29490   0.405 [OpenFlow              ] Findme                                                  :: Confirm that Findme works correctly. | step1: Confirm that LED is up on Hybrid OpenFlow port.
  - AWP-24856   0.405 [OpenFlow              ] Findme                                                  :: Confirm that Findme works correctly. | step1: Confirm that LED is up on Hybrid OpenFlow port.
  - AWP-26459   0.405 [OpenFlow              ] Findme                                                  :: Confirm that Findme works correctly. | step1: Confirm that LED is up on Hybrid OpenFlow port.
  - AWP-9681    0.391 [Find Me               ] Find Me - Functional - stop timer with no findme comman :: Find Me - using blinking port LEDs to find devices. | step1: Start findme command, then stop with no findme before normal timeout.
  - AWP-21916   0.356 [QoS                   ] Priority of LED flashing                                :: When the ATMF-Recover and the Findme-trigger is running , high priority of led flashing is ATMF-Recover. DUT is ATMF members. | st
  - AWP-17847   0.353 [ATMF                  ] ATMF LED indication prevails over FindMe                :: ATMF progress LED indication feature should always prevail over Findme 1. If Findme happens before ATMF recovery, it will be overr

### AWPTCM-T44290  |  area: Management EnhancedOperationManagement  |  feature: In Service Software Upgrade
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-27126   0.317 [PoE                   ] Verify impact to feature on IE300 software upgrade      :: Verify impact of an IE upgrade to 60W SSO 4-wire configured devices | step1: Connect Bosch camera to provisioned 4-wire single-sig
  - AWP-14229   0.303 [ISSU                  ] ISSU - Upgrade                                          :: S1716.1.10 ISSU must allow the release to be upgraded to a newer supported version of SW 1 Note: A software release may not be sup
  - AWP-27253   0.294 [AWC-lite              ] 7.3.4 Delete task of upgrade AP firmware                :: | step1: Confirm that user can delete task to upgrade firmware of AP.
  - AWP-29738   0.250 [5.4.8-2 Development   ] TQm5403 : FW Upgrade / Downgrade                        :: Confirm TQm5403 FW upgrade and downgrade will be performed correctly | step1: APs firmware upgrade from v5.1.1 to v5.1.2 => Firmwa
  - AWP-26074   0.243 [G.8032                ] Upgrade - EPSR Interconnect                             :: Verify that when the DUT is upgraded that the EPSR with a G.8032 C-Ring Interconnected recovers. | step1: Upgrade cycle a intercon
  - AWP-27249   0.233 [AWC-lite              ] 7.2.4 Edit task of upgrade AP firmware                  :: | step1: Confirm that user can edit the contents of task to upgrade firmware of AP.
  - AWP-24838   0.233 [OpenFlow              ] License -Upgrade F/W with Feature license-              :: Upgrade Firmware to 5.4.7 with Feature license, license and openflow configurations are disabled on 5.4.7. | step1: Upgrade DUT's 
  - AWP-24867   0.233 [OpenFlow              ] License -Upgrade F/W with Feature license-              :: Upgrade Firmware to 5.4.7 with Feature license, license and openflow configurations are disabled on 5.4.7. | step1: Upgrade DUT's 

### AWPTCM-T44291  |  area: Management ManagingConfigurationFilesAndSoftwareVersions  |  feature: Loading Files using HTTP
folder:/New Platform Template/Management  steps:1  obj:True
ZEPHYR: OBJ: Copying with Hypertext Transfer Protocol (HTTP) You device has a built-in HTTP client. The HTTP client enables the devic || Copying with Hypertext Transfer Protocol (HTTP) http:// [[<u
  - AWP-5835    0.275 [IPv6 Management       ] TFTP: ipv6 TFTP Client to TFTP Server                   :: Test for successful file transfer using TFTP from Client to server | step1: Copy From TFTP Client to TFTP Server STEPS: 1. Configu
  - AWP-2450    0.254 [z_Inactive            ] File - copy using http                                  :: File - copy using http | step1: Setup details: TB2 conf - Place a file (filea) to be copied in /var/www Start the http server proc
  - AWP-5478    0.253 [TFTP                  ] TFTP upload                                             :: [version 3] Edited a step because corresponding to CR41795 issue. | step1: TFTP uploads using menu (prompts): Start capture on Cli
  - AWP-6532    0.232 [SSH                   ] SCP - destination file not subject to directory tranver :: SCP Server Tests Test that SCP destination files are not subject to directory tranversal (using ../.. etc) | step1: * On DUT, crea
  - AWP-6541    0.225 [SSH                   ] SFTP - destination file not subject to directory tranve :: SFTP Server Tests Test that SFTP destination files are not subject to directory tranversal (using ../.. etc) | step1: * On DUT, cr
  - AWP-6645    0.225 [VLAN                  ] Copy running config to file.cfg                         :: VLAN packet counter configuration can be saved to file.cfg | step1: Command Handler: "enable" CLI level copy running config <file.
  - AWP-5834    0.224 [IPv6 Management       ] TFTP: ipv6 TFTP Server to TFTP Client                   :: Test for successful file transfer using TFTP from ipv6 Server to ipv6 Client | step1: Copy file from TFTP Server to TFTP Client ST
  - AWP-17679   0.215 [File System           ] File - command copy - copy to special files             :: File - command copy - copy to special files This specification is applicable from 5.4.3. 5.4.2 or before, "copy [src filename] sta

### AWPTCM-T44292  |  area: Management IEEE 1588v2PTP  |  feature: Peer-to-Peer Transparent Clock
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-24455   0.282 [Port Mirroring        ] Transparent bridging - ATMF management                  :: Ensure that the acquire command is configurable via ATMF | step1: Use the "acquire" command on the bridge interface on DUT1 via an
  - AWP-24311   0.259 [Port Mirroring        ] Transparent bridging - bridge filtering                 :: Determine the interop behaviour when mac-address filtering is configured. | step1: add mac-filter to the bridge => All traffic sho
  - AWP-24454   0.250 [Port Mirroring        ] Transparent bridging - IPv6                             :: Ensure that IPv6 L2TPv3 tunnels can be used in bridges. Ensure that ipv4 and IPv6 unicast and multicast traffic can pass over the 
  - AWP-24305   0.248 [Port Mirroring        ] Transparent bridging - triggers                         :: Ensure that this feature can be configured and reconfigured using trigger scripts | step1: Configure a trigger which implements th
  - AWP-24570   0.245 [Port Mirroring        ] Transparent bridging - Destination mac of router        :: Ensure traffic with the destination mac of the router can be bridged | step1: Set traffic from IXIA1 with a destination mac-addres
  - AWP-24319   0.243 [Port Mirroring        ] Transparent bridging - multiple interfaces              :: Identify behaviour when there are more than just two interfaces in the bridge as well as over multiple different interface types |
  - AWP-24294   0.240 [Port Mirroring        ] Transparent bridging - dynamic reconfiguration          :: Ensure that this feature can be dynamically reconfigured | step1: Use the "acquire" command on the bridge interface => mac address
  - AWP-24327   0.228 [Port Mirroring        ] Transparent bridging - VRF                              :: Determine behaviour when interoperating with a VRF instance. | step1: Add each of the bridges to a VRF instance => packet streams 

### AWPTCM-T44295  |  area: Management IEEE 1588v2PTP  |  feature: Boundary Clock
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-9635    0.491 [xSTP                  ] Confirm Region Boundary Bridge                          :: | step1: Confirm Region Boundary Bridge
  - AWP-564     0.371 [Triggers              ] Boundary Conditions                                     :: Tests for basic trigger CLI commands | step1: Create triggers with ID's 0 and 251 => Rejected: "% Invalid input detected at '^' ma
  - AWP-6434    0.214 [L2 Switching (L2 Learn] Dribble bit ATKK 5.1.5.4                                :: Frames with valid FCS that do not end on octet boundary. Should be corrected & forwarded (RFC 2889) | step1: Dribble bit ATKK 5.1.
  - AWP-9888    0.202 [DHCP Snooping         ] DHCP Snooping - NTP and clock changes                   :: Check if correct behavior was shown | step1: NTP and clock changes. Effects on lease times post startup when clock is set by NTP. 
  - AWP-24537   0.196 [ATMF                  ] clock set inside containers is not supported            :: The clock set command will not be supported inside containers. Containers will be fixed to the clock of the hosting VAA | step1: c
  - AWP-24538   0.186 [ATMF                  ] NTP will not update the clock inside container          :: NTP will not update the clock inside container | step1: ensure NTP will not update the clock inside the container => Confirm NTP w
  - AWP-4396    0.179 [ARP                   ] ARP Log: Command                                        :: CLI test for arp log command - including mac-address-format | step1: Check "arp log" command (w/ or w/o parameters) Use "no arp lo
  - AWP-15080   0.179 [Platform              ] Negative tests for CLI                                  :: Commands that refer to cards 1.7-1.12 should be rejected. | step1: Issue the following, where x is cards 7,12 and 13 (boundary tes

### AWPTCM-T44296  |  area: Management LLDP  |  feature: LLDP
folder:/New Platform Template/Management  steps:0  obj:True
ZEPHYR: OBJ: Confirm that DUT collects information of the neighbor by LLDP. And the information is correctly updated. (show lldp neig ||
  - AWP-5547    0.547 [LLDP                  ] Enabled LLDP on a port to receive only                  :: Test for LLDP enabled on a port configured to received only. | step1: --> Enable LLDP on a port to receive only. --> Connect a val
  - AWP-5548    0.530 [LLDP                  ] Enabled LLDP on a port to transmit only                 :: Test for LLDP enabled on a port configured to transmit only. | step1: --> Enable LLDP on a port to transmit only. --> Connect a va
  - AWP-5515    0.499 [LLDP                  ] Command Line Handler: show lldp interface               :: Test for show lldp interface command | step1: Command Handler: show lldp interface [if-range] => Should display the LLDP config an
  - AWP-5511    0.475 [LLDP                  ] Command Line Handler: lldp management address           :: Test for lldp management address command | step1: Command Handler: --> lldp management address [ip address] --> no lldp management
  - AWP-5504    0.460 [LLDP                  ] Command Line Handler: lldp receive                      :: Test for lldp receive command configured in port(s). | step1: Command Handler: --> lldp receive (conf t, int portx.y.z, lldp recei
  - AWP-5512    0.456 [LLDP                  ] Command Line Handler: show lldp                         :: Test for show lldp command | step1: Command Handler: --> show lldp --> show lldp interface [if-range] => --> show lldp - Should di
  - AWP-5509    0.454 [LLDP                  ] Command Line Handler: lldp transmit                     :: Test for lldp transmit command confiigured in port(s). | step1: Command Handler: --> lldp transmit --> no lldp transmit => --> lld
  - AWP-5506    0.450 [LLDP                  ] Command Line Handler: lldp run                          :: Test for lldp run command | step1: Command Handler: --> lldp run --> no lldp run => --> lldp run - The lldp operation will be enab

### AWPTCM-T44297  |  area: Management LLDP  |  feature: LLDP-TLV
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-5558    0.675 [LLDP                  ] LLDP on port based VLAN with LLDP TLV's configured      :: Test for port based VLAN with LLDP TLV's configured | step1: Configure a port based vlan and enable all of the LLDP TLV's to trans
  - AWP-5551    0.644 [LLDP                  ] LLDP TLV - test all TLV options available               :: Configure several ports, test all different lldp TLV-select options | step1: Enable LLDP to transmit only on several ports. On eac
  - AWP-5723    0.569 [LLDP                  ] LLDP-MED Security:Reserved LLDP-MED TLV                 :: Test for LLDP-MED security after sending a resevered LLDP-MED TLV | step1: Transmit a reserved LLDP-MED TLV [12-255] => The Unknow
  - AWP-5705    0.562 [LLDP                  ] LLDP after XEM Hotswap with management address configur :: Test for the LLDP operation after an XEM Hotswap with management address configured | step1: -->> Enable LLDP on switch -->> Confi
  - AWP-5711    0.558 [LLDP                  ] Security: Unknown TLV packet                            :: Test for the LLDP security after Unknown TLV packet was received from the switch | step1: Configure DUT ena conf t lldp run int po
  - AWP-5557    0.544 [LLDP                  ] LLDP on tagged port to several VLANs with LLDP TLV's co :: Test for tagged port to several VLANs with LLDP TLV's configured | step1: Configure a tagged port with several vlans and enable al
  - AWP-5508    0.524 [LLDP                  ] Command Line Handler: lldp tlv-select                   :: Test for lldp tlv-select command configured in port(s). | step1: Command Handler: --> lldp tlv-select [options] --> no lldp tlv-se
  - AWP-5610    0.520 [LLDP                  ] LLDP-MED:dot1 TLV enabled                               :: Test for LLDP-MED frames when dot1 TLV is enabled to transmit on a port. | step1: Enable the dot1 TLV's to transmit on a port. Cha

### AWPTCM-T44298  |  area: Management NTP  |  feature: IPv6 NTP Server
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-27159   0.636 [AWC-lite              ] NTP server                                              :: | step1: ip <correct ip address> Confirm that data of NTP server is configured on router.
  - AWP-19385   0.577 [z_ATKK_Inquiry_Based  ] NTP Server                                              :: Scope Confirm that ntp server feature. | step1: Confirm that ntp server feature. ntp packets is sent to registere address, when nt
  - AWP-1118    0.568 [NTP                   ] NTP - AW+ as an NTP server for other device types       :: NTP - Test that AW+ can act as an NTP server for other device types such as a PC | step1: Configure DUT to be NTP server set pc to
  - AWP-1128    0.544 [NTP                   ] NTP - Check NTP packet format                           :: NTP - Check NTP packet format | step1: Capture NTP packets during time sync, refer to RFC and ensure correct. => Packets have corr
  - AWP-1108    0.509 [NTP                   ] NTP - Device can sync time with a windows pc as a ntp s :: NTP - Device can sync time with a window pc as a ntp server | step1: Configure windows pc as a ntp time server Issue sh ntp status
  - AWP-11529   0.507 [NTP                   ] NTP over IPv6 - Operating as an NTP server.             :: NTP will respond to any NTP packets (unless the ingress packets are blocked by other processes - i.e. clasifiers) NTP will respond
  - AWP-10940   0.507 [NTP                   ] NTP over IPv6 - CLI - Configuration                     :: NTP - CLI - Help operation and detail Ensure IPv6 addresses are accepted for server and peer commands | step1: Configure an NTP IP
  - AWP-12422   0.505 [NTP                   ] NTP - Test for ntp source command                       :: NTP source command specify a preferred source interface for NTP requests. | step1: Configure DUT with ntp source command => NTP de

### AWPTCM-T44299  |  area: Management NTP  |  feature: IPv6 NTP Client
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-12422   0.539 [NTP                   ] NTP - Test for ntp source command                       :: NTP source command specify a preferred source interface for NTP requests. | step1: Configure DUT with ntp source command => NTP de
  - AWP-1128    0.533 [NTP                   ] NTP - Check NTP packet format                           :: NTP - Check NTP packet format | step1: Capture NTP packets during time sync, refer to RFC and ensure correct. => Packets have corr
  - AWP-27159   0.511 [AWC-lite              ] NTP server                                              :: | step1: ip <correct ip address> Confirm that data of NTP server is configured on router.
  - AWP-11529   0.480 [NTP                   ] NTP over IPv6 - Operating as an NTP server.             :: NTP will respond to any NTP packets (unless the ingress packets are blocked by other processes - i.e. clasifiers) NTP will respond
  - AWP-1118    0.472 [NTP                   ] NTP - AW+ as an NTP server for other device types       :: NTP - Test that AW+ can act as an NTP server for other device types such as a PC | step1: Configure DUT to be NTP server set pc to
  - AWP-19385   0.472 [z_ATKK_Inquiry_Based  ] NTP Server                                              :: Scope Confirm that ntp server feature. | step1: Confirm that ntp server feature. ntp packets is sent to registere address, when nt
  - AWP-15944   0.468 [IPv4                  ] NTP operation in "no ip forwarding"                     :: Confirm that NTP works correctly when "no ip forwarding" in configured. | step1: PC1 send NTP request packet. => DUT send NTP pack
  - AWP-12423   0.461 [NTP                   ] NTP - Command Line Handler: ntp source command          :: Test for ntp source command. | step1: Command Handler: 1. Issue ntp source <ip address> command. 2. Issue no ntp source command =>

### AWPTCM-T44300  |  area: Management Operation  |  feature: Hostname
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-5840    0.443 [IPv6 Management       ] DNS Client: Ping DNS hostname                           :: Test for ping command using DNS hostname assigned to the DUT-1 and DUT-2 | step1: Ping DUT-1 and DUT-2 using DNS hostname Note: Yo
  - AWP-24260   0.403 [ATMF                  ] Change the hostname                                     :: Change the hostname on the container, on the vaa, or on the physical devices | step1: change the hostname on the container => expe
  - AWP-2305    0.396 [Telnet                ] Telnet - Functional - hostname                          :: Basic test of Telnet | step1: Telnet from DUT to another device. Execute the following commands in User Exec and Privileged Exec m
  - AWP-5841    0.386 [IPv6 Management       ] DNS Client: Traceroute DNS hostname                     :: Test for traceroute command using the DNS hostname assigned to the DUT-1 and DUT-2 | step1: Traceroute DUT-1 and DUt-2 using DNS h
  - AWP-4452    0.356 [Command Shell         ] CLI - changing hostname                                 :: Check that hostname is reflected once changed and even after reboot/failover | step1: Change device hostname - letters only - digi
  - AWP-3821    0.337 [IPv4                  ] CLI-Interface Configuration-description                 :: CLI-Interface Configuration-description Description configuration for loopback interface -----------------------------------------
  - AWP-2327    0.312 [Telnet                ] Telnet - Functional - telnet with DNS hostname          :: Test telnet using a hostname instead of an ip adress as the destination. | step1: Setup and configure test box to be a DNS server.
  - AWP-22384   0.311 [ATMF                  ] test the network with hostname changes                  :: Change the host name on different atmf devices including atmf controller/master, edge, and guest nodes | step1: chaneg the hostnam

### AWPTCM-T44301  |  area: Management Trap  |  feature: Per-port link trap
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-6850    0.457 [Port Authentication   ] Port Authentication and SNMP Trap                       :: Port Authentication and SNMP Trap | step1: Refer to 4.3.doc => Refer to 4.3.doc Confirm that the switch sends SNMP trap message to
  - AWP-8352    0.375 [z_Inactive            ] SNMP trap is sent when a port goes down                 :: A SNMP trap is sent when a port is down | step1: Configure SNMP on DUT snmp-server community public snmp-server host 10.20.10.10 p
  - AWP-8353    0.355 [z_Inactive            ] SNMP trap is sent when a port goes into up state        :: A SNMP trap is sent when a port goes into the up state | step1: Configure SNMP on DUT snmp-server community public snmp-server hos
  - AWP-13597   0.334 [SNMP                  ] CR00034650 SNMP link/up down status trap delay          :: SNMP link/up down status trap delay | step1: Setup sending link status traps to server Set the delay snmp trap link-status trap-de
  - AWP-5745    0.321 [Port Security (Intrusi] intrusion action - trap                                 :: Intrusion action | step1: INTRUSION is set to Trap(restrict), Transmit stream 1.9.1_ix_1.str => Trap should be sent to SNMP manage
  - AWP-10501   0.307 [UDLD                  ] UDLD SNMP traps for Port Recovery                       :: Test that the device sends SNMP trap when the unidirectional port recovers from port down | step1: 1. Configure SNMP on the device
  - AWP-9819    0.307 [DHCP Snooping         ] DHCP Snooping Violation trap                            :: Confirm trap is transmitted when violation occurs | step1: DHCP Snooping Violation - trap => trap transmitted when violation occur
  - AWP-6326    0.307 [Storm Control         ] snmp trap test                                          :: Trap is sent to the SNMP Manager when loop is detected | step1: Enable SNMP trap in the switch and create loops between ports. => 

### AWPTCM-T44302  |  area: Management Triggers  |  feature: Stack Disable Master
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-10036   0.443 [ICMP                  ] Disable VMAC                                            :: Confirm that stack correctly used Master MAC on reboot | step1: Disable virtual-MAC. Check that stack correctly uses Master MAC on
  - AWP-9389    0.430 [xSTP                  ] Disable virtual-MAC, check that stack correctly uses Ma :: | step1: Disable virtual-MAC. Check that stack correctly uses Master MAC on reboot - Check ports on members including master => Co
  - AWP-8331    0.430 [IPv4                  ] Disable virtual-MAC.                                    :: Check that stack correctly uses Master MAC on reboot | step1: Disable virtual-MAC. Check that stack correctly uses Master MAC on r
  - AWP-10135   0.416 [IPv6                  ] Disable VMAC                                            :: Config successfully saved to all stack members and uses master MAC on reboot | step1: Disable virtual-MAC. Check that stack correc
  - AWP-6615    0.388 [RIP                   ] Operational: Running VMAC Disable and Reboot            :: Check that stack correctly uses Master MAC on reboot | step1: Disable virtual-MAC. Check that stack correctly uses Master MAC on r
  - AWP-627     0.385 [Triggers              ] Stack (VCS) Trigger on master fail                      :: Test for VCS triggers | step1: Configure the trigger to be activated when the master-fail occurs => Trigger activated
  - AWP-633     0.383 [Triggers              ] Stack (VCS) Trigger on disabled master - Simultaneously :: Test for VCS triggers | step1: Have 2 disabled master triggers to run simultaneously => Trigger activates when device becomes disa
  - AWP-24179   0.379 [ATMF                  ] Check Triggers will be supported                        :: Check Triggers will be supported | step1: check triggers will be supported => confirm triggers is supported

### AWPTCM-T44303  |  area: Management Triggers  |  feature: Stack Master Fault
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-627     0.338 [Triggers              ] Stack (VCS) Trigger on master fail                      :: Test for VCS triggers | step1: Configure the trigger to be activated when the master-fail occurs => Trigger activated
  - AWP-633     0.336 [Triggers              ] Stack (VCS) Trigger on disabled master - Simultaneously :: Test for VCS triggers | step1: Have 2 disabled master triggers to run simultaneously => Trigger activates when device becomes disa
  - AWP-24179   0.332 [ATMF                  ] Check Triggers will be supported                        :: Check Triggers will be supported | step1: check triggers will be supported => confirm triggers is supported
  - AWP-11636   0.316 [Environment Monitoring] System LED - no environment fault conditions            :: To check if fault LED is unlit when there is no environment fault conditions | step1: System normal with no environment fault cond
  - AWP-10431   0.316 [z_Inactive            ] System LED - no environment fault conditions            :: To check if fault LED is unlit when there is no environment fault conditions | step1: System normal with no environment fault cond
  - AWP-632     0.312 [Triggers              ] Stack (VCS) Trigger on disabled master - Status Pending :: Test for VCS triggers | step1: Fail over 2 members, ensure no triggers are activated whilst it status is pending => No triggers ac
  - AWP-630     0.311 [Triggers              ] Stack (VCS) Trigger on disabled master - device leaving :: Test for VCS triggers | step1: With triggers configured to run a script, ensure when a device leaves the stack that device does no
  - AWP-638     0.310 [Triggers              ] Trigger Stress Test multiple stack triggers             :: Trigger stress test | step1: Activate multiple triggers simultaneously (type=stack) => The DUT must work without any memory leak o
