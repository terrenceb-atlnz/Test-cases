# Traceability & Supporting Data for AWPTCM-T37859 (POE LED-Fault-OverDrawByUserBudget)

## Primary Decision
- From `data/decisions/dec_04.json`: AWPTCM-T37859 {"m": "AWP-4596", "c": "high", "w": "Exact: POE LED Fault OverDrawByUserBudget"}
- Zephyr title: "POE LED-Fault-OverDrawByUserBudget"
- Folder: /New Platform Test (MASTER)/Sanity Check
- Current Zephyr state: objective "Functional LED Operation Over drawing power based on User budget", steps include "Drawing more power than is allocated in the Power user budget"
- Note: Zephyr has some content already.

## Top Relevant TestLink Cases
Primary + closely related PoE LED fault and power budget cases from the PoE/LED suite. These cover LED states for nominal, fault overdraw (user budget and class), and allocated power behavior on PD fault/stop.

1. **AWP-4596** (Primary) — POE LED-Fault-OverDrawByUserBudget
   - Suite: PoE / LED
   - Summary: Functional LED Operation Over drawing power based on User budget.
   - Steps: Drawing more power than is allocated in the Power user budget => Fault indication on effected port (LED behavior per device spec; e.g. flashing orange on some platforms).
   - Justification: Direct high-confidence exact match. Core for user budget overdraw fault indication. Note: actual LED performance (color, flash pattern) varies platform-to-platform; check device spec for PD Fault operation.

2. **AWP-4595** — POE LED-Fault-OverDrawByClass
   - Suite: PoE / LED
   - Summary: Functional LED Operation Over drawing power based on Class allocation.
   - Steps: Fault condition caused by over drawing power per class allocation => Fault indication on effected port (e.g. steady orange on some platforms).
   - Justification: Related fault LED for class-based overdraw (complements user budget; LED details platform-specific).

3. **AWP-4594** — POE LED-POE
   - Suite: PoE / LED
   - Summary: Functional LED Operation Nominal POE port connection.
   - Steps: Normal PD operation is represented with a steady green LED (old Duplex LED) => Green LED is illuminated on effected port (nominal indication).
   - Justification: Baseline nominal POE LED state for contrast with fault states (platform variations may apply).

4. **AWP-4582** — POE AllocatedPower-PD-Fault
   - Suite: PoE / Sifos Non Scripted
   - Summary: Functional Allocated Power PD Fault updates available power.
   - Steps: PD in fault condition - allocated power updated. Put port into fault state by drawing more than max power. => Ports in fault state should be excluded from allocated calculation. Allocated power is updated when port returns from fault condition.
   - Justification: Power budget/allocated power update on PD fault (directly relates to overdraw condition).

5. **AWP-4581** — POE AllocatedPower-PD stops drawing power
   - Suite: PoE / Sifos Non Scripted
   - Summary: Functional Allocated Power PD Stops drawing power.
   - Steps: PD goes stop s drawing power, then starts drawing power. => Allocated power is recalculated when PD stops drawing power.
   - Justification: Power recalculation behavior on PD power stop (context for budget faults).

**Tangential Cases Reviewed (summary):** 
- System LED fault cases (AWP-11638, 10433 etc.) for XEM/environment faults.
- Other PoE power budget cases like not allocated exceed nominal.
- Ecofriendly LED, green features.
- Decision: Focused on PoE LED fault overdraw family (user budget primary, class, nominal) + allocated power fault behavior. System LED and green features tangential.

## ATPyLib Cases (Step 3)
- 1358 series (PoE tests): Basic PoE delivery, device reporting of POE status, POE supplied for priority settings, global disable/enable, legacy mode, HANP (high availability network power).
- 1358.1001.2 : Check device reporting of POE status.
- 1358.1001.3 : Check POE is supplied for all priority settings.
- Other 570x/5710 platform PoE: SNMP PoE MIB, etc.
- No direct hits for specific LED states (flashing orange for user budget fault) in enriched data; PoE tests focus on power delivery/status rather than LED behavior. LED fault indication appears TL-driven.

## Gaps Noted
- LED color/state details for "OverDrawByUserBudget" fault are from primary TL but vary platform-to-platform ("Check device spec for PD Fault operation").
- Class vs User budget distinction in overdraw faults from TL siblings.
- Allocated power recalculation on fault from related TL.
- ART provides power delivery, status reporting, priorities, but specific LED fault indication and exact overdraw-by-user-budget behavior may rely on manual/TL + device spec.

## ART Test Cases String
1358 (PoE power delivery/status/priorities/HANP) + 5701/5710 (platform PoE MIB etc.)

## Synthesis Notes for Objectives
Zephyr already has basic objective and step. Enrich with TL family, but qualify LED details as platform-specific per user feedback: fault indication for user budget overdraw (check device spec), contrast with class/nominal, and power budget updates on fault. Keep declarative end-states focused on the fault condition being properly indicated and power accounting. Include positive nominal + negative fault + reporting via LED/state per spec.

---
**Status**: Initial draft of TestLink list (Step 1). Proceeding with synthesis per "approved, next" pattern.

Following repeatable workflow in OBJECTIVE_DRAFTING_PROCESS.md.
