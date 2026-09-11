# Ask CK — Orientation for a Code Reviewer

**Scope of your review:** the database (`ask-ck/var/ck.db`) and every Python module that
touches it as part of an Ask CK function.

**Audience:** a developer new to this codebase who will read it, run it locally, and give
feedback. You are not expected to ship changes yet.

> **Proprietary and Confidential.** This repository and everything in it is the exclusive
> property of the copyright holder. No license is granted. Do not copy, redistribute, or share
> any part of it — including this document — outside the team. See [`COPYRIGHT`](COPYRIGHT).

---

## 1. What the system is for

Allied Telesis maintains a large body of **manual test cases** for network switches. Many are
sparse: a title and a few lines, with no clear statement of what the test is actually meant to
prove. Ask CK exists to fix that, in two stages:

1. **Enrich a manual test case** into a *refined case* — a declarative objective plus
   reviewable, Zephyr-ready test steps — by mining two historical sources for evidence.
2. **Turn a refined case into a runnable test script** for Allied Telesis' in-house `framework`
   automation, then run it on real switch hardware.

A human confirms at every step. The tool proposes; it never silently advances.

### Glossary — read this before the code

| Term | What it means here |
|---|---|
| **AWPTCM** | The manual test-case program this project serves. Case keys look like `AWPTCM-T33233`. |
| **Zephyr** | The live test-management system (Zephyr Scale) holding the manual cases. The system of record. |
| **TestLink** | A *historical* test system, now read-only to us. Detailed human-written cases (`AWP-*`) mined for context. |
| **ATPyLib / ART** | The existing automated test suites. Used to work out what automation already covers. |
| **`framework`** | Allied Telesis' Python test-automation framework that generated scripts run under. Lives at `/home/st-art/framework` and is **read-only to us**. |
| **DUT** | Device Under Test — the switch being tested. |
| **testbox** | A lab machine (e.g. `tb470`) cabled to switches, which executes test scripts. |
| **refined case** | The output bundle: `traceability.md` + `zephyr_payload.json`. A case is "Complete" once it exists. |
| **AlliedWare Plus** | The switch operating system. Its CLI output is what tests assert against. |

**The two tools** you will see referenced constantly:

- **Objective / Test Case Generator** (the "wizard") — stage 1 above. Six gated steps.
- **PyTest Creator** — stage 2. Seven gated steps, ending in execution on a testbox.

---

## 2. The one rule that matters most

**`ask-ck/var/ck.db` is a permanent artefact. It was built once, on 2026-07-20, and it cannot
be rebuilt.**

The source files it was built from have been deleted. `tool/build_db.py` still exists purely as
provenance and **refuses to run**. The database is committed to the repository via Git LFS —
all 439 MB of it — so a fresh clone gets a complete, populated, semantically-searchable
database with no build step.

This has consequences that will otherwise surprise you:

- **There is no migration framework and no runtime DDL.** Adding a column is not a small
  change; it would be the first in-place schema mutation of the permanent database. When you
  find something that "should obviously be a table", that is why it isn't — see §7.
- **Tests must never write it.** They run against an isolated copy. If you are running the
  server for experimentation, use `tool/run_scratch_server.sh`, never the real thing.
- **You cannot detect a write by checking the file's hash or mtime.** See §3.4. This is not a
  theoretical concern — a mutating test once deleted a real session row while `md5sum`
  reported the file unchanged.

### The four invariants

Flag it immediately if you find any of these violated. Two are enforced by automated guards
that run in the test gate.

1. **`ck.db` is the permanent single source of truth** — built once, shipped via Git LFS, not
   gitignored, not rebuildable.
2. **The server reads corpora only from `ck.db`** — zero runtime JSON. Guard:
   `tool/guard_db_only.py`.
3. **`/home/st-art/framework` is read-only** — never write, edit, or redirect into it. Guard:
   `tool/guard_framework_readonly.py`.
4. **The organisation's vLLM endpoint is the one live external dependency, and it is core
   function** — not a dependency to be engineered away. The embedding model, by contrast, is
   bundled and loads fully offline.

---

## 3. The database

### 3.1 It looks like 68 tables. It is really 13.

```
13  content tables      the actual data
30  FTS5 shadow tables   6 full-text indexes x 5 internal tables each
25  sqlite-vec shadows   5 vector indexes x 5 internal tables each
```

Only the 13 are yours to reason about. The rest are machinery that SQLite and the `sqlite-vec`
extension manage themselves — you never write them directly, and their contents are not
meaningful to read.

### 3.2 The 13 content tables

**The three corpora** — the evidence the tool reasons over. All read-only in practice:

| Table | Rows | What it is |
|---|---|---|
| `zephyr_cases` | 45,427 | Every Zephyr case. `is_target=1` marks the ~410 AWPTCM cases this project is actually working on. |
| `testlink_cases` | 21,620 | Historical TestLink cases, mined for context and overlap. |
| `atp_tests` | 10,157 | Automated-suite tests, enriched with a log-derived description of what each suite tests *for*. |

**The script corpus** — used by PyTest Creator to reuse existing automation:

| Table | Rows | What it is |
|---|---|---|
| `scripts` | 830 | Indexed `framework` test scripts, including full `source_text`. |
| `script_chunks` | 5,782 | Individual functions/classes carved out of those scripts, with exact line ranges. |

**The CLI reference** — harvested from the AlliedWare Plus documentation:

| Table | Rows | What it is |
|---|---|---|
| `cli_commands` | 6,323 | Real command syntax, examples, and — critically — **real sample output**. |
| `cli_command_products` | 68,301 | Which products support which command page. |

**Project working data:**

| Table | Rows | What it is |
|---|---|---|
| `candidates` | 410 | Per-case candidate matches, as a JSON payload. |
| `decisions` | 410 | Which candidate was chosen for a case, with rationale. |
| `sessions` | 51 | **The only table written at runtime.** One row per in-progress case. |
| `embeddings_meta` | 83,816 | Bookkeeping for the vectors: which row, which model, what content hash. |
| `meta` | 28 | Build provenance — when it was built, from what, with which embedding model. |
| `json_docs` | 2 | A small key/value escape hatch for whole JSON documents. |

### 3.3 Three ways to search, and why there are three

This is the most interesting part of the data layer.

- **Keyword (FTS5).** SQLite's built-in full-text search. Fast, exact, and blind to meaning —
  a search for "link negotiation" will not find a case that says "autoneg".
- **Semantic (sqlite-vec).** Every corpus row was embedded into a 384-dimensional vector using
  `sentence-transformers/all-MiniLM-L6-v2`; 83,816 vectors in total. Nearest-neighbour search
  finds conceptually similar text regardless of wording. The model is **bundled and loads with
  no network access** — see invariant 4.
- **Hybrid.** Both, with the results merged and re-scored. `search_*_hybrid` in `db.py`.

A shared relevance scorer (`db._relevance_score`) weights title matches above body matches and
adds term-frequency, whole-word, phrase, and coverage bonuses. It is deliberately one
implementation used by all three search paths — an earlier version had per-caller copies that
drifted.

### 3.4 Two gotchas that will bite you

**The database is in WAL mode.** A committed write can land in `ck.db-wal` and leave the main
file's bytes and mtime untouched for a long time. So `md5sum ck.db` proving "unchanged" proves
nothing. The WAL-safe check is `tool/ckdb_signature.py`, which asks SQLite itself and therefore
reads main + WAL together. `tests/test_db_isolation.py` is the authority in the test suite.

**Opening the vector tables requires loading the extension.** If you open `ck.db` with plain
`sqlite3` and query `vec_zephyr`, you get `no such module: vec0` — which looks like corruption
and is not. `db.get_connection()` loads `sqlite-vec` for you. To poke around by hand, do it
read-only and expect the `vec_*` tables to be unreadable without the extension:

```bash
PYTHONNOUSERSITE=1 .venv/bin/python -c "
import sqlite3
c = sqlite3.connect('file:ask-ck/var/ck.db?mode=ro', uri=True)   # ?mode=ro — always
print(c.execute('select count(*) from zephyr_cases').fetchone())
"
```

**Also note:** the `count:*` keys in the `meta` table are *build-time* provenance, not live
counts. `meta` says 35 sessions; there are 51 today. That is correct behaviour, not drift.

---

## 4. The code that touches the database

### 4.1 One module owns SQL

**`CK_server/db.py` (1,135 lines) is the only module in the entire server that opens a SQLite
connection.** Everything else goes through its API. If you find a second module importing
`sqlite3`, that is a finding.

Its public surface is 40 functions (plus 18 private helpers), in four groups:

| Group | Examples | Notes |
|---|---|---|
| Fetch by id | `get_case`, `get_testlink_case`, `get_script`, `get_script_chunks` | Straight reads. |
| Search | `search_zephyr`, `search_atp`, `search_code`, `search_*_hybrid` | The three modes from §3.3. |
| Sessions | `save_session`, `load_session`, `delete_session`, `list_session_progress` | The only writes. |
| Health / meta | `startup_check`, `counts`, `embeddings_count`, `get_meta` | `startup_check` is what `/health` reports. |

### 4.2 The modules in your review scope

Everything below reaches the database as part of an Ask CK function:

| Module | Lines | Role |
|---|---|---|
| `db.py` | 1,135 | **Sole SQL owner.** Connections, FTS5, vectors, sessions. Start here. |
| `routers/wizard/reviews.py` | 910 | Wizard steps 1–4: load a case, search/suggest candidates, confirm selections. 10 endpoints. |
| `routers/wizard/synthesis.py` | 341 | Wizard steps 5–6: LLM synthesis of objective + steps. 6 endpoints. |
| `routers/wizard/export.py` | 536 | Writes the refined-case bundle to disk; pushes to live Zephyr. 2 endpoints. |
| `routers/wizard/config.py` | 253 | Workspace LLM login and per-session config. 7 endpoints. |
| `routers/pytest_create.py` | 3,663 | The whole PyTest Creator flow. 27 endpoints. Imports `db as dbx` — see below. |
| `routers/admin.py` | 88 | Hidden admin panel: reset sessions, restart. |
| `session_store.py` | 128 | The in-memory sessions dict and its `ck.db` row. |
| `case_registry.py` | 162 | Which cases exist, which are Complete, which are hidden, how they group. |
| `generator/descriptions.py` | 215 | Builds display text and candidate queries; calls the shared scorer. |
| `generator/gates.py` | 106 | The confirm gates — can this step be synthesized yet? Invalidation of downstream steps. |
| `generator/backfill.py` | 96 | Rehydrates a Complete case from its on-disk bundle. |
| `data.py` | 98 | Thin accessor layer the routers depend on. |
| `llm_config.py` | 140 | Resolves which LLM backend a request uses; persists the workspace login. |
| `locks.py` | 248 | Per-case locking. Read its docstring in full — it is the best-written explanation in the repo. |
| `models.py` | 256 | Pydantic session models. The shape of what gets stored in `sessions.payload`. |

**A trap worth knowing:** `pytest_create.py` imports the data layer as `import db as dbx`,
because several of *its own* functions take a parameter called `db` (a script-database filter).
So grepping the codebase for `db.` will miss all of PyTest Creator's database access. Grep for
`dbx.` too.

### 4.3 How a request actually flows

Loading a case in the wizard, end to end. Read this alongside `load_case` in
`routers/wizard/reviews.py:54` — its docstring is worth your time:

```
browser  ──POST /api/wizard/load_case/AWPTCM-T33233──▶ routers/wizard/reviews.py
                                                         │
                       locks.acquire("wizard", key) ─────┤
                         ├─ not mine → serve a READ-ONLY snapshot and touch NOTHING
                         └─ mine     → continue below
                                                         │
                       data["zephyr_master"].get(key) ──▶│  lazy _DbMap → ck.db: zephyr_cases
                       data["decisions"].get(key) ──────▶│  lazy _DbMap → ck.db: decisions
                       load_persisted(key) ─────────────▶│  db.load_session → ck.db: sessions
                       generator.backfill ──────────────▶│  rehydrate if already Complete
                                                         │
                       db.save_session("wizard", …) ────▶│  ck.db: sessions  ← the only write
                                                         ▼
browser  ◀──────────────────── JSON session state ───────┘
```

Three things in that flow are not obvious and are all deliberate:

**Handlers rarely call `db.*` directly.** They go through `data.py`, whose `_DbMap` is a
**lazy, read-only mapping** — `data["zephyr_master"].get(key)` looks like a dictionary access
but is a SQLite lookup underneath. This keeps ~44 MB of corpora in the database instead of
server RAM. It also means grepping a handler for `db.` will under-report how much database
work it does.

**A lock you don't hold does not produce an error.** If another tab holds the case, you get a
read-only snapshot of the last saved state and the handler deliberately mutates nothing — not
even a hydration write, which would 409 against the holder's lock.

**Loading is deliberately cheap.** No step fetches its candidates here; each review step pulls
its own on demand via `GET /step_candidates/{key}/{step}`. This has bitten the tool twice, both
times because load pre-computed data for a panel the user had not opened: a blocking LLM call
that added ~60s to *every* load, and a bespoke scorer that scanned ~45k rows for 2.7s bare on
the event loop, freezing every concurrent request. If you are tempted to "helpfully" pre-load
something here, that is the history you are arguing with.

Every subsequent step follows the same shape: read corpora, mutate the in-memory session,
persist the whole session blob, return it. **Session writes are whole-blob overwrites** — which
is exactly why `locks.py` exists.

---

## 5. Running it locally

You can run the full server and both tools. You will **not** be able to run PyTest Creator's
step 6 (*Run*), which needs a lab testbox.

```bash
./setup.sh          # idempotent; installs into a repo-local .venv
./run.sh            # then open http://localhost:8000/  (http, NOT https)
```

Then set an LLM backend under **LLM → Configure** — most panels need one.

### The rule for experimenting

```bash
tool/run_scratch_server.sh      # runs on port 8123 against a THROWAWAY copy of ck.db
```

Use this for anything exploratory. Real user traffic legitimately dirties `ck.db` (loading a
case persists a session row) — that is correct. Test and throwaway traffic writing the
permanent, LFS-committed database is not. `/health` reports `db.is_permanent_db` so you can
always tell which database a running server is on.

### The test gate

```bash
./tool/run_tests.sh     # both guards + backend pytest + frontend Vitest
```

Currently 1,060 backend tests and 92 frontend tests, plus the two invariant guards. Run it
before and after any change. There is no CI runner, so this command is the entire safety net.

Note that `setup.sh` installs the **runtime** dependencies only; `pytest` lives in
`requirements-dev.txt`. If the gate tells you pytest is missing, that is why, and it prints the
exact command.

---

## 6. Some history that explains the code

You will read better if you know what this codebase has already been burned by.

- **Silent degradation is the recurring enemy.** The pattern that keeps recurring is not a
  crash — it is a function that politely returns nothing. A vector search that silently
  returned keyword-only results. An embedding guard that never ran. A missing dependency that
  degraded search instead of failing. A relocated virtualenv that made `setup.sh` install into
  the wrong Python while printing success at every step. When you review, **ask what a function
  does when its inputs are absent**, not just when they are present.
- **The LLM fabricates confidently.** Every model tried — including the strongest — invented
  CLI output formats the switch never prints, because the prompts demanded "exact CLI fields"
  while showing zero examples. The fix was grounding the prompts in 6,323 real harvested
  commands with real sample output. Fabricated tokens went from 13 to 0 in extracted sequences
  and 57 to 0 in generated scripts. This is why `cli_commands` exists.
- **Where prose and an example disagree, the model follows the example.** So the prompts' own
  code examples are executed as tests (`tests/test_prompt_examples.py`) against real data.

---

## 7. Deliberate decisions — please don't re-report these

Each of these looks like a defect and is not. They are settled, with reasons.

| Looks wrong | Why it is that way |
|---|---|
| **No authentication at all** | By design: localhost, single user. The server binds `127.0.0.1` by default; LAN exposure is an explicit opt-in. Real multi-user identity is planned (Phase 2 of `PLAN-auth-and-case-locking.md`) and gated on an organisational decision. |
| **Locks are an in-memory dict, not a table** | A durable `case_locks` table would have been the first in-place schema change to the permanent `ck.db`. The deliberate trade: locks live in memory, authoritative because the server is single-process, with an optimistic `rev` inside the session payload as backstop. `locks.py` documents the caveat prominently — going multi-worker silently reintroduces the bug. |
| **`build_db.py` exists but refuses to run** | Kept as provenance of how `ck.db` was constructed. Not dead code to delete. |
| **Session writes are whole-blob overwrites** | Known. That is precisely the problem `locks.py` solves. |
| **`sessions` is written at runtime while everything else is read-only** | Correct. It is the only mutable table. |
| **Generated test scripts name no devices** | Deliberate: generation targets a topology *contract*, never a specific bench, because a bench-reading generator silently weakens a test to fit whatever hardware is present. |

---

## 8. Suggested reading order

1. `ask-ck/ARCHITECTURE.md` — the executive summary. Shortest path to the shape of the system.
2. **`CK_server/db.py`** — read it top to bottom. It is the spine, and it is well commented.
   Pay attention to `get_connection` (extension loading, thread-locals) and the three search
   families.
3. `CK_server/locks.py` — read the module docstring in full. It is the clearest statement of a
   real trade-off in the repo.
4. `CK_server/routers/wizard/reviews.py` — the most representative handler. Follow `load_case`
   through to the session write.
5. `CK_server/generator/gates.py` — small, and it is where the "nothing advances without a
   human" rule is actually implemented.
6. `CK_server/routers/pytest_create.py` — the biggest file. Do not read it linearly; pick one
   endpoint and follow it.
7. `ask-ck/CK-main/SERVER-README.md` — the deep reference. Use it as a lookup, not a read.

`CHANGELOG.md` explains *why* things changed, and `ask-ck/objective-drafting/PROGRESS.md` has
the current state at the top.

---

## 9. What would be genuinely useful from you

- **Anywhere a failure is silent.** A swallowed exception, a default that masks an error, a
  search path that returns empty instead of raising. This repo's worst bugs have all been this.
- **Anywhere the database contract is bent** — a second SQLite connection, a write outside
  `save_session`, a query that assumes a column that isn't there.
- **Where `pytest_create.py` should be decomposed.** At 3,663 lines it is the obvious
  candidate; `routers/wizard.py` was already split this way and the plan for it
  (`PLAN-backend-module-split.md`) is worth reading first so the same reasoning applies.
- **Anything you had to read twice.** If the code confused you, that is data — say so. A
  newcomer's confusion is the only honest measure of how legible this is, and it stops being
  available the moment you know your way around.

Ask questions early rather than guessing at intent. Much of what looks arbitrary here has a
reason recorded somewhere, and it is usually faster to ask than to find it.
