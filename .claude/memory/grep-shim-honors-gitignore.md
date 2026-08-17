---
name: grep-shim-honors-gitignore
description: "`grep` in this shell is a function wrapping ugrep --ignore-files, so it silently skips .gitignored paths (.venv, node_modules, ask-ck/var/) — zero hits reads as real absence; use `command grep` to bypass"
metadata:
  type: project
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
