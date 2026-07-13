# Traceability & Supporting Data for AWPTCM-T33242 (ICMP)

## Primary Decision
- **AWP-9996** – `The IP source address in an ICMP Echo Reply` (ICMP)
  - "ICMP echo request must be the same with ICMP echo reply."
  - Decision confidence: med
  - Rationale: ICMP echo reply (ICMP suite)

## Top Relevant + Tangential TestLink Cases
**Primary + ICMP-related cases**
- AWP-9996 (primary) — The IP source address in an ICMP Echo Reply
- AWP-10106 — ICMP Response performance (IPv6)
- AWP-986 — VCS - ICMP Reply From VCS Member
- AWP-998 — ACL: Named Hardware on port - ICMP
- AWP-1006 — ICMP Request/Reply when "no ip forwarding" configured
- AWP-1010 — DHCP server - Probe IP Address using ICMP
- AWP-1018 — Device responds to ICMP Route Redirects

## ATPyLib Cases (Step 3)
- `2002.3.2` / `2010.3.2` — The IP source address in an ICMP Echo Reply MUST be the same as the specific-destination address of the corresponding ICMP Echo Request
- `2010.1.1` / `2010.1.3` — Verify router answers ICMP Echo Requests
- `2010.3.1` — The TTL for ICMP responses must not be taken from the packet which triggered the response
- `5701.1001.5` — SNMP MIB - icmp
- `1336.*` — Hardware IP/IPv6 ACL and QoS deny/permit for ICMP traffic

## ATPyLib Coverage Mapping
- Objective 1 (Echo Reply source address): Covered by 2002.3.2 / 2010.3.2
- Objective 2 (responds to Echo Requests): Covered by 2010.1.1 / 2010.1.3
- Objective 3 (TTL not copied): Covered by 2010.3.1
- Objective 5 (ACL/QoS): Covered by 1336.*
- Objective 8–10 (Destination Unreachable, Time Exceeded, Parameter Problem): Not directly covered
- Remaining objectives: Limited or no direct ATPyLib coverage

## Gaps Noted
- Strong coverage on Echo Reply source address, basic Echo response, TTL behavior, and ACL/QoS interaction.
- No direct coverage on Destination Unreachable, Time Exceeded, Parameter Problem generation, or VCS member replies.

## Tangential Cases Reviewed
- All ICMP-related cases from the ICMP, IPv6, ACL, and DHCP suites (listed above).
- Conclusion: Primary Echo Reply focus + VCS/Redirect/probing cases provide good coverage. Basic ICMP error message generation added from first-principles for completeness.

## ART Test Cases String
2002 + 2010 (Echo Reply source address + response behavior + TTL) + 5701 (SNMP icmp MIB) + 1336 (ACL/QoS ICMP)