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
    // Same as the root vitest.config.js, so specs read the same in both suites.
    globals: true,
    restoreMocks: true,
    clearMocks: true,
  },
});
