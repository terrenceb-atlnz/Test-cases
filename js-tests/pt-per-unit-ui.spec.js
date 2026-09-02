// Per-unit generation in the UI (PLAN-pytest-creator.md §9.5, 2026-09-02).
//
// Driven for real in jsdom: actions.js's click dispatcher, pytest.js's handlers, fetch
// stubbed and resolvable by hand. Source-level assertions cannot show that 30 units are
// dispatched CONCURRENTLY rather than in a loop, and that is the whole point of the change.
//
// Four properties are load-bearing:
//
//   1. "Generate all" dispatches every unit BEFORE any of them resolves. A `for … await`
//      loop passes every source-level check and defeats the entire design — that is
//      exactly what ptSuggestAllSteps still does on step 3.
//   2. One failure must not abandon the other results (allSettled, not all).
//   3. A failure NEVER blocks. window.alert freezes the event loop, so a blocking dialog
//      during a fan-out queues every other unit's result behind it, and 29 sequential
//      alerts cannot be dismissed faster than they arrive.
//   4. The button sends the EDITED prompt — including an edit made on a page since
//      navigated away from, which is why prompts live in JS state and not in 30 textareas.
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import '../ask-ck/CK-main/CK_server/static/js/actions.js';
import { S } from '../ask-ck/CK-main/CK_server/static/js/state.js';
import { ptLoadCase, renderPtGenPanel } from '../ask-ck/CK-main/CK_server/static/js/pytest.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const JS = readFileSync(resolve(HERE, '../ask-ck/CK-main/CK_server/static/js/pytest.js'), 'utf8')
  .replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');

const DOM = `
  <div id="nav-pt"></div>
  <div id="panel-pt-seq"><div id="pt-seq-case"></div><div id="pt-seq-refined"></div>
    <div id="pt-seq-list"></div><span id="pt-seq-status"></span><div id="pt-seq-prov"></div></div>
  <span id="pt-load-status"></span>
  <button id="pt-units-all-btn" data-action="ptGenerateAllUnits" class="btn">Generate all units (LLM)</button>
  <button id="pt-units-reload-btn" data-action="ptLoadUnits" class="btn">reload</button>
  <span id="pt-units-status"></span>
  <div id="pt-unit-pills"></div>
  <div id="pt-unit-errors"></div>
  <div id="pt-unit-page"></div>
  <div id="pt-summary-page" class="hidden">
    <input id="pt-gen-group" value="Management"><input id="pt-gen-name" value="x_test">
    <span id="pt-gen-path"></span><span id="pt-gen-status"></span>
    <div id="pt-lint-result"></div><div id="pt-review-result"></div>
    <textarea id="pt-gen-code"></textarea>
    <div id="pt-gen-lib-wrap" class="hidden"><span id="pt-gen-lib-name"></span>
      <textarea id="pt-gen-lib-code"></textarea></div>
    <div id="pt-gen-prov"></div>
    <button id="pt-assemble-btn" data-action="ptAssembleScript" class="btn">Assemble + check</button>
  </div>`;

const UNITS = [
  { id: 'setup', kind: 'setup', tc_n: null, label: 'TestSet.configure / tear_down',
    source_n: null, action: '', verify: '', blank_block: 'x', prompt: 'P-setup',
    edited: false, code: '', status: 'pending', error: '', at: '' },
  { id: 'tc1', kind: 'testcase', tc_n: 1, label: 'TestCase_1', source_n: 3,
    action: 'select a TLV', verify: 'it shows as selected', blank_block: 'x',
    prompt: 'P-1', edited: false, code: '', status: 'pending', error: '', at: '' },
  { id: 'tc2', kind: 'testcase', tc_n: 2, label: 'TestCase_2', source_n: 4,
    action: 'clear a TLV', verify: 'it shows as cleared', blank_block: 'x',
    prompt: 'P-2', edited: false, code: '', status: 'pending', error: '', at: '' },
];

let sent;          // unitId -> {id, prompt} actually posted
let dispatched;    // ids the batch endpoint accepted
let statusMap;     // what /units_status returns next

// The poll is what advances a pill now, so a test "resolves" a unit by writing its
// outcome into the status map and letting one poll tick run.
function land(id, ok = true, why = 'boom') {
  statusMap[id] = ok
    ? { status: 'ok', error: '', at: '2026-09-02T00:00:00Z', chars: 20 }
    : { status: 'error', error: why, at: '2026-09-02T00:00:00Z', chars: 0 };
}
function markRunning(ids) {
  ids.forEach(id => { statusMap[id] = { status: 'pending', error: '', at: '', chars: 0,
                                        running: true }; });
}
const SESSION = { step2: { sequence: [{ n: 3, action: 'a' }, { n: 4, action: 'b' }] }, step6: {} };

const reply = (body, ok = true, status = 200) => ({ ok, status, json: async () => body });

beforeEach(async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  document.body.innerHTML = DOM;
  sent = {}; dispatched = []; statusMap = {};
  S.ptCase = { key: 'AWPTCM-T1' };
  window.alert = vi.fn();
  global.fetch = vi.fn(async (url, opts) => {
    const u = String(url);
    if (u.includes('/load_case/')) {
      return reply({ session: SESSION, case_title: 't', group_display: 'g', objective: 'o',
                     steps: [], read_only: false, lock: null });
    }
    if (u.includes('/session/')) return reply({ session: SESSION });
    if (u.includes('/step_prompts/')) {
      return reply({ units: UNITS.map(x => {
        const st = statusMap[x.id];
        if (!st || st.running) return { ...x };
        return { ...x, status: st.status, error: st.error || '',
                 code: st.status === 'ok' ? `class X_${x.id}: pass` : '', at: st.at || '' };
      }) });
    }
    if (u.includes('/generate_units/')) {
      // ONE request for the whole fan-out, answered immediately — the deadlock fix.
      const body = JSON.parse(opts.body || '{}');
      (body.units || []).forEach(x => { sent[x.id] = x; });
      dispatched = (body.units || []).map(x => x.id);
      return reply({ dispatched, already_running: [], max_concurrent: 8 });
    }
    if (u.includes('/units_status/')) {
      return reply({ units: statusMap, running: Object.keys(statusMap)
                       .filter(k => statusMap[k].running) });
    }
    if (u.includes('/assemble_script/')) {
      return reply({ files: { test: { name: 'x.py', code: 'code' } },
                     lint: { ok: true, errors: [], warnings: [] },
                     manifest: { ok: true }, units: 3 });
    }
    return reply({});
  });
  await ptLoadCase();          // also resets per-unit state — see the isolation test below
  renderPtGenPanel();
  await settle(); await settle();
});

afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });

const settle = () => new Promise(r => setTimeout(r, 0));
// One poll interval, with the microtasks it spawns drained. The poll is a 2s setInterval;
// on real timers every one of these tests would sit for two seconds.
const tick = async () => {
  await vi.advanceTimersByTimeAsync(2100);
  await Promise.resolve();
};
const click = (sel) => document.querySelector(sel)
  .dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
const pills = () => Array.from(document.querySelectorAll('#pt-unit-pills .pt-pill'));

describe('the pill row', () => {
  it('has one pill per unit plus Summary', () => {
    expect(pills().length).toBe(UNITS.length + 1);
    expect(pills().at(-1).textContent).toContain('Summary');
  });

  it('starts every unit red', () => {
    pills().slice(0, -1).forEach(p => expect(p.className).toContain('pt-pill-gap'));
  });

  it('starts Summary red, because no unit is generated', () => {
    expect(pills().at(-1).className).toContain('pt-pill-gap');
  });

  it('turns a unit YELLOW on dispatch, then GREEN when the poll sees it land', async () => {
    click('[data-action="ptGenerateUnit"]');           // the current page (setup)
    await settle();
    expect(pills()[0].className).toContain('pt-pill-run');
    markRunning(['setup']);
    await tick();                                      // one poll: still running
    expect(pills()[0].className).toContain('pt-pill-run');
    land('setup', true);
    await tick();
    expect(pills()[0].className).toContain('pt-pill-ok');
  });

  it('leaves a failed unit RED, not yellow and not green', async () => {
    click('[data-action="ptGenerateUnit"]');
    await settle();
    land('setup', false, 'the reply contained no python code block');
    await tick();
    expect(pills()[0].className).toContain('pt-pill-gap');
  });

  it('turns Summary yellow — not green — once every unit is back', async () => {
    // Green is earned by assembling and passing the checks, not by the units existing.
    click('#pt-units-all-btn');
    await settle();
    UNITS.forEach(u => land(u.id, true));
    await tick();
    expect(pills().at(-1).className).toContain('pt-pill-run');
    expect(pills().at(-1).className).not.toContain('pt-pill-ok');
  });
});

describe('the fan-out holds no connection per unit', () => {
  it('dispatches every unit in ONE request', async () => {
    // The deadlock fix. One request per unit, each held open for the whole LLM call,
    // exhausts the browser's six connections per origin and starves the broker's poll.
    const before = global.fetch.mock.calls.length;
    click('#pt-units-all-btn');
    await settle();
    const urls = global.fetch.mock.calls.slice(before).map(c => String(c[0]));
    const dispatches = urls.filter(u => u.includes('/generate_units/'));
    expect(dispatches.length).toBe(1);
    expect(urls.some(u => u.includes('/generate_step/'))).toBe(false);
    expect(dispatched.sort()).toEqual(['setup', 'tc1', 'tc2']);
  });

  it('carries every unit\'s prompt in that one request', async () => {
    click('#pt-units-all-btn');
    await settle();
    expect(sent.setup.prompt).toBe('P-setup');
    expect(sent.tc1.prompt).toBe('P-1');
    expect(sent.tc2.prompt).toBe('P-2');
  });

  it('marks every dispatched unit yellow at once', async () => {
    click('#pt-units-all-btn');
    await settle();
    expect(pills().slice(0, -1).every(p => p.className.includes('pt-pill-run'))).toBe(true);
  });

  it('un-yellows a unit the server refused to dispatch', async () => {
    // Two clicks must not double-run: the server reports what it accepted.
    global.fetch = vi.fn(async (url, opts) => {
      const u = String(url);
      if (u.includes('/generate_units/')) {
        JSON.parse(opts.body || '{}');
        return reply({ dispatched: ['setup'], already_running: [], max_concurrent: 8 });
      }
      if (u.includes('/units_status/')) return reply({ units: {}, running: ['setup'] });
      if (u.includes('/step_prompts/')) return reply({ units: UNITS.map(x => ({ ...x })) });
      return reply({});
    });
    click('#pt-units-all-btn');
    await settle();
    const cs = pills().map(p => p.className);
    expect(cs[0]).toContain('pt-pill-run');
    expect(cs[1]).toContain('pt-pill-gap');
    expect(cs[2]).toContain('pt-pill-gap');
  });

  it('keeps the successes when one unit fails', async () => {
    click('#pt-units-all-btn');
    await settle();
    land('setup', true);
    land('tc1', false, 'nope');
    land('tc2', true);
    await tick();
    const cs = pills().map(p => p.className);
    expect(cs[0]).toContain('pt-pill-ok');
    expect(cs[1]).toContain('pt-pill-gap');
    expect(cs[2]).toContain('pt-pill-ok');
  });

  it('never blocks on a dialog', async () => {
    click('#pt-units-all-btn');
    await settle();
    UNITS.forEach(u => land(u.id, false, 'nope'));
    await tick();
    expect(window.alert).not.toHaveBeenCalled();
  });

  it('names each failed unit as soon as the poll sees it, with a re-run', async () => {
    click('#pt-units-all-btn');
    await settle();
    land('tc1', false, 'the reply defines TestCase_9, not TestCase_1');
    markRunning(['setup', 'tc2']);
    await tick();
    const box = document.getElementById('pt-unit-errors');
    expect(box.textContent).toContain('TestCase_1');
    expect(box.textContent).toContain('TestCase_9');
    expect(box.querySelector('[data-action="ptGenerateUnit"]')).not.toBeNull();
  });

  it('stops polling once nothing is running', async () => {
    click('#pt-units-all-btn');
    await settle();
    UNITS.forEach(u => land(u.id, true));
    await tick();
    const after = global.fetch.mock.calls.length;
    await tick(); await tick();
    const polls = global.fetch.mock.calls.slice(after)
      .filter(c => String(c[0]).includes('/units_status/'));
    expect(polls.length).toBe(0);
  });
});

describe('the prompt is what gets sent', () => {
  it('sends the editable frame content verbatim', async () => {
    const ta = document.getElementById('pt-unit-prompt');
    ta.value = 'MY EDITED PROMPT';
    ta.dispatchEvent(new window.Event('input', { bubbles: true }));
    click('[data-action="ptGenerateUnit"]');
    await settle();
    expect(sent.setup.prompt).toBe('MY EDITED PROMPT');
  });

  it('keeps an edit made on a page you have navigated away from', async () => {
    // Only one page is in the DOM at a time, so the edit has to live in JS state.
    const ta = document.getElementById('pt-unit-prompt');
    ta.value = 'EDITED ON SETUP';
    ta.dispatchEvent(new window.Event('input', { bubbles: true }));
    click('[data-action="ptUnitNext"]');
    await settle();
    click('#pt-units-all-btn');
    await settle();
    expect(sent.setup.prompt).toBe('EDITED ON SETUP');
    expect(sent.tc1.prompt).toBe('P-1');
  });

  it('shows the returned code in the top frame and leaves the prompt below', async () => {
    click('[data-action="ptGenerateUnit"]');
    await settle();
    land('setup', true);
    await tick();
    expect(document.getElementById('pt-unit-out').textContent).toContain('class X_setup');
    expect(document.getElementById('pt-unit-prompt').value).toContain('P-setup');
  });

  it('shows the raw prompt before anything has returned', () => {
    expect(document.getElementById('pt-unit-out').textContent).toContain('nothing yet');
    expect(document.getElementById('pt-unit-prompt').value).toBe('P-setup');
  });
});

describe('the Summary page', () => {
  it('is hidden while a unit page is selected, shown on Summary', async () => {
    expect(document.getElementById('pt-summary-page').classList.contains('hidden')).toBe(true);
    click('[data-action="ptGoSummary"]');
    await settle();
    expect(document.getElementById('pt-summary-page').classList.contains('hidden')).toBe(false);
  });

  it('assembles locally — no LLM call', async () => {
    click('[data-action="ptGoSummary"]');
    await settle();
    const before = global.fetch.mock.calls.length;
    click('#pt-assemble-btn');
    await settle(); await settle(); await settle();
    const urls = global.fetch.mock.calls.slice(before).map(c => String(c[0]));
    expect(urls.some(u => u.includes('/assemble_script/'))).toBe(true);
    expect(urls.some(u => u.includes('/generate_units/'))).toBe(false);
    expect(urls.some(u => u.includes('/generate_script/'))).toBe(false);
  });
});

describe('unit state belongs to one case', () => {
  it('a fresh load_case clears the previous case\'s units and stops its poll', async () => {
    click('#pt-units-all-btn');
    await settle();
    land('setup', true);
    markRunning(['tc1']);
    await tick();
    // Green from STATUS, even though the poll shipped no code and tc1 is still running.
    expect(pills()[0].className).toContain('pt-pill-ok');
    S.ptCase = { key: 'AWPTCM-T2' };
    statusMap = {};
    await ptLoadCase();
    renderPtGenPanel();
    await settle(); await settle();
    expect(pills()[0].className).toContain('pt-pill-gap');
    // The poll for the old case must not keep running.
    const after = global.fetch.mock.calls.length;
    await tick(); await tick();
    expect(global.fetch.mock.calls.slice(after)
      .filter(c => String(c[0]).includes('/units_status/')).length).toBe(0);
  });
});

describe('a unit that lands mid-run', () => {
  it('goes green from its STATUS, without waiting for its code', async () => {
    // The poll does not ship code back. Requiring it left every early finisher red until
    // the whole run ended — which on 30 units is most of the run.
    click('#pt-units-all-btn');
    await settle();
    land('tc1', true);
    markRunning(['setup', 'tc2']);
    await tick();
    expect(pills()[1].className).toContain('pt-pill-ok');
  });

  it('says its code is still coming rather than "nothing yet"', async () => {
    click('#pt-units-all-btn');
    await settle();
    land('setup', true);
    markRunning(['tc1']);
    await tick();
    expect(document.getElementById('pt-unit-out').textContent).toContain('loads when the run finishes');
  });
});

describe('source-level guards', () => {
  it('the fan-out never awaits a per-unit call', () => {
    const fn = JS.slice(JS.indexOf('async function ptGenerateAllUnits'),
                        JS.indexOf('async function ptAssembleScript'));
    expect(fn).not.toContain('Promise.all');
    expect(fn).toContain('_ptDispatchUnits');
  });

  it('collects a dispatch error instead of alerting', () => {
    const fn = JS.slice(JS.indexOf('async function _ptDispatchUnits'),
                        JS.indexOf('async function ptGenerateUnit'));
    expect(fn).toContain('errRef');
    expect(JS).not.toMatch(/alert\([^)]*unit/i);
  });

  it('guards a unit against a double dispatch', () => {
    const fn = JS.slice(JS.indexOf('async function ptGenerateUnit'),
                        JS.indexOf('async function ptGenerateAllUnits'));
    expect(fn).toMatch(/_ptUnitSending\[unitId\]\)\s*return/);
  });

  it('clears the poll interval rather than leaving it running', () => {
    expect(JS).toContain('clearInterval');
    expect(JS).toContain('_ptStopUnitPoll');
  });
});
