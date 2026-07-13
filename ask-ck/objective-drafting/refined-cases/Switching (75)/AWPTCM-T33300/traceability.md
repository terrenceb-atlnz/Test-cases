# Traceability & Supporting Data for AWPTCM-T33300 (Switching_LoopGuard - MAC Address Thrashing)

## Primary Decision
- **AWP-18040** – MAC-Thrashing (Customer Scenario / Standard)
  - Title: "MAC-Thrashing"
  - Summary: "Confirm that MAC-Thrashing works correctly. It is not good that this feature doesn't work correctly because it is default enabled."
  - Steps (thin): "Confirm that MAC-Thrashing detects the occurrence of loop and the action works correctly. (eg. between stack member.)" → "Confirm that MAC-Thrashing works correctly."
  - Decision confidence: high
  - Rationale: "MAC-Thrashing"

## Top Relevant TestLink Cases

**Primary (core feature)**
- AWP-18040 (primary) — MAC-Thrashing
  - Detects loop via rapid MAC movement and takes corrective action (default enabled).

**Related loop / thrash features**
- AWP-18059 — LDF (likely Loop Detection Feature or similar)
  - Steps overlap with MAC-Thrashing description; confirms detection and action on loops (e.g. stack members).

**Interop**
- AWP-26054 — Interop: MAC Thrashing and G.8032
  - Summary notes that G.8032 R-APS can cause rapid MAC moves, so recommend high thrash-limit.
  - Steps: Configure on G.8032 interfaces, verify functions normally, test with ring breaks/restores, try different actions (learn-disable, link-down, port-disable, vlan-disable, none).
  - Config example: `thrash-limit action learn-disable timeout 60`

**Command / display**
- AWP-7460 — Command Line Handler - show interface switchport (Storm Control / CLI)
  - Tests that `show int switchport` correctly displays which VLANs on an interface are currently thrashing due to rapid MAC movement.

**Other related from batch**
- AWP-27103 — Verify MAC Thrashing with UFO (Private VLAN Upstream Forwarding Only)
- AWP-13785 — Combination test LDF + MAC thrashing + 802.1x on trunk
- AWP-7470 / AWP-7471 — Thrash-limiting info on static/dynamic channel groups (should not display when not thrashing)

**Configuration / actions observed**
- `thrash-limit action <learn-disable | link-down | port-disable | vlan-disable | none> [timeout ...]`
- Actions on detection of MAC thrashing (rapid MAC moves indicating loop):
  - learn-disable: stop learning on affected ports/VLANs
  - link-down / port-disable
  - vlan-disable
  - none (log only?)
- Default enabled.
- Logging of reason.
- Show commands report thrashing VLANs/ports.
- Important on stacks and with protocols that can cause MAC moves (G.8032, etc.).

## ATPyLib Cases (Step 3)

**Direct coverage (executed):**
- 1346.1001.95 (suite_1346_swi_misc) — "MAC thrashing - link-down"
  - Induces MAC thrashing across ports.
  - Verifies thrashing protection detects the condition, takes the link-down action, and logs the reason.
  - Platform: x230v2-tb178.rel, PASS (run 3339835).

**Related loop protection (nearby in same suite):**
- 1346.1001.94? area — Loop protection with various actions:
  - link-down
  - port-disable
  - vlan-disable
- These verify loop detection leads to configured protective action + logging/state reporting.

**Inferred (no execution in selected runs):**
- Similar cases in other testsets for loop protection actions.

**Context:**
- MAC thrashing protection is part of broader loop/storm protection features in switching misc tests.
- Focus on detection via rapid MAC address movement and action application.

## Gaps Noted
- Primary AWP-18040 is high-level ("detects loop and action works correctly").
- Detailed actions, configuration, interop (G.8032, LAGs, UFO, LDF combo), and CLI output expectations come from the supporting TestLink family.
- ART has good direct coverage for MAC thrashing link-down action + logging, plus related loop protection actions.
- Some interop scenarios (G.8032 causing false positives, stack member thrashing) are primarily TestLink.
- Older notes indicate it is default enabled and important for loop prevention.

## Tangential Cases Reviewed
- Storm control / rate limiting cases (related but distinct from thrashing protection).
- General L2 learning, VLAN, G.8032 functional tests.
- These provide context for when rapid MAC moves can occur but do not focus on the thrashing protection feature itself.

## ART Test Cases String
1346 (MAC thrashing - link-down + loop protection actions) + MAC Thrashing / Loop Detection TestLink family (AWP-18040 primary + AWP-18059, AWP-26054, AWP-7460, AWP-7470/7471, AWP-13785 etc.)

## Synthesis Notes for Objectives (initial)
Objectives should cover:
- Detection of MAC thrashing (rapid MAC movement / loops), default enabled.
- Configurable actions on detection: learn-disable, link-down, port-disable, vlan-disable, none (with timeout where applicable).
- Correct logging and reporting (show commands indicate which ports/VLANs are thrashing).
- Interop: works on G.8032 (with appropriate limits), LAGs, stacks, in combination with other features (LDF, UFO, 802.1x).
- Actions take effect (e.g. port goes down or learning disabled) and can recover after timeout or condition clears.
- CLI for configuration and display.

This follows the pattern: expand thin primary using the feature family + ART for the core detection/action mechanism.
