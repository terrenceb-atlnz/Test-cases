// Zephyr Templating Tool page (PLAN-zephyr-templating.md §5a; docs/zephyr.txt "UI"). A Svelte island
// since 2026-10-09 (PLAN-test-composer Z1): the model is svelte-src/src/zt/model.js and the page is
// the BUILT bundle current/islands/zt.js, mounted here against a fake server — so these specs test
// exactly what ships. What they pin: the tree starts fully ticked and only the analysis's PROPOSALS
// untick it; unticking a parent unticks everything below it, ticking a child re-ticks its parents;
// the upload body lists every template cycle of a ticked plan (an unticked one must still be
// unlinked) and each kept cycle's unticked cases; the Results Analysis column is the questions in
// order, with failed calls and refused proposals shown rather than hidden; Write to Zephyr asks in a
// modal first; a stopped upload says nothing was undone.
import { describe, it, expect, afterEach } from 'vitest';

import { treeRows, applyProposals, setTick, uploadSelection, isOpen, cleanField }
  from '../../ask-ck/frontend/ck-main/current/svelte-src/src/zt/model.js';
import { mountZt, flushSync } from '../../ask-ck/frontend/ck-main/current/islands/zt.js';

const TREE = { plans: [
  { key: 'P1', name: 'Port', cycles: [{ key: 'C1', name: 'Port', cases: [{ key: 'T1', name: 'speed' }, { key: 'T2', name: 'duplex' }] }] },
  { key: 'P2', name: 'Boot', cycles: [
    { key: 'C2', name: 'Manual', cases: [{ key: 'T3', name: 'menu' }, { key: 'T1', name: 'speed' }] },
    { key: 'C3', name: 'Automated', cases: [] }] },
] };
const ids = (set) => [...set].sort();

describe('the tree', () => {
  it('has one row per plan, cycle and case, keyed by path', () => {
    expect(treeRows(TREE).map(r => r.id)).toEqual(
      ['P1', 'P1/C1', 'P1/C1/T1', 'P1/C1/T2', 'P2', 'P2/C2', 'P2/C2/T3', 'P2/C2/T1', 'P2/C3']);
  });

  it('starts all ticked; a proposal unticks its row and everything below, only inside its own plan', () => {
    const { ticked, ai } = applyProposals(TREE, { plans: {
      P1: { deselect: [{ key: 'T1', question: 'Q4', reason: 'no PoE', source: 'TPS §11.4' }] },
      P2: { deselect: [{ key: 'C2', question: 'Q2', reason: 'r', source: 's' }] },
    } });
    expect(ids(ticked)).toEqual(['P1', 'P1/C1', 'P1/C1/T2', 'P2', 'P2/C3']);
    expect(ai.get('P1/C1/T1')).toEqual({ question: 'Q4', reason: 'no PoE', source: 'TPS §11.4' });
    expect(ai.has('P2/C2/T1')).toBe(false);          // T1's proposal was P1's, not P2's
  });

  it('unticking a parent unticks its children; ticking a child re-ticks its parents', () => {
    const t = new Set(treeRows(TREE).map(r => r.id));
    setTick(t, TREE, 'P2', false);
    expect([...t].filter(x => x.startsWith('P2'))).toEqual([]);
    setTick(t, TREE, 'P2/C2/T3', true);
    expect(ids(t).filter(x => x.startsWith('P2'))).toEqual(['P2', 'P2/C2', 'P2/C2/T3']);
  });

  it("keeps a plan cut by the analysis itself collapsed; the user's own fold wins", () => {
    const job = { plans: { P1: { deselect: [{ key: 'P1', question: 'Q1', reason: 'not in scope', source: 'Strategy' }] } } };
    const { ai } = applyProposals(TREE, job);
    expect(isOpen('P1', ai, new Map())).toBe(false);
    expect(isOpen('P1', ai, new Map([['P1', true]]))).toBe(true);
  });
});

describe('the upload body', () => {
  it('lists every template cycle of a ticked plan, marks the unticked ones, and excludes unticked cases', () => {
    const t = new Set(treeRows(TREE).map(r => r.id));
    setTick(t, TREE, 'P1', false);
    setTick(t, TREE, 'P2/C3', false);
    setTick(t, TREE, 'P2/C2/T1', false);
    const sel = uploadSelection(TREE, t, { version: '5.5.6-2', product: 'IE570', middle: 'Tomahawk', number: '3001' });
    expect(sel).toEqual({ version: '5.5.6-2', middle: 'Tomahawk', product: 'IE570', number: '3001', plans: [
      { key: 'P2', name: 'Boot', cycles: [
        { key: 'C2', name: 'Manual', selected: true, excluded: ['T1'] },
        { key: 'C3', name: 'Automated', selected: false, excluded: [] }] }] });
  });
});

describe('the project fields', () => {
  it('treats blank, N/A, None and - as not set, and trims the rest', () => {
    for (const v of ['', '  ', 'N/A', 'n/a', 'NA', 'None', 'none', '-', null, undefined]) expect(cleanField(v)).toBe(null);
    expect(cleanField(' Tomahawk ')).toBe('Tomahawk');
    expect(cleanField('3001')).toBe('3001');
  });
});

// ------------------------------------------------------------------ the mounted page (built bundle)

const SNAPSHOT = Object.assign({ imported_at: '2026-10-05T01:14:27Z', counts: { plans: 2, cycles: 3, cases: 4 } }, TREE);
const PREVIEW = {
  targets: { testplan: { path: '/5.5.6-2/Tomahawk/Project 3001: IE570' }, testrun: { path: null } },
  counts: { plans: 1, cycles: 1, calls: 2, skipped: 1, writes: 10 }, problems: [],
  project_folders: [{ kind: 'testplan', path: '/5.5.6-2/Tomahawk/Project 3001: IE570', version: '5.5.6-2' },
                    { kind: 'testrun', path: '/5.5.6-1/Tomahawk/Project 3001: IE570', version: '5.5.6-1' }],
  duplicates: [{ key: 'P9', name: 'IE570: Port (Ask-CK)' }],
  calls: [{ n: 1, op: 'clone plan', method: 'POST', path: '/x', known: true, about: 'a <b>' },
          { n: 2, op: 'rename', method: 'PUT', path: '/y', known: true, about: 'b' }] };

/** A fake zephyr-tool router: `routes` maps "METHOD path" to a value or a function(body). */
function fakeApi(routes) {
  const calls = [];
  const api = async (path, opts = {}) => {
    const key = `${(opts.method || 'GET')} ${path}`;
    const body = opts.body ? JSON.parse(opts.body) : undefined;
    calls.push({ key, body });
    if (!(key in routes)) throw new Error('no route ' + key);
    const r = routes[key];
    const v = typeof r === 'function' ? r(body) : r;
    if (v instanceof Error) throw v;
    return JSON.parse(JSON.stringify(v));
  };
  return { api, calls };
}

let app = null;
let root = null;
afterEach(() => { if (app) app.destroy(); app = null; if (root) root.remove(); root = null; });

async function until(cond, ms = 2000) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    flushSync();
    if (cond()) return;
    await new Promise(r => setTimeout(r, 5));
  }
  throw new Error('timed out waiting');
}

async function page(routes) {
  const f = fakeApi(Object.assign({ 'GET /templates': { snapshot: SNAPSHOT } }, routes));
  root = document.createElement('div');
  root.id = 'panel-zt';
  document.body.appendChild(root);
  app = mountZt(root, { api: f.api, pollMs: 5 });
  await until(() => root.querySelector('#zt-tree .zt-row'));
  return f;
}

const $ = (sel) => root.querySelector(sel);
const keys = () => [...root.querySelectorAll('#zt-tree .zt-key')].map(e => e.textContent);
const click = async (el) => { el.click(); flushSync(); await Promise.resolve(); flushSync(); };

async function analysed(job) {
  const f = await page({ 'POST /analyse': { id: 'J1' }, 'GET /analyse/J1': job });
  const url = $('#zt-url');
  url.value = 'Project:3001_IE570';
  url.dispatchEvent(new Event('input', { bubbles: true }));
  await click($('#zt-analyse'));
  await until(() => $('.zt-state') && $('.zt-state').textContent.includes(job.state === 'done' ? 'complete' : ''));
  await until(() => !$('#zt-cancel'));
  return f;
}

describe('the page: tree and folding', () => {
  // Terrence 2026-10-07: "default-collapsed, unless a change has been made within them by the LLM analysis".
  it('starts with only the plans showing, all ticked, with counts and the templates line', async () => {
    await page({});
    expect(keys()).toEqual(['P1', 'P2']);
    expect($('#zt-tree').textContent).toContain('2 case(s)');
    expect($('#zt-tree-count').textContent).toBe('2/2 plans · 3/3 cycles · 4/4 cases ticked');
    expect($('#zt-templates-info').textContent).toContain('Templates imported 2026-10-05 01:14 UTC: 2 plans, 3 cycles, 4 cases.');
    expect($('#zt-upload').disabled).toBe(true);
  });

  it('opens the plan and cycle the analysis unticked something in — only those — and shows the reason', async () => {
    await analysed({ state: 'done', plans: { P2: { state: 'done', deselect: [{ key: 'T3', question: 'Q3', reason: 'no boot menu', source: 'TPS' }] } } });
    expect(keys()).toEqual(['P1', 'P2', 'C2', 'T3', 'T1', 'C3']);
    expect($('#zt-tree').textContent).toContain('1 unticked');
    expect($('#zt-tree').textContent).toContain('no boot menu');
    expect($('#zt-tree .zt-row.is-off .zt-key').textContent).toBe('T3');
  });

  it("the user's own fold wins, and a click on a parent unticks everything below it", async () => {
    await page({});
    await click(root.querySelector('.zt-fold[data-id="P1"]'));
    expect(keys()).toEqual(['P1', 'C1', 'P2']);
    const box = root.querySelector('input[data-id="P1"]');
    box.checked = false;
    box.dispatchEvent(new Event('change', { bubbles: true }));
    flushSync();
    expect($('#zt-tree-count').textContent).toBe('1/2 plans · 2/3 cycles · 2/4 cases ticked');
  });

  it('escapes names: a name is text, never markup', async () => {
    const f = fakeApi({ 'GET /templates': { snapshot: { plans: [{ key: 'P9', name: '<b>x</b>', cycles: [] }] } } });
    root = document.createElement('div'); document.body.appendChild(root);
    app = mountZt(root, { api: f.api, pollMs: 5 });
    await until(() => root.querySelector('#zt-tree .zt-row'));
    expect($('#zt-tree').textContent).toContain('<b>x</b>');
    expect($('#zt-tree label b')).toBe(null);
  });
});

describe('the page: Results Analysis', () => {
  it('lays it out as the questions, then gaps and AI Notes, and shows what went wrong', async () => {
    await analysed({ state: 'done', wiki_problems: ['the TPS has no SID table'], plans: {
      P1: { state: 'done', deselect: [{ key: 'T1', question: 'Q4', reason: 'no PoE', source: 'TPS §11.4' }],
            notes: [{ key: null, note: 'no PoE ports' }], dropped: [{ why: 'duplicate' }] },
      P2: { state: 'error', error: 'backend down', deselect: [], notes: [], dropped: [] } },
      gaps: { state: 'done', gaps: [{ requirement: 'PROFINET', source: 'Strategy §3.3' }], notes: [{ note: 'stacks 4' }], dropped: [] } });
    const text = $('#zt-analysis').textContent;
    const order = ['1. Test plans cut', '2. Cycles not relevant', '3. Cases not relevant', '4. Not Mandatory', '5. Gaps', '6. AI Notes', 'Check these'];
    const at = order.map(h => text.indexOf(h));
    expect(at.every(i => i >= 0)).toBe(true);
    expect([...at].sort((a, b) => a - b)).toEqual(at);
    expect(text).toContain('PROFINET');
    expect(text).toContain('P1: no PoE ports');
    expect(text).toContain('P2: the model call failed, so the whole plan stays ticked — backend down');
    expect(text).toContain('refused by the guardrail (duplicate)');
    expect($('#zt-status').textContent).toBe('Review the ticks, then Confirm.');
  });

  it('fills the four fields from the analysis', async () => {
    const job = { state: 'done', plans: {}, project: { version: '5.5.6-2', version_source: 'Test Strategy', product: 'IE570', middle: 'Tomahawk', number: '3001' } };
    await analysed(job);
    expect(['#zt-version', '#zt-product', '#zt-middle', '#zt-number'].map(s => $(s).value)).toEqual(['5.5.6-2', 'IE570', 'Tomahawk', '3001']);
    expect($('#zt-version-note').textContent).toBe('from the Test Strategy');
  });
});

describe('the page: what a poll must not undo', () => {
  /** An analysis that keeps answering `analysing` until finish() is called. */
  async function running(final) {
    let finished = false;
    const project = { version: '5.5.6-2', version_source: 'Test Strategy', product: 'IE570', middle: 'Tomahawk', number: '3001' };
    const f = await page({ 'POST /analyse': { id: 'J2' },
      'GET /analyse/J2': () => (finished ? Object.assign({ project }, final) : { state: 'analysing', plans: {}, project }) });
    $('#zt-url').value = 'x';
    $('#zt-url').dispatchEvent(new Event('input', { bubbles: true }));
    await click($('#zt-analyse'));
    await until(() => $('#zt-product').value === 'IE570');
    return { f, finish: () => { finished = true; } };
  }

  it("keeps what the user typed in a field over the analysis's next answers", async () => {
    const { finish } = await running({ state: 'done', plans: {} });
    $('#zt-product').value = 'IE560';
    $('#zt-product').dispatchEvent(new Event('input', { bubbles: true }));
    finish();
    await until(() => !$('#zt-cancel'));
    expect($('#zt-product').value).toBe('IE560');
    expect($('#zt-version').value).toBe('5.5.6-2');
  });

  it("keeps the user's own ticks over the analysis's next answers", async () => {
    const { finish } = await running({ state: 'done', plans: { P2: { state: 'done', deselect: [{ key: 'T3', question: 'Q3', reason: 'r', source: 's' }] } } });
    const box = root.querySelector('input[data-id="P1"]');
    box.checked = false;
    box.dispatchEvent(new Event('change', { bubbles: true }));
    finish();
    await until(() => !$('#zt-cancel'));
    expect($('#zt-tree-count').textContent).toBe('1/2 plans · 2/3 cycles · 1/4 cases ticked');
    expect(root.querySelector('input[data-id="P1"]').checked).toBe(false);
  });
});

describe('the page: API Upload and Write to Zephyr', () => {
  async function previewed(extra = {}) {
    const f = await page(Object.assign({ 'POST /upload/preview': PREVIEW }, extra));
    for (const [s, v] of [['#zt-version', '5.5.6-2'], ['#zt-product', 'IE570']]) {
      $(s).value = v; $(s).dispatchEvent(new Event('input', { bubbles: true }));
    }
    flushSync();
    await click($('#zt-confirm'));
    expect($('#zt-confirm').textContent).toBe('Confirmed ✓');
    expect($('#zt-upload').disabled).toBe(false);
    await click($('#zt-upload'));
    await until(() => $('#zt-upload-result .zt-calls'));
    return f;
  }

  it('lists the calls, the folders in every version, and what is skipped — nothing written yet', async () => {
    const f = await previewed();
    const text = $('#zt-upload-result').textContent;
    expect(text).toContain('nothing is written yet');
    expect(text).toContain('Cycle folder: not found');
    expect(text).toContain('a <b>');
    expect(text).toContain('/5.5.6-1/Tomahawk/Project 3001: IE570 — a different version from What Version (5.5.6-2)');
    expect(text).toContain('Check What Version');
    expect(text).toContain('P9 → IE570: Port (Ask-CK) exists');
    expect(root.querySelector('#zt-upload-result input')).toBe(null);
    const body = f.calls.find(c => c.key === 'POST /upload/preview').body;
    expect(body.product).toBe('IE570');
    expect(body.plans.map(p => p.key)).toEqual(['P1', 'P2']);
  });

  it('offers Write to Zephyr only when nothing stands in the way', async () => {
    await previewed({ 'POST /upload/preview': Object.assign({}, PREVIEW, { problems: ['no folder'] }) });
    expect($('#zt-run')).toBe(null);
    expect($('#zt-upload-result').textContent).toContain('no folder');
  });

  it('a change to the ticks or the fields withdraws the listed calls', async () => {
    await previewed();
    $('#zt-number').value = '9'; $('#zt-number').dispatchEvent(new Event('input', { bubbles: true }));
    flushSync();
    expect($('#zt-upload-result .zt-calls')).toBe(null);
    expect($('#zt-upload').disabled).toBe(true);
  });

  it('asks in a modal with the product and version from the fields, other versions first; Cancel writes nothing', async () => {
    const f = await previewed();
    await click($('#zt-run'));
    const modal = root.querySelector('.zt-confirm');
    expect(modal).not.toBe(null);
    const text = modal.textContent;
    expect(modal.querySelector('.zt-confirm-what').textContent).toBe('IE570 · AW+ 5.5.6-2');
    expect(text).toContain('also has folders under another version — is 5.5.6-2 still right?');
    expect(text).toContain('cycles: /5.5.6-1/Tomahawk/Project 3001: IE570');
    expect(text).toContain('Into /5.5.6-2/Tomahawk/Project 3001: IE570');
    expect(text).toContain('10 writes — 1 skipped, already there');
    await click(modal.querySelector('[data-zt-confirm="no"]'));
    expect(root.querySelector('.zt-confirm')).toBe(null);
    expect(f.calls.some(c => c.key === 'POST /upload/run')).toBe(false);
  });

  it('writes on Write to Zephyr, then shows a stopped upload as stopped, with what was created and nothing undone', async () => {
    const f = await previewed({
      'POST /upload/run': { id: 'R1' },
      'GET /upload/run/R1': { state: 'stopped', steps: [{ msg: 'clone plan: POST /x → 200' }],
        result: { stopped_at: 'P1', error: 'move cycle answered 500', created: [{ kind: 'plan', id: 11, from: 'P1' }], skipped: [] } } });
    await click($('#zt-run'));
    await click(root.querySelector('[data-zt-confirm="yes"]'));
    await until(() => $('#zt-run-result') && $('#zt-run-result').textContent.includes('nothing was undone'));
    const text = $('#zt-run-result').textContent;
    expect(text).toContain('move cycle answered 500');
    expect(text).toContain('plan 11 (from P1)');
    expect([...root.querySelectorAll('#zt-run-result li')].map(l => l.textContent)).toEqual(['clone plan: POST /x → 200']);
    const body = f.calls.find(c => c.key === 'POST /upload/run').body;
    expect([body.confirm_product, body.confirm_version]).toEqual(['IE570', '5.5.6-2']);
    expect($('#zt-status').textContent).toBe('The upload did not complete — see below.');
  });
});
