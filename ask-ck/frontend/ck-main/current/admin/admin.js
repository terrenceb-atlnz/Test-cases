// Admin panel — hidden maintenance controls, revealed by DOUBLE-clicking CK's
// face (top-left sidebar logo). Single-click still goes Home; double-click opens
// this panel. Reset session state or restart the server without a terminal.
//
// DB rebuild is intentionally absent: ck.db is the permanent single source of
// truth (built once; source couriers retired), so nothing here can wipe/refill
// corpora — only sessions and the server process are mutable. See routers/admin.py.
import { registerActions } from '../shared/actions.js';
import { S } from '../shared/state.js';
import { goToPanel } from '../shared/nav.js';
import { escapeHtml } from '../shared/dom-helpers.js';

export function openAdminPanel() {
  goToPanel('panel-admin');
  refreshAdminStatus();
  refreshLintTrends();
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

// --- R5 lint trends (PLAN-self-healing-generation.md §6.4) -------------------------------
// The ALWAYS-VISIBLE half of R5's two surfaces; the other is the step-5 Summary banner, which
// appears only while an alarm stands. This card renders its numbers whether or not a threshold
// is crossed, and turns red when one is. A card that appeared only on alarm would make "nothing
// is wrong" and "nothing was ever recorded" look identical — the silent-degradation failure
// this panel exists to make impossible (see the 2026-07-30 audit).
//
// Read-only by design. The thresholds are server constants in routers/pytest_create.py
// (_PT_TREND_WINDOW, _PT_PROMPT_DEFECT_UNIT_FRACTION, _PT_PROMPT_DEFECT_CONSECUTIVE,
// _PT_LINT_TEXT_RETURN_RATE). §6.4 also wants them editable from here; that is backend work
// and deliberately NOT in this slice.
//
// /lint_trends answers in three shapes and all three land here: a normal aggregate, a thin one
// ({runs: 0} — no total_units/repair/return_rate), and a failure ({error} — no window, no
// by_class, no prompt_version). Read every field defensively.
const _QUIET = 'justification-note mb-2';

export function renderLintTrendsCard(d) {
  if (!d) return { className: _QUIET, html: 'Lint trends unavailable.' };
  if (d.error) return { className: _QUIET, html: 'Lint trends unavailable: ' + escapeHtml(String(d.error)) };
  if (!d.runs) {
    return { className: _QUIET,
             html: 'No assembly runs recorded yet — the trend starts at the first Assemble.' };
  }
  const byClass = Object.entries(d.by_class || {}).map(([k, v]) => `${k}:${v}`).join(' · ') || 'none';
  const rr = (d.return_rate == null) ? 'n/a (no repairs attempted)' : Math.round(d.return_rate * 100) + '%';
  const alarms = d.alarms || [];
  const head = `${d.runs} run(s)`
    + (d.window ? ` in a window of ${d.window}` : '')
    + (d.total_units != null ? ` · ${d.total_units} unit(s)` : '')
    + (d.prompt_version ? ` · prompt version ${d.prompt_version}` : '');
  const body = `<div>${escapeHtml(head)}</div>`
    + `<div>lint errors by class — ${escapeHtml(byClass)}</div>`
    + `<div>repair return rate — ${escapeHtml(rr)}</div>`;
  if (!alarms.length) {
    return { className: _QUIET, html: body + '<div>no threshold crossed</div>' };
  }
  return {
    className: 'status-banner is-error',
    html: '<div class="status-title">⚠ Lint trend alarm</div>'
      + `<ul>${alarms.map(a => `<li>${escapeHtml(a.detail || a.class || '')}</li>`).join('')}</ul>`
      + `<div class="justification-note">${body}</div>`,
  };
}

async function refreshLintTrends() {
  const el = document.getElementById('admin-lint-trends');
  if (!el) return;
  let d = null;
  try {
    const r = await fetch('/api/pytest-create/lint_trends');
    if (r.ok) d = await r.json();
    else d = { error: 'HTTP ' + r.status };
  } catch (e) { d = { error: String(e) }; }
  const c = renderLintTrendsCard(d);
  el.className = c.className;
  el.innerHTML = c.html;
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
