---
verified: 2026-09-28
---
# PLAN — Test Composer: the run tool in five steps; the PyTest Creator ends at Save

> ## Status (read first)
>
> **PLAN ONLY — nothing built.** Terrence, 2026-09-28: *"Definitely a plan first."* Every
> "today" claim in §1 was checked against the code that day. The decisions Terrence took
> while asking for this are in §0 and are settled; §7 lists the ones still open.
>
> Supersedes, in part, `PLAN-pytest-creator.md` §8 (server-side setup templates, designed
> 2026-09-01): see §3 for what is kept and what his later decisions replaced.
>
> **2026-09-28 evening — new open point (g), for §7:** a tb470 run is now dispatched through
> device-testing's `/test-mode` (one session = sentinel + `bench-runner` subagents; `bench-runner`
> gate 8 refuses a dispatch that does not say `sentinel: parent` or name a live peer sentinel).
> §2 step 5 "Run" must decide how the Composer's run reaches the bench: (1) the server run path
> (`pt_exec`) with no sentinel — allowed by gate 7 but it runs none of the bench gates; (2) hand
> the script to `/test-mode` (a device-testing session) and read the result back via
> `run_result/{key}`; (3) the Composer's own agent dispatches `bench-runner` and arms the kit
> itself. Undecided; Terrence's call.

## 0. The ask — Terrence, 2026-09-28

The final form of the UI:

1. Identify the test box, check the connection works.
2. Determine whether the `.setup` on the test box matches the actual topology ON the test box.
3. Identify the script to test.
4. Determine whether the topology requirements of the script match the `.setup`.
5. Run the script on the test box.

And the decisions that frame it:

- **The Run panel is deprecated.** All five functions move into the Test Composer, *"as this
  is literally what its supposed to do."* **Confirm and Save to generated/ are the last steps
  of the PyTest Creator.**
- **Templates come later.** *"EVENTUALLY, we will create a template pair that the current file
  deployed on the box will compare against. Currently we need to create scripts to aggregate
  enough topological requirements to determine what that setup template should look like."*
- **Where results go.** A **"New Script?"** toggle changes the destination. Default:
  `test-composer/runs/<date of run>/<test>.log`. With the toggle on: into the script's own
  `.meta/` directory, a new `test/` beside `history/`. And *"the composer should hand the
  failure back to the pytest handler somehow, probably back to the summary page for the
  repair loop to handle."*
- Reuse what §8 already settled *"unless ive directly contradicted it, in which case, lets
  discuss. maybe the original is better."* (§3.)

## 1. What exists today, and where each piece goes

| Step | Today | Where | Goes to |
| --- | --- | --- | --- |
| 1 Testbox | profiles CRUD + `check` (`pt_exec.check_profile`), the Testboxes panel; `secrets.testboxes.json` (0600) | PyTest Creator | **moves** to the composer, unchanged |
| 2 Bench truth | **nothing in the server.** device-testing's `bench-setup/bench_probe.py run`, run by hand ON tb470: reads every console, regenerates `bench-state.md`, diffs its ```setup fence against the deployed `tb470.setup`; exit 0 MATCH / 1 MISMATCH / 2 NEEDS-CHECK; ~2 min | device-testing | **new**: the composer runs it over ssh and shows the result (§2.2) |
| 3 Script | only the open case's session script | PyTest Creator Run panel | **new**: a picker over `generated/` (§2.3) |
| 4 Requirements | `pt_preflight` — runs hidden inside Run; blocks or is overridden ("run anyway", recorded) | `pt_exec._preflight_gate` | **moves** and becomes a visible step; **new**: the requirements aggregate (§2.4) |
| 5 Run | `run/{key}`, `RunManager`, `--noupdate --nodefaultcfg`, log fetch, `parse_framework_log`, per-case PASS/FAIL | PyTest Creator, session `step7` | **moves**; results routing is **new** (§2.5) |
| — Validate | `validate/{key}` (all PASS → `provenance.json` stamped), the Validate panel, `confirm_step 8` | PyTest Creator `step8` | **retires** with the Run panel; the composer stamps provenance (§7 a) |
| — Fix from a run | `fix_script` / `fix_units` read `step7.runs[-1]` + `failure_excerpts` | PyTest Creator | **stays**; the composer hands the run back into `step7` (§2.5) |

Nothing here touches `ck.db`'s schema: the composer's state is files (§8).

## 2. The five steps, as the composer

The composer is **not a case tool**. It has no `PtSession`; its selections (testbox, script,
toggle) live in the tab (localStorage, per-viewer convenience) and its records on disk under
`ask-ck/functions/test-composer/runs/`. Each step is enabled by the one before it, the way the
creator's confirm gates work, but without confirms: the state is the last result on screen.

### 2.1 Testbox — moved

`GET/POST/DELETE /api/test-composer/testboxes`, `POST …/{name}/check`. Same profile shape,
same secrets file, same redaction. The creator's Testboxes panel and endpoints go in slice S3.

### 2.2 Bench truth — new

"Does the `.setup` on the box match what is cabled?" is exactly `bench_probe.py run`. The
composer does not re-implement it (one writer per repo: Test-cases calls device-testing's
tool and never edits it). `POST /api/test-composer/probe/{testbox}` runs, over the profile's
ssh, the command the profile names — for tb470
`python3 /home/terrenceb/claude/device-testing/bench-setup/bench_probe.py run` — captures
stdout and the exit code, and reports **MATCH / MISMATCH / NEEDS-CHECK** with the diff text.
Long-running, so it is a background job with a status poll like a run.

Three facts the step must respect, all from the probe's own docstring:

- it **opens every console** (`/dev/u0`–`u6`): refuse to start while a run is active on that
  testbox, and say that a console another operator holds will read as absent;
- it **switches `lldp run` on** for a device that had it off (running-config only, restored
  after) — a device-state change. The panel states it before the button is pressed
  (the bench-runner agent asks first; the composer's equivalent is the disclosure);
- it is **tb470's** tool: the profile gains an optional `probe` command. A profile without one
  reads *"no bench probe for this testbox"* at step 2, and step 4 falls back to the deployed
  file fetched by sftp.

When the probe MATCHes, `bench-setup/tb470.setup.current` is the file step 4 reads (the
always-current local copy `pt_preflight`'s own usage names). MISMATCH does not block step 5
— it is information for the operator, and `apply` stays a hand action in device-testing.

### 2.3 Script — new

`GET /api/test-composer/scripts` lists `generated/<group>/<name>.py` with what
`.meta/<group>/<name>/provenance.json` knows: case key, `saved_at`, iterations, validated.
Picking one binds the run's files the way `run/{key}` binds them today: the script, the
group's `library_<family>.py`, and the media helper (`_media_helper_source()` — every frame
imports it). The **"New Script?"** toggle sits here, default off (§7 d).

### 2.4 Requirements — moved, plus the aggregate

`POST /api/test-composer/preflight` = `pt_preflight.preflight_text(script, setup)` for the
chosen script against the step-2 file, rendered as its own page: RUNNABLE or the problems,
with the "run anyway" override recorded on the run as today.

**The aggregate (Terrence's point 1).** `GET /api/test-composer/requirements` runs
`pt_preflight.parse_script` over every saved script and unions the demands — link roles
(`tb`, `copper`, `fibre`, `cusfp`, optional or required), legacy `init_portlink` pairs, power
— per group and overall, with the scripts that ask for each. That table IS the shopping list
for the template pair (§3): what a bench must provide for the whole set to be runnable. Pure,
offline, no hardware; it is `PLAN-pytest-creator.md` §8.4's *"which profiles does nothing I
have implement?"* without the retired `[misc]` claims.

### 2.5 Run — moved, results routed

`POST /api/test-composer/run` starts `RunManager` exactly as today (workdir, sftp, the
run flags, log fetch, parse). What changes is where the record lands:

| toggle | destination | contents |
| --- | --- | --- |
| off (default) | `ask-ck/functions/test-composer/runs/<YYYY-MM-DD>/<test>.log` | the framework log; beside it `<test>.stdout.txt` and `<test>.run.json` (profile, setup + its hash, preflight verdict, parsed cases, exit code). A second run of the same test the same day gets `<test>.<HHMMSS>.log`. |
| **New Script?** on | `generated/.meta/<group>/<name>/test/<run_id>/` — a new `test/` beside `history/` | the same three files |

**Hand-back to the repair loop (New Script only).** `provenance.json` names the case key, so
after a New-Script run finishes the composer calls
`POST /api/pytest-create/run_result/{key}` with the run record. The creator appends it to
`step7.runs` — the list `fix_script`, `fix_units` (`failure_excerpts`) and the Summary page
already read — so the Summary page shows *"last run: N of M cases FAIL — Fix from run"* and
the repair loop works unchanged. `step7` stays in the session model as the data holder; its
panel goes. The creator never starts a run.

A run with the toggle off is a bench result, not a script under repair: nothing is handed
back and nothing in `.meta/` changes.

## 3. Templates — later; what §8 still says, and what Terrence's later decisions replaced

Kept from `PLAN-pytest-creator.md` §8 (2026-09-01):

- §8.2 — templates are **run-time only**; generation never reads a bench file; no `ck.db`
  change. Unchanged.
- §8.6 — the run wiring: upload the chosen template's `.setup` into the workdir, `-s` the
  bare name, and **record the template's text hash on the run**. Reused as written.
- §8.7 — verify a declaration against the real bench, never rewrite it from the bench. The
  probe's `diff` IS this; §2.2 is its first use.

Replaced:

- §8.3 storage (`pytest-creator/setups/` shared + `ask-ck/db/setups/` personal) → **Terrence
  2026-09-25**: pairs live in `ask-ck/functions/test-composer/templates/<setup>/` as
  `<setup>.setup` plus one `<setup>.<device>.cfg` per device (one per stack). The personal
  location is dropped unless he wants it back.
- §8.4 `[misc]` profile claims → retired 2026-09-21 (framework discovery). Matching is
  `pt_preflight` alone; the aggregate of §2.4 replaces the claims table as the way to know
  what a template must provide.

When enough scripts exist to draw the template, step 2 gains a second mode: the probe's
`diff` against the **template** instead of the deployed file, and a run starts by loading the
template's device configs (device-testing's `restore_cfg.py` does this today by hand; whether
the composer drives it is a decision for that day, not this plan).

## 4. API sketch — all under `/api/test-composer`

| Method | Path | Purpose |
| --- | --- | --- |
| `GET/POST/DELETE` | `/testboxes`, `/testboxes/{name}` | profiles (moved) |
| `POST` | `/testboxes/{name}/check` | connection check (moved) |
| `POST` / `GET` | `/probe/{name}`, `/probe/{name}/{job}` | run the bench probe; poll it |
| `GET` | `/scripts` | saved pairs with provenance |
| `POST` | `/preflight` | `{testbox, script}` → the preflight report |
| `GET` | `/requirements` | the aggregate of every saved script's demands |
| `POST` / `GET` | `/run`, `/run/{run_id}` | start a run `{testbox, setup, script, new_script, ignore_preflight}`; poll |
| `GET` | `/runs?date=` | the day's records |

And one on the creator: `POST /api/pytest-create/run_result/{key}` (§2.5).

## 5. Frontend

`panel-tc-1` … `panel-tc-5` replace `panel-tc-tbd`; `nav.js` `PANEL_META` and the sidebar
accordion get the five entries; `main.js` keeps `loadToolStatus('test-composer', …)`. The
Run, Validate and Testboxes code in `pytest-creator/pytest.js` moves to
`test-composer/composer.js` (the module boundary the README asks for). The creator's Summary
page gains the *last run* line and the *Fix from run* button it already has the data for.
Vitest covers the routing and the result-destination logic; the manual checklist covers the
panels (memory `user-prefers-manual-ui-testing`).

## 6. Build order — slices, each gated and mutation-checked, each one deploy

- **S1 — the move.** Testboxes + Run under `/api/test-composer`, `runs/<date>/` routing, the
  five-panel shell with steps 2 and 4 as placeholders. The creator's Run/Validate/Testboxes
  panels are hidden; their endpoints stay until S3 so nothing in flight breaks.
- **S2 — steps 3 and 4.** The script picker, the visible preflight, the requirements
  aggregate, the New-Script destination.
- **S3 — the hand-back, and the retirement.** `run_result/{key}`, the Summary page's run
  line, then the creator's Run/Validate/Testboxes panels and endpoints are removed; `confirm
  7/8` go; `validate`'s provenance stamp moves to the composer.
- **S4 — step 2.** The probe job, the profile's `probe` command, the disclosures.
- **S5 — templates.** Its own section when the aggregate says what the pair looks like.

S1 and S3 change `CK_server/*.py`, so they go through the branch-and-merge procedure
(SERVER-README, "Changing the backend of the hosted server").

## 7. Decisions still open for Terrence

- **(a) Final Validation's home.** Proposal: the composer stamps `provenance.json`
  (`validated_at`, `validated_run_id`, `validated_profile`) when a New-Script run passes every
  case; the creator's Validate panel and `confirm_step 8` retire with the Run panel.
- **(b) The probe's device-state change.** Disclosure on the panel (proposed), or an explicit
  confirm click like the admin panel's actions.
- **(c) Retention** of `runs/<date>/`: keep everything (proposed; it is small text), or prune.
- **(d) "New Script?"** default off, and the exact wording on the toggle.
- **(e)** One run at a time **per testbox** (proposed) rather than per case as today.
- **(f)** Whether a run with the toggle off may target a script that has an open creator
  session (proposed: yes; it just does not hand back).

## 8. Invariants this must not break

- `ck.db` gains no table: composer records are files under `test-composer/runs/` and
  `generated/.meta/…/test/`; the hand-back reuses the session's existing `step7`.
- `/home/st-art/framework` read-only; the workdir guard (`_assert_write_allowed`) moves with
  the run code.
- Generation never reads a bench file (`TOPOLOGY-PROFILES.md`); the composer is run-time only.
- Every hardware run launches with `FRAMEWORK_RUN_FLAGS` (test pinned).
- The write boundary: the composer **calls** device-testing's probe and reads its
  `tb470.setup.current`; it never writes into that repo.
- Tests never write the permanent `ck.db`; composer tests use `tmp_path` for records and the
  in-process fakes `pt_exec`'s tests already use.
