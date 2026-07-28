// ============================================================================
// Per-case locking UX (PLAN-auth-and-case-locking.md Phase 1).
//
// The server acquires/refreshes a lock inside load_case and returns { lock, read_only }.
// This module reacts to that: when WE hold the lock it starts a heartbeat and arms a
// release-on-close; when someone ELSE holds it, it shows a read-only banner and disables
// the tool's step inputs (D6a), offering "Take over" once the lock goes idle (D5).
//
// The holder identity is the per-tab X-CK-Session id (session.js). It is a correlation
// id, not a credential — release-on-unload uses navigator.sendBeacon, which CANNOT set
// request headers, so the holder id is sent in the beacon's JSON body instead.
// ============================================================================
import { CK_SESSION_ID } from './session.js';
import { escapeHtml } from './dom-helpers.js';

// Heartbeat well inside the server's 15-min idle TTL so a lock never lapses while the
// tab is open. Background tabs are throttled by the browser but not past ~1/min, so 5
// min stays comfortably under the TTL.
const HEARTBEAT_MS = 5 * 60 * 1000;

// Which step panels become read-only when the case is locked by someone else. The case
// picker (step-0 / panel-pt-cases) and the global Testboxes panel stay usable so you can
// still switch cases or manage testboxes while viewing someone else's work.
const _tools = {
  wizard: { key: null, heldByMe: false, timer: null, reload: null,
            panels: ['step-1', 'step-2', 'step-3', 'step-4', 'step-5'] },
  pt:     { key: null, heldByMe: false, timer: null, reload: null,
            panels: ['panel-pt-seq', 'panel-pt-search', 'panel-pt-frag',
                     'panel-pt-gen', 'panel-pt-run', 'panel-pt-validate'] },
};
let _releaseArmed = false;

function _url(kind, key, verb) {
  return `/api/locks/${kind}/${encodeURIComponent(key)}/${verb}`;
}

// A tool registers how to re-run its own load_case, so "Take over" can re-enter the
// normal editable load without this module importing the tool (which would cycle).
export function registerReloader(kind, fn) {
  if (_tools[kind]) _tools[kind].reload = fn;
}

// Called by each tool right after load_case returns.
export function onCaseLoaded(kind, key, lock, readOnly) {
  const t = _tools[kind];
  if (!t) return;
  // Switching cases: drop the lock we held on the previous case so others aren't kept
  // waiting for it to idle out.
  if (t.key && t.key !== key && t.heldByMe) releaseLock(kind, t.key);
  _stopHeartbeat(kind);
  t.key = key;
  t.heldByMe = !readOnly && !!(lock && lock.by_me);

  if (t.heldByMe) {
    _hideBanner();
    _setReadOnly(t.panels, false);
    _startHeartbeat(kind, key);
    _armRelease();
  } else {
    _renderBanner(kind, key, lock || {});
    _setReadOnly(t.panels, true);
  }
}

export async function acquireLock(kind, key) {
  try {
    const res = await fetch(_url(kind, key, 'acquire'), {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
    return res.ok ? await res.json() : null;
  } catch (_) { return null; }
}

export function heartbeatNow(kind, key) {
  // Fire-and-forget; used by the timer and by a long testbox run's status poll so the
  // lock never lapses mid-run (plan §6).
  fetch(_url(kind, key, 'heartbeat'), {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' }).catch(() => {});
}

export function releaseLock(kind, key) {
  fetch(_url(kind, key, 'release'), {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' }).catch(() => {});
}

function _startHeartbeat(kind, key) {
  const t = _tools[kind];
  t.timer = setInterval(() => heartbeatNow(kind, key), HEARTBEAT_MS);
}

function _stopHeartbeat(kind) {
  const t = _tools[kind];
  if (t.timer) { clearInterval(t.timer); t.timer = null; }
}

function _armRelease() {
  if (_releaseArmed) return;
  _releaseArmed = true;
  // pagehide fires on navigation-away and tab close (more reliable than 'unload'), and
  // ONLY then — a tab switch / minimise (visibilitychange) must NOT drop a live lock.
  window.addEventListener('pagehide', () => {
    for (const kind of Object.keys(_tools)) {
      const t = _tools[kind];
      if (t.key && t.heldByMe) _beaconRelease(kind, t.key);
    }
  });
}

function _beaconRelease(kind, key) {
  try {
    const blob = new Blob([JSON.stringify({ holder: CK_SESSION_ID })], { type: 'application/json' });
    navigator.sendBeacon(_url(kind, key, 'release'), blob);
  } catch (_) { /* best effort; the lock idles out anyway */ }
}

// --- Read-only enforcement (D6a) --------------------------------------------
// Disable every form control in the tool's step panels, remembering WHICH controls we
// disabled so re-enabling never clobbers a control disabled for another reason.
function _setReadOnly(panelIds, on) {
  panelIds.forEach(id => {
    const p = document.getElementById(id);
    if (!p) return;
    p.classList.toggle('ck-readonly', on);
    p.querySelectorAll('button, input, textarea, select').forEach(ctrl => {
      if (ctrl.hasAttribute('data-ck-lock-keep')) return;
      if (on) {
        if (!ctrl.disabled) { ctrl.setAttribute('data-ck-lock-disabled', '1'); ctrl.disabled = true; }
      } else if (ctrl.getAttribute('data-ck-lock-disabled') === '1') {
        ctrl.disabled = false;
        ctrl.removeAttribute('data-ck-lock-disabled');
      }
    });
  });
}

// --- Banner ------------------------------------------------------------------
function _bannerEl() {
  let el = document.getElementById('ck-lock-banner');
  if (!el) {
    el = document.createElement('div');
    el.id = 'ck-lock-banner';
    el.className = 'status-banner hidden';
    const anchor = document.getElementById('load-status');
    if (anchor && anchor.parentNode) anchor.parentNode.insertBefore(el, anchor);
    else document.body.insertBefore(el, document.body.firstChild);
  }
  return el;
}

function _fmtSince(iso) {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return '';
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch (_) { return ''; }
}

export function _renderBanner(kind, key, lock) {
  const el = _bannerEl();
  el.className = 'status-banner is-warning';
  const who = lock.holder_label || 'another session';
  const since = _fmtSince(lock.acquired_at);
  const tool = kind === 'pt' ? 'PyTest Creator' : 'Generator';
  let html = '<span class="status-title">🔒 ' +
    escapeHtml(key) + ' is being edited in the ' + tool + ' by ' + escapeHtml(who) +
    (since ? ' (since ' + escapeHtml(since) + ')' : '') +
    '. You are viewing it read-only.</span>';
  if (lock.stealable) {
    html += ' <button type="button" class="btn btn-secondary btn-compact" ' +
            'data-ck-lock-takeover="1" data-ck-lock-keep="1">Take over</button>';
  }
  el.innerHTML = html;
  const btn = el.querySelector('[data-ck-lock-takeover]');
  if (btn) btn.addEventListener('click', () => _takeOver(kind, key));
}

function _hideBanner() {
  const el = document.getElementById('ck-lock-banner');
  if (el) { el.className = 'status-banner hidden'; el.innerHTML = ''; }
}

async function _takeOver(kind, key) {
  const state = await acquireLock(kind, key);
  if (state && state.by_me) {
    const t = _tools[kind];
    if (t && typeof t.reload === 'function') t.reload();   // re-enter the editable load
  } else {
    // Not stealable yet (someone re-acquired / heartbeated). Refresh the banner.
    _renderBanner(kind, key, state || {});
  }
}
