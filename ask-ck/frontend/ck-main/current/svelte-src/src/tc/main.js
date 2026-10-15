// Entry of the `tc` island (Test Composer, and Run Scripts beside it) → ../islands/tc.js, mounted by
// current/test-composer/test-composer.js.
import { flushSync, mount, unmount } from 'svelte';
import RsPage from './RsPage.svelte';
import TcPage from './TcPage.svelte';
import { httpAgent, httpServer } from './api.js';

export function mountTc(target, opts = {}) {
  const app = mount(TcPage, { target, props: {
    server: opts.server || httpServer(), agent: opts.agent || httpAgent(opts.agentUrl),
    preselect: opts.preselect || null, openRun: opts.openRun || null,
    ...(opts.saveScript ? { saveScript: opts.saveScript } : {}), ...(opts.pollMs ? { pollMs: opts.pollMs } : {}) } });
  return { destroy() { unmount(app); } };
}

/** Run Scripts (PLAN-run-scripts): `link` is a parsed share link, which fills the page and never launches. */
export function mountRs(target, opts = {}) {
  const app = mount(RsPage, { target, props: {
    server: opts.server || httpServer(), agent: opts.agent || httpAgent(opts.agentUrl),
    link: opts.link || null, openRun: opts.openRun || null } });
  return { destroy() { unmount(app); } };
}

export * from './api.js';
export { flushSync };
