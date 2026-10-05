// Zephyr Templating Tool page (PLAN-zephyr-templating.md §5a; docs/zephyr.txt "UI").
// What these pin: the tree starts fully ticked and only the analysis's PROPOSALS untick it;
// unticking a parent unticks everything below it, ticking a child re-ticks its parents; the upload
// body lists every template cycle of a ticked plan (an unticked one must still be unlinked) and
// each kept cycle's unticked cases; and the Results Analysis column is the questions in order,
// with failed calls and refused proposals shown rather than hidden.
import { describe, it, expect } from 'vitest';

import '../../ask-ck/frontend/ck-main/current/shared/actions.js';
import { treeRows, applyProposals, setTick, uploadSelection, renderTree, renderAnalysis, renderUpload }
  from '../../ask-ck/frontend/ck-main/current/zephyr-tool/zephyr-tool.js';

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

  it('marks the not-yet-captured calls in the dry run', () => {
    const html = renderUpload({ targets: { testplan: { path: '/5.5.6-2/Tomahawk/Project 3001: IE570' }, testrun: { path: null } },
      counts: { calls: 2, writes_not_captured: 1 }, problems: [],
      calls: [{ n: 1, op: 'clone plan', method: 'POST', path: '/x', known: false, about: 'a' },
              { n: 2, op: 'rename', method: 'PUT', path: '/y', known: true, about: 'b' }] });
    expect(html).toContain('dry run (nothing was written)');
    expect(html).toContain('Cycle folder: not found');
    expect((html.match(/zt-unknown/g) || []).length).toBe(1);
  });
});
