---
verified: 2026-10-09
---
# PLAN — Test Composer: run a project's runnable cases on a topology template

> ## Status (read first)
>
> **PLAN ONLY — nothing built. Rewritten 2026-10-09** from Terrence's design in that day's
> conversation. It is the third of three plans:
> 1. [`PLAN-agent-sessions.md`](PLAN-agent-sessions.md) (A, first): how Ask-CK starts and talks
>    to a `/test-mode` session.
> 2. [`PLAN-test-validation.md`](PLAN-test-validation.md) (B): one script made to run, reviewed,
>    Finalized.
> 3. **this plan** (C).
>
> The 2026-09-28 version of this file (*"the run tool in five steps"*) is superseded. Its
> Validation half moved to B. Its template storage decision, its requirements aggregate and
> its reuse of `PLAN-pytest-creator.md` §8 carry over here (§3). The old text is in git
> history.
>
> **Settled 2026-10-09 (Terrence), not for re-litigation:**
> - **C-D1 — all new UI in Svelte, in `current/`, on both the Classic and ATUI pages.** That
>   covers the Composer, Validation and the ZTT port. It does not touch Trent's Svelte app:
>   *"lets not overwrite what Trent is doing, you doing it first will make it easier for him to
>   do his work later."*
> - **C-D2 — ZTT is ported to Svelte first, as the pilot, after the plans are written** (§6).
> - **C-D3 — ZTT records its uploads**, and a project can also be added by its wiki link (§2.1).
> - **C-D4 — email when done** goes through the server's postfix (A §8; verified 2026-10-09).
> - **C-D5 — after-hours runs** start from the seat agent polling the server (A D3).
> - **C-D6 — the grading tier list** (memory `grading-authority-tier-list`). *"These tests are
>   non-negotiable results, the agent wont override them."*

## 0. The ask — Terrence, 2026-10-09

> *"This will be separate from Validation, this will be the proper Test Composer tool."*
>
> - Pick a **Project** from a dropdown populated by the Zephyr Templating Tool (ZTT): *"Because we
>   created the project with ZTT, we should know the plans, cycles, and test-cases that are
>   attached to them."* The user also names the **test bench** in a field.
> - Pick a **topology template** (SetupA, SetupB, …), *"already linked to test-cases so we know
>   how many we can run in that topology. Selecting the setup should return how many test cases
>   are runnable with that topology."*
> - **Validate**: *"The agent will run the bench probe as usual, but this time it will be diffed
>   against the selected templated .setup file."* The user sees *"either a Green Checkmark, or a
>   list of differences that the agent found for the user to change, based on agent feedback."*
> - After the green check: *"do a quick GET to populate what is actually IN the project, and then
>   produce an identical frame to the ZTT hierarchy … filtered to match the topology file,
>   listing what cases are runnable. The checkboxes here are going to be what we are going to ask
>   the /test-mode agent to run."*
> - **Start** launches `/test-mode` on the ticked cases, with a live window (A §7).
> - **Results**: *"a table under PASS or FAIL or whatever the verdict is"*:
>   - sorted into test cycles, with *"a clear visual indicator of whether they were PyScripts or
>     manual tests"*;
>   - clickable logs (framework logs for scripts, `/create-logs` output for manual cases);
>   - a **Feedback** button where *"the pytest was run AND the agent encountered an error OR the
>     test failed"*;
>   - at the top, *"a clear numerical readout of Results, the amount of time the run took, and
>     how many tokens it took."*
> - From the ART tools (author's permission for **these two only**: the Test Runner and the Log
>   Viewer; *"please do not wander off or edit their data in any way"*): a Log Viewer port, and
>   *"do not reboot between tests", "skip getting a new build", and "email when done"* sorted out
>   now. A **Cron option** for runs that need multiple restarts, run after hours.

## 1. The flow

| # | Step | Who | Built on |
|---|---|---|---|
| 1 | **Project** (dropdown or wiki link), **variants** (checklist when several), **test bench** field | page + server | §2.1 |
| 2 | **Template** dropdown, with "N of M cases runnable" | server | §2.2 |
| 3 | **Validate**: probe vs the chosen template; a green check, or the differences with the agent's advice | session (A) | §2.3 |
| 4 | **The project tree**: a live GET, drawn like ZTT, filtered to runnable; tick boxes | server | §2.4 |
| 5 | **Start**: hand-off `kind: "composer"`, `/test-mode --from-ask-ck`, live window; run options | session (A) | §2.5 |
| 6 | **Results table**: by cycle, by verdict, script/manual marker, logs, Feedback, totals; Accept results | server + page | §2.6 |

## 2. The steps

### 2.1 Project, variants, test bench

Two ways in, both kept (*"because i want this to be backwards-compatible"*):

- **Templated Project** (dropdown). **C-D3: ZTT records each upload.**
  - **What:** project, product, version, team subfolder, project number, and each cloned plan and
    cycle with its new key and id.
  - **Where:** a record file beside the audit log, `ask-ck/db/zt-uploads.jsonl`, one line per
    finished family. The audit log stays an audit log.
  - **First entry:** IE570's Industrial Features upload of 2026-10-07 (P3266 / C8470), taken from
    the audit log once.
- **Zephyr Project Link** (URL field): the project's wiki page.
  - **What is read:** its **"Test Results:"** cell, through `zt_wiki.py`'s page reader (GET
    only). The cell is not parsed today; this is new.
  - **The cell can list several plans, one per variant,** each with its status (Passed, Tested,
    On Target, …).
  - **More than one plan → a checklist of variants** for *this* run. *"Variance within product
    families is very common … They are often entirely different chipsets and hardware, and as
    such, could have different tests that apply between variants … the test strategies arent
    always up-to-date with new variants, and the TPS can also lag behind as well."*
  - The plans for the ticked variants are then fetched from Zephyr by GET.
- **Test bench:** a field (`tbNNN`), which also feeds the hand-off.

### 2.2 Template and runnable count

- **Templates** live at `ask-ck/functions/test-composer/templates/<setup>/`: `<setup>.setup` plus
  one `<setup>.<device>.cfg` per device (Terrence, 2026-09-25). Today `setup-a` and `setup-b` hold
  **empty placeholder files**, a reference location only.
- **How templates will be authored (Terrence):** *"after i run enough tests i shall aggregate that
  data into a series of templates and then attempt to integrate as many of them as possible into
  as few .setup permutations as possible (adjusting config and shutting down unused ports is a
  non-issue, we just need the physical setup to be correct)."*
- **Testing uses mock data:** *"We can fill it with mock data when we get to testing to ensure we
  can handle swapping between two templates and how it can adjust the recommendations."*
- **Runnable count, by case kind:**
  - **Script cases** (a Finalized script exists): computed. `pt_preflight.parse_script(script)`
    is checked against the template's `.setup` (`pt_preflight.check`). This is the old plan's
    requirements aggregate, now used per template.
  - **Manual cases:** declared. A `cases.txt` (or similar) in the template's directory lists the
    case keys it supports, authored with the template. Open decision §8.1.

### 2.3 Validate — probe against the template

- **How:** the session runs `bench_probe.py --box <TB> run --template <setup>.setup`. The
  `--template` option exists (device-testing `bench-setup/bench_probe.py:1836`).
- **Result:**
  - **MATCH** → green check;
  - **MISMATCH / NEEDS-CHECK** → the differences, each with the agent's plain-words advice
    ("cable port1.0.3 of swi_a to tb eth2").
- **The user changes the bench, not the session.** A change STANDING-ORDERS §4 reserves (`apply`,
  recable, licence, root) is never self-applied (A §8 item 6). The user changes it and presses
  Validate again.
- **Bench questions (PDU and outlets, consoles, constraints)** are page fields filled before
  Validate and carried in the hand-off (A D2).

### 2.4 The project tree

- **Live, not stored:** after the green check, a GET of what is actually in the project (plans,
  cycles, cases), drawn with **ZTT's tree component** (the same Svelte component after the pilot,
  §6), so it looks identical.
- **Filtered** to the cases runnable on the template.
- **Each case shows:**
  - **script / manual**: a script case has a Finalized script (B §6). Its kind comes from the
    Objective and PyTest tools' records: *"eventually all of these tests will have details
    created by the previous Objective and PyTest tools, so … we should know all the test steps
    and whether or not they are automatable with py scripts."*
  - **Previously Run**: shown when an earlier run record has the same project, the same case
    and the same **release version** (*"IF the Release Version is the same as the previous
    session"*).
- **The ticks are the run list.**

### 2.5 Start, the window, run options

- **Start** writes the hand-off (`kind: "composer"`, A §6): every ticked case with its `kind`
  (script or manual), its cycle, and its script path for script cases. Then it launches
  `/test-mode --from-ask-ck`.
- **The live window** is A's W1 and up.
- **D5 applies:** a campaign never stops to wait. It sends an informative email, works past the
  problem, or BLOCKs that case and moves on (A §8).
- **Run options:**

| Option | What it means here | Source |
|---|---|---|
| Skip getting a new build | **Always on, not an option.** Every Ask-CK run is `--noupdate --nodefaultcfg` (memory `framework-run-always-noupdate`). ART's checkbox controls the web tool's own build fetch. `rtmt` itself always passes `--noupdate`. | `rtmt` read 2026-10-09 |
| Do not reboot between tests | ART wires it to `rtmt -N`, which adds `--noconf -p` **from the second repeat** (skip `configure()` and the startup power cycle). It matters only for repeat runs. Between cases, the framework's post-failure power cycle is **accepted and not overridden** (STANDING-ORDERS §6). Shown as information, not a switch, until repeat runs exist. | `/home/st-art/tools/run_test_many_times.py` |
| Email when done | Address field (pre-filled from the seat). The server sends via postfix → `int-smtp.atlnz.lc`, from `do-not-reply@alliedtelesis.co.nz`, with a small summary and a link. Also used for D5 notices. | verified 2026-10-09 |
| Run after hours (cron) | A start time. The seat agent polls the server and launches at that time (A D3). The page says the seat must be on and logged in. | A §8 |
| Extra framework flags | **Later**, as needed: *"eventually we will be able to integrate more of the functions this currently has (as required, like extra flags)."* | — |

**Borrowed from ART's Test Runner** (behaviour only, no code):
- the **share link** that pre-fills the form;
- **attach to an active run**;
- a **dry run** ("show the hand-off and the command, run nothing");
- the **Follow** toggle on the live window.

### 2.6 Results

- **Grouping:** one table, **grouped by test cycle**, columns by verdict (PASS, FAIL, UNSUPPORTED,
  BLOCKED, NOT TESTED, …), and a **script / manual** marker on every row.
- **Logs, click to open:**
  - **script cases:** the framework log (non-negotiable verdicts, C-D6);
  - **manual cases:** the final log written by `/create-logs --auto` (device-testing `83c0880`).

  The viewer opens in the page (side by side or expanding in the row, *"as long as the data is
  there, we can fix the UI later"*).
- **The viewer is a port of the ART Log Viewer's design:**
  - two panes, where any file can go in either pane to line up timestamps;
  - the tail loads first, then "load earlier";
  - download one file or the set;
  - deep links;
  - `.tgz` extraction on demand.

  It reads our records, read-only: device-testing's `<TB>/<FAMILY>/<group>-<STAMP>/` (stored by
  testbox, as today) and this run's own directory.
- **Feedback** appears on a script case that FAILed or where the agent hit an error. It is a
  separate LLM call on the seat's chosen backend: RCA, script feedback, by-the-ways, with the log
  and the script in context. The reply is stored with the run.
- **Grading:**
  - the user can re-grade any row (they are top of the tier list);
  - a manual case's re-grade re-runs `/create-logs --auto <queue> <id>`;
  - a script case's framework verdict is shown as-is, and a re-grade is recorded beside it, not
    over it.
- **Accept results:** deletes the campaign's `work/` folders (*"we may require the evidence"*,
  so only on Accept). Ask-CK's server does not write in device-testing, so Accept asks a session
  there to do it. The mechanism comes from A.
- **Header readout:**
  - result counts per verdict;
  - wall-clock time;
  - tokens: from the session's `result` line, falling back to `/create-logs`' per-case
    measurement (A §8, U4).

## 3. Carried over from the 2026-09-28 plan

- **Template storage:** `templates/<setup>/<setup>.setup` + `<setup>.<device>.cfg` (one per
  device; one per stack).
- **`PLAN-pytest-creator.md` §8.2** (templates are run-time only; generation never reads a bench
  file), **§8.6** (record the template's text hash on the run) and **§8.7** (verify a declaration
  against the bench; never rewrite it from the bench).
- **The requirements aggregate** (`GET /requirements`: every Finalized script's demands, unioned)
  is now also the input to Terrence's template design: *"what a bench must provide for the
  whole set to be runnable."*

## 4. API sketch — under `/api/test-composer`

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/projects` | templated projects (from `zt-uploads.jsonl`) |
| `POST` | `/projects/from-wiki` | `{url}` → the Test Results cell's plans and variants |
| `GET` | `/projects/{id}/tree?plans=…` | live GET of plans → cycles → cases |
| `GET` | `/templates` | templates with per-template runnable counts for a project |
| `GET` | `/requirements` | the aggregate of every Finalized script's demands |
| `POST` | `/runs` | write the hand-off and record the run; the seat launches it (A) |
| `GET` | `/runs/{run_id}` | the run record, results table, totals |
| `GET` | `/runs/{run_id}/logs/…` | Log Viewer reads: list, tail, earlier, download, extract |
| `POST` | `/runs/{run_id}/feedback/{case}` | the Feedback call |
| `POST` | `/runs/{run_id}/regrade/{case}` | a re-grade |
| `POST` | `/runs/{run_id}/accept` | Accept results |
| `GET` | `/composer?script=…` | the deep link Finalize puts in Zephyr (B §6) |

## 5. Deep link for Finalize

B's Finalize writes into Zephyr step 1: *"…use script <TITLE> in the ask-ck tool. <LINK>"*.
`<LINK>` = `http://10.33.22.17:8000/?panel=composer&script=<group>/<name>`. It opens the
Composer with the script's case preselected in step 4 once a project and template are chosen.
**The host part is the server of record** (memory `askck-lan-hosting`). If the server ever
moves, old links in Zephyr break, so the link should go through a stable name (open §8.5).

## 6. UI — Svelte in `current/`, ZTT first

**Decision C-D1.** Components are written in Svelte (versions matched to Trent's branch:
`svelte ^5.57`, `vite ^8.3`, `@sveltejs/vite-plugin-svelte ^7.3`, so they lift over). They are
compiled and mounted into panels of `current/`, on both `index.html` (Classic) and
`restyle/index.html` (ATUI). The component reads `<html data-ui="atui">` the way `shared/ui.js`
does.

**Proposed shape, which the pilot proves:**
- **Source:** `ask-ck/frontend/ck-main/current/svelte-src/` (its own `package.json` and
  `vite.config.js`). **Not** `ck-main/svelte/`, which is Trent's.
- **Build output:** `current/islands/<name>.js` + `.css`, **committed**, because there is no CI and
  the working tree is production. The gate gains a check that the committed output matches a
  fresh build.
- **Mounting:**
  - each panel has one mount element (`<div id="zt-root">`), present in both HTML files, so
    `tests/test_restyle_parity.py` holds;
  - `main.js` imports the island's mount function, and the existing nav and action registry keep
    working.
- **Tests:** component tests in `tests/js/` under Vitest, which gains the Svelte plugin; the
  existing 392 tests are unchanged.
- **Cache:** the built file is served with `?v=N` cache-busting as today (README convention 4).

**Pilot: ZTT** (608 lines in `current/zephyr-tool/zephyr-tool.js`, one page, `zt-page.spec.js`
covering it).
- **Done when:** it reaches feature parity on both UIs, the old module is removed, and the build,
  serve and test path is proven.
- **What the Composer reuses from it:** the tree component and the page patterns.

## 7. Slices — each gated, mutation-checked, one deploy

- **Z1 — the ZTT Svelte pilot** (§6). Needs nothing from A.
- **C1 — projects:**
  - ZTT records uploads (`zt-uploads.jsonl` + the backfill);
  - the dropdown;
  - the wiki link with the Test Results cell parser and the variants checklist;
  - the test bench field.
- **C2 — templates:** the template picker, the runnable count (script cases computed, manual cases
  declared), mock templates to exercise swapping.
- **C3 — Validate:** the probe against the template through A (launch + W1), the green check or
  the differences.
- **C4 — the tree, Start and run options:** email, schedule, share link, dry run.
- **C5 — results:** the table, the Log Viewer port, Feedback, re-grade, Accept results, totals.

C3 onward needs A's Phase 1. Scheduling needs A's Phase 4.

## 8. Open decisions for Terrence

1. **Manual cases on a template:** declared per template (a case list in the template's
   directory), or inferred some other way?
2. **ZTT upload record:** a file (`zt-uploads.jsonl`, proposed) or a `ck.db` table?
3. **Previously Run match key:** project + case + release version (proposed)? Is "release
   version" the Zephyr folder version (e.g. `5.5.6-2`) or the build?
4. **Feedback backend:** the seat's chosen LLM (proposed), or always Claude?
5. **The Finalize deep link's host:** the IP (works today), or a DNS name that survives a move?
6. **Accept results:** once per campaign (proposed), or per group?

## 9. Invariants

- `ck.db`: no schema change proposed (records are files; §8.2 open).
- Ask-CK writes only in Test-cases. device-testing is read, and changed only by its own sessions
  (the write boundary).
- `/home/st-art/framework` read-only. Every run uses `--noupdate --nodefaultcfg`. The standing
  orders and bench gates apply to launched campaigns exactly as to typed ones.
- Scripts never read a bench; templates are run-time only.
- The ART tools: reuse the design of the Test Runner and the Log Viewer only. Never call their
  APIs to change anything, never touch their data.
- Zephyr: GET for the tree. The only writes in these plans are B's Finalize (audit first, read
  back after).
- Tests never write the permanent `ck.db`.
