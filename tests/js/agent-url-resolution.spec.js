// The page must be able to find the local ck-agent on a port other than 8765.
//
// THE NEED (2026-09-16, mrfuji@LavenderTown, a homelab seat reached over an SSH tunnel): the
// browser hard-coded the agent at 127.0.0.1:8765, but VS Code already held 8765 (and Portainer
// held 9000). There was no way to point the page at a free port, so the local-CLI transport was
// unusable on any machine whose 8765 is taken. `resolveAgentUrl` adds the override: a
// `?agent-port=`/`?agent-url=` query param, remembered in localStorage, restricted to localhost
// so a crafted link can never send a seat's Claude traffic off-box.
import { describe, it, expect, vi } from 'vitest';

vi.mock('../../ask-ck/frontend/ck-main/current/shared/actions.js', () => ({ registerActions: () => {} }));
vi.mock('../../ask-ck/frontend/ck-main/current/shared/session.js', () => ({ CK_SESSION_ID: 'sess-test' }));
vi.mock('../../ask-ck/frontend/ck-main/current/shared/state.js', () => ({ S: {} }));
vi.mock('../../ask-ck/frontend/ck-main/current/shared/nav.js', () => ({ goToPanel: () => {} }));

const { resolveAgentUrl } = await import('../../ask-ck/frontend/ck-main/current/llm-config/agent.js');

function fakeStore(seed = {}) {
  const data = { ...seed };
  return {
    data,
    getItem: (k) => (k in data ? data[k] : null),
    setItem: (k, v) => { data[k] = v; },
  };
}
const KEY = 'ck.agentUrl';
const DEFAULT = 'http://127.0.0.1:8765';

describe('resolveAgentUrl', () => {
  it('defaults to 127.0.0.1:8765 with no param, store or injection', () => {
    expect(resolveAgentUrl()).toBe(DEFAULT);
    expect(resolveAgentUrl({ search: '', store: fakeStore() })).toBe(DEFAULT);
  });

  it('?agent-port builds a localhost URL and remembers it', () => {
    const store = fakeStore();
    expect(resolveAgentUrl({ search: '?agent-port=8770', store })).toBe('http://127.0.0.1:8770');
    expect(store.data[KEY]).toBe('http://127.0.0.1:8770');           // persisted for next reload
  });

  it('a remembered value is used when no param is present', () => {
    const store = fakeStore({ [KEY]: 'http://127.0.0.1:8770' });
    expect(resolveAgentUrl({ search: '', store })).toBe('http://127.0.0.1:8770');
  });

  it('a fresh ?agent-port overrides and replaces the remembered one', () => {
    const store = fakeStore({ [KEY]: 'http://127.0.0.1:8770' });
    expect(resolveAgentUrl({ search: '?agent-port=8781', store })).toBe('http://127.0.0.1:8781');
    expect(store.data[KEY]).toBe('http://127.0.0.1:8781');
  });

  it('?agent-url accepts a localhost URL and rejects an off-box one', () => {
    const store = fakeStore();
    expect(resolveAgentUrl({ search: '?agent-url=http://localhost:9100', store })).toBe('http://localhost:9100');
    // an attacker-controlled host is refused — the agent is always local — so it falls through
    const store2 = fakeStore();
    expect(resolveAgentUrl({ search: '?agent-url=http://evil.example.com:9100', store: store2 })).toBe(DEFAULT);
    expect(store2.data[KEY]).toBeUndefined();                        // nothing off-box is remembered
  });

  it('rejects an out-of-range or non-numeric port and falls through', () => {
    expect(resolveAgentUrl({ search: '?agent-port=0' })).toBe(DEFAULT);
    expect(resolveAgentUrl({ search: '?agent-port=70000' })).toBe(DEFAULT);
    expect(resolveAgentUrl({ search: '?agent-port=abc' })).toBe(DEFAULT);
  });

  it('a query param wins over an injected window.CK_AGENT_URL, which wins over the store', () => {
    const store = fakeStore({ [KEY]: 'http://127.0.0.1:8770' });
    // param beats everything
    expect(resolveAgentUrl({ search: '?agent-port=8781', store, injected: 'http://127.0.0.1:8799' }))
      .toBe('http://127.0.0.1:8781');
    // no param: the explicit injection beats the remembered value
    expect(resolveAgentUrl({ search: '', store, injected: 'http://127.0.0.1:8799' }))
      .toBe('http://127.0.0.1:8799');
  });

  it('a store that throws (private mode) never crashes the resolve', () => {
    const throwing = { getItem: () => { throw new Error('blocked'); }, setItem: () => { throw new Error('blocked'); } };
    expect(resolveAgentUrl({ search: '?agent-port=8770', store: throwing })).toBe('http://127.0.0.1:8770');
    expect(resolveAgentUrl({ search: '', store: throwing })).toBe(DEFAULT);
  });
});
