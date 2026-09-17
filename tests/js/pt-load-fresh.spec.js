// "Load Case & New Session" — the fresh-reload button (2026-09-17).
//
// A case edited upstream (objective/steps changed, re-exported + pushed) kept driving the
// OLD sequence in the PyTest Creator, because a plain "Load Case & Continue" reuses the
// stored session by design. This button is the opt-in to discard that session and reload
// from the freshly exported bundle on disk. The server does the discarding; the button's
// only jobs are (1) confirm before the destructive reload, and (2) send `?fresh=true`.
// Both are driven here through the real click dispatcher in jsdom, fetch stubbed.
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

import '../../ask-ck/frontend/ck-main/current/shared/actions.js';
import { S } from '../../ask-ck/frontend/ck-main/current/shared/state.js';
import '../../ask-ck/frontend/ck-main/current/pytest-creator/pytest.js';

const DOM = `
  <div id="nav-pt"></div>
  <div id="panel-pt-seq">
    <div id="pt-seq-case"></div><div id="pt-seq-refined"></div>
    <div id="pt-seq-list"></div><span id="pt-seq-status"></span><div id="pt-seq-prov"></div>
  </div>
  <span id="pt-load-status"></span>
  <div id="pt-steps-list"></div>
  <button data-action="ptLoadCase" class="btn btn-primary btn-compact">Load Case &amp; Continue</button>
  <button data-action="ptLoadCaseFresh" class="btn btn-secondary btn-compact">Load Case &amp; New Session</button>
`;

let calls;
const reply = (body) => ({ ok: true, status: 200, json: async () => body });
const click = (sel) => document.querySelector(sel)
  .dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
const settle = () => new Promise((r) => setTimeout(r, 0));

beforeEach(() => {
  document.body.innerHTML = DOM;
  calls = [];
  S.ptCase = { key: 'AWPTCM-T1' };
  window.alert = () => {};
  global.fetch = vi.fn(async (url) => {
    calls.push(String(url));
    return reply({ session: { step2: { sequence: [] } }, case_title: 't',
                   group_display: 'g', objective: 'o', steps: [], read_only: false, lock: null });
  });
});

afterEach(() => { vi.restoreAllMocks(); });

const loadCalls = () => calls.filter((u) => u.includes('/load_case/'));

describe('Load Case & New Session', () => {
  it('sends ?fresh=true once the destructive reload is confirmed', async () => {
    window.confirm = vi.fn(() => true);
    click('[data-action="ptLoadCaseFresh"]');
    await settle();
    expect(window.confirm).toHaveBeenCalledTimes(1);
    expect(loadCalls()).toHaveLength(1);
    expect(loadCalls()[0]).toContain('/load_case/AWPTCM-T1?fresh=true');
  });

  it('does nothing when the confirmation is dismissed', async () => {
    window.confirm = vi.fn(() => false);
    click('[data-action="ptLoadCaseFresh"]');
    await settle();
    expect(window.confirm).toHaveBeenCalledTimes(1);
    expect(loadCalls()).toHaveLength(0);   // no reload, no session discarded
  });
});

describe('Load Case & Continue (unchanged)', () => {
  it('reloads without fresh and without asking for confirmation', async () => {
    window.confirm = vi.fn(() => true);
    click('[data-action="ptLoadCase"]');
    await settle();
    expect(window.confirm).not.toHaveBeenCalled();
    expect(loadCalls()).toHaveLength(1);
    expect(loadCalls()[0]).not.toContain('fresh');
  });
});
