# PLAN — Frontend unit tests (Vitest + Testing Library, jsdom tier)

**Status:** ✅ BUILT + PASSING (2026-07-27) — 34 tests / 3 spec files green in ~1.5s.
Tests live in top-level `js-tests/` (separate from the module tree, by decision). Run `npm test`.

## What was built (2026-07-27)

- Deps (devDeps in the shared `package.json`): `vitest`, `jsdom`, `@testing-library/dom`.
- `vitest.config.js` — `environment: 'jsdom'`, `include: ['js-tests/**/*.spec.js']`.
- `package.json` scripts: `"test": "vitest run"`, `"test:watch": "vitest"`.
- `js-tests/helpers/fixture-dom.js` — `mountFromIndex(...ids)` lifts REAL container markup out
  of `index.html` into jsdom; **throws if an id is missing** (drift-detection — proven by a
  dedicated test). `resetDom()` clears the DOM + the `window.*` candidate buses between specs.
- `js-tests/dom-helpers.spec.js` (15) — `setButtonBusy` (disable/spinner/label-stash/restore/
  double-click guard/null-safe), `flashButtonDone` (is-done/is-error + auto-clear via fake
  timers), `showStatus` (kind class + HTML escaping + clear), `escapeHtml`/`truncateText`.
- `js-tests/tables.spec.js` (10) — the three render fns: row-per-candidate, **hides
  already-chosen ids** (E2E-proven), all-chosen note, empty state, HTML-escaping, chosen-table
  insertion order, + the fixture drift-detection test.
- `js-tests/chosen.spec.js` (9) — `chooseByIds` (append/dedup/**delta growth**/synthesized
  record/falsy-id skip), `restoreChosenFromSelections` (order-sort / list-order fallback /
  non-array tolerance), `chosenSelections` payload shape.

Failure output verified human-readable: failing test name + Expected/Received diff + source
frame with the offending line marked (the reason Vitest was chosen over Jasmine for this tier).

## Merge-function coverage — CLOSED (2026-07-27)

`mergeTestLinkCandidates` / `mergeZephyrCandidates` / `mergeATPCandidates` (`db-search.js`) were
made `export` (a one-line, behaviour-preserving change — they were already called internally;
exporting alters nothing at runtime) so they can be unit-tested directly, avoiding a brittle
fetch-stubbed handler round-trip. `js-tests/merge.spec.js` (13 tests) covers dedup, score
re-sort (desc), the longer-description preference, default scores (TL/Zephyr 0.6, ATP 0.5),
no-id skip, the `precheckIds` → chosen-bus path, and the ATP "keep higher LLM score but refresh
richer desc" special case.

## Glue — DONE (2026-07-27)

`npm test` was chained into `tool/run_tests.sh` (step 3, after guards + pytest) → a SINGLE gate
runs all three cheap layers. Verified green together: guards + 48 pytest + 47 Vitest, exit 0.
The script FAILS LOUDLY (exit 2) if npm is present but `node_modules/vitest` is missing — a
partial gate that silently drops a layer would falsely read "all green". Skips with a warning
only if npm itself is absent. The Playwright E2E stays OUT of this gate (sparingly-run,
`npm run e2e`).

Current suite total: **47 Vitest tests / 5 spec files** (dom-helpers, tables, chosen, merge,
+ fixture drift-detection).

---

### Original "READY TO BUILD" notes (retained)

**Captured:** 2026-07-27 (by Claude, from a design discussion with Terrence). Updated same day
after the Playwright E2E landed (commit `4f990ea`) — this layer is now derived FROM that
known-good reference (see "Derived from the E2E" below).

## Build decisions settled (2026-07-27)

1. **Tool:** Vitest + jsdom + `@testing-library/dom` (rationale unchanged, below).
2. **Fixture DOM:** **extract real fragments from `index.html`** into jsdom per-spec (NOT
   hand-written stubs). A container-id rename in `index.html` then breaks the spec — desirable
   drift-detection, same discipline as the E2E's grounded selectors. A small helper reads
   `static/index.html`, slices the needed container(s) by id, and injects into `document.body`.
3. **First spec:** `dom-helpers.js` (`setButtonBusy` / `flashButtonDone` / `showStatus`) — zero
   fixtures needed, pure DOM, regression-locks THIS session's LLM-button UX work, and is the
   fastest path to a green spec that demonstrates Vitest+TL output quality.

## Derived from the E2E (known-good reference → cheap exhaustive unit coverage)

The Playwright golden-path (`PLAN-playwright-e2e.md`, `e2e/golden-path.spec.js`) proved these
behaviours against the real app. The Vitest layer re-asserts the same logic exhaustively in
jsdom (every kind, every dedup/merge edge) with no browser/server:

| E2E ground truth (proven) | Vitest unit spec (jsdom, no server) |
|---|---|
| Choosing grows the chosen table by the DELTA ticked; in-progress cases pre-load chosen rows | `chosen.js` `chooseSelected(kind)` moves checked → chosen bus; `restoreChosenFromSelections` seeds pre-existing. Assert counts/dedup on pure `S.` state. |
| Search results land in the TOP table, MERGED not replaced | `mergeTestLinkCandidates`/`Zephyr`/`ATP` (`db-search.js`) — feed two batches, assert dedup + pool re-score. |
| Top table HIDES already-chosen candidates | `tables.js` render fns filter against `chosenIdSet` — assert a chosen id is absent from rendered top-table HTML. |
| Export banner flips to `is-error` + block headline | `showStatus('export-status','error',…)` → `status-banner is-error` + escaped title. |
| Buttons show busy→done feedback (this session) | `setButtonBusy`/`flashButtonDone` — the FIRST spec. |

**Original tool-decision + scope notes retained below.**

---

---

## Purpose

A **light, regularly-run** frontend test layer that covers the ~80% of the Ask-CK frontend
that is pure logic — everything that transforms data → DOM *without* a live server. Run
after big changes, alongside the pytest backend layer. Optimized for **clear human-readable
output**, because outputs are human-verified.

This is the cheap counterpart to the parked Playwright E2E ([[]] see `PLAN-playwright-e2e.md`):
- **This layer (jsdom):** pure logic, fast, every-big-change. No browser, no server, no LLM.
- **Playwright layer:** the integration seams (real boot, real fetch, real CSS) — sparingly.

## Tool decision: **Vitest + jsdom + `@testing-library/dom`** (settled)

Chosen on operator merits (familiarity explicitly set aside), optimizing for readable output:

- **Native ESM, zero loader config** — runs Ask-CK's real `import`/`export` modules as-is
  (no build step in this repo), so a failing test reflects the code, not a loader quirk.
- **Best human-readable failures in the no-browser tier:** Vitest prints a colored inline
  **expected-vs-received diff** + the exact highlighted source frame; `@testing-library/dom`
  prints the **actual accessible DOM tree** on a failed query and suggests better queries.
  Together: the diff *is* the verification.
- **Watch mode / focused reruns** for tight iteration after a change.
- **Jasmine-shaped API** (`describe`/`it`/`expect`/spies) — the "Jasmine-like experience"
  requested, with near-zero relearning.

**Ranking considered (for the record, if we ever revisit):**
`Vitest+Testing-Library > Vitest+jsdom-plain > @web/test-runner > Jasmine+jsdom > Karma+Jasmine`.
- `@web/test-runner` is the only option that beats Vitest on *fidelity* (real browser → sees
  CSS/visuals like the spinner + flash colors), but that overlaps the parked Playwright layer,
  so its extra weight isn't worth it **here**.
- Jasmine is a fine, defensible choice on personal-familiarity grounds; it loses only on the
  one-time ESM loader-config tax against this native-ESM codebase.
- Karma is config-heavy + legacy; not suited to a light regular runner.

## What this layer CAN cover (the ~80% — from a real scan of the JS, 2026-07-27)

The frontend splits cleanly into pure-logic (testable here) vs server round-trips (Playwright):

- **Table rendering** — `tables.js`: `renderTestLinkTable`, `renderZephyrTable`,
  `renderATPTable`, `renderChosenTable`, `renderStepTables`. **Zero fetch** — take a data
  array → produce `innerHTML`. Assert row counts, escaping, source badges, empty-state.
- **Selection / merge / dedup / re-score** — `chosen.js` (0 fetches: `chooseByIds`,
  `restoreChosenFromSelections`, `chosenSelections`) and the `mergeTestLinkCandidates` /
  `mergeZephyrCandidates` / `mergeATPCandidates` functions in `db-search.js`. Operate on
  client `S.` state. Assert dedup holds, pinned keep_ids survive, pool re-scores.
- **Button-feedback helpers (built this session)** — `dom-helpers.js`: `setButtonBusy`
  (busy class + disable + label stash/restore + double-click guard returns false),
  `flashButtonDone`, `showStatus` (kind→class, HTML escaping, `clear` hides).
- **The dispatcher** — `actions.js`: `data-action` name → registered fn called with the
  element as `this`; `data-args` JSON parsing; unknown-action warning path.
- **State transitions** — `state.js` and the pure reducers/helpers that read/write `S.`.

## What this layer CANNOT cover (explicitly out of scope → Playwright / manual)

- **`main.js` boot** — fires ~10 import-time side effects (`initCases()`, `goToPanel()`,
  `updateLLMStatus()`, `loadToolStatus()`…) that need the real page + a server. **Specs must
  import LEAF modules only, never `main.js`.**
- **Real `fetch` round-trips** — the server call itself. (Can stub `fetch` to test a handler's
  wiring, but that's testing the handler, not the endpoint.)
- **CSS / visuals** — jsdom has no layout/animation. The spinner *rendering*, the `!important`
  flash colors, `prefers-reduced-motion`, `:focus-visible` are NOT visible here. These stay in
  manual UI verification ([[user-prefers-manual-ui-testing]]) + the parked Playwright layer.

## Pairing with the pytest backend layer

"Pairs with pytest" = both invoked by the same gate + both exit non-zero on failure. **No JS
runner integrates with Python**; the glue is the shell. The repo already has this pattern in
`tool/run_tests.sh` (guards + pytest, non-zero on fail). Adding the frontend runner is one
more step there — e.g.:

```bash
echo "== frontend (vitest/jsdom) =="
npm test            # exits non-zero on fail
echo "== backend (pytest) =="
PYTHONNOUSERSITE=1 .venv/bin/pytest -q
```

**Exact glue deferred** (Terrence: "decide when building") — options were: extend
`run_tests.sh` (matches convention, single gate) vs keep `npm test` + `pytest` separate.

## Implementation notes for the future session (NOT done yet)

- **New files:** `package.json` (devDeps: `vitest`, `jsdom`, `@testing-library/dom`;
  `"test": "vitest run"` + a `test:watch`), `vitest.config.*` (environment: 'jsdom'), and a
  frontend test dir (e.g. `static/js/__tests__/` or a top-level `js-tests/`) kept OUT of the
  pytest path.
- **First specs (highest value, self-contained, no fixtures needed):** `setButtonBusy` /
  `flashButtonDone` / `showStatus` — pure DOM helpers, ideal to prove the harness + output
  quality. Then the `actions.js` dispatcher, then `tables.js` render fns, then the merge/dedup
  logic.
- **Fixture DOM** (for render/dispatcher specs that need target nodes): build minimal DOM in
  the spec, OR extract real fragments from `index.html`. **This is a genuine open decision**
  (fidelity vs isolation) — was about to be asked when the thread was reframed; defer to build
  time. Prefer real-fragment extraction where drift-catching matters (table containers), hand
  fixtures where isolation matters (helpers).
- **`fetch` stubbing** (only for handler-wiring specs, not the pure logic): stub `global.fetch`
  with canned JSON. Whether to use recorded endpoint fixtures vs hand-written stubs is **open**
  — defer to build time. The pure-logic first specs need no fetch at all.
- **No server, no LFS, no LLM needed** for this layer — that's the point. Runs anywhere Node runs.
- **Node present:** v24.15.0 / npm 11.12.1 on the Linux seat (verified 2026-07-27).

## Open (deferred — decide when building)

- Glue: extend `run_tests.sh` vs separate commands.
- Fixture DOM strategy: real-`index.html`-fragment extraction vs hand-written minimal fixtures
  (likely per-spec mix).
- `fetch` strategy for handler specs: recorded endpoint fixtures vs hand-written stubs.
- Test dir location + whether to add a coverage threshold gate later.
- Whether `@web/test-runner` earns a place later for the *visual* helpers (spinner/flash) if
  manual + Playwright coverage of them ever proves insufficient.

---

## Where this sits in the wider 4-layer testing design (context)

| Layer | Tool | Scope | Cadence | LLM |
|---|---|---|---|---|
| **Frontend units (THIS PLAN)** | **Vitest + Testing Library + jsdom** | pure logic: tables, merge/dedup, button helpers, dispatcher, state | every big change | No |
| Backend flow | pytest (extend existing `tests/`) | `load → suggest → export` via in-process `TestClient`; assert bundle structure; stub the one `llm.py` call | every big change | No (stubbed) |
| Boot smoke | curl `/health` in CI | server imports/wires OK | every push | No |
| E2E | Playwright (`PLAN-playwright-e2e.md`) | full golden journey against live app | sparingly / on demand | Intercepted |

Rationale for the split: frontend is ~80% pure functions (verified — `tables.js` render fns and
`chosen.js`/merge logic have zero fetch). That 80% is cheap to cover here; only the integration
seams need the browser+server (Playwright).

**Related:** [[user-prefers-manual-ui-testing]]. Sibling plans in this dir:
`PLAN-playwright-e2e.md` (the sparing E2E — this layer's expensive counterpart),
`PLAN-es-module-split.md` (the ES-module frontend both layers target), `PLAN-facelift.md`.
