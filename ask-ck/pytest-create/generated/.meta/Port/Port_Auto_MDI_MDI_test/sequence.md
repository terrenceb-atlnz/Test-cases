# Sequence — AWPTCM-T33234

1. Enter configuration mode and apply: `speed auto`, `duplex auto`, `polarity auto`.
   verify: N/A (configuration step)
2. Check default port configuration with no pluggable present.
   verify: Run `show interface` and confirm the output contains `current polarity auto` (or default), indicating automatic MDI/MDI-X handling is enabled by default.
3. Prompt operator to insert a supported pluggable into the port.
   verify: Poll `show interface status` until the port column shows `connected`, then run `show interface` and confirm link is up with resolved polarity.
4. Connect a straight-through cable. Configure link partner to `polarity mdi`. Verify local port remains `polarity auto`.
   verify: Run `show interface` and confirm the prose output contains `current polarity mdi`, `current duplex full`, `current speed 1000`, and link status is `connected`.
5. Connect a crossover cable. Configure link partner to `polarity mdix`. Verify local port remains `polarity auto`.
   verify: Run `show interface` and confirm the prose output contains `current polarity mdix`, `current duplex full`, `current speed 1000`, and link status is `connected`.
6. Set link partner to `polarity mdi`. Connect straight-through cable. Ensure local port is `polarity auto`.
   verify: Run `show interface` and confirm `current polarity mdi`, `current duplex full`, `current speed 1000`, and link status is `connected` (compatible combination).
7. Set link partner to `polarity mdix`. Connect straight-through cable. Ensure local port is `polarity auto`.
   verify: Run `show interface` and confirm link status is `down` or `disconnected`, and `show interface status` does not show `connected` (incompatible combination).
8. Set link partner to `polarity mdix`. Connect crossover cable. Ensure local port is `polarity auto`.
   verify: Run `show interface` and confirm `current polarity mdix`, `current duplex full`, `current speed 1000`, and link status is `connected` (compatible combination).
9. Set link partner to `polarity mdi`. Connect crossover cable. Ensure local port is `polarity auto`.
   verify: Run `show interface` and confirm link status is `down` or `disconnected`, and `show interface status` does not show `connected` (incompatible combination).
10. Verify the port accurately reports the resolved polarity setting together with negotiated speed and duplex.
   verify: Run `show interface` and assert the output contains the exact negotiated values, e.g., `current polarity <mdi|mdix>`, `current duplex <full|half>`, `current speed <10|100|1000>`, matching the active link parameters.
11. Monitor link status stability across the active configuration.
   verify: Poll `show interface status` over a 60-second interval and confirm the port column consistently shows `connected` without flapping or dropping to `disconnected`.
12. Prompt operator to hot-remove the supported pluggable.
   verify: Poll `show interface status` until the port shows `disconnected` or `down`, and `show interface` confirms link is down.
13. Prompt operator to hot-insert the supported pluggable back into the port.
   verify: Poll `show interface status` until the port shows `connected`, and `show interface` confirms link is up with resolved polarity.
14. Enable LPI on the port: `ecofriendly lpi`.
   verify: Run `show ecofriendly` and assert the `Configured` column for the port reads `lpi` and the `Status` column reads `lpi`, confirming LPI is active and stable.
15. Disable LPI on the port: `no ecofriendly lpi`.
   verify: Run `show ecofriendly` and assert the `Configured` column for the port reads `off`, confirming the feature was successfully disabled. Link remains stable.
