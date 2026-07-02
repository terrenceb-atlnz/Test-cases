# Rerank batch 11  (cases 330..359)

### AWPTCM-T44334  |  area: AdvancedManagement AMFSec  |  feature: Openflow Inactivity probe
folder:/New Platform Template/Advanced Management  steps:1  obj:False
  - AWP-25798   0.522 [OpenFlow              ] Inactive Probe Timer - Long Run                         :: Confirm that the problem does not occur while long run testing (1 night) if Inactivity Probe is set 5 seconds. | step1: Set Inacti
  - AWP-29448   0.497 [OpenFlow              ] Inactive Probe Timer - Long Run                         :: Confirm that the problem does not occur while long run testing (1 night) if Inactivity Probe is set 28 seconds. | step1: Set Inact
  - AWP-26392   0.497 [OpenFlow              ] Inactive Probe Timer - Long Run                         :: Confirm that the problem does not occur while long run testing (1 night) if Inactivity Probe is set 28 seconds. | step1: Set Inact
  - AWP-29447   0.418 [OpenFlow              ] Inactive Probe Timer                                    :: Confirm that Inactive Probe Timer works in the below case. - 5 seconds - 10 seconds (default) - 25 seconds - 60 seconds *If SESC d
  - AWP-25770   0.418 [OpenFlow              ] Inactive Probe Timer                                    :: Confirm that Inactive Probe Timer works in the below case. - 5 seconds - 10 seconds (default) - 25 seconds - 60 seconds *If SESC d
  - AWP-26391   0.418 [OpenFlow              ] Inactive Probe Timer                                    :: Confirm that Inactive Probe Timer works in the below case. - 5 seconds - 10 seconds (default) - 25 seconds - 60 seconds *If SESC d
  - AWP-29047   0.363 [SD-WAN                ] SD WAN _ http probe                                     :: to test functionality of http link mon probe | step1: configure http linkmon probe => probe can be configured
  - AWP-3550    0.344 [DHCP                  ] DHCP server - Command line test: ARP Probe              :: Test for Ping/ARP Probe commands | step1: •probe enable •no probe enable •probe type {ping|arp} •no probe type •probe packets <0-1

### AWPTCM-T44335  |  area: Other DataCenterApplication  |  feature: Resilient Ethernet Fabric
folder:/New Platform Template/Other  steps:1  obj:False
  - AWP-9072    0.323 [z_Inactive            ] QoS:fabric-queue map - configured                       :: QoS:fabric-queue map - configured | step1: Map egress queue to fabric queue. Need to find counters that confirm fa queue usage. No
  - AWP-9071    0.309 [QoS                   ] QoS:fabric-queue map - default                          :: Verify default queue configuration Egress Queue Fabric Queue ----------------------- 0 0 1 0 2 1 3 1 4 2 5 2 6 3 7 3 | step1: veri
  - AWP-9070    0.229 [QoS                   ] QoS: Global QoS - Fabric Queue Strict/WRR Commands & sh :: Verify that QoS fabric queues can be set to WRR with a weight - all queues | step1: Test that QoS fabric queues can be set to WRR 
  - AWP-21773   0.183 [PPP                   ] PPP IP Borrow from ethernet interface                   :: Verify that PPP interface can borrow IP address from an ethernet interface. | step1: Configure PPP interface to borrow IP address 
  - AWP-12167   0.176 [QoS                   ] QoS: fabric adapter queueing                            :: Use traffic to verify fabric adapter qos is correctly implemented and configurable: | step1: This method needs to be verified Syst
  - AWP-26686   0.166 [CFM                   ] CLI:show ethernet cfm domain                            :: Verify "show Ethernet cfm domain" and details option command. | step1: Issue the "show Ethernet cfm domain" command and verify: sh
  - AWP-3518    0.165 [PIM-SM                ] Redundant L2 network and network disruption             :: Testing multicast over a L2 redundant network, traffic recovers after network disruption | step1: Configure a resilient L2 network
  - AWP-12472   0.164 [PIM-SMv6              ] Redundant L2 network and network disruption             :: Testing multicast over a L2 redundant network, traffic recovers after network disruption | step1: Configure a resilient L2 network

### AWPTCM-T44336  |  area: Other DataCenterApplication  |  feature: DCB/DCBX
folder:/New Platform Template/Other  steps:1  obj:False
  - AWP-7025    0.302 [Software Licensing    ] License Bundle - Adv L3 (ROW) (x900 or SBx908)          :: License bundle - Adv L3 (ROW)(x900 or SBx908) Functional test for each of the features within the license bundle. So it would be n
  - AWP-7027    0.301 [Software Licensing    ] License Bundle - Adv L3 (Japan) (x900 or SBx908)        :: License bundle - Adv L3 (Japan)(x900 or SBx908) Functional test for each of the features within the license bundle. So it would be
  - AWP-13675   0.268 [Software Licensing    ] License Bundle - Adv L3 (ROW) (x610)                    :: License bundle - L3 (ROW) for x610 platform | step1: x610 Advanced L3 License All Base License features plus: OSPF-Full BGP-64 BGP
  - AWP-13684   0.267 [Software Licensing    ] License Bundle - Adv L3 (Japan) (x610)                  :: License bundle - L3 (Japan) for x610 platform | step1: x610 Advanced L3 License All Base License features plus: OSPF-Full BGP-64 B
  - AWP-8292    0.092 [IPv4                  ] Secondary IP in other interface                         :: Secondary ip should work in other interface | step1: Testing of Secondary IP addresses is being done in other places. i.e PIM etc 
  - AWP-6851    0.089 [Port Authentication   ] Port Authentication and Tagged port (Other Port)        :: Port Authentication and Tagged port (Other Port) | step1: Refer to 4.4.1.doc => Refer to 4.4.1.doc Confirm the authentication succ
  - AWP-15361   0.088 [Web Authentication    ] Web Authentication and Tagged port (Other Port)         :: Web Authentication and Tagged port (Other Port) | step1: Refer to 4.5.1.doc => Refer to 4.5.1.doc
  - AWP-24510   0.082 [ATMF                  ] Check ATMF provisioning of other nodes will be supporte :: Check ATMF provisioning of other nodes will be supported | step1: Check the support of ATMF provisioning of other nodes => Ensure 

### AWPTCM-T44337  |  area: Other DataCenterApplication  |  feature: Hypervisor aware
folder:/New Platform Template/Other  steps:1  obj:False
  - AWP-22220   0.453 [ATMF                  ] Same feature functionality as a VAA on hypervisor       :: | step1: Test various commands that would run on a VAA. Note that some of these commands will be included in othert test cases. S
  - AWP-26715   0.239 [CFM                   ] Functionality:MEP VLAN Aware - Operator Level           :: Verify the functionality of a VLAN aware MEP at the Operator level. | step1: Verify the functionality of a VLAN aware MEP at the O
  - AWP-26713   0.236 [CFM                   ] Functionality:MEP VLAN Aware - Customer Level           :: Verify the functionality of a VLAN aware MEP at the customer level. | step1: Verify the functionality of a VLAN aware MEP at the c
  - AWP-26714   0.235 [CFM                   ] Functionality:MEP VLAN Aware - Provider Level           :: Verify the functionality of a VLAN aware MEP at the Provider level. | step1: Verify the functionality of a VLAN aware MEP at the c
  - AWP-14600   0.223 [VRF-Lite              ] DNS Relay VRF aware - DNS client not VRF aware Ping ope :: 1739.2.05 DNS Client will not be made vrf-aware. Having a non-VRF aware DNS client means that if the ping command contains a URL, 
  - AWP-20939   0.222 [VM - AW-Plus on Virtua] VM : VM software restart                                :: VMware vSphere Hypervisor will be supported. | step1: Restart the Vshpere Sever => VAA should work fine after Vshpere Server resta
  - AWP-14603   0.220 [VRF-Lite              ] DNS Relay VRF aware - DNS client not VRF aware SSH oper :: S1739.2.05 DNS Client will not be made vrf-aware. Having a non-VRF aware DNS client means that if the SSH command contains a URL, 
  - AWP-14602   0.220 [VRF-Lite              ] DNS Relay VRF aware - DNS client not VRF aware Telnet o :: S1739.2.05 DNS Client will not be made vrf-aware. Having a non-VRF aware DNS client means that if the telnet command contains a UR

### AWPTCM-T44338  |  area: Other DataCenterApplication  |  feature: OVSDB
folder:/New Platform Template/Other  steps:1  obj:False
  - AWP-8292    0.358 [IPv4                  ] Secondary IP in other interface                         :: Secondary ip should work in other interface | step1: Testing of Secondary IP addresses is being done in other places. i.e PIM etc 
  - AWP-6851    0.345 [Port Authentication   ] Port Authentication and Tagged port (Other Port)        :: Port Authentication and Tagged port (Other Port) | step1: Refer to 4.4.1.doc => Refer to 4.4.1.doc Confirm the authentication succ
  - AWP-15361   0.342 [Web Authentication    ] Web Authentication and Tagged port (Other Port)         :: Web Authentication and Tagged port (Other Port) | step1: Refer to 4.5.1.doc => Refer to 4.5.1.doc
  - AWP-24510   0.321 [ATMF                  ] Check ATMF provisioning of other nodes will be supporte :: Check ATMF provisioning of other nodes will be supported | step1: Check the support of ATMF provisioning of other nodes => Ensure 
  - AWP-4503    0.319 [PoE                   ] POE CLI-Other-Show                                      :: PoE does not affect other show commands | step1: Set POE on different ports then check the other show commands show mem show proce
  - AWP-9370    0.310 [xSTP                  ] Interop with RSTP & MSTP on other devices.              :: | step1: Interop with RSTP & MSTP on other devices.
  - AWP-27178   0.295 [AWC-lite              ] use FW for other model                                  :: | step1: Confirm that error message of failure of FW update is dispalyed on router.
  - AWP-9846    0.276 [DHCP Snooping         ] DHCP Snooping - other ACL configuration                 :: Confirm that behavior is predictable as per ACL configuration | step1: Other ACL configurations that include DHCPSNOOPING - eg => 

### AWPTCM-T44339  |  area: Other DataCenterApplication  |  feature: VxLAN
folder:/New Platform Template/Other  steps:1  obj:False
  - AWP-8292    0.358 [IPv4                  ] Secondary IP in other interface                         :: Secondary ip should work in other interface | step1: Testing of Secondary IP addresses is being done in other places. i.e PIM etc 
  - AWP-6851    0.345 [Port Authentication   ] Port Authentication and Tagged port (Other Port)        :: Port Authentication and Tagged port (Other Port) | step1: Refer to 4.4.1.doc => Refer to 4.4.1.doc Confirm the authentication succ
  - AWP-15361   0.342 [Web Authentication    ] Web Authentication and Tagged port (Other Port)         :: Web Authentication and Tagged port (Other Port) | step1: Refer to 4.5.1.doc => Refer to 4.5.1.doc
  - AWP-24510   0.321 [ATMF                  ] Check ATMF provisioning of other nodes will be supporte :: Check ATMF provisioning of other nodes will be supported | step1: Check the support of ATMF provisioning of other nodes => Ensure 
  - AWP-4503    0.319 [PoE                   ] POE CLI-Other-Show                                      :: PoE does not affect other show commands | step1: Set POE on different ports then check the other show commands show mem show proce
  - AWP-9370    0.310 [xSTP                  ] Interop with RSTP & MSTP on other devices.              :: | step1: Interop with RSTP & MSTP on other devices.
  - AWP-27178   0.295 [AWC-lite              ] use FW for other model                                  :: | step1: Confirm that error message of failure of FW update is dispalyed on router.
  - AWP-9846    0.276 [DHCP Snooping         ] DHCP Snooping - other ACL configuration                 :: Confirm that behavior is predictable as per ACL configuration | step1: Other ACL configurations that include DHCPSNOOPING - eg => 

### AWPTCM-T44340  |  area: Other DataCenterApplication  |  feature: NVGRE
folder:/New Platform Template/Other  steps:1  obj:False
  - AWP-8292    0.358 [IPv4                  ] Secondary IP in other interface                         :: Secondary ip should work in other interface | step1: Testing of Secondary IP addresses is being done in other places. i.e PIM etc 
  - AWP-6851    0.345 [Port Authentication   ] Port Authentication and Tagged port (Other Port)        :: Port Authentication and Tagged port (Other Port) | step1: Refer to 4.4.1.doc => Refer to 4.4.1.doc Confirm the authentication succ
  - AWP-15361   0.342 [Web Authentication    ] Web Authentication and Tagged port (Other Port)         :: Web Authentication and Tagged port (Other Port) | step1: Refer to 4.5.1.doc => Refer to 4.5.1.doc
  - AWP-24510   0.321 [ATMF                  ] Check ATMF provisioning of other nodes will be supporte :: Check ATMF provisioning of other nodes will be supported | step1: Check the support of ATMF provisioning of other nodes => Ensure 
  - AWP-4503    0.319 [PoE                   ] POE CLI-Other-Show                                      :: PoE does not affect other show commands | step1: Set POE on different ports then check the other show commands show mem show proce
  - AWP-9370    0.310 [xSTP                  ] Interop with RSTP & MSTP on other devices.              :: | step1: Interop with RSTP & MSTP on other devices.
  - AWP-27178   0.295 [AWC-lite              ] use FW for other model                                  :: | step1: Confirm that error message of failure of FW update is dispalyed on router.
  - AWP-9846    0.276 [DHCP Snooping         ] DHCP Snooping - other ACL configuration                 :: Confirm that behavior is predictable as per ACL configuration | step1: Other ACL configurations that include DHCPSNOOPING - eg => 

### AWPTCM-T44341  |  area: Other DataCenterApplication  |  feature: VEPA
folder:/New Platform Template/Other  steps:1  obj:False
  - AWP-8292    0.358 [IPv4                  ] Secondary IP in other interface                         :: Secondary ip should work in other interface | step1: Testing of Secondary IP addresses is being done in other places. i.e PIM etc 
  - AWP-6851    0.345 [Port Authentication   ] Port Authentication and Tagged port (Other Port)        :: Port Authentication and Tagged port (Other Port) | step1: Refer to 4.4.1.doc => Refer to 4.4.1.doc Confirm the authentication succ
  - AWP-15361   0.342 [Web Authentication    ] Web Authentication and Tagged port (Other Port)         :: Web Authentication and Tagged port (Other Port) | step1: Refer to 4.5.1.doc => Refer to 4.5.1.doc
  - AWP-24510   0.321 [ATMF                  ] Check ATMF provisioning of other nodes will be supporte :: Check ATMF provisioning of other nodes will be supported | step1: Check the support of ATMF provisioning of other nodes => Ensure 
  - AWP-4503    0.319 [PoE                   ] POE CLI-Other-Show                                      :: PoE does not affect other show commands | step1: Set POE on different ports then check the other show commands show mem show proce
  - AWP-9370    0.310 [xSTP                  ] Interop with RSTP & MSTP on other devices.              :: | step1: Interop with RSTP & MSTP on other devices.
  - AWP-27178   0.295 [AWC-lite              ] use FW for other model                                  :: | step1: Confirm that error message of failure of FW update is dispalyed on router.
  - AWP-9846    0.276 [DHCP Snooping         ] DHCP Snooping - other ACL configuration                 :: Confirm that behavior is predictable as per ACL configuration | step1: Other ACL configurations that include DHCPSNOOPING - eg => 

### AWPTCM-T44342  |  area: Other DataCenterApplication  |  feature: TRILL
folder:/New Platform Template/Other  steps:1  obj:False
  - AWP-8292    0.358 [IPv4                  ] Secondary IP in other interface                         :: Secondary ip should work in other interface | step1: Testing of Secondary IP addresses is being done in other places. i.e PIM etc 
  - AWP-6851    0.345 [Port Authentication   ] Port Authentication and Tagged port (Other Port)        :: Port Authentication and Tagged port (Other Port) | step1: Refer to 4.4.1.doc => Refer to 4.4.1.doc Confirm the authentication succ
  - AWP-15361   0.342 [Web Authentication    ] Web Authentication and Tagged port (Other Port)         :: Web Authentication and Tagged port (Other Port) | step1: Refer to 4.5.1.doc => Refer to 4.5.1.doc
  - AWP-24510   0.321 [ATMF                  ] Check ATMF provisioning of other nodes will be supporte :: Check ATMF provisioning of other nodes will be supported | step1: Check the support of ATMF provisioning of other nodes => Ensure 
  - AWP-4503    0.319 [PoE                   ] POE CLI-Other-Show                                      :: PoE does not affect other show commands | step1: Set POE on different ports then check the other show commands show mem show proce
  - AWP-9370    0.310 [xSTP                  ] Interop with RSTP & MSTP on other devices.              :: | step1: Interop with RSTP & MSTP on other devices.
  - AWP-27178   0.295 [AWC-lite              ] use FW for other model                                  :: | step1: Confirm that error message of failure of FW update is dispalyed on router.
  - AWP-9846    0.276 [DHCP Snooping         ] DHCP Snooping - other ACL configuration                 :: Confirm that behavior is predictable as per ACL configuration | step1: Other ACL configurations that include DHCPSNOOPING - eg => 

### AWPTCM-T44343  |  area: Other DataCenterApplication  |  feature: FIP Snooping
folder:/New Platform Template/Other  steps:1  obj:False
  - AWP-9713    0.471 [DHCP Snooping         ] show ip dhcp snooping                                   :: "show ip dhcp snooping" should show correct output | step1: show ip dhcp snooping => Ref UIDv8 for show ip dhcp snooping Command i
  - AWP-8402    0.455 [MLD Snooping          ] MLD Snooping Interop with IGMP Snooping                 :: | step1: Ensure that both IGMP Snooping and MLD Snooping can operate independently of one another
  - AWP-8375    0.447 [MLD Snooping          ] Logging for MLD snooping                                :: | step1: Logging exists for MLD Snooping
  - AWP-9921    0.442 [DHCP Snooping         ] DHCP Snooping on base license                           :: Confirm that dhcp snooping works on base license | step1: DHCP Snooping works on Base license. => Need to remove any other feature
  - AWP-9826    0.438 [DHCP Snooping         ] DHCP Snooping disabled - check file                     :: Check file written when DHCP Snooping is disabled | step1: File written when DHCP Snooping is disabled => FUNCTIONALITY REMOVED
  - AWP-9691    0.430 [DHCP Snooping         ] CLI Test: ip dhcp-snooping                              :: CLI test for "ip dhcp-snooping" command. Use this command to enable DHCP snooping on one or more VLANs. | step1: Issue the followi
  - AWP-18463   0.422 [Validation Scenario   ] DHCP Snooping - Feature options                         :: To check other options within DHCP Snooping Feature. | step1: Explore Other feature options i.e. DHCP Snooping ACL - DHCP Snooping
  - AWP-9714    0.422 [DHCP Snooping         ] show ip dhcp snooping acl                               :: "show ip dhcp snooping acl" should show correct output | step1: show ip dhcp snooping acl => Ref UIDv8 for show ip dhcp snooping a

### AWPTCM-T44378  |  area: IPv4  |  feature: UDP Broadcast Helper
folder:/New Platform Template/IPv4  steps:1  obj:False
  - AWP-6689    0.651 [IP Helper             ] IP helper performance                                   :: Test that IP helper works on higher size UDP broadcast packets | step1: IP Helper Performance => Confirm feature performance and b
  - AWP-19388   0.593 [z_ATKK_Inquiry_Based  ] IB-54:UDP broadcast helper on single interface          :: Scope Verify UDP broadcast helper works in case of single interface (i.e. vlan1) | step1: Send UDP broadcast packet (10000/UDP) fr
  - AWP-6686    0.487 [IP Helper             ] Disable ip helper feature                               :: Test that no packet is being forwarded when feature is disabled | step1: Incomplete setting => The feature is disabled with either
  - AWP-6684    0.480 [IP Helper             ] routing test using two devices                          :: Test that udp broadcast is forwarded | step1: Routing test in two devices are used. => When two devices enabled ip helper are conn
  - AWP-9898    0.446 [DHCP Snooping         ] DHCP Snooping and IP Helper                             :: Security should still apply | step1: DHCP Snooping and IP Helper => Security should still apply
  - AWP-6682    0.444 [IP Helper             ] Transmission to a unicast address                       :: Test that packet will be transmitted to the specified address | step1: 1.Send configured udp broadcast packet. Confirm udp packet 
  - AWP-6676    0.426 [IP Helper             ] Command Line Handler - ip helper-address                :: Command Line Interface tests - ip helper commands executed as expected | step1: ip helper-address IPADDR / no ip helper-address IP
  - AWP-6688    0.420 [IP Helper             ] IP helper on stack environment                          :: Test that IP helper works correctly when route to the destination host is changed. | step1: Stack environment => When the route to

### AWPTCM-T44449  |  area: Pre-SVT  |  feature: Throughput
folder:/New Platform Template/Pre-SVT  steps:1  obj:True
ZEPHYR: OBJ: There are only 4 test need to do ATM and all auto test, details at: https://wiki.atlnz.lc/awpwiki/index.php/Project_plat ||
  - AWP-6443    0.267 [L2 Switching (L2 Learn] Scriptmate Address Cache Size test ATKK 5.1.1.2 Overlap :: Note that this automatic test does not work well with Marvell Silicon. Good as a stress test though. No specific pass criteria is 
  - AWP-27242   0.243 [AWC-lite              ] pre-authentication enable                               :: | step1: pre-authentication enable Confirm that pre-authentication is enabled on router.
  - AWP-23302   0.219 [Feature Not In This Li] Throughput test                                         :: To test that there were no significant performance degradation of DUT. | step1: Perform throughput test. Can insert specific proto
  - AWP-26079   0.203 [L3 Switching          ] CPU throughput test                                     :: This test is to check performance before and after CPSS upgrade is maintained specifically CPU through put. | step1: Run CPU throu
  - AWP-9925    0.187 [DHCP Snooping         ] DHCP Throughput - enabled on many vlans                 :: Reasonable behaviour to be defined with many vlans enabled | step1: Find DHCP throughput performance when enabled on lots of vlans
  - AWP-29625   0.177 [OpenFlow              ] OpenFlow Software Throughput (1chip)                    :: Measure the performance of software forwarding in OpenFlow-port by RFC2544. | step1: Set up the environment. (Please refer to the 
  - AWP-29384   0.177 [OpenFlow              ] OpenFlow Software Throughput (1chip)                    :: Measure the performance of software forwarding in OpenFlow-port by RFC2544. | step1: Set up the environment. (Please refer to the 
  - AWP-29626   0.176 [OpenFlow              ] OpenFlow Software Throughput (2chip)                    :: Measure the performance of software forwarding in OpenFlow-port by RFC2544. | step1: Set up the environment. (Please refer to the 

### AWPTCM-T44450  |  area: Pre-SVT  |  feature: FlowControl
folder:/New Platform Template/Pre-SVT  steps:1  obj:True
ZEPHYR: OBJ: There are only 4 test need to do ATM and all auto test, details at: https://wiki.atlnz.lc/awpwiki/index.php/Project_plat ||
  - AWP-10153   0.279 [Pause Control/Flow Con] Show flowcontrol command                                :: Flowcontrol for interface should show received admin "ON" | step1: Issue command ' show flowcontrol ' Note: Flowcontrol on and rec
  - AWP-14528   0.267 [Pause Control/Flow Con] Flowcontrol both command                                :: Able to execute flowcontrol both command | step1: Issue the command in interface mode: ' flowcontrol both ' => Confirm that the co
  - AWP-6443    0.263 [L2 Switching (L2 Learn] Scriptmate Address Cache Size test ATKK 5.1.1.2 Overlap :: Note that this automatic test does not work well with Marvell Silicon. Good as a stress test though. No specific pass criteria is 
  - AWP-10148   0.243 [Pause Control/Flow Con] Flowcontrol send on command                             :: Able to execute flowcontrol send on command | step1: Issue the command in interface mode: ' flowcontrol send on ' Note: Marvell pr
  - AWP-27242   0.240 [AWC-lite              ] pre-authentication enable                               :: | step1: pre-authentication enable Confirm that pre-authentication is enabled on router.
  - AWP-10151   0.232 [Pause Control/Flow Con] Flowcontrol receive on command                          :: Able to execute flowcontrol receive on command | step1: Issue the command in interface mode: ' flow control receive on ' => Confir
  - AWP-10163   0.230 [Pause Control/Flow Con] x908: Show flowcontrol command                          :: x908: Flowcontrol for interface should show received admin "ON" | step1: Issue command "show flowcontrol" [flow control receive mu
  - AWP-10161   0.221 [Pause Control/Flow Con] x908: Flowcontrol receive on command                    :: x908: Able to execute flowcontrol receive on command | step1: Issue the command "flow control receive on" from the interface => No

### AWPTCM-T44451  |  area: Pre-SVT  |  feature: PortMirror
folder:/New Platform Template/Pre-SVT  steps:1  obj:True
ZEPHYR: OBJ: There are only 4 test need to do ATM and all auto test, details at: https://wiki.atlnz.lc/awpwiki/index.php/Project_plat ||
  - AWP-6443    0.283 [L2 Switching (L2 Learn] Scriptmate Address Cache Size test ATKK 5.1.1.2 Overlap :: Note that this automatic test does not work well with Marvell Silicon. Good as a stress test though. No specific pass criteria is 
  - AWP-27242   0.258 [AWC-lite              ] pre-authentication enable                               :: | step1: pre-authentication enable Confirm that pre-authentication is enabled on router.
  - AWP-27068   0.180 [UFO                   ] Verify UFO - Reboot                                     :: Verify UFO functions correctly after a reboot. Upstream Forwarding Only TFS https://intranet.atlnz.lc/awpwiki/index.php/Upstream_F
  - AWP-27069   0.172 [UFO                   ] Verify UFO - Upgrade                                    :: Verify UFO functions correctly after an upgrade. Upstream Forwarding Only TFS https://intranet.atlnz.lc/awpwiki/index.php/Upstream
  - AWP-27067   0.166 [UFO                   ] Verify UFO - Power Cycle                                :: Verify UFO functions correctly after a power cycle. Upstream Forwarding Only TFS https://intranet.atlnz.lc/awpwiki/index.php/Upstr
  - AWP-27099   0.162 [UFO                   ] Verify UFO stacking failover                            :: Verify UFO functions with a stacking failover. Upstream Forwarding Only TFS section 3.1.2.16 https://intranet.atlnz.lc/awpwiki/ind
  - AWP-24522   0.161 [ATMF                  ] Check the support of event logging                      :: Event logging to email will be supported | step1: setup SMTP mail server/relay on testbox instructions about how to set up the mai
  - AWP-27041   0.159 [UFO                   ] Verify: show platform                                   :: Verify the "show platform table ufo" command. Upstream Forwarding Only TFS section 4.1 https://intranet.atlnz.lc/awpwiki/index.php

### AWPTCM-T44452  |  area: Pre-SVT  |  feature: QoS
folder:/New Platform Template/Pre-SVT  steps:1  obj:True
ZEPHYR: OBJ: There are only 4 test need to do ATM and all auto test, details at: https://wiki.atlnz.lc/awpwiki/index.php/Project_plat ||
  - AWP-6443    0.270 [L2 Switching (L2 Learn] Scriptmate Address Cache Size test ATKK 5.1.1.2 Overlap :: Note that this automatic test does not work well with Marvell Silicon. Good as a stress test though. No specific pass criteria is 
  - AWP-27242   0.246 [AWC-lite              ] pre-authentication enable                               :: | step1: pre-authentication enable Confirm that pre-authentication is enabled on router.
  - AWP-27068   0.172 [UFO                   ] Verify UFO - Reboot                                     :: Verify UFO functions correctly after a reboot. Upstream Forwarding Only TFS https://intranet.atlnz.lc/awpwiki/index.php/Upstream_F
  - AWP-9065    0.167 [QoS                   ] QoS globally enabled                                    :: Verify QoS commands are accepted when QoS is globally enabled | step1: qos can be enabled with the command: mls qos enable => Sele
  - AWP-27069   0.164 [UFO                   ] Verify UFO - Upgrade                                    :: Verify UFO functions correctly after an upgrade. Upstream Forwarding Only TFS https://intranet.atlnz.lc/awpwiki/index.php/Upstream
  - AWP-27067   0.158 [UFO                   ] Verify UFO - Power Cycle                                :: Verify UFO functions correctly after a power cycle. Upstream Forwarding Only TFS https://intranet.atlnz.lc/awpwiki/index.php/Upstr
  - AWP-27099   0.154 [UFO                   ] Verify UFO stacking failover                            :: Verify UFO functions with a stacking failover. Upstream Forwarding Only TFS section 3.1.2.16 https://intranet.atlnz.lc/awpwiki/ind
  - AWP-24522   0.154 [ATMF                  ] Check the support of event logging                      :: Event logging to email will be supported | step1: setup SMTP mail server/relay on testbox instructions about how to set up the mai

### AWPTCM-T44453  |  area:   |  feature: ART Limits Test
folder:/New Platform Template/ART Limits Test  steps:0  obj:True
ZEPHYR: OBJ: In order to pass 1341_limits testsuite tester needs to fill out spreadsheet /home/st-art/tools/ Limit s_for_New_Platform || In order to pass 1341_limits testsuite tester needs to fill out spreads
  - AWP-2729    0.258 [Bootloader            ] Bootloader - Access to u-boot shell                     :: Test Functionality of Bootloader shell. Test Bootloader - Access to u-boot shell Automated: http://intranet.atlnz.lc/systest/ATPyL
  - AWP-2691    0.238 [Bootloader            ] Bootloader - test all valid options for tftp load       :: Bootloader menu: " 1. Perform one-off boot from alternate source" should perform one-off boot Bootloader - test all valid options 
  - AWP-2718    0.212 [Bootloader            ] Bootloader - show device bootloader system information  :: Bootloader menu: "6. System information" should work Bootloader - show device bootloader system information Automated: http://intr
  - AWP-2670    0.198 [Bootloader            ] Bootloader - Boot Menu - Option 0. Restart              :: Bootloader menu: "0. Restart" should restart Check that the device can be rebooted from the bootloader menu Automated: http://intr
  - AWP-2639    0.196 [Bootloader            ] Boot system - Boot with a set release                   :: * Software upgrade must be a one-hit process - boot with a set release Automated: http://intranet.atlnz.lc/systest/ATPyLib/regress
  - AWP-2645    0.194 [Bootloader            ] Boot system - setting a release file that is not a rele :: * Software upgrade must be a one-hit process - can not install non-release file Automated: http://intranet.atlnz.lc/systest/ATPyLi
  - AWP-2642    0.188 [Bootloader            ] Boot system - Setting current and backup release        :: * Software upgrade must be a one-hit process - boot image and backup should not be set to the same file Automated: http://intranet
  - AWP-2650    0.186 [Bootloader            ] Boot system - backup release - setting a backup file th :: Test for when setting a backup file that is not a release but file name format is correct. Automated: http://intranet.atlnz.lc/sys

### AWPTCM-T45069  |  area:   |  feature: Boot from USB
folder:/Bootloader  steps:1  obj:True
ZEPHYR: OBJ: To verify that device can boot from the bootloader loaded in USB ||
  - AWP-11505   0.589 [File System           ] USB - Boot commands: boot system - single CFC           :: Check the current software can be set to file on USB device | step1: Issue commands: configure terminal boot system usb:/usb_relea
  - AWP-11504   0.545 [File System           ] USB - Boot commands: boot config-file - single CFC      :: Check boot config file can be set from command line boot options | step1: Issue commands: configure terminal boot config-file usb:
  - AWP-11511   0.491 [File System           ] USB - Boot from USB file with USB file as config file - :: Ensure a device boots with the default release on a USB device and can read a config file from a USB device | step1: Issue Command
  - AWP-11509   0.480 [File System           ] USB - Boot from USB file with USB file as config file - :: Ensure a device boots with the default release on a USB device and can read a config file from a USB device | step1: Issue Command
  - AWP-11507   0.445 [File System           ] USB - Boot commands: boot config-file - dual CFC        :: Ensure the boot config file can be set via the masters boot command when 2 CFC cards are present. File must auto-sync over stack t
  - AWP-11461   0.439 [File System           ] File - clearing all - USB                               :: Delete USB file using the "delete usb" command | step1: Issue "delete usb:/ <file>" command => File in the USB is deleted
  - AWP-2702    0.436 [Bootloader            ] Bootloader - test that device boot fails with default b :: Bootloader menu: " 2. Change the default boot source (for advanced users)" should work Test that device cannot load if release fil
  - AWP-11508   0.430 [File System           ] USB - Boot commands: boot system - dual CFC             :: Ensure the boot release can be set via the masters boot command when 2 CFC cards are present. File must auto-sync over stack to 's

### AWPTCM-T45070  |  area:   |  feature: Restore bootloader factory settings
folder:/Bootloader  steps:3  obj:False
ZEPHYR: Sanity test | Developer mode is cleared | TFTP settings reset
  - AWP-2719    0.702 [Bootloader            ] Bootloader - Boot Menu - Option 7 - Restore Bootloader  :: Bootloader menu: "7. Restore Bootloader factory settings" should work Bootloader - Restore bootloader factory settings - sanity te
  - AWP-2722    0.572 [Bootloader            ] Bootloader - Restore bootloader factory settings - tftp :: Bootloader menu: "7. Restore Bootloader factory settings" should work Bootloader - Restore bootloader factory settings - tftp sett
  - AWP-2720    0.538 [Bootloader            ] Bootloader - Restore bootloader factory settings - deve :: Bootloader menu: "7. Restore Bootloader factory settings" should work Bootloader - Restore bootloader factory settings - developer
  - AWP-2721    0.443 [Bootloader            ] Bootloader - Restore bootloader factory settings - cons :: Bootloader menu: "7. Restore Bootloader factory settings" should work Bootloader - Restore bootloader factory settings - console s
  - AWP-2723    0.434 [Bootloader            ] Bootloader - Restore bootloader factory settings - rele :: Bootloader menu: "7. Restore Bootloader factory settings" should work Bootloader - Restore bootloader factory settings - e.g. defa
  - AWP-19571   0.345 [Bootloader            ] Bootloader - Boot Menu - Option 8 - Developer menu opti :: Test that the developer menu will appear when configured. | step1: Enter developer menu and check the developer menu appears. => P
  - AWP-13634   0.310 [Bootloader            ] Bootloader - Security Level 1 - Clearing the Password/S :: Check option Security Level 1 if it clears and recovers the switch when the admin password is lost | step1: Reboot the device and 
  - AWP-2696    0.302 [Bootloader            ] Bootloader - Access to menu - Change default bootloader :: Bootloader menu: " Able to access menu 2. Change the default boot source (for advanced users)" should work Test that the default b

### AWPTCM-T45071  |  area:   |  feature: Test able to downgrade bootloader version
folder:/Bootloader  steps:1  obj:False
  - AWP-2713    0.623 [Bootloader            ] Bootloader - test able to downgrade bootloader version  :: Bootloader menu: " 3. Update Bootloader" should work. Assume new bootloader is already loaded from earlier testing - test that the
  - AWP-28697   0.363 [File System           ] Downgrade firmware with new bootloader                  :: The switch should keep 64MB flkash after updating the firmware to 5.4.6 or 5.4.7 from v5.4.8-0.2 | step1: Install v3.2.6 bootloade
  - AWP-29397   0.303 [5.4.8-2 Development   ] AW+ firmware downgrade when configure mac filter        :: Confirm that wireless controller will be able to manage the AP even if perform AW+ firmware downgrade when configured mac filter. 
  - AWP-2711    0.298 [Bootloader            ] Bootloader - Boot Menu - Option 3. Update Bootloader -  :: Bootloader menu: " 3. Update Bootloader" should work. Assume new bootloader is already loaded from earlier testing - test that the
  - AWP-29738   0.280 [5.4.8-2 Development   ] TQm5403 : FW Upgrade / Downgrade                        :: Confirm TQm5403 FW upgrade and downgrade will be performed correctly | step1: APs firmware upgrade from v5.1.1 to v5.1.2 => Firmwa
  - AWP-7108    0.276 [IGMP                  ] CLI Test - ip igmp version                              :: Use this command to set the current IGMP version (IGMP version 1, 2 or 3) on an interface. Use the no variant of this command to r
  - AWP-2667    0.274 [Bootloader            ] Bootloader - Check version at boot time                 :: The following messages will be displayed during the boot: Bootloader x.x.x loaded Press <Ctrl+B> for the Boot Menu And other messa
  - AWP-26275   0.270 [PoE                   ] Downgrade firmware but skip micro code downgrade        :: The switch should skip the microdoce re-install operation when customer try to install the old firmware which was included in old 

### AWPTCM-T45072  |  area:   |  feature: Check new maxrtc commands are enabled for configuring the clkout pin as well as to set the rtc offset.
folder:/Bootloader  steps:1  obj:False
ZEPHYR: Ctrl-U shell new commands maxrtc clkout (high|low|off high C
  - AWP-12891   0.253 [Clock                 ] Clock - Clock sets from nvs when no real time clock     :: A device with no real time clock (eg x200/x210) keep writing files to nvs containing current time. On startup these files are read
  - AWP-23643   0.220 [Firewall              ] Clock: Real Time Clock Works                            :: For devices with real time clocks (RTC). Check that the RTC is working Check Date/Time are retained even when DUT is powered down 
  - AWP-19047   0.210 [NTP                   ] Sync software time: NTP -> CPU clock -> RTC every ~11 m :: If NTP is running no time gap between System Time to the Hardware Clock (RTC). > Is this mode works regardless of NTP configuratio
  - AWP-25304   0.200 [RIPng                 ] RIPng with offset-list                                  :: RIPng with offset-list Confirm that "RIPng with offset-list" add an offset to in and out metrics to routes learned through RIPng. 
  - AWP-7046    0.138 [Logging               ] Configured time offset of log email and host            :: Test that the timestamp on remote devices matches the timezone of the remote host | step1: When logging to remote devices (via ema
  - AWP-8122    0.132 [RIPng                 ] VMAC enabled, send max RIPng routes then turn off and o :: | step1: On a stack with VMAC enabled, send max RIPng routes. Kill power to the slave and power back on again (Failover) => Stack 
  - AWP-8121    0.126 [RIPng                 ] VMAC enabled, send max RIPng routes then turn off and o :: RIPng with VMAC enable and master failover | step1: 1. On STK with VMAC enable send max RIPng routes 2. Kill power to the master a
  - AWP-10144   0.111 [IPv6                  ] Protocol specific failover tests - VMAC enabled/disable :: Specific protocol should function well with VMAC enabled/disabled | step1: [Insert protocol specific failover tests. Which should 

### AWPTCM-T45073  |  area: TFTP Boot  |  feature: Sanity Checks
folder:/Bootloader  steps:3  obj:False
ZEPHYR: Test that device boot fails with default bootloader source - | One-off load by tftp -save release -don't set as boot | One-off load by tftp -save release -set as boot
  - AWP-2705    0.452 [Bootloader            ] Bootloader - test that device boot fails with default b :: Bootloader menu: " 2. Change the default boot source (for advanced users)" should work Test that device cannot load if release fil
  - AWP-2689    0.424 [Bootloader            ] Bootloader - one-off load by tftp and operate but relea :: Bootloader menu: " 1. Perform one-off boot from alternate source" should perform one-off boot Test that Bootloader can run a one-o
  - AWP-2686    0.380 [Bootloader            ] Bootloader - Be able to load by default a release by tf :: Bootloader menu: " 1. Perform one-off boot from alternate source" should perform one-off boot Test that devices can load a release
  - AWP-2690    0.378 [Bootloader            ] Bootloader - one-off load by tftp, with pre-configured  :: Bootloader menu: " 1. Perform one-off boot from alternate source" should perform one-off boot Test that Bootloader can run a one-o
  - AWP-2688    0.364 [Bootloader            ] Bootloader - one-off load by tftp -save release -set as :: Bootloader menu: " 1. Perform one-off boot from alternate source" should perform one-off boot. | step1: (This step has been replac
  - AWP-2726    0.356 [Bootloader            ] Bootloader - One-off boot tftp - recover from flash bec :: Test loading of a release when the flash will run out of memory. (add test for other types of file loading) Bootloader - One-off b
  - AWP-12068   0.354 [Bootloader            ] Bootloader - one-off load by tftp -save release -don't  :: Bootloader menu: " 1. Perform one-off boot from alternate source" should perform one-off boot. This test was written due to CR3522
  - AWP-25156   0.351 [Bootloader            ] Bootloader - Be able to load by default a release by TF :: Bootloader menu: " 1. Perform one-off boot from alternate source" should perform one-off boot Test that devices can load a release

### AWPTCM-T45102  |  area:   |  feature: Issue placeholder
folder:/New Platform Template/Issue Placeholder  steps:1  obj:True
ZEPHYR: OBJ: This is for issue you raised which doesn't fit any existing test cases in the cycle. In general, this is a place to hold ||
  - AWP-14066   0.251 [BGP4+                 ] BGP4+ Routemap - (stress) lots of entries (placeholder  :: Configure a large numbers of route-maps with multiple entries over large number of interfaces. Make sure routes are redistributed 
  - AWP-24954   0.236 [DNS                   ] DDNS - IPv6 over IPv4 commands                          :: Ensure that the "use-ipv4-for-ipv6-updates" and the "suppress-ipv4-updates" commands work as intended | step1: Add ddns method to 
  - AWP-2418    0.114 [z_Inactive            ] File - command - move dir - for non-existing source     :: File - command - move dir - for non-existing source | step1: DIR-Test when source DIR doesn't exist. Directory A does not exist - 
  - AWP-3394    0.109 [Provisioning          ] Check port count of x600-48Ts                           :: Provision x600-48. Insert x600-48Ts in its place. | step1: * Fit DUT AT-StackXG (x600-24|x600-48) * Load DUT with blank config * I
  - AWP-7092    0.107 [IGMP                  ] CLI Test - ip igmp query-holdtime                       :: This command sets the time that an IGMP Querier waits after receiving a query solicitation before it sends an IGMP Query. IGMP Gen
  - AWP-2395    0.107 [File System           ] File - command - show file - various tests              :: File - command - show file - various tests | step1: Need to be tested on flash, nvs, SD card and USB File A is a text type Issue t
  - AWP-7804    0.106 [User Login            ] User Login - Login with user priv 1, issue enable comma :: Check that users with privilege level 1 are able to execute the enable command | step1: Add user with privilege level 1 Login, iss
  - AWP-15231   0.105 [ATMF                  ] ATMF Minor Clients - Minor client in middle of network  :: Cover the situation where a minor client device (x200/x210) has down stream nodes | step1: Setup ATMF network with minor client de

### AWPTCM-T45103  |  area: Other DataCenterApplication  |  feature: Netconf/RESTConf
folder:/New Platform Template/Other  steps:1  obj:False
  - AWP-8292    0.358 [IPv4                  ] Secondary IP in other interface                         :: Secondary ip should work in other interface | step1: Testing of Secondary IP addresses is being done in other places. i.e PIM etc 
  - AWP-6851    0.345 [Port Authentication   ] Port Authentication and Tagged port (Other Port)        :: Port Authentication and Tagged port (Other Port) | step1: Refer to 4.4.1.doc => Refer to 4.4.1.doc Confirm the authentication succ
  - AWP-15361   0.342 [Web Authentication    ] Web Authentication and Tagged port (Other Port)         :: Web Authentication and Tagged port (Other Port) | step1: Refer to 4.5.1.doc => Refer to 4.5.1.doc
  - AWP-24510   0.321 [ATMF                  ] Check ATMF provisioning of other nodes will be supporte :: Check ATMF provisioning of other nodes will be supported | step1: Check the support of ATMF provisioning of other nodes => Ensure 
  - AWP-4503    0.319 [PoE                   ] POE CLI-Other-Show                                      :: PoE does not affect other show commands | step1: Set POE on different ports then check the other show commands show mem show proce
  - AWP-9370    0.310 [xSTP                  ] Interop with RSTP & MSTP on other devices.              :: | step1: Interop with RSTP & MSTP on other devices.
  - AWP-27178   0.295 [AWC-lite              ] use FW for other model                                  :: | step1: Confirm that error message of failure of FW update is dispalyed on router.
  - AWP-9846    0.276 [DHCP Snooping         ] DHCP Snooping - other ACL configuration                 :: Confirm that behavior is predictable as per ACL configuration | step1: Other ACL configurations that include DHCPSNOOPING - eg => 

### AWPTCM-T45801  |  area:   |  feature: Flow Control
folder:/XEM  steps:1  obj:False
  - AWP-15367   0.459 [Web Authentication    ] CONTROL                                                 :: CONTROL | step1: Refer to 2.3.2.1.doc => Refer to 2.3.2.1.doc
  - AWP-4428    0.432 [z_Inactive            ] terminal session - test asyn flow control               :: Note: This test case was already included on AWP-4425 terminal session - test asyn flow control | step1: Test asyn terminal settin
  - AWP-10159   0.355 [Pause Control/Flow Con] x908: Flowcontrol send off command                      :: x908: Error message should appear "Flow control send is not on port1.0.1" | step1: Issue the command "flowcontrol send off" from t
  - AWP-10169   0.339 [Pause Control/Flow Con] x900-12: Flowcontrol send off command                   :: x900-12: Error message should appear "Flow control send is not on port1.0.1" | step1: Issue the command "flowcontrol send off" fro
  - AWP-10158   0.332 [Pause Control/Flow Con] x908: Flowcontrol send on command                       :: x908: Unable to execute flowcontrol send on command and error message should appear | step1: Issue the command "flowcontrol send o
  - AWP-10164   0.320 [Pause Control/Flow Con] x908: Loopback port - activate flowcontrol and broadcas :: Able to received flow control frames from DUT as observed from IXIA Explorer | step1: - loopback from port3-4,port5-6 …. Port11-12
  - AWP-10168   0.319 [Pause Control/Flow Con] x900-12: Flowcontrol send on command                    :: x900-12: Unable to execute flowcontrol send on command and error message should appear | step1: Issue the command "flowcontrol sen
  - AWP-10155   0.318 [Pause Control/Flow Con] x908: Flowcontrol command help option                   :: x908: Check that two options were shown: receive and send parameters | step1: Issue the command "flowcontrol ?" from the interface

### AWPTCM-T45802  |  area:   |  feature: Link check
folder:/XEM  steps:1  obj:True
ZEPHYR: OBJ: including hotswap ||
  - AWP-6398    0.338 [L2 Switching (L2 Learn] Link down ATKK 5.1.1.4.3                                :: Link Down | step1: Link down ATKK 5.1.1.4.3 => Link Down
  - AWP-17714   0.320 [EPSR, EPSR+, EPSR++   ] EPSR Master test Link Fail with L3 Traffic              :: | step1: Link failure- each link in epsr ring including aggregated link - Layer 3 => L3 traffic - at least 2000 ARP entries. on ep
  - AWP-17720   0.320 [EPSR, EPSR+, EPSR++   ] EPSR Master test Link Fail with L3 Traffic              :: | step1: Link failure- each link in epsr ring including aggregated link - Layer 3 => L3 traffic - at least 2000 ARP entries. on ep
  - AWP-17711   0.313 [EPSR, EPSR+, EPSR++   ] EPSR Master test Link Fail with L2 Traffic              :: | step1: Link failure- each link in epsr ring including aggregated link - Layer2 => L2 traffic - at least 9000 FDB entries. on eps
  - AWP-17717   0.313 [EPSR, EPSR+, EPSR++   ] EPSR Master test Link Fail with L2 Traffic              :: | step1: Link failure- each link in epsr ring including aggregated link - Layer2 => L2 traffic - at least 9000 FDB entries. on eps
  - AWP-10095   0.312 [IPv6                  ] IPv6 Address - link local                               :: Check that link local is not routed | step1: FE80::/10 Link Local => Check that link local is not routed
  - AWP-13058   0.303 [Find Me               ] Hotswap Pluggables                                      :: Verify how hotswap in and out will affect the feature | step1: Link some ports to ensure LEDs are up Or ports are active with traf
  - AWP-9943    0.296 [DHCP Snooping         ] DHCP Snooping - hotswap on trusted interfaces           :: Confirm normal operation after hotswap on trusted ports | step1: Hotswap on trusted interfaces [including LAGs] => Expect normal o

### AWPTCM-T45803  |  area:   |  feature: Ping or Traffic
folder:/XEM  steps:1  obj:False
  - AWP-10203   0.362 [Diagnostic Application] Show PING                                               :: Output should have no data | step1: Restart DUT with no config 'Show Ping' => Correct output should dislpay
  - AWP-8305    0.327 [IPv4                  ] Ping Existing IP                                        :: Target destination should have a reply | step1: Ping an IP address that exists => Expect reply from device which is being ping
  - AWP-24173   0.326 [ATMF                  ] Check Ping (IPv4 and IPv6) will be supported            :: Check Ping (IPv4 and IPv6) will be supported | step1: Check Ping (IPv4 and IPv6) will be supported => confirm Ping (IPv4 and IPv6)
  - AWP-15363   0.295 [Web Authentication    ] Ping Polling                                            :: Ping Polling | step1: Refer to 2.4.1.doc => Refer to 2.4.1.doc
  - AWP-10208   0.279 [Diagnostic Application] Ping Timeout                                            :: Ping should still succed | step1: Remove cable from DUT Ping 192.168.1.2 (wait 10 seconds and reinsert cable.) => Ping timeout is 
  - AWP-10205   0.272 [Diagnostic Application] PING under user exec mode                               :: Ping should work under user exec mode | step1: Using above set-up. Logout and back in to 'Exec' priv level and sanity test ping op
  - AWP-5805    0.270 [IPv6 Management       ] Ping and Traceroute: DUT-1 to DUT-2                     :: Test for Ping and Traceroute command from DUT-1 to DUT-2 | step1: Configure 4 devices with ipv6 address Perform ping and tracerout
  - AWP-12109   0.269 [VRRP                  ] Accept Mode                                             :: Enabled by default. Ping, telnet, ssh to virtual IP. Cannot be disabled. | step1: Configure VRRP Ping, telnet and ssh to configure

### AWPTCM-T45804  |  area:   |  feature: Supported Pluggables test
folder:/XEM  steps:1  obj:True
ZEPHYR: OBJ: All supported Types, be aware Types not Variants ||
  - AWP-10624   0.387 [Pluggable Transceivers] Functional Test: SPTX pluggables                        :: All pluggables detailed and diagnostic information will be displayed except for SPTX | step1: 1. Populate DUT baseboard with SPTX/
  - AWP-13058   0.335 [Find Me               ] Hotswap Pluggables                                      :: Verify how hotswap in and out will affect the feature | step1: Link some ports to ensure LEDs are up Or ports are active with traf
  - AWP-15168   0.320 [Pluggable Transceivers] Functional Test: SBx8100 - Hotswap LIF with pluggables  :: LIFs that accept pluggables: SBx81GS24 SBx81XS6 SBx81XS16 SBx81XLEM SBx81XLEM/XS8 SBx81XLEM/Q2 Performing a hotswap and ensuring t
  - AWP-15957   0.315 [ATMF                  ] ATMF - Hot-Swap Pluggables and XEM                      :: Hotswup out and in of XEM and pluggable should be okay in an ATMF link | step1: Hot swap out and in XEM with ATMF link and repeat 
  - AWP-15166   0.295 [Pluggable Transceivers] Performance Test: SBx8100 - Populate DUT with the same  :: SBx8100 with the same pluggables - all pluggables information detail and diagnostic are displayed, device should not hang even wit
  - AWP-13279   0.294 [Find Me               ] Hotswap XEM with pluggables                             :: Verify how hotswap in and out will affect the feature | step1: Link some ports to ensure LEDs are up Or ports are active with traf
  - AWP-15167   0.289 [Pluggable Transceivers] Performance Test: SBx8100 - Populate DUT with mixed plu :: Populate SBx8100 with mixed pluggables. | step1: 1. Populate DUT with mixed pluggables. Eg. mix of SFP and SFP+ on the DUT. 2. Use
  - AWP-13036   0.282 [Find Me               ] Find Me / XEM-2XP / Pluggables                          :: Verify feature works with XEM module wit pluggables | step1: Link some ports to ensure LEDs are up Or ports are active with traffi

### AWPTCM-T45805  |  area:   |  feature: Different Speeds Link
folder:/XEM  steps:1  obj:True
ZEPHYR: OBJ: Ping or Traffic ||
  - AWP-25033   0.323 [Platform              ] XLEM in slots with DR-XAUI speeds                       :: Send traffic across backplane and check for errors | step1: Send traffic at varying packet sizes across backplane on two separate 
  - AWP-14374   0.299 [Green Features (Ecofri] Ecofriendly LED - Eco mode works at multiple line speed :: Eco mode should be tested with both 1G and 10/100M traffic to test both the green and the amber LEDs. | step1: Have both 1 G and 1
  - AWP-10200   0.245 [z_Inactive            ] Reverse Telnet - CLI - enable/disable commands, running :: | step1: Load default config file
  - AWP-17832   0.199 [Platform              ] XS6 - Ensure 1G speed cannot be set                     :: The XS6 hardware does not support 1G speeds on its pluggables, so this test is to ensure no speed other than 10000 is accepted, us
  - AWP-3452    0.195 [Provisioning          ] Memory consumption in x908 BPS stack with 14 provisione :: On a x908 BPS have just one XEM in each unit present so the stack can form. Provision the remaining 14 bays with XEM-12T. Check th
  - AWP-94      0.168 [Port Speed, Duplex and] SFP Copper-1Gig-Straight-AUTO 10/Full-Auto              :: SFP Copper - 1Gig & Straight Through Cable - Speed/Duplex = AUTO 10/Full & Auto both ends DUT Port Type: SFP Copper - 1 Gig Partne
  - AWP-18283   0.165 [ATMF                  ] ATMF Controller - virtual area links from different IP  :: Using different IP address in every atmf virtual area link. | step1: Used different IP address in every atmf virtual area link => 
  - AWP-93      0.160 [Port Speed, Duplex and] SFP Copper-1Gig-Straight-AUTO 100/Half-Auto             :: SFP Copper - 1Gig & Straight Through Cable - Speed/Duplex = AUTO 100/Half & Auto both ends DUT Port Type: SFP Copper - 1 Gig Partn

### AWPTCM-T45806  |  area:   |  feature: show platform sensor
folder:/XEM  steps:1  obj:False
  - AWP-23955   0.300 [ATMF                  ] Platform API: Display Alarms                            :: Display using API all active sensor alarms in the system. Need to generate fault or error for alarms to appear. Ex: curl -u manage
  - AWP-23952   0.274 [ATMF                  ] Platform API: Display Bays info                         :: Display using API all information and sensors related to bays in the device. Ex: curl -u manager:friend -k https://172.16.50.1/api
  - AWP-27497   0.251 [GUI Support           ] Eventwatch will update for Platform API events          :: Eventwatch will support change indication for the feature: /api/platform /event/features/platform/ Timestamp will update when this
  - AWP-18267   0.250 [Platform              ] Sensor check                                            :: Description : This testcase is to ensure when 1 sensor overheats, shutdown is initiated. Also check the the fan sensor does not ca
  - AWP-23953   0.247 [ATMF                  ] Platform API: Display Boards info                       :: Display using API all information and sensors related to boards in the device. Ex: curl -u manager:friend -k https://172.16.50.1/a
  - AWP-8270    0.213 [IPv4                  ] Show Platform Table FDB                                 :: Command will display entries in Forwarding Database | step1: From the command line use this command show platform table fdb => See
  - AWP-10575   0.212 [Port Authentication   ] CLI Test: show platform                                 :: Display platform unique information on DUT platform | step1: - Check mac-vlan-hashing-algorithm: awplus# show platform => Must out
  - AWP-25981   0.202 [G.8032                ] CLI: show platform commands for G.8032                  :: Object: Verify the "show platform" commands output for G.8032 Requirement: Project:1916_G8032 TFS section 4.1 Tech Support Require

### AWPTCM-T45807  |  area:   |  feature: FEC counters under idle frames
folder:/XEM  steps:1  obj:False
  - AWP-21643   0.182 [Web Authentication    ] CLI-Test auth-web idle-timeout enable                   :: Command handler to enable/disable the idle timeout feature [no] auth-web idle-timeout enable (interface mode) | step1: Examples To
  - AWP-4404    0.177 [z_Inactive            ] user - multiple user login + console                    :: NOTE: This test case was already included under AWP-4403 user - multiple user login + console | step1: 2nd login via telnet and 's
  - AWP-6418    0.176 [L2 Switching (L2 Learn] Under Minimum Untagged & tagged size.                   :: Error Frame Reception and Error counters - Under Minimum Untagged & tagged size. | step1: Under Minimum Untagged & tagged size. =>
  - AWP-21911   0.176 [Web Authentication    ] That authentication release is not performed by the idl :: Confirmation that the certification released by idle timeout is not executed during communication | step1: awplus#conf t awplus(co
  - AWP-4405    0.172 [z_Inactive            ] user - multiple telnet user login                       :: NOTE: This test case was already included under AWP-4403 user - multiple telnet user login | step1: 3rd login via telnet and 'sh u
  - AWP-27942   0.165 [JITC Certification    ] V-14693:The network device must be configured to ensure :: ---- Warning ---- TestLink Warning test case name is too long (213 chars) > 100 => has been truncated Original name V-14693:The ne
  - AWP-21644   0.164 [Web Authentication    ] CLI-Test auth-web idle-timeout timeout                  :: Command handler To configure the idle timeout value [no] auth-web idle-timeout timeout<300-86400> (interface mode) default value i
  - AWP-11391   0.164 [VLAN                  ] Maximum VLANs                                           :: Test tagged and untagged port when maximum vlans are configured | step1: Create VLANs from 2-4094. Send frames from tagged to tagg
