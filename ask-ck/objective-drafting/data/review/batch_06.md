# Rerank batch 06  (cases 180..209)

### AWPTCM-T43861  |  area: IPv4 UnicastRouting  |  feature: ECMP Routing
folder:/New Platform Template/IPv4  steps:7  obj:True
ZEPHYR: OBJ: ECMP route Adding and Removing. || Add max ECMP Groups. | Remove some route. | Add route again.
  - AWP-19503   0.941 [L3 Switching          ] ECMP - Route Adding and Removing                        :: ECMP route Adding and Removing. | step1: Add max ECMP Groups. => correctly be added. - "show platform table ip" - "show platform t
  - AWP-25826   0.451 [IPv4                  ] ECMP routing with interface name will be supported for  :: | step1: device with multiple ppp link and set static routing to a specific subnet egressing from multiple ppp interface names an 
  - AWP-19500   0.435 [L3 Switching          ] ECMP - L3 Egress Mode Max ECMP Groups                   :: Confirm Maximum ECMP Groups. Same Next Hop Route be into same ECMP Group. | step1: Register max ECMP groups. Max next hop register
  - AWP-19501   0.435 [L3 Switching          ] ECMP - L3 Egress Mode One ECMP Group that will be fille :: Confirm one ECMP Group (Next hop A,B) that will be filled by max route. | step1: Register one ECMP Group with max route. Both IPv4
  - AWP-25827   0.390 [IPv4                  ] ECMP routing with interface name will be supported for  :: | step1: device with multiple ppp link and default static routing egressing from multiple ppp interface names and feed multi-sour 
  - AWP-13667   0.385 [IPv4                  ] ECMP Default Maximum-Path Value                         :: Objective: To determine the default maximum-path value on ECMP Expected Outcome: Default maximum-path value on ECMP should be set 
  - AWP-7384    0.350 [IPv6 Static Routes and] ECMP Test                                               :: ECMP IPv6 should work correctly. Check port counters, to ensure that multiple paths are used. Check show commands to display mutlp
  - AWP-25830   0.348 [IPv4                  ] ECMP routing with interface name will co-exist with rou :: | step1: set ECMP route egress from ppp and normal nethop ip address with same distance => expect traffic should egress from all i

### AWPTCM-T43862  |  area: IPv4 UnicastRouting  |  feature: Secondary IP Address
folder:/New Platform Template/IPv4  steps:1  obj:False
  - AWP-8266    0.668 [IPv4                  ] IP Address Secondary                                    :: Secondary IP address assignment should work properly | step1: Add this command to config t to a vlan interface ip address A.B.C.D/
  - AWP-8286    0.578 [IPv4                  ] Secondary IP Address Assignment Limit                   :: Check the limit of secondary ip address assignment | step1: Secondary IP addresses work, Check Max value of => Device supports 32 
  - AWP-8292    0.577 [IPv4                  ] Secondary IP in other interface                         :: Secondary ip should work in other interface | step1: Testing of Secondary IP addresses is being done in other places. i.e PIM etc 
  - AWP-8267    0.561 [IPv4                  ] IP Address Secondary with Label                         :: Label should also work for secondary address | step1: Add this command to config t to a vlan interface ip address A.B.C.D/M second
  - AWP-3805    0.543 [VRRP                  ] Interop with secondary IP interfaces                    :: To verify interoperability of VRRP with secondary IP interfaces | step1: Configure secondary IP on interface e.g. awplus(config-if
  - AWP-7639    0.507 [Policy Based Routing  ] PBR on a secondary next hop IP address                  :: Confirm that PBR should work for a secondary next hop IP address | step1: PBR should work well for a secondary next hop IP address
  - AWP-21199   0.500 [ACL                   ] Management ACLs will not block secondary IP address     :: secondary IP will not be blocked | step1: assigned certain vlan with both primary and secondary address,creat acl only block prima
  - AWP-3833    0.498 [IPv4                  ] Limits-Max Secondary                                    :: Limits-Max Secondary The maximum configurable secondary ip address for local interface should be 32. | step1: 1. Configure maximum

### AWPTCM-T43863  |  area: IPv4 MulticastRouting  |  feature: PIM-SM
folder:/New Platform Template/IPv4  steps:1  obj:False
  - AWP-10274   0.649 [Process Monitoring    ] Memory Monitoring - PIM-SM                              :: Correct output information for PIM-SM | step1: Execute the command "show memory allocations" and capture output => Check memory in
  - AWP-7186    0.473 [IGMP                  ] VCS+Query Solicitation - PIM-SM                         :: check qs works in a timely mannor across a vcs stack with pim + large number of groups SM | step1: check qs works in a timely mann
  - AWP-3468    0.453 [PIM-SM                ] CLI to check sh ip pim nexthop                          :: Command Line test | step1: 1. Setup PIM-DM / SM network 2. Execute the command to display nexthop information - show ip pim dense-
  - AWP-7735    0.445 [Validation Scenario   ] PIM-SM - Restarting Processes                           :: Check and verify PIM-SM for correct status and functionality. | step1: Restart processes/protocols (daemon). 3 ways to restart pro
  - AWP-13501   0.445 [Validation Scenario   ] PIM-SM - Restarting Processes                           :: Check and verify PIM-SM for correct status and functionality. | step1: Restart processes/protocols (daemon). 3 ways to restart pro
  - AWP-7731    0.444 [Validation Scenario   ] PIM-SM - Disconnect / Reconnect Links                   :: Check and verify PIM-SM for correct status and functionality. | step1: Disconnect then reconnect links and check for network recov
  - AWP-13497   0.444 [Validation Scenario   ] PIM-SM - Disconnect / Reconnect Links                   :: Check and verify PIM-SM for correct status and functionality. | step1: Disconnect then reconnect links and check for network recov
  - AWP-7733    0.439 [Validation Scenario   ] PIM-SM - Add / Delete Configurations                    :: Check and verify PIM-SM for correct status and functionality. | step1: Update related configurations by adding, removing or changi

### AWPTCM-T43864  |  area: IPv4 MulticastRouting  |  feature: PIM-DM
folder:/New Platform Template/IPv4  steps:1  obj:True
ZEPHYR: OBJ: PIM-DM works as expected DUT can route multicast traffic using PIM-DM || Setup a PIM-DM network
  - AWP-17873   0.858 [PIM-DM                ] PIM-DM End-to-end test                                  :: PIM-DM works as expected | step1: Setup a PIM-DM => Multicast client able to get multicast stream
  - AWP-10273   0.598 [Process Monitoring    ] Memory Monitoring - PIM-DM                              :: Correct output information for PIM-DM | step1: Execute the command "show memory allocations" and capture output => Check memory in
  - AWP-7726    0.519 [Validation Scenario   ] PIM-DM - Multicast Traffic                              :: Check and verify PIM-DM for correct status and functionality. | step1: Run multicast streams across network. e.g. 1 source multipl
  - AWP-3466    0.502 [PIM-SM                ] CLI to check sh ip pim mroute                           :: Command line test | step1: 1. Setup PIM-DM / SM network. 2. Server sends multicast traffic 3. Client joins the multicast group 4. 
  - AWP-7185    0.484 [IGMP                  ] VCS+Query Solicitation - PIM-DM                         :: check qs works in a timely mannor across a vcs stack with pim + large number of groups DM | step1: check qs works in a timely mann
  - AWP-3468    0.440 [PIM-SM                ] CLI to check sh ip pim nexthop                          :: Command Line test | step1: 1. Setup PIM-DM / SM network 2. Execute the command to display nexthop information - show ip pim dense-
  - AWP-7723    0.426 [Validation Scenario   ] PIM-DM - Disconnect / Reconnect Links                   :: Check and verify PIM-DM for correct status and functionality. | step1: Disconnect then reconnect links and check for network recov
  - AWP-7727    0.415 [Validation Scenario   ] PIM-DM - Restarting Processes                           :: Check and verify PIM-DM for correct status and functionality. | step1: Restart processes/protocols (daemon). 3 ways to restart pro

### AWPTCM-T43865  |  area: IPv4 MulticastRouting  |  feature: PIM-SSM
folder:/New Platform Template/IPv4  steps:3  obj:True
ZEPHYR: OBJ: PIM-SMM is entered entries dynamically || Multicast traffic is forwarded and status on multicast table | Multicast traffic was stopped and prune correctly when group | The state when port interfa
  - AWP-11233   0.979 [PIM-SSM               ] PIM-SSM functionality                                   :: PIM-SMM is entered entries dynamically | step1: Multicast traffic is forwarded and status on multicast table is correct when group
  - AWP-11230   0.520 [PIM-SSM               ] PIM-SSM with static mroute                              :: Verify PIM-SSM works properly with static mroute | step1: Configure the static mroute at the last hope router (DUT4). >Send multic
  - AWP-3466    0.440 [PIM-SM                ] CLI to check sh ip pim mroute                           :: Command line test | step1: 1. Setup PIM-DM / SM network. 2. Server sends multicast traffic 3. Client joins the multicast group 4. 
  - AWP-10313   0.423 [PIM-SSM               ] PIM-SSM with Static IGMP entries                        :: Static IGMPv3 entries | step1: Configure PIM-SSM with static igmp group: - ip igmp static-group <multicast group address> Check gr
  - AWP-11232   0.405 [PIM-SSM               ] CLI Test - PIM-SSM - ip igmp static-group               :: Command Line Test This CLI test specific to PIM-SSM. | step1: Issue the command: ip igmp static-group <ip-address> [source {<ip-so
  - AWP-10322   0.389 [PIM-SSM               ] PIM-SSM and LAG                                         :: Verify the behaviour of PIM-SSM with LAG | step1: Configure PIM-SSM with LAG => Multicast packet joined the correct source
  - AWP-3503    0.377 [PIM-SSM               ] PIM-SSM with multiple Source and Groups                 :: Tests IGMPv3 and Source Specifc multicast, hosts join the correct stream | step1: Use IGMP v3 and PIM source specific multicast. S
  - AWP-10300   0.358 [PIM-SSM               ] PIM-SSM using user defined range                        :: Verify that SSM works as expected using user defined multicast address ranges | step1: Connect a IGMPv3 capable host (vlc) or use 

### AWPTCM-T43866  |  area: IPv4 MulticastRouting  |  feature: VRF-Lite
folder:/New Platform Template/IPv4  steps:1  obj:False
  - AWP-10990   0.555 [VRF-Lite              ] VRF_Lite and Stack Management Vlan                      :: To operate VRF lite on a stack and confirm that there is no defect in the way VRF-Lite handles the stack management Vlan | step1: 
  - AWP-11451   0.546 [Validation Scenario   ] VRF-Lite - Unicast Traffic                              :: Check and verify VRF-Lite for correct status and functionality. | step1: Run background unicast traffic in the relevant scenario. 
  - AWP-4286    0.544 [VRF-Lite              ] VRF Lite Traceroute                                     :: VRF-Lite support traceroute operation | step1: From a VRF instance Run the command traceroute vrf <name> x.x.x.x From the global V
  - AWP-27318   0.484 [VRF-Lite              ] Check VRF-Lite works with NLB                           :: This comes from an external issue. See CR-58442. | step1: Ensure 10.200.5.100 can ping 128.1.0.17
  - AWP-4282    0.479 [VRF-Lite              ] Feature requires licence called VRF-Lite                :: VRF Feature Requires licence to be enabled before being able to be configured, the licence is called VRF-LIte | step1: sh lic => o
  - AWP-14294   0.450 [VRF-Lite              ] DHCP Relay VRF aware - VRF Instance Running DHCP-Relay  :: VRF-Lite running DHCP-Relay should work on common instance. | step1: enable dhcp-relay services #service dhcp-relay configure VRF-
  - AWP-10992   0.445 [VRF-Lite              ] VRF Lite route to resiliency Vlan                       :: To check that it is not possible to create a route (static or dynamic) to the resiliency link vlan | step1: create a static route 
  - AWP-10993   0.444 [VRF-Lite              ] VRF-Lite Route limiting max static routes.              :: To test the commands surrounding route Limits per VRF | step1: Test the command awplus(config-vrf)# max-static-routes <1-1000> It 

### AWPTCM-T43867  |  area: IPv4 MulticastRouting  |  feature: MSDP
folder:/New Platform Template/IPv4  steps:1  obj:True
ZEPHYR: OBJ: keep-alives source-active received (S,G) entries unknown ||
  - AWP-15387   0.289 [Web Authentication    ] Session Keep                                            :: Session Keep | step1: Session Keep => Session Keep
  - AWP-12861   0.260 [GRE                   ] GRE:Configurable tunnel source using IPv4 address       :: GRE tunnels require an IPv4 source address to be active. Tunel source addresses are configured using the "tunnel source <ipv4-addr
  - AWP-19543   0.242 [L2TPv3 Ethernet Pseudo] L2TPv3: Configurable tunnel source using IPv4 address   :: L2TPv3 tunnels require an IPv4 source address to be active (among other parameters). Tunel source addresses are configured using t
  - AWP-22597   0.225 [Logging               ] Log host source with both IPv4 and IPv6 address         :: | step1: Set IPv4 syslog server and IPv6 syslog server both,then add loopback interface which was set IPv4 address and IPv6 addre 
  - AWP-12967   0.212 [z_Inactive            ] IPv6 Tunnels: Configurable tunnel source using IPv6 add :: IPv6 tunnels require an IPv6 source address to be active. Tunnel source addresses are configured using the "tunnel source <ipv6-ad
  - AWP-13694   0.211 [IPsec IPv6 tunnels    ] IPsec IPv6: Configurable tunnel source using IPv6 addre :: IPsec IPv6 tunnels require an IPv6 source address to be active. Tunnel source addresses are configured using the "tunnel source <i
  - AWP-24173   0.206 [ATMF                  ] Check Ping (IPv4 and IPv6) will be supported            :: Check Ping (IPv4 and IPv6) will be supported | step1: Check Ping (IPv4 and IPv6) will be supported => confirm Ping (IPv4 and IPv6)
  - AWP-24184   0.199 [ATMF                  ] Check IPv4 static routes will be supported              :: Check IPv4 static routes will be supported | step1: Check IPv4 static routes will be supported => confirm IPv4 static routes are s

### AWPTCM-T43868  |  area: IPv4 SNMP  |  feature: SNMP v1
folder:/New Platform Template/IPv4  steps:1  obj:True
ZEPHYR: OBJ: Access DUT via SNMP Manager with a SNMPv1 specified access || Access DUT via SNMP Manager with a SNMPv1 specified access.
  - AWP-1232    0.878 [SNMP                  ] SNMPv1-Access                                           :: Access DUT via SNMP Manager with a SNMPv1 specified access | step1: Access DUT via SNMP Manager with a SNMPv1 specified access. Co
  - AWP-1233    0.747 [SNMP                  ] SNMPv1-Access-VCS                                       :: Access DUT via SNMP Manager with a SNMPv1 specified access, where DUT is a VCS stack. Set up DUT as VCS stack (max supported for m
  - AWP-1234    0.732 [SNMP                  ] SNMPv2c-Access                                          :: Access DUT via SNMP Manager with a SNMPv2c specified access | step1: Access DUT via SNMP Manager with a SNMPv2c specified access. 
  - AWP-1237    0.628 [SNMP                  ] SNMPv3-Access-Authentication only                       :: SNMPv3 Access Test With authentication but with no privacy. | step1: Access DUT via SNMP Manager with a SNMPv3 specified access. W
  - AWP-1235    0.626 [SNMP                  ] SNMPv2c-Access-VCS                                      :: Access DUT via SNMP Manager with a SNMPv2c specified access, where DUT is a VCS stack. Set up DUT as VCS stack (max supported for 
  - AWP-1238    0.607 [SNMP                  ] SNMPv3-Access-Authentication and Privacy                :: SNMPv3 Access Test With authentication and privacy | step1: Access DUT via SNMP Manager with a SNMPv3 specified access. With authe
  - AWP-1236    0.596 [SNMP                  ] SNMPv3-Access-No Authentication or Privacy              :: SNMPv3 Access Test With no authentication and no privacy | step1: Access DUT via SNMP Manager with a SNMPv3 specified access. With
  - AWP-1240    0.552 [SNMP                  ] VCS-SNMPv3-Access-Authentication only                   :: SNMPv3 Access Test With authentication but with no privacy, where DUT is a VCS stack. Set up DUT as VCS stack (max supported for m

### AWPTCM-T43869  |  area: IPv4 SNMP  |  feature: SNMPv2c
folder:/New Platform Template/IPv4  steps:1  obj:True
ZEPHYR: OBJ: Access DUT via SNMP Manager with a SNMPv2c specified access || Access DUT via SNMP Manager with a SNMPv2c specified access.
  - AWP-1234    0.977 [SNMP                  ] SNMPv2c-Access                                          :: Access DUT via SNMP Manager with a SNMPv2c specified access | step1: Access DUT via SNMP Manager with a SNMPv2c specified access. 
  - AWP-1235    0.836 [SNMP                  ] SNMPv2c-Access-VCS                                      :: Access DUT via SNMP Manager with a SNMPv2c specified access, where DUT is a VCS stack. Set up DUT as VCS stack (max supported for 
  - AWP-1232    0.762 [SNMP                  ] SNMPv1-Access                                           :: Access DUT via SNMP Manager with a SNMPv1 specified access | step1: Access DUT via SNMP Manager with a SNMPv1 specified access. Co
  - AWP-1233    0.649 [SNMP                  ] SNMPv1-Access-VCS                                       :: Access DUT via SNMP Manager with a SNMPv1 specified access, where DUT is a VCS stack. Set up DUT as VCS stack (max supported for m
  - AWP-1237    0.642 [SNMP                  ] SNMPv3-Access-Authentication only                       :: SNMPv3 Access Test With authentication but with no privacy. | step1: Access DUT via SNMP Manager with a SNMPv3 specified access. W
  - AWP-1238    0.621 [SNMP                  ] SNMPv3-Access-Authentication and Privacy                :: SNMPv3 Access Test With authentication and privacy | step1: Access DUT via SNMP Manager with a SNMPv3 specified access. With authe
  - AWP-1236    0.609 [SNMP                  ] SNMPv3-Access-No Authentication or Privacy              :: SNMPv3 Access Test With no authentication and no privacy | step1: Access DUT via SNMP Manager with a SNMPv3 specified access. With
  - AWP-1240    0.565 [SNMP                  ] VCS-SNMPv3-Access-Authentication only                   :: SNMPv3 Access Test With authentication but with no privacy, where DUT is a VCS stack. Set up DUT as VCS stack (max supported for m

### AWPTCM-T43870  |  area: IPv4 SNMP  |  feature: SNMPv3
folder:/New Platform Template/IPv4  steps:0  obj:True
ZEPHYR: OBJ: SNMPv3でsnmp-server view設定のフィルタリング動作を確認する。 ||
  - AWP-8772    0.373 [sFlow                 ] sFlow MIB - SNMPv3                                      :: Confirm can browse sFlow MIB from MIB browser using snmpv3 account | step1: snmpv3/snmpv2 => Ensure able to browse MIB from MIB br
  - AWP-1237    0.366 [SNMP                  ] SNMPv3-Access-Authentication only                       :: SNMPv3 Access Test With authentication but with no privacy. | step1: Access DUT via SNMP Manager with a SNMPv3 specified access. W
  - AWP-1238    0.354 [SNMP                  ] SNMPv3-Access-Authentication and Privacy                :: SNMPv3 Access Test With authentication and privacy | step1: Access DUT via SNMP Manager with a SNMPv3 specified access. With authe
  - AWP-1236    0.348 [SNMP                  ] SNMPv3-Access-No Authentication or Privacy              :: SNMPv3 Access Test With no authentication and no privacy | step1: Access DUT via SNMP Manager with a SNMPv3 specified access. With
  - AWP-1240    0.319 [SNMP                  ] VCS-SNMPv3-Access-Authentication only                   :: SNMPv3 Access Test With authentication but with no privacy, where DUT is a VCS stack. Set up DUT as VCS stack (max supported for m
  - AWP-6675    0.313 [VLAN                  ] Configure SNMPv3 with a view policy to allow standard u :: Standard user can connect to the device via SNMPv3 and access all mib object except AT-VLAN-MIB subtree | step1: Create account fo
  - AWP-1241    0.311 [SNMP                  ] VCS-SNMPv3-Access-Authentication and privacy            :: SNMPv3 Access Test With authentication and privacy, where DUT is a VCS stack. Set up DUT as VCS stack (max supported for model typ
  - AWP-1239    0.307 [SNMP                  ] VCS-SNMPv3-Access-No Authentication or Privacy          :: SNMPv3 Access Test With no authentication and no privacy, where DUT is a VCS stack. Set up DUT as VCS stack (max supported for mod

### AWPTCM-T44181  |  area: IPv4  |  feature: Ping Polling
folder:/New Platform Template/IPv4  steps:11  obj:True
ZEPHYR: OBJ: Run ART 1341_limits - 1341.1001.4991 - MAX supported ping polls Ping poll configuration - test show commands debug || Run ART 1341_limits - 1341.1001.4991 - MAX supported ping po | To configure y
  - AWP-623     0.408 [Triggers              ] Ping Poll Trigger on target reachable                   :: Test for ping poll triggers | step1: Configure a trigger to run scripts (both .sh and .scp) when a Ping Poll instance detects that
  - AWP-10218   0.388 [Diagnostic Application] Ping-Poll activation                                    :: Correct Output for Ping-Poll | step1: Replace cable to DUT See ping-poll up by 'sh ping-poll' and see trigger message => Confirm p
  - AWP-4991    0.374 [Limits                ] Number of ping polls                                    :: To verify max ping polls can be configured | step1: - Create up to 101 ping polls => - Confirm that there is 100 configured ping p
  - AWP-10216   0.359 [Diagnostic Application] Stop ping poll                                          :: Ping poll should stop | step1: Observe ping-poll packets flowing. Deactivate ping-poll and observe ping-poll packets stopped 'conf
  - AWP-622     0.356 [Triggers              ] Ping Poll Trigger on target unreachable                 :: Test for ping poll triggers Test granularity - response should be within about 2 seconds (ref CR36045) | step1: Configure a trigge
  - AWP-10217   0.354 [Diagnostic Application] Ping-Poll Details                                       :: Correct Output Display | step1: Active ping-poll Show ping-poll is up and then remove cable(break link) See trigger down message. 
  - AWP-10213   0.348 [Diagnostic Application] Ping Poll - Correct Values Display                      :: Should display the correct value | step1: On DUT create new config with ping poll and trigger Execute 'sh trigger' and 'sh ping po
  - AWP-10220   0.318 [Diagnostic Application] Default Ping-poll command                               :: Test Default ping-poll options | step1: Confirm ping-poll options can be changed to default using 'no' command. => Confirm valid r

### AWPTCM-T44182  |  area: IPv4  |  feature: Directed Broadcast Forwarding
folder:/New Platform Template/IPv4  steps:1  obj:False
  - AWP-9897    0.637 [DHCP Snooping         ] DHCP Snooping and directed broadcast                    :: Confirm security should still apply | step1: DHCP Snooping and directed broadcast => Security should still apply
  - AWP-5251    0.633 [Directed Broadcast    ] ip directed-broadcast / no ip directed-broadcast (? hel :: Tab complete working & ? help is accurate and useful | step1: ip directed-broadcast (help) - enter the vlan1 interface (int vlan1)
  - AWP-5255    0.590 [Directed Broadcast    ] IP Broadcast test(Directed Broadcast is enable)         :: the directed broadcast is forwarded. To confirm that the DUT can send IP broadcast packets when the Direct parameter for VLANs are
  - AWP-5258    0.542 [Directed Broadcast    ] IP directed-broadcast with all FF MAC address           :: When destination MAC address is all FF (FFFF.FFFF.FFFF), the directed broadcast packet is forwarded as same as directed broadcast 
  - AWP-5250    0.540 [Directed Broadcast    ] ip directed-broadcast / no ip directed-broadcast        :: All commands should work correctly. | step1: ip directed-broadcast - Configure 2 vlans (vlan1,vlan2) with routes on each other - c
  - AWP-5254    0.496 [Directed Broadcast    ] IP Broadcast test(Directed Broadcast is disable)        :: the directed broadcast (DA is subnet broadcast IP address) is not be forwarded. To confirm that the DUT does not send IP broadcast
  - AWP-5257    0.479 [Directed Broadcast    ] IP directed-broadcast to remote routing                 :: “ip directed-broadcast” command is nothing to do with off-link directed-broadcast packets. These packets should be routed and forw
  - AWP-5252    0.394 [Directed Broadcast    ] Show Command Output                                     :: configure is output correctly 1) show run | step1: configure ip directed-broadcast on vlan 1 issue show running-config => configur

### AWPTCM-T44184  |  area: IPv6  |  feature: Management Interface
folder:/New Platform Template/IPv6  steps:1  obj:True
ZEPHYR: OBJ: Able to configure IPv6 address on eth0 and IPv6 show command contain eth0 e.g. SBx908, SBx8100 .... || IPv6 on eth0 is functional - ping testbox
  - AWP-10090   0.926 [IPv6                  ] IPv6 on eth0 management interface (switches)            :: Able to configure IPv6 address on eth0 and IPv6 show command contain eth0 e.g. SBx908, SBx8100 .... | step1: IPv6 on eth0 is funct
  - AWP-10091   0.683 [IPv6                  ] IPv6 on eth0 show commands                              :: eth0 was shown in show command | step1: IPv6 on eth0 - show commands => Show command should contain eth0
  - AWP-10092   0.308 [IPv6                  ] IPv6 eth0 should not behave like a routed interface por :: Check that eth0 does not behave like a routed interface port (it does not send Router Advertisments) | step1: Enable RA on eth0. U
  - AWP-22591   0.306 [Logging               ] CLI: log host source                                    :: VLAN interface and loopback interface and eth0 interface can be choose as source address,interface name or IP address can be allow
  - AWP-22661   0.305 [ACL                   ] Management ACL will work on eth0                        :: Management ACL will block a incoming packet from eth interface. | step1: Added IP addres to eth interface,and create block eth int
  - AWP-24166   0.304 [ATMF                  ] Check The eth0 interface will be automatically configur :: Check The eth0 interface will be automatically configured as an AMF area-link | step1: check eth0 interface will be automatically 
  - AWP-11415   0.285 [VLAN                  ] Ensure packets cannot be routed via eth0                :: Eth0 should be out of band | step1: Setup two subnets one on a VLAN and one on the CFC. Try and route packets between eth0 and the
  - AWP-22596   0.282 [Logging               ] Log host source with IPv6 address                       :: | step1: Added IPv6 Address to loopback interface,and set lo interface as log host source. => The switch should use IPv6 Address a

### AWPTCM-T44185  |  area: IPv6  |  feature: Telnet Server
folder:/New Platform Template/IPv6  steps:4  obj:True
ZEPHYR: OBJ: Confirm that a Host can connect to the Router by Telnet. || Telnet connection from Host-A to 192.168.1.1. | Show log | Telnet connection from Host-A to 192.168.100.1.
  - AWP-18438   0.979 [Interop               ] Telnet Server                                           :: Confirm that a Host can connect to the Router by Telnet. | step1: Telnet connection from Host-A to 192.168.1.1. => Successfull.
  - AWP-24521   0.462 [ATMF                  ] Check the support of telnet server                      :: Telnet server (IPv4 and IPv6) will be supported | step1: check telnet server will be supported => Confirm telnet server will be su
  - AWP-2308    0.455 [Telnet                ] Telnet - show telnet                                    :: Executing 'show telnet' in the CLI shows the correct Telnet port. | step1: Execute 'show telnet' => check if the telnet server is 
  - AWP-2309    0.450 [Telnet                ] Telnet - show running                                   :: Show details of telnet in the running config | step1: show running => telnet configuration should be displayed correctly
  - AWP-24523   0.396 [ATMF                  ] Telnet server will be disabled by default               :: Telnet server will be disabled by default | step1: check telnet server is disabled by default => confirm telnet server is disabled
  - AWP-5816    0.367 [IPv6 Management       ] Telnet: SW-1 to DUT-2 - Disable telnet server           :: Test for Telnet command from SW-1 to DUT-2 (Disable Telnet server DUT-2) | step1: Configure 4 devices with ipv6 address Disable te
  - AWP-24520   0.351 [ATMF                  ] Check the support of telnet client                      :: Telnet client (IPv4 and IPv6) will be supported | step1: check telnet client will be supported => Confirm telnet client will be su
  - AWP-2338    0.349 [Telnet                ] Telnet - IPv6 - incoming to vcs default operation       :: test telnet with ipv6 | step1: Telnet from remote device to VCS-DUT using IPv6 address => Telnet succeeds.

### AWPTCM-T44186  |  area: IPv6  |  feature: Telnet Client
folder:/New Platform Template/IPv6  steps:0  obj:True
ZEPHYR: OBJ: Confirm that Telnet connection establish from DUT. ||
  - AWP-24520   0.700 [ATMF                  ] Check the support of telnet client                      :: Telnet client (IPv4 and IPv6) will be supported | step1: check telnet client will be supported => Confirm telnet client will be su
  - AWP-2308    0.520 [Telnet                ] Telnet - show telnet                                    :: Executing 'show telnet' in the CLI shows the correct Telnet port. | step1: Execute 'show telnet' => check if the telnet server is 
  - AWP-2309    0.500 [Telnet                ] Telnet - show running                                   :: Show details of telnet in the running config | step1: show running => telnet configuration should be displayed correctly
  - AWP-5814    0.496 [IPv6 Management       ] Telnet: DUT-2 to DUT-1 (VLAN1)                          :: Test for Telnet command from DUT-2 to DUT-1 (VLAN1) | step1: Configure 4 devices with ipv6 address Perform telnet from DUT-2 to DU
  - AWP-24521   0.496 [ATMF                  ] Check the support of telnet server                      :: Telnet server (IPv4 and IPv6) will be supported | step1: check telnet server will be supported => Confirm telnet server will be su
  - AWP-5813    0.462 [IPv6 Management       ] Telnet: DUT-2 to DUT-1 (VLAN2)                          :: Test for Telnet command from DUT-2 to DUT-1 (VLAN2) | step1: Configure 4 devices with ipv6 address Perform telnet from DUT-2 to DU
  - AWP-2338    0.462 [Telnet                ] Telnet - IPv6 - incoming to vcs default operation       :: test telnet with ipv6 | step1: Telnet from remote device to VCS-DUT using IPv6 address => Telnet succeeds.
  - AWP-9212    0.453 [VLAN                  ] Private VLAN with Telnet                                :: Private VLAN with Telnet | step1: 1. Private VLAN with Telnet - Telnet from PC-1 to DUT. - Telnet from PC-2 to DUT. => Results sho

### AWPTCM-T44187  |  area: IPv6  |  feature: SSH Server
folder:/New Platform Template/IPv6  steps:0  obj:True
ZEPHYR: OBJ: Confirm that SSH connection establish with DUT. ||
  - AWP-5821    0.731 [IPv6 Management       ] SSH: SSH Client to SSH Server                           :: Test for SSH command from DUT-2 (SSH Client) to DUT-1 (SSH Server) | step1: Configure 4 devices with ipv6 address Configure SSH se
  - AWP-24175   0.647 [ATMF                  ] Check SSH server (IPv4 and IPv6) will be supported      :: Check SSH server (IPv4 and IPv6) will be supported | step1: Check SSH server (IPv4 and IPv6) will be supported => Confirm SSH serv
  - AWP-6511    0.594 [SSH                   ] check SSH server via IPv6                               :: SSH Server Tests Verify that SSH session works unsing IPv6 address | step1: Connect to server(DUT) via IPv6: DUT(config-if)#ipv6 a
  - AWP-5824    0.591 [IPv6 Management       ] SSH: SW-1 to DUT-1 - Disable SSH server                 :: Test for SSH command from SW-1 to DUT-1 (Disable SSH server DUT-1) | step1: Configure 4 devices with ipv6 address Disable SSH serv
  - AWP-5825    0.538 [IPv6 Management       ] SSH: Max Session                                        :: Test for SSH Max Session per switch | step1: Configure 4 devices with ipv6 address Configure SSH server to DUT-1 Configure line vt
  - AWP-5817    0.521 [IPv6 Management       ] SSH: SW-2 to DUT-1 (VLAN1)                              :: Test for SSH command from SW-2 to DUT-1 (VLAN1) | step1: Configure 4 devices with ipv6 address Configure SSH server to DUT-1 Conne
  - AWP-5820    0.521 [IPv6 Management       ] SSH: SW-1 to DUT-1 (VLAN1)                              :: Test for SSH command from SW-1 to DUT-1 (VLAN1) | step1: Configure 4 devices with ipv6 address Configure SSH server to DUT-1 Conne
  - AWP-6485    0.505 [SSH                   ] enable/disable ssh server                               :: SSH Server Tests | step1: 1. On DUT, enable ssh server then make an ssh session from client to DUT DUT#conf t DUT(config)# service

### AWPTCM-T44188  |  area: IPv6  |  feature: SSH Client
folder:/New Platform Template/IPv6  steps:0  obj:True
ZEPHYR: OBJ: Confirm that SSH connection establish from DUT. ||
  - AWP-5821    0.737 [IPv6 Management       ] SSH: SSH Client to SSH Server                           :: Test for SSH command from DUT-2 (SSH Client) to DUT-1 (SSH Server) | step1: Configure 4 devices with ipv6 address Configure SSH se
  - AWP-24176   0.663 [ATMF                  ] Check SSH client (IPv4 and IPv6) will be supported      :: Check SSH client (IPv4 and IPv6) will be supported | step1: Check SSH client (IPv4 and IPv6) will be supported => Confirm SSH clie
  - AWP-6511    0.561 [SSH                   ] check SSH server via IPv6                               :: SSH Server Tests Verify that SSH session works unsing IPv6 address | step1: Connect to server(DUT) via IPv6: DUT(config-if)#ipv6 a
  - AWP-6524    0.530 [z_Inactive            ] Command Line Handler - show ssh client                  :: SSH Client Tests | step1: show ssh client gives appropriate information => Verify ssh client settings set are the configured setti
  - AWP-6485    0.518 [SSH                   ] enable/disable ssh server                               :: SSH Server Tests | step1: 1. On DUT, enable ssh server then make an ssh session from client to DUT DUT#conf t DUT(config)# service
  - AWP-6526    0.496 [z_Inactive            ] check that ssh client settings are not displayed in run :: SSH Client Tests | step1: ssh client settings for current session do not appear in running-config => Verify ssh settings does not 
  - AWP-24175   0.489 [ATMF                  ] Check SSH server (IPv4 and IPv6) will be supported      :: Check SSH server (IPv4 and IPv6) will be supported | step1: Check SSH server (IPv4 and IPv6) will be supported => Confirm SSH serv
  - AWP-6520    0.485 [SSH                   ] check that only specified client version is used for ou :: SSH Client Tests Verify specified version for client is used for connection | step1: ssh client version command - test that only s

### AWPTCM-T44189  |  area: IPv6  |  feature: IPv6 RA Guard
folder:/New Platform Template/IPv6  steps:4  obj:True
ZEPHYR: OBJ: Enable and disable Router Advertisment Guard on all or defined interfaces. This is the base case - no other configeratio || Configer RA Guard on port interfaces | Save configeration file | Remove
  - AWP-10872   0.952 [IPv6 RA Guard         ] RA Guard - Enable/Disable - single unit                 :: Enable and disable Router Advertisment Guard on all or defined interfaces. This is the base case - no other configeration applied:
  - AWP-10874   0.812 [IPv6 RA Guard         ] Enable/Disable RA-Guard on VCS Stack                    :: Enable and disable Router Advertisment Guard on all or defined switch ports on a Vitual Chassis Stack. This is the base case - no 
  - AWP-10996   0.633 [IPv6 RA Guard         ] Enable RA-Guard with maximum ACLs configered            :: Enable raguard on all or defined interfaces when the maximum ACL filters have been configered. The command should fail gracfully d
  - AWP-11001   0.573 [IPv6 RA Guard         ] Enable/Disable RA-Guard on Static Link Aggregators      :: Enable and disable Router Advertisment Guard on Static Link Aggregators RA Guard can be configered for an sa interface. To prevent
  - AWP-11199   0.514 [IPv6 RA Guard         ] Enable/Disable RA-Guard on Dynamic Link Aggregator port :: Enable and disable Router Advertisment Guard on Dynamic Link Aggregator (Etherchannel GrouP) ports RA Guard cannot be configured f
  - AWP-10875   0.371 [IPv6 RA Guard         ] RAGuard does not degrade EPSR                           :: Ports with Router Advertisment Guard (raguard) configered will not degrade or disable EPSR configeration | step1: Configer RA guar
  - AWP-10980   0.361 [IPv6 RA Guard         ] RA Guard cannot be bypassed with permit HW filters      :: Router Advertisment Guard (raguard) configeratations cannot be bypassed with permit all ipv6 filters. raguard has a higher precede
  - AWP-11198   0.358 [IPv6 RA Guard         ] RA-Guard can be provisioned                             :: RA-Guard can be provisioned on VCS stacks and XEMs Ports on missing members of x600/610/x900 and x908 stacks can be provisioned Po

### AWPTCM-T44190  |  area: IPv6  |  feature: ICMPv6
folder:/New Platform Template/IPv6  steps:1  obj:False
  - AWP-10101   0.601 [IPv6                  ] IPv6 Address - malformed packets ICMPv6                 :: Able to check malformed packets | step1: Malformed packets - ICMPV6 => Should be able to check malformed packets
  - AWP-11662   0.513 [VLAN                  ] CR00034145: ICMPv6 Packet                               :: ICMPv6 packets should not be sending when ipv6 interface is not enabled on the DUT (ipv6 forwarding or ipv6 enable) | step1: Check
  - AWP-10102   0.442 [IPv6                  ] Control Plane Prioritization of ICMPv6                  :: Able to configure control plane prioritization of ICMPv6 control frames | step1: Issue platform control-plane-prioritization rate 
  - AWP-12979   0.372 [z_Inactive            ] IPv6 Tunnels: Drop pkt and send ICMPv6 ParamProb if Enc :: When tunnel limit option is received and is equal to zero, packet should not be forwarded out another IPv6 tunnel. ICMPv6 Paramete
  - AWP-10979   0.358 [IPv6 RA Guard         ] RAGuard blocks RA and Redirect ingress on configered po :: Ports with Router Advertisment Guard (raguard) configered will deny all ICMPv6 packets with type 134 (RA) and 137 (Redirect) on in
  - AWP-12116   0.352 [VRRP                  ] ND Solicitation Request                                 :: DUT responds with VRRP MAC | step1: Setup a IPv6 VRRP instance on a single device => Device should respond with 00:00:5e:00:02:VRI
  - AWP-17838   0.332 [z_Inactive            ] IPv6 Tunnels: IPv4/6 over IPv6 over IPv6                :: Confirm that IPv4/6 over IPv6 over IPv6 works nomally. | step1: Ping to Host-B from Host-A. (IPv4/6) => Ping succeed.
  - AWP-10980   0.324 [IPv6 RA Guard         ] RA Guard cannot be bypassed with permit HW filters      :: Router Advertisment Guard (raguard) configeratations cannot be bypassed with permit all ipv6 filters. raguard has a higher precede

### AWPTCM-T44191  |  area: IPv6  |  feature: Trace Route
folder:/New Platform Template/IPv6  steps:1  obj:True
ZEPHYR: OBJ: Command will display route paths || Trace Route works
  - AWP-8309    0.973 [IPv4                  ] Trace Route                                             :: Command will display route paths | step1: Trace Route works => Paths will be displayed
  - AWP-24174   0.720 [ATMF                  ] Check Trace route will be supported                     :: Check Trace route will be supported | step1: Check Trace route will be supported => Confirm Trace route will be supported
  - AWP-10233   0.712 [z_Inactive            ] Trace route Result                                      :: Correct Show Trace Results | step1: restart DUT - no config 'sh trace' => correct show output
  - AWP-10234   0.550 [z_Inactive            ] Show Run for Trace                                      :: No trace result entries | step1: Execute show running-config => Confirm no trace entries
  - AWP-18423   0.536 [Interop               ] Trace operation check                                   :: Confirm whether switch can trace correctly. | step1: Trace to 10.0.0.1 on PC. => Confirm that Trace operation succeeds.
  - AWP-10225   0.527 [z_Inactive            ] No Trace Entries                                        :: There should be no trace entries | step1: Execute 'sh running-config' => Confirm - No Trace Entries
  - AWP-10224   0.439 [z_Inactive            ] Show Trace                                              :: Show Trace' will not function | step1: Restart DUT - No config Execute 'sh trace' on DUT => The function 'sh trace' is not current
  - AWP-3557    0.376 [DNS                   ] DNS Trace                                               :: Conduct a 'trace' using the FQDN of a device to check DNS lookup | step1: Setup as shown in Setup diagram The usual DNS Trace With

### AWPTCM-T44192  |  area: IPv6 DNSandDHCPRelated  |  feature: DNSv6 Client
folder:/New Platform Template/IPv6  steps:1  obj:False
  - AWP-13281   0.244 [Software Licensing    ] DUT works "IPv6 Basic" feature in BASIC License         :: Confirm that DUT works "IPv6 Basic" feature in BASIC License . | step1: Input "IPv6 Basic feature" features command. IPv6 Basic fe
  - AWP-13280   0.216 [Software Licensing    ] Base License contains "IPv6 Basic and MLD Snoop" featur :: Confirm that Base License contains "IPv6 Basic and MLD Snooping" features. | step1: Input"Show License ","show license index | NAM
  - AWP-24176   0.214 [ATMF                  ] Check SSH client (IPv4 and IPv6) will be supported      :: Check SSH client (IPv4 and IPv6) will be supported | step1: Check SSH client (IPv4 and IPv6) will be supported => Confirm SSH clie
  - AWP-24520   0.190 [ATMF                  ] Check the support of telnet client                      :: Telnet client (IPv4 and IPv6) will be supported | step1: check telnet client will be supported => Confirm telnet client will be su
  - AWP-9876    0.164 [DHCP Snooping         ] DHCP Client test                                        :: Show ip dhcp binding displays the DHCP client correctly | step1: Setup as DHCP Client => Expecting normal behaviour.
  - AWP-6511    0.155 [SSH                   ] check SSH server via IPv6                               :: SSH Server Tests Verify that SSH session works unsing IPv6 address | step1: Connect to server(DUT) via IPv6: DUT(config-if)#ipv6 a
  - AWP-5834    0.138 [IPv6 Management       ] TFTP: ipv6 TFTP Server to TFTP Client                   :: Test for successful file transfer using TFTP from ipv6 Server to ipv6 Client | step1: Copy file from TFTP Server to TFTP Client ST
  - AWP-24084   0.136 [DHCPv6                ] DHCPv6 Client Does not install default route            :: The default DHCPv6 client behavior is to not install a default route to the DHCPv6 server. | step1: Configure the DUT with IPv6 ad

### AWPTCM-T44193  |  area: IPv6 DNSandDHCPRelated  |  feature: DNSv6 Relay
folder:/New Platform Template/IPv6  steps:1  obj:False
  - AWP-9877    0.304 [DHCP Snooping         ] DHCP Relay test                                         :: Confirm that DHCP relay should have normal behavior | step1: DHCP Relay => Expecting normal behaviour.
  - AWP-13281   0.282 [Software Licensing    ] DUT works "IPv6 Basic" feature in BASIC License         :: Confirm that DUT works "IPv6 Basic" feature in BASIC License . | step1: Input "IPv6 Basic feature" features command. IPv6 Basic fe
  - AWP-13280   0.250 [Software Licensing    ] Base License contains "IPv6 Basic and MLD Snoop" featur :: Confirm that Base License contains "IPv6 Basic and MLD Snooping" features. | step1: Input"Show License ","show license index | NAM
  - AWP-6687    0.241 [IP Helper             ] Interoperability with DHCP relay                        :: Test that when DHCP relay is enabled, IP helper works correctly | step1: With DHCP Relay => Confirm that the relay performance of 
  - AWP-3207    0.230 [DNS                   ] DNS Relay and Hotswap                                   :: DNS Relay and Hotswap | step1: Hotswap client vlans (all ports in vlan) out then in Hotswap server vlan (all ports in vlan) out th
  - AWP-18483   0.227 [Router Bridging       ] Bridge as a DHCP relay interface                        :: Bridge should be able to act as a DHCP Relay | step1: 1. Configure Bridge 2. Assign interfaces to the bridge 3. Configure bridge t
  - AWP-3361    0.226 [DNS                   ] DNS Relay startup config                                :: DNS Relay startup config | step1: Configure a reasonable complex dns relay configuration copy running-config to startup config res
  - AWP-11002   0.223 [DHCPv6                ] DHCPv6 Relay - CLI                                      :: Ensure DHCPv6 Relay supports the IPv6 address and DUT interface for the DHCPv6 server | step1: Configure DHCP Relay with an IPv6 a

### AWPTCM-T44194  |  area: IPv6 DNSandDHCPRelated  |  feature: DHCPv6 Server Relay
folder:/New Platform Template/IPv6  steps:1  obj:False
  - AWP-13798   0.605 [DHCPv6                ] DHCPv6 Relay - Working on all VLANs configured          :: DHCPv6 Relay should work with all VLANs configured with it. | step1: Configure DHCPv6 Relay on several VLANs From CR00035636 => It
  - AWP-11526   0.578 [DHCPv6                ] DHCPv6 Relay - Show commands                            :: DHCP Relay show output is correct with DHCP-Relay configured. | step1: Enter SHOW IP DHCP-RELAY => Output correctly shows the IPv6
  - AWP-11002   0.547 [DHCPv6                ] DHCPv6 Relay - CLI                                      :: Ensure DHCPv6 Relay supports the IPv6 address and DUT interface for the DHCPv6 server | step1: Configure DHCP Relay with an IPv6 a
  - AWP-11527   0.545 [DHCPv6                ] DHCPv6 Relay - Interop: MS client and server            :: DUT can relay DHCPv6 packets between a Windows 7 DHCPv6 client and Windows Server 2008 DHCPv6 server. | step1: Start Windows 7 cli
  - AWP-13559   0.542 [DHCPv6                ] DHCPv6 Relay - Multiple interfaces                      :: Ensure DHCPv6 functionality is available on seperate L3 interfaces via DHCP Relay. DHCPv6 Relay should successfully relay the corr
  - AWP-11004   0.519 [DHCPv6                ] DHCPv6 Relay - Basic functionality                      :: Ensure basic DHCPv6 functionality is available via DHCP Relay. | step1: Configure the DHCPv6 client to use DHCPv6 to obtain an IPv
  - AWP-11528   0.498 [DHCPv6                ] DHCPv6 Relay - Relay Agent Remote-ID Option             :: DHCP-Relay can add option 37 to Relay Forward packets set to the configured DHCPv6 server. This is defined in RFC 4649 "Dynamic Ho
  - AWP-24090   0.467 [DHCPv6                ] Config DHCPv6 dns-server to use interface with no assig :: To see what happens when an interface is configured as the dns-server with no IPv6 address configuration. | step1: Configure DUT D

### AWPTCM-T44195  |  area: IPv6 DNSandDHCPRelated  |  feature: DHCPv6 Client
folder:/New Platform Template/IPv6  steps:0  obj:True
ZEPHYR: OBJ: Lease expiry and renewal process ||
  - AWP-15615   0.552 [Exploratory Tests     ] DHCP Client Lease Renewal                               :: | step1: Configure DUT as DHCP Client. Connect it to DHCP Server and configure the lease time => Check that lease is renewed after
  - AWP-24084   0.480 [DHCPv6                ] DHCPv6 Client Does not install default route            :: The default DHCPv6 client behavior is to not install a default route to the DHCPv6 server. | step1: Configure the DUT with IPv6 ad
  - AWP-13559   0.436 [DHCPv6                ] DHCPv6 Relay - Multiple interfaces                      :: Ensure DHCPv6 functionality is available on seperate L3 interfaces via DHCP Relay. DHCPv6 Relay should successfully relay the corr
  - AWP-11527   0.430 [DHCPv6                ] DHCPv6 Relay - Interop: MS client and server            :: DUT can relay DHCPv6 packets between a Windows 7 DHCPv6 client and Windows Server 2008 DHCPv6 server. | step1: Start Windows 7 cli
  - AWP-24085   0.425 [DHCPv6                ] DHCPv6 Client Default Route Enabled                     :: The device must be able to be configured to use DHCPv6 client to install an IPv6 default route via the DHCPv6 server. This functio
  - AWP-24115   0.417 [DHCPv6                ] DHCPv6 Client Default Route CLI Test                    :: CLI testing for DHCPv6 client to install an IPv6 default route via the DHCPv6 server. | step1: Test that you are able to configure
  - AWP-11526   0.401 [DHCPv6                ] DHCPv6 Relay - Show commands                            :: DHCP Relay show output is correct with DHCP-Relay configured. | step1: Enter SHOW IP DHCP-RELAY => Output correctly shows the IPv6
  - AWP-13794   0.401 [DHCPv6                ] DHCPv6 - Show Commands                                  :: Show commands for DHCPv6 must be accurate, helpful and complete. | step1: Check all available show commands for DHCPv6. Ex: Check 

### AWPTCM-T44196  |  area: IPv6 DNSandDHCPRelated  |  feature: DHCPv6 Relay
folder:/New Platform Template/IPv6  steps:5  obj:True
ZEPHYR: OBJ: Ensure basic DHCPv6 functionality is available via DHCP Relay. || Configure the DHCPv6 client to use DHCPv6 to obtain an IPv6 | Configure DHCP Relay on the DUT interface connected to the c | Chec
  - AWP-11004   0.983 [DHCPv6                ] DHCPv6 Relay - Basic functionality                      :: Ensure basic DHCPv6 functionality is available via DHCP Relay. | step1: Configure the DHCPv6 client to use DHCPv6 to obtain an IPv
  - AWP-11526   0.546 [DHCPv6                ] DHCPv6 Relay - Show commands                            :: DHCP Relay show output is correct with DHCP-Relay configured. | step1: Enter SHOW IP DHCP-RELAY => Output correctly shows the IPv6
  - AWP-11003   0.499 [DHCPv6                ] DHCPv6 Relay - Duel IPv4 and IPv6 operation             :: Both IPv4 and IPv6 DHCP Relays can operate on an AWP device Each relay operates independent of the other. The running configuratio
  - AWP-13559   0.485 [DHCPv6                ] DHCPv6 Relay - Multiple interfaces                      :: Ensure DHCPv6 functionality is available on seperate L3 interfaces via DHCP Relay. DHCPv6 Relay should successfully relay the corr
  - AWP-11002   0.451 [DHCPv6                ] DHCPv6 Relay - CLI                                      :: Ensure DHCPv6 Relay supports the IPv6 address and DUT interface for the DHCPv6 server | step1: Configure DHCP Relay with an IPv6 a
  - AWP-11527   0.418 [DHCPv6                ] DHCPv6 Relay - Interop: MS client and server            :: DUT can relay DHCPv6 packets between a Windows 7 DHCPv6 client and Windows Server 2008 DHCPv6 server. | step1: Start Windows 7 cli
  - AWP-24045   0.392 [DHCPv6                ] IPv6 DNS queries from the device are sent to DNS server :: The client should obtain DNS server addresses of the DUT (DHCPv6 Server) dynamically configured interface address. | step1: Config
  - AWP-11515   0.383 [DHCPv6                ] DHCPv6 Relay - Stability with link state changes        :: Ensure DHCP relay handles changes in link state and IP address assignment of its server and client links. This is a test with a si

### AWPTCM-T44197  |  area: IPv6 DNSandDHCPRelated  |  feature: DHCPv6-PD
folder:/New Platform Template/IPv6  steps:3  obj:True
ZEPHYR: OBJ: The device must be able to be configured to use DHCPv6 PD client to install an IPv6 default route via the DHCPv6 PD serv || Configure the DUT to be a DHCPv6 PD client with default rout | Configur
  - AWP-24110   0.986 [DHCPv6                ] DHCPv6 PD Client Default Route Enabled                  :: The device must be able to be configured to use DHCPv6 PD client to install an IPv6 default route via the DHCPv6 PD server. This f
  - AWP-24085   0.817 [DHCPv6                ] DHCPv6 Client Default Route Enabled                     :: The device must be able to be configured to use DHCPv6 client to install an IPv6 default route via the DHCPv6 server. This functio
  - AWP-24108   0.679 [DHCPv6                ] DHCPv6 PD Client Does not install default route         :: The default DHCPv6 Prefix Delegation client behavior is to not install a default route to the DHCPv6 server. | step1: Configure th
  - AWP-24116   0.674 [DHCPv6                ] DHCPv6 PD Client Default Route CLI test                 :: CLI testing for DHCPv6 PD client to install an IPv6 default route via the DHCPv6 PD server. This functionality will be introduced 
  - AWP-24113   0.636 [DHCPv6                ] DHCPv6 PD Client Default Route Removal                  :: A device configured to install a default route via the DHCPv6 Prefix Delegation client must be able to remove this default route, 
  - AWP-24086   0.605 [DHCPv6                ] DHCPv6 Client Default Route Removal                     :: A device conigured to install a default route via the DHCPv6 client must be able to remove this default route. | step1: Enable IPv
  - AWP-24084   0.604 [DHCPv6                ] DHCPv6 Client Does not install default route            :: The default DHCPv6 client behavior is to not install a default route to the DHCPv6 server. | step1: Configure the DUT with IPv6 ad
  - AWP-13793   0.473 [DHCPv6                ] DHCPv6 - Link-Local address installed/activated on a DH :: Link-Local address should be automatically installed/activated when only DHCPv6/prefix delegation is configured in an interface by

### AWPTCM-T44198  |  area: IPv6 Routing  |  feature: BGP4+
folder:/New Platform Template/IPv6  steps:1  obj:True
ZEPHYR: OBJ: Confirm max supported BGP4+ routers || Network setup: Ixia -> L2 Switch -> [DUT] Setup: -Clear all
  - AWP-14054   0.989 [BGP4+                 ] BGP4+ Routes                                            :: Confirm max supported BGP4+ routers | step1: Network setup: Ixia -> L2 Switch -> [DUT] Setup: -Clear all configs off the DUTs and 
  - AWP-17284   0.989 [Limits                ] BGP4+ Routes                                            :: Confirm max supported BGP4+ routers | step1: Network setup: Ixia -> L2 Switch -> [DUT] Setup: -Clear all configs off the DUTs and 
  - AWP-5032    0.797 [Limits                ] BGP Routes                                              :: Confirm max supported BGP routers | step1: Network setup: Ixia -> L2 Switch -> [DUT] This test can be done manually or using ATPyL
  - AWP-5022    0.418 [Limits                ] RIP routes                                              :: This test makes use of several Devices. To test make routes learned. | step1: Network setup: Ixia -BGP->[redist device SwitchB] <-
  - AWP-5024    0.372 [Limits                ] OSPF routes                                             :: Confirm max supported OSPF routes | step1: Network setup: Ixia -BGP->[redist device] <-OSPF-> [DUT] This test can be done manually
  - AWP-13953   0.327 [BGP4+                 ] BGP4+ Standard Test - Network Command                   :: Advertising routes using the network command | step1: Advertise IPv6 routes using the "network command" check advertisements using
  - AWP-14064   0.311 [BGP4+                 ] Forward 5000 BGP4+ routes into RIPng                    :: Check that there is no delay in redistribution of routes to the target device. | step1: Setup IxRouter to forward 5000 BGP4+ route
  - AWP-7583    0.300 [Route Redistribution  ] Redistribute 5000 OSPF routes into RIP/BGP              :: Objective: To confirm that RIP/BGP can redistribute 5000 OSPF routes Expected Outcome: RIP/BGP should be able to redistribute 5000

### AWPTCM-T44199  |  area: IPv6 Routing  |  feature: IPv6 Static Routing
folder:/New Platform Template/IPv6  steps:0  obj:True
ZEPHYR: OBJ: IPv6でStatic routeの動作を確認する。 ■Environment Topology_A2 ■Shutdown port - DUT : PeerInt2,PeerInt3,PeerInt4,TestInt2,TestInt3, ||
  - AWP-24240   0.585 [[ATKK] Auto Acceptance] Add RIP routes to route-table                           :: Validate addition RIP routes to the route-table. Enviroment Topology_A2 -DUT:PeerInt2,PeerInt3,PeerInt4,TestInt2,TestInt3,TestInt4
  - AWP-25914   0.477 [[ATKK] Auto Acceptance] OSPF : route aggregate on ASBR                          :: topology IXIA------DUT------DUT2------IXIA Ixia.Port1------DUT.TestInt1 DUT.PeerInt1------DUT2.PeerInt1 DUT2.TestInt1------Ixia.Po
  - AWP-22606   0.390 [[ATKK] Auto Acceptance] vlan classifier and tag vlan                            :: | step1: send packet to TestInt1 - send packet from 192.168.10.1 to 192.168.10.2 - send packet from 192.168.20.1 to 192.168.20.2 =
  - AWP-22604   0.290 [[ATKK] Auto Acceptance] vlan classifier and LACP                                :: | step1: Run following config (DUT) vlan database vlan 10,20 state enable ! vlan classifier rule 1 ipv4 192.168.10.0/24 vlan 10 v 
  - AWP-22607   0.240 [[ATKK] Auto Acceptance] vlan classifier and multicast packet                    :: confirm vlan classifier control multicast packet. | step1: send packet to port1.0.1 - send packet from 192.168.10.1 to 224.0.0.1 -
  - AWP-23347   0.205 [[ATKK] Auto Acceptance] Protocol based VLAN with some important protocols       :: This testcase based AWP-9220. | step1: setup following config awplus#show run no spanning-tree rstp enable ! vlan database vlan 2-
  - AWP-15936   0.192 [IPv4                  ] Disabled Static Routing                                 :: Confirm that Static Routing doesn't work when "no ip forwarding" in configured. | step1: Ping to other network address from PC1. =
  - AWP-23349   0.189 [[ATKK] Auto Acceptance] vlan classifier and ip routing on static LAG            :: | step1: send the packet and check DUT route the packet on IP subnet vlan port. => the packet should be routed on vlan10 and vlan2

### AWPTCM-T44200  |  area: IPv6  |  feature: RIPng
folder:/New Platform Template/IPv6  steps:1  obj:False
  - AWP-8094    0.646 [RIPng                 ] Delete a RIPng enabled vlan                             :: | step1: Delete a RIPng enabled vlan => Changes in network should be reflected in sh ipv6 route and device config
  - AWP-8091    0.609 [RIPng                 ] RIPng info of RIPng enabled interfaces                  :: RIPng routes only display RIPng enable interfaces | step1: Network for Interfaces with RIPng not enabled should not appear in rout
  - AWP-12155   0.593 [VRRP                  ] VRRP Interop with RIPng                                 :: To verify interoperability between VRRP and RIPng | step1: Setup RIPng and VRRP => Confirm VRRP works with RIPng
  - AWP-13642   0.573 [Limits                ] RIPng interfaces                                        :: Confirm the maximum number of RIPng interfaces that the DUT supports. | step1: Confirm the current limit. => The limit when this t
  - AWP-10271   0.542 [Process Monitoring    ] Memory Monitoring - RIPng                               :: Correct output information for RIPng | step1: Execute the command "show memory allocations" and capture output => Check memory inf
  - AWP-8099    0.534 [RIPng                 ] RIPng and STP                                           :: RIPng should work without STP | step1: 1. Turn off STP, and see how does RIPng handle it => RIPng should be able to deal with rout
  - AWP-8115    0.532 [RIPng                 ] RIPng works with VMAC on                                :: | step1: Check that [Feature] still functions correctly. => Feature should function without degradation
  - AWP-8098    0.518 [RIPng                 ] RIPng with link aggregation and EPSR                    :: RIPng can be interoperate with EPSR | step1: 1. Setup link aggregation 2. Take out links verify RIPng functionality 3.Add EPSR to 

### AWPTCM-T44201  |  area: IPv6  |  feature: OSPFv3
folder:/New Platform Template/IPv6  steps:1  obj:False
  - AWP-12156   0.523 [VRRP                  ] VRRP Interop with OSPFv3                                :: To verify interoperability between VRRP and OSPFv3 | step1: Setup VRRP and OSPFv3 => Confirm VRRP works with OSPFv3
  - AWP-3379    0.520 [OSPFv3                ] OSPFv3 Command Line Help                                :: Check that the ‘help’ descriptions for the OSPFv3 commands are useful | step1: check all ospfv3 commands ipv6 ospf configuration m
  - AWP-2629    0.441 [z_Inactive            ] OSPFv3 source IPv6 address (INACTIVE IxANVL OSPFV3-2.1) :: Check that the source IPv6 address on the OSPFv6 packets that the switch sends is the link-local address. | step1: Set up OSPF nei
  - AWP-13641   0.440 [Limits                ] OSPFv3 interfaces                                       :: Confirm the maximum number of OSPFv3 interfaces that the DUT supports | step1: Confirm the current maximum number of OSPFv3 interf
  - AWP-14074   0.426 [BGP4+                 ] Redistribute into BGP4+ from OSPFv3                     :: Confirm that OSPFv3 routes should be redistributed into BGP4+ | step1: Redistribute into BGP4+ from OSPFv3 Configure for redistrib
  - AWP-14095   0.415 [BGP4+                 ] License - BGP4+ -redistribution from OSPFv3 - routes ad :: In BGP router config mode, enable redistribution from OSPFv3. Configure OSPFv3 and advertise routes using OSPF from an Ixia port. 
  - AWP-13493   0.415 [Validation Scenario   ] OSPFv3 - Unicast Traffic                                :: Check and verify OSPFv3 for correct status and functionality. | step1: Run background unicast traffic in the relevant scenario. =>
  - AWP-4321    0.405 [z_Inactive            ] OSPFv3 License shown in show license                    :: OSPFv3 License shown in show license | step1: Implied in other tests for licenses => OSPFv3 License shown in show license Implied 
