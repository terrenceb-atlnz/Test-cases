// ============================================================================
// Per-tab session id + X-CK-Session header injection.
// Each browser tab gets a unique id so the shared server can route claude_agent
// LLM jobs back to THIS user's browser (and thus their own local ck-agent).
// We patch window.fetch once so every same-origin /api call carries the header
// without touching each call site.
// ============================================================================
const CK_SESSION_ID = (function () {
  let id = sessionStorage.getItem('ckSessionId');
  if (!id) {
    id = 'sess-' + Math.random().toString(36).slice(2) + '-' + Date.now().toString(36);
    sessionStorage.setItem('ckSessionId', id);
  }
  return id;
})();
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
        init.headers = headers;
      }
    } catch (_) { /* never break fetch */ }
    return orig.call(this, input, init);
  };
})();

export { CK_SESSION_ID };
