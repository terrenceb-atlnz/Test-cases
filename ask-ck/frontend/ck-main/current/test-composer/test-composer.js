// Test Composer + Validation — the adapters nav.js calls when their panels are shown
// (PLAN-test-composer §6, PLAN-test-validation). Both pages are Svelte islands
// (../svelte-src/src/tc, ../svelte-src/src/vd → ../islands/tc.js, vd.js), mounted once into
// #tc-root / #vd-root. The seat agent's URL comes from llm-config/agent.js, the one place that
// resolves it (?agent-port / localStorage / window.CK_AGENT_URL / 127.0.0.1:8765).
import { resolveAgentUrl } from '../llm-config/agent.js';

const mounted = {};
let pending = { tc: {}, vd: {} };

export function agentUrl() {
  let store = null;
  try { store = window.localStorage; } catch (_) { /* private mode */ }
  return resolveAgentUrl({ search: window.location.search, store, injected: window.CK_AGENT_URL });
}

/** Deep links (pure): `?panel=composer&script=<group>/<file>` (Finalize's Zephyr link, PLAN-test-
 *  composer §5), `?panel=validation&script=…`, and `?panel=tc-runs&run=<run id>` (the run e-mails). */
export function deepLink(search) {
  const q = new URLSearchParams(search || '');
  const panel = q.get('panel');
  const run = q.get('run');
  if (panel === 'composer') return { panel: 'panel-tc', island: 'tc', opts: { preselect: q.get('script'), openRun: run } };
  if (panel === 'validation') return { panel: 'panel-vd', island: 'vd', opts: { preselect: q.get('script'), openRun: run } };
  if (panel === 'tc-runs' && run) {
    const vd = /-val-/.test(run);
    return { panel: vd ? 'panel-vd' : 'panel-tc', island: vd ? 'vd' : 'tc', opts: { openRun: run } };
  }
  return null;
}

/** Called once after the session restore (main.js): a deep link wins over the restored panel. */
export function applyDeepLink(goToPanel, search = window.location.search) {
  const d = deepLink(search);
  if (!d) return false;
  pending[d.island] = d.opts;
  goToPanel(d.panel);
  return true;
}

async function mountIsland(name, rootId, load, fn) {
  if (mounted[name]) return;
  const root = document.getElementById(rootId);
  if (!root) return;
  mounted[name] = 'mounting';
  try {
    const mod = await load();
    mounted[name] = mod[fn](root, Object.assign({ agentUrl: agentUrl() }, pending[name] || {}));
  } catch (e) {
    mounted[name] = null;
    root.textContent = `Could not load this page: ${e.message}`;
  }
}

export function renderTcPanel() { return mountIsland('tc', 'tc-root', () => import('../islands/tc.js'), 'mountTc'); }
export function renderVdPanel() { return mountIsland('vd', 'vd-root', () => import('../islands/vd.js'), 'mountVd'); }
