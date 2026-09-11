# Traceability & Supporting Data for AWPTCM-T33351 (Authentication&Security_IEEE 802.1X - Single host)

## Primary Decision
- From `data/decisions/dec_01.json`: AWPTCM-T33351 {"m": "AWP-6809", "c": "high", "w": "802.1X single-host combination test"}
- Zephyr title: "(188) Authentication&Security_IEEE 802.1X -  Single host"
- Folder: /New Platform Test (MASTER)/New Platform Template/Authentication & Security
- Current Zephyr state: empty objective, empty precondition, single empty step. (Status: Draft)

## Top Relevant TestLink Cases
Primary + closely related "Single-Host" combination tests from the "Combination Tests - dot1x" and related "Functional" / "Parallel Use Tests" suites (Port Authentication area). These cover core single-host auth success, VLAN assignment (Guest/Dynamic), error cases for unsupported combos, basic port-control/host-mode, logoff, and parallel auth scenarios.

1. **AWP-6809** (Primary) — Combination Tests (802.1X authentication) - Single-Host / GuestVLAN / per port / no DynamicVLAN
   - Suite: Combination Tests - dot1x
   - Summary: When 802.1x authentication are used, confirm that the authentication is succeeded. And, after the authentication is succeeded, the supplicant is assigned to other VLAN.
   - Justification: Direct high-confidence match from decisions. Core single-host + GuestVLAN behavior.

2. **AWP-6807** — Combination Tests (802.1X authentication) - Single-Host / no GuestVLAN / per port / no DynamicVLAN
   - Suite: Combination Tests - dot1x
   - Summary: When 802.1x authentication is used, confirm that the each other authentication is succeeded. And, after the authentication is succeeded, the supplicant is assigned to other VLAN. (Mentions dot1x max-auth-fail etc.)
   - Justification: Same single-host family, no-GuestVLAN variant. Documents baseline single-host without guest.

3. **AWP-6808** — Combination Tests (802.1X authentication) - Single-Host / no GuestVLAN / per port / DynamicVLAN
   - Suite: Combination Tests - dot1x
   - Summary: When 802.1x authentication are used, confirm that the authentication is succeeded. And, after the authentication is succeeded, the supplicant is assigned to other VLAN.
   - Justification: Single-host with DynamicVLAN (no guest). Covers interaction of single-host mode + dyn vlan creation.

4. **AWP-6810** — Combination Tests (802.1X authentication) - Single-Host / GuestVLAN / per port / DynamicVLAN
   - Suite: Combination Tests - dot1x
   - Summary: When 802.1x authentication are used, confirm that the authentication is succeeded. And, after the authentication is succeeded, the supplicant is assigned to other VLAN. [Note on 5.4.5-0.x interface/auth-config modes]
   - Justification: Full combo of single-host + Guest + Dynamic. Completes the matrix for single-host variants.

5. **AWP-6811** — Combination Tests (802.1X authentication) - Single-Host in not supported combination DynamicVLAN
   - Suite: Combination Tests - dot1x
   - Summary: Confirm the behaviour with the non-support combination. Explicitly tests error when issuing auth dynamic-vlan-creation type multi etc. on single-host dot1x.
   - Justification: Negative/error case for unsupported dyn-vlan combos in single-host mode. Good for negative artefacts.

6. **AWP-6800** — Set Port Control - Single/Multi-Supplicant Mode
   - Suite: Functional (Port Authentication)
   - Summary: Confirm the port control state. Tests enabling dot1x port-control auto, then auth host-mode single-host (and multi). Verifies states: Authorized, Unauthorized, Auto.
   - Justification: Foundational command + state machine behaviour for single-host vs multi. Directly supports host-mode single.

7. **AWP-6805** — Receive EAP-Logoff Message - Single-Supplicant Mode
   - Suite: Functional (Port Authentication)
   - Summary: Confirm that the authenticator changes the port to the unauthorized state if it receives the EAP-Logoff message from the supplicant. Detailed expected: EAP-Failure, PAE state, log entries.
   - Justification: Specific single-supplicant logoff / deauth behavior and observability.

8. **AWP-6825** — 802.1X + WEB authentication - Single-Mode / no GuestVLAN / per port / no DynamicVLAN
   - Suite: Parallel Use Tests - dot1x, auth-mac, auth-web
   - Summary: Parallel use tests - Single-Mode / no GuestVLAN / per port / no DynamicVLAN.
   - Justification: Covers co-existence / interaction of 802.1X single-host with WEB auth (mentioned in batch candidates).

**Tangential Cases Reviewed (summary):** 
- Broader combination and MAC/WEB parallel cases (AWP-6812+, AWP-68xx multi-host, other AWP-67xx functional) were considered. Multi-host and MAC-focused cases add value for interop but were kept as secondary (single-host focus of this Zephyr case). G.8032 interop with port auth and other L2 constraints noted in candidates but scoped out as not core to single-host objective.
- Decision: Include above 8 as Top Relevant. Tangentials (e.g. full multi-host matrix, specific EAP variants) omitted unless they surface new artefacts during synthesis.

## ATPyLib Cases (Step 3)

**Core positive auth and VLAN assignment:**
- 1348.1001.20 : 802.1x/ dot1x authentication on port — Verifies 802.1X (dot1x) port authentication, confirming a supplicant is granted network access only after successful authentication.
- 1348.1001.33 : 802.1x/ dot1x authentication with dynamic vlan assignment on port — Verifies 802.1X authentication with dynamic VLAN assignment, confirming an authenticated supplicant is placed into the RADIUS-assigned VLAN.
- 1341.6001.5090 : 802.1x/ dot1x authentication with dynamic vlan assignment (untagged) on port — Scaling + confirmation of assignment.

**Configuration and scaling:**
- 1348.1001.11 : 802.1x configuration changes — Verifies 802.1X port-based authentication configuration, confirming dot1x is enabled and the correct RADIUS server is referenced, and that config is restored after the test.
- 1341.1001.4975 : max supported 802.1x clients — Scaling-limit test for 802.1x clients. Drives up to the platform maximum and confirms handling + config restore.

**RADIUS selection and related:**
- 1348.1001.27 : Flexible RADIUS group selection - 802.1X on port and VLAN.
- 1348.1001.28 : Flexible RADIUS group selection - 802.1x on ports, multiple radius servers.
- 1340.1001.55530 : ip radius source-interface does not work after rebooting (with dot1x auths performed to verify source IP usage post-reboot).
- 1340.1001.65686 : 802.1x auth is failed once if 2 or more users login same time when 2nd server is used (concurrent auth behavior).

**Other relevant:**
- 1331.1001.42500 : dot1x eap forward-vlan command behavior for EAP frames.
- 1331.3001.57026 : Dynamic VLAN assignment by VLAN name (CR57026).
- Host-mode tests (e.g. 1348.1001.42/43/44) primarily exercise multi-supplicant and host-plus-voice; single-host is the base/default exercised by the core auth cases.

## Gaps Noted
- Explicit single-host mode enforcement ("only one supplicant allowed per port") and the full single-host + GuestVLAN / DynamicVLAN matrix is primarily TestLink-driven (combination tests). ART basic auth and dyn-vlan cases cover success + assignment but not all matrix variants in detail.
- EAP-Logoff / deauth state machine details and logging for single-supplicant mode are strongly represented in TestLink AWP-6805.
- Unsupported combo error paths (e.g. dynamic-vlan type multi on single-host) detailed in TestLink (AWP-6811).
- Some CR regressions (re-auth after VCS, concurrent logins) have partial or "inferred/UNSUPPORTED" status in current enriched runs.
- Parallel single-mode 802.1X + WEB (AWP-6825) has limited direct automated coverage.
- Reporting accuracy for single-host state and exact "assigned to other VLAN" post-auth is well-covered in historical cases.

## ART Test Cases String
1348.1001.20 (core dot1x auth success), 1348.1001.33 + 1341.6001.5090 (dynamic VLAN assignment), 1348.1001.11 (config changes + restore), 1341.1001.4975 (max clients), 1348.1001.27 + 1348.1001.28 (RADIUS groups), 1340.1001.55530 (source-interface), 1340.1001.65686 (concurrent), 1331.1001.42500 (eap forward-vlan), 1331.3001.57026 (dyn vlan by name). (Host-mode contrast in 1348 multi-supplicant cases.)

## Tangential Cases Reviewed
Broader combination and MAC/WEB parallel cases (AWP-6812+ multi-host matrix, other AWP-67xx functional) were considered. Multi-host and MAC-focused cases add value for interop but were kept secondary (single-host focus of this Zephyr case). G.8032 interop with port auth and some L3 constraints noted in candidates were scoped out as not core. Web-auth guest VLAN cases (e.g. 1331) provide context but not primary for 802.1X single-host.

## Synthesis Notes for Objectives
Objectives synthesized as declarative end-state artefacts from the approved single-host TestLink family (focus on auth success + VLAN assignment for single supplicant, blocking, logoff deauth, host-mode config, unsupported errors, reporting, persistence, scaling/dyn-vlan) cross-referenced against the ART coverage above. Primary emphasis on single-host specifics per the Zephyr title and high-confidence primary match. Language kept platform-agnostic.

---
**Status**: TestLink list approved via continuation. ATPyLib reviewed. Objectives and testScript drafted and finalized in zephyr_payload.json. Traceability complete.

Following repeatable workflow in OBJECTIVE_DRAFTING_PROCESS.md.
