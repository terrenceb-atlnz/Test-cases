# Traceability & Supporting Data for AWPTCM-T33315 (QoS_PriorityRemarking - CoS Remarking)

## Primary Decision
- **AWP-20430** – QoS: Remarking of CoS value in the packet using "remark new-cos" command (QoS / policing)
  - Title: "QoS: Remarking of CoS value in the packet using \"remark new-cos\" command."
  - Summary: "This test is to verify that the original CoS value of the packet can be over written and replaced with new CoS value specified by \"remark new-cos\" command."
  - Decision confidence: high
  - Rationale: "Remarking of CoS value"
  - Key config: policy-map with class using "remark new-cos X both", applied via service-policy input.

## Top Relevant TestLink Cases

**Primary (remark new-cos)**
- AWP-20430 (primary) — QoS: Remarking of CoS value using "remark new-cos"
  - Uses policy-map + class-map (e.g. match vlan)
  - "remark new-cos 5 both"
  - Verify egress packets have the new CoS value (e.g. from 3 to 5)
  - Show policy-map to confirm attached.

**Conflict / CPU queue safety**
- AWP-21845 — CoS remarking do not cause conflict with traffic passing through CPU queue
  - Specific to certain platforms.
  - Verify that re-marked CoS does not affect CPU queue assignment (e.g. unknown dest to Q0).
  - Also supports "remark new-cos X internal new-cpu-queue Y"

**Related CoS / default / maps**
- AWP-9067 — QoS cos-queue map default
  - Verify default COS-TO-QUEUE-MAP (e.g. COS 0->Q2 etc.)
- AWP-9073 — QoS:switchport interface default cos
  - mls qos cos on ingress untagged, verify tagged on egress.
- AWP-9075 — QoS:static LAG interface default cos
  - Similar for LAG.
- AWP-9077 — QoS default CoS with Dynamic LAG

**Class set cos (sibling to previous DSCP case)**
- AWP-9108 — QoS on switchport interface - class set cos
  - Similar to DSCP but for CoS via class in policy-map.

**Other**
- AWP-9068 — QoS cos-queue map configuration (after reboot/failover)
- AWP-9067 etc. for maps.

**Configuration syntax observed**
- In policy-map class:
  ```
  remark new-cos 5 both
  remark new-cos 4 internal new-cpu-queue 3
  ```
- mls qos cos <value> on interface for default.
- cos-queue maps for internal mapping.

## ATPyLib Cases (Step 3)

**Related QoS remark / premark coverage (suite 1344_qos):**
- 1344.4101.30 — "QoS - DSCP premark - modify COS with switchport in trunk mode" (executed, PASS)
  - Builds class-map + policy-map, applies to trunk switchport.
  - Policy that rewrites CoS (802.1p) value of matched egress frames.
  - Verifies packets carry expected remarked CoS.
  - Platform: FS980-tb6.rel
- 1344.1002.7 — "QoS - DSCP premark to new cos - port = trunk mode" (inferred)
  - Similar rewrite of CoS on trunk.

**Broader QoS policy in 1344 and others:**
- Multiple DSCP premark cases that also touch CoS remarking.
- Policy-map application, class-maps for marking.

**Notes:**
- Direct support for CoS remarking via policy-maps in the QoS suite.
- Focus on egress marking verification, trunk mode, etc.
- Related to the DSCP class-set work from T33314.

## Gaps Noted
- Primary focuses on "remark new-cos" overwriting original CoS.
- Detailed verification (wireshark capture on egress, policy show, no CPU queue conflict) from TestLink.
- ART provides executed coverage for CoS modification via premark/policy on trunk ports.
- Default cos, cos-queue maps, LAG support from TestLink family.
- Some cases note platform specifics.

## Tangential Cases Reviewed
- Other remarking like policed-dscp, ToS.
- General QoS cos-queue, default cos on LAG/switchport.
- These provide context for CoS handling but the "remark new-cos" in policy is the core.

## ART Test Cases String
1344 (QoS DSCP premark / modify COS on trunk/switchport, executed cases for CoS rewrite) + CoS Remarking TestLink family (AWP-20430 primary + AWP-21845, AWP-9067, AWP-9073, AWP-9108, AWP-9068 etc.)

## Synthesis Notes for Objectives
Core:
- Use of "remark new-cos" in policy-map class to overwrite packet CoS on egress.
- Applies to ingress port, affects egress marking (verified by capture).
- Should not interfere with CPU queue assignment (internal CoS vs external?).
- Related to class set cos (from sibling cases), default cos, cos-queue maps.
- Works on switchport, LAG, with VCS.
- Policy must be attachable and show correctly.

Since previous DSCP was "class set", this is the remark variant for CoS.
