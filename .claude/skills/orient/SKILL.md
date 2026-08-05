---
name: orient
description: Orient at the start of an Ask-CK session — ground-truth the live repo, read the newest handoff, confirm the invariants, and brief the user on what priorities remain. Use at session start, or whenever asked "where are we", "what's pending", "what priorities remain", or to get up to speed before touching the project. Pairs with /wrap, which closes the loop at the end of the session.
---

# Orient (Ask-CK)

Establish current state from **reality, not memory** — then brief the user and wait for direction.

**Design rule for this file:** every fact that can rot is a *lookup*, not a literal. Do not
add file lists, memory names, test counts, or commit hashes here. Globs and greps only. The
prompt this skill replaced named four memory files; all four had ceased to exist.

---

## 1. Ground-truth first (cheap, deterministic, before any reading)

Run this. It is fast, and it starts the gate in the background so it finishes while you read.

```bash
git fetch --quiet origin
git status -sb                      # -sb shows ahead/behind: another stream commits to main
git log --oneline -12
ls -la ask-ck/var/ck.db             # must exist, must be LFS-tracked, must not be gitignored
git check-ignore -v ask-ck/var/ck.db && echo "!! ck.db IS GITIGNORED — invariant violated"
```

Then launch the full gate **in the background** and keep reading while it runs:

```bash
./tool/run_tests.sh                 # both guards + backend pytest + frontend vitest
```

Note the pass counts it prints. Establishing baseline-green *now* is what makes a failure
found later in the session attributable to this session. Playwright E2E is deliberately not
in the gate — do not run it as part of orienting.

**Never start the real server just to look around** — it writes `ask-ck/var/ck.db`, the
permanent source of truth. Use `tool/run_scratch_server.sh` for any exploratory or test
traffic. Start the real one (`./run.sh --bg`, `--restart`, `--stop`) only when the user
actually wants the running app; then `/health` should report `is_permanent_db: true`.

## 2. Read newest-first, with a budget

Orientation is a *briefing*, not a full re-read of the project's history. Following the old
prompt literally cost ~11,000 lines of prose before any work began, and the first ~50 lines
of the handoff log carried most of the value. Budget accordingly:

| Read | How much | Why |
|---|---|---|
| `ask-ck/objective-drafting/PROGRESS.md` | **`head -60`** — the newest entry only | Highest value per line in the repo. Newest entries are at the TOP and are current truth. Read further only where that entry points forward. |
| `SESSION_STATE.md` | the **last** `## Session Close / Handoff` entry (`tail`) | Long-form history; the tail is the only current part. Watch for "superseded by …" notes that make older docs wrong. |
| `README.md` | the **feature-status table** only | Whole-file read is not warranted at orientation. |
| `ask-ck/CK-main/SERVER-README.md` | **headings first** (`grep -n '^#'`), then only the sections today's task touches | This is the primary technical reference and the deepest well in the repo — read it *on demand*, not cover to cover. |

Skip the `CK_server/README.md` and `CK_server/static/js/README.md` stubs while orienting; the
first is explicitly a pointer file. Read the JS one when changing front-end module structure.

## 3. Deferred reads — rules, not steps

Do **not** read these upfront. At orientation the task is still unknown, so "the relevant
plan" cannot be resolved; the plans total several thousand lines and reading them all is
waste. Instead treat these as standing rules for later in the session:

- **Before touching any subsystem, read its plan's status header first.** Find plans by glob,
  never by a list written down here: `ls ask-ck/*/PLAN-*.md`. Settled decisions in a status
  header are settled — do not re-litigate them.
- **Before changing a prompt, a gate or a rule, read its DESIGN DOCUMENT — not just its code
  and tests.** A plan says what was done; a design doc says what the thing is *for*, and only
  the second can tell you a rule is wrong. On 2026-08-05 the steps prompt was reviewed rule by
  rule against the implementation, signed off, and turned out to contain three rules
  contradicting `OBJECTIVE_DRAFTING_PROCESS.md` — every check performed was
  consistency-with-code, none was conformance-with-design. The wizard's authority is that doc
  (Steps 1–2); the PyTest Creator's is `ask-ck/pytest-create/PLAN-pytest-*.md` plus
  `TOPOLOGY-PROFILES.md`. A doc banner that disclaims *data-access paths* is not disclaiming
  the method — read what it actually scopes. See memories `pipeline-layer-contract` and
  `autonomous-judgement-divergence`.
- **Before any work that touches lab hardware** — SSH to a testbox, driving a switch console,
  running a framework or legacy corpus script against a real DUT — read `TESTBOX-ACCESS.md`
  in full. It carries environment facts that cost real time to rediscover (the
  `SSH_AUTH_SOCK` gotcha, why a `.setup` console list cannot be trusted, the fix set every
  legacy script needs against the current framework).
- `/home/st-art/framework` is **read-only**. Never write or edit it; copy locally to change
  anything. `tool/guard_framework_readonly.py` enforces this and is part of the gate.

## 4. Memory — read the index, never a written-down list

```bash
ls .claude/memory/*.md      # the directory IS the list
```

Memories live **in the repo** at `.claude/memory/` as of 2026-07-30;
`~/.claude/projects/*/memory` are symlinks to it. Before that there were **two** stores keyed on
the session's launch directory — 38 memories under the `…-copilot-Test-cases` slug and 4 hardware
ones under `…-testbox-home` — and each was invisible to sessions started in the other directory.
That, not stale names, is what produced most "I can't find that memory" reports. If `ls` above
shows nothing, the symlinks are gone, not the memories: re-point
`~/.claude/projects/<slug>/memory` at `<repo>/.claude/memory`.

Read `MEMORY.md` (the index) and then the individual files whose one-line hooks look relevant
to today's work. **Any memory name hardcoded in any document — including this one — is a hint,
not a guarantee.** Verify before reporting a memory as missing, and before acting on one:
a memory reflects what was true when it was written, so if it names a file, function or flag,
confirm that still exists.

## 5. Confirm the invariants (flag immediately if any is violated)

1. **`ask-ck/var/ck.db` is the permanent single source of truth** — built once, shipped via
   Git LFS, **not** gitignored, **not** rebuildable. No courier/source JSON files, no corpus
   APIs, no re-fetch.
2. **The running server reads corpora only from `ck.db`** (`db.py`); zero runtime JSON.
   Evidence: `tool/guard_db_only.py` (in the gate).
3. **The testbox framework tree is read-only.** Evidence:
   `tool/guard_framework_readonly.py` (in the gate).
4. **The org vLLM is the one live external dependency, and it is core function** — not an
   inter-dependency to be removed. These are *reasoning* models (they emit reasoning content
   before content). The embedding model is bundled and loads offline.

Working rule that follows from #1: tests, smoke checks and E2E must **not** write the
permanent `ck.db`. `md5`/`mtime` cannot detect a write to it (WAL) — the gate's
`tests/test_db_isolation.py` is the WAL-safe authority, so a green gate is the evidence.
Real user traffic *should* dirty `ck.db`; that is not a violation.

## 6. Brief the user, then stop

Keep it dense and skimmable. Use clickable relative paths (`[PROGRESS.md](ask-ck/objective-drafting/PROGRESS.md#L12)`).

- **(a) Where it stands** — 4–6 concrete sentences from the newest handoff entry.
- **(b) What remains, ranked**, grouped as: *active thread — pick up here* / *blocked or
  needs a decision from the user* / *deferred by choice* / *hygiene*. One line each: what
  remains, the `file:line` to start from, and the blocker if there is one. Say so explicitly
  if a group is empty. **Verify before you list** — docs go stale in both directions, so
  check a claimed-open item against the code and `git log` before reporting it as open.
- **(c) Invariants** — each of the four above, held or at risk, with the evidence.
- **(d) Today's task** — only if the user has already stated one. If they have not, say
  "awaiting direction" and do **not** invent an agenda. (The prompt this replaced asked for
  this while also saying "then wait for me to direct the work" — unanswerable by design.)
- **(e) Anything uncommitted, or any drift from `origin/main`** — the tree is shared with
  another stream, so `git status` has a short shelf life. Re-check it before claiming clean.

Then wait. Close the loop at the end of the session with `/wrap`.
