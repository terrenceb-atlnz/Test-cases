# Changelog — Ask CK

Feature history for the Ask CK workbench, newest first. This file was split out of
`README.md` on 2026-08-17: the README's *Current Status* table had grown into a changelog
held inside table cells (one row ran to ~7,000 characters), which made both jobs harder.
The README now says what the system **is**; this file records how it **got there**, and
in particular *why* each decision was made.

For session-by-session narrative see [`SESSION_STATE.md`](SESSION_STATE.md); for the
current working thread see
[`ask-ck/objective-drafting/PROGRESS.md`](ask-ck/objective-drafting/PROGRESS.md).


## 2026-09-03 — Corrupt-WAL recovery for ck.db, and the setup unit stops raising a false indent error

**New tool + runbook to recover `ck.db` from a corrupt WAL without corrupting the base.**
`tool/db_wal_recover.sh` (+ `tool/DB-WAL-RECOVERY.md`). The permanent DB's base file can be
intact while its uncommitted `ck.db-wal` overlay is malformed — `PRAGMA integrity_check` reads
the two together, so check the base alone by copying only the main file. *Why the tool is
careful:* the server is a systemd unit with `Restart=always`, so the stop must be SIGKILL (a
clean close checkpoints — though a *corrupt* WAL fails to checkpoint, so this is conservative,
measured 2026-09-03) **and** mark the unit inactive (or it respawns onto the corrupt WAL). It
is fail-closed: refuses unless the base alone is `ok`, backs up first, restores and leaves the
server stopped if verification fails. Rehearsed on a throwaway systemd unit before real use.
**Never run a bare `sqlite3` on a corrupt-WAL DB as the last connection — it checkpoints on
close and folds the corruption into the base.**

**The setup unit no longer fails on arrival with an unmappable indent error.**
`_unit_shape_ok` used to parse the returned `configure()`/`tear_down()` pair inside a synthetic
`class _P:` wrapper, so a bad reply reported `IndentationError … line 38` against a line nobody
wrote. Syntax/indentation is already validated at the Summary step (`assemble_script` →
`_lint_generated` `py_compile`, real line numbers), so the setup arrival check now keeps only
the mappable structural question — did both methods come back (by regex) — and defers syntax to
Summary. *Why:* a false error in the wrong step. TestCase units are unchanged; PLAN §9.7 updated.

## 2026-09-02 — Per-unit script generation, a batch dispatch that survives the browser, and a cache-aware prompt order

**Step 6 generates one LLM call per test case instead of one per script.** The frame is
rendered deterministically and split by AST into units (`TestCase_<n>`, plus configure/
tear_down as one `setup` unit); replies are spliced back byte-exactly. Assembly uses no LLM —
splice, re-stamp, lint. *Why:* the single whole-script call for AWPTCM-T44297 took 672.9 s and
$1.58, and 39 % of its output was the model retyping a frame we already generate exactly.
Per-unit costs more in total (~$13.5 for 30) and buys parallelism, restartability of one
failed step, and an editable per-unit prompt.

**Fan-out is dispatched as ONE request.** *Why:* firing 30 blocking requests hits the
browser's 6-connections-per-origin limit and starves the agent broker's own poll — the page
cannot collect work it just queued. `POST /generate_units/{key}` queues them server-side
(`Semaphore(8)`) and `GET /units_status/{key}` polls; the browser broker runs 4 workers.

**The per-unit prompt is ordered so prompt caching can work, and the shared fill rules were
reworded to permit it.** Everything invariant precedes everything that varies; the measured
shared prefix across a case's 30 prompts went from 343 characters (0.7 %) to 11,143 (21.7 %).
*Why the rules changed:* `pt_fill_rules.jinja` is included by BOTH prompts, which place the
CLI reference on opposite sides of it, so rules 4b / 4b-ii / 5 saying "above" was false for one
caller. Three lines are now position-neutral; the whole-script render was diffed line by line
before the byte-identity snapshot was regenerated, and a guard test fails if a positional word
returns. **Do not put a position word in a shared prompt partial.**

**Pass C (holistic review) shipped** — `POST /review_script/{key}` returns findings as JSON,
persists them under `step6["review"]`, writes no files and invalidates no downstream step;
`fix_script` accepts `review_findings` as a fix reason.

**Every button now shows it was pressed**, and Save Selections confirms with `✓ Saved`. *Why:*
the save worked and always had — it flashed colour for 1.2 s, with no glyph, a screen-height
from the button that was clicked, which is indistinguishable from nothing happening.

## 2026-09-02 — tb470's `.setup` became a generated artifact, and the tree stopped holding rival copies of the bench

**What changed.** `/home/st-art/st-art/configs/tb470.setup` is no longer authored. It is
generated from `~/claude/IE520-testing/bench-setup/bench-state.md` (NFS lab home, outside this
repo) by `bench_setup.py apply`. Anything in this repo that told a reader to open the `.setup`
to learn what is cabled now points at that record instead, and the `scp tb470:...` step in
`pt_preflight.py`, `genpop.agent.md`, `RESUME.md` and `preflight-topology-check.md` is replaced
by the always-current local copy `bench-setup/tb470.setup.current`.

**Why.** Bench facts were being recorded in whatever document happened to be open, and there
was no way to tell which copy was current. The measurable damage: a `[portlink]` line that
outlived its cable; `.bak-*` files accumulating beside the live file in a *shared* `configs/`
directory with nothing marking which was current; `SETUP-FILE-REFERENCE.md` still calling the
file non-existent five weeks after it existed; and a stale bench copy named `TB470_LIVE` living
inside the test gate. A generated artifact cannot drift from its source — `bench_setup.py
check` proves it — which is the property none of those copies had.

**The distinction that matters, and that I initially got wrong:** a *derived* file is not a
second source of truth. What made the old arrangement bad was independently maintained copies
with nothing to invalidate them. Duplication between a record and something generated from it
is not the same defect, and should not be "fixed" by deleting the record.

**Versioning rule.** `bench-state.md` always names the current truth and is never renamed, so
every pointer to it stays valid. The *superseded* version is dated into `backups/`, paired
under one UTC stamp with the `.setup` it produced. This also holds for edits that change only
the prose and not the rendered file — otherwise history keeps the reflection and loses the
source.

**One behaviour change in this repo's code:** `tests/test_pt_preflight.py`'s `TB470_LIVE`
fixture is renamed `TB470_2026_07_30`. It was named "live" and its docstring said it pinned the
live bench; it is a frozen 2026-07-30 snapshot, and it must stay frozen because the two tests
that use it exist to pin a 0/3 → 2/3 contrast that only holds for that day's cabling. A
current-bench case needs a new fixture, not an edit to this one.

## 2026-09-01 — The Testboxes panel stopped guessing: `user` is required, and a setup is a named list with no "default"

Terrence: *"This page is not entirely intuitive… make sure it's only asking for fields that are
absolutely required."* The form was ten unlabelled placeholder boxes in three rows, so nothing
distinguished a required field from a defaulted one, or said what a value was for. It now has
real labels, per-field hints, a five-step instructions panel, and everything with a working
server-side default folded into a collapsed **Advanced** block.

**`user` is now required and has no default.** It defaulted to `st-art`, which is wrong on at
least one live bench — `st-art@tb470` answers `Permission denied (publickey,password)` while
`terrenceb@tb470` authenticates (TESTBOX-ACCESS §3a). A wrong-by-default username fails at the
SSH layer, so it presents as a network or testbox fault rather than a profile mistake, and it
cost a diagnosis session once already. `PROFILE_DEFAULTS["user"]` is `None` and `user` joined
`PROFILE_REQUIRED`, so the failure can no longer be reached by omission. The frontend's silent
`|| 'st-art'` fallback is gone with it. `tb_number` stays required at Terrence's call, but its
hint now says plainly that it is a label and nothing in the run path reads it.

**`.setup` files became a named map owned by whoever adds them, and are optional.** The form
used to write every setup under the literal key `default`. That silently *renamed* whatever was
already stored — the live tb470 profile keys its setup `tb470` — and on a LAN-shared server it
meant the last person to save named everyone else's setup. Terrence: *"there should NOT be a
default setting at all. This will be used by multiple people to run their own setups."* The
panel now has a repeatable name+path editor; the backend already stored `setups` as
`{name: path}` and the Run dropdown already rendered every entry, so only the form was
collapsing it. Names round-trip verbatim, half-filled and duplicate rows are refused instead of
silently dropped, and a testbox with **no** setups saves fine — the Run panel's existing
free-text path box covers "run mine". Requiring at least one would have made the creator's file
everyone's de-facto default under another name.

Fixed on the way through: `normalize_profile` rebuilds from defaults, so saving with the old
blank `.setup` field **wiped** a stored `setups` map entirely — the profile still looked fine
and then 400'd at Run.

**Tests:** `tests/test_pt_testbox_profile_fields.py` (10, incl. drift guards that the form's
asterisks, the JS validation list and `PROFILE_REQUIRED` are one set),
`js-tests/pt-testbox-setups.spec.js` (13, source-level per the house pattern) and
`js-tests/pt-testbox-setups-roundtrip.spec.js` (10, behavioural in jsdom — the "your name is
never rewritten" promise driven through real DOM). Every fix mutation-checked. Verified end to
end by driving the real UI against the scratch server: the on-disk diff was exactly one added
line, with the original `tb470` key byte-identical.

## 2026-08-31 — The step-3 confirm gate, the naming that would not stick, and provenance that previewed the wrong call

Terrence drove a real case (`AWPTCM-T33351`, 802.1X single-host) through the per-step flow
and hit three separate defects in sequence. All are fixed, each mutation-checked. The session
also **pulled two commits from the other stream that had never been gated** — their author's
host had neither pytest nor node, and said so — `23178e0` and `3224629`.

**Step 3 could not be confirmed, so step 4 was unreachable.** `confirm_step` accepted step 3
only on `step3.provenance` or `step3.matches`. After the 2026-08-26 move to a per-sequence-step
picker neither is written: step 3 has never written `provenance` (only steps 2, 5, 6 and 8 do),
and `matches` came solely from the whole-case `POST /suggest_scripts`, which left the UI on
2026-08-20. A step 3 reported with every sequence step covered and scripts chosen was rejected
regardless, and `gather_fragments`' `_require_confirmed` held step 4 shut behind it. Every
`pt-` session already in `ck.db` predated the change and still carried `matches`, which is why
the suite stayed green and the bug reached a user. `confirm_step` now also accepts the per-step
flow's own evidence that the step ran — `step_matches` (written even when a step matched
nothing, preserving "an empty list is a legitimate answer") or `selections` (keyword picks made
without invoking Suggest). Scoped to `matches`; step 5 writes real provenance, so `fragments`
keeps its original predicate. The fix arrived from origin with no test — the gate count was
unchanged — so it has one now.

**The LLM Provenance panel previewed a call the page was not making.** `provenance.js`
documents the contract in its own header: `bodyFn` "returns the request body (minus dry_run) at
click time so it always reflects current naming/inputs" — that is precisely what makes the
preview 1-for-1 with a real send. Every PyTest Creator panel passed a hard-coded `() => ({})`,
so Refresh posted an empty body and each endpoint fell back to its server-side defaults. Two
consequences, both visible. On **Generate**, the fallback group for this case was
`Authentication & Security`, which `_validate_naming` rejects — so Refresh answered
400 "Invalid group name" for a group the reviewer had already edited away, before rendering a
single line of prompt, while the Generate button (which does post its inputs) worked fine. On
**Script Search**, the mount still pointed at the retired whole-case `/suggest_scripts` — its
last reference anywhere in the frontend — so Refresh rendered the retired mega-prompt and
presented it as "what would be sent". `mountPtProvenance` now takes a `bodyFn` and accepts a
function endpoint; Generate passes its live naming, Script Search resolves
`/suggest_scripts_step/{key}/{n}` at click time so the preview follows the step pager.

**Step 3 recorded nothing about what it sent.** It was the one LLM step storing no provenance,
while its panel seeded from `step3.provenance` — a key only the retired whole-case suggest ever
wrote. For any session driven through the current picker that panel was permanently blank, with
no way to see what a suggest had sent after the fact. `suggest_scripts_step` now stores
`{llm, prompt, response, step_n}`. **One slot rather than one per sequence step** is
deliberate: the session payload is a row in the permanent `ck.db`, and a 32-step case would
otherwise carry 32 full prompts; `step_n` says which step it belongs to, and any other step's
prompt is a dry-run Refresh away at zero token cost. A dry run records nothing.

**Nothing would persist the step-6 naming until a generation had already succeeded.**
`step6.naming` had exactly two writers: the success tail of `generate_script`, and
`save_script`, which opens with `409 "Generate a script first."`. So before a first successful
generation there was no endpoint that would store the Group and script-name fields at all —
what the reviewer typed lived purely in the DOM, and `renderPtGenPanel`'s
`naming.group || group_display` re-seed silently replaced an edit with the default the moment
the panel was navigated away from and back. A generation that FAILED discarded it too, since
the write sat on the success path. New **`POST /api/pytest-create/save_naming/{key}`** persists
the two fields alone with no file required, autosaved on blur; it refuses once a script exists,
because renaming then has to move the file on disk and re-lint it — `save_script`'s job, and
half-doing it would strand the old file under the old name. `generate_script` additionally
persists the naming *before* the LLM call, skipped on `dry_run` so a preview stays a pure
no-write — that guard matters, because the write sits upstream of the dry-run return and would
otherwise have made merely LOOKING at a prompt write to the permanent `ck.db`.

**And the trap underneath all of it: the API handed the UI a default its own validator
refuses.** `_group_display` is both the value `load_case` returns to seed the Group field and
`generate_script`'s server-side default when the body carries no group, but it stripped only
the trailing `(42)` count — leaving any character outside `_GROUP_RX` in place. Enumerated
across `ck.db`: 5 distinct groups, of which exactly one produces an invalid default, and it is
the group of **42** cases. It now sanitises, collapsing each run of disallowed characters with
the spaces hugging it into a single `_` (`Authentication & Security` → `Authentication_Security`,
which is what the reviewer had typed by hand). A group that already validates is returned
byte-for-byte unchanged, so `Management`, `Port` and the `generated/` directories named after
them are untouched — only a name that could never have worked is rewritten.

**Gate discipline note — a test that asserts over real output must know what that output is.**
The first generation to emit a `library_*.py` companion turned the gate red, and the script was
fine: `tests/test_pt_preflight.py` globbed every `*.py` under `generated/` and assumed each was
a runnable test script, so a helper module that legitimately binds no devices read as "no
devices detected" — and, counted as having no demands, as trivially *runnable*. The same glob
was also sweeping `.meta/**/history/iter-N/`, the snapshots of superseded iterations, which
would have reddened the gate permanently the next time a case was generated twice. It now
excludes `.meta/` and selects on the skeleton's own shape — `class X(ATTestSet | ATTestCase)` —
rather than on the filename, because the library's name comes from the MODEL
(`_persist_generated_files` validates it for safety, not for a prefix). That rule also keeps the
hand-made `.REVIEW.py` in scope, which a sidecar-meta rule would silently have dropped, and an
assertion fails loudly if the filter ever matches nothing.

Gate: 1100 passed / 1 skipped (from 1071), 105 Vitest across 9 files (from 92), both invariant
guards OK, `ck.db` untouched by tests.

---

## 2026-08-26b — Step-3 results became durable and context-bearing; every LLM button gained live progress and a true Stop

Second session of the day, both features Terrence's explicit asks, both verified live in a
real browser against the scratch server — the LLM half against a fake `claude` CLI on PATH,
so not one token was spent proving it.

**Script Search: suggestions persist, chosen rows keep their verdicts, and the verdicts now
reach downstream.** Per-step LLM suggestions lived only in browser JS — the endpoint's own
docstring said "Not persisted to step3.matches". Tolerable while the whole-case suggest (which
does persist) owned the flow; once its button left the UI, nothing persisted: a hard reload
lost every candidate and degraded chosen rows to `other` / `?` / empty why (keyword-search
picks had no persisted record anywhere). Now: suggestions merge into
`step3.step_matches[step]` (by id, newest verdict wins — a re-suggest refreshes without
dropping what the page showed), Save Selections ships whitelisted record snapshots
(`step3.records`), and the seed path restores both on any load, in any browser. Fetching
suggestions deliberately does NOT unconfirm step 3 or invalidate fragments — candidates are
not selections; save_matches keeps its invalidation. A new **"Suggest all steps (LLM)"**
button in the coverage bar (left of the tally) runs the per-step suggest for every sequence
step **sequentially** — the same call the per-step button makes, never the retired whole-case
mega-prompt — populating and persisting as each step completes; a mid-run reload keeps every
finished step. And the **coverage/why verdicts now feed the Fragments prompt** ("chosen for
sequence step N — partial — <why>" per script, per-step verdicts outranking whole-case ones,
with a routing rule to start each step at the scripts whose verdicts name it) — previously
scripts arrived as bare symbol lists and the entire review context went nowhere. Fragment
`why` already flowed into Generate as "Reviewer note", so the chain is closed end to end.
Also: a per-step LLM failure is now a loud 502 instead of a silent `matches: []` — the same
error-is-not-empty shape gather_fragments already had, and a precondition for Stop reading as
"stopped" rather than "0 matches".

**Every LLM button: live progress + click-to-STOP, and the stop is real.** Chosen over a
UI-only abort explicitly: aborting the fetch client-side lets the server finish, spend the
tokens, and persist a result behind the user's back. Instead: the browser stamps each call
(`X-CK-LLM-Call` → middleware ContextVar → `llm_inflight.py`, in-memory, single-process like
locks.py); the busy button re-enables as a Stop button (`actions.js` routes its click to
`POST /api/llm/cancel/{id}` BEFORE data-action resolution, so it can never re-fire itself)
and shows `37s / ~45s · 12.3k streamed` with a 2px fill bar — `~45s` is the median of recent
successful same-template calls (llm-debug history), the streamed count is real server-side
observation. Cancel kills the CLI process group / closes the vLLM stream / wakes an agent
job abandoned; the endpoint errors "cancelled by user"; the UI says "⏹ stopped — nothing was
kept". The hardened claude_code transport moved from `subprocess.run` to `_run_cli`
(Popen + pump threads) — semantics preserved exactly (same timeout-kill, same >64 KiB stdin
safety, same CompletedProcess shape); all 25 transport-contract pins pass unchanged, and
three structural guards that tripped during the build (SSE utf-8 pin, thread-context guard,
truncation-signal fake) were each fixed at the source. Verified live: "Extracting… 5s / ~8s
· 356 streamed", bar at 62%, Stop click → shim CLI process dead server-side, run 1's
completed sequence rendered as real rows. Tests: +5 persistence, +6 cancel/progress → 1071.

Harness lessons recorded for future sessions: never delete a scratch `scratch.db` without its
`-wal`/`-shm` (an orphaned WAL replays into the next copy → "database disk image is
malformed", which then masquerades as lock trouble); and every Playwright run holds its
case's lock after `browser.close()` (pagehide/sendBeacon skipped), so consecutive runs must
restart the scratch server or use distinct cases.

## 2026-08-26 — PyTest Creator UI conformance, refresh-safe UI state, the `claude_code` radio (a deliberate reversal), and LAN hosting

A Playwright exploratory sweep of the PyTest Creator pages (explicitly requested — the
`user-prefers-manual-ui-testing` memory was exempted for this session by Terrence) found six
confirmed defect groups; everything below was then fixed, and every fix was **re-verified in a
real browser against the scratch server**, not just by tests. Gate before and after:
1060 passed / 1 skipped, 92 Vitest (8 files), both guards OK, `ck.db` untouched by tests.

- **The visible step numbering was fixed to match the design.** The 2026-07-23 flow revision in
  `PLAN-pytest-creator.md` is explicit: the visible flow is **7 steps**, internal `stepN`
  session keys are **unchanged** — only labels shifted. Four places in the UI had drifted back
  to internal numbering: the Validate panel's confirm button said "Step 8" inside a panel whose
  every other label says 7; the post-LLM-fix status pointed at "6. Generate" (6 is Run — an
  instruction naming a panel that doesn't exist); and two prose strings said "step 8" for
  Final Validation. Labels changed, `data-args='[N]'` internal values deliberately untouched.
  Three different Confirm-button conventions in one flow ("Confirm Step 2" / bare "Confirm" /
  "Confirm Step 8 (close out)") were unified to "Confirm Step N".
- **The no-selection copy pointed at the wrong dropdown.** Both the page subtitle and the
  load alert said "select a **completed** case" — but Complete is the *output* bucket
  (measured live: 52 Open/Partial, 0 Complete). Both now point at Open/Partial.
- **"step" was overloaded in the carousels.** Script Search showed "Confirm Step 3"
  (pipeline) beside "9/11 steps covered" and "Suggest for step 1" (extracted sequence) in one
  view. All 13 sequence-step labels now say "Sequence step N"; pipeline labels keep the bare
  form the sidebar uses.
- **Run and Validate now name the case they act on** — previously the panel that executes on
  hardware and the one that closes a case out were the only two with no case identity at all.
  Run also names the script it will execute (built from `step6.naming`, the same way
  `ptUpdateGenPath` does). **"Run on Testbox" is now disabled until a testbox is picked**
  ("Select a testbox first" tooltip) instead of being an enabled primary button whose click
  died in an alert; the gating explicitly yields to `locks.js` when the lock layer disabled
  the button. The two case dropdowns render at one width (empty bucket used to collapse to
  min-width beside a full one at max). The `.setup`-path input no longer clips its placeholder.
- **Keyboard users can now reach the tools at all.** `actions.js` has activated
  `div[role="button"]` on Enter/Space since the module split ("so sidebar navigation is usable
  without a mouse") — but every accordion section starts collapsed and the section headers
  were bare `<div>`s: unfocusable, so the support was unreachable. Headers now carry
  `role="button"`, `tabindex="0"`, live `aria-expanded`, and bodies `aria-labelledby`.
- **New `static/js/session-restore.js`: a refresh no longer loses the user's place** —
  app-wide (Generator selection included), not just PyTest Creator. F5 used to return to
  `panel-main` with the sidebar re-collapsed and dropdowns cleared while the server-side
  session was still loaded and nothing said so; this collided directly with the 2026-08-20
  stale-tab guard, whose only remedy is "reload". **sessionStorage, not localStorage, on
  purpose**: state must survive a refresh and nothing more — a tab reopened days later must
  not auto-load a case and silently re-acquire its per-case lock against a colleague. PyTest
  Creator's selected-vs-loaded distinction is preserved (only a case that was actually loaded
  is re-loaded, re-acquiring the lock exactly as the user's own click did). The restore waits
  on the case lists (`waitForOptions`) instead of the old fixed 200 ms guess, which raced
  `initCases()` on a cold load; the old first-open-case default is kept as the no-snapshot
  fallback. One bug found by verification, worth remembering: **the boot default
  `goToPanel('panel-main')` records itself, so it overwrote the snapshot before an async
  restore could read it** — the restore then faithfully returned to panel-main every time.
  `main.js` now captures `BOOT_SNAPSHOT` before applying the boot default.
- **`claude_code` got its own radio — "Claude Code CLI (this server)" — reversing the
  signed-off UI exclusion, deliberately** (Terrence chose Option A of
  `PLAN-llm-mode-selection.md`; reversal recorded in `models.py` and
  `routers/wizard/config.py` as that plan required). The remap at `llm.js`
  `restoreLLMConfigUI` (`claude_code → claude_agent`) is deleted. Why: hiding the mode never
  prevented the server-seat spend — it only made the radio lie. The plan's diagnosis was
  reproduced exactly on this checkout before the change: server on `claude_code`, radio
  checked `claude_agent`, "Check my local agent" offered and unable to work, and every tab
  long-polling `/api/agent/next` for jobs that can never be queued (deleting the remap fixed
  that broker loop for free — measured 0 polls after). Showing the model row under
  `claude_code` exposed a second, subtler lie: the Haiku/Sonnet/Opus **restore** was also
  gated on `claude_agent` alone, so the row showed the markup default (Sonnet) against a
  stored `opus`. Both Claude modes now share the row, its restore, the live toggle, and a
  mode-aware seat note; a server-seat instructions panel states plainly whose seat pays. The
  Configure page's description no longer claims Claude always runs on the user's own machine.
  **Deliberately NOT closed: the §3c Apply trap** — `save_global_llm` is still unconditional,
  so any seat's case-scoped Apply still rewrites the global default (it just can't write a
  *broken* value from the UI any more). Still open in that plan's §5, with the server's total
  lack of auth.
- **The app is now LAN-hosted**: `http://10.33.22.17:8000/` via the systemd user unit
  `ask-ck.service` + fstab automount + the `ck` control command. Host-local by nature (none
  of it is in this repo) — the full record is in SERVER-README "Hosted deployment", including
  why `Restart=always` and why `run.sh --stop` must not be used against it.
- Cache-busters bumped (`main.js?v=28`, `styles.css?v=27`). Verification tooling note: `bun`
  is absent on this host; the whole-module-graph build check used the repo's own
  `node_modules/rolldown`.

## 2026-08-20 — Multi-seat UX hardening (reconstructed 2026-08-26 from commit messages)

Five commits landed on 2026-08-20 (four by Jacob McClure, one by Terrence) with no CHANGELOG
entry; this entry reconstructs them **from their own commit messages** during the 08-26 wrap so
the dated history has no hole. The day's theme: the first real multi-seat use over the LAN.

- `4a769a8` **Grok removed from the Configure page, backend kept.** UI-only by choice —
  `grok_cli` stays in `SUPPORTED_AUTH_METHODS` ("a governance control rather than a
  convenience list"); retiring a backend is a bigger decision than hiding a button. The
  `auth_method` default and config-restore fallback were both `grok_cli` and would have
  dangled; both now fall back to `local_llm`.
- `076e3ba` **LLM suggestions land in candidates, not straight in the chosen list.** All three
  suggest-with-LLM paths auto-promoted every returned id via `precheckIds`; the picks were
  accepted before anyone looked at them. They now merge into the candidates table and the
  analyst ticks + chooses. The `precheckIds` mechanism itself was kept (test-covered, general).
- `b544f5e` **The agent broker loop stops when `claude_agent` mode ends.** `ckBrokerLoop()`
  was `while (true)`; after switching the workspace away, three remote seats kept long-polling
  for jobs that can never be queued — and the failure path made a stopped server *increase*
  traffic (2 s retry vs 25 s long-poll). `ckAgentModeActive()` existed for exactly this check
  and was never called; now consulted each iteration. (On 2026-08-26 the check became fully
  effective: the `claude_code→claude_agent` radio remap that defeated it was deleted.)
- `dd77ac1` **Open tabs are warned when the frontend they run is superseded.** Static assets
  serve straight off disk, so an edit is live with no restart and an open tab keeps running
  old modules with nothing to tell it — three seats sat on superseded code for a whole
  session. `GET /api/version` hashes mtime+size over the static tree ON DISK (deliberately not
  the git SHA and not a startup constant — neither moves in the cases that actually strand a
  tab); `version.js` polls it and raises a reload prompt, never auto-reloading (unsaved wizard
  work + live case locks make that a bad trade).
- `89722fe` (Terrence) memory + `TESTBOX-ACCESS.md` updates, a `run.sh` note removed, and a
  new `ck.db` — the tb470/IE520 stack findings recorded in `tb470-topology-and-setup`.

## 2026-08-17 — The README stopped being a status document

Its *Current Status* table had become a changelog held inside table cells — the PyTest Creator
row was a single ~7,000-character line spanning three weeks — which made it unreadable as a
table and awkward as history. The README is now navigational only (what the system is, quick
start, the four invariants, the gate, the data, the tools, the documentation map): **405 lines
/ 55 KB → 247 / 13.7 KB**. This file is where the history went.

Consequences worth knowing:

- **`/wrap` and `/orient` were repointed in the same change.** `/orient` now reads this file's
  newest entry and skips the README, which no longer changes session to session; `/wrap` knows
  this file as an append-only dated log and no longer expects a feature-status table.
- **Test counts were removed from the README on purpose.** It claimed **775** against a real
  **1060** — that is the number that rots fastest, and the gate prints it. Corpus figures that
  remain were re-measured against `ck.db`, not copied.
- Defects fixed in passing: the logo was a broken link, a stray `=D` sat on line 2, the
  copyright block appeared twice, a dead `../AGENTS.md` was referenced, and `setup.sh` was
  described as doing a **"DB build"** — it does not, and must not, which contradicted
  invariant #1.
- **Pointer cleanup across the tree**, 14 broken relative links → 8. The 8 that remain are
  deliberate: one is a *format example* inside backticks, five are repo-root-relative paths
  whose targets all exist, and two name `routers/wizard.py` inside **dated** entries. That file
  became the `wizard/` package on 2026-07-29, but a frozen log gets a banner, never an edit.

Six memories that cited `routers/wizard.py` were corrected the same day — tracing where each
symbol actually went, because the split also **dropped the underscore prefixes**
(`_can_synthesize` → `generator/gates.py: can_synthesize`, `_relevance_score` → `db.py`), so
grepping the old names would have failed too.

## 2026-08-17 — The venv stopped being relocatable, loudly and silently

The working tree moved from `copilot/Test-cases` to `claude/Test-cases`. A Python venv is
**not relocatable**: `pip` bakes an absolute shebang into every console script, and
`activate` hardcodes the absolute `VIRTUAL_ENV` it was built with. 30 files carried the
dead path (29 scripts in `.venv/bin/` plus `pyvenv.cfg`).

- **The gate failed loudly.** `tool/run_tests.sh` invoked `.venv/bin/pytest` directly, which
  died with `bad interpreter`. Fixed by running everything as `"$PY" -m <tool>` — `-m` reads
  the module out of site-packages and never consults a shebang, so the gate now survives any
  future move.
- **`setup.sh` failed *silently*, which was worse.** Its reuse check probes
  `.venv/bin/python3` — a *relative* symlink that still resolved — so it reported "Reusing
  existing virtual environment", sourced the stale `activate`, and then ran bare
  `python3 -m pip install`. With the venv's `bin/` missing from `PATH`, that resolved to
  the **system** Python 3.10 and would have installed the entire dependency set into the
  user's site-packages while printing success at every step. The sqlite-vec (§4b) and
  `ck.db` (§4c) checks had the same fault, so they were reporting on the wrong interpreter.
- **`run.sh` had it too**: the server would have started on system 3.10 with a `fastapi`
  from `~/.local` and **no `sentence-transformers`** — the exact "boots but silently
  degrades to keyword-only search" trap the setup docs warn about.

Fixes: the baked paths were rewritten in place; `setup.sh` gained a **§3b relocation
detector** that repairs a moved venv or fails loudly; and `setup.sh`/`run.sh`/`run_tests.sh`
now all call the venv interpreter **explicitly** rather than trusting an activated `PATH`.

## 2026-08-05 — The blank-`expectedResult` push rule was removed

The rule refused all 53 bundles on a false premise. A Zephyr **manual** step is *designed*
to leave `expectedResult` empty, so the tester produces evidence of function rather than
reproducing a stated result. `synthesize_steps` now forces the field empty at generation.
See memory `expected-results-deliberately-absent`; this was reversed circularly once before
and must not be re-litigated.

## 2026-08-04 — Lint gate split by authority

19 lint rules split into two classes with different powers:

- **14 blocking errors** — the artefact provably cannot work (syntax, missing structure, a
  surviving `>>> FILL` marker, a device the fixed `init()` frame never bound, a bad import,
  the truncation detector). **Not overridable.**
- **5 policy errors** — the script runs but breaks a house rule (the logging contract, a
  direct `setup.init_portlink()`). Overridable with
  `{"acknowledge_lint_policy": "<why>"}`, recorded on the session.

Unrecognised errors are treated as blocking. Also: **Run results** report one outcome per
case (PASS / FAIL / UNSUPPORTED, plus ERROR for a case that reached no verdict) with both
tallies labelled — `cases: … ; assertions: …` — and `results_complete` states whether the
results are *trustworthy*, which is a separate question from whether the test passed.

## 2026-08-03c — Multi-message generation: there is no output ceiling

The 32,000-token cap bounds one **message**, not the answer; a long reply simply continues
into further assistant messages. Measured `output_tokens` of 67,326 / 66,334 / 57,188 /
34,966 — every one a complete script. `CK_server/gen_assembly.py` reassembles the
continuation seams and resolves classes a continuation re-emits. A reply that does not
reassemble cleanly is **refused** rather than persisted (the full reply is saved under
`step6.failed_generations`), and a script covering fewer steps than the approved sequence
is a lint **error** that blocks confirmation.

The earlier "9–20 `TestCase` class ceiling" and its `_size_overflow()` gate were a defect in
`_parse_generated_blocks`, which stopped at the first *continuation* fence and discarded the
rest. Both are gone. `ask-ck/pytest-create/FINDINGS-generation-size-ceiling.md` carries a ⚠
banner because it records **parser** output, not model output.

## 2026-08-03 — Zephyr push validates before it writes; preflight stops guessing

- The push now **validates before it writes** (server shape rules, imported from
  `validate_zephyr_payload` — one owner, no second copy) and **fails closed**. A real write
  requires a per-case `{"confirm": "<key>"}` token.
- Fixed a heading mismatch that silently dropped **84 of 86 Zephyr web-links**.
- Every `--execute` appends to `ask-ck/var/zephyr-push-audit.jsonl` **before** the first
  network call; a case whose audit record cannot be written is refused.
- `tool/pt_preflight.py` now resolves a topology-**contract** role
  (`misc.get('ck_role_dut', …)`) rather than giving up. A script written to the new contract
  names no device literally, so preflight previously reported `UN-RUNNABLE (0/2 links)` — a
  confident wrong negative where the honest answer was "cannot determine".

## 2026-07-30 — Topology contract + minimality; pre-flight topology check

Generated scripts no longer name devices or leave the port link to a FILL slot. `init()`
resolves the DUT from the bench's own role contract (`[misc] ck_role_dut`, read at run time)
and binds its single link through a fixed-frame `_ck_bind_link()` that resolves
`ck_link_<role>`, refuses a silent `(None, None)` portlink, and **asserts the bound port's
media**.

That media assertion matters because the CLI is media-blind: on a 1000BASE-SX port
`speed ?` still offers `10…400000` and `duplex ?` still offers `half`, so a matrix bound to
fibre would record "DUT failed to set speed 100" — a false failure blamed on the product.

**Generation itself reads no bench file.** It targets a *contract*, because a bench-reading
generator silently weakens a test to fit whatever hardware happens to be present. The bound
device set is now a **consequence** of the topology — one link ⇒ exactly one partner, and
the partner *is* that link's far end — so over-declaration is structurally impossible rather
than merely discouraged. (T33235 previously bound 4 devices and 2 links while referencing 1
of each, making the script demand cabling for nothing.)

Also added `tool/pt_preflight.py`, which matches a script's `init_swi`/`init_portlink`
demands (via `ast`) against a bench's `.setup`. `Setup.init_portlink()` returns
`(None, None)` **silently** when a link is undeclared, so a missing *cable* would otherwise
grade as a *script* defect on hardware. Verdicts move with the bench: with only testbox↔DUT
declared it found all three Port (7) scripts un-runnable; declaring the two verified
`swi_a`↔`swi_b` links took that to 2 of 3.

Spec: `ask-ck/pytest-create/TOPOLOGY-PROFILES.md`. Checkers: `tool/pt_profiles.py`,
`tool/pt_preflight.py`, `tool/pt_media.py`.

## 2026-07-29 — Backend module split complete; the objective reaches Generate

**Module split (all 11 commits; commit 6 dropped by decision).** `routers/wizard.py` (2515
lines) became the `routers/wizard/` package — four route modules (`reviews` / `config` /
`synthesis` / `export`) plus `_shared.py`, function bodies moved byte-identical — with
shared concerns extracted to `llm_config.py`, `case_registry.py`, `session_store.py`, and
the `generator/` package.

The coupling fix that motivated it: `pytest_create.py` used to import **six
underscore-private helpers** out of `routers/wizard.py`, so renaming any one silently broke
a different tool. It now imports nothing from there. `export()` decomposed from a 351-line
handler into six named steps, verified byte-identical through the write path. A failed
session write now returns **500** instead of 200-with-work-lost.

**Objective in Generate.** The refined objective is baked into the generated script as a
`# ==== OBJECTIVE ====` header and carried into the Generate prompt, so the model grounds
each verdict in the declarative outcome instead of per-step action/verify text alone. A
5-model comparison judged by opus + vllm-fast (`tool/pt_matrix_judge.py`) confirmed the fix,
and isolated the next bottleneck as sequence-step **`kind` misclassification**.

## 2026-07-28 — Prompts are tested; test traffic stops writing the permanent DB

- `tests/test_prompt_examples.py` **executes the LLM prompts' own code examples** against
  real harvested CLI output in `ck.db`. Where prose and an example disagree, the model
  implements the **example** — several generated-script defects traced back to wrong
  examples in our own files. `tests/_prose.py` keeps such checks from firing on their own
  advice text (that happened 4 times).
- E2E and smoke checks now run against a **throwaway `ck.db` copy** on port 8123 via
  `tool/run_scratch_server.sh`. `ck.db` going dirty is correct when a *person* operates the
  app, but test traffic writing the permanent LFS-committed database is worthless data — the
  old Playwright `webServer: './run.sh --bg'` + `reuseExistingServer: true` attached to the
  real dev server on 8000 and did exactly that. `/health` now reports `db.db_path` +
  `db.is_permanent_db`.

## 2026-07-27 — CLI grounding, fragment-resolver hardening, security review, the test gate

**CLI grounding.** Both the sequence-extraction and generate prompts are grounded in the
real AlliedWare Plus command reference, harvested from `docs.atlnz.lc` into `ck.db`
(`cli_commands` / `cli_command_products`). Root cause it fixes: the prompts demanded "exact
CLI fields" while showing **zero examples**, so *every* model — Opus included — invented a
`speed=1000`/`state=up` schema the switch never prints (real output is `current duplex full,
current speed 1000, current polarity mdix`). Fabricated tokens went **13→0** in sequences
and **57→0** in scripts.

**Fragment-resolver hardening.** The resolver bounds every symbol by exact index `loc` —
else next-unit-start−1, else `loc_total` — replacing a blind `loc[0]+60` fallback that
over/under-captured ~18% of `test_case` entries. Legacy Python-2 fragment code is
deterministically modernized at resolve time via stdlib `lib2to3`; `status="translated"`
guarantees valid Py3 (tab/space normalized + `ast`-verified), untranslatable code ships
as-is with a ⚠ banner, and translated blocks carry a `(py2→py3)` provenance suffix.

**Security posture, full adversarial review.** Server-side objective-HTML sanitizer
(stored-XSS), `llm_config` secret redaction from all browser/disk serializations,
`shlex`-quoted + metachar-validated SSH run command, extended framework-read-only guard,
path-traversal guards on export `case_key` + generated filenames, session-bound agent
bridge, CORS lockdown. **Network defaults corrected (2026-07-27g):** binds `127.0.0.1`
(LAN exposure is now an explicit `HOST=0.0.0.0`), `push_to_zephyr` no longer hardcodes
`--force` (it was disabling the CLI's own "already refined — skip" guard on every push),
and SSH host keys are pinned trust-on-first-use.

**Three-layer test suite + one gate.** Backend pytest (in-process; no mocks, network or
testbox) + frontend Vitest/jsdom + a sparingly-run Playwright E2E, with
`./tool/run_tests.sh` as the single gate. Several backend tests are **structural** — an AST
sweep proves no async handler calls a blocking function unwrapped — so they catch the *next*
regression rather than only the one filed.

**Objective-coverage gate.** Every Zephyr step must map to ≥1 sequence step, enforced on the
Confirm button for *2. Sequence* and *5. Generate*, with an error quoting each untested step
(override: `acknowledge_coverage_gap`).

## 2026-07-23 — PyTest Creator UX + correctness revision

Script Search and Fragments became per-step carousels (one step per screen, step-pill nav);
Cases split into Open/Partial + Complete. The step sequence is classified **setup / verify /
physical / manual**, so physical plug/unplug/hot-swap steps generate an operator-prompt +
wait-for-state-change pattern (the SVT 3009 model) and manual checks generate a `yesNo()` —
**physical steps are in scope, not skipped**.

Also fixed: device-name reconciliation (bind the names fragments actually use), a
**provenance mis-attribution bug** (setup-step renumbering stamped the wrong fragment on the
wrong TestCase), fragment `maps_to` validation, and a positive **NO REUSE** gap marker. The
former **Fit Decision** step was removed — the fixed skeleton made it moot (8 steps → 7).

## 2026-07-22 — Zephyr push button, streaming transport, agent token reporting

- **(22c) Push to Zephyr** button in the Generator's step-6 export actions, with a dry-run
  Preview. Strips a leading `(N)` title group, ensures **version 2.0** (idempotent — bumps
  1.0→2.0, never beyond), uploads objective + steps + `traceability.md` + ART web-links.
  Shells out to `tool/upload_refined.py`, so the server never holds the JIRA token;
  attachments use replace-semantics. All 43 Complete cases pushed + audited to v2.0.
- **(22b) Streaming transport.** The vLLM path now streams (`stream:true` +
  `stream_options.include_usage`), so the HTTP read timeout bounds the gap *between* chunks
  rather than the whole response — the structural fix for `vllm-thinking` read-timing-out on
  the largest-output step (a 30s-read-timeout call ran 21+ minutes without timing out).
- **(22d) Claude agent tokens + model.** The per-user agent lifts `usage`/`total_cost_usd`
  from the `claude -p --output-format json` envelope, so the badge shows real `N in / M out`
  instead of "— tok" (a transport that reports nothing still shows "— tok" honestly). Added
  a Haiku / Sonnet / Opus selector for that mode.

## 2026-07-21 — Standardized generation; vLLM reasoning-model hardening

Generate fills a fixed skeleton template (`templates/pt_script_template.py.jinja`) — one
`TestCase` per verification step with a mandatory per-step logging contract, suite +
per-case `tear_down`, data-driven topology — and lint enforces template conformance.

The OpenAI-compatible path now handles the org models' chain-of-thought: 16k `max_tokens`,
null/truncated-`content` guards with clear errors, and the documented **system+user** message
shape with a JSON-only steer (−35% tokens on real prompts). These are *reasoning* models —
they emit `reasoning_content` before `content`.

## 2026-07-20 — Local LLM, observability, provenance, strict DB-only search

- **Local LLM** login mode (org vLLM, OpenAI-compatible; Fast/Thinking toggle; server-stored
  key in gitignored `secrets.local.json`) became the default, with a **Health check** button.
- **Observability** (dev scaffolding): per-panel debug footer, `N in / M out` token badges,
  per-session log in `CK_server/debug-log/`.
- **LLM Provenance** (permanent): every LLM panel can show/copy the exact prompt and
  **Refresh** it live via a no-send `dry_run` render — 1-for-1 with a real send, zero
  tokens — for pasting into a competing LLM.
- **Strict DB-only search**: literal script code + all semantic vectors ingested; the
  embedding model is bundled and loads offline. The server reads **zero** corpus JSON,
  enforced by `tool/guard_db_only.py`; startup fails fast without `ck.db`. Fixed 3 latent
  bugs (the embed guard never ran; sqlite-vec KNN silently returned nothing; a HuggingFace
  load-time ping).
- Hidden **admin panel** (double-click CK's face) — reset sessions + restart server.
- **(20b) The courier corpora were retired.** `ck.db` became the permanent committed source
  of truth, so the intermediate build inputs (`suite_*_enriched.json`,
  `all_test_suites.json`, `zephyr_cases.jsonl`, the script index/sidecars) were **deleted**
  and the rebuild paths removed. Only the raw Zephyr XML is kept, as a provenance root.
  `tool/build_db.py` remains as provenance and **refuses to run**.

## 2026-07-16 — Data layer moves to SQLite; two-table review UX; ES modules

- **Migration complete (committed A–D):** corpora + sessions served from `ask-ck/var/ck.db`
  with FTS5 keyword + sqlite-vec hybrid/semantic search.
- **Two-table "chosen shortlist"** on the TestLink / Zephyr / ATPyLib steps — candidates
  above, chosen below in insertion order; Confirm reads the **chosen** table only. Keyword
  search is relevance-ranked (title matches outrank body-only hits) and each new search
  re-ranks the whole candidate pool.
- Frontend refactored to browser-native **ES modules** (`static/app.js` → `static/js/`).
- **Repo hygiene:** removed a stray root `zephyr-auto_negotiation.xml` and completed-phase
  enrichment scratch files. (The build-input corpora were *deliberately kept* at the time as
  `build_db.py` input — superseded four days later by 2026-07-20b above, which retired them.)

## 2026-07-15 — Setup and maintenance fixes, from a fresh-machine walkthrough

Found by walking Getting Started on a clean Ubuntu box:

| Fix | Why it was needed |
|-----|-------------------|
| Added `ask-ck/CK-main/requirements.txt` as a mandatory install step | The server crashed with `ModuleNotFoundError: No module named 'fastapi'`. The Python dependencies were never listed anywhere, so a fresh clone had no way to know what to install. |
| Added a virtual-environment step | Isolates dependencies from global/site packages. Optional but recommended — it changes *where* packages live, not how the project runs. |
| Documented Git LFS ≥ 3.3, installed from the git-lfs repo rather than apt | Ubuntu apt ships LFS 3.0.2, incompatible with Git 2.38+; a fresh `git lfs pull` fails with `cannot add to the index - missing --add option?`. It only "worked" on the dev machine because the large files were already materialized, so the smudge step never ran. |
| Documented HTTP-only access and the `0.0.0.0` bind gotcha | Browsers with HTTPS-Only mode auto-upgrade to `https://`, and a plain-HTTP server cannot answer a TLS handshake — a blank `SSL_ERROR_RX_RECORD_TOO_LONG` page. A same-port redirect is impossible: the failure is at the TLS layer, before any HTTP is exchanged. |
| Added `setup.sh`, an idempotent one-shot bootstrap | `run.sh` assumes everything is set up and gives cryptic errors otherwise. It also detects a missing/too-old git-lfs and offers to fix it. **The git-lfs upgrade installs an explicit version** — Ubuntu ESM pins 3.0.2 at a *higher* apt priority (510) than packagecloud (500), so a plain `apt-get install git-lfs` kept the old one. |
| Corrected stale Git LFS paths in `.gitattributes`, then renormalized | After the 2026-07-13 restructure the LFS rules still pointed at the old `data/zephyr_full/…` paths and matched nothing, so `zephyr_cases.jsonl` (53 MB), `index.json` (17 MB) and `suites/testlink_awp.json` (28 MB) were committed as plain Git blobs. `git add --renormalize` re-ran them through the LFS filter. This does **not** rewrite history — old blobs remain in past commits. |
| `run.sh` gained venv auto-activation, foreground/background, and `--stop` | Previously you had to activate the venv by hand and it only ran in the foreground. Background mode detaches into its own session/process group, records `.ck-server.pid`, and appends to `.ck-server.log`. |

## 2026-07-13 — Multi-tool facelift and repository restructure

Renamed to **Ask CK**; the single-purpose drafting tool became a multi-tool workbench with a
sidebar (Generator, PyTest Creator, Test Composer, Zephyr Templating Tool) and a relocated
LLM Configure panel. The repo was restructured at the same time: `drafting-tool/` →
`ask-ck/CK-main/` (+ `CK_server/`), and root `data/`, `refined-cases/` and the process docs
moved under `ask-ck/objective-drafting/`. Historical documents may still reference pre-move
paths.
