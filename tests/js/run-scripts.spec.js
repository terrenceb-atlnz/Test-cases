// Run Scripts (ask-ck/plans/PLAN-run-scripts.md R2–R4). Drives the BUILT island (current/islands/tc.js,
// mountRs) against a fake server and a fake seat agent, as tc-pages.spec.js does. What it pins:
//   * the list is one source's validated scripts (the server is asked for validated=true), grouped,
//     filterable; the ck.db sources show "not yet"; the run order is the order ticked;
//   * Launch builds a `scripts` run on the SERVER with the scripts in that order, then starts it on
//     THIS seat's agent in campaign mode; a start time stores it scheduled and never starts it here;
//   * a share link fills the page (link fields over the seat's), never launches, never overwrites the
//     seat's remembered answers, reports a missing script, and never carries the email (R-D4);
//   * Run again refills the page from a finished run's hand-off and rebuilds the same body.
import { describe, it, expect, afterEach } from 'vitest';

import { mountRs, flushSync, scriptsLink } from '../../ask-ck/frontend/ck-main/current/islands/tc.js';
import { deepLink } from '../../ask-ck/frontend/ck-main/current/test-composer/test-composer.js';

let app = null, root = null;
afterEach(() => { if (app) app.destroy(); app = null; if (root) root.remove(); root = null; localStorage.clear(); });

async function until(cond, ms = 3000) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) { flushSync(); if (cond()) return; await new Promise(r => setTimeout(r, 5)); }
  throw new Error('timed out waiting');
}
const settle = async () => { for (let i = 0; i < 10; i++) { flushSync(); await new Promise(r => setTimeout(r, 5)); } };
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

const SID = '2026-10-16T1000-scr-ab12';
const A = '9001_Port/test-9001.33235.py', B = '9001_Port/test-9001.33236.py', L = '1234_Lag/test-1234.4321.py';
const SCRIPTS = [
  { path: L, group: '1234_Lag', case_key: 'AWPTCM-T4321', finalized_at: '2026-10-15T01:00:00+00:00' },
  { path: A, group: '9001_Port', case_key: 'AWPTCM-T33235', finalized_at: '2026-10-16T01:00:00+00:00' },
  { path: B, group: '9001_Port', case_key: 'AWPTCM-T33236', finalized_at: '2026-10-16T02:00:00+00:00' },
];
const NOT_YET = 'not yet: running scripts from ck.db is not built (PLAN-run-scripts §4)';
const SOURCES = [{ id: 'generated', label: 'Generated', enabled: true, reason: null },
  { id: 'art', label: 'ART', enabled: false, reason: NOT_YET },
  { id: 'legacy', label: 'Legacy', enabled: false, reason: NOT_YET },
  { id: 'svt', label: 'SVT', enabled: false, reason: NOT_YET }];
const EVENTS = [
  { seq: 0, t: 0, kind: 'state', state: 'running' },
  { seq: 1, t: 1, kind: 'text', text: 'Starting triage.' },
  { seq: 2, t: 2, kind: 'state', state: 'done' },
];
const HANDOFF = { schema: 1, run_id: SID, kind: 'scripts', source: 'generated', testbox: 'tb470', consoles: 'u0-u5 (u0 = DUT)',
  pdu: { ip: '10.36.150.14', outlets: { u0: 1, u1: 7 } }, constraints: 'no reloads before 17:00',
  cases: [{ key: 'AWPTCM-T33236', kind: 'script', path: B }, { key: 'AWPTCM-T33235', kind: 'script', path: A }],
  options: { email: 'someone.else@alliedtelesis.co.nz', start_after: null } };

function routes(over = {}) {
  return Object.assign({
    'GET /scripts': (_b, path) => {
      const src = new URLSearchParams(path.split('?')[1]).get('source');
      const s = SOURCES.find(x => x.id === src);
      return { source: src, enabled: s.enabled, reason: s.reason, scripts: s.enabled ? SCRIPTS : [], sources: SOURCES };
    },
    'POST /runs': (b) => ({ run_id: SID, handoff: { ...b, schema: 1, run_id: SID,
      start_at: b.options.start_after ? '2026-10-16T18:00:00+13:00' : null }, record: {} }),
    [`POST /runs/${SID}/events`]: { ok: true },
    [`GET /runs/${SID}`]: { record: { run_id: SID, state: 'done' }, table: [], handoff: HANDOFF },
    [`GET /runs/${SID}/events`]: { events: EVENTS },
    [`GET /runs/${SID}/campaign`]: { found: false, files: [] },
    'GET /runs': { runs: [] },
  }, over);
}

function fakeAgent(events = EVENTS) {
  const calls = [];
  return {
    calls,
    health: async () => ({ agent_version: '1.3.5', sessions: { available: true, sdk_version: '0.2.165', dt_root: '/home/u/claude/device-testing' } }),
    start: async (b) => { calls.push(['start', b]); return { ok: true, session_id: 's1' }; },
    events: async (sid, after) => { calls.push(['events', sid, after]); return after >= events.length ? { state: 'done', events: [], next: after } : { state: 'running', events: events.slice(after), next: events.length }; },
    sessions: async () => ({ sessions: [] }),
    answer: async () => ({ ok: true }), message: async () => ({ ok: true }), stop: async () => ({ ok: true }),
  };
}

async function page(opts = {}, r = routes(), agent = fakeAgent()) {
  const f = fakeServer(r);
  root = document.createElement('div'); document.body.appendChild(root);
  app = mountRs(root, { server: f.server, agent, ...opts });
  await until(() => $$('input[name="rs-source"]').length && /ready/.test(root.textContent));
  return { f, agent };
}
const rowFor = (p) => $(`input[name="rs-script"][value="${p}"]`);
const orderShown = () => $$('.rs-order li').map(li => li.textContent.replace(/\s+/g, ' ').trim());
const fill = () => { type($('#tc-testbox'), 'tb470'); type($('#tc-consoles'), 'u0-u5'); };

describe('Run Scripts', () => {
  it('lists one source\'s validated scripts, grouped and filterable, and runs them in the order ticked', async () => {
    const { f, agent } = await page();
    await until(() => $$('input[name="rs-script"]').length === 3);
    expect(f.calls.find(c => c.key === 'GET /scripts').path).toBe('/scripts?source=generated&validated=true');
    expect($$('.rs-group').map(g => g.textContent)).toEqual(['1234_Lag', '9001_Port']);
    const radios = $$('input[name="rs-source"]');
    expect(radios.map(r => [r.value, r.disabled, r.checked])).toEqual(
      [['generated', false, true], ['art', true, false], ['legacy', true, false], ['svt', true, false]]);
    expect(radios[1].parentNode.textContent).toContain('ART (not yet)');

    type($('#rs-filter'), '33236');
    expect($$('input[name="rs-script"]').map(i => i.value)).toEqual([B]);
    type($('#rs-filter'), '');

    for (const p of [B, L, A]) await click(rowFor(p));
    expect(orderShown()).toEqual([`AWPTCM-T33236 ${B}`, `AWPTCM-T4321 ${L}`, `AWPTCM-T33235 ${A}`]);
    await click(rowFor(L));                                   // unticking drops it from the order
    expect(orderShown()).toEqual([`AWPTCM-T33236 ${B}`, `AWPTCM-T33235 ${A}`]);

    expect($('#rs-launch').disabled).toBe(true);              // no bench yet
    fill();
    await click($('#rs-launch'));
    await until(() => agent.calls.some(c => c[0] === 'start'));
    const created = f.calls.find(c => c.key === 'POST /runs').body;
    expect(created).toMatchObject({ kind: 'scripts', source: 'generated', testbox: 'tb470', consoles: 'u0-u5',
      options: { start_after: null } });
    expect(created.cases).toEqual([{ key: 'AWPTCM-T33236', kind: 'script', script: B }, { key: 'AWPTCM-T33235', kind: 'script', script: A }]);
    const [, start] = agent.calls.find(c => c[0] === 'start');
    expect(start).toMatchObject({ run_id: SID, mode: 'campaign' });
    await until(() => /Starting triage\./.test(root.textContent));
    await until(() => f.calls.some(c => c.key === `POST /runs/${SID}/events`));
    expect(f.calls.some(c => c.path.startsWith('/runs?kind=scripts'))).toBe(true);
  });

  it('says how a script gets onto the list when the source has none', async () => {
    const r = routes({ 'GET /scripts': { source: 'generated', enabled: true, reason: null, scripts: [], sources: SOURCES } });
    await page({}, r);
    await until(() => $('.rs-empty'));
    expect($('.rs-empty').textContent).toContain('once Validation has finalized it');
    expect($('#rs-launch').disabled).toBe(true);
  });

  it('a start time stores the run scheduled and never starts it on this seat', async () => {
    const { f, agent } = await page();
    await until(() => $$('input[name="rs-script"]').length === 3);
    await click(rowFor(A)); fill();
    type($('#rs-start'), '18:00');
    expect($('#rs-launch').textContent).toContain('Schedule (1)');
    await click($('#rs-launch'));
    await until(() => /Scheduled/.test($('.tc-status').textContent));
    expect(f.calls.find(c => c.key === 'POST /runs').body.options.start_after).toBe('18:00');
    expect(agent.calls.some(c => c[0] === 'start')).toBe(false);
    expect($('.tc-status').textContent).toContain('2026-10-16T18:00:00+13:00');
  });

  it('a share link fills the page, never launches, reports a missing script and never carries the email', async () => {
    localStorage.setItem('ck.tc.setup', JSON.stringify({ testbox: 'tb100', consoles: 'u9', email: 'me@alliedtelesis.co.nz' }));
    const href = `http://ck.example:8000/restyle/?panel=run-scripts&source=generated&scripts=${encodeURIComponent([B, '9001_Port/gone.py', A].join(','))}`
      + '&testbox=tb470&consoles=u0-u5&pdu=10.36.150.14&outlets=u0%3D1&constraints=no+reloads&start=18:00';
    const d = deepLink(new URL(href).search);
    expect(d.panel).toBe('panel-rs');
    expect(d.opts.link.setup.email).toBeUndefined();
    const { f, agent } = await page(d.opts);
    await until(() => orderShown().length === 2);
    expect(orderShown()).toEqual([`AWPTCM-T33236 ${B}`, `AWPTCM-T33235 ${A}`]);
    expect($$('.rs-missing').map(m => m.textContent)).toEqual(['not available: 9001_Port/gone.py']);
    expect([$('#tc-testbox').value, $('#tc-consoles').value, $('#tc-pdu').value, $('#tc-outlets').value, $('#tc-constraints').value])
      .toEqual(['tb470', 'u0-u5', '10.36.150.14', 'u0=1', 'no reloads']);
    expect($('#tc-email').value).toBe('me@alliedtelesis.co.nz');         // this seat's own
    expect($('#rs-start').value).toBe('18:00');
    await settle();
    expect(f.calls.some(c => c.key === 'POST /runs')).toBe(false);
    expect(agent.calls.some(c => c[0] === 'start')).toBe(false);
    expect(JSON.parse(localStorage.getItem('ck.tc.setup')).testbox).toBe('tb100');   // not until Launch

    await click($('#rs-link'));
    await until(() => $('#rs-shared'));
    const link = $('#rs-shared').value;
    expect(link).not.toContain('email');
    expect(link).not.toContain('me%40alliedtelesis');
    expect(link.startsWith('http://localhost')).toBe(true);
    const back = deepLink(new URL(link).search).opts.link;
    expect(back).toEqual({ source: 'generated', scripts: [B, A], start: '18:00',
      setup: { testbox: 'tb470', consoles: 'u0-u5', pduIp: '10.36.150.14', outlets: 'u0=1', constraints: 'no reloads' } });
  });

  it('the link builder writes only the settings, in run order, and drops the page\'s own query', () => {
    const u = scriptsLink('http://h:8000/?panel=composer&run=x#frag', { source: 'generated', scripts: [B, A],
      setup: { testbox: 'tb470', consoles: '', pduIp: '', outlets: '', constraints: '', email: 'me@x.co' }, start: '' });
    expect(u).toBe(`http://h:8000/?panel=run-scripts&source=generated&scripts=${encodeURIComponent(`${B},${A}`)}&testbox=tb470`);
  });

  it('Run again refills the page from a finished run and rebuilds the same body, with this seat\'s email', async () => {
    localStorage.setItem('ck.tc.setup', JSON.stringify({ testbox: 'tb100', consoles: 'u9', email: 'me@alliedtelesis.co.nz' }));
    const { f, agent } = await page({ openRun: SID });
    await until(() => $('#rs-again') && !$('#rs-again').disabled);
    await click($('#rs-again'));
    await until(() => orderShown().length === 2);
    expect(orderShown()).toEqual([`AWPTCM-T33236 ${B}`, `AWPTCM-T33235 ${A}`]);
    expect([$('#tc-testbox').value, $('#tc-consoles').value, $('#tc-pdu').value, $('#tc-outlets').value, $('#tc-constraints').value])
      .toEqual(['tb470', 'u0-u5 (u0 = DUT)', '10.36.150.14', 'u0=1, u1=7', 'no reloads before 17:00']);
    expect($('#tc-email').value).toBe('me@alliedtelesis.co.nz');
    await click($('#rs-launch'));
    await until(() => agent.calls.some(c => c[0] === 'start'));
    const again = f.calls.find(c => c.key === 'POST /runs').body;
    expect(again).toMatchObject({ kind: 'scripts', source: HANDOFF.source, testbox: HANDOFF.testbox, consoles: HANDOFF.consoles,
      pdu: HANDOFF.pdu, constraints: HANDOFF.constraints, options: { email: 'me@alliedtelesis.co.nz', start_after: null } });
    expect(again.cases.map(c => c.script)).toEqual(HANDOFF.cases.map(c => c.path));
  });

  it('a run e-mail for a scripts run opens Run Scripts', () => {
    expect(deepLink(`?panel=tc-runs&run=${SID}`)).toEqual({ panel: 'panel-rs', island: 'rs', opts: { openRun: SID } });
    expect(deepLink('?panel=run-scripts').opts.link).toEqual({ source: 'generated', scripts: [], setup: {}, start: null });
  });
});
