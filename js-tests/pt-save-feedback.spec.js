// Save Selections has to show, on the button, that it did something (2026-09-02).
//
// "I hit save. didnt get the green check. i dont see any faults."
//
// The button was wired to pass itself to ptApi, which owns the spinner-while-busy
// and the ✓/✗ flash. Whether that wiring actually FIRES could not be settled by
// reading it, and the previous spec for this only pinned the source text. So this
// one drives the real handler through the real click dispatcher in jsdom, with
// fetch stubbed and resolved by hand, and asserts what the button looks like
// while the request is in flight and after it lands.
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

import '../ask-ck/CK-main/CK_server/static/js/actions.js';
import { S } from '../ask-ck/CK-main/CK_server/static/js/state.js';
import { ptLoadCase, renderPtFragPanel } from '../ask-ck/CK-main/CK_server/static/js/pytest.js';

// The handlers only touch these; everything else in index.html is irrelevant here.
const DOM = `
  <div id="nav-pt"></div>
  <div id="panel-pt-seq">
    <div id="pt-seq-case"></div><div id="pt-seq-refined"></div>
    <div id="pt-seq-list"></div><span id="pt-seq-status"></span><div id="pt-seq-prov"></div>
  </div>
  <span id="pt-load-status"></span>
  <div id="pt-steps-list"></div>
  <span id="pt-search-status"></span>
  <button data-action="ptSaveMatches" class="btn btn-compact" id="pt-save-matches-btn">Save Selections</button>
  <div id="pt-frag-coverage"></div>
  <div id="pt-frag-list"></div>
  <div id="pt-frag-prov"></div>
  <span id="pt-frag-status"></span>
  <button data-action="ptSaveFragments" class="btn btn-compact" id="pt-save-frag-btn">Save Selections</button>
  <span id="pt-frag-save-status"></span>
`;

let pending;            // resolver for the in-flight save
let calls;

function reply(body) {
  return { ok: true, status: 200, json: async () => body };
}

beforeEach(async () => {
  document.body.innerHTML = DOM;
  calls = [];
  pending = null;
  S.ptCase = { key: 'AWPTCM-T1' };
  window.alert = () => {};
  global.fetch = vi.fn(async (url, opts) => {
    calls.push(String(url));
    if (String(url).includes('/load_case/')) {
      return reply({ session: { step2: { sequence: [] } }, case_title: 't',
                     group_display: 'g', objective: 'o', steps: [], read_only: false, lock: null });
    }
    if (String(url).includes('/session/')) return reply({ session: { step2: { sequence: [] } } });
    if (String(url).includes('/save_fragments/') || String(url).includes('/save_matches/')) {
      return new Promise((res) => { pending = () => res(reply({ ok: true })); });
    }
    return reply({});
  });
  await ptLoadCase();                 // the only way to make ptSession truthy
  expect(calls.some(u => u.includes('/load_case/'))).toBe(true);
});

afterEach(() => { vi.restoreAllMocks(); });

const click = (id) => document.getElementById(id)
  .dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
const settle = () => new Promise((r) => setTimeout(r, 0));

describe.each([
  ['pt-save-frag-btn', '/save_fragments/'],
  ['pt-save-matches-btn', '/save_matches/'],
])('%s', (btnId, path) => {
  it('shows a named busy state while the save is in flight', async () => {
    click(btnId);
    await settle();
    const btn = document.getElementById(btnId);
    expect(calls.some(u => u.includes(path))).toBe(true);
    expect(btn.classList.contains('is-busy')).toBe(true);
    expect(btn.disabled).toBe(true);
    expect(btn.textContent).toContain('Saving');
    expect(btn.querySelector('.ck-spinner')).not.toBeNull();
  });

  it('leaves the busy state and flashes success when the save lands', async () => {
    click(btnId);
    await settle();
    pending();
    await settle();
    await settle();
    const btn = document.getElementById(btnId);
    expect(btn.classList.contains('is-busy')).toBe(false);
    expect(btn.disabled).toBe(false);
    expect(btn.querySelector('.ck-spinner')).toBeNull();
    expect(btn.textContent).not.toContain('Saving');
    // The green flash — the thing the reviewer went looking for and did not see.
    expect(btn.classList.contains('is-done')).toBe(true);
    expect(btn.classList.contains('is-error')).toBe(false);
  });

  it('says "Saved" in words, not colour alone', async () => {
    // Colour alone WAS wired and DID fire — this spec proved that before the label
    // existed. It was still reported as no feedback, because 1.2s of green on a fast
    // save is gone before the eye returns to the button. Words survive that.
    click(btnId);
    await settle();
    pending();
    await settle();
    await settle();
    const btn = document.getElementById(btnId);
    expect(btn.textContent).toContain('Saved');
    expect(btn.classList.contains('is-done')).toBe(true);
  });

  it('does not claim "Saved" when the save FAILED', async () => {
    // A red button reading "✓ Saved" is worse than no feedback at all: the whole
    // point of the label is that the reviewer trusts it without reading the status.
    global.fetch = vi.fn(async (url) => {
      if (String(url).includes(path)) {
        return { ok: false, status: 409, json: async () => ({ detail: 'stale write' }) };
      }
      return reply({ session: {} });
    });
    click(btnId);
    await settle(); await settle();
    const btn = document.getElementById(btnId);
    expect(btn.classList.contains('is-error')).toBe(true);
    expect(btn.classList.contains('is-done')).toBe(false);
    expect(btn.textContent).not.toContain('Saved');
    expect(btn.textContent).toBe('Save Selections');
  });

  it('also marks the press, so the click is visible before the response is', async () => {
    click(btnId);
    expect(document.getElementById(btnId).classList.contains('ck-pressed')).toBe(true);
  });
});

describe('the flash label is temporary', () => {
  it('puts the original label back when the flash ends', async () => {
    vi.useFakeTimers();
    try {
      click('pt-save-frag-btn');
      await vi.advanceTimersByTimeAsync(0);
      pending();
      await vi.advanceTimersByTimeAsync(0);
      await vi.advanceTimersByTimeAsync(0);
      const btn = document.getElementById('pt-save-frag-btn');
      expect(btn.textContent).toContain('Saved');
      await vi.advanceTimersByTimeAsync(2000);
      expect(btn.textContent).toBe('Save Selections');
      expect(btn.classList.contains('is-done')).toBe(false);
    } finally { vi.useRealTimers(); }
  });
});

describe('fragments save status', () => {
  it('writes its confirmation beside the button, not up beside Gather', async () => {
    click('pt-save-frag-btn');
    await settle();
    pending();
    await settle(); await settle(); await settle();
    expect(document.getElementById('pt-frag-save-status').textContent).toContain('Saved');
    expect(document.getElementById('pt-frag-status').textContent).toBe('');
  });
});


// The count on the save line (2026-09-02)
// --------------------------------------
// "I think theres more than 34 fragments selected for generation, but i could be
// wrong. is that number accurate?"
//
// It was: 34 unique fragments. The panel had 157 ticked CARDS on screen, because a
// fragment that serves 26 sequence steps is one pool entry and 26 cards. Counting
// what you can see and comparing it to what the button says makes a correct tool
// look broken, so the line now says which number it means and shows the other.
describe('the saved-count says which number it is reporting', () => {
  const frag = (sid, sym, steps) => ({ source_id: sid, symbol: sym, maps_to: steps, why: '' });

  async function seed(session) {
    global.fetch = vi.fn(async (url) => {
      if (String(url).includes('/load_case/')) {
        return reply({ session, case_title: 't', group_display: 'g', objective: 'o',
                       steps: [], read_only: false, lock: null });
      }
      if (String(url).includes('/session/')) return reply({ session });
      if (String(url).includes('/save_fragments/')) return reply({ ok: true });
      return reply({});
    });
    await ptLoadCase();
    renderPtFragPanel();          // seeds the pool / selection / accounting
  }

  it('reports unique fragments AND the cards on screen when they differ', async () => {
    await seed({
      step2: { sequence: [{ n: 1, action: 'a' }, { n: 2, action: 'b' }, { n: 3, action: 'c' }] },
      step5: {
        fragments: [frag('lib.py', 'wide', [1, 2, 3]), frag('lib.py', 'narrow', [1])],
        selected: [{ source_id: 'lib.py', symbol: 'wide' },
                   { source_id: 'lib.py', symbol: 'narrow' }],
        accounting: {},
      },
    });
    click('pt-save-frag-btn');
    for (let i = 0; i < 6; i++) await settle();
    const txt = document.getElementById('pt-frag-save-status').textContent;
    expect(txt).toContain('2 unique fragment(s)');
    expect(txt).toContain('4 ticked card(s)');     // 2 on step 1, 1 on step 2, 1 on step 3
    expect(txt).toContain('across 3 step(s)');
  });

  it('counts a fragment once per step, not once per accounting entry', async () => {
    // A fragment can be BOTH the chosen one for a step and in that step's maps_to.
    // Double-counting there would inflate the card number the reviewer is checking.
    await seed({
      step2: { sequence: [{ n: 1, action: 'a' }, { n: 2, action: 'b' }] },
      step5: {
        fragments: [frag('lib.py', 'wide', [1, 2])],
        selected: [{ source_id: 'lib.py', symbol: 'wide' }],
        accounting: { 1: [{ chosen: ['lib.py', 'wide'], redundant: [] }] },
      },
    });
    click('pt-save-frag-btn');
    for (let i = 0; i < 6; i++) await settle();
    expect(document.getElementById('pt-frag-save-status').textContent)
      .toContain('2 ticked card(s)');
  });

  it('counts a ticked REDUNDANT card, which the panel does render', async () => {
    await seed({
      step2: { sequence: [{ n: 1, action: 'a' }, { n: 2, action: 'b' }] },
      step5: {
        fragments: [frag('lib.py', 'chosen', [1, 2]), frag('lib.py', 'alt', [])],
        selected: [{ source_id: 'lib.py', symbol: 'chosen' },
                   { source_id: 'lib.py', symbol: 'alt' }],
        accounting: { 1: [{ chosen: ['lib.py', 'chosen'],
                            redundant: [{ key: ['lib.py', 'alt'], why: 'dup' }] }] },
      },
    });
    click('pt-save-frag-btn');
    for (let i = 0; i < 6; i++) await settle();
    // step 1 paints chosen + the ticked redundant alt; step 2 paints chosen only.
    const txt = document.getElementById('pt-frag-save-status').textContent;
    expect(txt).toContain('2 unique fragment(s)');
    expect(txt).toContain('3 ticked card(s)');
  });

  it('counts TICKED cards only, not every card on the page', async () => {
    // "ticked card(s)" has to mean ticked. Counting every card painted would put a
    // number on the line that the reviewer cannot reproduce by counting ticks —
    // which is the exact confusion this message exists to end.
    await seed({
      step2: { sequence: [{ n: 1, action: 'a' }, { n: 2, action: 'b' }] },
      step5: {
        fragments: [frag('lib.py', 'kept', [1, 2]), frag('lib.py', 'unticked', [1])],
        selected: [{ source_id: 'lib.py', symbol: 'kept' }],
        accounting: {},
      },
    });
    click('pt-save-frag-btn');
    for (let i = 0; i < 6; i++) await settle();
    const txt = document.getElementById('pt-frag-save-status').textContent;
    expect(txt).toContain('1 unique fragment(s)');
    expect(txt).toContain('2 ticked card(s)');     // NOT 3 — the unticked card is a card
  });

  it('drops the parenthetical when the two numbers agree', async () => {
    // One fragment, one step: "1 unique fragment(s) (1 ticked card(s) across 1
    // step(s))" is noise that makes a simple case read as a puzzle.
    await seed({
      step2: { sequence: [{ n: 1, action: 'a' }] },
      step5: {
        fragments: [frag('lib.py', 'only', [1])],
        selected: [{ source_id: 'lib.py', symbol: 'only' }],
        accounting: {},
      },
    });
    click('pt-save-frag-btn');
    for (let i = 0; i < 6; i++) await settle();
    const txt = document.getElementById('pt-frag-save-status').textContent;
    expect(txt).toBe('Saved — 1 fragment(s) selected for generation.');
    expect(txt).not.toContain('card(s)');
  });

  it('never reports fewer cards than unique fragments', async () => {
    // A selected fragment mapping to NO step still counts as one fragment. If the
    // card count could fall below it the message would contradict itself.
    await seed({
      step2: { sequence: [{ n: 1, action: 'a' }] },
      step5: {
        fragments: [frag('lib.py', 'orphan', []), frag('lib.py', 'onstep', [1])],
        selected: [{ source_id: 'lib.py', symbol: 'orphan' },
                   { source_id: 'lib.py', symbol: 'onstep' }],
        accounting: {},
      },
    });
    click('pt-save-frag-btn');
    for (let i = 0; i < 6; i++) await settle();
    // 2 unique, 1 card — the parenthetical is suppressed rather than showing 1 < 2.
    expect(document.getElementById('pt-frag-save-status').textContent)
      .toBe('Saved — 2 fragment(s) selected for generation.');
  });
});
