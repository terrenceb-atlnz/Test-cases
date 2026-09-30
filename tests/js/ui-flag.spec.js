// Specs for shared/ui.js, the ATUI restyle's switch for the shared JS (PLAN-atui-restyle.md S11).
// The contract that matters most is the Classic half: with no data-ui on <html> every helper
// returns exactly what its call site produced before, so Classic's output is byte-identical.
import { describe, it, expect, afterEach } from 'vitest';
import { isAtui, copy, icon, glyphHtml, setGlyphText, sevMark } from '../../ask-ck/frontend/ck-main/current/shared/ui.js';
import { escapeHtml } from '../../ask-ck/frontend/ck-main/current/shared/dom-helpers.js';

const atui = () => document.documentElement.setAttribute('data-ui', 'atui');
afterEach(() => { document.documentElement.removeAttribute('data-ui'); });

const SAMPLE = '✓ up — <model> & "x" ⚠ ⏸ ✗ ⏹ ↻ ↓ ↑ ‹ › ⏳ ⤺ ⠿ ✕ 🔒 → △ ·';

describe('Classic (no data-ui): byte-identical to the old call sites', () => {
  it('is not ATUI', () => { expect(isAtui()).toBe(false); });
  it('copy returns the Classic text', () => { expect(copy('OK, refresh', 'Refresh Page')).toBe('OK, refresh'); });
  it('icon returns the glyph itself', () => {
    for (const g of ['✓', '✗', '⚠', '⏸', '🔒']) expect(icon(g)).toBe(g);
    expect(icon('✓', 'checkmark-filled', 'covered')).toBe('✓');
  });
  it('glyphHtml is exactly escapeHtml', () => {
    expect(glyphHtml(SAMPLE)).toBe(escapeHtml(SAMPLE));
    expect(glyphHtml('')).toBe(escapeHtml(''));
  });
  it('setGlyphText is exactly textContent', () => {
    const el = document.createElement('span');
    setGlyphText(el, SAMPLE);
    expect(el.textContent).toBe(SAMPLE);
    expect(el.children.length).toBe(0);
  });
  it('sevMark returns the old _PT_SEV glyphs, with · for an unknown severity', () => {
    expect([sevMark('high'), sevMark('medium'), sevMark('low'), sevMark('bogus'), sevMark(undefined)])
      .toEqual(['✗', '△', '·', '·', '·']);
  });
});

describe('ATUI (data-ui="atui")', () => {
  it('is ATUI and takes the ATUI wording', () => {
    atui();
    expect(isAtui()).toBe(true);
    expect(copy('OK, refresh', 'Refresh Page')).toBe('Refresh Page');
  });
  it('icon is a decorative Carbon span, or a labelled one when it stands alone', () => {
    atui();
    expect(icon('⏸')).toBe('<span class="rs-icon rs-icon-pause-filled" aria-hidden="true"></span>');
    expect(icon('✓', 'checkmark-filled', 'covered'))
      .toBe('<span class="rs-icon rs-icon-checkmark-filled" role="img" aria-label="covered"></span>');
  });
  it('glyphHtml escapes the text BEFORE drawing icons, so server text cannot inject markup', () => {
    atui();
    const el = document.createElement('div');
    el.innerHTML = glyphHtml('✗ down — <img src=x onerror=alert(1)>');
    expect(el.querySelector('img')).toBeNull();
    expect(el.querySelector('.rs-icon-close')).not.toBeNull();
    expect(el.textContent).toBe(' down — <img src=x onerror=alert(1)>');
  });
  it('every mapped glyph becomes its icon; → △ · are left to their own call sites', () => {
    atui();
    const el = document.createElement('div');
    el.innerHTML = glyphHtml(SAMPLE);
    expect(el.querySelectorAll('.rs-icon').length).toBe(14);
    expect(el.querySelectorAll('.ck-spinner').length).toBe(1);        // ⏳ = busy
    expect(el.textContent).toMatch(/→ △ ·$/);
    expect(el.textContent).not.toMatch(/[✓✗⚠⏸⏹↻↓↑‹›⏳⤺⠿✕🔒]/u);
  });
  it('⏳ is the app spinner unless the site says it means a limit', () => {
    atui();
    expect(icon('⏳')).toBe('<span class="ck-spinner" aria-hidden="true"></span>');
    expect(icon('⏳', 'time')).toBe('<span class="rs-icon rs-icon-time" aria-hidden="true"></span>');
  });
  it('setGlyphText draws the icons', () => {
    atui();
    const el = document.createElement('span');
    setGlyphText(el, '⚠ no key stored');
    expect(el.querySelector('.rs-icon-warning-alt-filled')).not.toBeNull();
    expect(el.textContent).toBe(' no key stored');
  });
  it('a site can override the icon a glyph becomes (badges take the filled checkmark)', () => {
    atui();
    const el = document.createElement('span');
    setGlyphText(el, '✓ Confirmed', { '✓': 'checkmark-filled' });
    expect(el.innerHTML).toBe('<span class="rs-icon rs-icon-checkmark-filled" aria-hidden="true"></span> Confirmed');
  });
  it('sevMark is a labelled HealthDot shape', () => {
    atui();
    expect(sevMark('high')).toBe('<span class="rs-sev rs-sev-high" role="img" aria-label="high severity"></span>');
    expect(sevMark('bogus')).toContain('rs-sev-low');
  });
});
