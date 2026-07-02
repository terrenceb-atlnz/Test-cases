# Traceability & Supporting Data for AWPTCM-T33250 (IPv4_ARP - MC/Disparate ARPs (NLB))

## Primary Decision
- None (null primary in decisions)
- Decision confidence: low
- Rationale: "Disparate/MC ARP; no clear match" from initial candidate ranking

## Top Relevant TestLink Cases
**NLB / arp-mac-disparity family (ER-410 + Broadcom MS-NLB)**
- AWP-20263 — Microsoft NLB Support - static arp resolving to MC L2
- AWP-21286 — Arp-MAC-Disparity Default Operation
- AWP-21287 — Arp-Mac-Disparity-Multicast - Functional
- AWP-21288 — Arp-Mac-Disparity-Unicast - Functional
- AWP-21298 — Arp-MAC-Disparity - Configuration
- AWP-21239 — NLB Multicast mode : Add Static ARP with Unicast IP/Multicast Mac
- AWP-21248 — NLB IGMP mode : Add Static ARP with Unicast IP/Multicast Mac
- AWP-21299 — Arp-Mac-Disparity operates within a VRF instance
- AWP-21302 — Arp-Mac-Disparity - High Availability VCS Failover - Stress

## ATPyLib Cases (Step 3)
- 1355 (NLB suite): 1355.1001.x cases verifying arp-mac-disparity enabled VLANs, unicast and multicast virtual MAC ARP entries, port-specific vs flooding behavior, and static ARP combinations.
- 1351.1001.12 — NLB behaviour (disparate-ARP handling)
- 1351.1001.13 — NLB behaviour with Static ARP

## Gaps Noted
- Initial candidate ranking had no strong primary match for the manual case title.
- Core feature behaviour (accepting virtual MC/unicast MACs for unicast IPs in NLB clusters, mode-specific handling, port binding) is well covered in the historical TestLink family and targeted 1355/1351 suites.
- Some edge interop scenarios (specific LAG/VCS combinations) are distributed across multiple cases.

## Tangential Cases Reviewed
- None added (focused on the NLB arp-mac-disparity feature family per review).

## ART Test Cases String
1355 (NLB) + 1351.1001.12 and 1351.1001.13 (disparate-ARP handling) + primary TestLink NLB/arp-mac-disparity family cases
