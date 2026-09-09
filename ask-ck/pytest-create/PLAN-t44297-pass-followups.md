# PLAN — T44297 pass follow-ups: the seven issues one full fix loop exposed

> ## Status (read first)
>
> **PROPOSED 2026-09-09 — nothing implemented.** Written at Terrence's request as the plan
> for the issues found while driving AWPTCM-T44297 through generate → review → fix on
> 2026-09-09 (the first full loop on the ART-frame shape). This file is the **authority for
> items 1–6**; **item 7 is delegated** to `PLAN-fix-units-guardrails.md` and only pointed to
> here. The loose list these came from is the "Pending fixes" block at the top of
> `ask-ck/objective-drafting/PROGRESS.md`; that block now defers to this plan.
>
> Severity is not uniform. **#5 is a data-safety hazard and outranks everything else**; #7 and
> #6 are process reliability; #4 is review quality; #1–#3 are UI polish. Order below follows
> that, not the discovery order.

## How these were found

One case, one day, one full loop: 39 generate units, 3 reviews, 5 fix runs (debug log,
`sess-pjkmca6yz2`). Six of the eight review/fix runs were rework. Along the way the loop
exposed: a WAL corruption of the permanent DB on the NFS share (#5), a review transport that
dies with the user's SSH session (#6), a fixer that rewrites units a finding never named (#7),
loose review taxonomy (#4), and three UI gaps that made the state of the run hard to read
(#1–#3). Every item below cites the evidence it was seen with.

---

## #5 — ⚠ DATA-SAFETY: `ck.db` is WAL-mode SQLite on the NFS share and corrupts under write load

**What happened (2026-09-09 ~13:47).** During the review-driven Fix on T44297 — three rapid
per-unit CAS re-writes of the ~1.2 MB session row, while a second browser session
(`sess-ry6a677105`, a zombie tab) held the DB open for reads — the server's `ck.db-wal`/`-shm`
were unlinked/replaced while still open → NFS **silly-rename** (`.nfs*` orphans in
`ask-ck/var/`, held by the server pid), after which every disk-backed session op returned
*"file is not a database"*. The permanent **base survived** (`integrity_check` ok on a
main-file-only copy; the WAL truncated to 0). Recovery was a restart — but the three fixes
not yet checkpointed (cache rev 446 vs disk rev 444) were **lost and had to be re-run**. This
is `[[stale-session-connection-bug]]` escalated from "silent non-persist" to "corruption".

**Why it matters.** `ck.db` is the permanent single source of truth (invariant 1). WAL mode
relies on shared-memory locking that NFS does not honour — SQLite's own documentation says WAL
is unsafe over network filesystems. The corruption is not a fluke; it is the expected failure
mode of this layout, and the fix loop's write pattern (whole-session CAS writes, several per
fix) is exactly what provokes it. The next occurrence may not leave the base intact.

**Root-fix options.**
- **A — move `ck.db` off NFS onto the host's local disk** (recommended). The server of
  record runs on `10.33.22.17`; the DB can live on that host's local filesystem with the repo
  path becoming a symlink/bind, or `CK_DB_PATH` pointing at it. Preserves WAL performance.
  **Touches two settled things** and therefore needs its own decision, possibly its own plan:
  the LFS-tracked `ask-ck/var/ck.db` (how does the local copy stay the committed source — a
  sync step at `/wrap`? — see `[[db-is-permanent-source]]`) and the hosting layout
  (`[[askck-lan-hosting]]`, none of which is in the repo).
- **B — serialize session writes** (one writer, a process-level lock around `_pt_persist*`).
  Reduces contention but does not make WAL-on-NFS safe; readers in other sessions still hold
  the files open. Mitigation, not a fix.
- **C — drop WAL mode** (`journal_mode=DELETE`) on NFS. Safer semantics, slower, and the
  rollback journal has its own NFS caveats. Fallback if A is refused.

**Until fixed (operating rule).** Avoid concurrent sessions during a Fix/generate; treat a 200
as provisional until a disk read shows the rev advanced; keep the recurrence runbook: `.nfs*`
orphans clear on restart; verify the base via a main-file-only copy per
`[[ckdb-corrupt-wal-recovery]]`; snapshot the cache-held session with
`GET /api/pytest-create/session/<key>` (serves from memory) **before** restarting.

**Tests.** Not unit-testable; verified by procedure. `tests/test_db_isolation.py` stays the
authority that *tests* never write the permanent DB. Whatever A/B/C lands, re-run the
2026-09-09 provocation (a 3-unit fix with a second session's tab open) and confirm no `.nfs*`
orphan and rev parity between cache and disk. → **D5-1, D5-2**.

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
session. On 2026-09-09 a ~4-min Opus review **failed** when the SSH session dropped mid-call:
the browser reported `NetworkError … local agent unreachable — is ck-agent running?` after
burning the full 228 s, and stored nothing. Because the prior review had already been
**invalidated by re-assembly**, the script was left with **no review at all** until a manual
re-fire. Per-unit generate/fix calls are short enough to tolerate the browser path; the
multi-minute holistic review is the one call most exposed to a session drop.

**Fix.** Add a per-task route for `review` the way `unit_fill` has one (decision 6,
`_llm_cfg_for(sess, task)`), pointing at `claude_code` — the headless server-side Claude CLI,
already "the path every unattended batch run takes". `review_script` calls
`_llm_cfg_for(sess, "review")` instead of `_llm_cfg(sess)`. Model stays Opus. The workspace
default and the `unit_fill` route are untouched, so generate/fix keep their current behaviour.

**Tests.** `review_script` resolves the `review` task route; with a faked `llm._run_cli`
(tests fake `_run_cli`, **not** `subprocess.run` — `[[claude-code-cli-transport-contract]]`)
assert the headless path is taken and no `X-CK-Session` is required. A route-absent fallback
still reaches the workspace LLM, so nothing regresses if the route is unset. → **D6**.

---

## #1 — Error chunks need a timestamp in the UI

**Evidence.** A failed unit shows its error text but no time, so a fresh failure and a stale
one from a previous pass are indistinguishable — this is exactly the ambiguity behind the
2026-09-09 overclaim of "28 units generated" over stale 2026-09-07 chunks.

**Fix.** The data already exists: `_apply_crash` and `_fail` in `routers/pytest_create.py`
stamp `at` on every error chunk. Surface it in the unit-chip tooltip and the status line in
`static/js/pytest.js` (render local time + a relative "3 min ago"). Consider the same stamp on
`ok` chunks — "generated 14:41" — since freshness was the whole question.

**Tests.** Vitest (`js-tests/`): an `error` chunk with `at` renders the timestamp; one without
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

**Evidence.** `static/index.html:708-711` documents only the **whole-script** "Fix with LLM"
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
3. **#6** — small, independent, stops a whole class of wasted 4-minute calls.
4. **UI batch: #1 + #2 + #3 (+ #7's G7 render)** — one step-5 UI change, not four.
5. **#7** — per its own plan's order (G1+G5 → G4 → G2+G6 → G3+G7), interleaved with the above
   where it shares code.

**Gate after every step** (`./tool/run_tests.sh`: both guards, pytest, vitest, ck.db-untouched).
Tests never write the permanent `ck.db`. This tree is shared — re-check `git status` and stage
explicit paths. **No push** (Terrence pushes).

## Decisions needed before starting

| # | decision | recommendation |
|---|---|---|
| D5-1 | #5 root fix: A (off NFS) / B (serialize) / C (drop WAL)? | **A** — the only one that removes the hazard |
| D5-2 | Does A get its own plan (it touches the LFS-source invariant + hosting)? | yes — too consequential to ride inside a follow-ups plan |
| D4 | Adopt the proposed 7-value `kind` enum, with `structural` as G5's routing key? | yes; unknown → `other`, raw tag kept in provenance |
| D6 | #6 as a per-task `review` route (recommended) vs flipping the workspace default to `claude_code`? | per-task route — leaves generate/fix untouched |
| D1 | #1 timestamp: local time + relative? also stamp `ok` chunks? | yes / yes |
| D3 | #3 legend copy — draft for Terrence's review before implementing? write for the G7 end state? | yes / yes |
| D-UI | Land #1–#3 and G7's render in one pass? | yes (= guardrails plan D6) |
