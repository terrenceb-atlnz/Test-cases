// LLM configuration + status UI.
import { registerActions } from './actions.js';
import { S } from './state.js';
import { getActiveCaseKey } from './cases.js';
import { ckBrokerLoop, probeLocalAgent } from './agent.js';

async function setLLMConfig() {
  // Case is optional: without one the config is saved as the workspace default
  // (and copied onto cases as they load); with one it is also stored on that session.
  const key = S.currentKey || getActiveCaseKey();
  const model = document.getElementById('llmModel').value.trim();

  // Determine method from radio (the radios now directly select the subscription provider+mode)
  const methodRadios = document.querySelectorAll('input[name="llmAuthMethod"]');
  let auth_method = 'grok_cli';
  for (let r of methodRadios) {
    if (r.checked) { auth_method = r.value; break; }
  }

  let provider = (auth_method === 'claude_agent' || auth_method === 'claude_code') ? 'claude' : 'grok';

  const body = { provider, auth_method };
  // CLI subscription modes require no credential here
  if (model) body.model = model;

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
        alert("Claude (my local machine) enabled. Calls run through the ck-agent on YOUR machine against YOUR own Claude seat. Keep the agent running and this tab open.");
      } else if (a.ok && !a.claude_cli) {
        alert("Agent reachable, but the Claude CLI wasn't found on your machine. Install Claude Code and run 'claude' -> /login, then retry.");
      } else {
        alert("Claude (my local machine) selected, but your local agent isn't reachable.\n\nStart it: cd ask-ck/agent && ./run-agent.sh — then click 'Check my local agent'.");
      }
    } else if (auth_method === 'grok_cli') {
      const cli = data.llm_config.grok_cli || {};
      if (cli.available) {
        alert(`Grok CLI subscription mode enabled (CLI: ${cli.version || 'found'}). Calls use your local 'grok login' SuperGrok/X Premium+ session.`);
      } else {
        alert('Grok CLI mode set, but the CLI was NOT found.\n\n' + (cli.hint || 'Install grok CLI and run grok login --oauth, then re-apply.'));
      }
    }
    // No credential field anymore for subscription modes
  } else {
    alert('Failed to set LLM config: ' + (data.detail || data.message || 'unknown'));
  }
}

// --- Per-user local Claude agent (ck-agent on the USER's machine) -----------
export function normalizeLLMConfig(config) {
  // Normalize server/session llm_config for status display.
  const c = Object.assign({}, config || {});
  const am = (c.auth_method || '').toLowerCase();
  // Session dict does not include has_key; treat CLI modes as configured
  if (c.has_key === undefined) {
    c.has_key = !!(c.api_key || c.token) || am === 'claude_agent' || am === 'claude_code' || am === 'grok_cli';
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
  const cliMode = (am === 'claude_agent' || am === 'claude_code' || am === 'grok_cli');
  const hasCred = !!(c.has_key || c.api_key || c.token || cliMode);

  let text = '';
  let ok = false;

  if (!provider || !hasCred) {
    text = 'No credential (use CLI login or set key)';
    ok = false;
  } else {
    const p = provider === 'grok' ? 'Grok (xAI)' : (provider === 'claude' ? 'Claude' : provider);
    let m = ' (API key)';
    if (am === 'claude_agent') m = ' (Claude — my local machine)';
    else if (am === 'claude_code') m = ' (Claude Code CLI)';
    else if (am === 'grok_cli') m = ' (Grok CLI subscription)';
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
    modelInput.placeholder = '(Claude CLI default)';
  } else {
    modelInput.placeholder = '(Grok CLI default)';
  }
}

export function updateAuthMethodUI() {
  // Radios now directly choose the subscription CLI mode (no dropdown, no API key)
  const method = document.querySelector('input[name="llmAuthMethod"]:checked')?.value || 'grok_cli';
  const agentBtn = document.getElementById('agentStatusBtn');
  const grokBtn = document.getElementById('grokCliStatusBtn');
  const agentInstr = document.getElementById('claudeAgentInstructions');
  const grokInstr = document.getElementById('grokCliInstructions');

  if (method === 'claude_agent') {
    if (agentBtn) agentBtn.classList.remove('hidden');
    if (agentInstr) agentInstr.classList.remove('hidden');
    if (grokBtn) grokBtn.classList.add('hidden');
    if (grokInstr) grokInstr.classList.add('hidden');
  } else {
    // grok_cli
    if (grokBtn) grokBtn.classList.remove('hidden');
    if (grokInstr) grokInstr.classList.remove('hidden');
    if (agentBtn) agentBtn.classList.add('hidden');
    if (agentInstr) agentInstr.classList.add('hidden');
  }

  // Placeholder only (no reverse call into this function)
  updateLLMDefaults();
}

export function restoreLLMUI() {
  // Prefer active session config; fall back to last applied / localStorage
  let c = S.currentSession && S.currentSession.llm_config;
  const am = c && (c.auth_method || '').toLowerCase();
  const sessionActive = c && (am === 'claude_agent' || am === 'claude_code' || am === 'grok_cli' || c.api_key || c.token || c.has_key);
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
  let method = c.auth_method || 'grok_cli';
  if (method === 'account' || method === 'api_key') method = 'grok_cli';  // legacy mappings
  if (method === 'claude_code') method = 'claude_agent';  // server-local CLI removed from UI; map to per-user agent
  const radios = document.querySelectorAll('input[name="llmAuthMethod"]');
  for (let r of radios) {
    r.checked = (r.value === method);
  }

  // Keep model field in sync when present
  const modelInput = document.getElementById('llmModel');
  if (modelInput && c.model && !modelInput.value) {
    modelInput.value = c.model;
  }

  updateAuthMethodUI();
  updateLLMStatus(normalizeLLMConfig(c));
  if (method === 'claude_agent') ckBrokerLoop();  // resume serving jobs for a returning agent user
}


// Register this tool's data-action handlers.
registerActions({
  setLLMConfig,
});
