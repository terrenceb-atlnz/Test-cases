# Rerank batch 05  (cases 150..179)

### AWPTCM-T38768  |  area: Diagnostics Menu  |  feature: Flash Test
folder:/Bootloader  steps:1  obj:False
  - AWP-2763    0.453 [Bootloader            ] Bootloader - Diagnostic menu stage 2 - option 2 Test Fl :: Bootloader Diagnostic Shell (Stage 2) menu functionality check Test access to level 2 of Diagnostic menu and run option 2 Test Fla
  - AWP-2764    0.380 [Bootloader            ] Bootloader - Diagnostic menu stage 2 - option 4 Erase F :: Bootloader Diagnostic Shell (Stage 2) menu functionality check Test access to level 2 of Diagnostic menu and run option 4 Erase Fl
  - AWP-2759    0.379 [Bootloader            ] Bootloader - Diagnostic menu - option 7 - goto menu sta :: Bootloader Diagnostic Shell (Stage 1) menu functionality check Test that the diagnostic menu option 7 gets you to stage 2 menu. Au
  - AWP-2762    0.369 [Bootloader            ] Bootloader - Diagnostic menu stage 2 - option 0         :: Bootloader Diagnostic Shell (Stage 2) menu functionality check Test access to level 2 of Diagnostic menu and run option 0 - Reboot
  - AWP-2743    0.343 [Bootloader            ] Bootloader diagnostics- cli - check for invalid chars.  :: Testing error cases: * try unexpected keys (!@$#$^*(){:”) instead of the standard menu options Test Bootloader diagnostics cli - c
  - AWP-18957   0.337 [Bootloader            ] Bootloader Hidden feature , =program                    :: The feature in bootloader to config devices personality - same functionality as epi3mk command. | step1: Boot device and enter boo
  - AWP-22138   0.324 [Bootloader            ] Bootloader - Hidden feature =program                    :: The feature in bootloader to config devices personality - same functionality as epi3mk command. WIKI page - http://intranet.atlnz.
  - AWP-2680    0.321 [Bootloader            ] Bootloader - one-off menu - return a level              :: Bootloader menu: " 1. Perform one-off boot from alternate source" should perform one-off boot Test that when files are displayed t

### AWPTCM-T38769  |  area: Diagnostics Menu  |  feature: Erase Flash
folder:/Bootloader  steps:1  obj:False
  - AWP-2764    0.492 [Bootloader            ] Bootloader - Diagnostic menu stage 2 - option 4 Erase F :: Bootloader Diagnostic Shell (Stage 2) menu functionality check Test access to level 2 of Diagnostic menu and run option 4 Erase Fl
  - AWP-2763    0.401 [Bootloader            ] Bootloader - Diagnostic menu stage 2 - option 2 Test Fl :: Bootloader Diagnostic Shell (Stage 2) menu functionality check Test access to level 2 of Diagnostic menu and run option 2 Test Fla
  - AWP-2759    0.360 [Bootloader            ] Bootloader - Diagnostic menu - option 7 - goto menu sta :: Bootloader Diagnostic Shell (Stage 1) menu functionality check Test that the diagnostic menu option 7 gets you to stage 2 menu. Au
  - AWP-18957   0.357 [Bootloader            ] Bootloader Hidden feature , =program                    :: The feature in bootloader to config devices personality - same functionality as epi3mk command. | step1: Boot device and enter boo
  - AWP-17781   0.333 [ATMF                  ] Warning message with atmf cleanup / erase factory-defau :: Warning message shown when command issued | step1: Issue command "atmf cleanup" or erase factory-default => Confirm the following 
  - AWP-17782   0.329 [ATMF                  ] atmf cleanup / erase factory default clears nvs and fla :: DUT with release, backup release and v1 / v2 licence files | step1: Issue atmf cleanup / erase factory default and choose 'y' => C
  - AWP-17783   0.305 [ATMF                  ] Issue atmf cleanup / erase factory-default with VCS+ or :: DUT is more than 1 device (2 stack device) or in VCS+ | step1: Issue atmf cleanup / erase factory-default => Confirm the command f
  - AWP-22138   0.301 [Bootloader            ] Bootloader - Hidden feature =program                    :: The feature in bootloader to config devices personality - same functionality as epi3mk command. WIKI page - http://intranet.atlnz.

### AWPTCM-T38770  |  area: u-boot Shell  |  feature: printenv command
folder:/Bootloader  steps:1  obj:False
  - AWP-2742    0.388 [Bootloader            ] Bootloader - u-boot CLI - printenv                      :: Personality Programming using Bootloader shell * Uboot can programming base unit * Uboot can show pensonality of base unit * Uboot
  - AWP-2720    0.278 [Bootloader            ] Bootloader - Restore bootloader factory settings - deve :: Bootloader menu: "7. Restore Bootloader factory settings" should work Bootloader - Restore bootloader factory settings - developer
  - AWP-18392   0.241 [User Login            ] Force Default Password Change (FDPC) - U-boot environme :: Objective: This test will verify that the DUT allows access to U-boot boot loader and set a boot environment variable "relargs". E
  - AWP-3604    0.205 [File System           ] Check command for boot config ?                         :: Ensure boot config help command is helpful | step1: 1) issue command help "boot config ?" => Ensure it contain information for con
  - AWP-793     0.202 [Qualification         ] boot system' command                                    :: Check "boot system" command exists | step1: Check "boot system" command => TEST PASS: if there is a boot system from card option i
  - AWP-794     0.195 [Qualification         ] boot config-file' command                               :: Check "boot config-file" command exists | step1: Check "boot config-file" command => TEST PASS: if there is a boot config-file fro
  - AWP-3603    0.193 [File System           ] Check command for boot system ?                         :: Ensure boot system help command is helpful | step1: 1) issue command help "boot system ?" => Ensure it contain information for con
  - AWP-22523   0.169 [Bootloader            ] Bootloader - u-boot CLI - fw_setenv                     :: Use 'fw_setenv' to modify the environment. | step1: From start-shell in Linux, use fw_setenv to modify the environment. eg: fw_set

### AWPTCM-T38771  |  area: u-boot Shell  |  feature: bdinfo command
folder:/Bootloader  steps:1  obj:False
  - AWP-22274   0.266 [Bootloader            ] Bootloader - Memory size                                :: Check that bootloader option 6 (system information) and u-boot (bdinfo command) displays the correct memory size for the device. M
  - AWP-3604    0.193 [File System           ] Check command for boot config ?                         :: Ensure boot config help command is helpful | step1: 1) issue command help "boot config ?" => Ensure it contain information for con
  - AWP-793     0.191 [Qualification         ] boot system' command                                    :: Check "boot system" command exists | step1: Check "boot system" command => TEST PASS: if there is a boot system from card option i
  - AWP-794     0.184 [Qualification         ] boot config-file' command                               :: Check "boot config-file" command exists | step1: Check "boot config-file" command => TEST PASS: if there is a boot config-file fro
  - AWP-3603    0.183 [File System           ] Check command for boot system ?                         :: Ensure boot system help command is helpful | step1: 1) issue command help "boot system ?" => Ensure it contain information for con
  - AWP-3601    0.152 [File System           ] Check command for show boot                             :: To ensure show boot contain information when boot / config being configured to read from card. Also there should be configured bac
  - AWP-2729    0.149 [Bootloader            ] Bootloader - Access to u-boot shell                     :: Test Functionality of Bootloader shell. Test Bootloader - Access to u-boot shell Automated: http://intranet.atlnz.lc/systest/ATPyL
  - AWP-18050   0.147 [Bootloader            ] Bootloader - u-boot CLI - date command - user can set d :: Date command in the u-boot is used by the factory to set the time and date on AW+ products. Automated: http://intranet.atlnz.lc/sy

### AWPTCM-T38772  |  area: u-boot Shell  |  feature: fw_setenv command
folder:/Bootloader  steps:1  obj:False
  - AWP-27178   0.335 [AWC-lite              ] use FW for other model                                  :: | step1: Confirm that error message of failure of FW update is dispalyed on router.
  - AWP-22523   0.296 [Bootloader            ] Bootloader - u-boot CLI - fw_setenv                     :: Use 'fw_setenv' to modify the environment. | step1: From start-shell in Linux, use fw_setenv to modify the environment. eg: fw_set
  - AWP-2672    0.286 [Bootloader            ] Bootloader - Boot Menu - option 0 in sub-menu to go bac :: Bootloader - Be able to back up a menu level by entering '0' (zero) or 'n' ( for no) | step1: select "0" or 'n' to 'Return to a pr
  - AWP-13291   0.234 [Software Licensing    ] DUT has old license and new BASIC License when FW up.   :: DUT has old license and new BASIC License when FW up. | step1: 1. Input old license key with old Firmware 2. Firmware up to v5.4.3
  - AWP-27180   0.233 [AWC-lite              ] FW update of AP which failed to update once             :: | step1: Confirm that operation is completed even if the operation fail.
  - AWP-27174   0.232 [AWC-lite              ] FW update of multiple APs (multiple model)              :: | step1: Confirm that user cannot upgrade AP firmware with multiple AP at a time when user select different model APs.
  - AWP-18041   0.232 [Customer Scenario     ] ISSU FW Version Up                                      :: Confirm that ISSU works correctly. This feature is very important for user. | step1: Confirm that ISSU works correctly in the your
  - AWP-23776   0.225 [QoS                   ] change fw (ver.5.4.4 to 5.4.6)                          :: check vlan acl action for fw ver up and down 5.4.4-1.13 ----> 5.4.6 2.x 5.4.6 2.x -----> 5.4.4 4.13 this item can test only x900 s

### AWPTCM-T38773  |  area: u-boot Shell  |  feature: idprom
folder:/Bootloader  steps:1  obj:False
  - AWP-11516   0.277 [Bootloader            ] Bootloader - u-boot CLI - idprom command (x8100 CFC or  :: Bootloader is able to program local and backplane facing IDPROM Bootloader is able to update local and backplane facing IDPROM Boo
  - AWP-22139   0.236 [Bootloader            ] Bootloader - XLEM Hidden feature , =program, Baseboard  :: The feature in bootloader to config devices personality - same functionality as epi3mk command. WIKI page - http://intranet.atlnz.
  - AWP-22140   0.234 [Bootloader            ] Bootloader - XLEM Hidden feature , =program, Expansion  :: The feature in bootloader to config devices personality - same functionality as epi3mk command. WIKI page - http://intranet.atlnz.
  - AWP-22138   0.182 [Bootloader            ] Bootloader - Hidden feature =program                    :: The feature in bootloader to config devices personality - same functionality as epi3mk command. WIKI page - http://intranet.atlnz.
  - AWP-2766    0.156 [Bootloader            ] Bootloader - Diagnostic menu stage 2 - option 8 Quit to :: Bootloader Diagnostic Shell (Stage 2) menu functionality check Test access to level 2 of Diagnostic menu and run option 8 - Quit t
  - AWP-3604    0.151 [File System           ] Check command for boot config ?                         :: Ensure boot config help command is helpful | step1: 1) issue command help "boot config ?" => Ensure it contain information for con
  - AWP-793     0.151 [Qualification         ] boot system' command                                    :: Check "boot system" command exists | step1: Check "boot system" command => TEST PASS: if there is a boot system from card option i
  - AWP-2729    0.150 [Bootloader            ] Bootloader - Access to u-boot shell                     :: Test Functionality of Bootloader shell. Test Bootloader - Access to u-boot shell Automated: http://intranet.atlnz.lc/systest/ATPyL

### AWPTCM-T38774  |  area:   |  feature: Hidden function =PROGRAM
folder:/Bootloader  steps:1  obj:False
  - AWP-18957   0.299 [Bootloader            ] Bootloader Hidden feature , =program                    :: The feature in bootloader to config devices personality - same functionality as epi3mk command. | step1: Boot device and enter boo
  - AWP-21797   0.298 [ATMF                  ] VAA License : Base License on VAA will be hidden        :: It is to be tested that the base license on the VAA is hidden. | step1: Install VAA image in virtual machine and boot VAA => VAA s
  - AWP-9773    0.294 [DHCP Snooping         ] DHCP Snooping - Log buffered program option             :: Log message for log buffered program option can filter DHCP snooping | step1: "Log buffered program" option can filter DHCP Snoopi
  - AWP-22138   0.279 [Bootloader            ] Bootloader - Hidden feature =program                    :: The feature in bootloader to config devices personality - same functionality as epi3mk command. WIKI page - http://intranet.atlnz.
  - AWP-24576   0.266 [ATMF                  ] Check hidden block command cannot be used by privilege  :: | step1: 1) Add privilege 1 level user account 2) Login as that privilege 1 user 3) Do 'ip block <ip-address>' 4) Do ' ip port-do 
  - AWP-25774   0.215 [Logging               ] Configure log message with filter.                      :: S2028.4.2 [no] log external [level <level>] [program <program-name>] [facility <facility>] [msgtext <text-string>] | step1: Insert
  - AWP-22139   0.192 [Bootloader            ] Bootloader - XLEM Hidden feature , =program, Baseboard  :: The feature in bootloader to config devices personality - same functionality as epi3mk command. WIKI page - http://intranet.atlnz.
  - AWP-22140   0.190 [Bootloader            ] Bootloader - XLEM Hidden feature , =program, Expansion  :: The feature in bootloader to config devices personality - same functionality as epi3mk command. WIKI page - http://intranet.atlnz.

### AWPTCM-T41263  |  area:   |  feature: 1335_pbr
folder:/ART Testsuites  steps:1  obj:False
  - AWP-21506   0.285 [Policy Based Routing  ] PBR CLI: PBR rule                                       :: Test that command can be executed and deleted | step1: Configure a pbr rule => Test that command can be executed in the correct mo
  - AWP-7618    0.285 [Policy Based Routing  ] VCS - apply PBR to ingress ports                        :: Confim that PBR can be applied to the ingress ports in a VCS environment | step1: Able to apply PBR to the ingress ports in a VCS 
  - AWP-21618   0.269 [Policy Based Routing  ] PBR for Routers: IPv4 PBR and VRRP interoperability     :: Test that when both PBR and VRRP is enabled, both of the features works properly | step1: Configure PBR on device => Commands are 
  - AWP-7639    0.263 [Policy Based Routing  ] PBR on a secondary next hop IP address                  :: Confirm that PBR should work for a secondary next hop IP address | step1: PBR should work well for a secondary next hop IP address
  - AWP-21610   0.256 [Policy Based Routing  ] PBR for Routers: Show commands                          :: Test that show comands displays correct and accurate information Test show policy-based routing routes Test Show policy-based coun
  - AWP-21611   0.254 [Policy Based Routing  ] PBR for Routers: Show commands included in show tech su :: Test that pbr show commands are included in the tech support output | step1: - Do a show tech support => - Verify that show pbr ru
  - AWP-21619   0.251 [Policy Based Routing  ] PBR for Routers: IPv6 PBR and VRRPv3 Interop            :: Test that when both PBR and VRRPv3 is enabled, both feaure works properly | step1: Configure IPv6 PBR on device => Commands are ac
  - AWP-7633    0.245 [Policy Based Routing  ] Combination of regular and PBR traffic                  :: Confirm that the combination of regular and PBR traffic can be applied | step1: A combination of regular and PBR traffic. Mixture 

### AWPTCM-T41264  |  area:   |  feature: 1336_acl
folder:/ART Testsuites  steps:1  obj:False
  - AWP-8435    0.469 [MLD Snooping          ] IPv6 ACL's to send packets to the CPU                   :: | step1: Create IPv6 ACL's to send packets to the CPU => Multicast traffic should still work
  - AWP-9714    0.444 [DHCP Snooping         ] show ip dhcp snooping acl                               :: "show ip dhcp snooping acl" should show correct output | step1: show ip dhcp snooping acl => Ref UIDv8 for show ip dhcp snooping a
  - AWP-9846    0.402 [DHCP Snooping         ] DHCP Snooping - other ACL configuration                 :: Confirm that behavior is predictable as per ACL configuration | step1: Other ACL configurations that include DHCPSNOOPING - eg => 
  - AWP-9889    0.380 [DHCP Snooping         ] DHCP Snooping - full ACL tables - maximum entries       :: Confirm that attaching ACL to port should fail | step1: Configure DHCP Snooping ACL with full ACL tables - maximum entries on swit
  - AWP-15522   0.364 [RADIUS                ] Hardware ACL with downloadable ACL                      :: Confirm that Downloadable ACL works preferentially than Hardware ACL when those ACL is configured on same port. | step1: Execute a
  - AWP-9723    0.358 [DHCP Snooping         ] DHCP Snooping ACL command - startup config              :: ACL commands for DHCP snooping can be saved to startup config | step1: ACL commands for DHCP SNOOPING entry - write to startup and
  - AWP-8580    0.355 [ACL                   ] ACL: Standard - Command Handler                         :: ACL: Standard - Command Handler | step1: Check command handler for ACL standard Command execution (ranges) Negation of commands Co
  - AWP-6895    0.354 [Port Authentication   ] Auth-fail VLAN - MAC-auth / Auth-fail vlan on / ACL on  :: [Note] On 5.4.5-0.x, try this test on interface mode or auth-config mode. MAC-auth / Auth-fail vlan on / ACL on / | step1: MAC-aut

### AWPTCM-T41265  |  area:   |  feature: 1344_qos
folder:/ART Testsuites  steps:1  obj:False
  - AWP-9065    0.269 [QoS                   ] QoS globally enabled                                    :: Verify QoS commands are accepted when QoS is globally enabled | step1: qos can be enabled with the command: mls qos enable => Sele
  - AWP-10099   0.234 [IPv6                  ] IPv6 Address - QoS field works                          :: QoS output should reflect input QoS field | step1: QOS field works - output queue reflects input QoS field => Output queue reflect
  - AWP-21078   0.199 [QoS                   ] Command Handler: QoS                                    :: Verify command work properly | step1: Check 'qos' commands for: =>Command execution (sh run, sh run int port <range>) =>Negation o
  - AWP-7627    0.196 [Policy Based Routing  ] QoS configuration applied to the classified traffic     :: Confirm that QoS continue to function and not affected by PBR | step1: QoS configuration (eg. set commands under policy map) can b
  - AWP-13659   0.193 [ACL                   ] Interoperability with QoS                               :: ACLs be able to enable when QoS is set on ports. And can execute inset-before. | step1: Insert, move and remove ACL to a port set 
  - AWP-9064    0.181 [QoS                   ] QoS Global Disabled State - commands return error       :: Verify QoS commands will return error messages when QoS is globally disabled | step1: With mls qos disabled execute QOS commands. 
  - AWP-21494   0.175 [ACL                   ] Large IPv6 ACL group with max QoS utilization           :: Large extended ACL group should not affect QoS utilization | step1: 1. Fill-up QoS and ACL table Check "sh platform classifier sta
  - AWP-21493   0.174 [ACL                   ] Large IPv4 ACL group with max QoS utilization           :: Large extended ACL group should not affect QoS utilization | step1: 1. Fill-up QoS and ACL table Check "sh platform classifier sta

### AWPTCM-T41266  |  area:   |  feature: 5000_mdi_mdix
folder:/ART Testsuites  steps:1  obj:False
  - AWP-26897   0.441 [Green Features (Ecofri] 5G_Fixed Copper_Cross / 5G / Auto / MDI-MDIX            :: Verify LPI works with 5Gbit / Auto / MDI-MDIX | step1: Set DUT and partner device: Speed = 5000 Duplex = Auto Polarity = DUT-MDI, 
  - AWP-12285   0.402 [Green Features (Ecofri] Auto_Fixed Copper_Straight / Auto / Full / MDI-MDIX     :: Verify LPI works with Auto/ Full / MDI-MDIX settings | step1: Set DUT and partner device: Speed = Auto Duplex = Full Polarity = MD
  - AWP-12286   0.389 [Green Features (Ecofri] Auto_Fixed Copper_Straight / Auto / Half / MDI-MDIX     :: Verify LPI works with Auto / Half / MDI-MDIX settings | step1: Set DUT and partner device: Speed = Auto Duplex = Half Polarity = M
  - AWP-12292   0.388 [Green Features (Ecofri] 10G_Fixed Copper_Straight / Auto / Full / MDI-MDIX      :: Verify LPI works in Auto / Full / MDI-MDIX setting | step1: Set DUT and partner device: Speed = Auto Duplex = Full Polarity = MDI 
  - AWP-12282   0.383 [Green Features (Ecofri] 1G_Fixed Copper_Straight / 1000 / Auto / MDI-MDIX       :: Verify LPI works with 1000 / Auto / MDI-MDIX settings | step1: Set DUT and partner device: Speed = 1000 Duplex = Auto Polarity = M
  - AWP-26898   0.367 [Green Features (Ecofri] 2.5G_Fixed Copper_Cross / 2.5G / Auto / MDIX-MDI        :: Verify LPI works with 2.5Gbit / Auto / MDIX-MDI | step1: Set DUT and partner device: Speed = 2500 Duplex = Auto Polarity = DUT-MDI
  - AWP-61      0.358 [Port Speed, Duplex and] Fixed Copper-1Gig-Cross-MDIX/MDI                        :: Fixed Copper - 1Gig & Cross Over Cable - Speed/Duplex = Auto & MDIX/MDI mix DUT Port Type: Fixed Copper - 1 Gig Partner Port Type:
  - AWP-64      0.358 [Port Speed, Duplex and] Fixed Copper-1Gig-Cross-MDI/MDIX                        :: Fixed Copper - 1Gig & Cross Over Cable - Speed/Duplex = Auto & MDI/MDIX mix DUT Port Type: Fixed Copper - 1 Gig Partner Port Type:

### AWPTCM-T43817  |  area: Port  |  feature: Cable Diagnostics
folder:/New Platform Template/Port  steps:1  obj:False
  - AWP-14769   0.406 [ATMF                  ] ATMF Memory Diagnostics - show atmf memory              :: Quick check of output from new command | step1: Issue the command 'show atmf memory" => Command should accept and display memory a
  - AWP-14770   0.393 [ATMF                  ] ATMF Memory Diagnostics - included in show tech-support :: Quick check that new memory diagnostics are included in show tech-support output. | step1: Issue the command "show tech-support" =
  - AWP-2743    0.341 [Bootloader            ] Bootloader diagnostics- cli - check for invalid chars.  :: Testing error cases: * try unexpected keys (!@$#$^*(){:”) instead of the standard menu options Test Bootloader diagnostics cli - c
  - AWP-19058   0.314 [ATMF                  ] ATMF Controller - neighbour recovery files - diagnostic :: Need to be able to verify the status of neighbour recovery files (config files) | step1: Do neighbour recovery. Use a not supporte
  - AWP-25361   0.306 [ATMF                  ] Show atmf diagnostics bitmap                            :: S2015.1.13 The command show atmf diagnostic (consistency | links | network | bitmap) will add the bitmap option which compares the
  - AWP-22838   0.295 [USB Modem             ] Show tech-support                                       :: Show tech-support provides USB Modem diagnostics information. | step1: On the DUT, execute show tech-support command. => Show tech
  - AWP-17987   0.294 [VLAN                  ] VCT Basic Feature Test                                  :: Description : TestCase is to be repeated for each of the following: GP24/GT24, GT40, XEM-12Tv2, XEM-24Tv2, x510/IX5, x610, x210 an
  - AWP-10238   0.283 [Diagnostic Application] Port Tests                                              :: All ports should be ok | step1: a cable for each port ena test cable po=all sh test cable po=all => confirm all ports test ok.

### AWPTCM-T43818  |  area: IPv4  |  feature: IGMPv1
folder:/New Platform Template/IPv4  steps:3  obj:True
ZEPHYR: OBJ: Check DUT will register IGMPv1 Group reports Check DUT will clear multicast entries when receiving an IGMPv1 leave || Check multicast traffic is forwarded when the IGMPv1 group r | Leave traffic 
  - AWP-14013   0.450 [RIP                   ] Interoperability with IGMPv1                            :: Verify that RIP and IGMPv1 working correctly. | step1: Configure RIP routing and IGMPv1. Please refer to attachment file. => Confi
  - AWP-23052   0.359 [IGMP                  ] Verify IGMP port limits work with any version of IGMP   :: | step1: Set an IGMP limit on a port of 10. => Command is accept and running-config updated.
  - AWP-10313   0.294 [PIM-SSM               ] PIM-SSM with Static IGMP entries                        :: Static IGMPv3 entries | step1: Configure PIM-SSM with static igmp group: - ip igmp static-group <multicast group address> Check gr
  - AWP-3470    0.262 [PIM-SM                ] CLI to check sh platform table ipmulti                  :: Command Line test | step1: 1. Setup PIM-DM / SM network 2. Execute the command to display ip multicast table - show platform table
  - AWP-7131    0.261 [IGMP                  ] ALL Group Port - IGMP Report & Leave message            :: Confirm that when the switch receives an IGMP Report message, after already having received a Routing Protocol Packet, the IGMP Re
  - AWP-10309   0.260 [PIM-SSM               ] SSM-Mapping disabled                                    :: The router (with SSM-Mapping disabled) should ignore IGMPv1/v2 reports/leave for an SSM destination address and should not use the
  - AWP-7080    0.257 [IGMP                  ] CLI Test - clear ip igmp                                :: Use this command to clear all IGMP group membership records on all VLAN interfaces. | step1: Issue the command awplus# clear ip ig
  - AWP-25170   0.256 [IGMP                  ] Multicast for VRFs - basic Igmp                         :: Ensure that an IGMP group can be learned when the associated interface is in the same instance | step1: Send igmp reports => Group

### AWPTCM-T43819  |  area: IPv4 IGMPv2  |  feature: Stastic_IGMP
folder:/New Platform Template/IPv4  steps:3  obj:True
ZEPHYR: OBJ: Check DUT will register IGMPv2 Group reports Check DUT will clear multicast entries when receiving an IGMPv2 leave || Check multicast traffic is forwarded when the IGMPv2 group r | Leave traffic 
  - AWP-23052   0.438 [IGMP                  ] Verify IGMP port limits work with any version of IGMP   :: | step1: Set an IGMP limit on a port of 10. => Command is accept and running-config updated.
  - AWP-7145    0.379 [IGMP                  ] Stress Test - IGMPv2 Send a large number of Reports and :: IGMPv2 Send a large number of Reports and Leave over extended period. | step1: 1.Set up the DUT. 2.Send large number of Reports an
  - AWP-11489   0.354 [IGMP                  ] IGMP Stress - IGMP Reports and Leaves under CPU stress  :: This tests that processing IGMP reports and joins under CPU stress does not inhibit multicast traffic membership. | step1: Using s
  - AWP-10304   0.350 [PIM-SSM               ] SSM-Mapping: IGMPv2 and reciever host IGMPv2            :: Verify SSMP-Mapping works as expected | step1: Configure SSM-Mapping >DUT in IGMP version 2 >send IGMPv2 Joined => IGMP Host Joine
  - AWP-10313   0.343 [PIM-SSM               ] PIM-SSM with Static IGMP entries                        :: Static IGMPv3 entries | step1: Configure PIM-SSM with static igmp group: - ip igmp static-group <multicast group address> Check gr
  - AWP-4486    0.341 [PIM-SSM               ] Negative test of Source Specific Multicast using IGMPv2 :: Tests Source specific should only work for IGMPv3 packets | step1: Same test setup as AW+_3503 but try joining from IGMP v2 packet
  - AWP-7080    0.334 [IGMP                  ] CLI Test - clear ip igmp                                :: Use this command to clear all IGMP group membership records on all VLAN interfaces. | step1: Issue the command awplus# clear ip ig
  - AWP-3504    0.332 [PIM-SSM               ] Negative test of Source Specific Multicast using IGMPv2 :: Tests Source specific should only work for IGMPv3 packets | step1: Same test setup as AW+_3503 but try joining from IGMP v2 packet

### AWPTCM-T43820  |  area: IPv4  |  feature: IGMPv3
folder:/New Platform Template/IPv4  steps:3  obj:True
ZEPHYR: OBJ: Check DUT will register IGMPv3 Group reports Check DUT will clear multicast entries when receiving an IGMPv3 leave || Check multicast traffic is forwarded when the IGMPv1 group r | Leave traffic 
  - AWP-3526    0.404 [PIM-SM                ] Testing include mode in IGMPv3                          :: IGMPv3 type 1 is include mode, with an empty source list it should leave and not join any groups | step1: Send IGMP v3 type 1 pack
  - AWP-10313   0.361 [PIM-SSM               ] PIM-SSM with Static IGMP entries                        :: Static IGMPv3 entries | step1: Configure PIM-SSM with static igmp group: - ip igmp static-group <multicast group address> Check gr
  - AWP-7146    0.361 [IGMP                  ] Stress Test - IGMPv3 Send a large number of Reports and :: IGMPv3 Send a large number of Reports and Leave over extended period. | step1: 1.Set up the DUT. 2.Send large number of Reports an
  - AWP-10305   0.347 [PIM-SSM               ] SSM-Mapping: IGMPv3 and reciever host IGMPv3            :: Verify the behavior of PIM-SSM when both SSM mapping and IGMPv3 are enabled, if the hosts already support IGMPv3 (but not SSM), th
  - AWP-7073    0.318 [IGMP                  ] IGMPv3 with IP Source 0.0.0.0                           :: Report source IP can be 0.0.0.0 | step1: Report source IP can be 0.0.0.0 => Report source IP can be 0.0.0.0
  - AWP-10328   0.311 [PIM-SSM               ] IGMPv3 packets with max tuples                          :: IGMPv3 packets with max tuples (record) The limit is dependent on the MTU (Maximum Transmission Unit) of the interface, which is t
  - AWP-23052   0.309 [IGMP                  ] Verify IGMP port limits work with any version of IGMP   :: | step1: Set an IGMP limit on a port of 10. => Command is accept and running-config updated.
  - AWP-10316   0.306 [PIM-SSM               ] PIM-SSM and IGMPv3 query solicitation                   :: IGMPv3 query solicitation | step1: Configure PIM-SSM Enable IGMP Query Solicitation 1. Disconnect ports to enable query solicitati

### AWPTCM-T43821  |  area: IPv4  IGMPv2  |  feature: Query Soliciation
folder:/New Platform Template/IPv4  steps:3  obj:True
ZEPHYR: OBJ: Check DUT will register IGMPv2 Group reports Check DUT will clear multicast entries when receiving an IGMPv2 leave || Check multicast traffic is forwarded when the IGMPv2 group r | Leave traffic 
  - AWP-25184   0.366 [IGMP                  ] Multicast for VRFs - Query-solicitation                 :: Ensure that an interface enabled as an IGMP querier in a VRF will respond correctly once recieving a query-solicitation message. |
  - AWP-23052   0.334 [IGMP                  ] Verify IGMP port limits work with any version of IGMP   :: | step1: Set an IGMP limit on a port of 10. => Command is accept and running-config updated.
  - AWP-7145    0.322 [IGMP                  ] Stress Test - IGMPv2 Send a large number of Reports and :: IGMPv2 Send a large number of Reports and Leave over extended period. | step1: 1.Set up the DUT. 2.Send large number of Reports an
  - AWP-17844   0.301 [IGMP Snooping         ] IGMP Snooping - Last Reporter                           :: CR00042175 Previously, when an Unregistered multicast group turn into registered multicast group by an IGMP-Snooping switch receiv
  - AWP-11489   0.281 [IGMP                  ] IGMP Stress - IGMP Reports and Leaves under CPU stress  :: This tests that processing IGMP reports and joins under CPU stress does not inhibit multicast traffic membership. | step1: Using s
  - AWP-10304   0.279 [PIM-SSM               ] SSM-Mapping: IGMPv2 and reciever host IGMPv2            :: Verify SSMP-Mapping works as expected | step1: Configure SSM-Mapping >DUT in IGMP version 2 >send IGMPv2 Joined => IGMP Host Joine
  - AWP-25288   0.277 [IGMP                  ] Multicast for VRFs - ip igmp flood specific query       :: ensure the command "ip igmp (vrf NAME|) flood specific-query" works as intended. Command causes igmp queries to be sent to all hos
  - AWP-4486    0.277 [PIM-SSM               ] Negative test of Source Specific Multicast using IGMPv2 :: Tests Source specific should only work for IGMPv3 packets | step1: Same test setup as AW+_3503 but try joining from IGMP v2 packet

### AWPTCM-T43822  |  area: IPv4  |  feature: VRRP
folder:/New Platform Template/IPv4  steps:1  obj:False
  - AWP-9371    0.629 [xSTP                  ] Interop with VRRP                                       :: | step1: Interop with VRRP
  - AWP-3800    0.543 [VRRP                  ] VRRP Interop with OSPF                                  :: To verify interoperability between VRRP and OSPF | step1: -Setup VRRP and OSPF => - Confirm VRRP works with OSPF
  - AWP-3801    0.541 [VRRP                  ] VRRP Interop with BGP                                   :: To verify interoperability between VRRP and BGP | step1: -Setup VRRP and BGP => - Confirm VRRP works with BGP
  - AWP-10025   0.532 [ICMP                  ] Interop - VRRP                                          :: Confirm that interop with VRRP function well | step1: Interop with VRRP => Should function well
  - AWP-12156   0.522 [VRRP                  ] VRRP Interop with OSPFv3                                :: To verify interoperability between VRRP and OSPFv3 | step1: Setup VRRP and OSPFv3 => Confirm VRRP works with OSPFv3
  - AWP-3799    0.516 [VRRP                  ] VRRP Interop with RIP                                   :: To verify interoperability between VRRP and RIP | step1: Setup RIP on a VRRP enabled device => Confirm VRRP works with RIP
  - AWP-14082   0.516 [BGP4+                 ] VRRP Interop with BGP4+                                 :: To verify interoperability between VRRP and BGP4+ | step1: -Setup VRRP and BGP4+ => - Confirm VRRP works with BGP4+
  - AWP-12123   0.515 [VRRP                  ] Dual Stack with IPv4 and IPv6                           :: Able to have VRRP configured with v4 and v6 | step1: Setup VRRP using IPv4 on one instance => VRRP forms can pass traffic

### AWPTCM-T43848  |  area: IPv4 ARP  |  feature: Proxy ARP
folder:/New Platform Template/IPv4  steps:1  obj:True
ZEPHYR: OBJ: Check that proxy arp is working properly and correctly when virtual-MAC is configured on stack. || * Load both devices with blank config * Configure virtual-MA
  - AWP-4383    0.399 [ARP                   ] ARP and Virtual MAC                                     :: ARP supports Virtual MAC | step1: Setup a VCStack. Assign an IP address on the stack. => Stacks forms.
  - AWP-4354    0.358 [ARP                   ] Proxy ARP: Command                                      :: Test proxy-arp command for errors | step1: Check Proxy ARP commands (any parameter) ip proxy-arp no ip proxy-arp Command must be a
  - AWP-11483   0.348 [VRRP                  ] VRRP Interop with Proxy ARP                             :: To verify interoperability between VRRP and Proxy ARP | step1: Refer to CR00035522 Require 2 switches DUT and SwitchA plus an extr
  - AWP-4356    0.317 [ARP                   ] Local Proxy ARP: Command                                :: Test "ip local-proxy-arp" command | step1: Check Local Proxy ARP commands (any parameter) Command must be accepted and shown in co
  - AWP-8245    0.311 [BGP                   ] VMAC-ON - Virtual-MAC failover the Master               :: Check that the new stack sends out a Gratatious ARP with the configured MAC address (Virtual-MAC) | step1: 1) Stack two awplus dev
  - AWP-6617    0.298 [RIP                   ] Operational: Gratuitous ARP Sent by Stack Uses Virtual  :: Check that the Gratuitous ARP sent by stack contains the configured MAC address (Virtual-MAC) | step1: Setup a stack with VMAC ena
  - AWP-4355    0.290 [ARP                   ] Proxy ARP: Functionality                                :: Proxy ARP functions. ARP request outside the network will be replaced by DUT's address. | step1: Configure DUT and Backup switch C
  - AWP-8243    0.285 [BGP                   ] VMAC-ON - Disable virtual-MAC.                          :: Check that stack correctly uses Master MAC on reboot | step1: Disable virtual-MAC. Check that stack correctly uses Master MAC on r

### AWPTCM-T43849  |  area: IPv4 ARP  |  feature: Local Proxy ARP: Functionality
folder:/New Platform Template/IPv4  steps:1  obj:True
ZEPHYR: OBJ: Command "ip local-proxy-arp" functionality test || Configure DUT and BackupSW Connect both SW via VLAN 23 Confi
  - AWP-4357    0.990 [ARP                   ] Local Proxy ARP: Functionality                          :: Command "ip local-proxy-arp" functionality test | step1: Configure DUT and BackupSW Connect both SW via VLAN 23 Configure DUT as f
  - AWP-11490   0.472 [Validation Scenario   ] VRRP Interop with Local Proxy ARP                       :: To verify interoperate between VRRP and Local Proxy ARP | step1: Two devices DUT and switchA (could be any host) Connect devices b
  - AWP-11484   0.464 [VRRP                  ] VRRP Interop with Local Proxy ARP                       :: To verify interoperability between VRRP and Local Proxy ARP | step1: Refer to CR00035522 Two devices DUT and switchA (could be any
  - AWP-4356    0.402 [ARP                   ] Local Proxy ARP: Command                                :: Test "ip local-proxy-arp" command | step1: Check Local Proxy ARP commands (any parameter) Command must be accepted and shown in co
  - AWP-4370    0.387 [ARP                   ] ARPs on Static LAGs                                     :: DUT responds to ARPs over Static LAG | step1: Configure "static-channel-group" on 4 ports for DUT and BackupSW. Configure VLAN wit
  - AWP-4358    0.365 [ARP                   ] Local Proxy ARP: Off by Default                         :: Confirm that local-proxy-arp is off by default | step1: Confirm "ip local-proxy-arp" is OFF by default Restore to default configur
  - AWP-4355    0.357 [ARP                   ] Proxy ARP: Functionality                                :: Proxy ARP functions. ARP request outside the network will be replaced by DUT's address. | step1: Configure DUT and Backup switch C
  - AWP-4371    0.355 [ARP                   ] ARPs on Dynamic LAGs                                    :: DUT responses to ARPs over dynamic LAG | step1: Configure "channel-group 1 mode active" on 4 ports for DUT and BackupSW. Configure

### AWPTCM-T43850  |  area: IPv4 DHCPServer  |  feature: Option 82
folder:/New Platform Template/IPv4  steps:0  obj:True
ZEPHYR: OBJ: Option 82 is returned ||
  - AWP-3708    0.449 [DHCP Snooping         ] DHCP Snooping with Option 82 insertion - virtual MAC en :: Verify Option 82 sub-option 1 & 2 with VCS | step1: 1.Configure DUT in Stack with Virtual Mac enabled 2.Configure Option 82 (defau
  - AWP-9792    0.440 [DHCP Snooping         ] DHCP Snooping with Option 82 insertion                  :: Check that Option82 is observed | step1: AUTOMATED: 1165-502.5 DHCP REQUEST Packets - Option 82 is inserted => Option 82 is observ
  - AWP-9797    0.432 [DHCP Snooping         ] DHCP Snooping with Option 82 insertion - with VCS virtu :: Confirm that with Virtual MAC the sub-option 82 is correct | step1: Option 82 sub-option 2 - Switch MAC - uses correct virtual MAC
  - AWP-9793    0.425 [DHCP Snooping         ] DHCP Snooping with Option 82 insertion - removal        :: Confirm that Option82 is removed | step1: DHCP REPLYs going to untrusted ports - Option 82 is removed => Option 82 is removed
  - AWP-3709    0.422 [DHCP Snooping         ] DHCP Snooping with Option 82 insertion - virtual MAC di :: Verify Option 82 sub-option 1 & 2 with VCS (Virtual MAC disabled) | step1: VCS - functional test without virtual MAC enabled 1.Con
  - AWP-3705    0.420 [DHCP Snooping         ] DHCP Snooping option 82 - show commands                 :: Verify display DHCP snooping Option 82 information for all interfaces, a specific interface or a range of interfaces. | step1: The
  - AWP-3702    0.401 [DHCP Snooping         ] DHCP Snooping with Option 82 insertion - Trusted ports  :: Trusted Ports: DHCP packtes with Option 82 are accepted and Option 82 is not updated | step1: >Trusted port and DHCP Server Config
  - AWP-9802    0.400 [DHCP Snooping         ] DHCP Snooping with Option 82 insertion - virtual MAC en :: Confirm that DHCP snooping with option 82 functions well when VMAC enabled | step1: Stacking - functional test with virtual MAC en

### AWPTCM-T43851  |  area: IPv4 DHCPServer  |  feature: DHCP ARP Probe
folder:/New Platform Template/IPv4  steps:1  obj:True
ZEPHYR: OBJ: Test for enable and disable probing in DHCP Server || Use this command to enable/disable lease probing for a DHCP
  - AWP-3596    0.927 [DHCP                  ] DHCP server - ARP Probe - Enable and disable Probing    :: Test for enable and disable probing in DHCP Server | step1: Use this command to enable/disable lease probing for a DHCP pool. prob
  - AWP-3594    0.530 [DHCP                  ] DHCP server - Probe IP Address using ARP                :: Verify that when probe parameter is set to ARP, server probes IP address using ARP | step1: 1.Configure DUT as DHCP server. 2.Conn
  - AWP-3550    0.486 [DHCP                  ] DHCP server - Command line test: ARP Probe              :: Test for Ping/ARP Probe commands | step1: •probe enable •no probe enable •probe type {ping|arp} •no probe type •probe packets <0-1
  - AWP-3738    0.446 [DHCP                  ] DHCP Server - Probe IP Address with wireless dhcp clien :: Verify that Probing works with the wireless dhcp client. | step1: 1. Configure DUT as DHCP Server 2. Connect an Access Point to DU
  - AWP-15611   0.443 [Exploratory Tests     ] DHCP Lease Probing                                      :: | step1: P { margin-bottom: 0.08in; }A:link { } Configure probing on DHCP Server on the DUT => Confirm that probing has been confi
  - AWP-3739    0.439 [DHCP                  ] DHCP Server - Probe IP address with ACL (ICMP block)    :: Verify that Probing works with ACL configured blocking ICMP packets. | step1: 1. Configure a DHCP Server 2. Configure a DUT with A
  - AWP-3595    0.415 [DHCP                  ] DHCP server - ARP Probe - Configured number of Probe Pa :: Test Configured number of packets works correctly and verify ARP Probe packet | step1: Command to specify the number of packets se
  - AWP-3593    0.382 [DHCP                  ] DHCP server - Probe IP Address using ICMP (clients on r :: Ping Probing with clients on remote networks | step1: 1.Configure DUT as DHCP server. 2.Connect a DHCP Client to DHCP server => Ve

### AWPTCM-T43852  |  area: IPv4 DHCPServer  |  feature: DHCP Relay
folder:/New Platform Template/IPv4  steps:0  obj:True
ZEPHYR: OBJ: Confirm that PC can get IPv4, gateway, DNS server addresses by DHCP. ||
  - AWP-9877    0.496 [DHCP Snooping         ] DHCP Relay test                                         :: Confirm that DHCP relay should have normal behavior | step1: DHCP Relay => Expecting normal behaviour.
  - AWP-13580   0.458 [Validation Scenario   ] Check operation of DHCPServer/Relay with VRRP3 IPV6     :: to check and Verify DHCP v6 Server and DHCP Relay with VRRPv3 | step1: Conduct tests with DHCP V6 such that a ipv6 clients communi
  - AWP-18483   0.400 [Router Bridging       ] Bridge as a DHCP relay interface                        :: Bridge should be able to act as a DHCP Relay | step1: 1. Configure Bridge 2. Assign interfaces to the bridge 3. Configure bridge t
  - AWP-6687    0.390 [IP Helper             ] Interoperability with DHCP relay                        :: Test that when DHCP relay is enabled, IP helper works correctly | step1: With DHCP Relay => Confirm that the relay performance of 
  - AWP-2263    0.378 [DHCP                  ] DHCP relay - show commands                              :: Test for DHCP Relay show commands exist and usable. | step1: Pre-requisite: The DUT must be configured as a DHCP Relay Agent conne
  - AWP-11002   0.366 [DHCPv6                ] DHCPv6 Relay - CLI                                      :: Ensure DHCPv6 Relay supports the IPv6 address and DUT interface for the DHCPv6 server | step1: Configure DHCP Relay with an IPv6 a
  - AWP-14324   0.362 [VRF-Lite              ] DHCP Relay VRF aware - VCS                              :: DHCP-Relay should work normally with stack devices. | step1: Set-up DHCP-Relay in VRF-Lite with stack devices (2 stack and 4 stack
  - AWP-14293   0.361 [VRF-Lite              ] DHCP Relay VRF aware - DHCP Relay Global Commands       :: DHCP Relay commands on global VRF-Lite instance should work. | step1: service dhcp-relay/no service dhcp-relay => enables/disables

### AWPTCM-T43853  |  area: IPv4 DHCPServer  |  feature: DHCP 120-day lease
folder:/New Platform Template/IPv4  steps:1  obj:False
  - AWP-3578    0.604 [DHCP                  ] DHCP server - 120 day lease configured                  :: Test for DHCP server to offer 120 day lease time to a DHCP Client. | step1: Configure DUT as DHCP Server. Create a DHCP Pool with 
  - AWP-3579    0.468 [DHCP                  ] DHCP client - correctly obtain 120 day lease time       :: Test for DHCP Client if it correctly obtained the 120 day lease time from the DHCP Server. | step1: Configure DUT as DHCP Client C
  - AWP-9771    0.347 [DHCP Snooping         ] DHCP Snooping - log - lease deleted                     :: Log message when lease deleted should be seen at user level | step1: Log message when lease deleted => log message useful at user 
  - AWP-15615   0.342 [Exploratory Tests     ] DHCP Client Lease Renewal                               :: | step1: Configure DUT as DHCP Client. Connect it to DHCP Server and configure the lease time => Check that lease is renewed after
  - AWP-2475    0.337 [DHCP                  ] DHCP client - Lease time                                :: Test for DHCP client if it correctly refresh the IP address based on the configured lease time. | step1: Configure DUT as DHCP Cli
  - AWP-9770    0.336 [DHCP Snooping         ] DHCP Snooping - log - new lease added                   :: Log message when new lease added should be seen at user level | step1: Log message when new lease added => log message useful at u
  - AWP-2271    0.322 [DHCP                  ] DHCP server - lease time 1 minute                       :: Configure DHCP server with lease time of 1 minute. | step1: Configure a DHCP server with lease time of 1 minute e.g.: ip dhcp pool
  - AWP-15614   0.299 [Exploratory Tests     ] DHCP Client Lease Acceptance                            :: | step1: P { margin-bottom: 0.08in; }A:link { } Configure DUT as DHCP Client. Connect it to DHCP Server and configure the lease t 

### AWPTCM-T43854  |  area: IPv4 DHCPClient  |  feature: DNS Relay
folder:/New Platform Template/IPv4  steps:1  obj:True
ZEPHYR: OBJ: DNS Relay - enable/disable Requirements: Supports forwarding DNS query packet to server Switches to enable and disable D || configure name-servers enable dns relay (ip dns forwarding)
  - AWP-3360    0.988 [DNS                   ] DNS Relay - enable/disable                              :: DNS Relay - enable/disable Requirements: Supports forwarding DNS query packet to server Switches to enable and disable DNS relay f
  - AWP-3359    0.561 [DNS                   ] DNS Relay - name resolver support                       :: DNS Relay - name resolver support Features that use local name resolver are supported by dns relay. Name resolver functions when n
  - AWP-11510   0.479 [DNS                   ] DNS Relay with IPv6 Server address                      :: Configer a DUT DNS relay on a DUT with an IPv6 name server configered. Althougn the DNS relay does not have any addresses configur
  - AWP-3194    0.476 [DNS                   ] DNS Relay show commands                                 :: DNS Relay show commands | step1: Output is accurate & useful show ip dns forwarding (configurations) show ip dns forwarding server
  - AWP-3197    0.447 [DNS                   ] DNS Relay Debug                                         :: DNS Relay Debug | step1: Setup DNS Server, with name lists and IP addresses of DNS Server, DNS Relay, and Client
  - AWP-11530   0.447 [DNS                   ] DNS Relay - IPv6 information in show commands           :: DNS relay show commands should correctly show IPv6 as well as IPv4 information: SHOW IP DNS FORWARDING SERVER SHOW IP DNS FORWARDI
  - AWP-3365    0.412 [DNS                   ] DNS Relay - source interface configuration              :: Configures source interface sending DNS query packet. Works if dns relay switch has two routes to the dns server. | step1: Set as 
  - AWP-14303   0.412 [VRF-Lite              ] DNS Relay VRF aware - DNS forwarding with VRF instance  :: Test that configuration command for activating DNS forwarding should be useful and working | step1: On a DUT, enable ip dns forwar

### AWPTCM-T43855  |  area: IPv4 UnicastRouting  |  feature: IPv4 Static
folder:/New Platform Template/IPv4  steps:1  obj:True
ZEPHYR: OBJ: Check IPv4 static routes will be supported || Check IPv4 static routes will be supported
  - AWP-24184   0.979 [ATMF                  ] Check IPv4 static routes will be supported              :: Check IPv4 static routes will be supported | step1: Check IPv4 static routes will be supported => confirm IPv4 static routes are s
  - AWP-24185   0.712 [ATMF                  ] Check IPv6 static routes will be supported              :: Check IPv6 static routes will be supported | step1: check IPv6 static routes will be supported => confirm IPv6 static routes are s
  - AWP-24173   0.595 [ATMF                  ] Check Ping (IPv4 and IPv6) will be supported            :: Check Ping (IPv4 and IPv6) will be supported | step1: Check Ping (IPv4 and IPv6) will be supported => confirm Ping (IPv4 and IPv6)
  - AWP-24175   0.523 [ATMF                  ] Check SSH server (IPv4 and IPv6) will be supported      :: Check SSH server (IPv4 and IPv6) will be supported | step1: Check SSH server (IPv4 and IPv6) will be supported => Confirm SSH serv
  - AWP-24176   0.513 [ATMF                  ] Check SSH client (IPv4 and IPv6) will be supported      :: Check SSH client (IPv4 and IPv6) will be supported | step1: Check SSH client (IPv4 and IPv6) will be supported => Confirm SSH clie
  - AWP-7681    0.489 [Validation Scenario   ] IPv4 Static Routes - Unicast Traffic                    :: Check and verify IPv4 Static Routes for correct status and functionality. | step1: Run background unicast traffic in the relevant 
  - AWP-25826   0.397 [IPv4                  ] ECMP routing with interface name will be supported for  :: | step1: device with multiple ppp link and set static routing to a specific subnet egressing from multiple ppp interface names an 
  - AWP-20439   0.366 [Validation Scenario   ] Field Issue IPv4 Multicast Routes                       :: A field issue had been created indicating that Static IPv4 multicast routes were not working. This Test is created as a result of 

### AWPTCM-T43856  |  area: IPv4 UnicastRouting  |  feature: RIP v1/v2
folder:/New Platform Template/IPv4  steps:1  obj:False
  - AWP-12917   0.424 [MLD                   ] MLDv2 interop with v1 host                              :: MLDv2 interop with v1 host | step1: Device with ipv6 mld enabled (default v2) Send in v1 report Send in v1 done => Command accepte
  - AWP-12916   0.379 [MLD                   ] MLD v1 and v2 interop                                   :: Interop of different MLD versions | step1: 2 Devices with MLD enabled Device one operating in V1 mode Device two operating in V2 m
  - AWP-6573    0.337 [RIP                   ] Device Management: Show IP RIP                          :: Verify RIP elements are correctly displayed in show ip rip output. | step1: Configure RIP on DUT Issue show ip rip command => Show
  - AWP-6574    0.302 [RIP                   ] Device Management: RIP Summary                          :: Check RIP commands are correctly reflected in show running-config | step1: Configure RIP on DUT Issue show running-config router r
  - AWP-19394   0.292 [z_ATKK_Inquiry_Based  ] RIP Neighbor                                            :: Scope Verify the number of RIP neighbor that DUT can accept. | step1: Run IxNetwork with the above configuration then execute "sho
  - AWP-3799    0.289 [VRRP                  ] VRRP Interop with RIP                                   :: To verify interoperability between VRRP and RIP | step1: Setup RIP on a VRRP enabled device => Confirm VRRP works with RIP
  - AWP-6577    0.287 [RIP                   ] Device Management: RIP Logging                          :: Check RIP Logging is accurate and useful | step1: Configure RIP and RIP logging on DUT. Issue show log command. => RIP logging is 
  - AWP-7380    0.283 [IPv6 Static Routes and] Show IPv6 RIP/OSPF                                      :: Show commands should display correctly | step1: Issue sh ipv6 rip|ospf command => Command output should be correct and useful

### AWPTCM-T43857  |  area: IPv4 Unica stRouting  |  feature: OSPFv2
folder:/New Platform Template/IPv4  steps:1  obj:False
  - AWP-7718    0.579 [Validation Scenario   ] OSPFv2 - Unicast Traffic                                :: Check and verify OSPFv2 for correct status and functionality. | step1: Run background unicast traffic in the relevant scenario. =>
  - AWP-2636    0.556 [OSPFv3                ] OSPF v3 interop with OSPFv2                             :: OSPF v3 interop with OSPFv2 | step1: Create at least a 3-device network Apply OSPFv2 and OSPFv3 Use show commands to verify OSPFv2
  - AWP-7719    0.437 [Validation Scenario   ] OSPFv2 - Restarting Processes                           :: Check and verify OSPFv2 for correct status and functionality. | step1: Restart processes/protocols (daemon). 3 ways to restart pro
  - AWP-7715    0.435 [Validation Scenario   ] OSPFv2 - Disconnect / Reconnect Links                   :: Check and verify OSPFv2 for correct status and functionality. | step1: Disconnect then reconnect links and check for network recov
  - AWP-7717    0.431 [Validation Scenario   ] OSPFv2 - Add / Delete Configurations                    :: Check and verify OSPFv2 for correct status and functionality. | step1: Update related configurations by adding, removing or changi
  - AWP-7716    0.338 [Validation Scenario   ] OSPFv2 - Hotswap                                        :: Check and verify OSPFv2 for correct status and functionality. | step1: Check and verify that devices operates uninterupted after a
  - AWP-7713    0.326 [Validation Scenario   ] OSPFv2 - Master Failover                                :: Check and verify OSPFv2 for correct status and functionality. | step1: Fail Master device in stack, check for correct recovery, re
  - AWP-7714    0.294 [Validation Scenario   ] OSPFv2 - Slave Failover                                 :: Check and verify <feature> for correct status and functionality. | step1: Fail slave device in stack, check for correct recovery, 

### AWPTCM-T43858  |  area: IPv4 UnicastRouting  |  feature: BGPv4
folder:/New Platform Template/IPv4  steps:1  obj:True
ZEPHYR: OBJ: Check and verify BGPv4 for correct status and functionality. || Run background unicast traffic in the relevant scenario.
  - AWP-14120   0.947 [BGP4+                 ] BGPv4 - Unicast Traffic                                 :: Check and verify BGPv4 for correct status and functionality. | step1: Run background unicast traffic in the relevant scenario. => 
  - AWP-7650    0.947 [Validation Scenario   ] BGPv4 - Unicast Traffic                                 :: Check and verify BGPv4 for correct status and functionality. | step1: Run background unicast traffic in the relevant scenario. => 
  - AWP-7681    0.623 [Validation Scenario   ] IPv4 Static Routes - Unicast Traffic                    :: Check and verify IPv4 Static Routes for correct status and functionality. | step1: Run background unicast traffic in the relevant 
  - AWP-7775    0.618 [Validation Scenario   ] VCS - Unicast Traffic                                   :: Check and verify VCS for correct status and functionality. | step1: Run background unicast traffic in the relevant scenario. => Se
  - AWP-13530   0.604 [Validation Scenario   ] VLANs - Unicast Traffic                                 :: Check and verify VLANs for correct status and functionality. | step1: Run background unicast traffic in the relevant scenario. => 
  - AWP-7658    0.599 [Validation Scenario   ] EPSR - Unicast Traffic                                  :: Check and verify EPSR for correct status and functionality. | step1: Run background unicast traffic in the relevant scenario. => S
  - AWP-13493   0.588 [Validation Scenario   ] OSPFv3 - Unicast Traffic                                :: Check and verify OSPFv3 for correct status and functionality. | step1: Run background unicast traffic in the relevant scenario. =>
  - AWP-7742    0.588 [Validation Scenario   ] RIP - Unicast Traffic                                   :: Check and verify RIP for correct status and functionality. | step1: Run background unicast traffic in the relevant scenario. => Se

### AWPTCM-T43859  |  area: IPv4 UnicastRouting  |  feature: VRF-Lite
folder:/New Platform Template/IPv4  steps:1  obj:True
ZEPHYR: OBJ: VRF-Lite support traceroute operation || From a VRF instance Run the command traceroute vrf <name> x.
  - AWP-4286    0.965 [VRF-Lite              ] VRF Lite Traceroute                                     :: VRF-Lite support traceroute operation | step1: From a VRF instance Run the command traceroute vrf <name> x.x.x.x From the global V
  - AWP-10227   0.415 [z_Inactive            ] Traceroute for 192.168.1.1                              :: Traceroute should show the correct result | step1: trace 192.168.1.1 => confirm correct trace result
  - AWP-10228   0.409 [z_Inactive            ] Traceroute for 192.168.1.2                              :: Traceroute should be successful | step1: trace 192.168.1.2 => confirm correct trace result
  - AWP-10990   0.406 [VRF-Lite              ] VRF_Lite and Stack Management Vlan                      :: To operate VRF lite on a stack and confirm that there is no defect in the way VRF-Lite handles the stack management Vlan | step1: 
  - AWP-11451   0.396 [Validation Scenario   ] VRF-Lite - Unicast Traffic                              :: Check and verify VRF-Lite for correct status and functionality. | step1: Run background unicast traffic in the relevant scenario. 
  - AWP-4144    0.378 [VRF-Lite              ] VRF Lite Telnet command                                 :: To test Telnet operation to the default vlan To test Telnet opertion to an interface within a VRF. | step1: Configure L3 interface
  - AWP-10992   0.373 [VRF-Lite              ] VRF Lite route to resiliency Vlan                       :: To check that it is not possible to create a route (static or dynamic) to the resiliency link vlan | step1: create a static route 
  - AWP-14294   0.364 [VRF-Lite              ] DHCP Relay VRF aware - VRF Instance Running DHCP-Relay  :: VRF-Lite running DHCP-Relay should work on common instance. | step1: enable dhcp-relay services #service dhcp-relay configure VRF-

### AWPTCM-T43860  |  area: IPv4 UnicastRouting  |  feature: IP Route Filter
folder:/New Platform Template/IPv4  steps:1  obj:False
  - AWP-8293    0.401 [IPv4                  ] Static Route                                            :: Command should add static route | step1: To add static routes to device, use device to communicate with another interface. Using t
  - AWP-10526   0.383 [VRF-Lite              ] route map filter is obeyed                              :: Ensure that routes that have a route map filter applied obey the route filter rules | step1: Ensure that routes that have a route 
  - AWP-11272   0.383 [VRF-Lite              ] route map filter is obeyed                              :: Ensure that routes that have a route map filter applied obey the route filter rules | step1: Ensure that routes that have a route 
  - AWP-8272    0.379 [IPv4                  ] Show IP Route                                           :: Command will display the route configuration | step1: Include IP address and routes, make sure they are displayed using this comma
  - AWP-4969    0.377 [Limits                ] MAC Filter entries                                      :: Deactivated | step1: N/A => N/A
  - AWP-11050   0.374 [VRF-Lite              ] Configure a route map filter for route sharing between  :: To check the operation of route-map and route-map filter and add the following route-map commands | step1: Run the sho ip route co
  - AWP-14031   0.339 [IPv4                  ] IP Route Filter(Route Map) Entry limit                  :: Check maxmium number of route-map entries as support limit. | step1: Confirm that L3SW1 learn max number of routes. (this means DU
  - AWP-27361   0.339 [ATMF                  ] Check ip-filter blocks can be cleared from CLI          :: DUT#clear ip-filter blocking ? A.B.C.D Blocked IPv4 address | step1: Send in ip-filter block => Block exists on AMF Member
