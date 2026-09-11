# Traceability & Supporting Data for AWPTCM-T37860 (POE LED-POE)

## Primary Decision
- From `data/decisions/dec_04.json`: AWPTCM-T37860 {"m": "AWP-4594", "c": "high", "w": "Exact: POE LED-POE"}
- Zephyr title: "POE LED-POE"
- Folder: /New Platform Test (MASTER)/Sanity Check
- Current Zephyr state: objective "Functional LED Operation Nominal POE port connection", steps: "Normal PD operation is represented with a steady green LED (old Duplex LED)"
- Note: Zephyr has some content already. Part of PoE LED family following T37859.

## Top Relevant TestLink Cases
Primary + closely related PoE LED cases from the PoE/LED suite. These cover nominal POE LED (green), non-POE, no connection, and related fault/power budget for context.

1. **AWP-4594** (Primary) — POE LED-POE
   - Suite: PoE / LED
   - Summary: Functional LED Operation Nominal POE port connection.
   - Steps: Normal PD operation is represented with a steady green LED (old Duplex LED) => Green LED is illuminated on effected port.
   - Justification: Direct high-confidence exact match. Core for nominal POE LED indication (steady green).

2. **AWP-4593** — POE LED-NonPOE
   - Suite: PoE / LED
   - Summary: Functional LED Operation Non-POE port connection.
   - Steps: Make a non POE connection, but carry L2 traffic via port POE => No duple? (no LED change expected for PoE).
   - Justification: Contrast for non-POE connection on PoE-capable port.

3. **AWP-4592** — POE LED-NoConnections
   - Suite: PoE / LED
   - Summary: Functional LED Operation No port connection.
   - Steps: No connection to port => No LED is illuminated.
   - Justification: Baseline for no connection (no LED).

4. **AWP-4596** — POE LED-Fault-OverDrawByUserBudget (cross-ref from previous)
   - Suite: PoE / LED
   - Summary: Over drawing power based on User budget => Flashing Orange LED fault.
   - Justification: Related fault case for contrast (user feedback: LED details platform-specific; check device spec).

5. **AWP-4595** — POE LED-Fault-OverDrawByClass
   - Suite: PoE / LED
   - Summary: Over drawing power based on Class allocation => Steady Orange LED.
   - Justification: Related fault LED state.

**Tangential Cases Reviewed (summary):** 
- Power budget cases (AWP-25249 etc.), system LEDs, AWC LED.
- Decision: Focused on core PoE LED states (nominal, non, none, fault). LED behavior varies by platform per prior feedback.

## ATPyLib Cases (Step 3)
- 1358 series (PoE tests): Basic PoE delivery, device reporting of POE status, POE supplied for priority settings, global disable/enable, legacy mode, HANP (high availability network power).
- 1358.1001.2 : Check device reporting of POE status.
- 1358.1001.3 : Check POE is supplied for all priority settings.
- No direct hits for specific nominal LED states (steady green) in enriched data; PoE tests focus on power delivery/status rather than LED behavior. LED indication appears TL-driven.

## Gaps Noted
- Specific LED color/state for nominal POE (steady green) is from primary TL; ART does not appear to verify LED colors/states directly.
- Distinctions between POE / NonPOE / No connection from TL.
- ART provides power delivery, status reporting, but LED behavior for nominal vs fault may rely on manual/TL + device spec.
- Platform variation noted (from T37859 feedback): actual light performance varies platform-to-platform.

## ART Test Cases String
1358 (PoE power delivery/status/priorities/HANP) + 5701/5710 (platform PoE MIB etc.)

## Synthesis Notes for Objectives
Zephyr already has basic objective and step for nominal POE LED (steady green). Enrich with TL family for full states: steady green for nominal POE connection, no LED for no connection, specific for non-POE. Include contrasts with fault cases (with platform spec note). Qualify LED details as platform-specific per user feedback. Keep declarative end-states. Cover power-related context from family if relevant.

---
**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.

Following repeatable workflow in OBJECTIVE_DRAFTING_PROCESS.md.
