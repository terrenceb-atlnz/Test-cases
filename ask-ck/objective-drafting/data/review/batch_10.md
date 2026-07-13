# Rerank batch 10  (cases 300..329)

### AWPTCM-T44304  |  area: Management Triggers  |  feature: Stack Member
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-5290    0.505 [OSPF                  ] Stack Failover Member                                   :: Stack should use VMAC even on Stack Member | step1: Fail-over Member => Check that [Feature] uses virtual-MAC on member
  - AWP-11523   0.492 [Triggers              ] Trigger Stress Test multiple stack member join triggers :: Trigger stress test | step1: Activate multiple triggers simultaneously (type=stack member join) => The DUT must work without any m
  - AWP-624     0.480 [Triggers              ] Stack (VCS) Trigger on stack member join                :: Test for VCS triggers | step1: Configure the trigger to be activated when the device becomes a stack member by joining => Trigger 
  - AWP-625     0.470 [Triggers              ] Stack (VCS) Trigger on stack member leave               :: Test for VCS triggers | step1: Configure the trigger to be activated when the stack member leaves the stacking group => Trigger ac
  - AWP-5281    0.433 [OSPF                  ] Stack Fail-over Member                                  :: Stack member should use the Master MAC when it boots up | step1: Fail-over Member => Check that [Feature] uses MAC of Master when 
  - AWP-24179   0.423 [ATMF                  ] Check Triggers will be supported                        :: Check Triggers will be supported | step1: check triggers will be supported => confirm triggers is supported
  - AWP-638     0.395 [Triggers              ] Trigger Stress Test multiple stack triggers             :: Trigger stress test | step1: Activate multiple triggers simultaneously (type=stack) => The DUT must work without any memory leak o
  - AWP-25756   0.394 [Bootup                ] ETH as Management Port: DHCP-server connected to the st :: This test is to check "Extended Clean Node Startup" when the DHCP server is connected to the ETH port of Stack-Member in a stack e

### AWPTCM-T44305  |  area: Management Triggers  |  feature: Stack Link
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-628     0.444 [Triggers              ] Stack (VCS) Trigger on stack link up/down               :: Test for VCS triggers | step1: Configure the trigger to be activated when the xem-stk link goes up/down => Trigger activated
  - AWP-24179   0.437 [ATMF                  ] Check Triggers will be supported                        :: Check Triggers will be supported | step1: check triggers will be supported => confirm triggers is supported
  - AWP-638     0.407 [Triggers              ] Trigger Stress Test multiple stack triggers             :: Trigger stress test | step1: Activate multiple triggers simultaneously (type=stack) => The DUT must work without any memory leak o
  - AWP-11523   0.371 [Triggers              ] Trigger Stress Test multiple stack member join triggers :: Trigger stress test | step1: Activate multiple triggers simultaneously (type=stack member join) => The DUT must work without any m
  - AWP-584     0.352 [Triggers              ] Interface Trigger on VLAN - Link down on LINK UP Trigge :: Tests for interface triggers | step1: Remove cable from a vlan1 port, on a device configured with a link-UP interface trigger => T
  - AWP-597     0.339 [Triggers              ] Interface Trigger link down                             :: Tests for interface triggers | step1: Remove cable from a vlan1 port within a trigger-specified time period => The link goes down 
  - AWP-13059   0.338 [Find Me               ] Long Run: Triggers                                      :: Long Run with Triggers | step1: Link some ports to ensure LEDs are up Or ports are active with traffic flowing Create a script (.s
  - AWP-4990    0.333 [Limits                ] Triggers                                                :: To verify max trigger can be configured | step1: - Create up to 251 triggers => - Confirm that there is 250 configured triggers - 

### AWPTCM-T44306  |  area: Management Triggers  |  feature: AMF
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-24179   0.446 [ATMF                  ] Check Triggers will be supported                        :: Check Triggers will be supported | step1: check triggers will be supported => confirm triggers is supported
  - AWP-4990    0.340 [Limits                ] Triggers                                                :: To verify max trigger can be configured | step1: - Create up to 251 triggers => - Confirm that there is 250 configured triggers - 
  - AWP-25865   0.300 [ATMF                  ] AMF Links API - Get all AMF links                       :: Web API support for getting all AMF links | step1: Use URL to list all ATMF links including link types and states etc => output sh
  - AWP-13059   0.291 [Find Me               ] Long Run: Triggers                                      :: Long Run with Triggers | step1: Link some ports to ensure LEDs are up Or ports are active with traffic flowing Create a script (.s
  - AWP-23039   0.288 [ATMF                  ] Change the network name on the AMF masters              :: Change the network name on the AMF masters | step1: change the network name on AMF master to a different one from the existing net
  - AWP-25862   0.283 [ATMF                  ] AMF Links API - Delete AMF virtual crosslink            :: Web API support for deleting AMF virtual crosslink | step1: use URL to remove an ATMF virtual crosslink => configuration should be
  - AWP-563     0.279 [Triggers              ] Max Number of Triggers                                  :: Tests for basic trigger CLI commands | step1: Create 250 triggers => Triggers 1-250 display accurately in sh running-config, sh tr
  - AWP-636     0.279 [Triggers              ] Trigger Stress Test multiple interface triggers         :: Trigger stress test | step1: Activate multiple triggers simultaneously (type=interface) => The DUT must work without any memory le

### AWPTCM-T44307  |  area: Management Triggers  |  feature: Log message
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-24179   0.448 [ATMF                  ] Check Triggers will be supported                        :: Check Triggers will be supported | step1: check triggers will be supported => confirm triggers is supported
  - AWP-13059   0.398 [Find Me               ] Long Run: Triggers                                      :: Long Run with Triggers | step1: Link some ports to ensure LEDs are up Or ports are active with traffic flowing Create a script (.s
  - AWP-12311   0.346 [Green Features (Ecofri] Long Run: Triggers                                      :: Long Run with Triggers | step1: Enable LPI in all ports and loopback all ports. Create EEE.scp and activate it using triggers Plea
  - AWP-4990    0.341 [Limits                ] Triggers                                                :: To verify max trigger can be configured | step1: - Create up to 251 triggers => - Confirm that there is 250 configured triggers - 
  - AWP-9818    0.281 [DHCP Snooping         ] DHCP Snooping Violation - log message                   :: Confirm log message when violation occurs | step1: DHCP Snooping Violation - log => log message when violation occurs - eg max bin
  - AWP-563     0.280 [Triggers              ] Max Number of Triggers                                  :: Tests for basic trigger CLI commands | step1: Create 250 triggers => Triggers 1-250 display accurately in sh running-config, sh tr
  - AWP-636     0.280 [Triggers              ] Trigger Stress Test multiple interface triggers         :: Trigger stress test | step1: Activate multiple triggers simultaneously (type=interface) => The DUT must work without any memory le
  - AWP-638     0.276 [Triggers              ] Trigger Stress Test multiple stack triggers             :: Trigger stress test | step1: Activate multiple triggers simultaneously (type=stack) => The DUT must work without any memory leak o

### AWPTCM-T44308  |  area: Management  |  feature: RMON
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-10279   0.623 [Process Monitoring    ] Memory Monitoring - RMON                                :: Correct output information for RMON | step1: Execute the command "show memory allocations" and capture output => Check memory info
  - AWP-1723    0.556 [SNMP                  ] RFC2819-MIB - Verify OID - rmon                         :: NOT-ACCESSIBLE SNMP Access Type Objects RFC2819-MIB II-Verify OID | step1: Verify OID - rmon => OID should be 1.3.6.1.2.1.16
  - AWP-18542   0.489 [802.1Q Interfaces     ] 802.1Q interface with RMON                              :: An 802.1Q sub-interface is capable of transmiting packets to an RMON collector Note: RMON is not supported on 545 release | step1:
  - AWP-13649   0.394 [SNMP                  ] RFC2819-RMON-MIB Traps (Notification)                   :: Test case to verify CR00023686 | step1: Generate traffic on eth0/port interface (e.g. by pinging a connected device) until incomin
  - AWP-1387    0.354 [SNMP                  ] RFC2819 (RMON MIB) - Group 1 Accessible                 :: RFC2819 - RMON MIB RFC1757 - RMON MIB Objective: MIBs describe the structure of the management data of a device subsystem; they us
  - AWP-1388    0.354 [SNMP                  ] RFC2819 (RMON MIB) - Group 2 Accessible                 :: RFC2819 - RMON MIB RFC1757 - RMON MIB Objective: MIBs describe the structure of the management data of a device subsystem; they us
  - AWP-1389    0.354 [SNMP                  ] RFC2819 (RMON MIB) - Group 3 Accessible                 :: RFC2819 - RMON MIB RFC1757 - RMON MIB Objective: MIBs describe the structure of the management data of a device subsystem; they us
  - AWP-1390    0.354 [SNMP                  ] RFC2819 (RMON MIB) - Group 9 Accessible                 :: RFC2819 - RMON MIB RFC1757 - RMON MIB Objective: MIBs describe the structure of the management data of a device subsystem; they us

### AWPTCM-T44309  |  area: Management SFlow  |  feature: SFlow Agent
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-8723    0.513 [sFlow                 ] Configure sflow then save config and reboot             :: | step1: Configure sflow (enable), agent, collector and interface, then save the config and perform a reboot => sflow configuratio
  - AWP-8713    0.498 [sFlow                 ] Command Line Handler - sflow agent and collector ipv4   :: Confirm sflow agent and collector can be configure via ipv4 | step1: Able to configure sflow agent and collector in ipv4 address -
  - AWP-8738    0.497 [sFlow                 ] sFlow ipv6 agent and collector                          :: Confirm sflow agent and collector works using ipv6 addressing | step1: Configure sflow agent and collector using ipv6 address - sf
  - AWP-8726    0.496 [sFlow                 ] Command Line Handler - show sflow                       :: | step1: Issue following commands: - show sflow - show sflow interface portx.y.z => Confirm that the CLI shows sflow agent propert
  - AWP-8714    0.483 [sFlow                 ] Command Line Handler - sflow agent and collector ipv6   :: Confirm that sflow agent and collector can configure via ipv6 | step1: Able to configure sflow agent and collector in ipv6 address
  - AWP-8725    0.434 [sFlow                 ] Check sflow default status                              :: | step1: Check that sflow is not turned on by default - startup device without any config - issue command "show sflow" => Confirm 
  - AWP-8773    0.405 [sFlow                 ] sFlow MIB                                               :: Able to walk sFlow MIB | step1: Load sFlow MIB and perform WALK => Using MIB browser, confirm all the MIB being set as expected
  - AWP-8718    0.392 [sFlow                 ] Configure sflow on an interface port for sampling       :: | step1: Configure sflow on the interface port1.0.1 for sampling => Able to configure interface port1.0.1 and confirmed from show 

### AWPTCM-T44310  |  area: Management  |  feature: Industry standard SHOW INTERFACE STATUS
folder:/New Platform Template/Management  steps:2  obj:False
ZEPHYR: sh int status verify correct output | awplus#sh interface ?
  - AWP-8202    0.220 [BGP                   ] Device Management - Show Command                        :: Show command output | step1: Show command output => Accurate and useful
  - AWP-8594    0.203 [ACL                   ] ACL: Named Standard - adding & removing entries         :: ACL: Named Standard - adding & removing entries | step1: Configure and negate named standard ACLs access-list standard <name> [per
  - AWP-8581    0.198 [ACL                   ] ACL: Standard - Entries                                 :: ACL: Standard - Entries | step1: Configure and negate standard ACLs access-list {<1-99> | <1300-1999>} [permit | deny] no access-l
  - AWP-8603    0.198 [ACL                   ] ACL: IPv6 Named Standard - adding & removing entries    :: ACL: IPv6 Named Standard - adding & removing entries | step1: Configure and negate IPv6 named standard ACLs ipv6 access-list stand
  - AWP-13953   0.193 [BGP4+                 ] BGP4+ Standard Test - Network Command                   :: Advertising routes using the network command | step1: Advertise IPv6 routes using the "network command" check advertisements using
  - AWP-5496    0.182 [TFTP                  ] Interop with "standard" Linux TFTP Server               :: | step1: Interop with "standard" Linux TFTP Server => Use testbox
  - AWP-8604    0.178 [ACL                   ] ACL: IPv6 Named Standard - adding & removing entries by :: ACL: IPv6 Named Standard - adding & removing entries by sequence number | step1: Configure and negate IPv6 named standard ACLs usi
  - AWP-8582    0.177 [ACL                   ] ACL: Standard - Full lists                              :: ACL: Standard - Full lists | step1: Configure and negate standard ACLs - full range access-list {<1-99> | <1300-1999>} [permit | d

### AWPTCM-T44311  |  area: Redundency  |  feature: VCS
folder:/New Platform Template/Redundancy  steps:1  obj:False
  - AWP-18454   0.393 [Validation Scenario   ] VCS - ICMP Reply From VCS Member                        :: Test functionality of ICMP reply from VCS meber | step1: Configure appropriate Vlan and ip addresses
  - AWP-7187    0.383 [IGMP                  ] VCS and IGMP feature                                    :: Check that [Feature] uses Master-MAC when Virtual-MAC is not enabled | step1: Check that [Feature] uses Master-MAC when Virtual-MA
  - AWP-627     0.375 [Triggers              ] Stack (VCS) Trigger on master fail                      :: Test for VCS triggers | step1: Configure the trigger to be activated when the master-fail occurs => Trigger activated
  - AWP-12796   0.368 [MLD                   ] VCS and MLD feature                                     :: Check that [Feature] uses Master-MAC when Virtual-MAC is not enabled | step1: Check that [Feature] uses Master-MAC when Virtual-MA
  - AWP-25787   0.361 [Logging               ] Log external after VCS failover.                        :: Check the behavior after master failover. | step1: Tested AWP-25786. (Setup log configration with VCS.)
  - AWP-7775    0.358 [Validation Scenario   ] VCS - Unicast Traffic                                   :: Check and verify VCS for correct status and functionality. | step1: Run background unicast traffic in the relevant scenario. => Se
  - AWP-7188    0.351 [IGMP                  ] VCS and IGMP - Fail-over Member                         :: Fail-over Member | step1: Fail-over Member => Check that [Feature] uses MAC of Master when it rejoins the stack
  - AWP-7618    0.350 [Policy Based Routing  ] VCS - apply PBR to ingress ports                        :: Confim that PBR can be applied to the ingress ports in a VCS environment | step1: Able to apply PBR to the ingress ports in a VCS 

### AWPTCM-T44312  |  area: Redundency  |  feature: Resiliency link on switch port
folder:/New Platform Template/Redundancy  steps:1  obj:False
  - AWP-5293    0.585 [OSPF                  ] Stack with Resiliency Link                              :: Stack should still operate through a resiliency link | step1: Master fail-over with resiliency link configured and operating. Lost
  - AWP-4586    0.583 [PoE                   ] PoE Disabled Master Resiliency Link                     :: POE Functionality continues on a port configured for resiliency link | step1: A port configured for resiliency link may also suppo
  - AWP-8338    0.533 [IPv4                  ] Master fail-over with resiliency link                   :: Master fail-over with resiliency link configured and operating. | step1: Master fail-over with resiliency link configured and oper
  - AWP-10992   0.497 [VRF-Lite              ] VRF Lite route to resiliency Vlan                       :: To check that it is not possible to create a route (static or dynamic) to the resiliency link vlan | step1: create a static route 
  - AWP-12494   0.494 [PIM-SMv6              ] Resiliency link configured, traffic running, perform fa :: Testing vmac with resiliency link, performing fail overs with multicast. | step1: Fail overs with the resiliency link configured (
  - AWP-10988   0.494 [VRF-Lite              ] VRF_Lite and Stack Resiliency Link                      :: To test a stack with resiliency link configured and ensure that there is no problem noted with co-operation with VRF lite. | step1
  - AWP-9672    0.479 [xSTP                  ] Master fail-over with resiliency link configured and op :: | step1: Master fail-over with resiliency link configured and operating. Lost stack connectivity but not resiliency link => Stack 
  - AWP-9396    0.479 [xSTP                  ] Master fail-over with resiliency link configured and op :: | step1: Master fail-over with resiliency link configured and operating. Lost stack connectivity but not resiliency link => Stack 

### AWPTCM-T44313  |  area: Redundency  |  feature: Long distance stacking on SFP+
folder:/New Platform Template/Redundancy  steps:1  obj:False
  - AWP-8294    0.425 [IPv4                  ] Static Route Distance Value                             :: Command can define the distance for a certain static route | step1: To add static routes to device, use device to communicate with
  - AWP-21036   0.373 [ATMF                  ] ATMF VM : Static Route Distance Value                   :: Command can define the distance for a certain static route | step1: To add static routes to device, use device to communicate with
  - AWP-28501   0.328 [DS-Lite               ] API: Configure DS-Lite default route distance via API   :: DS-Lite must be able to ber configured with a custom default route distance using the API. | step1: Perform API testing to add/rem
  - AWP-28511   0.320 [DS-Lite               ] Check the ds-lite default route has the custom distance :: The DS-Lite default route must be installed into the routing table with the correct custom administrative distance. | step1: Confi
  - AWP-24141   0.317 [Pluggable Transceivers] using SFP+ to form stack                                :: | step1: using SFP+ purely for stacking => stack should form
  - AWP-28454   0.315 [DS-Lite               ] CLI: DS-lite default route distance command             :: The DS-Lite feature must have a command to set the administrative distance for the default route via the DS-Lite tunnel. | step1: 
  - AWP-24143   0.238 [Pluggable Transceivers] SFP+ passing traffic                                    :: | step1: using SPF+ on lif card => traffic should pass
  - AWP-2632    0.236 [OSPFv3                ] OSPFv3 correct administrative distance                  :: Check that routes learnt by OSPFv3 are put into the route table with the correct Administrative Distance. Note that there is no "d

### AWPTCM-T44314  |  area: Redundency  |  feature: Long distance stacking on QSFP+
folder:/New Platform Template/Redundancy  steps:1  obj:False
  - AWP-24089   0.403 [Pluggable Transceivers] QSFP+ will form stack                                   :: | step1: if QSFP+ is applied => stack will form
  - AWP-8294    0.394 [IPv4                  ] Static Route Distance Value                             :: Command can define the distance for a certain static route | step1: To add static routes to device, use device to communicate with
  - AWP-24136   0.379 [Pluggable Transceivers] Mixed use DAC for traffic and QSFP+ for stacking        :: "stack enable expansion-ports" | step1: plug DAC first => no stack form
  - AWP-24137   0.354 [Pluggable Transceivers] Mixed use DAC for stacking and QSFP+ for traffic        :: stack enable builtin-ports | step1: plug QSFP+ first => no stack should form
  - AWP-21036   0.346 [ATMF                  ] ATMF VM : Static Route Distance Value                   :: Command can define the distance for a certain static route | step1: To add static routes to device, use device to communicate with
  - AWP-24132   0.305 [Pluggable Transceivers] QSFP+ stands for hotswap                                :: | step1: hotswap QSFP+ stack cable (both) => it is expected the devices form stack after hotswap
  - AWP-28501   0.304 [DS-Lite               ] API: Configure DS-Lite default route distance via API   :: DS-Lite must be able to ber configured with a custom default route distance using the API. | step1: Perform API testing to add/rem
  - AWP-28511   0.296 [DS-Lite               ] Check the ds-lite default route has the custom distance :: The DS-Lite default route must be installed into the routing table with the correct custom administrative distance. | step1: Confi

### AWPTCM-T44315  |  area: Redundency  |  feature: N-unit stacking with basic license features
folder:/New Platform Template/Redundancy  steps:1  obj:False
  - AWP-13298   0.357 [Software Licensing    ] VCS:Master with PREMIUM License and Slave with BASIC Li :: VCS:Master with PREMIUM License and Slave with BASIC License only don't stack. | step1: Master with PREMIUM License and Slave with
  - AWP-15261   0.344 [Software Licensing    ] License - Testing bit 12- IPv6 Basic                    :: Testing that license bit correctly turns appropriate feature on or off at : boot time, when a license is added/deleted and when tr
  - AWP-13280   0.341 [Software Licensing    ] Base License contains "IPv6 Basic and MLD Snoop" featur :: Confirm that Base License contains "IPv6 Basic and MLD Snooping" features. | step1: Input"Show License ","show license index | NAM
  - AWP-13291   0.331 [Software Licensing    ] DUT has old license and new BASIC License when FW up.   :: DUT has old license and new BASIC License when FW up. | step1: 1. Input old license key with old Firmware 2. Firmware up to v5.4.3
  - AWP-13281   0.319 [Software Licensing    ] DUT works "IPv6 Basic" feature in BASIC License         :: Confirm that DUT works "IPv6 Basic" feature in BASIC License . | step1: Input "IPv6 Basic feature" features command. IPv6 Basic fe
  - AWP-13283   0.309 [Software Licensing    ] DUT does not delete Basic License when use "no licesnse :: Confirm that DUT does not delete Basic License when use "no licesnse" command. | step1: Input "no license" command. => DUT display
  - AWP-13301   0.275 [Software Licensing    ] x8100:MasterCFC with PREMIUM License and SlaveCFC with  :: x8100:MasterCFC with PREMIUM License and SlaveCFC with BASIC License are established stack.. | step1: MasterCFC with PREMIUM Licen
  - AWP-7032    0.270 [z_Inactive            ] License Bundle - IPv6 (Japan) (x600)                    :: License bundle - IPv6 (Japan) (x600) License Bundle (For 5.4.1) Functional test for each of the features within the license bundle

### AWPTCM-T44316  |  area: Redundency  |  feature: N-unit stacking with Full L3 license features
folder:/New Platform Template/Redundancy  steps:1  obj:False
  - AWP-13685   0.322 [Software Licensing    ] License Bundle - IPv6 (Japan) (x610)                    :: License bundle - IPv6 (Japan) for x610 platform | step1: x610 IPv6 License All Advanced L3 features plus: OSPFv3-64 OSPFv3-Full RI
  - AWP-13675   0.300 [Software Licensing    ] License Bundle - Adv L3 (ROW) (x610)                    :: License bundle - L3 (ROW) for x610 platform | step1: x610 Advanced L3 License All Base License features plus: OSPF-Full BGP-64 BGP
  - AWP-13684   0.299 [Software Licensing    ] License Bundle - Adv L3 (Japan) (x610)                  :: License bundle - L3 (Japan) for x610 platform | step1: x610 Advanced L3 License All Base License features plus: OSPF-Full BGP-64 B
  - AWP-7018    0.299 [z_Inactive            ] License Bit Codes - bundle -RADIUS-full                 :: License - bundle -RADIUS-full | step1: RADIUS-full => Confirm license/bit map are valid for the release and can be applied and all
  - AWP-28192   0.297 [Software Licensing    ] License bundle - Base (ROW) for x550 platform           :: | step1: Execute show license => awplus#sh license Board region: Global Feature licenses on stack member 2: Index
  - AWP-28191   0.295 [Software Licensing    ] License bundle - Base (Japan) for x550 platform         :: | step1: Execute show license => awplus#sh license Board region: Japan Feature licenses on stack member 2: Index
  - AWP-13266   0.289 [Software Licensing    ] PREMIUM License (x510 only)                             :: Check PREMIUM License. Contains "RIP-FULL" features. | step1: 1.Input PREMIUM license key. 2.Input "Show License "and "show licens
  - AWP-15257   0.288 [Software Licensing    ] License - Testing bit 8 - OSPF-FULL                     :: Testing that license bit correctly turns appropriate feature on or off at : boot time, when a license is added/deleted and when tr

### AWPTCM-T44317  |  area: Redundency  |  feature: Flexi Stacking
folder:/New Platform Template/Redundancy  steps:1  obj:False
  - AWP-13729   0.430 [VLAN                  ] show vlan vlan-stacking                                 :: Verify that commands are entered without a problem and displayed correct informations. | step1: Enter "show vlan vlan-stacking". =
  - AWP-4978    0.424 [Limits                ] VCS - Maximum throughput on stacking cable              :: To verify maximum throughput for stacking cable | step1: - Using RFC2544 to test maximum throughput on stacking cable => Expecting
  - AWP-13727   0.421 [VLAN                  ] switchport vlan-stacking                                :: Verify that commands are entered without a problem and saved correctly. | step1: Enter following commands. "switchport vlan-stacki
  - AWP-9223    0.421 [VLAN                  ] VLAN Stacking with LACP (Static Channel) on customer po :: | step1: VLAN Stacking with LACP (Static Channel) on customer port => 12.11.8_config.txt
  - AWP-9222    0.416 [VLAN                  ] VLAN Stacking with LACP (Static Channel) on provider po :: | step1: VLAN Stacking with LACP (Static Channel) on provider port => 12.11.7_config.txt
  - AWP-9163    0.401 [VLAN                  ] Command Line Handler - switchport vlan-stacking         :: Command Line Handler - switchport vlan-stacking: Test that port can be set to be a provider's port or a customer's port | step1: E
  - AWP-18371   0.388 [Platform              ] show stack                                              :: Scope: Confirm VCS state(disable/enable). Assertion: | step1: Enter "show stack" command. => Display "%Warning: Stacking is curren
  - AWP-4125    0.388 [z_Inactive            ] EPSR VCS Master, remove stacking hardware.              :: Remove the stacking hardware from the stack and power up standalone device. | step1: Remove stacking hardware. Power up standalone

### AWPTCM-T44318  |  area: AdvancedManagement AMF  |  feature: AMF Master support
folder:/New Platform Template/Advanced Management  steps:1  obj:False
  - AWP-23039   0.403 [ATMF                  ] Change the network name on the AMF masters              :: Change the network name on the AMF masters | step1: change the network name on AMF master to a different one from the existing net
  - AWP-25865   0.383 [ATMF                  ] AMF Links API - Get all AMF links                       :: Web API support for getting all AMF links | step1: Use URL to list all ATMF links including link types and states etc => output sh
  - AWP-25866   0.372 [ATMF                  ] AMF Links API - Getting all AMF virtual links           :: Web API support for getting all AMF virtual links | step1: API support for getting all ATMF virtual links including ID and ip addr
  - AWP-25257   0.370 [ATMF                  ] 1 AMF Virtual crosslink on ATMF master                  :: S2015.1.2 A single AMF Virtual crosslink can be configured on a VAA ATMF master. | step1: On a 300 virtual-links network add 1 amf
  - AWP-25862   0.361 [ATMF                  ] AMF Links API - Delete AMF virtual crosslink            :: Web API support for deleting AMF virtual crosslink | step1: use URL to remove an ATMF virtual crosslink => configuration should be
  - AWP-25867   0.349 [ATMF                  ] AMF Links API - Provision a node on a link              :: Web API support for provisioning a node on a link | step1: API support to provision a node on a link => configuration should be ta
  - AWP-28205   0.341 [ATMF                  ] ATMF Master License Expires                             :: ATMF Master nodes need a license. Test with a license that expires. This may require a creation of an AMF master license that expi
  - AWP-21725   0.336 [ATMF                  ] VAA License: AMF network will automatically reform afte :: It is to be tested that when ATMF master transitions from unlicensed to licensed, the licensed feature will be re-enabled and the 

### AWPTCM-T44319  |  area: AdvancedManagement AMF  |  feature: AMF Member support
folder:/New Platform Template/Advanced Management  steps:1  obj:False
  - AWP-25865   0.372 [ATMF                  ] AMF Links API - Get all AMF links                       :: Web API support for getting all AMF links | step1: Use URL to list all ATMF links including link types and states etc => output sh
  - AWP-25866   0.362 [ATMF                  ] AMF Links API - Getting all AMF virtual links           :: Web API support for getting all AMF virtual links | step1: API support for getting all ATMF virtual links including ID and ip addr
  - AWP-23040   0.362 [ATMF                  ] Change the network name on the AMF members              :: Change the network name on the AMF members | step1: Change the network name on ATMF members to be a different one => Enusre this m
  - AWP-25862   0.351 [ATMF                  ] AMF Links API - Delete AMF virtual crosslink            :: Web API support for deleting AMF virtual crosslink | step1: use URL to remove an ATMF virtual crosslink => configuration should be
  - AWP-25867   0.339 [ATMF                  ] AMF Links API - Provision a node on a link              :: Web API support for provisioning a node on a link | step1: API support to provision a node on a link => configuration should be ta
  - AWP-21260   0.324 [ATMF                  ] ATMF Member Stack - Correct information in AMF database :: It is to be tested that AMF database is not effected by stack reboot. | step1: Change the state of links between Master and differ
  - AWP-25861   0.318 [ATMF                  ] AMF Links API - Create AMF virtual crosslink            :: Web API support for creating AMF virtual cross link | step1: use URL to create an ATMF virtual crosslink => configuration should b
  - AWP-25860   0.317 [ATMF                  ] AMF Links API - Delete AMF virtual vertical link        :: Web API support for deleting AMF virtual vertical link | step1: use URL to remove an ATMF virtual vertical link => configuration s

### AWPTCM-T44320  |  area: AdvancedManagement AMF  |  feature: AMF Controller support
folder:/New Platform Template/Advanced Management  steps:1  obj:False
  - AWP-23041   0.403 [ATMF                  ] Change the network name on the AMF controllers          :: Change the network name on the AMF controllers | step1: Change the network name on the controller to be a different one => Ensure 
  - AWP-21829   0.402 [ATMF                  ] VAA License: VAA will require AMF controller license to :: It is to be tested that VAA will require an AMF virtual controller license to function as an ATMF controller | step1: Run "atmf co
  - AWP-21214   0.398 [ATMF                  ] Link state information for x900 is not added to the Mas :: It is to be tested that Link state information for x900 is not added to AMF Master / Controller database | step1: Execute "apteryx
  - AWP-21216   0.395 [ATMF                  ] Node status information for x900 is not added to Master :: It is to be tested that Node status information for x900 is not added to the Master / Controller AMF database | step1: Execute "ap
  - AWP-21218   0.389 [ATMF                  ] Recovery status information for x900 is not added to th :: It is to be tested that recovery status information for x900 is not added to the Master / Controller AMF database | step1: Execute
  - AWP-18216   0.385 [ATMF                  ] ATMF Controller - Virtual link <-> virtual area link co :: Use virtual link in all AMF connection | step1: Use virtual link in all AMF connection between areas and connection between nodes 
  - AWP-21217   0.366 [ATMF                  ] Node status information for x200 is not added to the Ma :: It is to be tested that Node status information for x200 is not added to the Master / Controller AMF database | step1: Execute "ap
  - AWP-21219   0.361 [ATMF                  ] Recovery status information for x200 is not added to Ma :: It is to be tested that recovery status information for x200 is not added to the Master / Controller AMF database | step1: Execute

### AWPTCM-T44321  |  area: AdvancedManagement AMF  |  feature: AMF API for AMF Vista Manager support
folder:/New Platform Template/Advanced Management  steps:1  obj:False
  - AWP-27324   0.442 [GUI Support           ] ER1749: Vista Manager                                   :: Check Vista Manager can still connect to devices | step1: Check Vista Manager can connect to a member node => Node is shown in top
  - AWP-25865   0.426 [ATMF                  ] AMF Links API - Get all AMF links                       :: Web API support for getting all AMF links | step1: Use URL to list all ATMF links including link types and states etc => output sh
  - AWP-25867   0.417 [ATMF                  ] AMF Links API - Provision a node on a link              :: Web API support for provisioning a node on a link | step1: API support to provision a node on a link => configuration should be ta
  - AWP-24246   0.415 [ATMF                  ] Check Vista Manager will be supported                   :: Check Vista Manager will be supported to the same level as other ATMF master devices | step1: check vista manager will be supporte
  - AWP-25866   0.406 [ATMF                  ] AMF Links API - Getting all AMF virtual links           :: Web API support for getting all AMF virtual links | step1: API support for getting all ATMF virtual links including ID and ip addr
  - AWP-25862   0.401 [ATMF                  ] AMF Links API - Delete AMF virtual crosslink            :: Web API support for deleting AMF virtual crosslink | step1: use URL to remove an ATMF virtual crosslink => configuration should be
  - AWP-9909    0.369 [DHCP Snooping         ] Interop - Windows Vista DHCP Client                     :: Confirm normal operation with Windows Vista DHCP Client | step1: Windows Vista DHCP Client => Expect normal operation
  - AWP-25863   0.365 [ATMF                  ] AMF Links API - Create AMF virtual arealink             :: Web API support for creating AMF virtual arealink | step1: Create AFM virtual area link using API => Link comes up when configured

### AWPTCM-T44322  |  area: AdvancedManagement AMF  |  feature: AMF Edge Node support
folder:/New Platform Template/Advanced Management  steps:1  obj:False
  - AWP-25867   0.410 [ATMF                  ] AMF Links API - Provision a node on a link              :: Web API support for provisioning a node on a link | step1: API support to provision a node on a link => configuration should be ta
  - AWP-18245   0.396 [ATMF                  ] ATMF Controller - non-controller SW as edge nodes       :: Devices running AW+ 5.4.4 can join a controller network and run as a edge nodes. | step1: Use AW+ 5.4.4 devices as edge node => AW
  - AWP-12374   0.389 [ATMF                  ] ATMF Unit Recovery - Recovery of an Edge node device    :: On a ATMF Network, Remove a member node and replace with a "clean" unit. New unit should be automatically reincarnated with the sa
  - AWP-21747   0.361 [ATMF                  ] ATMF Config - Edge node                                 :: ATMF Edge node can have single ATMF link. Cannot be an intermediate node. Only 'switchport atmf-link' can be configured as ATMF li
  - AWP-25868   0.345 [ATMF                  ] AMF Links API - Un-provision a node on a link           :: Web API support for un-provisioning a node on a link | step1: API support for un-provisioning a node on a link => configuration sh
  - AWP-22080   0.338 [ATMF                  ] AMF daemon can obtain the MAC address of any device con :: It is to be tested that AMF daemon can obtain the MAC address of any device connected via a guestlink port | step1: Configure one 
  - AWP-22079   0.337 [ATMF                  ] AMF daemon accepts information for statically configure :: It is to be tested that AMF daemon accepts guest node information for statically configured guest nodes | step1: Configure one of 
  - AWP-22075   0.331 [ATMF                  ] Infrastructure support on Edge devices is enabled by de :: It is to be tested that Infrastructure Support on Edge device is enabled by default however it will be inactive unless guest-links

### AWPTCM-T44323  |  area: AdvancedManagement AMF  |  feature: AMF Guest Node support
folder:/New Platform Template/Advanced Management  steps:1  obj:False
  - AWP-22114   0.493 [ATMF                  ] Binary [on/off] version license for AMF Masters to enab :: It is to be tested that binary [on/off] version license made available for AMF Masters to enable Guest node U.I. support works | s
  - AWP-22303   0.485 [ATMF                  ] the number of Guest Nodes attached to an individual AMF :: As Guest Nodes must be directly connected to a guestlink port, the number of Guest Nodes attached to an individual AMF Node is lim
  - AWP-25867   0.435 [ATMF                  ] AMF Links API - Provision a node on a link              :: Web API support for provisioning a node on a link | step1: API support to provision a node on a link => configuration should be ta
  - AWP-25858   0.424 [ATMF                  ] AMF Links API - Delete AMF guest link on a switchport   :: Web API support for deleting AMF guest link | step1: use URL to remove an ATMF guestlink on individual switchport => configuration
  - AWP-22109   0.417 [ATMF                  ] Modified '<nodename> has left' message on AMF masters t :: It is to be tested that the modified '<nodename> has left' message on AMF masters to log when a guest node has left works | step1:
  - AWP-22079   0.417 [ATMF                  ] AMF daemon accepts information for statically configure :: It is to be tested that AMF daemon accepts guest node information for statically configured guest nodes | step1: Configure one of 
  - AWP-22108   0.410 [ATMF                  ] Modified '<nodename> has joined' message on AMF masters :: It is to be tested that the modified '<nodename> has joined' message on AMF masters to log when a guest node has joined works | st
  - AWP-22082   0.401 [ATMF                  ] Backup of guest node configuration works for TQ devices :: It is to be tested that ATMF will support backup of guest node configuration for TQ devices | step1: Connect guest node to the DUT

### AWPTCM-T44324  |  area: AdvancedManagement AMF  |  feature: AMF APP Proxy
folder:/New Platform Template/Advanced Management  steps:1  obj:False
  - AWP-28197   0.317 [ATMF                  ] AMF Application Proxy on VAA - Delete block entry       :: AMF Application Proxy on VAA - AMF Master running on VAA should be able to Remove or delete block entries for the AMF application-
  - AWP-4354    0.310 [ARP                   ] Proxy ARP: Command                                      :: Test proxy-arp command for errors | step1: Check Proxy ARP commands (any parameter) ip proxy-arp no ip proxy-arp Command must be a
  - AWP-27373   0.307 [ATMF                  ] Application Proxy blocks are NOT removed when AMF Maste :: | step1: Send in multiple ip-filter blocks => Blocks are active.
  - AWP-24347   0.295 [ATMF                  ] Check the 'AMF Application Proxy ' feature can be enabl :: service amfappsd | step1: 1) On ATMF Member check the feature is shown as disabled. Check daemon is not running 2) Turn the featur
  - AWP-24328   0.284 [ATMF                  ] Check the 'AMF Application Proxy' feature is disabled b :: | step1: 1) If any commands exist, check the feature is shown as disabled 2) Check running-config does not contain the command to 
  - AWP-29753   0.279 [AT-SESC               ] AT-SESC - Save the configuration                        :: Confirm that configuration of AMF Application proxy whitelist is saved correctly. | step1: Open "Edit AMF Masters" page from "AMF 
  - AWP-4356    0.267 [ARP                   ] Local Proxy ARP: Command                                :: Test "ip local-proxy-arp" command | step1: Check Local Proxy ARP commands (any parameter) Command must be accepted and shown in co
  - AWP-30012   0.266 [AT-SESC               ] AT-SESC - Roaming - Deny - Other AMF Member             :: Confirm that Application Proxy Whitelist works correctly even if roam the device. | step1: Connect the unregistered device and sta

### AWPTCM-T44325  |  area: AdvancedManagement AMF  |  feature: AMF APP Proxy
folder:/New Platform Template/Advanced Management  steps:1  obj:False
  - AWP-28197   0.317 [ATMF                  ] AMF Application Proxy on VAA - Delete block entry       :: AMF Application Proxy on VAA - AMF Master running on VAA should be able to Remove or delete block entries for the AMF application-
  - AWP-4354    0.310 [ARP                   ] Proxy ARP: Command                                      :: Test proxy-arp command for errors | step1: Check Proxy ARP commands (any parameter) ip proxy-arp no ip proxy-arp Command must be a
  - AWP-27373   0.307 [ATMF                  ] Application Proxy blocks are NOT removed when AMF Maste :: | step1: Send in multiple ip-filter blocks => Blocks are active.
  - AWP-24347   0.295 [ATMF                  ] Check the 'AMF Application Proxy ' feature can be enabl :: service amfappsd | step1: 1) On ATMF Member check the feature is shown as disabled. Check daemon is not running 2) Turn the featur
  - AWP-24328   0.284 [ATMF                  ] Check the 'AMF Application Proxy' feature is disabled b :: | step1: 1) If any commands exist, check the feature is shown as disabled 2) Check running-config does not contain the command to 
  - AWP-29753   0.279 [AT-SESC               ] AT-SESC - Save the configuration                        :: Confirm that configuration of AMF Application proxy whitelist is saved correctly. | step1: Open "Edit AMF Masters" page from "AMF 
  - AWP-4356    0.267 [ARP                   ] Local Proxy ARP: Command                                :: Test "ip local-proxy-arp" command | step1: Check Local Proxy ARP commands (any parameter) Command must be accepted and shown in co
  - AWP-30012   0.266 [AT-SESC               ] AT-SESC - Roaming - Deny - Other AMF Member             :: Confirm that Application Proxy Whitelist works correctly even if roam the device. | step1: Connect the unregistered device and sta

### AWPTCM-T44326  |  area: AdvancedManagement Vista/AWC  |  feature: Vista mini support
folder:/New Platform Template/Advanced Management  steps:1  obj:False
  - AWP-9909    0.502 [DHCP Snooping         ] Interop - Windows Vista DHCP Client                     :: Confirm normal operation with Windows Vista DHCP Client | step1: Windows Vista DHCP Client => Expect normal operation
  - AWP-27324   0.474 [GUI Support           ] ER1749: Vista Manager                                   :: Check Vista Manager can still connect to devices | step1: Check Vista Manager can connect to a member node => Node is shown in top
  - AWP-24246   0.445 [ATMF                  ] Check Vista Manager will be supported                   :: Check Vista Manager will be supported to the same level as other ATMF master devices | step1: check vista manager will be supporte
  - AWP-25747   0.364 [Web Control           ] Web-Control: SNI filtering compatibility with Vista Man :: Web-Control permit rules must be able to allow Vista Manager HTTPS traffic to pass through Web-Control. Vista Manger uses some HTT
  - AWP-26922   0.315 [GUI Support           ] Vista Manager Notifications                             :: | step1: Notify VM when master receives a request for config
  - AWP-29018   0.218 [AWC-lite              ] AWC with vlan routing                                   :: | step1: Connect AP to the switch,and start to capture between AP and the switch. => AP should be Managed status under routing env
  - AWP-29704   0.212 [5.4.8-2 Development   ] cb-config with wpa-enterprise                           :: Confirm channel blanket with wpa-enterprise security will work correctly. S2199.1.10 When pre-authentication in wpa-enterprise is 
  - AWP-29146   0.201 [AWC-lite              ] Multiple Master failover                                :: In 5.4.8-2, bulk sync support on AWC VCS. Confirm that if multiple failover occrs at same time, AWC data will be takebn over befor

### AWPTCM-T44327  |  area: AdvancedManagement Vista/AWC  |  feature: AWC Wireless Controller
folder:/New Platform Template/Advanced Management  steps:1  obj:False
  - AWP-29018   0.356 [AWC-lite              ] AWC with vlan routing                                   :: | step1: Connect AP to the switch,and start to capture between AP and the switch. => AP should be Managed status under routing env
  - AWP-29030   0.341 [AWC-lite              ] Check AWC task after slave failover                     :: Confirm AWC task will work correctly after slave failover | step1: Check the status and perform slave failover after saving config
  - AWP-29024   0.334 [AWC-lite              ] Check AWC task after master failover                    :: Confirm AWC task will work correctly after master failover | step1: Check the status and perform master failover with power-off af
  - AWP-27275   0.306 [AWC-lite              ] 10.3 Repeat AWC calculation and apply per 10 minutes.   :: | step1: Confirm that crash do not occur on router.
  - AWP-27250   0.306 [AWC-lite              ] 7.3.1 Delete task of apply AWC calculation result       :: | step1: Confirm that user can delete task to apply AWC calculation result.
  - AWP-27268   0.305 [AWC-lite              ] 5.7 Execute AWC calculation repeatedly in short interva :: | step1: Confirm that all AWC calculation result are displayed and memory leak do not occur when user execute manual AWC calculat
  - AWP-9909    0.302 [DHCP Snooping         ] Interop - Windows Vista DHCP Client                     :: Confirm normal operation with Windows Vista DHCP Client | step1: Windows Vista DHCP Client => Expect normal operation
  - AWP-28930   0.301 [AWC-lite              ] Failed to get hwtype                                    :: If wireless controller failed to get hwtype for an AP in the session, wireless controller skips the AP and starts to get next AP h

### AWPTCM-T44328  |  area: AdvancedManagement Vista/AWC  |  feature: AWC-CB Channel Blanket
folder:/New Platform Template/Advanced Management  steps:1  obj:False
  - AWP-29724   0.500 [5.4.8-2 Development   ] mac filter and cb-config                                :: Confirm ap-profile that has mac filter and cb-config will be applied to AP correctly | step1: Then check the status in show comman
  - AWP-29684   0.463 [5.4.8-2 Development   ] Reset channel-blanket configuration                     :: Confirm when configured cb-profile, each parameter will become reset after inputting "no channel-blanket" command S2199.1.16 "no" 
  - AWP-29671   0.445 [5.4.8-2 Development   ] channel-blanket                                         :: S2199.1.14 Confirm channel-blanket command will be accepted and move to #config-wireless-ap-prof-cb mode S2199.1.1 It can enter co
  - AWP-29713   0.431 [5.4.8-2 Development   ] max APs with cb-config                                  :: Confirm channel blanket will be formed correctly when configure 100 APs with cb-config Note 100 APs with cb-config are supported a
  - AWP-29704   0.401 [5.4.8-2 Development   ] cb-config with wpa-enterprise                           :: Confirm channel blanket with wpa-enterprise security will work correctly. S2199.1.10 When pre-authentication in wpa-enterprise is 
  - AWP-29677   0.394 [5.4.8-2 Development   ] cb-channel radio [1|2|3] channel CHANNELS               :: S2199.1.28 Confirm "cb-channel radio [1|2|3] channel CHANNELS" command will be accepted S2199.1.13 It can configure CB mode to rad
  - AWP-29681   0.389 [5.4.8-2 Development   ] channel-blanket command in show tech                    :: S2199.4.1 S2199.4.2 Confirm tech support will include show wireless channel-blanket ap status command and show wireless channel-bl
  - AWP-29672   0.381 [5.4.8-2 Development   ] control-vlan <1-4094>                                   :: S2199.1.17 Confirm control-vlan command will be accepted | step1: Input help command or tab in config-wireless-ap-prof-cb mode awp

### AWPTCM-T44329  |  area: AdvancedManagement Vista/AWC  |  feature: AWC-SC Smart Connect
folder:/New Platform Template/Advanced Management  steps:1  obj:False
  - AWP-29018   0.301 [AWC-lite              ] AWC with vlan routing                                   :: | step1: Connect AP to the switch,and start to capture between AP and the switch. => AP should be Managed status under routing env
  - AWP-27324   0.254 [GUI Support           ] ER1749: Vista Manager                                   :: Check Vista Manager can still connect to devices | step1: Check Vista Manager can connect to a member node => Node is shown in top
  - AWP-29126   0.236 [AWC-lite              ] AWC calculation with vlan routing                       :: | step1: Connect AP to the switch => AP should be Managed status under routing environment.
  - AWP-27275   0.233 [AWC-lite              ] 10.3 Repeat AWC calculation and apply per 10 minutes.   :: | step1: Confirm that crash do not occur on router.
  - AWP-27250   0.233 [AWC-lite              ] 7.3.1 Delete task of apply AWC calculation result       :: | step1: Confirm that user can delete task to apply AWC calculation result.
  - AWP-27268   0.232 [AWC-lite              ] 5.7 Execute AWC calculation repeatedly in short interva :: | step1: Confirm that all AWC calculation result are displayed and memory leak do not occur when user execute manual AWC calculat
  - AWP-9909    0.230 [DHCP Snooping         ] Interop - Windows Vista DHCP Client                     :: Confirm normal operation with Windows Vista DHCP Client | step1: Windows Vista DHCP Client => Expect normal operation
  - AWP-22050   0.225 [Hardware Health Monito] ER-528 - CLI - 'no/system hw-monitoring shutdown smart- :: Verify that command can only be executed in the correct mode, CLI help and tab works, valid parameters are accepted, and invalid p

### AWPTCM-T44330  |  area: AdvancedManagement AMFSec  |  feature: AMF Sec
folder:/New Platform Template/Advanced Management  steps:1  obj:False
  - AWP-25865   0.269 [ATMF                  ] AMF Links API - Get all AMF links                       :: Web API support for getting all AMF links | step1: Use URL to list all ATMF links including link types and states etc => output sh
  - AWP-23039   0.258 [ATMF                  ] Change the network name on the AMF masters              :: Change the network name on the AMF masters | step1: change the network name on AMF master to a different one from the existing net
  - AWP-25862   0.254 [ATMF                  ] AMF Links API - Delete AMF virtual crosslink            :: Web API support for deleting AMF virtual crosslink | step1: use URL to remove an ATMF virtual crosslink => configuration should be
  - AWP-16281   0.248 [PPPoE Client          ] PPPoE - Momentarily Disconnecting the WAN Cable (2.5 Se :: To confirm that the router operates normally when the WAN cable is momentarily (2.5 sec or more) disconnected. | step1: Cable disc
  - AWP-29195   0.244 [5.4.8-2 Development   ] Setting "dynamic-vlan"                                  :: Confirm Dynamic-vlan configured S2149.10.1 Set enable/disable dynamic-vlan function. | step1: enable (config-wireless-sec-wpa-ent)
  - AWP-24166   0.242 [ATMF                  ] Check The eth0 interface will be automatically configur :: Check The eth0 interface will be automatically configured as an AMF area-link | step1: check eth0 interface will be automatically 
  - AWP-28920   0.241 [AWC-lite              ] Maximum auto-config session time                        :: x908Gen2 supports up to 125 AP, and AR4050S supports up to 25 AP and the other supports 5 up to AP. Each session takes the followi
  - AWP-29294   0.240 [5.4.8-2 Development   ] Security-mode WEP                                       :: Confirm that security-mode WEP setting refrect to AP. | step1: Change security 1 to wep. (config-wireless)# security 1 mode wep (c

### AWPTCM-T44331  |  area: AdvancedManagement AMFSec  |  feature: Openflow v1.3
folder:/New Platform Template/Advanced Management  steps:1  obj:False
  - AWP-29551   0.468 [OpenFlow              ] OpenFlow packet version                                 :: Check the version of OpenFlow packet is "v1.3". | step1: Set up the environment of preconditions.
  - AWP-29444   0.468 [OpenFlow              ] OpenFlow packet version                                 :: Check the version of OpenFlow packet is "v1.3". | step1: Set up the environment of preconditions.
  - AWP-23203   0.468 [OpenFlow              ] OpenFlow packet version                                 :: Check the version of OpenFlow packet is "v1.3". | step1: Set up the environment of preconditions.
  - AWP-26471   0.468 [OpenFlow              ] OpenFlow packet version                                 :: Check the version of OpenFlow packet is "v1.3". | step1: Set up the environment of preconditions.
  - AWP-1114    0.368 [NTP                   ] Test with v1 NTP                                        :: Test with v1 NTP | step1: ntp peer xxx.xxx.xxx.xxx prefer VERSION 1 Issue sh ntp status command => Times on Linux PC and DUT must 
  - AWP-12917   0.367 [MLD                   ] MLDv2 interop with v1 host                              :: MLDv2 interop with v1 host | step1: Device with ipv6 mld enabled (default v2) Send in v1 report Send in v1 done => Command accepte
  - AWP-6496    0.325 [SSH                   ] SSH server version 1 - remote client using v1.5 can log :: SSH Server Tests Verify that SSH remote client using SSHv1.5 can login successfully in SSHv1 Server(DUT) | step1: ssh server set t
  - AWP-6498    0.323 [SSH                   ] SSH version 2 - login fails if remote client is using v :: SSH Server Tests Verify that a client using SSHv1 fails to login to a Version 2 SSH server (DUT) | step1: ssh server set to versio

### AWPTCM-T44332  |  area: AdvancedManagement AMFSec  |  feature: Openflow Connection Interruption
folder:/New Platform Template/Advanced Management  steps:1  obj:False
  - AWP-25844   0.451 [OpenFlow              ] Connection Interruption - Secure Mode                   :: Confirm that Secure Mode works correctly after disconnecting SESC. | step1: Execute "show run" and "show openflow config". => Conf
  - AWP-26623   0.451 [OpenFlow              ] Connection Interruption - Secure Mode                   :: Confirm that Secure Mode works correctly after disconnecting SESC. | step1: Execute "show run" and "show openflow config". => Conf
  - AWP-29526   0.423 [OpenFlow              ] Connection Interruption - Longrun with traffic          :: Confirm that Secure Mode with non-rule-expired option works correctly after disconnecting SESC. Change Hard Timeout to 300 secocnd
  - AWP-28243   0.423 [OpenFlow              ] Connection Interruption - Longrun with traffic          :: Confirm that Secure Mode with non-rule-expired option works correctly after disconnecting SESC. Change Hard Timeout to 300 secocnd
  - AWP-28214   0.423 [OpenFlow              ] Connection Interruption - Longrun with traffic          :: Confirm that Secure Mode with non-rule-expired option works correctly after disconnecting SESC. Change Hard Timeout to 300 secocnd
  - AWP-29665   0.401 [OpenFlow              ] Connection Interruption - Secure Mode                   :: Confirm that Secure Mode works correctly after disconnecting SESC. | step1: Execute "show run" and "show openflow config". => Conf
  - AWP-28241   0.401 [OpenFlow              ] Connection Interruption - Secure Mode                   :: Confirm that Secure Mode works correctly after disconnecting SESC. | step1: Execute "show run" and "show openflow config". => Conf
  - AWP-28203   0.401 [OpenFlow              ] Connection Interruption - Secure Mode                   :: Confirm that Secure Mode works correctly after disconnecting SESC. | step1: Execute "show run" and "show openflow config". => Conf

### AWPTCM-T44333  |  area: AdvancedManagement AMFSec  |  feature: Openflow Connection Interruption - non rule expiry option
folder:/New Platform Template/Advanced Management  steps:1  obj:False
  - AWP-29526   0.437 [OpenFlow              ] Connection Interruption - Longrun with traffic          :: Confirm that Secure Mode with non-rule-expired option works correctly after disconnecting SESC. Change Hard Timeout to 300 secocnd
  - AWP-28243   0.437 [OpenFlow              ] Connection Interruption - Longrun with traffic          :: Confirm that Secure Mode with non-rule-expired option works correctly after disconnecting SESC. Change Hard Timeout to 300 secocnd
  - AWP-28214   0.437 [OpenFlow              ] Connection Interruption - Longrun with traffic          :: Confirm that Secure Mode with non-rule-expired option works correctly after disconnecting SESC. Change Hard Timeout to 300 secocnd
  - AWP-29525   0.434 [OpenFlow              ] Connection Interruption - Secure mode with non-rule-exp :: Confirm that Secure Mode with non-rule-expired option works correctly after disconnecting SESC. | step1: Execute "show run" and "s
  - AWP-28242   0.434 [OpenFlow              ] Connection Interruption - Secure mode with non-rule-exp :: Confirm that Secure Mode with non-rule-expired option works correctly after disconnecting SESC. | step1: Execute "show run" and "s
  - AWP-28204   0.434 [OpenFlow              ] Connection Interruption - Secure mode with non-rule-exp :: Confirm that Secure Mode with non-rule-expired option works correctly after disconnecting SESC. | step1: Execute "show run" and "s
  - AWP-29527   0.412 [OpenFlow              ] Connection Interruption - Longrun without traffic       :: Confirm that Secure Mode with non-rule-expired option works correctly after disconnecting SESC. Change Hard Timeout to 300 secocnd
  - AWP-28244   0.412 [OpenFlow              ] Connection Interruption - Longrun without traffic       :: Confirm that Secure Mode with non-rule-expired option works correctly after disconnecting SESC. Change Hard Timeout to 300 secocnd
