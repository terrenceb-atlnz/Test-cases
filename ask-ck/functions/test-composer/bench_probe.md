# bench_probe.py — moved

The bench probe (reads a testbox's real state through the framework's own console driver,
read-only apart from `--assign-ip`) lives in the **device-testing** repo:

[`claude/device-testing/bench-setup/bench_probe.py`](../../../../device-testing/bench-setup/bench_probe.py)

The copy that used to sit here was deleted on 2026-09-23 (Terrence's ruling): it had fallen
behind the device-testing copy, and bench tooling belongs with the bench. Its history is in
this repo's `git log -- ask-ck/functions/test-composer/bench_probe.py`.
