---
name: testing-suite-3-layer
description: Ask-CK's gate run_tests.sh has FOUR layers since 2026-10-30 — guards, pytest, root Vitest (Classic + islands), the Svelte app's own Vitest; set -euo pipefail so a red stops the rest; never pipe the gate through grep — read its exit code; Playwright E2E separate
metadata: 
  node_type: memory
  type: project
  verified: 2026-10-30
  originSessionId: 5da34e66-6995-49af-8d5e-491007959772
  modified: 2026-07-27T00:32:32.933Z
---

Built 2026-07-27f (commits `4f990ea`→`e871caa`, pushed to `main`). Ask-CK now has three
automated-test layers:

- **Backend units** — `tests/` (pytest, in-process TestClient, no network/LLM/testbox; **190 tests** as of 2026-07-27g).
- **Frontend units** — `tests/js/` (moved from repo-root `js-tests/` 2026-09-11; Vitest + jsdom, no browser/server/LLM; **72 tests** as of 2026-07-27g).
  Covers DOM/button helpers, table renderers, chosen-list, and `db-search.js` `merge*` (exported
  for testability). DOM fixtures are lifted from the REAL `index.html` and throw on a renamed id
  (drift-detection).
- **E2E** — `e2e/` at repo root (Playwright, one Chromium golden-path). **Sparingly-run, NOT in the
  gate.** Asserts the export validation gate BLOCKS an un-synthesized case (a green export needs
  LLM synthesis, so the deterministic assertion is the blocked outcome).

**How to run:**
- `./ask-ck/tools/run_tests.sh` = THE regular gate: guards + pytest + `npm test` (Vitest). Fails loudly if
  Node deps aren't installed.
- `npm test` / `npm run test:watch` — frontend units only.
- `npm run e2e` — Playwright E2E (sparingly; starts/reuses the server via run.sh).

**⚠ The gate is `set -euo pipefail`, so it STOPS AT THE FIRST FAILING LAYER** (verified
2026-09-22). A single red in pytest means `npm test` never runs at all — the frontend layer is
not skipped-with-a-warning, it is simply never reached, and the run still *looks* like "the gate"
to anyone reading the summary. That happened for real: one stale test (a Zephyr link floor
calibrated on a corpus that `e35bbb2` deliberately rewound) hid the whole Vitest layer from
2026-09-16 to 2026-09-22. **How to apply:** while any known red stands, run `npm test`
SEPARATELY before believing the frontend is green, and treat a long-lived "known red" as
actively dangerous rather than cosmetic — it is masking every layer behind it.

Seen again 2026-09-30: one false pytest red inside a scratch worktree left Vitest unrun until it was
run by hand — same shape, same fix.

**2026-10-30 — a FOURTH layer, and the opposite mistake.** `run_tests.sh` now also runs the Svelte
app's own Vitest (`cd ask-ck/frontend/ck-main/svelte && npm test`; exits 2 if its `node_modules`
is missing — a second `npm install --legacy-peer-deps` per clone), after the root Vitest. The
opposite mistake happened the same day: a landing chain ran `npm test | grep … | head`, the grep's
exit code replaced vitest's, a red spec sailed through and main's gate was red until a follow-up
commit. **How to apply:** run the gate (or a layer) to a log file and read its exit code / summary
line afterwards; never put a filter in the pipeline you are gating on.

**Why:** the user wanted regression protection after big changes; chose Vitest over Jasmine for
readable failure output, and E2E-first as a known-good reference the unit layer derives from.

**2026-07-27g:** the adversarial-review batches grew the suite (48→190 pytest, 47→72 Vitest) and
introduced **structural** tests alongside example-based ones — e.g. an AST sweep asserting no async
handler calls a blocking function without `run_in_threadpool`, and source assertions that a guard
precedes a state write. These catch the NEXT regression, not only the filed one; prefer that shape
where a defect has a machine-checkable form. Test fixtures must clear BOTH the in-memory session and
the persisted `ck.db` row — an in-memory-only pop leaks throwaway keys into the permanent DB and
masks failures across tests.

**How to apply:** run `./ask-ck/tools/run_tests.sh` before committing frontend/backend changes; run the
E2E on demand (pre-release), not every commit. JS tooling (`package.json`, configs, `e2e/`,
`tests/js/`) lives at repo root, separate from the front-end tree (`ask-ck/frontend/ck-main/current/`); `node_modules` + PW artifacts are
gitignored. No CI runner yet (`.github/workflows`). See [[user-prefers-manual-ui-testing]] — the
E2E/manual layer still owns the visual checks jsdom can't see (spinner animation, flash colors).
Plans: `archive/plans/PLAN-playwright-e2e.md`, `PLAN-frontend-unit-tests.md`.
