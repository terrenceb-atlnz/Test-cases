---
name: x230v2-5700-control-corpus
description: "raw-data/test_scripts/5700_bootloader/ is a FULL x230v2 run of the same 5700 suite (Feb 2026, near all-pass) — the control that separates IE520 output DIVERGENCE from universal test rot; grep needs -a or these logs read as binary and return NOTHING"
metadata:
  node_type: memory
  type: reference
---

`raw-data/test_scripts/5700_bootloader/` holds a **complete 5700 bootloader campaign run on x230v2**
— 2026-02-19, build `awplus_main-20260218-1237`, same suite, `framework -> /home/st-art/framework`.
It has the pristine `test-5700.200x.py` + `library_5700.py` **and** full console captures
(`swi_a_2001..2005.log`). Read-only reference — never write here.

**Why it matters:** it is the only way to answer "does the IE520 say something different, or does
NO platform say this any more?" Baseline results — 2003 **13 PASS / 0 FAIL**, 2005 **8 PASS / 0
FAIL**, 2002 16 PASS / 3 FAIL / 7 UNSUP. Effectively all-pass, so any IE520 failure on a gate string
that passes here is a **product output question, not test rot.**

> **`grep` READS THESE LOGS AS BINARY.** Both the x230v2 and IE520 `swi_a_*.log` contain control
> bytes, so plain `grep` prints nothing and `grep -c` returns 0 — indistinguishable from a real
> absence. **Always `grep -a`.** This produced a false "0 occurrences on both platforms" mid-session
> until caught. Combine with the device-output-only filter (drop lines matching
> `^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d: `) or you match the framework's own logged strList as if it were
> device output.

**The 2026-08-12 comparison, for reuse.** Of 26 edits made to run the IE520, **12 (5 defects)
accommodate IE520 verbiage** and should be product questions; 14 are genuine cross-platform test
bugs. Divergences:

| # | x230v2 emits | IE520 emits |
|---|---|---|
| D1 | `Verifying release... OK` + `Booting...` (215 device lines) | raw U-Boot/FIT: `Probing SPI flash... Complete`, `Booting image 04000000#IE520-28GSX ...`, `Verifying Hash Integrity ... sha1+ OK` (0 `Verifying release`) |
| D2 | `Reading filesystem...` → straight to `Listing of usable files` | dumps the raw filesystem listing (sizes) in between — which is WHY the size-as-menu-index parse bit here and not there |
| D3 | `Saving settings... Complete` contiguous | split by `Saving Environment to SPIFlash...` (0 on x230v2, 36 on IE520) |
| D4 | `Restoring default settings... Complete` contiguous | same SPIFlash interleave |
| D5 | `Verifying release... Error: This release file is not intended for this device.` | no such stage; `Could not find configuration node` / `ERROR -2: can't get kernel image!` (upper case, so `'Error'` misses) |

**D1 and D5 are one question:** does the IE520 implement the AT release-verification stage at all?
If it should, several "fixed" cases are passing against the wrong output.

> ## UPDATE 2026-08-12 — A0 CONFIRMED AND FIXED; D1/D5 STILL BROKEN
>
> A second bootloader (`IE520-bootloader-pauld.kwb`, a developer `-dirty` build, still U-Boot
> 2025.01 underneath) was tested live on tb470 u4. **The A0 inference was right and the leak is
> a suppression problem:** all 11 leaked strings now measure 0 (`U-Boot 2025.01` 995→0,
> `Verifying Hash Integrity` 495→0, `Saving Environment to SPIFlash` 142→0), and the AT banner
> form is restored (`Bootloader pauld loaded`, matching x230v2's `Bootloader 6.2.37 loaded`).
> **D2, D3, D4 all FIXED.**
>
> **But suppression alone was not the fix.** Removing the U-Boot noise did not restore the AT
> messages the tests gate on. **D1 and D5 are now SILENT rather than wrong** — and D5 is *worse*:
> a foreign release is correctly refused with no output at all, then the normal reboot prints
> `Allied Telesis Inc.` / `Mounting` / `Initializing`, all in case 30's **good** keyword list, so
> the test concludes the foreign release **booted**.
>
> Also: **`BOOT_MARKERS` is broken on that build** — 3 of 4 markers dead, only `login:` survives
> (the last line of a completed boot). Use `Mounting` / `Initializing`.
>
> The ask is now singular: restore `Verifying release... OK` and `Error: This release file is not
> intended for this device.` Full detail + captures:
> `claude/IE520-testing/automated-bootloader/ie520-5700-edit-inventory-2026-08-12.txt` and
> `new-bootloader-pauld-20260812/`.

**Ruled OUT as divergence — genuine universal test rot, correct to fix:**
`'Password Successfully updated'` (0 device lines on x230v2 too; the gate logs `wait time reached`
there as well, so x230v2 passed by accident-of-timeout identically), and the `dir *.rel` existence
parse (output format is **byte-identical** in shape on both: `flash:/mainrelease.rel`).

Corrects the "gate-string rot" framing in [[bootloader-media-parse-bug]]. Design principle:
**never reclassify a failing gate as "rot" from one platform's logs alone** — check a passing
platform first, or you convert a product finding into a test change.
