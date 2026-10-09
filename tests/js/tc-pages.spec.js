// Validation and Test Composer pages (PLAN-test-validation, PLAN-test-composer, PLAN-agent-sessions P1).
// They drive the BUILT islands (current/islands/vd.js, tc.js) against a fake server and a fake seat
// agent. What they pin:
//   * Launch builds the run on the SERVER, then starts it on THIS seat's agent (D7), in campaign mode;
//   * the window shows the stream, denied tools, markers and a not-waited-for question (D5), and
//     relays every event to the server's record;
//   * the results table groups by cycle, marks PyScript / Manual, keeps a re-grade BESIDE the verdict;
//   * Finalize stays disabled and says why (V0 not captured);
//   * the Composer reads a project link's variants, offers templates with runnable counts, filters the
//     live tree to runnable cases, tags Previously Run, and Starts exactly the ticked cases.
import { describe, it, expect, afterEach } from 'vitest';

import { mountVd, flushSync } from '../../ask-ck/frontend/ck-main/current/islands/vd.js';
import { mountTc, byCycle, verdictCounts, parseOutlets, runBody, tokensOf }
  from '../../ask-ck/frontend/ck-main/current/islands/tc.js';
import { deepLink } from '../../ask-ck/frontend/ck-main/current/test-composer/test-composer.js';

let app = null, root = null;
afterEach(() => { if (app) app.destroy(); app = null; if (root) root.remove(); root = null; localStorage.clear(); });

async function until(cond, ms = 3000) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) { flushSync(); if (cond()) return; await new Promise(r => setTimeout(r, 5)); }
  throw new Error('timed out waiting');
}
const $ = (s) => root.querySelector(s);
const $$ = (s) => [...root.querySelectorAll(s)];
const type = (el, v) => { el.value = v; el.dispatchEvent(new Event('input', { bubbles: true })); flushSync(); };
const click = async (el) => { el.click(); flushSync(); await Promise.resolve(); flushSync(); };

function fakeServer(routes) {
  const calls = [];
  const server = async (path, opts = {}) => {
    const key = `${opts.method || 'GET'} ${path.split('?')[0]}`;
    const body = opts.body ? JSON.parse(opts.body) : undefined;
    calls.push({ key, path, body });
    const r = routes[key];
    if (r === undefined) throw new Error('no route ' + key);
    return JSON.parse(JSON.stringify(typeof r === 'function' ? r(body, path) : r));
  };
  return { server, calls };
}

const RID = '2026-10-09T1500-val-ab12';
const EVENTS = [
  { seq: 0, t: 0, kind: 'state', state: 'running' },
  { seq: 1, t: 1, kind: 'text', text: 'Starting triage.' },
  { seq: 2, t: 2, kind: 'tool_use', id: 't1', name: 'Bash', summary: 'precheck', input: 'tools/tb precheck tb470 0-5' },
  { seq: 3, t: 3, kind: 'tool_result', id: 't1', is_error: true, denied: true, excerpt: 'denied by the auto mode classifier' },
  { seq: 4, t: 4, kind: 'question', request_id: 'q4', tool: 'AskUserQuestion', waits: 0, input: { questions: [{ question: 'Which PDU?', options: [{ label: 'A' }] }] } },
  { seq: 5, t: 5, kind: 'marker', marker: 'RESULT', line: 'RESULT AWPTCM-T33234 UNSUPPORTED -- no copper port -- work/run1.log' },
  { seq: 6, t: 6, kind: 'marker', marker: 'NOTIFY', line: 'NOTIFY campaign -- consoles logged in -- left them' },
  { seq: 7, t: 9, kind: 'result', num_turns: 4, duration_ms: 9000, total_cost_usd: 1.25, model_usage: { m: { inputTokens: 1000, outputTokens: 500 } } },
  { seq: 8, t: 10, kind: 'state', state: 'done' },
];

function fakeAgent(events = EVENTS) {
  const calls = [];
  return {
    calls,
    health: async () => ({ agent_version: '1.3.0', sessions: { available: true, sdk_version: '0.2.165', dt_root: '/home/u/claude/device-testing' } }),
    start: async (b) => { calls.push(['start', b]); return { ok: true, session_id: 's1' }; },
    events: async (sid, after) => { calls.push(['events', sid, after]); return after >= events.length ? { state: 'done', events: [], next: after } : { state: 'running', events: events.slice(after), next: events.length }; },
    answer: async (sid, b) => { calls.push(['answer', b]); return { ok: true }; },
    message: async (sid, t) => { calls.push(['message', t]); return { ok: true }; },
    stop: async () => ({ ok: true }),
  };
}

const RECORD = { run_id: RID, state: 'done', started: '2026-10-09T15:00:00+13:00', ended: '2026-10-09T15:09:00+13:00', tokens: 1500, cost_usd: 1.25 };
const TABLE = [{ case: 'AWPTCM-T33234', kind: 'script', cycle: 'AWPTCM-C8470', verdict: 'UNSUPPORTED', reason: 'no copper port', log: 'work/run1.log', regrade: null }];

function vdRoutes(over = {}) {
  return Object.assign({
    'GET /scripts': { scripts: [{ path: '9001_Port/test-9001.33234.py', case_key: 'AWPTCM-T33234', saved_at: '2026-09-23', iterations: 2 }] },
    'POST /runs': (b) => ({ run_id: RID, handoff: { schema: 1, run_id: RID, ...b }, record: {} }),
    [`POST /runs/${RID}/events`]: { ok: true },
    [`GET /runs/${RID}`]: { record: RECORD, table: TABLE, handoff: {} },
    [`GET /runs/${RID}/events`]: { events: EVENTS },
    'GET /runs': { runs: [] },
    [`GET /runs/${RID}/campaign`]: { found: false, files: [] },
  }, over);
}

describe('pure helpers', () => {
  it('groups by cycle, counts verdicts with re-grades, parses outlets, sums tokens', () => {
    const t = [{ case: 'a', cycle: 'C2', verdict: 'FAIL', regrade: { verdict: 'PASS' } }, { case: 'b', cycle: null, verdict: 'PASS' },
               { case: 'c', cycle: 'C1', verdict: 'FAIL' }];
    expect(byCycle(t).map(g => g.cycle)).toEqual(['C2', 'C1', null]);
    expect(verdictCounts(t)).toEqual([{ verdict: 'PASS', n: 2 }, { verdict: 'FAIL', n: 1 }]);
    expect(parseOutlets('u0=1, u1=7,bad=3 u12=40')).toEqual({ u0: 1, u1: 7, u12: 40 });
    expect(runBody('validation', { testbox: ' tb470 ', consoles: 'u0', pduIp: '', email: '' }).pdu).toBe(null);
    expect(tokensOf({ a: { inputTokens: 1, outputTokens: 2, cacheReadInputTokens: 3 } })).toBe(6);
  });

  it('deep links: Finalize\'s composer link, Validation, and a run e-mail by its kind', () => {
    expect(deepLink('?panel=composer&script=9001_Port/test-9001.33234.py')).toEqual(
      { panel: 'panel-tc', island: 'tc', opts: { preselect: '9001_Port/test-9001.33234.py', openRun: null } });
    expect(deepLink('?panel=tc-runs&run=2026-10-09T1500-val-ab12').panel).toBe('panel-vd');
    expect(deepLink('?panel=tc-runs&run=2026-10-09T1500-com-ab12').panel).toBe('panel-tc');
    expect(deepLink('?panel=pt')).toBe(null);
  });
});

describe('Validation', () => {
  async function page(routes = vdRoutes(), agent = fakeAgent()) {
    const f = fakeServer(routes);
    root = document.createElement('div'); document.body.appendChild(root);
    app = mountVd(root, { server: f.server, agent });
    await until(() => $$('.tc-script-row').length && $('.tc-line .tc-small') && /ready/.test($('.tc-line .tc-small').textContent));
    return { f, agent };
  }

  it('launches on the server, then on this seat, and the window shows and relays the stream', async () => {
    const { f, agent } = await page();
    expect($('#vd-launch').disabled).toBe(true);
    $('input[name="vd-script"]').click(); flushSync();
    type($('#tc-testbox'), 'tb470'); type($('#tc-consoles'), 'u0-u5'); type($('#tc-pdu'), '10.36.150.14'); type($('#tc-outlets'), 'u0=1, u1=7');
    await click($('#vd-launch'));
    await until(() => $$('.tc-marker').length === 2);
    const created = f.calls.find(c => c.key === 'POST /runs').body;
    expect(created).toMatchObject({ kind: 'validation', testbox: 'tb470', consoles: 'u0-u5',
      pdu: { ip: '10.36.150.14', outlets: { u0: 1, u1: 7 } },
      cases: [{ key: 'AWPTCM-T33234', kind: 'script', script: '9001_Port/test-9001.33234.py' }] });
    const [, start] = agent.calls.find(c => c[0] === 'start');
    expect(start).toMatchObject({ run_id: RID, mode: 'campaign' });
    expect(start.handoff.run_id).toBe(RID);
    const text = $('.tc-stream').textContent;
    expect(text).toContain('Starting triage.');
    expect($('.tc-tool-status').textContent).toBe('denied');
    expect(text).toContain('Not waited for: the campaign carries on (D5).');
    expect($$('.tc-marker').map(m => m.className)).toEqual(expect.arrayContaining([expect.stringContaining('tc-m-notify')]));
    await until(() => f.calls.some(c => c.key === `POST /runs/${RID}/events`));
    const relayed = f.calls.filter(c => c.key === `POST /runs/${RID}/events`).flatMap(c => c.body.events.map(e => e.seq));
    expect(relayed).toEqual(EVENTS.map(e => e.seq));
    expect(JSON.parse(localStorage.getItem('ck.tc.setup')).testbox).toBe('tb470');
  });

  it('shows results by cycle with the type marker, and Finalize disabled with its reasons', async () => {
    await page();
    $('input[name="vd-script"]').click(); flushSync();
    type($('#tc-testbox'), 'tb470'); type($('#tc-consoles'), 'u0-u5');
    await click($('#vd-launch'));
    await until(() => $('.tc-results'));
    expect($('.tc-cycle').textContent).toBe('Cycle AWPTCM-C8470');
    expect($('.tc-kind').textContent).toBe('PyScript');
    expect($('.tc-readout').textContent).toContain('1 UNSUPPORTED');
    expect($('.tc-readout').textContent).toContain('tokens 1.5k');
    expect($('#vd-finalize').disabled).toBe(true);
    expect($('.tc-blockers').textContent).toContain('not captured yet (V0)');
  });

  it('refuses to launch when the seat agent cannot run sessions, and says why', async () => {
    const agent = fakeAgent();
    agent.health = async () => ({ agent_version: '1.2.0', sessions: { available: false, reason: 'Claude Agent SDK not installed' } });
    const f = fakeServer(vdRoutes());
    root = document.createElement('div'); document.body.appendChild(root);
    app = mountVd(root, { server: f.server, agent });
    await until(() => /SDK not installed/.test(root.textContent));
    $('input[name="vd-script"]').click(); flushSync();
    type($('#tc-testbox'), 'tb470'); type($('#tc-consoles'), 'u0');
    expect($('#vd-launch').disabled).toBe(true);
  });
});

describe('Test Composer', () => {
  const TEMPLATES = [{ name: 'mock-tb470', setup: 'mock-tb470.setup', runnable_scripts: ['AWPTCM-T33234'], manual_cases: ['AWPTCM-T2'], runnable_count: 2, note: null },
                     { name: 'setup-a', setup: 'a.setup', runnable_scripts: [], manual_cases: [], runnable_count: 0, note: 'empty template' }];
  const TREE = { plans: [{ key: 'AWPTCM-P3266', name: 'Industrial Features', cycles: [{ key: 'AWPTCM-C8470', name: 'IF', cases: [
    { key: 'AWPTCM-T33234', name: 'MDI' }, { key: 'AWPTCM-T2', name: 'manual one' }, { key: 'AWPTCM-T3', name: 'not on this template' }] }] }] };
  const WIKI = { title: 'Project:3171 AT-x230-V2', variants: [
    { version: '5.5.5-2', project: '3171', status: 'Passed', title: 'x230-28GTv2 + others', plans: [{ key: 'AWPTCM-P2901', name: 'x230-28GPv2' }] },
    { version: '5.5.5-2', project: '3171-V2', status: 'Tested', title: 'x230-52GP V2 + others', plans: [{ key: 'AWPTCM-P2903', name: 'x230-52GT V2' }] }] };
  const PREV = '2026-10-08T1000-com-aaaa';
  const OTHER = '2026-09-01T1000-com-cccc';      // another release version: must not tag

  function tcRoutes() {
    return {
      'GET /projects': { projects: [{ id: 'IE570|5.5.6-2|3001', product: 'IE570', version: '5.5.6-2', number: '3001', plans: ['AWPTCM-P3266'] }] },
      'GET /scripts': { scripts: [{ path: '9001_Port/test-9001.33234.py', case_key: 'AWPTCM-T33234' }] },
      'GET /templates': { templates: TEMPLATES },
      'POST /projects/from-wiki': WIKI,
      'GET /projects/tree': TREE,
      'GET /runs': (b, path) => ({ runs: path.includes('kind=composer') ? [{ run_id: PREV }, { run_id: OTHER }] : [] }),
      [`GET /runs/${OTHER}`]: { record: {}, handoff: { project: { version: '9.9.9-1' } }, table: [{ case: 'AWPTCM-T33234', verdict: 'PASS' }] },
      [`GET /runs/${PREV}`]: { record: {}, handoff: { project: { version: '5.5.6-2' } }, table: [{ case: 'AWPTCM-T2', verdict: 'PASS' }] },
      'POST /runs': (b) => ({ run_id: '2026-10-09T1600-com-bbbb', handoff: { schema: 1, run_id: '2026-10-09T1600-com-bbbb', ...b }, record: {} }),
      'POST /runs/2026-10-09T1600-com-bbbb/events': { ok: true },
      'GET /runs/2026-10-09T1600-com-bbbb': { record: RECORD, table: TABLE, handoff: {} },
      'GET /runs/2026-10-09T1600-com-bbbb/events': { events: [] },
    };
  }

  async function page() {
    const f = fakeServer(tcRoutes());
    const agent = fakeAgent();
    root = document.createElement('div'); document.body.appendChild(root);
    app = mountTc(root, { server: f.server, agent });
    await until(() => $$('#tc-template option').length === 3 && $$('#tc-project option').length === 2);
    return { f, agent };
  }

  it('reads a project link into a variant checklist with each variant\'s status and plans', async () => {
    await page();
    $$('input[type="radio"]')[1].click(); flushSync();
    type($('#tc-wiki'), 'https://wiki/Project:3171_AT-x230-V2');
    await click([...root.querySelectorAll('button')].find(b => b.textContent.includes('Read Test Results')));
    await until(() => $$('.tc-variant').length === 2);
    expect($$('.tc-variant')[1].textContent).toContain('Tested');
    expect($$('.tc-variant')[1].textContent).toContain('AWPTCM-P2903 x230-52GT V2');
    expect($('.tc-status').textContent).toContain('tick the ones this run is for');
  });

  it('filters the live tree to runnable cases, tags Previously Run, and Starts exactly the ticked cases', async () => {
    const { f, agent } = await page();
    const sel = $('#tc-project'); sel.value = 'IE570|5.5.6-2|3001'; sel.dispatchEvent(new Event('change')); flushSync();
    const tp = $('#tc-template'); tp.value = 'mock-tb470'; tp.dispatchEvent(new Event('change')); flushSync();
    expect(root.textContent).toContain('1 script case(s) and 1 manual case(s) can run on mock-tb470.setup');
    type($('#tc-testbox'), 'tb470'); type($('#tc-consoles'), 'u0-u5');
    await click($('#tc-load-tree'));
    await until(() => $$('.tc-tree .zt-case').length === 2 && root.querySelector('.tc-prev'));
    const rows = $$('.tc-tree .zt-case').map(r => r.textContent.replace(/\s+/g, ' ').trim());
    expect(rows[0]).toContain('AWPTCM-T33234 MDI PyScript');
    expect(rows[0]).not.toContain('Previously Run');            // its earlier PASS was another version
    expect(rows[1]).toContain('AWPTCM-T2 manual one Manual Previously Run');
    expect($('#tc-start').textContent).toBe('Start (2)');
    await click($('#tc-start'));
    await until(() => agent.calls.some(c => c[0] === 'start'));
    const body = f.calls.find(c => c.key === 'POST /runs').body;
    expect(body.kind).toBe('composer');
    expect(body.template).toBe('mock-tb470');
    expect(body.cases).toEqual([{ key: 'AWPTCM-T33234', kind: 'script', script: '9001_Port/test-9001.33234.py', cycle: 'AWPTCM-C8470' },
                                { key: 'AWPTCM-T2', kind: 'manual', cycle: 'AWPTCM-C8470' }]);
    expect(body.project).toMatchObject({ product: 'IE570', version: '5.5.6-2', plans: ['AWPTCM-P3266'] });
  });

  it('Validate launches a composer-validate run against the chosen template', async () => {
    const { f, agent } = await page();
    const tp = $('#tc-template'); tp.value = 'setup-a'; tp.dispatchEvent(new Event('change')); flushSync();
    type($('#tc-testbox'), 'tb470'); type($('#tc-consoles'), 'u0-u5');
    await click($('#tc-validate'));
    await until(() => agent.calls.some(c => c[0] === 'start'));
    expect(f.calls.find(c => c.key === 'POST /runs').body).toMatchObject({ kind: 'composer-validate', template: 'setup-a', cases: [] });
    expect(root.textContent).toContain('empty template');
  });
});
