// Vitest config for the Ask-CK frontend unit layer (jsdom tier).
// Runs REGULARLY after big changes — the cheap counterpart to the sparingly-run
// Playwright E2E. Covers the ~80% of the frontend that is pure logic (tables,
// chosen/merge machinery, DOM helpers, dispatcher) with no browser/server/LLM.
// See archive/plans/PLAN-frontend-unit-tests.md (complete; archived 2026-09-11).
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    // jsdom gives us document/window so the render fns + helpers run unchanged.
    environment: 'jsdom',
    // Tests live OUT of the module tree (tests/js/, beside the backend tests), by design.
    include: ['tests/js/**/*.spec.js'],
    // A reset between tests keeps window.* candidate buses / DOM from leaking
    // across specs (the app stores chosen lists on window.*Chosen).
    globals: true,
    restoreMocks: true,
    clearMocks: true,
  },
});
