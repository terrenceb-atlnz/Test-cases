# Rerank batch 03  (cases 90..119)

### AWPTCM-T33393  |  area: Management EnhancedOperationManagement  |  feature: Loading Files using Zmodem
folder:/New Platform Template/Management  steps:1  obj:False
ZEPHYR: ZMODEM allows you to copy files from a network host over an
  - AWP-2448    0.662 [z_Inactive            ] File - copy using zmodem                                :: File - copy using zmodem | step1: copy using zmodem => files are copied
  - AWP-6645    0.243 [VLAN                  ] Copy running config to file.cfg                         :: VLAN packet counter configuration can be saved to file.cfg | step1: Command Handler: "enable" CLI level copy running config <file.
  - AWP-17679   0.232 [File System           ] File - command copy - copy to special files             :: File - command copy - copy to special files This specification is applicable from 5.4.3. 5.4.2 or before, "copy [src filename] sta
  - AWP-5478    0.231 [TFTP                  ] TFTP upload                                             :: [version 3] Edited a step because corresponding to CR41795 issue. | step1: TFTP uploads using menu (prompts): Start capture on Cli
  - AWP-5835    0.227 [IPv6 Management       ] TFTP: ipv6 TFTP Client to TFTP Server                   :: Test for successful file transfer using TFTP from Client to server | step1: Copy From TFTP Client to TFTP Server STEPS: 1. Configu
  - AWP-2360    0.221 [z_Inactive            ] File - command copy to new file                         :: File - command copy to new file | step1: File A does not exist on the source media Issue the command COPY A B => Operation fails g
  - AWP-2366    0.214 [z_Inactive            ] File - command copy to special extension named files    :: File - command copy to special extension named files | step1: File A is a text type. File B's extension another different text typ
  - AWP-2361    0.213 [z_Inactive            ] File - command copy to existing file                    :: File - command copy to existing file | step1: File B exists on target media Issue the command COPY A B => Prompted for 'Overwrite 

### AWPTCM-T33394  |  area: Management EnhancedOperationManagement  |  feature: Uploading Files using HTTP
folder:/New Platform Template/Management  steps:2  obj:False
ZEPHYR: On the DUT download a file with http copy http://192.168.1.1 | On the DUT upload a file with http copy test.txt http://192.
  - AWP-22084   0.355 [ATMF                  ] Uploading of guest node firmware works for TQ devices   :: It is to be tested that ATMF support ATMF will support uploading of Guest Node firmware | step1: Connect guest node to DUT => Conf
  - AWP-5497    0.329 [TFTP                  ] TFTP compatibility with AT-TFTP server                  :: Objective: To test TFTP compatibility with a server using AT-TFTP Expected Outcome: TFTP should be able to download and upload fil
  - AWP-22905   0.296 [ATMF                  ] File API: Upload file from device flash                 :: * Able to securely POST a file from user's pc to router via web API to be saved into device flash. * User must be authenticated. *
  - AWP-2450    0.295 [z_Inactive            ] File - copy using http                                  :: File - copy using http | step1: Setup details: TB2 conf - Place a file (filea) to be copied in /var/www Start the http server proc
  - AWP-22906   0.286 [ATMF                  ] File API: Upload file from device flash with firewall e :: * Able to securely POST a file from user's pc to router via web API to be saved into device flash. * User must be authenticated. *
  - AWP-15431   0.270 [Web Authentication    ] HTTP Per Port                                           :: Limits | step1: >> Please see the attached files. => >> Refer to the attached document for expected result (3.4.1.1).
  - AWP-15432   0.262 [Web Authentication    ] HTTP Per Switch                                         :: Limits | step1: >> Please see the attached files. => >> Refer to the attached document for expected result (3.4.1.2).
  - AWP-22184   0.241 [ATMF                  ] Guest node firmware upload is supported on TQ devices   :: ATMF will support uploading of Guest Node firmware | step1: Configure a TQ device as a guest node => Confirm its firmware can be u

### AWPTCM-T33395  |  area: Management EnhancedOperationManagement  |  feature: Uploading Files using TFTP
folder:/New Platform Template/Management  steps:2  obj:False
ZEPHYR: Copy files from a remote file server using TFTP | Copy files from the DUT to a remote file server using TFTP
  - AWP-5497    0.514 [TFTP                  ] TFTP compatibility with AT-TFTP server                  :: Objective: To test TFTP compatibility with a server using AT-TFTP Expected Outcome: TFTP should be able to download and upload fil
  - AWP-5481    0.428 [TFTP                  ] TFTP recovers on port link down and up                  :: TFTP recovers on port link down and link up while uploading or downloading file. | step1: 2.2. => Expect TFTP transfer to recover 
  - AWP-5834    0.369 [IPv6 Management       ] TFTP: ipv6 TFTP Server to TFTP Client                   :: Test for successful file transfer using TFTP from ipv6 Server to ipv6 Client | step1: Copy file from TFTP Server to TFTP Client ST
  - AWP-5835    0.365 [IPv6 Management       ] TFTP: ipv6 TFTP Client to TFTP Server                   :: Test for successful file transfer using TFTP from Client to server | step1: Copy From TFTP Client to TFTP Server STEPS: 1. Configu
  - AWP-5482    0.334 [TFTP                  ] TFTP operation with TFTP server disabled                :: Objective: To test TFTP behaviour when TFTP server is disabled Expected Outcome: TFTP operation should indicate that host is unrea
  - AWP-29160   0.304 [GRE                   ] GRE: TFTP copy files over GRE tunnel between two PC's.  :: This test comes from field issue CR-59790 | step1: TFTP copy files between two PC's over the GRE tunnel => Files should copy wihou
  - AWP-22084   0.303 [ATMF                  ] Uploading of guest node firmware works for TQ devices   :: It is to be tested that ATMF support ATMF will support uploading of Guest Node firmware | step1: Connect guest node to DUT => Conf
  - AWP-5496    0.286 [TFTP                  ] Interop with "standard" Linux TFTP Server               :: | step1: Interop with "standard" Linux TFTP Server => Use testbox

### AWPTCM-T33396  |  area: Management EnhancedOperationManagement  |  feature: Uploading Files using Zmodem
folder:/New Platform Template/Management  steps:1  obj:False
ZEPHYR: ZMODEM allows you to copy files from a network host over an
  - AWP-2448    0.625 [z_Inactive            ] File - copy using zmodem                                :: File - copy using zmodem | step1: copy using zmodem => files are copied
  - AWP-6645    0.230 [VLAN                  ] Copy running config to file.cfg                         :: VLAN packet counter configuration can be saved to file.cfg | step1: Command Handler: "enable" CLI level copy running config <file.
  - AWP-17679   0.219 [File System           ] File - command copy - copy to special files             :: File - command copy - copy to special files This specification is applicable from 5.4.3. 5.4.2 or before, "copy [src filename] sta
  - AWP-5478    0.218 [TFTP                  ] TFTP upload                                             :: [version 3] Edited a step because corresponding to CR41795 issue. | step1: TFTP uploads using menu (prompts): Start capture on Cli
  - AWP-5835    0.215 [IPv6 Management       ] TFTP: ipv6 TFTP Client to TFTP Server                   :: Test for successful file transfer using TFTP from Client to server | step1: Copy From TFTP Client to TFTP Server STEPS: 1. Configu
  - AWP-2360    0.209 [z_Inactive            ] File - command copy to new file                         :: File - command copy to new file | step1: File A does not exist on the source media Issue the command COPY A B => Operation fails g
  - AWP-2366    0.202 [z_Inactive            ] File - command copy to special extension named files    :: File - command copy to special extension named files | step1: File A is a text type. File B's extension another different text typ
  - AWP-2361    0.201 [z_Inactive            ] File - command copy to existing file                    :: File - command copy to existing file | step1: File B exists on target media Issue the command COPY A B => Prompted for 'Overwrite 

### AWPTCM-T33397  |  area: Management IEEE 1588v2PTP  |  feature: End-to-End Transparent Clock
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-24455   0.292 [Port Mirroring        ] Transparent bridging - ATMF management                  :: Ensure that the acquire command is configurable via ATMF | step1: Use the "acquire" command on the bridge interface on DUT1 via an
  - AWP-24311   0.268 [Port Mirroring        ] Transparent bridging - bridge filtering                 :: Determine the interop behaviour when mac-address filtering is configured. | step1: add mac-filter to the bridge => All traffic sho
  - AWP-24454   0.259 [Port Mirroring        ] Transparent bridging - IPv6                             :: Ensure that IPv6 L2TPv3 tunnels can be used in bridges. Ensure that ipv4 and IPv6 unicast and multicast traffic can pass over the 
  - AWP-24305   0.257 [Port Mirroring        ] Transparent bridging - triggers                         :: Ensure that this feature can be configured and reconfigured using trigger scripts | step1: Configure a trigger which implements th
  - AWP-24570   0.254 [Port Mirroring        ] Transparent bridging - Destination mac of router        :: Ensure traffic with the destination mac of the router can be bridged | step1: Set traffic from IXIA1 with a destination mac-addres
  - AWP-24319   0.251 [Port Mirroring        ] Transparent bridging - multiple interfaces              :: Identify behaviour when there are more than just two interfaces in the bridge as well as over multiple different interface types |
  - AWP-24294   0.249 [Port Mirroring        ] Transparent bridging - dynamic reconfiguration          :: Ensure that this feature can be dynamically reconfigured | step1: Use the "acquire" command on the bridge interface => mac address
  - AWP-24327   0.236 [Port Mirroring        ] Transparent bridging - VRF                              :: Determine behaviour when interoperating with a VRF instance. | step1: Add each of the bridges to a VRF instance => packet streams 

### AWPTCM-T33398  |  area: Management LLDP  |  feature: LLDP-Med
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-5691    0.614 [LLDP                  ] LLDP-MED with MAC authentication method                 :: Test for LLDP-MED with MAC authentication setup | step1: Repeat the above tests using MAC authentication instead of dot1x => Tests
  - AWP-5597    0.604 [LLDP                  ] LLDP-MED Transmission                                   :: Test for the correct transmission of LLDP-MED frames to a switch. | step1: Transmit a valid LLDP-MED frame to the switch and captu
  - AWP-5723    0.597 [LLDP                  ] LLDP-MED Security:Reserved LLDP-MED TLV                 :: Test for LLDP-MED security after sending a resevered LLDP-MED TLV | step1: Transmit a reserved LLDP-MED TLV [12-255] => The Unknow
  - AWP-5522    0.595 [LLDP                  ] Command Line Handler: lldp med-notifications            :: Test for lldp med-notifications command configured in port(s). | step1: Command Handler: --> lldp med-notifications --> no lldp me
  - AWP-5612    0.561 [LLDP                  ] LLDP-MED: LLDP-MED TLVs not selected                    :: Test for the LLDP frames will not be transmitted when LLDP-MED TLVs are not selected. | step1: On a port deselect all of the LLDP-
  - AWP-5607    0.551 [LLDP                  ] LLDP-MED: remote entry expiration                       :: Test for the LLDP-MED frames to be sent until the remote entry expire. | step1: Send a valid LLDP-MED frame to the switch verify t
  - AWP-5706    0.533 [LLDP                  ] HighAvailability: LLDP-MED                              :: Test for LLDP-MED frames under High Availability Condition | step1: 1. Connect two switches 2. Enable TLVs on port. 3. Connect IP 
  - AWP-5724    0.532 [LLDP                  ] LLDP-MED Security:Wrong LLDP-MED combination            :: Test for LLDP-MED security after sending a wrong combination of LLDP-MED TLV | step1: Send five different LLDP-MED framed with two

### AWPTCM-T33399  |  area: Management NTP  |  feature: IPv4 NTP Server
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-27159   0.618 [AWC-lite              ] NTP server                                              :: | step1: ip <correct ip address> Confirm that data of NTP server is configured on router.
  - AWP-19385   0.561 [z_ATKK_Inquiry_Based  ] NTP Server                                              :: Scope Confirm that ntp server feature. | step1: Confirm that ntp server feature. ntp packets is sent to registere address, when nt
  - AWP-1118    0.553 [NTP                   ] NTP - AW+ as an NTP server for other device types       :: NTP - Test that AW+ can act as an NTP server for other device types such as a PC | step1: Configure DUT to be NTP server set pc to
  - AWP-1128    0.528 [NTP                   ] NTP - Check NTP packet format                           :: NTP - Check NTP packet format | step1: Capture NTP packets during time sync, refer to RFC and ensure correct. => Packets have corr
  - AWP-1108    0.495 [NTP                   ] NTP - Device can sync time with a windows pc as a ntp s :: NTP - Device can sync time with a window pc as a ntp server | step1: Configure windows pc as a ntp time server Issue sh ntp status
  - AWP-12422   0.491 [NTP                   ] NTP - Test for ntp source command                       :: NTP source command specify a preferred source interface for NTP requests. | step1: Configure DUT with ntp source command => NTP de
  - AWP-10940   0.473 [NTP                   ] NTP over IPv6 - CLI - Configuration                     :: NTP - CLI - Help operation and detail Ensure IPv6 addresses are accepted for server and peer commands | step1: Configure an NTP IP
  - AWP-15944   0.464 [IPv4                  ] NTP operation in "no ip forwarding"                     :: Confirm that NTP works correctly when "no ip forwarding" in configured. | step1: PC1 send NTP request packet. => DUT send NTP pack

### AWPTCM-T33400  |  area: Management NTP  |  feature: IPv4 NTP Client
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-12422   0.525 [NTP                   ] NTP - Test for ntp source command                       :: NTP source command specify a preferred source interface for NTP requests. | step1: Configure DUT with ntp source command => NTP de
  - AWP-1128    0.519 [NTP                   ] NTP - Check NTP packet format                           :: NTP - Check NTP packet format | step1: Capture NTP packets during time sync, refer to RFC and ensure correct. => Packets have corr
  - AWP-27159   0.497 [AWC-lite              ] NTP server                                              :: | step1: ip <correct ip address> Confirm that data of NTP server is configured on router.
  - AWP-1118    0.460 [NTP                   ] NTP - AW+ as an NTP server for other device types       :: NTP - Test that AW+ can act as an NTP server for other device types such as a PC | step1: Configure DUT to be NTP server set pc to
  - AWP-19385   0.459 [z_ATKK_Inquiry_Based  ] NTP Server                                              :: Scope Confirm that ntp server feature. | step1: Confirm that ntp server feature. ntp packets is sent to registere address, when nt
  - AWP-15944   0.456 [IPv4                  ] NTP operation in "no ip forwarding"                     :: Confirm that NTP works correctly when "no ip forwarding" in configured. | step1: PC1 send NTP request packet. => DUT send NTP pack
  - AWP-12423   0.448 [NTP                   ] NTP - Command Line Handler: ntp source command          :: Test for ntp source command. | step1: Command Handler: 1. Issue ntp source <ip address> command. 2. Issue no ntp source command =>
  - AWP-25933   0.441 [NTP                   ] CR-54723 NTP master with NTP source                     :: This test is check for CR-54723. Check that CR-54723 does not occur. CR-54723 : If NTP source is configured, NTP server does not w

### AWPTCM-T33401  |  area: Management Operation  |  feature: Syslog Facility Override
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-24992   0.394 [Log                   ] UTM facility logging long run stress to syslog          :: Test that heavy UTM facility logging to a syslog server and no memory leaks and is stable | step1: Perform a lot of logging to a s
  - AWP-15939   0.371 [IPv4                  ] syslog operation in "no ip forwarding"                  :: Confirm that syslog works correctly when "no ip forwarding" in configured. | step1: Make DUT send any syslog packet. => DUT send s
  - AWP-24177   0.360 [ATMF                  ] Check Syslog will be supported                          :: Check Syslog will be supported | step1: check syslog will be supported => confirm syslog is supported
  - AWP-26694   0.330 [CFM                   ] CLI:show facility-alarm status - Future                 :: Verify "show facility-alarm status" command for CFM. | step1: Verify the "show facility-alarm status" command: show facility-alarm
  - AWP-25651   0.325 [PIM-SM                ] ip pim (vrf NAME|) rp-address A.B.C.D (override |)      :: CLI Test | step1: Ensure that all commands have correct context sensitive help tab auto-complete and check vrf option works correc
  - AWP-22601   0.304 [Logging               ] Change Log facility                                     :: The switch should send a log message which was set by log facility commands. auth security/authorization messages authpriv securit
  - AWP-24977   0.299 [PPP                   ] PPP API - IP-override                                   :: Ensure that the DUT can be configured via the API to use the statically configured IP-address on a given PPP interface over a nego
  - AWP-22537   0.279 [Logging               ] Command Line Handler - log facility                     :: Test that all variations of log facility command and CLI help work | step1: Test log facility command. Use CLI help. => Output is 

### AWPTCM-T33402  |  area: Management Operation  |  feature: Syslog stored in NVS
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-15939   0.426 [IPv4                  ] syslog operation in "no ip forwarding"                  :: Confirm that syslog works correctly when "no ip forwarding" in configured. | step1: Make DUT send any syslog packet. => DUT send s
  - AWP-24177   0.414 [ATMF                  ] Check Syslog will be supported                          :: Check Syslog will be supported | step1: check syslog will be supported => confirm syslog is supported
  - AWP-5075    0.318 [Limits                ] Log - Syslog servers                                    :: Confirm 20 syslog servers can be configured. | step1: Configure up to 20 syslog server => Issue the command "show log config" and 
  - AWP-20582   0.301 [Wireless controller (U] Check Syslog                                            :: Please check Syslog-server when you execute all testcases. (AW+_syslog and ap_syslog) | step1: Set envirnonment. => All APs are ma
  - AWP-19360   0.300 [Wireless controller (U] Check Syslog                                            :: Please check Syslog-server when you execute all testcases. (AW+_syslog and ap_syslog) | step1: Set envirnonment. => All APs are ma
  - AWP-14400   0.291 [Storm Control         ] syslog test                                             :: Syslog is sent to the Syslog server when loop is detected | step1: Enable syslog in the switch and create loops between ports. => 
  - AWP-19166   0.280 [Wireless controller (U] Check Syslog                                            :: [1]Please check Syslog-server when you execute all testcases. (AW+_syslog and ap_syslog) [2]Also, Syslog results should reflect th
  - AWP-9831    0.280 [DHCP Snooping         ] DHCP Snooping - set to write to NVS                     :: Confirm that device is stable and database can be read correctly after restart | step1: Setting to write to nvs (large database) =

### AWPTCM-T33403  |  area: Management Operation  |  feature: Scripting
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-24178   0.753 [ATMF                  ] Check Scripting will be supported                       :: Check Scripting will be supported | step1: create a scripton the container run the script => confirm scripting will be supported
  - AWP-8202    0.142 [BGP                   ] Device Management - Show Command                        :: Show command output | step1: Show command output => Accurate and useful
  - AWP-27241   0.115 [AWC-lite              ] management frame protection                             :: | step1: management frame protection enable Confirm that management frame protection is enabled on router.
  - AWP-27248   0.115 [AWC-lite              ] management frame protection                             :: | step1: management frame protection enable Confirm that management frame protection is enabled on router.
  - AWP-13893   0.113 [BGP4+                 ] BGP4+ Device Management - Show Command                  :: Show command output | step1: Show command output => Accurate and useful
  - AWP-18423   0.102 [Interop               ] Trace operation check                                   :: Confirm whether switch can trace correctly. | step1: Trace to 10.0.0.1 on PC. => Confirm that Trace operation succeeds.
  - AWP-27327   0.101 [AWC-lite              ] Management IP Address                                   :: Configure the management IP address from start tab | step1: Select management IP Address and save it. => The configuration should 
  - AWP-28296   0.101 [[ATKK] Auto Acceptance] Management IP Address                                   :: Configure the management IP address from start tab | step1: Select management IP Address and save it. => The configuration should 

### AWPTCM-T33404  |  area: Management Operation  |  feature: CLI
folder:/New Platform Template/Management  steps:1  obj:True
ZEPHYR: OBJ: Run the ART testsuite 1337_cli_walk ||
  - AWP-1133    0.270 [NTP                   ] NTP - CLI - Help operation and detail                   :: NTP - CLI - Help operation and detail | step1: Test NTP CLI and help => Useful and corrrect help information presented
  - AWP-4508    0.218 [PoE                   ] POE CLI-Error-Messages                                  :: Device Management Command Handler CLI Error messages | step1: CLI Error messages - clear and useful. - stacking environment - powe
  - AWP-8202    0.216 [BGP                   ] Device Management - Show Command                        :: Show command output | step1: Show command output => Accurate and useful
  - AWP-5477    0.202 [TFTP                  ] TFTP CLI operation using prompts and single-line format :: Objective: To verify CLI operation of TFTP using prompts or single-line format Expected Outcome: CLI should accept and execute com
  - AWP-4500    0.189 [PoE                   ] POE CLI-Help                                            :: Device Management Command Handler Command Line Help useful and accurate for all commands | step1: Command Line Help useful and acc
  - AWP-3469    0.187 [PIM-SM                ] CLI to set ip pim passive mode                          :: Command Line test | step1: 1. Login to DUT. 2. Execute the command to enable passive mode operation on local members on the VLAN i
  - AWP-5353    0.182 [OSPF                  ] Disable graceful restart via CLI - check restart operat :: Graceful restart capability is on by default. This test disables the default configuration and ensures OSPF performs a cold restar
  - AWP-7904    0.182 [OSPFv3                ] Disable graceful restart via CLI - check restart operat :: Graceful restart capability is on by default. This test disables the default configuration and ensures OSPF performs a cold restar

### AWPTCM-T33405  |  area: Management Operation  |  feature: Web GUI
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-4265    0.410 [TACACS+               ] TACACS+ GUI                                             :: GUI workaround | step1: Configure GUI user in local and TAC+ server => GUI user should be able to login
  - AWP-4512    0.390 [PoE                   ] POE GUI-Functions                                       :: Device Management GUI Confirm required GUI POE functions work. | step1: Confirm required GUI POE functions work. {not implemented 
  - AWP-3823    0.386 [IPv4                  ] GUI-Access                                              :: GUI-Access Configure local interface on the device, should be able to load the GUI app. | step1: 1. Configure local interface on t
  - AWP-25754   0.380 [Web Control           ] Web-Control: NGFW GUI Works with Web-Control SNI Filter :: The NGFW GUI must be accessable when Web-Control with SNI filtering is enabled. It must work with default action allow and with de
  - AWP-21177   0.374 [GUI Support           ] GUI timeout will be disabled by default                 :: GUI timeout will be disabled by default | step1: Verify that GUI timeout is disabled by default. Erase the start-up config and reb
  - AWP-21179   0.372 [GUI Support           ] GUI Timeout log messages                                :: GUI Timeout commands reflect in the logs | step1: Execute GUI timeout commands => No unnecessary log messages should be present
  - AWP-27327   0.361 [AWC-lite              ] Management IP Address                                   :: Configure the management IP address from start tab | step1: Select management IP Address and save it. => The configuration should 
  - AWP-28296   0.361 [[ATKK] Auto Acceptance] Management IP Address                                   :: Configure the management IP address from start tab | step1: Select management IP Address and save it. => The configuration should 

### AWPTCM-T33406  |  area: Management Operation  |  feature: User authentication DB with strong password
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-14946   0.423 [Web Authentication    ] Strong Web Auth Password                                :: Confirm that Web Auth password can be extened up to 64 characters. This change is due to CR00039536. | step1: Attempt WEB auth fro
  - AWP-6471    0.226 [z_Inactive            ] password login succeeds when no user key available      :: Password Login Tests | step1: Password login succeeds when no user key available - DUT to remote server => Verify user can success
  - AWP-10244   0.217 [Diagnostic Application] Invalid password Test                                   :: Test should not run | step1: test invalid password => test not run
  - AWP-19195   0.211 [Wireless controller (U] Add / Delete entry to Valid AP DB                       :: (1) If AP's MAC is registered in DB as "managed" , AP is managed by WM. (2) If AP's MAC isn't registered in DB , AP isn't managed 
  - AWP-19770   0.211 [Wireless controller (U] Add / Delete entry to Valid AP DB                       :: (1) If AP's MAC is registered in DB as "managed" , AP is managed by WM. (2) If AP's MAC isn't registered in DB , AP isn't managed 
  - AWP-5456    0.205 [RADIUS                ] When over 5000 MAC entries on fdb, execute "copy fdb-ra :: Confirm the MAC entry that exceeds 5000 cannot be registered to Local Radius DB. | step1: When over 5000 mac entries exist on the 
  - AWP-20062   0.203 [Wireless controller (U] Add / Delete eintry to Valid AP DB                      :: (1) If AP's MAC is registered in DB as "managed" , AP is managed by WM. (2) If AP's MAC isn't registered in DB , AP isn't managed 
  - AWP-19175   0.202 [Wireless controller (U] Add / Delete eintry to Valid AP DB                      :: (1) If AP's MAC is registered in DB as "managed" , AP is managed by WM. (2) If AP's MAC isn't registered in DB , AP isn't managed 

### AWPTCM-T33407  |  area: Management RADIUS  |  feature: Local RADIUS Server
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-5388    0.565 [RADIUS                ] Enable Local Radius Server                              :: Confirm that local radius server information should be shown correctly after the local radius server is enabled. | step1: Enter “s
  - AWP-5386    0.559 [RADIUS                ] Local Radius Server information before radius-server lo :: Confirm that local radius authentication doesn’t work at all, before entering “radius-server local” command. | step1: Normal 0 fal
  - AWP-5390    0.529 [RADIUS                ] Local Radius Server - Changing Authentication Port      :: Confirm that local radius server authentication should work correctly after the local radius server authentication port is changed
  - AWP-27244   0.473 [AWC-lite              ] radius / group                                          :: | step1: radius auth group radius Confirm that RADIUS server group is configured on router.
  - AWP-5393    0.436 [RADIUS                ] Local Radius Registration of User                       :: Confirm that a client can be authenticated with local radius user name, and this client should be moved to the group’s vlan by dyn
  - AWP-6982    0.432 [RADIUS                ] License - RADIUS - test that radius server works when a :: Operational - (with local RADIUS server configured with max numbers of users) - test that a user can be authenicated. | step1: Ope
  - AWP-5392    0.430 [RADIUS                ] Local Radius Server Registration of User Group          :: Confirm that a client can be authenticated with local radius group name, and this client should be moved to the group’s vlan by dy
  - AWP-22688   0.430 [RADIUS                ] Local Radius Server - NAS 127.0.0.1                     :: When the local radius server is enabled a NAS of 127.0.0.1 is created by default (shared-key awplus-local-radius-server This confi

### AWPTCM-T33408  |  area: Management RADIUS  |  feature: Radius Client mode
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-15942   0.464 [IPv4                  ] RADIUS Client operation in "no ip forwarding"           :: Confirm that RADIUS Client works correctly when "no ip forwarding" in configured. | step1: Execute Port auth (or User auth) from P
  - AWP-29488   0.411 [OpenFlow              ] RADIUS client                                           :: Confirm that DUT works as Radius client. Confirm that User can login with Radius authentication. | step1: Create a user which is a
  - AWP-24854   0.411 [OpenFlow              ] RADIUS client                                           :: Confirm that DUT works as Radius client. Confirm that User can login with Radius authentication. | step1: Create a user which is a
  - AWP-26457   0.411 [OpenFlow              ] RADIUS client                                           :: Confirm that DUT works as Radius client. Confirm that User can login with Radius authentication. | step1: Create a user which is a
  - AWP-5358    0.403 [RADIUS                ] CLI Test - RADIUS Configuration                         :: RADIUS client settings and parameters can be configured/changed and are properly reflected in RADIUS show commands and in running-
  - AWP-27244   0.403 [AWC-lite              ] radius / group                                          :: | step1: radius auth group radius Confirm that RADIUS server group is configured on router.
  - AWP-20354   0.375 [RADIUS                ] Interoperability of Windows Radius Client and Windows R :: Confirm that DUT can authenticate Windows Radius Client to a Window's Radius Server. | step1: Using a Windows machine as the RADIU
  - AWP-5383    0.372 [RADIUS                ] RADIUS Authentication - Logging Test                    :: Confirm logs for each operation | step1: 1.Login client through 802.1x with radius server authenticated. 2.Login telnet client wit

### AWPTCM-T33409  |  area: Management RADIUS  |  feature: Radius Proxy
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-27244   0.393 [AWC-lite              ] radius / group                                          :: | step1: radius auth group radius Confirm that RADIUS server group is configured on router.
  - AWP-4354    0.375 [ARP                   ] Proxy ARP: Command                                      :: Test proxy-arp command for errors | step1: Check Proxy ARP commands (any parameter) ip proxy-arp no ip proxy-arp Command must be a
  - AWP-27255   0.355 [AWC-lite              ] (MAC) radius auth group                                 :: | step1: mac-auth radius auth group radius Confirm that RADIUS server group is configured on router.
  - AWP-27254   0.345 [AWC-lite              ] (Web) radius auth group                                 :: | step1: web-auth radius auth group radius Confirm that RADIUS server group is configured on router.
  - AWP-6972    0.333 [Software Licensing    ] License - RADIUS-FULL - show command displays radius-10 :: Test; that with a radius-full license applied, radius-100 and radius-full should display. | step1: Test; that with a radius-full l
  - AWP-5358    0.323 [RADIUS                ] CLI Test - RADIUS Configuration                         :: RADIUS client settings and parameters can be configured/changed and are properly reflected in RADIUS show commands and in running-
  - AWP-4356    0.323 [ARP                   ] Local Proxy ARP: Command                                :: Test "ip local-proxy-arp" command | step1: Check Local Proxy ARP commands (any parameter) Command must be accepted and shown in co
  - AWP-15943   0.320 [IPv4                  ] RADIUS Server operation in "no ip forwarding"           :: Confirm that RADIUS Server works correctly when "no ip forwarding" in configured. | step1: Execute Port auth (or User auth) from P

### AWPTCM-T33410  |  area: Management TACACS+  |  feature: Accounting
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-10631   0.474 [TACACS+               ] TACACS+ command accounting privilege levels             :: Testing that TACACS+ command accounting can be configured to account commands that are run at any privilege level ( 1 to 15 ). One
  - AWP-10444   0.464 [TACACS+               ] TACACS+ login accounting - start record                 :: When a user logs in a TACACS+ login accounting start record should be sent to the TACACS+ server. | step1: Login onto DUT Capture 
  - AWP-19982   0.451 [Wireless controller (U] Radius accounting mode / no radius accounting mode      :: radius accounting mode no radius accounting mode show radius accounting show radius accounting statistics | step1: (1)Set the envi
  - AWP-19249   0.438 [Wireless controller (U] Radius accounting mode / no radius accounting mode      :: Wireless manager send information to accounting server | step1: (1)Set the environemnt (2)Set radius accountingserver (3)Set wirel
  - AWP-20687   0.438 [Wireless controller (U] Radius accounting mode / no radius accounting mode      :: Wireless manager send information to accounting server | step1: (1)Set the environemnt (2)Set radius accountingserver (3)Set wirel
  - AWP-5384    0.415 [RADIUS                ] RADIUS Accounting - Logging Test                        :: Confirm logs for each operation. | step1: 1. Configure "aaa accounting dot1x default start-stop group radius" on DUT 2. Login clie
  - AWP-10704   0.414 [TACACS+               ] TACACS+ show accounting statistics (not yet implimented :: This case shall test the following command issued with a user in privilege level 1. ( not yet implimentented; as of 542 - CR34629)
  - AWP-10441   0.413 [TACACS+               ] TACACS+ login accounting - stop record                  :: When a user logs out, a TACACS+ login accounting stop record should be sent to the TACACS+ server. | step1: Login onto DUT Capture

### AWPTCM-T33411  |  area: Management TACACS+  |  feature: Authentication
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-24507   0.515 [ATMF                  ] Authentication using TACACS+ will be supported          :: Authentication using TACACS+ will be supported | step1: Check the support of TACACS+ on vaa => ensure it is working
  - AWP-4261    0.509 [TACACS+               ] TACACS+ Invalid Authentication                          :: Invalid Authentication | step1: Invalid login on console port Invalid login on telnet session Invalid login on SSH session login o
  - AWP-4260    0.492 [TACACS+               ] TACACS+ Valid Authentication                            :: Valid Authentication tests | step1: Valid user login on console port Valid user login on telnet session Valid user login on SSH se
  - AWP-12146   0.446 [TACACS+               ] TACACS+ SSH Login                                       :: Confirm that SSH Login with TACACS server works. | step1: Login User through SSH from TACACS SERVER Commands: service ssh crypto k
  - AWP-24527   0.437 [ATMF                  ] Authentication using TACACS+ will be supported on conta :: Authentication using TACACS+ will be supported on containers | step1: configure tacacs+ on the containers by specifying the tacacs
  - AWP-7830    0.426 [User Login            ] TACACS Auth: Login with valid username and password     :: Check if the users logging in will pass the authentication of the TACACS server | step1: - TACACS server with usernames and passwo
  - AWP-7834    0.404 [User Login            ] TACACS Auth: Login with invalid username and invalid pa :: Check if the users logging in will pass the authentication of the TACACS server | step1: - TACACS server with usernames and passwo
  - AWP-7832    0.401 [User Login            ] TACACS Auth: Login with valid username and invalid pass :: Check if the users logging in will pass the authentication of the TACACS server | step1: - TACACS server with usernames and passwo

### AWPTCM-T33412  |  area: Management TACACS+  |  feature: Logging
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-9337    0.606 [xSTP                  ] Logging                                                 :: | step1: Logging => accurate and useful
  - AWP-6577    0.498 [RIP                   ] Device Management: RIP Logging                          :: Check RIP Logging is accurate and useful | step1: Configure RIP and RIP logging on DUT. Issue show log command. => RIP logging is 
  - AWP-5519    0.494 [LLDP                  ] Logging                                                 :: Check logging is available and usable | step1: Logging is available and useful => Logging can be displayed via the console and the
  - AWP-7830    0.426 [User Login            ] TACACS Auth: Login with valid username and password     :: Check if the users logging in will pass the authentication of the TACACS server | step1: - TACACS server with usernames and passwo
  - AWP-8136    0.421 [z_Inactive            ] Device Management: Excessive logging                    :: Confirm that only used logs are created | step1: Check that there is no excessive logging => Only use full logs are created.
  - AWP-5476    0.415 [TFTP                  ] Logging of debug - Not Supported                        :: Test that debug logging is useful | step1: Logging of Debug accurate and useful => Logging of debug is accurate
  - AWP-8375    0.410 [MLD Snooping          ] Logging for MLD snooping                                :: | step1: Logging exists for MLD Snooping
  - AWP-9626    0.409 [xSTP                  ] MSTP logging                                            :: | step1: MSTP logging => Log entries for MSTP are shown.

### AWPTCM-T33413  |  area: Management Trap  |  feature: Temperature
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-11626   0.493 [Environment Monitoring] Show sys environment - temperature                      :: To check if monitored component temperature was shown in show sys environment and value is correct | step1: Execute the "show syst
  - AWP-10421   0.473 [z_Inactive            ] Show sys environment - temperature                      :: To check if monitored component temperature was shown in show sys environment and value is correct | step1: Indicator value is cor
  - AWP-7427    0.349 [PoE                   ] RPS Temperature LEDs                                    :: | step1: Insert power supply into RPS Bay 'A. (Ensure power is not connected - hot-swapping is not recommended.) Power up RPS Bay 
  - AWP-17855   0.273 [Platform              ] SNMP Traps                                              :: Requirement: -An SNMP trap will generated when the over temperature shutdown is initiated. -An SNMP trap will generated if the ove
  - AWP-18259   0.243 [Platform              ] VCS+ Compatibility                                      :: Description : This testcase is to ensure overtemp does not adversely affect VCS+. PASS Condition: VCS+ partner is not affected by 
  - AWP-6850    0.238 [Port Authentication   ] Port Authentication and SNMP Trap                       :: Port Authentication and SNMP Trap | step1: Refer to 4.3.doc => Refer to 4.3.doc Confirm that the switch sends SNMP trap message to
  - AWP-11639   0.237 [Environment Monitoring] System LED - monitored temp                             :: To check if LED is flashing red colour - 6 flash per period | step1: Monitor the temperature using the command "show system enviro
  - AWP-17786   0.231 [Platform              ] Detect over-temp condition                              :: Requirement : -The system will detect a condition requiring shutdown . - Shutdown will be triggered by an over temperature conditi

### AWPTCM-T33415  |  area: Management Triggers  |  feature: CPU
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-615     0.508 [Triggers              ] CPU Trigger default configuration                       :: Test for CPU triggers | step1: Confirm that the default setting for a CPU trigger is ANY => Default setting for a CPU trigger is A
  - AWP-24179   0.454 [ATMF                  ] Check Triggers will be supported                        :: Check Triggers will be supported | step1: check triggers will be supported => confirm triggers is supported
  - AWP-612     0.368 [Triggers              ] CPU Trigger high limit activation                       :: Test for CPU triggers | step1: Configure a trigger to activate when the CPU exceeds a specified usage level => Trigger activated
  - AWP-613     0.358 [Triggers              ] CPU Trigger low limit activation                        :: Test for CPU triggers | step1: Configure a trigger to activate when the CPU drops below a specified usage level => Trigger activat
  - AWP-4990    0.346 [Limits                ] Triggers                                                :: To verify max trigger can be configured | step1: - Create up to 251 triggers => - Confirm that there is 250 configured triggers - 
  - AWP-8435    0.337 [MLD Snooping          ] IPv6 ACL's to send packets to the CPU                   :: | step1: Create IPv6 ACL's to send packets to the CPU => Multicast traffic should still work
  - AWP-614     0.324 [Triggers              ] CPU Trigger threshold cross activation                  :: Test for CPU triggers | step1: Configure a trigger to activate when the CPU either rises above or drops below a specified usage le
  - AWP-13059   0.297 [Find Me               ] Long Run: Triggers                                      :: Long Run with Triggers | step1: Link some ports to ensure LEDs are up Or ports are active with traffic flowing Create a script (.s

### AWPTCM-T33416  |  area: Management Triggers  |  feature: Interface
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-24179   0.544 [ATMF                  ] Check Triggers will be supported                        :: Check Triggers will be supported | step1: check triggers will be supported => confirm triggers is supported
  - AWP-636     0.434 [Triggers              ] Trigger Stress Test multiple interface triggers         :: Trigger stress test | step1: Activate multiple triggers simultaneously (type=interface) => The DUT must work without any memory le
  - AWP-4990    0.414 [Limits                ] Triggers                                                :: To verify max trigger can be configured | step1: - Create up to 251 triggers => - Confirm that there is 250 configured triggers - 
  - AWP-18506   0.361 [Router Bridging       ] Triggers for bridge interface change state              :: Triggers support link up/down for bridge inteface | step1: 1. Configure a bridge 2. Assign interfaces to the bridge, make sure int
  - AWP-13059   0.356 [Find Me               ] Long Run: Triggers                                      :: Long Run with Triggers | step1: Link some ports to ensure LEDs are up Or ports are active with traffic flowing Create a script (.s
  - AWP-609     0.355 [Triggers              ] Interface Trigger default configuration                 :: Tests for interface triggers | step1: Confirm that the default setting for an Interface trigger is ANY => Trigger activated
  - AWP-597     0.354 [Triggers              ] Interface Trigger link down                             :: Tests for interface triggers | step1: Remove cable from a vlan1 port within a trigger-specified time period => The link goes down 
  - AWP-596     0.348 [Triggers              ] Interface Trigger on reboot                             :: Tests for interface triggers | step1: Reboot a device configured with a link-UP interface trigger, following repeated removal and 

### AWPTCM-T33417  |  area: Management Triggers  |  feature: Memory
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-621     0.518 [Triggers              ] Memory trigger default configuration                    :: Test for memory triggers | step1: Confirm the default value of a Memory trigger is ANY => Default setting for a Memory trigger is 
  - AWP-24179   0.453 [ATMF                  ] Check Triggers will be supported                        :: Check Triggers will be supported | step1: check triggers will be supported => confirm triggers is supported
  - AWP-636     0.381 [Triggers              ] Trigger Stress Test multiple interface triggers         :: Trigger stress test | step1: Activate multiple triggers simultaneously (type=interface) => The DUT must work without any memory le
  - AWP-638     0.374 [Triggers              ] Trigger Stress Test multiple stack triggers             :: Trigger stress test | step1: Activate multiple triggers simultaneously (type=stack) => The DUT must work without any memory leak o
  - AWP-634     0.374 [Triggers              ] Trigger Stress Test multiple time triggers              :: Trigger stress test | step1: Activate multiple triggers simultaneously (type=time) => The DUT must work without any memory leak or
  - AWP-619     0.354 [Triggers              ] Memory trigger high limit activation                    :: Tests for memory triggers | step1: Configure a trigger to run scripts (both .sh and .scp) when memory usage exceeds a specified le
  - AWP-620     0.345 [Triggers              ] Memory trigger low limit activation                     :: Tests for memory triggers | step1: Configure a trigger to run scripts (both .sh and .scp) when memory usage drops below a specifie
  - AWP-4990    0.345 [Limits                ] Triggers                                                :: To verify max trigger can be configured | step1: - Create up to 251 triggers => - Confirm that there is 250 configured triggers - 

### AWPTCM-T33418  |  area: Management Triggers  |  feature: Interval
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-24179   0.422 [ATMF                  ] Check Triggers will be supported                        :: Check Triggers will be supported | step1: check triggers will be supported => confirm triggers is supported
  - AWP-21561   0.346 [Active Fiber Monitorin] Configuring polling interval                            :: Verify that polling interval can be configured | step1: Under interface configuration mode, change the polling interval by "fiber-
  - AWP-10494   0.342 [z_Inactive            ] UDLD Message Interval                                   :: Send UDLD packet per term of message interval | step1: Enable UDLD. Check if device transmit UDLD packets based on the message int
  - AWP-7054    0.340 [IGMP                  ] Standard Test - Query Interval                          :: Confirm that the Query packet is sent by the Querier at the Query interval. | step1: 1.Set up the DUT. 2.Start capture. 3.Check at
  - AWP-27377   0.330 [AWC-lite              ] Profile ext:Interval                                    :: | step1: Create profile and attached network to it. => 1)Those configuration should appear on Access point page. 2)The devise shou
  - AWP-4990    0.321 [Limits                ] Triggers                                                :: To verify max trigger can be configured | step1: - Create up to 251 triggers => - Confirm that there is 250 configured triggers - 
  - AWP-13579   0.319 [OSPF                  ] OSPF Retransmit interval                                :: Test case to verify CR00036359 | step1: On the interface configuration mode, issue the command " ip ospf retransmit-interval ? " =
  - AWP-18520   0.317 [Dynamic DNS           ] Registration interval                                   :: Test that registration interval can be set and functional | step1: 1. Configure DDNS service provider and account 2. Configure int

### AWPTCM-T33419  |  area: Management Triggers  |  feature: Time
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-24179   0.497 [ATMF                  ] Check Triggers will be supported                        :: Check Triggers will be supported | step1: check triggers will be supported => confirm triggers is supported
  - AWP-634     0.464 [Triggers              ] Trigger Stress Test multiple time triggers              :: Trigger stress test | step1: Activate multiple triggers simultaneously (type=time) => The DUT must work without any memory leak or
  - AWP-598     0.388 [Triggers              ] Interface Trigger time parameter - AFTER                :: Tests for interface triggers | step1: Insert a removed cable at a time after the trigger's AFTER parameter value => The link becom
  - AWP-611     0.380 [Triggers              ] Time Trigger default setting                            :: Test for time triggers | step1: Confirm that the default setting for a Time trigger is 00:00:00 (ANY) => Trigger activated
  - AWP-4990    0.379 [Limits                ] Triggers                                                :: To verify max trigger can be configured | step1: - Create up to 251 triggers => - Confirm that there is 250 configured triggers - 
  - AWP-610     0.351 [Triggers              ] Time Trigger with scripts                               :: Test for time triggers | step1: Configure a trigger to run scripts (both .sh and .scp) at a set time when the trigger is activated
  - AWP-599     0.341 [Triggers              ] Interface Trigger time parameter - BEFORE               :: Tests for interface triggers | step1: Remove a cable at a time before the trigger's BEFORE parameter value => Trigger activated
  - AWP-13059   0.325 [Find Me               ] Long Run: Triggers                                      :: Long Run with Triggers | step1: Link some ports to ensure LEDs are up Or ports are active with traffic flowing Create a script (.s

### AWPTCM-T33420  |  area: Management Triggers  |  feature: Ping Polling
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-15363   0.694 [Web Authentication    ] Ping Polling                                            :: Ping Polling | step1: Refer to 2.4.1.doc => Refer to 2.4.1.doc
  - AWP-15366   0.620 [Web Authentication    ] Ping Polling - Error Message Check                      :: Ping Polling - Error Message Check | step1: Refer to 2.4.4.doc => Refer to 2.4.4.doc
  - AWP-15365   0.618 [Web Authentication    ] Ping Polling - Timeout                                  :: Ping Polling - Timeout | step1: Refer to 2.4.3.doc => Refer to 2.4.3.doc
  - AWP-15364   0.475 [Web Authentication    ] Ping Polling - Failcount                                :: Ping Polling - Failcount | step1: Refer to 2.4.2.doc => Refer to 2.4.2.doc
  - AWP-8722    0.439 [sFlow                 ] Configure sflow on vlan for polling or sampling         :: | step1: Configure sflow on the vlan for polling or sampling => Confirmed that sflow configuration is not allowed
  - AWP-10223   0.438 [Diagnostic Application] Stress test for multiple ping-poll sessions             :: Simultaneous ping-poll sessions should be stable for over a period of time | step1: Perform ping-polling sress test. Setup three s
  - AWP-8734    0.408 [sFlow                 ] Configure on some ports with sflow for polling and samp :: | step1: Configure on some ports with sflow for polling and sampling => confirm that packets can be sent out with samples and coun
  - AWP-21561   0.395 [Active Fiber Monitorin] Configuring polling interval                            :: Verify that polling interval can be configured | step1: Under interface configuration mode, change the polling interval by "fiber-

### AWPTCM-T33421  |  area: Management Triggers  |  feature: Reboot
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-24179   0.512 [ATMF                  ] Check Triggers will be supported                        :: Check Triggers will be supported | step1: check triggers will be supported => confirm triggers is supported
  - AWP-4990    0.391 [Limits                ] Triggers                                                :: To verify max trigger can be configured | step1: - Create up to 251 triggers => - Confirm that there is 250 configured triggers - 
  - AWP-596     0.377 [Triggers              ] Interface Trigger on reboot                             :: Tests for interface triggers | step1: Reboot a device configured with a link-UP interface trigger, following repeated removal and 
  - AWP-29308   0.364 [5.4.8-2 Development   ] AP Management after reboot the switch                   :: Confirm that AP Management after reboot the switch. | step1: Connect AP and confirm AP status become "Managd".
  - AWP-13059   0.335 [Find Me               ] Long Run: Triggers                                      :: Long Run with Triggers | step1: Link some ports to ensure LEDs are up Or ports are active with traffic flowing Create a script (.s
  - AWP-563     0.321 [Triggers              ] Max Number of Triggers                                  :: Tests for basic trigger CLI commands | step1: Create 250 triggers => Triggers 1-250 display accurately in sh running-config, sh tr
  - AWP-636     0.321 [Triggers              ] Trigger Stress Test multiple interface triggers         :: Trigger stress test | step1: Activate multiple triggers simultaneously (type=interface) => The DUT must work without any memory le
  - AWP-638     0.315 [Triggers              ] Trigger Stress Test multiple stack triggers             :: Trigger stress test | step1: Activate multiple triggers simultaneously (type=stack) => The DUT must work without any memory leak o

### AWPTCM-T33423  |  area: Management Triggers  |  feature: USB or external media
folder:/New Platform Template/Management  steps:1  obj:False
  - AWP-25778   0.600 [Logging               ] Configure USB with no external media                    :: Configure USB with no media | step1: Input the configuration. log external usb:/log/messages.log log external level informational 
  - AWP-25771   0.563 [Logging               ] Configure logging command with external media           :: Configure logging command with external media | step1: Create log file on external media. usb:/messages.log Insert external media.
  - AWP-25834   0.515 [Logging               ] Change log file configuration.                          :: Change the configuration to other file name. | step1: log external usb:/messages.log => the log file is created in external media.
  - AWP-25783   0.511 [Logging               ] Change to new media.                                    :: Setup the attachment configuration. (Choose usb or card.) | step1: Setup configuration and Insert external media.
  - AWP-25792   0.510 [Logging               ] Hotswap and in external media.                          :: | step1: Setup configuration and Insert external media. => Check the log external media.
  - AWP-25835   0.502 [Logging               ] log external command with USB/card trigger              :: log external command with USB/card trigger. The trigger works after remove/insert. The trigger does not work when unmount external
  - AWP-25797   0.473 [Logging               ] Unmount external media on CFC                           :: S2028.4.10 unmount [ card | usb ] [ member <1-8>| card <X.X-Y.Y>] (Privileged Exec mode) | step1: Setup configuration and Insert e
  - AWP-25780   0.472 [Logging               ] Disable logging to external media feature               :: Disable logging to external media feature | step1: Input the configuration and insert external media. log external usb:/log/messag

### AWPTCM-T33427  |  area: Management  |  feature: Flexera Licensing
folder:/New Platform Template/Management  steps:1  obj:False
ZEPHYR: 1. Request Chris Robb to generate a Flexera License for a pa
  - AWP-28279   0.353 [Flexera Subscription L] Flexera license API - license installed correctly       :: Insure that a license can be transferred and installed correctly via the api. | step1: Using the API transfer a license to the DUT
  - AWP-29520   0.339 [OpenFlow              ] Add subscription license to DUT with feature license be :: Check the combination of new feature license and subscription license. Removal/expiration of either one of the licenses will have 
  - AWP-28268   0.339 [OpenFlow              ] Add subscription license to DUT with feature license be :: Check the combination of new feature license and subscription license. Removal/expiration of either one of the licenses will have 
  - AWP-26985   0.339 [OpenFlow              ] Add subscription license to DUT with feature license be :: Check the combination of new feature license and subscription license. Removal/expiration of either one of the licenses will have 
  - AWP-29441   0.334 [OpenFlow              ] License -Switch License-                                :: Enable other license before the license in used is expired. Confirm that information of licnese updated. Confirm that OpenFlow wor
  - AWP-24846   0.334 [OpenFlow              ] License -Switch License-                                :: Enable other license before the license in used is expired. Confirm that information of licnese updated. Confirm that OpenFlow wor
  - AWP-26517   0.334 [OpenFlow              ] License -Switch License-                                :: Enable other license before the license in used is expired. Confirm that information of licnese updated. Confirm that OpenFlow wor
  - AWP-26507   0.334 [OpenFlow              ] License -Switch License-                                :: Enable other license before the license in used is expired. Confirm that information of licnese updated. Confirm that OpenFlow wor
