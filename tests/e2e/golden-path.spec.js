// Ask-CK golden-path E2E — the deterministic, non-LLM integration gate.
//
// WHY THIS SHAPE (see ask-ck/ck-facelift/PLAN-playwright-e2e.md):
//   The keyword-only path CANNOT produce a green export — /api/wizard/export is
//   gated by validate_zephyr_payload, which requires a synthesized objective
//   (<ul> + >=3 <li>) and >=2 test steps, both LLM-only artefacts. So the honest,
//   100%-deterministic assertion (Option A) is that Export on an un-synthesized
//   case is *blocked* with an error banner. This exercises the entire non-LLM
//   frontend surface — boot, nav, case-load, all three keyword searches, the
//   merge/dedup/choose machinery, and the export round-trip + its gate — without
//   any LLM dependency or on-disk fixture that could drift.
//
// This is the "known-good reference" the Vitest unit layer is derived from.
import { test, expect } from '@playwright/test';
import { GeneratorPage } from './pages/generator.page.js';

// A real open/partial case present in ck.db (verified via /api/wizard/cases).
// Picked dynamically in beforeAll so a single re-keyed case doesn't break the run.
let CASE_KEY = 'AWPTCM-T30649';
const QUERY = 'vlan'; // returns rows on all three search endpoints (verified)

test.beforeAll(async ({ request }) => {
  // Ground the fixture in live data: use the first open/partial case the server
  // reports, falling back to the hard-coded key if the shape is unexpected.
  try {
    const res = await request.get('/api/wizard/cases');
    const data = await res.json();
    const first = data?.incomplete?.cases?.[0]?.key;
    if (first) CASE_KEY = first;
  } catch {
    /* keep the fallback key */
  }
});

test('golden path: boot → load → search+choose x3 → export is gated (no-LLM)', async ({ page }) => {
  const gen = new GeneratorPage(page);

  await test.step('app boots to the shell', async () => {
    await gen.open();
  });

  await test.step('load a real open/partial case', async () => {
    await gen.loadCase(CASE_KEY);
  });

  await test.step('keyword-search + choose candidates on all three tabs', async () => {
    const tl = await gen.searchAndChoose('testlink', QUERY, 2);
    const zp = await gen.searchAndChoose('zephyr', QUERY, 2);
    const atp = await gen.searchAndChoose('atp', QUERY, 2);
    // The whole point of the middle of the journey: real results were merged and
    // moved into the chosen tables. At least one kind must have produced rows.
    expect(tl + zp + atp).toBeGreaterThan(0);
  });

  await test.step('export is deterministically blocked (validation gate fires)', async () => {
    await gen.exportFromCasesPanel();
    const banner = gen.statusBanner();
    // The gate returns wrote_bundle:false → showStatus('error', ...) →
    // class becomes "status-banner is-error". This is the deterministic outcome
    // for an un-synthesized case; a green success would require LLM synthesis.
    await expect(banner).toHaveClass(/is-error/, { timeout: 15_000 });
    // Assert the real block headline (content assertions don't require the banner
    // to be in-viewport — it lives at the bottom of the Cases panel).
    await expect(banner).toContainText(/Export blocked|did not pass validation/i);
    // And it must NOT have silently succeeded.
    await expect(banner).not.toHaveClass(/is-success/);
  });
});
