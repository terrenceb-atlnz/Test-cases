// Slice A in the UI (PLAN-generate-state-and-sequence-sanity, 2026-09-21).
//
// The server keeps two copies of the script (per-unit chunks, assembled file); after Fix whole
// script / Save / Generate Script only the file is current and any re-splice discards the edit.
// The server now refuses (409) while `gen_state.diverged`. Pinned here is the VISIBLE half:
//   * a pill in the unit row says "units stale" with the server's reason as its tooltip;
//   * every button that would re-splice is disabled with that reason, and re-enabled in sync;
//   * "Re-chunk from script" posts /rechunk and the panel re-renders from the returned state;
//   * "Reset Generate" asks first and posts /reset_generate only on yes.
// Driven through the real click dispatcher in jsdom, fetch stubbed.
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

import '../../ask-ck/frontend/ck-main/current/shared/actions.js';
import { S } from '../../ask-ck/frontend/ck-main/current/shared/state.js';
import { ptLoadCase, renderPtGenPanel } from '../../ask-ck/frontend/ck-main/current/pytest-creator/pytest.js';

const DOM = `
  <div id="nav-pt"></div>
  <div id="panel-pt-seq"><div id="pt-seq-case"></div><div id="pt-seq-refined"></div>
    <div id="pt-seq-list"></div><span id="pt-seq-status"></span><div id="pt-seq-prov"></div></div>
  <span id="pt-load-status"></span>
  <button id="pt-units-all-btn" data-action="ptGenerateAllUnits" class="btn" title="fire all">Generate all units (LLM)</button>
  <button id="pt-units-reload-btn" data-action="ptLoadUnits" class="btn">reload</button>
  <span id="pt-units-status"></span>
  <div id="pt-unit-pills"></div>
  <div id="pt-unit-errors"></div>
  <div id="pt-unit-page"></div>
  <div id="pt-summary-page" class="hidden">
    <span id="pt-gen-path"></span><span id="pt-gen-status"></span>
    <button id="pt-assemble-btn" data-action="ptAssembleAndSettle" class="btn">1 · Assemble + settle</button>
    <button id="pt-assemble-only-btn" data-action="ptAssembleScript" class="btn" title="Assemble + lint only">Assemble only</button>
    <button id="pt-fix-units-btn" data-action="ptFixUnits" class="btn">Fix units</button>
    <button id="pt-apply-held-btn" data-action="ptApplyAllHeld" class="btn">Apply all held</button>
    <button id="pt-rechunk-btn" data-action="ptRechunk" class="btn">Re-chunk from script</button>
    <button id="pt-reset-gen-btn" data-action="ptResetGenerate" class="btn">Reset Generate</button>
    <div id="pt-lint-result"></div><div id="pt-review-result"></div>
    <textarea id="pt-gen-code"></textarea>
    <div id="pt-gen-lib-wrap" class="hidden"><span id="pt-gen-lib-name"></span>
      <textarea id="pt-gen-lib-code"></textarea></div>
    <div id="pt-gen-prov"></div>
  </div>`;

const UNITS = [
  { id: 'setup', kind: 'setup', tc_n: null, label: 'TestSet.configure / tear_down', source_n: null,
    action: '', verify: '', blank_block: 'x', prompt: 'P-setup', edited: false, code: 'c', status: 'ok', error: '', at: 't' },
  { id: 'tc1', kind: 'testcase', tc_n: 1, label: 'TestCase_1', source_n: 1, action: 'a', verify: 'v',
    blank_block: 'x', prompt: 'P-1', edited: false, code: 'c', status: 'ok', error: '', at: 't' },
];
const REASON = 'The assembled script and the generated units are out of step: … Re-chunk from script first.';
const STALE = { script_hash: 'abc123', assembled_hash: '', units: 2, frame_snapshot: false,
                diverged: true, reason: REASON, review_stale: false };
const SYNC = { ...STALE, assembled_hash: 'abc123', frame_snapshot: true, diverged: false, reason: '' };

let calls, genState, confirmAnswer;
const reply = (body) => ({ ok: true, status: 200, json: async () => body });
const click = (sel) => document.querySelector(sel).dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
const settle = async (n = 4) => { for (let i = 0; i < n; i++) await new Promise((r) => setTimeout(r, 0)); };
const session = () => ({ step2: { sequence: [{ n: 1, action: 'a', verify: 'v' }] },
                         step6: { files: { test: { name: 'x.py', code: 'print(1)' } }, lint: { ok: true, errors: [], warnings: [] } } });

beforeEach(async () => {
  document.body.innerHTML = DOM;
  calls = []; genState = STALE; confirmAnswer = true;
  S.ptCase = { key: 'AWPTCM-T1' };
  window.alert = vi.fn();
  window.confirm = vi.fn(() => confirmAnswer);
  global.fetch = vi.fn(async (url, opts) => {
    const u = String(url); calls.push(u);
    if (u.includes('/load_case/')) return reply({ session: session(), case_title: 't', group_display: 'g', objective: 'o', steps: [], read_only: false, lock: null, gen_state: genState });
    if (u.includes('/session/')) return reply({ session: session(), gen_state: genState });
    if (u.includes('/step_prompts/')) return reply({ units: UNITS });
    if (u.includes('/units_status/')) return reply({ units: {}, running: [] });
    if (u.includes('/rechunk/')) { genState = SYNC; return reply({ changed: ['setup', 'tc1'], dropped: [], units: ['setup', 'tc1'], gen_state: SYNC }); }
    if (u.includes('/reset_generate/')) { genState = { ...STALE, units: 0 }; return reply({ dropped_units: ['setup', 'tc1'], kept: ['files', 'lint', 'naming'], gen_state: genState }); }
    return reply({});
  });
  await ptLoadCase();
  renderPtGenPanel();
  await settle();
});
afterEach(() => vi.restoreAllMocks());

describe('the units ⇄ script pill', () => {
  it('says the units are stale, with the server reason as its tooltip, while diverged', () => {
    const pill = document.getElementById('pt-gen-state-pill');
    expect(pill).not.toBeNull();
    expect(pill.textContent).toContain('units stale');
    expect(pill.title).toBe(REASON);
    expect(pill.classList.contains('pt-state-stale')).toBe(true);
  });

  it('disables every button that would re-splice, and only those', () => {
    for (const id of ['pt-assemble-btn', 'pt-assemble-only-btn', 'pt-fix-units-btn', 'pt-apply-held-btn', 'pt-units-all-btn']) {
      const b = document.getElementById(id);
      expect(b.disabled, id).toBe(true);
      expect(b.title, id).toBe(REASON);
    }
    expect(document.getElementById('pt-rechunk-btn').disabled).toBe(false);
    expect(document.getElementById('pt-reset-gen-btn').disabled).toBe(false);
  });
});

describe('Re-chunk from script', () => {
  it('posts /rechunk, then shows the in-sync pill and re-enables the buttons with their own titles', async () => {
    click('#pt-rechunk-btn');
    await settle(8);
    expect(calls.some((u) => u.includes('/rechunk/AWPTCM-T1'))).toBe(true);
    const pill = document.getElementById('pt-gen-state-pill');
    expect(pill.textContent).toContain('units ⇄ script');
    expect(pill.classList.contains('pt-state-ok')).toBe(true);
    const only = document.getElementById('pt-assemble-only-btn');
    expect(only.disabled).toBe(false);
    expect(only.title).toBe('Assemble + lint only');        // the original tooltip is restored
    expect(document.getElementById('pt-units-all-btn').title).toBe('fire all');
    expect(document.getElementById('pt-gen-status').textContent).toContain('Re-chunked from the script');
  });
});

describe('Reset Generate', () => {
  it('asks first and does nothing on no', async () => {
    confirmAnswer = false;
    click('#pt-reset-gen-btn');
    await settle();
    expect(window.confirm).toHaveBeenCalled();
    expect(calls.some((u) => u.includes('/reset_generate/'))).toBe(false);
  });

  it('posts /reset_generate on yes and reports what was dropped', async () => {
    click('#pt-reset-gen-btn');
    await settle(8);
    expect(calls.some((u) => u.includes('/reset_generate/AWPTCM-T1'))).toBe(true);
    expect(document.getElementById('pt-gen-status').textContent).toContain('2 unit(s) dropped');
  });
});
