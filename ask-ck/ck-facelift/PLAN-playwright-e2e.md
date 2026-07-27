# PLAN — Playwright E2E (sparingly-run golden-path gate)

**Status:** ✅ BUILT + PASSING (2026-07-27) — first spec green, deterministic over 4/4 runs (~7s).
**Captured:** 2026-07-27 (by Claude, from a design discussion with Terrence).
**Scope + LLM handling settled during the design discussion (below); Option A chosen for the export assertion.**

## What was built (2026-07-27)

- `package.json` + `package-lock.json` — dev-dep `@playwright/test@^1.62.0` (npm package only).
- `playwright.config.js` — testDir `e2e/`, chromium project, `webServer` runs `./run.sh --bg`
  with `reuseExistingServer:true`, `workers:1`/`retries:0` (deterministic gate, flakes visible),
  HTML report → `e2e/.report/`, artifacts → `e2e/.artifacts/`.
- `e2e/pages/generator.page.js` — Page Object; **all selectors live here** (grounded in real
  `index.html` + `tables.js`/`db-search.js`/`generator.js`, not guessed).
- `e2e/golden-path.spec.js` — the Option-A journey (below).
- `.gitignore` — added `node_modules/`, `e2e/.report/`, `e2e/.artifacts/`, `test-results/`.
- Browser: Playwright 1.62 pins **chromium rev 1234**; the cached 1228 did NOT match, so
  `npx playwright install chromium` downloaded 1234 (~115 MiB, one-time). System Chrome 150 /
  Vivaldi 8.1 exist as `channel:'chrome'` fallbacks but the pinned build is used for determinism.

## Three real-DOM discoveries that shaped the spec (would have broken a guessed test)

1. **Export CANNOT go green on the non-LLM path** — `validate_zephyr_payload` (routers/wizard.py
   ~2038) hard-requires a synthesized objective (`<ul>`+≥3`<li>`) and ≥2 steps, both LLM-only.
   So **Option A** was chosen: assert the export is *blocked* (`#export-status.is-error`, headline
   "Export blocked — the payload did not pass validation…"). 100% deterministic, no LLM, no seed.
2. **Sidebar is a collapsed accordion on load** — `goToStep` nav items aren't clickable until the
   "Objective/Test Case Generator" section label is clicked open. Page Object expands it first.
3. **`#load-status` is hidden again in the handler's `finally`** — not a load-complete signal.
   Real signal: `updateUI()` writes the session JSON (incl. the case key) into `#session-view`.
   Also: an in-progress case loads with **pre-existing chosen rows**, so `searchAndChoose` asserts
   the chosen-table count grew by the DELTA ticked, not an absolute count.

## How to run

```
npm run e2e            # headless (starts/reuses the server via run.sh)
npm run e2e:headed     # watch it drive the browser
npm run e2e:report     # open the last HTML report
```
Preconditions unchanged (see below): LFS `ck.db`, port 8000 free-or-reused, `/health` 200.

---

### Original design notes (retained for context)

---

## Purpose

A single, deterministic end-to-end test that drives the **real running Ask-CK app**
(real server + real browser + real `ck.db`) through one critical journey, to catch
regressions that unit-level tests structurally cannot — real app boot (`main.js` + its
~10 import-time side effects), real button→endpoint round-trips, real table population,
real navigation, and real CSS/visual state.

**Run policy: SPARINGLY.** This is the slowest, most brittle test layer and it conflicts
with the standing manual-UI-testing preference ([[user-prefers-manual-ui-testing]]). It is
NOT a per-commit gate. Intended cadence: on demand / pre-release confidence check on the
golden path — not every push.

## Where this sits in the wider testing design (context)

This E2E is **one layer of a 4-layer design** discussed but not yet built. The others are
NOT part of this plan and remain open:

| Layer | Tool | Scope | Cadence | LLM |
|---|---|---|---|---|
| Frontend units | Jasmine or Vitest **+ jsdom** | pure-logic: tables render fns, merge/dedup/re-score, `setButtonBusy`/`flashButtonDone`/`showStatus`, `actions.js` dispatcher, state transitions | every push | No |
| Backend flow | pytest (extend existing `tests/`) | `load → suggest → export` via in-process `TestClient`; assert emitted bundle structure/invariants; stub the one `llm.py` call | every push | No (stubbed) |
| Boot smoke | curl `/health` in CI | server wires up / imports OK | every push | No |
| **E2E (THIS PLAN)** | **Playwright** | full golden journey against live app | **sparingly / on demand** | Intercepted |

Rationale for the split: the frontend is **~80% pure functions** (tables.js render fns and
chosen.js/merge logic have **zero fetch** — they transform client `S.` state → `innerHTML`).
That 80% is cheap to cover in jsdom. Only the *integration seams* (real click → real endpoint
→ real repaint → real bundle) need a browser + server, and that is exactly and only what this
E2E covers. No single cheap tool tests "everything"; Playwright is the only tool that *can*
test the whole app as it actually runs, but it's reserved for the seams.

---

## Agreed decisions (settled — do not re-litigate)

1. **Golden journey = the NON-LLM deterministic path.** No LLM synthesis in the asserted
   flow, so the test is a reliable green/red gate that does not depend on org-vLLM
   availability or produce non-deterministic output.

   Journey shape:
   ```
   load app (panel-main)
     → select a case + Load  (Cases panel)
     → keyword-search TestLink / Zephyr / ATP  (deterministic, no LLM)
     → tick candidate rows → tables populate + merge/dedup + chosen-table updates
     → export a repeatable bundle
     → assert: bundle written / status banner success / expected files named
   ```

2. **LLM endpoints handled via Playwright route interception.** Any LLM endpoint the journey
   brushes against is intercepted at the browser network layer and returns canned JSON, so the
   run stays deterministic + fast while still exercising the real frontend + real non-LLM
   server paths. (The golden path is designed to avoid LLM calls, but interception is the
   safety net so a stray suggest/health ping can't make the test flaky.)

## Known environment preconditions (from this repo — must hold before the E2E can run)

- **LFS-materialized `ck.db`** — the server reads all corpora only from `ask-ck/var/ck.db`
  ([[db-is-permanent-source]], [[db-only-single-source]]); a CI checkout **must** `git lfs`
  pull or corpora are empty and the journey has no cases. (Verified 2026-07-27: 380 cases
  present locally, `/api/wizard/cases` returns counts.)
- **Port 8000** — server binds `0.0.0.0:8000`; a stale instance causes
  `[Errno 98] Address already in use`. The harness must start cleanly (use `./run.sh --restart`
  or ensure no prior instance) and tear down after.
- **Server start** — `./run.sh --bg`; wait for `/health` → 200 before driving the browser.
- **Node/npm present** — verified Node v24.15.0, npm 11.12.1 on the Linux seat.
- **Playwright browser binaries** — `npx playwright install` needed on the runner (adds
  system deps). Prefer a **self-hosted runner on the testbox** so LFS + the browser + (if ever
  needed) org-vLLM are all local, matching [[commit-and-push-on-session-end]] (push works from
  the Linux seat, not the Mac seat).

## Implementation notes for the future session (NOT done yet)

- **Ground selectors in the REAL DOM.** The single biggest cause of brittle E2E is guessed
  selectors. Before writing specs, extract exact element ids from `static/index.html` and the
  render functions in `static/js/tables.js` / `db-search.js` / `generator.js`. Known-relevant
  anchors already seen this session:
  - Case selects: `#ptCaseSelOpen` / `#ptCaseSelDone` (PyTest side); Generator has its own
    dual case-selects (see `cases.js refreshCaseSelects`).
  - Search inputs: `#tlSearchQ`, `#zephyrSearchQ`, `#atpSearchQ`.
  - Suggest buttons (LLM — would be intercepted / avoided): `#tl-suggest-llm-btn`,
    `#zp-suggest-llm-btn`, `#atp-suggest-llm-btn`.
  - Export: `<button data-action="exportBundle">` (two exist — static `index.html:248`
    "Export", and the dynamically-rendered `generator.js:228` "Export Repeatable Bundle").
  - Status banners: `#export-status`, `#objective-status`, `#steps-status` (`.status-banner`).
  - Interaction is via the delegated `data-action` dispatcher (`actions.js`) — Playwright can
    click by `[data-action="..."]` or by id.
- **Use the Page Object pattern** so selector churn is isolated to one place.
- **Assert structure, not prose** — even on the non-LLM path, assert counts / presence /
  banner-kind / named files, never exact copy, so the test survives benign content changes.
- **Fixtures:** pick a stable known case key present in `ck.db` (e.g. an incomplete case with
  step1-3), or query `/api/wizard/cases` at setup to choose one dynamically.
- **Layout:** a new top-level `e2e/` (or `tests/e2e/`) with `playwright.config.ts`; keep it
  OUT of the pytest path. Add an npm script + a **separate** CI job (manual/`workflow_dispatch`
  trigger), NOT the per-push gate.
- **Do not add mock mode to the server** — mock/demo mode was deliberately removed. Determinism
  comes from the non-LLM journey + route interception, not a server mock.

## Open (deferred — decide when building)

- Exact golden case key + whether to pick it dynamically from `/api/wizard/cases`.
- Whether the export assertion inspects the written `refined-cases/**` files on disk or only
  the success banner + `saved_files` response.
- Whether to also add the narrow **UI-feedback** variant (spinner appears / button disables /
  double-click blocked / completion flash for the buttons built 2026-07-27) as a second spec —
  parked; the deterministic golden path is the priority first E2E.
- CI host: GitHub Actions (needs LFS bandwidth + browser deps) vs self-hosted testbox runner
  (LFS local, can reach vLLM). Leaning self-hosted.

---

**Related:** [[user-prefers-manual-ui-testing]], [[db-is-permanent-source]],
[[db-only-single-source]], [[commit-and-push-on-session-end]]. Sibling plans in this dir:
`PLAN-es-module-split.md` (the ES-module frontend this E2E drives), `PLAN-facelift.md`.
