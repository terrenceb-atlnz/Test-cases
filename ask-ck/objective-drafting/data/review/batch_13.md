# Rerank batch 13  (cases 390..409)

### AWPTCM-T47190  |  area: Switching  |  feature: MRP
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-10077   0.471 [IPv6                  ] IPv6 Switching - rstp topology change                   :: IPv6 and rstp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that rstp 
  - AWP-10078   0.459 [IPv6                  ] IPv6 Switching - stp topology change                    :: IPv6 and stp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that stp fo
  - AWP-10087   0.388 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Dynamic an :: Confirm configuration was correct over a LAG interface and traffic passes with linkup/down | step1: Link Aggregation - Dynamic. Co
  - AWP-10084   0.388 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Static     :: Confirm that it is correctly configured over a LAG interface and traffic passes with linkup/down | step1: 1.) Configure VCS Stack 
  - AWP-10088   0.385 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Dynamic Ha :: Able to perform L3 hashing on IPv6 addresses with LAG Dynamic | step1: Link Aggregation - Dynamic . Hashing => L3 Hashing on IPv6 
  - AWP-2480    0.346 [VRF-Lite              ] Through-put performance Inter VRF switching hardware    :: To check throughput performance (RFC2544) for traffic switched in hardware | step1: Setup a traffic path such that traffic is swit
  - AWP-10085   0.341 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Static Has :: Able to perform L3 hashing on IPv6 addresses | step1: 1.) Configure VCS Stack 2.) Configure EPSR and Static Link Aggregation 3.) C
  - AWP-29644   0.335 [OpenFlow              ] ER-2059 - Repeat switching between hardware processing  :: Confirm that memory leak does not occur when repeat switching between hardware processing and software processing. | step1: Regist

### AWPTCM-T47191  |  area: Authentication Security TPM 2.0  |  feature: Trusted boot
folder:/New Platform Template/Authentication & Security  steps:1  obj:False
  - AWP-9883    0.466 [DHCP Snooping         ] DHCP Snooping - static on trusted ports                 :: Check that trusted command can be applied | step1: static - on trusted ports => ? Can the trusted command be applied to a channel 
  - AWP-9882    0.462 [DHCP Snooping         ] DHCP Snooping - dynamic on trusted ports                :: Confirm that trusted command can be applied | step1: dynamic - on trusted ports => ? Can the trusted command be applied to a chann
  - AWP-9943    0.400 [DHCP Snooping         ] DHCP Snooping - hotswap on trusted interfaces           :: Confirm normal operation after hotswap on trusted ports | step1: Hotswap on trusted interfaces [including LAGs] => Expect normal o
  - AWP-9893    0.332 [DHCP Snooping         ] DHCP Snooping - trusted and untrusted ports             :: Confirm that DHCP Snooping continues to function normally | step1: DHCP snooping configured and trusted and untrusted ports up and
  - AWP-9791    0.308 [DHCP Snooping         ] DHCP Snooping with Option 82 insertion - Trusted ports  :: Confirm Option82 is unchanged on trusted ports | step1: AUTOMATED: 1165-502.4 Trusted Ports: DHCP packtes with Option 82 are accep
  - AWP-9788    0.292 [DHCP Snooping         ] DHCP Snooping - Trusted ports and Option 82             :: Confirm that Option82 is unchanged | step1: AUTOMATED 1165-502.1 Trusted Ports: DHCP packets with Option 82 are accepted and Optio
  - AWP-27197   0.284 [AWC-lite              ] security                                                :: | step1: security <configured security id> Confirm that ID of security for network setting are configured on router.
  - AWP-3702    0.284 [DHCP Snooping         ] DHCP Snooping with Option 82 insertion - Trusted ports  :: Trusted Ports: DHCP packtes with Option 82 are accepted and Option 82 is not updated | step1: >Trusted port and DHCP Server Config

### AWPTCM-T47192  |  area: Management Config File  |  feature: A dynamic configuration while operating
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-9672    0.269 [xSTP                  ] Master fail-over with resiliency link configured and op :: | step1: Master fail-over with resiliency link configured and operating. Lost stack connectivity but not resiliency link => Stack 
  - AWP-9396    0.269 [xSTP                  ] Master fail-over with resiliency link configured and op :: | step1: Master fail-over with resiliency link configured and operating. Lost stack connectivity but not resiliency link => Stack 
  - AWP-9490    0.246 [xSTP                  ] Master fail-over with resiliency link configured and op :: | step1: Master fail-over with resiliency link configured and operating with virtual-MAC disabled. Lost stack connectivity but no 
  - AWP-6403    0.216 [L2 Switching (L2 Learn] Ageing - Dynamic and Static                             :: Verify hat static entry does not get removed while dynamic entry does. | step1: Ageing - Add dynamic entry at the same time and ma
  - AWP-8129    0.212 [z_Inactive            ] Device Management: Commands work and correct informatio :: All commands should work and config file is updated accordingly | step1: Check that all commands work and save the correct informa
  - AWP-8192    0.204 [z_Inactive            ] High Availability: Failover master with resiliency link :: Stack generates new virtual-mac and send gratatious ARP *** SAME TEST WITH AWP-8188, deactivated | step1: Master fail-over with re
  - AWP-6643    0.200 [VLAN                  ] Show running-config                                     :: VLAN packet counter configuration are shown in running-config | step1: Command Handler: "enable" CLI level show running config => 
  - AWP-1038    0.199 [Qualification         ] ID-ThermalOperatingRange                                :: Thermal operating range specified Setup: NA | step1: Thermal operating range specified => Check specification sheet shows thermal 

### AWPTCM-T47193  |  area: Management Config File  |  feature: Two or more configuration file can be stored
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-14773   0.293 [Port Authentication   ] auth two-step enable                                    :: Confirm that "auth two-step enable" command can be configured correctly. | step1: Input "auth two-step enable" on configuration mo
  - AWP-8129    0.258 [z_Inactive            ] Device Management: Commands work and correct informatio :: All commands should work and config file is updated accordingly | step1: Check that all commands work and save the correct informa
  - AWP-14943   0.254 [Web Authentication    ] Web Auth Proxy / Stored PAC file / via Web-server       :: Confirm that supplicant can get Stored PAC file via Web-server from auth-port or un-auth-port. | step1: [Gloval-enabled the featur
  - AWP-24091   0.241 [DHCPv6                ] Check IPV6 DNS information is stored on device.         :: DNS information learnt via DHCPv6 should be stored and viewable on the DUT | step1: Configure a DHCPv6 server to supply IP and DNS
  - AWP-25834   0.236 [Logging               ] Change log file configuration.                          :: Change the configuration to other file name. | step1: log external usb:/messages.log => the log file is created in external media.
  - AWP-6645    0.226 [VLAN                  ] Copy running config to file.cfg                         :: VLAN packet counter configuration can be saved to file.cfg | step1: Command Handler: "enable" CLI level copy running config <file.
  - AWP-14585   0.222 [File System           ] USB flash and ATMF: recover with backup files that was  :: ATMF recovery with the backup file which is stored other file system. | step1: run atmf backup. => the backup files stored in USB 
  - AWP-28781   0.218 [SNMP                  ] Configure mail client with and without a user password  :: S2118.1.3 It will be possible to configure the AW+ mail client with an authentication username and password, the defaults being em

### AWPTCM-T47194  |  area: Management Config File  |  feature: Screen editor support for a configuration file
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-2405    0.253 [z_Inactive            ] File - sanity test edit existing file                   :: File - sanity test edit existing file | step1: 2) Open existing file and save with new filename from the editor. => new file creat
  - AWP-8129    0.210 [z_Inactive            ] Device Management: Commands work and correct informatio :: All commands should work and config file is updated accordingly | step1: Check that all commands work and save the correct informa
  - AWP-27314   0.199 [VLAN                  ] Log:exceed the Max number of Multiple Dynamic VLAN      :: In this testcase,we verify whether log message appears on screen if supplicant exceeds the number of maximum ■Environment IXIA p1 
  - AWP-12977   0.192 [PIM-SMv6              ] Enable debugging and check output                       :: Enable PIM debugging and ensure info is displayed on screen | step1: Enable a PIM debug message Enable term mon Issue undebug all 
  - AWP-27179   0.191 [AWC-lite              ] from support version to not support version             :: | step1: Confirm the result of this operation. (expectation:FW update succeed, but AP cannot be managed?) Record the result in th
  - AWP-10059   0.182 [IPv6                  ] Show tech-support                                       :: Able to execute show tech-support and produce tech-support file | step1: show tech-support output => Supportability for IPv6
  - AWP-14898   0.181 [Web Authentication    ] Web Auth Proxy / show tech-support                      :: Confirm that "show proxy-autoconfig-file" command is included in tech-support file. **** This test case is not need to test **** S
  - AWP-24907   0.180 [Port Authentication   ] Log:exceed the Max number of Multiple Dynamic VLAN      :: The multiple Dynamic VLAN function of FS980M series register the log message when the supplicant exceeds the number of maximum In 

### AWPTCM-T47195  |  area: Management Config File  |  feature: A configuration file in text format as editable
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-2388    0.433 [z_Inactive            ] File - command - move file - text type file to non-text :: File - command - move file - text type file to non-text type | step1: File A is a text type. File B's extension another different 
  - AWP-2387    0.389 [z_Inactive            ] File - command - move file - non-text file              :: File - command - move file - non-text file | step1: File A is a non-text type. File Bs' extension is different to file A Issue the
  - AWP-2470    0.347 [File System           ] File - command - show file system                       :: File - command - show file system | step1: Run the 'show file system' => Confirm correct output format, time to display, the value
  - AWP-8200    0.346 [BGP                   ] Device Management - Show Command format                 :: Relevant show command output format | step1: Show command format and accuracy in complex BGP setup. Check the various show command
  - AWP-2365    0.342 [z_Inactive            ] File - command copy - non-text file                     :: File - command copy - non-text file | step1: File A is a non-text type. File B's extension is different to file A Issue the comman
  - AWP-2395    0.328 [File System           ] File - command - show file - various tests              :: File - command - show file - various tests | step1: Need to be tested on flash, nvs, SD card and USB File A is a text type Issue t
  - AWP-2397    0.287 [z_Inactive            ] File - command - show file NVS- various tests           :: File - command - show file NVS- various tests | step1: On NVS. File A is a text type Issue the command SHOW FILE A File A is a non
  - AWP-2396    0.275 [z_Inactive            ] File - command - show file card/usb - various tests     :: File - command - show file card/usb - various tests | step1: On CARD (or on USB in x8100 platform) File A is a text type Issue the

### AWPTCM-T47196  |  area: Management Config File  |  feature: A configuration file is movable easily
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-8129    0.274 [z_Inactive            ] Device Management: Commands work and correct informatio :: All commands should work and config file is updated accordingly | step1: Check that all commands work and save the correct informa
  - AWP-28916   0.233 [AWC-lite              ] can not delete/modify the config                        :: During auto-config session,configuration which was created by auto-config can not be deleted and modified. | step1: Connect AP to 
  - AWP-794     0.223 [Qualification         ] boot config-file' command                               :: Check "boot config-file" command exists | step1: Check "boot config-file" command => TEST PASS: if there is a boot config-file fro
  - AWP-8198    0.222 [BGP                   ] Device Management - BGP Startup                         :: Restart DUT with a complex BGP scenario config | step1: Create a configuration file. Copy running config to startup config in a co
  - AWP-6645    0.218 [VLAN                  ] Copy running config to file.cfg                         :: VLAN packet counter configuration can be saved to file.cfg | step1: Command Handler: "enable" CLI level copy running config <file.
  - AWP-2470    0.216 [File System           ] File - command - show file system                       :: File - command - show file system | step1: Run the 'show file system' => Confirm correct output format, time to display, the value
  - AWP-28917   0.205 [AWC-lite              ] can not delete/modify the ap-profile                    :: During auto-config session,ap-profile which was specified by command execution can not be deleted and modified. | step1: Connect A
  - AWP-25834   0.198 [Logging               ] Change log file configuration.                          :: Change the configuration to other file name. | step1: log external usb:/messages.log => the log file is created in external media.

### AWPTCM-T47197  |  area: Management Config File  |  feature: Config File Name  :
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-8129    0.458 [z_Inactive            ] Device Management: Commands work and correct informatio :: All commands should work and config file is updated accordingly | step1: Check that all commands work and save the correct informa
  - AWP-794     0.388 [Qualification         ] boot config-file' command                               :: Check "boot config-file" command exists | step1: Check "boot config-file" command => TEST PASS: if there is a boot config-file fro
  - AWP-2470    0.328 [File System           ] File - command - show file system                       :: File - command - show file system | step1: Run the 'show file system' => Confirm correct output format, time to display, the value
  - AWP-8198    0.328 [BGP                   ] Device Management - BGP Startup                         :: Restart DUT with a complex BGP scenario config | step1: Create a configuration file. Copy running config to startup config in a co
  - AWP-8130    0.326 [z_Inactive            ] Device Management: Negative commands test               :: All commands can be negated and config file is updated accordingly | step1: Negating 6to4 Tunnel commands work and the config file
  - AWP-2383    0.324 [z_Inactive            ] File - command - delete file with space in filename     :: File - command - delete file with space in filename | step1: Delete should work as normal. awplus#delete "file name" Delete flash:
  - AWP-2389    0.305 [z_Inactive            ] File - command - move file - various destination extens :: File - command - move file - various destination extension name | step1: File B is of unknown type Issue the command MOVE A B => F
  - AWP-3607    0.305 [File System           ] Boot config file on card (large config file) - stacked  :: Ensure softsync across the stack for large config file on the card | step1: 1) config the stack to boot from master where the conf

### AWPTCM-T47198  |  area: Management ManagingConfigurationFilesAndSoftwareVersions  |  feature: Silicon Profiles
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-26009   0.299 [G.8032                ] Functionallity: Capacity for G.8032 - 128 ERP Profiles  :: Verify that 128 ERP G.8032 Profiles are supported on the DUT. | step1: Verify that 128 ERP Profiles can be created. => That 128 ER
  - AWP-11206   0.282 [Platform              ] Command Line Interface:"Silicon-profile" create config  :: Verify silicon profile command and configuration are present in DUTs running config | step1: On x908 - Enter global configuration 
  - AWP-11205   0.274 [Platform              ] Command Line Interface: Silicon-profile extended does n :: Verify the command silicon-profile extended is not supported on an x900 platform | step1: On x900: - enter the command "silicon-pr
  - AWP-13899   0.263 [BGP4+                 ] BGP4+Verify silicon route tables                        :: Test that routes are added, removed from IP/IPv6 route table and silicon route table. | step1: 1) COnfigure DUT, TR1 and IXIA as e
  - AWP-11223   0.248 [Platform              ] Silicon-profile extended: Large silicon table           :: Verify DUT can handle large entries on its silicon table | step1: Use Ixia stream that will generate 70,000 MAC address On X908: -
  - AWP-11214   0.246 [Platform              ] Platform silicon-profile: set to different values on sl :: Check stack synchronization when silicon-profile configuration is different with each other | step1: 2 x908 - configure DUT 1(mast
  - AWP-12354   0.238 [Limits                ] SBx8100 Silicon Profile - High Availability - line card :: Testing the CLI against various cards. The SBx8100 supports a number of different cards with varying table sizes. In the first rel
  - AWP-11215   0.235 [Platform              ] Platform silicon-profile: set to different values on sl :: Verify VMAC enabled stack synchronization when silicon-profile configuration is different with each other | step1: 2 x908 - config

### AWPTCM-T47199  |  area: Management Operation  |  feature: Show warning message when user continue to use default PW
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-17781   0.264 [ATMF                  ] Warning message with atmf cleanup / erase factory-defau :: Warning message shown when command issued | step1: Issue command "atmf cleanup" or erase factory-default => Confirm the following 
  - AWP-8202    0.231 [BGP                   ] Device Management - Show Command                        :: Show command output | step1: Show command output => Accurate and useful
  - AWP-20744   0.222 [Wireless controller (U] Continue reboot AP                                      :: | step1: Set Environment
  - AWP-19275   0.221 [Wireless controller (U] Continue reboot AP                                      :: | step1: Set Environment
  - AWP-20039   0.221 [Wireless controller (U] Continue reboot AP                                      :: | step1: Set Environment
  - AWP-20745   0.219 [Wireless controller (U] Continue reboot WM                                      :: After finish LongRun, confirm following points. (1)APs and wireless clients can be connected. (2)Wireless client can comminicate t
  - AWP-19314   0.218 [Wireless controller (U] Continue reboot WM                                      :: After finish LongRun, confirm following points. (1)APs and wireless clients can be authenticated. (2)Wireless client can comminica
  - AWP-20040   0.218 [Wireless controller (U] Continue reboot WM                                      :: After finish LongRun, confirm following points. (1)APs and wireless clients can be authenticated. (2)Wireless client can comminica

### AWPTCM-T47200  |  area: IPv4 BFD  |  feature: With IPv4 Static Routing
folder:/New Platform Template/IPv4  steps:1  obj:False
  - AWP-24184   0.408 [ATMF                  ] Check IPv4 static routes will be supported              :: Check IPv4 static routes will be supported | step1: Check IPv4 static routes will be supported => confirm IPv4 static routes are s
  - AWP-15936   0.351 [IPv4                  ] Disabled Static Routing                                 :: Confirm that Static Routing doesn't work when "no ip forwarding" in configured. | step1: Ping to other network address from PC1. =
  - AWP-25826   0.339 [IPv4                  ] ECMP routing with interface name will be supported for  :: | step1: device with multiple ppp link and set static routing to a specific subnet egressing from multiple ppp interface names an 
  - AWP-23349   0.286 [[ATKK] Auto Acceptance] vlan classifier and ip routing on static LAG            :: | step1: send the packet and check DUT route the packet on IP subnet vlan port. => the packet should be routed on vlan10 and vlan2
  - AWP-7681    0.285 [Validation Scenario   ] IPv4 Static Routes - Unicast Traffic                    :: Check and verify IPv4 Static Routes for correct status and functionality. | step1: Run background unicast traffic in the relevant 
  - AWP-10714   0.267 [PPP                   ] PPP - Operational - IPCP - IPv4 - Static Address        :: Static IPv4 Address configured on a PPP interface | step1: Ping across the ppp link => Traffic traverses the PPP link successfuly
  - AWP-18495   0.259 [Router Bridging       ] Configure IPv4 and IPv6 address on the bridge           :: Configure IPv4 and IPv6 address on the bridge | step1: 1. Configure bridge and assign interfaces 2. Configure ipv4 and ipv6 addres
  - AWP-24173   0.247 [ATMF                  ] Check Ping (IPv4 and IPv6) will be supported            :: Check Ping (IPv4 and IPv6) will be supported | step1: Check Ping (IPv4 and IPv6) will be supported => confirm Ping (IPv4 and IPv6)

### AWPTCM-T47201  |  area: IPv4 BFD  |  feature: With RIP v1/v2
folder:/New Platform Template/IPv4  steps:1  obj:False
  - AWP-12917   0.365 [MLD                   ] MLDv2 interop with v1 host                              :: MLDv2 interop with v1 host | step1: Device with ipv6 mld enabled (default v2) Send in v1 report Send in v1 done => Command accepte
  - AWP-12916   0.326 [MLD                   ] MLD v1 and v2 interop                                   :: Interop of different MLD versions | step1: 2 Devices with MLD enabled Device one operating in V1 mode Device two operating in V2 m
  - AWP-6573    0.290 [RIP                   ] Device Management: Show IP RIP                          :: Verify RIP elements are correctly displayed in show ip rip output. | step1: Configure RIP on DUT Issue show ip rip command => Show
  - AWP-6574    0.260 [RIP                   ] Device Management: RIP Summary                          :: Check RIP commands are correctly reflected in show running-config | step1: Configure RIP on DUT Issue show running-config router r
  - AWP-19394   0.252 [z_ATKK_Inquiry_Based  ] RIP Neighbor                                            :: Scope Verify the number of RIP neighbor that DUT can accept. | step1: Run IxNetwork with the above configuration then execute "sho
  - AWP-3799    0.249 [VRRP                  ] VRRP Interop with RIP                                   :: To verify interoperability between VRRP and RIP | step1: Setup RIP on a VRRP enabled device => Confirm VRRP works with RIP
  - AWP-6577    0.247 [RIP                   ] Device Management: RIP Logging                          :: Check RIP Logging is accurate and useful | step1: Configure RIP and RIP logging on DUT. Issue show log command. => RIP logging is 
  - AWP-7380    0.243 [IPv6 Static Routes and] Show IPv6 RIP/OSPF                                      :: Show commands should display correctly | step1: Issue sh ipv6 rip|ospf command => Command output should be correct and useful

### AWPTCM-T47202  |  area: IPv4 BFD  |  feature: With OSPFv2
folder:/New Platform Template/IPv4  steps:1  obj:False
  - AWP-7718    0.468 [Validation Scenario   ] OSPFv2 - Unicast Traffic                                :: Check and verify OSPFv2 for correct status and functionality. | step1: Run background unicast traffic in the relevant scenario. =>
  - AWP-2636    0.449 [OSPFv3                ] OSPF v3 interop with OSPFv2                             :: OSPF v3 interop with OSPFv2 | step1: Create at least a 3-device network Apply OSPFv2 and OSPFv3 Use show commands to verify OSPFv2
  - AWP-7719    0.353 [Validation Scenario   ] OSPFv2 - Restarting Processes                           :: Check and verify OSPFv2 for correct status and functionality. | step1: Restart processes/protocols (daemon). 3 ways to restart pro
  - AWP-7715    0.352 [Validation Scenario   ] OSPFv2 - Disconnect / Reconnect Links                   :: Check and verify OSPFv2 for correct status and functionality. | step1: Disconnect then reconnect links and check for network recov
  - AWP-7717    0.348 [Validation Scenario   ] OSPFv2 - Add / Delete Configurations                    :: Check and verify OSPFv2 for correct status and functionality. | step1: Update related configurations by adding, removing or changi
  - AWP-7716    0.274 [Validation Scenario   ] OSPFv2 - Hotswap                                        :: Check and verify OSPFv2 for correct status and functionality. | step1: Check and verify that devices operates uninterupted after a
  - AWP-7713    0.264 [Validation Scenario   ] OSPFv2 - Master Failover                                :: Check and verify OSPFv2 for correct status and functionality. | step1: Fail Master device in stack, check for correct recovery, re
  - AWP-7714    0.237 [Validation Scenario   ] OSPFv2 - Slave Failover                                 :: Check and verify <feature> for correct status and functionality. | step1: Fail slave device in stack, check for correct recovery, 

### AWPTCM-T47203  |  area: IPv4 BFD  |  feature: With BGP4
folder:/New Platform Template/IPv4  steps:1  obj:False
  - AWP-13893   0.376 [BGP4+                 ] BGP4+ Device Management - Show Command                  :: Show command output | step1: Show command output => Accurate and useful
  - AWP-14082   0.368 [BGP4+                 ] VRRP Interop with BGP4+                                 :: To verify interoperability between VRRP and BGP4+ | step1: -Setup VRRP and BGP4+ => - Confirm VRRP works with BGP4+
  - AWP-14076   0.316 [BGP4+                 ] Redistribute into BGP4+ from Static routes              :: Confirm that static routes should be displayed on the BGP4+ table | step1: Redistribute into BGP4+ from Static routes Configure fo
  - AWP-14074   0.304 [BGP4+                 ] Redistribute into BGP4+ from OSPFv3                     :: Confirm that OSPFv3 routes should be redistributed into BGP4+ | step1: Redistribute into BGP4+ from OSPFv3 Configure for redistrib
  - AWP-15489   0.293 [Validation Scenario   ] BGP4+ - Unicast Traffic                                 :: Check and verify BGP4+ for correct status and functionality. | step1: Run background unicast traffic in the relevant scenario. => 
  - AWP-13941   0.276 [BGP4+                 ] BGP4+ Graceful-restart on Master after Reboot           :: Test if stack recovers after reboot of master | step1: Enable virtual-mac Configure BGP4+ and advestise routes reboot master After
  - AWP-7404    0.272 [IPv6 Static Routes and] BGP4+ Redistributed to OSPFv3                           :: Using distribution list and route-maps BGP4+ Routes should be redistributed into OSPFv3 | step1: Redistribute BGP4+ routes into OS
  - AWP-14048   0.271 [BGP4+                 ] Static Routes Redistributed to BGP4+                    :: Using distribution lists and route-maps Static Routes should be redistributed into BGP4+ | step1: Redistribute Static Routes into 

### AWPTCM-T47204  |  area: IPv6 BFD  |  feature: With IPv6 Static Routing
folder:/New Platform Template/IPv6  steps:1  obj:False
  - AWP-24185   0.365 [ATMF                  ] Check IPv6 static routes will be supported              :: Check IPv6 static routes will be supported | step1: check IPv6 static routes will be supported => confirm IPv6 static routes are s
  - AWP-15936   0.363 [IPv4                  ] Disabled Static Routing                                 :: Confirm that Static Routing doesn't work when "no ip forwarding" in configured. | step1: Ping to other network address from PC1. =
  - AWP-13665   0.298 [PIM-SMv6              ] Disable - Enable ipv6 multicast routing                 :: Multicast traffic should recover upon disabling and reenabling ipv6 multicast-routing | step1: Setup a working PIM-SMv6 network. S
  - AWP-23349   0.296 [[ATKK] Auto Acceptance] vlan classifier and ip routing on static LAG            :: | step1: send the packet and check DUT route the packet on IP subnet vlan port. => the packet should be routed on vlan10 and vlan2
  - AWP-10063   0.295 [IPv6                  ] Maximum Static IPv6 Neighbors.                          :: Able to configure full table of static IPv6 neighbors | step1: Configure maximum static IPv6 neighbours. Consult with limits datab
  - AWP-5797    0.292 [IPv6                  ] IPv6 Routing Advertisement                              :: Test for command on how to enable IPv6 Routing Advertisement | step1: Enable/disable ipv6 routing advertisement on vlan interface 
  - AWP-7416    0.273 [IPv6 Static Routes and] Maximum IPv6 Routes on all Routing Protocol             :: With maximum routes configured, redistribite this routes with one another and verify that te device will not crash | step1: Enable
  - AWP-12399   0.273 [IPv6 Static Multicast ] Create and remove multicast static route                :: Create and remove static mcast routes. | step1: Enable multicast routing ipv6 multicast-routing Create static route: ipv6 multicas

### AWPTCM-T47205  |  area: QoS DCB  |  feature: Enhanced Transmission Selection  ; 802.1Qaz
folder:/New Platform Template/QoS  steps:1  obj:False
  - AWP-145     0.292 [Customer Scenario     ] EPSR enhanced recovery mode                             :: Confirm Enhanced Recovery mode works correctly. | step1: Confirm ESPR status. => Enhanced Recovery mode works correctly.
  - AWP-4083    0.243 [EPSR, EPSR+, EPSR++   ] Enhanced Recovery - disabled on EPSR Master node (Test  :: Enhanced recovery when it is not enabled on the master | step1: Enhanced recovery when it is not enabled on the master => Refer Su
  - AWP-2128    0.237 [SNMP                  ] RFC1213-MIB-VerifyOID-transmission                      :: RFC1213-MIB II-Verify OID NOT-ACCESSIBLE SNMP Access Type Objects | step1: Verify OID - transmission => OID should be 1.3.6.1.2.1.
  - AWP-9065    0.236 [QoS                   ] QoS globally enabled                                    :: Verify QoS commands are accepted when QoS is globally enabled | step1: qos can be enabled with the command: mls qos enable => Sele
  - AWP-5597    0.228 [LLDP                  ] LLDP-MED Transmission                                   :: Test for the correct transmission of LLDP-MED frames to a switch. | step1: Transmit a valid LLDP-MED frame to the switch and captu
  - AWP-4084    0.218 [EPSR, EPSR+, EPSR++   ] Enhanced Recovery - disabled on EPSR Transit node (Test :: Enhanced recovery when it is not enabled on the transit node | step1: Enhanced recovery when it is not enabled on the transit node
  - AWP-4578    0.195 [PoE                   ] POE Enhanced                                            :: POE ports can be set to enhanced max power 20000mW | step1: Configure ports to max power value of 20000mW. Connect Powered Device 
  - AWP-5086    0.194 [Limits                ] IP host (L3) entries (Enhanced Mode Nexthop)            :: Determine max number of ARP entries. | step1: - using static arp to populate the ip host table => - confirm that there is 5060 ip 

### AWPTCM-T47206  |  area: Redundency Long Distance VCS  |  feature: Stack on Fiber QSFP28
folder:/New Platform Template/Redundancy  steps:1  obj:False
  - AWP-8294    0.355 [IPv4                  ] Static Route Distance Value                             :: Command can define the distance for a certain static route | step1: To add static routes to device, use device to communicate with
  - AWP-21596   0.352 [Active Fiber Monitorin] Disable fiber-monitoring                                :: Verify that fiber-monitoring can be disabled | step1: Enable fiber-monitoring on interface, issue "show system fiber-monitoring" c
  - AWP-21036   0.311 [ATMF                  ] ATMF VM : Static Route Distance Value                   :: Command can define the distance for a certain static route | step1: To add static routes to device, use device to communicate with
  - AWP-21547   0.296 [Active Fiber Monitorin] Fiber monitoring is turned off by default               :: Verify that fiber monitoring is turned-off by default | step1: Execute "show system fiber-minitoring" command => Command accepted 
  - AWP-21631   0.288 [Active Fiber Monitorin] Fiber Monitoring: Debug Command                         :: Enabling and Disabling of debugging command Test that debug command is not written in the running configuration Test that log mess
  - AWP-28501   0.274 [DS-Lite               ] API: Configure DS-Lite default route distance via API   :: DS-Lite must be able to ber configured with a custom default route distance using the API. | step1: Perform API testing to add/rem
  - AWP-28511   0.267 [DS-Lite               ] Check the ds-lite default route has the custom distance :: The DS-Lite default route must be installed into the routing table with the correct custom administrative distance. | step1: Confi
  - AWP-28454   0.263 [DS-Lite               ] CLI: DS-lite default route distance command             :: The DS-Lite feature must have a command to set the administrative distance for the default route via the DS-Lite tunnel. | step1: 

### AWPTCM-T47207  |  area: Redundency  |  feature: 2-unit stacking with Basic license's features
folder:/New Platform Template/Redundancy  steps:1  obj:False
  - AWP-13298   0.357 [Software Licensing    ] VCS:Master with PREMIUM License and Slave with BASIC Li :: VCS:Master with PREMIUM License and Slave with BASIC License only don't stack. | step1: Master with PREMIUM License and Slave with
  - AWP-15261   0.344 [Software Licensing    ] License - Testing bit 12- IPv6 Basic                    :: Testing that license bit correctly turns appropriate feature on or off at : boot time, when a license is added/deleted and when tr
  - AWP-13280   0.341 [Software Licensing    ] Base License contains "IPv6 Basic and MLD Snoop" featur :: Confirm that Base License contains "IPv6 Basic and MLD Snooping" features. | step1: Input"Show License ","show license index | NAM
  - AWP-13291   0.331 [Software Licensing    ] DUT has old license and new BASIC License when FW up.   :: DUT has old license and new BASIC License when FW up. | step1: 1. Input old license key with old Firmware 2. Firmware up to v5.4.3
  - AWP-13281   0.319 [Software Licensing    ] DUT works "IPv6 Basic" feature in BASIC License         :: Confirm that DUT works "IPv6 Basic" feature in BASIC License . | step1: Input "IPv6 Basic feature" features command. IPv6 Basic fe
  - AWP-13283   0.309 [Software Licensing    ] DUT does not delete Basic License when use "no licesnse :: Confirm that DUT does not delete Basic License when use "no licesnse" command. | step1: Input "no license" command. => DUT display
  - AWP-13301   0.275 [Software Licensing    ] x8100:MasterCFC with PREMIUM License and SlaveCFC with  :: x8100:MasterCFC with PREMIUM License and SlaveCFC with BASIC License are established stack.. | step1: MasterCFC with PREMIUM Licen
  - AWP-7032    0.270 [z_Inactive            ] License Bundle - IPv6 (Japan) (x600)                    :: License bundle - IPv6 (Japan) (x600) License Bundle (For 5.4.1) Functional test for each of the features within the license bundle

### AWPTCM-T47495  |  area: QoS  |  feature: Priority Flow Control  ; 802.1Qbb
folder:/New Platform Template/QoS  steps:1  obj:False
  - AWP-9367    0.414 [xSTP                  ] Interop with 802.1x port control                        :: | step1: Interop with 802.1x port control
  - AWP-15367   0.286 [Web Authentication    ] CONTROL                                                 :: CONTROL | step1: Refer to 2.3.2.1.doc => Refer to 2.3.2.1.doc
  - AWP-4428    0.270 [z_Inactive            ] terminal session - test asyn flow control               :: Note: This test case was already included on AWP-4425 terminal session - test asyn flow control | step1: Test asyn terminal settin
  - AWP-14392   0.262 [PoE                   ] Set power-inline priority                               :: power-inline priority <> | step1: Configure PoE priority Syntax: power-inline priority <> => Configure priority and confirm it has
  - AWP-4154    0.254 [Link Aggregation      ] Commands: no lacp port-priority                         :: Ability to remove lacp port-priority Setup: Standalone Config: Default | step1: Configure "no lacp port-priority" NOTE: configure 
  - AWP-4564    0.253 [PoE                   ] POE Priority-Default                                    :: Functional POE Priority Default=Low | step1: show power-inline detail confirms default PoE priority is low. => Confirm default pow
  - AWP-4155    0.242 [Link Aggregation      ] Commands: no lacp system-priority                       :: Ability to remove lacp system-priority Setup: Standalone Config: Default | step1: Configure "no lacp system-priority" NOTE: config
  - AWP-4149    0.233 [Link Aggregation      ] Commands: lacp port-priority                            :: Ability to configure a port priority Setup: Standalone Config: Default | step1: Configure "lacp port-priority <1-1-65535>" Try dif

### AWPTCM-T47871  |  area: Port  |  feature: Link Health Monitoring
folder:/New Platform Template/Port  steps:2  obj:False
ZEPHYR: Configure a link health monitoring with related trigger. Con | show linkmon probe
  - AWP-27508   0.323 [SD-WAN                ] SD-WAN - Historic data for probes                       :: The ability to configure a Link Health Monitoring probe metric history collection instance. | step1: Create linkmon probe-history 
  - AWP-26249   0.319 [SD-WAN                ] SD WAN - Stress Health probe constant state change      :: Ensure that the Health probe goes into the correct state after constantly causing state changes, see CR-56334. Ensure that no memo
  - AWP-26560   0.319 [SD-WAN                ] SD WAN ICMP probe - Health probe DSCP and ToS           :: Ensure that the configured DSCP and/or ToS values for the health probe are applied. | step1: Configure one of the linkmon proes wi
  - AWP-26951   0.279 [SD-WAN                ] SD WAN ICMP probe - Health probe heavy load             :: Determine behaviour of health probes when DUT is under heavy load | step1: Send heavy traffic to the DUT, some of which matches th
  - AWP-26632   0.237 [SD-WAN                ] SD WAN ICMP probe - Multiple health probes single link  :: Ensure that it is possible to configure multiple health probes going accross the same link | step1: Start sending traffic matching
  - AWP-21596   0.229 [Active Fiber Monitorin] Disable fiber-monitoring                                :: Verify that fiber-monitoring can be disabled | step1: Enable fiber-monitoring on interface, issue "show system fiber-monitoring" c
  - AWP-29047   0.219 [SD-WAN                ] SD WAN _ http probe                                     :: to test functionality of http link mon probe | step1: configure http linkmon probe => probe can be configured
  - AWP-27286   0.216 [SD-WAN                ] SD WAN - debug                                          :: Ensure that the debug information is useful and free of spelling errors | step1: Check specific linkmon debug awplus#debug linkmon
