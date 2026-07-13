# Rerank batch 00  (cases 0..29)

### AWPTCM-T30649  |  area: IPv6 DNSandDHCPRelated  |  feature: DHCPv6 Server
folder:/New Platform Template/IPv6  steps:1  obj:False
  - AWP-24090   0.582 [DHCPv6                ] Config DHCPv6 dns-server to use interface with no assig :: To see what happens when an interface is configured as the dns-server with no IPv6 address configuration. | step1: Configure DUT D
  - AWP-24084   0.581 [DHCPv6                ] DHCPv6 Client Does not install default route            :: The default DHCPv6 client behavior is to not install a default route to the DHCPv6 server. | step1: Configure the DUT with IPv6 ad
  - AWP-24091   0.514 [DHCPv6                ] Check IPV6 DNS information is stored on device.         :: DNS information learnt via DHCPv6 should be stored and viewable on the DUT | step1: Configure a DHCPv6 server to supply IP and DNS
  - AWP-24085   0.512 [DHCPv6                ] DHCPv6 Client Default Route Enabled                     :: The device must be able to be configured to use DHCPv6 client to install an IPv6 default route via the DHCPv6 server. This functio
  - AWP-13791   0.511 [DHCPv6                ] DHCPv6 - Address Range                                  :: Should be able to configure address range on an IPv6 server. | step1: Configure DHCPv6 server with address pool range created from
  - AWP-13801   0.503 [DHCPv6                ] DHCPv6 - Counter works                                  :: The DHCPv6 Server counter should increment correctly. | step1: Request IPv6 address from client to server. Try to request address 
  - AWP-24086   0.494 [DHCPv6                ] DHCPv6 Client Default Route Removal                     :: A device conigured to install a default route via the DHCPv6 client must be able to remove this default route. | step1: Enable IPv
  - AWP-24113   0.480 [DHCPv6                ] DHCPv6 PD Client Default Route Removal                  :: A device configured to install a default route via the DHCPv6 Prefix Delegation client must be able to remove this default route, 

### AWPTCM-T33233  |  area: Port  |  feature: Auto Negotiation
folder:/New Platform Template/Port  steps:1  obj:True
ZEPHYR: OBJ: Verify port configuration using "auto" command. This test case cover port speeds. || The testing for this is covered by the auto test : https://w
  - AWP-12283   0.270 [Green Features (Ecofri] 1G_Fixed Copper_Cross / 1000 / Auto/ MDI                :: Verify LPI works with 1000 / Auto / MDI settings | step1: Set DUT and partner device: Speed = 1000 Duplex = Auto Polarity = MDI / 
  - AWP-23992   0.258 [Port Speed, Duplex and] Copper SFP-10Gig-Straight-Defaults-Auto/Auto-Polarity a :: NOTE: 1G/10G Fixed Speed and Full Duplex only supported on CPU based i2c platforms. ( x930, SBx81XLEM/XS8) Refer to TFS: https://i
  - AWP-104     0.242 [Port Speed, Duplex and] SFP Fibre-1Gig-MDIX/MDI                                 :: SFP Fibre - 1Gig - Speed/Duplex = Auto & MDIX/MDI mix DUT Port Type: SFP Fibre - 1 Gig Partner Port Type: Any Fibre - 1 Gig Steps:
  - AWP-112     0.240 [Port Speed, Duplex and] SFP Fibre-100M-MDIX/MDI                                 :: SFP Fibre - 100M - Speed/Duplex = Auto & MDIX/MDI mix DUT Port Type: SFP Fibre - 100M Partner Port Type: Any Fibre - 100M Steps: 1
  - AWP-35      0.235 [Port Speed, Duplex and] Fixed Copper-1Gig-Straight-MDIX/MDI                     :: Fixed Copper - 1Gig & Straight Through Cable - Speed/Duplex = Auto & MDIX/MDI mix DUT Port Type: Fixed Copper - 1 Gig Partner Port
  - AWP-38      0.235 [Port Speed, Duplex and] Fixed Copper-1Gig-Straight-MDI/MDIX                     :: Fixed Copper - 1Gig & Straight Through Cable - Speed/Duplex = Auto & MDI/MDIX mix DUT Port Type: Fixed Copper - 1 Gig Partner Port
  - AWP-108     0.232 [Port Speed, Duplex and] SFP Fibre-1Gig-AUTO 100/Full-Auto                       :: SFP Fibre - 1Gig - Speed/Duplex = AUTO 100/Full & Auto both ends DUT Port Type: SFP Fibre - 1 Gig Partner Port Type: Any Fibre - 1
  - AWP-98      0.228 [Port Speed, Duplex and] SFP Copper-1Gig-Cross-MDIX/MDI                          :: Version2: AW+ 5.4.1 onwards SFP Copper - 1Gig & Cross Over Cable - Speed/Duplex = Auto & MDIX/MDI mix DUT Port Type: SFP Copper - 

### AWPTCM-T33234  |  area: Port  |  feature: Auto MDI/MDI-X
folder:/New Platform Template/Port  steps:1  obj:True
ZEPHYR: OBJ: Verify port configuration using "auto" command. This test case cover port mdi/mdix. || The testing for this is covered by the auto test : https://w
  - AWP-12285   0.369 [Green Features (Ecofri] Auto_Fixed Copper_Straight / Auto / Full / MDI-MDIX     :: Verify LPI works with Auto/ Full / MDI-MDIX settings | step1: Set DUT and partner device: Speed = Auto Duplex = Full Polarity = MD
  - AWP-12283   0.362 [Green Features (Ecofri] 1G_Fixed Copper_Cross / 1000 / Auto/ MDI                :: Verify LPI works with 1000 / Auto / MDI settings | step1: Set DUT and partner device: Speed = 1000 Duplex = Auto Polarity = MDI / 
  - AWP-104     0.359 [Port Speed, Duplex and] SFP Fibre-1Gig-MDIX/MDI                                 :: SFP Fibre - 1Gig - Speed/Duplex = Auto & MDIX/MDI mix DUT Port Type: SFP Fibre - 1 Gig Partner Port Type: Any Fibre - 1 Gig Steps:
  - AWP-12286   0.356 [Green Features (Ecofri] Auto_Fixed Copper_Straight / Auto / Half / MDI-MDIX     :: Verify LPI works with Auto / Half / MDI-MDIX settings | step1: Set DUT and partner device: Speed = Auto Duplex = Half Polarity = M
  - AWP-112     0.356 [Port Speed, Duplex and] SFP Fibre-100M-MDIX/MDI                                 :: SFP Fibre - 100M - Speed/Duplex = Auto & MDIX/MDI mix DUT Port Type: SFP Fibre - 100M Partner Port Type: Any Fibre - 100M Steps: 1
  - AWP-35      0.350 [Port Speed, Duplex and] Fixed Copper-1Gig-Straight-MDIX/MDI                     :: Fixed Copper - 1Gig & Straight Through Cable - Speed/Duplex = Auto & MDIX/MDI mix DUT Port Type: Fixed Copper - 1 Gig Partner Port
  - AWP-38      0.350 [Port Speed, Duplex and] Fixed Copper-1Gig-Straight-MDI/MDIX                     :: Fixed Copper - 1Gig & Straight Through Cable - Speed/Duplex = Auto & MDI/MDIX mix DUT Port Type: Fixed Copper - 1 Gig Partner Port
  - AWP-12292   0.347 [Green Features (Ecofri] 10G_Fixed Copper_Straight / Auto / Full / MDI-MDIX      :: Verify LPI works in Auto / Full / MDI-MDIX setting | step1: Set DUT and partner device: Speed = Auto Duplex = Full Polarity = MDI 

### AWPTCM-T33235  |  area: Port  |  feature: Fixed port Speed
folder:/New Platform Template/Port  steps:1  obj:False
  - AWP-12294   0.497 [Green Features (Ecofri] Fixed Copper_Unsupported Speed                          :: Verify port status of unsupported speed | step1: Set DUT speed to 10 then connect it to HUB. Also, try configure 'ecofriendly lpi'
  - AWP-25123   0.386 [Port Speed, Duplex and] Fixed Copper-1Gig-Straight- Auto/Full-Polarity auto     :: Fixed Fixed - 1Gig & Straight Cable - Speed/Duplex = Auto/Full & Polarity auto Port Type: Fixed Fixed - 1 Gig Partner Port Type: A
  - AWP-25122   0.378 [Port Speed, Duplex and] Fixed Copper-1Gig-Straight- 1000/Full-Polarity auto     :: Fixed Fixed - 1Gig & Straight Cable - Speed/Duplex = 1000/Full & Polarity auto Port Type: Fixed Fixed - 1 Gig Partner Port Type: A
  - AWP-59      0.362 [Port Speed, Duplex and] Fixed Copper-1Gig-Straight-Auto                         :: Fixed Copper - 1Gig & Straight Through Cable - Auto DUT Port Type: Fixed Copper - 1 Gig Partner Port Type: Any Copper - 1 Gig Cabl
  - AWP-85      0.362 [Port Speed, Duplex and] Fixed Copper-1Gig-Cross-Auto                            :: Fixed Copper - 1Gig & Cross Over Cable - Auto DUT Port Type: Fixed Copper - 1 Gig Partner Port Type: Any Copper - 1 Gig Cable Type
  - AWP-22439   0.361 [Port Speed, Duplex and] Fixed Copper-10Gig-100/Full-Polarity auto               :: Fixed Copper - 10Gig & Cross Over Cable - Speed/Duplex = 100/Full & Polarity auto Port Type: Fixed Copper - 10 Gig Partner Port Ty
  - AWP-25125   0.360 [Port Speed, Duplex and] Fixed Copper-1Gig-Straight- Auto1000/Full-Polarity auto :: Fixed Fixed - 1Gig & Straight Cable - Speed/Duplex = Auto1000/Full & Polarity auto Port Type: Fixed Fixed - 1 Gig Partner Port Typ
  - AWP-22514   0.358 [Port Speed, Duplex and] Fixed Copper-10Gig-Straight- 10/Full-Polarity auto      :: Fixed Copper - 10Gig & Straight Cable - Speed/Duplex = 10/Full & Polarity auto Port Type: Fixed Copper - 10 Gig Partner Port Type:

### AWPTCM-T33236  |  area: Port  |  feature: Fixed Full or half Duplex
folder:/New Platform Template/Port  steps:1  obj:False
  - AWP-26792   0.446 [Port Speed, Duplex and] Fixed Copper -2.5G/5G - 10Mb/Half-Duplex                :: 2.5/5 Gbit capable ports tested at 10Mbit with Half Duplex Use both Straight-through and Crossover cables. | step1: Set DUT and Li
  - AWP-26793   0.442 [Port Speed, Duplex and] Fixed Copper -2.5G/5G - 100Mb/Half-Duplex               :: 2.5/5 Gbit capable ports tested at 100Mbit with Half Duplex Use both Straight-through and Crossover cables. | step1: Set DUT and L
  - AWP-83      0.437 [Port Speed, Duplex and] Fixed Copper-1Gig-Cross-10/Half-MDI to MDI              :: Fixed Copper - 1Gig & Cross Over Cable - Speed/Duplex = AUTO 10/Half & MDI both ends DUT Port Type: Fixed Copper - 1 Gig Partner P
  - AWP-22510   0.431 [Port Speed, Duplex and] CR-53726 - Half/Full Duplex configuration on ETH/VLAN p :: Confirm that changing the duplex configuration of an ETH or switchport would not cause the port LED to be OFF. | step1: In an ETH 
  - AWP-57      0.424 [Port Speed, Duplex and] Fixed Copper-1Gig-Straight- 10/Half-MDI to MDI          :: Fixed Copper - 1Gig & Straight Through Cable - Speed/Duplex = AUTO 10/Half & MDI both ends DUT Port Type: Fixed Copper - 1 Gig Par
  - AWP-75      0.423 [Port Speed, Duplex and] Fixed Copper-1Gig-Cross-100/Half-MDI to MDI             :: Fixed Copper - 1Gig & Cross Over Cable - Speed/Duplex = AUTO 100/Half & MDI both ends DUT Port Type: Fixed Copper - 1 Gig Partner 
  - AWP-82      0.423 [Port Speed, Duplex and] Fixed Copper-1Gig-Cross-10/Half-MDIX to MDIX            :: Fixed Copper - 1Gig & Cross Over Cable - Speed/Duplex = AUTO 10/Half & MDIX both ends DUT Port Type: Fixed Copper - 1 Gig Partner 
  - AWP-49      0.423 [Port Speed, Duplex and] Fixed Copper-1Gig-Straight-100/Half-MDI to MDI          :: Fixed Copper - 1Gig & Straight Through Cable - Speed/Duplex = AUTO 100/Half & MDI both ends DUT Port Type: Fixed Copper - 1 Gig Pa

### AWPTCM-T33237  |  area: Port  |  feature: Active Fiber Monitoring
folder:/New Platform Template/Port  steps:1  obj:False
  - AWP-21596   0.677 [Active Fiber Monitorin] Disable fiber-monitoring                                :: Verify that fiber-monitoring can be disabled | step1: Enable fiber-monitoring on interface, issue "show system fiber-monitoring" c
  - AWP-21547   0.546 [Active Fiber Monitorin] Fiber monitoring is turned off by default               :: Verify that fiber monitoring is turned-off by default | step1: Execute "show system fiber-minitoring" command => Command accepted 
  - AWP-21881   0.535 [Active Fiber Monitorin] Fiber Monitoring - Configured on a provisioned port     :: Test that fiber monitoring can be configured on a provisioned port Test that fiber monitoring logs a message if configuration is s
  - AWP-21631   0.531 [Active Fiber Monitorin] Fiber Monitoring: Debug Command                         :: Enabling and Disabling of debugging command Test that debug command is not written in the running configuration Test that log mess
  - AWP-21855   0.514 [Active Fiber Monitorin] Fiber Monitoring - Non-AT hardware                      :: Verify that non-AT hardware will not be supported for fiber monitoring | step1: Enable terminal monitor and debug for SFP/SFP+ por
  - AWP-21853   0.425 [Active Fiber Monitorin] Show tech support includes Show fiber-mon command       :: Test that "show system fiber-monitoring" command is included in tech support | step1: Plug in supported SFP/SFP+ on monitored port
  - AWP-21632   0.394 [Active Fiber Monitorin] Fiber Monitoring: Debug messages                        :: Test that when the received power is lower than the threshold, log messages will be printed out Test that when an unsupported SFP 
  - AWP-21854   0.359 [Active Fiber Monitorin] Log messages for unsupported hardware                   :: Test that when an SFP/SFP+ which is not DDM cable is enabled for fiber monitoring, a log messages will be Test that log messages a

### AWPTCM-T33241  |  area: IPv4 Local Interfaces  |  feature: Loopback Address
folder:/New Platform Template/IPv4  steps:1  obj:False
  - AWP-10240   0.398 [Diagnostic Application] Loopback                                                :: Loopback are discovered | step1: loopback (zero length cable) ena test cable po=x sh test cable po=x => confirm loopback discovere
  - AWP-22594   0.394 [Logging               ] Log host source on loopback Interface                   :: The switch should use loopback intercafe as source IP address when syslog is enabled and configured log host source | step1: Added
  - AWP-4660    0.385 [IPv4                  ] VCS - IP Local Loopback Address is preserved after Stac :: IP Local Loopback Address is preserved and remain working correctly after Stack Failover (Master and Slave). | step1: 1. Configure
  - AWP-21772   0.378 [PPP                   ] PPP IP Borrow from Loopback interface                   :: Verify that PPP interface can borrow IP address from a Loopback interface. | step1: Configure PPP interface to borrow IP address f
  - AWP-4498    0.372 [IPv4                  ] RIP-IP Loopback interface subnets advertised in RIP     :: Advertise IP Loopback inteface subnets via RIP when configured | step1: 1. Configure RIP network to include loopback int ip addres
  - AWP-3832    0.355 [IPv4                  ] Limits-Max Primary                                      :: Limits-Max Primary The maximum configurable primary ip address for loopback interface should be 1. | step1: 1. Configure a primary
  - AWP-3824    0.344 [IPv4                  ] SNMP Manager Connection                                 :: SNMP Manager Connection The SNMP Manager should be able to communicate with the DUT using its Loopback Interface IP address as the
  - AWP-22597   0.341 [Logging               ] Log host source with both IPv4 and IPv6 address         :: | step1: Set IPv4 syslog server and IPv6 syslog server both,then add loopback interface which was set IPv4 address and IPv6 addre 

### AWPTCM-T33242  |  area: IPv4  |  feature: ICMP
folder:/New Platform Template/IPv4  steps:1  obj:False
  - AWP-21047   0.408 [ATMF                  ] ATMF VM : The IP source address in an ICMP Echo Reply   :: ICMP echo request must be the same with ICMP echo reply. | step1: 1.1 Configure VLAN1 IP address on DUT (192.168.1.1) 1.2. Ping DU
  - AWP-10106   0.398 [IPv6                  ] ICMP Response performance                               :: Check ICMP response performance work as expected | step1: ICMP Response performance - particularly to ICMP Echo Request 1.) Config
  - AWP-9996    0.397 [ICMP                  ] The IP source address in an ICMP Echo Reply             :: ICMP echo request must be the same with ICMP echo reply. | step1: 1.1 Configure VLAN1 IP address on DUT (192.168.1.1) 1.2. Ping DU
  - AWP-2121    0.363 [SNMP                  ] RFC1213-MIB-VerifyOID-icmp                              :: RFC1213-MIB II-Verify OID NOT-ACCESSIBLE SNMP Access Type Objects | step1: Verify OID - icmp => OID should be 1.3.6.1.2.1.5
  - AWP-2071    0.340 [SNMP                  ] RFC2011-MIB-VerifyOID-icmp                              :: RFC2011-MIB (IP-MIB)- Verify OID NOT-ACCESSIBLE SNMP Access Types Objects | step1: Verify OID - icmp => OID value should be 1.3.6.
  - AWP-18454   0.339 [Validation Scenario   ] VCS - ICMP Reply From VCS Member                        :: Test functionality of ICMP reply from VCS meber | step1: Configure appropriate Vlan and ip addresses
  - AWP-8642    0.318 [ACL                   ] ACL: Named Hardware on port - ICMP                      :: ACL:Named Hardware on port - ICMP | step1: Apply ACL via interface Access-group - specify src/dest host & ICMP type. Also specify 
  - AWP-15940   0.310 [IPv4                  ] ping operation in "no ip forwarding"                    :: Confirm that sending ICMP Request/Reply when "no ip forwarding" in configured. | step1: Execute ping to DUT from PC1. => DUT send 

### AWPTCM-T33243  |  area: IPv4  ARP  |  feature: Gratuitous ARP
folder:/New Platform Template/IPv4  steps:1  obj:False
  - AWP-3802    0.558 [VRRP                  ] VRRP Interop with Gratuitous ARP                        :: To verify interoperability between VRRP and Gratuitous ARP | step1: Setup VRRP and Gratuitous ARP Monitor links on VRRP vlan. Crea
  - AWP-4359    0.536 [ARP                   ] Gratuitous ARP: On Link Up                              :: A Gratuitous ARP is transmitted by the device 5 seconds after link transitions to Up. | step1: Enable TCP dump or wireshark on Tes
  - AWP-6617    0.533 [RIP                   ] Operational: Gratuitous ARP Sent by Stack Uses Virtual  :: Check that the Gratuitous ARP sent by stack contains the configured MAC address (Virtual-MAC) | step1: Setup a stack with VMAC ena
  - AWP-4361    0.533 [ARP                   ] IP Gratuitous ARP: Command                              :: To verify acceptable parameters for "ip gratuitous-arp-link" command | step1: Test "ip gratuitous-arp-link <0-300>" command using 
  - AWP-14666   0.516 [Pause Control/Flow Con] Receive Gratuitous ARP packet                           :: | step1: Set to connect between DUT and IXIA.
  - AWP-4386    0.501 [ARP                   ] Gratuitous ARP & ARP: Master failover. VMAC On          :: VCS with Virtual MAC on. After a Master failover no misleading gratuitous ARP. | step1: Configure about 10 VLAN. Configure stack w
  - AWP-4364    0.494 [ARP                   ] Gratuitous ARP: After Start-up                          :: Gratuitous ARP sent per VLAN | step1: Configure at least 20 VLANS (ex. VLAN2-21) with IP Addresses Disable STP Configure a trunk p
  - AWP-4360    0.490 [ARP                   ] Gratuitous ARP: On IP Interface                         :: Gratuitous ARP on IP Interface changes. With and without STP | step1: With STP enabled Enable TCP dump or wireshark on Test Box Mi

### AWPTCM-T33246  |  area: IPv4 ARP  |  feature: ARP Polling
folder:/New Platform Template/IPv4  steps:3  obj:False
ZEPHYR: follow precondition | quickly remove ip address of vlan1 from DUT A and sh arp glo | quickly assign the same ip address to DUT C and sh arp globa
  - AWP-15363   0.302 [Web Authentication    ] Ping Polling                                            :: Ping Polling | step1: Refer to 2.4.1.doc => Refer to 2.4.1.doc
  - AWP-15366   0.270 [Web Authentication    ] Ping Polling - Error Message Check                      :: Ping Polling - Error Message Check | step1: Refer to 2.4.4.doc => Refer to 2.4.4.doc
  - AWP-15365   0.270 [Web Authentication    ] Ping Polling - Timeout                                  :: Ping Polling - Timeout | step1: Refer to 2.4.3.doc => Refer to 2.4.3.doc
  - AWP-4383    0.264 [ARP                   ] ARP and Virtual MAC                                     :: ARP supports Virtual MAC | step1: Setup a VCStack. Assign an IP address on the stack. => Stacks forms.
  - AWP-4396    0.249 [ARP                   ] ARP Log: Command                                        :: CLI test for arp log command - including mac-address-format | step1: Check "arp log" command (w/ or w/o parameters) Use "no arp lo
  - AWP-23821   0.246 [VRF-Lite              ] Clear ARP within a VRF.                                 :: clear arp-cache [vrf < vrf-name >|global] [< ip-address >] | step1: 1) Ping a connected device and check ARP is present using show
  - AWP-8722    0.245 [sFlow                 ] Configure sflow on vlan for polling or sampling         :: | step1: Configure sflow on the vlan for polling or sampling => Confirmed that sflow configuration is not allowed
  - AWP-3794    0.230 [VRRP                  ] VRRP Interop with ARP                                   :: To verify DUT does not advertise its MAC | step1: Setup VRRP on device Send ARP request to master => Confirm ARP does not contain 

### AWPTCM-T33247  |  area: IPv4 ARP  |  feature: Clear ARP
folder:/New Platform Template/IPv4  steps:1  obj:False
  - AWP-23821   0.594 [VRF-Lite              ] Clear ARP within a VRF.                                 :: clear arp-cache [vrf < vrf-name >|global] [< ip-address >] | step1: 1) Ping a connected device and check ARP is present using show
  - AWP-9729    0.463 [DHCP Snooping         ] DHCP Snooping - Clear ARP Security statistics           :: DHCP Snooping - Clear ARP Security statistics work as expected | step1: clear arp security statistics (interface ifrange | ) => Re
  - AWP-7626    0.390 [Policy Based Routing  ] Clear the ARP table with Policy Based Routing           :: With a Policy Clear ARP table and confirm classified traffic should arp for the PBR next hop and add entry in the HW table NB: Fie
  - AWP-4354    0.376 [ARP                   ] Proxy ARP: Command                                      :: Test proxy-arp command for errors | step1: Check Proxy ARP commands (any parameter) ip proxy-arp no ip proxy-arp Command must be a
  - AWP-4339    0.374 [ARP                   ] ARP Commands: Clear ARP                                 :: Ability to use "clear arp-cache" command to remove Dynamic ARP entries. Static ARPs not affected. Command affects HW table (shell-
  - AWP-4338    0.333 [ARP                   ] Show ARP: Command                                       :: Display ARP table | step1: Configure a Static ARP and use IXIA to send Dynamic ARP a. Add 5 static ARP b. Add 120 dynamic ARP usin
  - AWP-4337    0.331 [ARP                   ] Static ARP: CLI Help                                    :: Accurate static ARP help | step1: 1. Check Help for ARP commands (arp ?) 2. Check Tab function if working 3. Check Help for comman
  - AWP-4396    0.324 [ARP                   ] ARP Log: Command                                        :: CLI test for arp log command - including mac-address-format | step1: Check "arp log" command (w/ or w/o parameters) Use "no arp lo

### AWPTCM-T33248  |  area: IPv4 ARP  |  feature: Static ARP
folder:/New Platform Template/IPv4  steps:1  obj:False
  - AWP-4337    0.518 [ARP                   ] Static ARP: CLI Help                                    :: Accurate static ARP help | step1: 1. Check Help for ARP commands (arp ?) 2. Check Tab function if working 3. Check Help for comman
  - AWP-4341    0.512 [ARP                   ] Static ARP: Command                                     :: Static ARP command & functions | step1: Configure Static ARP on VLAN a. Configure VLAN with IP and configre Static ARP. b. Configu
  - AWP-4338    0.502 [ARP                   ] Show ARP: Command                                       :: Display ARP table | step1: Configure a Static ARP and use IXIA to send Dynamic ARP a. Add 5 static ARP b. Add 120 dynamic ARP usin
  - AWP-4342    0.490 [ARP                   ] Static ARP: Over Restart and Failover                   :: Static ARP works after failover or restart | step1: Configure Static ARP and restart DUT 1.Configure VLAN with IP. 2.Configure sta
  - AWP-4351    0.486 [ARP                   ] Static ARP and Static MAC Interoperability              :: Static ARP and Static MAC conflicts should not occur | step1: Configure VLAN with IP Address for at least 2 ports Configure a stat
  - AWP-9959    0.438 [DHCP Snooping         ] ARP Security - on static channel after master failover  :: Confirm normal operation on static channel after master failover | step1: ARP Security applied correctly on static channel group i
  - AWP-9958    0.437 [DHCP Snooping         ] ARP Security - on static channel after hotswap          :: Confirm normal operation on static channel after hotswap | step1: ARP Security applied correctly on static channel group interface
  - AWP-24184   0.431 [ATMF                  ] Check IPv4 static routes will be supported              :: Check IPv4 static routes will be supported | step1: Check IPv4 static routes will be supported => confirm IPv4 static routes are s

### AWPTCM-T33249  |  area: IPv4 ARP  |  feature: ARP Logging
folder:/New Platform Template/IPv4  steps:1  obj:False
  - AWP-9337    0.565 [xSTP                  ] Logging                                                 :: | step1: Logging => accurate and useful
  - AWP-9864    0.506 [DHCP Snooping         ] ARP Security - logging enabled/disabled/thrash          :: Confirm that ARP Security logs are created | step1: ARP Security logging enable/disable /thrash => ARP Security logs created. Some
  - AWP-5519    0.460 [LLDP                  ] Logging                                                 :: Check logging is available and usable | step1: Logging is available and useful => Logging can be displayed via the console and the
  - AWP-5476    0.386 [TFTP                  ] Logging of debug - Not Supported                        :: Test that debug logging is useful | step1: Logging of Debug accurate and useful => Logging of debug is accurate
  - AWP-8375    0.382 [MLD Snooping          ] Logging for MLD snooping                                :: | step1: Logging exists for MLD Snooping
  - AWP-9626    0.381 [xSTP                  ] MSTP logging                                            :: | step1: MSTP logging => Log entries for MSTP are shown.
  - AWP-4397    0.370 [ARP                   ] ARP Log: Functionality                                  :: ARP Logging correctly | step1: Configure "arp log" command Use "arp log mac-address-format ieee" command to remove Enable "termina
  - AWP-12727   0.369 [MLD                   ] Logging exist for MLD                                   :: Verify logging works with MLD | step1: show log => display log output with correct information

### AWPTCM-T33250  |  area: IPv4 ARP  |  feature: MC/Disparate ARPs
folder:/New Platform Template/IPv4  steps:1  obj:False
  - AWP-4348    0.297 [ARP                   ] Static ARP: Not Replaced by Dynamic ARP                 :: Static ARPs not replaced by dynamic ARPs | step1: Configure some Static ARPs on a VLAN 1.Configure VLAN with IP. 2.Configure stati
  - AWP-4380    0.256 [ARP                   ] ARP response performance                                :: ARP response performance | step1: Configure IP on an interface. From IXIA, setup an ARP stream that ARPs for the switch address. S
  - AWP-9857    0.244 [DHCP Snooping         ] DHCP Snooping - ARPs on untrusted port                  :: Confirm that ARPs are dropped | step1: ARPs on untrusted port not matching source from DHCP snooping binding database are dropped 
  - AWP-4352    0.238 [ARP                   ] Static and Dynamic ARP Flushed When VLAN Removed        :: ARPs flushed when VLAN removed from port | step1: a. Configure Static ARP to a port with VLAN b. Start ARP request and reply to po
  - AWP-4378    0.235 [z_Inactive            ] Dynamic ARPs can be added up to HW limit                :: Deactivated as duplicate test exists in Limits test suite: bugsearch/testlink/linkto.php ARP HW limit is achieved. | step1: Use IX
  - AWP-9869    0.235 [DHCP Snooping         ] ARP Security - switch act as Layer 3                    :: ARPs for switch IP are effectively blocked | step1: ARP Security when switch is acting as Layer 3 switch. Arps for the snooping sw
  - AWP-9860    0.233 [DHCP Snooping         ] DHCP Snooping - ARP behavior on other vlans             :: Confirm that ARPs are forwarded on vlans without arp-security enabled | step1: ARP still works normally on other vlans when ARP se
  - AWP-4339    0.230 [ARP                   ] ARP Commands: Clear ARP                                 :: Ability to use "clear arp-cache" command to remove Dynamic ARP entries. Static ARPs not affected. Command affects HW table (shell-

### AWPTCM-T33261  |  area: IPv6 SNMP  |  feature: SNMPv3
folder:/New Platform Template/IPv6  steps:1  obj:False
  - AWP-8772    0.413 [sFlow                 ] sFlow MIB - SNMPv3                                      :: Confirm can browse sFlow MIB from MIB browser using snmpv3 account | step1: snmpv3/snmpv2 => Ensure able to browse MIB from MIB br
  - AWP-1237    0.396 [SNMP                  ] SNMPv3-Access-Authentication only                       :: SNMPv3 Access Test With authentication but with no privacy. | step1: Access DUT via SNMP Manager with a SNMPv3 specified access. W
  - AWP-1238    0.383 [SNMP                  ] SNMPv3-Access-Authentication and Privacy                :: SNMPv3 Access Test With authentication and privacy | step1: Access DUT via SNMP Manager with a SNMPv3 specified access. With authe
  - AWP-1236    0.376 [SNMP                  ] SNMPv3-Access-No Authentication or Privacy              :: SNMPv3 Access Test With no authentication and no privacy | step1: Access DUT via SNMP Manager with a SNMPv3 specified access. With
  - AWP-1240    0.345 [SNMP                  ] VCS-SNMPv3-Access-Authentication only                   :: SNMPv3 Access Test With authentication but with no privacy, where DUT is a VCS stack. Set up DUT as VCS stack (max supported for m
  - AWP-1241    0.336 [SNMP                  ] VCS-SNMPv3-Access-Authentication and privacy            :: SNMPv3 Access Test With authentication and privacy, where DUT is a VCS stack. Set up DUT as VCS stack (max supported for model typ
  - AWP-1239    0.331 [SNMP                  ] VCS-SNMPv3-Access-No Authentication or Privacy          :: SNMPv3 Access Test With no authentication and no privacy, where DUT is a VCS stack. Set up DUT as VCS stack (max supported for mod
  - AWP-5836    0.293 [IPv6 Management       ] SNMP IPV6 : SNMP Manager access via ipv6                :: Test for the successful ipv6 connection between SNMP Manager and the device under test. | step1: Configure DUT and PC with ipv6 ad

### AWPTCM-T33263  |  area: IPv6  |  feature: MLD v2 Snooping
folder:/New Platform Template/IPv6  steps:1  obj:False
  - AWP-8375    0.588 [MLD Snooping          ] Logging for MLD snooping                                :: | step1: Logging exists for MLD Snooping
  - AWP-6414    0.573 [L2 Switching (L2 Learn] MLD                                                     :: MLD | step1: MLD => MLD
  - AWP-8360    0.557 [MLD Snooping          ] Command Line Handler - (no) ipv6 mld snooping           :: | step1: Command Handler: ipv6 mld snooping => Configured Globally/Per Vlan
  - AWP-8362    0.550 [MLD Snooping          ] Command Line Handler - (no) ipv6 mld snooping interface :: | step1: Command Handler: ipv6 mld snooping interface [vlan/port/static/LACP]
  - AWP-8384    0.534 [MLD Snooping          ] MLD Snooping counter with valid packets                 :: | step1: MLD Snooping counter operation check with valid packets
  - AWP-8385    0.529 [MLD Snooping          ] MLD Snooping counter with invalid packets               :: | step1: MLD Snooping counter operation check with invalid packets
  - AWP-8391    0.520 [MLD Snooping          ] MLD Snooping - ipv6 mld access-group                    :: Create an ACL to block a multicast group | step1: Create an ACL to block a particular multicast group => Group should not be forwa
  - AWP-8402    0.520 [MLD Snooping          ] MLD Snooping Interop with IGMP Snooping                 :: | step1: Ensure that both IGMP Snooping and MLD Snooping can operate independently of one another

### AWPTCM-T33265  |  area: Switching Trunking  |  feature: Port Trunking: manual configuration
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-13647   0.351 [Link Aggregation      ] Max trunking group (lacp)                               :: Verify max number of link aggregation (lacp). Defined by the total number of entries in the aggregation hardware table. The result
  - AWP-27874   0.339 [JITC Certification    ] V-5623:Port trunking must be disabled on all access por :: ---- Warning ---- TestLink Warning test case name is too long (131 chars) > 100 => has been truncated Original name V-5623:Port tr
  - AWP-5562    0.324 [LLDP                  ] Management address TLV: trunking                        :: Test for management address TLV transmit with trunking | step1: Change the mode of the port to be a trunk and assign several vlans
  - AWP-7910    0.312 [VRF-Lite              ] Setup 802.1Q Trunking with VRF-Lite                     :: To setup multiple VRF's and assign vlans to each VRF Assign a port to be a member of all vlans Pass L2 Traffic | step1: Program th
  - AWP-10776   0.297 [VRF-Lite              ] 802.1Q Trunking with L3 islolation                      :: To test L3 isolation on VRF lite using an 802.1Q trunk. | step1: ping the same vlan on the conencting switch. => the ip address sh
  - AWP-10753   0.297 [VRF-Lite              ] 802.1Q Trunking with L3 islolation                      :: To test L3 isolation on VRF lite using an 802.1Q trunk. | step1: ping the same vlan on the conencting switch. => the ip address sh
  - AWP-10752   0.290 [VRF-Lite              ] Setup 802.1Q Trunking with VRF lite                     :: To setup multiple VRF's and assign vlans to each VRF Assign a port to be a member of all vlans Assign an IP address to each of the
  - AWP-5778    0.272 [Hot Swap              ] Hot swap - XEM. General basic test -Trunking            :: Hot swap - XEM. General test that XEM hot-swap has no issues. | step1: 1. Bootup device with no config 2. Swap in and out all type

### AWPTCM-T33266  |  area: Switching Mirroring  |  feature: Port Mirror
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-8745    0.555 [sFlow                 ] sFlow and port mirroring                                :: Confirm when sflow is enable, port mirror is not allowed | step1: Enable sflow in DUT Configure port mirror in interface port with
  - AWP-8747    0.545 [sFlow                 ] check that mirroring can mirror a port in TX direction  :: | step1: check that mirroring can mirror a port in TX direction that has sflow on it => this should work on an x600 and fail on an
  - AWP-8746    0.539 [sFlow                 ] check that mirroring can mirror a port in RX direction  :: | step1: check that mirroring can mirror a port in RX direction that has sflow on it => this should work on an x600 and fail on an
  - AWP-20233   0.520 [sFlow                 ] Mirroring multiple ports with sFlow.                    :: Check mirroring multiple ports and across the instance with sFlow enabled. | step1: Configure mirror port.Source ports are 3ports.
  - AWP-6913    0.491 [Port Mirroring        ] CR30073 - CLI to disable port mirroring                 :: CR30073 - CLI to disable port mirroring | step1: Setup up mirror port for some ports on each stack and stack members. Issue no mir
  - AWP-23103   0.487 [RSPAN - Mirror to VLAN] RSPAN Egress: RSPAN Egress and port-mirroring on same d :: Remote-mirror-egress ports and port-mirroring can be on the same switch or stacked device. | step1: Configure remote-mirror interf
  - AWP-5312    0.466 [Port Mirroring        ] CLI show mirror                                         :: Verify show mirror command | step1: No mirror port was setup Command Handler: show mirror => No mirror port showed
  - AWP-3444    0.433 [Provisioning          ] Provisioned ports - Set port mirroring - mirror VLAN in :: Set port mirroring on a provisioned port, to mirror a VLAN interface. | step1: * Fit DUT with( XEM-STK (X900-12|x900-24 only) or A

### AWPTCM-T33267  |  area: Switching Mirroring  |  feature: VLAN Mirror
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-8747    0.489 [sFlow                 ] check that mirroring can mirror a port in TX direction  :: | step1: check that mirroring can mirror a port in TX direction that has sflow on it => this should work on an x600 and fail on an
  - AWP-8745    0.484 [sFlow                 ] sFlow and port mirroring                                :: Confirm when sflow is enable, port mirror is not allowed | step1: Enable sflow in DUT Configure port mirror in interface port with
  - AWP-8746    0.483 [sFlow                 ] check that mirroring can mirror a port in RX direction  :: | step1: check that mirroring can mirror a port in RX direction that has sflow on it => this should work on an x600 and fail on an
  - AWP-20233   0.473 [sFlow                 ] Mirroring multiple ports with sFlow.                    :: Check mirroring multiple ports and across the instance with sFlow enabled. | step1: Configure mirror port.Source ports are 3ports.
  - AWP-3444    0.437 [Provisioning          ] Provisioned ports - Set port mirroring - mirror VLAN in :: Set port mirroring on a provisioned port, to mirror a VLAN interface. | step1: * Fit DUT with( XEM-STK (X900-12|x900-24 only) or A
  - AWP-23103   0.433 [RSPAN - Mirror to VLAN] RSPAN Egress: RSPAN Egress and port-mirroring on same d :: Remote-mirror-egress ports and port-mirroring can be on the same switch or stacked device. | step1: Configure remote-mirror interf
  - AWP-6913    0.431 [Port Mirroring        ] CR30073 - CLI to disable port mirroring                 :: CR30073 - CLI to disable port mirroring | step1: Setup up mirror port for some ports on each stack and stack members. Issue no mir
  - AWP-5312    0.403 [Port Mirroring        ] CLI show mirror                                         :: Verify show mirror command | step1: No mirror port was setup Command Handler: show mirror => No mirror port showed

### AWPTCM-T33268  |  area: Switching PortSecurity  |  feature: Limited Mode
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-10077   0.283 [IPv6                  ] IPv6 Switching - rstp topology change                   :: IPv6 and rstp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that rstp 
  - AWP-10078   0.276 [IPv6                  ] IPv6 Switching - stp topology change                    :: IPv6 and stp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that stp fo
  - AWP-14444   0.267 [ACL                   ] ipv4-limited-ipv6 maximum ACL                           :: There is hardware rule mode "ipv4-limited-ipv6" test. So, if the device does not have this mode, it is excluded. | step1: Set the 
  - AWP-23059   0.235 [IGMP                  ] Verify reports from a single host for multiple groups a :: and vice versa. | step1: Set an IGMP Group limit of 10 on a port. => Configuration accepted.
  - AWP-10087   0.233 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Dynamic an :: Confirm configuration was correct over a LAG interface and traffic passes with linkup/down | step1: Link Aggregation - Dynamic. Co
  - AWP-10084   0.233 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Static     :: Confirm that it is correctly configured over a LAG interface and traffic passes with linkup/down | step1: 1.) Configure VCS Stack 
  - AWP-10088   0.232 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Dynamic Ha :: Able to perform L3 hashing on IPv6 addresses with LAG Dynamic | step1: Link Aggregation - Dynamic . Hashing => L3 Hashing on IPv6 
  - AWP-9316    0.228 [Web Authentication    ] DHCP mode on / DHCP server on / guest vlan on           :: dhcp mode dhcp mode without VCS command handler test functional test | step1: DHCP mode on / DHCP server on / guest vlan on Confir

### AWPTCM-T33270  |  area: Switching  |  feature: Disabling 10/100 Port at the Hardware Level
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-9457    0.247 [xSTP                  ] Device learning when enabling and disabling a port repe :: Ensure device learning operates correctly when enabling and disabling a port repeatedly with traffic | step1: Minimum of 3 switche
  - AWP-2480    0.246 [VRF-Lite              ] Through-put performance Inter VRF switching hardware    :: To check throughput performance (RFC2544) for traffic switched in hardware | step1: Setup a traffic path such that traffic is swit
  - AWP-16279   0.241 [PPPoE Client          ] PPPoE - Disabling a PPP Interface                       :: To confirm that a PPP interface will be normally initialized when disabled. | step1: Ping => Ping succeeds.
  - AWP-29644   0.218 [OpenFlow              ] ER-2059 - Repeat switching between hardware processing  :: Confirm that memory leak does not occur when repeat switching between hardware processing and software processing. | step1: Regist
  - AWP-29156   0.218 [OpenFlow              ] ER-2059 - Repeat switching between hardware processing  :: Confirm that memory leak does not occur when repeat switching between hardware processing and software processing. | step1: Regist
  - AWP-11143   0.202 [TACACS+               ] TACACS+ enable-disable privilege level                  :: This case shall test the feature to enable or disable a user's current privilege level. | step1: Login valid user and password as 
  - AWP-10077   0.191 [IPv6                  ] IPv6 Switching - rstp topology change                   :: IPv6 and rstp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that rstp 
  - AWP-12743   0.190 [MLD                   ] Disable All-Group port                                  :: Disabling ports on the ALL Group Port prevents communication on that port even though registration has been carried out. When the 

### AWPTCM-T33274  |  area: Switching EPSR  |  feature: - EPSR Mib
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-3991    0.547 [EPSR, EPSR+, EPSR++   ] EPSR Mib Support                                        :: EPSR Mib operation as expected | step1: atr-MIB supported => ATP
  - AWP-9368    0.455 [xSTP                  ] Interop with EPSR                                       :: | step1: Interop with EPSR
  - AWP-10084   0.433 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Static     :: Confirm that it is correctly configured over a LAG interface and traffic passes with linkup/down | step1: 1.) Configure VCS Stack 
  - AWP-10087   0.407 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Dynamic an :: Confirm configuration was correct over a LAG interface and traffic passes with linkup/down | step1: Link Aggregation - Dynamic. Co
  - AWP-10088   0.405 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Dynamic Ha :: Able to perform L3 hashing on IPv6 addresses with LAG Dynamic | step1: Link Aggregation - Dynamic . Hashing => L3 Hashing on IPv6 
  - AWP-10085   0.381 [IPv6                  ] VCS - IPv6 switching after EPSR change - LAG Static Has :: Able to perform L3 hashing on IPv6 addresses | step1: 1.) Configure VCS Stack 2.) Configure EPSR and Static Link Aggregation 3.) C
  - AWP-10089   0.374 [IPv6                  ] VCS - IPv6 switching after EPSR change - challenging re :: Check functionality if works well with challenging reconfigurations | step1: Implement challenging reconfigurations such as L2 top
  - AWP-7176    0.363 [IGMP                  ] Query Solicitation - EPSR+ and EPSR++                   :: EPSR+ and EPSR++ with QS | step1: EPSR+ and EPSR++ with QS => Query Solicits works with EPSR+ and EPSR++

### AWPTCM-T33275  |  area: Switching EPSR  |  feature: Enhanced Recovery
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-145     0.760 [Customer Scenario     ] EPSR enhanced recovery mode                             :: Confirm Enhanced Recovery mode works correctly. | step1: Confirm ESPR status. => Enhanced Recovery mode works correctly.
  - AWP-4083    0.645 [EPSR, EPSR+, EPSR++   ] Enhanced Recovery - disabled on EPSR Master node (Test  :: Enhanced recovery when it is not enabled on the master | step1: Enhanced recovery when it is not enabled on the master => Refer Su
  - AWP-4084    0.572 [EPSR, EPSR+, EPSR++   ] Enhanced Recovery - disabled on EPSR Transit node (Test :: Enhanced recovery when it is not enabled on the transit node | step1: Enhanced recovery when it is not enabled on the transit node
  - AWP-4076    0.437 [EPSR, EPSR+, EPSR++   ] Enhanced Recovery - Single link failure (Test Case 6.1. :: EPSR ring with enhancedrecovery mode on. Single link failures and recovers are all successful | step1: EPSR ring with enhancedreco
  - AWP-4096    0.434 [EPSR, EPSR+, EPSR++   ] Enhanced Recovery - VCS Master Failover (Test 6.1.19.3) :: EPSR with Stack as EPSR Master - power off Stack master unit then restore | step1: EPSR with Stack as EPSR Master - power off Stac
  - AWP-13200   0.432 [z_Inactive            ] Enable Enhanced Recovery, single link failure.          :: EPSR ring with enhancedrecovery mode on. Single link failures and recovers are all successful | step1: EPSR ring with enhancedreco
  - AWP-4095    0.407 [EPSR, EPSR+, EPSR++   ] Enhanced Recovery - VCS Slave Failover (Test 6.1.19.2)  :: EPSR with Stack as EPSR Master Enhancedrecover mode on. - power off Stack slave unit then restore | step1: EPSR with Stack as EPSR
  - AWP-4086    0.396 [EPSR, EPSR+, EPSR++   ] Enhanced Recovery - Link Failure - reconnect per link ( :: Testing Link failure per link - disconnect and reconnect per link. | step1: EPSR 2 Domain setup. One link down. Removing all links

### AWPTCM-T33276  |  area: Switching STP  |  feature: STP
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-10078   0.643 [IPv6                  ] IPv6 Switching - stp topology change                    :: IPv6 and stp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that stp fo
  - AWP-3796    0.544 [VRRP                  ] VRRP Interop with STP                                   :: To verify interoperability of VRRP with STP | step1: -Setup VRRP and STP => - Confirm VRRP works with STP
  - AWP-9336    0.539 [xSTP                  ] Check STP commands in running config and startup config :: | step1: Confirm STP commands in running config & can be saved to startup config
  - AWP-6855    0.534 [Port Authentication   ] Port Authentication and STP                             :: Port Authentication and STP | step1: >> Please see the attached files => >> Refere to the attached document for expected results C
  - AWP-9331    0.513 [xSTP                  ] command line                                            :: | step1: Configure STP via the command line => STP can be configured properly using CLI
  - AWP-9637    0.483 [xSTP                  ] Interoperability with STP/RSTP                          :: | step1: MSTP interoperates correctly with STP/RSTP
  - AWP-9388    0.475 [xSTP                  ] Enable VMAC. Check that STP still functions correctly.  :: | step1: Enable VMAC. Check that STP still functions correctly. => STP should function without degradation
  - AWP-9381    0.464 [xSTP                  ] STP uses master mac when VMAC is disabled               :: | step1: Check that STP uses Master-MAC when Virtual-MAC is not enabled

### AWPTCM-T33277  |  area: Switching STP  |  feature: RSTP
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-9637    0.629 [xSTP                  ] Interoperability with STP/RSTP                          :: | step1: MSTP interoperates correctly with STP/RSTP
  - AWP-10077   0.537 [IPv6                  ] IPv6 Switching - rstp topology change                   :: IPv6 and rstp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that rstp 
  - AWP-10078   0.500 [IPv6                  ] IPv6 Switching - stp topology change                    :: IPv6 and stp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that stp fo
  - AWP-13049   0.487 [Find Me               ] Interop with STP and RSTP                               :: Verify it works with STP and RSTP | step1: Link some ports to ensure LEDs are up Or ports are active with traffic flowing Configur
  - AWP-6855    0.471 [Port Authentication   ] Port Authentication and STP                             :: Port Authentication and STP | step1: >> Please see the attached files => >> Refere to the attached document for expected results C
  - AWP-12297   0.427 [Green Features (Ecofri] EEE interop with STP and RSTP                           :: Verify EEE works with STP and RSTP | step1: Set DUT: spanning-tree mode rstp ecofriendly lpi Set partner device: spanning-tree mod
  - AWP-3797    0.380 [VRRP                  ] VRRP Interop with RSTP                                  :: To verify interoperate between VRRP and RSTP | step1: -Setup VRRP and RSTP => - Confirm VRRP works with RSTP
  - AWP-6856    0.378 [Port Authentication   ] Port Authentication and RSTP                            :: Port Authentication and RSTP | step1: >> Please see the attached files Change spanning-tree mode to rstp => >> Please see the atta

### AWPTCM-T33278  |  area: Switching STP  |  feature: MSTP
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-9626    0.528 [xSTP                  ] MSTP logging                                            :: | step1: MSTP logging => Log entries for MSTP are shown.
  - AWP-9627    0.526 [xSTP                  ] MSTP Debug                                              :: | step1: MSTP Debug => Debug messages must be generated by MSTP to the logging system.
  - AWP-11487   0.486 [xSTP                  ] STP Debugging                                           :: | step1: Debugging modes are : all all cli CLI Commands packet MSTP Packets protocol Protocol timer MSTP Timers => accurate and us
  - AWP-10078   0.468 [IPv6                  ] IPv6 Switching - stp topology change                    :: IPv6 and stp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that stp fo
  - AWP-6857    0.461 [Port Authentication   ] Port Authentication and MSTP                            :: Port Authentication and MSTP | step1: >> Please see the attached files => >> Refere to the attached document for expected results 
  - AWP-3798    0.454 [VRRP                  ] VRRP Interop with MSTP                                  :: To verify interoperability between VRRP and MSTP | step1: -Setup VRRP and MSTP => - Confirm VRRP works with MSTP
  - AWP-9637    0.453 [xSTP                  ] Interoperability with STP/RSTP                          :: | step1: MSTP interoperates correctly with STP/RSTP
  - AWP-26785   0.434 [CFM                   ] Interop:STP/MSTP and CFM                                :: Verify CFM can function with STP and MSTP. | step1: Verify that STP is running on the CFM interface: show span brief => That CFM a

### AWPTCM-T33279  |  area: Switching STP  |  feature: BPDU Forwarding
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-9400    0.535 [xSTP                  ] BPDU Forwarding behavior with spanning tree protocols   :: BPDU Forwarding (x600 only) | step1: BPDU Forwarding cannot enabled with spanning tree protocols (stp, rstp, mstp) => BPDU Forward
  - AWP-24882   0.509 [xSTP                  ] BPDU Forwarding behavior with spanning tree protocols   :: BPDU Forwarding (x930,SBx908,SBx81CFC400,SBx81CFC960) | step1: BPDU Forwarding cannot enabled with spanning tree protocols (stp, r
  - AWP-10078   0.473 [IPv6                  ] IPv6 Switching - stp topology change                    :: IPv6 and stp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that stp fo
  - AWP-9401    0.456 [xSTP                  ] BPDU Forwarding - including multiple vlans and trunk mo :: BPDU Forwarding (x600 only) | step1: Functionality: BPDU Forwarding - including multiple vlans and trunk mode ports => NO vlan tag
  - AWP-9407    0.440 [xSTP                  ] Protocol Interop: BPDU Forwarding across static channel :: BPDU Forwarding (x600 only) | step1: Protocol Interop: BPDU Forwarding across static channels => Static channel groups should act 
  - AWP-24883   0.431 [xSTP                  ] BPDU Forwarding - including multiple vlans and trunk mo :: BPDU Forwarding (x930,SBx908,SBx81CFC960,SBx81CFC400) | step1: Functionality: BPDU Forwarding - including multiple vlans and trunk
  - AWP-24888   0.418 [xSTP                  ] Protocol Interop: BPDU Forwarding across static channel :: BPDU Forwarding (x930,SBx908,SBx81CFC400,SBx81CFC960) | step1: Protocol Interop: BPDU Forwarding across static channels => Static 
  - AWP-9409    0.417 [xSTP                  ] Protocl Interop: BPDU Forwarding with 802.1x            :: BPDU Forwarding (x600 only) | step1: Protocl Interop: BPDU Forwarding with 802.1x => Behaviour to be determined - 802.1x uses a fo

### AWPTCM-T33280  |  area: Switching STP  |  feature: BPDU Guard
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-7545    0.565 [Storm Control         ] Interop with BPDU-guard feature                         :: Test that BPDU guard and packet storm protection can be configured together. | step1: Interop with bpdu-guard feature - which can 
  - AWP-9439    0.441 [xSTP                  ] Command implementation of spanning-tree portfast bpdu-g :: | step1: Command implementation: spanning-tree portfast bpdu-guard => - Portfast Globally enabled, disabled on port -off - portfas
  - AWP-10078   0.365 [IPv6                  ] IPv6 Switching - stp topology change                    :: IPv6 and stp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that stp fo
  - AWP-9440    0.336 [xSTP                  ] Command implementation of spanning-tree autoedge on por :: Verify spanning-tree autoedge operates accordingly | step1: - Setup 3 switch w/ RSTP environment(all ports are in vlan1) - configu
  - AWP-9400    0.335 [xSTP                  ] BPDU Forwarding behavior with spanning tree protocols   :: BPDU Forwarding (x600 only) | step1: BPDU Forwarding cannot enabled with spanning tree protocols (stp, rstp, mstp) => BPDU Forward
  - AWP-9346    0.320 [xSTP                  ] BPDU's not tagged in VLAN Trunk mode                    :: BPDU's not tagged in VLAN Trunk mode | step1: Configure tagged Ports between devices on the topology. => Verify that BPDU's not ta
  - AWP-24882   0.318 [xSTP                  ] BPDU Forwarding behavior with spanning tree protocols   :: BPDU Forwarding (x930,SBx908,SBx81CFC400,SBx81CFC960) | step1: BPDU Forwarding cannot enabled with spanning tree protocols (stp, r
  - AWP-9403    0.280 [xSTP                  ] BPDU Forward-vlan                                       :: BPDU Forwarding (x600 only) | step1: BPDU Forward-vlan => (expected behaviour with trunk mode ports to be determined….) NO vlan ta

### AWPTCM-T33281  |  area: Switching STP  |  feature: BPDU Filter
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-10078   0.413 [IPv6                  ] IPv6 Switching - stp topology change                    :: IPv6 and stp should work as expected | step1: Setup IPv6 on L2 redundant topology. Implement changes in L2 topology so that stp fo
  - AWP-9400    0.379 [xSTP                  ] BPDU Forwarding behavior with spanning tree protocols   :: BPDU Forwarding (x600 only) | step1: BPDU Forwarding cannot enabled with spanning tree protocols (stp, rstp, mstp) => BPDU Forward
  - AWP-9438    0.364 [xSTP                  ] Command implementation of spanning-tree portfast bpdu-f :: | step1: Command implementation: spanning-tree portfast bpdu-filter => - ports set to portfast use this (unless overridden by port
  - AWP-9346    0.362 [xSTP                  ] BPDU's not tagged in VLAN Trunk mode                    :: BPDU's not tagged in VLAN Trunk mode | step1: Configure tagged Ports between devices on the topology. => Verify that BPDU's not ta
  - AWP-24882   0.360 [xSTP                  ] BPDU Forwarding behavior with spanning tree protocols   :: BPDU Forwarding (x930,SBx908,SBx81CFC400,SBx81CFC960) | step1: BPDU Forwarding cannot enabled with spanning tree protocols (stp, r
  - AWP-9471    0.331 [xSTP                  ] Interop with VLANS ingress filter                       :: | step1: Interop with VLANS ingress filter => BPDU must not be filtered even if ingress filtering is on - access & trunk ports
  - AWP-9377    0.331 [xSTP                  ] Interop with VLANS ingress filter                       :: | step1: Interop with VLANS ingress filter => BPDU must not be filtered even if ingress filtering is on - access & trunk ports
  - AWP-9403    0.317 [xSTP                  ] BPDU Forward-vlan                                       :: BPDU Forwarding (x600 only) | step1: BPDU Forward-vlan => (expected behaviour with trunk mode ports to be determined….) NO vlan ta

### AWPTCM-T33283  |  area: Switching  |  feature: PVST+ compatibility
folder:/New Platform Template/Switching  steps:1  obj:False
  - AWP-5497    0.241 [TFTP                  ] TFTP compatibility with AT-TFTP server                  :: Objective: To test TFTP compatibility with a server using AT-TFTP Expected Outcome: TFTP should be able to download and upload fil
  - AWP-13782   0.229 [EPSR, EPSR+, EPSR++   ] Compatibility test with Port Security                   :: Confirm that working together EPSR and Port Security | step1: Configure EPSR setting on more than 3 Units. => Port-secutiry is cor
  - AWP-4012    0.225 [EPSR, EPSR+, EPSR++   ] EPSR compatibility other ATL switch                     :: Compatibiliy of ATL EPSR other ATL switch family, i.e TN9400 | step1: redundancy of EPSR => Confirm redundancy and that unicast st
  - AWP-4011    0.224 [EPSR, EPSR+, EPSR++   ] EPSR compatibility other switch vendor                  :: Compatibiliy of ATL EPSR with other swtich vendor EPSR, i.e. Extreme | step1: Redundancy of EPSR => Confirm redundancy and that un
  - AWP-9472    0.217 [xSTP                  ] Interop with cisco                                      :: Verify alliedware plus' RSTP works with cisco's rapid-pvst | step1: Create RSTP topology between DUT(AW+) and cisco switch Check R
  - AWP-28698   0.212 [File System           ] Compatibility Test                                      :: Hardware of x230 128MB flash is used by several products. So we should do compatibility test. IE210L series and x230-17L should wo
  - AWP-22192   0.196 [ATMF                  ] Test backwards compatibility                            :: Backwards compatibility will be tested in the network to make sure the exsiting ATMF funcitonalities are not broken | step1: Load 
  - AWP-13781   0.194 [EPSR, EPSR+, EPSR++   ] Compatibility test with DHCP Snooping                   :: DHCP Snooping is working correctly - Trusted Port and Untrusted Port | step1: Configure EPSR setting On more than 3 Units. => Trus
