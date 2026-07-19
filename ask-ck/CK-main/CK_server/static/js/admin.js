// Admin panel — hidden maintenance controls, revealed by DOUBLE-clicking CK's
// face (top-left sidebar logo). Single-click still goes Home; double-click opens
// this panel. Reset session state, rebuild search data, or restart the server
// without a terminal. Heavy rebuilds run server-side as background jobs; we poll
// /api/admin/job and show a live tail. See routers/admin.py.
import { registerActions } from './actions.js';
import { S } from './state.js';
import { goToPanel } from './nav.js';

let _pollTimer = null;

export function openAdminPanel() {
  goToPanel('panel-admin');
  refreshAdminStatus();
}

async function refreshAdminStatus() {
  const el = document.getElementById('admin-status');
  if (!el) return;
  try {
    const r = await fetch('/api/admin/status');
    const d = await r.json();
    const db = d.db || {};
    const c = db.counts || {};
    const vec = db.vector_search ? 'on' : 'off';
    const parts = Object.entries(c).map(([k, v]) => `${k}:${v}`).join(' · ');
    el.textContent = `DB ${db.ok ? 'ready' : 'NOT ready'} — ${parts || 'no counts'} · vectors ${vec}`
      + (db.embeddings != null ? ` · ${db.embeddings} embeddings` : '');
    if (d.job && d.job.state && d.job.state !== 'idle') renderJob(d.job);
  } catch (e) {
    el.textContent = 'Status unavailable: ' + e;
  }
}

function renderJob(job) {
  const view = document.getElementById('admin-job-view');
  if (!view) return;
  view.classList.remove('hidden');
  const dur = job.started
    ? Math.round(((job.finished || (Date.now() / 1000)) - job.started)) + 's'
    : '';
  view.textContent = `job: ${job.name || '-'} · ${job.state} ${dur}`
    + (job.returncode != null ? ` · rc=${job.returncode}` : '')
    + (job.tail ? `\n\n${job.tail}` : '');
}

function startPolling() {
  if (_pollTimer) return;
  _pollTimer = setInterval(async () => {
    try {
      const r = await fetch('/api/admin/job');
      const job = await r.json();
      renderJob(job);
      if (job.state !== 'running') { clearInterval(_pollTimer); _pollTimer = null; refreshAdminStatus(); }
    } catch (_) { clearInterval(_pollTimer); _pollTimer = null; }
  }, 1500);
}

async function post(path, body) {
  const r = await fetch('/api/admin' + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}),
  });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.detail || ('HTTP ' + r.status));
  return d;
}

// --- session resets ----------------------------------------------------------
async function adminResetCase() {
  const key = S.currentKey;
  if (!key) { alert('No case is loaded. Load a case first, or use "Reset ALL sessions".'); return; }
  if (!confirm(`Reset the session for ${key}?\nSelections / confirms / synthesis for this case will be cleared. Corpora and your LLM login are kept.`)) return;
  try {
    const d = await post('/reset-session', { scope: 'case', key });
    alert('Cleared: ' + (d.cleared || []).join(', '));
    refreshAdminStatus();
  } catch (e) { alert('Reset failed: ' + e); }
}

async function adminResetWorkspace() {
  if (!confirm('Reset the workspace LLM config?\nThe saved provider/login default will be cleared (you can re-apply it on Configure). Cases and corpora are untouched.')) return;
  try {
    const d = await post('/reset-session', { scope: 'workspace' });
    alert('Cleared: ' + (d.cleared || []).join(', '));
  } catch (e) { alert('Reset failed: ' + e); }
}

async function adminResetAll() {
  if (!confirm('Reset ALL sessions?\nEVERY case\'s wizard/pytest progress and the workspace LLM default will be cleared. This does NOT touch corpora (Zephyr/TestLink/ATP) — only your working sessions. Continue?')) return;
  try {
    const d = await post('/reset-session', { scope: 'all' });
    alert('Cleared: ' + (d.cleared || []).join(', ') + '\n\nReload the page for a clean slate.');
  } catch (e) { alert('Reset failed: ' + e); }
}

// --- rebuilds (background) ----------------------------------------------------
async function adminRebuildEmbeddings() {
  if (!confirm('Rebuild semantic-search vectors?\nRuns build_db.py --embed in the background (downloads the model on first run; a few minutes CPU). Keyword search keeps working meanwhile.')) return;
  try { await post('/rebuild-embeddings'); startPolling(); refreshAdminStatus(); }
  catch (e) { alert('Could not start: ' + e); }
}

async function adminRebuildDb() {
  const embed = !!document.getElementById('admin-rebuild-embed')?.checked;
  if (!confirm(`Rebuild the ENTIRE database (full re-ingest of all corpora)${embed ? ' + embeddings' : ''}?\nThis is heavy and takes a while. Sessions are preserved. Runs in the background.`)) return;
  try { await post('/rebuild-db', { embed }); startPolling(); refreshAdminStatus(); }
  catch (e) { alert('Could not start: ' + e); }
}

// --- restart -----------------------------------------------------------------
async function adminRestart() {
  if (!confirm('Restart the server?\nThe app reloads (dev server runs with --reload). The page will briefly lose connection and then reconnect.')) return;
  try {
    await post('/restart');
    const el = document.getElementById('admin-status');
    if (el) el.textContent = 'Restarting… reconnecting in a moment.';
    // Give uvicorn a beat to reload, then reload the page to reconnect fresh.
    setTimeout(() => window.location.reload(), 2500);
  } catch (e) { alert('Restart failed: ' + e); }
}

registerActions({
  adminResetCase, adminResetWorkspace, adminResetAll,
  adminRebuildEmbeddings, adminRebuildDb, adminRestart,
});
