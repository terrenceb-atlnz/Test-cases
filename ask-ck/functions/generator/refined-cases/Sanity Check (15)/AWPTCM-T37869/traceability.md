# Traceability & Supporting Data for AWPTCM-T37869 (System LED - fan stop)

## Primary Decision
- From `data/decisions/dec_04.json`: AWPTCM-T37869 {"m": "AWP-11637", "c": "high", "w": "Exact: System LED - fan stop"}
- Zephyr title: "System LED - fan stop"
- Folder: /New Platform Test (MASTER)/Sanity Check
- Current Zephyr state: objective "To check if LED is flashing red colour - 1 flash per period (details may vary on some platforms if applicable).", steps: "Cause a unit fan to stop (e.g. XEM fan or PSU fan)"

## Top Relevant TestLink Cases
Primary + closely related System LED fault cases from Environment Monitoring suite. These cover fan stop, faulty XEM, temp, concurrent alarms, and LED patterns (flashes, on some platforms if applicable).

1. **AWP-11637** (Primary) — System LED - fan stop
   - Suite: Environment Monitoring / Environment Monitoring
   - Summary: To check if LED is flashing red colour - 1 flash per period (details may vary on some platforms if applicable).
   - Steps: Cause a unit fan to stop (e.g. XEM fan or PSU fan) => Flashing red colour- 1 flash per period (or equivalent on some platforms if applicable).
   - Justification: Direct high-confidence exact match. Core for fan stop LED indication (1 flash red, platform details if applicable).

2. **AWP-10432** — System LED - fan stop (inactive variant)
   - Suite: z_Inactive
   - Summary: To check if LED is flashing red colour - 1 flash per period.
   - Justification: Related fan stop test.

3. **AWP-11638** — System LED - faulty XEM
   - Suite: Environment Monitoring
   - Summary: To check if LED is flashing red colour -4 flash per period.
   - Justification: Related fault (XEM fail, 4 flashes).

4. **AWP-11640** — System LED - concurrent XEM fail, temp and fan fail alarms
   - Suite: Environment Monitoring
   - Summary: To check if LED lit in sequences of flashes.
   - Justification: Concurrent faults and LED sequencing.

5. **AWP-17692** — LED State - System Failure
   - Suite: Green Features (Ecofriendly)
   - Summary: Verify LED state in the event of system failure. Induced a System Failure like Fan failure, Temperature failure.
   - Justification: LED for system/fan failure (details may vary on some platforms if applicable).

**Tangential Cases Reviewed (summary):** 
- Temp monitoring (AWP-10434), PSU LEDs, green features.
- Decision: Focused on System LED fault patterns for fan stop (primary) and related environment faults. LED details may vary on some platforms if applicable.

## ATPyLib Cases (Step 3)
- Limited direct hits for exact System LED flash patterns in enriched data.
- 1358/5700+ platform/environment suites cover fan status, temp monitoring, system health, but focus on functional status rather than LED behavior.
- Related system failure/LED in green features or platform tests.

## Gaps Noted
- Specific LED patterns (flashing red 1/period) from TL primary. Details may vary on some platforms if applicable.
- ART covers environment monitoring (fan/temp), but LED indication is TL-driven.

## ART Test Cases String
1358/5700 environment and platform monitoring (fan/temp status, system health) + related.

## Synthesis Notes for Objectives
Zephyr has objective for fan stop LED. Enrich with TL family: flashing red for fan stop (1 flash per period, on some platforms if applicable); contrasts with XEM (4 flashes), temp, concurrent. Declarative artefacts for fault indication via LED patterns. Steps to induce fan stop and observe LED (details if applicable on platform).

---
**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.

Following repeatable workflow in OBJECTIVE_DRAFTING_PROCESS.md.
