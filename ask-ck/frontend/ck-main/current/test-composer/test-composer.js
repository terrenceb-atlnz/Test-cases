// Test Composer, Validation and Run Scripts — the adapters nav.js calls when their panels are shown
// (PLAN-test-composer §6, PLAN-test-validation, PLAN-run-scripts). The pages are Svelte islands
// (../svelte-src/src/tc, ../svelte-src/src/vd → ../islands/tc.js, vd.js; Run Scripts is mountRs in
// tc.js), mounted once into #tc-root / #vd-root / #rs-root. The seat agent's URL comes from llm-config/agent.js, the one place that
// resolves it (?agent-port / localStorage / window.CK_AGENT_URL / 127.0.0.1:8765).
import { resolveAgentUrl } from '../llm-config/agent.js';

const mounted = {};
let pending = { tc: {}, vd: {}, rs: {} };

export function agentUrl() {
  let store = null;
  try { store = window.localStorage; } catch (_) { /* private mode */ }
  return resolveAgentUrl({ search: window.location.search, store, injected: window.CK_AGENT_URL });
}

/** Run Scripts' share link → what it fills (PLAN-run-scripts §3; built by islands/tc.js scriptsLink).
 *  There is no email field to read: a link never carries one. */
export function scriptsLinkFields(q) {
  const get = (k) => (q.get(k) || '').trim();
  const setup = {};
  for (const [k, f] of [['testbox', 'testbox'], ['consoles', 'consoles'], ['pdu', 'pduIp'], ['outlets', 'outlets'], ['constraints', 'constraints']]) {
    if (get(k)) setup[f] = get(k);
  }
  return { source: get('source') || 'generated', scripts: get('scripts').split(',').map(s => s.trim()).filter(Boolean),
    setup, start: get('start') || null };
}

/** Deep links (pure): `?panel=composer&script=<group>/<file>` (Finalize's Zephyr link, PLAN-test-
 *  composer §5), `?panel=validation&script=…`, `?panel=run-scripts&…` (a Run Scripts share link),
 *  and `?panel=tc-runs&run=<run id>` (the run e-mails, routed by the run id's kind). */
export function deepLink(search) {
  const q = new URLSearchParams(search || '');
  const panel = q.get('panel');
  const run = q.get('run');
  if (panel === 'composer') return { panel: 'panel-tc', island: 'tc', opts: { preselect: q.get('script'), openRun: run } };
  if (panel === 'validation') return { panel: 'panel-vd', island: 'vd', opts: { preselect: q.get('script'), openRun: run } };
  if (panel === 'run-scripts') return { panel: 'panel-rs', island: 'rs', opts: { link: scriptsLinkFields(q), openRun: run } };
  if (panel === 'tc-runs' && run) {
    if (/-val-/.test(run)) return { panel: 'panel-vd', island: 'vd', opts: { openRun: run } };
    if (/-scr-/.test(run)) return { panel: 'panel-rs', island: 'rs', opts: { openRun: run } };
    return { panel: 'panel-tc', island: 'tc', opts: { openRun: run } };
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

/** Open Validation on one script (`<group>/<name>.py`, or a case key) — the PyTest Creator's
 *  "test the new script?" pop-up. An island already mounted is told directly; one not mounted
 *  yet (or still mounting) reads it from `pending` when it mounts. */
export function openValidation(goToPanel, preselect) {
  const app = mounted.vd;
  if (app && typeof app.select === 'function') app.select(preselect);
  else pending.vd = Object.assign({}, pending.vd, { preselect });
  goToPanel('panel-vd');
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
export function renderRsPanel() { return mountIsland('rs', 'rs-root', () => import('../islands/tc.js'), 'mountRs'); }
