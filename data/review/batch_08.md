# Rerank batch 08  (cases 240..269)

### AWPTCM-T44234  |  area: Switching IGMPSnooping  |  feature: IGMP v3 Snooping
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-7117    0.572 [IGMP                  ] Logging exist for IGMP and IGMPSnooping                 :: Verify logging works with IGMP and IGMP Snooping | step1: show log => display log output with correct information
  - AWP-8402    0.346 [MLD Snooping          ] MLD Snooping Interop with IGMP Snooping                 :: | step1: Ensure that both IGMP Snooping and MLD Snooping can operate independently of one another
  - AWP-17438   0.341 [IGMP Snooping         ] IGMP-CFG-001:IP IGMP Snooping                           :: | step1: 1. Verify that the user can enable and disable IGMP Snooping. => 1. The user should be able to enable and disable IGMP sn
  - AWP-17839   0.333 [IGMP Snooping         ] IP IGMP Snooping Source Timeout                         :: IP IGMP Snooping Source Timeout is working correctly. | step1: Setup multicast envronment using IGMP snooping Configure ip igmp sn
  - AWP-7097    0.331 [IGMP                  ] CLI Test - ip igmp snooping                             :: Use this command to enable IGMP Snooping. When this command is used in the Global Configuration mode, IGMP Snooping is enabled at 
  - AWP-7114    0.329 [IGMP                  ] CLI Test - show ip igmp snooping statistics             :: Use this command to display IGMP Snooping statistics data. | step1: Issue the command show ip igmp snooping statistics interface <
  - AWP-7128    0.325 [IGMP Snooping         ] Disable IGMP snooping per Vlan                          :: Confirm that IGMP snooping function is workable per VLAN | step1: ATKK 3.5 Disable IGMP snooping per Vlan => Refer to ATKK 3.5
  - AWP-17604   0.324 [IGMP Snooping         ] AWP5-IGMPSN-FUN-003 - AWP-7117:Logging exist for IGMP a :: Objective: Verify logging works with IGMP and IGMP Snooping Test Case: AWP-7117:Logging exist for IGMP and IGMPSnooping Automation

### AWPTCM-T44235  |  area: Switching LoopGuard  |  feature: LDF
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-22550   0.535 [Storm Control         ] receive LDF on different vlan                           :: | step1: connect port configured different tag vlan. => loop is not detected.
  - AWP-18059   0.510 [Customer Scenario     ] LDF                                                     :: Confirm that LDF works correctly. | step1: Confirm that MAC-Thrashing detects the occurrence of loop and the action works correctl
  - AWP-6315    0.499 [Storm Control         ] LDF frame receive test                                  :: Test that ports receive LDF frames | step1: Set loop-protection loop-detect ldf-rx-window in Global config mode. Create a loop bet
  - AWP-6314    0.484 [Storm Control         ] LDF frame transmission test                             :: Test that LDF counter increases | step1: Set loop-protection loop-detect ldf interval in an interface => LDF counter increases dep
  - AWP-14650   0.439 [Pause Control/Flow Con] Receive LDF frame                                       :: When the DUT received the LDF frame, check whether any cpu-queue is used by the frame. | step1: Set to connect between DUT and IXI
  - AWP-13622   0.436 [Storm Control         ] CR00036087 Minimum LDF interval                         :: Minimum LDF interval is 1 sec | step1: Issue loop-protection loop-detect command and configure ldf-interval parameter => ldf-inter
  - AWP-13784   0.396 [Storm Control         ] Using together Port Security and LDF                    :: LDF working correctly on the port which is assigned as Port Security | step1: Configure LDF and Port Security and confirm followin
  - AWP-22549   0.380 [Storm Control         ] action: none                                            :: | step1: confirm DUT does NOT send LDF

### AWPTCM-T44236  |  area: Switching LoopGuard  |  feature: QoS Storm Protection
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-19488   0.451 [QoS                   ] QoS: IPv6 Storm Protection                              :: This test was derived from Kochi-Univ scenario to confirm ipv6 storm protection works correct behavior with specified packets. | s
  - AWP-13384   0.401 [ATMF                  ] ATMF Control - QoS Storm Control Protection on an ATMF- :: ATMF packets should not be affected by QoS storm control protection (QSP), except for storm-action linkdown due to the port being 
  - AWP-13388   0.389 [ATMF                  ] ATMF Control - QoS Storm Control Protection on a Static :: ATMF packets should not be affected by QoS storm control protection (QSP), except for the storm-action linkdown due to the port be
  - AWP-19486   0.387 [QoS                   ] QoS: Storm Protection over 10gig traffic level - Storm- :: This is to verify that QoS can handle 10gig of traffic storm. Storm control on policy map triggers correctly when a specified stor
  - AWP-21924   0.386 [QoS                   ] Policy Based Storm Protection with LED Flashing Test    :: Confirm that LED is flashing when the Thrash Limiting works. | step1: Set storm-action to linkdown. Send in ixia traffic stream th
  - AWP-21940   0.381 [QoS                   ] Check the LED when recover from QoS Storm action        :: Check the LED when recover from QoS Storm action. | step1: Configure Findme trigger all and QoS Storm Protection on the device. Ac
  - AWP-13980   0.363 [Storm Control         ] Policy Based Storm Protection - storm-action & storm-do :: policy based storm protection has three possible actions linkdown Shutdown the port physically portdisable Disables the port in so
  - AWP-21930   0.362 [QoS                   ] Set QoS Storm action with SNMP via working-set          :: Check to execute qsp commands via working-set | step1: Execute the working-set hte DUT from the master. Execute following commands

### AWPTCM-T44238  |  area: Switching PacketStormProtection  |  feature: Broadcast Packet Filtering
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-7473    0.347 [Storm Control         ] Disable ingress filtering on a switchport               :: Test that ingress filtering is successfully disabled. | step1: Ingress filtering is enabled. Issue the command "switchport mode ac
  - AWP-7479    0.344 [Storm Control         ] enable ingress filtering                                :: Test that ingress filtering can still be successfully enabled. | step1: Ingress filtering is NOT disabled. Issue the command "swit
  - AWP-7042    0.329 [Logging               ] Command Line Handler - log filtering                    :: Test that all variations of log permanent command and CLI help work | step1: CLI/Log outputs => Log Filtering
  - AWP-8092    0.324 [RIPng                 ] Check route filtering using various methods             :: Check for route filtering | step1: 1.Verify route filtering works correctly using various methods a) distribute list b) passive-in
  - AWP-6386    0.290 [L2 Switching (L2 Learn] access mode - ingress filtering on                      :: Expect no SMAC address to be learned from tagged packets | step1: access mode - ingress filtering on => Expect no SMAC address to 
  - AWP-6590    0.288 [RIP                   ] Operational: Route Filtering by Route-Map               :: Confirm route filtering is working correctly | step1: Setup and configure a RIP routing environment Configure OSPF Routes to be re
  - AWP-14670   0.275 [Pause Control/Flow Con] Receive RIPv1 broadcast packet                          :: | step1: Set to connect between DUT and IXIA.
  - AWP-7483    0.263 [Storm Control         ] With ingress filtering enabled, set the thrash-limiting :: Test that thrash-limiting action can be set to none with ingress filtering enabled. | step1: Ingress filtering is NOT disabled. Is

### AWPTCM-T44239  |  area: Switching PacketStormProtection  |  feature: Multicast Packet Filtering
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-7473    0.362 [Storm Control         ] Disable ingress filtering on a switchport               :: Test that ingress filtering is successfully disabled. | step1: Ingress filtering is enabled. Issue the command "switchport mode ac
  - AWP-7479    0.359 [Storm Control         ] enable ingress filtering                                :: Test that ingress filtering can still be successfully enabled. | step1: Ingress filtering is NOT disabled. Issue the command "swit
  - AWP-7042    0.343 [Logging               ] Command Line Handler - log filtering                    :: Test that all variations of log permanent command and CLI help work | step1: CLI/Log outputs => Log Filtering
  - AWP-8092    0.338 [RIPng                 ] Check route filtering using various methods             :: Check for route filtering | step1: 1.Verify route filtering works correctly using various methods a) distribute list b) passive-in
  - AWP-6386    0.303 [L2 Switching (L2 Learn] access mode - ingress filtering on                      :: Expect no SMAC address to be learned from tagged packets | step1: access mode - ingress filtering on => Expect no SMAC address to 
  - AWP-6590    0.301 [RIP                   ] Operational: Route Filtering by Route-Map               :: Confirm route filtering is working correctly | step1: Setup and configure a RIP routing environment Configure OSPF Routes to be re
  - AWP-3471    0.284 [PIM-SM                ] CLI to set ip pim accept-register list                  :: Command Line test | step1: 1. Login to DUT. 2. Execute the command to enable filtering out of multicast sources. - ip pim accept-r
  - AWP-7483    0.274 [Storm Control         ] With ingress filtering enabled, set the thrash-limiting :: Test that thrash-limiting action can be set to none with ingress filtering enabled. | step1: Ingress filtering is NOT disabled. Is

### AWPTCM-T44240  |  area: Switching PacketStormProtection  |  feature: Unknown Unicast Packet Filtering
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-7473    0.303 [Storm Control         ] Disable ingress filtering on a switchport               :: Test that ingress filtering is successfully disabled. | step1: Ingress filtering is enabled. Issue the command "switchport mode ac
  - AWP-7479    0.300 [Storm Control         ] enable ingress filtering                                :: Test that ingress filtering can still be successfully enabled. | step1: Ingress filtering is NOT disabled. Issue the command "swit
  - AWP-18491   0.297 [Router Bridging       ] Forwarding L2 Unicast traffic                           :: Test that L2 unicast traffic is handled correctly | step1: 1. Set up DUT as above 2. Send unicast traffic from int1 to int2 => If 
  - AWP-7042    0.287 [Logging               ] Command Line Handler - log filtering                    :: Test that all variations of log permanent command and CLI help work | step1: CLI/Log outputs => Log Filtering
  - AWP-8092    0.283 [RIPng                 ] Check route filtering using various methods             :: Check for route filtering | step1: 1.Verify route filtering works correctly using various methods a) distribute list b) passive-in
  - AWP-9190    0.262 [VLAN                  ] Tagged vlan test - Transparent packet type test         :: Confirm that when generating broadcast / multicast / unknown address packet / well-known packet, it is not forwarded across the VL
  - AWP-5711    0.254 [LLDP                  ] Security: Unknown TLV packet                            :: Test for the LLDP security after Unknown TLV packet was received from the switch | step1: Configure DUT ena conf t lldp run int po
  - AWP-6386    0.254 [L2 Switching (L2 Learn] access mode - ingress filtering on                      :: Expect no SMAC address to be learned from tagged packets | step1: access mode - ingress filtering on => Expect no SMAC address to 

### AWPTCM-T44241  |  area: Switching PortSecurity  |  feature: Dynamic Port Security
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-27197   0.425 [AWC-lite              ] security                                                :: | step1: security <configured security id> Confirm that ID of security for network setting are configured on router.
  - AWP-5748    0.396 [Port Security (Intrusi] CLI to enable port security                             :: Command line test | step1: int port1.0.23 (no) switchport port-security => Tab can be use to complete the command. The no command 
  - AWP-27204   0.395 [AWC-lite              ] security                                                :: | step1: security <configured security id> Confirm that ID of security for WDS setting are configured on router.
  - AWP-9961    0.378 [DHCP Snooping         ] ARP Security - on dynamic channel after hotswap         :: Confirm normal operation on dynamic channel after hotswap | step1: ARP Security applied correctly on dynamic channel group interfa
  - AWP-5752    0.373 [Port Security (Intrusi] CLI to display port security status on an interface     :: Command line test | step1: show port-security interface port1.0.1 => Displays port security status tab key complete the command "?
  - AWP-10088   0.358 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Dynamic Ha :: Able to perform L3 hashing on IPv6 addresses with LAG Dynamic | step1: Link Aggregation - Dynamic . Hashing => L3 Hashing on IPv6 
  - AWP-10087   0.349 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Dynamic an :: Confirm configuration was correct over a LAG interface and traffic passes with linkup/down | step1: Link Aggregation - Dynamic. Co
  - AWP-5726    0.343 [Port Security (Intrusi] CLI to set maximum port security on an interface        :: Port Secuity | step1: Set Mac address learn limit to 10 interface port1.0.1 switchport port-security switchport port-security maxi

### AWPTCM-T44242  |  area: Switching PortSecurity  |  feature: Dynamic Limited Mode
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-10088   0.334 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Dynamic Ha :: Able to perform L3 hashing on IPv6 addresses with LAG Dynamic | step1: Link Aggregation - Dynamic . Hashing => L3 Hashing on IPv6 
  - AWP-10087   0.326 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Dynamic an :: Confirm configuration was correct over a LAG interface and traffic passes with linkup/down | step1: Link Aggregation - Dynamic. Co
  - AWP-10077   0.253 [IPv6                  ] IPv6 Switching - rstp topology change                   :: IPv6 and rstp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that rstp 
  - AWP-10078   0.247 [IPv6                  ] IPv6 Switching - stp topology change                    :: IPv6 and stp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that stp fo
  - AWP-14444   0.238 [ACL                   ] ipv4-limited-ipv6 maximum ACL                           :: There is hardware rule mode "ipv4-limited-ipv6" test. So, if the device does not have this mode, it is excluded. | step1: Set the 
  - AWP-23059   0.210 [IGMP                  ] Verify reports from a single host for multiple groups a :: and vice versa. | step1: Set an IGMP Group limit of 10 on a port. => Configuration accepted.
  - AWP-9502    0.208 [Roaming Authentication] Auth+ LAG Static - Multi-mode, no guest VLAN, per port, :: Test that authentication works with multi-mode, no guest VLAN, per port, dynamic VLAN | step1: Multi-Mode / no GuestVLAN / per por
  - AWP-10084   0.208 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Static     :: Confirm that it is correctly configured over a LAG interface and traffic passes with linkup/down | step1: 1.) Configure VCS Stack 

### AWPTCM-T44244  |  area: Switching PortSecurity  |  feature: Secure Mode
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-24596   0.509 [ATMF                  ] Check the support of secure mode and non-secure mode    :: Check the support of secure mode and non-secure mode | step1: upgrade the container area from non-secure mode to the secure mode =
  - AWP-25263   0.430 [ATMF                  ] Secure-mode support for max virtual-links               :: Test secure-mode support for maximum virtual-links. Secure-mode currently only support 126 nodes, this needs to be verified and te
  - AWP-24623   0.394 [ATMF                  ] support of secure mode on container                     :: support of secure mode on container | step1: if controller is in secure mode a new container should be in secure mode without any 
  - AWP-24362   0.372 [ATMF                  ] Check blacklisting of host address works when secure mo :: | step1: 1) Enable ATMF Secure mode. 2) Send syslog message to ATMF Master to simulate a threat on the network 3) Check IP addres 
  - AWP-24361   0.366 [ATMF                  ] Check blacklisting of host address works when secure mo :: | step1: 1) Disable ATMF Secure mode. 2) Send syslog message to ATMF Master to simulate a threat on the network 3) Check IP addre 
  - AWP-25844   0.346 [OpenFlow              ] Connection Interruption - Secure Mode                   :: Confirm that Secure Mode works correctly after disconnecting SESC. | step1: Execute "show run" and "show openflow config". => Conf
  - AWP-26623   0.346 [OpenFlow              ] Connection Interruption - Secure Mode                   :: Confirm that Secure Mode works correctly after disconnecting SESC. | step1: Execute "show run" and "show openflow config". => Conf
  - AWP-24624   0.333 [ATMF                  ] support of secure mode on controller                    :: support of secure mode on controller | step1: turn on the secure mode on the controller => confirm previously configured areas are

### AWPTCM-T44245  |  area: Switching STP  |  feature: Spanning tree port fast
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-12334   0.497 [xSTP                  ] Configuring mode of spanning tree                       :: Configuring mode of spanning tree | step1: Issue the command "spanning-tree mode [stp,rstp,mstp] => Issuing the command should be 
  - AWP-12096   0.432 [SMTP                  ] SMTP On Spanning Tree                                   :: Confirm SMTP is working on Spanning Tree | step1: Spanning Tree enabled Send mail => SMTP must work with Spanning Tree Should not 
  - AWP-9464    0.392 [xSTP                  ] Interop with STP & MSTP on other devices.               :: Verify interoperability of RSTP with other spanning-tree modes | step1: Interop with STP & MSTP on other devices. Minimum of 3 Swi
  - AWP-9400    0.372 [xSTP                  ] BPDU Forwarding behavior with spanning tree protocols   :: BPDU Forwarding (x600 only) | step1: BPDU Forwarding cannot enabled with spanning tree protocols (stp, rstp, mstp) => BPDU Forward
  - AWP-23102   0.359 [RSPAN - Mirror to VLAN] RSPAN Egress: STP BPDUs not sent from switch to remote- :: Spanning-Tree BPDUs will not be sent from the switch to the remote-mirror egress port | step1: Send IXIA Traffic on SOURCE SWITCH.
  - AWP-24882   0.354 [xSTP                  ] BPDU Forwarding behavior with spanning tree protocols   :: BPDU Forwarding (x930,SBx908,SBx81CFC400,SBx81CFC960) | step1: BPDU Forwarding cannot enabled with spanning tree protocols (stp, r
  - AWP-10078   0.352 [IPv6                  ] IPv6 Switching - stp topology change                    :: IPv6 and stp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that stp fo
  - AWP-9621    0.346 [xSTP                  ] Show command output                                     :: | step1: Test the following commands: show spanning-tree mst config show spanning-tree mst show spanning-tree mst instance [numbe 

### AWPTCM-T44246  |  area: Switching Trunking  |  feature: Port Trunking LACP
folder:/New Platform Template/Switching  steps:0  obj:True
ZEPHYR: OBJ: Dynamic reconfiguration Traffic flows correctly Fail over channel member and ensure traffic flows correctly ||
  - AWP-13647   0.495 [Link Aggregation      ] Max trunking group (lacp)                               :: Verify max number of link aggregation (lacp). Defined by the total number of entries in the aggregation hardware table. The result
  - AWP-7910    0.316 [VRF-Lite              ] Setup 802.1Q Trunking with VRF-Lite                     :: To setup multiple VRF's and assign vlans to each VRF Assign a port to be a member of all vlans Pass L2 Traffic | step1: Program th
  - AWP-27874   0.297 [JITC Certification    ] V-5623:Port trunking must be disabled on all access por :: ---- Warning ---- TestLink Warning test case name is too long (131 chars) > 100 => has been truncated Original name V-5623:Port tr
  - AWP-5562    0.294 [LLDP                  ] Management address TLV: trunking                        :: Test for management address TLV transmit with trunking | step1: Change the mode of the port to be a trunk and assign several vlans
  - AWP-10775   0.286 [VRF-Lite              ] Setup 802.1Q Trunking with VRF lite                     :: To setup 64 VRF's and assign 64 vlans to each VRF Ingress and egress static/dynamic channel groups to be a member of all vlans/VRF
  - AWP-10752   0.283 [VRF-Lite              ] Setup 802.1Q Trunking with VRF lite                     :: To setup multiple VRF's and assign vlans to each VRF Assign a port to be a member of all vlans Assign an IP address to each of the
  - AWP-10765   0.271 [VRF-Lite              ] Setup 802.1Q Trunking with VRF-Lite                     :: To setup 64 VRF's and assign a vlan to each VRF Pass L2 Traffic | step1: Program the switch with 63 VRF instances Create 63 vlans 
  - AWP-10776   0.269 [VRF-Lite              ] 802.1Q Trunking with L3 islolation                      :: To test L3 isolation on VRF lite using an 802.1Q trunk. | step1: ping the same vlan on the conencting switch. => the ip address sh

### AWPTCM-T44247  |  area: Switching Trunking  |  feature: Resilient Ethernet Fabric
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-9072    0.286 [z_Inactive            ] QoS:fabric-queue map - configured                       :: QoS:fabric-queue map - configured | step1: Map egress queue to fabric queue. Need to find counters that confirm fa queue usage. No
  - AWP-9071    0.274 [QoS                   ] QoS:fabric-queue map - default                          :: Verify default queue configuration Egress Queue Fabric Queue ----------------------- 0 0 1 0 2 1 3 1 4 2 5 2 6 3 7 3 | step1: veri
  - AWP-9070    0.203 [QoS                   ] QoS: Global QoS - Fabric Queue Strict/WRR Commands & sh :: Verify that QoS fabric queues can be set to WRR with a weight - all queues | step1: Test that QoS fabric queues can be set to WRR 
  - AWP-13647   0.175 [Link Aggregation      ] Max trunking group (lacp)                               :: Verify max number of link aggregation (lacp). Defined by the total number of entries in the aggregation hardware table. The result
  - AWP-21773   0.162 [PPP                   ] PPP IP Borrow from ethernet interface                   :: Verify that PPP interface can borrow IP address from an ethernet interface. | step1: Configure PPP interface to borrow IP address 
  - AWP-12167   0.156 [QoS                   ] QoS: fabric adapter queueing                            :: Use traffic to verify fabric adapter qos is correctly implemented and configurable: | step1: This method needs to be verified Syst
  - AWP-5562    0.156 [LLDP                  ] Management address TLV: trunking                        :: Test for management address TLV transmit with trunking | step1: Change the mode of the port to be a trunk and assign several vlans
  - AWP-27874   0.151 [JITC Certification    ] V-5623:Port trunking must be disabled on all access por :: ---- Warning ---- TestLink Warning test case name is too long (131 chars) > 100 => has been truncated Original name V-5623:Port tr

### AWPTCM-T44248  |  area: Switching VLAN  |  feature: IP subnet VLAN
folder:/New Platform Template/Switching  steps:0  obj:True
ZEPHYR: OBJ: Verify whether Multiple Dynamic VLAN can operate combination with IP subnet VLAN ■Environment IXIA p1 ---------- (port1. ||
  - AWP-9196    0.570 [VLAN                  ] IP subnet based VLAN and invalid source IP address      :: Confirm that the invalid source IP packets are not forwarded. | step1: 1. Setup the device as shown in the setup attached ! vlan d
  - AWP-9208    0.558 [VLAN                  ] Combination Test - Private VLAN and IP subnet-based VLA :: Combination Test - Private VLAN and IP subnet-based VLAN | step1: 1. Create primary vlan 10 and 20 2. Create rule for subnet 192.1
  - AWP-9195    0.535 [VLAN                  ] IP Subnet VLAN and ENABLE IP module                     :: Test IP Subnet VLAN Functionality when IP Module is enabled ** IP Module of AW+ Switched is enabled on the default. Field Issue: C
  - AWP-19369   0.528 [z_ATKK_Inquiry_Based  ] IB-3:IP subnet based VLAN and invalid source IP address :: Scope Confirm that the invalid source IP packets are not forwarded. | step1: 1. Setup the device as shown in the setup attached ! 
  - AWP-9200    0.438 [VLAN                  ] IP subnet based VLAN and VLSM                           :: Confirm the IP subnet VLAN works correctly when use the VLSM (variable length subnet mask). | step1: 1. Set up is the same as AWP-
  - AWP-9221    0.423 [VLAN                  ] Protocol based VLAN and CPU packets                     :: Protocol based VLAN and CPU packets | step1: 1. Protocol based VLAN and CPU packets - DHCP - ARP - ICMP - Trap - BPDU Can use the 
  - AWP-19373   0.414 [z_ATKK_Inquiry_Based  ] IB-7:IP subnet based VLAN and VLSM                      :: Scope Confirm the IP subnet VLAN works correctly when use the VLSM (variable length subnet mask). | step1: 1. Set up is the same a
  - AWP-22538   0.409 [VLAN                  ] vlan classifier and LACP                                :: | step1: Run following config (DUT) vlan database vlan 2,10,20 state enable ! vlan classifier rule 1 ipv4 192.168.10.0/24 vlan 10 

### AWPTCM-T44249  |  area: Switching VLAN  |  feature: MAC based VLAN
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-9879    0.370 [DHCP Snooping         ] DHCP Snooping with Port authentication - MAC based      :: Confirm that authentication should function normally | step1: Portauth/MAC based => 802.1x and MAC based authentication should fun
  - AWP-9182    0.333 [VLAN                  ] Port based VLAN with LACP                               :: Test that LAG ports can be assigned to a VLAN | step1: 1. Create a static LACP 2. under po1 interface, issue command: "switchport 
  - AWP-6858    0.316 [Port Authentication   ] 802.1x Authentication and MAC based Authentication      :: Confirm that the 802.1x port authentication and MAC based authentication operate correctly at the same time. | step1: Refer to 4.8
  - AWP-6782    0.313 [Port Authentication   ] MAC Based Authentication Test                           :: Confirm the behavior when the Authenticator is set as MAC base authentication. | step1: >> Please see the attached files Configure
  - AWP-5558    0.312 [LLDP                  ] LLDP on port based VLAN with LLDP TLV's configured      :: Test for port based VLAN with LLDP TLV's configured | step1: Configure a port based vlan and enable all of the LLDP TLV's to trans
  - AWP-9901    0.306 [DHCP Snooping         ] DHCP Snooping with 802.1x & MAC based auth              :: Expect normal operation with 802.1x and MAC auth | step1: 802.1x & MAC based auth => Expect normal operation
  - AWP-9238    0.300 [VLAN                  ] Maximum number of port based vlan                       :: Maximum number of port based vlan | step1: Maximum number of Port-based VLAN 1. Create maximum number of vlan 2-4094 2. Create ran
  - AWP-9179    0.292 [VLAN                  ] Deleting and creating port based VLAN                   :: Deleting and creating port based VLAN | step1: 1. Create port based VLANs. 2. Delete created port based VLANs. 3. Re-create same V

### AWPTCM-T44250  |  area: Switching VLAN  |  feature: Guest VLAN
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-9900    0.438 [DHCP Snooping         ] Dynamic vlan assignment and guest vlan                  :: Expect normal operation with dynamic and guest vlan | step1: Dynamic vlan assignment and guest vlan => Expect normal operation
  - AWP-15506   0.438 [RADIUS                ] RADIUS packet on Guest VLAN                             :: Confirm that VLAN ID is included in RADIUS packet when authentication port is assigned Guest VLAN. | step1: Execute Authentication
  - AWP-9307    0.370 [Web Authentication    ] Web-auth / Auth-fail vlan on / ACL on / guest-vlan on   :: Auth-fail vlan Auth-fail vlan without VCS | step1: Web-auth Auth-fail vlan on / ACL on guest-vlan on Note: Meaning of authenticati
  - AWP-22353   0.369 [RADIUS                ] AAA List with Guest VLAN                                :: Confirm that radius query is send on aaa LIST when authentication port is assigned Guest VLAN. | step1: Execute Authentication fro
  - AWP-9502    0.363 [Roaming Authentication] Auth+ LAG Static - Multi-mode, no guest VLAN, per port, :: Test that authentication works with multi-mode, no guest VLAN, per port, dynamic VLAN | step1: Multi-Mode / no GuestVLAN / per por
  - AWP-9534    0.362 [Roaming Authentication] Roaming Auth - Multi-mode, no guest VLAN, per port, dyn :: Authentication works with multi-mode, no guest VLAN, per port, dynamic VLAN | step1: Multi-Mode / no GuestVLAN / per port / Dynami
  - AWP-9529    0.360 [Roaming Authentication] Roaming Auth - Single-mode, no guest VLAN, per port, no :: Authentication works correctly with single-mode, no guest VLAN, per port and no dynamic VLAN | step1: Single-Mode / no GuestVLAN /
  - AWP-22305   0.360 [ATMF                  ] same guest name can be configured on multiple ports     :: The same guest name can be configured on multiple ports if the guest has the same characteristics | step1: attach the same type of

### AWPTCM-T44251  |  area: Switching VLAN  |  feature: Voice VLAN
folder:/New Platform Template/Switching  steps:3  obj:False
ZEPHYR: Configure the swithcport with a voice VLAN | Configure a DHCP pool for the voice VLAN | Mirror the port with the voice VLAN and connect an IP phone
  - AWP-5694    0.489 [LLDP                  ] Interop with IP Phones: Voice VLAN configuration        :: Test for the IP Phones to communicate after configuring the voice VLAN and authentication | step1: Configure the switch with voice
  - AWP-9899    0.447 [DHCP Snooping         ] DHCP Snooping - Voice vlans                             :: Expect normal operation with voice vlans | step1: Voice vlans => Expect normal operation
  - AWP-5533    0.422 [LLDP                  ] Command Line Handler: switchport voice vlan             :: Test for switchport voice vlan command | step1: Command Handler: --> switchport voice vlan <options> --> no switchport voice vlan 
  - AWP-5531    0.407 [LLDP                  ] Command Line Handler: switchport voice vlan priority    :: Test for switchport voice vlan priority command | step1: Command Handler: --> switchport voice vlan priority <0-7> --> no switchpo
  - AWP-9165    0.405 [VLAN                  ] Command Line Handler - switchport voice vlan            :: Device Management Tests - Command should configure the Voice VLAN tagging advertised when the transmission of LLDP-MED Network Pol
  - AWP-5692    0.389 [LLDP                  ] LLDP-MED Opration: voice VLAN with VID                  :: Test for LLDP Operation using voice VLAN with VID | step1: Configure a voice vlan with a vid and the change the port to be an acce
  - AWP-5628    0.383 [LLDP                  ] Network Policy TLV: voice VLAN as untagged              :: Test for the valid frames sent whenever the voice VLAN was set as untagged. | step1: Configure a voice vlan as untagged and captur
  - AWP-9166    0.376 [VLAN                  ] Command Line Handler - switchport voice vlan priority   :: Device Management Tests - Command should configure the Layer 2 user priority advertised when the transmission of LLDP-MED Network 

### AWPTCM-T44252  |  area: Switching VLAN  |  feature: Q-in-Q
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-10077   0.428 [IPv6                  ] IPv6 Switching - rstp topology change                   :: IPv6 and rstp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that rstp 
  - AWP-10078   0.418 [IPv6                  ] IPv6 Switching - stp topology change                    :: IPv6 and stp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that stp fo
  - AWP-10087   0.353 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Dynamic an :: Confirm configuration was correct over a LAG interface and traffic passes with linkup/down | step1: Link Aggregation - Dynamic. Co
  - AWP-10084   0.353 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Static     :: Confirm that it is correctly configured over a LAG interface and traffic passes with linkup/down | step1: 1.) Configure VCS Stack 
  - AWP-10088   0.350 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Dynamic Ha :: Able to perform L3 hashing on IPv6 addresses with LAG Dynamic | step1: Link Aggregation - Dynamic . Hashing => L3 Hashing on IPv6 
  - AWP-2480    0.315 [VRF-Lite              ] Through-put performance Inter VRF switching hardware    :: To check throughput performance (RFC2544) for traffic switched in hardware | step1: Setup a traffic path such that traffic is swit
  - AWP-10085   0.311 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Static Has :: Able to perform L3 hashing on IPv6 addresses | step1: 1.) Configure VCS Stack 2.) Configure EPSR and Static Link Aggregation 3.) C
  - AWP-29644   0.305 [OpenFlow              ] ER-2059 - Repeat switching between hardware processing  :: Confirm that memory leak does not occur when repeat switching between hardware processing and software processing. | step1: Regist

### AWPTCM-T44253  |  area: Switching VLAN  |  feature: GVRP
folder:/New Platform Template/Switching  steps:2  obj:True
ZEPHYR: OBJ: Check DUT can learn VLAN's from a GVRP server Check DUT can propogate VLAN's to other switches https://www.alliedtelesis || Configure both switches for GVRP | Check that the DUT can learn VLANs f
  - AWP-1094    0.403 [GVRP                  ] GVRP VLAN limit                                         :: Device functional to VLAN limit. | step1: Dynamic VLAN limit can be created => Dynamic vlan limit can be reached. and Vlans age ou
  - AWP-4309    0.400 [GVRP                  ] GVRP Dynamic Vlan creation can be disabled              :: GVRP Dynamic Vlan creation can be disabled | step1: 1.configure device with a GVRP neighbor 2.set gvrp dynamic-vlan-creation enabl
  - AWP-5       0.391 [GVRP                  ] GVRP Show commands                                      :: GVRP - Show commands adequately display status of GVRP dynamic vlans. [Note that dynamic vlans not normally indicated in running c
  - AWP-1089    0.364 [GVRP                  ] GVRP dynamic-vlan-creation enabled/disabled             :: GVRP with dynamic-vlan-creation disabled will advertise registrations of static VLANs, but no VLANs will be created. | step1: 1.co
  - AWP-4310    0.364 [GVRP                  ] GVRP Configuration on Dynamic - errors at startup       :: GVRP Dynamically created VLANs can be configured (eg with an IP address) but this will result in an error at startup. | step1: 1.S
  - AWP-1093    0.358 [GVRP                  ] GVRP Interop EPSR                                       :: GVRP and EPSR can coexist - but no interoperability expected. | step1: Simple EPSR ring of at least 2 devices. Configure GVRP on s
  - AWP-1086    0.355 [GVRP                  ] GVRP Dynamic vlans can be converted to static           :: GVRP Dynamic VLANs can be converted via configuration to static VLANs. | step1: STart with ports with all VLANs added Setup device
  - AWP-10      0.322 [GVRP                  ] GVRP Dynamic vlans timeout                              :: GVRP Dynamic vlans timeout - test up to 400 vlans in this test. | step1: Connect to a GVRP peer -with 400 static vlans configured.

### AWPTCM-T44254  |  area: Switching VLAN  |  feature: Upstream Forwarding Only   on Private VLAN
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-27055   0.455 [UFO                   ] Verify multiple Upstream UFO interfaces                 :: Verify that UFO can have multiple upstream interfaces configured for 1 UFO VLAN. Upstream Forwarding Only TFS section 3.1.1 https:
  - AWP-27054   0.413 [UFO                   ] Verify UFO on VLAN 1                                    :: Verify that UFO can be configured and functions as expected on VLAN 1. Upstream Forwarding Only TFS section 3.1.1 https://intranet
  - AWP-18060   0.412 [Customer Scenario     ] Private VLAN                                            :: Confirm that Private VLAN works correctly. | step1: Confirm that Private VLAN allows or detects the traffic as configured. => Conf
  - AWP-27098   0.411 [UFO                   ] Verify multiple Upstream UFO interfaces - Stacking      :: Verify that UFO can have multiple upstream interfaces configured for 1 UFO VLAN across stack members. Upstream Forwarding Only TFS
  - AWP-27042   0.395 [UFO                   ] Verify: debug private-vlan ufo                          :: Verify the "debug private-vlan ufo" command. Upstream Forwarding Only TFS section 4.3.2 https://intranet.atlnz.lc/awpwiki/index.ph
  - AWP-27040   0.385 [UFO                   ] Verify: show running-config                             :: Verify the "show running-config" command. Upstream Forwarding Only TFS section 4.1 https://intranet.atlnz.lc/awpwiki/index.php/Ups
  - AWP-9903    0.374 [DHCP Snooping         ] Private VLAN                                            :: Expect normal operation | step1: Private VLAN => Expect normal operation
  - AWP-27105   0.373 [UFO                   ] Verify IGMP with UFO                                    :: Verify IGMP over a UFO VLAN, there is no particular interaction between Private VLAN UFO and IGMP Snooping. Upstream Forwarding On

### AWPTCM-T44256  |  area: Switching  |  feature: Flow Control
folder:/New Platform Template/Switching  steps:3  obj:False
ZEPHYR: Enable Flow control on a switchport | Over subscribe one of the switchports and check that the DUT | send flow control pause frames to the DUT and check that the
  - AWP-15854   0.335 [Pause Control/Flow Con] Flow control operation after Linkdown/up                :: Confirm that flow control works correctly affter the port link goes down/up. | step1: Transmit packet from IXIA1 at wirerate. Then
  - AWP-15831   0.308 [Pause Control/Flow Con] Flow control interoperability with platform             :: Confirm that Flow control Send/Receive works correctly when connected different platform. | step1: If Partner support Pause send/r
  - AWP-15855   0.301 [Pause Control/Flow Con] Flow control operation with MDI                         :: Confirm that flowcontrol works correctly on all of supported MDI configuration. | step1: Transmit packet from IXIA1 at wirerate. T
  - AWP-10164   0.294 [Pause Control/Flow Con] x908: Loopback port - activate flowcontrol and broadcas :: Able to received flow control frames from DUT as observed from IXIA Explorer | step1: - loopback from port3-4,port5-6 …. Port11-12
  - AWP-10174   0.289 [Pause Control/Flow Con] x900-12: Loopback port - activate flowcontrol and broad :: Able to received flow control frames from DUT as observed from IXIA Explorer | step1: - loopback from port3-4,port5-6 …. Port11-12
  - AWP-24862   0.280 [OpenFlow              ] Flowcontrol                                             :: Confirm that DUT stops send/receive packets when DUT receive pause frame. | step1: Send any packets between HostA and Host1 bidire
  - AWP-15830   0.280 [Pause Control/Flow Con] Flow control operation on supported module              :: Confirm that flow control Send/Receive works correctly on any supported module such as SFP/XFP and so on. CR-54636 Flow control do
  - AWP-15858   0.271 [Pause Control/Flow Con] Flow control operation with different packet type       :: Confirm that flowcontrol works differntly depend on packet type. In AW+ 5.4.4, Pause packet send when Broadcast and Multicast rece

### AWPTCM-T44257  |  area: Switching  |  feature: Jumbo Frames
folder:/New Platform Template/Switching  steps:1  obj:True
ZEPHYR: OBJ: Check Jumbo Frames can be forwarded ||
  - AWP-10100   0.515 [IPv6                  ] IPv6 Address - jumbo frame                              :: Confirm that "jumbo frame" is supported | step1: Enable jumbo frame support. Issue command platform jumboframe. Pass jumbo frame t
  - AWP-6448    0.489 [L2 Switching (L2 Learn] Maximum Jumbo frame size is forwarded & learned,        :: Verify that mazimum jumbo frames size is forwarded and learned | step1: Maximum Jumbo frame size is forwarded & learned, => x900 s
  - AWP-13711   0.418 [IP Helper             ] CR00035996 - x510 crashes when transferring jumbo frame :: | step1: transmit jumbo frames using IP helper => DUT must not crash when transmitting jumbo frames using IP helper
  - AWP-6446    0.401 [L2 Switching (L2 Learn] Maximum tagged frame size is learned & forwarded (jumbo :: 1522 to be accepted | step1: Maximum tagged frame size is learned & forwarded (jumbo not enabled) => 1522 to be accepted
  - AWP-23090   0.398 [RSPAN - Mirror to VLAN] RSPAN Source: Jumbo Frames on RSPAN Ports               :: Verify if jumbo frames can be mirrored. | step1: Transmit a packet with the max allowed frame size (Pkts + 4bytes RSPAN vlan) On I
  - AWP-13593   0.363 [Logging               ] Logging - jumbo multicast frame                         :: To check that when jumbo frame support is enabled there would be no unexpected log messages CR36171: x908 PUMA: Log message shown 
  - AWP-5000    0.361 [Limits                ] Max Jumbo frame size                                    :: To verify silicon max jumbo framesize | step1: Sending in jumbo framesize packets - for x900/x908 requires platform jumboframe (at
  - AWP-6445    0.338 [L2 Switching (L2 Learn] Maximum untagged frame size is learned & forwarded (jum :: Check for 1518 bytres, but 1522 will also be accepted. | step1: Maximum untagged frame size is learned & forwarded (jumbo not enab

### AWPTCM-T44259  |  area: Switching  |  feature: ITU-T G.8032 and CFM
folder:/New Platform Template/Switching  steps:2  obj:True
ZEPHYR: OBJ: Verify G.8032 w/ CFM. || Verify G.8032 w/ CFM. | Need to verify with breaks using media converters to keep th
  - AWP-26019   0.682 [G.8032                ] Functionallity: G.8032 w/ CFM                           :: Verify G.8032 w/ CFM. | step1: Verify G.8032 w/ CFM.
  - AWP-26059   0.398 [G.8032                ] Interop: CFM and G.8032 - Not done will complete after  :: Verify that CFM will function on a G.8032 interface. | step1: Verify that CFM can be configured on the G.8032 interfaces. => CFM c
  - AWP-28483   0.288 [Software Licensing    ] License - G.8032/CFM - IE210L RoW                       :: Verify G.8032 and CFM license can be enable on IE210L. | step1: Install g.8032 license by "license" command. => Index : 2 License 
  - AWP-26698   0.283 [CFM                   ] CLI:show running-config for cfm                         :: Verify the "show running-config" command output for CFM. | step1: Verify that the "show running-config" command shows the CFM conf
  - AWP-28482   0.277 [Software Licensing    ] License - G.8032/CFM - IE210L ATKK                      :: Verify G.8032 and CFM and PTP license can be enable on IE210L | step1: Install g.8032 license by "license" command. => Index : 3 L
  - AWP-26723   0.257 [CFM                   ] Functionality:CFM w/ VLAN tagged                        :: Verify that CFM can function with a tagged VLAN. | step1: Verify CFM using an tagged VLAN. => That CFM can functions with an tagge
  - AWP-27046   0.244 [Software Licensing    ] License - G.8032/CFM - x550 RoW                         :: Verify G.8032 and CFM license can be enable on x550. | step1: Install g.8032 license by "license" command. => Check G.8032 and CFM
  - AWP-27047   0.237 [Software Licensing    ] License - G.8032/CFM - x550 ATKK                        :: Verify G.8032 and CFM license can be enable on x550. | step1: Install g.8032 license by "license" command. => Check G.8032 and CFM

### AWPTCM-T44262  |  area: Switching  |  feature: UDLD
folder:/New Platform Template/Switching  steps:1  obj:True
ZEPHYR: OBJ: Configure enable/disable all Fiber-Optic ports on CLI (Default is disabled) || - Bootup device with no config - Enable UDLD globally: awplu
  - AWP-10483   0.933 [UDLD                  ] UDLD Global Configuration                               :: Configure enable/disable all Fiber-Optic ports on CLI (Default is disabled) | step1: - Bootup device with no config - Enable UDLD 
  - AWP-10486   0.777 [UDLD                  ] UDLD Port Configuration                                 :: Configure enable/disable each Physical ports on CLI. (Default is disabled) | step1: - Bootup device with no config - Enable UDLD o
  - AWP-10491   0.571 [z_Inactive            ] Show UDLD Globally                                      :: Display UDLD system wide setting and status on CLI | step1: - Bootup device with no config -Enable/disable udld on global configur
  - AWP-10472   0.545 [UDLD                  ] Command Line Interface: udld port disable / no udld por :: Test that UDLD feature can be disabled to specific ports. This command has effect to both copper and fiber-optic port. UDLD is alw
  - AWP-10471   0.533 [UDLD                  ] Command Line Interface: udld port / no udld port        :: Test that UDLD feature can be enabled and disabled to specific ports. This command has effect to both copper and fiber-optic port.
  - AWP-10484   0.508 [UDLD                  ] UDLD Treatment for Combo-ports                          :: Always maintain Combo-ports as Fiber-Optic ports even though Copper port is upped. (Not applicable for x200) | step1: - Link-up th
  - AWP-10496   0.499 [UDLD                  ] UDLD Action                                             :: Device will make the port DOWN when it detects a unidirectional link | step1: Configure UDLD. Connect a unidirectional link and Ch
  - AWP-10504   0.491 [UDLD                  ] UDLD After Interface Shutdown                           :: UDLD must still work with shutdown and no shutdown on an interface. | step1: Configure UDLD on an interface. Shutdown the interfac

### AWPTCM-T44263  |  area: Switching  |  feature: MAC Security, if supported by HW
folder:/New Platform Template/Switching  steps:4  obj:False
ZEPHYR: Configure Mac sec on the link between the DUT and sw1. Use t | Configure Ixia to send traffic over the MAC sec link. Send t | Shutdown the port, wait 15 seconds then restore the port. tr
  - AWP-5727    0.248 [Port Security (Intrusi] check for learned mac addresses                         :: Port Secuity | step1: Configure port security on interface port int port1.0.23 switchport port-security switchport port-security m
  - AWP-9868    0.241 [DHCP Snooping         ] Compare ARP Security with internal HW and source MAC    :: ARPs are effectively blocked as per snooping database | step1: ARP Security - compare with internal HW field different from source
  - AWP-5729    0.235 [Port Security (Intrusi] learned mac addresses are still in MAC table after rebo :: Port Secuity | step1: Configure port security on port interface Send IXIA frame with source mac more than the port security maximu
  - AWP-27197   0.230 [AWC-lite              ] security                                                :: | step1: security <configured security id> Confirm that ID of security for network setting are configured on router.
  - AWP-5748    0.226 [Port Security (Intrusi] CLI to enable port security                             :: Command line test | step1: int port1.0.23 (no) switchport port-security => Tab can be use to complete the command. The no command 
  - AWP-24247   0.221 [ATMF                  ] Check reboot will be supported                          :: Check reboot will be supported | step1: check reboot will be supported => confirm containers still work as masters after the reboo
  - AWP-10087   0.216 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Dynamic an :: Confirm configuration was correct over a LAG interface and traffic passes with linkup/down | step1: Link Aggregation - Dynamic. Co
  - AWP-27204   0.214 [AWC-lite              ] security                                                :: | step1: security <configured security id> Confirm that ID of security for WDS setting are configured on router.

### AWPTCM-T44264  |  area: QoS  |  feature: Hierarchical QOS
folder:/New Platform Template/QoS  steps:1  obj:False
  - AWP-9065    0.391 [QoS                   ] QoS globally enabled                                    :: Verify QoS commands are accepted when QoS is globally enabled | step1: qos can be enabled with the command: mls qos enable => Sele
  - AWP-10099   0.340 [IPv6                  ] IPv6 Address - QoS field works                          :: QoS output should reflect input QoS field | step1: QOS field works - output queue reflects input QoS field => Output queue reflect
  - AWP-21078   0.290 [QoS                   ] Command Handler: QoS                                    :: Verify command work properly | step1: Check 'qos' commands for: =>Command execution (sh run, sh run int port <range>) =>Negation o
  - AWP-7627    0.285 [Policy Based Routing  ] QoS configuration applied to the classified traffic     :: Confirm that QoS continue to function and not affected by PBR | step1: QoS configuration (eg. set commands under policy map) can b
  - AWP-13659   0.280 [ACL                   ] Interoperability with QoS                               :: ACLs be able to enable when QoS is set on ports. And can execute inset-before. | step1: Insert, move and remove ACL to a port set 
  - AWP-9064    0.263 [QoS                   ] QoS Global Disabled State - commands return error       :: Verify QoS commands will return error messages when QoS is globally disabled | step1: With mls qos disabled execute QOS commands. 
  - AWP-21494   0.255 [ACL                   ] Large IPv6 ACL group with max QoS utilization           :: Large extended ACL group should not affect QoS utilization | step1: 1. Fill-up QoS and ACL table Check "sh platform classifier sta
  - AWP-21493   0.253 [ACL                   ] Large IPv4 ACL group with max QoS utilization           :: Large extended ACL group should not affect QoS utilization | step1: 1. Fill-up QoS and ACL table Check "sh platform classifier sta

### AWPTCM-T44265  |  area: QoS  |  feature: Virtual Packet Buffer
folder:/New Platform Template/QoS  steps:1  obj:False
  - AWP-5567    0.311 [LLDP                  ] Tx buffer algorithm                                     :: Test for the tx buffer's algorithm on the hierarchy of TLVs to be dropped first. | step1: This test is to check the algorithm when
  - AWP-22051   0.261 [Hardware Health Monito] ER-528 - Packet-buffer disable/reset with Global HW-mon :: This command is also controlled by the global hw-monitoring enable (i.e. disabling hardware monitoring will prevent this monitorin
  - AWP-8329    0.236 [IPv4                  ] Virtual-MAC                                             :: Check for virtual-MAC feature | step1: Check that [Feature] uses virtual-MAC when it is enabled. - Requires saving config and rebo
  - AWP-6846    0.228 [Port Authentication   ] Throughput Test - Port Authentication                   :: Confirm the throughput when port authentication is enabled. | step1: Send L2 Unicast streams from Ixia-111 and Ixia-112. Confirm t
  - AWP-9065    0.220 [QoS                   ] QoS globally enabled                                    :: Verify QoS commands are accepted when QoS is globally enabled | step1: qos can be enabled with the command: mls qos enable => Sele
  - AWP-14145   0.211 [ATMF                  ] ATMF Virtual Links - Show commands & counters           :: ATMF Virtual Links - show command display status of virtual link and check ATMF virtual link couters if it is operating properly |
  - AWP-4122    0.208 [z_Inactive            ] EPSR with Virtual MAC test                              :: Enable Virtual MAC with EPSR, save configuration and reboot | step1: Check that [Feature] uses virtual-MAC when it is enabled. - R
  - AWP-25270   0.204 [ATMF                  ] Show atmf virtual-link                                  :: AMF300VL-12: Add show atmf virtual-link id ? remote-id ? | step1: sh atmf virtual-links id <1-4094> => Should display relevant det

### AWPTCM-T44266  |  area: QoS  |  feature: CoS
folder:/New Platform Template/QoS  steps:1  obj:False
  - AWP-9067    0.674 [QoS                   ] QoS cos-queue map default                               :: Verify QoS cos-queue map in correct default values | step1: Examine with show command. "show mls qos maps cos-queue" => Def is for
  - AWP-9073    0.586 [QoS                   ] QoS:switchport interface default cos                    :: Verify that the default COS value is still tagged on the egressing packet. | step1: On interface set cos value for ingress untagge
  - AWP-9108    0.583 [QoS                   ] QoS on switchport interface - class set cos             :: Verify that classified traffic class set CoS as defined. | step1: Create a policy with a class. Set cos values via service-policy 
  - AWP-9075    0.582 [QoS                   ] QoS:static LAG interface default cos                    :: Verify frames should have COS tag set by mls qos cos configuration on ingress LAG interface | step1: On static LAG interface set c
  - AWP-9077    0.556 [QoS                   ] QoS default CoS with Dynamic LAG                        :: Objective: To verify if egress frames have the default CoS after passing through a LAG interface Expected Outcome: Egress frames s
  - AWP-9068    0.554 [QoS                   ] QoS cos-queue map configuration                         :: Verify QoS cos-queue map configurations has taken effect after reboot and failovers | step1: Configure a selection of cos-queue ma
  - AWP-9087    0.534 [QoS                   ] QoS: CoS Specify CoS                                    :: Verify that matching and non matching traffic with specific to COS should conform to the configured class-map and default maps. | 
  - AWP-9112    0.532 [QoS                   ] QoS on static LAG interface - default class set cos     :: Verify that traffic default bandwidth class set CoS passing through static LAG were defined. Note: This test case is only applicab

### AWPTCM-T44268  |  area: QoS PolicyBase  |  feature: RED Curves
folder:/New Platform Template/QoS  steps:1  obj:False
  - AWP-23308   0.264 [QoS                   ] WRR: Configure and apply RED curve template             :: RED curve templates can be applied to any number of traffic classes. RED-curves can be applied to a WRR class/subclass/subsubclass
  - AWP-23307   0.264 [QoS                   ] HTB: Configure and apply RED curve template             :: RED curve templates can be applied to any number of traffic classes. RED-curves can be applied to an HTB class/subclass/subsubclas
  - AWP-23306   0.262 [QoS                   ] PQ: Configure and apply RED curve template              :: RED curve templates can be applied to any number of traffic classes. RED-curves can be applied to a Priority Queue class/subclass/
  - AWP-9123    0.202 [QoS                   ] QoS: static LAG based policing - single-rate - action d :: Verify the amount and timing of the egress traffic rate which conforms to the single-rate policer configuration applied in a Stati
  - AWP-23305   0.196 [QoS                   ] Show RED-curve command                                  :: Show command for Red-curve: awplus# show traffic-control red-curve Show traffic-control policy will be updated to show which RED c
  - AWP-23660   0.193 [VRF-Lite              ] Check 'ip vrf <vrf-name>; max-static-routes' can limit  :: ip vrf red max-static-routes 5 ip vrf green int eth1 ip vrf forwarding red ip address 1.1.1.1/24 interface eth2 ip vrf forwarding 
  - AWP-9120    0.188 [QoS                   ] QoS: aggregate policers on ports - action drop-red      :: Verify the amount and timing of the egress traffic rate which conforms to the single-rate policer configuration this time via aggr
  - AWP-23310   0.187 [QoS                   ] Changes to RED curve template applied automatically     :: Changing a configured RED curve template will update all traffic-classes using that template to the new configuration. | step1: Cr

### AWPTCM-T44269  |  area: QoS  |  feature: Policy-based routing
folder:/New Platform Template/QoS  steps:1  obj:False
  - AWP-15937   0.585 [IPv4                  ] Policy-based Routing in "no ip forwarding"              :: Confirm whether Policy-based Routing work when "no ip forwarding" in configured. | step1: Ping to 10.0.0.100 from PC1. => Confirm 
  - AWP-4967    0.526 [Limits                ] SW policy routing                                       :: Deactivated | step1: ﻿Deactivated => Move to QoS
  - AWP-13380   0.436 [QoS                   ] Policy-based QoS and ACL test                           :: (Broadcom chip product) Policy-based QoS and ACL work correctly each other on same port. The order of processing is ACL -> Policy-
  - AWP-4739    0.400 [Policy Based Routing  ] Policy-based routing with Virtual MAC                   :: Configure a stack to use vmac, and to policy-route packets arriving destined to that MAC. | step1: 1. Start with the attached conf
  - AWP-7626    0.372 [Policy Based Routing  ] Clear the ARP table with Policy Based Routing           :: With a Policy Clear ARP table and confirm classified traffic should arp for the PBR next hop and add entry in the HW table NB: Fie
  - AWP-5036    0.354 [Limits                ] QoS - Number of Policy Entries per Unit                 :: Verify policy entry limit | step1: - Create one class map for each policy map - Applying one policy map for each interface => - Co
  - AWP-20971   0.329 [QoS                   ] DPMAP: Dynamic change of attached policy-map            :: Change the policy-map attached to interface without detachment. this function will be supported in 5.4.7 for BCM/IE200/Marvell Pro
  - AWP-21605   0.322 [Policy Based Routing  ] PBR for Routers: IPv6 routing based on source address   :: Test that packets are routed to correct path/nexthop when ipv6 source address is matched | step1: Set up DUT similar to the precon

### AWPTCM-T44270  |  area: Authentication Security IEEE 802.1XEncryptionType  |  feature: EAP-PEAP
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-5397    0.564 [RADIUS                ] Local Radius behavior of EAP-PEAP authentication Dot1x  :: Confirm that a client can be authenticated with EAP-PEAP(PEAP-TLS, MSCHAP v2), and this client should be moved to the group’s vlan
  - AWP-5404    0.484 [RADIUS                ] Local Radius dot1x(EAP-PEAP), WEB(EAP-MD5), MAC(EAP-MD5 :: Confirm that a client can be authenticated with dot1X(EAP-PEAP) and WEB(EAP-MD5), MAC(EAP-MD5), and this client should be moved to
  - AWP-6786    0.408 [Port Authentication   ] Authentication message exchange                         :: Confirm that an authenticator exchanges authentication messages between the supplicant and Radius server. | step1: 1. Configure DU
  - AWP-6787    0.365 [Port Authentication   ] Packet Format on Authenticator port                     :: Confirm the Packet format that the protocol used for port-based access control is the IETF standard Extensible Authentication Prot
  - AWP-6778    0.283 [Port Authentication   ] EAP Forwarding Tests                                    :: [Note] On 5.4.5-0.x, try this test on interface mode or auth-config mode. Verify switch action when EAP forwarding is enabled or d
  - AWP-142     0.279 [Customer Scenario     ] EAP support                                             :: Confirm that dot1authentications is possible. (all kinds of eap supported on AW+) | step1: Do dot1 authentication on each eap type
  - AWP-5469    0.278 [RADIUS                ] AW+ Radius Server PEAP Testing                          :: Please see attached file "3.1.x_CR28184-Test-procedures.doc" for Network Setup and configurations The AW+ RADIUS server has now be
  - AWP-5435    0.237 [RADIUS                ] Local Radius & VCS / Web Auth / EAP-MD5                 :: Behavior of EAP-MD5 Authentication: Confirm that a client can be authenticated through Web Authentication using EAP-MD5 Challenge 
