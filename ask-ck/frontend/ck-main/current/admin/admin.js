// Admin panel — hidden maintenance controls, revealed by DOUBLE-clicking CK's
// face (top-left sidebar logo). Single-click still goes Home; double-click opens
// this panel. Reset session state or restart the server without a terminal.
//
// DB rebuild is intentionally absent: ck.db is the permanent single source of
// truth (built once; source couriers retired), so nothing here can wipe/refill
// corpora — only sessions and the server process are mutable. See routers/admin.py.
import { registerActions } from './actions.js';
import { S } from './state.js';
import { goToPanel } from './nav.js';

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
  } catch (e) {
    el.textContent = 'Status unavailable: ' + e;
  }
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
  adminResetCase, adminResetWorkspace, adminResetAll, adminRestart,
});
