// "Do you want to test the new script?" (Terrence 2026-10-12).
//
// Confirm Step 5 is the end of the PyTest Creator: running and fixing a script moved to
// Validation (PLAN-test-validation). After a successful confirm a pop-up asks; Yes opens
// Validation on that script, No goes back to 1. Cases. Driven through the real click
// dispatcher in jsdom, fetch stubbed.
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

import '../../ask-ck/frontend/ck-main/current/shared/actions.js';
import { S } from '../../ask-ck/frontend/ck-main/current/shared/state.js';
import '../../ask-ck/frontend/ck-main/current/pytest-creator/pytest.js';

const DOM = `
  <div id="nav-pt"></div>
  <div id="panel-pt-seq" class="card tool-panel hidden">
    <div id="pt-seq-case"></div><div id="pt-seq-refined"></div>
    <div id="pt-seq-list"></div><span id="pt-seq-status"></span><div id="pt-seq-prov"></div>
  </div>
  <span id="pt-load-status"></span>
  <div id="pt-steps-list"></div>
  <button data-action="ptLoadCase" id="load">Load Case &amp; Continue</button>
  <div id="panel-pt-cases" class="card tool-panel hidden"></div>
  <div id="panel-pt-gen" class="card tool-panel">
    <span id="pt-gen-status"></span>
    <button data-action="ptConfirm" data-args='[6]' id="c6">4 · Confirm step 5</button>
    <button data-action="ptConfirm" data-args='[2]' id="c2">Confirm step 2</button>
  </div>
  <div id="panel-vd" class="card tool-panel hidden"><div id="vd-root"></div></div>
`;

let calls, status;
const SESSION = { step6: { confirmed: true, naming: { group: 'Port', name: 'test-9001.33234' },
  files: { test: { name: 'test-9001.33234.py', code: '' } } } };
const click = (el) => el.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
const settle = () => new Promise((r) => setTimeout(r, 0));
const until = async (fn, ms = 2000) => {
  const t0 = Date.now();
  while (!fn()) { if (Date.now() - t0 > ms) throw new Error('timed out'); await settle(); }
};
const dialog = () => document.querySelector('.update-overlay [role="dialog"]');
const shown = (id) => !document.getElementById(id).classList.contains('hidden');

beforeEach(() => {
  document.body.innerHTML = DOM;
  calls = [];
  status = 200;
  S.ptCase = { key: 'AWPTCM-T33234' };
  window.alert = () => {};
  global.fetch = vi.fn(async (url) => {
    calls.push(String(url));
    const ok = status === 200;
    const body = String(url).includes('/load_case/') ? { session: SESSION, case_title: 't', group_display: 'g',
      objective: 'o', steps: [], read_only: false, lock: null }
      : String(url).includes('/confirm_step/') ? (ok ? { session: SESSION } : { detail: 'Nothing to confirm yet' })
      : String(url).includes('/api/test-composer/scripts') ? { scripts: [
        { path: '9001_Port/test-9001.33233.py', case_key: 'AWPTCM-T33233' },
        { path: '9001_Port/test-9001.33234.py', case_key: 'AWPTCM-T33234' }] }
      : String(url).includes('/api/test-composer/runs') ? { runs: [] } : {};
    return { ok, status, json: async () => body };
  });
});

// ptSession is module-local: load the case the way the page does.
async function loaded() {
  click(document.getElementById('load'));
  await until(() => calls.some((u) => u.includes('/load_case/')));
  await settle(); await settle();
}

afterEach(() => { document.querySelectorAll('.update-overlay').forEach((o) => o.remove()); vi.restoreAllMocks(); });

describe('Confirm Step 5 asks to test the new script', () => {
  it('asks after a successful confirm, naming the saved script', async () => {
    await loaded();
    click(document.getElementById('c6'));
    await until(() => dialog());
    expect(calls.some((u) => u.endsWith('/confirm_step/AWPTCM-T33234/6'))).toBe(true);
    expect(dialog().textContent).toContain('Do you want to test the new script?');
    expect(dialog().textContent).toContain('test-9001.33234.py');
  });

  it('No goes back to 1. Cases', async () => {
    await loaded();
    click(document.getElementById('c6'));
    await until(() => dialog());
    click(document.getElementById('pt-test-new-no'));
    expect(dialog()).toBe(null);
    expect(shown('panel-pt-cases')).toBe(true);
    expect(shown('panel-vd')).toBe(false);
  });

  it('Escape is No', async () => {
    await loaded();
    click(document.getElementById('c6'));
    await until(() => dialog());
    document.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape' }));
    expect(dialog()).toBe(null);
    expect(shown('panel-pt-cases')).toBe(true);
  });

  it('Yes opens Validation', async () => {
    await loaded();
    click(document.getElementById('c6'));
    await until(() => dialog());
    click(document.getElementById('pt-test-new-yes'));
    expect(dialog()).toBe(null);
    expect(shown('panel-vd')).toBe(true);
    // The island mounts with the case's script ticked (by case key — the session's display
    // group "Port" is not the family directory "9001_Port" Validation lists).
    await until(() => document.querySelector('#vd-root input[name="vd-script"]:checked'), 5000);
    expect(document.querySelector('#vd-root input[name="vd-script"]:checked').value).toBe('9001_Port/test-9001.33234.py');
    expect(shown('panel-pt-cases')).toBe(false);
  });

  it('does not ask when the confirm fails, or for any other step', async () => {
    await loaded();
    status = 409;
    click(document.getElementById('c6'));
    await until(() => calls.some((u) => u.includes('/confirm_step/')));
    await settle(); await settle();
    expect(dialog()).toBe(null);
    status = 200;
    click(document.getElementById('c2'));
    await until(() => calls.some((u) => u.endsWith('/confirm_step/AWPTCM-T33234/2')));
    await settle(); await settle();
    expect(dialog()).toBe(null);
  });
});

// Confirm Step 5 saves (server side), so the page pushes what is on screen first; and the two
// refusals a reviewer may override (X-CK-Needs) are asked for and resent — the page always sent
// `{}` before, so neither could ever be confirmed from the UI.
describe('Confirm Step 5: push first, then ask for an acknowledgement the server names', () => {
  let confirms, saves, replies;
  const headers = (needs) => ({ get: (h) => (h === 'X-CK-Needs' ? needs : null) });

  beforeEach(() => {
    document.getElementById('panel-pt-gen').insertAdjacentHTML('beforeend',
      '<textarea id="pt-gen-code">print("edited")</textarea><div id="pt-gen-lib-wrap" class="hidden"></div>');
    confirms = []; saves = [];
    replies = [];                       // queued confirm_step answers: {status, detail, needs}
    global.fetch = vi.fn(async (url, opts = {}) => {
      const u = String(url);
      calls.push(u);
      if (u.includes('/load_case/')) return { ok: true, status: 200, headers: headers(null), json: async () => (
        { session: SESSION, case_title: 't', group_display: 'g', objective: 'o', steps: [], read_only: false, lock: null }) };
      if (u.includes('/save_script/')) { saves.push(JSON.parse(opts.body)); return { ok: true, status: 200, headers: headers(null), json: async () => ({ lint: {} }) }; }
      if (u.includes('/confirm_step/')) {
        confirms.push(JSON.parse(opts.body));
        const r = replies.shift() || { status: 200 };
        return { ok: r.status === 200, status: r.status, headers: headers(r.needs || null),
                 json: async () => (r.status === 200 ? { session: SESSION, written: ['generated/9001_Port/test-9001.33234.py'] } : { detail: r.detail }) };
      }
      return { ok: true, status: 200, headers: headers(null), json: async () => ({}) };
    });
  });

  const ackDialog = () => document.querySelector('.pt-ack-dialog');

  it('pushes the editor into the session (no disk write) before confirming', async () => {
    await loaded();
    click(document.getElementById('c6'));
    await until(() => dialog());
    expect(saves).toEqual([{ code: 'print("edited")', write_files: false }]);
    expect(calls.findIndex((u) => u.includes('/save_script/'))).toBeLessThan(calls.findIndex((u) => u.includes('/confirm_step/')));
    expect(document.getElementById('pt-gen-status').textContent).toContain('Saved: generated/9001_Port/test-9001.33234.py');
  });

  it('asks for a reason on a house-rule refusal, resends with it, then asks to test', async () => {
    replies = [{ status: 409, detail: 'This script breaks house rules:\n  - policy: x', needs: 'acknowledge_lint_policy' }];
    await loaded();
    click(document.getElementById('c6'));
    await until(() => ackDialog());
    expect(ackDialog().textContent).toContain('policy: x');
    const ok = document.getElementById('pt-ack-ok');
    expect(ok.disabled).toBe(true);                         // a reason is required
    const reason = document.getElementById('pt-ack-reason');
    reason.value = 'the bench has no fibre'; reason.dispatchEvent(new window.Event('input'));
    expect(ok.disabled).toBe(false);
    click(ok);
    await until(() => dialog() && !ackDialog());
    expect(confirms).toEqual([{}, { acknowledge_lint_policy: 'the bench has no fibre' }]);
    expect(dialog().textContent).toContain('Do you want to test the new script?');
  });

  it('a coverage gap then a house rule: both are asked, each once, and sent together', async () => {
    replies = [{ status: 409, detail: 'gap', needs: 'acknowledge_coverage_gap' },
               { status: 409, detail: 'rules', needs: 'acknowledge_lint_policy' }];
    await loaded();
    click(document.getElementById('c6'));
    await until(() => ackDialog());
    expect(document.getElementById('pt-ack-reason')).toBe(null);   // a gap needs no reason
    click(document.getElementById('pt-ack-ok'));
    await until(() => document.getElementById('pt-ack-reason'));
    const reason = document.getElementById('pt-ack-reason');
    reason.value = 'ok'; reason.dispatchEvent(new window.Event('input'));
    click(document.getElementById('pt-ack-ok'));
    await until(() => confirms.length === 3);
    expect(confirms[2]).toEqual({ acknowledge_coverage_gap: true, acknowledge_lint_policy: 'ok' });
  });

  it('Cancel sends nothing more and asks nothing else', async () => {
    replies = [{ status: 409, detail: 'gap', needs: 'acknowledge_coverage_gap' }];
    await loaded();
    click(document.getElementById('c6'));
    await until(() => ackDialog());
    click(document.getElementById('pt-ack-cancel'));
    await settle(); await settle();
    expect(confirms.length).toBe(1);
    expect(dialog()).toBe(null);
  });

  it('a refusal with nothing to acknowledge is reported, not retried', async () => {
    const alerts = [];
    window.alert = (m) => alerts.push(m);
    replies = [{ status: 409, detail: 'This script has errors that cannot be overridden' }];
    await loaded();
    click(document.getElementById('c6'));
    await until(() => alerts.length);
    expect(alerts[0]).toContain('cannot be overridden');
    expect(confirms.length).toBe(1);
    expect(dialog()).toBe(null);
  });

  it('the same acknowledgement asked twice is reported, not looped', async () => {
    const alerts = [];
    window.alert = (m) => alerts.push(m);
    replies = [{ status: 409, detail: 'gap', needs: 'acknowledge_coverage_gap' },
               { status: 409, detail: 'gap again', needs: 'acknowledge_coverage_gap' }];
    await loaded();
    click(document.getElementById('c6'));
    await until(() => ackDialog());
    click(document.getElementById('pt-ack-ok'));
    await until(() => alerts.length);
    expect(alerts[0]).toContain('gap again');
    expect(confirms.length).toBe(2);
  });
});
