# Traceability & Supporting Data for AWPTCM-T33275 (Switching_EPSR - Enhanced Recovery)

## Primary Decision
- **AWP-145** – EPSR enhanced recovery mode (Customer Scenario / EPSR)
  - Title: "EPSR enhanced recovery mode"
  - Summary: "Confirm Enhanced Recovery mode works correctly."
  - Preconditions: "Note: More detail criteria might be need."
  - Steps (thin): 
    - "Confirm ESPR status." → "Enhanced Recovery mode works correctly."
  - Decision confidence: high
  - Rationale: "EPSR enhanced recovery mode"

## Top Relevant TestLink Cases

**Primary (very thin)**
- AWP-145 — EPSR enhanced recovery mode (Customer Scenario / EPSR)

**Core negative / control cases (disabled behavior)**
- AWP-4083 — Enhanced Recovery - disabled on EPSR Master node (Test 6.1.8)
  - Suite: EPSR+ and EPSR++ Tests
  - Summary: "Enhanced recovery when it is not enabled on the master"
  - Expected: "Refer Support document reference 6.1.8(EPSR+_++ test descriptions v0.02)"
- AWP-4084 — Enhanced Recovery - disabled on EPSR Transit node (Test 6.1.9)
  - Suite: EPSR+ and EPSR++ Tests
  - Summary: "Enhanced recovery when it is not enabled on the transit node"
  - Expected: "Traffic should recover only on the domain with Enhanced recovery enabled. Refer Support document reference 6.1.9(EPSR+_++ test descriptions v0.02)"

**Basic recovery scenarios (no stack)**
- AWP-4076 — Enhanced Recovery - Single link failure (Test Case 6.1.1)
  - Suite: Race-Condition cases
  - Summary: "EPSR ring with enhancedrecovery mode on. Single link failures and recovers are all successful"
  - Preconditions: "Please use AWP-4133.jpg for the network diagram"
  - Expected: "There should be no loop at any time. Refer Support document reference 6.1.1(EPSR+_++ test descriptions v0.02)"
- AWP-4077 — Enhanced Recovery - Two link failures (Test Case 6.1.2)
  - Suite: Race-Condition cases
  - Summary: "EPSR Ring with enhancedrecovery mode on. When there are two link failures in the ring. Restore one link, test that newly recovered segments of nodes will be available for the packet flow. Restore both link, the ring will change to complete state."
  - Preconditions: "Please use AWP-4133.jpg for the network diagram"
  - Expected: "The node can recover after up to 4 seconds. Refer Support document reference 6.1.2..."
- AWP-4078 — Enhanced Recovery - Multiple link failures (Test Case 6.1.3)
  - Suite: Race-Condition cases
  - Summary: Similar multi-failure restore segments + full ring complete. No loops.
  - Expected: "There should be no loop at any time."

**Reconnect and partial recovery**
- AWP-4086 — Enhanced Recovery - Link Failure - reconnect per link (Test 6.1.11)
  - Suite: Further EPSR+ and EPSR++ Tests - Scenario 1 – ring with no stack
  - Summary: "Testing Link failure per link - disconnect and reconnect per link."
  - Preconditions: "Please use AWP-4086.jpg for network diagram"
  - Steps include: "EPSR 2 Domain setup. One link down. Removing all links and reconnecting."
  - Expected: "Disconnection and partial reconnection of inter nodes links should start traffic flowing again"

**Multi-domain independence**
- Multi-domain cases (e.g. around AWP-4091 area): Enhanced Recovery works independently per domain. Traffic recovers only on domains where the mode is enabled.
- AWP-13200 — Enable Enhanced Recovery, single link failure (duplicate of basic scenario).

**Reviewed but out of current scope**
- VCS / Stack scenarios (AWP-4095, AWP-4096, AWP-4094): Slave failover, master failover, and reconnect with stacked master. These were examined but excluded from objectives per direction.
- Hot-swap (AWP-4085): Hot-swap of modules terminating EPSR ports. Reviewed but excluded from objectives.

**Configuration syntax observed across cases**
- `epsr <ep-name> enhancedrecovery enable`
- Example:
  ```
  epsr configuration
  epsr ep1 mode master controlvlan 4000 primaryport port1.0.3
  epsr ep1 datavlan 409,1000
  epsr ep1 enhancedrecovery enable
  epsr ep1 state enabled
  ```

Many TestLink cases defer detailed pass/fail criteria and diagrams to "EPSR+_++ test descriptions v0.02" support documents.

## ATPyLib Cases (Step 3)

**Primary direct coverage — Enhanced Recovery protocol (executed, 1334_epsr):**
All on recent runs (2026-06-20), PASS.

- **1334.3001.6** (transit, priorities set)
  - "EPSR - Enhanced Recovery Enabled - transit node (priorities set) when a port comes up with enhanced recovery enabled, a Link Forward Request is transmitted"
  - Verifies: Link Forward Request transmitted on relevant control VLANs (withheld where not expected). Platform: FS980-tb6.rel

- **1334.3001.7** (transit, priorities)
  - "EPSR - Enhanced Recovery - transit node with EPSR instances (priorities set). When port goes down and comes up again, if a Permission Link Forward is sent in response to a Link Forward Request, the port goes forwarding."
  - Platform: FS980-tb6.rel

- **1334.3001.8** (transit, no priority)
  - Similar Link Forward Request transmission when no priority configured.

- **1334.3001.9** (transit, no priority)
  - Permission Link Forward response causes port to forwarding state.

- **1334.3001.10** (Master node, priorities set)
  - "EPSR - Enhanced Recovery Enabled - Master node (priorities set) when a Link Forwarding Request is received ... a Permission Link Forwarding is transmitted"
  - Platform: GS970EMX-tb328.rel (different run)

**Timing / regression intent (inferred only — no execution history, 1340_past_issues_2):**
- 1340.3001.414211 — CR41421: Measure traffic interruption during EPSR failover, enhancedrecovery **disabled**.
- 1340.3001.414212 — CR41421: Measure traffic interruption during EPSR failover, enhancedrecovery **enabled** (expects reduced limit).

**Baseline EPSR (1334) useful for context:**
- Standard ring up/down, Ring-Failed / Ring-Down FDB-flush, Ring-Up, state Complete/Failed transitions, hello/traps.

## Gaps Noted
- Primary AWP-145 is extremely minimal ("Confirm status").
- Most TestLink cases are high-level and point to external docs for exact procedures/expectations.
- Excellent executed ART coverage of the *mechanism* (Link Forward Request + Permission Link Forward handshake) on master and transit, with/without priorities.
- No executed coverage for the exact traffic interruption timing numbers in 1340.
- Multi-domain independence is primarily from TestLink.
- "Enhanced" semantics (why it's faster/better) are implicit in the protocol messages and the "recover only on enabled domains" rule.
- VCS failover and hot-swap scenarios were reviewed in the candidate data but deliberately excluded from scope for this case.

## Tangential Cases Reviewed
Broader EPSR TestLink (~375 cases) cover:
- Standard (non-enhanced) failover/recovery
- Interop with LAG, STP, IPv6, ATMF, CFM, port-security, etc.
- SLP (Super Loop Prevention) interop with enhanced recovery
- Basic EPSR command and ring setup

Conclusion: These provide good context but the dedicated 6.1.x Enhanced Recovery family + the specific 1334.3001.6–10 cases are the direct sources. No need to pull in general EPSR cases for this manual test's objective.

## ART Test Cases String
1334.3001.6–10 (Enhanced Recovery Link Forward Request / Permission Link Forward on master + transit, priorities and no-priority) + 1340 (CR41421 timing) + Enhanced Recovery TestLink family (AWP-145 primary + AWP-4076/4077/4078/4083/4084/4086 + multi-domain independence cases)

## Synthesis Notes for Objectives
The feature being tested:
1. The `enhancedrecovery` option is configurable per EPSR domain.
2. When enabled, the ring uses a specific Link Forward Request / Permission Link Forward exchange to allow ports to go forwarding on recovery.
3. Recovery produces correct state transitions with no loops.
4. Behavior is per-domain (disabling on master or a transit affects only that domain's recovery).
5. Partial link recovery allows traffic flow in recovered segments.

VCS stack failover and hot-swap scenarios were reviewed in the candidate data (AWP-4094/4095/4096 and AWP-4085) but intentionally excluded from the objectives and test steps for this case.

This matches the pattern from T33274 (EPSR MIB) — thin primary expanded via the feature family.
