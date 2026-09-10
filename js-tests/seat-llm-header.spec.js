// The seat's LLM choice rides on every /api call as X-CK-LLM (plan §5, decision D1).
//
// session.js already patches window.fetch to add X-CK-Session; since 2026-09-10 it also
// reads the seat's stored choice (localStorage.draftingLLMConfig, written by llm.js on
// Apply and on the model toggles) and sends it as `auth;model;unit;match`. Absent = the
// seat has never chosen = the server uses the site default. These pin the header's
// presence, format and scope (never to the localhost agent or a foreign host), and that
// llm.js stores the routing fields too — otherwise the header would drop them.
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const LLM_SRC = readFileSync(resolve(HERE, '../ask-ck/CK-main/CK_server/static/js/llm.js'), 'utf8')
  .replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');

vi.mock('../ask-ck/CK-main/CK_server/static/js/state.js', () => ({ S: { currentPanel: 'panel-main' } }));

let session;
let origFetch;
beforeEach(async () => {
  localStorage.clear();
  sessionStorage.clear();
  origFetch = vi.fn(async () => ({ ok: true }));
  window.fetch = origFetch;
  vi.resetModules();
  session = await import('../ask-ck/CK-main/CK_server/static/js/session.js');
});

const lastHeaders = () => new Headers(origFetch.mock.calls.at(-1)[1].headers);

describe('seatLlmHeaderValue', () => {
  it('formats auth;model;unit;match and strips separators', () => {
    expect(session.seatLlmHeaderValue({ auth_method: 'claude_agent', model: 'opus', unit_model: 'sonnet', match_model: null }))
      .toBe('claude_agent;opus;sonnet;');
    expect(session.seatLlmHeaderValue({ auth_method: 'local_llm', model: 'vllm;fast\r\n' })).toBe('local_llm;vllmfast;;');
    expect(session.seatLlmHeaderValue(null)).toBe('');
    expect(session.seatLlmHeaderValue({ model: 'x' })).toBe('');
  });
});

describe('fetch patch', () => {
  it('sends no X-CK-LLM when the seat has never chosen (site default applies)', async () => {
    await window.fetch('/api/wizard/llm_config');
    expect(lastHeaders().get('X-CK-LLM')).toBeNull();
    expect(lastHeaders().get('X-CK-Session')).toMatch(/^sess-/);
  });
  it('sends the stored seat choice on same-origin /api calls', async () => {
    localStorage.setItem('draftingLLMConfig', JSON.stringify({ provider: 'claude', auth_method: 'claude_agent', model: 'opus', unit_model: 'sonnet' }));
    await window.fetch('/api/pytest-create/generate/AWPTCM-T1', { method: 'POST' });
    expect(lastHeaders().get('X-CK-LLM')).toBe('claude_agent;opus;sonnet;');
  });
  it('never attaches it to the localhost agent or a foreign host', async () => {
    localStorage.setItem('draftingLLMConfig', JSON.stringify({ auth_method: 'claude_agent', model: 'opus' }));
    await window.fetch('http://127.0.0.1:8765/health');
    expect(origFetch.mock.calls.at(-1)[1]).toBeUndefined();
    await window.fetch('https://example.com/api/x');
    expect(origFetch.mock.calls.at(-1)[1]).toBeUndefined();
  });
  it('never sends a retired stored choice, and drops it so the seat falls back to the site default', async () => {
    // A browser that last applied the removed server-side mode must not 400 on every call.
    localStorage.setItem('draftingLLMConfig', JSON.stringify({ provider: 'claude', auth_method: 'claude_code', model: 'opus' }));
    await window.fetch('/api/wizard/llm_config');
    expect(lastHeaders().get('X-CK-LLM')).toBeNull();
    expect(localStorage.getItem('draftingLLMConfig')).toBeNull();
    // ...and remembers the drop, so LLM → Configure can say so once (plan §11.3, D14).
    expect(localStorage.getItem(session.SEAT_LLM_RETIRED_KEY)).toBe('claude_code');
    expect(session.seatLlmHeaderValue({ auth_method: 'api_key', model: 'x' })).toBe('');
    expect(session.seatLlmHeaderValue({ auth_method: 'grok_cli', model: 'x' })).toBe('');
  });
  it('reads localStorage at call time, so an Apply changes the very next request', async () => {
    localStorage.setItem('draftingLLMConfig', JSON.stringify({ auth_method: 'local_llm', model: 'vllm-fast' }));
    await window.fetch('/api/a');
    expect(lastHeaders().get('X-CK-LLM')).toBe('local_llm;vllm-fast;;');
    localStorage.setItem('draftingLLMConfig', JSON.stringify({ auth_method: 'claude_agent', model: 'sonnet' }));
    await window.fetch('/api/b');
    expect(lastHeaders().get('X-CK-LLM')).toBe('claude_agent;sonnet;;');
  });
});

describe('llm.js stores what the header needs (structural)', () => {
  it('stores unit_model and match_model alongside the model', () => {
    const fn = LLM_SRC.slice(LLM_SRC.indexOf('export function storeSeatLlm'));
    const body = fn.slice(0, fn.indexOf('\n}\n'));
    expect(body).toContain('unit_model');
    expect(body).toContain('match_model');
    // every success path uses the one store helper — no stray localStorage.setItem of the key
    expect(LLM_SRC.match(/localStorage\.setItem\('draftingLLMConfig'/g) || []).toHaveLength(1);
  });
  it('the site default is a separate action and plain Apply posts only set_llm_config', () => {
    expect(LLM_SRC).toContain("'/api/wizard/set_site_default_llm'");
    const apply = LLM_SRC.slice(LLM_SRC.indexOf('async function setLLMConfig'));
    expect(apply.slice(0, apply.indexOf('\n}\n'))).not.toContain('set_site_default_llm');
    expect(LLM_SRC).toMatch(/registerActions\(\{[\s\S]*setSiteDefaultLLM/);
  });
  it('the seat\'s stored choice is preferred over the case session when restoring the UI', () => {
    const fn = LLM_SRC.slice(LLM_SRC.indexOf('export function restoreLLMUI'));
    const body = fn.slice(0, fn.indexOf('\n}\n'));
    expect(body.indexOf('storedSeatLlm()')).toBeGreaterThan(-1);
    expect(body.indexOf('storedSeatLlm()')).toBeLessThan(body.indexOf('S.currentSession'));
  });
});
