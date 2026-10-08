---
verified: 2026-10-09
---
# PLAN — Validation: one generated script, made to run end to end, reviewed, then Finalized

> ## Status (read first)
>
> **PLAN ONLY — nothing built.** Written 2026-10-09 from Terrence's design in that day's
> conversation. It is the second of three plans:
> 1. [`PLAN-agent-sessions.md`](PLAN-agent-sessions.md) (A, first): how Ask-CK starts and talks
>    to a `/test-mode` session.
> 2. **this plan** (B).
> 3. [`PLAN-test-composer.md`](PLAN-test-composer.md) (C): campaigns over a project.
>
> **Depends on A:** Phase 1 (launch + read-only window) before anything here can run. The
> repair conversation (§3) wants A's Phase 3 (W3).
>
> **Supersedes** the Validation half of the 2026-09-28 `PLAN-test-composer.md` (its §1–§2 steps
> 1–5, §2.5 and §7 a, d, f). That plan's text is in git history; what carries over is listed in §1.
>
> **Settled 2026-10-09 (Terrence), not for re-litigation:**
> - the repair edits a scratchpad copy, and overwrites the original **only with the user's
>   approval**;
> - the definition of a clean run (§4);
> - the four Finalize actions and their order (§6);
> - anyone can press Finalize until LDAP or session permissions exist;
> - the grading tier list (memory `grading-authority-tier-list`);
> - UI in **Svelte, in `current/`, Classic and ATUI** (PLAN-test-composer §0).

## 0. The ask — Terrence, 2026-10-09

> *"Validation - this section will be as described previously, for the most part. In this section
> the agent will run the probe, make sure the script's requirements for testing are met by the
> topology, and then execute the script."*
>
> *"If there are errors, the Sentinel has full authority to direct the subagent to change the
> pyscript in order to achieve a running script. Even if the test fails, the first goal is to
> ensure the pyscript runs end-to-end."* — and later: *"Ideally have some conversation with the
> user during the repair to ensure its the right choice."*
>
> *"At the end of the run, the Sentinel shall do a review of the script's logs. ensure the test
> didnt have any false positives or false negatives. Review the connected test-case that the
> script is being created for. Do the tests meet the objectives / test steps? does the script
> make sense for the objectives / test steps? what improvements can we make to it?"*
>
> *"At the end of the run, after any requested edits are made and finalized, and a clean run
> obtained, we shall have a Finalize button…"* (§6).

## 1. What carries over, what changes, what retires

| From the 2026-09-28 plan | Fate |
|---|---|
| Step 1 testbox and connection check | **Changes.** The testbox, consoles, PDU and constraints are page fields collected **before launch** and carried in the hand-off (A §4, D2). The session's own occupancy check and probe replace the server's `check_profile` for this flow. |
| Step 2 bench truth (`bench_probe.py run`, MATCH / MISMATCH / NEEDS-CHECK) | **Kept, run by the session** inside `/test-mode` TRIAGE, not by the server over ssh. A MISMATCH that needs `apply`, a recable or a licence blocks: it is never self-applied (STANDING-ORDERS §4; A §8 item 6). |
| Step 3 the script picker over `generated/` with `provenance.json` | **Kept.** It lists saved scripts that are not yet Finalized. |
| Step 4 `pt_preflight` made visible | **Kept**, run by the session against the probed `.setup`. Its verdict is shown in the window and on the run record. |
| Step 5 the run (`RunManager`, `--noupdate --nodefaultcfg`) | **Changes.** bench-runner runs it, through `/test-mode --from-ask-ck`, with the same flags (memory `framework-run-always-noupdate`). |
| §2.5 results routing (the "New Script?" toggle) | **Simplified.** A Validation run is always a script under test, so its record always goes to `generated/.meta/<group>/<name>/test/<run_id>/`. The toggle is gone. Campaign records are C's. |
| The hand-back into `step7` (`run_result/{key}`) | **Kept as an option** (§8 open 3): the repair now happens in the session, so the creator's Fix-from-run is a second path, not the main one. |
| The creator's Run, Validate and Testboxes panels | **Retire** when Validation ships (slice V4). Trent's Svelte branch already says *"Validating and fixing a script happens later, in Test Composer"* (`GenerateStep.svelte`): the same split. |

## 2. The flow

1. **Pick the script.** A picker over `generated/<group>/<name>.py`. Each row shows its case key,
   its `saved_at` and how many runs it has had.
2. **Say where it runs.** The page fields:
   - testbox;
   - the consoles this session may use;
   - PDU IP and outlets, or "no PDU";
   - session constraints, verbatim.

   They are pre-filled from the seat's last answers (browser storage) and confirmed every time.
3. **Launch.** Ask-CK writes the hand-off (`kind: "validation"`; A §6) and starts
   `/test-mode --from-ask-ck`. The window shows it live.
4. **TRIAGE (the session).**
   - occupancy check;
   - the probe against the deployed `.setup`;
   - `pt_preflight` of the script against that `.setup`.

   RUNNABLE goes on. Not runnable: the session reports the exact change that would unblock it,
   then blocks (no self-apply).
5. **Run, and repair until it runs clean** (§3, §4).
6. **Review** (§5).
7. **The user approves or rejects the edits.** Approved: the repaired copy overwrites the
   original, through the PyTest Creator's own save path (§3).
8. **Finalize** (§6), available once the run is clean and no edit is waiting for approval.

## 3. The repair loop — authority, limits, and the copy

**Authority.** The sentinel may direct bench-runner to change the script to make it run end to end,
*"even if the test fails"*. Bench-runner keeps its full authority within a test (STANDING-ORDERS).

**What may change (proposed line; confirm in §8):**
- **Allowed — mechanics:**
  - imports, syntax, framework API use, timing and waits, console handling;
  - a defaulting command the platform rejects;
  - a missing config step that made a case read UNSUPPORTED.
- **Not allowed — the test's meaning:**
  - removing or loosening a check;
  - asserting a weaker field (memory `configured-vs-current-show-interface`);
  - hardcoding a port or any bench fact (memory `scripts-must-be-hardware-agnostic`);
  - overriding the framework's post-failure power cycle (STANDING-ORDERS §6).
- **Every change** is logged with its reason, as a numbered entry the review and the user both see.

**The copy.** The session edits and re-runs **a scratchpad copy**: the run's workdir and the
session's scratch, never `generated/` and never `/home/st-art/framework`. The original is
overwritten **only on the user's approval** (step 7). That write goes through
`POST /api/pytest-create/save_script/{key}`, the path for user edits, so the creator's
units⇄script hash binding reports the script as edited outside its units
(`pytest_create.py:7453-7497`), exactly as a hand edit would. Nothing pretends the units
produced it.

**Conversation.** *"Ideally have some conversation with the user during the repair."* Before
each repair re-run, the sentinel posts the proposed diff and its reason to the window. With W3
(A Phase 3) the user can answer: agree, object, or redirect. Whether the loop **waits** for that
answer or proceeds and lets the approval at step 7 be the gate is an open decision (§8 open 1).
D5 says campaigns never wait, but Validation is one script and is interactive by design.

**Stopping.** Systematic failures stop the run, not N power cycles (STANDING-ORDERS §6). A repair
that needs a §4 decision (licence, recable, `apply`) blocks with a `NOTIFY`.

## 4. "Clean run" — Terrence's definition

> *"'clean run' means that the script ran with no exception errors, no device errors from config,
> the CLI commands worked, didnt miss a config step to enable a feature and make a test case read
> UNSUPPORTED, no Python Syntax errors, etc. 'clean' here means the script ran with no issues at
> all, contextually or otherwise. It is up to the agentic analysis and the user to determine
> whether or not the script did what the Objectives and Test Steps ask for, whether the script is
> effective at testing what it needs to, and whether it requries further editing."*

So **clean is about the run, not the verdict**: a case may FAIL on a real device fault and the
run is still clean. Clean is judged by the session from the logs and confirmed by the user. It
is recorded on the run as `clean: true` with the reasoning.

## 5. The review

At the end of a clean run the sentinel reviews, **in context** (memory
`terrence-prefers-session-model-as-judge`; one exhaustive pass, memory `review-one-exhaustive-pass`):

1. **The logs:** any false positive (a PASS that proved nothing) or false negative (a FAIL from
   the script, not the DUT).
2. **The case:** read the Zephyr case's objective and test steps. Does each test meet them? Does
   the script make sense for them?
3. **Improvements:** better structure or efficiency *"without reducing the quality of output"*;
   outdated tests to update.

**Authority:** the framework's verdicts stand (grading tier list: a validated script ranks just
under Terrence). The review is analysis and recommendation.

**Where the user sees it:** in the window, conversationally, once W3 exists. Until then a
read-only panel beside the script, with the review's comments anchored to lines and
**Approve / Deny** for the pending edits. *"TBD, pending the plan execution."*

The review is stored with the run record (`review.md`).

## 6. Finalize

Enabled when: the latest run is clean, no edit is pending approval, and the review exists.
**Anyone can press it** (no LDAP or session permissions yet).

**Actions:**
1. **Remove the case from the PyTest Creator's list:** *"i dont want it re-authored there"*.
2. **Zephyr: add to step 1 of the case.** The text goes on the line after the templated
   "attachments" sentence, as an addendum:
   *"This test is now automatable. use script <TITLE> in the ask-ck tool. <LINK>"*.
   `<LINK>` opens the Composer with this script preselected (the URL scheme is C's §5).
3. **Zephyr: version 2.0 → 3.0.** *"The filled out cases would be version 2.0 after the Test
   Composer API load, so just re-use what it has and gut it only to update the version to 3.0
   and add the specific step data."*
4. **Remove the case from the Objective / Test Case Creator's list.**

**Order and failure (Terrence: *"only remove the case after a successful upload"*):**
- **Zephyr first:** 2 then 3, each preceded by an audit line, the zephyr-tool pattern (P3/D14:
  stop and report, no automatic undo).
- **The lists change only after both writes succeed and read back.** A half-done Finalize leaves
  the case visible and the audit log says what landed.

**How (to build):**
- **Step 2 reuses `upload_refined.py`:** `GET rest/atm/1.0/testcase/{key}` then `put_case`, with
  only the step text changed.
- **Step 3's request is not known yet.** It is one capture with the Network tab open while
  creating a new version in Zephyr's UI, done the way §6a of the zephyr plan captured the
  upload requests. Until then step 3 is unbuilt and Finalize is not offered.
- **Steps 1 and 4 are a finalized marker on disk, not a code list.** `finalized_at` (and the run
  id) go in `generated/.meta/<group>/<name>/provenance.json`. Both case lists skip a finalized
  case, beside today's display-only `HIDDEN_CASE_KEYS` (`case_registry.py:43`). No `ck.db`
  change. Deleting the marker brings the case back.

## 7. Records

`generated/.meta/<group>/<name>/test/<run_id>/` holds:
- the hand-off;
- `run.json`: testbox, the `.setup` and its hash, the preflight verdict, parsed cases, `clean`,
  time, tokens;
- the framework log;
- the edit log;
- `review.md`.

The repaired script versions also go here until approved. Finalize adds its audit lines here
too.

## 8. Open decisions for Terrence

1. **Does the repair loop wait for the user's answer** on a proposed edit (W3), or proceed and
   rely on the approval at step 7? Proposed: proceed on the copy; the approval is the gate.
2. **The "what may change" line** in §3: as written?
3. **Fix-from-run in the creator** (`run_result/{key}` → `step7`): keep it as a second repair path,
   or retire it with the Run panel?
4. **Retiring `pt_exec`'s server-side run path.** Once Validation runs through `/test-mode`,
   the server's `RunManager` and its testbox profiles have no caller in the UI. Keep them for
   tests and headless use, or remove them in V4?
5. **Finalize's step 3**: confirm that a new Zephyr *version* (not an edit of the version
   field) is what 3.0 means. The capture will show what the UI does.

## 9. Slices — each gated, each mutation-checked, each one deploy

- **V0 (no code):** the Zephyr "new version" capture (§6, step 3).
- **V1:** script picker + the setup fields + launch (`kind: validation`) + the read-only window,
  on A's Phase 1.
- **V2:** run records in `.meta/…/test/`; the edit log; approve → `save_script`.
- **V3:** the review (panel first, conversation when W3 lands); Finalize (marker, both Zephyr
  writes, both lists).
- **V4:** retire the creator's Run / Validate / Testboxes panels (and per §8.3–8.4, the endpoints).

Server changes follow the branch-and-merge procedure (SERVER-README). UI is Svelte in `current/`,
built the way the ZTT pilot establishes (PLAN-test-composer §6).

## 10. Invariants

- `ck.db`: no schema change. The finalized marker and run records are files.
- `/home/st-art/framework` read-only; edits happen in the run's workdir copy.
- Every run: `--noupdate --nodefaultcfg`; the standing orders and bench gates are not bypassed.
- Scripts stay hardware-agnostic; a repair never hardcodes a bench fact.
- Zephyr writes: audit line first, read back after, no automatic undo.
- Tests never write the permanent `ck.db`.
