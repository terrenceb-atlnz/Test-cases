# Sequence — AWPTCM-T33247

1. On the DUT, create test VLAN 10 and add the test port to it as a tagged trunk member. Create routed VLAN 20 on the source port as an untagged access member. Configure 'interface vlan10' / 'ip address 192.168.10.1/24' and 'interface vlan20' / 'ip address 192.168.20.1/24'.
   verify: Setup only, with no pass/fail check.
2. Configure two static ARP entries on the DUT in global configuration: 'arp 192.168.10.201 0000.5e00.5301 <test port>' and 'arp 192.168.10.202 0000.5e00.5302 <test port>'.
   verify: Setup only, with no pass/fail check.
3. On the traffic host attached to the test port, start Scapy ARP/ICMP responders on VLAN 10 for neighbours 192.168.10.11, .12, .13 and .14, each with its own unique MAC. On the traffic host attached to the source port, configure 192.168.20.100/24 with gateway 192.168.20.1. Start tcpdump on the test-port host interface, capturing ARP and IP.
   verify: Setup only, with no pass/fail check.
4. From the DUT, ping 192.168.10.11, .12, .13 and .14 (2 packets each). Then read 'show arp' and save the full table.
   verify: 'show arp' lists all four neighbours, each with the MAC its responder uses, on interface vlan10 and the test port, as dynamic entries. Both 192.168.10.201 (0000.5e00.5301) and 192.168.10.202 (0000.5e00.5302) are listed as static. Record the snapshot.
5. Stop all traffic toward the neighbours, with no pings and no host-originated traffic. Run 'clear arp-cache' on the DUT, then read 'show arp' straight away.
   verify: None of 192.168.10.11–.14 appear in 'show arp'. Both 192.168.10.201 and .202 are still present as static entries, with the same MAC, interface and port as in baselineArp.
6. Count the rows in the 'show arp' output captured in step 5, before any new traffic starts.
   verify: The global table contains no dynamic entries. The total row count equals the number of static entries (2), so it is lower than baselineCount by exactly the 4 cleared dynamic entries.
7. Ping 192.168.10.11–.14 from the DUT again so the cache refills, and check that 'show arp' matches baselineArp. Stop the traffic, run 'clear arp-cache 192.168.10.12', then read 'show arp' straight away.
   verify: 192.168.10.12 is missing. 192.168.10.11, .13 and .14 are still present as dynamic entries with their baseline MAC, interface and port. Both static entries are unchanged.
8. Count the rows in the 'show arp' output captured in step 7, before any new traffic starts.
   verify: The total row count is baselineCount minus 1. Only the 192.168.10.12 row is gone, and the global scope holds exactly 3 dynamic entries.
9. With traffic still stopped, run 'clear arp-cache 192.168.10.11' and check in 'show arp' that .11 is missing. From the source-port host, start a continuous UDP stream routed through the DUT to 192.168.10.11 and .12, for example 10 pps for 10 s, while tcpdump captures on the test-port host.
   verify: tcpdump shows ARP who-has requests from the DUT, with sender 192.168.10.1, for 192.168.10.11 and .12. 'show arp' then lists both as dynamic entries with their correct MACs again. tcpdump shows the routed UDP stream reaching both neighbours, and loss stops once ARP has resolved: every packet after the first ARP reply in the second half of the stream is received.
10. Stop all traffic, run 'clear arp-cache', and check in 'show arp' that no dynamic entries are left. From the source-port host, start the routed UDP stream to all of 192.168.10.11–.14 while tcpdump captures on the test-port host.
   verify: tcpdump shows the DUT sending an ARP request for each of the four neighbours. 'show arp' lists all four as dynamic entries again, with their baseline MACs. Every neighbour receives the stream, with no loss continuing after resolution. The static entries stay unchanged throughout.
11. On the DUT, run 'ip vrf red' and 'ip vrf blue'. Create VLAN 30 and VLAN 40 and add them as tagged VLANs on the test port. On 'interface vlan30' apply 'ip vrf forwarding red' then 'ip address 192.168.30.1/24'. On 'interface vlan40' apply 'ip vrf forwarding blue' then 'ip address 192.168.40.1/24'. On the test-port host, start Scapy responders for 192.168.30.11–.12 (VLAN 30) and 192.168.40.11–.12 (VLAN 40), each with its own unique MAC.
   verify: Setup only, with no pass/fail check.
12. Ping all global neighbours from the DUT, then ping the red and blue neighbours with 'ping vrf red 192.168.30.11', 'ping vrf red 192.168.30.12', 'ping vrf blue 192.168.40.11' and 'ping vrf blue 192.168.40.12'. Read 'show arp', 'show arp vrf red' and 'show arp vrf blue', and save each table.
   verify: The global table holds 192.168.10.11–.14 as dynamic entries plus the two static entries. The red VRF table holds 192.168.30.11 and .12 as dynamic entries on vlan30. The blue VRF table holds 192.168.40.11 and .12 as dynamic entries on vlan40.
13. Stop all traffic. Run 'clear arp-cache vrf red', then read 'show arp vrf red', 'show arp vrf blue' and 'show arp' straight away.
   verify: 192.168.30.11 and .12 are missing from the red VRF table. The blue VRF table and the global table match vrfBaseline exactly, including the static entries.
14. Count the rows in the 'show arp vrf red' output captured in step 13, before any new traffic starts.
   verify: The red VRF table contains no dynamic entries. Its entry count has dropped from 2 to 0, while the blue and global entry counts match vrfBaseline.
15. Refill the red VRF cache with 'ping vrf red 192.168.30.11' and 'ping vrf red 192.168.30.12'. Stop the traffic, run 'clear arp-cache vrf red 192.168.30.11', then read 'show arp vrf red', 'show arp vrf blue' and 'show arp' straight away.
   verify: 192.168.30.11 is missing from the red VRF table, and 192.168.30.12 is still there with its baseline MAC. The blue VRF table and the global table match vrfBaseline. The red entry count is exactly 1.
16. Refill the red VRF cache. Snapshot the global, red and blue tables, then run 'clear arp-cache 192.168.10.99', an address with no entry in any table. Snapshot all three tables again.
   verify: The DUT either rejects the command with an error indication or accepts it without output. Both are valid results, and the response should be logged. The global, red and blue tables are identical before and after the command, both row by row and in row count.
17. Snapshot the global, red and blue tables, then run 'clear arp-cache vrf red 192.168.30.99', an address with no entry in that VRF. Snapshot all three tables again.
   verify: The DUT either rejects the command with an error indication or accepts it without output. Both are valid results, and the response should be logged. The global, red and blue tables are identical before and after the command.
18. Snapshot the global, red and blue tables, then run 'clear arp-cache vrf nosuchvrf'. Snapshot all three tables again.
   verify: The DUT either rejects the command with an error indication (expected) or ignores it. The global, red and blue tables are identical before and after the command.
19. Snapshot 'show arp', then run 'clear arp-cache 192.168.10.201' against the static entry. Read 'show arp' and 'show running-config' straight away.
   verify: 192.168.10.201 is still listed as a static entry with MAC 0000.5e00.5301 on the test port. The running-config still contains the 'arp 192.168.10.201 0000.5e00.5301' line. All other entries match the snapshot. Any error indication or silent acceptance is logged as the DUT's handling and is acceptable either way.
