// The per-unit controls must RENDER usable, not merely have a rule written for them.
//
// THE DEFECT THIS CATCHES (2026-09-02)
// ------------------------------------
// The prompt frame shipped 120px tall at 11px font, showing about five lines of an
// 87,973-character prompt. Terrence: "The tinyness of the prompt makes it unreadable...
// this is ridiculous."
//
// Nothing was wrong with the rule. `.pt-unit-prompt { height: 380px }` was correct and
// present — and lost, because `.editor-textarea { height:120px; font-size:11px }` is
// declared 550 lines LATER at identical specificity (0,1,0), so source order decided it.
// Same for the output pane against `.session-pre { max-height:160px }`.
//
// styles.css already documents this exact trap for the pill row ("a bare
// button.pt-pill-ok only TIES (0,1,1) and the later :not(.btn) rule then wins the tie"),
// and it was repeated anyway. A source-level assertion cannot catch it: the rule IS
// there. So this asserts the COMPUTED value, with the real stylesheet loaded, which is
// the only form of the check that is immune to source order by construction.
import { describe, it, expect, beforeEach } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const CSS = readFileSync(
  resolve(HERE, '../ask-ck/CK-main/CK_server/static/styles.css'), 'utf8');

beforeEach(() => {
  document.head.innerHTML = '';
  const st = document.createElement('style');
  st.textContent = CSS;
  document.head.appendChild(st);
  // Exactly the classes ptRenderUnitPage emits.
  document.body.innerHTML =
    '<textarea id="p" class="form-input editor-textarea pt-unit-prompt"></textarea>'
    + '<pre id="o" class="session-pre pt-unit-out"></pre>';
});

const cs = (id) => getComputedStyle(document.getElementById(id));

describe('the prompt frame is readable', () => {
  it('is not left at the base editor height', () => {
    // The regression: .editor-textarea's 120px winning the tie.
    const h = cs('p').height;
    expect(h).not.toBe('120px');
    expect(h).toMatch(/vh$|^\d{3,}px$/);      // viewport-relative, or at least 100px+
  });

  it('is not left at the base editor font size', () => {
    expect(cs('p').fontSize).not.toBe('11px');
    expect(parseInt(cs('p').fontSize, 10)).toBeGreaterThanOrEqual(12);
  });

  it('can be dragged taller, because no default suits 3k and 88k alike', () => {
    expect(cs('p').resize).toBe('vertical');
  });
});

describe('the returned-code frame is readable', () => {
  it('is not left at the base session-pre cap', () => {
    expect(cs('o').maxHeight).not.toBe('160px');
  });

  it('is not left at the base session-pre font size', () => {
    expect(parseInt(cs('o').fontSize, 10)).toBeGreaterThanOrEqual(12);
  });
});

describe('why these win', () => {
  it('both rules carry an element selector, so source order cannot decide them', () => {
    // The fix, stated as the property rather than the outcome: at 0,1,1 they beat the
    // later 0,1,0 base rules wherever those happen to sit in the file.
    expect(CSS).toMatch(/textarea\.pt-unit-prompt\s*\{/);
    expect(CSS).toMatch(/pre\.pt-unit-out\s*\{/);
  });

  it('the base rules really are declared later, which is what made this possible', () => {
    // If this ever stops being true the trap is gone and these tests are belt-and-braces
    // — worth knowing rather than silently over-specifying forever.
    expect(CSS.indexOf('textarea.pt-unit-prompt')).toBeLessThan(CSS.indexOf('.editor-textarea {'));
    expect(CSS.indexOf('pre.pt-unit-out')).toBeLessThan(CSS.indexOf('.session-pre {'));
  });
});
