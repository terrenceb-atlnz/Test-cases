// Entry of the `vd` island (Validation) → ../islands/vd.js, mounted by current/validation/validation.js.
import { flushSync, mount, unmount } from 'svelte';
import VdPage from './VdPage.svelte';
import { httpAgent, httpServer } from '../tc/api.js';

export function mountVd(target, opts = {}) {
  const app = mount(VdPage, { target, props: {
    server: opts.server || httpServer(), agent: opts.agent || httpAgent(opts.agentUrl),
    preselect: opts.preselect || null, openRun: opts.openRun || null,
    ...(opts.saveScript ? { saveScript: opts.saveScript } : {}), ...(opts.pollMs ? { pollMs: opts.pollMs } : {}) } });
  return { destroy() { unmount(app); } };
}

export { flushSync };
