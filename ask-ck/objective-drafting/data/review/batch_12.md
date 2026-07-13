# Rerank batch 12  (cases 360..389)

### AWPTCM-T45808  |  area:   |  feature: eco mode leds
folder:/XEM  steps:1  obj:False
  - AWP-14374   0.526 [Green Features (Ecofri] Ecofriendly LED - Eco mode works at multiple line speed :: Eco mode should be tested with both 1G and 10/100M traffic to test both the green and the amber LEDs. | step1: Have both 1 G and 1
  - AWP-14562   0.514 [Green Features (Ecofri] Ecofriendly affecting LEDs when eco LED is enabled by H :: | step1: 1. Push mode select button and select LED off mode. 2. Run ecofriendly led command. 3. Run show running-config 4. Push m
  - AWP-14564   0.513 [Green Features (Ecofri] Ecofriendly affecting LEDs when eco LED is enabled by H :: | step1: 1. Push mode select button and select LED off mode. 2. Run ecofriendly led command. 3. Run show running-config 4. Push m
  - AWP-14565   0.505 [Green Features (Ecofri] Eco LED button affecting LEDs when ecofriendly led comm :: | step1: 1. Run ecofriendly led command. 2. Push mode select button. 3. Run show running-config 4. Push mode select button.
  - AWP-14566   0.505 [Green Features (Ecofri] Eco LED button affecting LEDs when ecofriendly led comm :: | step1: 1. Run ecofriendly led command. 2. Push mode select button. 3. Run show running-config 4. Push mode select button.
  - AWP-17642   0.444 [Green Features (Ecofri] Ecofriendly affecting LEDs when eco LED is enabled by H :: Check Ecofriendly button is working | step1: 1. Push mode select button and select LED off mode. 2. Run ecofriendly led command. 3
  - AWP-25116   0.443 [Green Features (Ecofri] Ecofriendly affecting LEDs when eco LED is enabled by H :: Check Ecofriendly button is working | step1: 1. Push mode select button and select LED off mode. 2. Run ecofriendly led command. 3
  - AWP-17696   0.360 [Green Features (Ecofri] LED State - ECO LED enabled                             :: Verify 7 Segment LED when ecofriendly is enabled. | step1: DUT VCS Master: 1. Ecofriendly button 2. Ecofriendly command => In ECO 

### AWPTCM-T45809  |  area:   |  feature: stack
folder:/XEM  steps:1  obj:False
  - AWP-24605   0.493 [ATMF                  ] stack failover                                          :: stack failover | step1: perform stack failover => confirm atmf network still reforms and no crash or new log errors
  - AWP-8436    0.474 [MLD Snooping          ] Multicast traffic on stack                              :: | step1: stacking x900/x908 => Ensure that multicast traffic works across stack
  - AWP-5290    0.465 [OSPF                  ] Stack Failover Member                                   :: Stack should use VMAC even on Stack Member | step1: Fail-over Member => Check that [Feature] uses virtual-MAC on member
  - AWP-5281    0.413 [OSPF                  ] Stack Fail-over Member                                  :: Stack member should use the Master MAC when it boots up | step1: Fail-over Member => Check that [Feature] uses MAC of Master when 
  - AWP-17694   0.407 [Green Features (Ecofri] LED State - VCS Enabled                                 :: Verify 7 Segment LED in VCS mode. | step1: Stack ID 1 => LED shows stack ID 1
  - AWP-624     0.384 [Triggers              ] Stack (VCS) Trigger on stack member join                :: Test for VCS triggers | step1: Configure the trigger to be activated when the device becomes a stack member by joining => Trigger 
  - AWP-10028   0.378 [ICMP                  ] VMAC off - Master stack MAC Address                     :: Confirm that MAC address used is Master stack MAC address | step1: Check that [Feature] uses Master-MAC when Virtual-MAC is not en
  - AWP-18371   0.377 [Platform              ] show stack                                              :: Scope: Confirm VCS state(disable/enable). Assertion: | step1: Enter "show stack" command. => Display "%Warning: Stacking is curren

### AWPTCM-T45810  |  area:   |  feature: findme
folder:/XEM  steps:1  obj:False
  - AWP-21920   0.595 [QoS                   ] Findme trigger with VCS                                 :: Test that the findme trigger works as expected on VCS setup. | step1: Set an attachment config file. Start ixia traffic. => Confor
  - AWP-21919   0.503 [QoS                   ] Findme trigger with VCS + LAG                           :: Test that the findme trigger works as expected on VCS and LAG setup. Tests both static and lacp. | step1: Set an attachment config
  - AWP-29490   0.438 [OpenFlow              ] Findme                                                  :: Confirm that Findme works correctly. | step1: Confirm that LED is up on Hybrid OpenFlow port.
  - AWP-24856   0.438 [OpenFlow              ] Findme                                                  :: Confirm that Findme works correctly. | step1: Confirm that LED is up on Hybrid OpenFlow port.
  - AWP-26459   0.438 [OpenFlow              ] Findme                                                  :: Confirm that Findme works correctly. | step1: Confirm that LED is up on Hybrid OpenFlow port.
  - AWP-9681    0.422 [Find Me               ] Find Me - Functional - stop timer with no findme comman :: Find Me - using blinking port LEDs to find devices. | step1: Start findme command, then stop with no findme before normal timeout.
  - AWP-21916   0.385 [QoS                   ] Priority of LED flashing                                :: When the ATMF-Recover and the Findme-trigger is running , high priority of led flashing is ATMF-Recover. DUT is ATMF members. | st
  - AWP-17847   0.382 [ATMF                  ] ATMF LED indication prevails over FindMe                :: ATMF progress LED indication feature should always prevail over Findme 1. If Findme happens before ATMF recovery, it will be overr

### AWPTCM-T45821  |  area:   |  feature: Hotswap
folder:/XEM  steps:1  obj:False
  - AWP-8437    0.581 [MLD Snooping          ] Multicast traffic on hotswap                            :: | step1: hotsawap => Ensure that multicast traffic works across stack following a hotswap
  - AWP-3207    0.545 [DNS                   ] DNS Relay and Hotswap                                   :: DNS Relay and Hotswap | step1: Hotswap client vlans (all ports in vlan) out then in Hotswap server vlan (all ports in vlan) out th
  - AWP-13058   0.473 [Find Me               ] Hotswap Pluggables                                      :: Verify how hotswap in and out will affect the feature | step1: Link some ports to ensure LEDs are up Or ports are active with traf
  - AWP-9946    0.460 [DHCP Snooping         ] DHCP Snooping ACLs - after hotswap                      :: Check ACLs in HW tables after hotswap | step1: DHCP Snooping ACLs applied correctly after hotswap in => Check ACLs in HW tables
  - AWP-22602   0.457 [VLAN                  ] vlan classifier and hotswap                             :: | step1: pull out module i.e. XEM, LIF
  - AWP-9958    0.456 [DHCP Snooping         ] ARP Security - on static channel after hotswap          :: Confirm normal operation on static channel after hotswap | step1: ARP Security applied correctly on static channel group interface
  - AWP-9961    0.454 [DHCP Snooping         ] ARP Security - on dynamic channel after hotswap         :: Confirm normal operation on dynamic channel after hotswap | step1: ARP Security applied correctly on dynamic channel group interfa
  - AWP-9943    0.442 [DHCP Snooping         ] DHCP Snooping - hotswap on trusted interfaces           :: Confirm normal operation after hotswap on trusted ports | step1: Hotswap on trusted interfaces [including LAGs] => Expect normal o

### AWPTCM-T45835  |  area:   |  feature: Boot from Flash
folder:/GRUB Bootloader  steps:1  obj:False
  - AWP-25813   0.538 [Bootup                ] No startup/boot config, files exist on flash            :: | step1: Boot a not clean device => nothing happens
  - AWP-3604    0.509 [File System           ] Check command for boot config ?                         :: Ensure boot config help command is helpful | step1: 1) issue command help "boot config ?" => Ensure it contain information for con
  - AWP-3603    0.481 [File System           ] Check command for boot system ?                         :: Ensure boot system help command is helpful | step1: 1) issue command help "boot system ?" => Ensure it contain information for con
  - AWP-2699    0.365 [Bootloader            ] Bootloader - test that device boot fails with default b :: Bootloader menu: " 2. Change the default boot source (for advanced users)" should work Test that device cannot load if release fil
  - AWP-11504   0.361 [File System           ] USB - Boot commands: boot config-file - single CFC      :: Check boot config file can be set from command line boot options | step1: Issue commands: configure terminal boot config-file usb:
  - AWP-793     0.361 [Qualification         ] boot system' command                                    :: Check "boot system" command exists | step1: Check "boot system" command => TEST PASS: if there is a boot system from card option i
  - AWP-14255   0.352 [ISSU                  ] ISSU - ISSU supports boot release from flash or USB     :: S1716.1.20 ISSU must support setting the boot release to be from flash, or USB | step1: Run ISSU with file on USB drive of both CF
  - AWP-794     0.349 [Qualification         ] boot config-file' command                               :: Check "boot config-file" command exists | step1: Check "boot config-file" command => TEST PASS: if there is a boot config-file fro

### AWPTCM-T45836  |  area:   |  feature: Boot from USB storage device
folder:/GRUB Bootloader  steps:1  obj:False
  - AWP-11506   0.473 [File System           ] USB - Boot commands: Error messages - single CFC        :: Check boot command error messages are output correctly when accessing files (or not) on a USB Storage Device | step1: Issue comman
  - AWP-11505   0.466 [File System           ] USB - Boot commands: boot system - single CFC           :: Check the current software can be set to file on USB device | step1: Issue commands: configure terminal boot system usb:/usb_relea
  - AWP-11462   0.459 [File System           ] File - copy to usb                                      :: command copy to usb | step1: Destination media is 'usb' Issue the command COPY A usb when usb device is supported and usb is prese
  - AWP-11459   0.441 [File System           ] File - commands mkdir - usb                             :: This teObjective: To verify that file operation can be performed successfully on USB storage device Expected Outcome: Directory sh
  - AWP-11504   0.432 [File System           ] USB - Boot commands: boot config-file - single CFC      :: Check boot config file can be set from command line boot options | step1: Issue commands: configure terminal boot config-file usb:
  - AWP-2435    0.403 [z_Inactive            ] File - test that a file can be moved to default storage :: File - test that a file can be moved to default storage location | step1: Test a file can be MOVED to the default storage area. Te
  - AWP-5485    0.395 [TFTP                  ] TFTP operation with different storage types             :: Objective: To test TFTP behaviour using different storage types Expected Outcome: TFTP should operate without any issue using diff
  - AWP-11511   0.390 [File System           ] USB - Boot from USB file with USB file as config file - :: Ensure a device boots with the default release on a USB device and can read a config file from a USB device | step1: Issue Command

### AWPTCM-T45837  |  area:   |  feature: Adjust console baud rate
folder:/GRUB Bootloader  steps:1  obj:False
  - AWP-2715    0.787 [Bootloader            ] Bootloader - Adjust the console baud rate               :: Bootloader menu: "4. Adjust the console baud rate" should work Bootloader - Adjust the console baud rate | step1: reboot device, e
  - AWP-2714    0.542 [Bootloader            ] Bootloader - access to the console baud rate menu - RET :: Bootloader menu: "4. Adjust the console baud rate" should work Bootloader - access to the console baud rate menu | step1: reboot d
  - AWP-7593    0.474 [z_Inactive            ] Able to operate at all baud rates                       :: Console port is able to operate at all baud rates | step1: Connect console to test box Open connection to device Verify operation 
  - AWP-4467    0.366 [Command Shell         ] console speed - testing console speed                   :: Verify console speed can be successfully configured and reflected on DUT | step1: Test changing console speed on active session aw
  - AWP-2721    0.351 [Bootloader            ] Bootloader - Restore bootloader factory settings - cons :: Bootloader menu: "7. Restore Bootloader factory settings" should work Bootloader - Restore bootloader factory settings - console s
  - AWP-2723    0.333 [Bootloader            ] Bootloader - Restore bootloader factory settings - rele :: Bootloader menu: "7. Restore Bootloader factory settings" should work Bootloader - Restore bootloader factory settings - e.g. defa
  - AWP-4472    0.317 [z_Inactive            ] console speed - CLI setting to default                  :: NOTE: This test case as already included under AWP-4467 console speed - CLI setting to default | step1: Check that [no speed] sets
  - AWP-4466    0.271 [Command Shell         ] console speed - help option                             :: Veirfy help option with console speed were accurate and useful | step1: Test console speed option awplus(config)#line console 0 aw

### AWPTCM-T45838  |  area:   |  feature: Special boot options
folder:/GRUB Bootloader  steps:1  obj:False
  - AWP-7390    0.403 [IPv6 Static Routes and] Special address range added as Static Routes            :: Special addresses should not be allowed to be used as static route | step1: Add static routes to special address ranges e.g. multi
  - AWP-2717    0.384 [Bootloader            ] Bootloader - Test that device will skip a non-default n :: Bootloader menu: "5. Special boot options" should work. 1-skip startup script 2-Clear manager password ( This feature retired from
  - AWP-2716    0.310 [Bootloader            ] Bootloader - Test that device will skip default.cfg con :: Bootloader menu: "5. Special boot options" should work. 1-skip startup script 2-Clear manager password ( This feature retired from
  - AWP-7852    0.303 [User Login            ] Recover manager login if password forgotten.            :: If manager password is forgotten, tes that the device can be accessed by bypassing startup config in the bootloader menu option. (
  - AWP-18470   0.296 [Validation Scenario   ] Two Step Auth Feature options                           :: Configure some extra options with in the feature and confirm operation | step1: Configure other options within two step auth and c
  - AWP-21960   0.289 [z_ATKK_Inquiry_Based  ] Older U-Boot and Not Set Backup Release                 :: ER-700 for x210 - include new bootloder 2.0.24 ER-734 for x510 - include new bootloader 2.0.25 Flowchart - http://intranet.atlnz.l
  - AWP-13633   0.288 [Bootloader            ] Bootloader - Security Level 3 - Accessible options      :: Check accessible options in Boot Menu at Security Level 3 | step1: Reboot the device and enter the Boot Menu (ctrl-b) Enter "s" to
  - AWP-21962   0.287 [z_ATKK_Inquiry_Based  ] Newer U-Boot and Not Set Backup Release                 :: ER-700 for x210 - include new bootloder 2.0.24 ER-734 for x510 - include new bootloader 2.0.25 Flowchart - http://intranet.atlnz.l

### AWPTCM-T45839  |  area:   |  feature: Boot System Release
folder:/GRUB Bootloader  steps:1  obj:False
  - AWP-2639    0.566 [Bootloader            ] Boot system - Boot with a set release                   :: * Software upgrade must be a one-hit process - boot with a set release Automated: http://intranet.atlnz.lc/systest/ATPyLib/regress
  - AWP-19413   0.545 [Bootloader            ] Boot system - Repeat boot system(To check CR00040425)   :: * Repeat boot system - boot with a set release | step1: 1. Configure a device with a release and with no backup boot image set usi
  - AWP-793     0.531 [Qualification         ] boot system' command                                    :: Check "boot system" command exists | step1: Check "boot system" command => TEST PASS: if there is a boot system from card option i
  - AWP-21004   0.514 [ATMF                  ] ATMF VM Config - Boot System                            :: VAA software cannot be change by "boot system" command "boot system" is a feature that will not be implemented on ATMF VM | step1:
  - AWP-3603    0.502 [File System           ] Check command for boot system ?                         :: Ensure boot system help command is helpful | step1: 1) issue command help "boot system ?" => Ensure it contain information for con
  - AWP-2645    0.501 [Bootloader            ] Boot system - setting a release file that is not a rele :: * Software upgrade must be a one-hit process - can not install non-release file Automated: http://intranet.atlnz.lc/systest/ATPyLi
  - AWP-2640    0.495 [Bootloader            ] Boot system - Boot fails with no release set            :: * Software upgrade must be a one-hit process - boot fails with no release set Automated: http://intranet.atlnz.lc/systest/ATPyLib/
  - AWP-2648    0.491 [Bootloader            ] Boot system - backup release - backup file missing      :: Backup release will not be set when the release file does not exist. Automated: http://intranet.atlnz.lc/systest/ATPyLib/regressio

### AWPTCM-T45840  |  area:   |  feature: Backup Release
folder:/GRUB Bootloader  steps:1  obj:False
  - AWP-2648    0.496 [Bootloader            ] Boot system - backup release - backup file missing      :: Backup release will not be set when the release file does not exist. Automated: http://intranet.atlnz.lc/systest/ATPyLib/regressio
  - AWP-2650    0.483 [Bootloader            ] Boot system - backup release - setting a backup file th :: Test for when setting a backup file that is not a release but file name format is correct. Automated: http://intranet.atlnz.lc/sys
  - AWP-2642    0.433 [Bootloader            ] Boot system - Setting current and backup release        :: * Software upgrade must be a one-hit process - boot image and backup should not be set to the same file Automated: http://intranet
  - AWP-2639    0.407 [Bootloader            ] Boot system - Boot with a set release                   :: * Software upgrade must be a one-hit process - boot with a set release Automated: http://intranet.atlnz.lc/systest/ATPyLib/regress
  - AWP-2646    0.379 [Bootloader            ] Boot system - backup release - set backup file          :: Test that the device can have a backup release set and can boot with it if the main release fails. Automated: http://intranet.atln
  - AWP-2651    0.372 [Bootloader            ] Boot system - Boot with main and backup files set.      :: Functionality of backup file: Test that the device boots with a release and backup file set. Backup file should be used when speci
  - AWP-2652    0.371 [Bootloader            ] Boot system - Boot with backup file if release file un- :: Functionality of backup file: * backup file should be used when specified release file is not available or not set. Test that the 
  - AWP-24439   0.363 [ATMF                  ] ATMF API Firmware Distribution Precheck - Upgrade is sa :: ATMF API Firmware Distribution Precheck - Firmware to upgrade is same as the backup release | step1: Via API create a list of targ

### AWPTCM-T45841  |  area:   |  feature: Log Level and logging
folder:/GRUB Bootloader  steps:1  obj:False
  - AWP-6492    0.592 [z_Inactive            ] SSH server logging                                      :: SSH Server Tests | step1: ssh server logging - works and appropriate output. Log level can be changed => Verify ssh server logging
  - AWP-9337    0.584 [xSTP                  ] Logging                                                 :: | step1: Logging => accurate and useful
  - AWP-5519    0.540 [LLDP                  ] Logging                                                 :: Check logging is available and usable | step1: Logging is available and useful => Logging can be displayed via the console and the
  - AWP-12727   0.485 [MLD                   ] Logging exist for MLD                                   :: Verify logging works with MLD | step1: show log => display log output with correct information
  - AWP-9626    0.457 [xSTP                  ] MSTP logging                                            :: | step1: MSTP logging => Log entries for MSTP are shown.
  - AWP-6577    0.421 [RIP                   ] Device Management: RIP Logging                          :: Check RIP Logging is accurate and useful | step1: Configure RIP and RIP logging on DUT. Issue show log command. => RIP logging is 
  - AWP-22148   0.416 [Logging               ] FDB Logging - Show commands                             :: Configured fdb logging shows up in show command | step1: Configure fdb logging in configure terminal with 'mac address-table loggi
  - AWP-25780   0.407 [Logging               ] Disable logging to external media feature               :: Disable logging to external media feature | step1: Input the configuration and insert external media. log external usb:/log/messag

### AWPTCM-T45842  |  area:   |  feature: Kernel Arguments
folder:/GRUB Bootloader  steps:1  obj:False
  - AWP-14191   0.308 [z_Inactive            ] ARP flag changes in kernel must update NSM              :: Change the ARP flag in the kernel for interfaces like eth0, vlan1 and tunnel to verify the kernel updates NSM. | step1: Turn off A
  - AWP-14193   0.265 [z_Inactive            ] All multicast flag changes from kernel must update NSM  :: Check the changes of multicast flag under kernel updates NSM. | step1: Disable all multicast flag under kernel for interface like 
  - AWP-4420    0.264 [z_Inactive            ] help - test ? Help -Capitals are arguments              :: NOTE: This test case has been included under AWP-4417 help - test ? Help -Capitals are arguments | step1: ? help displays. Capital
  - AWP-14142   0.233 [z_Inactive            ] ECMP routes in NSM should update Kernel                 :: Adding multiple Ipv4 static routes with same metric for a destination should reflect in kernel. Test in stack[x610,x510,SB908], X9
  - AWP-28506   0.227 [Exception Handling    ] Check kernel panic core are written to the flash (CR-58 :: This test is as a result of CR-58729. | step1: At the shell prompt (start-shell) run the following command: simul-fail --panic-ker
  - AWP-12265   0.210 [PPP                   ] PPP - Operational - Neighbor route                      :: Once IPCP negotiation is complete, we learn the IP address of the remote end of the PPP. A host route to this address is added to 
  - AWP-10986   0.198 [VRF-Lite              ] VRF-Lite platform show commands                         :: New commands added in 542 to show platform tables per VRF instance | step1: awplus# show platform table ip vrf (NAME | <0-63>) awp
  - AWP-10523   0.195 [VRF-Lite              ] Ip tables, nsm, hardware and kernal uniform             :: To ensure that the software, hardware and kernel tables are uniform | step1: Check ip tables, nsm, hsl and kernel all the same => 

### AWPTCM-T45923  |  area:   |  feature: NLB
folder:/New Platform Template/Uncategorized Features  steps:1  obj:False
  - AWP-27318   0.538 [VRF-Lite              ] Check VRF-Lite works with NLB                           :: This comes from an external issue. See CR-58442. | step1: Ensure 10.200.5.100 can ping 128.1.0.17
  - AWP-22405   0.519 [MS NLB Support        ] Ping test between NLB server and switch with NLB suppor :: In this test - a real NLB equipped server should be used to test that a ping from the NLB server to the switch providing NLB suppo
  - AWP-21240   0.491 [IGMP                  ] NLB Multicast mode : Forwarding behavior                :: The switch should forward a packet which included destination Mac Address of Multicast Mac to specific ports which connected NLB s
  - AWP-21247   0.490 [IGMP                  ] NLB IGMP mode : Forwarding behavior                     :: The switch should forward a packet which included destination Mac Address of Multicast Mac to specific ports which connected NLB s
  - AWP-21635   0.471 [MS NLB Support        ] Ping test between NLB server and switch with NLB suppor :: In this test - a real NLB equipped server should be used to test that a ping from the NLB server to the switch providing NLB suppo
  - AWP-21602   0.457 [MS NLB Support        ] Ping test between NLB server and switch with NLB suppor :: In this test - a real NLB equipped server should be used to test that a ping from the NLB server to the switch providing NLB suppo
  - AWP-21242   0.424 [IGMP                  ] Interop CFC Fail over                                   :: Verify the combination CFC failover and Static ARP | step1: 1,Start Capture by ixia port1 2,Ping to NLB server from Client PC1-1 =
  - AWP-21241   0.421 [IGMP                  ] Interop VCS failover                                    :: Verify the combination with VCS and Static ARP | step1: 1,Start Capture by ixia port1 2,Ping to NLB server from Client PC1-1 => 1,

### AWPTCM-T45972  |  area:   |  feature: IPv4 VRF
folder:/New Platform Template/Uncategorized Features  steps:1  obj:False
  - AWP-12121   0.414 [VRRP                  ] InterOp with VRF                                        :: VRRP able to work and form in IPv4 global and local VRF VRRP able to work and form in IPv6 global VRF VRRP not supported in IPv6 l
  - AWP-24173   0.346 [ATMF                  ] Check Ping (IPv4 and IPv6) will be supported            :: Check Ping (IPv4 and IPv6) will be supported | step1: Check Ping (IPv4 and IPv6) will be supported => confirm Ping (IPv4 and IPv6)
  - AWP-25473   0.336 [IGMP                  ] no debug vrf NAME all                                   :: CLI Test | step1: Check command for tab complete, ? And help strings. Ensure vrf option works correctly where available. => Comman
  - AWP-24184   0.334 [ATMF                  ] Check IPv4 static routes will be supported              :: Check IPv4 static routes will be supported | step1: Check IPv4 static routes will be supported => confirm IPv4 static routes are s
  - AWP-25737   0.332 [VRF-Lite              ] ip mroute (vrf NAME|) A.B.C.D/M ( MROUTE_CLI_IPV4_PROTO :: CLI Test | step1: Ensure that all commands have correct context sensitive help, tab auto-complete and can survive a restart. Check
  - AWP-10983   0.331 [VRF-Lite              ] Sho interface information per VRF                       :: Use the following command to see interface information per VRF sho ip vrf sho ip vrf brief sho ip vrf detail sho ip vrf interface 
  - AWP-3729    0.331 [VRF-Lite              ] Sho interface information per VRF                       :: Use the following command to see interface information per VRF sho ip vrf sho ip vrf brief sho ip vrf detail sho ip vrf interface 
  - AWP-25641   0.330 [VRF-Lite              ] no debug vrf NAME all                                   :: CLI Test | step1: Ensure that all commands have correct context sensitive help tab auto-complete and check vrf option works correc

### AWPTCM-T45973  |  area:   |  feature: ECMP for BGP routes
folder:/New Platform Template/Uncategorized Features  steps:1  obj:False
  - AWP-7384    0.514 [IPv6 Static Routes and] ECMP Test                                               :: ECMP IPv6 should work correctly. Check port counters, to ensure that multiple paths are used. Check show commands to display mutlp
  - AWP-19500   0.436 [L3 Switching          ] ECMP - L3 Egress Mode Max ECMP Groups                   :: Confirm Maximum ECMP Groups. Same Next Hop Route be into same ECMP Group. | step1: Register max ECMP groups. Max next hop register
  - AWP-3520    0.432 [PIM-SM                ] Multicast and ECMP                                      :: Testing multicast over a network with ECMP, traffic recovers after network disruption | step1: Incorporate ECMP into the network, 
  - AWP-12474   0.429 [PIM-SMv6              ] Multicast and ECMP                                      :: Testing multicast over a network with ECMP, traffic recovers after network disruption | step1: Incorporate ECMP into the network, 
  - AWP-19501   0.424 [L3 Switching          ] ECMP - L3 Egress Mode One ECMP Group that will be fille :: Confirm one ECMP Group (Next hop A,B) that will be filled by max route. | step1: Register one ECMP Group with max route. Both IPv4
  - AWP-25830   0.410 [IPv4                  ] ECMP routing with interface name will co-exist with rou :: | step1: set ECMP route egress from ppp and normal nethop ip address with same distance => expect traffic should egress from all i
  - AWP-25829   0.403 [IPv4                  ] The maximum number of ECMP routes will be limited to th :: | step1: configuration at least 8 ECMP routes and show ip route => should see only 4 routes in use
  - AWP-19506   0.398 [L3 Switching          ] ECMP - Interoperability with VCS                        :: Confirm Interoperability with VCS. | step1: Execute master failover. => H/W table is correctly synced.

### AWPTCM-T46408  |  area:   |  feature: Multiple times vcs member reboot
folder:/New Platform Template/Uncategorized Features  steps:1  obj:False
  - AWP-3529    0.385 [PIM-SM                ] VCS Multicast traffic flowing - Multiple failovers      :: Fail over the master >3 times, traffic resumes | step1: Have traffic running, reboot stack members and perform master fail overs m
  - AWP-4484    0.367 [PIM-SM                ] VCS (VMAC) Multicast traffic flowing - Multiple failove :: Fail over the master >3 times, traffic resumes | step1: Have traffic running, reboot stack members and perform master fail overs m
  - AWP-25319   0.348 [PIM-SM                ] Multicast for VRFs - VCS multiple failovers PIM         :: Ensure that multicast communication is restored after multiple stack failovers when the associated interfaces are in a VRF | step1
  - AWP-22240   0.347 [QoS                   ] Multiple Reboot                                         :: This test is to ensure that the save QoS configuration will function correctly after multiple reboot. | step1: Configure and apply
  - AWP-18454   0.344 [Validation Scenario   ] VCS - ICMP Reply From VCS Member                        :: Test functionality of ICMP reply from VCS meber | step1: Configure appropriate Vlan and ip addresses
  - AWP-7188    0.340 [IGMP                  ] VCS and IGMP - Fail-over Member                         :: Fail-over Member | step1: Fail-over Member => Check that [Feature] uses MAC of Master when it rejoins the stack
  - AWP-12797   0.329 [MLD                   ] VCS and MLD - Fail-over Member                          :: Fail-over Member | step1: Fail-over Member => Check that [Feature] uses MAC of Master when it rejoins the stack
  - AWP-7192    0.314 [IGMP                  ] VCS (vmac enabled) and IGMP - Fail-over Member          :: Fail-over Member | step1: Fail-over Member => Check that [Feature] uses virtual-MAC on member

### AWPTCM-T46409  |  area:   |  feature: Multiple times vcs master reboot
folder:/New Platform Template/Uncategorized Features  steps:1  obj:False
  - AWP-3529    0.457 [PIM-SM                ] VCS Multicast traffic flowing - Multiple failovers      :: Fail over the master >3 times, traffic resumes | step1: Have traffic running, reboot stack members and perform master fail overs m
  - AWP-4484    0.436 [PIM-SM                ] VCS (VMAC) Multicast traffic flowing - Multiple failove :: Fail over the master >3 times, traffic resumes | step1: Have traffic running, reboot stack members and perform master fail overs m
  - AWP-25319   0.397 [PIM-SM                ] Multicast for VRFs - VCS multiple failovers PIM         :: Ensure that multicast communication is restored after multiple stack failovers when the associated interfaces are in a VRF | step1
  - AWP-22240   0.355 [QoS                   ] Multiple Reboot                                         :: This test is to ensure that the save QoS configuration will function correctly after multiple reboot. | step1: Configure and apply
  - AWP-4481    0.347 [PIM-SM                ] VCS Multicast trafic flowing - Slave failover           :: Fail over the master >3 times, traffic resumes | step1: Have traffic running, reboot stack members and perform master fail overs m
  - AWP-21471   0.334 [ATMF                  ] VAA License : License is retained after multiple reboot :: It is to be tested that license is retained after multiple reboot for VAA. | step1: Install AMF Master 10 nodes license => License
  - AWP-13591   0.319 [Logging               ] Logging - Master failover                               :: Test if there is any log errors on DUT after performing master failover DM - Note This is actually a VCS test case, not a logging 
  - AWP-27170   0.297 [AWC-lite              ] some of the multiple APs are down                       :: | step1: Confirm that reboot of connected AP is successful and that error message of failure of reboot is displayed.

### AWPTCM-T46410  |  area:   |  feature: Multiple times whole stack reboot
folder:/New Platform Template/Uncategorized Features  steps:1  obj:False
  - AWP-10034   0.369 [ICMP                  ] VMAC on - save config and reboot stack                  :: Confirm that config is saved successfully across the whole stack | step1: Check that [Feature] uses virtual-MAC when it is enabled
  - AWP-25924   0.324 [ACL                   ] Expand ACL limits for DC2552XS - VCS Reboot             :: | step1: Whole stack reboot 5 times. => Confirm that the ACL entries are NOT change before reboot.
  - AWP-18      0.322 [Software Licensing    ] CLI Delete a license to a whole stack                   :: Delete a license to all stack members by one command, while on a master console connection. | step1: Testing to be done on various
  - AWP-14      0.303 [Software Licensing    ] CLI Add a license to a whole stack                      :: Add a license to all stack members by one command, while on a master console connection. | step1: Testing to be done on various st
  - AWP-22240   0.295 [QoS                   ] Multiple Reboot                                         :: This test is to ensure that the save QoS configuration will function correctly after multiple reboot. | step1: Configure and apply
  - AWP-3529    0.274 [PIM-SM                ] VCS Multicast traffic flowing - Multiple failovers      :: Fail over the master >3 times, traffic resumes | step1: Have traffic running, reboot stack members and perform master fail overs m
  - AWP-4484    0.262 [PIM-SM                ] VCS (VMAC) Multicast traffic flowing - Multiple failove :: Fail over the master >3 times, traffic resumes | step1: Have traffic running, reboot stack members and perform master fail overs m
  - AWP-12455   0.254 [PIM-SMv6              ] Stack Seperation with multicast                         :: Fail over the master >3 times, traffic resumes | step1: Have traffic running, reboot stack members and perform master fail overs m

### AWPTCM-T46411  |  area:   |  feature: Pluggable/XEM Hotswap
folder:/New Platform Template/Uncategorized Features  steps:1  obj:False
  - AWP-10613   0.415 [Pluggable Transceivers] Command Handler: show system pluggable                  :: All pluggable information about pluggable inserted are displayed | step1: 1. Insert SPTX/SFP/XFP/SFP+/QSFP module in the DUT 2. Ex
  - AWP-10614   0.396 [Pluggable Transceivers] Command Handler: show system pluggable detail           :: All pluggable information about pluggable transceiver are displayed | step1: 1. Insert SPTX/SFP/XFP/SFP+/QSFP module in the DUT 2.
  - AWP-11016   0.391 [Pluggable Transceivers] Command handler : show system pluggable with port range :: Confirm that show sys pluggable can define port range | step1: Issue command show sys pluggable with port range => Confirm only po
  - AWP-13057   0.372 [Find Me               ] Hotswap XEM module                                      :: Verify how hotswap in and out will affect the feature | step1: Link some ports to ensure LEDs are up Or ports are active with traf
  - AWP-15168   0.361 [Pluggable Transceivers] Functional Test: SBx8100 - Hotswap LIF with pluggables  :: LIFs that accept pluggables: SBx81GS24 SBx81XS6 SBx81XS16 SBx81XLEM SBx81XLEM/XS8 SBx81XLEM/Q2 Performing a hotswap and ensuring t
  - AWP-3757    0.357 [VRRP                  ] VRRP resume after hotswap                               :: To verify VRRP can resume after hotswap | step1: Configure VRRP with neighbor attached to XEM interface Hotswap XEM out then in (f
  - AWP-13279   0.354 [Find Me               ] Hotswap XEM with pluggables                             :: Verify how hotswap in and out will affect the feature | step1: Link some ports to ensure LEDs are up Or ports are active with traf
  - AWP-10626   0.352 [Pluggable Transceivers] Functional Test: Hotswap XEM module                     :: Console message appear for each swap and detailed information, diagnostic are dispalyed for SFP/SFP+/XFP/SPTX. For SPTX no diagnos

### AWPTCM-T46433  |  area: Multi-speed port under auto speed -straight cable  |  feature: pluggable to pluggable
folder:/New Platform Template/Uncategorized Features  steps:1  obj:False
  - AWP-11016   0.417 [Pluggable Transceivers] Command handler : show system pluggable with port range :: Confirm that show sys pluggable can define port range | step1: Issue command show sys pluggable with port range => Confirm only po
  - AWP-10613   0.407 [Pluggable Transceivers] Command Handler: show system pluggable                  :: All pluggable information about pluggable inserted are displayed | step1: 1. Insert SPTX/SFP/XFP/SFP+/QSFP module in the DUT 2. Ex
  - AWP-10614   0.388 [Pluggable Transceivers] Command Handler: show system pluggable detail           :: All pluggable information about pluggable transceiver are displayed | step1: 1. Insert SPTX/SFP/XFP/SFP+/QSFP module in the DUT 2.
  - AWP-10615   0.324 [Pluggable Transceivers] Command Handler: show system pluggable diagnostic       :: All pluggable information diagnostics about pluggable are displayed Ensure as much as possible that values are correct: Field Issu
  - AWP-59      0.301 [Port Speed, Duplex and] Fixed Copper-1Gig-Straight-Auto                         :: Fixed Copper - 1Gig & Straight Through Cable - Auto DUT Port Type: Fixed Copper - 1 Gig Partner Port Type: Any Copper - 1 Gig Cabl
  - AWP-96      0.301 [Port Speed, Duplex and] SFP Copper-1Gig-Straight-Auto                           :: SFP Copper - 1Gig & Straight Through Cable - Auto DUT Port Type: SFP Copper - 1 Gig Partner Port Type: Any Copper - 1 Gig Cable Ty
  - AWP-92      0.295 [Port Speed, Duplex and] SFP Copper-1Gig-Straight-AUTO 100/Full-Auto             :: SFP Copper - 1Gig & Straight Through Cable - Speed/Duplex = AUTO 100/Full & Auto both ends DUT Port Type: SFP Copper - 1 Gig Partn
  - AWP-25123   0.295 [Port Speed, Duplex and] Fixed Copper-1Gig-Straight- Auto/Full-Polarity auto     :: Fixed Fixed - 1Gig & Straight Cable - Speed/Duplex = Auto/Full & Polarity auto Port Type: Fixed Fixed - 1 Gig Partner Port Type: A

### AWPTCM-T46434  |  area: Multi-speed port under auto speed  |  feature: crossover cable - pluggable to pluggable
folder:/New Platform Template/Uncategorized Features  steps:1  obj:False
  - AWP-11016   0.369 [Pluggable Transceivers] Command handler : show system pluggable with port range :: Confirm that show sys pluggable can define port range | step1: Issue command show sys pluggable with port range => Confirm only po
  - AWP-10613   0.360 [Pluggable Transceivers] Command Handler: show system pluggable                  :: All pluggable information about pluggable inserted are displayed | step1: 1. Insert SPTX/SFP/XFP/SFP+/QSFP module in the DUT 2. Ex
  - AWP-10614   0.343 [Pluggable Transceivers] Command Handler: show system pluggable detail           :: All pluggable information about pluggable transceiver are displayed | step1: 1. Insert SPTX/SFP/XFP/SFP+/QSFP module in the DUT 2.
  - AWP-10615   0.287 [Pluggable Transceivers] Command Handler: show system pluggable diagnostic       :: All pluggable information diagnostics about pluggable are displayed Ensure as much as possible that values are correct: Field Issu
  - AWP-108     0.246 [Port Speed, Duplex and] SFP Fibre-1Gig-AUTO 100/Full-Auto                       :: SFP Fibre - 1Gig - Speed/Duplex = AUTO 100/Full & Auto both ends DUT Port Type: SFP Fibre - 1 Gig Partner Port Type: Any Fibre - 1
  - AWP-23998   0.243 [Pluggable Transceivers] Functional Test: Repeated shutdown / no - shutdown of p :: Functional Test: Repeated shutdown / no - shutdown of port with pluggable | step1: Have your DUT paired up with another device usi
  - AWP-26799   0.240 [Port Speed, Duplex and] Fixed Copper -2.5G/5G - Auto/Auto/Auto                  :: 2.5/5 Gbit capable ports tested Use both Straight-through and Crossover cables. | step1: Set DUT: Speed: Default (AUTO) Duplex: De
  - AWP-26800   0.226 [Port Speed, Duplex and] Fixed Copper -2.5G/5G - 10Mb/Fixed-Polarity             :: 2.5/5 Gbit capable ports tested with Fixed Polarity Use both Straight-through and Crossover cables. | step1: Straight Through Cabl

### AWPTCM-T46435  |  area: Multi-speed port under auto speed  |  feature: crossover cable - pluggable to fixed copper
folder:/New Platform Template/Uncategorized Features  steps:1  obj:False
  - AWP-59      0.385 [Port Speed, Duplex and] Fixed Copper-1Gig-Straight-Auto                         :: Fixed Copper - 1Gig & Straight Through Cable - Auto DUT Port Type: Fixed Copper - 1 Gig Partner Port Type: Any Copper - 1 Gig Cabl
  - AWP-85      0.384 [Port Speed, Duplex and] Fixed Copper-1Gig-Cross-Auto                            :: Fixed Copper - 1Gig & Cross Over Cable - Auto DUT Port Type: Fixed Copper - 1 Gig Partner Port Type: Any Copper - 1 Gig Cable Type
  - AWP-26800   0.381 [Port Speed, Duplex and] Fixed Copper -2.5G/5G - 10Mb/Fixed-Polarity             :: 2.5/5 Gbit capable ports tested with Fixed Polarity Use both Straight-through and Crossover cables. | step1: Straight Through Cabl
  - AWP-26801   0.380 [Port Speed, Duplex and] Fixed Copper -2.5G/5G - 100Mb/Fixed-Polarity            :: 2.5/5 Gbit capable ports tested at with Fixed Polarity Use both Straight-through and Crossover cables. | step1: Straight Through C
  - AWP-26803   0.378 [Port Speed, Duplex and] Fixed Copper -2.5G/5G - 2.5Gb/Fixed-Polarity            :: 2.5/5 Gbit capable ports tested at with Fixed Polarity Use both Straight-through and Crossover cables. | step1: Straight Through C
  - AWP-26804   0.378 [Port Speed, Duplex and] Fixed Copper -2.5G/5G - 5Gb/Fixed-Polarity              :: 2.5/5 Gbit capable ports tested at with Fixed Polarity Use both Straight-through and Crossover cables. | step1: Straight Through C
  - AWP-25123   0.377 [Port Speed, Duplex and] Fixed Copper-1Gig-Straight- Auto/Full-Polarity auto     :: Fixed Fixed - 1Gig & Straight Cable - Speed/Duplex = Auto/Full & Polarity auto Port Type: Fixed Fixed - 1 Gig Partner Port Type: A
  - AWP-26798   0.374 [Port Speed, Duplex and] Fixed Copper -2.5G/5G - 5Gb/Auto/Auto                   :: 2.5/5 Gbit capable ports tested Use both Straight-through and Crossover cables. | step1: Set DUT and Link Partner Speed: 5Gb Duple

### AWPTCM-T46436  |  area: Multi-speed port under auto speed -straight cable  |  feature: pluggable to fixed copper
folder:/New Platform Template/Uncategorized Features  steps:1  obj:False
  - AWP-59      0.510 [Port Speed, Duplex and] Fixed Copper-1Gig-Straight-Auto                         :: Fixed Copper - 1Gig & Straight Through Cable - Auto DUT Port Type: Fixed Copper - 1 Gig Partner Port Type: Any Copper - 1 Gig Cabl
  - AWP-25123   0.490 [Port Speed, Duplex and] Fixed Copper-1Gig-Straight- Auto/Full-Polarity auto     :: Fixed Fixed - 1Gig & Straight Cable - Speed/Duplex = Auto/Full & Polarity auto Port Type: Fixed Fixed - 1 Gig Partner Port Type: A
  - AWP-12293   0.487 [Green Features (Ecofri] Fixed Copper_Straight / 10 / Auto                       :: Verify LPI cannot be set in 10BASE-T port | step1: Set DUT and partner device: Speed = 10 Duplex/Polarity = Auto ecofriendly lpi =
  - AWP-22514   0.485 [Port Speed, Duplex and] Fixed Copper-10Gig-Straight- 10/Full-Polarity auto      :: Fixed Copper - 10Gig & Straight Cable - Speed/Duplex = 10/Full & Polarity auto Port Type: Fixed Copper - 10 Gig Partner Port Type:
  - AWP-22440   0.482 [Port Speed, Duplex and] Fixed Copper-10Gig-Straight- 100/Full-Polarity auto     :: Fixed Copper - 10Gig & Straight Cable - Speed/Duplex = 100/Full & Polarity auto Port Type: Fixed Copper - 10 Gig Partner Port Type
  - AWP-25122   0.470 [Port Speed, Duplex and] Fixed Copper-1Gig-Straight- 1000/Full-Polarity auto     :: Fixed Fixed - 1Gig & Straight Cable - Speed/Duplex = 1000/Full & Polarity auto Port Type: Fixed Fixed - 1 Gig Partner Port Type: A
  - AWP-22442   0.465 [Port Speed, Duplex and] Fixed Copper-10Gig-Straight- 1000/Full-Polarity auto    :: Fixed Copper - 10Gig & Straight Cable - Speed/Duplex = 1000/Full & Polarity auto Port Type: Fixed Copper - 10 Gig Partner Port Typ
  - AWP-34      0.463 [Port Speed, Duplex and] Fixed Copper-1Gig-Straight-Defaults                     :: Fixed Copper - 1Gig & Straight Through Cable - Defaults DUT Port Type: Fixed Copper - 1 Gig Partner Port Type: Any Copper - 1 Gig 

### AWPTCM-T46898  |  area:   |  feature: Test date from uboot
folder:/Bootloader  steps:4  obj:False
ZEPHYR: Enter uboot shell and do a date reset | Wait for some seconds (>10 seconds to see it clearly) date M | In the uboot shell check date
  - AWP-18050   0.214 [Bootloader            ] Bootloader - u-boot CLI - date command - user can set d :: Date command in the u-boot is used by the factory to set the time and date on AW+ products. Automated: http://intranet.atlnz.lc/sy
  - AWP-2729    0.213 [Bootloader            ] Bootloader - Access to u-boot shell                     :: Test Functionality of Bootloader shell. Test Bootloader - Access to u-boot shell Automated: http://intranet.atlnz.lc/systest/ATPyL
  - AWP-2736    0.210 [Bootloader            ] Bootloader - u-boot CLI - epi3mk option MAC address     :: Personality Programming using Bootloader shell * Uboot can programming base unit * Uboot can show pensonality of base unit * Uboot
  - AWP-2733    0.203 [Bootloader            ] Bootloader - u-boot CLI - epi3mk option Year            :: Personality Programming using Bootloader shell * Uboot can programming base unit * Uboot can show pensonality of base unit * Uboot
  - AWP-2739    0.202 [Bootloader            ] Bootloader - u-boot CLI - epi3mk option OEM             :: Personality Programming using Bootloader shell * Uboot can programming base unit * Uboot can show pensonality of base unit * Uboot
  - AWP-2734    0.202 [Bootloader            ] Bootloader - u-boot CLI - epi3mk option Month           :: Personality Programming using Bootloader shell * Uboot can programming base unit * Uboot can show pensonality of base unit * Uboot
  - AWP-2737    0.198 [Bootloader            ] Bootloader - u-boot CLI - epi3mk option PCBRev          :: Personality Programming using Bootloader shell * Uboot can programming base unit * Uboot can show pensonality of base unit * Uboot
  - AWP-2735    0.193 [Bootloader            ] Bootloader - u-boot CLI - epi3mk option BoardID         :: Personality Programming using Bootloader shell * Uboot can programming base unit * Uboot can show pensonality of base unit * Uboot

### AWPTCM-T47184  |  area: Switching  |  feature: BFD - with EPSR
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-10084   0.305 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Static     :: Confirm that it is correctly configured over a LAG interface and traffic passes with linkup/down | step1: 1.) Configure VCS Stack 
  - AWP-9368    0.295 [xSTP                  ] Interop with EPSR                                       :: | step1: Interop with EPSR
  - AWP-10087   0.288 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Dynamic an :: Confirm configuration was correct over a LAG interface and traffic passes with linkup/down | step1: Link Aggregation - Dynamic. Co
  - AWP-10088   0.286 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Dynamic Ha :: Able to perform L3 hashing on IPv6 addresses with LAG Dynamic | step1: Link Aggregation - Dynamic . Hashing => L3 Hashing on IPv6 
  - AWP-13673   0.282 [Software Licensing    ] License Bundle - Base (ROW) (x610)                      :: License bundle - Base (ROW) for x610 platform | step1: x610 Verify Base license Must include: OSPF-64 VRRP VRRPv3 LAG-128 Virtual-
  - AWP-13682   0.280 [Software Licensing    ] License Bundle - Base (Japan) (x610)                    :: License bundle - Base (Japan) for x610 platform | step1: x610 Base License Must include: OSPF-64 VRRP VRRPv3 LAG-128 Virtual-MAC E
  - AWP-10085   0.269 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Static Has :: Able to perform L3 hashing on IPv6 addresses | step1: 1.) Configure VCS Stack 2.) Configure EPSR and Static Link Aggregation 3.) C
  - AWP-10089   0.262 [IPv6                  ] VCS - IPv6 switching after EPSR change - challenging re :: Check functionality if works well with challenging reconfigurations | step1: Implement challenging reconfigurations such as L2 top

### AWPTCM-T47185  |  area: Switching  |  feature: BFD - with STP
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-10078   0.434 [IPv6                  ] IPv6 Switching - stp topology change                    :: IPv6 and stp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that stp fo
  - AWP-3796    0.344 [VRRP                  ] VRRP Interop with STP                                   :: To verify interoperability of VRRP with STP | step1: -Setup VRRP and STP => - Confirm VRRP works with STP
  - AWP-9336    0.341 [xSTP                  ] Check STP commands in running config and startup config :: | step1: Confirm STP commands in running config & can be saved to startup config
  - AWP-6855    0.338 [Port Authentication   ] Port Authentication and STP                             :: Port Authentication and STP | step1: >> Please see the attached files => >> Refere to the attached document for expected results C
  - AWP-9331    0.324 [xSTP                  ] command line                                            :: | step1: Configure STP via the command line => STP can be configured properly using CLI
  - AWP-9637    0.306 [xSTP                  ] Interoperability with STP/RSTP                          :: | step1: MSTP interoperates correctly with STP/RSTP
  - AWP-9388    0.301 [xSTP                  ] Enable VMAC. Check that STP still functions correctly.  :: | step1: Enable VMAC. Check that STP still functions correctly. => STP should function without degradation
  - AWP-9381    0.294 [xSTP                  ] STP uses master mac when VMAC is disabled               :: | step1: Check that STP uses Master-MAC when Virtual-MAC is not enabled

### AWPTCM-T47186  |  area: Switching  |  feature: BFD - with RSTP
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-10077   0.401 [IPv6                  ] IPv6 Switching - rstp topology change                   :: IPv6 and rstp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that rstp 
  - AWP-3797    0.284 [VRRP                  ] VRRP Interop with RSTP                                  :: To verify interoperate between VRRP and RSTP | step1: -Setup VRRP and RSTP => - Confirm VRRP works with RSTP
  - AWP-6856    0.282 [Port Authentication   ] Port Authentication and RSTP                            :: Port Authentication and RSTP | step1: >> Please see the attached files Change spanning-tree mode to rstp => >> Please see the atta
  - AWP-9637    0.246 [xSTP                  ] Interoperability with STP/RSTP                          :: | step1: MSTP interoperates correctly with STP/RSTP
  - AWP-9370    0.238 [xSTP                  ] Interop with RSTP & MSTP on other devices.              :: | step1: Interop with RSTP & MSTP on other devices.
  - AWP-11431   0.229 [Validation Scenario   ] RSTP - Unicast Traffic                                  :: Check and verify RSTP for correct status and functionality. | step1: Run background unicast traffic in the relevant scenario. => S
  - AWP-13681   0.224 [Software Licensing    ] License Bundle - Base (Japan) (x510)                    :: License bundle - Base (Japan) for x510 platform | step1: x510 Base License Must include: VRRP VRRPv3 LAG-128 Virtual-MAC BFD IPv6 
  - AWP-9418    0.220 [xSTP                  ] SNMP/MIB                                                :: Verify RSTP operations reflects with SNMP/MIB | step1: SNMP/MIB Set SNMP on DUT Check RSTP operation on MIB browser, check RSTP op

### AWPTCM-T47187  |  area: Switching  |  feature: BFD - with MSTP
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-9626    0.405 [xSTP                  ] MSTP logging                                            :: | step1: MSTP logging => Log entries for MSTP are shown.
  - AWP-9627    0.404 [xSTP                  ] MSTP Debug                                              :: | step1: MSTP Debug => Debug messages must be generated by MSTP to the logging system.
  - AWP-6857    0.354 [Port Authentication   ] Port Authentication and MSTP                            :: Port Authentication and MSTP | step1: >> Please see the attached files => >> Refere to the attached document for expected results 
  - AWP-3798    0.349 [VRRP                  ] VRRP Interop with MSTP                                  :: To verify interoperability between VRRP and MSTP | step1: -Setup VRRP and MSTP => - Confirm VRRP works with MSTP
  - AWP-10278   0.320 [Process Monitoring    ] Memory Monitoring - MSTP                                :: Correct output information for MSTP | step1: Execute the command "show memory allocations" and capture output => Check memory info
  - AWP-9625    0.318 [xSTP                  ] MSTP commands in running config and startup config      :: | step1: After configuring MSTP on two devices, do the following: show running-config copy running-config startup-config => MSTP c
  - AWP-9370    0.305 [xSTP                  ] Interop with RSTP & MSTP on other devices.              :: | step1: Interop with RSTP & MSTP on other devices.
  - AWP-9638    0.284 [xSTP                  ] MSTP - stress - L2 traffic                              :: Confirm that when high traffic load is generated, no loop occurs in the network. | step1: L2 Traffic - Broadcast Setup an MSTP net

### AWPTCM-T47188  |  area: Switching  |  feature: BFD - with G.8032
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-25981   0.277 [G.8032                ] CLI: show platform commands for G.8032                  :: Object: Verify the "show platform" commands output for G.8032 Requirement: Project:1916_G8032 TFS section 4.1 Tech Support Require
  - AWP-26016   0.267 [G.8032                ] Functionallity: Every Port is a G.8032 Port             :: Verify that every port on the DUT can be a G.8032 port. | step1: Verify that every port on the DUT can be a G.8032 port. => That e
  - AWP-26019   0.252 [G.8032                ] Functionallity: G.8032 w/ CFM                           :: Verify G.8032 w/ CFM. | step1: Verify G.8032 w/ CFM.
  - AWP-26056   0.249 [G.8032                ] Interop: Port Auth and G.8032                           :: Verify that G.8032 and Port Authentication are not allowed to run on the same interface port or interface LAG. | step1: Verify tha
  - AWP-25980   0.226 [G.8032                ] CLI: show running-conifg for G.8032                     :: Object: Verify the "show running-config" command output for G.8032 Requirement: Project:1916_G8032 TFS section 4.1 Tech Support Re
  - AWP-13681   0.219 [Software Licensing    ] License Bundle - Base (Japan) (x510)                    :: License bundle - Base (Japan) for x510 platform | step1: x510 Base License Must include: VRRP VRRPv3 LAG-128 Virtual-MAC BFD IPv6 
  - AWP-26047   0.212 [G.8032                ] Interop: G.8032 Functionality on a Stack                :: Verify G.8032 functions correctly on Stacked Members. | step1: Disconnect one of the Ring interfaces and verify G.8032 functions a
  - AWP-13672   0.211 [Software Licensing    ] License Bundle - Base (ROW) (x510)                      :: License bundle - Base (ROW) for x510 platform | step1: x510 Verify Base license Must include: VRRP VRRPv3 LAG-128 Virtual-MAC BFD 

### AWPTCM-T47189  |  area: Switching HardwarePacketFilter(IP)  |  feature: ACLs for SNMPv3 groups
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-9855    0.303 [DHCP Snooping         ] DHCP Snooping - max-bindings when DHCP Snooping ACLs ar :: Confirm that max-bindings cannot be changed when dhcp snooping ACLs are applied to port | step1: max-bindings cannot be changed wh
  - AWP-9853    0.300 [DHCP Snooping         ] DHCP Snooping - dynamic channel groups untrusted        :: Confirm that entries for static channel group and dhcpsnooping ACLs are effective | step1: Dynamic Channel groups. (ACLs applied t
  - AWP-9946    0.296 [DHCP Snooping         ] DHCP Snooping ACLs - after hotswap                      :: Check ACLs in HW tables after hotswap | step1: DHCP Snooping ACLs applied correctly after hotswap in => Check ACLs in HW tables
  - AWP-9851    0.295 [DHCP Snooping         ] DHCP Snooping - static channel groups untrusted         :: Check that entries for static channel group and dhcpsnooping ACLs are effective | step1: Static channel groups Untrusted - Snoopin
  - AWP-9854    0.284 [DHCP Snooping         ] DHCP Snooping - dynamic channel groups across stack unt :: Confirm that entries for static channel group and dhcpsnooping ACLs are effective across stack | step1: Dynamic Channel groups acr
  - AWP-7110    0.279 [IGMP                  ] CLI Test - show ip igmp groups                          :: Use this command to display the multicast groups with receivers directly connected to the router, and learned through IGMP. | step
  - AWP-9852    0.276 [DHCP Snooping         ] DHCP Snooping - static channel groups across stack untr :: Check that entries for static channel group and dhcpsnooping ACLs are effective across stack | step1: Static Channel groups across
  - AWP-9916    0.260 [DHCP Snooping         ] DHCP snooping configued and Channel groups coming and g :: DHCP snooping working normally including ACLs | step1: DHCP snooping configued and Channel groups coming and going. => DHCP snoopi
