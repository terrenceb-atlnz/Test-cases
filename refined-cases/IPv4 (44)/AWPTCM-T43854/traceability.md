# Traceability & Supporting Data for AWPTCM-T43854 (IPv4_DHCPClient - DNS Relay)

## Primary Decision
- From `data/decisions/dec_05.json`: AWPTCM-T43854 {"m": "AWP-3360", "c": "high", "w": "Exact: DNS Relay enable/disable"}
- Zephyr title: "(29) IPv4_DHCPClient - DNS Relay"
- Folder: /New Platform Test (MASTER)/New Platform Template/IPv4
- Current Zephyr state: objective "DNS Relay - enable/disable ...", with steps for configure, enable/disable, confirm forwarding.

## Top Relevant TestLink Cases
Primary + closely related DNS Relay cases from DNS / DNS Relay suite.

1. **AWP-3360** (Primary) — DNS Relay - enable/disable
   - Suite: DNS / DNS Relay
   - Summary: DNS Relay - enable/disable Requirements: Supports forwarding DNS query packet to server Switches to enable and disable DNS relay feature. Configures system global DNS relay and name resolver settings. ip dns forwarding
   - Steps: configure name-servers, enable dns relay, confirm forwarding, disable, confirm stops, cycle.
   - Justification: Direct high-confidence exact match. Core for enable/disable of DNS relay.

2. **AWP-3359** — DNS Relay - name resolver support
   - Suite: DNS / DNS Relay
   - Summary: DNS Relay - name resolver support Features that use local name resolver are supported by dns relay. Name resolver functions when no dns relay.
   - Justification: Related name resolver behavior.

3. **AWP-3194** — DNS Relay show commands
   - Suite: DNS / DNS Relay
   - Summary: DNS Relay show commands | Output is accurate & useful show ip dns forwarding ...
   - Justification: Observability via show commands.

4. **AWP-3197** — DNS Relay Debug
   - Suite: DNS / DNS Relay
   - Summary: DNS Relay Debug
   - Justification: Debug support.

5. **AWP-3365** — DNS Relay - source interface configuration
   - Suite: DNS / DNS Relay
   - Summary: Configures source interface sending DNS query packet. Works if dns relay switch has two routes to the dns server.
   - Justification: Source interface config.

**Tangential Cases Reviewed (summary):** 
- AWP-11510 IPv6 server, AWP-11530 IPv6 info in show, AWP-14303 VRF aware.
- Decision: Focused on core enable/disable and related config/show/debug.

## ATPyLib Cases (Step 3)
- 1346: 1346.1001.87 / 1346.1010.9 DNS forwarding configuration and CLI output (parameters like retry/timeout, CLI verification).
- Other DNS in 13xx/20xx for forwarding, name resolver.
- Limited direct "dns relay enable/disable"; more on config and behavior.

## Gaps Noted
- Specific enable/disable of DNS relay and forwarding from TL primary.
- ART covers DNS forwarding config/CLI but relay switch behavior from TL.
- Zephyr has objective.

## ART Test Cases String
1346.1001.87 (DNS forwarding config/CLI) + related DNS suites (13xx/20xx).

## Synthesis Notes for Objectives
Zephyr objective: DNS Relay - enable/disable. Enrich with TL: enable forwarding (ip dns forwarding), disable stops, cycle enable/disable, name resolvers supported when relay on, show commands accurate.

---
**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.

Following repeatable workflow in OBJECTIVE_DRAFTING_PROCESS.md.
