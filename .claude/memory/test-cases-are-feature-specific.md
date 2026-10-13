---
name: test-cases-are-feature-specific
description: Zephyr test cases (and cycles) are FEATURE-specific — no platform-specific checks, models, port types, chip notes or platform lists; platform detail belongs in the test plan / strategy only
metadata:
  type: feedback
  verified: 2026-10-14
---

**Test cases are feature-specific. Omit any mention of platform-specific checks at the
test-case level.** Terrence, 2026-10-14, authoring the Project 3301 FRER cases: *"please omit any
mention of platform-specific checks. these are supposed to be feature-specific at the test-case
level."* Then, of the cycle: *"clean up the test cycle, it shouldnt be platform specific. The test
plan is fine."*

**Why:** a case describes what the FEATURE must do; which platforms run it is an execution
decision (which cycle, which bench, which ART platforms), not part of the case. A case naming
IE560 or "SFP+ at 10G" stops being reusable on the next platform the feature lands on.

**How to apply** (case name, objective, precondition, steps AND the step-0 traceability line):
- No platform/model names (IE570, 28GSX…), no platform lists ("on IE220, IE340…"), no
  silicon/chip notes (BCM, flow-ID offsets) even as rationale in traceability.
- No specific port types or speeds ("100M SFP, SFP+ 10G, PoE") — say "every port type and
  speed the DUT offers", "paths at different speeds", "the maximum frame size".
- A case that only existed to repeat checks on other platforms is dissolved: keep its
  feature-level check in the feature case, drop the platform run.
- Features are not platforms: VCStack, channel groups, licences stay (they are FRER-refusal /
  feature checks).
- Test CYCLE name/description: no platform either. The **test plan** and the **test strategy**
  may carry platforms, models, resources (Terrence: "The test plan is fine") — scoped, see
  [[scoped-directives-stay-scoped]].

Related: [[scripts-must-be-hardware-agnostic]] (same principle one layer down, for generated
scripts), [[objective-grounding-scope-and-agnosticism]] (product-specific grounding breaks
agnosticism), [[pipeline-layer-contract]] (objectives are platform-agnostic end states).
