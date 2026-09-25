---
name: framework-run-always-noupdate
description: DEFAULT for every run-script Ask-CK executes on hardware (Terrence 2026-09-25) — pre-load the topology's .cfg on each device and boot it, then run with --noupdate --nodefaultcfg; without them setup resets every device (default.cfg, licence strip, reboot, TFTP .rel copy)
metadata:
  type: feedback
  verified: 2026-09-25
---

**Every framework script Ask-CK runs on a bench is launched as
`sudo -n env PYTHONPATH=/home/st-art python3 <script>.py -s <topology>.setup -v --noupdate --nodefaultcfg`,
on devices already running the topology's own config** (Terrence, 2026-09-25: "We will just do
(a) … record that change as the intended default behavior for any run-script we are executing from
ask-ck"). The topology pairs live in `ask-ck/functions/test-composer/templates/<setup-name>/`: the
`.setup` plus **one `.cfg` per device the `.setup` declares, and ONE `.cfg` shared by every
member of a stack** (Terrence, 2026-09-25; his `setup-a/a.setup` + `a.cfg` files are examples, not
the whole convention). File names: **`<setup>.<device>.cfg`**, the device by its `.setup` name —
`a.swi_b.cfg`, `a.swi_f.cfg`, and `a.stk_a.cfg` for the whole stack (Terrence: "a cleaner filename
format. do that"). Bench execution is owned by the
device-testing `bench-runner` agent (building 2026-09-25; linked into this repo's
`.claude/agents/`), which runs its pre-run gate (`fuser`, bare-CR shell check, `bench_probe.py run`
= MATCH) before launching.

**Why:** without the flags, `ATTestSet` setup (`__pre_configure` → `_DefaultConfigThread`) resets
every device it initialises: generates `default.cfg` in Python and echoes it into flash through
`start-shell`, `boot conf default.cfg`, loads/unloads licences (only when the script's `FEATURES`
is non-empty — the Ask-CK frame's `['ALL']` strips every licence not in
`/home/st-art/feature_license_keys.env` except the keep-list `ACCESS, VCSPLUS, AT-FL-CF9-VCSPL,
No-License-Lock`, compared case-sensitively, so a lowercase `access` is removed), reboots, then
TFTP-copies `<platform>-<host>.rel` into flash as the boot image. On 2026-09-25 that reset tb470's
four devices, stripped NZ/FULL/access, and hung on the TFTP copy (`/tftproot` is tmpfs, empty after
tb470's reboot) after deleting crash files. `--noupdate` skips only the copy; `--nodefaultcfg`
skips the whole reset (no default.cfg, no licences, no reboot, no power cycle). The framework still
runs `configure()`, saves the running config as `<hostname>.cfg` via CLI (`copy run` + `boot
conf`) and tear-down returns to it.

**How to apply:** pre-run, load each device's topology `.cfg` into flash under its own name, set
`boot config-file`, reboot, diff running vs file (method proven 2026-09-25: shell `echo` write +
md5 where ACCESS/FULL gives `start-shell`, CLI `copy running-config` otherwise). Post-run, set the
boot config back to the topology file and diff. Never pass `-n/--noconf` unless the run must also
skip `configure()` and tear-down. Related: [[framework-unsupported-needs-a-failure]],
[[legacy-scripts-vs-framework]], [[testbox-console-access]], [[console-secret-redaction-wraps]].
