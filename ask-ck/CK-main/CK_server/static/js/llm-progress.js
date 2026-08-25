// Live progress + true Stop for LLM buttons (2026-08-26, Terrence).
//
// Every LLM call in the app already showed a spinner via setButtonBusy; what it
// lacked was a sense of progress and a way OUT. This module upgrades a busy LLM
// button into a live one:
//
//   [⏸ Generating… 37s / ~45s · 12.3k streamed]     ← click to STOP
//    ▔▔▔▔▔▔▔▔▔▔▔▔▔▔ 2px fill bar = elapsed vs typical
//
//   * elapsed ticks every second;
//   * "~45s" is the median of this session's recent successful calls to the
//     SAME prompt template (served by GET /api/llm/inflight/{id}), and drives
//     the fill bar — the single-call equivalent of the suggest-all X/N tally;
//   * "12.3k streamed" is REAL output observed server-side as it arrives
//     (vLLM SSE chunks; claude/grok CLI stream-json lines);
//   * clicking the busy button fires POST /api/llm/cancel/{id} — a TRUE
//     server-side cancel (the CLI process group is killed / the vLLM stream is
//     closed / the agent job is abandoned). Nothing persists; the endpoint
//     errors with "cancelled by user". A UI-only abort that lets the server
//     finish and spend anyway was explicitly rejected.
//
// The click routing lives in actions.js: its delegated click listener checks
// data-ck-cancel BEFORE resolving data-action, so a busy (re-enabled) button
// can never re-fire its own action.
import { setButtonBusy } from './dom-helpers.js';

export function newCallId() {
  return 'llm-' + Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
}

/** True when an error string is the user's own Stop, not a real failure. */
export function isCancelMessage(text) {
  return String(text || '').includes('cancelled by user');
}

function fmtK(n) {
  return n >= 10000 ? (n / 1000).toFixed(0) + 'k' : n >= 1000 ? (n / 1000).toFixed(1) + 'k' : String(n);
}

/**
 * Put an LLM button into live-busy mode. Returns null when the button is
 * already busy (same double-click guard setButtonBusy provides), else
 * { headers, end } — spread `headers` into the fetch so the server can track
 * and cancel this exact call; call `end()` in the caller's finally.
 */
export function llmButtonStart(btn, label) {
  if (!setButtonBusy(btn, true, { label })) return null;
  const id = newCallId();
  // Re-enable: a disabled button swallows clicks, and this button's click now
  // means STOP (routed via data-ck-cancel before any data-action can fire).
  btn.disabled = false;
  btn.dataset.ckCancel = id;
  btn.classList.add('ck-stoppable');
  btn.title = 'Click to stop this LLM call — nothing will be kept';

  const started = Date.now();
  let snap = null;
  let ticks = 0;
  const timer = setInterval(async () => {
    ticks += 1;
    if (btn.dataset.ckStopping === '1') return;   // label is "Stopping…" — leave it
    const lbl = btn.querySelector('.ck-busy-label');
    if (!lbl) return;
    if (ticks % 2 === 0) {
      try {
        const r = await fetch('/api/llm/inflight/' + id);
        if (r.ok) { const d = await r.json(); if (d.found) snap = d; }
      } catch (_) { /* poll is best-effort; the ticker keeps counting */ }
    }
    const s = Math.round((Date.now() - started) / 1000);
    let text = `${label} ${s}s`;
    if (snap && snap.typical_ms) {
      text += ` / ~${Math.round(snap.typical_ms / 1000)}s`;
      btn.style.setProperty('--ck-pct',
        Math.min(97, (s * 1000 / snap.typical_ms) * 100).toFixed(0) + '%');
    }
    if (snap && snap.chars) text += ` · ${fmtK(snap.chars)} streamed`;
    lbl.textContent = text;
  }, 1000);

  return {
    headers: { 'X-CK-LLM-Call': id },
    end() {
      clearInterval(timer);
      delete btn.dataset.ckCancel;
      delete btn.dataset.ckStopping;
      btn.classList.remove('ck-stoppable');
      btn.style.removeProperty('--ck-pct');
      btn.title = '';
      setButtonBusy(btn, false);
    },
  };
}

/** Fire the true cancel for a call id (used by suggest-all's own Stop too). */
export function cancelLlmCall(id) {
  if (!id) return;
  fetch('/api/llm/cancel/' + encodeURIComponent(id), { method: 'POST' }).catch(() => {});
}
