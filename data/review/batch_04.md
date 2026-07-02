# Rerank batch 04  (cases 120..149)

### AWPTCM-T33430  |  area: Other Windows10Support  |  feature: 802.1x Authentication Server
folder:/New Platform Template/Other  steps:1  obj:False
  - AWP-6858    0.592 [Port Authentication   ] 802.1x Authentication and MAC based Authentication      :: Confirm that the 802.1x port authentication and MAC based authentication operate correctly at the same time. | step1: Refer to 4.8
  - AWP-9367    0.567 [xSTP                  ] Interop with 802.1x port control                        :: | step1: Interop with 802.1x port control
  - AWP-6724    0.533 [Port Authentication   ] 802.1X Authentication Log - Disabled dot1x Authenticati :: Confirm that the dot1x authenticator log outputs correctly. | step1: Disable dot1x Authentication Specify parameter : all (default
  - AWP-5690    0.526 [LLDP                  ] LLDP-MED - 802.1x: switch between Server and supplicant :: Test for LLDP-MED with 802.1x authentication with a setup of Switch between the Server and the supplicant | step1: Repeat the abov
  - AWP-10275   0.522 [Process Monitoring    ] Memory Monitoring - 802.1X                              :: Correct output information for 802.1X | step1: Execute the command "show memory allocations" and capture output => Check memory in
  - AWP-6722    0.522 [Port Authentication   ] 802.1X Authentication Log - no auth log dot1x all       :: Confirm that the dot1x authenticator log outputs correctly. | step1: Specify parameter : all Command : no auth log dot1x all => Al
  - AWP-5553    0.521 [LLDP                  ] Enable LLDP with 802.1x                                 :: Test for LLDP ports with 802.1x protocol running. | step1: Enable 802.1x on a port. Enable LLDP on this port => LLDP packets shoul
  - AWP-6723    0.521 [Port Authentication   ] 802.1X Authentication Log - auth log dot1x all          :: Confirm that the dot1x authenticator log outputs correctly. | step1: Specify parameter : all (default behavior) Command : auth log

### AWPTCM-T33431  |  area: Other Windows10Support  |  feature: IPv4 Ping Traceroute
folder:/New Platform Template/Other  steps:1  obj:False
  - AWP-5805    0.634 [IPv6 Management       ] Ping and Traceroute: DUT-1 to DUT-2                     :: Test for Ping and Traceroute command from DUT-1 to DUT-2 | step1: Configure 4 devices with ipv6 address Perform ping and tracerout
  - AWP-5806    0.563 [IPv6 Management       ] Ping and Traceroute: DUT-1 to DUT-2 (VLAN2)             :: Test for Ping and Traceroute command from DUT-1 to DUT-2 (VLAN2) | step1: Configure 4 devices with ipv6 address Perform ping and t
  - AWP-5807    0.563 [IPv6 Management       ] Ping and Traceroute: DUT-1 to DUT-1 (VLAN2)             :: Test for Ping and Traceroute command from DUT-1 to DUT-1 (VLAN2) | step1: Configure 4 devices with ipv6 address Perform ping and t
  - AWP-5798    0.546 [IPv6 Management       ] Ping and Traceroute: DUT-1 to SW-2                      :: Test for Ping and Traceroute command from DUT-1 to SW-2 | step1: Configure 4 devices with ipv6 address Perform ping and traceroute
  - AWP-5804    0.530 [IPv6 Management       ] Ping and Traceroute: DUT1 to PC2                        :: Test for Ping and Traceroute command from DUT1 to PC2 | step1: Setup PC1 <---> DUT1 <---> DUT2 <---> PC2 using ipv6 configuration.
  - AWP-5803    0.528 [IPv6 Management       ] Ping and Traceroute: SW-1 to DUT-1 (VLAN1)              :: Test for Ping and Traceroute command from SW-1 to DUT-1 (VLAN1) | step1: Configure 4 devices with ipv6 address Perform ping and tr
  - AWP-10228   0.516 [z_Inactive            ] Traceroute for 192.168.1.2                              :: Traceroute should be successful | step1: trace 192.168.1.2 => confirm correct trace result
  - AWP-10227   0.516 [z_Inactive            ] Traceroute for 192.168.1.1                              :: Traceroute should show the correct result | step1: trace 192.168.1.1 => confirm correct trace result

### AWPTCM-T33432  |  area: Other Windows10Support  |  feature: DHCP Server
folder:/New Platform Template/Other  steps:1  obj:False
  - AWP-15418   0.583 [Web Authentication    ] DHCP mode off / DHCP server on                          :: DHCP Mode | step1: DHCP mode off / DHCP server on Confirm all supplicants get a IP address from DHCP server. => All supplicant mus
  - AWP-9875    0.553 [DHCP Snooping         ] DHCP Server - configured on same device                 :: Confirm correct and normal behavior if server is configured on same device | step1: DHCP Server configured on same device. => Expe
  - AWP-9902    0.552 [DHCP Snooping         ] Local DHCP server                                       :: Expect normal operation with local DHCP server | step1: Local DHCP server => Expect normal operation
  - AWP-9907    0.514 [DHCP Snooping         ] Interop - AW DHCP Server                                :: Confirm normal operation with AW DHCP Server | step1: AW DHCP Server => Expect normal operation
  - AWP-6849    0.485 [Port Authentication   ] Port Authentication and External DHCP Server            :: Port Authentication and External DHCP Server | step1: Refer to 4.2.2.doc => Refer to 4.2.2.doc Confirm the external DHCP server an
  - AWP-9910    0.480 [DHCP Snooping         ] Interop - Linux DHCP Server                             :: Confirm normal operation with Linux DHCP Server | step1: Linux DHCP Server => Expect normal operation
  - AWP-15360   0.463 [Web Authentication    ] Web Authentication and External DHCP Server             :: Web Authentication and External DHCP Server | step1: Refer to 4.3.2.doc => Refer to 4.3.2.doc
  - AWP-6848    0.462 [Port Authentication   ] Port Authentication and Internal DHCP Server            :: Port Authentication and Internal DHCP Server | step1: Refer to 4.2.1.doc => Refer to 4.2.1.doc Confirm the internal DHCP server an

### AWPTCM-T33433  |  area: Other Windows10Support  |  feature: IPv6 Ping Traceroute
folder:/New Platform Template/Other  steps:1  obj:False
  - AWP-5805    0.702 [IPv6 Management       ] Ping and Traceroute: DUT-1 to DUT-2                     :: Test for Ping and Traceroute command from DUT-1 to DUT-2 | step1: Configure 4 devices with ipv6 address Perform ping and tracerout
  - AWP-5806    0.624 [IPv6 Management       ] Ping and Traceroute: DUT-1 to DUT-2 (VLAN2)             :: Test for Ping and Traceroute command from DUT-1 to DUT-2 (VLAN2) | step1: Configure 4 devices with ipv6 address Perform ping and t
  - AWP-5807    0.624 [IPv6 Management       ] Ping and Traceroute: DUT-1 to DUT-1 (VLAN2)             :: Test for Ping and Traceroute command from DUT-1 to DUT-1 (VLAN2) | step1: Configure 4 devices with ipv6 address Perform ping and t
  - AWP-5798    0.603 [IPv6 Management       ] Ping and Traceroute: DUT-1 to SW-2                      :: Test for Ping and Traceroute command from DUT-1 to SW-2 | step1: Configure 4 devices with ipv6 address Perform ping and traceroute
  - AWP-5803    0.585 [IPv6 Management       ] Ping and Traceroute: SW-1 to DUT-1 (VLAN1)              :: Test for Ping and Traceroute command from SW-1 to DUT-1 (VLAN1) | step1: Configure 4 devices with ipv6 address Perform ping and tr
  - AWP-5804    0.585 [IPv6 Management       ] Ping and Traceroute: DUT1 to PC2                        :: Test for Ping and Traceroute command from DUT1 to PC2 | step1: Setup PC1 <---> DUT1 <---> DUT2 <---> PC2 using ipv6 configuration.
  - AWP-5799    0.567 [IPv6 Management       ] Ping and Traceroute: SW-1 to SW-2                       :: Test for Ping and Traceroute commandfrom SW-1 to SW-2 | step1: Configure 4 devices with ipv6 address Perform ping and traceroute t
  - AWP-5802    0.563 [IPv6 Management       ] Ping and Traceroute: SW-1 to DUT-1 (VLAN2)              :: Test for Ping and Traceroute command from SW-1 to DUT-1 (VLAN2) | step1: Configure 4 devices with ipv6 address Perform ping and tr

### AWPTCM-T33434  |  area: Other Windows10Support  |  feature: Radius Client
folder:/New Platform Template/Other  steps:1  obj:False
  - AWP-15942   0.506 [IPv4                  ] RADIUS Client operation in "no ip forwarding"           :: Confirm that RADIUS Client works correctly when "no ip forwarding" in configured. | step1: Execute Port auth (or User auth) from P
  - AWP-29488   0.444 [OpenFlow              ] RADIUS client                                           :: Confirm that DUT works as Radius client. Confirm that User can login with Radius authentication. | step1: Create a user which is a
  - AWP-24854   0.444 [OpenFlow              ] RADIUS client                                           :: Confirm that DUT works as Radius client. Confirm that User can login with Radius authentication. | step1: Create a user which is a
  - AWP-26457   0.444 [OpenFlow              ] RADIUS client                                           :: Confirm that DUT works as Radius client. Confirm that User can login with Radius authentication. | step1: Create a user which is a
  - AWP-5358    0.427 [RADIUS                ] CLI Test - RADIUS Configuration                         :: RADIUS client settings and parameters can be configured/changed and are properly reflected in RADIUS show commands and in running-
  - AWP-27244   0.414 [AWC-lite              ] radius / group                                          :: | step1: radius auth group radius Confirm that RADIUS server group is configured on router.
  - AWP-20354   0.407 [RADIUS                ] Interoperability of Windows Radius Client and Windows R :: Confirm that DUT can authenticate Windows Radius Client to a Window's Radius Server. | step1: Using a Windows machine as the RADIU
  - AWP-5383    0.403 [RADIUS                ] RADIUS Authentication - Logging Test                    :: Confirm logs for each operation | step1: 1.Login client through 802.1x with radius server authenticated. 2.Login telnet client wit

### AWPTCM-T33435  |  area: Other Windows10Support  |  feature: Web Browser setting
folder:/New Platform Template/Other  steps:1  obj:False
  - AWP-19525   0.415 [Web Authentication    ] without proxy setting                                   :: If there is no Proxy set, authentication screen must be displayed | step1: Configure auth-web-server intercept-port any command. =
  - AWP-19526   0.401 [Web Authentication    ] In case of correct proxy setting                        :: When correct proxy setting is used on supplicant, authenticator should be displayed web-auth page. Then, supplicant can authentica
  - AWP-15947   0.385 [IPv4                  ] WEB auth operation in "no ip forwarding"                :: Confirm that WEB Authentication works correctly when "no ip forwarding" in configured. | step1: Input "http://192.168.1.200" on PC
  - AWP-19527   0.380 [Web Authentication    ] In case of incorrect proxy setting                      :: When incorrect proxy setting is used on supplicant, authenticator should be displayed error page. | step1: Confirm the authenticat
  - AWP-14937   0.364 [Web Authentication    ] Web Auth Proxy / interoperability (Browser) / Multi-sup :: - Confirm the basic feature of Web Auth Proxy works correctly on all supported-browser. - If your test product supports the featur
  - AWP-15361   0.313 [Web Authentication    ] Web Authentication and Tagged port (Other Port)         :: Web Authentication and Tagged port (Other Port) | step1: Refer to 4.5.1.doc => Refer to 4.5.1.doc
  - AWP-18464   0.301 [Validation Scenario   ] Web-Auth Feature Options                                :: Check other options with Web-Auth features | step1: Explore other feature options i.e. DHCP server for Web-Authentication => Check
  - AWP-28986   0.276 [Web Redirect          ] Web Redirect: Support for Google Chrome                 :: The feature interoperates with current version of Google Chrome The test results will document the current general release version

### AWPTCM-T33436  |  area: Other Windows10Support  |  feature: NTP Server
folder:/New Platform Template/Other  steps:1  obj:False
  - AWP-1118    0.699 [NTP                   ] NTP - AW+ as an NTP server for other device types       :: NTP - Test that AW+ can act as an NTP server for other device types such as a PC | step1: Configure DUT to be NTP server set pc to
  - AWP-27159   0.691 [AWC-lite              ] NTP server                                              :: | step1: ip <correct ip address> Confirm that data of NTP server is configured on router.
  - AWP-19385   0.626 [z_ATKK_Inquiry_Based  ] NTP Server                                              :: Scope Confirm that ntp server feature. | step1: Confirm that ntp server feature. ntp packets is sent to registere address, when nt
  - AWP-1128    0.574 [NTP                   ] NTP - Check NTP packet format                           :: NTP - Check NTP packet format | step1: Capture NTP packets during time sync, refer to RFC and ensure correct. => Packets have corr
  - AWP-1108    0.550 [NTP                   ] NTP - Device can sync time with a windows pc as a ntp s :: NTP - Device can sync time with a window pc as a ntp server | step1: Configure windows pc as a ntp time server Issue sh ntp status
  - AWP-12422   0.533 [NTP                   ] NTP - Test for ntp source command                       :: NTP source command specify a preferred source interface for NTP requests. | step1: Configure DUT with ntp source command => NTP de
  - AWP-1106    0.510 [NTP                   ] NTP - Device time will follow a time server change      :: NTP - Device time will follow a time server change | step1: Adjust time on Linux box Issue sh ntp status command => Times on Linux
  - AWP-1111    0.510 [NTP                   ] NTP - test AW+ device as Master                         :: NTP - test AW+ device as Master | step1: Configure DUT as NTP Server with stratum 1 - ntp master 1 Configure second device using D

### AWPTCM-T35370  |  area: IPv4 DHCPClient  |  feature: DHCP Extended ID
folder:/New Platform Template/IPv4  steps:0  obj:True
ZEPHYR: OBJ: l || DUT (DHCP client)-----DHCP server -------------------------------| -------------------------------Wireshark Server Configuration awplus(config)#service dhcp-server awplus(config)#ip dhcp poo
  - AWP-15454   0.438 [Web Authentication    ] auth-web forward dhcp and arp                           :: Functional test with auth-web forward dhcp and arp | step1: 1) Set up environment. 2) Confirm that PC can obtain IP-address from e
  - AWP-3578    0.400 [DHCP                  ] DHCP server - 120 day lease configured                  :: Test for DHCP server to offer 120 day lease time to a DHCP Client. | step1: Configure DUT as DHCP Server. Create a DHCP Pool with 
  - AWP-4789    0.393 [DHCP                  ] CR31049: ARP Probe DHCP Pool in the Secondary IP Interf :: The DHCP Server should detect conflict IP using ARP Probe and give out the next available IP. The Network of the DHCP Pool is set 
  - AWP-15230   0.390 [DHCP                  ] System usage of the DHCP address pool (CR39157)         :: DHCP server system usage counts up base on actual ip address given | step1: Configure DHCP pool ip dhcp pool <name> network 192.16
  - AWP-10001   0.387 [ICMP                  ] Add IP interface                                        :: Confirm that IP interface is added | step1: ADD IP INTERFACE Sample Results: awplus(config)#vlan database awplus(config-vlan)#vlan
  - AWP-2266    0.380 [DHCP                  ] DHCP server - Pool                                      :: Test for configuring Pool in DHCP Server | step1: 1. Configure DHCP Server in the DUT and add a DHCP pool. (e.g ip dhcp pool TestP
  - AWP-9787    0.373 [DHCP Snooping         ] DHCP Snooping - interop with DHCP-RELAY                 :: Confirm that DHCP Snooping can be interop with DHCP relay note: DHCP-relay is not supported on x230 devices | step1: Setup DHCP cl
  - AWP-3594    0.366 [DHCP                  ] DHCP server - Probe IP Address using ARP                :: Verify that when probe parameter is set to ARP, server probes IP address using ARP | step1: 1.Configure DUT as DHCP server. 2.Conn

### AWPTCM-T35383  |  area: Switching RateLimit  |  feature: Ingress Limit
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-10077   0.214 [IPv6                  ] IPv6 Switching - rstp topology change                   :: IPv6 and rstp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that rstp 
  - AWP-10078   0.209 [IPv6                  ] IPv6 Switching - stp topology change                    :: IPv6 and stp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that stp fo
  - AWP-7473    0.207 [Storm Control         ] Disable ingress filtering on a switchport               :: Test that ingress filtering is successfully disabled. | step1: Ingress filtering is enabled. Issue the command "switchport mode ac
  - AWP-7479    0.205 [Storm Control         ] enable ingress filtering                                :: Test that ingress filtering can still be successfully enabled. | step1: Ingress filtering is NOT disabled. Issue the command "swit
  - AWP-9471    0.202 [xSTP                  ] Interop with VLANS ingress filter                       :: | step1: Interop with VLANS ingress filter => BPDU must not be filtered even if ingress filtering is on - access & trunk ports
  - AWP-9377    0.202 [xSTP                  ] Interop with VLANS ingress filter                       :: | step1: Interop with VLANS ingress filter => BPDU must not be filtered even if ingress filtering is on - access & trunk ports
  - AWP-1094    0.193 [GVRP                  ] GVRP VLAN limit                                         :: Device functional to VLAN limit. | step1: Dynamic VLAN limit can be created => Dynamic vlan limit can be reached. and Vlans age ou
  - AWP-7618    0.190 [Policy Based Routing  ] VCS - apply PBR to ingress ports                        :: Confim that PBR can be applied to the ingress ports in a VCS environment | step1: Able to apply PBR to the ingress ports in a VCS 

### AWPTCM-T37856  |  area:   |  feature: 5000 mdi_mdix auto test
folder:/Sanity Check  steps:0  obj:False
ZEPHYR: need to pass all supported tests, script attached including python2 framework
  - AWP-26897   0.420 [Green Features (Ecofri] 5G_Fixed Copper_Cross / 5G / Auto / MDI-MDIX            :: Verify LPI works with 5Gbit / Auto / MDI-MDIX | step1: Set DUT and partner device: Speed = 5000 Duplex = Auto Polarity = DUT-MDI, 
  - AWP-12285   0.405 [Green Features (Ecofri] Auto_Fixed Copper_Straight / Auto / Full / MDI-MDIX     :: Verify LPI works with Auto/ Full / MDI-MDIX settings | step1: Set DUT and partner device: Speed = Auto Duplex = Full Polarity = MD
  - AWP-12286   0.391 [Green Features (Ecofri] Auto_Fixed Copper_Straight / Auto / Half / MDI-MDIX     :: Verify LPI works with Auto / Half / MDI-MDIX settings | step1: Set DUT and partner device: Speed = Auto Duplex = Half Polarity = M
  - AWP-12292   0.379 [Green Features (Ecofri] 10G_Fixed Copper_Straight / Auto / Full / MDI-MDIX      :: Verify LPI works in Auto / Full / MDI-MDIX setting | step1: Set DUT and partner device: Speed = Auto Duplex = Full Polarity = MDI 
  - AWP-12282   0.375 [Green Features (Ecofri] 1G_Fixed Copper_Straight / 1000 / Auto / MDI-MDIX       :: Verify LPI works with 1000 / Auto / MDI-MDIX settings | step1: Set DUT and partner device: Speed = 1000 Duplex = Auto Polarity = M
  - AWP-26898   0.359 [Green Features (Ecofri] 2.5G_Fixed Copper_Cross / 2.5G / Auto / MDIX-MDI        :: Verify LPI works with 2.5Gbit / Auto / MDIX-MDI | step1: Set DUT and partner device: Speed = 2500 Duplex = Auto Polarity = DUT-MDI
  - AWP-104     0.330 [Port Speed, Duplex and] SFP Fibre-1Gig-MDIX/MDI                                 :: SFP Fibre - 1Gig - Speed/Duplex = Auto & MDIX/MDI mix DUT Port Type: SFP Fibre - 1 Gig Partner Port Type: Any Fibre - 1 Gig Steps:
  - AWP-112     0.327 [Port Speed, Duplex and] SFP Fibre-100M-MDIX/MDI                                 :: SFP Fibre - 100M - Speed/Duplex = Auto & MDIX/MDI mix DUT Port Type: SFP Fibre - 100M Partner Port Type: Any Fibre - 100M Steps: 1

### AWPTCM-T37858  |  area:   |  feature: platform led test <colour>
folder:/Sanity Check  steps:1  obj:True
ZEPHYR: OBJ: platform led test green all green switchport LEDs come on and stay until turned off by another command or platform led t ||
  - AWP-18412   0.360 [Factory Runup Support ] FactoryRunUp-LED testing-ARC                            :: ARC - Production Build Tests ARC - LED test: | step1: Run following CLI commands and confirm required LEDs lit as expected. (For a
  - AWP-10432   0.299 [z_Inactive            ] System LED - fan stop                                   :: To check if LED is flashing red colour - 1 flash per period | step1: Cause a unit fan to stop (e.g. XEM fan) => Flashing red colou
  - AWP-11637   0.293 [Environment Monitoring] System LED - fan stop                                   :: To check if LED is flashing red colour - 1 flash per period For x510, 7-segment LED flashes "F". | step1: Cause a unit fan to stop
  - AWP-11421   0.288 [Port Speed, Duplex and] CFC PSU LED                                             :: PSU LED Solid Green - at least one PSU is up, no faults Solid Amber - occurs in transitory state during startup Flashing Amber - F
  - AWP-11638   0.275 [Environment Monitoring] System LED - faulty XEM                                 :: To check if LED is flashing red colour -4 flash per period | step1: Cause a XEM to fail (e.g - install a faulty XEM or one with an
  - AWP-10433   0.275 [z_Inactive            ] System LED - faulty XEM                                 :: To check if LED is flashing red colour -4 flash per period | step1: Cause a XEM to fail (e.g - install a faulty XEM or one with an
  - AWP-14374   0.271 [Green Features (Ecofri] Ecofriendly LED - Eco mode works at multiple line speed :: Eco mode should be tested with both 1G and 10/100M traffic to test both the green and the amber LEDs. | step1: Have both 1 G and 1
  - AWP-3644    0.271 [Green Features (Ecofri] Ecofriendly control of x900-12XT/S SFP port LEDs        :: Feature controls LEDs | step1: On all x900-12XT/S DUTs SFP ports. 1. Insert SFPs into all SFP bays, loop all SFPs with fibre cable

### AWPTCM-T37859  |  area:   |  feature: POE LED-Fault-OverDrawByUserBudget
folder:/Sanity Check  steps:1  obj:True
ZEPHYR: OBJ: Functional LED Operation Over drawing power based on User budget || Drawing more power than is allocated in the Power user budge
  - AWP-4596    0.913 [PoE                   ] POE LED-Fault-OverDrawByUserBudget                      :: Functional LED Operation Over drawing power based on User budget | step1: Drawing more power than is allocated in the Power user b
  - AWP-4595    0.479 [PoE                   ] POE LED-Fault-OverDrawByClass                           :: Functional LED Operation Over drawing power based on Class allocation | step1: Fault condition caused by over drawing power per cl
  - AWP-4582    0.456 [PoE                   ] POE AllocatedPower-PD-Fault                             :: Functional Allocated Power PD Fault updates available power | step1: PD in fault condition - allocated power updated Put port into
  - AWP-4581    0.414 [PoE                   ] POE AllocatedPower-PD stops drawing power               :: Functional Allocated Power PD Stops drawing power | step1: PD goes stop s drawing power, then starts drawing power. => Allocated p
  - AWP-4594    0.329 [PoE                   ] POE LED-POE                                             :: Functional LED Operation Nominal POE port connection | step1: Normal PD operation is represented with a steady green LED (old Dupl
  - AWP-11636   0.285 [Environment Monitoring] System LED - no environment fault conditions            :: To check if fault LED is unlit when there is no environment fault conditions | step1: System normal with no environment fault cond
  - AWP-10431   0.285 [z_Inactive            ] System LED - no environment fault conditions            :: To check if fault LED is unlit when there is no environment fault conditions | step1: System normal with no environment fault cond
  - AWP-25249   0.278 [PoE                   ] Not Allocated Power - exceed Nominal Power              :: Stop to supply to port which priority is lower if Allocated Power exceeds Nominal Power. Usually, this port’s state becomes “Denie

### AWPTCM-T37860  |  area:   |  feature: POE LED-POE
folder:/Sanity Check  steps:1  obj:True
ZEPHYR: OBJ: Functional LED Operation Nominal POE port connection || Normal PD operation is represented with a steady green LED (
  - AWP-4594    0.999 [PoE                   ] POE LED-POE                                             :: Functional LED Operation Nominal POE port connection | step1: Normal PD operation is represented with a steady green LED (old Dupl
  - AWP-4593    0.533 [PoE                   ] POE LED-NonPOE                                          :: Functional LED Operation Non-POE port connection | step1: Make a non POE connection, but carry L2 traffic via port POE => No duple
  - AWP-4592    0.533 [PoE                   ] POE LED-NoConnections                                   :: Functional LED Operation No port connection | step1: No connection to port => No LED is illuminated
  - AWP-25249   0.380 [PoE                   ] Not Allocated Power - exceed Nominal Power              :: Stop to supply to port which priority is lower if Allocated Power exceeds Nominal Power. Usually, this port’s state becomes “Denie
  - AWP-4595    0.373 [PoE                   ] POE LED-Fault-OverDrawByClass                           :: Functional LED Operation Over drawing power based on Class allocation | step1: Fault condition caused by over drawing power per cl
  - AWP-27161   0.370 [AWC-lite              ] LED                                                     :: | step1: led enable Confirm that LED setting is configured on router.
  - AWP-4596    0.349 [PoE                   ] POE LED-Fault-OverDrawByUserBudget                      :: Functional LED Operation Over drawing power based on User budget | step1: Drawing more power than is allocated in the Power user b
  - AWP-11641   0.299 [Environment Monitoring] PSU LED - present and good state                        :: To check if LED for each PSU is green | step1: Check Green (present and good state) for all PSU's => LED for each PSU is green

### AWPTCM-T37861  |  area: POE  |  feature: lldp max power and cli power
folder:/Sanity Check  steps:1  obj:True
ZEPHYR: OBJ: lldp max power is overridden by cli setting for interface max power || Connect device running LLDP script via a POE Load box. Send
  - AWP-4577    0.999 [PoE                   ] POE - lldp max power and cli power                      :: lldp max power is overridden by cli setting for interface max power | step1: Connect device running LLDP script via a POE Load box
  - AWP-4576    0.704 [PoE                   ] POE - lldp max power is recognised                      :: lldp max power is recognised and overrides classification max power | step1: Connect device running LLDP script via a POE Load box
  - AWP-4575    0.466 [PoE                   ] PoE cli Interface max power                             :: POE Max power can be configured on each port & overrides classification power | step1: A PoE interface can be configured to a max 
  - AWP-14385   0.419 [PoE                   ] Change the max power                                    :: Change the max power. "power-inline max <> " | step1: Change the max power. "power-inline max <> " => Confirm PoE max power has ch
  - AWP-5657    0.375 [LLDP                  ] Extended Power TLV: Max power not configured            :: Test for the actual value of Extended Power TLV transmitted when Max power is not configured. | step1: 1. On a port, remove the ma
  - AWP-4574    0.364 [PoE                   ] POE+ -PowerBudget-LLDP-MED-Max-per-Class                :: Functional Power Budget LLDP MED Check max per class for POE or PoE+ unit | step1: lldp must be enabled with "lldp run" command Sh
  - AWP-4573    0.360 [PoE                   ] POE-PowerBudget-LLDP-MED-Max-per-Class                  :: Functional Power Budget LLDP MED Check max per class for POE unit | step1: lldp must be enabled with "lldp run" command Show Power
  - AWP-4580    0.360 [PoE                   ] POE AllocatedPower-DynamicChanges                       :: Functional Allocated Power Vcarious dynamic port config changes using CLI, LLDP-MED and Classification | step1: Dynamic changes to

### AWPTCM-T37862  |  area:   |  feature: PoE Single Signature
folder:/Sanity Check  steps:9  obj:True
ZEPHYR: OBJ: Single Signature class 1-8 power output. PSE Output Power vs the PD Input Power. || Class 1 | Class 0 | Class 2
  - AWP-27128   0.288 [PoE                   ] Document new output parameters to the PoE show command  :: Verify new output for POE show commands | step1: Verify target port Signature mode awplus#show power-inline interface detail
  - AWP-27131   0.288 [PoE                   ] Plug in a AT-TQ2403 (Class 4 30W PD) into a 4-wire sing :: Verify result of plugging a simple class4 30W PD into a switchport configured for a 4-wire single-signature PD | step1: Log into D
  - AWP-27133   0.282 [PoE                   ] Document new output parameters to the PoE show command  :: Document new output parameters to the PoE show command test cases | step1: Verify target port Signature mode awplus#show power-inl
  - AWP-27117   0.281 [PoE                   ] POE support for single-signature power configuration (C :: Objective: Able to operate in single-signature mode where-by: 1. The spare pair is put into manual mode. 2. The data pair is put i
  - AWP-27116   0.274 [PoE                   ] POE support for single-signature power configuration (R :: Objective: Able to operate in single-signature mode where-by: 1. The spare pair is put into manual mode. 2. The data pair is put i
  - AWP-4604    0.250 [PoE                   ] POE Interop-PD                                          :: Operational Interoperation With as many PD's as possible | step1: All available PDs tested => All PD's connect and operate as expe
  - AWP-4530    0.240 [PoE                   ] POE Detection-R=22k-C=0.1-Valid                         :: Functional POE PD Detection AUTOMATED test1076.501.1 R=22k-C=0.1 Confirm PD is valid | step1: AUTOMATED test-1076.0201-poe+2.py 2.
  - AWP-15882   0.235 [PoE                   ] Power Cycle                                             :: Connect PD devices to PoE Unit,then power up and power off continuously | step1: Restart reboot the unit after connect to PD devic

### AWPTCM-T37863  |  area:   |  feature: IEEE 802.3bt supports dual signature
folder:/Sanity Check  steps:2  obj:True
ZEPHYR: OBJ: IEEE 802.3bt supports dual signature || On Sifos execute power_bt 1,1 ca 5D cb 5D | iload 1,a i 950;iload 1,b i 550 (this specify the current on
  - AWP-27116   0.334 [PoE                   ] POE support for single-signature power configuration (R :: Objective: Able to operate in single-signature mode where-by: 1. The spare pair is put into manual mode. 2. The data pair is put i
  - AWP-27117   0.330 [PoE                   ] POE support for single-signature power configuration (C :: Objective: Able to operate in single-signature mode where-by: 1. The spare pair is put into manual mode. 2. The data pair is put i
  - AWP-25267   0.291 [PoE                   ] Max Actual Power Consumption                            :: Connect PoE loader to all ports of DUT. And Check DUT power supply is correct. | step1: Connect PoE loader to all ports of DUT Als
  - AWP-26261   0.272 [PoE                   ] power-inline max with the Dynamic Mode                  :: SER-1508.1.3 Support port max value PPL setting with the dynamic power management mode. To confirm Denied PD will be changed to Po
  - AWP-27127   0.254 [PoE                   ] Verify feature cannot be set on non-supported interface :: Verify rejection of command “power-inline four-pair mode single-signature” on ports1.0.1-port1.0.8 | step1: Verify target port is 
  - AWP-27119   0.241 [PoE                   ] Modify an active Bosch camera interface from Single-Sig :: Document the results of modifying an active Bosch camera port from Single-signature to Dual-Signature | step1: Verify target port 
  - AWP-27120   0.239 [PoE                   ] Connect a dual-signature device (Axis camera) to a port :: Document the results of connecting a dual-signature device (Axis camera) to a port that is configured for single-signature mode an
  - AWP-27118   0.237 [PoE                   ] Modify an active Bosch camera interface from Dual-Signa :: Document the results of modifying an active Bosch camera port from Dual-signature to Single-Signature | step1: Verify target port 

### AWPTCM-T37865  |  area:   |  feature: HANP-POE Powered Device does not lose Power during a restart
folder:/Sanity Check  steps:2  obj:False
ZEPHYR: Enable HANP. Attach several PoE capable devices to the DUT. | Warm restart the DUT. awplus#reboot Check log for HANP is ac
  - AWP-24553   0.999 [PoE                   ] HANP-POE Powered Device does not lose Power during a re :: | step1: Enable HANP. Attach several PoE capable devices to the DUT. Check "show power-inline interface detail" and confirm Last =
  - AWP-24560   0.881 [PoE                   ] HANP-POE Powered Device does not lose Power during a so :: Updating the release file does not cause attached PoE devices to power off. | step1: Enable HANP. Attach several PoE capable devic
  - AWP-24554   0.592 [PoE                   ] CLI - HANP Show Commands                                :: Verify system level and interface level configuration for HANP is show on the CLI. Also verify information on when the port negoti
  - AWP-24552   0.537 [PoE                   ] Feature can be disabled on a per-port basis provided it :: | step1: Enable HANP Confirm with "show power-inline" Attach PoE capable device to an POE capable interface. => HANP should be ena
  - AWP-23800   0.369 [Web API               ] POE API: Power-inline HANP                              :: Configure High Availability Network Power (HANP) on the device and on interface. Power to the port will become uninterrupted (no d
  - AWP-24551   0.344 [PoE                   ] Feature can be activated on a system wide basis.        :: HANP can be enabled Globally. | step1: Enable HANP globally awplus(config)# power-inline hanp Check enabled with "show power-inlin
  - AWP-4506    0.279 [PoE                   ] POE CLI-Startup-Power-Disabled                          :: Disabled PoE should not supply power to PDs during startup | step1: Configure the "no power-inline enable" to all ports and save t
  - AWP-11693   0.269 [PoE                   ] POE CFC / controller - Slave failover                   :: | step1: Load device with several PoE loads, including the following power-inline options: no enable (ie not the default) max pri

### AWPTCM-T37866  |  area:   |  feature: Stack ID renumbering
folder:/Sanity Check  steps:1  obj:True
ZEPHYR: OBJ: Renumbering Stack IDs to IDs that are already in use. || Renumber the stack ID of a member (member A) to have the sam
  - AWP-18063   0.507 [Customer Scenario     ] Chassis replace on VCS+ renumbering                     :: Confirm that DUT works Stack ID renumbering.( Project:1765 VCS+ Phase 2 feature) | step1: Disconnect stack member. Reconnect a new
  - AWP-12369   0.335 [ATMF                  ] Node renumbering causes IP address change               :: If a node renumbers, it must also change the IP address | step1: 1. Change the node ID on DUT to match another ATMF node ID (Creat
  - AWP-5290    0.274 [OSPF                  ] Stack Failover Member                                   :: Stack should use VMAC even on Stack Member | step1: Fail-over Member => Check that [Feature] uses virtual-MAC on member
  - AWP-3576    0.270 [Customer Scenario     ] CRP Member-ID conflict VCS devices                      :: On stacked devices cause a VCS duplicate member-ID error which will reboot the slave unit and cause a log message to be recorded i
  - AWP-5281    0.236 [OSPF                  ] Stack Fail-over Member                                  :: Stack member should use the Master MAC when it boots up | step1: Fail-over Member => Check that [Feature] uses MAC of Master when 
  - AWP-17694   0.233 [Green Features (Ecofri] LED State - VCS Enabled                                 :: Verify 7 Segment LED in VCS mode. | step1: Stack ID 1 => LED shows stack ID 1
  - AWP-3647    0.217 [Green Features (Ecofri] Ecofriendly control of XEM-STK Member ID Display        :: Feature controls numerical display | step1: On XEM-STK DUTs fitted to a VCS stack of x900-24X, x900-12XT/S or SBx908 switches. 1. 
  - AWP-23812   0.209 [Web API               ] POE API: Failover VCS/Stack tests                       :: Apteryx should be able to sync across VCS or Stack members for configs to withstand failovers | step1: Configure any PoE interface

### AWPTCM-T37867  |  area:   |  feature: Duplicate stack ID renumbering
folder:/Sanity Check  steps:1  obj:True
ZEPHYR: OBJ: Stack IDs are renumbered and renumbered stack members are rebooted when duplicate is detected. || Configure all members in the stack to have the same stack ID
  - AWP-18063   0.405 [Customer Scenario     ] Chassis replace on VCS+ renumbering                     :: Confirm that DUT works Stack ID renumbering.( Project:1765 VCS+ Phase 2 feature) | step1: Disconnect stack member. Reconnect a new
  - AWP-12369   0.305 [ATMF                  ] Node renumbering causes IP address change               :: If a node renumbers, it must also change the IP address | step1: 1. Change the node ID on DUT to match another ATMF node ID (Creat
  - AWP-17694   0.212 [Green Features (Ecofri] LED State - VCS Enabled                                 :: Verify 7 Segment LED in VCS mode. | step1: Stack ID 1 => LED shows stack ID 1
  - AWP-10989   0.207 [VRF-Lite              ] VRF_Lite and VCS stack Management Vlan IP address dupli :: To test the operation of the stack management vlan ip address with VRF Lite. It should be possible to have duplications of the sta
  - AWP-10135   0.206 [IPv6                  ] Disable VMAC                                            :: Config successfully saved to all stack members and uses master MAC on reboot | step1: Disable virtual-MAC. Check that stack correc
  - AWP-10133   0.196 [IPv6                  ] Enable VMAC                                             :: Enabling VMAC should saved across all stack members | step1: Check that [Feature] uses virtual-MAC when it is enabled. - Requires 
  - AWP-12253   0.195 [ATMF                  ] ATMF Control - Unique internal IDs                      :: Unique internal IDs, tests for: valid network formation. Story 26 | step1: Valid network formation . 1. From existing network remo
  - AWP-10036   0.194 [ICMP                  ] Disable VMAC                                            :: Confirm that stack correctly used Master MAC on reboot | step1: Disable virtual-MAC. Check that stack correctly uses Master MAC on

### AWPTCM-T37868  |  area:   |  feature: Rebooting whole stack for 300 iterations
folder:/Sanity Check  steps:1  obj:True
ZEPHYR: OBJ: Booting stack+ for 300 iterations. || Rebooting whole Stack over night. Atleast 300 iterations
  - AWP-18102   0.375 [Logging               ] Logging - Reboots - No error messages                   :: Test if there is any log errors on DUT after performing reboots. | step1: Perform repeated software reboots. 300 iterations => Aft
  - AWP-18      0.242 [Software Licensing    ] CLI Delete a license to a whole stack                   :: Delete a license to all stack members by one command, while on a master console connection. | step1: Testing to be done on various
  - AWP-10034   0.230 [ICMP                  ] VMAC on - save config and reboot stack                  :: Confirm that config is saved successfully across the whole stack | step1: Check that [Feature] uses virtual-MAC when it is enabled
  - AWP-14      0.220 [Software Licensing    ] CLI Add a license to a whole stack                      :: Add a license to all stack members by one command, while on a master console connection. | step1: Testing to be done on various st
  - AWP-23945   0.199 [ATMF                  ] ATMF Network Size - 300 nodes                           :: ATMF Master nodes need a license. AMF-MASTER-300, | step1: Install 300 nodes license => console warning messages should only appea
  - AWP-6392    0.166 [L2 Switching (L2 Learn] aging timer setting (300 seconds)                       :: Set to default setting | step1: default aging timer setting (300 seconds) => Set to default setting
  - AWP-24605   0.154 [ATMF                  ] stack failover                                          :: stack failover | step1: perform stack failover => confirm atmf network still reforms and no crash or new log errors
  - AWP-28233   0.153 [ATMF                  ] VAA: 60 Containers with 300 nodes each                  :: VAA: 60 Containers with 300 nodes each | step1: Configure 60 areas/container with 300 nodes attached to each area. => Total of 18,

### AWPTCM-T37869  |  area: System LED  |  feature: fan stop
folder:/Sanity Check  steps:1  obj:True
ZEPHYR: OBJ: To check if LED is flashing red colour - 1 flash per period For x510, 7-segment LED flashes "F". || Cause a unit fan to stop (e.g. XEM fan or PSU fan)
  - AWP-11637   0.999 [Environment Monitoring] System LED - fan stop                                   :: To check if LED is flashing red colour - 1 flash per period For x510, 7-segment LED flashes "F". | step1: Cause a unit fan to stop
  - AWP-10432   0.867 [z_Inactive            ] System LED - fan stop                                   :: To check if LED is flashing red colour - 1 flash per period | step1: Cause a unit fan to stop (e.g. XEM fan) => Flashing red colou
  - AWP-11638   0.511 [Environment Monitoring] System LED - faulty XEM                                 :: To check if LED is flashing red colour -4 flash per period | step1: Cause a XEM to fail (e.g - install a faulty XEM or one with an
  - AWP-10433   0.511 [z_Inactive            ] System LED - faulty XEM                                 :: To check if LED is flashing red colour -4 flash per period | step1: Cause a XEM to fail (e.g - install a faulty XEM or one with an
  - AWP-10434   0.440 [z_Inactive            ] System LED - monitored temp                             :: To check if LED is flashing red colour - 6 flash per period | step1: Cause a monitored temperature to alarm by using a heat gun on
  - AWP-11640   0.412 [Environment Monitoring] System LED - concurrent XEM fail, temp and fan fail ala :: To check if LED lit in sequences of flashes | step1: Cause concurrent XEM fail, tempeture and fan fail alarms. => Fault LED lit wi
  - AWP-10435   0.412 [z_Inactive            ] System LED - concurrent XEM fail, temp and fan fail ala :: To check if LED lit in sequences of flashes | step1: Cause concurrent XEM fail, tempeture and fan fail alarms. => Fault LED lit wi
  - AWP-17692   0.329 [Green Features (Ecofri] LED State - System Failure                              :: Verify 7 Segment LED in the event of system failure. | step1: Induced a System Failure like Fan failure, Temparature failure. => "

### AWPTCM-T37870  |  area:   |  feature: Rebooting stack Slave for 300 iterations
folder:/Sanity Check  steps:1  obj:True
ZEPHYR: OBJ: Booting stack for 300 iterations. || Rebooting Stack slave over night. - repeatedly (atleast 300
  - AWP-18102   0.385 [Logging               ] Logging - Reboots - No error messages                   :: Test if there is any log errors on DUT after performing reboots. | step1: Perform repeated software reboots. 300 iterations => Aft
  - AWP-13542   0.206 [Validation Scenario   ] VCS - Slave Failover                                    :: Check and verify <feature> for correct status and functionality. | step1: Fail slave device in stack, check for correct recovery, 
  - AWP-7771    0.206 [Validation Scenario   ] VCS - Slave Failover                                    :: Check and verify <feature> for correct status and functionality. | step1: Fail slave device in stack, check for correct recovery, 
  - AWP-23945   0.204 [ATMF                  ] ATMF Network Size - 300 nodes                           :: ATMF Master nodes need a license. AMF-MASTER-300, | step1: Install 300 nodes license => console warning messages should only appea
  - AWP-13526   0.204 [Validation Scenario   ] VLANs - Slave Failover                                  :: Check and verify VLANs for correct status and functionality. | step1: Fail slave device in stack, check for correct recovery, reco
  - AWP-7663    0.203 [Validation Scenario   ] IGMP - Slave Failover                                   :: Check and verify IGMP for correct status and functionality. | step1: Fail slave device in stack, check for correct recovery, recon
  - AWP-7654    0.203 [Validation Scenario   ] EPSR- Slave Failover                                    :: Check and verify <feature> for correct status and functionality. | step1: Fail slave device in stack, check for correct recovery, 
  - AWP-13504   0.202 [Validation Scenario   ] MLD - Slave Failover                                    :: Check and verify MLD for correct status and functionality. | step1: Fail slave device in stack, check for correct recovery, reconf

### AWPTCM-T37871  |  area:   |  feature: Rebooting stack Master for 300 iterations
folder:/Sanity Check  steps:1  obj:True
ZEPHYR: OBJ: Booting stack for 300 iterations. || Rebooting Stack Master over night. - repeatedly (atleast 300
  - AWP-18102   0.392 [Logging               ] Logging - Reboots - No error messages                   :: Test if there is any log errors on DUT after performing reboots. | step1: Perform repeated software reboots. 300 iterations => Aft
  - AWP-23945   0.240 [ATMF                  ] ATMF Network Size - 300 nodes                           :: ATMF Master nodes need a license. AMF-MASTER-300, | step1: Install 300 nodes license => console warning messages should only appea
  - AWP-12487   0.211 [PIM-SMv6              ] After master fail over, stack uses new mac              :: Existing stack members uses new mac address | step1: Fail over master, stack uses mac of new master => MAC used should be of the m
  - AWP-5281    0.199 [OSPF                  ] Stack Fail-over Member                                  :: Stack member should use the Master MAC when it boots up | step1: Fail-over Member => Check that [Feature] uses MAC of Master when 
  - AWP-12491   0.189 [PIM-SMv6              ] VMAC on, fail over master, stack uses vmac              :: VMAC on, fail over master, new master uses vmac address. | step1: Fail over the master and ensure stack still uses the virtual mac
  - AWP-3543    0.189 [z_Inactive            ] VMAC on, fail over master, stack uses vmac              :: VMAC on, fail over master, new master uses vmac address | step1: Fail over the master and ensure stack still uses the virtual mac 
  - AWP-3539    0.188 [z_Inactive            ] After master fail over, stack uses new mac              :: Existing stack members uses new mac address. | step1: 1. Server sends traffic to a multicast group 2. Client joins the multicast g
  - AWP-5282    0.175 [OSPF                  ] Stack Fail-over Master w/ heavy traffic                 :: OSPF and Traffic should recover and use the MAC of the Master | step1: Fail-over Master while passing heavy traffic across stack-m

### AWPTCM-T37872  |  area:   |  feature: Disable/enable Ecofriendly button
folder:/Sanity Check  steps:10  obj:False
ZEPHYR: no ecofriendly button enable | press ecofriendly button | save and reboot
  - AWP-17642   0.413 [Green Features (Ecofri] Ecofriendly affecting LEDs when eco LED is enabled by H :: Check Ecofriendly button is working | step1: 1. Push mode select button and select LED off mode. 2. Run ecofriendly led command. 3
  - AWP-25116   0.412 [Green Features (Ecofri] Ecofriendly affecting LEDs when eco LED is enabled by H :: Check Ecofriendly button is working | step1: 1. Push mode select button and select LED off mode. 2. Run ecofriendly led command. 3
  - AWP-14562   0.339 [Green Features (Ecofri] Ecofriendly affecting LEDs when eco LED is enabled by H :: | step1: 1. Push mode select button and select LED off mode. 2. Run ecofriendly led command. 3. Run show running-config 4. Push m
  - AWP-14564   0.339 [Green Features (Ecofri] Ecofriendly affecting LEDs when eco LED is enabled by H :: | step1: 1. Push mode select button and select LED off mode. 2. Run ecofriendly led command. 3. Run show running-config 4. Push m
  - AWP-25118   0.335 [Green Features (Ecofri] VCS - Master Failover                                   :: Check Ecofriendly working after Master failover | step1: 1. Run ecofriendly led command. 2. Run show running-config => Ports LED -
  - AWP-25119   0.331 [Green Features (Ecofri] VCS - Member Failover                                   :: Check Ecofriendly working after Member failover | step1: 1. Run ecofriendly led command. 2. Run show running-config => Ports LED -
  - AWP-17643   0.327 [Green Features (Ecofri] Ecofriendly affecting LED when ecofriendly led command  :: Check Ecofriendly working using CLI | step1: 1. Run ecofriendly led command. 2. Run show running-config => Ports LED - turns off 7
  - AWP-25117   0.326 [Green Features (Ecofri] Ecofriendly affecting LED when ecofriendly led command  :: Check Ecofriendly working using CLI | step1: 1. Run ecofriendly led command. 2. Run show running-config => Ports LED - turns off 7

### AWPTCM-T38017  |  area:   |  feature: Web Authentication with a single supplicant
folder:/Temp  steps:3  obj:True
ZEPHYR: OBJ: The supplicant is authenticated by logging into a web access authentication gateway Configurations attached || From web browser of ubuntu desktop, access ip address as fol | use login info as fol
  - AWP-6779    0.350 [Port Authentication   ] Port Authentication (Authenticator) - Single-Supplicant :: Confirm the behavior when the Authenticator is set as Single-Supplicant Mode. | step1: >> Please see the attached files Configure 
  - AWP-18302   0.323 [Web Authentication    ] WEB authentication on gateway(single-host)              :: Confirm that WEB authentication works correctly when DUT works as default gateway. This testcase should be executed since AW+5.4.4
  - AWP-18346   0.309 [Web Authentication    ] WEB authentication on not gateway(single-host / dynamic :: Confirm that WEB authentication works correctly when DUT works as L2 switch(Not gateway). (on single-host / Dynamic VLAN) This tes
  - AWP-18338   0.309 [Web Authentication    ] WEB authentication on gateway(single-host / dynamic vla :: Confirm that WEB authentication works correctly when DUT works as default gateway. (on single-host / Dynamic VLAN) This testcase s
  - AWP-14409   0.304 [Web Authentication    ] auth-web-server gateway / promiscuous mode / Dynamic VL :: | step1: GW-address of supplicant is upper than Authenticator. Configure "auth-web-server gateway" command with IP-address of Gat 
  - AWP-15122   0.299 [Port Authentication   ] Web + MAC authentication - Multi-Mode / no GuestVLAN /  :: [Note] On 5.4.5-0.x, try this test on interface mode or auth-config mode. Confirm that Web + MAC authentication works correctly wi
  - AWP-18305   0.298 [Web Authentication    ] WEB authentication on not gateway(single-host)          :: Confirm that WEB authentication works correctly when DUT works as L2 switch(Not gateway). (on single-host) This testcase should be
  - AWP-14899   0.295 [Web Authentication    ] Web Auth Proxy / Single-host(per port)                  :: Confirm the basic feature of Web Auth Proxy works correctly in the single-host. If your test product supports the feature of VCS, 

### AWPTCM-T38029  |  area:   |  feature: dot1x Authentication with a single supplicant
folder:/Temp  steps:2  obj:True
ZEPHYR: OBJ: After the supplicant || From Supplicant ping radius server 192.168.1.254 * If ping d | From Authenticator, execute CLI: sh auth supplicant brief
  - AWP-6779    0.448 [Port Authentication   ] Port Authentication (Authenticator) - Single-Supplicant :: Confirm the behavior when the Authenticator is set as Single-Supplicant Mode. | step1: >> Please see the attached files Configure 
  - AWP-9616    0.370 [Roaming Authentication] Roaming with dot1x authentication                       :: Test that roaming with dot1x does not work | step1: Roaming with dot1x => Roaming auth supports MAC authentication and Web authent
  - AWP-19440   0.342 [Port Authentication   ] Tri-Auth / single-host /auth guest-vlan forward / descr :: Parallel use tests | step1: Configure as the followings, auth profile test dot1x port-control auto auth-web enable auth-mac enable
  - AWP-21344   0.339 [Roaming Authentication] Move between auth port without roaming auth(802.1x)     :: Confirm that move dot1x supplicant between auth port without roaming auth, then authentication works correctly. | step1: Execute d
  - AWP-6800    0.335 [Port Authentication   ] Set Port Control - Single/Multi-Supplicant Mode         :: Confirm the port control state. | step1: 1. Configure Interface port1.0.1. ! conf t interface port1.0.1 ! 2. Enable port authentic
  - AWP-28452   0.332 [Port Authentication   ] single-supplicant mode with multiple VLAN and re-authen :: Confirm re-authentication works correctly without deleting FDB. | step1: After authed, confirm re-authentication start => FDB shou
  - AWP-6792    0.332 [Port Authentication   ] Parameter Test (Authenticator) - Enable/Disable Re-Auth :: Confirm that the re-authentication option works correctly. | step1: 1. Configure DUT for authentication. 2. Run terminal monitor a
  - AWP-15516   0.326 [RADIUS                ] MAC auth with downloadble ACL on single host port.      :: Confirm that Downloadble ACL works correctly on MAC auth single host port. | step1: Execute Authentication from supplicant, then i

### AWPTCM-T38764  |  area: Boot Menu  |  feature: Boot from TFTPv6
folder:/Bootloader  steps:1  obj:False
  - AWP-25156   0.510 [Bootloader            ] Bootloader - Be able to load by default a release by TF :: Bootloader menu: " 1. Perform one-off boot from alternate source" should perform one-off boot Test that devices can load a release
  - AWP-2748    0.246 [Bootloader            ] Bootloader - Boot with traffic - goto bootloader menu   :: Testing error cases: * Start Bootloader with traffic on the eth0 port Bootloader - Boot with traffic - goto bootloader menu | step
  - AWP-2709    0.242 [Bootloader            ] Bootloader - Boot Menu - Option 2 - 9 - Reset boot from :: Bootloader menu: " 2. Change the default boot source (for advanced users)" should work Bootloader - default load menu - select cli
  - AWP-2670    0.237 [Bootloader            ] Bootloader - Boot Menu - Option 0. Restart              :: Bootloader menu: "0. Restart" should restart Check that the device can be rebooted from the bootloader menu Automated: http://intr
  - AWP-2760    0.237 [Bootloader            ] Bootloader - Diagnostic menu - option 8 - exit menu to  :: Bootloader Diagnostic Shell (Stage 1) menu functionality check Test that Bootloader - Diagnostic menu - option 8 will exit the men
  - AWP-2749    0.236 [Bootloader            ] Bootloader - Boot with traffic - goto diagnostic menu   :: Testing error cases: * Start Bootloader with traffic on the eth0 port Bootloader - Boot with traffic - goto diagnostic menu | step
  - AWP-2672    0.231 [Bootloader            ] Bootloader - Boot Menu - option 0 in sub-menu to go bac :: Bootloader - Be able to back up a menu level by entering '0' (zero) or 'n' ( for no) | step1: select "0" or 'n' to 'Return to a pr
  - AWP-11511   0.226 [File System           ] USB - Boot from USB file with USB file as config file - :: Ensure a device boots with the default release on a USB device and can read a config file from a USB device | step1: Issue Command

### AWPTCM-T38765  |  area: Boot Menu  |  feature: Boot from YMODEM
folder:/Bootloader  steps:1  obj:False
  - AWP-2706    0.630 [Bootloader            ] Bootloader - default load menu - YMODEM                 :: Bootloader menu: " 2. Change the default boot source (for advanced users)" should work Bootloader - default load menu - YMODEM | s
  - AWP-2671    0.403 [Bootloader            ] Bootloader - Boot Menu - Option 1. Perform one-off boot :: Bootloader menu: " 1. Perform one-off boot from alternate source" should perform one-off boot Check that a release can be selected
  - AWP-2695    0.398 [Bootloader            ] Bootloader - Exit bootloader and boot as per default se :: Bootloader menu: 2. Change the default boot source (for advanced users) Bootloader - Exit bootloader and continue to boot as per d
  - AWP-2696    0.398 [Bootloader            ] Bootloader - Access to menu - Change default bootloader :: Bootloader menu: " Able to access menu 2. Change the default boot source (for advanced users)" should work Test that the default b
  - AWP-2674    0.373 [Bootloader            ] Bootloader -device can boot from flash                  :: Bootloader menu: " 1. Perform one-off boot from alternate source" should perform one-off boot Confirm that the device can actually
  - AWP-2694    0.371 [Bootloader            ] Bootloader - test valid options for tftp load but wrong :: Bootloader menu: " 1. Perform one-off boot from alternate source" should perform one-off boot Bootloader - test valid options for 
  - AWP-2711    0.371 [Bootloader            ] Bootloader - Boot Menu - Option 3. Update Bootloader -  :: Bootloader menu: " 3. Update Bootloader" should work. Assume new bootloader is already loaded from earlier testing - test that the
  - AWP-13869   0.339 [Bootloader            ] Bootloader - update bootloader - YMODEM                 :: The purpose of this test is to ensure that the bootloader can be updated via YMODEM. More generically this will also excercise the

### AWPTCM-T38766  |  area: Boot Menu  |  feature: Bootloader Update
folder:/Bootloader  steps:1  obj:False
  - AWP-2748    0.597 [Bootloader            ] Bootloader - Boot with traffic - goto bootloader menu   :: Testing error cases: * Start Bootloader with traffic on the eth0 port Bootloader - Boot with traffic - goto bootloader menu | step
  - AWP-2670    0.532 [Bootloader            ] Bootloader - Boot Menu - Option 0. Restart              :: Bootloader menu: "0. Restart" should restart Check that the device can be rebooted from the bootloader menu Automated: http://intr
  - AWP-2711    0.517 [Bootloader            ] Bootloader - Boot Menu - Option 3. Update Bootloader -  :: Bootloader menu: " 3. Update Bootloader" should work. Assume new bootloader is already loaded from earlier testing - test that the
  - AWP-2744    0.513 [Bootloader            ] Bootloader - Boot Menu - Test with input invalid chars  :: Testing error cases: * try unexpected keys (!@$#$^*(){:”) instead of the standard menu options Test Bootloader cli - check for inv
  - AWP-2719    0.508 [Bootloader            ] Bootloader - Boot Menu - Option 7 - Restore Bootloader  :: Bootloader menu: "7. Restore Bootloader factory settings" should work Bootloader - Restore bootloader factory settings - sanity te
  - AWP-2749    0.507 [Bootloader            ] Bootloader - Boot with traffic - goto diagnostic menu   :: Testing error cases: * Start Bootloader with traffic on the eth0 port Bootloader - Boot with traffic - goto diagnostic menu | step
  - AWP-2709    0.482 [Bootloader            ] Bootloader - Boot Menu - Option 2 - 9 - Reset boot from :: Bootloader menu: " 2. Change the default boot source (for advanced users)" should work Bootloader - default load menu - select cli
  - AWP-2718    0.478 [Bootloader            ] Bootloader - show device bootloader system information  :: Bootloader menu: "6. System information" should work Bootloader - show device bootloader system information Automated: http://intr

### AWPTCM-T38767  |  area: Boot Menu  |  feature: Restore Factory Settings
folder:/Bootloader  steps:1  obj:False
  - AWP-2719    0.718 [Bootloader            ] Bootloader - Boot Menu - Option 7 - Restore Bootloader  :: Bootloader menu: "7. Restore Bootloader factory settings" should work Bootloader - Restore bootloader factory settings - sanity te
  - AWP-2722    0.523 [Bootloader            ] Bootloader - Restore bootloader factory settings - tftp :: Bootloader menu: "7. Restore Bootloader factory settings" should work Bootloader - Restore bootloader factory settings - tftp sett
  - AWP-2723    0.478 [Bootloader            ] Bootloader - Restore bootloader factory settings - rele :: Bootloader menu: "7. Restore Bootloader factory settings" should work Bootloader - Restore bootloader factory settings - e.g. defa
  - AWP-2720    0.458 [Bootloader            ] Bootloader - Restore bootloader factory settings - deve :: Bootloader menu: "7. Restore Bootloader factory settings" should work Bootloader - Restore bootloader factory settings - developer
  - AWP-2721    0.448 [Bootloader            ] Bootloader - Restore bootloader factory settings - cons :: Bootloader menu: "7. Restore Bootloader factory settings" should work Bootloader - Restore bootloader factory settings - console s
  - AWP-11242   0.377 [File System           ] Perform restore from media when device continuously reb :: Create a situation that would cause the device to boot continuously | step1: 1.Load device and issue ""no boot system"" 2.No back 
  - AWP-2696    0.335 [Bootloader            ] Bootloader - Access to menu - Change default bootloader :: Bootloader menu: " Able to access menu 2. Change the default boot source (for advanced users)" should work Test that the default b
  - AWP-19571   0.335 [Bootloader            ] Bootloader - Boot Menu - Option 8 - Developer menu opti :: Test that the developer menu will appear when configured. | step1: Enter developer menu and check the developer menu appears. => P
