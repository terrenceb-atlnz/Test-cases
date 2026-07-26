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
