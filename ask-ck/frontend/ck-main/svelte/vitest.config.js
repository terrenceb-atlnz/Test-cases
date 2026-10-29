// Vitest config for the Svelte frontend's unit + component tests (jsdom tier).
// Separate from vite.config.js so the dev server's config stays untouched — Vitest uses
// this file instead of vite.config.js whenever both exist.
//
// tests/e2e/ is excluded: those specs are Playwright's, not Vitest's.
import { defineConfig } from 'vitest/config';
import { svelte } from '@sveltejs/vite-plugin-svelte';
// svelteTesting(): resolves Svelte's browser build (jsdom tests otherwise get the SSR build,
// where mount() is unavailable) and unmounts rendered components after each test.
import { svelteTesting } from '@testing-library/svelte/vite';

export default defineConfig({
  plugins: [svelte(), svelteTesting()],
  test: {
    environment: 'jsdom',
    include: ['tests/**/*.spec.js'],
    exclude: ['tests/e2e/**', 'node_modules/**'],
    setupFiles: ['./tests/setup.js'],     // added: runs before every spec file
    globals: true,
    restoreMocks: true,
    clearMocks: true,
    coverage: {
      provider: 'v8', // or 'istanbul'
      include: ['src/**/*.{js,svelte}'],   // measure your app code, not the tests
      // Write the report even when a spec fails (e.g. an empty placeholder spec) — by
      // default Vitest skips the report on any failure.
      reportOnFailure: true,
    },
  },
});
