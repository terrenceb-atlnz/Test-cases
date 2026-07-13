# Rerank batch 02  (cases 60..89)

### AWPTCM-T33357  |  area: Authentication Security IEEE 802.1XEncryptionType  |  feature: EAP-TLS
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-5398    0.477 [RADIUS                ] Local Radius behavior of EAP-TLS authentication Dot1x   :: Confirm that a client can be authenticated with EAP-TLS, and this client should be moved to the group’s vlan by dynamic vlan. | st
  - AWP-5418    0.433 [RADIUS                ] Local Radius & VCS / Dot1x Auth / EAP-TLS               :: Behavior of EAP-TLS authentication: Confirm that a client can be authenticated with EAP-MD5, and this client should be moved to th
  - AWP-5405    0.405 [RADIUS                ] Local Radius dot1x(EAP-TLS), WEB(EAP-MD5), MAC(EAP-MD5) :: Confirm that a client can be authenticated with dot1X(EAP-TLS) and WEB(EAP-MD5), MAC(EAP-MD5), and this client should be moved to 
  - AWP-5443    0.394 [RADIUS                ] Local Radius & VCS / Tri-Auth / EAP-MD5                 :: Confirm that a client can be authenticated with dot1X(EAP-TLS) and WEB(EAP-MD5), MAC(EAP-MD5), and this client should be moved to 
  - AWP-6786    0.379 [Port Authentication   ] Authentication message exchange                         :: Confirm that an authenticator exchanges authentication messages between the supplicant and Radius server. | step1: 1. Configure DU
  - AWP-5422    0.368 [RADIUS                ] Local Radius & VCS / Dot1x Auth / EAP-TLS / Backup Memb :: Confirm that a client can be authenticated with EAP-MD5, and this client should be moved to the group’s vlan by dynamic vlan. | st
  - AWP-5420    0.368 [RADIUS                ] Local Radius & VCS / Dot1x Auth / EAP-TLS / Static LAG  :: Confirm that a client can be authenticated with EAP-MD5, and this client should be moved to the group’s vlan by dynamic vlan. | st
  - AWP-5423    0.366 [RADIUS                ] Local Radius & VCS / Dot1x Auth / EAP-TLS / Backup Memb :: Confirm that a client can be authenticated with EAP-MD5, and this client should be moved to the group’s vlan by dynamic vlan. | st

### AWPTCM-T33358  |  area: Authentication Security IEEE 802.1XEncryptionType  |  feature: EAP-TTLS
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-6778    0.387 [Port Authentication   ] EAP Forwarding Tests                                    :: [Note] On 5.4.5-0.x, try this test on interface mode or auth-config mode. Verify switch action when EAP forwarding is enabled or d
  - AWP-142     0.382 [Customer Scenario     ] EAP support                                             :: Confirm that dot1authentications is possible. (all kinds of eap supported on AW+) | step1: Do dot1 authentication on each eap type
  - AWP-6786    0.353 [Port Authentication   ] Authentication message exchange                         :: Confirm that an authenticator exchanges authentication messages between the supplicant and Radius server. | step1: 1. Configure DU
  - AWP-5435    0.324 [RADIUS                ] Local Radius & VCS / Web Auth / EAP-MD5                 :: Behavior of EAP-MD5 Authentication: Confirm that a client can be authenticated through Web Authentication using EAP-MD5 Challenge 
  - AWP-6787    0.315 [Port Authentication   ] Packet Format on Authenticator port                     :: Confirm the Packet format that the protocol used for port-based access control is the IETF standard Extensible Authentication Prot
  - AWP-5396    0.314 [RADIUS                ] Local Radius behavior of EAP-MD5 authentication Dot1x   :: Confirm that a client can be authenticated with EAP-MD5, and this client should be moved to the group’s vlan by dynamic vlan. | st
  - AWP-5410    0.311 [RADIUS                ] Local Radius & VCS / Dot1x Auth / EAP-MD5               :: Dot1X authentication by EAP-MD5: Confirm that a client can be authenticated with EAP-MD5, and this client should be moved to the g
  - AWP-5398    0.310 [RADIUS                ] Local Radius behavior of EAP-TLS authentication Dot1x   :: Confirm that a client can be authenticated with EAP-TLS, and this client should be moved to the group’s vlan by dynamic vlan. | st

### AWPTCM-T33359  |  area: Authentication Security IEEE 802.1XEncryptionType  |  feature: EAP-PEAP
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-5397    0.564 [RADIUS                ] Local Radius behavior of EAP-PEAP authentication Dot1x  :: Confirm that a client can be authenticated with EAP-PEAP(PEAP-TLS, MSCHAP v2), and this client should be moved to the group’s vlan
  - AWP-5404    0.484 [RADIUS                ] Local Radius dot1x(EAP-PEAP), WEB(EAP-MD5), MAC(EAP-MD5 :: Confirm that a client can be authenticated with dot1X(EAP-PEAP) and WEB(EAP-MD5), MAC(EAP-MD5), and this client should be moved to
  - AWP-6786    0.408 [Port Authentication   ] Authentication message exchange                         :: Confirm that an authenticator exchanges authentication messages between the supplicant and Radius server. | step1: 1. Configure DU
  - AWP-6787    0.365 [Port Authentication   ] Packet Format on Authenticator port                     :: Confirm the Packet format that the protocol used for port-based access control is the IETF standard Extensible Authentication Prot
  - AWP-6778    0.283 [Port Authentication   ] EAP Forwarding Tests                                    :: [Note] On 5.4.5-0.x, try this test on interface mode or auth-config mode. Verify switch action when EAP forwarding is enabled or d
  - AWP-142     0.279 [Customer Scenario     ] EAP support                                             :: Confirm that dot1authentications is possible. (all kinds of eap supported on AW+) | step1: Do dot1 authentication on each eap type
  - AWP-5469    0.278 [RADIUS                ] AW+ Radius Server PEAP Testing                          :: Please see attached file "3.1.x_CR28184-Test-procedures.doc" for Network Setup and configurations The AW+ RADIUS server has now be
  - AWP-5435    0.237 [RADIUS                ] Local Radius & VCS / Web Auth / EAP-MD5                 :: Behavior of EAP-MD5 Authentication: Confirm that a client can be authenticated through Web Authentication using EAP-MD5 Challenge 

### AWPTCM-T33360  |  area: Authentication Security IEEE 802.1XEncryptionType  |  feature: Multiple Authentication
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-5762    0.337 [Port Security (Intrusi] enable port authentication                              :: port security ignores supplicant mac addresses | step1: enable port authentication (802.1x), enable port-security on port1.0.1. =>
  - AWP-6858    0.294 [Port Authentication   ] 802.1x Authentication and MAC based Authentication      :: Confirm that the 802.1x port authentication and MAC based authentication operate correctly at the same time. | step1: Refer to 4.8
  - AWP-27197   0.277 [AWC-lite              ] security                                                :: | step1: security <configured security id> Confirm that ID of security for network setting are configured on router.
  - AWP-28452   0.269 [Port Authentication   ] single-supplicant mode with multiple VLAN and re-authen :: Confirm re-authentication works correctly without deleting FDB. | step1: After authed, confirm re-authentication start => FDB shou
  - AWP-6724    0.262 [Port Authentication   ] 802.1X Authentication Log - Disabled dot1x Authenticati :: Confirm that the dot1x authenticator log outputs correctly. | step1: Disable dot1x Authentication Specify parameter : all (default
  - AWP-27204   0.258 [AWC-lite              ] security                                                :: | step1: security <configured security id> Confirm that ID of security for WDS setting are configured on router.
  - AWP-6748    0.253 [Port Authentication   ] 802.1X Authentication Log with VCS - Disabled dot1x Aut :: Confirm that the dot1x authenticator log outputs correctly. | step1: Disable dot1x Authentication Specify parameter : all (default
  - AWP-6775    0.245 [Port Authentication   ] 802.1X Authentication Log with VCS failover - Disabled  :: Confirm that the dot1x authenticator log outputs correctly. | step1: Disable dot1x Authentication Specify parameter : all (default

### AWPTCM-T33361  |  area: Authentication Security IEEE 802.1XEncryptionType  |  feature: MAC Auth fail log
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-6711    0.506 [Port Authentication   ] MAC Authentication Log - no auth log auth-mac all       :: Confirm that the MAC authenticator log is output correctly. | step1: Specify parameter : all Command : no auth log auth-mac all =>
  - AWP-6712    0.505 [Port Authentication   ] MAC Authentication Log - auth log auth-mac all          :: Confirm that the MAC authenticator log is output correctly. | step1: Specify parameter : all (default behavior) Command : auth log
  - AWP-6735    0.481 [Port Authentication   ] MAC Authentication log with VCS - no auth log auth-mac  :: Confirm that the MAC authenticator log is output correctly. | step1: Specify parameter : all Command : no auth log auth-mac all =>
  - AWP-6736    0.480 [Port Authentication   ] MAC Authentication log with VCS - auth log auth-mac all :: Confirm that the MAC authenticator log is output correctly. | step1: Specify parameter : all (default behavior) Command : auth log
  - AWP-6762    0.458 [Port Authentication   ] MAC Authentication Log with VCS failover - no auth log  :: Confirm that the MAC authenticator log is output correctly. | step1: Specify parameter : all Command : no auth log auth-mac all =>
  - AWP-6763    0.457 [Port Authentication   ] MAC Authentication Log with VCS failover - auth log aut :: Confirm that the MAC authenticator log is output correctly. | step1: Specify parameter : all (default behavior) Command : auth log
  - AWP-6704    0.452 [Port Authentication   ] MAC Authentication Log - no auth log auth-mac failure   :: Confirm that the MAC authenticator log is output correctly. | step1: Specify parameter : failure Command : no auth log auth-mac fa
  - AWP-6897    0.451 [Port Authentication   ] Auth-fail VLAN - MAC+802.1X / Auth-fail vlan on / ACL o :: [Note] On 5.4.5-0.x, try this test on interface mode or auth-config mode. MAC+802.1X / Auth-fail vlan on / ACL on / | step1: MAC+8

### AWPTCM-T33362  |  area: Authentication Security DynamicVlan  |  feature: Multiple Dynamic VLAN
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-6817    0.391 [Port Authentication   ] Combination Tests (MAC authentication) - Multi-Supplica :: Confirm the combination of port mode, Multiple Dynamic VLAN and Multiple Guest VLAN with MAC authentication. [Note] On 5.4.5-0.x, 
  - AWP-6816    0.360 [Port Authentication   ] Combination Test (802.1X authentication) - Multi-Suppli :: Parameter : auth dynamic-vlan-creation [rule {deny|permit}] [type {multi|single}] The command below is not supported on marvell (x
  - AWP-9502    0.337 [Roaming Authentication] Auth+ LAG Static - Multi-mode, no guest VLAN, per port, :: Test that authentication works with multi-mode, no guest VLAN, per port, dynamic VLAN | step1: Multi-Mode / no GuestVLAN / per por
  - AWP-15312   0.336 [Customer Scenario     ] Tri-Authentication                                      :: Confirm that dot1,MAC,Web authentications is possible.When the cable is removed, the switch doesn't influence the state of authent
  - AWP-9534    0.336 [Roaming Authentication] Roaming Auth - Multi-mode, no guest VLAN, per port, dyn :: Authentication works with multi-mode, no guest VLAN, per port, dynamic VLAN | step1: Multi-Mode / no GuestVLAN / per port / Dynami
  - AWP-9500    0.332 [Roaming Authentication] Auth+ LAG Static - Single-mode, guest VLAN, per port, d :: Test that authentication works with single-mode, guest VLAN, per port, dynamic VLAN | step1: Single-Mode / GuestVLAN / per port / 
  - AWP-9504    0.330 [Roaming Authentication] Auth+ LAG Static - Multi-mode, guest VLAN, per port, dy :: Test that authentication works with multi-mode, guest VLAN, per port, dynamic VLAN | step1: Multi-Mode / GuestVLAN / per port / Dy
  - AWP-9499    0.329 [Roaming Authentication] Auth+ LAG Static - Single-mode, guest VLAN, per port, n :: Test that authentication works with single-mode, guest VLAN, per port, dynamic VLAN | step1: Single-Mode / GuestVLAN / per port / 

### AWPTCM-T33363  |  area: Authentication Security DynamicVlan  |  feature: Single Dynamic VLAN
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-9529    0.506 [Roaming Authentication] Roaming Auth - Single-mode, no guest VLAN, per port, no :: Authentication works correctly with single-mode, no guest VLAN, per port and no dynamic VLAN | step1: Single-Mode / no GuestVLAN /
  - AWP-9497    0.500 [Roaming Authentication] Auth+ LAG Static - Single-mode, no guest VLAN, per port :: Test that authentication works correctly with single-mode, no guest VLAN, per port and no dynamic VLAN | step1: Single-Mode / no G
  - AWP-9500    0.499 [Roaming Authentication] Auth+ LAG Static - Single-mode, guest VLAN, per port, d :: Test that authentication works with single-mode, guest VLAN, per port, dynamic VLAN | step1: Single-Mode / GuestVLAN / per port / 
  - AWP-9499    0.494 [Roaming Authentication] Auth+ LAG Static - Single-mode, guest VLAN, per port, n :: Test that authentication works with single-mode, guest VLAN, per port, dynamic VLAN | step1: Single-Mode / GuestVLAN / per port / 
  - AWP-9498    0.493 [Roaming Authentication] Auth+ LAG Static - Single-mode, no guest VLAN, per port :: Test that authentication works with single-mode, no guest VLAN, per port, dynamic VLAN | step1: Single-Mode / no GuestVLAN / per p
  - AWP-9516    0.485 [Roaming Authentication] Auth+ LAG LACP - Single-mode, guest VLAN, per port, dyn :: Check that authentication works with single-mode, guest VLAN, per port, dynamic VLAN | step1: Single-Mode / GuestVLAN / per port /
  - AWP-9515    0.481 [Roaming Authentication] Auth+ LAG LACP - Single-mode, guest VLAN, per port, no  :: Check that authentication works with single-mode, guest VLAN, per port, dynamic VLAN | step1: Single-Mode / GuestVLAN / per port /
  - AWP-9532    0.467 [Roaming Authentication] Roaming Auth -Single-mode, guest VLAN, per port, dynami :: Authentication works with single-mode, guest VLAN, per port, dynamic VLAN | step1: Single-Mode / GuestVLAN / per port / DynamicVLA

### AWPTCM-T33365  |  area: Authentication Security WebAuthentication  |  feature: Public key encryption
folder:/New Platform Template/Authentication & Security  steps:7  obj:True
ZEPHYR: OBJ: To make sure that x509 public key can import with Web authentication || Using the attached config | Create a trustpoint to use a local self-signed CA | Create a local self-signed Root CA certific
  - AWP-22642   0.403 [Common Criteria - PKI ] Confirm that self-signed certificate authority works wi :: Confirm that self-signed certificate authority works without any issue | step1: Create a Rivest-Shamir-Adelman (RSA) key pair for 
  - AWP-18194   0.343 [SSL Upgrade Tests     ] AWP+ GUI                                                :: Objective: To verify that the AW+ GUI can operate under HTTPS with self-signed certificate Expected Outcome: AW+ GUI should load u
  - AWP-14508   0.330 [OpenVPN               ] OpenVPN (server) is authenticated with a signed certifi :: The OpenVPN server authenticates itself with a signed certificate. This may either be self signed (the default) in which case the 
  - AWP-14774   0.314 [Port Authentication   ] show auth two-step supplicant                           :: Confirm that "show auth two-step supplicant" shows two-step supplicant information correctly. | step1: Input "show auth two-step s
  - AWP-22896   0.271 [Common Criteria - PKI ] FIA_X509_EXT.3.2 Confirm that the chain of certificates :: FIA_X509_EXT.3.2 The TSF shall validate the chain of certificates from the Root CA upon receiving the CA Certificate Response. | s
  - AWP-22646   0.270 [Common Criteria - PKI ] Confirm that exporting and importing of root certificat :: Confirm that exporting and importing of root certificate works without any issue | step1: Execute following commands on source sys
  - AWP-22649   0.265 [Common Criteria - PKI ] Confirm backward compatibility with older system        :: Confirm backward compatibility with older sytem | step1: Declare the local trustpoint crypto pki trustpoint local => Command shoul
  - AWP-18192   0.264 [SSL Upgrade Tests     ] Port authentication dot1x TLS                           :: Port authentication using 802.1x and TLS should be tested. Make sure you are also using certificates. This test is set up using th

### AWPTCM-T33366  |  area: Authentication Security WebAuthentication  |  feature: Promiscuous / Intercept web Authentication
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-18061   0.546 [Customer Scenario     ] Intercept mode                                          :: Confirm that the intercept mode works correctly. | step1: Confirm that intercept mode works correctly when do web-auth. => Confirm
  - AWP-15413   0.449 [Web Authentication    ] CLI Test - auth-web-server mode intercept               :: Intercept traffic | step1: auth-web-server mode intercept no auth-web-server mode none show auth-web-server Confirm the input, out
  - AWP-15414   0.443 [Web Authentication    ] CLI Test - auth-web-server mode promiscuous             :: Promiscuous mode | step1: auth-web-server mode promiscuous no auth-web-server mode none show auth-web-server Confirm the input, ou
  - AWP-9295    0.420 [Web Authentication    ] Negative testing /guest-vlan on /auth-fail vlan on / dh :: Promiscuous mode ============= Single-host / guest-vlan on /dhcp mode on / promiscuos mode on / * Guest-vlan is not able to use to
  - AWP-19523   0.415 [Web Authentication    ] auth-web-server intercept-port command                  :: Confirm the auth-web-server intercept command. | step1: execute "configure terminal". => Confirm the change into Grobal configurat
  - AWP-9288    0.404 [Web Authentication    ] Multi-supplicant / guest-vlan off / dhcp mode on / inte :: Intercept traffic from supplicant Multi-supplicant / guest-vlan off / dhcp mode on /intercept mode on / supplicant in same subnet 
  - AWP-9290    0.402 [Web Authentication    ] Single-host / guest-vlan off / dhcp mode on / intercept :: Intercept mode Single-host / guest-vlan off / dhcp mode on /intercept mode on / supplicant in same subnet / supplicant's IP is sta
  - AWP-9294    0.391 [Web Authentication    ] Multi-supplicant / guest-vlan off / dhcp mode on / dyna :: Promiscuous mode Multi-supplicant / guest-vlan off / dhcp mode on / dynamic vlan on /promiscuous mode on / supplicant in different

### AWPTCM-T33368  |  area: Authentication Security SMTP  |  feature: SMTP server authentication
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-12092   0.501 [SMTP                  ] SMTP on LAG (Static)                                    :: Confirm SMTP is working with LAG ports (Static) | step1: Configure static LAG Send email => SMTP should work when passing through 
  - AWP-12093   0.497 [SMTP                  ] SMTP on LAG (Dynamic)                                   :: Confirm SMTP is working with LAG ports (Dynamic) | step1: Configure dynamic LAG Send email => SMTP should work when passing throug
  - AWP-12094   0.494 [SMTP                  ] SMTP on Tagged Port                                     :: Confirm SMTP is working on tagged ports. | step1: Configure DUT's port to tag vlan10,20,30 Send mail => SMTP must work with tagged
  - AWP-12097   0.481 [SMTP                  ] SMTP on XEM Module                                      :: Confirm SMTP is working on XEM | step1: Use XEM module Send mail => SMTP must work with XEM module
  - AWP-12098   0.473 [SMTP                  ] SMTP with Max VLAN Configured                           :: Confirm SMTP is still working when max vlan configured. | step1: Configure max number of vlans Send mail => SMTP must still work w
  - AWP-12096   0.467 [SMTP                  ] SMTP On Spanning Tree                                   :: Confirm SMTP is working on Spanning Tree | step1: Spanning Tree enabled Send mail => SMTP must work with Spanning Tree Should not 
  - AWP-12095   0.461 [SMTP                  ] SMTP After Topology Change                              :: Confirm SMTP is still working after topology change | step1: Spanning Tree enabled Change topology Send mail => SMTP must still wo
  - AWP-12080   0.427 [SMTP                  ] Mail SMTP Server                                        :: Confirm the command can only configure 1 SMTP server. | step1: Add SMTP server: Issue the command: awplus(config)# mail smtpserver

### AWPTCM-T33369  |  area: Authentication Security TwoStepAuthentication  |  feature: Mac-based 1st then 802.1x 2nd
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-14776   0.561 [Port Authentication   ] Log when 802.1x auth is successful as 1st or 2nd step   :: Confirm that Log is displayed correctly at the right time. | step1: Attempt 802.1x auth with correct UserID/Password at the 1st St
  - AWP-14879   0.538 [Port Authentication   ] MAX acceptable Supplicant when used Two-Step auth(1st:M :: Confirm that how many supplicant will be accepted when used Two-Step auth(1st:MAC 2nd:802.1x). | step1: Attempt MAC auth and 802.1
  - AWP-14782   0.535 [Port Authentication   ] Two-Step 1st: MAC / 2nd 802.1x                          :: Confirm that Two-Step Auth works correctly when 1st Step:MAC, 2nd Step:802.1x | step1: Attempt MAC auth with invalid MAC address a
  - AWP-14779   0.510 [Port Authentication   ] Log when 802.1x auth is faill as 1st or 2nd step        :: Confirm that Log is displayed correctly at the right time. | step1: Attempt 802.1x auth with invalid UserID/Password at the 1st St
  - AWP-6858    0.508 [Port Authentication   ] 802.1x Authentication and MAC based Authentication      :: Confirm that the 802.1x port authentication and MAC based authentication operate correctly at the same time. | step1: Refer to 4.8
  - AWP-14880   0.487 [Port Authentication   ] MAX acceptable Supplicant when used Two-Step auth(1st:8 :: Confirm that how many supplicant will be accepted when used Two-Step auth(1st:802.1x 2nd:WEB). | step1: Attempt 802.1x auth and WE
  - AWP-14882   0.462 [Port Authentication   ] Repeat Two-Step auth(1st:MAC 2nd:802.1x)                :: Confirm that DUT doesn't occur crash or hung up or any errors after repeated Two-Step auth. | step1: Attempt MAC auth and 802.1x a
  - AWP-9901    0.458 [DHCP Snooping         ] DHCP Snooping with 802.1x & MAC based auth              :: Expect normal operation with 802.1x and MAC auth | step1: 802.1x & MAC based auth => Expect normal operation

### AWPTCM-T33370  |  area: Authentication Security TwoStepAuthentication  |  feature: Mac-based 1st then Web Auth 2nd
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-14878   0.519 [Port Authentication   ] MAX acceptable Supplicant when used Two-Step auth(1st:M :: Confirm that how many supplicant will be accepted when used Two-Step auth(1st:MAC 2nd:WEB). | step1: Attempt MAC auth and WEB auth
  - AWP-14777   0.466 [Port Authentication   ] Log when WEB auth is successful as 2nd step             :: Confirm that Log is displayed correctly at the right time. | step1: Attempt WEB auth with correct MAC address at the 2nd Step. => 
  - AWP-14881   0.465 [Port Authentication   ] Repeat Two-Step auth(1st:MAC 2nd:WEB)                   :: Confirm that DUT doesn't occur crash or hung up or any errors after repeated Two-Step auth. | step1: Attempt MAC auth and WEB auth
  - AWP-14783   0.454 [Port Authentication   ] Two-Step 1st: MAC / 2nd WEB                             :: Confirm that Two-Step Auth works correctly when 1st Step:MAC, 2nd Step:802.1x Confirm that DUT send log messages In each steps. [N
  - AWP-14780   0.452 [Port Authentication   ] Log when WEB auth is fail as 2nd step                   :: Confirm that Log is displayed correctly at the right time. | step1: Attempt WEB auth with invalid UserID/Password at the 2nd Step.
  - AWP-15819   0.437 [RADIUS                ] RADIUS packet with 2-step authentication                :: Confirm that VLAN ID is included in RADIUS-Request each time when using 2-step authentication. | step1: Execute MAC auth as 1st st
  - AWP-15977   0.437 [Port Authentication   ] auth-mac password / Two-Step auth / MAC + WEB           :: Confirm that "auth-mac password" command works correctly when using Two-Step auth of MAC and WEB. | step1: (1) Start MAC auth with
  - AWP-14880   0.431 [Port Authentication   ] MAX acceptable Supplicant when used Two-Step auth(1st:8 :: Confirm that how many supplicant will be accepted when used Two-Step auth(1st:802.1x 2nd:WEB). | step1: Attempt 802.1x auth and WE

### AWPTCM-T33371  |  area: Authentication Security TwoStepAuthentication  |  feature: 802.1x 1st then Web Auth 2nd
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-14880   0.625 [Port Authentication   ] MAX acceptable Supplicant when used Two-Step auth(1st:8 :: Confirm that how many supplicant will be accepted when used Two-Step auth(1st:802.1x 2nd:WEB). | step1: Attempt 802.1x auth and WE
  - AWP-14776   0.575 [Port Authentication   ] Log when 802.1x auth is successful as 1st or 2nd step   :: Confirm that Log is displayed correctly at the right time. | step1: Attempt 802.1x auth with correct UserID/Password at the 1st St
  - AWP-14879   0.559 [Port Authentication   ] MAX acceptable Supplicant when used Two-Step auth(1st:M :: Confirm that how many supplicant will be accepted when used Two-Step auth(1st:MAC 2nd:802.1x). | step1: Attempt MAC auth and 802.1
  - AWP-14782   0.541 [Port Authentication   ] Two-Step 1st: MAC / 2nd 802.1x                          :: Confirm that Two-Step Auth works correctly when 1st Step:MAC, 2nd Step:802.1x | step1: Attempt MAC auth with invalid MAC address a
  - AWP-14784   0.531 [Port Authentication   ] Two-Step 1st: 802.1x / 2nd:WEB                          :: Confirm that Two-Step Auth works correctly when 1st Step:802.1x, 2nd Step:WEB | step1: Attempt 802.1x auth with invalid UserID/Pas
  - AWP-15819   0.530 [RADIUS                ] RADIUS packet with 2-step authentication                :: Confirm that VLAN ID is included in RADIUS-Request each time when using 2-step authentication. | step1: Execute MAC auth as 1st st
  - AWP-14779   0.522 [Port Authentication   ] Log when 802.1x auth is faill as 1st or 2nd step        :: Confirm that Log is displayed correctly at the right time. | step1: Attempt 802.1x auth with invalid UserID/Password at the 1st St
  - AWP-14882   0.485 [Port Authentication   ] Repeat Two-Step auth(1st:MAC 2nd:802.1x)                :: Confirm that DUT doesn't occur crash or hung up or any errors after repeated Two-Step auth. | step1: Attempt MAC auth and 802.1x a

### AWPTCM-T33373  |  area: Authentication Security  |  feature: Roaming Authentication
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-156     0.629 [Customer Scenario     ] The Roaming Authentication                              :: Confirm that the roaming auth is possible and, the communication is possible to each device. | step1: Move to other port on same a
  - AWP-15313   0.629 [Customer Scenario     ] The Roaming Authentication                              :: Confirm that the roaming auth is possible and, the communication is possible to each device. | step1: Move to other port on same a
  - AWP-9616    0.601 [Roaming Authentication] Roaming with dot1x authentication                       :: Test that roaming with dot1x does not work | step1: Roaming with dot1x => Roaming auth supports MAC authentication and Web authent
  - AWP-381     0.581 [Customer Scenario     ] The Roaming Authentication                              :: Confirm that the roaming auth is possible and, the communication is possible to each device after repeat roaming auth. | step1: Re
  - AWP-205     0.581 [Customer Scenario     ] The Roaming Authentication                              :: Confirm that the roaming auth is possible and, the communication is possible to each device after repeat roaming auth. | step1: Re
  - AWP-15605   0.581 [Customer Scenario     ] The Roaming Authentication                              :: Confirm that the roaming auth is possible and, the communication is possible to each device after repeat roaming auth. | step1: Re
  - AWP-426     0.581 [Customer Scenario     ] The Roaming Authentication                              :: Confirm that the roaming auth is possible and, the communication is possible to each device after repeat roaming auth. | step1: Re
  - AWP-9546    0.503 [Roaming Authentication] Disconnect no auth roaming                              :: Check that roaming does not work, re-authentication is executed | step1: no auth roaming disconnected => If the supplicant attache

### AWPTCM-T33374  |  area: Authentication Security  |  feature: Re-authentication option
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-28865   0.467 [VLAN                  ] Re-authentication                                       :: Confirm re-authentication works correctly without deleting FDB. | step1: After authed, confirm re-authentication start => FDB shou
  - AWP-28452   0.360 [Port Authentication   ] single-supplicant mode with multiple VLAN and re-authen :: Confirm re-authentication works correctly without deleting FDB. | step1: After authed, confirm re-authentication start => FDB shou
  - AWP-6792    0.320 [Port Authentication   ] Parameter Test (Authenticator) - Enable/Disable Re-Auth :: Confirm that the re-authentication option works correctly. | step1: 1. Configure DUT for authentication. 2. Run terminal monitor a
  - AWP-27197   0.314 [AWC-lite              ] security                                                :: | step1: security <configured security id> Confirm that ID of security for network setting are configured on router.
  - AWP-9276    0.305 [Web Authentication    ] Re-Authentication(Long-Run) Test                        :: Performance & Limits | step1: Enable reauthentication in port Perform web authentication and leave it authenticated overnight Next
  - AWP-9274    0.302 [Web Authentication    ] Re-authentication duplicately (Long-Run)                :: Negative Tests | step1: Re-authentication duplicately (Long-Run) using IxLoad => Confirm that the web authentication can be re-aut
  - AWP-5762    0.302 [Port Security (Intrusi] enable port authentication                              :: port security ignores supplicant mac addresses | step1: enable port authentication (802.1x), enable port-security on port1.0.1. =>
  - AWP-27204   0.292 [AWC-lite              ] security                                                :: | step1: security <configured security id> Confirm that ID of security for WDS setting are configured on router.

### AWPTCM-T33375  |  area: Authentication Security  |  feature: MAC Auth/Web Auth
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-15445   0.575 [Web Authentication    ] Web Auth disabled - auth log auth-web all               :: Logging test | step1: Disable Web authentication Specify parameter : all (default behavior) Command : auth log auth-web all => All
  - AWP-15443   0.568 [Web Authentication    ] no auth log auth-web all                                :: Logging test | step1: Specify parameter : all Command : no auth log auth-web all => All Web authentication's logs must be not gene
  - AWP-15444   0.566 [Web Authentication    ] auth log auth-web all                                   :: Logging test | step1: Specify parameter : all (default behavior) Command : auth log auth-web all => All Web authentication's logs 
  - AWP-15446   0.550 [Web Authentication    ] Web auth and MAC auth - Logging test                    :: Logging test | step1: Using Web auth and MAC auth together, specify different target log with each authentication method. auth-web
  - AWP-6711    0.515 [Port Authentication   ] MAC Authentication Log - no auth log auth-mac all       :: Confirm that the MAC authenticator log is output correctly. | step1: Specify parameter : all Command : no auth log auth-mac all =>
  - AWP-6712    0.514 [Port Authentication   ] MAC Authentication Log - auth log auth-mac all          :: Confirm that the MAC authenticator log is output correctly. | step1: Specify parameter : all (default behavior) Command : auth log
  - AWP-15436   0.493 [Web Authentication    ] no auth log auth-web failure                            :: Logging test | step1: Specify parameter : failure Command : no auth log auth-web failure => When supplicant succeeds or logoff in 
  - AWP-6735    0.489 [Port Authentication   ] MAC Authentication log with VCS - no auth log auth-mac  :: Confirm that the MAC authenticator log is output correctly. | step1: Specify parameter : all Command : no auth log auth-mac all =>

### AWPTCM-T33377  |  area: Authentication Security  |  feature: Enhanced Guest VLAN
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-145     0.425 [Customer Scenario     ] EPSR enhanced recovery mode                             :: Confirm Enhanced Recovery mode works correctly. | step1: Confirm ESPR status. => Enhanced Recovery mode works correctly.
  - AWP-15506   0.383 [RADIUS                ] RADIUS packet on Guest VLAN                             :: Confirm that VLAN ID is included in RADIUS packet when authentication port is assigned Guest VLAN. | step1: Execute Authentication
  - AWP-4083    0.353 [EPSR, EPSR+, EPSR++   ] Enhanced Recovery - disabled on EPSR Master node (Test  :: Enhanced recovery when it is not enabled on the master | step1: Enhanced recovery when it is not enabled on the master => Refer Su
  - AWP-9900    0.333 [DHCP Snooping         ] Dynamic vlan assignment and guest vlan                  :: Expect normal operation with dynamic and guest vlan | step1: Dynamic vlan assignment and guest vlan => Expect normal operation
  - AWP-22353   0.326 [RADIUS                ] AAA List with Guest VLAN                                :: Confirm that radius query is send on aaa LIST when authentication port is assigned Guest VLAN. | step1: Execute Authentication fro
  - AWP-4084    0.316 [EPSR, EPSR+, EPSR++   ] Enhanced Recovery - disabled on EPSR Transit node (Test :: Enhanced recovery when it is not enabled on the transit node | step1: Enhanced recovery when it is not enabled on the transit node
  - AWP-9880    0.311 [DHCP Snooping         ] DHCP Snooping with Port authentication with dynamic and :: Check that dynamic and guest VLANs should function normally | step1: Port Authentication - Dynamic and Guest VLANs => Dynamic and 
  - AWP-9500    0.303 [Roaming Authentication] Auth+ LAG Static - Single-mode, guest VLAN, per port, d :: Test that authentication works with single-mode, guest VLAN, per port, dynamic VLAN | step1: Single-Mode / GuestVLAN / per port / 

### AWPTCM-T33378  |  area: Management  |  feature: Telnet Server
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-24521   0.658 [ATMF                  ] Check the support of telnet server                      :: Telnet server (IPv4 and IPv6) will be supported | step1: check telnet server will be supported => Confirm telnet server will be su
  - AWP-2308    0.631 [Telnet                ] Telnet - show telnet                                    :: Executing 'show telnet' in the CLI shows the correct Telnet port. | step1: Execute 'show telnet' => check if the telnet server is 
  - AWP-24523   0.607 [ATMF                  ] Telnet server will be disabled by default               :: Telnet server will be disabled by default | step1: check telnet server is disabled by default => confirm telnet server is disabled
  - AWP-2309    0.539 [Telnet                ] Telnet - show running                                   :: Show details of telnet in the running config | step1: show running => telnet configuration should be displayed correctly
  - AWP-5816    0.518 [IPv6 Management       ] Telnet: SW-1 to DUT-2 - Disable telnet server           :: Test for Telnet command from SW-1 to DUT-2 (Disable Telnet server DUT-2) | step1: Configure 4 devices with ipv6 address Disable te
  - AWP-18438   0.507 [Interop               ] Telnet Server                                           :: Confirm that a Host can connect to the Router by Telnet. | step1: Telnet connection from Host-A to 192.168.1.1. => Successfull.
  - AWP-9212    0.463 [VLAN                  ] Private VLAN with Telnet                                :: Private VLAN with Telnet | step1: 1. Private VLAN with Telnet - Telnet from PC-1 to DUT. - Telnet from PC-2 to DUT. => Results sho
  - AWP-24520   0.450 [ATMF                  ] Check the support of telnet client                      :: Telnet client (IPv4 and IPv6) will be supported | step1: check telnet client will be supported => Confirm telnet client will be su

### AWPTCM-T33379  |  area: Management  |  feature: Telnet Client
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-24520   0.679 [ATMF                  ] Check the support of telnet client                      :: Telnet client (IPv4 and IPv6) will be supported | step1: check telnet client will be supported => Confirm telnet client will be su
  - AWP-2308    0.539 [Telnet                ] Telnet - show telnet                                    :: Executing 'show telnet' in the CLI shows the correct Telnet port. | step1: Execute 'show telnet' => check if the telnet server is 
  - AWP-2309    0.518 [Telnet                ] Telnet - show running                                   :: Show details of telnet in the running config | step1: show running => telnet configuration should be displayed correctly
  - AWP-9212    0.445 [VLAN                  ] Private VLAN with Telnet                                :: Private VLAN with Telnet | step1: 1. Private VLAN with Telnet - Telnet from PC-1 to DUT. - Telnet from PC-2 to DUT. => Results sho
  - AWP-24521   0.444 [ATMF                  ] Check the support of telnet server                      :: Telnet server (IPv4 and IPv6) will be supported | step1: check telnet server will be supported => Confirm telnet server will be su
  - AWP-24523   0.409 [ATMF                  ] Telnet server will be disabled by default               :: Telnet server will be disabled by default | step1: check telnet server is disabled by default => confirm telnet server is disabled
  - AWP-5814    0.404 [IPv6 Management       ] Telnet: DUT-2 to DUT-1 (VLAN1)                          :: Test for Telnet command from DUT-2 to DUT-1 (VLAN1) | step1: Configure 4 devices with ipv6 address Perform telnet from DUT-2 to DU
  - AWP-2310    0.401 [Telnet                ] Telnet - copy running config                            :: Be able to save telnet configs for reboot. | step1: copy running-config startup-config => telnet configuration is recorded correct

### AWPTCM-T33380  |  area: Management  |  feature: SSH Server
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-5821    0.624 [IPv6 Management       ] SSH: SSH Client to SSH Server                           :: Test for SSH command from DUT-2 (SSH Client) to DUT-1 (SSH Server) | step1: Configure 4 devices with ipv6 address Configure SSH se
  - AWP-24175   0.545 [ATMF                  ] Check SSH server (IPv4 and IPv6) will be supported      :: Check SSH server (IPv4 and IPv6) will be supported | step1: Check SSH server (IPv4 and IPv6) will be supported => Confirm SSH serv
  - AWP-6492    0.516 [z_Inactive            ] SSH server logging                                      :: SSH Server Tests | step1: ssh server logging - works and appropriate output. Log level can be changed => Verify ssh server logging
  - AWP-5824    0.511 [IPv6 Management       ] SSH: SW-1 to DUT-1 - Disable SSH server                 :: Test for SSH command from SW-1 to DUT-1 (Disable SSH server DUT-1) | step1: Configure 4 devices with ipv6 address Disable SSH serv
  - AWP-6485    0.509 [SSH                   ] enable/disable ssh server                               :: SSH Server Tests | step1: 1. On DUT, enable ssh server then make an ssh session from client to DUT DUT#conf t DUT(config)# service
  - AWP-6483    0.501 [z_Inactive            ] Command Line Handler - ssh server                       :: SSH Server Tests | step1: Command Handler - ssh server commands (including show, no, clear and debug, also include all parameters)
  - AWP-6511    0.482 [SSH                   ] check SSH server via IPv6                               :: SSH Server Tests Verify that SSH session works unsing IPv6 address | step1: Connect to server(DUT) via IPv6: DUT(config-if)#ipv6 a
  - AWP-6486    0.456 [SSH                   ] SSH server uses port 22 by default                      :: SSH Server Tests This is to verify that port 22 is open and service is set to ssh | step1: 1. Configure the DUT only with the comm

### AWPTCM-T33381  |  area: Management  |  feature: SSH Client
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-5821    0.631 [IPv6 Management       ] SSH: SSH Client to SSH Server                           :: Test for SSH command from DUT-2 (SSH Client) to DUT-1 (SSH Server) | step1: Configure 4 devices with ipv6 address Configure SSH se
  - AWP-24176   0.567 [ATMF                  ] Check SSH client (IPv4 and IPv6) will be supported      :: Check SSH client (IPv4 and IPv6) will be supported | step1: Check SSH client (IPv4 and IPv6) will be supported => Confirm SSH clie
  - AWP-6524    0.567 [z_Inactive            ] Command Line Handler - show ssh client                  :: SSH Client Tests | step1: show ssh client gives appropriate information => Verify ssh client settings set are the configured setti
  - AWP-6526    0.530 [z_Inactive            ] check that ssh client settings are not displayed in run :: SSH Client Tests | step1: ssh client settings for current session do not appear in running-config => Verify ssh settings does not 
  - AWP-6485    0.521 [SSH                   ] enable/disable ssh server                               :: SSH Server Tests | step1: 1. On DUT, enable ssh server then make an ssh session from client to DUT DUT#conf t DUT(config)# service
  - AWP-6517    0.469 [SSH                   ] Command Line Handler - SSH client                       :: SSH Client Tests Verify that SSH client commands are correctly handled by DUT | step1: ssh client command handler - test all comma
  - AWP-6511    0.446 [SSH                   ] check SSH server via IPv6                               :: SSH Server Tests Verify that SSH session works unsing IPv6 address | step1: Connect to server(DUT) via IPv6: DUT(config-if)#ipv6 a
  - AWP-6520    0.442 [SSH                   ] check that only specified client version is used for ou :: SSH Client Tests Verify specified version for client is used for connection | step1: ssh client version command - test that only s

### AWPTCM-T33382  |  area: Management  |  feature: ECOFriendly - ECO LED feature
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-14565   0.578 [Green Features (Ecofri] Eco LED button affecting LEDs when ecofriendly led comm :: | step1: 1. Run ecofriendly led command. 2. Push mode select button. 3. Run show running-config 4. Push mode select button.
  - AWP-14566   0.577 [Green Features (Ecofri] Eco LED button affecting LEDs when ecofriendly led comm :: | step1: 1. Run ecofriendly led command. 2. Push mode select button. 3. Run show running-config 4. Push mode select button.
  - AWP-14562   0.563 [Green Features (Ecofri] Ecofriendly affecting LEDs when eco LED is enabled by H :: | step1: 1. Push mode select button and select LED off mode. 2. Run ecofriendly led command. 3. Run show running-config 4. Push m
  - AWP-14564   0.562 [Green Features (Ecofri] Ecofriendly affecting LEDs when eco LED is enabled by H :: | step1: 1. Push mode select button and select LED off mode. 2. Run ecofriendly led command. 3. Run show running-config 4. Push m
  - AWP-3679    0.558 [Green Features (Ecofri] Ecofriendly LED - Disable Feature Config                :: Disable feature command accepted when feature not enabled | step1: Enter the configuration NO ECOFRIENDLY LED 1. Enter SHOW RUN =>
  - AWP-17696   0.549 [Green Features (Ecofri] LED State - ECO LED enabled                             :: Verify 7 Segment LED when ecofriendly is enabled. | step1: DUT VCS Master: 1. Ecofriendly button 2. Ecofriendly command => In ECO 
  - AWP-3678    0.538 [Green Features (Ecofri] Ecofriendly LED Enabled Config                          :: feature enable command added to config | step1: Enter the configuration ECOFRIENDLY LED 1. Enter SHOW RUN => 1. The statement ECOF
  - AWP-3677    0.522 [Green Features (Ecofri] Ecofriendly LED - default Config                        :: feature is not in the default configuration | step1: Start the DUT with no configuration file. 1. Enter SHOW RUN => 1. No "ECOFRIE

### AWPTCM-T33383  |  area: Management  |  feature: ECOFriendly - ECO LPI low power
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-12279   0.408 [Green Features (Ecofri] Command Handler: ecofriendly lpi                        :: Verify command work properly | step1: Check 'ecofriendly lpi' commands for: =>Command execution (sh run, sh int port <range> and s
  - AWP-12280   0.387 [Green Features (Ecofri] LPI Command                                             :: Verify LPI command successfully enabled and works. | step1: Set DUT and partner device port 'ecofriendly lpi'. Connect cable to ea
  - AWP-14562   0.378 [Green Features (Ecofri] Ecofriendly affecting LEDs when eco LED is enabled by H :: | step1: 1. Push mode select button and select LED off mode. 2. Run ecofriendly led command. 3. Run show running-config 4. Push m
  - AWP-17696   0.377 [Green Features (Ecofri] LED State - ECO LED enabled                             :: Verify 7 Segment LED when ecofriendly is enabled. | step1: DUT VCS Master: 1. Ecofriendly button 2. Ecofriendly command => In ECO 
  - AWP-14564   0.377 [Green Features (Ecofri] Ecofriendly affecting LEDs when eco LED is enabled by H :: | step1: 1. Push mode select button and select LED off mode. 2. Run ecofriendly led command. 3. Run show running-config 4. Push m
  - AWP-14565   0.377 [Green Features (Ecofri] Eco LED button affecting LEDs when ecofriendly led comm :: | step1: 1. Run ecofriendly led command. 2. Push mode select button. 3. Run show running-config 4. Push mode select button.
  - AWP-14566   0.376 [Green Features (Ecofri] Eco LED button affecting LEDs when ecofriendly led comm :: | step1: 1. Run ecofriendly led command. 2. Push mode select button. 3. Run show running-config 4. Push mode select button.
  - AWP-14374   0.356 [Green Features (Ecofri] Ecofriendly LED - Eco mode works at multiple line speed :: Eco mode should be tested with both 1G and 10/100M traffic to test both the green and the amber LEDs. | step1: Have both 1 G and 1

### AWPTCM-T33384  |  area: Management EnhancedOperationManagement  |  feature: Auto boot from external media
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-25792   0.548 [Logging               ] Hotswap and in external media.                          :: | step1: Setup configuration and Insert external media. => Check the log external media.
  - AWP-25784   0.466 [Logging               ] Clear log external                                      :: S2028.4.7 clear log external (Privileged Exec mode) | step1: Setup configuration and insert external media.
  - AWP-25783   0.459 [Logging               ] Change to new media.                                    :: Setup the attachment configuration. (Choose usb or card.) | step1: Setup configuration and Insert external media.
  - AWP-25771   0.458 [Logging               ] Configure logging command with external media           :: Configure logging command with external media | step1: Create log file on external media. usb:/messages.log Insert external media.
  - AWP-25778   0.429 [Logging               ] Configure USB with no external media                    :: Configure USB with no media | step1: Input the configuration. log external usb:/log/messages.log log external level informational 
  - AWP-25780   0.427 [Logging               ] Disable logging to external media feature               :: Disable logging to external media feature | step1: Input the configuration and insert external media. log external usb:/log/messag
  - AWP-11236   0.421 [File System           ] Copy from external media is disabled                    :: Configure the autoboot.txt to ignore restore from external media | step1: 1. Set the Copy_from_external_media_enabled to no 2. Boo
  - AWP-25788   0.411 [Logging               ] unmount the media                                       :: S2028.1.14 : remove external media, Adds a unmount feature for external media. | step1: Setup configuration with external media.

### AWPTCM-T33386  |  area: Management EnhancedOperationManagement  |  feature: Management ACL
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-8202    0.404 [BGP                   ] Device Management - Show Command                        :: Show command output | step1: Show command output => Accurate and useful
  - AWP-22661   0.390 [ACL                   ] Management ACL will work on eth0                        :: Management ACL will block a incoming packet from eth interface. | step1: Added IP addres to eth interface,and create block eth int
  - AWP-21197   0.365 [ACL                   ] management ACLs work for both ipv4 and ipv6 ACL         :: numbered software ACL for ipv4 named software ACL for ipv6 | step1: two scenairos (IPv4 and IPv6) and apply two types of managemen
  - AWP-21196   0.347 [ACL                   ] Management ACL blocks ssh and telent access             :: Management ACL will successfully block ssh and telent accordingly | step1: set ssh link between two device => ssh expected to work
  - AWP-27241   0.326 [AWC-lite              ] management frame protection                             :: | step1: management frame protection enable Confirm that management frame protection is enabled on router.
  - AWP-27248   0.326 [AWC-lite              ] management frame protection                             :: | step1: management frame protection enable Confirm that management frame protection is enabled on router.
  - AWP-13893   0.322 [BGP4+                 ] BGP4+ Device Management - Show Command                  :: Show command output | step1: Show command output => Accurate and useful
  - AWP-8435    0.319 [MLD Snooping          ] IPv6 ACL's to send packets to the CPU                   :: | step1: Create IPv6 ACL's to send packets to the CPU => Multicast traffic should still work

### AWPTCM-T33387  |  area: Management EnhancedOperationManagement  |  feature: Management Stacking
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-8202    0.364 [BGP                   ] Device Management - Show Command                        :: Show command output | step1: Show command output => Accurate and useful
  - AWP-1091    0.349 [GVRP                  ] GVRP Interop with Stacking management VLAN & resiliancy :: GVRP should not have any effect, or be affected by the stacking vlan or resiliancy vlan | step1: Monitor vlans on DUT using "show 
  - AWP-13729   0.323 [VLAN                  ] show vlan vlan-stacking                                 :: Verify that commands are entered without a problem and displayed correct informations. | step1: Enter "show vlan vlan-stacking". =
  - AWP-4978    0.319 [Limits                ] VCS - Maximum throughput on stacking cable              :: To verify maximum throughput for stacking cable | step1: - Using RFC2544 to test maximum throughput on stacking cable => Expecting
  - AWP-13727   0.316 [VLAN                  ] switchport vlan-stacking                                :: Verify that commands are entered without a problem and saved correctly. | step1: Enter following commands. "switchport vlan-stacki
  - AWP-9223    0.316 [VLAN                  ] VLAN Stacking with LACP (Static Channel) on customer po :: | step1: VLAN Stacking with LACP (Static Channel) on customer port => 12.11.8_config.txt
  - AWP-9222    0.313 [VLAN                  ] VLAN Stacking with LACP (Static Channel) on provider po :: | step1: VLAN Stacking with LACP (Static Channel) on provider port => 12.11.7_config.txt
  - AWP-9163    0.301 [VLAN                  ] Command Line Handler - switchport vlan-stacking         :: Command Line Handler - switchport vlan-stacking: Test that port can be set to be a provider's port or a customer's port | step1: E

### AWPTCM-T33388  |  area: Management EnhancedOperationManagement  |  feature: Hardware Watchdog
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-20431   0.194 [Platform              ] Watchdog is operating properly                          :: A watchdog is used to automatically detect software anomalies. It reboots the switch if any error occurs to avoid software from ha
  - AWP-10072   0.188 [IPv6                  ] Traffic switched via hardware                           :: Able to confgure max number of addresses which can route traffic via hardware | step1: Configure maximum number of addresses => Al
  - AWP-24388   0.187 [ATMF                  ] Check the atmf-application-proxy process is restarted i :: '''Usage: simul-fail <option> ''' --help 'Print this help' --watchdog 'Tell system to stop tickling the watchdog' --trash-kernel '
  - AWP-8623    0.161 [ACL                   ] ACL: Named Hardware applied to range of ports via servi :: ACL: Named Hardware applied to range of ports via service policy | step1: ACL is applied in hardware to all ports in range via ser
  - AWP-8608    0.160 [ACL                   ] ACL: IPv6 Hardware - Command Handler                    :: ACL: IPv6 Hardware - Command Handler | step1: Check command handler for IPv6 hardware ACL Command execution (ranges) Negation of c
  - AWP-8202    0.158 [BGP                   ] Device Management - Show Command                        :: Show command output | step1: Show command output => Accurate and useful
  - AWP-8641    0.155 [ACL                   ] ACL: Named Hardware can be applied to ports in a dynami :: ACL: Named Hardware can be applied to ports in a dynamic LAG. | step1: Attempt to add an ACL to member ports of a dynamic LAG => C
  - AWP-8599    0.150 [ACL                   ] ACL: Named Hardware - Command Handler                   :: ACL: Named Hardware - Command Handler | step1: Check command handler for named hardware ACL Command execution (ranges) Negation of

### AWPTCM-T33389  |  area: Management EnhancedOperationManagement  |  feature: Software Watchdog
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-20431   0.229 [Platform              ] Watchdog is operating properly                          :: A watchdog is used to automatically detect software anomalies. It reboots the switch if any error occurs to avoid software from ha
  - AWP-24388   0.185 [ATMF                  ] Check the atmf-application-proxy process is restarted i :: '''Usage: simul-fail <option> ''' --help 'Print this help' --watchdog 'Tell system to stop tickling the watchdog' --trash-kernel '
  - AWP-8202    0.156 [BGP                   ] Device Management - Show Command                        :: Show command output | step1: Show command output => Accurate and useful
  - AWP-21197   0.153 [ACL                   ] management ACLs work for both ipv4 and ipv6 ACL         :: numbered software ACL for ipv4 named software ACL for ipv6 | step1: two scenairos (IPv4 and IPv6) and apply two types of managemen
  - AWP-20938   0.152 [VM - AW-Plus on Virtua] VM : AW-plus software restart                           :: Graceful restart of VAA. | step1: Try to reload the DUT with or without configuration => DUT will reload gracefully
  - AWP-14635   0.140 [Hardware Health Monito] HHM - CLI - 'show platform swtable hard'                :: Test that the command 'show platform swtable hard' runs and is a hidden command ( help '?' and tab completion don't work) | step1:
  - AWP-14637   0.140 [Hardware Health Monito] HHM - HW_MON_TEST alters the timeout periods            :: Test that the flag ( file presence) of HW_MON_TEST causes some of the HHM timeouts to be reduced to allow quicker testing. | step1
  - AWP-29632   0.138 [OpenFlow              ] ER-2059 - Stop the communication of the device that pro :: Confirm that deleting flows that proccesed by software does not affect to flows that processed by hardware. | step1: Register the 

### AWPTCM-T33390  |  area: Management EnhancedOperationManagement  |  feature: Fixed password of AT-FL
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-29006   0.287 [AWC-lite              ] Licensing test for RoW                                  :: Confirm AT-FL-GEN2-WL20-1YR / AT-FL-GEN2-WL20-5YR will be installed correctly and works well | step1: Same step as AWP-29005
  - AWP-10244   0.261 [Diagnostic Application] Invalid password Test                                   :: Test should not run | step1: test invalid password => test not run
  - AWP-18369   0.239 [Platform              ] Operation with and without SFP+ license                 :: Scope: 1.SFP+ link up is correctly confirmed. 2.Confirm link up trap occurs. 3.SFP+ can communicate with fixedport. Asssertion: | 
  - AWP-6470    0.197 [z_Inactive            ] password login fails on incorrect password              :: Password Login Tests | step1: password login fails when incorrect password used (change case of a letter). remote client to DUT =>
  - AWP-6471    0.164 [z_Inactive            ] password login succeeds when no user key available      :: Password Login Tests | step1: Password login succeeds when no user key available - DUT to remote server => Verify user can success
  - AWP-20686   0.152 [Wireless controller (U] Change common password of radius                        :: [Wireless manager] Change radius password. ("radius-server key <key>" or "radius-server host <server-IP> key <key>") [Radius serve
  - AWP-7815    0.152 [User Login            ] User Login - Enable password                            :: IPInfusion supports the setting of a password on the enable command. If an enable password has been set, then users in the wheel g
  - AWP-7838    0.152 [User Login            ] User Login - Max+1 length password                      :: Check if command allow to add user that is beyond the maximum character length on a password | step1: Add user with max+1 length p

### AWPTCM-T33392  |  area: Management ManagingConfigurationFilesAndSoftwareVersions  |  feature: Loading Files using TFTP
folder:/New Platform Template/Management  steps:1  obj:True
ZEPHYR: OBJ: Objective: To test TFTP upload and download using different destination filenames Expected Outcome: TFTP should operate || Execute TFTP copy operation with the following setup: Downlo
  - AWP-5488    0.913 [TFTP                  ] TFTP upload and download operation with different desti :: Objective: To test TFTP upload and download using different destination filenames Expected Outcome: TFTP should operate normally i
  - AWP-5497    0.503 [TFTP                  ] TFTP compatibility with AT-TFTP server                  :: Objective: To test TFTP compatibility with a server using AT-TFTP Expected Outcome: TFTP should be able to download and upload fil
  - AWP-5478    0.381 [TFTP                  ] TFTP upload                                             :: [version 3] Edited a step because corresponding to CR41795 issue. | step1: TFTP uploads using menu (prompts): Start capture on Cli
  - AWP-5485    0.373 [TFTP                  ] TFTP operation with different storage types             :: Objective: To test TFTP behaviour using different storage types Expected Outcome: TFTP should operate without any issue using diff
  - AWP-5490    0.349 [TFTP                  ] filename does not exist on the switch                   :: | step1: TFTP upload where file name does not exist on switch
  - AWP-29493   0.347 [OpenFlow              ] File download/upload                                    :: Confirm that User can File upload/download from DUT. | step1: Send any packets between HostA and Host1 bidirectionally => The flow
  - AWP-24858   0.347 [OpenFlow              ] File download/upload                                    :: Confirm that User can File upload/download from DUT. | step1: Send any packets between HostA and Host1 bidirectionally => The flow
  - AWP-26462   0.347 [OpenFlow              ] File download/upload                                    :: Confirm that User can File upload/download from DUT. | step1: Send any packets between HostA and Host1 bidirectionally => The flow
