---
name: grep-shim-honors-gitignore
description: "TWO ways a search here returns a false zero: the `grep` shim honors .gitignore (use `command grep`), AND a full-tree recursive grep over the testbox_home NFS mount can be reaped as exit 0 / no matches before it finishes — both read as real absence"
metadata:
  type: project
  verified: 2026-09-01
---

`grep` in the Claude Code shell is **not** `/usr/bin/grep`. It is a shell **function** that
execs the `claude` binary as `ugrep` with `-G --ignore-files --hidden -I --exclude-dir=.git …`.
Confirm with `type grep`.

**`--ignore-files` makes it honor `.gitignore`.** So a recursive search into any gitignored
path returns **0 hits**, with exit code 0 and nothing on stderr — indistinguishable from
"the string genuinely is not there".

Measured 2026-08-17 while repairing the relocated venv:

```
grep -rl 'copilot/Test-cases' .venv/       ->     0 files   (WRONG - .venv is gitignored)
grep -rl 'copilot/Test-cases' .venv/bin/   ->    29 files   (explicit path still works)
command grep -rl 'copilot/Test-cases' .venv/ -> 12,209 files (the truth)
```

I reported the 0 as fact before noticing the 29 contradicted it. Naming a subdirectory
explicitly can still match, so the two results disagreeing is the tell.

**How to apply:** use `command grep` whenever searching inside a gitignored tree — `.venv/`,
`node_modules/`, `ask-ck/var/`, `CK_server/debug-log/`, the `secrets.*` files. Prefer it for
any count you are going to *state*, and if two greps of the same string disagree, believe the
one with the explicit path and re-run with `command grep`. Note `git ls-files` has the same
blind spot by design, so "not in git" and "not on disk" are different questions.

This is the same shape as [[silent-degradation-audit-2026-07-30]] — a polite zero standing in
for a real answer — and the reason [[mutate-before-you-claim]] exists: a search that cannot
fail loudly has to be proven against a known-present string before its absence means anything.
Related: [[checks-must-not-match-their-own-advice]].

---

## Second failure mode: a truncated search reported as exit 0 (added 2026-09-01)

`command grep` bypasses the shim — it is genuinely **GNU grep 3.7** — but that is not enough.
A **recursive search of the whole `testbox_home` tree over the NFS mount takes minutes**, and
when it is backgrounded on the harness timeout it can come back **`exit 0` with no matches and
nothing on stderr**. Again indistinguishable from real absence.

Measured 2026-09-01, hunting the serial of a swapped IE520:

```
command grep -ral '264A23061' . "old test runs"   ->  0 hits    (WRONG - reaped early, exit 0)
command grep -ral '264A23061' .                   ->  5 files   (same command, run to completion)
command grep -ac  '264A23061' u4-console.log      ->  1         (direct hit, contradicts the 0)
```

There is **no ignore file at the lab-home root** — this is purely the search not finishing. It
also hid two files a scoped search never reached
(`claude/IE520-testing/automated-bootloader/run-20260810/swi_a_200[12].log`), which carried
material evidence.

**How to apply:** never state an absence from a full-tree recursive grep of `testbox_home`.
**Scope the search** to a directory, or bound it with `--include=`, and prefer several narrow
greps to one wide one. If a wide search reports zero, prove the command against a
known-present string before believing it. Same tell as above: a direct per-file hit that
contradicts a recursive zero means the recursive one is lying.
