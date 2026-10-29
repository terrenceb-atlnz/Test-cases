# Sequence — AWPTCM-T33247

1. Set the DUT to a known base state. Create the test VLAN, add the test port to it as an access port, and give the VLAN interface an IPv4 address, e.g. 'interface vlan<test>' then 'ip address 192.168.10.1/24'. Connect the traffic host (Scapy/tcpdump) to the test port. On that host, emulate four neighbours, N1 to N4, each with its own IP in 192.168.10.0/24 and its own unique MAC. Each neighbour answers ARP requests for its own IP only while its responder is enabled.
   verify: No check here (setup). The script reads the port names from the .setup [portlink] section.
2. Configure two static ARP entries on the DUT for addresses in the test subnet that no emulated neighbour uses, S1 and S2. Use 'arp <S-ip> <S-mac> <test port>' for each.
   verify: No check here (setup). Step 4 checks the static entries.
3. Configure two VRFs on the DUT, VRF-A and VRF-B, with 'ip vrf <name>'. Create two more VLANs and add a VRF-test port to each. Bind one VLAN to each VRF with 'ip vrf forwarding <name>' before giving it an address, e.g. 'ip address 172.16.1.1/24' for VRF-A and 'ip address 172.16.2.1/24' for VRF-B. On the traffic host, emulate neighbours A1 and A2 in VRF-A's subnet, and B1 and B2 in VRF-B's subnet. Keep N1 to N4 in the global table on the test VLAN. Add one static ARP entry inside VRF-A for an unused address SA1, using 'arp vrf VRF-A <SA1-ip> <SA1-mac> <port>'.
   verify: No check here (setup). The VRF steps depend on this. The DUT must have the VRF feature or licence.
4. Populate the global cache. With N1 to N4 answering ARP, send IP traffic from the DUT to each of them, e.g. 'ping <Nx-ip> repeat 3' from the DUT's CLI. Then stop all neighbour traffic and disable the ARP responders so nothing can trigger relearning. Read 'show arp'.
   verify: 'show arp' lists N1 to N4, each with its emulated MAC on the test VLAN, as dynamic entries. It lists S1 and S2 as static entries with their configured MACs. Record the full table as the baseline.
5. With traffic stopped, run 'clear arp-cache' on the DUT.
   verify: The command is accepted with no error.
6. Immediately after step 5, before any traffic resumes, read 'show arp'.
   verify: None of N1 to N4 appears. S1 and S2 are still present as static entries with exactly the IP-to-MAC mappings and interfaces from arpBaselineGlobal. The number of entries equals the step 4 total minus dynCountGlobal.
7. Enable the N1 to N4 responders again and ping each of them once from the DUT so the dynamic entries come back. Stop traffic and disable the responders. Read 'show arp'. Then run 'clear arp-cache <N2-ip>'.
   verify: Before the clear, 'show arp' lists N1 to N4 as dynamic and S1 and S2 as static, giving the pre-clear table. The single-address clear is accepted with no error.
8. Immediately after step 7, with no traffic, read 'show arp'.
   verify: N2's entry is gone. N1, N3, N4, S1 and S2 are present with the same MAC, interface and type as in arpPreSingle. The entry count is exactly one lower than in arpPreSingle.
9. Try to clear a static entry by its address with 'clear arp-cache <S1-ip>'. Then read 'show arp'.
   verify: The DUT either rejects the command with an error or accepts it silently. Either way, S1 is still listed as static with its original MAC and interface. All other entries match the table from step 8.
10. Relearning after a single-address clear. Leave N2 cleared with traffic stopped. Start tcpdump on the traffic host on the test port, re-enable N2's ARP responder, and resume traffic from the DUT to N2 with 'ping <N2-ip> repeat 5'.
   verify: The capture shows an ARP request from the DUT's MAC for N2's IP and N2's reply. 'show arp' lists N2 again as dynamic with its emulated MAC. Only the first ping may fail while the address resolves. The remaining pings succeed and the capture shows those echo requests sent to N2's MAC.
11. Relearning after a clear-all. With traffic stopped and responders disabled, run 'clear arp-cache' and check with 'show arp' that N1 to N4 are gone. Start tcpdump, re-enable all responders, and ping each of N1 to N4 with 'repeat 5'.
   verify: For each of N1 to N4, the capture shows an ARP request from the DUT and the neighbour's reply. 'show arp' lists all four as dynamic with the correct MACs, and S1 and S2 are unchanged. For each neighbour, loss is limited to the first ping and the rest succeed.
12. Stop traffic and disable the responders. Read 'show arp' as the baseline. Run 'clear arp-cache <unused-ip>' for an address in the test subnet that has no ARP entry. Read 'show arp' again.
   verify: The DUT either rejects the command with an error or accepts it silently. Either way, the table after the clear is identical to the baseline: the same entries, MACs, interfaces, types and count.
13. Populate the VRF caches. With A1, A2, B1 and B2 answering ARP, ping each of them from the DUT inside its VRF, e.g. 'ping vrf VRF-A <A1-ip>'. Make sure N1 to N4 are also present in the global table, re-pinging them if needed. Stop all traffic and disable all responders. Read 'show arp' (which includes the VRF entries) and 'show arp vrf VRF-A' / 'show arp vrf VRF-B'.
   verify: VRF-A lists A1 and A2 as dynamic and SA1 as static. VRF-B lists B1 and B2 as dynamic. The global table lists N1 to N4 as dynamic and S1 and S2 as static. Record all three tables.
14. Run 'clear arp-cache vrf VRF-A'.
   verify: The command is accepted with no error.
15. Immediately after step 14, with no traffic, read 'show arp vrf VRF-A', 'show arp vrf VRF-B' and the global 'show arp'.
   verify: VRF-A has no dynamic entries: A1 and A2 are gone. SA1 is still there as static with its original MAC. VRF-B and the global table match arpBaselineVrf exactly. The total count is exactly two lower than at baseline.
16. Re-enable the A1 and A2 responders and ping both in VRF-A so the entries come back. Stop traffic and disable the responders. Run 'clear arp-cache vrf VRF-A <A1-ip>'. Then read 'show arp vrf VRF-A', 'show arp vrf VRF-B' and 'show arp'.
   verify: The command is accepted. VRF-A has lost A1 and still has A2 (dynamic, same MAC) and SA1 (static). VRF-B and the global table match arpBaselineVrf. The total count is exactly one lower than before this clear.
17. Read all ARP tables as the baseline. Run 'clear arp-cache vrf VRF-B <unused-ip>' for an address in VRF-B's subnet that has no entry. Read all ARP tables again.
   verify: The DUT either rejects the command with an error or accepts it silently. Either way, the global, VRF-A and VRF-B tables are identical to the baseline.
18. Read all ARP tables as the baseline. Run 'clear arp-cache vrf <name>' for a VRF name that is not configured on the DUT. Read all ARP tables again.
   verify: The DUT either rejects the command with an error (for example, that the VRF does not exist) or makes no change. Either way, the global, VRF-A and VRF-B tables are identical to the baseline.
19. Clean up. Remove the static ARP entries with 'no arp <S-ip>' and 'no arp vrf VRF-A <SA1-ip>'. Remove the VRF bindings, the VRFs, the extra VLANs and the IP addresses. Stop the emulated neighbours.
   verify: No check here (teardown).
