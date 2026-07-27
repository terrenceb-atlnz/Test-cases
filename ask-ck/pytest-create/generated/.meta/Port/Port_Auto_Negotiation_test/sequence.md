# Sequence — AWPTCM-T33233

1. Check default port configuration for speed and duplex.
   verify: Run `show interface <port> status`. Confirm default speed and duplex are reported with `a-` prefix (e.g., `a-full`, `a-1000`) indicating automatic negotiation mode.
2. Physically insert a supported pluggable into the port.
   verify: Wait for link state change. Run `show interface <port> status`. Confirm column shows `connected` and autonegotiation completes (speed/duplex values appear in status columns).
3. Configure local port speed and duplex to `auto`. Configure link partner port speed and duplex to `auto`.
   verify: Wait for link up. Run `show interface <port> status`. Confirm status shows `connected` and reports negotiated speed/duplex values. Run `show interface <port>` to confirm config shows `auto`.
4. Configure local port to `speed auto duplex auto`. Configure link partner to `speed 1000 duplex full`.
   verify: Wait for link up. Run `show interface <port> status`. Confirm status shows `connected` with negotiated speed `1000` and duplex `full`.
5. Configure local port to `speed auto duplex auto`. Configure link partner to `speed 100 duplex half`.
   verify: Wait for link up. Run `show interface <port> status`. Confirm status shows `connected` with negotiated speed `100` and duplex `half`.
6. Configure local port to `speed 1000 duplex full`. Configure link partner to `speed 100 duplex half`.
   verify: Wait for link state. Run `show interface <port> status`. Confirm status shows `down` or `disconnected`. Link does not establish.
7. Physically hot-insert a supported pluggable while port is configured for `auto` speed/duplex.
   verify: Wait for link state to transition. Run `show interface <port> status`. Confirm status shows `connected` and negotiated speed/duplex values appear.
8. Physically hot-remove the pluggable.
   verify: Wait for link state to transition. Run `show interface <port> status`. Confirm status shows `down` or `disconnected`.
9. Enable `ecofriendly lpi` on the local port.
   verify: Run `show ecofriendly`. Confirm the port's `Configured` column shows `lpi` and `Status` column shows `lpi` (or `off` if not yet active). Verify `show interface <port> status` still shows `connected` and link remains stable.
10. Disable `ecofriendly lpi` using `no ecofriendly lpi`.
   verify: Run `show ecofriendly`. Confirm the port's `Configured` and `Status` columns show `off`. Verify `show interface <port> status` still shows `connected` and link remains stable.
