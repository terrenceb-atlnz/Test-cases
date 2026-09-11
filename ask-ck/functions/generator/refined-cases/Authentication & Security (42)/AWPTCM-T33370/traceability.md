# Traceability & Supporting Data for AWPTCM-T33370 (Authentication&Security_TwoStepAuthentication - Mac-based 1st then Web Auth 2nd)

## Primary Decision
- From `data/decisions/dec_02.json`: AWPTCM-T33370 {"m": "AWP-14783", "c": "high", "w": "Two-Step 1st MAC / 2nd WEB"}
- Zephyr title: "(211) Authentication&Security_TwoStepAuthentication - Mac-based 1st then Web Auth 2nd"
- Folder: /New Platform Test (MASTER)/New Platform Template/Authentication & Security
- Current Zephyr state: empty objective, empty precondition, single empty step. (Status: Draft)

## Top Relevant TestLink Cases
Primary + closely related Two-Step Authentication cases, focused on 1st:MAC / 2nd:WEB flow, plus foundational two-step CLI, show commands, logging at each step (especially WEB as 2nd), max supplicants, repeat testing, auth-mac password, and RADIUS 2-step. These are primarily from "Port Authentication" / "End to End test" / "Log test" / "CLI test" suites.

1. **AWP-14783** (Primary) — Two-Step 1st: MAC / 2nd WEB
   - Suite: End to End test (Port Authentication)
   - Summary: Confirm that Two-Step Auth works correctly when 1st Step:MAC, 2nd Step:WEB. (Note: summary text had copy-paste artifact mentioning 802.1x but title/steps confirm WEB.)
   - Steps (key flow):
     - Invalid MAC at 1st step → status HELD during quiet-period.
     - Correct MAC at 1st → status "Connecting" for WEB-auth.
     - Invalid WEB within max-auth-fail times at 2nd → "Reauthenticating".
     - Invalid WEB at max-auth-fail count at 2nd → HELD during quiet-period.
     - Correct WEB at 2nd step → "Authenticated".
   - Preconditions: Enable two-step auth, mac-auth, WEB auth and auth log. (Optional password for MAC via "auth-mac password").
   - Justification: Direct high-confidence primary match. Core end-to-end happy + negative path for this exact two-step order (WEB as second method).

2. **AWP-14773** — auth two-step enable
   - Suite: CLI test (Port Authentication)
   - Summary: Confirm that "auth two-step enable" command can be configured correctly. Includes show running-config, save/reboot persistence, and "no" form clears it.
   - Justification: Foundational configuration for the two-step feature (shared with sibling cases).

3. **AWP-14774** — show auth two-step supplicant
   - Suite: CLI test (Port Authentication)
   - Summary: Confirm that "show auth two-step supplicant brief" and detailed output correctly displays two-step info: firstMethod, secondMethod, counts, per-supplicant status for each step.
   - Justification: Core observability / reporting command for two-step supplicants (firstMethod=mac, secondMethod=web).

4. **AWP-14777** — Log when WEB auth is successful as 2nd step
   - Suite: Log test (Port Authentication)
   - Summary: Confirm correct log messages at the right time for WEB auth success as the 2nd step.
   - Justification: Important for logging behaviour specific to WEB second step in this two-step combo.

5. **AWP-14780** — Log when WEB auth fails as 2nd step
   - Suite: Port Authentication
   - Summary: Confirm correct failure logs for WEB auth as the 2nd step (including within max-auth-fail and after).
   - Justification: Negative path logging for 2nd step WEB failure.

6. **AWP-14878** — MAX acceptable Supplicant when used Two-Step auth(1st:MAC 2nd:WEB)
   - Suite: Limit test (Port Authentication)
   - Summary: Confirm how many supplicants will be accepted when using Two-Step auth (1st:MAC 2nd:WEB).
   - Justification: Scaling / limit behaviour specific to this two-step combination.

7. **AWP-14881** — Repeat Two-Step auth(1st:MAC 2nd:WEB)
   - Suite: Stress test (Port Authentication)
   - Summary: Confirm DUT does not crash/hang or produce errors after repeated Two-Step auth with this order.
   - Justification: Robustness / repeatability of the feature.

8. **AWP-15977** — auth-mac password / Two-Step auth / MAC + WEB
   - Suite: End to End test (Port Authentication)
   - Summary: Confirm that "auth-mac password" command works correctly when using Two-Step auth of MAC and WEB. Covers correct MAC first then WEB second with password matching MAC or RADIUS.
   - Justification: Specific support for auth-mac password in MAC-first two-step with WEB second.

**Additional context from batch candidates:** AWP-15819 (RADIUS packet with 2-step), AWP-14778 (MAC fail log 1st step), other two-step orders and max/repeat for contrast.

**Tangential Cases Reviewed (summary):** 
- Sibling two-step orders (1st 802.1x / 2nd WEB, etc.) and general tri-auth / critical-port cases provide context but are not core to 1st-MAC/2nd-WEB.
- DHCP snooping with auth, roaming, and other simultaneous cases scoped as secondary.
- Decision: Focus on the specific primary order + enable/show + logs for WEB 2nd + max/repeat + auth-mac password. Broader two-step family noted for traceability.

## ATPyLib Cases (Step 3)

**Direct two-step coverage (suite 6201):**
- 6201.1033.1 : Two step auth MAC Address List (Allow mode)
- 6201.1033.2 : Two step auth MAC Address List (Deny mode)
- 6201.1033.3 : Two step auth MAC RADIUS
- 6201.1033.4 : Two step auth MAC Address list + external RADIUS
- 6201.1033.5 : Two step auth Check MAC auth and web auth fail

**Related web auth:**
- 1348.3001 series: web authentication success/failure paths, guest-vlan on failure, multi-user web auth.
- General MAC + web coexistence and RADIUS integration in port auth suites.

Two-step specific sequencing and per-step state (HELD → Connecting → Reauthenticating → Authenticated) + detailed logging for WEB as 2nd step appear to have stronger coverage in the historical TestLink end-to-end cases. 6201 provides good MAC-list first step + fail checks including web.

## Gaps Noted
- Exact two-step state machine transitions for WEB second method (Connecting after good MAC 1st, Reauthenticating on WEB fail within limit, HELD after max-auth-fail) and precise log message timing (including IP/MAC in WEB logs) are documented in detail in TestLink (AWP-14783 primary + log cases).
- "auth-mac password" usage in two-step MAC+WEB context from dedicated TL.
- ART has good two-step MAC first + RADIUS/list support in 6201 and basic web auth paths in 1348, but the ordered MAC-then-WEB with Reauthenticating state and auth-mac password specifics rely more on TestLink.
- Max supplicant and repeat for this exact order from TL.

## ART Test Cases String
6201.1033.1–5 (two-step MAC list allow/deny, MAC RADIUS, list+RADIUS, MAC+web fail checks) + 1348.3001 web auth paths + related RADIUS/port auth.

## Tangential Cases Reviewed
Sibling two-step (e.g. with 802.1x 2nd), general tri-auth, critical-port, roaming, and DHCP snooping with auth cases provide broader context but kept secondary to focus on 1st-MAC/2nd-WEB.

## Synthesis Notes for Objectives
Objectives synthesized from approved primary two-step MAC/WEB family: ordered state progression with MAC first triggering WEB second, HELD on MAC fail, Reauthenticating/HELD on WEB fails, success to Authenticated, specific WEB logs, auth two-step enable + show reporting (first=mac second=web), auth-mac password, max supplicants, repeat. ART 6201 gives MAC-list two-step + web fail; 1348 for web success/fail.

---
**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.

Following repeatable workflow in OBJECTIVE_DRAFTING_PROCESS.md.
