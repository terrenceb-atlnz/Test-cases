// ============================================================================
// Per-tab session id + X-CK-Session / X-CK-Panel header injection.
// Each browser tab gets a unique id so the shared server can route claude_agent
// LLM jobs back to THIS user's browser (and thus their own local ck-agent).
// X-CK-Panel carries the active panel so the server's LLM debug log can
// attribute each request to the page that triggered it (llm-debug.js).
// We patch window.fetch once so every same-origin /api call carries the headers
// without touching each call site.
// ============================================================================
import { S } from './state.js';

const CK_SESSION_ID = (function () {
  let id = sessionStorage.getItem('ckSessionId');
  if (!id) {
    id = 'sess-' + Math.random().toString(36).slice(2) + '-' + Date.now().toString(36);
    sessionStorage.setItem('ckSessionId', id);
  }
  return id;
})();
// The SEAT's LLM choice (PLAN-seat-setup-and-per-seat-llm.md §5): what this browser
// applied under LLM → Configure, stored in localStorage by llm.js, sent on every /api call
// as X-CK-LLM so the server dispatches THIS seat's requests to THIS seat's backend. Absent
// (no stored choice) means "use the site default". Format: auth;model;unit;match.
// Mirrors models.SUPPORTED_AUTH_METHODS. A stored choice outside it (e.g. a browser that
// last applied a since-retired mode) is NOT sent: the server would 400 every request, and
// the right outcome for that seat is the site default until it chooses again.
export const SEAT_LLM_METHODS = ['local_llm', 'claude_agent'];
// Set when storedSeatLlm() drops a retired choice; read by llm.js for the one-time notice.
export const SEAT_LLM_RETIRED_KEY = 'ckSeatLlmRetired';

export function seatLlmHeaderValue(cfg) {
  if (!cfg || !cfg.auth_method) return '';
  if (!SEAT_LLM_METHODS.includes(String(cfg.auth_method).toLowerCase())) return '';
  const f = (v) => (v == null ? '' : String(v)).replace(/[;\r\n]/g, '');
  return [f(cfg.auth_method), f(cfg.model), f(cfg.unit_model), f(cfg.match_model)].join(';');
}

export function storedSeatLlm() {
  try {
    const raw = localStorage.getItem('draftingLLMConfig');
    const cfg = raw ? JSON.parse(raw) : null;
    if (cfg && cfg.auth_method && !SEAT_LLM_METHODS.includes(String(cfg.auth_method).toLowerCase())) {
      // Self-heal: a retired stored choice is dropped so the seat falls back to the site
      // default and the Configure panel shows what its requests will actually get. The drop
      // is remembered so LLM → Configure can say so once (llm.js renders it; the seat's next
      // Apply clears it) — plan §11.3, decision D14.
      try { localStorage.setItem(SEAT_LLM_RETIRED_KEY, String(cfg.auth_method)); } catch (_) {}
      localStorage.removeItem('draftingLLMConfig');
      return null;
    }
    return cfg;
  } catch (_) { return null; }
}

(function patchFetch() {
  const orig = window.fetch;
  window.fetch = function (input, init) {
    try {
      const url = (typeof input === 'string') ? input : (input && input.url) || '';
      // Only attach to our own API (never to the localhost agent or external hosts).
      const sameApi = url.startsWith('/api/') || url.includes(location.host + '/api/');
      if (sameApi) {
        init = init || {};
        const headers = new Headers(init.headers || (typeof input !== 'string' && input.headers) || {});
        headers.set('X-CK-Session', CK_SESSION_ID);
        if (S.currentPanel) headers.set('X-CK-Panel', S.currentPanel);
        const seat = seatLlmHeaderValue(storedSeatLlm());
        if (seat) headers.set('X-CK-LLM', seat);
        init.headers = headers;
      }
    } catch (_) { /* never break fetch */ }
    return orig.call(this, input, init);
  };
})();

export { CK_SESSION_ID };
