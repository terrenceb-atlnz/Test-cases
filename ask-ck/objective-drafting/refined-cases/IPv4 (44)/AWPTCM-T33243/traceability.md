# Traceability & Supporting Data for AWPTCM-T33243 (IPv4_ARP - Gratuitous ARP)

## Primary Decision
- **AWP-4359** – Gratuitous ARP: On Link Up (ARP / Standalone)
  - "Gratuitous ARP on link up (ARP suite)"
  - Decision confidence: high
  - Rationale: Gratuitous ARP transmitted 5 seconds after link up

## Top Relevant TestLink Cases
**Primary + Standalone Gratuitous ARP family**
- AWP-4359 (primary) — Gratuitous ARP: On Link Up
- AWP-4360 — Gratuitous ARP: On IP Interface
- AWP-4362 — IP Gratuitous ARP: Link Delay Time
- AWP-4363 — Gratuitous ARP: On Tagged Ports
- AWP-4364 — Gratuitous ARP: After Start-up
- AWP-4365–4368 — Gratuitous ARP on static/dynamic channels (tagged/untagged)
- AWP-4392 — Gratuitous ARP & ARP: Hotswap

## ATPyLib Cases (Step 3)
- 1351.1001.1–6, 1351.1002.1–2 — Default and configurable gratuitous-ARP-on-link behaviour, timer values (including 0), multiple port flips, table correctness, static ARP interaction, static channel-group handling

## Gaps Noted
- None significant for the core feature.

## Tangential Cases Reviewed
- Receive Gratuitous-ARP family (AWP-13993+), VCS/EPSR failover variants, VRRP interop.
- Conclusion: Primary Standalone cases + 1351 suite provide complete coverage.

## ART Test Cases String
1351 (Gratuitous ARP on link up, timer, disable, LAG, table behaviour)