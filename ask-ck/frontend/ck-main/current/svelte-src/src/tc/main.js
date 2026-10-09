// Entry of the `tc` island (Test Composer) → ../islands/tc.js, mounted by current/test-composer/test-composer.js.
import { flushSync, mount, unmount } from 'svelte';
import TcPage from './TcPage.svelte';
import { httpAgent, httpServer } from './api.js';

export function mountTc(target, opts = {}) {
  const app = mount(TcPage, { target, props: {
    server: opts.server || httpServer(), agent: opts.agent || httpAgent(opts.agentUrl),
    preselect: opts.preselect || null, openRun: opts.openRun || null,
    ...(opts.saveScript ? { saveScript: opts.saveScript } : {}), ...(opts.pollMs ? { pollMs: opts.pollMs } : {}) } });
  return { destroy() { unmount(app); } };
}

export * from './api.js';
export { flushSync };
