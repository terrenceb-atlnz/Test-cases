// Per-task model routing on the Configure page (token-efficiency decision 6, 2026-09-07).
//
// Two properties are load-bearing, and one is a regression pin:
//
//   1. The routing selects travel WITH the model toggle: one POST carries model +
//      unit_model + match_model, so the server can preserve whichever the body omits.
//   2. A stored config restores the selects (blank for "same"), so the page tells the
//      truth about what the next fan-out will spend.
//   3. REGRESSION: applyClaudeMode posts the CHECKED auth method. It used to post the
//      literal 'claude_agent', so flipping the model while on "Claude Code CLI (this
//      server)" silently moved the whole workspace to the browser-brokered agent.
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mountFromIndex } from './helpers/fixture-dom.js';
import { S } from '../ask-ck/CK-main/CK_server/static/js/state.js';
import { applyClaudeMode, restoreLLMUI, claudeRoutingFromUI }
  from '../ask-ck/CK-main/CK_server/static/js/llm.js';

function radios(method) {
  return `<label><input type="radio" name="llmAuthMethod" value="local_llm" ${method === 'local_llm' ? 'checked' : ''}></label>
          <label><input type="radio" name="llmAuthMethod" value="claude_agent" ${method === 'claude_agent' ? 'checked' : ''}></label>
          <label><input type="radio" name="llmAuthMethod" value="claude_code" ${method === 'claude_code' ? 'checked' : ''}></label>
          <span id="llmStatus"></span>`;
}

let posted;
beforeEach(() => {
  document.body.innerHTML = radios('claude_code');
  mountFromIndex('claudeAgentRow', 'claudeRoutingRow');     // the REAL markup, drift-detected
  S.currentSession = null;
  window.lastLLMConfig = null;
  posted = [];
  vi.stubGlobal('fetch', vi.fn(async (url, opts) => {
    posted.push({ url, body: JSON.parse(opts.body) });
    const c = { provider: 'claude', ...JSON.parse(opts.body), has_key: true };
    return { ok: true, json: async () => ({ llm_config: c }) };
  }));
});
afterEach(() => { vi.unstubAllGlobals(); });

describe('the routing selects', () => {
  it('post alongside the model, with blank meaning "same"', async () => {
    document.querySelector('input[name="claudeMode"][value="opus"]').checked = true;
    document.getElementById('claudeUnitModel').value = 'sonnet';
    await applyClaudeMode();
    expect(posted).toHaveLength(1);
    expect(posted[0].body).toMatchObject({
      provider: 'claude', model: 'opus', unit_model: 'sonnet', match_model: '',
    });
  });

  it('are restored from the stored config', () => {
    window.lastLLMConfig = { provider: 'claude', auth_method: 'claude_code', model: 'opus',
                             unit_model: 'sonnet', match_model: null, has_key: true };
    restoreLLMUI();
    expect(document.getElementById('claudeUnitModel').value).toBe('sonnet');
    expect(document.getElementById('claudeMatchModel').value).toBe('');
    expect(claudeRoutingFromUI()).toEqual({ unit_model: 'sonnet', match_model: '' });
  });
});

describe('the model toggle', () => {
  it('posts the CHECKED auth method, not a literal claude_agent', async () => {
    await applyClaudeMode();
    expect(posted[0].body.auth_method).toBe('claude_code');
    document.body.innerHTML = radios('claude_agent');
    mountFromIndex('claudeAgentRow', 'claudeRoutingRow');
    await applyClaudeMode();
    expect(posted[1].body.auth_method).toBe('claude_agent');
  });

  it('does nothing under a non-Claude method', async () => {
    document.body.innerHTML = radios('local_llm');
    mountFromIndex('claudeAgentRow', 'claudeRoutingRow');
    await applyClaudeMode();
    expect(posted).toHaveLength(0);
  });
});
