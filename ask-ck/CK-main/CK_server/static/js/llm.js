// LLM configuration + status UI.
import { registerActions } from './actions.js';
import { S } from './state.js';
import { getActiveCaseKey } from './cases.js';
import { ckBrokerLoop, probeLocalAgent } from './agent.js';
import { fmtTokens } from './llm-debug.js';
import { setButtonBusy, flashButtonDone } from './dom-helpers.js';

async function setLLMConfig() {
  // Case is optional: without one the config is saved as the workspace default
  // (and copied onto cases as they load); with one it is also stored on that session.
  const key = S.currentKey || getActiveCaseKey();
  const model = document.getElementById('llmModel').value.trim();

  // Determine method from radio (the radios now directly select the subscription provider+mode)
  const methodRadios = document.querySelectorAll('input[name="llmAuthMethod"]');
  let auth_method = 'local_llm';
  for (let r of methodRadios) {
    if (r.checked) { auth_method = r.value; break; }
  }

  let provider = 'openai';   // org vLLM rides the OpenAI-compatible path
  if (auth_method === 'claude_agent' || auth_method === 'claude_code') provider = 'claude';

  const body = { provider, auth_method };
  // CLI subscription modes require no credential here
  if (model) body.model = model;

  if (auth_method === 'claude_agent' && !model) {
    // Haiku/Sonnet/Opus toggle picks the model unless an explicit one was typed.
    const cm = document.querySelector('input[name="claudeMode"]:checked');
    body.model = (cm && cm.value) || 'sonnet';
  }

  if (auth_method === 'local_llm') {
    // Fast/Thinking toggle IS the model choice for the org vLLM.
    const mode = document.querySelector('input[name="localLlmMode"]:checked');
    body.model = (mode && mode.value) || 'vllm-fast';
    // Key travels ONLY when (re-)entered; blank keeps the server-stored key.
    const keyEl = document.getElementById('localLlmKey');
    const key = keyEl && keyEl.value.trim();
    if (key) body.local_llm_key = key;
  }

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
    // Remember client-side too (survives until hard refresh; server also stores workspace default)
    window.lastLLMConfig = data.llm_config;
    try { localStorage.setItem('draftingLLMConfig', JSON.stringify({
      provider: data.llm_config.provider,
      auth_method: data.llm_config.auth_method,
      model: data.llm_config.model || null
    })); } catch (_) {}
    updateLLMStatus(data.llm_config);
    if (auth_method === 'claude_agent') {
      ckBrokerLoop();  // ensure the broker is running (idempotent) so jobs get served
      const a = await probeLocalAgent();
      if (a.ok && a.claude_cli) {
        const cm = body.model ? ` — ${body.model} model` : '';
        alert(`Claude (my local machine) enabled${cm}. Calls run through the ck-agent on YOUR machine against YOUR own Claude seat. Keep the agent running and this tab open.`);
      } else if (a.ok && !a.claude_cli) {
        alert("Agent reachable, but the Claude CLI wasn't found on your machine. Install Claude Code and run 'claude' -> /login, then retry.");
      } else {
        alert("Claude (my local machine) selected, but your local agent isn't reachable.\n\nStart it: cd ask-ck/agent && ./run-agent.sh — then click 'Check my local agent'.");
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
      try {
        localStorage.setItem('draftingLLMConfig', JSON.stringify({
          provider: data.llm_config.provider,
          auth_method: data.llm_config.auth_method,
          model: data.llm_config.model || null,
        }));
      } catch (_) {}
      updateLLMStatus(data.llm_config);
      const stateEl = document.getElementById('localLlmKeyState');
      if (stateEl) stateEl.textContent = data.llm_config.local_llm_key_set !== false ? 'key stored ✓' : '⚠ no key stored';
    }
  } catch (_) { /* leave prior state on a transient failure */ }
}

export async function applyClaudeMode() {
  // Live Haiku/Sonnet/Opus toggle for the local Claude agent: persist the new
  // model immediately (no Apply click). Only meaningful when claude_agent is the
  // selected method. Stays quiet — this is an incidental toggle, not a login.
  const method = document.querySelector('input[name="llmAuthMethod"]:checked')?.value;
  if (method !== 'claude_agent') return;
  const cm = document.querySelector('input[name="claudeMode"]:checked');
  const model = (cm && cm.value) || 'sonnet';

  const key = S.currentKey || getActiveCaseKey();
  const url = key
    ? `/api/wizard/set_llm_config/${encodeURIComponent(key)}`
    : '/api/wizard/set_llm_config';
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider: 'claude', auth_method: 'claude_agent', model }),
    });
    const data = await res.json();
    if (data.llm_config) {
      if (S.currentSession) S.currentSession.llm_config = data.llm_config;
      window.lastLLMConfig = data.llm_config;
      try {
        localStorage.setItem('draftingLLMConfig', JSON.stringify({
          provider: data.llm_config.provider,
          auth_method: data.llm_config.auth_method,
          model: data.llm_config.model || null,
        }));
      } catch (_) {}
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
    c.has_key = !!(c.api_key || c.token) || am === 'claude_agent' || am === 'claude_code' || am === 'local_llm';
  }
  return c;
}

export function updateLLMStatus(config) {
  const statusEl = document.getElementById('llmStatus');
  const sidebarEl = document.getElementById('llm-status-sidebar');

  let c = config || (S.currentSession && S.currentSession.llm_config) || window.lastLLMConfig || {};
  c = normalizeLLMConfig(c);
  const provider = c.provider || '';
  const am = (c.auth_method || '').toLowerCase();
  const cliMode = (am === 'claude_agent' || am === 'claude_code' || am === 'local_llm');
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
    if (am === 'claude_agent') {
      const cm = c.model ? c.model.charAt(0).toUpperCase() + c.model.slice(1) : 'default';
      m = ` (Claude — my local machine · ${cm})`;
    }
    else if (am === 'claude_code') m = ' (Claude Code CLI)';
    text = `Using ${p}${m}`;
    ok = true;
  }

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

  if (localRow) localRow.classList.toggle('hidden', method !== 'local_llm');
  if (claudeRow) claudeRow.classList.toggle('hidden', method !== 'claude_agent');

  if (method === 'claude_agent') {
    if (agentBtn) agentBtn.classList.remove('hidden');
    if (agentInstr) agentInstr.classList.remove('hidden');
  } else {
    // Org vLLM (local_llm): no CLI to check, no instruction panels
    if (agentBtn) agentBtn.classList.add('hidden');
    if (agentInstr) agentInstr.classList.add('hidden');
  }

  // Placeholder only (no reverse call into this function)
  updateLLMDefaults();
}

export async function loadWorkspaceLLMConfig() {
  // Cold-load status: fetch the persisted workspace LLM config so the status
  // line + Configure radios reflect the real stored login (incl. whether a
  // Local LLM key is stored) instead of "No credential" until the user
  // re-applies. Secrets are never returned by this endpoint.
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
  // Prefer active session config; fall back to last applied / localStorage
  let c = S.currentSession && S.currentSession.llm_config;
  const am = c && (c.auth_method || '').toLowerCase();
  const sessionActive = c && (am === 'claude_agent' || am === 'claude_code' || am === 'local_llm' || c.api_key || c.token || c.has_key);
  if (!sessionActive) {
    c = window.lastLLMConfig || null;
    if (!c) {
      try {
        const raw = localStorage.getItem('draftingLLMConfig');
        if (raw) c = JSON.parse(raw);
      } catch (_) {}
    }
  }
  if (!c || !c.provider) return;

  // Set method from saved config (no provider dropdown; radios embody the choice)
  let method = c.auth_method || 'local_llm';
  if (method === 'account' || method === 'api_key') method = 'local_llm';  // legacy mappings
  if (method === 'claude_code') method = 'claude_agent';  // server-local CLI removed from UI; map to per-user agent
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
  if (modelInput && c.model && !modelInput.value && method !== 'local_llm' && method !== 'claude_agent') {
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
  if (!setButtonBusy(btn, true, { label: 'Pinging…' })) return;   // guard double-click
  if (out) { out.textContent = '⏳ pinging…'; out.style.color = ''; }
  let ok = false;
  try {
    const res = await fetch('/api/wizard/llm_health', { method: 'POST' });
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
    setButtonBusy(btn, false);
    flashButtonDone(btn, ok);
  }
}

// Register this tool's data-action handlers.
registerActions({
  setLLMConfig,
  checkLlmHealth,
  applyClaudeMode,
});
