// COPIED OVER FROM current/shared/llm-progress.js
// NOT PORTED (DOM-coupled): mutating a <button> element directly each tick (label
// textContent, a CSS custom property for the fill bar, dataset flags). Svelte components
// hold their own reactive progress state instead and render it however they like.

export function newCallId() {
  return 'llm-' + Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
}

/** True when an error string is the user's own Stop, not a real failure. */
export function isCancelMessage(text) {
  return String(text || '').includes('cancelled by user');
}

/** True server-side cancel — kills the CLI process / closes the vLLM stream / wakes an
    abandoned agent job. The call that's blocked on this id then errors with "cancelled by
    user", which is how the caller finds out (there's no client-side abort involved at all). */
export function cancelLlmCall(id) {
  if (!id) return Promise.resolve();
  return fetch('/api/llm/cancel/' + encodeURIComponent(id), { method: 'POST' }).catch(() => {});
}

function fmtK(n) {
  return n >= 10000 ? (n / 1000).toFixed(0) + 'k' : n >= 1000 ? (n / 1000).toFixed(1) + 'k' : String(n);
}

// MODIFIED FROM current/shared/llm-progress.js TO WORK WITH SVELTE
// (llmButtonStart wrote into a <button> every tick; this calls onTick({text, pct}) with
// plain data every second instead, so a component can hold `progressText`/`progressPct`
// and render them. Returns {headers, stop()} — same shape as the original's
// {headers, end()}: spread `headers` into the real fetch so the server can track/cancel
// this exact call; call `stop()` in the caller's `finally`.)
export function startLlmProgress(label, onTick) {
  const id = newCallId();
  const started = Date.now();
  let snap = null;
  let ticks = 0;
  const timer = setInterval(async () => {
    ticks += 1;
    if (ticks % 2 === 0) {
      try {
        const r = await fetch('/api/llm/inflight/' + id);
        if (r.ok) { const d = await r.json(); if (d.found) snap = d; }
      } catch (_) { /* poll is best-effort */ }
    }
    const s = Math.round((Date.now() - started) / 1000);
    let text = `${label} ${s}s`;
    let pct = null;
    if (snap && snap.typical_ms) {
      text += ` / ~${Math.round(snap.typical_ms / 1000)}s`;
      pct = Math.min(97, (s * 1000 / snap.typical_ms) * 100);
    }
    if (snap && snap.chars) text += ` · ${fmtK(snap.chars)} streamed`;
    onTick({ text, pct });
  }, 1000);

  return { callId: id, headers: { 'X-CK-LLM-Call': id }, stop() { clearInterval(timer); } };
}

// COPIED OVER FROM current/shared/llm-debug.js (fmtTok/fmtTokens — verbatim, pure formatting)
// NOT PORTED: the per-panel debug footer (renderLlmDebugFooter/llm-debug-view) and panel
// attribution (S.currentPanel/X-CK-Panel) — there's no "current panel" concept in Svelte yet
// (client.js's own header-injection comment already says so) and no caller has asked for the
// prompt/response debug footer, just the token badge.
function fmtTok(n) {
  if (n == null) return '?';
  if (n >= 10000) return (n / 1000).toFixed(1).replace(/\.0$/, '') + 'k';
  return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

export function fmtTokens(usage) {
  if (!usage) return '— tok';
  const inp = usage.input_tokens, out = usage.output_tokens;
  const total = (inp != null && out != null) ? ` (${fmtTok(inp + out)} total)` : '';
  return `${fmtTok(inp)} in / ${fmtTok(out)} out${total}`;
}

// MODIFIED FROM current/shared/llm-debug.js's recordLLMDebug TO WORK WITH SVELTE (that wrote
// a <span> badge directly after a button element and filed records per-panel; this just
// returns the newest record so a component can render its own badge — call only after a
// successful LLM call, matching the original's "badge updates ONLY on success" rule).
export async function fetchLatestLlmUsage() {
  try {
    const res = await fetch('/api/llm/recent?limit=5');
    if (!res.ok) return null;
    const data = await res.json();
    const records = data.records || [];
    return records.length ? records[records.length - 1] : null;   // oldest→newest
  } catch (_) {
    return null;
  }
}
