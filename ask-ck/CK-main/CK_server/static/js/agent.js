// Local ck-agent bridge (broker long-poll + CLI status probes).
import { registerActions } from './actions.js';
import { CK_SESSION_ID } from './session.js';
import { S } from './state.js';
import { escapeHtml } from './dom-helpers.js';

const CK_AGENT_URL = (window.CK_AGENT_URL || 'http://127.0.0.1:8765');

export async function probeLocalAgent() {
  // Ask the user's own ck-agent whether it's up and whether claude is installed.
  try {
    const res = await fetch(CK_AGENT_URL + '/health', { method: 'GET' });
    if (!res.ok) return { ok: false };
    const s = await res.json();
    return { ok: true, claude_cli: !!s.claude_cli, path: s.claude_path, hint: s.hint };
  } catch (e) {
    return { ok: false, error: String(e) };
  }
}

// The broker loop: while claude_agent is the active LLM mode, continuously
// long-poll the shared server for prompt jobs for THIS session, run each on the
// user's own local agent, and post the completion back. This is the transport
// that lets the shared server use each user's own Claude seat.
let ckBrokerRunning = false;

function ckAgentModeActive() {
  const c = (S.currentSession && S.currentSession.llm_config) || window.lastLLMConfig || {};
  const am = (c.auth_method || '').toLowerCase();
  const radio = document.querySelector('input[name="llmAuthMethod"]:checked');
  return am === 'claude_agent' || (radio && radio.value === 'claude_agent');
}

export async function ckBrokerLoop() {
  if (ckBrokerRunning) return;      // single loop per tab
  ckBrokerRunning = true;
  while (true) {
    try {
      // Long-poll for the next job (server holds up to ~25s). Header added by patchFetch.
      const res = await fetch(`/api/agent/next?session=${encodeURIComponent(CK_SESSION_ID)}&wait=25`);
      if (!res.ok) { await new Promise(r => setTimeout(r, 2000)); continue; }
      const data = await res.json();
      const job = data.job;
      if (!job) continue;           // timed out with no work — poll again
      // Run it on the user's own local agent.
      let content = '', error = false, usage = null, cost = null;
      try {
        const ares = await fetch(CK_AGENT_URL + '/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: job.prompt, model: job.model, timeout: 600 }),
        });
        const ajson = await ares.json();
        content = ajson.content || '';
        error = !!ajson.error;
        usage = ajson.usage || null;                                  // token accounting from the local CLI
        cost = (ajson.total_cost_usd != null) ? ajson.total_cost_usd : null;
      } catch (e) {
        content = 'ERROR: local agent unreachable — is ck-agent running? ' + e;
        error = true;
      }
      // Deliver the completion back to the shared server. Forwarding usage lets
      // the token badge + debug-log populate for agent-brokered Claude calls.
      await fetch('/api/agent/result', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: job.job_id, content, error, usage, total_cost_usd: cost }),
      });
    } catch (e) {
      await new Promise(r => setTimeout(r, 2000));   // transient error — back off, keep going
    }
  }
}

async function checkLocalAgent() {
  const resultDiv = document.getElementById('agentStatusResult');
  if (resultDiv) resultDiv.innerHTML = '<em class="status-muted">Checking your local agent…</em>';
  const s = await probeLocalAgent();
  if (!resultDiv) return;
  if (!s.ok) {
    resultDiv.innerHTML = `<span class="status-err">&#10007; Agent not reachable at ${escapeHtml(CK_AGENT_URL)}.</span> `
      + `Start it: <code>cd ask-ck/agent &amp;&amp; ./run-agent.sh</code>, then retry.`;
  } else if (!s.claude_cli) {
    resultDiv.innerHTML = `<span class="status-err">&#10007; Agent up, but Claude CLI not found on your machine.</span> ${escapeHtml(s.hint || "Install Claude Code and run 'claude' -> /login.")}`;
  } else {
    resultDiv.innerHTML = `<span class="status-ok">&#10003; Local agent ready</span> <span class="status-muted">(claude at ${escapeHtml(s.path || '')})</span><br><span class="status-muted">Prompts will run on YOUR machine against YOUR own seat while this tab is open.</span>`;
  }
}

// Register this tool's data-action handlers.
registerActions({
  checkLocalAgent,
});
