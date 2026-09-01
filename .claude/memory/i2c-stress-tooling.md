---
name: i2c-stress-tooling
description: ~/i2c-stress/ holds two validated IE520 i2c stress scripts (standalone pyserial + thin framework wrapper); smoke-tested clean on tb470 2026-08-26; 'show platform port' on a stacked pair = ~36 s / 344 KB, so 300 pairs ≈ 3.1 h, NOT the campaign's 2 s/iter figure
metadata:
  type: project
---

`~/i2c-stress/` (testbox_home root) holds the re-created i2c stress tooling from the
2026-08-19/20 lockup campaign (`~/i2c_evidence.log` is the full campaign record;
[[tb470-topology-and-setup]] has the bench):

- `i2c_stress.py` — standalone (pyserial only, no framework, no .setup; `--baud/--user/--password`)
- `i2c_stress_fw.py` — thin wrapper over `ATSwitch.Switch(devicePath)`, needs `PYTHONPATH=/home/st-art`, no .setup, no sudo
- Both: interleave `show platform port` + `show system pluggable diagnostics` N times each
  (default 300), stop-on-first-lock, hands-off recovery (IE520 watchdog self-resets ~42 s
  after a lock), logs to CWD → always run from a fresh dated dir under `~/i2c-stress/runs/`.

**Both smoke-tested clean on tb470 2026-08-26** (`runs/2026-08-26-tb470-smoke/`), u4+u5
stacked, 19 pluggables, faulty AT-SPTXc ...006 quarantined (absent from inventory).

**Why:** the boss wants i2c stress runs on other IE520 units to trigger fails; these are the
portable reproducer harness. The proven single-command reproducer is `show platform port`
(+2.6 s lock with ...006 fitted); the DDM Vcc census in the baseline doubles as the field
screen (faulty module read Vcc 3.4167 V > 3.4000 High threshold).

**How to apply:** timing math on a STACKED pair: `show platform port` covers 56 ports →
344 KB ≈ 36 s at 115200 (serial transfer dominates), so 300 pairs ≈ **3.1 h per console** —
never budget from the campaign's ~2 s per-unit figure. Framework variant drops an extra
`swi_noname_4.log` at `Switch()` construction despite per-run log names (cosmetic). A full
300-iteration campaign was proposed but NOT yet run as of 2026-08-26 — Terrence's call.
