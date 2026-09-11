# Traceability & Supporting Data for AWPTCM-T37865 (HANP-POE Powered Device does not lose Power during a restart)

## Primary Decision
- From `data/decisions/dec_04.json`: AWPTCM-T37865 {"m": "AWP-24553", "c": "high", "w": "Exact: HANP - no power loss on restart"}
- Zephyr title: "HANP-POE Powered Device does not lose Power during a restart"
- Folder: /New Platform Test (MASTER)/Sanity Check
- Current Zephyr state: empty objective, steps matching the TL primary (enable HANP, attach PDs, check negotiated time, warm restart, no power loss, log check).

## Top Relevant TestLink Cases
Primary + closely related HANP PoE cases from the PoE / High Availability Network Power (HANP) suite. These cover HANP enable, per-port/global, CLI show, restart behavior (warm/soft), and API.

1. **AWP-24553** (Primary) — HANP-POE Powered Device does not lose Power during a restart
   - Suite: PoE / High Availability Network Power (HANP)
   - Summary: (empty, but steps detailed)
   - Steps: Enable HANP. Attach PDs. Check "show power-inline interface detail" for Last negotiated time/date. Warm reboot (reboot). Check log for HANP active. Check negotiated time same as before. Expect: no PoE device loses power, times match.
   - Justification: Direct high-confidence exact match. Core for HANP preventing PoE power loss on warm restart.

2. **AWP-24560** — HANP-POE Powered Device does not lose Power during a soft restart
   - Suite: PoE / High Availability Network Power (HANP)
   - Summary: Updating the release file does not cause attached PoE devices to power off.
   - Steps: Enable HANP. Attach PDs. (implied during soft update).
   - Justification: Related soft restart / software update case without power loss.

3. **AWP-24554** — CLI - HANP Show Commands
   - Suite: PoE / High Availability Network Power (HANP)
   - Summary: Verify system level and interface level configuration for HANP is show on the CLI. Also verify information on when the port negotiated power.
   - Justification: CLI observability for HANP config and negotiated times.

4. **AWP-24552** — Feature can be disabled on a per-port basis provided it is enabled globally
   - Suite: PoE
   - Summary: Enable HANP. Confirm per-port disable possible if global enabled.
   - Justification: Per-port control of HANP.

5. **AWP-24551** — Feature can be activated on a system wide basis.
   - Suite: PoE
   - Summary: HANP can be enabled Globally.
   - Justification: Global enable behavior.

**Tangential Cases Reviewed (summary):** 
- AWP-23800 (POE API HANP), AWP-4506 (startup power disabled), AWP-11693 (PoE CFC failover).
- These provide context for HANP activation, startup, and failover but lower direct match for restart power retention.
- Decision: Focused on core HANP PoE restart family.

## ATPyLib Cases (Step 3)
- 1358 PoE suite: 1358.1001.7 Check high-availability network power behaviour (inferred/UNSUPPORTED in some runs).
- 1358.1001.10 Check HANP works after PoE is restored after stopping.
- 1358.1001.56299 PoE is restored after stopping.
- General PoE delivery, status reporting, priorities, disable/enable, persistence over reboot/rolling-reboot.
- Limited direct "no power loss during warm restart with HANP" in enriched data; more on PoE subsystem restart and HANP after stop/restore. Power delivery persistence and HANP behavior covered in 1358.

## Gaps Noted
- Specific "no PoE power loss during warm restart with HANP enabled" and "Last negotiated time preserved" is primarily from TL primary.
- ART covers PoE status, delivery, and some HANP after forced stop/restore, plus general persistence over reboots.
- Warm reboot vs soft update (AWP-24560) distinguished in TL.
- CLI show for HANP config/negotiated times from TL.
- Some ART HANP cases inferred or unsupported in current runs.

## ART Test Cases String
1358 (PoE power delivery, status, priorities, HANP after stop/restore, persistence over reboot) + related 57xx platform PoE if applicable.

## Synthesis Notes for Objectives
Zephyr currently empty objective with steps directly from TL. Enrich to capture HANP-enabled PoE devices retain power and negotiated state across warm restart. Include enable, attach, check, reboot, verify no loss + log + time preservation. Platform-agnostic where possible. Number of bullets flexible.

---
**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.

Following repeatable workflow in OBJECTIVE_DRAFTING_PROCESS.md.
