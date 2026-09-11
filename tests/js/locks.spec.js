// Unit specs for the per-case lock UX (PLAN-auth-and-case-locking.md Phase 1, frontend).
//
// The DOM half of locking: a read-only banner + disabled step inputs when another tab
// holds the case (D6a), and clean re-enable when we hold it. Network calls (acquire/
// heartbeat/release) are exercised in the backend suite; here we cover the DOM effects
// in jsdom, plus a source drift-check that the release-on-close + heartbeat wiring stays.
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { onCaseLoaded, _renderBanner } from '../ask-ck/CK-main/CK_server/static/js/locks.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const LOCKS_JS = resolve(HERE, '../ask-ck/CK-main/CK_server/static/js/locks.js');

beforeEach(() => {
  document.body.innerHTML = `
    <div id="load-status"></div>
    <div id="step-1" class="card tool-panel">
      <input id="i1">
      <button id="b1">go</button>
      <button id="b0" disabled>already off</button>
      <button id="keep" data-ck-lock-keep="1">case picker</button>
    </div>
    <div id="step-2" class="card tool-panel"><textarea id="t1"></textarea></div>`;
});

function locked(holder = 'session abcd1234') {
  return { held: true, by_me: false, holder, holder_label: holder,
           acquired_at: '2026-07-29T12:00:00+00:00', expired: false, stealable: false };
}

describe('read-only banner', () => {
  it('names the holder, says read-only, and uses the warning style', () => {
    _renderBanner('wizard', 'AWPTCM-T1', locked('session abcd1234'));
    const el = document.getElementById('ck-lock-banner');
    expect(el).toBeTruthy();
    expect(el.className).toContain('is-warning');
    expect(el.textContent).toContain('AWPTCM-T1');
    expect(el.textContent).toContain('session abcd1234');
    expect(el.textContent.toLowerCase()).toContain('read-only');
  });

  it('shows a "since" time when acquired_at is valid, and omits it when not', () => {
    _renderBanner('wizard', 'AWPTCM-T1', locked());
    expect(document.getElementById('ck-lock-banner').textContent).toContain('since');
    _renderBanner('wizard', 'AWPTCM-T1', { ...locked(), acquired_at: null });
    expect(document.getElementById('ck-lock-banner').textContent).not.toContain('since');
  });

  it('offers "Take over" ONLY when the lock is stealable (expired)', () => {
    _renderBanner('wizard', 'AWPTCM-T1', { ...locked(), stealable: false });
    expect(document.querySelector('[data-ck-lock-takeover]')).toBeNull();
    _renderBanner('wizard', 'AWPTCM-T1', { ...locked(), stealable: true });
    expect(document.querySelector('[data-ck-lock-takeover]')).toBeTruthy();
  });
});

describe('read-only input disabling (D6a)', () => {
  it('disables step inputs when another holds the lock, then cleanly re-enables', () => {
    vi.useFakeTimers();  // onCaseLoaded(by_me) starts a heartbeat interval; don't let it fire
    try {
      onCaseLoaded('wizard', 'AWPTCM-T1', locked(), true);
      expect(document.getElementById('i1').disabled).toBe(true);
      expect(document.getElementById('b1').disabled).toBe(true);
      expect(document.getElementById('t1').disabled).toBe(true);
      // A control we did not disable stays as it was; an exempt control stays usable.
      expect(document.getElementById('b0').disabled).toBe(true);   // was already disabled
      expect(document.getElementById('keep').disabled).toBe(false); // data-ck-lock-keep
      expect(document.getElementById('ck-lock-banner').className).toContain('is-warning');

      // Now WE hold it: inputs come back, the banner clears, and the pre-disabled
      // control is left untouched (we only re-enable what we disabled).
      onCaseLoaded('wizard', 'AWPTCM-T1', { held: true, by_me: true, holder: '', acquired: true }, false);
      expect(document.getElementById('i1').disabled).toBe(false);
      expect(document.getElementById('b1').disabled).toBe(false);
      expect(document.getElementById('b0').disabled).toBe(true);   // still off — not ours to re-enable
      expect(document.getElementById('ck-lock-banner').className).toContain('hidden');
    } finally {
      vi.clearAllTimers();
      vi.useRealTimers();
    }
  });
});

describe('locks.js source (drift detection)', () => {
  const src = readFileSync(LOCKS_JS, 'utf8');
  it('releases on tab close via sendBeacon on pagehide', () => {
    expect(src).toMatch(/addEventListener\(\s*['"]pagehide['"]/);
    expect(src).toMatch(/navigator\.sendBeacon/);
  });
  it('heartbeats well inside the 15-minute idle TTL', () => {
    expect(src).toMatch(/5 \* 60 \* 1000/);
  });
  it('remembers which controls it disabled so re-enable is non-destructive', () => {
    expect(src).toContain('data-ck-lock-disabled');
  });
});
