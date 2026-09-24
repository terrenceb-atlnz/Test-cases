# bench_probe.py — lives in device-testing

The bench tool lives in the **device-testing** repo. Its name and path are fixed, because this
pointer and that repo's skills name them:

[`claude/device-testing/bench-setup/bench_probe.py`](../../../../device-testing/bench-setup/bench_probe.py)

Since **2026-09-25** it is the ONE bench-state tool for tb470 (it replaced `bench_setup.py`,
`bench_topology.py` and the old 28-command probe). Run ON tb470:

| command | what it does |
| --- | --- |
| `./bench_probe.py run` | read every console (`/dev/u0`–`u6` over pyserial, 7 `show` commands each, raw text saved under `bench-setup/captures/<stamp>/`) → regenerate `bench-setup/bench-state.md` → semantic diff against the deployed `/home/st-art/st-art/configs/tb470.setup`. Exit 0 MATCH / 1 MISMATCH / 2 NEEDS-CHECK. About 2 minutes. |
| `./bench_probe.py apply` | write bench-state.md's ```setup fence to the box (snapshot pair → `backups/`, readback) and refresh **`bench-setup/tb470.setup.current`**, the local copy that `ask-ck/tools/pt_preflight.py` reads. |
| `generate <capture-dir>`, `diff`, `render` | offline steps; run anywhere. |

bench-state.md is generated and carries no prose. The facts no `show` command reveals — a
unit's `swi_` name by serial, the PDU IP and outlets — are hand-entered once in
`bench-setup/tb470.static`.

The copy that used to sit here (a framework-driver probe) was deleted on 2026-09-23 (Terrence's
ruling): it had fallen behind, and bench tooling belongs with the bench. Its history is in this
repo's `git log -- ask-ck/functions/test-composer/bench_probe.py`.
