---
name: bootloader-media-parse-bug
description: "5700 suite: ATBootLoader has TWO LAYERED bugs (file-size parse + 'Saving settings' rot); runs MUST be root or eth1 reads as missing; Level-2 erase is 2145s MEASURED; \"INFINITE LOOP\"/\"WAITED TOO LONG\" are flat 1800s timeouts"
metadata: 
  node_type: memory
  type: project
  originSessionId: 16d533ce-4a44-4c64-85a0-7af2c092d5db
  modified: 2026-08-10T20:35:35.446Z
---

RCA of the 2026-08-07/08 `test-5700.200x` campaign on tb504 (IE520), plus the 2026-08-10 fix-and-
rerun. **No product defects found.** Fixes live in `copilot/` (staging) and `copilot/run-20260810/`.

**Run from `copilot/run-20260810/` via `launch.sh`, never from `copilot/`** — the framework writes
its logs into CWD and OVERWRITES them, which would destroy bidhanc's campaign logs (the evidence
base). His run dir was renamed to `/home/bidhanc/5700_bootloader_x220` on 2026-08-10; he is active.

**MUST RUN AS ROOT.** `ATTestBox.Eth` reads `/etc/NetworkManager/system-connections/ethN.nmconnection`
(0600 root:root). `ConfigParser.read()` **ignores an unreadable file without raising**, so as a normal
user the branch finds no `[ipv4]` section but still sets `loadFromCommand=False`, skipping the
`ip addr show` fallback that would have worked. Result: `ipv4addr=''` → `init_eth()` returns None →
`Setup.py` prints **"tb eth port eth1 not found"** and `sys.exit(2)`, while eth1 is up the whole time.

**A. `__set_swi_boot_from_media_via_bootrom()` sent the file SIZE as the menu index.**
`if filename in line: number = line.split()[0][:-1]` — the bootloader prints the raw filesystem
listing *before* the numbered menu, so it grabbed the size: `"41015155"[:-1]` → `4101515`, typed at a
prompt offering `(1-1, 0 to cancel)`. Slicing never raises, so `except (ValueError, IndexError)` was
DEAD CODE. Worse: both releases are the same size, so it returned the *same* wrong index whichever
file was asked for, and "succeeded" on truncated output. FIXED by reuse — anchor on
`x.strip().endswith(':{}'.format(filename))` (menu line has a colon before the name, the raw listing
has whitespace, so they cannot be confused). Verified 4/4 by replay + on hardware.

**A2. `KEYWORD_SAVING_SETTINGS = 'Saving settings... Complete'` never matches — and A MASKED IT.**
The device interleaves SPI progress between the halves. So `bootSet` was cleared even though the
boot source HAD saved, every retry was burned, and it reported "Problem occured setting <swi> to
boot <file> from <media> media". Nobody ever saw this because with bug A the selection never
succeeded. **Fixing one bug exposes the next — per-cause case counts always understate the work.**

**B. NOT "gate-string rot" — IE520 OUTPUT DIVERGENCE. Corrected 2026-08-12.** `"Verifying release"`
appears in ZERO IE520 device output; the device says `Verifying Hash Integrity ... sha1+ OK`. Fixed
via `BOOT_MARKERS` + `wait_for_release_boot()` in library_5700 — **but that fix is an accommodation,
not a repair.** x230v2 emits `Verifying release... OK` on **215 device lines** and passes all seven of
these cases (see [[x230v2-5700-control-corpus]]). The string is live everywhere else; the IE520 has no
AT release-verification stage and exposes raw U-Boot/FIT output instead. **This is a product question,
and 8 of the 2026-08-11 passes are passes against different output.** Same for `Saving settings...
Complete` (A2) and `Restoring default settings... Complete` — contiguous on x230v2, split by
`Saving Environment to SPIFlash...` (0 on x230v2, 36 on IE520) only on the IE520.

Three traps: (1) grep is misleading — the framework logs its own strList, so the dead string appears
in logs as OUR text; (2) **the console read splits strings mid-token** (`... sha1<EOS>` then `+ OK`),
so even the CORRECT literal is a coin flip — gate on short atomic markers, and always pass an explicit
waitTime; (3) **`grep` treats `swi_a_*.log` as BINARY — use `-a` or you get 0 hits and read it as
absence.**

**2026-08-12 — A/A2 are FIXED on the newer "pauld" bootloader, B is NOT.** Tested live on tb470 u4.
The file-selection listing is now clean (no raw dump, so even the ORIGINAL buggy parse would work),
and `Saving settings... Complete` / `Restoring default settings... Complete` are both contiguous with
zero SPI-flash interleave. But **`Verifying release` is still never emitted — that window is now
SILENT**, and `BOOT_MARKERS` loses 3 of its 4 anchors there (only `login:` survives). See
[[x230v2-5700-control-corpus]]. **Always check `show system` → `Bootloader version :` before applying
anything here** — `9.1.0` and `pauld` behave differently at every one of these points.

**Erase cost is 2145 s, MEASURED — do not extrapolate.** Level 2→1 = 2143 s, Level 3→1 = 2150 s
(agree within 7 s, so reproducible not load-dependent). An earlier ~1700 s estimate came from
extrapolating the "n/50 blocks" counter linearly from two TIMED-OUT runs; the operation runs longer
than linear. Budget is now 3000 s. The original 780 s covered 36%, so the DUT was power-cycled
mid-erase and the level never cleared — that is why tb504 sat at Level 2 and locked out 2002/3/5.

**Three framework copies on tb504 all differ** (`/home/st-art/framework`, `/home/bidhanc/framework`,
and bidhanc's run-dir copy). Only the run-dir one reproduces the campaign. `1800` was refactored to
`DEFAULT_COMMAND_WAIT = 1800` — same value, so the timeout finding holds. **`ATPublisher` only fires
if `.atpylib_publisher.json` exists in CWD** — absent, so nothing reaches the shared results DB.

**False-pass shape worth reusing:** AWP2684 passed 12 s after power-on because `if not booting:`
passed UNCONDITIONALLY, and `not booting` is also what you get when the DUT never reached the menu.
The "did we actually try?" guard sat on the other branch. Any pass predicated on absence-of-evidence
needs positive evidence attached.

**The framework MANUFACTURES failures on the abort path.** `_post_tear_down()` is gated by
`doConfCheck` in `__run`, but `__handle_exception_in_test_run()` calls it UNCONDITIONALLY. So a case
built as `TestCase_N(confCheck=False)` — which 5700.2005 does for cases 2-8 because they erase flash
on purpose — never ran `_save_configs`, yet on any exception still tried to restore and compare a
config that was never saved. That turned 2005.3's ONE real failure into THREE. Patched to keep the
restore (deliberate) and skip the compare/failure-reporting when `doConfCheck` is False.

**How to hunt gate-string rot properly:** FIRST check the string against a platform that PASSES
([[x230v2-5700-control-corpus]]) — a gate that is live there is a divergence to escalate, not rot to
patch. Only then build a device-output-only corpus by DROPPING every line
matching `^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d: ` from `swi_a_*.log` — the framework logs its own strLists,
so any other method finds the string as OUR text (see [[checks-must-not-match-their-own-advice]]).
Then test every `strList=[...]` literal against it. Done 2026-08-11 over 74k lines: 35 distinct gates,
27 live, 8 never emitted — and ALL 8 turned out benign: multi-anchor lists with a live alternative
(`Enter IP version` etc. rely on `Please enter an ethernet interface to download from`), dead code
(`setSecurityLevelError` is never called), an UNSUPPORTED case (`Pass 11`, needs NVS), or a platform
split the author documented (`Pass 5` vs the IE520's `Test of DRAM with 5 iterations with 0 errors`).
**Verify a replacement gate against ordering, not just presence** — anchoring on
`Security Settings menu` would have returned TWO LINES before
`The security Level is currently set to ...`, turning a slow pass into a failure.

**STILL OPEN — `Error, no UBI device selected!`** on one-off-boot-from-flash in 2002.110/120.
Pre-existing (7 occurrences in bidhanc's 2002, 8 in ours), so not caused by the fixes. Hypothesis:
downstream of the `Saving settings` bug leaving the default boot source on removable media so UBI is
never attached. Unproven — if it survives a re-run with A2 fixed it becomes a second genuine product
question alongside the diagnostics-menu one.

Results 2026-08-10: **2001** 9/9 PASS (rc=0, matches baseline). **2002** 5 PASS/14 FAIL → **11 PASS/
8 FAIL**, 103→133 assertions, 10 h 10 m → 5 h 31 m. **2005** cases 1-3: 2 PASS/1 FAIL (was 8 cases
registered, only 2 ever reporting).

See [[ie520-bootloader-console-driving]] for the operational half, and
[[legacy-scripts-vs-framework]] — gate strings rot silently.
