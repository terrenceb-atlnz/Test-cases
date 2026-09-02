// The broker loop must be revivable. A stuck `ckBrokerRunning` used to make it
// permanently dead for the life of the page.
//
// THE DEFECT (2026-09-01, AWPTCM-T33351 — a 30-minute hang)
// ---------------------------------------------------------
// `ckBrokerRunning` was set true on entry and cleared in exactly ONE place: the clean
// mode-switch exit. There was no `finally`. Any other way out of the loop left the flag
// stuck true forever, and because BOTH restart callers in llm.js begin
// `if (ckBrokerRunning) return;` — one commented "idempotent", the other "resume serving
// jobs for a returning agent user" — neither could ever revive it. Only a reload could.
//
// A backgrounded tab is such a way out: Chromium (and Vivaldi) freezes a hidden tab after
// ~5 minutes, suspending the pending `await fetch` so it never settles and no `finally`
// would run either. Measured in the journal — polls perfectly regular at ~25.4s from
// 12:45:08 to 12:51:54, then stopped dead. No tail-off, which is what separates a renderer
// freeze from timer throttling. The user clicked Generate two minutes later; the page was
// responsive, the broker was not, and the job was enqueued for nobody.
//
// So the fix has to be liveness-based, not flag-based: a `finally` alone cannot help a
// frozen renderer, because nothing in a frozen renderer runs.
//
// Source-level, matching pt-testbox-setups.spec.js and pt-provenance-body.spec.js: the
// loop is a module-scoped async function driven by fetch and timers, and asserting on its
// STRUCTURE is what pins the invariants. Comments are stripped before every assertion —
// this file's prose quotes the very identifiers it reasons about.
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const SRC = readFileSync(
  resolve(HERE, '../ask-ck/CK-main/CK_server/static/js/agent.js'), 'utf8');

// Strip block and line comments so prose can never satisfy an assertion.
const CODE = SRC.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');

describe('broker loop liveness', () => {
  it('always releases the running claim, on every exit path', () => {
    // Was `ckBrokerRunning = false`. Since 2026-09-02 the claim is a per-worker COUNT,
    // so releasing it is a decrement — but the property is identical: it must happen in
    // a finally, on every exit path, or a dead worker's claim outlives it.
    expect(CODE).toMatch(/\}\s*finally\s*\{/);
    const fin = CODE.slice(CODE.lastIndexOf('} finally {'));
    expect(fin).toContain('ckBrokerWorkers--');
  });

  it('records when a long-poll actually completed', () => {
    // The flag is a claim; this is evidence. Without it there is nothing to detect a
    // loop that stopped without saying so.
    expect(CODE).toContain('ckBrokerLastPollAt = Date.now()');
    // And it must be stamped on the poll itself, not only at loop entry — otherwise a
    // loop that dies on its first fetch looks alive forever.
    const pollIdx = CODE.indexOf('/api/agent/next');
    const stampAfterPoll = CODE.indexOf('ckBrokerLastPollAt = Date.now()', pollIdx);
    expect(stampAfterPoll).toBeGreaterThan(pollIdx);
  });

  it('lets a caller restart a loop whose polls have gone stale', () => {
    // The whole point: the early return must be conditional on liveness, not on the
    // flag alone. `if (ckBrokerRunning) return;` is the bug.
    // `if (workers > 0) return;` unqualified is the bug — the early return must be
    // conditional on LIVENESS, not on the claim alone.
    expect(CODE).not.toMatch(/if\s*\(\s*ckBrokerWorkers\s*>\s*0\s*\)\s*return\s*;/);
    expect(CODE).toMatch(/if\s*\(\s*ckBrokerWorkers\s*>\s*0\s*&&\s*!ckBrokerIsStale\(\)\s*\)\s*return/);
  });

  it('treats a loop as stale only well after the long-poll window', () => {
    // agent.js long-polls with wait=25, so anything at or under ~25s would declare a
    // healthy loop dead mid-poll and start a second one against the same session.
    expect(CODE).toContain('wait=25');
    const m = CODE.match(/CK_BROKER_STALE_MS\s*=\s*([0-9_]+)/);
    expect(m).toBeTruthy();
    expect(Number(m[1].replace(/_/g, ''))).toBeGreaterThan(25_000);
  });

  it('retires a superseded loop so a thawed tab cannot broker twice', () => {
    // If a frozen loop resumes after a replacement started, two brokers would claim jobs
    // for one session. The generation counter makes the older one stand down.
    expect(CODE).toContain('ckBrokerGeneration');
    expect(CODE).toMatch(/myGeneration\s*!==\s*ckBrokerGeneration/);
  });

  it('abandons a job the server no longer wants, instead of finishing it', () => {
    // THE DEFECT (2026-09-02, AWPTCM-T44297): cancel freed only the server. This loop
    // stayed inside the ck-agent fetch until the local CLI finished, so it stopped
    // long-polling for the whole remaining budget of work already discarded — and the next
    // LLM action the user clicked had nobody to claim it. Measured: generate cancelled
    // 6.8s in at 16:13:22, last poll 16:13:16, never polled again.
    expect(CODE).toContain('job_wanted/');
    expect(CODE).toContain('AbortController');
    // The abort signal must actually be attached to the run fetch, or the watcher is
    // decorative and the loop still blocks.
    const runIdx = CODE.indexOf("/run'");
    const runCall = CODE.slice(runIdx - 200, runIdx + 700);
    expect(runCall).toContain('signal:');
  });

  it('does not post a result for a job nobody is waiting for', () => {
    // Delivering an abandoned job is harmless server-side (it is gone from _inflight) but
    // the loop must return to polling IMMEDIATELY rather than doing more work first.
    expect(CODE).toMatch(/if\s*\(\s*abandoned\s*\)\s*continue\s*;/);
  });

  it('tells its own ck-agent to stop, so the local CLI is not left burning a seat', () => {
    // Freeing the loop fixes the starvation; killing the process is what stops paying for
    // an answer that has already been thrown away.
    expect(CODE).toContain("'/cancel'");
    // job_id must reach ck-agent on the run, or /cancel has nothing to look up.
    const runIdx = CODE.indexOf("/run'");
    expect(CODE.slice(runIdx, runIdx + 900)).toContain('job_id: job.job_id');
  });

  it('never abandons a job because the wanted-check itself failed', () => {
    // A transport hiccup on a boolean must not throw away a long, expensive generation.
    // The check is guarded on an explicit `=== false`, not on falsiness.
    expect(CODE).toMatch(/wanted\s*===\s*false/);
  });

  it('revives the broker when the tab becomes visible again', () => {
    // The one event that reliably fires when a frozen renderer thaws, and exactly when
    // the user is about to click something that needs the broker.
    expect(CODE).toContain("addEventListener('visibilitychange'");
    const idx = CODE.indexOf("addEventListener('visibilitychange'");
    const handler = CODE.slice(idx, idx + 300);
    expect(handler).toContain('ckBrokerLoop()');
    // Guarded on the mode: a tab on local_llm/claude_code must not start brokering just
    // because it regained focus.
    expect(handler).toContain('ckAgentModeActive()');
  });
});

// ---------------------------------------------------------------------------
// CONCURRENCY (2026-09-02) — the broker is N workers, not one loop.
//
// The single serial component in the whole transport was this file. The server has
// always handed out N at once (`_queues` is a FIFO, `_inflight` is keyed by job id,
// every job carries its own Event, and `submit` blocks in its own request thread), and
// `ck_agent.py` has always RUN N at once (ThreadingHTTPServer, `_RUNNING` keyed by job_id
// under a lock). One `while(true)` loop claiming one job at a time is what made 29
// per-step generations take 29 turns.
//
// The hazard this introduces, and the reason ckBrokerActive exists: with every worker
// inside a 600s job nobody long-polls, so poll-time alone reports the broker as dead
// exactly when it is working hardest — and the visibilitychange handler would then bump
// the generation and retire all of them. Liveness is therefore two signals, the same
// shape as the server's `session_present`: a recent poll OR a job in flight.
describe('broker concurrency', () => {
  it('spawns more than one worker', () => {
    expect(CODE).toContain('function ckBrokerWorker');
    expect(CODE).toMatch(/for \(let i = 0; i < n; i\+\+\) ckBrokerWorker/);
    // The count must come from the knob, and the knob's default must actually be > 1 —
    // a loop that runs exactly once is the serial broker with extra machinery.
    expect(CODE).toMatch(/const n = ckBrokerWorkerCount\(\)/);
    const def = CODE.match(/CK_BROKER_WORKERS_DEFAULT\s*=\s*(\d+)/);
    expect(def, 'a numeric default must be declared').not.toBeNull();
    expect(Number(def[1])).toBeGreaterThan(1);
  });

  it('does not await the workers it spawns', () => {
    // `await`ing them would serialise the very thing this change exists to parallelise.
    const sup = CODE.slice(CODE.indexOf('export async function ckBrokerLoop'),
                          CODE.indexOf('async function ckBrokerWorker'));
    expect(sup).not.toMatch(/await\s+ckBrokerWorker/);
    expect(sup).not.toMatch(/Promise\.all/);
  });

  it('tracks live workers as a count, not a boolean claim', () => {
    // A boolean cannot say "3 of 4 workers retired", and the last one out must be the
    // one that clears the claim.
    expect(CODE).toContain('ckBrokerWorkers++');
    expect(CODE).toContain('ckBrokerWorkers--');
    expect(CODE).not.toContain('ckBrokerRunning');
  });

  it('releases a worker claim unconditionally, not only for the current generation', () => {
    // A superseded worker that skipped its decrement would leak the liveness signal for
    // the life of the page — the exact defect the generation guard was added to fix,
    // reintroduced from the other side.
    const fin = SRC.slice(CODE.lastIndexOf('} finally {'));
    expect(fin).toContain('ckBrokerWorkers--');
    expect(fin).not.toMatch(/myGeneration === ckBrokerGeneration\)\s*ckBrokerWorkers/);
  });

  it('counts a busy worker as alive', () => {
    expect(CODE).toContain('ckBrokerActive++');
    expect(CODE).toContain('ckBrokerActive--');
    const stale = CODE.slice(CODE.indexOf('function ckBrokerIsStale'),
                            CODE.indexOf('const CK_BROKER_WORKERS_DEFAULT'));
    expect(stale).toMatch(/ckBrokerActive > 0/);
  });

  it('decrements the active count on every exit from a job', () => {
    // There are three ways out of a job body: deliver, `continue` on abandonment, and a
    // throw caught by the outer handler. A finally is the only construct that covers all
    // three — an increment paired with a plain decrement after the deliver would leak on
    // the other two and permanently wedge the broker as "busy", hence never revivable.
    expect(CODE).toMatch(/\}\s*finally\s*\{\s*ckBrokerActive--;\s*\}/);
  });

  it('takes the worker count from storage, with a safe default and bounds', () => {
    // Every worker is a separate `claude` process on the user's machine, so the right
    // number is a property of that machine.
    expect(CODE).toContain('CK_BROKER_WORKERS_DEFAULT');
    expect(CODE).toMatch(/localStorage\.getItem\('ckBrokerWorkers'\)/);
    expect(CODE).toMatch(/v >= 1 && v <= 16/);
  });

  it('survives storage being unavailable', () => {
    // Private windows and blocked site data throw on access, not return null.
    const fn = CODE.slice(CODE.indexOf('function ckBrokerWorkerCount'),
                         CODE.indexOf('export async function ckBrokerLoop'));
    expect(fn).toContain('try {');
    expect(fn).toContain('catch');
  });
});
