# Ask CK / AWPTCM test-case workbench

Server-backed workbench that turns sparse manual test cases into refined Zephyr cases and then
into runnable Allied Telesis `framework` test scripts. FastAPI backend at
`ask-ck/CK-main/CK_server/`, browser-native ES modules in `static/js/`, all corpora in SQLite.

**Start a session with `/orient`** — it ground-truths the repo, reads the newest handoff, and
briefs you. **End with `/wrap`.** Both live in `.claude/skills/`. Don't reimplement what they do.

## Invariants — flag immediately if any is violated

1. **`ask-ck/var/ck.db` is the permanent single source of truth.** Built once, shipped via Git
   LFS, **not** gitignored, **not** rebuildable. No courier JSON, no corpus APIs, no re-fetch.
2. **The server reads corpora only from `ck.db`** — zero runtime JSON. Guard:
   `tool/guard_db_only.py`.
3. **`/home/st-art/framework` is read-only.** Never write, edit or redirect into it; copy to a
   local staging path to change anything. Guard: `tool/guard_framework_readonly.py`.
4. **The org vLLM is the one live external dependency and it is core function**, not an
   inter-dependency to remove. Its models are *reasoning* models. Embeddings are bundled and
   load offline.

Tests, smoke checks and E2E must **not** write the permanent `ck.db` — use
`tool/run_scratch_server.sh`. `md5`/`mtime` cannot detect a write to it (WAL);
`tests/test_db_isolation.py` is the authority. Real user traffic *should* dirty it.

## The gate

```bash
./tool/run_tests.sh        # both guards + backend pytest + frontend vitest
```

Run it before and after a change. Playwright E2E (`npm run e2e`) is deliberately **not** in the
gate. There is no CI runner.

## Before touching lab hardware

Read **`TESTBOX-ACCESS.md`** in full first — SSH from this host needs an explicit
`SSH_AUTH_SOCK`, a `.setup` file is declarative and may not match the bench, and legacy corpus
scripts need a known fix set (including gate strings that no longer exist in the software).

## Memory

Memories live **in this repo** at `.claude/memory/`, with `MEMORY.md` as the index.
`~/.claude/projects/*/memory` are **symlinks** to it, so the same set loads whichever directory
the session starts in — before 2026-07-30 there were two stores keyed on the launch directory
and each was invisible to the other. Consequences:

- Memory edits show up in `git status`; `/wrap` commits them. That is intended.
- **Never put a credential in a memory** — this directory is pushed. `secrets.md` (gitignored)
  is where lab/API credentials belong.
- If `~/.claude` is ever wiped, re-create the two symlinks rather than re-writing memories.

Any memory name written down in a document is a **hint, not a guarantee** — verify before acting
on one, and before reporting it missing.

## Working notes

`ask-ck/objective-drafting/PROGRESS.md` is the highest-value file in the repo (newest entry at
the **top**). `SESSION_STATE.md` is long-form history; only its tail is current. Plans are
`ask-ck/*/PLAN-*.md` — read a plan's status header before touching its subsystem, and treat
settled decisions there as settled. This tree is shared with a concurrent stream, so re-check
`git status` before claiming it clean, and stage explicit paths.
