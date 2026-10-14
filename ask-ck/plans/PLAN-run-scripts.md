# PLAN — Run Scripts: run validated scripts on a bench, several at once, from a shareable link

> ## Status (read first)
>
> **PLANNED 2026-10-15, nothing built.** Written from Terrence's design in that day's
> conversation. It is a fourth Test Composer page beside [`PLAN-test-validation.md`](PLAN-test-validation.md)
> (B) and [`PLAN-test-composer.md`](PLAN-test-composer.md) (C), and depends on
> [`PLAN-agent-sessions.md`](PLAN-agent-sessions.md) (A) exactly as they do.
>
> **Known gap, deliberately left out (Terrence 2026-10-15):** the results table is filled from
> `RESULT` markers, and the two newest real runs (2026-10-13 `1223-val-3ede`, `1454-val-43dd`)
> recorded none. Until that is fixed, this page's results table will be empty, the same as
> Validation's. *"write this up as a plan as-is, we will fix the results later. having some
> discussions around that now."*
>
> **Decided 2026-10-15 (Terrence), §7:**
> - **R-O1 → wait for V0:** the list shows finalized scripts only. *"Ill be finalising a script
>   soon, then we can test it."*
> - **R-O2 → one-off start:** a one-off start time only.
> - **The `scripts` kind and the share link:** approved as written.
> - **Sources:** they come from `ck.db`. ART is refreshed by pulling the framework. Where the SVT
>   and Legacy scripts come from is for Terrence to track down (§4).

## 0. The ask — Terrence, 2026-10-15

> *"I want another module, where we can run single-scripts, but without the baggage of
> Validation. I want the same features of selection, but i want the dropdown to be composed of
> the scripts in /generated/ and be able to select multiple scripts to run at once.
> Additionally, i want us to be able to create a link with the settings pre-defined, so we can
> share it with others and repeat runs on the same test box with the same script. The results
> should still return a /create-log, should still show run logs, etc."*

The design in §2 was proposed back and accepted (*"yes, that sounds perfect"*), with these
answers:

| # | Question | Answer |
| --- | --- | --- |
| R-D1 | Reuse the `composer` run kind, or a new one? | **A new kind.** |
| R-D2 | Which scripts appear? | **Validated scripts only.** *"dont show the not-validated ones. thats strictly for validation to approve."* |
| R-D3 | Script sources | **Scaffold a source choice now**: *"Eventually i will probably want sections so we can run other scripts that we know about, so scaffold a way to decide between sources. (Generated, ART, Legacy, SVT, the sources we currently have and use.)"* Only Generated is built. |
| R-D4 | What the share link carries | **The constraints, not the email.** |
| R-D5 | A script fails | **Carry on** to the next one. |
| R-D6 | After-hours start | **Yes**, *"have a cron-job feature as well"*: a **one-off** start time (R-O2). |

## 1. What already exists (checked 2026-10-15)

- **The run kind `composer`** is, to `/test-mode`, *"a normal TRIAGE then RUN of `cases[]`"*,
  with no repair loop and no review (device-testing `test-mode/SKILL.md` §1). An Ask-CK campaign
  ends with `/create-logs --auto` (§8). The new kind behaves the same way.
- **`tc_runs.build_handoff`** already takes several `kind: script` cases. Only `validation` is
  held to exactly one script.
- **`GET /api/test-composer/scripts`** (`tc_runs.list_scripts`) lists `generated/<group>/*.py`,
  without `library_*`. Each entry carries provenance: `case_key`, `saved_at`, `validated_at`,
  `finalized_at`.
- **Shared Svelte pieces in `svelte-src/src/tc/`:**
  - `SetupFields` (bench, consoles, PDU, outlets, constraints, email);
  - `AgentWindow` (the live session, reattach);
  - `ResultsTable`, `LogViewer`, `RunsList`;
  - `api.js` (`runBody`, `loadSetup` / `saveSetup`).
- **The share link pattern:** `TcPage.shareLink()` writes `panel`, `project`, `wiki` and
  `template` into the URL.
- **The after-hours start (A, P4):** `options.start_after` (HH:MM) makes a run `scheduled`, and
  the seat agent polls `/api/test-composer/scheduled` every 60 s and starts it once. No tab is
  needed. Compose a Run has the field; Validation does not.
- **The other sources are already in `ck.db`.** The `scripts` table carries `db` ∈ `art`, `svt`,
  `legacy` (built once by `ask-ck/tools/build_script_index.py` from `testsuites_art/`,
  `svt_scripts/` and `test_scripts/`), with the full `source_text`. Invariant 2 applies: the
  server reads them **only from `ck.db`**, never from those folders. `guard_db_only.py` refuses
  a runtime reference to the old mount roots.

## 2. The page

A third entry in the sidebar's **Test Composer** section, after Validate a Script and Compose a
Run: **Run Scripts**. It is in Svelte, in `current/`, on both the Classic and ATUI pages
(PLAN-test-composer C-D1). It is a new island, or a new page in the `tc` island, whichever the
build makes simpler.

1. **Source** (R-D3). A selector: **Generated** · ART · Legacy · SVT. Only Generated is enabled;
   the others show *"not yet"* (§4).
2. **Scripts.**
   - **What is listed:** validated scripts from the chosen source, which today means **finalized**
     (R-D2, R-O1), grouped by folder
     (`9001_Port`, …), with a filter box. Each row shows the case key, the path and when it was
     validated.
   - **Choosing:** tick several. **The order they are ticked is the order they run**; the page
     shows the order as a numbered list beside the checklist.
3. **Where it runs.** `SetupFields`, unchanged.
4. **When.** **Now**, or **once, after hours from HH:MM** (R-D6, R-O2), the same field as Compose
   a Run. There is no recurring schedule.
5. **Launch.**
   - **Now:** through this seat's agent, as Validation does.
   - **Scheduled:** stored as `scheduled` and left to the seat agent.
6. **Copy link** (§3) and, on a finished run, **Run again**.
7. **The session:** `AgentWindow`, with the run's logs.
8. **Results:** `ResultsTable` and the Log Viewer, including the `/create-logs` output. Feedback
   and re-grade as on Compose a Run.

**Not on this page (the baggage):**
- the repair loop;
- the repaired copy and its Approve;
- the review;
- Finalize;
- a Project or topology template.

**Kept, because they are the run's safety, not baggage:**
- the occupancy check, the bench probe and the preflight;
- the sentinel.

`/test-mode` refuses a run without them (bench-runner gate 8).

## 3. The share link

- **What it carries:**
  - `panel=run-scripts`;
  - `source` (R-D3);
  - `scripts`: the ticked paths, repo-relative, in run order;
  - `testbox`, `consoles`, `pdu`, `outlets`;
  - `constraints`;
  - `start` (if set).
- **Never the email** (R-D4): it is whoever opens the link who gets the mail. Their own
  remembered email fills that field, as today (`loadSetup`).
- **Opening a link:**
  - it fills the page and changes nothing else;
  - **it never launches**: the person opening it presses Launch, on their own seat agent (A, K1);
  - fields from the link win over the seat's remembered answers;
  - the seat's remembered answers are not overwritten until that person launches.
- **A script in the link that is missing or no longer validated** is listed as *"not available:
  <path>"* and not ticked. The rest still load.
- **Run again:** a finished run's button fills the page from that run's hand-off: the same
  scripts in the same order, and the same bench, consoles, PDU and constraints. The email comes
  from the seat's own answers.
- **Two people launching the same link on one bench at once:** the second run's occupancy check
  finds the first one's consoles held and stops, as it would today. Nothing new is needed; the
  plan records it so it is not mistaken for a bug.

## 4. Sources (R-D3) — the scaffold

A source is a small server-side record:

```
{ id, label, enabled, list() -> [script], resolve(id) -> how the session gets the file }
```

| id | label | where its scripts are | enabled now |
| --- | --- | --- | --- |
| `generated` | Generated | `ask-ck/functions/pytest-creator/generated/` (files, as `list_scripts`) | **yes** |
| `art` | ART | `ck.db` `scripts` where `db='art'` | no |
| `legacy` | Legacy | `ck.db` `scripts` where `db='legacy'` | no |
| `svt` | SVT | `ck.db` `scripts` where `db='svt'` | no |

- **`GET /scripts?source=<id>`** lists one source. With no `source` it means `generated`, so
  Validation is unchanged.
- **A disabled source:**
  - **Listing it:** returns `enabled: false`, a reason and no scripts.
  - **`POST /runs` with a script from it:** refused.
- **What enabling a `ck.db` source will need later (not in this plan):**
  - **Shipping the script:** the session must receive the script from `source_text`, because the
    session cannot read `ck.db`. Most likely the server writes it into the run's record directory
    and the hand-off names it, so no file outside Test-cases is touched.
  - **Libraries:** a script's library files come with it (`db.get_script_source` already finds a
    suite's `library` kind).
  - **Legacy fixes:** legacy scripts need the known fix set before they run on the current
    framework (memory `legacy-scripts-vs-framework`, `TESTBOX-ACCESS.md`).
  - **Validation:** what "validated" means for a script nobody here generated. ART scripts run
    in ART's own system today ("please do not wander off or edit their data in any way" covers
    ART's tools and data).

  Each of those is a decision for when a source is turned on.
- **Where each `ck.db` source is refreshed from (Terrence 2026-10-15):**
  - **ART:** *"we can update the art scripts by pulling the framework"*.
  - **SVT and Legacy:** *"unsure as to SVT/Legacy source, ill have to track that down"*.

  The refresh itself is not designed here. `ck.db` is the permanent source of truth (invariant 1),
  so a refresh is a deliberate, separate step, like the CLI docs' renewal (memory
  `atlnz-docs-cli-reference`), never a runtime read of a script folder.

## 5. The run kind (R-D1)

- **The kind:**
  - **Name:** `scripts`, run ids `…-scr-xxxx`.
  - **Rules:** one or more `kind: script` cases and no `manual` ones. `cycle` is not used.
- **Server (`tc_runs.py`):**
  - add the kind to `KINDS`;
  - refuse a script that is not validated (R-O1) or not from an enabled source;
  - keep the scripts' order as given;
  - `RunsList` shows the kind.
- **device-testing `test-mode/SKILL.md` §1:**
  - add `scripts` beside `composer` as *"a normal TRIAGE then RUN of `cases[]`"*;
  - say that a failed case does not stop the rest (R-D5; that is already D5's
    work-past-it rule for campaigns, so this only names it);
  - that is the whole device-testing change. Committed in device-testing by its own wrap.
- **The seat agent:** no change. It starts `mode: 'campaign'` sessions and relays markers the
  same way for any kind.

## 6. Phases

| Phase | What | Done when |
| --- | --- | --- |
| **R1 — server** | the `scripts` kind; the source registry with `generated` enabled; `/scripts?source=`; the validated-only filter (R-O1); `POST /runs` re-checks both. | pytest pins each refusal (an unvalidated script, a disabled source, a manual case) and the order; mutation-checked. |
| **R2 — the page** | the source selector, checklist, order, `SetupFields`, Launch, `AgentWindow`, `ResultsTable`, Log Viewer, Feedback/re-grade. Sidebar entry under Test Composer. Classic + ATUI. | vitest drives the built bundle with fake server and agent (the `tc-pages.spec.js` pattern). Terrence checks it by hand (memory `user-prefers-manual-ui-testing`). |
| **R3 — link and Run again** | §3. | vitest: a link fills the page, never launches, reports a missing script, never carries the email; Run again rebuilds the same body. |
| **R4 — schedule** | a one-off `start_after` on this page (reuses A's P4; R-O2). | the scheduled path pinned as in Compose a Run. |
| **R5 — device-testing** | §5's lines in `test-mode/SKILL.md`. | a real run of two scripts on tb470 with Terrence: both run in order, `/create-logs --auto` writes the group, the page shows the logs. |

R5's real run is also where the `RESULT` gap (Status) will show. Its fix is separate.

## 7. Decisions taken after the design (Terrence, 2026-10-15)

- **R-O1 — what "validated" means: option 3, wait for V0.**
  - **The facts:** R-D2 lists only validated scripts, and the only stamp today is Finalize's
    `finalized_at`. Finalize always refuses while V0 is open (PLAN-test-validation §6). On
    2026-10-15 neither generated script (T33234, T33235) had `validated_at` or `finalized_at`,
    though T33235 passed clean in run `1223-val-3ede`.
  - **What follows:** the list is empty until a script is finalized. Terrence: *"Ill be
    finalising a script soon, then we can test it."*
  - **Rejected:**
    - a clean Validation run stamping `validated_at`;
    - Finalize's local half running without its Zephyr writes.
- **R-O2 — the "cron-job": one-off.**
  - **What it is:** "start once after HH:MM", as Compose a Run already has (A, P4).
  - **Not built:** no recurring schedule.
- **R-D1 kind `scripts` and §3's share link:** approved as written.

## 8. Invariants

- **K1 (A):** a run uses the launching person's own seat and Claude login. A share link
  carries settings, never a credential or a session.
- **`ck.db`:** gains no table. A future `ck.db` source is read-only, and only through `db.py`
  (invariant 2). Run records stay files under `ask-ck/functions/test-composer/runs/`.
- **`generated/` is read, never written** by this page. Only Validation's Approve writes a script.
- **`/home/st-art/framework` stays read-only;** runs go through `tools/tb fwprep` / `fw` as today.
- **The write boundary:** Ask-CK writes only in Test-cases. The device-testing change in R5 is
  made and committed in device-testing.
