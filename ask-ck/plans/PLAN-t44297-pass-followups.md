# PLAN — T44297 pass follow-ups: the seven issues one full fix loop exposed

> ## Status (read first)
>
> **PROPOSED 2026-09-09 — #5 ROOT-CAUSED AND FIXED 2026-09-10; items 1–4, 6 unimplemented.**
> Written at Terrence's request as the plan
> for the issues found while driving AWPTCM-T44297 through generate → review → fix on
> 2026-09-09 (the first full loop on the ART-frame shape). This file is the **authority for
> items 1–6**; **item 7 is delegated** to `PLAN-fix-units-guardrails.md` and only pointed to
> here. The loose list these came from is the "Pending fixes" block at the top of
> `ask-ck/functions/generator/PROGRESS.md`; that block now defers to this plan.
>
> Severity is not uniform. **#5 was the data-safety hazard and outranked everything else** —
> closed 2026-09-10 once the real cause turned out to be two SQLite libraries in one process,
> not NFS (read the item: the 2026-09-09 diagnosis is retracted there). #7 and #6 are process
> reliability; #4 is review quality; #1–#3 are UI polish. Order below follows that, not the
> discovery order.

## How these were found

One case, one day, one full loop: 39 generate units, 3 reviews, 5 fix runs (debug log,
`sess-pjkmca6yz2`). Six of the eight review/fix runs were rework. Along the way the loop
exposed: a WAL corruption of the permanent DB on the NFS share (#5), a review call that
dies with the user's SSH session (#6), a fixer that rewrites units a finding never named (#7),
loose review taxonomy (#4), and three UI gaps that made the state of the run hard to read
(#1–#3). Every item below cites the evidence it was seen with.

---

## #5 — ⚠ DATA-SAFETY: ck.db WAL deleted/corrupted under the live server — ROOT-CAUSED AND FIXED 2026-09-10

**Status: FIXED.** `ask-ck/tools/cli_lookup.py` + `tests/test_sqlite_single_library.py` (+ fixture fix in
`tests/test_cli_grounding_phase4.py`); gate green; live server reloaded 2026-09-10 08:55 and
verified holding its locks on `ck.db`/`ck.db-shm` in `/proc/locks` afterwards. **The 2026-09-09
diagnosis ("WAL mode is unsafe on NFS") is retracted** — NFS only supplied the `.nfs*`-orphan
signature; the same bug corrupts on local disk. Options A/B/C below are re-assessed accordingly.

**Root cause — two SQLite libraries in one process.** `db.py` binds `pysqlite3` (SQLite 3.51,
for `sqlite-vec`). `ask-ck/tools/cli_lookup.py`, imported by `routers/pytest_create.py` while rendering
every unit prompt, opened `ck.db` through the **stdlib** `sqlite3` (SQLite 3.37) — read-only, a
fresh connection per call across a dozen call sites, closed by garbage collection. POSIX advisory
locks belong to the *process*, not the descriptor, and each library keeps its own per-inode lock
accounting; so when the stdlib connection closed, that library saw "my last connection" and
issued a real `F_UNLCK`, which released **every** lock the server's pysqlite3 connections held on
`ck.db` and `ck.db-shm`. Two consequences, both reproduced with throwaway WAL databases on the
same mount (probes 1–5, 2026-09-10, all cleaned up):

1. **Lockless, the WAL is deletable from outside.** Any *read-write* open+close of `ck.db` by
   another process takes the exclusive lock SQLite uses to decide "last connection", finds a
   fully-checkpointed WAL, and unlinks `-wal`/`-shm`. The server keeps writing into the
   unlinked inode (NFS: silly-rename → `.nfs*` orphans held by the server pid); every outside
   reader sees base-only and goes stale; a new in-process connection opens the fresh empty WAL
   → split-brain → *"disk I/O error"* / *"database disk image is malformed"* / *"file is not a
   database"*; a restart drops the orphan and every un-checkpointed row in it. That is the
   2026-09-09 loss of three fixes (cache rev 446 vs disk 444) and the 2026-09-10 rev-467 save
   that only the server could see.
2. **Lockless, concurrent writers corrupt the WAL on their own.** The shm locks *are* the WAL
   write lock and reader marks. Two fix-fan-out threads persisting at once with no lock between
   them is the 2026-09-09 ~13:47 "malformed" — no outside process needed. The 2026-09-03
   "malformed" (`[[ckdb-corrupt-wal-recovery]]`) fits the same mechanism.

**Evidence chain.** Live worker held **zero** `/proc/locks` entries on `ck.db` while a probe
holder on the same NFS mount showed both READ locks (so NFSv4 locks are visible there — the
server had *lost* its locks, not hidden them); its `-wal`/`-shm` fds pointed at `.nfs*`
orphans; base vs base+orphan differed in exactly one row. Probe 4 (pysqlite3 holder + stdlib
read-only open/close, same process): all locks gone. Probe 5 (same library both sides): locks
kept. Probe 2/3: a **read-only** peer cannot delete the WAL (`F_WRLCK` on an `O_RDONLY` fd fails),
a **read-write** peer can — so the test gate's read-only snapshot and read-only diagnostics are
exonerated; the read-write opener that removed the WAL on 2026-09-09 ~15:40 was not identified
from the transcripts, and does not change the fix.

**Fix.** `cli_lookup` binds `try: import pysqlite3 as sqlite3 / except ImportError: import
sqlite3` exactly as `db.py`, and resolves `CK_DB_PATH` like `db._resolve_db_path()` (so the test
copy and the scratch server are honoured). Guard `tests/test_sqlite_single_library.py`: identity
(`cli_lookup.sqlite3 is db.sqlite3`); a static scan of every module that runs inside the server
process (CK_server + the `ask-ck/tools/` modules it imports) for stdlib `sqlite3` imports outside the
preference block; the incident path on a tmp WAL db observed through `/proc/locks`; and a
**negative control** that proves the check sees the bug (with pysqlite3 installed, a stdlib
connection closing *does* strip the holder's locks). Tests that hand `cli_lookup` a connection
now build it from `cli_lookup.sqlite3` — another library's exception classes are not caught.

**Rules that remain.**
1. **One SQLite library per server process** (guarded). Any new module the server imports that
   needs SQLite copies db.py's preference block or takes a connection from `db.get_connection()`.
2. **Never open the live `ck.db` read-write from another process while the server runs.**
   Read-only URI opens are safe (they cannot take the exclusive lock). `sqlite3 ask-ck/var/ck.db`
   at a shell, an inline `sqlite3.connect("ask-ck/var/ck.db")`, and the corpus loaders are all
   read-write. Stop the service first (`ck off`), or work on a copy.
3. **A 200 is provisional until a disk-side read shows the rev** — from a *copy* of
   base+`-wal`+`-shm` taken together, never a live open.

**Options A/B/C re-assessed.** None addresses the cause. **A (move `ck.db` off NFS)** removes
only the `.nfs*` orphan signature and is now an optional hosting/perf question, not data-safety.
**B (serialize writes)** would have masked consequence 2 without fixing 1. **C (drop WAL)** —
withdrawn. Recurrence runbook stays valid: `.nfs*` orphans in `ask-ck/var/` held by the server
pid = the server has no locks → find the second library/opener first, then restart. → **D5-1,
D5-2 re-scoped.**

---

## #4 — Tighten the Review(LLM) `kind` vocabulary

**Evidence.** Review #1 on T44297: a parse-index bug (tc6 `baseRow[4]` vs siblings' `[6]`/`[-4]`)
came back tagged `naming_inconsistency`; a *missing* `lldp tlv-select management-address`
came back `duplicate_setup` — the opposite. The `what`/`evidence`/`suggestion` bodies were
accurate every time; only the tag was loose. Harmless today; it becomes load-bearing the
moment anything routes on `kind` — and `PLAN-fix-units-guardrails.md` **G5 does exactly that**
(structural findings must be routable, never auto-fixed).

**Fix.** Two layers. (1) Constrain the review prompt (`templates/prompts/pt_review_script.jinja`)
to a small, defined enum, each value with a one-line definition. Proposed set:
`verdict_mismatch` (verdict claims more/other than what is checked), `weak_observation`
(passes on presence/CLI agreement instead of the observed value), `wrong_symbol`
(unbound/fabricated/mis-used name or layer), `cross_unit_inconsistency` (units disagree on a
shared convention), `missing_precondition` (setup the step depends on is absent),
`structural` (needs a new case, or verdicts in the config-only setup — G5's routing key),
`other`. (2) Normalise server-side in `_normalize_findings`: any tag outside the enum →
`other`; never invent a tag; keep the raw tag in provenance for audit.

**Tests.** `_normalize_findings`: an in-enum tag passes through; an unknown tag → `other` with
the original preserved; the two real 2026-09-09 finding dicts pin the behaviour. A prompt test
(`tests/test_prompt_examples.py` pattern) asserts the enum in the template matches the
server's — the two must not drift. → **D4**.

---

## #6 — Review(LLM) must not depend on a live SSH/browser session

**Evidence.** `review_script` uses `_llm_cfg(sess)` — the workspace LLM — which is
`claude_agent`: browser-brokered through the user's local ck-agent bridge, tethered to the SSH
session. On 2026-09-09 a ~4-min Opus review **failed twice** when the SSH session dropped
mid-call: the browser reported `NetworkError … local agent unreachable — is ck-agent running?`
after burning the full 228 s, and stored nothing. Because the prior review had already been
**invalidated by re-assembly**, the script was left with **no review at all** until a manual
re-fire. Per-unit generate/fix calls are short enough to tolerate the browser path; the
multi-minute holistic review is the one call most exposed to a session drop.

**Fix — stay on the release transport.** *(Reshaped 2026-09-10.)* `claude_agent` is the release
transport and the server-side CLI is **demo-only and will not ship**
(`[[claude-agent-is-the-release-transport]]`, 2026-09-07; seat governance in
`archive/plans/PLAN-per-user-agent.md`). So the fix is durability *within* `claude_agent`, not a
transport swap. The first draft of this item said "route the review through `claude_code`" —
**withdrawn**: it was written while that ruling's memory had fallen off the over-length index
(see the 2026-09-10 MEMORY.md trim), a live instance of an unloaded memory misleading a plan.
Two halves:

1. **The job survives the tab.** Today `agent.js` drives the local ck-agent's `/run` and posts
   the result back; when the tab/SSH dies mid-call the CLI's work is orphaned and the server
   records the `NetworkError`. Make the result durable: the agent completes the CLI call
   regardless of the tab, and the result is **collected on reconnect** — the per-session job
   registry (`agent_jobs`) holds a finished result under a TTL and `/api/agent/next` hands it
   back when that session polls again, instead of the request dying at the 228-s mark.
2. **Never review-less.** `_assemble_and_store` invalidates the stored review on re-assembly.
   Keep it instead, **marked STALE** (`assembled_at > review.at`) until a new review lands, so a
   dropped call leaves the last findings visible rather than nothing.

Generate/fix are untouched; the workspace default and the `unit_fill` route are untouched.

**Tests.** A review job whose session disconnects mid-call is **not** failed: a result posted
by the agent is held and delivered on that session's next `/api/agent/next` (fake the agent,
drop the session, reconnect); an uncollected result expires at the TTL; re-assembly leaves
`step6.review` present with the stale marker, and a completed review replaces it. Tests fake
`llm._run_cli` / the agent bridge — never a real CLI (`[[claude-code-cli-transport-contract]]`).
→ **D6**.
---

## #1 — Error chunks need a timestamp in the UI

**Evidence.** A failed unit shows its error text but no time, so a fresh failure and a stale
one from a previous pass are indistinguishable — this is exactly the ambiguity behind the
2026-09-09 overclaim of "28 units generated" over stale 2026-09-07 chunks.

**Fix.** The data already exists: `_apply_crash` and `_fail` in `routers/pytest_create.py`
stamp `at` on every error chunk. Surface it in the unit-chip tooltip and the status line in
`frontend/ck-main/current/pytest-creator/pytest.js` (render local time + a relative "3 min ago"). Consider the same stamp on
`ok` chunks — "generated 14:41" — since freshness was the whole question.

**Tests.** Vitest (`tests/js/`): an `error` chunk with `at` renders the timestamp; one without
`at` (legacy rows — `[[old-sessions-are-not-coverage]]`) renders without crashing. → **D1**.

---

## #2 — Per-unit regenerate has no visual cue

**Evidence.** Clicking a single case's regenerate produced no feedback that it fired or
succeeded (Terrence, 2026-09-09: "no visual cue appeared to suggest it worked").

**Fix.** Give `ptGenerateUnit` the same in-flight → done affordance the bulk generate has:
the chip goes to the in-flight glyph on click (the server already marks the unit in flight via
`_pt_unit_mark`), and back to ✓/✗ when `units_status` reports it. Reuse the existing poll —
never a second blocking request per unit (`[[browser-fanout-connection-ceiling]]`).

**Tests.** Vitest: click → chip shows in-flight; a status poll returning `ok` → chip shows ✓.

---

## #3 — The "If something's wrong" legend and Fix-button styling are out of sync with the buttons

**Evidence.** `frontend/ck-main/current/index.html:708-711` documents only the **whole-script** "Fix with LLM"
and per-unit *regenerate-from-page*; it never names **"⤺ Fix units (LLM)"** (`:737-740`), whose
only accurate description is its hover `title=` and an **unrendered HTML comment** (`:730-733`).
The legend's "don't re-Assemble after a Fix — it re-splices the units and discards the fix" is
TRUE for the whole-script Fix but MISLEADING for `fix_units`, which re-syncs chunks, writes the
fix into the chunk, and re-assembles+lints itself (so re-assembling is merely redundant). And
both Fix buttons call the LLM, yet "Fix units" is `btn-primary` (blue) while "Fix whole
script" is `btn-compact` (grey), contradicting the page's own "grey = local, blue = LLM"
convention (`:722`). This mismatch produced a contradiction between the page and Claude's
guidance on 2026-09-09.

**Fix.** Rewrite the visible legend to name both Fix buttons and their *opposite* re-assemble
behaviour; make both LLM Fixes `btn-primary`. If `PLAN-fix-units-guardrails.md` G7 lands
(preview/approve), the legend must describe the `held` state too — write it once, for the
end state. → **D3**.

**Tests.** Vitest: both Fix buttons carry the LLM class; the legend text names both.

---

## #7 — Guardrail `fix_units` → see `PLAN-fix-units-guardrails.md`

Delegated. Seven guardrails G1–G7 against five code-proven root causes (evidence prose hijacks
the target unit; scope is a prompt suggestion with no diff/frozen-line check; every unit is
re-written on every fix; a fix is trusted on shape alone; structural findings are auto-fixed).
Its **G5 depends on #4** here (the `structural` kind), its **G4 shrinks #5's** write pattern,
and its **G7 UI lands with #1–#3** (its D6). Decisions D1–D6 live in that file.

---

## Order

1. **#5** — data-safety first; at minimum the operating rule and runbook are in force today,
   and the A/B/C decision is made (A likely spawns its own plan).
2. **#4** — small, and it unblocks #7's G5.
3. **#6** — independent; no longer small (touches `agent_jobs`, the bridge and `agent.js`), but it stops a whole class of wasted 4-minute calls and the review-less state.
4. **UI batch: #1 + #2 + #3 (+ #7's G7 render)** — one step-5 UI change, not four.
5. **#7** — per its own plan's order (G1+G5 → G4 → G2+G6 → G3+G7), interleaved with the above
   where it shares code.

**Gate after every step** (`./ask-ck/tools/run_tests.sh`: both guards, pytest, vitest, ck.db-untouched).
Tests never write the permanent `ck.db`. This tree is shared — re-check `git status` and stage
explicit paths. **No push** (Terrence pushes).

## Decisions needed before starting

| # | decision | recommendation |
|---|---|---|
| D5-1 | ~~A/B/C~~ — root cause fixed 2026-09-10. Is moving `ck.db` off NFS still wanted as a hosting/perf change (it no longer buys data safety)? | defer; not urgent |
| D5-2 | Does A get its own plan? | only if D5-1 becomes yes |
| D4 | Adopt the proposed 7-value `kind` enum, with `structural` as G5's routing key? | yes; unknown → `other`, raw tag kept in provenance |
| D6 | #6 durability: TTL for an uncollected agent result (rec: align with `LOCK_IDLE_TTL`, 15 min)? keep a superseded review visibly STALE rather than deleting it (rec: yes)? | 15 min / yes |
| D1 | #1 timestamp: local time + relative? also stamp `ok` chunks? | yes / yes |
| D3 | #3 legend copy — draft for Terrence's review before implementing? write for the G7 end state? | yes / yes |
| D-UI | Land #1–#3 and G7's render in one pass? | yes (= guardrails plan D6) |
