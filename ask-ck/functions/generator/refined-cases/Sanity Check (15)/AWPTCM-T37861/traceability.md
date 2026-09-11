# Traceability & Supporting Data for AWPTCM-T37861 (POE - lldp max power and cli power)

## Primary Decision
- From `data/decisions/dec_04.json`: AWPTCM-T37861 {"m": "AWP-4577", "c": "high", "w": "Exact: POE lldp max power and cli power"}
- Zephyr title: "POE - lldp max power and cli power"
- Folder: /New Platform Test (MASTER)/Sanity Check
- Current Zephyr state: objective "lldp max power is overridden by cli setting for interface max power", steps for LLDP script + CLI config.

## Top Relevant TestLink Cases
Primary + closely related PoE LLDP and max power cases. Focus on LLDP max power recognition, CLI override, and related power budget.

1. **AWP-4577** (Primary) — POE - lldp max power and cli power
   - Suite: PoE / LLDP
   - Summary: lldp max power is overridden by cli setting for interface max power.
   - Steps: Connect LLDP device via POE Load box. Send LLDP max power values. Configure from cli. Expect: cli overrides lldp max power, reverts when CLI removed.
   - Justification: Direct high-confidence exact match. Core for CLI override of LLDP max power.

2. **AWP-4576** — POE - lldp max power is recognised
   - Suite: PoE / LLDP
   - Summary: lldp max power is recognised and overrides classification max power.
   - Justification: LLDP max power recognition and override of class power.

3. **AWP-4575** — PoE cli Interface max power
   - Suite: PoE
   - Summary: POE Max power can be configured on each port & overrides classification power.
   - Justification: CLI interface max power behavior.

4. **AWP-14385** — Change the max power
   - Suite: PoE
   - Summary: Change the max power. "power-inline max <> " => Confirm PoE max power has changed.
   - Justification: CLI max power config.

5. **AWP-5657** — Extended Power TLV: Max power not configured
   - Suite: LLDP
   - Summary: Test for the actual value of Extended Power TLV transmitted when Max power is not configured.
   - Justification: LLDP TLV behavior for max power.

**Tangential Cases Reviewed (summary):** 
- PowerBudget LLDP-MED cases (AWP-4574, 4573), dynamic changes (AWP-4580).
- Decision: Focused on LLDP vs CLI max power interaction family.

## ATPyLib Cases (Step 3)
- 1358 PoE: device reporting of POE status (show power-inline), POE supplied for priorities, global/port disable/enable, power persistence, HANP.
- LLDP suites (e.g. 1332): LLDP-MED TLV conformance (Capabilities Policy TLV etc.).
- Limited direct hits for exact "CLI overrides LLDP max power" ; general PoE status and LLDP power TLVs.

## Gaps Noted
- Specific CLI override of LLDP max power (and revert) is TL-driven (primary and siblings).
- ART covers PoE status reporting and LLDP TLVs, but the precedence/override behavior between CLI and LLDP-MED max power may rely on TL.
- Related power budget/LLDP-MED cases provide context.

## ART Test Cases String
1358 (PoE status, priorities, disable, HANP) + LLDP suites (e.g. 1332 TLV) + platform PoE.

## Synthesis Notes for Objectives
Zephyr focuses on CLI overriding LLDP max power. Enrich with TL: CLI max power takes precedence over LLDP, reverts when removed; LLDP recognised and overrides classification. Include verification steps with LLDP script and load box. Note platform aspects if relevant. Declarative artefacts for the override behavior.

---
**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.

Following repeatable workflow in OBJECTIVE_DRAFTING_PROCESS.md.