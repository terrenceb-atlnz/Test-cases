// Ask-CK E2E — deferred per-step candidate loading (the Generator's three DB reviews).
//
// WHY THIS EXISTS (see ask-ck/ck-facelift/PLAN-backend-module-split.md A1):
//   The three review steps used to receive their candidate pools inside the load_case
//   response, i.e. the server built data for panels the user had not opened. That
//   caused two separate incidents:
//     * Step 3 (ATPyLib) ran a blocking analyze_atp_coverage LLM call — ~60s on EVERY
//       case load — for a ranking the step's own "Suggest with LLM" button redid.
//     * Step 2 (Zephyr) scanned all ~45k slim rows through a bespoke Python scorer:
//       a measured 2.7s bare on the event loop, freezing every concurrent request.
//   Each step now fetches its own pool on first visit, via one uniform endpoint.
//
//   Every claim below is network- or DOM-observable, which is exactly what the manual
//   checklist could only eyeball: whether a fetch happened, how many times, for which
//   step, and whether an in-flight response is allowed to destroy user work. The Vitest
//   layer (js-tests/step-candidates.spec.js) pins loadStepCandidates in isolation; this
//   layer proves it is actually WIRED — that goToStep triggers it against the real
//   server and the real tables.
//
// Deterministic and non-LLM throughout: keyword mode only, no synthesis.
import { test, expect } from '@playwright/test';
import {
  GeneratorPage,
  KINDS,
  NOT_FETCHED_TEXT,
  STEP_CANDIDATES_GLOB,
} from './pages/generator.page.js';

const KIND_NAMES = ['testlink', 'zephyr', 'atp'];

// Two real open/partial cases from ck.db, resolved live so a re-keyed case cannot
// break the run (same approach as golden-path.spec.js).
let CASE_A = 'AWPTCM-T30649';
let CASE_B = null;

test.beforeAll(async ({ request }) => {
  try {
    const res = await request.get('/api/wizard/cases');
    const cases = (await res.json())?.incomplete?.cases || [];
    if (cases[0]?.key) CASE_A = cases[0].key;
    if (cases[1]?.key) CASE_B = cases[1].key;
  } catch {
    /* keep fallbacks */
  }
});

test.describe('load_case does no per-step work', () => {
  test('the API response carries no candidate pools', async ({ request }) => {
    // The server-side half of the contract. If any of these keys come back, the
    // frontend would be free to start depending on them again.
    const res = await request.post(`/api/wizard/load_case/${CASE_A}`);
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(Object.keys(body).sort()).toEqual(['case_title', 'message', 'session']);
    for (const gone of ['testlink_candidates', 'zephyr_refs', 'atp_candidates']) {
      expect(body).not.toHaveProperty(gone);
    }
  });

  test('loading a case fires ZERO candidate requests, and tables say "not fetched"',
    async ({ page }) => {
      const gen = new GeneratorPage(page);
      await gen.open();
      const net = gen.trackStepCandidateRequests();

      await gen.loadCase(CASE_A);

      // The point of the change: nothing is fetched for a panel not yet opened.
      expect(net.urls).toHaveLength(0);

      for (const name of KIND_NAMES) {
        // Must NOT claim "No candidates for this case" — that asserts a fact the
        // server has not been asked about yet. This distinction is the reason the
        // load path renders only the chosen table.
        await expect(gen.candidateTable(name)).toContainText(NOT_FETCHED_TEXT);
        await expect(gen.candidateTable(name)).not.toContainText(KINDS[name].emptyTop);
      }
    });

  test('chosen tables render at load, without waiting for any candidate fetch',
    async ({ page }) => {
      // Chosen rows come from the session, so they are free at load — a returning
      // user sees their prior picks immediately. Either real rows or the explicit
      // empty-state proves the chosen table was rendered (not left blank).
      const gen = new GeneratorPage(page);
      await gen.open();
      await gen.loadCase(CASE_A);

      for (const name of KIND_NAMES) {
        const chosen = gen.chosenTable(name);
        const boxes = chosen.locator('input[type="checkbox"]');
        if ((await boxes.count()) === 0) {
          await expect(chosen).toContainText(KINDS[name].emptyChosen);
        }
        await expect(chosen).not.toContainText(NOT_FETCHED_TEXT);
      }
    });
});

test.describe('opening a step fetches exactly once', () => {
  for (const name of KIND_NAMES) {
    const step = KINDS[name].step;

    test(`step ${step} (${name}): fetches on first open, renders rows, never re-fetches`,
      async ({ page }) => {
        const gen = new GeneratorPage(page);
        await gen.open();
        const net = gen.trackStepCandidateRequests();
        await gen.loadCase(CASE_A);
        expect(net.forStep(step)).toHaveLength(0);

        await gen.openStepAndWaitForCandidates(name);

        // Exactly one request, and for THIS step's endpoint.
        expect(net.forStep(step)).toHaveLength(1);
        expect(net.forStep(step)[0]).toContain(`/step_candidates/${CASE_A}/${step}`);
        expect(await gen.candidateRows(name).count()).toBeGreaterThan(0);

        // Leave and come back twice: the memo must hold, or every navigation would
        // re-pay the query (step 2's is the expensive one).
        await gen.goToStep(0);
        await gen.goToStep(step);
        await gen.goToStep(0);
        await gen.goToStep(step);
        await expect(gen.candidateRows(name).first()).toBeVisible();
        expect(net.forStep(step)).toHaveLength(1);
      });
  }

  test('opening all three steps fetches each exactly once (uniform behaviour)',
    async ({ page }) => {
      // The uniformity requirement: three steps, three identical fetches, no step
      // doing anything structurally different from the others.
      const gen = new GeneratorPage(page);
      await gen.open();
      const net = gen.trackStepCandidateRequests();
      await gen.loadCase(CASE_A);

      for (const name of KIND_NAMES) await gen.openStepAndWaitForCandidates(name);

      expect(net.urls).toHaveLength(3);
      for (const name of KIND_NAMES) {
        expect(net.forStep(KINDS[name].step)).toHaveLength(1);
      }
    });
});

test.describe('switching cases', () => {
  test('resets the tables and re-fetches for the new case, leaking no rows',
    async ({ page }) => {
      test.skip(!CASE_B, 'needs a second open/partial case in ck.db');
      const gen = new GeneratorPage(page);
      await gen.open();
      const net = gen.trackStepCandidateRequests();

      await gen.loadCase(CASE_A);
      await gen.openStepAndWaitForCandidates('zephyr');
      const firstRowCount = await gen.candidateRows('zephyr').count();
      expect(firstRowCount).toBeGreaterThan(0);

      // Load the OTHER case. loadCase clears the pools and resets the memo, so the
      // previous case's rows must disappear rather than linger under a new case.
      await gen.loadCase(CASE_B);
      await expect(gen.candidateTable('zephyr')).toContainText(NOT_FETCHED_TEXT);
      expect(await gen.candidateRows('zephyr').count()).toBe(0);
      expect(net.forKey(CASE_B)).toHaveLength(0);

      // Re-opening step 2 fetches again — for the NEW key.
      await gen.openStepAndWaitForCandidates('zephyr');
      expect(net.forKey(CASE_B)).toHaveLength(1);
      expect(net.forKey(CASE_B)[0]).toContain(`/step_candidates/${CASE_B}/2`);
    });
});

test.describe('in-flight responses must not destroy user work', () => {
  test('a slow default fetch does not clobber Search results', async ({ page }) => {
    // The race the manual checklist could only attempt by clicking fast: hold the
    // default fetch open, run an explicit Search, then release it. The search rows
    // are an explicit request and outrank a default view, so they must survive.
    const gen = new GeneratorPage(page);
    await gen.open();

    let release = () => {};
    const held = new Promise((r) => { release = r; });
    await page.route(STEP_CANDIDATES_GLOB, async (route) => {
      await held;
      await route.continue();
    });

    await gen.loadCase(CASE_A);
    await gen.goToStep(KINDS.zephyr.step);          // default fetch now blocked

    await page.locator(KINDS.zephyr.searchInput).fill('vlan');
    await page.locator(KINDS.zephyr.searchAction).click();
    await expect(gen.candidateRows('zephyr').first()).toBeVisible({ timeout: 20_000 });
    const searchRows = await gen.candidateRows('zephyr').count();
    expect(searchRows).toBeGreaterThan(0);

    release();                                       // default view lands late
    // Give the late response time to be (incorrectly) applied.
    await page.waitForTimeout(1_000);
    expect(await gen.candidateRows('zephyr').count()).toBe(searchRows);
  });

  test('the app stays responsive while a step fetch is in flight', async ({ page }) => {
    // The regression that motivated all of this: step 2 ran on the event loop, so a
    // case load froze every other request. Hold the step fetch open and prove an
    // unrelated endpoint still answers.
    const gen = new GeneratorPage(page);
    await gen.open();

    let release = () => {};
    const held = new Promise((r) => { release = r; });
    await page.route(STEP_CANDIDATES_GLOB, async (route) => {
      await held;
      await route.continue();
    });

    await gen.loadCase(CASE_A);
    await gen.goToStep(KINDS.zephyr.step);

    // Navigation must not be blocked by the pending fetch...
    await gen.goToStep(0);
    await expect(page.locator('#step-0')).toBeVisible();
    // ...and the server must still serve other requests.
    const health = await page.request.get('/health');
    expect(health.ok()).toBeTruthy();

    release();
  });
});

test.describe('failure handling', () => {
  test('a failed fetch is reported in the table and retried on the next visit',
    async ({ page }) => {
      const gen = new GeneratorPage(page);
      await gen.open();
      await gen.loadCase(CASE_A);

      // Fail only the FIRST candidate request, then let the retry through.
      let seen = 0;
      await page.route(STEP_CANDIDATES_GLOB, async (route) => {
        seen += 1;
        if (seen === 1) return route.fulfill({ status: 500, body: 'boom' });
        return route.continue();
      });

      await gen.goToStep(KINDS.zephyr.step);
      await expect(gen.candidateTable('zephyr'))
        .toContainText(/Could not load candidates/i, { timeout: 20_000 });

      // A failure must NOT be memoized, or the step would stay broken until reload.
      await gen.goToStep(0);
      await gen.openStepAndWaitForCandidates('zephyr');
      expect(seen).toBeGreaterThanOrEqual(2);
      expect(await gen.candidateRows('zephyr').count()).toBeGreaterThan(0);
    });

  test('an invalid step is rejected by the API', async ({ request }) => {
    for (const bad of [0, 4, 99]) {
      const res = await request.get(`/api/wizard/step_candidates/${CASE_A}/${bad}`);
      expect(res.status()).toBe(400);
    }
  });

  test('an unknown case key is rejected by the API', async ({ request }) => {
    const res = await request.get('/api/wizard/step_candidates/AWPTCM-T00000/1');
    expect(res.status()).toBe(404);
  });
});

test('the whole deferred journey produces no console errors', async ({ page }) => {
  const gen = new GeneratorPage(page);
  await gen.open();
  const errors = gen.trackConsoleErrors();

  await gen.loadCase(CASE_A);
  for (const name of KIND_NAMES) await gen.openStepAndWaitForCandidates(name);
  await gen.goToStep(0);

  expect(errors).toEqual([]);
});
