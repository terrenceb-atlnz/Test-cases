// Small pure DOM/string helpers shared across tools.

export function truncateText(str, maxLen) {
  if (str == null) return '';
  const s = String(str);
  if (s.length <= maxLen) return s;
  return s.slice(0, Math.max(0, maxLen - 1)).trimEnd() + '…';
}

export function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/[&<>"']/g, function(m) {
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m];
  });
}

/** data-args attribute value for the click dispatcher: JSON array, HTML-escaped. */
export function dataArgs(...args) {
  return escapeHtml(JSON.stringify(args));
}

/**
 * Render a persistent, readable status banner into the element with id `elId`.
 * Replaces console-only / alert-only surfacing so synthesis/export/run failures are
 * visible in-page (backlog: Error/loading UX). Content is escaped; `items` render as a list.
 *
 * @param {string} elId  target element id (a <div class="status-banner">)
 * @param {'success'|'warning'|'error'|'busy'|'clear'} kind
 * @param {string} title one-line summary
 * @param {string[]} [items] optional detail lines (e.g. validation issues)
 */
export function showStatus(elId, kind, title, items) {
  const el = document.getElementById(elId);
  if (!el) return;
  if (kind === 'clear') {
    el.className = 'status-banner hidden';
    el.innerHTML = '';
    return;
  }
  el.className = 'status-banner is-' + kind;
  let html = '<span class="status-title">' + escapeHtml(title || '') + '</span>';
  if (Array.isArray(items) && items.length) {
    html += '<ul>' + items.map(function(i){ return '<li>' + escapeHtml(String(i)) + '</li>'; }).join('') + '</ul>';
  }
  el.innerHTML = html;
}

/**
 * Put an LLM/async button into (or out of) its in-flight "busy" state.
 *
 * Busy (on=true): shows a pressed style, replaces the label with an animated
 * spinner + a working message, and disables the button so a second click while
 * the request is in flight is a no-op (prevents stacked LLM calls). The original
 * label is stashed on the element and restored when on=false.
 *
 * Idempotent: calling with on=true twice keeps the FIRST stashed label, so a
 * stray double-invoke never captures the spinner markup as the "original".
 * Returns true when it transitioned into busy from idle, false if it was already
 * busy — callers can use this to bail out of a double-triggered handler.
 *
 * @param {HTMLElement|null} btn
 * @param {boolean} on
 * @param {{label?: string}} [opts]  label = working message (default 'Working…')
 * @returns {boolean} true if this call started a new busy state
 */
export function setButtonBusy(btn, on, opts) {
  if (!btn) return false;
  if (on) {
    if (btn.dataset.busy === '1') return false;   // already in flight — guard
    btn.dataset.busy = '1';
    btn.dataset.busyLabel = btn.innerHTML;        // stash original (glyphs + text)
    const msg = (opts && opts.label) || 'Working…';
    btn.classList.add('is-busy');
    btn.classList.remove('is-done', 'is-error');
    btn.setAttribute('aria-busy', 'true');
    btn.disabled = true;
    btn.innerHTML = '<span class="ck-spinner" aria-hidden="true"></span>'
      + '<span class="ck-busy-label">' + escapeHtml(msg) + '</span>';
    return true;
  }
  if (btn.dataset.busy !== '1') return false;      // not busy — nothing to undo
  delete btn.dataset.busy;
  if (btn.dataset.busyLabel != null) {
    btn.innerHTML = btn.dataset.busyLabel;
    delete btn.dataset.busyLabel;
  }
  btn.classList.remove('is-busy');
  btn.removeAttribute('aria-busy');
  btn.disabled = false;
  return false;
}

/**
 * Briefly flash a completed async button green or red so success/failure is visible
 * on the button itself, not only in a status banner. Non-blocking: it auto-clears.
 * Safe to call right after setButtonBusy(off).
 *
 * `opts.label` swaps the button's text for the duration of the flash. Colour alone
 * is weak feedback for a FAST request — the spinner comes and goes in under a tenth
 * of a second and the colour can be gone before the eye gets back to the button, so
 * a reviewer who was watching still reports "nothing happened" (2026-09-02). A word
 * survives that, and holds a little longer because reading takes longer than seeing.
 * Note there is no ✓ glyph unless a caller asks for one in its label — this
 * docstring used to claim otherwise.
 *
 * @param {HTMLElement|null} btn
 * @param {boolean} ok  true → success flash, false → error flash
 * @param {{label?: string, ms?: number}} [opts]
 */
export function flashButtonDone(btn, ok, opts) {
  if (!btn) return;
  const cls = ok ? 'is-done' : 'is-error';
  const label = (opts && opts.label) || '';
  const ms = (opts && opts.ms) || (label ? 1600 : 1200);
  btn.classList.remove('is-done', 'is-error');
  // reflow so re-adding the same class restarts the CSS transition
  void btn.offsetWidth;
  btn.classList.add(cls);
  // Generation token: a second flash landing mid-flash must own the restore, or the
  // first one's timer puts the stale label back and clears the new colour early.
  const gen = String(Number(btn.dataset.flashGen || 0) + 1);
  btn.dataset.flashGen = gen;
  if (label) {
    if (btn.dataset.flashLabel == null) btn.dataset.flashLabel = btn.innerHTML;
    btn.innerHTML = escapeHtml(label);
  }
  window.setTimeout(function () {
    if (btn.dataset.flashGen !== gen) return;      // a later flash owns the button now
    delete btn.dataset.flashGen;
    btn.classList.remove(cls);
    if (btn.dataset.flashLabel != null) {
      btn.innerHTML = btn.dataset.flashLabel;
      delete btn.dataset.flashLabel;
    }
  }, ms);
}
