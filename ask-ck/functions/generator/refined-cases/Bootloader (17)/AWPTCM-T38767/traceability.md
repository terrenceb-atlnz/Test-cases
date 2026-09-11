# Traceability & Supporting Data for AWPTCM-T38767 (Boot Menu - Restore Factory Settings)

## Primary Decision
- From `data/decisions/dec_04.json`: AWPTCM-T38767 {"m": "AWP-2719", "c": "high", "w": "Restore bootloader factory settings"}
- Zephyr title: "Boot Menu - Restore Factory Settings"
- Folder: /New Platform Test (MASTER)/Bootloader
- Current Zephyr state: empty objective and steps (thin case).

## Top Relevant TestLink Cases
Primary + closely related Bootloader restore cases from the Bootloader suite. These cover restore factory settings, variants for tftp, release, developer mode, console speed.

1. **AWP-2719** (Primary) — Bootloader - Boot Menu - Option 7 - Restore Bootloader factory settings
   - Suite: Bootloader / Bootloader - BootMenu
   - Summary: Bootloader menu: "7. Restore Bootloader factory settings" should work. Bootloader - Restore bootloader factory settings - sanity test.
   - Steps: Set up device to boot from tftp by default. Reboot and confirm. Reboot and go into bootloader (ctrl-B). Select "7" from Boot Menu to restore. When rebooted, the device will reboot as set by default options. Expect: Bootloader settings are restored to default by option 7.
   - Justification: Direct high-confidence exact match. Core for restore bootloader factory settings via menu option 7.

2. **AWP-2722** — Bootloader - Restore bootloader factory settings - tftp settings reset
   - Suite: Bootloader / Bootloader - General tests
   - Summary: Bootloader menu: "7. Restore Bootloader factory settings" should work. Bootloader - Restore bootloader factory settings - tftp settings reset.
   - Justification: Specific variant for tftp settings reset on restore.

3. **AWP-2723** — Bootloader - Restore bootloader factory settings - release boot file settings reset
   - Suite: Bootloader / Bootloader - General tests
   - Summary: Bootloader menu: "7. Restore Bootloader factory settings" should work. Bootloader - Restore bootloader factory settings - e.g. default boot source and console baud rate.
   - Justification: Release boot file settings reset.

4. **AWP-2720** — Bootloader - Restore bootloader factory settings - developer mode cleared
   - Suite: Bootloader / Bootloader - General tests
   - Summary: Bootloader menu: "7. Restore Bootloader factory settings" should work. Bootloader - Restore bootloader factory settings - developer mode cleared.
   - Justification: Developer mode cleared on restore.

5. **AWP-2721** — Bootloader - Restore bootloader factory settings - console speed settings reset
   - Suite: Bootloader / Bootloader - General tests
   - Summary: Bootloader menu: "7. Restore Bootloader factory settings" should work. Bootloader - Restore bootloader factory settings - console speed settings reset.
   - Justification: Console speed reset.

**Tangential Cases Reviewed (summary):** 
- Other bootloader menu options (AWP-2696, AWP-19571 developer menu), restore from media, etc.
- Decision: Focused on the restore factory settings family and its specific reset behaviors.

## ATPyLib Cases (Step 3)
- 5700 platform tests: 5700.1002.7 Check bootloader version.
- 5700.1003.5 Diagnostics menu option 4, Bootloader ROM checksum test.
- Other bootloader related in 5700 series for diagnostics, version checks.
- Limited direct "restore factory settings" coverage; more on version, checksum, boot menu options.

## Gaps Noted
- Specific restore via menu option 7 and the various reset behaviors (tftp, release, developer, console) are from TL.
- ART covers bootloader version checks and ROM tests, but not the full restore process.
- Zephyr case is thin (empty objective/steps).

## ART Test Cases String
5700.1002.7 (bootloader version), 5700.1003.5 (ROM checksum) + related platform bootloader/diagnostics tests.

## Synthesis Notes for Objectives
Zephyr is empty. Enrich with TL: restore factory settings via bootloader menu option 7 resets various settings to default (tftp, release boot, developer mode, console speed). Artefacts around successful restore, settings reverted, device boots with defaults.

---
**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.

Following repeatable workflow in OBJECTIVE_DRAFTING_PROCESS.md.
