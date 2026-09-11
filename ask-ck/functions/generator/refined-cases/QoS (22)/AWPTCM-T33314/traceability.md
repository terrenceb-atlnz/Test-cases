# Traceability & Supporting Data for AWPTCM-T33314 (QoS - DSCP)

## Primary Decision
- **AWP-9109** – QoS on switchport interface - class set dscp (QoS / policy-maps)
  - Title: "QoS on switchport interface - class set dscp"
  - Summary: "Verify that classified traffic class set DSCP as defined."
  - Decision confidence: high
  - Rationale: "Exact: class set dscp (obj identical)"
  - Zephyr note: "Verify that classified traffic class set DSCP as defined."

## Top Relevant TestLink Cases

**Primary (class set dscp on switchport)**
- AWP-9109 (primary, very strong 0.942 match) — QoS on switchport interface - class set dscp
  - Create policy with class, set dscp via service-policy.
  - Transmit matching/non-matching traffic.
  - Monitor egress for DSCP value.
  - Verify on VCS master/backup, after failover, after reboot.

**LAG variant**
- AWP-9113 — QoS on static LAG interface - default class set dscp
  - Similar: set dscp via service-policy on static LAG.
  - Verify classified traffic DSCP set as defined.
  - VCS master/backup, failover, reboot.

**Related DSCP / class-map**
- AWP-9088 — QoS: DSCP Specify IP DSCP
  - Verify matching and non-matching traffic specific to DSCP conform to class-map and default maps.
  - Use class-map match dscp, service-policy.
  - Policer counters, VCS, failover, boot config.
  - Expected: Matching traffic per class; non-matching to default.

**Other close from batch**
- AWP-9108 (class set cos)
- AWP-9110 (class set queue)
- AWP-9107 (class set bandwidth class)
- These are siblings in the QoS policy-map "class set" family.

**Configuration pattern observed**
- class-map match dscp ...
- policy-map
- class <name>
- set dscp <value>
- service-policy input <policy> on interface (switchport or static LAG)
- Verify egress DSCP marking on classified traffic.

## ATPyLib Cases (Step 3)

**Related QoS policy / DSCP coverage:**
- Suite 1344 (1344_qos): Multiple "QoS - DSCP premark" cases (inferred/no execution in selected runs):
  - QoS - DSCP premark
  - QoS - DSCP premark on aggregation (static channel)
  - Variants for new bandwidth class (red/yellow) with/without static channel.
  - Builds class-map + policy-map, applies to switchport/LAG, rewrites DSCP or sets bandwidth class (colour), verifies forwarded packets and counters.
- Suite 1331 (past_issues): Cases around policy-map attach/detach, large QoS configs on LAG in VCS, no crashes on apply.
- General QoS policy application in other suites.

**Notes:**
- Strong pattern coverage for applying policy-maps with class-maps that set DSCP/markings on switchports and LAGs.
- VCS failover and config persistence testing is common in the family.
- Direct "class set dscp" execution may be covered under the premark / set tests in 1344.

## Gaps Noted
- Primary is very close to the Zephyr objective itself.
- Detailed expectations (VCS master/backup, failover, reboot, matching vs non-matching) come from the TestLink family.
- ART provides good inferred + related coverage for DSCP remarking/premark via policy, including on LAGs and bandwidth class interaction.
- Exact "set dscp" verification on egress is well represented.

## Tangential Cases Reviewed
- Other QoS class set (cos, queue, bandwidth).
- General mls qos, cos-queue maps, default cos.
- These are adjacent but the DSCP-specific class set is the focus.

## ART Test Cases String
1344 (DSCP premark, on switchport and static channel/LAG, with bandwidth class variants) + QoS policy-map / class set DSCP TestLink family (AWP-9109 primary + AWP-9113, AWP-9088 + siblings)

## Synthesis Notes for Objectives
Since Zephyr already has a concise objective, enrich it with the full scope from the family:
- Classified traffic (via class-map + policy-map) has DSCP set as configured on egress.
- Applies to switchport and static LAG interfaces.
- Works for matching and non-matching traffic (default class).
- Verified across VCS master/backup, failovers, and reboot.
- Consistent with policer counters and show commands.
- Part of broader QoS class actions (set dscp, cos, queue, etc.).

This is a high-confidence, near-identical match case — objectives should stay close to the provided Zephyr text but expanded for completeness and traceability.
