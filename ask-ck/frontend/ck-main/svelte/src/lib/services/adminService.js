// COPIED OVER FROM current/admin/admin.js
// NOT PORTED (Svelte has no equivalent need):
//   - openAdminPanel()/goToPanel() — the Svelte reveal is local `isAdmin` state on
//     HomePage.svelte, not a router panel switch.
//   - registerActions({...}) — that's the vanilla data-action dispatch system;
//     Svelte binds on:click directly, so there is nothing to register into.

// @ts-nocheck
const ADMIN_API = '/api/admin';

export async function fetchAdminStatus() {
  try {
    const r = await fetch(`${ADMIN_API}/status`);
    return await r.json();
  } catch (e) {
    return { db: { ok: false, error: String(e) } };
  }
}

// MODIFIED FROM current/admin/admin.js TO WORK WITH SVELTE
// (refreshAdminStatus wrote straight into #admin-status' textContent; this returns the
// same string so the component can render it.)
export function describeAdminStatus(data) {
  const db = (data && data.db) || {};
  const c = db.counts || {};
  const vec = db.vector_search ? 'on' : 'off';
  const parts = Object.entries(c).map(([k, v]) => `${k}:${v}`).join(' · ');
  return `DB ${db.ok ? 'ready' : 'NOT ready'} — ${parts || 'no counts'} · vectors ${vec}`
    + (db.embeddings != null ? ` · ${db.embeddings} embeddings` : '');
}

async function post(path, body) {
  const r = await fetch(ADMIN_API + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}),
  });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.detail || ('HTTP ' + r.status));
  return d;
}

export async function resetWorkspaceLlmConfig() {
  return post('/reset-session', { scope: 'workspace' });
}

export async function resetAllSessions() {
  return post('/reset-session', { scope: 'all' });
}

export async function restartServer() {
  return post('/restart');
}
