// Entry of the `zt` island → ../islands/zt.js. current/zephyr-tool/zephyr-tool.js imports it on
// first show of the panel and calls mountZt(#zt-root). `api` and `pollMs` are injectable so the
// specs drive the BUILT bundle with a fake server (tests/js/zt-page.spec.js).
import { flushSync, mount, unmount } from 'svelte';
import ZtPage from './ZtPage.svelte';

export const ZT_API = '/api/zephyr-tool';

/** fetch() against the zephyr-tool router; throws the server's `detail` (string or {error}). */
export function httpApi(base = ZT_API) {
  return async function api(path, opts = {}) {
    const r = await fetch(base + path, Object.assign({ headers: { 'Content-Type': 'application/json' } }, opts));
    const d = await r.json().catch(() => ({}));
    if (!r.ok) {
      const det = d.detail;
      throw new Error(typeof det === 'string' ? det : det && det.error ? det.error : `HTTP ${r.status}`);
    }
    return d;
  };
}

export function mountZt(target, opts = {}) {
  const app = mount(ZtPage, { target, props: { api: opts.api || httpApi(), pollMs: opts.pollMs ?? 2000 } });
  return { destroy() { unmount(app); } };
}

export { flushSync };
