// COPIED OVER FROM current/llm-config/llm.js
// NOT PORTED (DOM-reading/writing glue with no Svelte equivalent needed):
//   - buildLLMBody(doc) / claudeRoutingFromUI() — read radios/selects off the DOM;
//     SettingsPage.svelte already holds that state reactively and builds its own body.
//   - updateAuthMethodUI() / updateLLMDefaults() — show/hide DOM rows by auth method;
//     Svelte's {#if provider.id === '...'} in the template already does this reactively.
//   - restoreLLMUI() — sets radio/select DOM values from a loaded config; the component
//     reads the returned config object's fields directly instead.
// NOT PORTED (deliberate scope decision, not just DOM glue):
//   - applyLocalLlmMode() / applyClaudeMode() — the "live toggle applies immediately,
//     before Apply is clicked" behavior. SettingsPage.svelte only applies on an explicit
//     Apply click, so there is no live-toggle race for these to solve. NOTE: this is also
//     WHY agentService.js's ckAgentModeActive() could drop its live-DOM-radio fallback —
//     if this behavior is ever added, revisit that too.
import { storedSeatLlm, SEAT_LLM_RETIRED_KEY, setEffectiveAuthMethod } from '../api/client.js';

const WIZARD_API = '/api/wizard';

// The LLM choice is PER SEAT: what this browser applies is stored here and rides on every
// /api call as X-CK-LLM (client.js). Apply also writes the site default server-side — the
// row a seat that has never chosen starts from.
export function storeSeatLlm(cfg) {
  try {
    localStorage.setItem('draftingLLMConfig', JSON.stringify({
      provider: cfg.provider,
      auth_method: cfg.auth_method,
      model: cfg.model || null,
      unit_model: cfg.unit_model || null,
      match_model: cfg.match_model || null,
    }));
    // A fresh choice ends the "your previous choice was retired" notice.
    localStorage.removeItem(SEAT_LLM_RETIRED_KEY);
  } catch (_) {}
}

// MODIFIED FROM current/llm-config/llm.js TO WORK WITH SVELTE
// (renderSeatLlmRetiredNotice wrote straight into #llmSeatNotice's textContent/hidden
// class; this just tells the caller whether the notice should show, and its text.)
export function seatLlmRetiredNotice() {
  let retired = null;
  try { retired = localStorage.getItem(SEAT_LLM_RETIRED_KEY); } catch (_) {}
  if (!retired) return null;
  return 'Your previous LLM choice for this seat is no longer available — this seat uses the site default until you Apply a new one.';
}

export function normalizeLLMConfig(config) {
  const c = Object.assign({}, config || {});
  const am = (c.auth_method || '').toLowerCase();
  // Session dict does not include has_key; treat CLI + server-keyed modes as configured.
  if (c.has_key === undefined) {
    c.has_key = !!(c.api_key || c.token) || am === 'claude_agent' || am === 'local_llm';
  }
  return c;
}

// MODIFIED FROM current/llm-config/llm.js TO WORK WITH SVELTE
// (updateLLMStatus wrote its text/class straight into #llmStatus and #llm-status-sidebar;
// this returns the same {text, tone} data so any component can render it. Same status
// rules as the original, just no DOM access.)
export function describeLLMStatus(config) {
  const seat = storedSeatLlm();
  let c = config || seat || {};
  c = normalizeLLMConfig(c);
  const provider = c.provider || '';
  const am = (c.auth_method || '').toLowerCase();
  const cliMode = (am === 'claude_agent' || am === 'local_llm');
  const hasCred = !!(c.has_key || c.api_key || c.token || cliMode);

  let text = '';
  let tone = 'warn';

  if (!provider || !hasCred) {
    text = 'No credential (use CLI login or set key)';
  } else if (am === 'local_llm') {
    const modeLabel = c.model === 'vllm-thinking' ? 'Thinking' : 'Fast';
    const ok = c.local_llm_key_set !== false;
    text = `Using Local LLM (vLLM — ${modeLabel})` + (ok ? '' : ' — no key stored on server');
    tone = ok ? 'ok' : 'warn';
  } else {
    const p = provider === 'claude' ? 'Claude' : provider;
    let m = ' (API key)';
    const cap = (x) => (x ? x.charAt(0).toUpperCase() + x.slice(1) : 'default');
    if (am === 'claude_agent') m = ` (Claude — my local machine · ${cap(c.model)})`;
    const routed = [];
    if (c.unit_model && c.unit_model !== c.model) routed.push(`units ${cap(c.unit_model)}`);
    if (c.match_model && c.match_model !== c.model) routed.push(`matching ${cap(c.match_model)}`);
    if (routed.length) m += ` · ${routed.join(', ')}`;
    text = `Using ${p}${m}`;
    tone = 'ok';
  }
  if (text && tone === 'ok') text += (seat && seat.auth_method) ? ' · this seat' : ' · site default';

  return { text, tone };
}

// `body` shape depends on auth_method — the caller (SettingsPage) builds it:
//   local_llm    -> { provider: 'openai', auth_method: 'local_llm', model: 'vllm-fast'|'vllm-thinking', local_llm_key? }
//   claude_agent -> { provider: 'claude', auth_method: 'claude_agent', model: 'haiku'|'sonnet'|'opus', unit_model, match_model }
export async function applyConfig(caseKey, body) {
  const url = caseKey
    ? `${WIZARD_API}/set_llm_config/${encodeURIComponent(caseKey)}`
    : `${WIZARD_API}/set_llm_config`;
  const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const data = await res.json().catch(() => ({}));
  if (!data.llm_config) return null;
  storeSeatLlm(data.llm_config);
  setEffectiveAuthMethod(data.llm_config.auth_method);
  return normalizeLLMConfig(data.llm_config);
}

// Cold-load: THIS SEAT's stored choice wins outright — it is what every request from this
// browser carries. Only a seat that has never chosen asks the server for the site default.
export async function loadConfig() {
  const seat = storedSeatLlm();
  if (seat && seat.auth_method) {
    setEffectiveAuthMethod(seat.auth_method);
    return normalizeLLMConfig(seat);
  }
  try {
    const res = await fetch(`${WIZARD_API}/llm_config`);
    if (!res.ok) return null;
    const data = await res.json();
    if (!data.llm_config || !data.llm_config.provider) return null;
    setEffectiveAuthMethod(data.llm_config.auth_method);
    return normalizeLLMConfig(data.llm_config);
  } catch (_) {
    return null;
  }
}

// Pings the CURRENTLY CONFIGURED backend via the server (same real-call path) to confirm
// it's up and answering — distinguishes "config wrong" from "backend down". Works for
// whichever provider is applied; not local-LLM-specific.
export async function checkHealth() {
  try {
    const res = await fetch(`${WIZARD_API}/llm_health`, { method: 'POST' });
    return await res.json();
  } catch (e) {
    return { ok: false, detail: String(e) };
  }
}
