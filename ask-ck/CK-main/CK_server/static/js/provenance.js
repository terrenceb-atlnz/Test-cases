// Shared "LLM Provenance" block — a portable view of the exact prompt that
// would be sent for a given panel's LLM call. Purpose: copy the prompt to paste
// into a competing LLM (comparative analysis / free-LLM fallback), and/or see
// what was actually sent.
//
// Refresh = re-render the prompt from CURRENT session state WITHOUT sending it
// to the LLM (the backend endpoint accepts dry_run:true and returns the rendered
// prompt only — no tokens). Because the preview reuses the real call path with a
// flag flipped, the previewed/copied prompt is 1-for-1 with a real send.
import { registerActions } from './actions.js';
import { escapeHtml, setButtonBusy, flashButtonDone } from './dom-helpers.js';

// panelId -> { endpoint, body, prompt, response, provider, model, auth_method }
const provByPanel = {};

// Register a panel's provenance source so Refresh knows which endpoint to
// dry-run. `bodyFn` returns the request body (minus dry_run) at click time so it
// always reflects current naming/inputs. Optional `seed` fills initial values
// (e.g. prompt/response from the last real call stored on the session).
export function registerProvenance(panelId, endpointFn, bodyFn, seed) {
  provByPanel[panelId] = { endpointFn, bodyFn: bodyFn || (() => ({})), ...(seed || {}) };
}

export function renderProvenanceBlock(panelId) {
  const p = provByPanel[panelId];
  if (!p) return '';
  const hasPrompt = !!(p.prompt && p.prompt.length);
  const meta = [p.provider, p.model, p.auth_method].filter(Boolean).join(' / ');
  return `
    <details class="provenance-details" data-prov-panel="${escapeHtml(panelId)}">
      <summary class="provenance-summary">LLM Provenance${meta ? ' — ' + escapeHtml(meta) : ''}</summary>
      <div class="provenance-actions">
        <button type="button" class="btn btn-secondary btn-compact-small"
                data-action="provRefresh" data-prov-panel="${escapeHtml(panelId)}"
                title="Re-render the exact prompt from current state without sending (no tokens)">↻ Refresh (no send)</button>
        <button type="button" class="btn btn-secondary btn-compact-small"
                data-action="provCopyPrompt" data-prov-panel="${escapeHtml(panelId)}"
                ${hasPrompt ? '' : 'disabled'}>Copy prompt</button>
        <button type="button" class="btn btn-secondary btn-compact-small"
                data-action="provCopyResponse" data-prov-panel="${escapeHtml(panelId)}"
                ${p.response ? '' : 'disabled'}>Copy response</button>
        <span class="provenance-status" data-prov-status="${escapeHtml(panelId)}"></span>
      </div>
      <div class="provenance-label">Prompt (what would be sent)</div>
      <pre class="provenance-pre" data-prov-prompt="${escapeHtml(panelId)}">${hasPrompt ? escapeHtml(p.prompt) : '(press Refresh to render the current prompt without sending)'}</pre>
      ${p.response ? `<div class="provenance-label">Response (last send)</div>
      <pre class="provenance-pre" data-prov-response="${escapeHtml(panelId)}">${escapeHtml(p.response)}</pre>` : ''}
    </details>`;
}

// Seed provenance from a session step's stored provenance (after a real call).
export function seedProvenanceFromStep(panelId, stepProv) {
  const p = provByPanel[panelId];
  if (!p || !stepProv) return;
  const llm = stepProv.llm || stepProv;
  p.prompt = stepProv.prompt || stepProv.objective_prompt || stepProv.steps_prompt || stepProv.gaps_prompt || p.prompt || '';
  p.response = stepProv.response || stepProv.objective_response || stepProv.steps_response || p.response || '';
  p.provider = llm.provider || p.provider;
  p.model = llm.model || p.model;
  p.auth_method = llm.auth_method || p.auth_method;
}

function setStatus(panelId, msg, isErr) {
  const el = document.querySelector(`[data-prov-status="${CSS.escape(panelId)}"]`);
  if (el) { el.textContent = msg || ''; el.style.color = isErr ? 'var(--status-low,#ef4444)' : ''; }
}

async function provRefresh() {
  const el = this;  // dispatcher calls fn.apply(el, args) — el is `this`
  const btn = el instanceof HTMLElement ? el : null;
  const panelId = el.getAttribute('data-prov-panel');
  const p = provByPanel[panelId];
  if (!p) return;
  if (!setButtonBusy(btn, true, { label: 'Rendering…' })) return;   // guard double-click
  setStatus(panelId, '⏳ rendering…');
  let ok = false;
  try {
    const res = await fetch(p.endpointFn(), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...p.bodyFn(), dry_run: true }),
    });
    // An error body is JSON too, so parsing alone proves nothing: a 400/404/500 used
    // to fall through and render as a green "(empty)" success, discarding the
    // actionable `detail`. Same idiom as admin.js:41 — the throw lands in the catch
    // below, which already styles the status red and leaves ok=false for the flash.
    const d = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(d.detail || ('HTTP ' + res.status));
    const prov = d.provenance || d;
    p.prompt = prov.prompt || '';
    p.provider = prov.provider || p.provider;
    p.model = prov.model || p.model;
    p.auth_method = prov.auth_method || p.auth_method;
    const pre = document.querySelector(`[data-prov-prompt="${CSS.escape(panelId)}"]`);
    if (pre) pre.textContent = p.prompt || (prov.note ? `(${prov.note})` : '(empty)');
    const copyBtn = document.querySelector(`[data-action="provCopyPrompt"][data-prov-panel="${CSS.escape(panelId)}"]`);
    if (copyBtn) copyBtn.disabled = !(p.prompt && p.prompt.length);
    setStatus(panelId, p.prompt ? `✓ ${p.prompt.length} chars (not sent)` : (prov.note || 'empty'));
    ok = true;
  } catch (e) {
    setStatus(panelId, `✗ ${e.message || e}`, true);
  } finally {
    setButtonBusy(btn, false);
    flashButtonDone(btn, ok);
  }
}

async function copyText(text, panelId) {
  try {
    await navigator.clipboard.writeText(text || '');
    setStatus(panelId, '✓ copied');
  } catch (_) {
    setStatus(panelId, '✗ copy failed (clipboard blocked)', true);
  }
}

function provCopyPrompt() {
  const panelId = this.getAttribute('data-prov-panel');
  copyText((provByPanel[panelId] || {}).prompt, panelId);
}

function provCopyResponse() {
  const panelId = this.getAttribute('data-prov-panel');
  copyText((provByPanel[panelId] || {}).response, panelId);
}

registerActions({ provRefresh, provCopyPrompt, provCopyResponse });
