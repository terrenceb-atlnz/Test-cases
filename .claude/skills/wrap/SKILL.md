---
name: wrap
description: Close out an Ask-CK session — reconcile the docs against what actually shipped, sweep for staleness, confirm the gate and invariants, then commit and push to main. Use at the end of a work session, or when asked to "sync the docs", "wrap up", or "close the loop". Replaces pasting END_OF_SESSION_PROMPT.md.
---

# Wrap (Ask-CK)

Make the documentation match reality, then commit and push. Pairs with `/orient`, which reads
these same locations at the start of a session — same doc map both directions, so the docs are
the trusted handoff between sessions, never memory.

**Design rule for this file:** every fact that can rot is a *lookup*, not a literal. No file
lists, memory names, test counts or hashes written down here — globs and greps only.

---

## 1. Establish what actually shipped (before writing a word)

```bash
git status -sb                      # -sb shows drift from origin; the tree is shared
git log --oneline origin/main..HEAD # this session's commits, if any are already local
git diff --stat                     # uncommitted work
./tool/run_tests.sh                 # both guards + backend pytest + frontend vitest
```

Document from this, not from recollection of what you intended. The gate must be green before
you commit; note the pass counts so drift is visible next session.

A green gate is also the evidence that `ask-ck/var/ck.db` was not dirtied by tests —
`md5`/`mtime` cannot see a write to it (WAL), and `tests/test_db_isolation.py` is the
WAL-safe authority. Real user traffic legitimately dirties `ck.db`; tests, smoke checks and
E2E must not.

## 2. Living reference docs — edit in place to describe the CURRENT system

- `README.md` — repo entry: setup, getting started, **feature-status table**, data-layer
  overview. Update the table and anything whose setup or behaviour changed.
- `ask-ck/CK-main/SERVER-README.md` — the deep technical reference (architecture, data layer,
  endpoints, admin panel, LLM config, workflow). Most substantive changes land here.
- `ask-ck/CK-main/CK_server/README.md` — thin pointer stub; touch only if the pointers moved.
- `ask-ck/CK-main/CK_server/static/js/README.md` — front-end ES-module conventions; update if
  the JS module structure changed.
- `TESTBOX-ACCESS.md` — update if this session learned anything non-obvious about reaching or
  driving lab hardware, or about running legacy scripts against the current framework.

## 3. Dated logs — APPEND, never rewrite

- `ask-ck/objective-drafting/PROGRESS.md` — add a `## Latest session (YYYY-MM-DD…)` entry at
  the **top**. This is the file the next session reads first, so it carries the real weight:
  what shipped, what is pending, what is blocked and on what, and where to pick up.
- `SESSION_STATE.md` — add a `## Session Close / Handoff (YYYY-MM-DD…)` entry at the **end**.
  If an older entry is now wrong, add a one-line "superseded by …" note pointing at the new
  entry — do **not** edit the old text. The log's value is that it is frozen.

Convert relative dates to absolute ("last Tuesday" is useless in three months).

## 4. Plans — update status headers, don't rewrite history

Find them by glob, never by a list written down here:

```bash
ls ask-ck/*/PLAN-*.md
```

If a plan advanced or a decision changed, update its **status header** (mark phases done, add
a superseded / final-state note). Leave the historical body intact — add banners rather than
deleting. Any doc describing a retired pipeline or deleted file must carry a
"⚠ Historical / superseded" banner pointing at the current source of truth (`ask-ck/var/ck.db`).

## 5. Memory — reconcile only durable facts

```bash
ls ~/.claude/projects/*Test-cases/memory/*.md      # the directory IS the list
```

Update a memory file if this session changed a standing decision, finished pending work, or
established a new constraint. Keep `MEMORY.md` to one pointer line per memory — never put
memory content in the index. Delete memories that turned out to be wrong.

Don't record what the repo already records (code structure, past fixes, git history). Don't
record what only mattered inside this conversation.

## 6. Staleness sweep

Grep tracked `.md` plus `setup.sh` for claims that contradict the invariants — that the server
reads JSON at runtime, that the DB is rebuildable or gitignored, or a reference to a deleted
courier file with no historical marker. Each hit must be either corrected (in a living
reference doc) or clearly flagged historical (in a log or plan doc).

**When a check greps for a bad pattern, it will find that pattern in the text forbidding it.**
Use the `tests/_prose.py` helpers (`code_lines` / `flat` / `code_fences`) rather than a raw
grep, so advice about a pattern doesn't register as the pattern.

**Never write a hardcoded list into a doc that a glob could produce.** The start-of-session
prompt this skill's counterpart replaced named four memory files "as at" a date; all four had
ceased to exist, while the four it declared dead were all still live. A list in prose is a
cache with no invalidation.

## 7. Commit and push

```bash
git add <explicit paths>            # never `git add -A` — the tree is shared with another stream
git commit                          # clear message; conventional prefix (docs:/feat:/fix:/test:)
git push origin main
```

- Stage **explicit paths**. Another stream commits to `main` concurrently, so a blanket add can
  capture work that isn't yours.
- Push is expected as part of wrapping up, not a separate ask.
- If push fails on auth from a Mac-attached SSH session, `SSH_AUTH_SOCK` needs to point at the
  keyring agent — see `TESTBOX-ACCESS.md`.

## 8. Report back

Show the diff summary, the gate result, confirm the four invariants still hold
(`ck.db` permanent single source / server reads corpora only from `ck.db` / framework tree
read-only / org vLLM is the one live external dep), and give the commit + push result. State
plainly anything you left undone.
