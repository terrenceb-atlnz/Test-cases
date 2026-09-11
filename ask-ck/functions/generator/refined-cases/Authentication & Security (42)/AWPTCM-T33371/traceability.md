# Traceability & Supporting Data for AWPTCM-T33371 (Authentication&Security_TwoStepAuthentication - 802.1x 1st then Web Auth 2nd)

## Primary Decision
- From `data/decisions/dec_02.json`: AWPTCM-T33371 {"m": "AWP-14784", "c": "high", "w": "Two-Step 1st 802.1x / 2nd WEB"}
- Zephyr title: "(212) Authentication&Security_TwoStepAuthentication - 802.1x 1st then Web Auth 2nd"
- Folder: /New Platform Test (MASTER)/New Platform Template/Authentication & Security
- Current Zephyr state: empty objective, empty precondition, single empty step. (Status: Draft)

## Top Relevant TestLink Cases
Primary + closely related Two-Step Authentication cases, focused on 1st:802.1x / 2nd:WEB flow (note reversed order from previous siblings), plus foundational two-step CLI, show commands, logging at each step (especially 802.1x as 1st), max supplicants for this order, RADIUS 2-step, and blocked access at wrong step.

1. **AWP-14784** (Primary) — Two-Step 1st: 802.1x / 2nd:WEB
   - Suite: End to End test (Port Authentication)
   - Summary: Confirm that Two-Step Auth works correctly when 1st Step:802.1x, 2nd Step:WEB
   - Steps (key flow):
     - Invalid 802.1x at 1st step → status HELD during quiet-period.
     - Correct 802.1x at 1st → status "Connecting" for WEB-auth.
     - Invalid WEB within max-auth-fail times at 2nd → "Reauthenticating".
     - Invalid WEB at max-auth-fail count at 2nd → HELD during quiet-period.
     - Correct WEB at 2nd → "Authenticated".
     - Access WEB auth page at the 1st step → shows "please retry later", cannot try WEB auth.
   - Preconditions: Enable two-step auth, 802.1x auth and WEB auth. (Possibly increase "auth timeout connect-timeout".)
   - Justification: Direct high-confidence primary match for this specific order (802.1x first, WEB second).

2. **AWP-14773** — auth two-step enable
   - Suite: CLI test (Port Authentication)
   - Summary: Confirm that "auth two-step enable" command can be configured correctly. Includes show running-config, save/reboot persistence, and "no" form.
   - Justification: Foundational for two-step feature (shared across orders).

3. **AWP-14774** — show auth two-step supplicant
   - Suite: CLI test (Port Authentication)
   - Summary: Confirm "show auth two-step supplicant brief" and detailed correctly show firstMethod, secondMethod, counts, per-supplicant step status.
   - Justification: Core reporting for two-step (first=802.1x, second=web).

4. **AWP-14776** — Log when 802.1x auth is successful as 1st or 2nd step
   - Suite: Log test (Port Authentication)
   - Summary: Confirm correct log messages at right time for 802.1x success (here as 1st step).
   - Justification: Logging for 802.1x as first method.

5. **AWP-14779** — Log when 802.1x auth fails as 1st or 2nd step
   - Suite: Log test (Port Authentication)
   - Summary: Confirm correct failure logs for 802.1x fail (as 1st step).
   - Justification: Negative logging for first-step 802.1x failure.

6. **AWP-14880** — MAX acceptable Supplicant when used Two-Step auth(1st:802.1x 2nd:WEB)
   - Suite: Port Authentication (from batch candidates)
   - Summary: Confirm how many supplicants accepted for Two-Step 1st:802.1x 2nd:WEB.
   - Justification: Scaling/limit specific to this order.

7. **AWP-15819** — RADIUS packet with 2-step authentication
   - Suite: RADIUS
   - Summary: Confirm VLAN ID included in RADIUS-Request each time when using 2-step authentication.
   - Justification: RADIUS behavior in two-step (relevant for 802.1x first).

8. **AWP-14777** — Log when WEB auth is successful as 2nd step (and related fail logs)
   - Suite: Log test (Port Authentication)
   - Summary: Confirm correct logs for WEB success as 2nd step.
   - Justification: Logging for WEB as second method.

**Additional context:** Related two-step cases from family (max/repeat for other orders, auth-mac password for other combos) provide contrast. The primary includes explicit test that WEB page is blocked when 802.1x first step not yet done.

**Tangential Cases Reviewed (summary):** 
- Other two-step orders and max/repeat cases.
- Roaming auth and general re-auth cases (next in batch).
- Scoped broader simultaneous/tri-auth and customer scenario roaming as not core to this exact 802.1x-first / WEB-second order.

## ATPyLib Cases (Step 3)

**802.1x auth coverage:**
- 1348.1001.20 : 802.1x/ dot1x authentication on port
- 1348.1001.11 : 802.1x configuration changes
- 1348.1001.27/28 : Flexible RADIUS for 802.1X

**Web auth coverage:**
- 1348.3001 series (e.g. 1348.3001.2/4/6/8): web auth success/failure, access granted/denied, guest-vlan on fail, multi-user web auth.

**Two-step / combined:**
- 6201.1033.* : Two step auth variants (MAC focused but include web fail checks)
- General coexistence and RADIUS in port auth suites.

Specific 802.1x-first then WEB ordering, blocked access at first step, and Reauthenticating state transitions are lighter in enriched ART (more general auth paths); rely on TL for detailed sequencing.

## Gaps Noted
- Exact flow for 802.1x as 1st (HELD on fail, Connecting on success, blocked WEB page) and WEB as 2nd (Reauthenticating/HELD, success) + specific logs primarily TestLink (AWP-14784 + log cases).
- "auth two-step enable", show supplicant, and max supplicants for this order from TL.
- RADIUS packet behavior in 2-step.
- ART good for standalone 802.1x and web auth; combined two-step order with block relies on TL family.

## ART Test Cases String
1348.1001.20 (802.1x auth), 1348.1001.11 (config), 1348.3001.* (web auth success/fail/guest), 6201.1033.* (two-step variants + web fail) + RADIUS selection cases.

## Tangential Cases Reviewed
Other two-step orders, max/repeat cases, roaming auth (next batch items), and general re-auth were reviewed but scoped to keep focus on 802.1x-first / WEB-second order.

## Synthesis Notes for Objectives
Objectives from this reversed two-step order: 802.1x first success moves to WEB second, failure behaviors, blocked early WEB access, logs, enable/show with correct methods, max, RADIUS. ART provides separate 802.1x and web coverage; TL supplies the ordered two-step details and block.

---
**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.

Following repeatable workflow in OBJECTIVE_DRAFTING_PROCESS.md.
