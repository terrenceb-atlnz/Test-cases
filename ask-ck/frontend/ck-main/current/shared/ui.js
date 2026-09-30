// The ATUI restyle's one switch for the shared JS (ask-ck/plans/PLAN-atui-restyle.md S11).
//
// restyle/index.html puts data-ui="atui" on <html>; Classic (current/index.html) never does.
// On Classic every helper here returns exactly what its call site produced before it existed,
// so Classic's output stays byte-identical — the glyph assertions in tests/js pin that. On
// ATUI they return the approved wording (§9) and Carbon icons (§10) instead.

import { escapeHtml } from './dom-helpers.js';

export function isAtui() {
  return document.documentElement.getAttribute('data-ui') === 'atui';
}

/** Classic's text, or the approved ATUI wording. */
export function copy(classic, atui) {
  return isAtui() ? atui : classic;
}

// Glyph -> the Carbon icon it becomes (§10). The class names are restyle/styles.css's
// .rs-icon-* rules. A site whose glyph means something else passes its own name to icon().
const ICONS = {
  '✓': 'checkmark', '✗': 'close', '⚠': 'warning-alt-filled', '⏸': 'pause-filled',
  '⏹': 'stop-filled-alt', '↻': 'renew', '↓': 'arrow-down', '↑': 'arrow-up',
  '‹': 'chevron-left', '›': 'chevron-right', '⏳': 'spinner', '⤺': 'tools', '⠿': 'draggable',
  '✕': 'close', '🔒': 'locked',
};
const GLYPHS = new RegExp('[' + Object.keys(ICONS).join('') + ']', 'gu');

/**
 * A glyph used as an icon: the glyph itself on Classic, a Carbon icon on ATUI.
 * `label` is for an icon that stands alone (nothing else says what it means).
 * ⏳ is busy text ("pinging…") nearly everywhere, so it defaults to the app's own spinner (I10);
 * the one place it means a limit passes 'time'.
 */
export function icon(glyph, name, label) {
  if (!isAtui()) return glyph;
  const a11y = label ? ` role="img" aria-label="${escapeHtml(label)}"` : ' aria-hidden="true"';
  const n = name || ICONS[glyph];
  if (n === 'spinner') return `<span class="ck-spinner"${a11y}></span>`;
  return `<span class="rs-icon rs-icon-${n}"${a11y}></span>`;
}

/**
 * escapeHtml(text) on Classic; on ATUI the same, with each known glyph drawn as its icon.
 * `names` overrides the icon per glyph, e.g. { '✓': 'checkmark-filled' } in a badge (I1).
 */
export function glyphHtml(text, names = {}) {
  const html = escapeHtml(text);
  return isAtui() ? html.replace(GLYPHS, (g) => icon(g, names[g])) : html;
}

/** el.textContent = text on Classic; on ATUI the same text with its glyphs drawn as icons. */
export function setGlyphText(el, text, names) {
  if (isAtui()) el.innerHTML = glyphHtml(text, names);
  else el.textContent = text;
}

// Review severity (§10 I11): ATUI's HealthDot shapes, so severity is not colour-only.
const SEV = { high: ['✗', 'high'], medium: ['△', 'medium'], low: ['·', 'low'] };

/** A review finding's severity mark: Classic's ✗ △ ·, or a diamond / triangle / circle. */
export function sevMark(severity) {
  const [glyph, name] = SEV[severity] || SEV.low;
  if (!isAtui()) return glyph;
  return `<span class="rs-sev rs-sev-${name}" role="img" aria-label="${name} severity"></span>`;
}
