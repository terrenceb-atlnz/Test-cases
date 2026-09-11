# Traceability & Supporting Data for AWPTCM-T33404 (Management Operation - CLI)

## Primary Decision
- From `data/decisions/dec_03.json`: AWPTCM-T33404 {"m": null, "c": "high", "w": "Zephyr: run ART testsuite 1337_cli_walk - automated, no TL equiv"}
- Zephyr title: "(??) Management Operation - CLI" (from batch)
- Folder: /New Platform Template/Management
- Current Zephyr state: OBJ: Run the ART testsuite 1337_cli_walk ||
- Note: This case is explicitly to execute the automated CLI walk test suite. No strong primary TestLink match; marked high confidence due to Zephyr intent for ART coverage.

## Top Relevant TestLink Cases
Primary match is null / automated. Candidates from review are low-score CLI-related cases (general device management, help, errors, show commands). These provide context for CLI testing but no exact equivalent.

1. **AWP-1133** — NTP - CLI - Help operation and detail
   - Suite: NTP / CLI
   - Summary: NTP - CLI - Help operation and detail | Test NTP CLI and help => Useful and correct help information presented.
   - Justification: Example of CLI help testing in management/CLI area.

2. **AWP-4508** — POE CLI-Error-Messages
   - Suite: PoE / CLI
   - Summary: Device Management Command Handler CLI Error messages. Clear and useful error messages in stacking, power contexts.
   - Justification: CLI error message handling.

3. **AWP-8202** — Device Management - Show Command
   - Suite: BGP / Device Management
   - Summary: Show command output => Accurate and useful.
   - Justification: General show command verification in device management.

4. **AWP-5477** — TFTP CLI operation using prompts and single-line format
   - Suite: TFTP
   - Summary: Objective: To verify CLI operation of TFTP using prompts or single-line format Expected Outcome: CLI should accept and execute commands.
   - Justification: CLI command acceptance for file ops (related to previous TFTP case).

5. **AWP-4500** — POE CLI-Help
   - Suite: PoE
   - Summary: Device Management Command Handler Command Line Help useful and accurate for all commands.
   - Justification: CLI help accuracy.

6. **AWP-3469** — CLI to set ip pim passive mode
   - Suite: PIM-SM
   - Summary: Command Line test.
   - Justification: Example of specific CLI command testing.

**Tangential Cases Reviewed (summary):** 
- Many other CLI help/error/show from PoE, NTP, BGP, OSPF, etc. in candidates.
- Broader device management CLI cases.
- Decision: Since no strong TL primary (per decision note), the relevant are general CLI/device mgmt cases from the low-score list. The case's purpose is ART automation rather than specific TL feature.

## ATPyLib Cases (Step 3)

**Direct coverage:**
- Suite 1337 (CLI Walk): 
  - 1337.1.1 Walk through all the CLI SHOW commands [Log-derived analysis] Broad CLI robustness / soak walk. Saves baseline, walks commands, verifies no exceptions, output, restores config.
  - 1337.1.2 Walk through all the CLI CLEAR commands
  - 1337.1.3 Walk through all the CLI NO commands
  - Other 1337.x cases for CLI robustness / soak testing.

The case objective is explicitly to run the full 1337_cli_walk ART suite for broad CLI coverage.

## Gaps Noted
- No detailed primary TestLink case matching the "run ART 1337_cli_walk" intent (per decision: no TL equiv).
- TL candidates are scattered CLI tests (help, errors, specific commands like NTP/PoE/TFTP/BGP show) but low confidence / general.
- The value and intent of this manual test case is automated exhaustive CLI walk (show/clear/no) for robustness.
- ART 1337 provides the direct coverage; TL provides supplementary examples of expected CLI behavior (useful help, accurate show, clear error messages).

## ART Test Cases String
1337 (full cli_walk suite: 1337.1.1 SHOW walk, 1337.1.2 CLEAR, 1337.1.3 NO, plus related CLI cases)

## Synthesis Notes for Objectives
This case is special: Zephyr objective is literally "Run the ART testsuite 1337_cli_walk". We document the primary as automated (no TL), list relevant CLI TL as tangential context, and synthesize objectives around the coverage provided by the walk: the CLI is complete and robust when exercised by 1337 (all show commands produce accurate/useful output, clear/no commands work as expected, no crashes/exceptions during full walk, config restorable). Use the Zephyr as base. Number of bullets minimal as it's automation-driven.

---
**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.

Following repeatable workflow in OBJECTIVE_DRAFTING_PROCESS.md.
