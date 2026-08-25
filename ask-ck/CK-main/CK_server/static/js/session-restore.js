// Refresh-safe UI state, app-wide.
//
// The server keeps a session per case, but the FRONTEND forgot everything on a
// reload: F5 returned you to panel-main with the sidebar re-collapsed and the
// case dropdowns cleared, even though the case was still loaded server-side and
// nothing said so. That got worse when the stale-frontend guard shipped
// (version.js), because its only remedy is "reload" — so the fix for running
// superseded code was to lose your place in the flow.
//
// Storage is sessionStorage, NOT localStorage, and the distinction is
// deliberate: this must survive a refresh and nothing more. A tab reopened
// later would otherwise auto-load a case and re-acquire its per-case lock
// (locks.js), which on a shared server blocks a colleague from a case nobody is
// actually looking at. sessionStorage is scoped to the one tab, so each tab
// keeps its own place and a closed tab leaves no claim behind.
//
// Every access is wrapped: sessionStorage throws outright when site data is
// blocked, and a restore is a convenience — it must never break boot.

const KEY = 'ck.ui.state.v1';

export function readSnapshot() {
  try {
    const raw = sessionStorage.getItem(KEY);
    if (!raw) return {};
    const d = JSON.parse(raw);
    return d && typeof d === 'object' ? d : {};
  } catch (_) { return {}; }
}

function write(patch) {
  try {
    sessionStorage.setItem(KEY, JSON.stringify({ ...readSnapshot(), ...patch }));
  } catch (_) { /* site data blocked — restore is best-effort, boot must not care */ }
}

/** The panel the user is looking at. Called from nav.goToPanel. */
export function rememberPanel(panelId) {
  if (panelId) write({ panel: panelId });
}

/**
 * A tool's case selection. `kind` is 'gen' or 'pt'.
 * `loaded` distinguishes PyTest Creator's two states: the Generator loads on
 * select, but PyTest Creator needs an explicit "Load Case & Continue" — and
 * only a case that was actually loaded should be re-loaded on restore.
 */
export function rememberCase(kind, key, loaded) {
  if (kind === 'gen') write({ genKey: key || null });
  else if (kind === 'pt') {
    const patch = { ptKey: key || null };
    if (loaded !== undefined) patch.ptLoaded = !!loaded && !!key;
    if (!key) patch.ptLoaded = false;
    write(patch);
  }
}

export function clearSnapshot() {
  try { sessionStorage.removeItem(KEY); } catch (_) { /* nothing to do */ }
}

/**
 * Wait for a <select> to be populated. initCases() fetches the case lists and
 * is not awaited at boot, so a restore fired on a fixed timeout races it on a
 * cold load. Polls instead of guessing, and gives up rather than hanging.
 */
export function waitForOptions(selectId, timeoutMs = 6000, stepMs = 100) {
  return new Promise((resolve) => {
    const t0 = Date.now();
    const tick = () => {
      const el = document.getElementById(selectId);
      if (el && Array.from(el.options).some(o => o.value)) return resolve(el);
      if (Date.now() - t0 >= timeoutMs) return resolve(null);
      setTimeout(tick, stepMs);
    };
    tick();
  });
}

/** True when `key` is a real option of the given select. */
export function hasOption(selectId, key) {
  const el = document.getElementById(selectId);
  if (!el || !key) return false;
  return Array.from(el.options).some(o => o.value === key);
}
