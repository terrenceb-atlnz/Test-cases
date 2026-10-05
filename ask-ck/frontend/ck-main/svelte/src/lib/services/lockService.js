// COPIED OVER FROM current/shared/locks.js (acquire/heartbeat/release mechanics) — the
// routers/locks.py docstring is explicit that this is "a correctness/UX mechanism, not a
// security control" (the real backstop is session_store.persist_session's
// require_can_write/next_rev, which 409s any blocked write regardless of what the client
// does). So this service exists to make editing feel right — avoid an idle-steal of a
// lock you're actively using, free it promptly when you close the tab, and offer a clean
// "Take over" — not to prevent data loss, which the backend already guarantees.

import { CK_SESSION_ID } from '../api/client.js';

const LOCKS_API = '/api/locks';
const HEARTBEAT_MS = 5 * 60 * 1000;   // server idle TTL is 15 min; well inside it

function url(kind, key, verb) {
  return `${LOCKS_API}/${kind}/${encodeURIComponent(key)}/${verb}`;
}

export async function acquireLock(kind, key) {
  try {
    const res = await fetch(url(kind, key, 'acquire'), {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}',
    });
    return res.ok ? await res.json() : null;
  } catch (_) {
    return null;
  }
}

function heartbeatNow(kind, key) {
  fetch(url(kind, key, 'heartbeat'), {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}',
  }).catch(() => {});
}

// Explicit release for a deliberate in-app case switch (the page itself knows it's about
// to abandon this case for another) — NOT used for a mere tool-to-tool navigation, which
// in this SPA destroys the page component without necessarily meaning "give this case up"
// (see startLockLifecycle's own doc comment on why that distinction matters here).
export function releaseLock(kind, key) {
  fetch(url(kind, key, 'release'), {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}',
  }).catch(() => {});
}

// Starts the heartbeat timer and arms a release-on-tab-close beacon for one held lock.
// Returns a stop() that clears the timer and removes the beacon listener — it deliberately
// does NOT release the lock itself. Two different "this page went away" cases need two
// different answers: a real tab close/refresh (pagehide fires regardless of component
// lifecycle) SHOULD release, but in this SPA, navigating to a different tool page destroys
// the Svelte component that was holding this lock even though the user hasn't given up the
// case — they're still "in" it, just looking elsewhere (exactly the case current/'s single-
// page model never has to handle, since nothing there ever unmounts). Releasing on every
// destroy would let someone else steal the moment you glance at Settings; not releasing
// just lets the heartbeat lapse and the lock idle out after 15 min if you genuinely don't
// come back — a bounded, honest trade-off. A deliberate case switch calls releaseLock()
// explicitly instead (see GeneratorPage.svelte/PyTestPage.svelte's case-switch handler).
function fmtSince(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '';
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// PORTED FROM current/shared/locks.js's _renderBanner — load_case never sends a ready-made
// message, only the raw lock fields (holder_label/acquired_at/stealable/...), so the banner
// text has always had to be built client-side.
export function formatLockMessage(kind, key, lock) {
  if (!lock) return '';
  const who = lock.holder_label || 'another session';
  const since = fmtSince(lock.acquired_at);
  const tool = kind === 'pt' ? 'PyTest Creator' : 'Generator';
  return `${key} is being edited in the ${tool} by ${who}` +
    (since ? ` (since ${since})` : '') + '. You are viewing it read-only.';
}

export function startLockLifecycle(kind, key) {
  const timer = setInterval(() => heartbeatNow(kind, key), HEARTBEAT_MS);
  const onPageHide = () => {
    try {
      // navigator.sendBeacon cannot set headers, so client.js's fetch patch (which attaches
      // X-CK-Session) never runs for this request — the holder id has to ride in the body
      // instead, exactly as current/shared/locks.js does, or the server falls back to an
      // empty holder and release() silently no-ops (it only drops a lock that matches the
      // CALLING holder).
      const blob = new Blob([JSON.stringify({ holder: CK_SESSION_ID })], { type: 'application/json' });
      navigator.sendBeacon(url(kind, key, 'release'), blob);
    } catch (_) { /* best effort; the lock idles out anyway */ }
  };
  window.addEventListener('pagehide', onPageHide);
  return function stop() {
    clearInterval(timer);
    window.removeEventListener('pagehide', onPageHide);
  };
}
