# Sequence — AWPTCM-T44297

1. Bring up the cabled link between the DUT test port and the neighbour port taken from the [portlink] section of the .setup file: on both devices enter interface configuration for the respective port and remove any administrative shutdown.
   verify: Each device's interface status display reports the port connected/link up at the negotiated speed; both ends agree the link is up before any LLDP configuration is applied.
2. Start an LLDPDU capture on that link — run tcpdump/Scapy on the capture interface of the test host attached to the link (or on the mirror destination port declared in the .setup), filtering Ethertype 0x88CC and writing to a pcap the script can decode.
   verify: The capture process starts and reports it is listening on the capture interface; a decoder run over the (initially empty) pcap succeeds, proving the capture path is usable for the later per-TLV assertions.
3. Enable LLDP globally on the DUT, and enable LLDP on the neighbour device over its own console so it receives and records neighbour information on the partner port.
   verify: The DUT's LLDP status display reports LLDP running/enabled with the configured transmit interval, and the capture collects LLDPDUs sourced from the DUT test port's MAC at that interval.
4. Configure a known management address on the DUT with `management address <ipv4-addr>`, using an IPv4 address configured on the DUT's management/VLAN interface.
   verify: The command is accepted without a diagnostic and `management address <ipv4-addr>` appears in the DUT's running configuration with the address just applied.
5. Re-select the complete optional TLV set on the DUT test port to restore the reference state for the content and independence checks that follow.
   verify: The per-port TLV display lists all five optional TLVs as selected and captured LLDPDUs again carry all five optional TLV types plus the mandatory TLVs.
6. Restore transmit-and-receive LLDP operation on the DUT test port.
   verify: The port's LLDP operational state reads as both transmit and receive enabled, and the DUT relearns the neighbour on that port within one of the neighbour's transmit intervals.
7. Configure an LLDP-MED network policy on the DUT test port — a voice application policy referencing a VLAN configured on the device, with a defined layer-2 priority and DSCP value — and confirm it is applied to the test port.
   verify: The device's LLDP-MED configuration display and running configuration show the network policy applied to the test port with the VLAN ID, priority and DSCP values just configured.
8. With LLDP still disabled on the DUT, enter interface configuration for the DUT test port and select two optional TLVs for transmission (port description and system name) using the per-port LLDP TLV-select configuration command; record the resulting running configuration for that port.
   verify: Neither command returns a diagnostic/error line, and the two TLV selections are present in the running configuration under the test port even though LLDP is not running; the capture shows no LLDPDU from the DUT while LLDP is disabled.
9. Without re-applying any TLV configuration, capture LLDPDUs transmitted on the test port for at least two transmit intervals and decode their TLV type list.
   verify: The two TLV selections made while LLDP was disabled are now effective: each captured LLDPDU carries a port description TLV (type 4) and a system name TLV (type 5) in addition to the mandatory TLVs — the retained configuration took effect on enabling LLDP with no re-entry of the commands.
10. With LLDP still enabled, clear every optional TLV selection on the DUT test port (issue the no-form of the per-port TLV-select command for each optional TLV), then capture at least three consecutive LLDPDUs from that port.
   verify: The DUT's per-port LLDP TLV display shows no optional TLV selected, and every captured LLDPDU contains exactly chassis ID (type 1), port ID (type 2) and time-to-live (type 3) followed immediately by the end-of-LLDPDU marker (type 0), with no TLV of any other type present on the wire.
11. From that cleared baseline, select only the port description TLV for transmission on the DUT test port and capture the next LLDPDUs.
   verify: The command is accepted; the per-port TLV display shows port description selected and the other optional TLVs unselected; captured LLDPDUs carry exactly one port description TLV (type 4) plus the mandatory TLVs and no other optional TLV.
12. Clear the port description selection, then select only the system name TLV on the DUT test port and capture the next LLDPDUs.
   verify: The per-port TLV display shows system name selected and all other optional TLVs unselected; captured LLDPDUs carry exactly one system name TLV (type 5) plus the mandatory TLVs and no port description TLV.
13. Clear the system name selection, then select only the system description TLV on the DUT test port and capture the next LLDPDUs.
   verify: The per-port TLV display shows system description selected and all others unselected; captured LLDPDUs carry exactly one system description TLV (type 6) plus the mandatory TLVs and no other optional TLV.
