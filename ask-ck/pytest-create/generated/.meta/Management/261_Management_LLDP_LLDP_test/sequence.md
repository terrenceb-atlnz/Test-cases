# Sequence — AWPTCM-T44297

1. Cable the DUT's test port to the partner switch's partner port, bring both ports up, and start a live LLDPDU capture on the link (tcpdump on a mirror/tap of the partner port, or 'show lldp neighbors detail' plus a decode of captured frames). Configure a management IP address on the DUT via its documented management-address configuration.
   verify: Both ports link up; the capture pipeline receives LLDP EtherType (88cc) frames from the DUT; the configured management address is present in the DUT's own management display.
2. Enable LLDP globally on the DUT ('lldp run') and enable LLDP on the partner switch so it records received neighbour information.
   verify: DUT reports LLDP running and the test port as an active LLDP tx port in 'show lldp'; the partner switch lists the DUT as a neighbour in its 'show lldp neighbors'.
3. On the test port, select each optional TLV in turn — port description, system name, system description, system capabilities, management address — one at a time ('lldp tlv-select <tlv>').
   verify: After each selection, the DUT's per-port LLDP operational/config display shows that TLV as selected (transmit-enabled) on the test port; each of the five is accepted individually.
4. With all five optional TLVs selected on the test port, clear each one individually in turn ('no lldp tlv-select <tlv>'), leaving the other selections in place each time.
   verify: After each clear, the DUT's per-port display shows only the just-cleared TLV changed to unselected while the remaining selected TLVs stay selected — clearing one does not disturb the others.
5. Select the complete set of optional TLVs on the test port, then capture several transmitted LLDPDUs on the link.
   verify: Every captured LLDPDU contains all five selected optional TLVs in addition to the mandatory chassis ID, port ID and TTL TLVs (and the end-of-LLDPDU marker).
6. With all optional TLVs selected and confirmed on the wire, clear all optional TLVs on the test port while LLDP remains enabled, then capture subsequent LLDPDUs.
   verify: Captured LLDPDUs carry only chassis ID, port ID and TTL TLVs followed by the end-of-LLDPDU marker; no optional TLV (port description, system name, system description, system capabilities, management address) appears on the wire.
7. Re-select all optional TLVs on the test port and capture several LLDPDUs, decoding each single-instance TLV type.
   verify: No single LLDPDU contains more than one port description, system name, system description or system capabilities TLV — each single-instance TLV appears at most once per LLDPDU.
8. Ensure management address transmission is selected on the test port and capture several LLDPDUs.
   verify: Every captured LLDPDU contains at least one management address TLV.
9. Associate multiple management addresses with the test port (configure more than one management/interface address the port advertises), then capture LLDPDUs.
   verify: A single captured LLDPDU is permitted to, and does, carry more than one management address TLV — one per associated address.
10. Decode the management address TLV from a captured LLDPDU and compare it against the management address configured on the DUT (as shown by the device's own management/LLDP local-info display).
   verify: The address carried in the management address TLV matches the management address the DUT reports as locally configured.
11. Change the configured management address on the DUT, then capture subsequent LLDPDUs.
   verify: LLDPDUs transmitted after the change carry the new management address in the management address TLV; the old address no longer appears.
12. With the full optional TLV set selected, decode the content of each transmitted TLV (system name, system description, port description, system capabilities, management address) and compare each against the corresponding value the DUT reports through its own management interfaces ('show lldp local-info' and the related show commands).
   verify: Each transmitted TLV's content equals the locally configured or locally derived value the DUT reports for it — no mismatch between wire content and the device's own reported values.
13. For each TLV in turn, set a known transmit-enable selection through the CLI on the test port, then read the per-port TLV transmit-enable state the DUT holds in its LLDP MIB / local-info display.
   verify: The transmit-enable state held per port and per TLV agrees with the state selected through the command interface, checked TLV by TLV; no TLV shows a MIB state disagreeing with its configured selection.
14. Select a different set of optional TLVs on a second port while the test port keeps its own selection, and capture LLDPDUs from the test port.
   verify: The set of TLVs transmitted on the test port is unchanged by the selection applied to the second port — per-port independence holds.
15. Leave one port with no optional TLVs selected while other ports transmit their selected optional TLVs, and capture LLDPDUs from the no-selection port.
   verify: The no-selection port continues to transmit only the mandatory TLVs (chassis ID, port ID, TTL) with no optional TLV, while the other ports' LLDPDUs carry their selected optional TLVs.
16. Set a port to transmit-only (disable LLDP receive, keep transmit) on that port, select optional TLVs on it, and capture its LLDPDUs.
   verify: The optional TLV selection takes effect on the transmit-only port with the same transmitted TLV set as on a transmit-and-receive port — receive capability is not a precondition for TLV transmission.
17. On the test port, select an LLDP-MED TLV set separately from the basic optional TLV set (select a MED TLV without changing the basic selection, and change a basic selection without changing the MED selection).
   verify: The per-port display shows the MED TLV set and the basic optional TLV set are independently selectable — selecting one leaves the other's state unchanged.
18. With MED TLVs selected, capture LLDPDUs from the test port and decode the organisationally specific TLVs.
   verify: The selected MED TLVs appear in transmitted LLDPDUs as the standards-defined organisationally specific (MED OUI) TLVs.
19. Configure a MED capability and a MED network-policy on the test port, then decode the MED capability and network policy TLVs from captured LLDPDUs.
   verify: The MED capability and network policy TLVs conform to the defined TLV format and carry values consistent with the DUT's MED configuration as the device reports it.
20. With LLDP running and a partial TLV set already transmitting, select one additional TLV on the test port without restarting LLDP or bouncing the port, then capture subsequent LLDPDUs.
   verify: The newly selected TLV appears in LLDPDUs transmitted after the change, the already-selected TLVs continue to appear uninterrupted, and no LLDP/port restart was needed.
21. With LLDP running and several TLVs transmitting, clear one selected TLV on the test port without restarting LLDP or the port, then capture subsequent LLDPDUs.
   verify: The cleared TLV is absent from LLDPDUs transmitted after the change while the remaining selected TLVs continue to be transmitted without interruption.
22. Note the current TLV selection on the test port, then attempt to select an unsupported TLV keyword (a real keyword the parser does not accept in this context).
   verify: The CLI rejects the attempt with a diagnostic message and does not apply any selection.
23. Attempt to select a misspelled TLV keyword on the test port.
   verify: The CLI rejects the attempt with a diagnostic message and does not apply any selection.
24. Attempt to select an out-of-range TLV keyword/parameter on the test port.
   verify: The CLI rejects the attempt with a diagnostic message and does not apply any selection.
25. After each of the three rejected keyword attempts above, read the per-port TLV selection state from the DUT's display.
   verify: The previously configured TLV selection on the test port is identical to what it was before each rejected attempt — no rejected keyword altered the stored selection.
26. Disable LLDP on a port ('no lldp run' globally or disable transmit on the port), apply several TLV selection commands on it, read the running configuration, then enable LLDP and capture LLDPDUs.
   verify: The TLV selection commands are accepted and retained in the running configuration while LLDP is disabled; once LLDP is enabled, the retained selections become effective and appear on the wire.
27. On the test port, re-issue a TLV selection command for a TLV that is already selected, and issue a clear command for a TLV that is already deselected.
   verify: Both commands are accepted without error and the resulting per-port TLV selection state is unchanged from before the commands.
28. Read the DUT's operational LLDP display commands (per-port LLDP local-info / interface configuration) for the test port with a known mix of selected and unselected TLVs.
   verify: The operational display reports the TLV selection state per port, distinguishing selected TLVs from unselected ones, matching the mix that was configured.
29. Confirm the TLV selection state appears in the DUT's displayed running configuration ('show running-config lldp'), save the configuration, reload the device over the CLI, and after it comes back read the configuration and capture LLDPDUs.
   verify: The TLV selections are present in the displayed running config, and after save+reload the same selections are restored and effective (config shows them and they appear on the wire again).
30. With a known set of optional TLVs selected on the test port and the rest unselected, read the partner switch's received LLDP neighbour information for the DUT ('show lldp neighbors detail').
   verify: The partner reports exactly the set of optional TLVs selected on the test port and reports no information for the TLVs that were not selected.
31. Record the DUT's LLDP frame and per-TLV statistics counters, then perform a series of valid TLV selection and clear changes on the test port, and re-read the counters.
   verify: Frame and TLV counters remain consistent across the selection changes, with no increment of error, malformed-frame or discarded-TLV counters attributable to a valid TLV selection.
