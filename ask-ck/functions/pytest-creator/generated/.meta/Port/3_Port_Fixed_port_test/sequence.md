# Sequence — AWPTCM-T33235

1. configure interface port1.0.1 speed 1000 duplex full
   verify: Run 'show interface port1.0.1' and assert output contains 'configured speed 1000', 'configured duplex full', 'current speed 1000', 'current duplex full', and 'Link is UP'. Send Scapy traffic and verify forwarding.
2. configure interface port1.0.1 speed 100 duplex full
   verify: Run 'show interface port1.0.1' and assert output contains 'configured speed 100', 'configured duplex full', 'current speed 100', 'current duplex full', and 'Link is UP'. Send Scapy traffic and verify forwarding.
3. configure interface port1.0.1 speed 100 duplex half
   verify: Run 'show interface port1.0.1' and assert output contains 'configured speed 100', 'configured duplex half', 'current speed 100', 'current duplex half', and 'Link is UP'. Send Scapy traffic and verify forwarding.
4. configure interface port1.0.1 speed 1000 duplex half
   verify: Run 'show interface port1.0.1' and assert output contains 'configured speed 1000', 'configured duplex half', 'current speed 1000', 'current duplex half', and 'Link is UP'. Send Scapy traffic and verify forwarding.
5. configure interface port1.0.1 speed 2500
   verify: Run 'show interface port1.0.1' and assert output contains 'configured speed 2500', 'current speed 2500', and 'Link is DOWN'. Verify that the port does not establish a link and status reflects the unsupported configuration.
6. configure interface port1.0.1 speed 1000 duplex full
   verify: Prompt operator to physically remove and re-insert the cable/pluggable. Wait for link state transition. Run 'show interface port1.0.1' and assert 'configured speed 1000', 'configured duplex full', 'current speed 1000', 'current duplex full', and 'Link is UP' are retained.
7. Run 'show interface port1.0.1' and 'show interface status port1.0.1'.
   verify: Assert 'show interface' output contains exact prose: 'current duplex full, current speed 1000, current polarity mdix', 'configured duplex full, configured speed 1000, configured polarity auto', and 'Link is UP'. Assert 'show interface status' columns show 'full' or 'a-full', '1000' or 'a-1000', and 'connected'.
