# Traceability & Supporting Data for AWPTCM-T33279 (Switching_STP - BPDU Forwarding)

## Primary Decision
- **AWP-9400** – BPDU Forwarding behavior with spanning tree protocols (xSTP / STP)
  - Title: "BPDU Forwarding behavior with spanning tree protocols"
  - Summary: "BPDU Forwarding (x600 only)"
  - Steps: "BPDU Forwarding cannot enabled with spanning tree protocols (stp, rstp, mstp)" → "BPDU Forwarding is automatically disabled (and removed from the running config) when any spanning tree protocol is enabled."
  - Decision confidence: high
  - Rationale: "BPDU Forwarding behavior"

## Top Relevant TestLink Cases

**Primary (mutual exclusion with STP)**
- AWP-9400 (primary) — BPDU Forwarding behavior with spanning tree protocols
- AWP-24882 — BPDU Forwarding behavior with spanning tree protocols (other platforms: x930, SBx908, SBx81CFC400/960)

**BPDU Forwarding command**
- AWP-9399 — BPDU Forwarding command
  - Suite: STP (x600)
  - Summary: "BPDU Forwarding (x600 only)"
  - Steps: Commands - `awplus(config)#spanning-tree bpdu ?`
    - discard  Discard
    - forward  Forward
    - forward-untagged-vlan  Forward to ports with same untagged vlan
    - forward-vlan  Forward to ports with same vlan
  - Expected: "There are no other parameters to configured. - enabled with forward command - disabled with discard command (should be no command). Disabled version of command does not appear in running config."
- AWP-24878 — BPDU Forwarding command (other platforms)

**Functionality with VLANs / trunk**
- AWP-9401 — BPDU Forwarding - including multiple vlans and trunk mode ports
  - Expected: "NO vlan tags on forwarded BPDUs"
- AWP-24883 — equivalent for other platforms

**Protocol interop**
- AWP-9407 — Protocol Interop: BPDU Forwarding across static channels
  - Expected: "Static channel groups should act as a single port, not individual ports"
- AWP-24888 — equivalent for other platforms

**Other interop**
- AWP-9409 — Protocol Interop: BPDU Forwarding with 802.1x
  - Expected: "Behaviour to be determined - 802.1x uses a form of BPDU."
- AWP-24890 — equivalent

**Older / related**
- AWP-6415 — BPDU (L2 Switching) — "Proper frame reception and counters - BPDU forwarding feature" (notes lack of command at the time)

**Configuration syntax observed**
- Under spanning-tree context:
  ```
  spanning-tree bpdu forward
  spanning-tree bpdu forward-untagged-vlan
  spanning-tree bpdu forward-vlan
  spanning-tree bpdu discard
  ```
- Key behaviour: When any STP protocol (stp/rstp/mstp) is enabled, the BPDU Forwarding setting is automatically disabled and removed from running config.

Many TestLink cases note platform differences (x600 family vs later platforms).

## ATPyLib Cases (Step 3)

**Related STP / BPDU handling (executed in various suites):**
- Suite 1346 (swi_misc): Multiple cases around enabling RSTP, shutdown/re-enable ports and BPDU transmission (e.g. 1346.1001.x series checking BPDU packets sent when RSTP enabled, no BPDUs when shut).
- Suite 2031 (IxANVL_rstp): Extensive BPDU packet format tests (CONFIG BPDU, RST BPDU, TCN BPDU), state machine tests involving BPDU reception and transmission.
- Suite 2032 (IxANVL_stp): Similar STP conformance BPDU handling.
- Suite 2021 (IxANVL_mstp): MSTP BPDU / CIST / MSTI message handling.
- General RSTP/MSTP cases in 1330 (VCS failover under RSTP/MSTP) verify BPDU-based loop prevention and topology changes.

**Notes on coverage:**
- Strong coverage of BPDU packet formats and transmission when spanning-tree protocols are active.
- Limited or no direct executed coverage found for the specific "spanning-tree bpdu forward" feature (the non-STP BPDU forwarding mode).
- The mutual exclusion (auto-disable when STP enabled) is primarily documented in TestLink historical cases.
- Interop details (LAG as single port, untagged behavior, 802.1x) appear to be TestLink-driven.

## Gaps Noted
- Primary AWP-9400 focuses on the conflict with STP protocols.
- Detailed command options and forwarding semantics (no tags, per-vlan, LAG treatment) come from the dedicated BPDU Forwarding TestLink family.
- ART provides excellent protocol-level BPDU handling when STP is running, but the "BPDU Forwarding" feature (used when STP is disabled) has thinner direct automation coverage.
- Older case AWP-6415 notes that a command for BPDU forwarding was not always present.

## Tangential Cases Reviewed
- Standard STP topology change, interop (IPv6 + STP, VRRP + STP, etc.) from batch.
- General BPDU reception in L2 learning suites.
- These exercise normal STP BPDU processing but do not cover the "bpdu forward" mode or the explicit mutual exclusion with STP protocols.

## ART Test Cases String
1346 (BPDU transmission under RSTP), 2031/2032/2021 (IxANVL RSTP/STP/MSTP BPDU formats and state machines) + BPDU Forwarding TestLink family (AWP-9399/9400/9401/9407/9409 + platform variants 248xx)

## Scope Notes
- The manual case title is "BPDU Forwarding" under Switching STP.
- Core artefacts centre on:
  - The `spanning-tree bpdu forward` (and variants) command.
  - Automatic disable when STP/RSTP/MSTP is enabled.
  - Forwarding behaviour: untagged BPDUs, LAG treated as single logical port, per-VLAN options.
- User direction on previous case (T33275) was to exclude VCS/hot-swap style scenarios when they are secondary; apply similar judgement here if needed.

## Synthesis Notes for Objectives (draft)
Objectives should cover:
- Command availability and options under spanning-tree.
- Mutual exclusion: enabling STP protocol auto-disables / removes bpdu forward setting.
- When BPDU Forwarding is active (STP disabled), BPDUs are forwarded without VLAN tags (or per configured vlan rules).
- LAG / static channel groups are treated as a single port for BPDU forwarding.
- Interop notes with other features (e.g. 802.1x) where relevant.
