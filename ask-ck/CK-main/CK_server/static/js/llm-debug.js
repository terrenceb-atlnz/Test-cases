// LLM-request observability: per-panel "last LLM request" footer + token badges.
//
// Records come from GET /api/llm/recent — a separate endpoint, NOT the tool
// responses, so failures (pytest 502s, wizard error-provenance) surface too.
// The per-panel store is a plain object that dies with the page (deliberately
// not persisted across browser sessions); the server keeps the durable history
// in debug-log/<session>.jsonl. See ask-ck/ck-facelift/PLAN-llm-observability.md.
//
// Token counts are shown honestly: transports that don't report usage
// (grok CLI plain output, agent bridge) render as "— tok", never estimated.
import { S } from './state.js';

const llmDebugByPanel = {};   // panel id -> newest record seen for that panel

function fmtTok(n) {
  if (n == null) return '?';
  if (n >= 10000) return (n / 1000).toFixed(1).replace(/\.0$/, '') + 'k';
  return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

export function fmtTokens(usage) {
  if (!usage) return '— tok';
  return `${fmtTok(usage.input_tokens)}→${fmtTok(usage.output_tokens)} tok`;
}

/** Reuse/insert a token badge right after the pressed LLM button. */
export function setTokenBadge(btnEl, usage) {
  if (!btnEl) return;
  let badge = btnEl.nextElementSibling;
  if (!badge || !badge.classList || !badge.classList.contains('llm-token-badge')) {
    badge = document.createElement('span');
    btnEl.insertAdjacentElement('afterend', badge);
  }
  badge.className = 'badge llm-token-badge' + (usage ? ' badge-success' : '');
  badge.textContent = fmtTokens(usage);
  badge.title = (usage && usage.cost_usd != null)
    ? ('$' + usage.cost_usd)
    : (usage ? 'input→output tokens' : 'This transport does not report token usage');
}

/**
 * Fetch the session's recent LLM records and adopt the newest one for the
 * current panel (fallback: newest overall — covers a panel header that raced).
 * Call after any handler that may have triggered an LLM request, success or
 * failure. Badge updates ONLY on success; errors go to the footer.
 */
export async function recordLLMDebug(btnEl) {
  try {
    const res = await fetch('/api/llm/recent?limit=5');
    if (!res.ok) return;
    const data = await res.json();
    const records = data.records || [];
    if (!records.length) return;
    // Server returns oldest→newest; prefer the newest record for THIS panel.
    const mine = records.filter(r => r.panel === S.currentPanel);
    const pool = mine.length ? mine : records;
    const rec = pool[pool.length - 1];
    const prev = llmDebugByPanel[S.currentPanel];
    if (prev && prev.request_id === rec.request_id) return;   // already shown
    llmDebugByPanel[S.currentPanel] = rec;
    renderLlmDebugFooter();
    if (btnEl && !rec.error) setTokenBadge(btnEl, rec.usage);
  } catch (_) { /* a debug aid must never break the flow */ }
}

/** Render (or hide) the footer for the current panel. Hooked into goToPanel. */
export function renderLlmDebugFooter() {
  const box = document.getElementById('llm-debug');
  const view = document.getElementById('llm-debug-view');
  const tag = document.getElementById('llm-debug-tag');
  if (!box || !view) return;
  const rec = llmDebugByPanel[S.currentPanel];
  if (!rec) {
    // No LLM activity on this panel — stay hidden (matches #session-debug).
    box.classList.add('hidden');
    return;
  }
  box.classList.remove('hidden');
  const usageTxt = fmtTokens(rec.usage);
  const head = `${rec.ts || ''} · ${rec.endpoint || ''} · ${rec.template || '(no template)'}`
    + ` · ${rec.provider || '?'}/${rec.model || '?'} via ${rec.auth_method || '?'}`
    + ` · ${rec.duration_ms != null ? rec.duration_ms + 'ms' : '?'} · ${usageTxt}`;
  let text = head + '\n';
  if (rec.error) {
    text += '\n⚠ ERROR\n' + (rec.error_detail || '(no provider error body — see response below)') + '\n';
  }
  text += `\n--- PROMPT ---\n${rec.prompt || ''}\n\n--- RESPONSE ---\n${rec.response || ''}`;
  view.textContent = text;   // textContent: no HTML injection from prompt/response
  if (tag) {
    tag.classList.remove('hidden');
    tag.className = 'badge' + (rec.error ? ' llm-debug-error' : (rec.usage ? ' badge-success' : ''));
    tag.textContent = rec.error ? 'ERROR' : usageTxt;
  }
}
