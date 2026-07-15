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
