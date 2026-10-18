//@ts-nocheck

export const ZT_API = '/api/zephyr-tool';

/** fetch() against the zephyr-tool router; throws the server's `detail` (string or {error}). */
export function httpApi(base = ZT_API) {
  return async function api(path, opts = {}) {
    const r = await fetch(base + path, Object.assign({ headers: { 'Content-Type': 'application/json' } }, opts));
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(errorMessage(d.detail, r.status));
    return d;
  };
}

// A failed server-side tool (e.g. the template snapshot) answers {error, returncode, stderr}.
// `error` alone is generic ("…nothing was imported"); the real reason is the tool's own last
// line of stderr (a missing JIRA_KEY, an HTTP error from Zephyr), so it is appended.
function errorMessage(det, status) {
  if (typeof det === 'string') return det;
  if (!det || !det.error) return `HTTP ${status}`;
  const reason = lastLine(det.stderr);
  return reason ? `${det.error} — ${reason}` : det.error;
}

function lastLine(text) {
  const lines = String(text || '').split('\n').map((l) => l.trim()).filter(Boolean);
  return lines.length ? lines[lines.length - 1] : '';
}