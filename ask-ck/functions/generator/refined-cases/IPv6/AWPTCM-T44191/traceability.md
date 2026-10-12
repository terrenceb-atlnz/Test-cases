# Traceability & Supporting Data for AWPTCM-T44191 ()

## Primary Decision

- **AWP-8309** – Trace route (obj match)
  - Decision confidence: high
  - Rationale: Trace route (obj match)


## Top Relevant TestLink Cases

**Primary + relevant historical TestLink cases reviewed for artefacts and context**

- **AWP-8309** — Trace Route
  - Justification: Step: Trace Route works
Expected: Paths will be displayed



## Zephyr Cross-References (Step 2)
**Relevant Zephyr Scale cases identified**

These cases were reviewed from the full Zephyr database (via `data/zephyr_full/`) for objective style, step structure, and related behaviour.


1. **[AWPTCM-T8611](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T8611)** — Traceroute V6
   - Folder: 
   - Objective: No
   - Justification: Has objective: None | Num steps: None

1. **[AWPTCM-T5461](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T5461)** — Traceroute Function
   - Folder: 
   - Objective: No
   - Justification: Has objective: None | Num steps: None


## ATPyLib Cases (Step 3)


- `1353.2001.61398` — ICMP Time Exceeded of TraceRoute is discarded in Firewall


- ART string: 1353.2001.61398 + 2005.5.10

## Gaps Noted
The selected ART coverage (1353.2001.61398) addresses traceroute only indirectly, through firewall handling of ICMP Time Exceeded responses, which confirms that traceroute-related control traffic is processed and filtered as policy dictates. It does not confirm the core intent of AWP-8309 and AWPTCM-T5461, which is that a traceroute runs successfully and shows a complete, correct hop-by-hop path to the destination. IPv6 traceroute, as captured in AWPTCM-T8611, has no apparent automated counterpart. Several behaviours and observability points are also not well covered by automation: accuracy of the path output, hop ordering, display of latency per probe, handling of unreachable or non-responding hops (timeouts and asterisks), maximum-hop and TTL limits, and behaviour across multi-hop topologies when the firewall is not involved.

## Tangential Cases Reviewed
(See selections for full list.)

## ART Test Cases String
1353.2001.61398 + 2005.5.10

**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.