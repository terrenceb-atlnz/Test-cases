// Click feedback on every button (2026-09-02).
//
// THE COMPLAINT
// -------------
// "Can we add an animation on every button to show its being clicked? Im unsure if
// 'save selections' is actually working or not, i have no visual feedback or any
// feedback at all."
//
// Two separate gaps sat behind that one sentence:
//
//   1. Nothing in the app acknowledged a click. `.btn` had no `:active` rule at all
//      (only .btn-danger and .btn-export did), so a press was invisible unless the
//      handler happened to write status text — and a handler that blocks the main
//      thread writes it too late to read as a response to the click.
//
//   2. Save Selections never passed its button to ptApi, so the spinner + ✓/✗ flash
//      every LLM button already had did not apply to it. Its only report was a line
//      of text which, on the fragments panel, rendered beside Gather at the top of a
//      31-step list — a screen-height above the button that was pressed.
//
// The listener half is exercised for real (jsdom, actions.js imported); the CSS and
// the handler wiring are pinned at source level. Comments are stripped before every
// source assertion — this file's prose names identifiers it then forbids.
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const read = (rel) => readFileSync(resolve(HERE, rel), 'utf8');
const strip = (s) => s.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');

const CSS = strip(read('../ask-ck/CK-main/CK_server/static/styles.css'));
const PYTEST = strip(read('../ask-ck/CK-main/CK_server/static/js/pytest.js'));
const HTML = read('../ask-ck/CK-main/CK_server/static/index.html')
  .replace(/<!--[\s\S]*?-->/g, '');

// actions.js registers its document listeners at import time. It imports nothing,
// so a bare import is enough to install them.
await import('../ask-ck/CK-main/CK_server/static/js/actions.js');

describe('press pulse (live, via the delegated listener)', () => {
  beforeEach(() => { vi.useFakeTimers(); document.body.innerHTML = ''; });
  afterEach(() => { vi.useRealTimers(); });

  const click = (el) => el.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));

  it('marks a plain <button> with no data-action at all', () => {
    // The legacy inline-onclick buttons are exactly the ones a data-action-only
    // implementation would leave feeling dead.
    document.body.innerHTML = '<button id="b">go</button>';
    const b = document.getElementById('b');
    click(b);
    expect(b.classList.contains('ck-pressed')).toBe(true);
  });

  it('marks the BUTTON when the click lands on something inside it', () => {
    document.body.innerHTML = '<button id="b"><span class="ck-spinner"></span><span id="lbl">go</span></button>';
    click(document.getElementById('lbl'));
    expect(document.getElementById('b').classList.contains('ck-pressed')).toBe(true);
  });

  it('marks a .btn that is not a <button> element', () => {
    document.body.innerHTML = '<a id="a" class="btn" href="#">export</a>';
    click(document.getElementById('a'));
    expect(document.getElementById('a').classList.contains('ck-pressed')).toBe(true);
  });

  it('fires even when the handler stops propagation', () => {
    // Capture phase, or the pulse is at the mercy of every handler in the app.
    document.body.innerHTML = '<div id="wrap"><button id="b">go</button></div>';
    document.getElementById('wrap')
      .addEventListener('click', (e) => e.stopPropagation());
    const b = document.getElementById('b');
    click(b);
    expect(b.classList.contains('ck-pressed')).toBe(true);
  });

  it('leaves a disabled button alone', () => {
    document.body.innerHTML = '<button id="b" disabled>go</button>';
    const b = document.getElementById('b');
    click(b);
    expect(b.classList.contains('ck-pressed')).toBe(false);
  });

  it('clears itself on a timer, so the pressed style is never stuck on', () => {
    // On a TIMER and not on animationend: prefers-reduced-motion sets
    // `animation: none`, and then animationend never fires.
    document.body.innerHTML = '<button id="b">go</button>';
    const b = document.getElementById('b');
    click(b);
    expect(b.classList.contains('ck-pressed')).toBe(true);
    vi.advanceTimersByTime(400);
    expect(b.classList.contains('ck-pressed')).toBe(false);
  });

  it('restarts on a re-click instead of doing nothing the second time', () => {
    document.body.innerHTML = '<button id="b">go</button>';
    const b = document.getElementById('b');
    click(b);
    vi.advanceTimersByTime(100);      // still mid-pulse
    click(b);
    expect(b.classList.contains('ck-pressed')).toBe(true);
    // The first click's timer must not strip the second click's class early.
    vi.advanceTimersByTime(130);
    expect(b.classList.contains('ck-pressed')).toBe(true);
  });

  it('ignores a click with no button anywhere above it', () => {
    document.body.innerHTML = '<div id="d">text</div>';
    expect(() => click(document.getElementById('d'))).not.toThrow();
    expect(document.querySelectorAll('.ck-pressed').length).toBe(0);
  });
});

describe('press feedback CSS', () => {
  it('gives every button a held-press state', () => {
    expect(CSS).toMatch(/button:active:not\(:disabled\)/);
    expect(CSS).toMatch(/\.btn:active:not\(:disabled\)/);
  });

  it('defines the pulse the listener triggers', () => {
    expect(CSS).toContain('@keyframes ck-press');
    expect(CSS).toMatch(/\.ck-pressed\s*\{[^}]*animation:\s*ck-press/s);
  });

  it('animates transform, or the transition would not be seen', () => {
    // .btn transitions an explicit property list; transform has to be on it.
    const btn = CSS.slice(CSS.indexOf('.btn {'), CSS.indexOf('.btn:focus-visible'));
    expect(btn).toMatch(/transition:[^;]*transform/s);
  });

  it('keeps a non-motion pressed state for prefers-reduced-motion', () => {
    const i = CSS.indexOf('ck-press 180ms');
    const rm = CSS.slice(i);
    const block = rm.slice(rm.indexOf('@media (prefers-reduced-motion: reduce)'));
    expect(block).toContain('ck-pressed');
    expect(block).toMatch(/animation:\s*none/);
    expect(block).toMatch(/filter:\s*brightness/);
  });

  it('does not scale the sidebar nav rows', () => {
    // div[role="button"] nav items are full-width; scaling one reads as a glitch.
    expect(CSS).not.toMatch(/\[role="button"\]:active/);
  });
});

describe('Save Selections reports on the button it was pressed on', () => {
  const handler = (name, end) => PYTEST.slice(PYTEST.indexOf(`async function ${name}(`),
                                              PYTEST.indexOf(end));

  it('step 3 passes its button to ptApi', () => {
    const fn = handler('ptSaveMatches', 'async function ptViewSource');
    expect(fn).toContain("getElementById('pt-save-matches-btn')");
    expect(fn).toMatch(/ptApi\([^;]*\bbtn\b/s);
    expect(HTML).toContain('id="pt-save-matches-btn"');
  });

  it('step 4 passes its button to ptApi', () => {
    const fn = handler('ptSaveFragments', '// --- Step 6');
    expect(fn).toContain("getElementById('pt-save-frag-btn')");
    expect(fn).toMatch(/ptApi\([^;]*\bbtn\b/s);
    expect(HTML).toContain('id="pt-save-frag-btn"');
  });

  it('step 4 reports beside the Save button, not up beside Gather', () => {
    // #pt-frag-status lives in the Gather row at the top of the panel. On a 31-step
    // case that is a screen-height from the Save button, which is why the save read
    // as a no-op. The confirmation has to render where the click happened.
    const fn = handler('ptSaveFragments', '// --- Step 6');
    expect(fn).toContain('pt-frag-save-status');
    expect(fn).not.toContain('pt-frag-status');
    expect(HTML).toContain('id="pt-frag-save-status"');
  });

  it('both keep a busy label, so the in-flight state names itself', () => {
    for (const [n, end] of [['ptSaveMatches', 'async function ptViewSource'],
                            ['ptSaveFragments', '// --- Step 6']]) {
      expect(handler(n, end)).toMatch(/busyLabel:\s*'Saving…'/);
    }
  });
});
