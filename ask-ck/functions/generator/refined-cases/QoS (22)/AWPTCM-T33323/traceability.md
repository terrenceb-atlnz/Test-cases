# Traceability & Supporting Data for AWPTCM-T33323 (QoS - Dynamic changes to policy contents)

## Primary Decision
- **AWP-20971** – DPMAP: Dynamic change of attached policy-map (QoS / Dynamic changes to policy-map)
  - Title: "DPMAP: Dynamic change of attached policy-map"
  - Summary: "Change the policy-map attached to interface without detachment. this function will be supported in 5.4.7 for BCM/IE200/Marvell Product."
  - Decision confidence: high
  - Rationale: "DPMAP dynamic change of attached policy-map"

## Top Relevant TestLink Cases

**Primary (dynamic change without detach)**
- AWP-20971 (primary) — DPMAP: Dynamic change of attached policy-map
  - Configure QoS (ACL/class-map/policy-map), apply to interface.
  - Change the class of policy-map (or contents) without detaching.
  - Verify no error, show command reflects, traffic works with updated policy.

**While traffic running**
- AWP-20974 — DPMAP: Dynamic change while traffic running
  - Change contents without detach while traffic flowing.
  - Change applied immediately, no error, QoS updates live.

**With LAG**
- AWP-21187 — DPMAP: Dynamic change to policy-map with LAG
  - Same dynamic change on static LAG and LACP interfaces.

**With VCS**
- AWP-21053 — DPMAP: Dynamic change to policy-map with VCS
  - On VCS stack, change during normal and during disruption (failover).
  - Stable, no leaks, etc.

**Exceeding limit**
- AWP-20975 — DPMAP: Dynamic change for exceeding the limit
  - When HW table full, additional changes rejected with error, existing within limit still works.

**Configuration / behavior**
- Create policy, attach, then modify class-map contents or add to policy without "no service-policy" detach.
- Supported on certain platforms (BCM/IE200/Marvell in 5.4.7+).
- Immediate effect on traffic.
- Works with LAG, VCS.

## ATPyLib Cases (Step 3)

**Related QoS policy attach / dynamic (limited direct):**
- Suite 1331: "Policy-map cannot be re-attached after getting dettached from some ports." — verifies re-attach works after detach.
- "Not able to apply storm-protection based qos policy" — attach policy with storm settings.
- "When QoS entry more than 1024 was configured to LAG ports in VCS" — large policy on LAG/VCS, no crash.
- General class-map/policy-map attach tests in 1344_qos (many classmap + policer, but focused on match/policer not dynamic content change without detach).
- No strong direct "change policy while attached without detach" in enriched data; the dynamic DPMAP feature is primarily covered in TestLink for the supported platforms.

## Gaps Noted
- Primary focuses on changing attached policy-map contents/class without detachment.
- Detailed scenarios (while running traffic, LAG, VCS, HW limit exceed) from the DPMAP TestLink family.
- ART has coverage for policy attach, re-attach after detach, large configs on LAG/VCS, but the specific "live update without detach" behavior for DPMAP may rely more on TestLink (feature targeted for 5.4.7+ on specific silicons).
- Live traffic effect and stability during VCS changes are key TestLink artefacts.

## Tangential Cases Reviewed
- Other QoS policy, class set, remarking from recent cases.
- PBR dynamic next-hop, triggers/scripts.
- These provide context for dynamic config but not the specific DPMAP attach-without-detach.

## ART Test Cases String
1331 (policy-map re-attach after detach, storm QoS policy attach, large QoS on LAG/VCS) + 1344 (QoS class-map/policy with policer on various matches) + DPMAP TestLink family (AWP-20971 primary + AWP-20974 running, AWP-21187 LAG, AWP-21053 VCS, AWP-20975 limit)

## Synthesis Notes for Objectives
- Policy-map can be modified (e.g. change class contents) while attached to interface/LAG without detaching.
- Changes take effect without error, visible in show, and immediately affect traffic.
- Supported on LAG (static/LACP), VCS (including during disruptions).
- When HW limits reached, further changes are rejected gracefully; prior config works.
- Basic setup: ACL/class-map/policy-map attached, then live update.

This continues the QoS series, focusing on dynamic policy management.
