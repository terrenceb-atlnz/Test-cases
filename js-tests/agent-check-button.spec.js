// "Check my local agent" must tell the truth about the seat.
//
// THE DEFECT (2026-09-10, demo day). The button called /health, which reported only
// "is a `claude` binary present". An installed-but-logged-out CLI, or one two months
// stale, both rendered "✓ Local agent ready". The same day the server's CLI failed every
// call because it was pinned at 2.1.207, and nothing on any screen said so.
//
// Since agent 1.1.0 /health carries `logged_in`, `cli_version`, `agent_version`, and the
// button also POSTs /update (plan PLAN-seat-setup-and-per-seat-llm.md §4.1 layer 2). These
// tests pin the rendered line and the readiness rule, and — structurally — that the button
// asks for the update AFTER health and never while the agent is unreachable.
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const SRC = readFileSync(resolve(HERE, '../ask-ck/CK-main/CK_server/static/js/agent.js'), 'utf8');
const CODE = SRC.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');

vi.mock('../ask-ck/CK-main/CK_server/static/js/actions.js', () => ({ registerActions: () => {} }));
vi.mock('../ask-ck/CK-main/CK_server/static/js/session.js', () => ({ CK_SESSION_ID: 'sess-test' }));
vi.mock('../ask-ck/CK-main/CK_server/static/js/state.js', () => ({ S: {} }));

let agent;
beforeEach(async () => {
  agent = await import('../ask-ck/CK-main/CK_server/static/js/agent.js');
});

const up = (extra = {}) => ({ ok: true, claude_cli: true, path: '/home/u/.local/bin/claude',
  agent_version: '1.1.0', cli_version: '2.1.267', logged_in: true, org: 'Allied Telesis Labs NZ', ...extra });

describe('agentIsReady', () => {
  it('is ready only when up, CLI found and not known to be logged out', () => {
    expect(agent.agentIsReady(up())).toBe(true);
    expect(agent.agentIsReady(up({ logged_in: false }))).toBe(false);
    expect(agent.agentIsReady(up({ claude_cli: false }))).toBe(false);
    expect(agent.agentIsReady({ ok: false })).toBe(false);
  });
  it('treats an OLD agent that cannot report login as ready (unknown is not "no")', () => {
    expect(agent.agentIsReady(up({ logged_in: undefined }))).toBe(true);
  });
});

describe('renderAgentStatus', () => {
  it('shows versions and the org when ready', () => {
    const html = agent.renderAgentStatus(up(), { ok: true, updated: false });
    expect(html).toContain('Local agent ready');
    expect(html).toContain('agent 1.1.0');
    expect(html).toContain('CLI 2.1.267');
    expect(html).toContain('logged in as Allied Telesis Labs NZ');
  });
  it('says "updated from" when the update changed the CLI', () => {
    const html = agent.renderAgentStatus(up({ cli_version: '2.1.267' }),
      { ok: true, updated: true, from: '2.1.207', to: '2.1.267' });
    expect(html).toContain('updated from 2.1.207');
  });
  it('never says ready for a logged-out CLI, and names the fix', () => {
    const html = agent.renderAgentStatus(up({ logged_in: false, hint: "Claude CLI is installed but not logged in: run 'claude auth login'." }), { ok: true });
    expect(html).not.toContain('Local agent ready');
    expect(html).toContain('Not ready');
    expect(html).toContain('NOT logged in');
    expect(html).toContain('claude auth login');
  });
  it('reports an update skipped for a job in flight, and a failed update', () => {
    expect(agent.renderAgentStatus(up(), { ok: true, skipped: true, reason: 'job in flight (1); retry when the run finishes' }))
      .toContain('update skipped: job in flight');
    expect(agent.renderAgentStatus(up(), { ok: false, error: 'claude update exited 7: network down' }))
      .toContain('update failed: claude update exited 7');
  });
  it('tells an old agent to re-run the seat setup', () => {
    expect(agent.renderAgentStatus(up({ agent_version: null, logged_in: undefined }), null))
      .toContain('agent too old');
  });
  it('points an unreachable agent at the one-line seat setup', () => {
    const html = agent.renderAgentStatus({ ok: false }, undefined);
    expect(html).toContain('not reachable');
    expect(html).toContain('seat setup');
  });
  it('escapes what the agent reports', () => {
    const html = agent.renderAgentStatus(up({ org: '<img src=x onerror=alert(1)>' }), { ok: true });
    expect(html).not.toContain('<img');
    expect(html).toContain('&lt;img');
  });
});

describe('checkLocalAgent structure', () => {
  it('requests the update only after a healthy probe, with a JSON content type', () => {
    const fn = CODE.slice(CODE.indexOf('async function checkLocalAgent'));
    const body = fn.slice(0, fn.indexOf('\n}\n') + 3);
    expect(body).toMatch(/probeLocalAgent\(\)/);
    expect(body.indexOf('probeLocalAgent()')).toBeLessThan(body.indexOf('requestAgentUpdate()'));
    expect(body).toMatch(/if \(s\.ok && s\.claude_cli\)[\s\S]*requestAgentUpdate\(\)/);
    const upd = CODE.slice(CODE.indexOf('export async function requestAgentUpdate'));
    expect(upd.slice(0, upd.indexOf('\n}\n'))).toContain("'Content-Type': 'application/json'");
  });
});
