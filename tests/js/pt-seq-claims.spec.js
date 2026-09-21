// Slice C in the UI (PLAN-generate-state-and-sequence-sanity, 2026-09-21).
//
// The extractor now checks its own sequence: state-changing steps carry a `claim` (cable /
// DUT / partner / expected link) and unresolved contradictions arrive as `sanity` flags.
// Pinned: the claim renders as a compact column ("crossover · DUT mdix · partner mdi → down"),
// flagged rows are marked with the issue as their tooltip, the flags are listed above the
// table, Confirm Step 2 is NOT disabled by any of it, and a Save Edits round-trip carries
// `kind` and `claim` back to the server (they used to be dropped — a setup step came back as
// a TestCase). Driven through ptLoadCase + renderPtSeqPanel in jsdom, fetch stubbed.
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

import '../../ask-ck/frontend/ck-main/current/shared/actions.js';
import { S } from '../../ask-ck/frontend/ck-main/current/shared/state.js';
import { ptLoadCase, renderPtSeqPanel } from '../../ask-ck/frontend/ck-main/current/pytest-creator/pytest.js';

const DOM = `
  <div id="nav-pt"></div>
  <div id="panel-pt-seq">
    <div id="pt-seq-case"></div><div id="pt-seq-refined"></div>
    <button data-action="ptExtractSequence" id="pt-seq-extract-btn" class="btn">Extract</button>
    <button data-action="ptSaveSequence" id="pt-seq-save-btn" class="btn">Save Edits</button>
    <button data-action="ptConfirm" data-args='[2]' id="pt-seq-confirm-btn" class="btn">Confirm Step 2</button>
    <span id="pt-seq-status"></span>
    <div id="pt-seq-sanity"></div>
    <div id="pt-seq-list"></div><div id="pt-seq-prov"></div>
  </div>
  <span id="pt-load-status"></span><div id="pt-steps-list"></div>`;

const SEQ = [
  { n: 1, action: 'set both ends to auto', verify: '', kind: 'setup', zephyr_step_idx: 1 },
  { n: 2, action: 'force DUT mdix, partner mdi over crossover', verify: 'link is down', kind: 'verify', zephyr_step_idx: 2,
    claim: { cable: 'crossover', dut: 'mdix', partner: 'mdi', expect: 'down' } },
  { n: 3, action: 'read show interface', verify: 'current polarity present', kind: 'verify', zephyr_step_idx: 2 },
];
const SANITY = [{ steps: [2, 3], issue: 'step 3 asserts a current value on a link step 2 expects down' }];

let calls, bodies, session;
const reply = (body) => ({ ok: true, status: 200, json: async () => body });
const click = (sel) => document.querySelector(sel).dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
const settle = async (n = 4) => { for (let i = 0; i < n; i++) await new Promise((r) => setTimeout(r, 0)); };

beforeEach(async () => {
  document.body.innerHTML = DOM;
  calls = []; bodies = {};
  session = { step2: { sequence: SEQ, sanity: SANITY, confirmed: false } };
  S.ptCase = { key: 'AWPTCM-T1' };
  window.alert = vi.fn();
  global.fetch = vi.fn(async (url, opts) => {
    const u = String(url); calls.push(u);
    if (opts && opts.body) { try { bodies[u] = JSON.parse(opts.body); } catch (e) { /* not json */ } }
    if (u.includes('/load_case/')) return reply({ session, case_title: 't', group_display: 'g', objective: 'o', steps: [{ description: 's1' }, { description: 's2' }], read_only: false, lock: { by_me: true } });
    if (u.includes('/session/')) return reply({ session });
    if (u.includes('/save_sequence/')) return reply({ sequence: SEQ, coverage: { ok: true }, sanity: SANITY });
    return reply({});
  });
  await ptLoadCase();
  renderPtSeqPanel();
  await settle();
});
afterEach(() => vi.restoreAllMocks());

describe('claims and sanity flags on the Sequence page', () => {
  it('renders the claim as a compact column, dash where a step has none', () => {
    const cells = Array.from(document.querySelectorAll('td.pt-seq-claim')).map((td) => td.textContent.trim());
    expect(cells).toHaveLength(3);
    expect(cells[1]).toBe('crossover · DUT mdix · partner mdi → down');
    expect(cells[0]).toBe('—');
  });

  it('lists the flags above the table and marks the rows they name, with the issue as tooltip', () => {
    const box = document.getElementById('pt-seq-sanity');
    expect(box.textContent).toContain('1 sanity flag(s)');
    expect(box.textContent).toContain('steps 2, 3');
    const rows = Array.from(document.querySelectorAll('tr.pt-seq-row'));
    expect(rows[0].classList.contains('pt-seq-flagged')).toBe(false);
    expect(rows[1].classList.contains('pt-seq-flagged')).toBe(true);
    expect(rows[2].classList.contains('pt-seq-flagged')).toBe(true);
    expect(rows[1].title).toContain('step 3 asserts a current value');
  });

  it('never disables Confirm Step 2 — the flags warn, the human decides', () => {
    expect(document.getElementById('pt-seq-confirm-btn').disabled).toBe(false);
  });

  it('carries kind and claim back on Save Edits so a setup step stays a setup step', async () => {
    click('#pt-seq-save-btn');
    await settle(6);
    const url = calls.find((u) => u.includes('/save_sequence/'));
    expect(url).toBeTruthy();
    const sent = bodies[url].sequence;
    expect(sent[0].kind).toBe('setup');
    expect(sent[1].claim).toEqual({ cable: 'crossover', dut: 'mdix', partner: 'mdi', expect: 'down' });
    expect(sent[2].kind).toBe('verify');
    expect(sent[2].claim).toBeUndefined();
  });
});

describe('a sequence with no claims and no flags', () => {
  it('renders exactly as before: no claim column, empty sanity box', async () => {
    session = { step2: { sequence: SEQ.map(({ claim, ...s }) => s), sanity: [] } };
    await ptLoadCase();
    renderPtSeqPanel();
    await settle();
    expect(document.querySelector('td.pt-seq-claim')).toBeNull();
    expect(document.getElementById('pt-seq-sanity').innerHTML).toBe('');
    expect(document.querySelector('tr.pt-seq-flagged')).toBeNull();
  });
});
