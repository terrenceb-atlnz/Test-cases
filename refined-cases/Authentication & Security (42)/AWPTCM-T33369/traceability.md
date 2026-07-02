# Traceability & Supporting Data for AWPTCM-T33369 (Authentication&Security_TwoStepAuthentication - Mac-based 1st then 802.1x 2nd)

## Primary Decision
- From `data/decisions/dec_02.json`: AWPTCM-T33369 {"m": "AWP-14782", "c": "high", "w": "Two-Step 1st MAC / 2nd 802.1x"}
- Zephyr title: "(210) Authentication&Security_TwoStepAuthentication - Mac-based 1st then 802.1x 2nd"
- Folder: /New Platform Test (MASTER)/New Platform Template/Authentication & Security
- Current Zephyr state: empty objective, empty precondition, single empty step. (Status: Draft)

## Top Relevant TestLink Cases
Primary + closely related Two-Step Authentication cases, focused on 1st:MAC / 2nd:802.1x flow, plus foundational two-step CLI, show commands, logging at each step, max supplicants, repeat testing, and simultaneous auth. These are primarily from "Port Authentication" / "End to End test" / "CLI test" suites.

1. **AWP-14782** (Primary) — Two-Step 1st: MAC / 2nd 802.1x
   - Suite: End to End test (Port Authentication)
   - Summary: Confirm that Two-Step Auth works correctly when 1st Step:MAC, 2nd Step:802.1x
   - Steps (key flow):
     - Invalid MAC at 1st step → status HELD during quiet-period.
     - Correct MAC at 1st → status "Connecting" for 802.1x 2nd step.
     - Invalid 802.1x at 2nd → HELD.
     - Correct 802.1x at 2nd → "Authenticated".
   - Preconditions: Enable two-step auth, mac-auth and 802.1x; optional auth-mac password.
   - Justification: Direct high-confidence primary match. Core end-to-end happy + negative path for this exact two-step order.

2. **AWP-14773** — auth two-step enable
   - Suite: CLI test (Port Authentication)
   - Summary: Confirm that "auth two-step enable" command can be configured correctly. Includes show running-config, save/reboot persistence, and "no" form clears it.
   - Justification: Foundational configuration for the two-step feature.

3. **AWP-14774** — show auth two-step supplicant
   - Suite: CLI test (Port Authentication)
   - Summary: Confirm "show auth two-step supplicant brief" and detailed output correctly displays two-step info: firstMethod, secondMethod, counts, per-supplicant status for each step.
   - Justification: Core observability / reporting command for two-step supplicants.

4. **AWP-14776** — Log when 802.1x auth is successful as 1st or 2nd step
   - Suite: Port Authentication
   - Summary: Confirm correct log messages at the right time for 802.1x success whether it is the 1st or 2nd step.
   - Justification: Important for logging behaviour in two-step scenarios (2nd step success in our primary).

5. **AWP-14779** — Log when 802.1x auth fails as 1st or 2nd step (and related fail log cases)
   - Suite: Port Authentication
   - Summary: Confirm correct failure logs (HELD, quiet-period, etc.) for 802.1x failure at 1st or 2nd step.
   - Justification: Negative path logging for 2nd step failure in primary flow.

6. **AWP-14879** — MAX acceptable Supplicant when used Two-Step auth(1st:MAC 2nd:802.1x)
   - Suite: Port Authentication
   - Summary: Confirm how many supplicants are accepted when using Two-Step auth (1st:MAC 2nd:802.1x).
   - Justification: Scaling / limit behaviour specific to this two-step combination.

7. **AWP-14882** — Repeat Two-Step auth(1st:MAC 2nd:802.1x)
   - Suite: Port Authentication
   - Summary: Confirm DUT does not crash/hang or produce errors after repeated Two-Step auth with this order.
   - Justification: Robustness / repeatability of the feature.

8. **AWP-6858** — 802.1x Authentication and MAC based Authentication (simultaneous)
   - Suite: Port Authentication
   - Summary: Confirm that 802.1x and MAC auth operate correctly at the same time (relevant to two-step coexistence).
   - Justification: Related simultaneous MAC + 802.1x behaviour.

**Additional context from batch candidates:** AWP-14783/14784 (sibling two-step orders), AWP-9901 (DHCP Snooping with 802.1x & MAC), log cases for other methods/steps.

**Tangential Cases Reviewed (summary):** 
- Other two-step orders (MAC/WEB, 802.1x/WEB) and general tri-auth / critical-port cases provide context but are not core to 1st-MAC/2nd-802.1x.
- Broad simultaneous auth and roaming two-step cases scoped as secondary.
- Decision: Focus on the specific primary order + enable/show + logs for this variant + max/repeat. Broader two-step family noted for traceability.

## ATPyLib Cases (Step 3)

**Direct two-step coverage (suite 6201):**
- 6201.1033.1 : Two step auth MAC Address List (Allow mode)
- 6201.1033.2 : Two step auth MAC Address List (Deny mode)
- 6201.1033.3 : Two step auth MAC RADIUS
- 6201.1033.4 : Two step auth MAC Address list + external RADIUS
- 6201.1033.5 : Two step auth Check MAC auth and web auth fail

**Related auth coexistence:**
- 1348 series port auth tests covering MAC + 802.1x / dot1x combinations and state.
- 1357 STOAT clients using Dot1x (MAC authentication aspects).
- General RADIUS and auth-forward cases that exercise multi-method auth.

Two-step specific sequencing and per-step state (HELD → Connecting → Authenticated) + detailed logging appear to have stronger coverage in the historical TestLink end-to-end cases.

## Gaps Noted
- Exact two-step state machine transitions (1st MAC success moves to "Connecting" for 802.1x 2nd step; failure paths to HELD/quiet-period) and precise log message timing are documented in detail in TestLink (AWP-14782 primary + log cases).
- "auth two-step enable" command, persistence across reboot, and "show auth two-step supplicant" (brief + detailed with firstMethod/secondMethod) are primarily from dedicated CLI TestLink cases (AWP-14773, AWP-14774).
- Max supplicant limits and repeat robustness for the MAC-then-802.1x order come from specific TL cases.
- ART provides good coverage for MAC address list two-step (allow/deny + RADIUS variants) and basic MAC+dot1x coexistence, but the ordered "first then second" with explicit 802.1x as 2nd step and HELD states relies more on TestLink.
- Simultaneous vs two-step distinction and DHCP snooping interop noted in candidates.

## ART Test Cases String
6201.1033.1–5 (two-step MAC list allow/deny, MAC RADIUS, list+external RADIUS, fail checks) + 1348 port auth (MAC + 802.1x/dot1x) + related 1357.

## Tangential Cases Reviewed
Sibling two-step combinations (AWP-14783 MAC/ WEB, AWP-14784 802.1x/WEB), general tri-auth, critical-port two-step, and roaming two-step cases provide broader context for the feature family but were kept secondary to keep focus on 1st:MAC / 2nd:802.1x.

## Synthesis Notes for Objectives
Objectives focus on the specific ordered two-step flow (MAC first succeeds → triggers 802.1x second), correct state progression and HELD on failure at either step, logging at each transition, CLI enable + show supplicant reporting (first/second method), persistence of enable, max supplicants, and robustness. ART 6201 cases give MAC-list two-step support; TestLink provides the detailed sequencing and observability.

---
**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.

Following repeatable workflow in OBJECTIVE_DRAFTING_PROCESS.md.
