// Playwright config for the Ask-CK E2E gate.
// SPARINGLY-RUN — this is the golden-path integration layer, not a per-commit gate.
// See ask-ck/ck-facelift/PLAN-playwright-e2e.md for the full design + rationale.
import { defineConfig, devices } from '@playwright/test';

const BASE_URL = process.env.CK_BASE_URL || 'http://localhost:8000';

export default defineConfig({
  testDir: './e2e',
  outputDir: './e2e/.artifacts',
  // Deterministic gate: no test-level retries (a flake should be seen, not masked),
  // fully serial (the app is stateful — one session/case at a time on the server).
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 60_000,             // whole-test budget; LLM is NOT on the asserted path
  expect: { timeout: 10_000 }, // per-assertion wait (search round-trips, table repaint)
  reporter: [['list'], ['html', { outputFolder: 'e2e/.report', open: 'never' }]],
  use: {
    baseURL: BASE_URL,
    headless: true,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  // Start the real server if one isn't already up; reuse an existing instance locally.
  // The server reads corpora only from the LFS-materialized ck.db (db-only invariant).
  webServer: {
    command: './run.sh --bg',
    url: `${BASE_URL}/health`,
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
