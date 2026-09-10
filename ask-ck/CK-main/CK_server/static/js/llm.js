// LLM configuration + status UI.
import { registerActions } from './actions.js';
import { S } from './state.js';
import { getActiveCaseKey } from './cases.js';
import { ckBrokerLoop, probeLocalAgent } from './agent.js';
import { fmtTokens } from './llm-debug.js';
import { llmButtonStart } from './llm-progress.js';
import { flashButtonDone } from './dom-helpers.js';
import { storedSeatLlm } from './session.js';

// The LLM choice is PER SEAT (PLAN-seat-setup-and-per-seat-llm.md §5): what this browser
// applies is stored here and rides on every /api call as X-CK-LLM (session.js). The server
// writes nothing for a plain Apply; only "Set as site default" writes the row that seats
// which have never chosen start from.
export function storeSeatLlm(cfg) {
  try {
    localStorage.setItem('draftingLLMConfig', JSON.stringify({
      provider: cfg.provider,
      auth_method: cfg.auth_method,
      model: cfg.model || null,
      unit_model: cfg.unit_model || null,
      match_model: cfg.match_model || null,
    }));
  } catch (_) {}
}

// The body for set_llm_config / set_site_default_llm, read from the Configure panel.
export function buildLLMBody(doc = document) {
  const model = (doc.getElementById('llmModel')?.value || '').trim();
  let auth_method = 'local_llm';
  for (const r of doc.querySelectorAll('input[name="llmAuthMethod"]')) {
    if (r.checked) { auth_method = r.value; break; }
  }
  let provider = 'openai';   // org vLLM rides the OpenAI-compatible path
  if (auth_method === 'claude_agent') provider = 'claude';
  const body = { provider, auth_method };
  if (model) body.model = model;
  if (auth_method === 'claude_agent' && !model) {
    // Haiku/Sonnet/Opus toggle picks the model unless an explicit one was typed.
    const cm = doc.querySelector('input[name="claudeMode"]:checked');
    body.model = (cm && cm.value) || 'sonnet';
  }
  if (auth_method === 'claude_agent') {
    const pick = (id) => { const el = doc.getElementById(id); return el ? (el.value || '') : ''; };
    body.unit_model = pick('claudeUnitModel');
    body.match_model = pick('claudeMatchModel');
  }
  if (auth_method === 'local_llm') {
    // Fast/Thinking toggle IS the model choice for the org vLLM.
    const mode = doc.querySelector('input[name="localLlmMode"]:checked');
    body.model = (mode && mode.value) || 'vllm-fast';
    // Key travels ONLY when (re-)entered; blank keeps the server-stored key.
    const keyEl = doc.getElementById('localLlmKey');
    const key = keyEl && keyEl.value.trim();
    if (key) body.local_llm_key = key;
  }
  return body;
}

async function setSiteDefaultLLM() {
  // Decision D2: a separate, labelled control writes the site default; Apply never does.
  const body = buildLLMBody();
  if (!confirm(`Set the SITE default LLM to ${body.provider} via ${body.auth_method}${body.model ? ` (${body.model})` : ''}?\n\nSeats that have chosen their own LLM keep it; seats that never chose start from this.`)) return;
  const res = await fetch('/api/wizard/set_site_default_llm', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  });
  const data = await res.json();
  if (data.llm_config) alert(data.message || 'Site default set.');
  else alert('Failed to set the site default: ' + (data.detail || data.message || 'unknown'));
}

async function setLLMConfig() {
  // THIS SEAT only. The case key is passed for URL compatibility; the server ignores it.
  const key = S.currentKey || getActiveCaseKey();
  const body = buildLLMBody();
  const auth_method = body.auth_method;

  const url = key
    ? `/api/wizard/set_llm_config/${encodeURIComponent(key)}`
    : '/api/wizard/set_llm_config';
  const res = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body)
  });
  const data = await res.json();
  if (data.llm_config) {
    if (S.currentSession) S.currentSession.llm_config = data.llm_config;
    // The seat's choice lives HERE (localStorage) and rides on every request from now on.
    window.lastLLMConfig = data.llm_config;
    storeSeatLlm(data.llm_config);
    updateLLMStatus(data.llm_config);
    if (auth_method === 'claude_agent') {
      ckBrokerLoop();  // ensure the broker is running (idempotent) so jobs get served
      const a = await probeLocalAgent();
      if (a.ok && a.claude_cli && a.logged_in === false) {
        alert("Agent reachable and Claude is installed, but it is NOT logged in on your machine.\n\nRun 'claude auth login' there, then click 'Check my local agent'.");
      } else if (a.ok && a.claude_cli) {
        const cm = body.model ? ` — ${body.model} model` : '';
        alert(`Claude (my local machine) enabled${cm}. Calls run through the ck-agent on YOUR machine against YOUR own Claude seat. Keep the agent running and this tab open.`);
      } else if (a.ok && !a.claude_cli) {
        alert("Agent reachable, but the Claude CLI wasn't found on your machine. Install Claude Code and run 'claude auth login', then retry.");
      } else {
        alert("Claude (my local machine) selected, but your local agent isn't reachable.\n\nRun the one-line seat setup from the Ask CK home page (or: cd ask-ck/agent && ./run-agent.sh), then click 'Check my local agent'.");
      }
    } else if (auth_method === 'local_llm') {
      const keyEl = document.getElementById('localLlmKey');
      if (keyEl) keyEl.value = '';   // write-only field: never leave the key in the DOM
      const keySet = data.llm_config.local_llm_key_set !== false;
      const stateEl = document.getElementById('localLlmKeyState');
      if (stateEl) stateEl.textContent = keySet ? 'key stored ✓' : '⚠ no key stored';
      if (!keySet) {
        alert('Local LLM selected, but NO API key is stored on the server yet.\n\nEnter your key in the "Local LLM API key" field and Apply again (it is stored server-side; you won\'t need to re-enter it until it expires).');
      } else {
        const modeLabel = (body.model === 'vllm-thinking') ? 'Thinking' : 'Fast';
        alert(`Local LLM (org vLLM) enabled — ${modeLabel} mode. The key is stored server-side and persists across restarts.`);
      }
    }
    // No credential field anymore for subscription modes
  } else {
    alert('Failed to set LLM config: ' + (data.detail || data.message || 'unknown'));
  }
}

export async function applyLocalLlmMode() {
  // Live Fast/Thinking toggle: persist the new model immediately (no Apply
  // click needed). Only meaningful when Local LLM is the selected method.
  // Reuses the server-stored key (no key is sent), and stays quiet — no alert
  // popups — because this is an incidental toggle, not an explicit login.
  const method = document.querySelector('input[name="llmAuthMethod"]:checked')?.value;
  if (method !== 'local_llm') return;
  const mode = document.querySelector('input[name="localLlmMode"]:checked');
  const model = (mode && mode.value) || 'vllm-fast';

  const key = S.currentKey || getActiveCaseKey();
  const url = key
    ? `/api/wizard/set_llm_config/${encodeURIComponent(key)}`
    : '/api/wizard/set_llm_config';
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider: 'openai', auth_method: 'local_llm', model }),
    });
    const data = await res.json();
    if (data.llm_config) {
      if (S.currentSession) S.currentSession.llm_config = data.llm_config;
      window.lastLLMConfig = data.llm_config;
      storeSeatLlm(data.llm_config);
      updateLLMStatus(data.llm_config);
      const stateEl = document.getElementById('localLlmKeyState');
      if (stateEl) stateEl.textContent = data.llm_config.local_llm_key_set !== false ? 'key stored ✓' : '⚠ no key stored';
    }
  } catch (_) { /* leave prior state on a transient failure */ }
}

export function claudeRoutingFromUI() {
  // The two per-task routing selects (decision 6, 2026-09-07). Blank = same as the toggle.
  const pick = (id) => { const el = document.getElementById(id); return el ? (el.value || '') : ''; };
  return { unit_model: pick('claudeUnitModel'), match_model: pick('claudeMatchModel') };
}

export async function applyClaudeMode() {
  // Live Haiku/Sonnet/Opus toggle for the Claude mode, plus the per-task routing selects:
  // persist immediately (no Apply click). Stays quiet — this is an incidental toggle,
  // not a login. `auth_method` is always the CHECKED radio, never a literal: a literal
  // here once moved the whole workspace to a different backend on a model toggle.
  const method = document.querySelector('input[name="llmAuthMethod"]:checked')?.value;
  if (method !== 'claude_agent') return;
  const cm = document.querySelector('input[name="claudeMode"]:checked');
  const model = (cm && cm.value) || 'sonnet';
  const routing = claudeRoutingFromUI();

  const key = S.currentKey || getActiveCaseKey();
  const url = key
    ? `/api/wizard/set_llm_config/${encodeURIComponent(key)}`
    : '/api/wizard/set_llm_config';
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider: 'claude', auth_method: method, model, ...routing }),
    });
    const data = await res.json();
    if (data.llm_config) {
      if (S.currentSession) S.currentSession.llm_config = data.llm_config;
      window.lastLLMConfig = data.llm_config;
      storeSeatLlm(data.llm_config);
      updateLLMStatus(data.llm_config);
    }
  } catch (_) { /* leave prior state on a transient failure */ }
}

// --- Per-user local Claude agent (ck-agent on the USER's machine) -----------
export function normalizeLLMConfig(config) {
  // Normalize server/session llm_config for status display.
  const c = Object.assign({}, config || {});
  const am = (c.auth_method || '').toLowerCase();
  // Session dict does not include has_key; treat CLI + server-keyed modes as configured
  if (c.has_key === undefined) {
    c.has_key = !!(c.api_key || c.token) || am === 'claude_agent' || am === 'local_llm';
  }
  return c;
}

export function updateLLMStatus(config) {
  const statusEl = document.getElementById('llmStatus');
  const sidebarEl = document.getElementById('llm-status-sidebar');

  // Source order: what was just applied, else THIS SEAT's stored choice, else the site
  // default fetched at boot, else (legacy) whatever the case session carries.
  const seat = storedSeatLlm();
  let c = config || seat || window.lastLLMConfig || (S.currentSession && S.currentSession.llm_config) || {};
  c = normalizeLLMConfig(c);
  const provider = c.provider || '';
  const am = (c.auth_method || '').toLowerCase();
  const cliMode = (am === 'claude_agent' || am === 'local_llm');
  const hasCred = !!(c.has_key || c.api_key || c.token || cliMode);

  let text = '';
  let ok = false;

  if (!provider || !hasCred) {
    text = 'No credential (use CLI login or set key)';
    ok = false;
  } else if (am === 'local_llm') {
    const modeLabel = (c.model === 'vllm-thinking') ? 'Thinking' : 'Fast';
    text = `Using Local LLM (vLLM — ${modeLabel})`;
    ok = c.local_llm_key_set !== false;
    if (!ok) text += ' — ⚠ no key stored on server';
  } else {
    const p = provider === 'claude' ? 'Claude' : provider;
    let m = ' (API key)';
    const cap = (x) => (x ? x.charAt(0).toUpperCase() + x.slice(1) : 'default');
    if (am === 'claude_agent') m = ` (Claude — my local machine · ${cap(c.model)})`;
    // Per-task routing is part of "which model am I spending" — say it in the status line.
    const routed = [];
    if (c.unit_model && c.unit_model !== c.model) routed.push(`units ${cap(c.unit_model)}`);
    if (c.match_model && c.match_model !== c.model) routed.push(`matching ${cap(c.match_model)}`);
    if (routed.length) m += ` · ${routed.join(', ')}`;
    text = `Using ${p}${m}`;
    ok = true;
  }
  if (text && ok) text += (seat && seat.auth_method) ? ' · this seat' : ' · site default';

  [statusEl, sidebarEl].forEach(el => {
    if (!el) return;
    el.textContent = text;
    el.classList.remove('llm-status-ok', 'llm-status-warn');
    el.classList.add(ok ? 'llm-status-ok' : 'llm-status-warn');
  });
}

function updateLLMDefaults() {
  // Adjust model placeholder from the selected subscription radio only.
  // IMPORTANT: do not call updateAuthMethodUI() here — that used to recurse forever
  // (updateAuthMethodUI → updateLLMDefaults → updateAuthMethodUI → …) and crash Load
  // with "RangeError: Maximum call stack size exceeded".
  const modelInput = document.getElementById('llmModel');
  if (!modelInput || modelInput.value) return;

  const checked = document.querySelector('input[name="llmAuthMethod"]:checked');
  if (checked && checked.value === 'claude_agent') {
    modelInput.placeholder = '(model set by Haiku/Sonnet/Opus toggle)';
  } else if (checked && checked.value === 'local_llm') {
    modelInput.placeholder = '(model set by Fast/Thinking toggle)';
  } else {
    modelInput.placeholder = '(CLI default)';
  }
}

export function updateAuthMethodUI() {
  // Radios now directly choose the subscription CLI mode (no dropdown, no API key)
  const method = document.querySelector('input[name="llmAuthMethod"]:checked')?.value || 'local_llm';
  const agentBtn = document.getElementById('agentStatusBtn');
  const agentInstr = document.getElementById('claudeAgentInstructions');
  const localRow = document.getElementById('localLlmRow');
  const claudeRow = document.getElementById('claudeAgentRow');
  const routingRow = document.getElementById('claudeRoutingRow');
  const modeNote = document.getElementById('claudeModeNote');

  if (localRow) localRow.classList.toggle('hidden', method !== 'local_llm');
  const isClaude = (method === 'claude_agent');
  if (claudeRow) claudeRow.classList.toggle('hidden', !isClaude);
  if (routingRow) routingRow.classList.toggle('hidden', !isClaude);
  if (modeNote) {
    modeNote.innerHTML = 'Runs as <code>claude --model &lt;name&gt;</code> on your own seat.';
  }

  // The local-agent button and its instructions are about the USER's machine.
  const wantsAgent = (method === 'claude_agent');
  if (agentBtn) agentBtn.classList.toggle('hidden', !wantsAgent);
  if (agentInstr) agentInstr.classList.toggle('hidden', !wantsAgent);

  // Placeholder only (no reverse call into this function)
  updateLLMDefaults();
}

export async function loadWorkspaceLLMConfig() {
  // Cold-load status. THIS SEAT's stored choice wins outright — it is what every request
  // from this browser carries. Only a seat that has never chosen asks the server for the
  // site default, so the radios and status line show what its requests will actually get.
  // Secrets are never returned by that endpoint.
  if (storedSeatLlm()?.auth_method) {
    restoreLLMUI();
    return;
  }
  try {
    const res = await fetch('/api/wizard/llm_config');
    if (!res.ok) return;
    const data = await res.json();
    const c = data.llm_config;
    if (!c || !c.provider) return;
    window.lastLLMConfig = c;
    restoreLLMUI();               // sets radios + Fast/Thinking toggle + key-state note
    updateLLMStatus(normalizeLLMConfig(c));
  } catch (_) { /* offline / no stored config — leave the default status */ }
}

export function restoreLLMUI() {
  // THIS SEAT's stored choice first (it is what this browser's requests carry), then the
  // site default fetched at boot, then — legacy — whatever the case session carries.
  let c = storedSeatLlm();
  if (!c || !c.auth_method) c = window.lastLLMConfig || null;
  if (!c || !c.auth_method) {
    const s = S.currentSession && S.currentSession.llm_config;
    const am = s && (s.auth_method || '').toLowerCase();
    if (s && (am === 'claude_agent' || am === 'local_llm' || s.has_key)) c = s;
  }
  if (!c || !c.provider) return;

  // Set method from saved config (no provider dropdown; radios embody the choice)
  let method = c.auth_method || 'local_llm';
  if (method === 'account' || method === 'api_key') method = 'local_llm';  // legacy mappings
  const radios = document.querySelectorAll('input[name="llmAuthMethod"]');
  for (let r of radios) {
    r.checked = (r.value === method);
  }

  if (method === 'claude_agent') {
    // Restore the Haiku/Sonnet/Opus toggle from the saved model. Only override
    // when the config carries one of the known aliases — a restore whose model
    // is missing/"default" must NOT silently reset a chosen model.
    if (c.model === 'haiku' || c.model === 'sonnet' || c.model === 'opus') {
      document.querySelectorAll('input[name="claudeMode"]').forEach((r) => {
        r.checked = (r.value === c.model);
      });
    }
    // Per-task routing selects follow the stored config; a missing field means "same".
    [['claudeUnitModel', c.unit_model], ['claudeMatchModel', c.match_model]].forEach(([id, v]) => {
      const el = document.getElementById(id);
      if (el) el.value = (v === 'haiku' || v === 'sonnet' || v === 'opus') ? v : '';
    });
  }

  if (method === 'local_llm') {
    // Restore the Fast/Thinking toggle from the saved model (key field stays
    // blank — it is write-only; the key lives server-side). Only override the
    // toggle when the config carries an explicit vllm model — a restore whose
    // model is missing/"default" (e.g. a case-load re-applying the workspace
    // config) must NOT silently reset a chosen Thinking back to Fast.
    if (c.model === 'vllm-fast' || c.model === 'vllm-thinking') {
      document.querySelectorAll('input[name="localLlmMode"]').forEach((r) => {
        r.checked = (r.value === c.model);
      });
    }
    // Surface the stored-key state on restore too (not only after Apply). The
    // saved config carries local_llm_key_set when it came from set_llm_config;
    // when absent (older session), leave the note blank rather than guess.
    const stateEl = document.getElementById('localLlmKeyState');
    if (stateEl && c.local_llm_key_set !== undefined) {
      stateEl.textContent = c.local_llm_key_set ? 'key stored ✓' : '⚠ no key stored';
    }
  }

  // Keep model field in sync when present (not for local_llm / claude_agent —
  // their model is the toggle, not the free-text field)
  const modelInput = document.getElementById('llmModel');
  if (modelInput && c.model && !modelInput.value && method !== 'local_llm'
      && method !== 'claude_agent') {
    modelInput.value = c.model;
  }

  updateAuthMethodUI();
  updateLLMStatus(normalizeLLMConfig(c));
  if (method === 'claude_agent') ckBrokerLoop();  // resume serving jobs for a returning agent user
}


export async function checkLlmHealth() {
  // Ping the configured LLM via the server (same real-call path) to confirm it's
  // up and answering — distinguishes "config wrong" from "backend down" without
  // firing a real synthesize. Provider-agnostic; the ping is recorded in debug-log.
  const btn = document.getElementById('llmHealthBtn');
  const out = document.getElementById('llmHealthState');
  const llmCtl = llmButtonStart(btn, 'Pinging…');   // live progress + click-to-stop
  if (!llmCtl) return;                               // guard double-click
  if (out) { out.textContent = '⏳ pinging…'; out.style.color = ''; }
  let ok = false;
  try {
    const res = await fetch('/api/wizard/llm_health', { method: 'POST', headers: llmCtl.headers });
    const d = await res.json();
    ok = !!d.ok;
    if (out) {
      if (d.ok) {
        const tok = d.usage ? ` · ${fmtTokens(d.usage)}` : '';
        out.textContent = `✓ up — ${d.model} (${d.latency_ms} ms)${tok}`;
        out.style.color = 'var(--status-ok, #16a34a)';
      } else if (d.reason === 'not_configured') {
        out.textContent = `⚠ ${d.detail || 'no LLM configured'}`;
        out.style.color = 'var(--status-warn, #d97706)';
      } else {
        out.textContent = `✗ down — ${d.detail || 'LLM call failed'}`;
        out.style.color = 'var(--status-low, #ef4444)';
      }
    }
  } catch (e) {
    if (out) { out.textContent = `✗ request failed — ${e.message || e}`; out.style.color = 'var(--status-low, #ef4444)'; }
  } finally {
    llmCtl.end();
    flashButtonDone(btn, ok);
  }
}

// Register this tool's data-action handlers.
registerActions({
  setLLMConfig,
  setSiteDefaultLLM,
  checkLlmHealth,
  applyClaudeMode,
});
