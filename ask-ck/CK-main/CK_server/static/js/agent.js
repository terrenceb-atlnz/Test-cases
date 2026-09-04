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
let ckBrokerWorkers = 0;      // live worker loops (was a single boolean claim)

// Workers currently INSIDE a job, i.e. awaiting the local CLI rather than long-polling.
// This is the second liveness signal, and it is what makes N workers safe: with every
// worker busy on a 600s generation nobody polls, so poll-time alone reports the whole
// broker as dead exactly when it is working hardest. Same two-signal shape as the
// server's `session_present` (a recent poll OR a claimed job) — see agent_jobs.py.
let ckBrokerActive = 0;

// When the broker last COMPLETED a long-poll. This, not the boolean above, is what
// says the loop is alive.
//
// THE DEFECT THIS EXISTS FOR (2026-09-01, cost a 30-minute hang on AWPTCM-T33351)
// ------------------------------------------------------------------------------
// `ckBrokerRunning` was set true on entry and cleared in exactly ONE place: the clean
// mode-switch exit below. There was no `finally`. So any other way out of the loop left
// the flag stuck true for the LIFE OF THE PAGE, and because both restart callers in
// llm.js begin `if (ckBrokerRunning) return;`, the loop could never be revived — only a
// reload fixed it.
//
// A backgrounded tab is exactly such a way out. Chromium (and Vivaldi, which is
// Chromium) freezes a hidden tab after ~5 minutes, suspending the pending `await fetch`
// so it never settles and no `finally` would run either. Measured in the journal: polls
// were perfectly regular at ~25.4s from 12:45:08 to 12:51:54, then stopped dead — no
// tail-off, which is what distinguishes a freeze from timer throttling. The user clicked
// Generate two minutes later; the page was responsive, the broker was not. The job was
// enqueued for nobody, and `submit` waited out its whole budget.
//
// So liveness is measured, not asserted. A caller may restart the loop whenever the last
// completed poll is older than the long-poll window plus margin, whatever the flag says.
let ckBrokerLastPollAt = 0;

// Bumped when a stale loop is superseded, so the old one retires if it ever wakes up.
let ckBrokerGeneration = 0;

// The server holds a long-poll for ~25s (`wait=25`, capped at 55 server-side). A live
// loop therefore touches ckBrokerLastPollAt at least every ~25s plus request overhead.
// 90s is generous enough that a slow network or a briefly-throttled (not frozen) tab is
// never mistaken for a dead loop, and short enough that tabbing back revives it long
// before a human notices.
const CK_BROKER_STALE_MS = 90_000;

// How often to check that a running job is still wanted. 3s is cheap (one boolean) and
// bounds how long an abandoned local run can keep the broker busy after a Stop.
const CK_CANCEL_POLL_MS = 3_000;

function ckBrokerIsStale() {
  if (ckBrokerActive > 0) return false;   // busy is alive — see ckBrokerActive
  return ckBrokerLastPollAt > 0 && (Date.now() - ckBrokerLastPollAt) > CK_BROKER_STALE_MS;
}

// How many jobs this browser will broker CONCURRENTLY (2026-09-02).
//
// The server has always been able to hand out N at once — `_queues` is a FIFO, `_inflight`
// is keyed by job id and every job carries its own Event, and `submit` blocks in its own
// request thread. `ck_agent.py` has always been able to RUN N at once — ThreadingHTTPServer,
// with `_RUNNING` keyed by job_id under a lock. The single serial component in the whole
// transport was this file: one loop, claiming one job, awaiting it to completion.
//
// Overriding: localStorage.ckBrokerWorkers. Every worker is a separate `claude` process on
// the user's own machine, so the right number is a property of THAT machine, not of this
// code — 4 is a conservative default that still turns 29 per-step calls into ~8 waves.
const CK_BROKER_WORKERS_DEFAULT = 4;

function ckBrokerWorkerCount() {
  let n = CK_BROKER_WORKERS_DEFAULT;
  try {
    const v = parseInt(window.localStorage.getItem('ckBrokerWorkers') || '', 10);
    if (Number.isFinite(v) && v >= 1 && v <= 16) n = v;
  } catch (_) { /* private window / blocked storage — the default is correct */ }
  return n;
}

function ckAgentModeActive() {
  const c = (S.currentSession && S.currentSession.llm_config) || window.lastLLMConfig || {};
  const am = (c.auth_method || '').toLowerCase();
  const radio = document.querySelector('input[name="llmAuthMethod"]:checked');
  return am === 'claude_agent' || (radio && radio.value === 'claude_agent');
}

// Start (or revive) the broker. N workers, each an independent claim-run-post loop.
export async function ckBrokerLoop() {
  // "Running" is a CLAIM, and a stale claim used to be permanent (see ckBrokerLastPollAt).
  // Believe it only while polls are arriving or a job is in flight.
  if (ckBrokerWorkers > 0 && !ckBrokerIsStale()) return;
  if (ckBrokerWorkers > 0) {
    // Adopting stale workers. Any that are merely suspended rather than dead will resume,
    // see the generation bump and retire at the top of their next lap — a superseded
    // worker cannot outlive the bump, and the new ones are the ones known to be alive.
    ckBrokerGeneration++;
  }
  const myGeneration = ckBrokerGeneration;
  ckBrokerLastPollAt = Date.now();   // grace: do not judge a worker before its first poll
  const n = ckBrokerWorkerCount();
  // Deliberately NOT awaited: these run concurrently for the life of the mode.
  for (let i = 0; i < n; i++) ckBrokerWorker(myGeneration);
}

async function ckBrokerWorker(myGeneration) {
  ckBrokerWorkers++;
  try {
  while (true) {
    // A superseded loop stops. Without this, a thawed tab would run two brokers against
    // one session, and both would claim jobs.
    if (myGeneration !== ckBrokerGeneration) return;
    // The loop must not outlive the mode that started it. ckAgentModeActive() was
    // written for exactly this and was never wired in, so a tab switched to
    // local_llm/claude_code kept long-polling forever for jobs that can never be
    // queued — and on a server outage fell back to a 2s retry, polling HARDER than
    // when it had work. Clearing the flag lets a later switch back to claude_agent
    // start a fresh loop via either caller in llm.js.
    if (!ckAgentModeActive()) return;
    try {
      // Long-poll for the next job (server holds up to ~25s). Header added by patchFetch.
      const res = await fetch(`/api/agent/next?session=${encodeURIComponent(CK_SESSION_ID)}&wait=25`);
      ckBrokerLastPollAt = Date.now();   // the loop is demonstrably alive
      if (!res.ok) { await new Promise(r => setTimeout(r, 2000)); continue; }
      const data = await res.json();
      const job = data.job;
      if (!job) continue;           // timed out with no work — poll again
      ckBrokerActive++;             // busy is alive — see ckBrokerIsStale
      try {
      // Run it on the user's own local agent.
      let content = '', error = false, usage = null, cost = null;
      // ABANDON WORK NOBODY WANTS (2026-09-02, AWPTCM-T44297).
      //
      // Cancelling from the UI used to free only the SERVER. This loop stayed inside the
      // fetch below until the local CLI finished — so it stopped long-polling for the whole
      // remaining budget of work already thrown away, and the next LLM action the user
      // clicked had nobody to claim it. Measured: a generate cancelled 6.8s in at 16:13:22,
      // last poll 16:13:16, never polled again; the Extract Sequence a minute later failed
      // with "nobody picked this up". With budgets floored to 1800s that is up to half an
      // hour of dead broker per Stop.
      //
      // So while the job runs, watch whether the server still wants it, and abort the
      // moment it does not. Aborting returns us to the top of the loop immediately.
      const ac = new AbortController();
      let abandoned = false;
      let settled = false;
      const watcher = (async () => {
        while (!settled) {
          await new Promise(r => setTimeout(r, CK_CANCEL_POLL_MS));
          if (settled) return;
          try {
            const w = await fetch(`/api/agent/job_wanted/${encodeURIComponent(job.job_id)}`);
            if (!w.ok) continue;                       // transport hiccup — never abandon on it
            const wj = await w.json();
            if (wj.wanted === false) { abandoned = true; ac.abort(); return; }
          } catch (_) { /* keep working — a failed check is not a cancellation */ }
        }
      })();
      try {
        const ares = await fetch(CK_AGENT_URL + '/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          signal: ac.signal,
          // Bound the local run by the SAME budget the server is waiting on. This used
          // to be a hard-coded 600 while the server waited on whatever the caller asked
          // for — gather_fragments asks 300, so the server gave up at 300s and this
          // machine kept working for another 300 on a result that was then discarded.
          // The fallback covers a server older than job.timeout (2026-08-27).
          //
          // job_id rides along so a cancel can KILL the local process rather than merely
          // stop waiting for it — without it, an abandoned `claude` keeps burning the
          // user's own seat to produce an answer that is already discarded.
          //
          // system: the server's steer, which the agent passes as the CLI's
          // --system-prompt (2026-09-04). Replacing the CLI's harness prompt is what lets
          // the shared prefix of a fan-out actually hit the prompt cache.
          body: JSON.stringify({ job_id: job.job_id, prompt: job.prompt, model: job.model,
                                 timeout: job.timeout || 600, system: job.system || '' }),
        });
        const ajson = await ares.json();
        content = ajson.content || '';
        error = !!ajson.error;
        usage = ajson.usage || null;                                  // token accounting from the local CLI
        cost = (ajson.total_cost_usd != null) ? ajson.total_cost_usd : null;
      } catch (e) {
        if (abandoned) {
          // Tell our own agent to stop; the server already knows and is not waiting.
          try {
            await fetch(CK_AGENT_URL + '/cancel', {
              method: 'POST', headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ job_id: job.job_id }),
            });
          } catch (_) { /* best effort — freeing the loop is the part that matters */ }
        }
        content = 'ERROR: local agent unreachable — is ck-agent running? ' + e;
        error = true;
      } finally {
        settled = true;
      }
      if (abandoned) continue;   // nobody is waiting; do not post a result for a dead job
      // Deliver the completion back to the shared server. Forwarding usage lets
      // the token badge + debug-log populate for agent-brokered Claude calls.
      await fetch('/api/agent/result', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: job.job_id, content, error, usage, total_cost_usd: cost }),
      });
      } finally { ckBrokerActive--; }
    } catch (e) {
      await new Promise(r => setTimeout(r, 2000));   // transient error — back off, keep going
    }
  }
  } finally {
    // ALWAYS release this worker's claim. Before this, the flag was cleared on exactly one
    // exit path (the mode switch), so any other way out wedged the loop permanently. A
    // `finally` cannot help a FROZEN tab — nothing in a frozen renderer runs — which is
    // why staleness detection above exists as well; this covers the ordinary escapes
    // (a throw from ckAgentModeActive, an unhandled rejection, a superseded generation).
    // Unconditional, unlike the old generation-guarded clear: each worker owns exactly one
    // count, and a superseded worker that failed to decrement would leak the broker's
    // liveness signal permanently.
    ckBrokerWorkers--;
  }
}

// Tabbing back is the moment to repair a broker that died while hidden — it is the one
// event that reliably fires when a frozen renderer thaws, and it is exactly when the user
// is about to click something that needs the broker.
//
// Guarded on the mode, so a tab sitting on local_llm/claude_code does not start brokering
// just because it regained focus. ckBrokerLoop() is a no-op when the loop is alive and
// unstale, so this is safe to fire on every visibility change.
if (typeof document !== 'undefined' && document.addEventListener) {
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && ckAgentModeActive()) ckBrokerLoop();
  });
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
