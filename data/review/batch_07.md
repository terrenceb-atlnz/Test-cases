# Rerank batch 07  (cases 210..239)

### AWPTCM-T44202  |  area: IPv6 MilticastRouting  |  feature: PIM-SMv6
folder:/New Platform Template/IPv6  steps:1  obj:False
  - AWP-12456   0.461 [PIM-SMv6              ] VCS and EPSR and PIM-SMv6                               :: Check that when the stack acts as RP, all traffic recovers when slave joins after slave failover. | step1: 1. Configure EPSR and P
  - AWP-13016   0.393 [PIM-SMv6              ] PIM-SMv6 Bootstrap Message (BSM) analysis               :: Configure different interfaces on a PIM domain as BR candidates. Confirm BSMs are sent and processed correctly among the PIM route
  - AWP-13019   0.376 [PIM-SMv6              ] Show command for BSR                                    :: Run show commands for BSR details and verify the results. | step1: Configure PIM-SMv6 => n/a
  - AWP-13665   0.349 [PIM-SMv6              ] Disable - Enable ipv6 multicast routing                 :: Multicast traffic should recover upon disabling and reenabling ipv6 multicast-routing | step1: Setup a working PIM-SMv6 network. S
  - AWP-13017   0.325 [PIM-SMv6              ] PIM-SMv6 Bootstrap Message (BSM) with different priorit :: Configure BSR candidates with different priorites and analyze if the correct candidate is selected as the BSR Hash Mask length is 
  - AWP-13325   0.271 [PIM-SMv6              ] CLI - PIM sparse-mode                                   :: cli to test pim sparse-mode command | step1: ipv6 multicast-routing ! int vlan1 ipv6 pim sparse-mode Attempt to enable on multiple
  - AWP-18477   0.244 [PIM-SSMv6             ] Native group range                                      :: Test joining multicast groups in the default range (ff3x::/12 - x = scope) Check only (S,G) entries are created in PIM-SMv6 TIB (s
  - AWP-18480   0.234 [PIM-SSMv6             ] Custom group range                                      :: Test joining multicast groups in a custom range defined by the user. Check only (S,G) entries are created in PIM-SMv6 TIB (show ip

### AWPTCM-T44203  |  area: IPv6 MilticastRouting  |  feature: PIM-DMv6
folder:/New Platform Template/IPv6  steps:1  obj:False
  - AWP-13325   0.515 [PIM-SMv6              ] CLI - PIM sparse-mode                                   :: cli to test pim sparse-mode command | step1: ipv6 multicast-routing ! int vlan1 ipv6 pim sparse-mode Attempt to enable on multiple
  - AWP-5063    0.424 [z_Inactive            ] PIM Forwarding routes (groups)                          :: N/A | step1: Same as test 9.8 => Same as test 9.9
  - AWP-10322   0.411 [PIM-SSM               ] PIM-SSM and LAG                                         :: Verify the behaviour of PIM-SSM with LAG | step1: Configure PIM-SSM with LAG => Multicast packet joined the correct source
  - AWP-4476    0.392 [PIM-SM                ] CLI to check ip pim sparse-mode                         :: Command Line test | step1: 1. Login to DUT. 2. Execute the command in interface mode: - (no) ip pim sparse-mode => Command should 
  - AWP-17873   0.383 [PIM-DM                ] PIM-DM End-to-end test                                  :: PIM-DM works as expected | step1: Setup a PIM-DM => Multicast client able to get multicast stream
  - AWP-11500   0.379 [z_Inactive            ] Max PIM interfaces (PIM 100 license applied)            :: Duplicate of limits test: bugsearch/testlink/linkto.php With PIM 100 license applied, device allows 100 pim interfaces | step1: lo
  - AWP-7005    0.375 [Software Licensing    ] License - 100-PIM - 100 sparse PIM interfaces accepted  :: License - 100-PIM - 100 sparse PIM interfaces accepted | step1: Confirm that the 100-PIM license displays PIM-100 with 'show licen
  - AWP-3499    0.374 [PIM-SM                ] CLI to set ip pim rp-address                            :: Command Line test | step1: Issue ip pim rp-address <ip-address> on the global config mode. => Changes reflect in sh run.

### AWPTCM-T44204  |  area: IPv6 MilticastRouting  |  feature: PIM-SSMv6
folder:/New Platform Template/IPv6  steps:1  obj:False
  - AWP-18480   0.268 [PIM-SSMv6             ] Custom group range                                      :: Test joining multicast groups in a custom range defined by the user. Check only (S,G) entries are created in PIM-SMv6 TIB (show ip
  - AWP-13325   0.251 [PIM-SMv6              ] CLI - PIM sparse-mode                                   :: cli to test pim sparse-mode command | step1: ipv6 multicast-routing ! int vlan1 ipv6 pim sparse-mode Attempt to enable on multiple
  - AWP-18477   0.225 [PIM-SSMv6             ] Native group range                                      :: Test joining multicast groups in the default range (ff3x::/12 - x = scope) Check only (S,G) entries are created in PIM-SMv6 TIB (s
  - AWP-18481   0.223 [PIM-SSMv6             ] Native group range using MLD SSM static mapping         :: Test joining multicast groups in the default range (ff3x::/12 - x = scope). Test using MLDv1 joins for the ff3x::/12 range. Check 
  - AWP-5063    0.207 [z_Inactive            ] PIM Forwarding routes (groups)                          :: N/A | step1: Same as test 9.8 => Same as test 9.9
  - AWP-10322   0.201 [PIM-SSM               ] PIM-SSM and LAG                                         :: Verify the behaviour of PIM-SSM with LAG | step1: Configure PIM-SSM with LAG => Multicast packet joined the correct source
  - AWP-4476    0.191 [PIM-SM                ] CLI to check ip pim sparse-mode                         :: Command Line test | step1: 1. Login to DUT. 2. Execute the command in interface mode: - (no) ip pim sparse-mode => Command should 
  - AWP-17873   0.186 [PIM-DM                ] PIM-DM End-to-end test                                  :: PIM-DM works as expected | step1: Setup a PIM-DM => Multicast client able to get multicast stream

### AWPTCM-T44205  |  area: IPv6 SNMP  |  feature: SNMPv1
folder:/New Platform Template/IPv6  steps:1  obj:True
ZEPHYR: OBJ: Access DUT via SNMP Manager with a SNMPv1 specified access || Access DUT via SNMP Manager with a SNMPv1 specified access.
  - AWP-1232    0.982 [SNMP                  ] SNMPv1-Access                                           :: Access DUT via SNMP Manager with a SNMPv1 specified access | step1: Access DUT via SNMP Manager with a SNMPv1 specified access. Co
  - AWP-1233    0.835 [SNMP                  ] SNMPv1-Access-VCS                                       :: Access DUT via SNMP Manager with a SNMPv1 specified access, where DUT is a VCS stack. Set up DUT as VCS stack (max supported for m
  - AWP-1234    0.769 [SNMP                  ] SNMPv2c-Access                                          :: Access DUT via SNMP Manager with a SNMPv2c specified access | step1: Access DUT via SNMP Manager with a SNMPv2c specified access. 
  - AWP-1237    0.662 [SNMP                  ] SNMPv3-Access-Authentication only                       :: SNMPv3 Access Test With authentication but with no privacy. | step1: Access DUT via SNMP Manager with a SNMPv3 specified access. W
  - AWP-1235    0.658 [SNMP                  ] SNMPv2c-Access-VCS                                      :: Access DUT via SNMP Manager with a SNMPv2c specified access, where DUT is a VCS stack. Set up DUT as VCS stack (max supported for 
  - AWP-1238    0.640 [SNMP                  ] SNMPv3-Access-Authentication and Privacy                :: SNMPv3 Access Test With authentication and privacy | step1: Access DUT via SNMP Manager with a SNMPv3 specified access. With authe
  - AWP-1236    0.628 [SNMP                  ] SNMPv3-Access-No Authentication or Privacy              :: SNMPv3 Access Test With no authentication and no privacy | step1: Access DUT via SNMP Manager with a SNMPv3 specified access. With
  - AWP-1240    0.582 [SNMP                  ] VCS-SNMPv3-Access-Authentication only                   :: SNMPv3 Access Test With authentication but with no privacy, where DUT is a VCS stack. Set up DUT as VCS stack (max supported for m

### AWPTCM-T44206  |  area: IPv6 SNMP  |  feature: SNMPv2c
folder:/New Platform Template/IPv6  steps:1  obj:True
ZEPHYR: OBJ: Access DUT via SNMP Manager with a SNMPv2c specified access || Access DUT via SNMP Manager with a SNMPv2c specified access.
  - AWP-1234    0.983 [SNMP                  ] SNMPv2c-Access                                          :: Access DUT via SNMP Manager with a SNMPv2c specified access | step1: Access DUT via SNMP Manager with a SNMPv2c specified access. 
  - AWP-1235    0.840 [SNMP                  ] SNMPv2c-Access-VCS                                      :: Access DUT via SNMP Manager with a SNMPv2c specified access, where DUT is a VCS stack. Set up DUT as VCS stack (max supported for 
  - AWP-1232    0.767 [SNMP                  ] SNMPv1-Access                                           :: Access DUT via SNMP Manager with a SNMPv1 specified access | step1: Access DUT via SNMP Manager with a SNMPv1 specified access. Co
  - AWP-1233    0.652 [SNMP                  ] SNMPv1-Access-VCS                                       :: Access DUT via SNMP Manager with a SNMPv1 specified access, where DUT is a VCS stack. Set up DUT as VCS stack (max supported for m
  - AWP-1237    0.646 [SNMP                  ] SNMPv3-Access-Authentication only                       :: SNMPv3 Access Test With authentication but with no privacy. | step1: Access DUT via SNMP Manager with a SNMPv3 specified access. W
  - AWP-1238    0.624 [SNMP                  ] SNMPv3-Access-Authentication and Privacy                :: SNMPv3 Access Test With authentication and privacy | step1: Access DUT via SNMP Manager with a SNMPv3 specified access. With authe
  - AWP-1236    0.613 [SNMP                  ] SNMPv3-Access-No Authentication or Privacy              :: SNMPv3 Access Test With no authentication and no privacy | step1: Access DUT via SNMP Manager with a SNMPv3 specified access. With
  - AWP-1240    0.568 [SNMP                  ] VCS-SNMPv3-Access-Authentication only                   :: SNMPv3 Access Test With authentication but with no privacy, where DUT is a VCS stack. Set up DUT as VCS stack (max supported for m

### AWPTCM-T44207  |  area: IPv6  |  feature: MLDv1/v2
folder:/New Platform Template/IPv6  steps:1  obj:False
  - AWP-8422    0.561 [MLD Snooping          ] Send in an MLDv1 report for a different group           :: | step1: Send in an MLDv1 report for a different group => Should be forwarded to mrouter port as MLDv1 message and groups should b
  - AWP-8430    0.561 [MLD Snooping          ] Send MLDv1 report for a different group                 :: | step1: Send in an MLDv1 report for a different group => Should be forwarded to mrouter port as MLDv1 message and groups should b
  - AWP-8419    0.515 [MLD Snooping          ] Send MLDv1 Report for the group created                 :: | step1: Send MLDv1 Report for the group created above => Should be forwarded to mrouter port as an MLDv2 message with source addr
  - AWP-12452   0.406 [PIM-SMv6              ] Negative test of Source Specific Multicast using MLDv1  :: Tests Source specific should only work for MLDv2 packets | step1: Same test setup as AW+_3503 but try joining from MLD v1 packet =
  - AWP-12755   0.374 [MLD                   ] Stress Test - MLDv1 send large number of Reports and Le :: MLDv1 send large number of Reports and Leave over extended period. | step1: 1.Set up the DUT. 2.Send large number of Reports and L
  - AWP-12678   0.239 [MLD                   ] Standard Test - Group membership registered with v2 Rep :: Group membership registered with v2 Report with multiple group | step1: 1. Enable MLD on VLAN interface. 2. Send different MLD v2 
  - AWP-12677   0.232 [MLD                   ] Standard Test - Group membership registered with Source :: Group membership registered with Source-specific v2 Report | step1: 1. Enable MLD on VLAN interface 2. Send MLD Source-specific v2
  - AWP-1115    0.228 [NTP                   ] Test with v2 NTP                                        :: Test with v2 NTP | step1: ntp peer xxx.xxx.xxx.xxx prefer version 2 Issue sh ntp status command => Times on Linux PC and DUT must 

### AWPTCM-T44208  |  area: IPv6  |  feature: MLD v1 Snooping
folder:/New Platform Template/IPv6  steps:1  obj:False
  - AWP-8375    0.568 [MLD Snooping          ] Logging for MLD snooping                                :: | step1: Logging exists for MLD Snooping
  - AWP-6414    0.554 [L2 Switching (L2 Learn] MLD                                                     :: MLD | step1: MLD => MLD
  - AWP-8360    0.538 [MLD Snooping          ] Command Line Handler - (no) ipv6 mld snooping           :: | step1: Command Handler: ipv6 mld snooping => Configured Globally/Per Vlan
  - AWP-8362    0.531 [MLD Snooping          ] Command Line Handler - (no) ipv6 mld snooping interface :: | step1: Command Handler: ipv6 mld snooping interface [vlan/port/static/LACP]
  - AWP-8384    0.516 [MLD Snooping          ] MLD Snooping counter with valid packets                 :: | step1: MLD Snooping counter operation check with valid packets
  - AWP-8385    0.511 [MLD Snooping          ] MLD Snooping counter with invalid packets               :: | step1: MLD Snooping counter operation check with invalid packets
  - AWP-8391    0.502 [MLD Snooping          ] MLD Snooping - ipv6 mld access-group                    :: Create an ACL to block a multicast group | step1: Create an ACL to block a particular multicast group => Group should not be forwa
  - AWP-8402    0.502 [MLD Snooping          ] MLD Snooping Interop with IGMP Snooping                 :: | step1: Ensure that both IGMP Snooping and MLD Snooping can operate independently of one another

### AWPTCM-T44209  |  area: IPv6  |  feature: IPv6 Ready Logo
folder:/New Platform Template/IPv6  steps:1  obj:False
  - AWP-18298   0.445 [Web Authentication    ] auth-web-server page logo                               :: auth-web-server page logo (auto/default/hidden) command is configured correctly. Also, all of parameter remain after rebooted. | s
  - AWP-18320   0.442 [Web Authentication    ] WEB authentication change page logo                     :: Confirm that WEB authentication works correctly when web-auth page change logo. | step1: Send a logo file(X.gif) to flash. => Conf
  - AWP-5795    0.180 [IPv6                  ] Check IPV6 forwarding                                   :: Test for show command when ipv6 forwarding is enabled | step1: awplus#show ipv6 forwarding => "ipv6 forwarding is on" when ipv6 fo
  - AWP-19365   0.153 [Wireless controller (U] Redundancy performance_VCS master fail over             :: Measure the time from VCS master start rebooting to finish booting. reboot(y) ~ login prompt is displayed Target: x930, SBx908, SB
  - AWP-19863   0.153 [Wireless controller (U] Redundancy performance_VCS master fail over             :: Measure the time from VCS master start rebooting to finish booting. reboot(y) ~ login prompt is displayed Target: x930, SBx908, SB
  - AWP-20559   0.152 [Wireless controller (U] Redundancy performance_VCS master fail over             :: Measure the time from VCS master start rebooting to finish booting. reboot(y) ~ login prompt is displayed Target: x930, SBx908, SB
  - AWP-10069   0.143 [IPv6                  ] Remove IPv6                                             :: Able to remove IPv6 from interface and check for memory leaks | step1: remove IPv6 from interface => - full tables, check for memo
  - AWP-24173   0.140 [ATMF                  ] Check Ping (IPv4 and IPv6) will be supported            :: Check Ping (IPv4 and IPv6) will be supported | step1: Check Ping (IPv4 and IPv6) will be supported => confirm Ping (IPv4 and IPv6)

### AWPTCM-T44210  |  area: IPv6  |  feature: QoS for IPv6 traffic
folder:/New Platform Template/IPv6  steps:1  obj:False
  - AWP-10099   0.480 [IPv6                  ] IPv6 Address - QoS field works                          :: QoS output should reflect input QoS field | step1: QOS field works - output queue reflects input QoS field => Output queue reflect
  - AWP-9065    0.406 [QoS                   ] QoS globally enabled                                    :: Verify QoS commands are accepted when QoS is globally enabled | step1: qos can be enabled with the command: mls qos enable => Sele
  - AWP-21494   0.402 [ACL                   ] Large IPv6 ACL group with max QoS utilization           :: Large extended ACL group should not affect QoS utilization | step1: 1. Fill-up QoS and ACL table Check "sh platform classifier sta
  - AWP-7627    0.380 [Policy Based Routing  ] QoS configuration applied to the classified traffic     :: Confirm that QoS continue to function and not affected by PBR | step1: QoS configuration (eg. set commands under policy map) can b
  - AWP-8694    0.334 [ACL                   ] ACL:Named IPv6 Hardware on static LAG - IP with Mac     :: ACL:Named IPv6 Hardware on static LAG - IP | step1: A number of different ACLs probably required to cover this test case. Apply AC
  - AWP-8679    0.321 [ACL                   ] ACL:Named IPv6 Hardware on port - Proto                 :: ACL:Named IPv6 Hardware on port - Proto | step1: Apply ACL via interface Access-group - specify IP Protocol numbers. Transmit IPv6
  - AWP-8697    0.317 [ACL                   ] ACL: Named IPv6 Hardware on static LAG - mac with vlan  :: ACL: Named IPv6 Hardware on static LAG - mac with vlan | step1: Apply ACL via interface ipv6 traffic-filter - specify vlan. Specif
  - AWP-8692    0.312 [ACL                   ] ACL:Named IPv6 Hardware on static LAG - IP              :: ACL:Named IPv6 Hardware on static LAG - IP | step1: Apply ACL to static LAG via interface Access-group - specify src/dest host & w

### AWPTCM-T44211  |  area: IPv6  |  feature: ACL for IPv6 traffic
folder:/New Platform Template/IPv6  steps:1  obj:False
  - AWP-8435    0.602 [MLD Snooping          ] IPv6 ACL's to send packets to the CPU                   :: | step1: Create IPv6 ACL's to send packets to the CPU => Multicast traffic should still work
  - AWP-8175    0.445 [z_Inactive            ] Security: Block tunnel destination or source through IP :: Confirm that no traffic from host when tunnel destination or source is blocked using IPv6 ACL | step1: Block certian tunnel destin
  - AWP-8608    0.404 [ACL                   ] ACL: IPv6 Hardware - Command Handler                    :: ACL: IPv6 Hardware - Command Handler | step1: Check command handler for IPv6 hardware ACL Command execution (ranges) Negation of c
  - AWP-8694    0.399 [ACL                   ] ACL:Named IPv6 Hardware on static LAG - IP with Mac     :: ACL:Named IPv6 Hardware on static LAG - IP | step1: A number of different ACLs probably required to cover this test case. Apply AC
  - AWP-8679    0.383 [ACL                   ] ACL:Named IPv6 Hardware on port - Proto                 :: ACL:Named IPv6 Hardware on port - Proto | step1: Apply ACL via interface Access-group - specify IP Protocol numbers. Transmit IPv6
  - AWP-8697    0.381 [ACL                   ] ACL: Named IPv6 Hardware on static LAG - mac with vlan  :: ACL: Named IPv6 Hardware on static LAG - mac with vlan | step1: Apply ACL via interface ipv6 traffic-filter - specify vlan. Specif
  - AWP-8692    0.374 [ACL                   ] ACL:Named IPv6 Hardware on static LAG - IP              :: ACL:Named IPv6 Hardware on static LAG - IP | step1: Apply ACL to static LAG via interface Access-group - specify src/dest host & w
  - AWP-8676    0.371 [ACL                   ] ACL:Named IPv6 Hardware on port - IP                    :: ACL:Named IPv6 Hardware on port - IP | step1: Apply ACL via interface Access-group - specify src/dest host & with and without vlan

### AWPTCM-T44212  |  area: (obsoleted) Switching  |  feature: BFD
folder:/New Platform Template/Switching  steps:3  obj:True
ZEPHYR: OBJ: Determine behaviour when interoperating BFD with port mirroring || Ensure BFD packets are mirrored correctly | Attempt to configure BFD on port1.1.3 on DUT2 | unconfigure port mirroring on port1.
  - AWP-4992    0.243 [Limits                ] Mirroring - Mirrored ports                              :: To verify max mirror can be configured | step1: Configure up to 8 mirrored ports => - Confirm that after adding 3 interface ports,
  - AWP-20233   0.197 [sFlow                 ] Mirroring multiple ports with sFlow.                    :: Check mirroring multiple ports and across the instance with sFlow enabled. | step1: Configure mirror port.Source ports are 3ports.
  - AWP-27026   0.181 [VLAN                  ] Verify VLAN translations with mirroring.                :: Verify VLAN translations with mirroring. | step1: Create some vlans vlans: awplus# configure terminal awplus(config)# vlan databas
  - AWP-6913    0.178 [Port Mirroring        ] CR30073 - CLI to disable port mirroring                 :: CR30073 - CLI to disable port mirroring | step1: Setup up mirror port for some ports on each stack and stack members. Issue no mir
  - AWP-23103   0.177 [RSPAN - Mirror to VLAN] RSPAN Egress: RSPAN Egress and port-mirroring on same d :: Remote-mirror-egress ports and port-mirroring can be on the same switch or stacked device. | step1: Configure remote-mirror interf
  - AWP-13681   0.176 [Software Licensing    ] License Bundle - Base (Japan) (x510)                    :: License bundle - Base (Japan) for x510 platform | step1: x510 Base License Must include: VRRP VRRPv3 LAG-128 Virtual-MAC BFD IPv6 
  - AWP-8745    0.171 [sFlow                 ] sFlow and port mirroring                                :: Confirm when sflow is enable, port mirror is not allowed | step1: Enable sflow in DUT Configure port mirror in interface port with
  - AWP-13672   0.170 [Software Licensing    ] License Bundle - Base (ROW) (x510)                      :: License bundle - Base (ROW) for x510 platform | step1: x510 Verify Base license Must include: VRRP VRRPv3 LAG-128 Virtual-MAC BFD 

### AWPTCM-T44213  |  area: Switching DHCPSnooping  |  feature: ARP Security
folder:/New Platform Template/Switching  steps:1  obj:True
ZEPHYR: OBJ: Should be stable and secure wiith ARP storm conditions when ARP security is enabled || ARP storm conditions
  - AWP-9936    0.815 [DHCP Snooping         ] DHCP Snooping - ARP storm with ARP security             :: Should be stable and secure wiith ARP storm conditions when ARP security is enabled | step1: ARP storm conditions => Should be sta
  - AWP-9935    0.630 [DHCP Snooping         ] DHCP Snooping - ARP storm conditions                    :: Should be stable and secure wiith ARP storm conditions | step1: ARP storm conditions => Should be stable and secure
  - AWP-9938    0.459 [DHCP Snooping         ] DHCP Pkt storm conditions - snooping enabled on differe :: Check that this should be stable though functionality will be impared. | step1: DHCP Pkt storm conditions - snooping enabled on di
  - AWP-9937    0.400 [DHCP Snooping         ] DHCP Snooping - Pkt storm conditions                    :: Check that this should be stable though functionality will be impared with dhcp snooping vlan | step1: DHCP Pkt storm conditions -
  - AWP-9867    0.391 [DHCP Snooping         ] ARP Security and malformed packets                      :: Confirm that ARP Security is stable | step1: ARP Security and malformed ARP packets => ARP Security is stable
  - AWP-9724    0.374 [DHCP Snooping         ] DHCP Snooping - ARP Security Command                    :: DHCP Snooping - ARP Security Command work as expected | step1: (no) arp security - vlan interface mode => Ref UIDv8. Stable when d
  - AWP-9726    0.369 [DHCP Snooping         ] DHCP Snooping - ARP Security Show Commands              :: DHCP Snooping - ARP Security Show Command work as expected | step1: show arp security => Ref UIDv8. Stable when dhcp-snooping serv
  - AWP-9728    0.368 [DHCP Snooping         ] DHCP Snooping - ARP Security Show Command               :: DHCP Snooping - ARP Security Show Command work as expected | step1: show arp security interface => Ref UIDv8 shows arp security vi

### AWPTCM-T44214  |  area: Switching DHCPSnooping  |  feature: Option 82
folder:/New Platform Template/Switching  steps:0  obj:True
ZEPHYR: OBJ: Option 82 is returned ||
  - AWP-3708    0.459 [DHCP Snooping         ] DHCP Snooping with Option 82 insertion - virtual MAC en :: Verify Option 82 sub-option 1 & 2 with VCS | step1: 1.Configure DUT in Stack with Virtual Mac enabled 2.Configure Option 82 (defau
  - AWP-9792    0.449 [DHCP Snooping         ] DHCP Snooping with Option 82 insertion                  :: Check that Option82 is observed | step1: AUTOMATED: 1165-502.5 DHCP REQUEST Packets - Option 82 is inserted => Option 82 is observ
  - AWP-9797    0.442 [DHCP Snooping         ] DHCP Snooping with Option 82 insertion - with VCS virtu :: Confirm that with Virtual MAC the sub-option 82 is correct | step1: Option 82 sub-option 2 - Switch MAC - uses correct virtual MAC
  - AWP-9793    0.434 [DHCP Snooping         ] DHCP Snooping with Option 82 insertion - removal        :: Confirm that Option82 is removed | step1: DHCP REPLYs going to untrusted ports - Option 82 is removed => Option 82 is removed
  - AWP-3709    0.431 [DHCP Snooping         ] DHCP Snooping with Option 82 insertion - virtual MAC di :: Verify Option 82 sub-option 1 & 2 with VCS (Virtual MAC disabled) | step1: VCS - functional test without virtual MAC enabled 1.Con
  - AWP-3705    0.429 [DHCP Snooping         ] DHCP Snooping option 82 - show commands                 :: Verify display DHCP snooping Option 82 information for all interfaces, a specific interface or a range of interfaces. | step1: The
  - AWP-3702    0.409 [DHCP Snooping         ] DHCP Snooping with Option 82 insertion - Trusted ports  :: Trusted Ports: DHCP packtes with Option 82 are accepted and Option 82 is not updated | step1: >Trusted port and DHCP Server Config
  - AWP-9802    0.408 [DHCP Snooping         ] DHCP Snooping with Option 82 insertion - virtual MAC en :: Confirm that DHCP snooping with option 82 functions well when VMAC enabled | step1: Stacking - functional test with virtual MAC en

### AWPTCM-T44215  |  area: Switching DHCPSnooping  |  feature: Subscriber ID
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-9699    0.536 [DHCP Snooping         ] CLI Test: ip dhcp snooping subscriber-id                :: "ip dhcp snooping subscriber-id " command work as expected | step1: (no) ip dhcp snooping subscriber-id word => UIDv8 Switchport i
  - AWP-18387   0.492 [DHCPv6                ] Confirm subscriber field has the mac address            :: Confirm subscriber field has mac address | step1: Capture the packets between DUT and server. => Check the "dhcp relay" packet tha
  - AWP-18386   0.425 [DHCPv6                ] ip dhcp-relay agent-option for new field: subscriber-id :: Confirm new command: ip dhcp-relay agent-option subscriber-id-auto-mac | step1: Issue "ip dhcp-relay agent-option subscriber-id-au
  - AWP-9721    0.254 [DHCP Snooping         ] DHCP Snooping ACL command - MAC/IP                      :: MAC dhcpsnooping keyword should be available | step1: (no) access-list hardware <name> (no) 10 permit ip dhcpsnooping any mac dhcp
  - AWP-9720    0.242 [DHCP Snooping         ] DHCP Snooping ACL command - IP                          :: Dhcpsnooping keyword should be available | step1: (no) access-list hardware <name> (no) 10 permit ip dhcpsnooping any (no) 20 deny
  - AWP-10077   0.182 [IPv6                  ] IPv6 Switching - rstp topology change                   :: IPv6 and rstp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that rstp 
  - AWP-9800    0.178 [DHCP Snooping         ] DHCP Snooping with Option 82 insertion - sup-option 6   :: Check that option82 contains sub-option 6 only once configured | step1: Option 82 inserted with sub-option 6 (subscriber ID) if co
  - AWP-10078   0.178 [IPv6                  ] IPv6 Switching - stp topology change                    :: IPv6 and stp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that stp fo

### AWPTCM-T44216  |  area: Switching DHCPSnooping  |  feature: IP Source Guard
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-9721    0.319 [DHCP Snooping         ] DHCP Snooping ACL command - MAC/IP                      :: MAC dhcpsnooping keyword should be available | step1: (no) access-list hardware <name> (no) 10 permit ip dhcpsnooping any mac dhcp
  - AWP-7545    0.316 [Storm Control         ] Interop with BPDU-guard feature                         :: Test that BPDU guard and packet storm protection can be configured together. | step1: Interop with bpdu-guard feature - which can 
  - AWP-9720    0.310 [DHCP Snooping         ] DHCP Snooping ACL command - IP                          :: Dhcpsnooping keyword should be available | step1: (no) access-list hardware <name> (no) 10 permit ip dhcpsnooping any (no) 20 deny
  - AWP-9439    0.247 [xSTP                  ] Command implementation of spanning-tree portfast bpdu-g :: | step1: Command implementation: spanning-tree portfast bpdu-guard => - Portfast Globally enabled, disabled on port -off - portfas
  - AWP-9441    0.244 [xSTP                  ] Command implementation of spanning-tree guard root      :: Verify root guard oparates accordingly | step1: - Setup 3 switch w/ RSTP environment(all ports are in vlan1) - Identify Rootbridge
  - AWP-7073    0.241 [IGMP                  ] IGMPv3 with IP Source 0.0.0.0                           :: Report source IP can be 0.0.0.0 | step1: Report source IP can be 0.0.0.0 => Report source IP can be 0.0.0.0
  - AWP-10872   0.230 [IPv6 RA Guard         ] RA Guard - Enable/Disable - single unit                 :: Enable and disable Router Advertisment Guard on all or defined interfaces. This is the base case - no other configeration applied:
  - AWP-9718    0.217 [DHCP Snooping         ] show ip source binding                                  :: "show ip source binding" should show correct output | step1: show ip source binding => Ref UIDv8 for show ip source binding. Comma

### AWPTCM-T44217  |  area: Switching DHCPSnooping  |  feature: Dynamic ARP inspection
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-4338    0.262 [ARP                   ] Show ARP: Command                                       :: Display ARP table | step1: Configure a Static ARP and use IXIA to send Dynamic ARP a. Add 5 static ARP b. Add 120 dynamic ARP usin
  - AWP-9721    0.245 [DHCP Snooping         ] DHCP Snooping ACL command - MAC/IP                      :: MAC dhcpsnooping keyword should be available | step1: (no) access-list hardware <name> (no) 10 permit ip dhcpsnooping any mac dhcp
  - AWP-9720    0.233 [DHCP Snooping         ] DHCP Snooping ACL command - IP                          :: Dhcpsnooping keyword should be available | step1: (no) access-list hardware <name> (no) 10 permit ip dhcpsnooping any (no) 20 deny
  - AWP-10088   0.232 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Dynamic Ha :: Able to perform L3 hashing on IPv6 addresses with LAG Dynamic | step1: Link Aggregation - Dynamic . Hashing => L3 Hashing on IPv6 
  - AWP-9961    0.232 [DHCP Snooping         ] ARP Security - on dynamic channel after hotswap         :: Confirm normal operation on dynamic channel after hotswap | step1: ARP Security applied correctly on dynamic channel group interfa
  - AWP-4341    0.227 [ARP                   ] Static ARP: Command                                     :: Static ARP command & functions | step1: Configure Static ARP on VLAN a. Configure VLAN with IP and configre Static ARP. b. Configu
  - AWP-10087   0.227 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Dynamic an :: Confirm configuration was correct over a LAG interface and traffic passes with linkup/down | step1: Link Aggregation - Dynamic. Co
  - AWP-9962    0.226 [DHCP Snooping         ] ARP Security - on dynamic channel after master failover :: Confirm normal operation on dynamic channel after master failover | step1: ARP Securityapplied correctly on dynamic channel group 

### AWPTCM-T44218  |  area: Switching EPSR  |  feature: Master
folder:/New Platform Template/Switching  steps:1  obj:True
ZEPHYR: OBJ: Ensure support for EPSR Master is enabled on the base license ||
  - AWP-13615   0.449 [EPSR, EPSR+, EPSR++   ] CR00035779 EPSR master feature license                  :: EPSR master cannot be configured without a EPSR master feature license. EPSR master is disabled when EPSR master feature license i
  - AWP-13316   0.432 [EPSR, EPSR+, EPSR++   ] Delete master license on x510 as epsr master            :: The master EPSR instances are changed to disable state when EPSR Master license is removed or expired. | step1: Deleter master lic
  - AWP-10084   0.390 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Static     :: Confirm that it is correctly configured over a LAG interface and traffic passes with linkup/down | step1: 1.) Configure VCS Stack 
  - AWP-12989   0.373 [EPSR, EPSR+, EPSR++   ] x510 works correctry as epsr master.                    :: x510 can become epsr master with master license. | step1: Set epsr master configuration after master license input. => command inp
  - AWP-10087   0.370 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Dynamic an :: Confirm configuration was correct over a LAG interface and traffic passes with linkup/down | step1: Link Aggregation - Dynamic. Co
  - AWP-10088   0.368 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Dynamic Ha :: Able to perform L3 hashing on IPv6 addresses with LAG Dynamic | step1: Link Aggregation - Dynamic . Hashing => L3 Hashing on IPv6 
  - AWP-7173    0.367 [IGMP                  ] Query Solicitation - EPSR Master                        :: change the node that is the epsr master | step1: change the node that is the epsr master => qs continues normally
  - AWP-4083    0.357 [EPSR, EPSR+, EPSR++   ] Enhanced Recovery - disabled on EPSR Master node (Test  :: Enhanced recovery when it is not enabled on the master | step1: Enhanced recovery when it is not enabled on the master => Refer Su

### AWPTCM-T44219  |  area: Switching EPSR  |  feature: Transit
folder:/New Platform Template/Switching  steps:1  obj:True
ZEPHYR: OBJ: EPSR Transit - No VCS - No Link Aggregation. Simple Setup Fail Each link in the epsr ring while L3 unicast traffic runni || Link failure- each link in epsr ring including aggregated li
  - AWP-17708   0.931 [EPSR, EPSR+, EPSR++   ] EPSR Transit test Link Fail with L3 Traffic             :: EPSR Transit - No VCS - No Link Aggregation. Simple Setup Fail Each link in the epsr ring while L3 unicast traffic running through
  - AWP-4026    0.886 [EPSR, EPSR+, EPSR++   ] EPSR Transit test Link Fail with L3 Traffic             :: Fail Each link in the epsr ring while L3 unicast traffic running through the EPSR Transit | step1: Link failure- each link in epsr
  - AWP-17709   0.781 [EPSR, EPSR+, EPSR++   ] EPSR Transit test Node Failure L3 Traffic               :: EPSR Transit - No VCS - No Link Aggregation. Simple Setup Fail each of the transit nodes while carrying L3 Traffic through the EPS
  - AWP-17705   0.774 [EPSR, EPSR+, EPSR++   ] EPSR Transit test Link Fail with L2 Traffic             :: EPSR Transit - No VCS - No Link Aggregation. Simple Setup Fail Each link in the epsr ring while L2 unicast traffic running through
  - AWP-17702   0.748 [EPSR, EPSR+, EPSR++   ] EPSR Master test Link Fail with L3 Traffic              :: EPSR Master - No VCS - No Link Aggregation - Simple SetupFail Each link in the epsr ring while L3 unicast traffic running through 
  - AWP-4047    0.745 [EPSR, EPSR+, EPSR++   ] Link failure- each link in epsr ring and edge - Layer 3 :: Stack as EPSR Transit with dynamic link aggregation to edge and link aggregation in epsr ring. Fail Each link in the epsr ring whi
  - AWP-4048    0.738 [EPSR, EPSR+, EPSR++   ] Transit node failure in EPSR ring - Layer 3             :: Stack as EPSR Transit with dynamic link aggregation to edge and link aggregation in epsr ring. Fail each of the transit nodes whil
  - AWP-4023    0.726 [EPSR, EPSR+, EPSR++   ] EPSR Transit test Link Fail with L2 Traffic             :: Fail Each link in the epsr ring while L2 unicast traffic running through EPSR Transit | step1: Link failure- each link in epsr rin

### AWPTCM-T44221  |  area: Switching EPSR  |  feature: SLP
folder:/New Platform Template/Switching  steps:1  obj:True
ZEPHYR: OBJ: Simple topology VCS Failover Transit nodes with shared links. Include tests for failovers while tranist is in different || VCS Failover on transit node with Links up Links down Pre-fo
  - AWP-10599   0.931 [EPSR Super-Loop Preven] EPSR-SLP Simple shared link topology - VCS Failover Tra :: Simple topology VCS Failover Transit nodes with shared links. Include tests for failovers while tranist is in different states. Li
  - AWP-10598   0.487 [EPSR Super-Loop Preven] EPSR-SLP Simple shared link topology - VCS Failover on  :: Simple topology - VCS Failover on EPSR Masters Failover while in different states. Complete, Failed with secondary blocked, Failed
  - AWP-10352   0.449 [EPSR Super-Loop Preven] EPSR-SLP with simple shared link topology - node failur :: Simple Shared link Topology. Master not on shared Link.nodes with shared links fail & recover. EPSR behaves normally on rings inde
  - AWP-10363   0.439 [EPSR Super-Loop Preven] EPSR-SLP with two adjacent shared links. Master on shar :: Two adjacent shared links. High priority Master node on shared link. Failure of shared links. | step1:
  - AWP-10364   0.425 [EPSR Super-Loop Preven] EPSR-SLP with two adjacent shared links. Master on shar :: Two adjacent shared links. High priority Master node on shared link. Failure of nodes (restart) individually | step1:
  - AWP-10362   0.423 [EPSR Super-Loop Preven] EPSR-SLP with two adjacent shared links - EPSR+/++      :: Two adjacent shared links. Master nodes not on shared links. Enhanced recovery. | step1: Setup shared link topology with 2 physica
  - AWP-10357   0.418 [EPSR Super-Loop Preven] EPSR-SLP with simple shared link topology - LAG group o :: Simple Shared link Topology. Shared link is static channel group Highest pririoty EPSR Master a node that is connected to the shar
  - AWP-10360   0.411 [EPSR Super-Loop Preven] EPSR-SLP with two adjacent shared link - failure of non :: Two adjacent shared links. Master nodes not on shared links. Failure of non-shared links. | step1: Setup shared link topology with

### AWPTCM-T44222  |  area: Switching EPSR  |  feature: Router Redundency Protocol
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-10084   0.357 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Static     :: Confirm that it is correctly configured over a LAG interface and traffic passes with linkup/down | step1: 1.) Configure VCS Stack 
  - AWP-10087   0.341 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Dynamic an :: Confirm configuration was correct over a LAG interface and traffic passes with linkup/down | step1: Link Aggregation - Dynamic. Co
  - AWP-10088   0.339 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Dynamic Ha :: Able to perform L3 hashing on IPv6 addresses with LAG Dynamic | step1: Link Aggregation - Dynamic . Hashing => L3 Hashing on IPv6 
  - AWP-10085   0.314 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Static Has :: Able to perform L3 hashing on IPv6 addresses | step1: 1.) Configure VCS Stack 2.) Configure EPSR and Static Link Aggregation 3.) C
  - AWP-10089   0.305 [IPv6                  ] VCS - IPv6 switching after EPSR change - challenging re :: Check functionality if works well with challenging reconfigurations | step1: Implement challenging reconfigurations such as L2 top
  - AWP-9368    0.282 [xSTP                  ] Interop with EPSR                                       :: | step1: Interop with EPSR
  - AWP-10077   0.272 [IPv6                  ] IPv6 Switching - rstp topology change                   :: IPv6 and rstp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that rstp 
  - AWP-10078   0.265 [IPv6                  ] IPv6 Switching - stp topology change                    :: IPv6 and stp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that stp fo

### AWPTCM-T44223  |  area: Switching ForwardingMode  |  feature: Store and Forward
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-6435    0.290 [L2 Switching (L2 Learn] Switchport mode access - forward                        :: Discarding and forwarding - Switchport mode access - forward | step1: Switchport mode access - forward => Discarding and forwardin
  - AWP-6677    0.273 [IP Helper             ] Command Line Handler - ip forward-protocol              :: Command Line Interface tests - ip forward-protocol commands executed as expected | step1: ip forward-protocol udp PORT / no ip for
  - AWP-10047   0.270 [IPv6                  ] IPv6 forward command                                    :: Confirm that the command is executable and work as expected | step1: issue command ipv6 forwarding: => command works, functions co
  - AWP-6679    0.256 [IP Helper             ] Command Line Help - ip forward-protocol                 :: Command Line Help tests - ip forward-protocol commands display useful info | step1: ip forward-protocol udp PORT / no ip forward-p
  - AWP-22172   0.251 [Port Authentication   ] auth-web forward x.x.x.x/M dns                          :: auth-web forward 192.168.1.0/24 dns This test has to test by Broadcom(VCS) and Marvell(VCS), Router(eth port only), x230. | step1:
  - AWP-14945   0.250 [Web Authentication    ] auth-web forward / arp,dns,dhcp,tcp,udp                 :: Confirm that the setting of "auth-web forward" works correctly with each option. | step1: (1) Configure "auth-web forward" with an
  - AWP-22259   0.243 [Port Authentication   ] auth-web forward x.x.x.x/M dns with DNS relay           :: When DUT set dns relay, destination of address have to set DUT. This test has to test by Broadcom(VCS) and Marvell(VCS), Router(et
  - AWP-6437    0.240 [L2 Switching (L2 Learn] switchport mode trunk - allowed vlan - forward          :: Discarding and forwarding - switchport mode trunk - allowed vlan - forward | step1: switchport mode trunk - allowed vlan - forward

### AWPTCM-T44224  |  area: Switching ForwardingMode  |  feature: Cut Through
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-2480    0.247 [VRF-Lite              ] Through-put performance Inter VRF switching hardware    :: To check throughput performance (RFC2544) for traffic switched in hardware | step1: Setup a traffic path such that traffic is swit
  - AWP-10077   0.221 [IPv6                  ] IPv6 Switching - rstp topology change                   :: IPv6 and rstp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that rstp 
  - AWP-10078   0.215 [IPv6                  ] IPv6 Switching - stp topology change                    :: IPv6 and stp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that stp fo
  - AWP-10085   0.200 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Static Has :: Able to perform L3 hashing on IPv6 addresses | step1: 1.) Configure VCS Stack 2.) Configure EPSR and Static Link Aggregation 3.) C
  - AWP-12915   0.193 [ATMF                  ] Data Plane: ATMF Splits                                 :: Story 58 If network failures lead to a ATMF splitting, all pieces should continue to function (within the limits of connectivity).
  - AWP-10087   0.182 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Dynamic an :: Confirm configuration was correct over a LAG interface and traffic passes with linkup/down | step1: Link Aggregation - Dynamic. Co
  - AWP-10084   0.182 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Static     :: Confirm that it is correctly configured over a LAG interface and traffic passes with linkup/down | step1: 1.) Configure VCS Stack 
  - AWP-10088   0.180 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Dynamic Ha :: Able to perform L3 hashing on IPv6 addresses with LAG Dynamic | step1: Link Aggregation - Dynamic . Hashing => L3 Hashing on IPv6 

### AWPTCM-T44225  |  area: Switching ForwardingMode  |  feature: L2 Filter
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-10077   0.411 [IPv6                  ] IPv6 Switching - rstp topology change                   :: IPv6 and rstp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that rstp 
  - AWP-10078   0.401 [IPv6                  ] IPv6 Switching - stp topology change                    :: IPv6 and stp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that stp fo
  - AWP-4969    0.339 [Limits                ] MAC Filter entries                                      :: Deactivated | step1: N/A => N/A
  - AWP-5770    0.267 [Port Security (Intrusi] L2 attack - private vlan attack with HW filter          :: Test switch handles private VLAN attack | step1: Configure SW-1 with HW filter to discard packets originated from 192.168.1.0/25 d
  - AWP-9243    0.252 [VLAN                  ] Port-based VLAN - access mode - ingress-filter is on    :: Port-based VLAN - access mode - ingress-filter is on | step1: 1. Create vlan10(111),20(112), 30(113) 2. Assign port to each vlan 3
  - AWP-10089   0.249 [IPv6                  ] VCS - IPv6 switching after EPSR change - challenging re :: Check functionality if works well with challenging reconfigurations | step1: Implement challenging reconfigurations such as L2 top
  - AWP-18460   0.245 [Router Bridging       ] Show mac-filter command                                 :: Test that show command shows accurate information | step1: 1. Create a bridge 2. Add interfaces 3. Create a mac-filter/s 4. Apply 
  - AWP-7150    0.238 [IGMP                  ] Maximum L2 Multicast MAC Entry                          :: Maximum L2 Multicast MAC Entry | step1: No config on switch Send in 4000 L2 multicast macs Check they are all registered in snoopi

### AWPTCM-T44227  |  area: Switching HardwarePacketFilter(IP)  |  feature: Access Control Lists
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-27897   0.363 [JITC Certification    ] V-3000:The network device must log all interface access :: V-3000 NET1020 The network device must log all interface access control lists (ACL) deny statements. | step1: Configure interface 
  - AWP-9086    0.353 [QoS                   ] QoS: access-group Specify IP or MAC Hardware access con :: Verify that matching and non matching traffic should conform to the configured class-map and default maps. | step1: Create ACL and
  - AWP-15367   0.298 [Web Authentication    ] CONTROL                                                 :: CONTROL | step1: Refer to 2.3.2.1.doc => Refer to 2.3.2.1.doc
  - AWP-8589    0.261 [ACL                   ] ACL: Hardware IP 3000 range full lists                  :: ACL: Hardware IP 3000 range full lists | step1: Configure and negate hardware IP 3000 range ACLs - full range access-list {<3000-3
  - AWP-8582    0.259 [ACL                   ] ACL: Standard - Full lists                              :: ACL: Standard - Full lists | step1: Configure and negate standard ACLs - full range access-list {<1-99> | <1300-1999>} [permit | d
  - AWP-7084    0.254 [IGMP                  ] CLI Test - ip igmp access-group                         :: This command adds an access control list to a VLAN interface configured for IGMP, IGMP Snooping, or IGMP Proxy. The access control
  - AWP-8622    0.246 [ACL                   ] ACL: Named Hardware applied to port ranges and lists ef :: ACL: Named Hardware applied to port ranges and lists effective | step1: ACL is applied in hardware to all ports in range => Change
  - AWP-8586    0.244 [ACL                   ] ACL: Extended - Full lists                              :: ACL: Extended - Full lists | step1: Configure and negate extended ACLs - full range access-list {<100-199> | <2000-2699>} [permit 

### AWPTCM-T44228  |  area: Switching HardwarePacketFilter(IP)  |  feature: ACL Table Utilization
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-21494   0.346 [ACL                   ] Large IPv6 ACL group with max QoS utilization           :: Large extended ACL group should not affect QoS utilization | step1: 1. Fill-up QoS and ACL table Check "sh platform classifier sta
  - AWP-21493   0.344 [ACL                   ] Large IPv4 ACL group with max QoS utilization           :: Large extended ACL group should not affect QoS utilization | step1: 1. Fill-up QoS and ACL table Check "sh platform classifier sta
  - AWP-11645   0.338 [QoS                   ] QoS and ACL 100% utilization - with reboot/failover     :: To check if DUT can handle QoS and ACL 100% utilization and configuration should be recovered after reboot or failover. | step1: F
  - AWP-13620   0.317 [ACL                   ] Correct Utilization of ACL with XEM and XEMv2           :: Utilization of classifier entry should be correct for both XEM and XEMv2 | step1: Configure number of ACLs Use the command 'show p
  - AWP-8710    0.269 [ACL                   ] ACL: Limits Combination of filters                      :: ACL: Limits Combination of filters | step1: Configure access-lists - platform table for ACL should be full Effective / after hotsw
  - AWP-9714    0.266 [DHCP Snooping         ] show ip dhcp snooping acl                               :: "show ip dhcp snooping acl" should show correct output | step1: show ip dhcp snooping acl => Ref UIDv8 for show ip dhcp snooping a
  - AWP-14341   0.249 [ACL                   ] Routing-ratio command no longer sets IPv4/IPv6 ACL tabl :: On x900/x908 for SW version 5.4.3 and earlier the IPv4/IPv6 tables are set via the platform routingratio command. From 5.4.4 onwar
  - AWP-10077   0.245 [IPv6                  ] IPv6 Switching - rstp topology change                   :: IPv6 and rstp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that rstp 

### AWPTCM-T44229  |  area: Switching HardwarePacketFilter(IP)  |  feature: Sequence Number
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-8598    0.341 [ACL                   ] ACL: Named Extended - adding & removing entries by sequ :: ACL: Named Extended - adding & removing entries by sequence number | step1: Configure and negate named extended ACLs using sequenc
  - AWP-23141   0.334 [[ATKK] Auto Acceptance] CLI: Negate sequence entry                              :: CR-52510/CR-52051/CR-51854 | step1: Create ACL using sequence number Execute show access-list => The switch should show correct se
  - AWP-8601    0.331 [ACL                   ] ACL: Named Hardware - adding & removing entries by sequ :: ACL: Named Hardware - adding & removing entries by sequence number | step1: Configure and negate named hardware ACLs using sequenc
  - AWP-8595    0.329 [ACL                   ] ACL: Named Standard - adding & removing entries by sequ :: ACL: Named Standard - adding & removing entries by sequence number | step1: Configure and negate named standard ACLs using sequenc
  - AWP-8610    0.327 [ACL                   ] ACL: IPv6 Hardware - adding & removing entries by seque :: ACL: IPv6 Hardware - adding & removing entries by sequence number | step1: Configure and negate IPv6 hardware ACLs using sequence 
  - AWP-8604    0.320 [ACL                   ] ACL: IPv6 Named Standard - adding & removing entries by :: ACL: IPv6 Named Standard - adding & removing entries by sequence number | step1: Configure and negate IPv6 named standard ACLs usi
  - AWP-8607    0.316 [ACL                   ] ACL: IPv6 Named Extended - adding & removing entries by :: ACL: IPv6 Named Extended - adding & removing entries by sequence number | step1: Configure and negate IPv6 named extended ACLs usi
  - AWP-26994   0.308 [GUI Support           ] API event - member                                      :: Increase Efficiency of communication from Vista to/from AW+ | step1: Member node: Link down/up interface => From member: sh atmf d

### AWPTCM-T44230  |  area: Switching HardwarePacketFilter(IP)  |  feature: Action send-to-vlan-port
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-22549   0.333 [Storm Control         ] action: none                                            :: | step1: confirm DUT does NOT send LDF
  - AWP-20234   0.301 [sFlow                 ] ACL action copy-to-mirror/send-to-mirror with sFlow.    :: Check ACL action copy-to-mirror and send-to-mirror with sFlow enabled. | step1: Create ACL action copy-to-mirror and apply to a po
  - AWP-22546   0.288 [Storm Control         ] action: port-disable on tag vlan                        :: | step1: - confirm DUT detect loop, and disable port. - confirm DUT re-enabled port by timeout - confirm DUT detect loop again. -
  - AWP-22547   0.274 [Storm Control         ] action: link-down on tag vlan                           :: | step1: - confirm DUT detect loop, and disable port. - confirm DUT re-enabled port by timeout - confirm DUT detect loop again. -
  - AWP-10077   0.269 [IPv6                  ] IPv6 Switching - rstp topology change                   :: IPv6 and rstp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that rstp 
  - AWP-7530    0.266 [Storm Control         ] Port-disable action for a particular vlan.              :: Test that port is disabled until timeout period expires. | step1: Test that port-disable is effective. Change the configuration on
  - AWP-22581   0.263 [VLAN                  ] vlan classifier and VRF                                 :: vlan classifier routing/switching behavior match routing routing to other vlan in vrf instance match switching switching to vlan a
  - AWP-22612   0.263 [[ATKK] Auto Acceptance] vlan classifier and VRF                                 :: vlan classifier routing/switching behavior match routing routing to other vlan in vrf instance match switching switching to vlan a

### AWPTCM-T44231  |  area: Switching HardwarePacketFilter(IP)  |  feature: ACLs for a VLAN or a VLAN range
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-9946    0.325 [DHCP Snooping         ] DHCP Snooping ACLs - after hotswap                      :: Check ACLs in HW tables after hotswap | step1: DHCP Snooping ACLs applied correctly after hotswap in => Check ACLs in HW tables
  - AWP-9948    0.285 [DHCP Snooping         ] DHCP Snooping ACLs - on node joining stack              :: Check ACLs in HW tables on node joining stack | step1: DHCP Snooping ACLs applied correctly on node joining stack => Check ACLs in
  - AWP-9947    0.281 [DHCP Snooping         ] DHCP Snooping ACLs - after masterfailover               :: Check ACLs in HW tables after masterfailover | step1: DHCP Snooping ACLs applied correctly after master failover => Check ACLs in 
  - AWP-8588    0.279 [ACL                   ] ACL: Hardware IP 3000 range entries                     :: ACL: Hardware IP 3000 range entries | step1: Configure and negate hardware IP 3000 range ACLs access-list {<3000-3699>} {copy-to-c
  - AWP-21199   0.270 [ACL                   ] Management ACLs will not block secondary IP address     :: secondary IP will not be blocked | step1: assigned certain vlan with both primary and secondary address,creat acl only block prima
  - AWP-9949    0.269 [DHCP Snooping         ] DHCP Snooping ACLs - on static channel after hotswap    :: Check ACLs in HW tables on static channel after hotswap | step1: DHCP Snooping ACL's applied correctly on static channel group int
  - AWP-9952    0.268 [DHCP Snooping         ] DHCP Snooping ACLs - on dynamic channel after hotswap   :: Check ACLs in HW tables on dynamic channel after hotswap | step1: DHCP Snooping ACL's applied correctly on dynamic channel group i
  - AWP-9847    0.265 [DHCP Snooping         ] DHCP Snooping - ACLs set to null - IP address only      :: Confirm that ACLs seto to null source address and traffic is blocked if entry is removed from DHCP binding database for IP address

### AWPTCM-T44232  |  area: Switching IGMPSnooping  |  feature: IGMP Snooping All-groups
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-7117    0.590 [IGMP                  ] Logging exist for IGMP and IGMPSnooping                 :: Verify logging works with IGMP and IGMP Snooping | step1: show log => display log output with correct information
  - AWP-7110    0.385 [IGMP                  ] CLI Test - show ip igmp groups                          :: Use this command to display the multicast groups with receivers directly connected to the router, and learned through IGMP. | step
  - AWP-8402    0.357 [MLD Snooping          ] MLD Snooping Interop with IGMP Snooping                 :: | step1: Ensure that both IGMP Snooping and MLD Snooping can operate independently of one another
  - AWP-17438   0.352 [IGMP Snooping         ] IGMP-CFG-001:IP IGMP Snooping                           :: | step1: 1. Verify that the user can enable and disable IGMP Snooping. => 1. The user should be able to enable and disable IGMP sn
  - AWP-17839   0.344 [IGMP Snooping         ] IP IGMP Snooping Source Timeout                         :: IP IGMP Snooping Source Timeout is working correctly. | step1: Setup multicast envronment using IGMP snooping Configure ip igmp sn
  - AWP-7097    0.342 [IGMP                  ] CLI Test - ip igmp snooping                             :: Use this command to enable IGMP Snooping. When this command is used in the Global Configuration mode, IGMP Snooping is enabled at 
  - AWP-7114    0.340 [IGMP                  ] CLI Test - show ip igmp snooping statistics             :: Use this command to display IGMP Snooping statistics data. | step1: Issue the command show ip igmp snooping statistics interface <
  - AWP-7128    0.335 [IGMP Snooping         ] Disable IGMP snooping per Vlan                          :: Confirm that IGMP snooping function is workable per VLAN | step1: ATKK 3.5 Disable IGMP snooping per Vlan => Refer to ATKK 3.5

### AWPTCM-T44233  |  area: Switching IGMPSnooping  |  feature: IGMP Fast Leave
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-7136    0.510 [IGMP Snooping         ] IGMP snooping - Fast Leave                              :: Confirm the Fast Leave feature. If ‘Fast Leave’ is enabled for the switch then where a ‘Leave’ message about a group is received o
  - AWP-7098    0.506 [IGMP                  ] CLI Test - ip igmp snooping fast-leave                  :: Use this command to enable IGMP Snooping fast-leave processing. Fast-leave processing is analogous to immediate-leave processing; 
  - AWP-7117    0.499 [IGMP                  ] Logging exist for IGMP and IGMPSnooping                 :: Verify logging works with IGMP and IGMP Snooping | step1: show log => display log output with correct information
  - AWP-7137    0.483 [IGMP                  ] IGMP - Fast Leave                                       :: Confirm the Fast Leave feature. If ‘ip igmp immediate-leave’ is enabled for the switch then where a ‘Leave’ message about a group 
  - AWP-8401    0.419 [MLD Snooping          ] MLD Snooping - ipv6 mld snooping fast-leave             :: | step1: Test MLD snooping with fast Leave disabled, Then test MLD Snooping Fast Leave enabled. With Fast Leave enabled/disabled =
  - AWP-8361    0.413 [MLD Snooping          ] Command Line Handler - (no) ipv6 mld snooping fast-leav :: | step1: Command Handler: ipv6 mld snooping fast-leave
  - AWP-17596   0.383 [IGMP Snooping         ] AWP5-IGMPSN-CFG-002 - AWP-7098:CLI Test - ip igmp snoop :: Objective: Use this command to enable IGMP Snooping fast-leave processing. Fast-leave processing is analogous to immediate-leave p
  - AWP-17607   0.356 [IGMP Snooping         ] AWP5-IGMPSN-FUN-006 - AWP-7136:IGMP snooping - Fast Lea :: Objective: Confirm the Fast Leave feature. If ‘Fast Leave’ is enabled for the switch then where a ‘Leave’ message about a group is
