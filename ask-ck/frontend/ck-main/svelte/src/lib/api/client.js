// ============================================================================
// Per-tab session id + X-CK-Session / X-CK-LLM header injection.
// COPIED OVER FROM current/shared/session.js, MODIFIED FOR SVELTE:
//   - no S.currentPanel / X-CK-Panel — that's current/'s per-panel debug-log
//     attribution, and there's no equivalent "current panel" concept here yet.
//   - the fetch patch is otherwise the same trick: patch window.fetch ONCE, so
//     every /api/ call anywhere in the app (agentService.js, llmConfigService.js,
//     any future service) gets the right headers without a manual wrapper at
//     each call site.
// ============================================================================

const CK_SESSION_ID = (function () {
  let id = sessionStorage.getItem('ckSessionId');
  if (!id) {
    id = 'sess-' + Math.random().toString(36).slice(2) + '-' + Date.now().toString(36);
    sessionStorage.setItem('ckSessionId', id);
  }
  return id;
})();

// The SEAT's LLM choice: what this browser applied under Settings -> LLM, stored in
// localStorage by llmConfigService.js, sent on every /api call as X-CK-LLM so the server
// dispatches THIS seat's requests to THIS seat's backend. Absent (no stored choice) means
// "use the site default". Format: auth;model;unit;match. Mirrors the server's
// SUPPORTED_AUTH_METHODS — a stored choice outside it is dropped by storedSeatLlm() below.
export const SEAT_LLM_METHODS = ['local_llm', 'claude_agent'];
export const SEAT_LLM_RETIRED_KEY = 'ckSeatLlmRetired';

export function seatLlmHeaderValue(cfg) {
  if (!cfg || !cfg.auth_method) return '';
  if (!SEAT_LLM_METHODS.includes(String(cfg.auth_method).toLowerCase())) return '';
  const f = (v) => (v == null ? '' : String(v)).replace(/[;\r\n]/g, '');
  return [f(cfg.auth_method), f(cfg.model), f(cfg.unit_model), f(cfg.match_model)].join(';');
}

// The EFFECTIVE auth_method — whatever config Apply/cold-load last resolved, seat override
// or site default. storedSeatLlm() alone is null for a seat that has never clicked Apply,
// which is exactly the common cold-load case; agentService.js's ckAgentModeActive() needs
// to know the mode is active even then, or the broker never starts its first poll.
let effectiveAuthMethod = null;

export function setEffectiveAuthMethod(method) {
  effectiveAuthMethod = method || null;
}

export function effectiveAuthMethodActive(method) {
  const seat = storedSeatLlm();
  if (seat && seat.auth_method) return seat.auth_method === method;
  return effectiveAuthMethod === method;
}

export function storedSeatLlm() {
  try {
    const raw = localStorage.getItem('draftingLLMConfig');
    const cfg = raw ? JSON.parse(raw) : null;
    if (cfg && cfg.auth_method && !SEAT_LLM_METHODS.includes(String(cfg.auth_method).toLowerCase())) {
      // Self-heal: a retired stored choice is dropped so the seat falls back to the site
      // default. The drop is remembered so the LLM tab can say so once.
      try { localStorage.setItem(SEAT_LLM_RETIRED_KEY, String(cfg.auth_method)); } catch (_) {}
      localStorage.removeItem('draftingLLMConfig');
      return null;
    }
    return cfg;
  } catch (_) {
    return null;
  }
}

// Patch window.fetch ONCE, at module load. Every other service in lib/ can just call
// plain fetch('/api/...') and get X-CK-Session / X-CK-LLM for free — no wrapper needed
// at each call site (this is what agentService.js's bare fetch(...) calls rely on).
(function patchFetch() {
  const orig = window.fetch;
  window.fetch = function (input, init) {
    try {
      const url = (typeof input === 'string') ? input : (input && input.url) || '';
      // Only attach to our own API (never to the localhost ck-agent or external hosts).
      const sameApi = url.startsWith('/api/') || url.includes(location.host + '/api/');
      if (sameApi) {
        init = init || {};
        const headers = new Headers(init.headers || (typeof input !== 'string' && input.headers) || {});
        headers.set('X-CK-Session', CK_SESSION_ID);
        const seat = seatLlmHeaderValue(storedSeatLlm());
        if (seat) headers.set('X-CK-LLM', seat);
        init.headers = headers;
      }
    } catch (_) { /* never break fetch */ }
    return orig.call(this, input, init);
  };
})();

export { CK_SESSION_ID };
