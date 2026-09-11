// Local ck-agent bridge (broker long-poll + CLI status probes).
import { registerActions } from './actions.js';
import { CK_SESSION_ID } from './session.js';
import { S } from './state.js';
import { escapeHtml } from './dom-helpers.js';
import { goToPanel } from './nav.js';

const CK_AGENT_URL = (window.CK_AGENT_URL || 'http://127.0.0.1:8765');

export async function probeLocalAgent() {
  // Ask the user's own ck-agent whether it's up, whether claude is installed, and — since
  // agent 1.1.0 — whether it is LOGGED IN and which versions are in play. An older agent
  // omits those fields; `logged_in` is then undefined (unknown), never false.
  try {
    const res = await fetch(CK_AGENT_URL + '/health', { method: 'GET' });
    if (!res.ok) return { ok: false };
    const s = await res.json();
    return {
      ok: true, claude_cli: !!s.claude_cli, path: s.claude_path, hint: s.hint,
      logged_in: (typeof s.logged_in === 'boolean') ? s.logged_in : undefined,
      org: s.org || null, cli_version: s.cli_version || null,
      agent_version: s.agent_version || null, update_error: s.update_error || null,
    };
  } catch (e) {
    return { ok: false, error: String(e) };
  }
}

// "Ready" means: agent up, CLI found, and not known to be logged out. An old agent that
// cannot report login is still treated as ready (unknown ≠ no), so upgrading the page
// never strands a seat that has not upgraded its agent yet.
export function agentIsReady(s) {
  return !!(s && s.ok && s.claude_cli && s.logged_in !== false);
}

// Layer 2 of keeping the CLI current (plan §4.1): ask the agent to run `claude update`.
// Separate from /health so health stays instant; the agent skips it while a job is
// running and says so. Returns null for an agent too old to have the route.
export async function requestAgentUpdate() {
  try {
    const res = await fetch(CK_AGENT_URL + '/update', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}',
    });
    if (res.status === 404) return null;
    if (!res.ok) return { ok: false, error: `HTTP ${res.status}` };
    return await res.json();
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
    // local_llm kept long-polling forever for jobs that can never be
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
// Guarded on the mode, so a tab sitting on local_llm does not start brokering
// just because it regained focus. ckBrokerLoop() is a no-op when the loop is alive and
// unstale, so this is safe to fire on every visibility change.
if (typeof document !== 'undefined' && document.addEventListener) {
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && ckAgentModeActive()) ckBrokerLoop();
  });
}

// The one line the user reads. Built from the probe and the update result; exported so
// the unit tests can pin what "ready" and "not ready" look like without a DOM.
export function renderAgentStatus(s, upd) {
  if (!s || !s.ok) {
    return `<span class="status-err">&#10007; Agent not reachable at ${escapeHtml(CK_AGENT_URL)}.</span> `
      + `Run the one-line seat setup from the Ask CK home page (or <code>cd ask-ck/agent &amp;&amp; ./run-agent.sh</code>), then retry.`;
  }
  if (!s.claude_cli) {
    return `<span class="status-err">&#10007; Agent up, but Claude CLI not found on your machine.</span> ${escapeHtml(s.hint || "Install Claude Code and run 'claude auth login'.")}`;
  }
  const parts = [];
  if (s.agent_version) parts.push(`agent ${escapeHtml(s.agent_version)}`);
  if (s.cli_version) {
    let v = `CLI ${escapeHtml(s.cli_version)}`;
    if (upd && upd.updated && upd.from) v += ` (updated from ${escapeHtml(upd.from)})`;
    parts.push(v);
  }
  if (upd && upd.skipped) parts.push(`update skipped: ${escapeHtml(upd.reason || 'job in flight')}`);
  else if (upd && upd.error) parts.push(`update failed: ${escapeHtml(upd.error)}`);
  else if (upd === null) parts.push('update: agent too old to support it — re-run the seat setup');
  if (s.logged_in === false) {
    parts.push('<span class="status-err">NOT logged in</span>');
    return `<span class="status-err">&#10007; Not ready</span> <span class="status-muted">(${parts.join(' · ')})</span><br>`
      + `<span class="status-err">${escapeHtml(s.hint || "Run 'claude auth login' on your machine, then retry.")}</span>`;
  }
  parts.push(s.logged_in === true
    ? `logged in${s.org ? ` as ${escapeHtml(s.org)}` : ''}`
    : 'login: unknown (old agent)');
  return `<span class="status-ok">&#10003; Local agent ready</span> <span class="status-muted">(${parts.join(' · ')})</span><br>`
    + `<span class="status-muted">Prompts will run on YOUR machine against YOUR own seat while this tab is open.</span>`;
}

async function checkLocalAgent() {
  const resultDiv = document.getElementById('agentStatusResult');
  if (resultDiv) resultDiv.innerHTML = '<em class="status-muted">Checking your local agent…</em>';
  const s = await probeLocalAgent();
  let upd;
  if (s.ok && s.claude_cli) {
    if (resultDiv) resultDiv.innerHTML = '<em class="status-muted">Agent up — checking for a Claude CLI update…</em>';
    upd = await requestAgentUpdate();
    // The update may have changed the version or the login view; re-probe for the line.
    if (upd && (upd.updated || upd.health)) {
      const fresh = upd.health ? { ok: true, claude_cli: !!upd.health.claude_cli, path: upd.health.claude_path,
        hint: upd.health.hint, logged_in: (typeof upd.health.logged_in === 'boolean') ? upd.health.logged_in : undefined,
        org: upd.health.org || null, cli_version: upd.health.cli_version || null,
        agent_version: upd.health.agent_version || null } : await probeLocalAgent();
      if (fresh.ok) Object.assign(s, fresh);
    }
  }
  if (!resultDiv) return;
  resultDiv.innerHTML = renderAgentStatus(s, upd);
}

// ---------------------------------------------------------------------------
// Seat setup (plan §3.2 / §3.3): the splash page's one-liners carry THIS server's origin,
// filled in at load so nothing is hard-coded; and `?seat-check=1`, which the setup script
// opens when it finishes, makes the page run the authoritative check itself and show it
// where the user will look for it (LLM → Configure).
// ---------------------------------------------------------------------------
export function seatSetupCommands(origin) {
  const o = String(origin || '').replace(/\/+$/, '');
  return {
    windows: `irm ${o}/setup/setup.ps1 | iex`,
    ubuntu: `curl -fsSL ${o}/setup/setup.sh | bash`,
  };
}

export function fillSeatSetupSnippets(doc = document, origin = window.location.origin) {
  const cmds = seatSetupCommands(origin);
  const w = doc.getElementById('seatSetupWindows');
  const u = doc.getElementById('seatSetupUbuntu');
  if (w) w.textContent = cmds.windows;
  if (u) u.textContent = cmds.ubuntu;
  return cmds;
}

async function copySeatSetup(ev) {
  const btn = ev && ev.currentTarget ? ev.currentTarget : (ev && ev.target);
  const id = btn && btn.dataset ? btn.dataset.target : '';
  const el = id ? document.getElementById(id) : null;
  if (!el) return;
  const flash = (text) => { const old = btn.textContent; btn.textContent = text; setTimeout(() => { btn.textContent = old; }, 2000); };
  // navigator.clipboard exists only in a SECURE context. Ask CK is served over plain http from
  // a LAN address, so on every real seat it is undefined and the old fallback merely selected
  // the text with no feedback — "Copy button doesn't work" (Windows demo, 2026-09-11). The
  // legacy execCommand('copy') still works on http for a user-initiated click.
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(el.textContent);
      flash('Copied');
      return;
    }
  } catch (_) { /* fall through to the legacy path */ }
  try {
    const r = document.createRange(); r.selectNodeContents(el);
    const s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
    const ok = document.execCommand && document.execCommand('copy');
    flash(ok ? 'Copied' : 'Selected — press Ctrl+C');
  } catch (_e) {
    flash('Select the line and press Ctrl+C');
  }
}

export function seatCheckRequested(search = window.location.search) {
  try { return new URLSearchParams(search).get('seat-check') === '1'; } catch (_) { return false; }
}

if (typeof document !== 'undefined' && typeof window !== 'undefined' && window.location) {
  try { fillSeatSetupSnippets(); } catch (_) {}
  if (seatCheckRequested()) {
    // Go where the result is shown, then run the check the setup script deferred to us.
    // Deferred a tick so the boot navigation in main.js has finished.
    setTimeout(() => {
      try { goToPanel('panel-llm-config'); } catch (_) {}
      checkLocalAgent();
    }, 0);
  }
}

// Register this tool's data-action handlers.
registerActions({
  checkLocalAgent,
  copySeatSetup,
});
