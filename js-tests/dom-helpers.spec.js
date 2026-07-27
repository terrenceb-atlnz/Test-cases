// Unit specs for the shared DOM helpers — including the LLM-button feedback
// helpers (setButtonBusy / flashButtonDone) added 2026-07-27. Pure DOM, no
// fixtures, no fetch. Regression-locks the busy/disable/flash behaviour.
import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  setButtonBusy,
  flashButtonDone,
  showStatus,
  escapeHtml,
  truncateText,
} from '../ask-ck/CK-main/CK_server/static/js/dom-helpers.js';

function makeButton(label = 'Suggest') {
  const b = document.createElement('button');
  b.className = 'btn btn-primary';
  b.innerHTML = label;
  document.body.appendChild(b);
  return b;
}

beforeEach(() => {
  document.body.innerHTML = '';
});

describe('setButtonBusy', () => {
  it('disables, marks busy, and swaps in the spinner + label', () => {
    const b = makeButton('Suggest');
    const started = setButtonBusy(b, true, { label: 'Suggesting…' });

    expect(started).toBe(true);
    expect(b.disabled).toBe(true);
    expect(b.classList.contains('is-busy')).toBe(true);
    expect(b.getAttribute('aria-busy')).toBe('true');
    expect(b.querySelector('.ck-spinner')).not.toBeNull();
    expect(b.textContent).toContain('Suggesting…');
  });

  it('restores the exact original label when cleared', () => {
    const b = makeButton('<span>Suggest</span> now');
    const original = b.innerHTML;
    setButtonBusy(b, true, { label: 'Working…' });
    setButtonBusy(b, false);

    expect(b.disabled).toBe(false);
    expect(b.classList.contains('is-busy')).toBe(false);
    expect(b.hasAttribute('aria-busy')).toBe(false);
    expect(b.innerHTML).toBe(original);
  });

  it('guards double-clicks: a second busy call returns false and keeps the first label', () => {
    const b = makeButton('Generate');
    setButtonBusy(b, true, { label: 'Generating…' });
    const second = setButtonBusy(b, true, { label: 'Should be ignored' });

    expect(second).toBe(false);
    // The stashed original must still be the real label, not the spinner markup —
    // this is what lets the handler bail out without corrupting the button.
    setButtonBusy(b, false);
    expect(b.innerHTML).toBe('Generate');
  });

  it('is a safe no-op on a null button', () => {
    expect(setButtonBusy(null, true)).toBe(false);
    expect(setButtonBusy(null, false)).toBe(false);
  });

  it('clearing a not-busy button does nothing', () => {
    const b = makeButton('Idle');
    expect(setButtonBusy(b, false)).toBe(false);
    expect(b.disabled).toBe(false);
    expect(b.innerHTML).toBe('Idle');
  });

  it('defaults the busy label to "Working…" when none is given', () => {
    const b = makeButton('X');
    setButtonBusy(b, true);
    expect(b.textContent).toContain('Working…');
  });
});

describe('flashButtonDone', () => {
  it('adds is-done on success and auto-clears after ~1.2s', () => {
    vi.useFakeTimers();
    const b = makeButton('Go');
    flashButtonDone(b, true);
    expect(b.classList.contains('is-done')).toBe(true);
    expect(b.classList.contains('is-error')).toBe(false);
    vi.advanceTimersByTime(1200);
    expect(b.classList.contains('is-done')).toBe(false);
    vi.useRealTimers();
  });

  it('adds is-error on failure', () => {
    vi.useFakeTimers();
    const b = makeButton('Go');
    flashButtonDone(b, false);
    expect(b.classList.contains('is-error')).toBe(true);
    expect(b.classList.contains('is-done')).toBe(false);
    vi.advanceTimersByTime(1200);
    expect(b.classList.contains('is-error')).toBe(false);
    vi.useRealTimers();
  });

  it('is a safe no-op on a null button', () => {
    expect(() => flashButtonDone(null, true)).not.toThrow();
  });
});

describe('showStatus', () => {
  function banner() {
    const d = document.createElement('div');
    d.id = 'x-status';
    d.className = 'status-banner hidden';
    document.body.appendChild(d);
    return d;
  }

  it('sets the kind class and an escaped title', () => {
    const d = banner();
    showStatus('x-status', 'error', 'Broke <b>hard</b> & fast');
    expect(d.className).toBe('status-banner is-error');
    // Title text must be escaped (no live <b> injected).
    expect(d.querySelector('.status-title').innerHTML).toContain('&lt;b&gt;');
    expect(d.querySelector('b')).toBeNull();
  });

  it('renders items as an escaped list', () => {
    const d = banner();
    showStatus('x-status', 'warning', 'Issues', ['one', '<script>bad</script>']);
    const items = d.querySelectorAll('li');
    expect(items.length).toBe(2);
    expect(d.querySelector('script')).toBeNull();
  });

  it('clear hides the banner and empties it', () => {
    const d = banner();
    showStatus('x-status', 'success', 'done');
    showStatus('x-status', 'clear');
    expect(d.className).toBe('status-banner hidden');
    expect(d.innerHTML).toBe('');
  });

  it('is a safe no-op when the target id is absent', () => {
    expect(() => showStatus('does-not-exist', 'error', 'x')).not.toThrow();
  });
});

describe('escapeHtml / truncateText (pure)', () => {
  it('escapes the five HTML-sensitive chars', () => {
    expect(escapeHtml(`<a href="x" & 'y'>`)).toBe(
      '&lt;a href=&quot;x&quot; &amp; &#39;y&#39;&gt;',
    );
  });
  it('truncates with an ellipsis past the max', () => {
    expect(truncateText('abcdef', 4)).toBe('abc…');
    expect(truncateText('ab', 4)).toBe('ab');
  });
});
