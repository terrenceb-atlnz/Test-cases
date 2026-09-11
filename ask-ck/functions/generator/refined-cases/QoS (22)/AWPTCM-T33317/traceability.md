# Traceability & Supporting Data for AWPTCM-T33317 (QoS - PriorityRemarking - DSCP Remarking)

## Primary Decision
- **AWP-9126** – QoS:policed-dscp map (remarking) configuration changes, show command, restart (QoS / policing)
  - Title: "QoS:policed-dscp map (remarking) configuration changes, show command, restart"
  - Summary: "Verify that Policed-dscp map configurations should be in running and startup config"
  - Decision confidence: high
  - Rationale: "policed-dscp map (DSCP remarking)"
  - Note: Command not available for Broadcom platform.

## Top Relevant TestLink Cases

**Primary (policed-dscp map config)**
- AWP-9126 (primary) — policed-dscp map (remarking) config, show, restart
  - mls qos enable
  - mls qos map policed-dscp <dscp> bandwidth-class <green|yellow|red> to new-dscp X new-cos Y new-queue Z newbandwidth-class W
  - Check running-config, save, restart.
  - Expected in startup-config too.

**Revert**
- AWP-9127 — policed-dscp map reverts to default via "no" command
  - Configure map, then "no mls qos map policed-dscp ..."

**Policing using the map (single-rate, default class)**
- AWP-9129 — switchport based policing on default class - single-rate - action policed-dscp map (remarking)
  - policy-map with class default, police single-rate ... action policed-dscp-transmit
  - Apply to ingress port.
  - Send traffic, verify egress green/yellow/red packets remarked per the policed-dscp map.

- AWP-9130 — static LAG based policing - single-rate - action policed-dscp map (remarking)
  - Same but on static LAG (sa1).

**Twin-rate variants**
- AWP-17776 — switchport based policing on default class - twin-rate
- AWP-17777 — static LAG based policing on - twin-rate

**Related from previous QoS cases**
- Ties back to class set dscp, policed-dscp remarking in QoS policy.

**Configuration syntax**
- mls qos map policed-dscp 2 bandwidth-class green to new-dscp 5 new-cos 3 new-queue 4 newbandwidth-class yellow
- In policy: police single-rate <cir> <cbs> <ebs> action policed-dscp-transmit
- Note: not for Broadcom.

## ATPyLib Cases (Step 3)

**QoS policer / classmap coverage (mostly inferred in 1344):**
- 1344_qos has many "QoS - ClassMap - match on ..." with associated policer tests (inferred, no execution history for most selected runs).
  - match on vlan, cos, tos, TPID, access-group, inner-cos etc. on trunk and static channel.
  - Verifies per-class QoS policer counters.
- Some executed policer related in other sets, but specific policed-dscp map remarking not directly found in enriched descriptions.
- General QoS policy-map, class-map, mls qos in 1344 and 1331 past issues (policy attach on LAG/VCS).

**Gaps:**
- The policed-dscp map configuration itself (mls qos map policed-dscp) appears to be TestLink primary, with limited direct ART coverage in the enriched data (focus on general policers and class-maps).
- Policing action "policed-dscp-transmit" and resulting remarking covered indirectly via classmap+policer tests.

## Gaps Noted
- Primary AWP-9126 is about the map config persisting in running/startup and restart.
- Detailed remarking behavior when used in policer (green/yellow/red to new-dscp/cos/queue/bandwidth-class) from the policing TestLink cases (AWP-9129/9130 etc.).
- ART has good class-map + policer counter verification, but the specific "policed-dscp map" command and its remarking tables may have thinner direct automation (inferred cases).
- Platform note: not Broadcom.

## Tangential Cases Reviewed
- Other QoS remarking (class set dscp/cos from T33314/15), premark-dscp, trust dscp.
- These overlap in the QoS area but focus on classification vs policer-based remarking via policed-dscp map.

## ART Test Cases String
1344 (QoS class-map with policer on various match criteria, trunk + LAG) + policed-dscp map TestLink family (AWP-9126 primary + AWP-9127 revert, AWP-9129/9130 single-rate policing on switchport/LAG, twin-rate variants)

## Synthesis Notes for Objectives
- The policed-dscp map command configures remarking for bandwidth classes (green/yellow/red) to new-dscp, new-cos, new-queue, new-bandwidth-class.
- Config must appear in running-config and survive save/restart (in startup-config).
- "no" command reverts to default.
- When used with policer action policed-dscp-transmit (single-rate or twin-rate), egress traffic in each bandwidth class gets remarked per the map.
- Applies to switchport and static LAG.
- Verified with traffic, capture, counters (no drops, counts match).
- Part of QoS policing remarking.

This continues the QoS remarking theme from T33314 (class set dscp) and T33315 (CoS remark).
