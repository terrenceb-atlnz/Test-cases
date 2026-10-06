// Zephyr Templating Tool page (PLAN-zephyr-templating.md §5a; docs/zephyr.txt "UI").
// What these pin: the tree starts fully ticked and only the analysis's PROPOSALS untick it;
// unticking a parent unticks everything below it, ticking a child re-ticks its parents; the upload
// body lists every template cycle of a ticked plan (an unticked one must still be unlinked) and
// each kept cycle's unticked cases; and the Results Analysis column is the questions in order,
// with failed calls and refused proposals shown rather than hidden.
import { describe, it, expect } from 'vitest';

import '../../ask-ck/frontend/ck-main/current/shared/actions.js';
import { treeRows, applyProposals, setTick, uploadSelection, renderTree, renderAnalysis, renderUpload,
  renderConfirm, renderRun, isOpen, cleanField } from '../../ask-ck/frontend/ck-main/current/zephyr-tool/zephyr-tool.js';

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

describe('folding the tree', () => {
  // Terrence 2026-10-07: "default-collapsed, unless a change has been made within them by the LLM analysis".
  const keys = (html) => [...html.matchAll(/class="zt-key">([^<]+)</g)].map(m => m[1]);

  it('starts with only the plans showing when the analysis changed nothing', () => {
    const html = renderTree(TREE, new Set(treeRows(TREE).map(r => r.id)), new Map());
    expect(keys(html)).toEqual(['P1', 'P2']);
    expect(html).toContain('2 case(s)');
  });

  it('opens the plan and cycle the analysis unticked something in — and only those', () => {
    const job = { plans: { P2: { deselect: [{ key: 'T3', question: 'Q3', reason: 'r', source: 's' }] } } };
    const { ticked, ai } = applyProposals(TREE, job);
    const html = renderTree(TREE, ticked, ai);
    expect(keys(html)).toEqual(['P1', 'P2', 'C2', 'T3', 'T1', 'C3']);
    expect(html).toContain('1 unticked');
  });

  it('keeps a plan cut by the analysis itself collapsed — its reason is on its own row', () => {
    const job = { plans: { P1: { deselect: [{ key: 'P1', question: 'Q1', reason: 'not in scope', source: 'Strategy' }] } } };
    const { ticked, ai } = applyProposals(TREE, job);
    expect(isOpen('P1', ai, new Map())).toBe(false);
    expect(renderTree(TREE, ticked, ai)).toContain('not in scope');
  });

  it("the user's own fold wins either way", () => {
    const job = { plans: { P2: { deselect: [{ key: 'T3', question: 'Q3', reason: 'r', source: 's' }] } } };
    const { ticked, ai } = applyProposals(TREE, job);
    const folds = new Map([['P2', false], ['P1', true]]);
    expect(keys(renderTree(TREE, ticked, ai, folds))).toEqual(['P1', 'C1', 'P2']);
  });
});

describe('rendering', () => {
  it('escapes names and shows the AI reason on the row it unticked', () => {
    const tree = { plans: [{ key: 'P9', name: '<b>x</b>', cycles: [] }] };
    const html = renderTree(tree, new Set(), new Map([['P9', { question: 'Q1', reason: 'out of scope', source: 'Strategy §4' }]]));
    expect(html).toContain('&lt;b&gt;x&lt;/b&gt;');
    expect(html).toContain('is-off');
    expect(html).toContain('out of scope');
  });

  it('lays Results Analysis out as the questions, then gaps and AI Notes, and shows what went wrong', () => {
    const job = { state: 'done', wiki_problems: ['the TPS has no SID table'], plans: {
      P1: { state: 'done', deselect: [{ key: 'T1', question: 'Q4', reason: 'no PoE', source: 'TPS §11.4' }],
            notes: [{ key: null, note: 'no PoE ports' }], dropped: [{ why: 'duplicate' }] },
      P2: { state: 'error', error: 'backend down', deselect: [], notes: [], dropped: [] } },
      gaps: { state: 'done', gaps: [{ requirement: 'PROFINET', source: 'Strategy §3.3' }], notes: [{ note: 'stacks 4' }], dropped: [] } };
    const html = renderAnalysis(job, TREE);
    const order = ['1. Test plans cut', '2. Cycles not relevant', '3. Cases not relevant', '4. Not Mandatory', '5. Gaps', '6. AI Notes', 'Check these'];
    const at = order.map(h => html.indexOf(h));
    expect(at.every(i => i >= 0)).toBe(true);
    expect([...at].sort((a, b) => a - b)).toEqual(at);
    expect(html).toContain('PROFINET');
    expect(html).toContain('P1: no PoE ports');
    expect(html).toContain('P2: the model call failed, so the whole plan stays ticked — backend down');
    expect(html).toContain('refused by the guardrail (duplicate)');
  });

  const SEL = { version: '5.5.6-2', product: 'IE570', plans: [] };
  const PREVIEW = {
    targets: { testplan: { path: '/5.5.6-2/Tomahawk/Project 3001: IE570' }, testrun: { path: null } },
    counts: { plans: 1, cycles: 1, calls: 2, skipped: 1 }, problems: [],
    project_folders: [{ kind: 'testplan', path: '/5.5.6-2/Tomahawk/Project 3001: IE570', version: '5.5.6-2' },
                      { kind: 'testrun', path: '/5.5.6-1/Tomahawk/Project 3001: IE570', version: '5.5.6-1' }],
    duplicates: [{ key: 'P9', name: 'IE570: Port (Ask-CK)' }],
    calls: [{ n: 1, op: 'clone plan', method: 'POST', path: '/x', known: true, about: 'a <b>' },
            { n: 2, op: 'rename', method: 'PUT', path: '/y', known: true, about: 'b' }] };

  it('lists the calls, the folders in every version, and what is skipped — nothing written yet', () => {
    const html = renderUpload(PREVIEW, SEL);
    expect(html).toContain('nothing is written yet');
    expect(html).toContain('Cycle folder: not found');
    expect(html).toContain('a &lt;b&gt;');
    expect(html).toContain('/5.5.6-1/Tomahawk/Project 3001: IE570 — a different version from What Version (5.5.6-2)');
    expect(html).toContain('Check What Version');
    expect(html).toContain('P9</span> → IE570: Port (Ask-CK) exists');
  });

  it('offers Write to Zephyr only when nothing stands in the way — no typing on the page', () => {
    expect(renderUpload(PREVIEW, SEL)).toContain('id="zt-run"');
    expect(renderUpload(PREVIEW, SEL)).not.toContain('<input');
    expect(renderUpload(Object.assign({}, PREVIEW, { problems: ['no folder'] }), SEL)).not.toContain('zt-run');
    expect(renderUpload(Object.assign({}, PREVIEW, { calls: [] }), SEL)).not.toContain('zt-run');
  });

  it('confirms in a modal showing the product and version from the fields, and other versions first', () => {
    const html = renderConfirm(PREVIEW, SEL);
    expect(html).toContain('<b>IE570</b> · AW+ <b>5.5.6-2</b>');
    expect(html).toContain('also has folders under another version — is 5.5.6-2 still right?');
    expect(html).toContain('cycles: /5.5.6-1/Tomahawk/Project 3001: IE570');
    expect(html).toContain('Into /5.5.6-2/Tomahawk/Project 3001: IE570');
    expect(html).toContain('1 skipped, already there');
    expect(html).toContain('data-zt-confirm="no"');
    expect(html).toContain('data-zt-confirm="yes"');
    const same = Object.assign({}, PREVIEW, { project_folders: PREVIEW.project_folders.slice(0, 1) });
    expect(renderConfirm(same, SEL)).not.toContain('another version');
  });

  it('shows a stopped upload as stopped, with what was created and nothing undone', () => {
    const html = renderRun({ state: 'stopped', steps: [{ msg: 'clone plan: POST /x → 200' }],
      result: { stopped_at: 'P1', error: 'move cycle answered 500', created: [{ kind: 'plan', id: 11, from: 'P1' }], skipped: [] } });
    expect(html).toContain('nothing was undone');
    expect(html).toContain('move cycle answered 500');
    expect(html).toContain('plan 11 (from P1)');
    expect(html).toContain('<li>clone plan: POST /x → 200</li>');
    expect(renderRun({ state: 'refused', steps: [], result: { error: 'typed version differs' } })).toContain('nothing was written');
  });
});

describe('the project fields', () => {
  it('treats blank, N/A, None and - as not set, and trims the rest', () => {
    for (const v of ['', '  ', 'N/A', 'n/a', 'NA', 'None', 'none', '-', null, undefined]) expect(cleanField(v)).toBe(null);
    expect(cleanField(' Tomahawk ')).toBe('Tomahawk');
    expect(cleanField('3001')).toBe('3001');
  });
});

