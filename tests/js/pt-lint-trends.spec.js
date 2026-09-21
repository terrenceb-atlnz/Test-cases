// R5's two JS surfaces (PLAN-self-healing-generation.md §6.4).
//
// The backend shipped 2026-09-15 and these were deferred then, explicitly "once real data
// accrues" — they would have rendered empty. Built 2026-09-22, once /lint_trends began
// answering with runs. The two surfaces have deliberately DIFFERENT rules, and that is what
// this file pins:
//   * step-5 Summary banner — §6.4's "on every case while the alarm stands": visible ONLY
//     while a threshold is crossed, amber (it blocks nothing; the red ✗ lines below it do).
//   * admin "Lint trends" card — always renders its numbers, red only on alarm, so that
//     "nothing is wrong" and "nothing was ever recorded" can never look the same.
// Both read ONE endpoint that answers in three shapes (normal / {runs:0} / {error}), and a
// missing key in any of them must not throw — /lint_trends drops total_units, repair and
// return_rate when thin, and window, by_class and prompt_version outright on error.
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

import '../../ask-ck/frontend/ck-main/current/shared/actions.js';
import { S } from '../../ask-ck/frontend/ck-main/current/shared/state.js';
import { ptLoadCase, renderPtGenPanel, ptLintTrendBanner }
  from '../../ask-ck/frontend/ck-main/current/pytest-creator/pytest.js';
import { renderLintTrendsCard, openAdminPanel } from '../../ask-ck/frontend/ck-main/current/admin/admin.js';

// The three shapes /lint_trends really returns (routers/pytest_create.py:_pt_lint_trends).
const ALARM = {
  class: 'pep8', kind: 'prompt_defect',
  detail: 'class `pep8` touched 2/19 units (11%) over 1 runs — change the generate prompt, not the repair',
};
const LOUD = { runs: 1, window: 5, total_units: 19, prompt_version: 'c35474bbbe',
               by_class: { pep8: 2 }, repair: { other: { repaired_ok: 1, arrival_failed: 0 } },
               return_rate: 1.0, alarms: [ALARM] };
const QUIET = { ...LOUD, alarms: [] };
const THIN = { runs: 0, window: 5, alarms: [], by_class: {}, prompt_version: 'c35474bbbe' };
const ERR = { error: 'no such table: sessions', alarms: [], runs: 0 };

describe('the Summary banner (pure)', () => {
  it('stays hidden and empty while no threshold is crossed', () => {
    const b = ptLintTrendBanner(QUIET);
    expect(b.className).toContain('hidden');
    expect(b.html).toBe('');
  });

  it('is hidden for the thin and error shapes, and for no payload at all', () => {
    for (const d of [THIN, ERR, null, undefined, {}]) {
      expect(ptLintTrendBanner(d).className, JSON.stringify(d)).toContain('hidden');
    }
  });

  it('shows AMBER, not red — the lint errors beneath it are the blocking ones', () => {
    const b = ptLintTrendBanner(LOUD);
    expect(b.className).toBe('status-banner is-warning');
    expect(b.className).not.toContain('is-error');
  });

  it("renders the server's detail VERBATIM, so the banner, the log line and /health agree", () => {
    expect(ptLintTrendBanner(LOUD).html).toContain(ALARM.detail);
  });

  it('names the window and the prompt version, and gets run/runs right', () => {
    expect(ptLintTrendBanner(LOUD).html).toContain('the last 1 run');
    expect(ptLintTrendBanner(LOUD).html).toContain('prompt version c35474bbbe');
    expect(ptLintTrendBanner({ ...LOUD, runs: 5 }).html).toContain('the last 5 runs');
  });

  it('lists every alarm, not just the first', () => {
    const second = { class: 'suite_owned', kind: 'lint_text_defect', detail: 'second alarm text' };
    const html = ptLintTrendBanner({ ...LOUD, alarms: [ALARM, second] }).html;
    expect(html).toContain(ALARM.detail);
    expect(html).toContain('second alarm text');
    expect(html.match(/<li>/g)).toHaveLength(2);
  });

  it('escapes the detail — it reaches the DOM as innerHTML', () => {
    const html = ptLintTrendBanner({ ...LOUD, alarms: [{ detail: '<img src=x onerror=1>' }] }).html;
    expect(html).not.toContain('<img');
    expect(html).toContain('&lt;img');
  });
});

describe('the admin Lint trends card (pure)', () => {
  it('renders the numbers even when nothing is wrong — silence must not read as "never ran"', () => {
    const c = renderLintTrendsCard(QUIET);
    expect(c.className).not.toContain('is-error');
    expect(c.html).toContain('1 run(s)');
    expect(c.html).toContain('in a window of 5');
    expect(c.html).toContain('19 unit(s)');
    expect(c.html).toContain('pep8:2');
    expect(c.html).toContain('100%');
    expect(c.html).toContain('no threshold crossed');
  });

  it('turns red and names the alarm when a threshold IS crossed', () => {
    const c = renderLintTrendsCard(LOUD);
    expect(c.className).toBe('status-banner is-error');
    expect(c.html).toContain(ALARM.detail);
    expect(c.html).toContain('19 unit(s)');        // the numbers survive alongside the alarm
  });

  it('says so plainly when no run has been recorded yet', () => {
    const c = renderLintTrendsCard(THIN);
    expect(c.className).not.toContain('is-error');
    expect(c.html).toContain('No assembly runs recorded yet');
  });

  it('surfaces a backend error instead of pretending the trend is clean', () => {
    const c = renderLintTrendsCard(ERR);
    expect(c.html).toContain('unavailable');
    expect(c.html).toContain('no such table: sessions');
  });

  it('never throws on the keys the thin and error shapes omit', () => {
    for (const d of [THIN, ERR, null, {}, { runs: 2 }, { runs: 2, alarms: [ALARM] }]) {
      expect(() => renderLintTrendsCard(d), JSON.stringify(d)).not.toThrow();
    }
  });

  it('distinguishes "no repairs attempted" from a 0% return rate', () => {
    expect(renderLintTrendsCard({ ...QUIET, return_rate: null }).html).toContain('no repairs attempted');
    expect(renderLintTrendsCard({ ...QUIET, return_rate: 0 }).html).toContain('0%');
  });
});

// --- the wiring: the Summary really mounts it, through the real render path ----------------
const DOM = `
  <div id="nav-pt"></div>
  <div id="panel-pt-seq"><div id="pt-seq-case"></div><div id="pt-seq-refined"></div>
    <div id="pt-seq-list"></div><span id="pt-seq-status"></span><div id="pt-seq-prov"></div></div>
  <span id="pt-load-status"></span>
  <button id="pt-units-all-btn" data-action="ptGenerateAllUnits" class="btn">Generate all units (LLM)</button>
  <button id="pt-units-reload-btn" data-action="ptLoadUnits" class="btn">reload</button>
  <span id="pt-units-status"></span>
  <div id="pt-unit-pills"></div><div id="pt-unit-errors"></div><div id="pt-unit-page"></div>
  <div id="pt-summary-page" class="hidden">
    <span id="pt-gen-path"></span><span id="pt-gen-status"></span>
    <button id="pt-assemble-btn" data-action="ptAssembleAndSettle" class="btn">1 · Assemble</button>
    <button id="pt-assemble-only-btn" data-action="ptAssembleScript" class="btn">Assemble only</button>
    <button id="pt-fix-units-btn" data-action="ptFixUnits" class="btn">Fix units</button>
    <button id="pt-apply-held-btn" data-action="ptApplyAllHeld" class="btn">Apply all held</button>
    <button id="pt-rechunk-btn" data-action="ptRechunk" class="btn">Re-chunk</button>
    <button id="pt-reset-gen-btn" data-action="ptResetGenerate" class="btn">Reset Generate</button>
    <div id="pt-lint-trends" class="mb-2"></div>
    <div id="pt-lint-result"></div><div id="pt-review-result"></div>
    <textarea id="pt-gen-code"></textarea>
    <div id="pt-gen-lib-wrap" class="hidden"><span id="pt-gen-lib-name"></span>
      <textarea id="pt-gen-lib-code"></textarea></div>
    <div id="pt-gen-prov"></div>
  </div>`;

const reply = (body) => ({ ok: true, status: 200, json: async () => body });
const settle = async (n = 6) => { for (let i = 0; i < n; i++) await new Promise((r) => setTimeout(r, 0)); };
const GEN_STATE = { script_hash: 'a', assembled_hash: 'a', units: 0, frame_snapshot: true,
                    diverged: false, reason: '', review_stale: false };
const session = () => ({ step2: { sequence: [{ n: 1, action: 'a', verify: 'v' }] },
                         step6: { files: { test: { name: 'x.py', code: 'print(1)' } },
                                  lint: { ok: true, errors: [], warnings: [] } } });

async function mount(trendPayload, { ok = true } = {}) {
  document.body.innerHTML = DOM;
  S.ptCase = { key: 'AWPTCM-T1' };
  window.alert = vi.fn();
  global.fetch = vi.fn(async (url) => {
    const u = String(url);
    if (u.includes('/lint_trends')) {
      return ok ? reply(trendPayload) : { ok: false, status: 500, json: async () => ({}) };
    }
    if (u.includes('/load_case/')) return reply({ session: session(), case_title: 't', group_display: 'g', objective: 'o', steps: [], read_only: false, lock: null, gen_state: GEN_STATE });
    if (u.includes('/session/')) return reply({ session: session(), gen_state: GEN_STATE });
    if (u.includes('/step_prompts/')) return reply({ units: [] });
    if (u.includes('/units_status/')) return reply({ units: {}, running: [] });
    return reply({});
  });
  await ptLoadCase();
  renderPtGenPanel();
  await settle();
  return document.getElementById('pt-lint-trends');
}

describe('the Summary banner (wired through renderPtGenPanel)', () => {
  afterEach(() => vi.restoreAllMocks());

  it('fetches /lint_trends and shows the alarm above the lint result', async () => {
    const el = await mount(LOUD);
    expect(global.fetch.mock.calls.some(([u]) => String(u).includes('/api/pytest-create/lint_trends'))).toBe(true);
    expect(el.className).toBe('status-banner is-warning');
    expect(el.textContent).toContain('change the generate prompt, not the repair');
    // it must sit ABOVE the lint result, not below it (Terrence, 2026-09-22)
    const page = document.getElementById('pt-summary-page');
    const ids = [...page.children].map((c) => c.id);
    expect(ids.indexOf('pt-lint-trends')).toBeLessThan(ids.indexOf('pt-lint-result'));
  });

  it('leaves the banner empty while the trend is quiet', async () => {
    const el = await mount(QUIET);
    expect(el.className).toContain('hidden');
    expect(el.innerHTML).toBe('');
  });

  it('stays silent when /lint_trends fails — a trend must never block the assemble flow', async () => {
    const el = await mount(LOUD, { ok: false });
    expect(el.className).toContain('hidden');
    expect(window.alert).not.toHaveBeenCalled();
  });
});

// The admin card needs the same wiring pin as the banner: mutation M2 (dropping the render
// call) left every pure test green, so "the function is right" proves nothing about whether
// anything calls it.
describe('the admin Lint trends card (wired through openAdminPanel)', () => {
  afterEach(() => vi.restoreAllMocks());

  it('fetches /lint_trends on open and paints the card red when an alarm stands', async () => {
    document.body.innerHTML = '<div id="panel-admin" class="tool-panel hidden">'
      + '<div id="admin-status"></div><div id="admin-lint-trends" class="mb-2"></div></div>';
    global.fetch = vi.fn(async (url) => (String(url).includes('/lint_trends')
      ? reply(LOUD)
      : reply({ db: { ok: true, counts: {}, vector_search: true } })));
    openAdminPanel();
    await settle();
    expect(global.fetch.mock.calls.some(([u]) => String(u).includes('/api/pytest-create/lint_trends'))).toBe(true);
    const el = document.getElementById('admin-lint-trends');
    expect(el.className).toBe('status-banner is-error');
    expect(el.textContent).toContain(ALARM.detail);
  });

  it('still shows the numbers on open when the trend is quiet', async () => {
    document.body.innerHTML = '<div id="panel-admin" class="tool-panel hidden">'
      + '<div id="admin-status"></div><div id="admin-lint-trends" class="mb-2"></div></div>';
    global.fetch = vi.fn(async (url) => (String(url).includes('/lint_trends')
      ? reply(QUIET)
      : reply({ db: { ok: true, counts: {}, vector_search: true } })));
    openAdminPanel();
    await settle();
    const el = document.getElementById('admin-lint-trends');
    expect(el.className).not.toContain('is-error');
    expect(el.textContent).toContain('19 unit(s)');
    expect(el.textContent).toContain('no threshold crossed');
  });

  it('reports a failed fetch in the card rather than leaving the last numbers up', async () => {
    document.body.innerHTML = '<div id="panel-admin" class="tool-panel hidden">'
      + '<div id="admin-status"></div><div id="admin-lint-trends" class="mb-2"></div></div>';
    global.fetch = vi.fn(async (url) => (String(url).includes('/lint_trends')
      ? { ok: false, status: 500, json: async () => ({}) }
      : reply({ db: { ok: true, counts: {}, vector_search: true } })));
    openAdminPanel();
    await settle();
    expect(document.getElementById('admin-lint-trends').textContent).toContain('unavailable');
  });
});
