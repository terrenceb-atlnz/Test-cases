# Rerank batch 01  (cases 30..59)

### AWPTCM-T33293  |  area: Switching DHCPSnooping  |  feature: Enhancement to clear an entry in DHCP Bind DB
folder:/New Platform Template/Switching  steps:1  obj:True
ZEPHYR: OBJ: Enhancement to clear an entry in DHCP-BIND-DB Link Down DHCP Release ||
  - AWP-9721    0.233 [DHCP Snooping         ] DHCP Snooping ACL command - MAC/IP                      :: MAC dhcpsnooping keyword should be available | step1: (no) access-list hardware <name> (no) 10 permit ip dhcpsnooping any mac dhcp
  - AWP-9720    0.231 [DHCP Snooping         ] DHCP Snooping ACL command - IP                          :: Dhcpsnooping keyword should be available | step1: (no) access-list hardware <name> (no) 10 permit ip dhcpsnooping any (no) 20 deny
  - AWP-9704    0.214 [DHCP Snooping         ] DHCP Snooping - clear ip dhcp snooping statistics       :: "clear ip dhcp snooping statistics" command work as expected | step1: clear ip dhcp snooping statistics (interface ifrange | ) => 
  - AWP-9703    0.208 [DHCP Snooping         ] DHCP Snooping - clear ip dhcp snooping command          :: "clear ip dhcp snooping" command work as expected | step1: clear ip dhcp snooping binding (a.b.c.d | interface ifrange | vlan (<1-
  - AWP-9845    0.202 [DHCP Snooping         ] DHCP Snooping - IP MAC ACL                              :: Confirm that ACLs are created and effective when entry goes in DHCP binding database for IP and MAC | step1: ACLs created and effe
  - AWP-2273    0.201 [DHCP                  ] DHCP server - static IP address                         :: Configure DHCP server with static IP to MAC address binding | step1: 1. Configure a DHCP server with one IP address in range, and 
  - AWP-9844    0.196 [DHCP Snooping         ] DHCP Snooping - IP only ACL                             :: Confirm that ACLs are created and effective when entry goes in DHCP binding database for IP only | step1: ACLs created and effecti
  - AWP-9848    0.189 [DHCP Snooping         ] DHCP Snooping - ACLs set to null - IP and MAC address   :: Confirm that traffic is dropped when entry is removed | step1: ACLs set to null source address when entry removed from DHCP Bindin

### AWPTCM-T33297  |  area: Switching RateLimit  |  feature: Multicast/Broadcast/DLF per 1 port
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-7523    0.358 [Storm Control         ] storm-control tests with LACP                           :: Test that correct number of packets are received with LACP | step1: Perform following tests with two devices over an lacp link: - 
  - AWP-7524    0.353 [Storm Control         ] storm-control tests with static channel group           :: Test that correct number of packets are received with static channel group | step1: Perform following tests with two devices using
  - AWP-13779   0.340 [EPSR, EPSR+, EPSR++   ] EPSR with Packt Storm Protection                        :: Storm-control such as Broadcast,Multicast, and dlf should be work on EPSR domain | step1: Configure EPSR setting On more than 3 Un
  - AWP-7440    0.324 [Storm Control         ] Command Line Handler - storm-control dlf level          :: Test that storm-control dlf level command is executable and displayed in the running config | step1: 1. Log in with no config 2. E
  - AWP-8434    0.307 [MLD Snooping          ] Broadcast storm with multicast traffic running          :: | step1: Create broadcast storm with multicast traffic running => Multicast traffic should still work
  - AWP-7438    0.304 [Storm Control         ] Command Line Handler - storm-control types              :: Test that storm-control broadcast (or multicast, or dlf) level command is executable and displayed in the running config | step1: 
  - AWP-7522    0.278 [Storm Control         ] storm-control dlf level 95                              :: Test that when packet storm protection dlf level 95 is set, correct number of packets make it through | step1: 1. Execute the foll
  - AWP-7517    0.273 [Storm Control         ] storm-control dlf level 20                              :: Test that when packet storm protection dlf level 20 is set, 80% of the packets are dropped on other ports | step1: 1. Execute the 

### AWPTCM-T33298  |  area: Switching RateLimit  |  feature: Egress Limit
folder:/New Platform Template/Switching  steps:1  obj:True
ZEPHYR: OBJ: Use this command to limit the amount of traffic that can be transmitted per second from this port. egress-rate-limit <ra ||
  - AWP-20080   0.438 [QoS                   ] No Egress-Rate-Limit                                    :: 4.7.2.5 No Egress-Rate-Limit [P2, 10M] Scope: | step1: No Egress-rate-limit => Outgoing rate should be wire-rated.
  - AWP-20078   0.375 [QoS                   ] Egress-Limit=Max                                        :: 4.7.2.3 Egress-Limit=Max [P2, 10M] Scope: | step1: Egress-Limit=Max(kbit/sec) => Outgoing rate should be limited.
  - AWP-20077   0.366 [QoS                   ] Egress-Limit=Min                                        :: 4.7.2.2 Egress-Limit=Min [P2, 10M] Scope: | step1: Egress-Limit=Min(kbit/sec) => Outgoing rate should be limited.
  - AWP-9079    0.280 [QoS                   ] QoS: Interface egress-rate-limiting                     :: Verify that the passing traffic uses the configured egress rate limit | step1: Set egress rate limit and pass traffic. Use tagged 
  - AWP-15161   0.255 [Port Speed, Duplex and] CR00039861: Egress rate limit configuration should be c :: Running configurations on the CFC should always be in sync. | step1: 1. Select all ports in one CFC 2. Command the following -egre
  - AWP-25348   0.250 [PIM-SM                ] Multicast for VRFs - ip pim register-rate-limit         :: "ip pim (vrf NAME|) register-rate-limit <1-65535>" is used to limit how many register packets can be sent from the DUT per second.
  - AWP-3477    0.243 [PIM-SM                ] CLI to set ip pim register-rate-limit                   :: Command Line test | step1: 1. Login to DUT. 2. Execute the command to configure rate of register packets. - ip pim register-rate-l
  - AWP-19686   0.242 [QoS                   ] Egress-Limit=1000                                       :: 4.7.2.1 Egress-Limit=1000 [P2, 10M] Scope: Confirm that if Egress limit works correctly. Assertion: Confirm that when Egress limit

### AWPTCM-T33300  |  area: Switching LoopGuard  |  feature: MAC Address Thrashing
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-18040   0.607 [Customer Scenario     ] MAC-Thrashing                                           :: Confirm that MAC-Thrashing works correctly. It is not good that this feature doesn't work correctly because it is default enabled.
  - AWP-26054   0.411 [G.8032                ] Interop: MAC Thrashing and G.8032                       :: Verify that MAC Thrashing will function on a G.8032 interface. TFS recommends if used, the user should set the thrash-limit to a h
  - AWP-18059   0.404 [Customer Scenario     ] LDF                                                     :: Confirm that LDF works correctly. | step1: Confirm that MAC-Thrashing detects the occurrence of loop and the action works correctl
  - AWP-27103   0.380 [UFO                   ] Verify MAC Thrashing with UFO                           :: Verify that Private VLAN UFO shall not override any blocking/forwarding decisions from MAC Thrashing. Upstream Forwarding Only TFS
  - AWP-7470    0.366 [Storm Control         ] Thrash-limiting info on static channel group when inter :: Test that thrash-limiting parameters are not displayed when the interface is not thrashing | step1: Rapid Mac Movement - Sh static
  - AWP-7471    0.365 [Storm Control         ] Thrash-limiting info on dynamic channel group when inte :: Test that thrash-limiting parameters are not displayed when the interface is not thrashing | step1: Rapid Mac Movement - Sh etherc
  - AWP-13785   0.356 [VLAN                  ] Convination test. LDF,MAC address thrashing and IEEE802 :: LDF and MAC address thrashing is working correctly on Trank Port. | step1: Configure LDF and MAC address thrashing on Trank Port a
  - AWP-7460    0.349 [Storm Control         ] Command Line Handler - show interface switchport        :: Test that the command correctly displays the vlans that are thrashing | step1: Rapid Mac Movement - Issue the command: awplus>sh i

### AWPTCM-T33302  |  area: Switching VLAN  |  feature: Port VLAN
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-10077   0.344 [IPv6                  ] IPv6 Switching - rstp topology change                   :: IPv6 and rstp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that rstp 
  - AWP-10078   0.335 [IPv6                  ] IPv6 Switching - stp topology change                    :: IPv6 and stp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that stp fo
  - AWP-14859   0.294 [[ATKK] Auto Acceptance] IP Subnet VLAN and Broadcast                            :: 2.12 IP Subnet VLAN and Broadcast [10M] Scope: Create the two IP subnet based VLANs. Configure one port which belongs to these two
  - AWP-10087   0.283 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Dynamic an :: Confirm configuration was correct over a LAG interface and traffic passes with linkup/down | step1: Link Aggregation - Dynamic. Co
  - AWP-10084   0.283 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Static     :: Confirm that it is correctly configured over a LAG interface and traffic passes with linkup/down | step1: 1.) Configure VCS Stack 
  - AWP-10088   0.281 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Dynamic Ha :: Able to perform L3 hashing on IPv6 addresses with LAG Dynamic | step1: Link Aggregation - Dynamic . Hashing => L3 Hashing on IPv6 
  - AWP-22581   0.279 [VLAN                  ] vlan classifier and VRF                                 :: vlan classifier routing/switching behavior match routing routing to other vlan in vrf instance match switching switching to vlan a
  - AWP-22612   0.279 [[ATKK] Auto Acceptance] vlan classifier and VRF                                 :: vlan classifier routing/switching behavior match routing routing to other vlan in vrf instance match switching switching to vlan a

### AWPTCM-T33303  |  area: Switching VLAN  |  feature: IEEE802.1Q Tag
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-13785   0.346 [VLAN                  ] Convination test. LDF,MAC address thrashing and IEEE802 :: LDF and MAC address thrashing is working correctly on Trank Port. | step1: Configure LDF and MAC address thrashing on Trank Port a
  - AWP-19070   0.314 [Router Bridging       ] Filter traffic based on VLAN/802.1q tag                 :: Test that frames can be filter by vlan tag | step1: 1. Create a filter that would filter frames based on vlan tag only 2. apply fi
  - AWP-18493   0.291 [Router Bridging       ] Packets with 802.1Q tag can traverse bridge             :: Test that packets with 802.1q tags can traverse the bridge | step1: 1. Create a bridge. 2. Add 2 eth subinterfaces and encapsulate
  - AWP-18433   0.278 [Router Bridging       ] Filter Rule based on MAC address and 802.1Q tag         :: Test that filtering traffic based on mac and vlan tags works as expected | step1: 1. Create a bridge 2. Add all possible interface
  - AWP-18509   0.256 [802.1Q Interfaces     ] 802.1Q Tagging on Ethernet Interfaces                   :: 802.1Q tagged interfaces can be implemented on top of any Ethernet (Ethernet, Bridge, WLAN, L2 Tunnel) interface. Packets transmit
  - AWP-24239   0.249 [ATMF                  ] The bridge will support 802.1q tagged traffic           :: The bridge will support 802.1q (VLAN) tagged traffic | step1: confirm the bridge supports 802.1q traffic => send pinging from the 
  - AWP-14496   0.226 [OpenVPN               ] OpenVPN TAP: 802.1Q tagging of users by RADIUS attribut :: Traffic between users and the OpenVPN TAP tunnel interface is assigned 802.1Q tagging per user attributes in RADIUS. The RADIUS at
  - AWP-18511   0.221 [802.1Q Interfaces     ] 802.1Q Tagging on L2TP Tunnels                          :: To be updated once feature is complete | step1: 1. Configure a dot1q sub-interface to an L2TP tunnel 2. Send traffic to the vlan =

### AWPTCM-T33304  |  area: Switching VLAN  |  feature: Multiple VLAN
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-23078   0.343 [RSPAN - Mirror to VLAN] CLI: Show vlan brief                                    :: Verify the show vlan brief commands and other show vlan options. | step1: create multiple remote-mirror-vlans => multiple vlans wi
  - AWP-6655    0.311 [VLAN                  ] VLAN Packet Counter instance on multiple ports - tagged :: VLAN Packet Counter increment as packet destined to the instance vlan ingress | step1: Configure a vlan packet counter instance on
  - AWP-10077   0.310 [IPv6                  ] IPv6 Switching - rstp topology change                   :: IPv6 and rstp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that rstp 
  - AWP-17493   0.303 [IGMP                  ] Constantly switching between multicast sources (CR41699 :: Multiple Reports and Leaves for multiple groups | step1: Setup 2 streams with different addresses => Have multiple groups associat
  - AWP-10078   0.302 [IPv6                  ] IPv6 Switching - stp topology change                    :: IPv6 and stp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that stp fo
  - AWP-28452   0.283 [Port Authentication   ] single-supplicant mode with multiple VLAN and re-authen :: Confirm re-authentication works correctly without deleting FDB. | step1: After authed, confirm re-authentication start => FDB shou
  - AWP-6654    0.282 [VLAN                  ] VLAN Packet Counter instance on one port - tagged port  :: VLAN Packet Counter increment as packet destined to the instance vlan ingress | step1: Configure a vlan packet counter instance on
  - AWP-6652    0.280 [VLAN                  ] VLAN Packet Counter instance on multiple ports - untagg :: VLAN Packet Counter increment as traffic ingress to one or more configured port destined to the instane vlan | step1: Configure a 

### AWPTCM-T33305  |  area: Switching VLAN  |  feature: Protocol VLAN
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-10077   0.308 [IPv6                  ] IPv6 Switching - rstp topology change                   :: IPv6 and rstp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that rstp 
  - AWP-10078   0.300 [IPv6                  ] IPv6 Switching - stp topology change                    :: IPv6 and stp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that stp fo
  - AWP-10087   0.254 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Dynamic an :: Confirm configuration was correct over a LAG interface and traffic passes with linkup/down | step1: Link Aggregation - Dynamic. Co
  - AWP-10084   0.254 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Static     :: Confirm that it is correctly configured over a LAG interface and traffic passes with linkup/down | step1: 1.) Configure VCS Stack 
  - AWP-10088   0.252 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Dynamic Ha :: Able to perform L3 hashing on IPv6 addresses with LAG Dynamic | step1: Link Aggregation - Dynamic . Hashing => L3 Hashing on IPv6 
  - AWP-21668   0.250 [VLAN                  ] Protocol vlan with LAG                                  :: Confirm whether protocol vlan work well with LAG interface The specification is different between each version,please see below. v
  - AWP-8340    0.234 [IPv4                  ] Protocol specific failover tests                        :: Protocol specific failover tests with virtual-MAC | step1: [Insert protocol specific failover tests. Which should now be done with
  - AWP-6677    0.227 [IP Helper             ] Command Line Handler - ip forward-protocol              :: Command Line Interface tests - ip forward-protocol commands executed as expected | step1: ip forward-protocol udp PORT / no ip for

### AWPTCM-T33309  |  area: Switching VLAN  |  feature: VLAN ID Translation
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-26724   0.467 [CFM                   ] Functionality:CFM w/ VLAN Translation                   :: Verify that CFM can function with a translated VLAN | step1: Verify CFM using a translated VLAN. conf t int port1.0.2 switchport v
  - AWP-27014   0.427 [VLAN                  ] Verify VLAN translation functions following removal of  :: Verify VLAN translation functions following removal of untagged "native" VLAN. | step1: Remove the untagged (native) default vlan 
  - AWP-27002   0.416 [VLAN                  ] VLAN Translation: Configuration persists after reboot   :: Verify VLAN translation configuration functionas correctly after reboot and power cycle. | step1: Restart the system and verify aw
  - AWP-28481   0.405 [VLAN                  ] Check VLAN translation work after a VCS failover        :: | step1: Setup VLAN translation on switchport of the VCS Master member Send bidirectional traffic and ensure the translation is w 
  - AWP-27107   0.403 [UFO                   ] Verify VLAN Translation with UFO                        :: Verify VLAN Translation on a UFO VLAN. Upstream Forwarding Only TFS https://intranet.atlnz.lc/awpwiki/index.php/Upstream_Forwardin
  - AWP-27023   0.393 [VLAN                  ] Verify VLAN translation with ARP Security               :: Verify ARP Security will filter internal VID when a translation is configured. | step1: Configure ARP Security on an interface and
  - AWP-27016   0.391 [VLAN                  ] Verify VLAN translation error generation if max transla :: Verify VLAN translation error generation if max translation # exceeded | step1: Create some vlans vlans: awplus# configure termina
  - AWP-28597   0.383 [[ATKK] Auto Acceptance] 9005.2001 VLAN Translation: Configuration persists afte :: Verify VLAN translation configuration functionas correctly after reboot and power cycle. | step1: TestCase_1 Restart the system an

### AWPTCM-T33311  |  area: QoS  |  feature: Physical Queue: Q10 to Q0
folder:/New Platform Template/QoS  steps:1  obj:False
  - AWP-21845   0.354 [QoS                   ] CoS remarking do not cause conflict with traffic passin :: This is to verify that re-marked CoS traffic does not affect traffic intended to CPU queue | step1: 1. Send an unknown destination
  - AWP-9067    0.309 [QoS                   ] QoS cos-queue map default                               :: Verify QoS cos-queue map in correct default values | step1: Examine with show command. "show mls qos maps cos-queue" => Def is for
  - AWP-9071    0.306 [QoS                   ] QoS:fabric-queue map - default                          :: Verify default queue configuration Egress Queue Fabric Queue ----------------------- 0 0 1 0 2 1 3 1 4 2 5 2 6 3 7 3 | step1: veri
  - AWP-9072    0.302 [z_Inactive            ] QoS:fabric-queue map - configured                       :: QoS:fabric-queue map - configured | step1: Map egress queue to fabric queue. Need to find counters that confirm fa queue usage. No
  - AWP-9076    0.284 [QoS                   ] QoS:static LAG interface default queue                  :: Verify frames should egress via queue set by mls qos cos configuration while passing a LAG interface | step1: On static LAG interf
  - AWP-9074    0.282 [QoS                   ] QoS:switchport interface default queue                  :: Verify that the tagged ingress traffic will fill in the default queues when congestion was detected | step1: On interface set queu
  - AWP-9078    0.271 [QoS                   ] QoS:dynamic LAG interface default queue                 :: Verify frames should have COS tag set by mls qos cos configuration on ingress LAG interface | step1: To be verified On dynamic LAG
  - AWP-10099   0.270 [IPv6                  ] IPv6 Address - QoS field works                          :: QoS output should reflect input QoS field | step1: QOS field works - output queue reflects input QoS field => Output queue reflect

### AWPTCM-T33313  |  area: Qos  |  feature: ToS
folder:/New Platform Template/QoS  steps:1  obj:False
  - AWP-8138    0.499 [z_Inactive            ] Functional: Tos on the 6to4 results in ipv4 packets     :: To check out going packets with the correct tos | step1: Tos on the 6to4 tunnel results in ipv4 packets with the correct tos 1.) c
  - AWP-26560   0.343 [SD-WAN                ] SD WAN ICMP probe - Health probe DSCP and ToS           :: Ensure that the configured DSCP and/or ToS values for the health probe are applied. | step1: Configure one of the linkmon proes wi
  - AWP-14533   0.334 [OpenVPN               ] OpenVPN: TOS field copied from inner packet to outer pa :: TOS field values of all protected packets traversing the tunnel is copied to the outer header of that packet . This behaviour is e
  - AWP-28140   0.290 [DS-Lite               ] Check 'dscp-preservation' in DS-Lite where IPv4 TOS is  :: DS-Lite must preserve the IPv4 TOS values in the outgoing IPv6 traffic sent over the tunnel. | step1: With the router connected to
  - AWP-18427   0.260 [Interop               ] IPv4 Ping Test                                          :: Confirm that IPv4 Ping works correctly. | step1: Ping 192.168.3.1 => Ping succeeds.
  - AWP-9065    0.244 [QoS                   ] QoS globally enabled                                    :: Verify QoS commands are accepted when QoS is globally enabled | step1: qos can be enabled with the command: mls qos enable => Sele
  - AWP-21418   0.228 [GRE IPv6              ] GRE IPv6: Configurable DCSP value for insertion into th :: Configurable DCSP value for insertion into the outer header (defaults to copying from the inner header) The DSCP is the upper 6 bi
  - AWP-10099   0.213 [IPv6                  ] IPv6 Address - QoS field works                          :: QoS output should reflect input QoS field | step1: QOS field works - output queue reflects input QoS field => Output queue reflect

### AWPTCM-T33314  |  area: QoS  |  feature: DSCP
folder:/New Platform Template/QoS  steps:1  obj:True
ZEPHYR: OBJ: Verify that classified traffic class set DSCP as defined. || Create a policy with a class. Set dscp values via service-po
  - AWP-9109    0.942 [QoS                   ] QoS on switchport interface - class set dscp            :: Verify that classified traffic class set DSCP as defined. | step1: Create a policy with a class. Set dscp values via service-polic
  - AWP-9113    0.889 [QoS                   ] QoS on static LAG interface - default class set dscp    :: Verify that Classified traffic DSCP were set as defined. | step1: Create a policy with a class. Set dscp values via service-policy
  - AWP-9108    0.626 [QoS                   ] QoS on switchport interface - class set cos             :: Verify that classified traffic class set CoS as defined. | step1: Create a policy with a class. Set cos values via service-policy 
  - AWP-9088    0.617 [QoS                   ] QoS: DSCP Specify IP DSCP                               :: Verify that matching and non matching traffic specific to DSCP should conform to the configured class-map and default maps. | step
  - AWP-9110    0.592 [QoS                   ] QoS on switchport interface - class set queue           :: Verify that classified traffic class set queue as defined. | step1: Create a policy with a class. Set queue values via service-pol
  - AWP-9107    0.553 [QoS                   ] QoS on switchport interface - class set bandwidth class :: Verify that classified traffic bandwidth class set as defined. | step1: Create a policy with a class. Set bandwidth classes (green
  - AWP-9112    0.548 [QoS                   ] QoS on static LAG interface - default class set cos     :: Verify that traffic default bandwidth class set CoS passing through static LAG were defined. Note: This test case is only applicab
  - AWP-9114    0.526 [QoS                   ] QoS on static LAG interface - default class set queue   :: Verify that Classified traffic using queue were set as defined. | step1: Create a policy with a class. Set queue values via servic

### AWPTCM-T33315  |  area: QoS PriorityRemarking  |  feature: CoS Remarking
folder:/New Platform Template/QoS  steps:1  obj:False
  - AWP-9067    0.474 [QoS                   ] QoS cos-queue map default                               :: Verify QoS cos-queue map in correct default values | step1: Examine with show command. "show mls qos maps cos-queue" => Def is for
  - AWP-20430   0.458 [QoS                   ] QoS: Remarking of CoS value in the packet using "remark :: This test is to verify that the original CoS value of the packet can be over written and replaced with new CoS value specified by 
  - AWP-21845   0.436 [QoS                   ] CoS remarking do not cause conflict with traffic passin :: This is to verify that re-marked CoS traffic does not affect traffic intended to CPU queue | step1: 1. Send an unknown destination
  - AWP-9073    0.413 [QoS                   ] QoS:switchport interface default cos                    :: Verify that the default COS value is still tagged on the egressing packet. | step1: On interface set cos value for ingress untagge
  - AWP-9108    0.410 [QoS                   ] QoS on switchport interface - class set cos             :: Verify that classified traffic class set CoS as defined. | step1: Create a policy with a class. Set cos values via service-policy 
  - AWP-9075    0.410 [QoS                   ] QoS:static LAG interface default cos                    :: Verify frames should have COS tag set by mls qos cos configuration on ingress LAG interface | step1: On static LAG interface set c
  - AWP-9126    0.395 [QoS                   ] QoS:policed-dscp map (remarking) configuration changes, :: Verify that Policed-dscp map configurations should be in running and startup config | step1: Enable Qos awplus(config)#mls qos ena
  - AWP-9077    0.392 [QoS                   ] QoS default CoS with Dynamic LAG                        :: Objective: To verify if egress frames have the default CoS after passing through a LAG interface Expected Outcome: Egress frames s

### AWPTCM-T33316  |  area: QoS PriorityRemarking  |  feature: ToS Remarking
folder:/New Platform Template/QoS  steps:1  obj:False
  - AWP-8138    0.363 [z_Inactive            ] Functional: Tos on the 6to4 results in ipv4 packets     :: To check out going packets with the correct tos | step1: Tos on the 6to4 tunnel results in ipv4 packets with the correct tos 1.) c
  - AWP-9126    0.302 [QoS                   ] QoS:policed-dscp map (remarking) configuration changes, :: Verify that Policed-dscp map configurations should be in running and startup config | step1: Enable Qos awplus(config)#mls qos ena
  - AWP-9127    0.271 [QoS                   ] QoS:policed-dscp map (remarking) reverts to default via :: Verify that the policed-dscp map reverts to default via use of no command | step1: Enable QoS awplus(config)#mls qos enable Config
  - AWP-26560   0.249 [SD-WAN                ] SD WAN ICMP probe - Health probe DSCP and ToS           :: Ensure that the configured DSCP and/or ToS values for the health probe are applied. | step1: Configure one of the linkmon proes wi
  - AWP-14533   0.243 [OpenVPN               ] OpenVPN: TOS field copied from inner packet to outer pa :: TOS field values of all protected packets traversing the tunnel is copied to the outer header of that packet . This behaviour is e
  - AWP-21845   0.228 [QoS                   ] CoS remarking do not cause conflict with traffic passin :: This is to verify that re-marked CoS traffic does not affect traffic intended to CPU queue | step1: 1. Send an unknown destination
  - AWP-20430   0.218 [QoS                   ] QoS: Remarking of CoS value in the packet using "remark :: This test is to verify that the original CoS value of the packet can be over written and replaced with new CoS value specified by 
  - AWP-28140   0.211 [DS-Lite               ] Check 'dscp-preservation' in DS-Lite where IPv4 TOS is  :: DS-Lite must preserve the IPv4 TOS values in the outgoing IPv6 traffic sent over the tunnel. | step1: With the router connected to

### AWPTCM-T33317  |  area: QoS  |  feature: PriorityRemarking - DSCP Remarking
folder:/New Platform Template/QoS  steps:1  obj:False
  - AWP-9126    0.547 [QoS                   ] QoS:policed-dscp map (remarking) configuration changes, :: Verify that Policed-dscp map configurations should be in running and startup config | step1: Enable Qos awplus(config)#mls qos ena
  - AWP-9127    0.510 [QoS                   ] QoS:policed-dscp map (remarking) reverts to default via :: Verify that the policed-dscp map reverts to default via use of no command | step1: Enable QoS awplus(config)#mls qos enable Config
  - AWP-9129    0.400 [QoS                   ] QoS: switchport based policing on default class - singl :: This test is to verify that the egress traffic in each bandwidth class be marked with new dscp values based policed-dscp mapping t
  - AWP-9109    0.395 [QoS                   ] QoS on switchport interface - class set dscp            :: Verify that classified traffic class set DSCP as defined. | step1: Create a policy with a class. Set dscp values via service-polic
  - AWP-9130    0.388 [QoS                   ] QoS: static LAG based policing on - single-rate - actio :: This test is to verify that the egress traffic in each bandwidth class be marked with new dscp values based policed-dscp mapping i
  - AWP-17776   0.383 [QoS                   ] QoS: switchport based policing on default class - twin- :: This test is to verify that the egress traffic in each bandwidth class be marked with new dscp values based policed-dscp mapping t
  - AWP-9113    0.375 [QoS                   ] QoS on static LAG interface - default class set dscp    :: Verify that Classified traffic DSCP were set as defined. | step1: Create a policy with a class. Set dscp values via service-policy
  - AWP-17777   0.350 [QoS                   ] QoS: static LAG based policing on - twin-rate - action  :: This test is to verify that the egress traffic in each bandwidth class be marked with new dscp values based policed-dscp mapping i

### AWPTCM-T33318  |  area: QoS  |  feature: PriorityRemarking - IP DSCP Override
folder:/New Platform Template/QoS  steps:1  obj:False
  - AWP-25651   0.412 [PIM-SM                ] ip pim (vrf NAME|) rp-address A.B.C.D (override |)      :: CLI Test | step1: Ensure that all commands have correct context sensitive help tab auto-complete and check vrf option works correc
  - AWP-9109    0.388 [QoS                   ] QoS on switchport interface - class set dscp            :: Verify that classified traffic class set DSCP as defined. | step1: Create a policy with a class. Set dscp values via service-polic
  - AWP-24977   0.387 [PPP                   ] PPP API - IP-override                                   :: Ensure that the DUT can be configured via the API to use the statically configured IP-address on a given PPP interface over a nego
  - AWP-27104   0.376 [UFO                   ] Verify QOS with UFO                                     :: Verify Private VLAN UFO shall not override any QoS treatments. Unexhausted list includes: p-bit or DSCP settings, Queue priority s
  - AWP-9088    0.371 [QoS                   ] QoS: DSCP Specify IP DSCP                               :: Verify that matching and non matching traffic specific to DSCP should conform to the configured class-map and default maps. | step
  - AWP-9113    0.369 [QoS                   ] QoS on static LAG interface - default class set dscp    :: Verify that Classified traffic DSCP were set as defined. | step1: Create a policy with a class. Set dscp values via service-policy
  - AWP-9115    0.335 [QoS                   ] QoS:premark-dscp map                                    :: Verify that premark-dscp map command handles properly | step1: Configure various premark maps. - test parameter ranges - test long
  - AWP-9104    0.325 [QoS                   ] QoS:policy-map class trust dscp                         :: Verify that the command policy-map class trust dscp were accepted and applied. | step1: Execute Command awplus(config)#class-map C

### AWPTCM-T33319  |  area: QoS  |  feature: Port Priority
folder:/New Platform Template/QoS  steps:1  obj:False
ZEPHYR: Port Priority DUT-------------IXIA Port1.0.3------Port 5 Por
  - AWP-9108    0.274 [QoS                   ] QoS on switchport interface - class set cos             :: Verify that classified traffic class set CoS as defined. | step1: Create a policy with a class. Set cos values via service-policy 
  - AWP-9073    0.270 [QoS                   ] QoS:switchport interface default cos                    :: Verify that the default COS value is still tagged on the egressing packet. | step1: On interface set cos value for ingress untagge
  - AWP-21882   0.267 [QoS                   ] ACL has higher priority over QoS                        :: This test is to verify marked traffic can be assigned to specific CoS-Queue using QoS policy map. Traffic marked as low priority w
  - AWP-22580   0.266 [VLAN                  ] vlan classifier and QoS remark                          :: | step1: start capture on Ix-2
  - AWP-9067    0.265 [QoS                   ] QoS cos-queue map default                               :: Verify QoS cos-queue map in correct default values | step1: Examine with show command. "show mls qos maps cos-queue" => Def is for
  - AWP-9112    0.260 [QoS                   ] QoS on static LAG interface - default class set cos     :: Verify that traffic default bandwidth class set CoS passing through static LAG were defined. Note: This test case is only applicab
  - AWP-20430   0.258 [QoS                   ] QoS: Remarking of CoS value in the packet using "remark :: This test is to verify that the original CoS value of the packet can be over written and replaced with new CoS value specified by 
  - AWP-9087    0.257 [QoS                   ] QoS: CoS Specify CoS                                    :: Verify that matching and non matching traffic with specific to COS should conform to the configured class-map and default maps. | 

### AWPTCM-T33320  |  area: QoS PolicyBase  |  feature: Maximum band width
folder:/New Platform Template/QoS  steps:1  obj:False
  - AWP-27157   0.454 [AWC-lite              ] band                                                    :: | step1: band : 2 Confirm that band of profile is configured on router.
  - AWP-27196   0.325 [AWC-lite              ] band steering                                           :: | step1: band-steering Confirm that band steering is configured on router.
  - AWP-29304   0.194 [5.4.8-2 Development   ] network [ vlan / mac-auth / web-auth / band-steering ]  :: Confirm networksetting reflect to AP | step1: Enter the following command. (config-wireless)#network 1 (config-wireless-network)#v
  - AWP-6845    0.179 [Port Authentication   ] Maximum Clients Test                                    :: Confirm the maximum number of client per port. | step1: Configure dot1x in the DUT with maximum clients that it can support (repea
  - AWP-27331   0.171 [AWC-lite              ] Network ext:Hide-SSID/Band-Steering/VLAN                :: | step1: Enable hide-ssid and save it. => The devise should save it on running-config
  - AWP-28303   0.171 [[ATKK] Auto Acceptance] Network ext:Hide-SSID/Band-Steering/VLAN                :: | step1: Enable hide-ssid and save it. => The devise should save it on running-config
  - AWP-9065    0.166 [QoS                   ] QoS globally enabled                                    :: Verify QoS commands are accepted when QoS is globally enabled | step1: qos can be enabled with the command: mls qos enable => Sele
  - AWP-9138    0.152 [QoS                   ] QoS:Interface -applying queue-set to port with taildrop :: Verify maximum thresholds of each queue where traffic passes through | step1: Enable QoS Configure queue-set thresholds (use "mls 

### AWPTCM-T33321  |  area: QoS PolicyBase  |  feature: Minimum band width
folder:/New Platform Template/QoS  steps:1  obj:False
  - AWP-27157   0.436 [AWC-lite              ] band                                                    :: | step1: band : 2 Confirm that band of profile is configured on router.
  - AWP-27196   0.312 [AWC-lite              ] band steering                                           :: | step1: band-steering Confirm that band steering is configured on router.
  - AWP-6418    0.193 [L2 Switching (L2 Learn] Under Minimum Untagged & tagged size.                   :: Error Frame Reception and Error counters - Under Minimum Untagged & tagged size. | step1: Under Minimum Untagged & tagged size. =>
  - AWP-29304   0.186 [5.4.8-2 Development   ] network [ vlan / mac-auth / web-auth / band-steering ]  :: Confirm networksetting reflect to AP | step1: Enter the following command. (config-wireless)#network 1 (config-wireless-network)#v
  - AWP-5740    0.170 [Port Security (Intrusi] minimum setup, ageing time is enabled, switch filter ad :: Port Security minimum setup | step1: Repeat above test but add swith filter in running config => learned MACs are not added due to
  - AWP-27331   0.164 [AWC-lite              ] Network ext:Hide-SSID/Band-Steering/VLAN                :: | step1: Enable hide-ssid and save it. => The devise should save it on running-config
  - AWP-28303   0.164 [[ATKK] Auto Acceptance] Network ext:Hide-SSID/Band-Steering/VLAN                :: | step1: Enable hide-ssid and save it. => The devise should save it on running-config
  - AWP-5738    0.161 [Port Security (Intrusi] check minimum setup                                     :: Port Secuity minimum setup | step1: set Learn limit to 1 for port1.0.1 on DUT, send 10,000 packets from ixia with srcMAC increment

### AWPTCM-T33322  |  area: QoS PolicyBase  |  feature: QoS Action in Hardware Filter
folder:/New Platform Template/QoS  steps:1  obj:False
  - AWP-9065    0.356 [QoS                   ] QoS globally enabled                                    :: Verify QoS commands are accepted when QoS is globally enabled | step1: qos can be enabled with the command: mls qos enable => Sele
  - AWP-21148   0.343 [QoS                   ] VACL: vlan filter with QoS (Marvel)                     :: Combination test of VACL and QoS. Confirm which takes precedence. | step1: Configure VLAN ACL and QoS. - create access-list/vlan a
  - AWP-10099   0.310 [IPv6                  ] IPv6 Address - QoS field works                          :: QoS output should reflect input QoS field | step1: QOS field works - output queue reflects input QoS field => Output queue reflect
  - AWP-13380   0.303 [QoS                   ] Policy-based QoS and ACL test                           :: (Broadcom chip product) Policy-based QoS and ACL work correctly each other on same port. The order of processing is ACL -> Policy-
  - AWP-21940   0.293 [QoS                   ] Check the LED when recover from QoS Storm action        :: Check the LED when recover from QoS Storm action. | step1: Configure Findme trigger all and QoS Storm Protection on the device. Ac
  - AWP-4969    0.282 [Limits                ] MAC Filter entries                                      :: Deactivated | step1: N/A => N/A
  - AWP-8694    0.265 [ACL                   ] ACL:Named IPv6 Hardware on static LAG - IP with Mac     :: ACL:Named IPv6 Hardware on static LAG - IP | step1: A number of different ACLs probably required to cover this test case. Apply AC
  - AWP-21078   0.264 [QoS                   ] Command Handler: QoS                                    :: Verify command work properly | step1: Check 'qos' commands for: =>Command execution (sh run, sh run int port <range>) =>Negation o

### AWPTCM-T33323  |  area: QoS  |  feature: Dynamic changes to policy contents
folder:/New Platform Template/QoS  steps:1  obj:False
  - AWP-21187   0.407 [QoS                   ] DPMAP: Dynamic change to policy-map with LAG            :: Change the policy-map attached to LAG interface. this function will be supported in 5.4.7 for BCM/IE200/Marvell Product. | step1: 
  - AWP-20974   0.392 [QoS                   ] DPMAP: Dynamic change while traffic running             :: Change the policy-map attached to interface without detachment while traffic running. this function will be supported in 5.4.7 for
  - AWP-21053   0.379 [QoS                   ] DPMAP: Dynamic change to policy-map with VCS            :: Change the policy-map attached to interface on VCS unit. this function will be supported in 5.4.7 for BCM/IE200/Marvell Product. |
  - AWP-579     0.334 [Triggers              ] Display Script Contents                                 :: Tests for basic trigger CLI commands | step1: Display the contents of a script stored on the device => Script contents can be disp
  - AWP-7628    0.324 [Policy Based Routing  ] Dynamic changes to the next hop with traffic            :: Confirm that dynamic changes to the next hop up/down with traffic on works | step1: Dynamic changes to the next hop up/down with t
  - AWP-20971   0.308 [QoS                   ] DPMAP: Dynamic change of attached policy-map            :: Change the policy-map attached to interface without detachment. this function will be supported in 5.4.7 for BCM/IE200/Marvell Pro
  - AWP-5036    0.304 [Limits                ] QoS - Number of Policy Entries per Unit                 :: Verify policy entry limit | step1: - Create one class map for each policy map - Applying one policy map for each interface => - Co
  - AWP-20975   0.292 [QoS                   ] DPMAP: Dynamic change for exceeding the limit           :: Change policy-map contents while HW table is full of entries. this function will be supported in 5.4.7 for BCM/IE200/Marvell Produ

### AWPTCM-T33324  |  area: QoS  |  feature: Enable/Disable Port Egress Queue and Flow Control
folder:/New Platform Template/QoS  steps:1  obj:False
  - AWP-9076    0.444 [QoS                   ] QoS:static LAG interface default queue                  :: Verify frames should egress via queue set by mls qos cos configuration while passing a LAG interface | step1: On static LAG interf
  - AWP-9074    0.434 [QoS                   ] QoS:switchport interface default queue                  :: Verify that the tagged ingress traffic will fill in the default queues when congestion was detected | step1: On interface set queu
  - AWP-9078    0.414 [QoS                   ] QoS:dynamic LAG interface default queue                 :: Verify frames should have COS tag set by mls qos cos configuration on ingress LAG interface | step1: To be verified On dynamic LAG
  - AWP-9071    0.394 [QoS                   ] QoS:fabric-queue map - default                          :: Verify default queue configuration Egress Queue Fabric Queue ----------------------- 0 0 1 0 2 1 3 1 4 2 5 2 6 3 7 3 | step1: veri
  - AWP-9072    0.391 [z_Inactive            ] QoS:fabric-queue map - configured                       :: QoS:fabric-queue map - configured | step1: Map egress queue to fabric queue. Need to find counters that confirm fa queue usage. No
  - AWP-9110    0.384 [QoS                   ] QoS on switchport interface - class set queue           :: Verify that classified traffic class set queue as defined. | step1: Create a policy with a class. Set queue values via service-pol
  - AWP-9069    0.381 [QoS                   ] QoS cos-queue map effective                             :: Verify QoS cos-queue maps reflects on the egress queue when traffic passes COS-TO-QUEUE-MAP: COS : 0 1 2 3 4 5 6 7 ---------------
  - AWP-9139    0.371 [QoS                   ] QoS:Interface -applying queue-set to port with taildrop :: Verify maximum thresholds of each queue where traffic passes through | step1: Enable QoS Configure queue-set thresholds - queue ba

### AWPTCM-T33325  |  area: QoS  |  feature: Scheduling
folder:/New Platform Template/QoS  steps:1  obj:False
  - AWP-29031   0.273 [AWC-lite              ] AP firmware upgrading after slave failover              :: Confirm AP firmware upgrading will work after slave failover | step1: Check the status and perform slave failover after saving con
  - AWP-29025   0.266 [AWC-lite              ] AP firmware upgrading after master failover             :: Confirm AP firmware upgrading will work after master failover | step1: Check the status and perform master failover with power-off
  - AWP-9065    0.227 [QoS                   ] QoS globally enabled                                    :: Verify QoS commands are accepted when QoS is globally enabled | step1: qos can be enabled with the command: mls qos enable => Sele
  - AWP-22496   0.226 [QoS                   ] LLQ: Priority Queue + HTB                               :: LLQ (Low Latency Queueing) Mixed scheduling will be supported. Any combination of scheduling algorithms operating together on an e
  - AWP-22770   0.221 [QoS                   ] LLQ: Priority Queue + WRR                               :: LLQ (Low Latency Queueing) Mixed scheduling will be supported. Any combination of scheduling algorithms operating together on an e
  - AWP-10099   0.197 [IPv6                  ] IPv6 Address - QoS field works                          :: QoS output should reflect input QoS field | step1: QOS field works - output queue reflects input QoS field => Output queue reflect
  - AWP-22776   0.190 [QoS                   ] LLQ: Priority Queue + HTB and WRR                       :: LLQ (Low Latency Queueing) Mixed scheduling will be supported. Any combination of scheduling algorithms operating together on an e
  - AWP-12130   0.182 [ATMF                  ] ATMF File Server - Command Line Testing                 :: ATMF File Server commands, test for: Valid parameters all accepted & intended result Non-valid parameters cause error Command line

### AWPTCM-T33326  |  area: QoS  |  feature: DOS Attack Detection
folder:/New Platform Template/QoS  steps:1  obj:False
  - AWP-6854    0.628 [Port Authentication   ] Port Authentication and DoS Detection                   :: (SBx908 and x900 are not supported) Port Authentication and DoS Detection | step1: Refer to 4.6.doc => Refer to 4.6.doc When the d
  - AWP-14335   0.357 [Port Security (Intrusi] CR00039551: DOS Land Attack.                            :: This type of attack occurs when the Source IP and Destination IP address are the same. This can cause a target host to be confused
  - AWP-5767    0.327 [Port Security (Intrusi] L2 attack - test ping from switch                       :: Test switch handles ARP attack | step1: Ping 192.168.1.254 from sw-2 => check Ix-2 receives the echo requests
  - AWP-5769    0.308 [Port Security (Intrusi] L2 attack - private vlan attack                         :: Test switch handles private VLAN attack | step1: Private Vlan Attack: From TB ping 192.168.1.254 (SW-2) Send 10 IP packets from Ix
  - AWP-5765    0.298 [Port Security (Intrusi] L2 attack - ARP attack                                  :: Test switch handles ARP attack | step1: Arp Attack: SW-1 with no configuration (Layer 2 switch) Ping from SW-2 to 192.168.1.254 (I
  - AWP-6313    0.284 [Storm Control         ] enable/disable loop-detection                           :: Test that loop-detection can be enabled/disabled in an interface. | step1: Enable/Disable Loopdetection test => Should be able to 
  - AWP-5771    0.259 [Port Security (Intrusi] L2 attack - random frame stress attack                  :: Test switch handles random frames attack | step1: Random frame stress attack(No Special configuration) Send ARP from Ix-1 Start PC
  - AWP-5770    0.258 [Port Security (Intrusi] L2 attack - private vlan attack with HW filter          :: Test switch handles private VLAN attack | step1: Configure SW-1 with HW filter to discard packets originated from 192.168.1.0/25 d

### AWPTCM-T33351  |  area: Authentication Security IEEE 802.1X  |  feature: Single host
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-6809    0.471 [Port Authentication   ] Combination Tests (802.1X authentication) - Single-Host :: When 802.1x authentication are used, confirm that the authentication is succeeded. And, after the authentication is succeeded, the
  - AWP-6810    0.462 [Port Authentication   ] Combination Tests (802.1X authentication) - Single-Host :: When 802.1x authentication are used, confirm that the authentication is succeeded. And, after the authentication is succeeded, the
  - AWP-6808    0.459 [Port Authentication   ] Combination Tests (802.1X authentication) - Single-Host :: When 802.1x authentication are used, confirm that the authentication is succeeded. And, after the authentication is succeeded, the
  - AWP-6825    0.403 [Port Authentication   ] 802.1X + WEB authentication - Single-Mode / no GuestVLA :: Parallel use tests - Single-Mode / no GuestVLAN / per port / no DynamicVLAN | step1: >> Please see the attached file => >> Refer t
  - AWP-6807    0.403 [Port Authentication   ] Combination Tests (802.1X authentication) - Single-Host :: When 802.1x authentication is used, confirm that the each other authentication is succeeded. And, after the authentication is succ
  - AWP-6828    0.398 [Port Authentication   ] 802.1X + WEB authentication - Single-Mode / GuestVLAN / :: [Note] On 5.4.5-0.x, try this test on interface mode or auth-config mode. Parallel use tests - Single-Mode / GuestVLAN / per port 
  - AWP-6826    0.394 [Port Authentication   ] 802.1X + WEB authentication - Single-Mode / no GuestVLA :: [Note] On 5.4.5-0.x, try this test on interface mode or auth-config mode. Parallel use tests - Single-Mode / no GuestVLAN / per po
  - AWP-6827    0.394 [Port Authentication   ] 802.1X + WEB authentication - Single-Mode / GuestVLAN / :: [Note] On 5.4.5-0.x, try this test on interface mode or auth-config mode. Parallel use tests - Single-Mode / GuestVLAN / per port 

### AWPTCM-T33352  |  area: Authentication Security IEEE 802.1X  |  feature: Multiple Host
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-6858    0.371 [Port Authentication   ] 802.1x Authentication and MAC based Authentication      :: Confirm that the 802.1x port authentication and MAC based authentication operate correctly at the same time. | step1: Refer to 4.8
  - AWP-6809    0.364 [Port Authentication   ] Combination Tests (802.1X authentication) - Single-Host :: When 802.1x authentication are used, confirm that the authentication is succeeded. And, after the authentication is succeeded, the
  - AWP-6841    0.358 [Port Authentication   ] 802.1X + MAC + WEB authentication - Multi-host / no Gue :: Parallel use tests - Multi-host / no GuestVLAN / per port / DynamicVLAN | step1: >> Please see the attached file => >> Refer to th
  - AWP-6810    0.357 [Port Authentication   ] Combination Tests (802.1X authentication) - Single-Host :: When 802.1x authentication are used, confirm that the authentication is succeeded. And, after the authentication is succeeded, the
  - AWP-6832    0.357 [Port Authentication   ] 802.1X + WEB authentication - Multi-host / GuestVLAN /  :: [Note] On 5.4.5-0.x, try this test on interface mode or auth-config mode. Parallel use tests - Multi-host / GuestVLAN / per port /
  - AWP-9367    0.355 [xSTP                  ] Interop with 802.1x port control                        :: | step1: Interop with 802.1x port control
  - AWP-6808    0.354 [Port Authentication   ] Combination Tests (802.1X authentication) - Single-Host :: When 802.1x authentication are used, confirm that the authentication is succeeded. And, after the authentication is succeeded, the
  - AWP-6830    0.353 [Port Authentication   ] 802.1X + WEB authentication - Multi-host / no GuestVLAN :: [Note] On 5.4.5-0.x, try this test on interface mode or auth-config mode. Parallel use tests - Multi-host / no GuestVLAN / per por

### AWPTCM-T33353  |  area: Authentication Security IEEE 802.1X  |  feature: Multiple Authentication
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-6858    0.436 [Port Authentication   ] 802.1x Authentication and MAC based Authentication      :: Confirm that the 802.1x port authentication and MAC based authentication operate correctly at the same time. | step1: Refer to 4.8
  - AWP-6724    0.396 [Port Authentication   ] 802.1X Authentication Log - Disabled dot1x Authenticati :: Confirm that the dot1x authenticator log outputs correctly. | step1: Disable dot1x Authentication Specify parameter : all (default
  - AWP-5762    0.388 [Port Security (Intrusi] enable port authentication                              :: port security ignores supplicant mac addresses | step1: enable port authentication (802.1x), enable port-security on port1.0.1. =>
  - AWP-6748    0.383 [Port Authentication   ] 802.1X Authentication Log with VCS - Disabled dot1x Aut :: Confirm that the dot1x authenticator log outputs correctly. | step1: Disable dot1x Authentication Specify parameter : all (default
  - AWP-6722    0.379 [Port Authentication   ] 802.1X Authentication Log - no auth log dot1x all       :: Confirm that the dot1x authenticator log outputs correctly. | step1: Specify parameter : all Command : no auth log dot1x all => Al
  - AWP-6723    0.378 [Port Authentication   ] 802.1X Authentication Log - auth log dot1x all          :: Confirm that the dot1x authenticator log outputs correctly. | step1: Specify parameter : all (default behavior) Command : auth log
  - AWP-6775    0.371 [Port Authentication   ] 802.1X Authentication Log with VCS failover - Disabled  :: Confirm that the dot1x authenticator log outputs correctly. | step1: Disable dot1x Authentication Specify parameter : all (default
  - AWP-9367    0.367 [xSTP                  ] Interop with 802.1x port control                        :: | step1: Interop with 802.1x port control

### AWPTCM-T33354  |  area: Authentication Security IEEE 802.1X  |  feature: EAP-Notification
folder:/New Platform Template/Authentication & Security  steps:1  obj:True
ZEPHYR: OBJ: Not Support ||
  - AWP-142     0.344 [Customer Scenario     ] EAP support                                             :: Confirm that dot1authentications is possible. (all kinds of eap supported on AW+) | step1: Do dot1 authentication on each eap type
  - AWP-6786    0.320 [Port Authentication   ] Authentication message exchange                         :: Confirm that an authenticator exchanges authentication messages between the supplicant and Radius server. | step1: 1. Configure DU
  - AWP-6778    0.307 [Port Authentication   ] EAP Forwarding Tests                                    :: [Note] On 5.4.5-0.x, try this test on interface mode or auth-config mode. Verify switch action when EAP forwarding is enabled or d
  - AWP-6858    0.305 [Port Authentication   ] 802.1x Authentication and MAC based Authentication      :: Confirm that the 802.1x port authentication and MAC based authentication operate correctly at the same time. | step1: Refer to 4.8
  - AWP-9367    0.292 [xSTP                  ] Interop with 802.1x port control                        :: | step1: Interop with 802.1x port control
  - AWP-6787    0.286 [Port Authentication   ] Packet Format on Authenticator port                     :: Confirm the Packet format that the protocol used for port-based access control is the IETF standard Extensible Authentication Prot
  - AWP-6724    0.281 [Port Authentication   ] 802.1X Authentication Log - Disabled dot1x Authenticati :: Confirm that the dot1x authenticator log outputs correctly. | step1: Disable dot1x Authentication Specify parameter : all (default
  - AWP-6722    0.275 [Port Authentication   ] 802.1X Authentication Log - no auth log dot1x all       :: Confirm that the dot1x authenticator log outputs correctly. | step1: Specify parameter : all Command : no auth log dot1x all => Al

### AWPTCM-T33355  |  area: Authentication Security IEEE 802.1X  |  feature: IEEE 802.1X-2004
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-9367    0.400 [xSTP                  ] Interop with 802.1x port control                        :: | step1: Interop with 802.1x port control
  - AWP-11686   0.396 [Port Authentication   ] CR00027654 The authentication state machine is not comp :: The authentication state machine is not compliance with 802.1X-2004 | step1: Transmit any packet (without EAP) from supplicant to 
  - AWP-6858    0.384 [Port Authentication   ] 802.1x Authentication and MAC based Authentication      :: Confirm that the 802.1x port authentication and MAC based authentication operate correctly at the same time. | step1: Refer to 4.8
  - AWP-10275   0.369 [Process Monitoring    ] Memory Monitoring - 802.1X                              :: Correct output information for 802.1X | step1: Execute the command "show memory allocations" and capture output => Check memory in
  - AWP-5553    0.368 [LLDP                  ] Enable LLDP with 802.1x                                 :: Test for LLDP ports with 802.1x protocol running. | step1: Enable 802.1x on a port. Enable LLDP on this port => LLDP packets shoul
  - AWP-4975    0.355 [Limits                ] 802.1x Client on a unit                                 :: Confirm limit of 1024 802.1x clients | step1: ATKK run this test for us using IxLoad. => ATKK to run this test.
  - AWP-6724    0.343 [Port Authentication   ] 802.1X Authentication Log - Disabled dot1x Authenticati :: Confirm that the dot1x authenticator log outputs correctly. | step1: Disable dot1x Authentication Specify parameter : all (default
  - AWP-6722    0.342 [Port Authentication   ] 802.1X Authentication Log - no auth log dot1x all       :: Confirm that the dot1x authenticator log outputs correctly. | step1: Specify parameter : all Command : no auth log dot1x all => Al

### AWPTCM-T33356  |  area: Authentication Security IEEE 802.1XEncryptionType  |  feature: EAP-MD5
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-5435    0.471 [RADIUS                ] Local Radius & VCS / Web Auth / EAP-MD5                 :: Behavior of EAP-MD5 Authentication: Confirm that a client can be authenticated through Web Authentication using EAP-MD5 Challenge 
  - AWP-5443    0.467 [RADIUS                ] Local Radius & VCS / Tri-Auth / EAP-MD5                 :: Confirm that a client can be authenticated with dot1X(EAP-TLS) and WEB(EAP-MD5), MAC(EAP-MD5), and this client should be moved to 
  - AWP-5396    0.459 [RADIUS                ] Local Radius behavior of EAP-MD5 authentication Dot1x   :: Confirm that a client can be authenticated with EAP-MD5, and this client should be moved to the group’s vlan by dynamic vlan. | st
  - AWP-5410    0.455 [RADIUS                ] Local Radius & VCS / Dot1x Auth / EAP-MD5               :: Dot1X authentication by EAP-MD5: Confirm that a client can be authenticated with EAP-MD5, and this client should be moved to the g
  - AWP-5427    0.447 [RADIUS                ] Local Radius & VCS / MAC Auth / EAP-MD5                 :: Behavior of EAP-MD5 Authentication: Confirm that a client can be authenticated with PAP of MAC, and this client should be moved to
  - AWP-5405    0.428 [RADIUS                ] Local Radius dot1x(EAP-TLS), WEB(EAP-MD5), MAC(EAP-MD5) :: Confirm that a client can be authenticated with dot1X(EAP-TLS) and WEB(EAP-MD5), MAC(EAP-MD5), and this client should be moved to 
  - AWP-5400    0.416 [RADIUS                ] Local Radius behavior of EAP-MD5 authentication - Mac A :: Confirm that a client can be authenticated with PAP of MAC, and this client should be moved to the group’s vlan by dynamic vlan. |
  - AWP-5404    0.409 [RADIUS                ] Local Radius dot1x(EAP-PEAP), WEB(EAP-MD5), MAC(EAP-MD5 :: Confirm that a client can be authenticated with dot1X(EAP-PEAP) and WEB(EAP-MD5), MAC(EAP-MD5), and this client should be moved to
