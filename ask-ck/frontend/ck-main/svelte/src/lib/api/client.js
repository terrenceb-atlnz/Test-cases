/** Author: Trent Morgan
 *  Contact: trent.morgan@alliedtelesis.co.nz
 *  Date Last Modified: 8/10/2024
 *
 *  Description: Client-side API utilities for Svelte frontend. This file is loaded
 *               once at app startup, and patches window.fetch to inject per-tab session
 *               id + X-CK-Session / X-CK-LLM headers on every /api call.
 */

 // @ts-nocheck

 // List of auth methods that are considered "seat LLM" methods. These are used to determine
 // whether to include the X-CK-LLM header in API requests.
 // - Ported from current/shared/session.js
export const SEAT_LLM_METHODS = ['local_llm', 'claude_agent'];

// Key used to store the last retired seat LLM method in localStorage. This is used to
// track when a seat LLM method is no longer supported and to prevent it from being used.
 // - Ported from current/shared/session.js
export const SEAT_LLM_RETIRED_KEY = 'ckSeatLlmRetired';

// Variable to hold the effective auth method for the current session. This is used to
// determine whether the current session is using a seat LLM method.
let effectiveAuthMethod = null;

// Generate a unique session ID for the current browser session. This ID is stored in
// sessionStorage and is used to identify the session in API requests.
 // - Ported from current/shared/session.js
const CK_SESSION_ID = (function () {
  let id = sessionStorage.getItem('ckSessionId');
  if (!id) {
    id = 'sess-' + Math.random().toString(36).slice(2) + '-' + Date.now().toString(36);
    sessionStorage.setItem('ckSessionId', id);
  }
  return id;
})();

// Function to generate the value for the X-CK-LLM header based on the provided configuration.
 // - Ported from current/shared/session.js
export function seatLlmHeaderValue(cfg) {
  if (!cfg || !cfg.auth_method) return '';
  if (!SEAT_LLM_METHODS.includes(String(cfg.auth_method).toLowerCase())) return '';
  const f = (v) => (v == null ? '' : String(v)).replace(/[;\r\n]/g, '');
  return [f(cfg.auth_method), f(cfg.model), f(cfg.unit_model), f(cfg.match_model)].join(';');
}

// Function to set the effective auth method for the current session. This is used to
// determine whether the current session is using a seat LLM method.
export function setEffectiveAuthMethod(method) {
  effectiveAuthMethod = method || null;
}

// Function to check if the effective auth method for the current session matches the provided method.
export function effectiveAuthMethodActive(method) {
  const seat = storedSeatLlm();
  if (seat && seat.auth_method) return seat.auth_method === method;
  return effectiveAuthMethod === method;
}

// Function to retrieve the stored seat LLM configuration from localStorage. If the stored configuration 
// is invalid or uses a retired auth method, it is removed from localStorage and null is returned.
 // - Ported from current/shared/session.js
export function storedSeatLlm() {
  try {
    const raw = localStorage.getItem('draftingLLMConfig');
    const cfg = raw ? JSON.parse(raw) : null;
    if (cfg && cfg.auth_method && !SEAT_LLM_METHODS.includes(String(cfg.auth_method).toLowerCase())) {

      try { localStorage.setItem(SEAT_LLM_RETIRED_KEY, String(cfg.auth_method)); } catch (_) {}
      localStorage.removeItem('draftingLLMConfig');
      return null;
    }
    return cfg;
  } catch (_) {
    return null;
  }
}

// Immediately patch the global fetch function to automatically include session and LLM headers for API requests.
// - Ported from current/shared/session.js
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
