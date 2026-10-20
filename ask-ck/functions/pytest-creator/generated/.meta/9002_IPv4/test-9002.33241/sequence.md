# Sequence — AWPTCM-T33241

1. Record the baseline: capture 'show running-config interface lo' and 'show ip interface brief' (and 'show interface lo' if present) so later steps can compare for unchanged configuration. Ensure the test loopback address is not already configured.
   verify: Baseline output is captured and the loopback test address does not appear in the interface/address output.
2. Enter configure mode, enter 'interface lo' and assign a valid loopback IPv4 address with 'ip address <loopback-addr>/32'. Exit to privileged mode.
   verify: The command is accepted with no CLI error indication (no '% Invalid input' or similar message).
3. Read 'show ip interface brief' and 'show interface lo' (and 'show running-config interface lo').
   verify: The loopback interface row/section lists the assigned loopback address; the interface is shown as up/operational; running-config for the loopback contains the 'ip address' line.
4. From the DUT CLI, run 'ping <loopback-addr>' (a few packets).
   verify: Ping output shows replies received from the loopback address with 0% packet loss.
5. Record the physical-link-bearing ports from the .setup file's [portlink] section (the test port, the partner port and any other linked ports). On each, issue 'shutdown' one at a time; after each port is shut down, read 'show interface <port> status' and ping the loopback address from the DUT.
   verify: For each shutdown port, its status row does NOT read 'connected'. After every individual shutdown the ping to the loopback address still receives replies with 0% loss and 'show ip interface brief' still lists the loopback address.
6. With ALL linked ports now shut down, confirm none shows 'connected' in 'show interface status' (match each row by its first token being the port name), then ping the loopback address from the DUT and read 'show interface lo'.
   verify: No port row reads 'connected'. Ping to the loopback address still gets replies with 0% loss and the loopback address is still listed in the interface/address information.
7. Restore the links: issue 'no shutdown' on every port shut down in the previous steps, wait for the test port link to come up, then ping the loopback address again.
   verify: The test port's status row reads 'connected' again; ping to the loopback address still succeeds with 0% loss and the address is still shown.
8. Configure the partner (over its own CLI) or the traffic-capture host with an address in the same reachability path as the DUT test port, and ensure the DUT has a route/connected interface to it. Start tcpdump/Scapy sniffing on the partner-side capture interface for ICMP echo requests from the loopback address.
   verify: The DUT can reach the far-end address (plain ping from the DUT to the far-end address succeeds) and the capture is running.
9. On the DUT, run 'ping <far-end-addr> source <loopback-addr>' (a few packets).
   verify: The capture at the far end shows ICMP echo request packets whose IPv4 source address equals the loopback address and whose destination is the far-end address. (If the far end has a return route to the loopback, echo replies are also seen; the source-address check is the pass criterion.)
10. Attempt to assign each of these invalid addresses on the loopback interface, one entry per attempt, capturing the CLI response after each: (a) a multicast address 224.0.0.1/32, (b) the limited broadcast 255.255.255.255/32, (c) the 0.0.0.0/32 address, (d) the 127.0.0.1/8 reserved loopback-range address, (e) a class E address 240.0.0.1/32. After each attempt run 'show running-config interface lo' and 'show ip interface brief'. Publish nothing; each attempt is its own check of rejection.
   verify: Each attempt is refused with a CLI error indication (e.g. '% Invalid input' or an address-invalid message) as decided by the DUT; after each, the running-config for the loopback and the address listing are identical to the state after step 3, with the valid loopback address still present and the rejected address absent.
11. Ping the valid loopback address once more from the DUT after the rejected attempts.
   verify: Ping still receives replies with 0% loss, showing the existing configuration was left unchanged.
12. Enter 'interface lo' and remove the loopback address with 'no ip address <loopback-addr>/32' (or 'no ip address'), then exit to privileged mode.
   verify: The command is accepted with no CLI error indication.
13. Read 'show ip interface brief', 'show interface lo' and 'show running-config interface lo'.
   verify: The removed loopback address no longer appears in any of the outputs and the running-config has no 'ip address' line for it.
14. From the DUT CLI, run 'ping <loopback-addr>' (a few packets).
   verify: Ping gets no replies (100% packet loss or an unreachable indication) from the removed loopback address.
