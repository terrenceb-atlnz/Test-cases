# Sequence — AWPTCM-T44297

1. Enable LLDP globally on the device under test (`lldp run` at global config) and on the test port set it to transmit and receive (`lldp transmit`, `lldp receive`). Bring up the physical link from the test port to the partner switch, configure the partner port to receive LLDP so it records neighbour information, and start a packet capture (tcpdump/Scapy) on the link so transmitted LLDPDUs can be decoded.
   verify: `show lldp` reports LLDP running; `show lldp interface <port>` for the test port shows it enabled for transmit and receive; `show interface <port> status` reads connected; the capture is running and at least one LLDPDU from the test port is decodable.
2. On the test port select only the port-description optional TLV (`lldp tlv-select port-description`).
   verify: `show lldp interface <port>` lists port-description as an enabled/selected TLV, and a captured LLDPDU from the test port decodes a Port Description TLV.
3. On the test port additionally select the system-name optional TLV (`lldp tlv-select system-name`).
   verify: `show lldp interface <port>` shows system-name selected, and a captured LLDPDU decodes a System Name TLV.
4. On the test port additionally select the system-description optional TLV (`lldp tlv-select system-description`).
   verify: `show lldp interface <port>` shows system-description selected, and a captured LLDPDU decodes a System Description TLV.
5. On the test port additionally select the system-capabilities optional TLV (`lldp tlv-select system-capabilities`).
   verify: `show lldp interface <port>` shows system-capabilities selected, and a captured LLDPDU decodes a System Capabilities TLV.
6. On the test port additionally select the management-address optional TLV (`lldp tlv-select management-address`).
   verify: `show lldp interface <port>` shows management-address selected, and a captured LLDPDU decodes a Management Address TLV.
7. With the complete optional TLV set now selected on the test port, capture several consecutive LLDPDUs from the test port.
   verify: Every captured LLDPDU carries the mandatory Chassis ID, Port ID and Time To Live TLVs plus all five selected optional TLVs (port description, system name, system description, system capabilities, management address) and ends with the End Of LLDPDU marker.
8. With all optional TLVs selected, capture LLDPDUs and inspect the TLV list for the single-instance optional TLVs.
   verify: No captured LLDPDU contains more than one Port Description, System Name, System Description or System Capabilities TLV — each single-instance optional TLV appears at most once per LLDPDU.
9. With management-address transmission selected, capture a series of LLDPDUs from the test port.
   verify: Every captured LLDPDU carries at least one Management Address TLV.
10. Read the management address currently configured on the device via its own management interfaces (e.g. `show lldp local-info interface <port>`), then decode the Management Address TLV in a captured LLDPDU.
   verify: The address carried in the Management Address TLV matches the management address the device reports as locally configured.
11. Associate a second management address with the port (configure an additional management address using the device's documented management-address command), then capture LLDPDUs from the test port.
   verify: A single captured LLDPDU carries multiple Management Address TLVs, one per configured management address.
12. Change the configured management address on the device to a different valid address, wait for the next transmit interval, and capture subsequent LLDPDUs.
   verify: LLDPDUs transmitted after the change carry the new management address in the Management Address TLV; the previous address is no longer present.
13. For each currently selected optional TLV, read its locally configured or locally derived value from the device's management interfaces (`show lldp local-info interface <port>`, `show system`, `show run` as applicable) and decode the same TLV from a captured LLDPDU.
   verify: The content of each transmitted TLV (port description, system name, system description, system capabilities, management address) equals the corresponding value the device reports for itself.
14. Read the per-port TLV transmit-enable state held in the LLDP MIB / operational database for the test port (`show lldp interface <port>`) and compare it TLV by TLV against the selections made through the CLI; repeat the comparison for another port with a known distinct selection.
   verify: For every port and every TLV, the transmit-enable state reported by the LLDP management information agrees with the state configured through the command interface.
15. Run the operational display command for LLDP TLV selection on the test port (`show lldp interface <port>`).
   verify: The display reports the per-port TLV selection state, distinguishing which optional TLVs are selected from those that are unselected, and matches the current configuration.
16. Clear only the port-description TLV on the test port (`no lldp tlv-select port-description`), leaving the other optional TLVs selected, and capture LLDPDUs.
   verify: `show lldp interface <port>` shows port-description no longer selected while the other optional TLVs remain selected; captured LLDPDUs no longer carry a Port Description TLV but still carry the remaining selected TLVs.
17. Clear only the system-name TLV on the test port (`no lldp tlv-select system-name`), leaving the remaining optional TLVs selected, and capture LLDPDUs.
   verify: `show lldp interface <port>` shows system-name no longer selected; captured LLDPDUs no longer carry a System Name TLV but still carry the remaining selected TLVs.
18. Clear only the system-description TLV on the test port (`no lldp tlv-select system-description`), leaving the remaining optional TLVs selected, and capture LLDPDUs.
   verify: `show lldp interface <port>` shows system-description no longer selected; captured LLDPDUs no longer carry a System Description TLV but still carry the remaining selected TLVs.
19. Clear only the system-capabilities TLV on the test port (`no lldp tlv-select system-capabilities`), leaving the remaining optional TLVs selected, and capture LLDPDUs.
   verify: `show lldp interface <port>` shows system-capabilities no longer selected; captured LLDPDUs no longer carry a System Capabilities TLV but still carry the remaining selected TLVs.
20. Clear only the management-address TLV on the test port (`no lldp tlv-select management-address`), leaving any remaining optional TLVs selected, and capture LLDPDUs.
   verify: `show lldp interface <port>` shows management-address no longer selected; captured LLDPDUs no longer carry a Management Address TLV but still carry any remaining selected TLVs.
21. With LLDP still enabled, clear all remaining optional TLVs on the test port so none are selected, then capture several LLDPDUs.
   verify: Each captured LLDPDU carries only the Chassis ID, Port ID and Time To Live TLVs followed immediately by the End Of LLDPDU marker; no optional TLV appears on the wire.
22. With LLDP running and only mandatory TLVs on the wire, select one additional optional TLV (e.g. `lldp tlv-select system-name`) without restarting LLDP or bouncing the port, and capture the next LLDPDUs.
   verify: The newly selected TLV appears in subsequent LLDPDUs without any LLDP or port restart, and transmission of the already-present mandatory TLVs is uninterrupted.
23. With LLDP running and several optional TLVs selected, clear one of them (`no lldp tlv-select <tlv>`) without restarting LLDP or the port, and capture the next LLDPDUs.
   verify: The cleared TLV is absent from subsequent LLDPDUs while the remaining selected TLVs continue to be transmitted, with no LLDP or port restart.
24. Select a distinct set of optional TLVs on a second transmitting port (different from the test port's set), and capture LLDPDUs from the first test port.
   verify: The TLVs transmitted on the first test port are unchanged by the configuration applied to the second port; `show lldp interface` for the first port shows its selection unaltered.
25. Leave one port with no optional TLVs selected while other ports transmit their selected optional TLVs, and capture LLDPDUs from each.
   verify: The port with no optional TLVs selected transmits only the mandatory TLVs and end marker, while the other ports simultaneously transmit their selected optional TLVs — per-port independence holds.
26. Set a spare port to transmit-only (`lldp transmit`, `no lldp receive`), select an optional TLV set on it, cable it to a partner that captures its LLDPDUs, and capture from that port.
   verify: The transmit-only port's LLDPDUs carry exactly the selected optional TLVs, matching the result obtained on a transmit-and-receive port — receive capability is not a precondition for TLV transmission.
27. On the test port select an LLDP-MED TLV (e.g. `lldp med-tlv-select capabilities`) independently of the basic optional TLV set, then toggle a basic optional TLV.
   verify: `show lldp interface <port>` shows MED TLV selection independent of the basic optional TLV selection — changing one does not alter the other; the MED TLV set is separately selectable.
28. With the MED capabilities and network-policy MED TLVs selected on the test port, capture LLDPDUs and decode their organisationally specific TLVs.
   verify: The selected MED TLVs appear in transmitted LLDPDUs as the standards-defined TIA/LLDP-MED organisationally specific TLVs (correct OUI and subtype).
29. Read the device's MED configuration (MED capabilities and any configured network policy), then decode the MED Capability and Network Policy TLVs from a captured LLDPDU.
   verify: The MED Capability and Network Policy TLVs conform to the defined TLV format and carry values consistent with the device's MED configuration.
30. Note the current TLV selection on the test port, then attempt to select an unsupported but real-format TLV keyword the platform does not support (a valid LLDP TLV name outside the device's supported set).
   verify: The CLI rejects the command with a diagnostic/error message and does not apply any change.
31. Attempt to select a misspelled TLV keyword (e.g. `lldp tlv-select port-descrip`).
   verify: The CLI rejects the command with a diagnostic/error message (unrecognised keyword) and applies no change.
32. Attempt to select a TLV using an out-of-range value where the command takes a numeric/index argument (a value outside the documented range).
   verify: The CLI rejects the command with a diagnostic/error message and applies no change.
33. After each of the three rejected keyword attempts, re-read the port's TLV selection.
   verify: `show lldp interface <port>` shows the previously configured TLV selection unchanged after every rejected attempt.
34. Disable LLDP on a spare port (`no lldp transmit`/`no lldp receive` or port-level disable), apply a set of TLV selections while it is disabled, confirm they are accepted and stored, then enable LLDP transmission on that port and capture LLDPDUs.
   verify: The TLV-select commands are accepted while LLDP is disabled and shown in `show lldp interface <port>` / running config; once LLDP is enabled the retained selections take effect and the corresponding TLVs appear in captured LLDPDUs.
35. On a port with a known TLV selected, re-issue the same `lldp tlv-select <tlv>` command; on a TLV already deselected, re-issue the `no lldp tlv-select <tlv>` command.
   verify: Both commands are accepted without error and the resulting per-port TLV selection state (via `show lldp interface <port>`) is unchanged from before.
36. With a known TLV set selected on the test port, have the partner switch capture and decode the LLDPDUs and read its neighbour table (`show lldp neighbors detail` on the partner).
   verify: The neighbour reports exactly the set of optional TLVs selected on the transmitting port and reports no information for the TLVs that were not selected.
37. Record the LLDP frame and TLV counters before and after performing a sequence of valid TLV selection/deselection changes (`show lldp statistics` / `show lldp interface <port>` counters).
   verify: Transmitted/received frame and TLV counters remain consistent with the traffic, and no error, malformed-frame or discarded-TLV counter increments as a result of any valid TLV selection change.
38. Confirm the current TLV selections appear in `show running-config` (LLDP section), save with `copy running-config startup-config`, reload the device, and after it comes back capture LLDPDUs and re-read the LLDP config.
   verify: The running configuration shows the TLV selection state before save; after restart the same selections are restored in `show running-config`/`show lldp interface <port>` and are in effect on the wire (captured LLDPDUs carry the same optional TLVs).
