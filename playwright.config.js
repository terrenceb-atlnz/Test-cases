// Playwright config for the Ask-CK E2E gate.
// SPARINGLY-RUN — this is the golden-path integration layer, not a per-commit gate.
// See ask-ck/ck-facelift/PLAN-playwright-e2e.md for the full design + rationale.
import { defineConfig, devices } from '@playwright/test';

// E2E drives real case loads, which WRITE session rows. It must never do that to
// ask-ck/var/ck.db (the permanent, LFS-committed source of truth), so it runs on its own
// port against a throwaway copy — see tool/run_scratch_server.sh. Port 8123, not 8000,
// precisely so `reuseExistingServer` can never latch onto the real dev server.
const E2E_PORT = process.env.CK_E2E_PORT || '8123';
const BASE_URL = process.env.CK_BASE_URL || `http://localhost:${E2E_PORT}`;

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
  // Start a server against a THROWAWAY copy of ck.db. reuseExistingServer is false on
  // purpose: true meant "attach to whatever is on this URL", and with the old port 8000
  // that was the developer's real-database server — so every E2E run wrote session rows
  // into the permanent ck.db. (Reuse is still effectively free: the scratch copy is cached
  // by ck.db's revision, so start-up is ~0.3s of file copy.)
  webServer: {
    command: './tool/run_scratch_server.sh --bg',
    url: `${BASE_URL}/health`,
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
