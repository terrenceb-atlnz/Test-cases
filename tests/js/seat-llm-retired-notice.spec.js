// The one-time "your previous choice was retired" notice (PLAN-seat-setup-and-per-seat-llm.md
// §11.3, decision D14, 2026-09-11).
//
// session.js drops a stored seat choice whose backend was retired (claude_code 2026-09-10,
// grok_cli 2026-09-11) so the seat falls back to the site default instead of 400-ing on every
// call. Silently, though, a user who applied "(this server)" on demo day would just see the
// site default and wonder. So the drop is remembered, LLM → Configure says so ONCE — until the
// seat next Applies — and the text names no retired mode (D3: no evidence it existed).
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mountFromIndex } from './helpers/fixture-dom.js';
import { S } from '../ask-ck/CK-main/CK_server/static/js/state.js';
import { updateLLMStatus, storeSeatLlm, renderSeatLlmRetiredNotice, SEAT_LLM_RETIRED_TEXT }
  from '../ask-ck/CK-main/CK_server/static/js/llm.js';
import { storedSeatLlm, SEAT_LLM_RETIRED_KEY } from '../ask-ck/CK-main/CK_server/static/js/session.js';

const SITE_DEFAULT = { provider: 'openai', auth_method: 'local_llm', model: 'vllm-fast',
                       has_key: true, local_llm_key_set: true };

beforeEach(() => {
  localStorage.clear();
  document.body.innerHTML = '';
  mountFromIndex('panel-llm-config');            // the REAL Configure panel: #llmStatus + #llmSeatNotice
  S.currentSession = null;
  window.lastLLMConfig = SITE_DEFAULT;
  vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, json: async () => ({}) })));
});
afterEach(() => { vi.unstubAllGlobals(); });

const notice = () => document.getElementById('llmSeatNotice');

describe('a seat whose stored choice was retired', () => {
  it('is told so under LLM → Configure, in words that name no retired mode', () => {
    localStorage.setItem('draftingLLMConfig', JSON.stringify({ provider: 'claude', auth_method: 'claude_code', model: 'opus' }));
    expect(storedSeatLlm()).toBeNull();                       // dropped (2026-09-10 behaviour)
    expect(localStorage.getItem(SEAT_LLM_RETIRED_KEY)).toBe('claude_code');
    updateLLMStatus();
    expect(notice().classList.contains('hidden')).toBe(false);
    expect(notice().textContent).toBe(SEAT_LLM_RETIRED_TEXT);
    expect(notice().textContent).toMatch(/no longer available/);
    expect(notice().textContent).toMatch(/site default/);
    for (const retired of ['claude_code', 'grok', 'this server', 'api_key']) {
      expect(notice().textContent.toLowerCase()).not.toContain(retired);
    }
    // The status line itself still tells the truth about what requests will get.
    expect(document.getElementById('llmStatus').textContent).toMatch(/site default/);
  });

  it('keeps seeing it across renders until the seat next Applies — then never again', () => {
    localStorage.setItem(SEAT_LLM_RETIRED_KEY, 'grok_cli');
    updateLLMStatus();
    updateLLMStatus();
    expect(notice().classList.contains('hidden')).toBe(false);
    // Apply (any success path goes through storeSeatLlm) clears the flag and the notice.
    storeSeatLlm({ provider: 'openai', auth_method: 'local_llm', model: 'vllm-fast' });
    expect(localStorage.getItem(SEAT_LLM_RETIRED_KEY)).toBeNull();
    updateLLMStatus();
    expect(notice().classList.contains('hidden')).toBe(true);
    expect(notice().textContent).toBe('');
  });

  it('shows nothing for a seat that never had a retired choice', () => {
    expect(renderSeatLlmRetiredNotice()).toBe(false);
    updateLLMStatus();
    expect(notice().classList.contains('hidden')).toBe(true);
  });

  it('renders nowhere when the Configure panel is not mounted (no throw, no stray text)', () => {
    document.body.innerHTML = '';
    localStorage.setItem(SEAT_LLM_RETIRED_KEY, 'claude_code');
    expect(renderSeatLlmRetiredNotice()).toBe(false);
    expect(() => updateLLMStatus()).not.toThrow();
  });
});
