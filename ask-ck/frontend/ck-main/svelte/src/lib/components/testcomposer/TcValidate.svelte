<script>
// @ts-nocheck

  // Test Composer — the "Validate a Script" tab (ask-ck/plans/PLAN-test-validation.md): one saved
  // script → /test-mode on the seat (probe, preflight, run, repair on a scratch copy until the run is
  // clean, review) → approve the repaired copy → Finalize. Launch goes through THIS seat's ck-agent
  // (PLAN-agent-sessions D7). Ported from current/svelte-src/src/vd/VdPage.svelte.
  import { onMount } from 'svelte';
  import AgentWindow from './AgentWindow.svelte';
  import ResultsTable from './ResultsTable.svelte';
  import RunsList from './RunsList.svelte';
  import SetupFields from './SetupFields.svelte';
  import Button from '../Button.svelte';
  import LlmButton from '../LlmButton.svelte';
  import { loadSetup, runBody, saveSetup } from './testComposerModel.js';

  import { httpServer, httpAgent } from '../../services/testcomposer/testComposerService.js';
  let { server = httpServer(), agent = httpAgent(), preselect = null, openRun = null, saveScript = defaultSave, pollMs = 5000 } = $props();

  /** Approval goes through the PyTest Creator's own save, so its units⇄script binding reports the edit. */
  async function defaultSave(caseKey, code) {
    const r = await fetch(`/api/pytest-create/save_script/${encodeURIComponent(caseKey)}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code }) });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(typeof d.detail === 'string' ? d.detail : `HTTP ${r.status}`);
    return d;
  }

  let scripts = $state([]);
  let chosen = $state(null);                 // script path
  let setup = $state(Object.assign({ testbox: '', consoles: '', pduIp: '', outlets: '', constraints: '', email: '' }, loadSetup()));
  let health = $state(null);
  let busy = $state(false);
  let status = $state({ msg: '', bad: false });
  let run = $state(null);                    // {runId, sessionId}
  let runState = $state(null);
  let refreshKey = $state(0);
  let markers = $state([]);

  const script = $derived(scripts.find(s => s.path === chosen));
  const sessionsOk = $derived(health && health.sessions && health.sessions.available);
  const canLaunch = $derived(!!script && sessionsOk && setup.testbox && setup.consoles && !busy);
  // device-testing's markers (test-mode §11, da37c2d): `REPAIRED <case> <path>`, `REVIEWED <case> <path>`.
  const parse = (l) => { const [, c, ...p] = l.split(/\s+/); return { case: c, path: p.join(' ') }; };
  const repaired = $derived(markers.filter(l => l.startsWith('REPAIRED ')).map(parse));
  const reviews = $derived(markers.filter(l => l.startsWith('REVIEWED ')).map(parse));
  const reviewed = $derived(reviews.length > 0);
  let compare = $state({});     // path → {code, original, busy, error, saved}
  let reviewText = $state({});  // path → text

  async function loadCompare(r) {
    compare = { ...compare, [r.path]: { busy: true } };
    try {
      const d = await server(`/runs/${encodeURIComponent(run.runId)}/repaired?path=${encodeURIComponent(r.path)}&case=${encodeURIComponent(r.case)}`);
      compare = { ...compare, [r.path]: { code: d.code, original: d.original } };
    } catch (e) { compare = { ...compare, [r.path]: { error: e.message } }; }
  }

  async function approve(r) {
    const c = compare[r.path];
    if (!c || !c.code) return;
    try { await saveScript(r.case, c.code); compare = { ...compare, [r.path]: { ...c, saved: true } }; }
    catch (e) { compare = { ...compare, [r.path]: { ...c, error: `Not saved: ${e.message}. Open ${r.case} in the PyTest Creator (it holds the case), then approve again.` } }; }
  }

  async function loadReview(r) {
    try { reviewText = { ...reviewText, [r.path]: (await server(`/runs/${encodeURIComponent(run.runId)}/file?path=${encodeURIComponent(r.path)}`)).data }; }
    catch (e) { reviewText = { ...reviewText, [r.path]: 'Could not read the review: ' + e.message }; }
  }

  /** Changed-line count between two texts (a quick summary, not a full diff). */
  function changed(a, b) {
    const A = (a || '').split('\n'), B = (b || '').split('\n');
    const setA = new Set(A), setB = new Set(B);
    return { removed: A.filter(x => !setB.has(x)).length, added: B.filter(x => !setA.has(x)).length };
  }
  // A clean run turns Finalize on (Terrence 2026-10-12; PLAN-test-validation §6): it finished,
  // the review exists, and no repaired copy waits for approval. The server re-checks all of it,
  // and refuses before any write while V0 (the Zephyr new-version capture) is open.
  const finalizeBlockers = $derived([
    !run && 'no run yet',
    run && runState !== 'done' && 'the latest run has not finished cleanly',
    repaired.some(r => !(compare[r.path] && compare[r.path].saved)) && 'a repaired copy is waiting for your approval',
    !reviewed && 'the review has not been written yet (test-mode §11.2)',
  ].filter(Boolean));
  let finalizing = $state(false);
  let finalized = $state(null);

  async function finalize() {
    if (finalizeBlockers.length || finalizing) return;
    finalizing = true;
    const c = reviews[0].case;
    try {
      finalized = await server(`/runs/${encodeURIComponent(run.runId)}/finalize/${encodeURIComponent(c)}`, { method: 'POST' });
      setStatus(`${c} finalized: it has left the PyTest Creator and the Objective / Test Case lists.`);
      loadScripts();
    } catch (e) {
      setStatus(`Finalize did not run for ${c}: ${e.message}`, true);
    } finally { finalizing = false; }
  }

  /** The PyTest Creator's "test the new script?" pop-up opens this page on one script. */
  export function select(key) {
    preselect = key;
    return loadScripts();
  }

// A launch only starts the seat session (the LLM work runs in it afterwards, shown in the
  // agent window), so its LlmButton has nothing to cancel: a busy click does nothing.
  const noStop = () => {};

  function setStatus(msg, bad = false) { status = { msg, bad }; }

  async function loadScripts() {
    try {
      scripts = (await server('/scripts')).scripts;
      if (preselect) chosen = (scripts.find(s => s.path === preselect || s.case_key === preselect) || {}).path || chosen;
    } catch (e) { setStatus('Could not list scripts: ' + e.message, true); }
  }

  async function checkAgent() {
    try { health = await agent.health(); } catch (e) { health = { error: e.message }; }
  }

  async function launch() {
    if (!canLaunch) return;
    busy = true;
    saveSetup(setup);
    try {
      const body = runBody('validation', setup, { cases: [{ key: script.case_key, kind: 'script', script: script.path }] });
      const created = await server('/runs', { method: 'POST', body: JSON.stringify(body) });
      const started = await agent.start({ run_id: created.run_id, handoff: created.handoff, mode: 'campaign' });
      if (!started.ok) throw new Error(started.error || 'the seat agent refused the session');
      run = { runId: created.run_id, sessionId: started.session_id };
      markers = [];
      finalized = null;
      refreshKey += 1;
      setStatus(`Launched ${created.run_id} on ${body.testbox}.`);
    } catch (e) {
      setStatus('Launch failed: ' + e.message, true);
    } finally { busy = false; }
  }

  async function watchMarkers() {
    if (!run) return;
    try {
      const d = await server(`/runs/${encodeURIComponent(run.runId)}/events`);
      markers = d.events.filter(e => e.kind === 'marker').map(e => e.line);
    } catch (_) { /* the table shows errors */ }
  }

  onMount(() => {
    loadScripts();
    checkAgent();
    if (openRun) run = { runId: openRun, sessionId: null };
    const t = setInterval(watchMarkers, pollMs);
    return () => clearInterval(t);
  });
</script>

<div class="tool-page tc-page">
  <div class="section-description">Run one saved script on a test bench through your seat's agent. The session probes the bench, checks the script's topology needs, runs it, repairs a <i>copy</i> until the run is clean, and reviews it. Nothing changes the saved script until you approve; Finalize then marks the case automatable in Zephyr and takes it off the authoring lists.</div>

  <div class="tc-step"><span class="tc-step-n">1</span> Script</div>
  <div class="tc-line">
    <div class="tc-row tc-full">
      <div class="tc-scripts">
        {#each scripts as s (s.path)}
          <label class="tc-script-row" class:is-chosen={chosen === s.path}>
            <input type="radio" name="vd-script" value={s.path} bind:group={chosen}>
            <span class="tc-key">{s.case_key || '?'}</span> <span>{s.path}</span>
            <span class="tc-small tc-row-end">saved {String(s.saved_at || '').slice(0, 10)} · {s.iterations || 0} iteration(s)</span>
            {#if s.finalized_at}<span class="tc-badge tc-state-done">finalized</span>{/if}
          </label>
        {/each}
        {#if !scripts.length}<div class="tc-small tc-empty">No saved scripts — save one from the PyTest Creator first.</div>{/if}
      </div>
    </div>
  </div>

  <div class="tc-step"><span class="tc-step-n">2</span> Where it Runs</div>
  <div class="tc-line">
    <SetupFields bind:setup />
  </div>

  <div class="tc-step"><span class="tc-step-n">3</span> Launch</div>
  <div class="tc-line">
    <div class="tc-row">
      <LlmButton label="Launch Validation" verb="Launching…" disabled={!canLaunch} onRun={launch} onStop={noStop} />
      <div class="tc-status" class:is-bad={status.bad} role="status">{status.msg}</div>
    </div>
    <div class="tc-row">
      <span class="tc-small">
        {#if !health}checking your seat agent…
        {:else if health.error}Your seat agent is not reachable ({health.error}) — run the seat setup from the home page.
        {:else if !sessionsOk}Your seat agent cannot run sessions: {health.sessions ? health.sessions.reason : 'agent too old — re-run the seat setup'}
        {:else}Seat agent {health.agent_version} ready · Agent SDK {health.sessions.sdk_version} · device-testing at {health.sessions.dt_root}{/if}
      </span>
    </div>
  </div>

  {#if run}
    <div class="tc-step"><span class="tc-step-n">4</span> The Session — {run.runId}</div>
    {#key run.runId}
      <div class="tc-line">
        <div class="tc-row tc-full">
          <AgentWindow runId={run.runId} sessionId={run.sessionId} {agent} {server} onstate={(s) => { runState = s; if (['done', 'stopped', 'error'].includes(s)) refreshKey += 1; }} />
        </div>
      </div>
      <div class="tc-step"><span class="tc-step-n">5</span> Results</div>
      <div class="tc-line">
        <div class="tc-row tc-full">
          <ResultsTable runId={run.runId} {server} />
        </div>
      </div>
    {/key}

    <div class="tc-step"><span class="tc-step-n">6</span> Review and Repaired Copy</div>
    <div class="tc-line">
      {#each reviews as r (r.path)}
        <div class="tc-row tc-full">
          <div class="tc-card"><div class="tc-card-head">Review of {r.case}</div>
            {#if reviewText[r.path]}<pre class="tc-pre">{reviewText[r.path]}</pre>
            {:else}<Button variant="outline" on:click={() => loadReview(r)}>Read the review</Button>{/if}
          </div>
        </div>
      {/each}
      {#each repaired as r (r.path)}
        {@const c = compare[r.path]}
        <div class="tc-row tc-full">
          <div class="tc-card"><div class="tc-card-head">Repaired copy of {r.case}</div>
            <div class="tc-small">{r.path} — the session's numbered changes are in its work/repairs.md (Logs). Approving overwrites the saved script through the PyTest Creator's save; it then reads as edited outside its units.</div>
            {#if !c}<Button variant="outline" on:click={() => loadCompare(r)}>Compare with the saved script</Button>
            {:else if c.busy}<span class="tc-small">Loading…</span>
            {:else}
              {#if c.error}<div class="tc-problem">{c.error}</div>{/if}
              {#if c.code}
                {@const d = changed(c.original, c.code)}
                <div class="tc-small">{d.removed} line(s) removed, {d.added} added.</div>
                <div class="tc-panes">
                  <div><div class="tc-small">Saved</div><pre class="tc-pre tc-pre-tall">{c.original}</pre></div>
                  <div><div class="tc-small">Repaired</div><pre class="tc-pre tc-pre-tall">{c.code}</pre></div>
                </div>
                {#if c.saved}<span class="tc-check">✓ saved to the PyTest Creator</span>
                {:else}<Button variant="primary" on:click={() => approve(r)}>Approve → save</Button>{/if}
              {/if}
            {/if}
          </div>
        </div>
      {/each}
      {#if !repaired.length && !reviews.length}
        <div class="tc-row tc-small">No repaired copy or review yet — both appear here when the session reports them.</div>
      {/if}
    </div>

    <div class="tc-step"><span class="tc-step-n">7</span> Finalize</div>
    <div class="tc-line">
      <div class="tc-row">
        <Button variant="primary" loading={finalizing} disabled={finalizeBlockers.length > 0 || !!finalized} on:click={finalize}>{finalizing ? 'Finalizing…' : 'Finalize'}</Button>
        {#if finalized}<span class="tc-check">✓ finalized {String(finalized.finalized_at || '').slice(0, 16)}</span>
        {:else if finalizeBlockers.length}<ul class="tc-blockers">{#each finalizeBlockers as b}<li>{b}</li>{/each}</ul>
        {:else}<span class="tc-small">Writes Zephyr first (step 1's note, then version 3.0), then takes the case off the lists. Zephyr's "new version" request is not captured yet (V0), so for now the server says so and writes nothing.</span>{/if}
      </div>
    </div>
  {/if}

  <div class="tc-step tc-earlier">Earlier Validation Runs</div>
  <RunsList {server} kind="validation" {refreshKey} onopen={(id) => { run = { runId: id, sessionId: null }; markers = []; finalized = null; }} />
</div>

<style>
  /* Same look as TcRun and TcCompose: numbered step circles with an accent line running down
     each step's content. The shared rules are copied, not imported — styles are scoped. */
  .tc-page {
    margin-top: 1rem;
    width: 100%;
  }

  .section-description {
    color: var(--color-text-muted);
    font-size: 0.94rem;
    padding-bottom: 1rem;
  }

  /* --- Numbered step headings -------------------------------------------------------- */
  .tc-step {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 8px 0 8px;
    font-weight: 600;
    color: var(--color-text-heading);
  }

  .tc-step-n {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 3.5rem;
    height: 3.5rem;
    border-radius: 50%;
    border: 4px solid var(--color-accent);
    background: var(--color-bg-content);
    color: var(--color-text-heading);
    font-size: 1.1rem;
  }

  .tc-earlier {
    margin: 1rem 0 1rem 0;
    padding-top: 1rem;
    border-top: 1px solid var(--color-border-surface);
    width: 100%;
    font-size: 0.88rem;
    color: var(--color-text-muted);
    text-transform: uppercase;
  }

  /* --- Lines, rows, notes, status ---------------------------------------------------- */
  .tc-line {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    margin: 4px 0;
    border-left: 4px solid var(--color-accent);
    padding-left: 2.2rem;
    margin-left: 1.6rem;
    width: 100%;
  }

  /* One row inside a step — each takes the step's full width, so rows stack. */
  .tc-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px;
    width: 100%;
    margin-bottom: 0.8rem;
  }

  /* A row holding a block (script list, card) rather than a line of controls. */
  .tc-full {
    display: block;
  }

  .tc-small {
    color: var(--color-text-muted);
    font-size: 0.94rem;
  }

  /* Same look as ZephyrPage's .zt-status. */
  .tc-status {
    min-height: 18px;
    margin: 6px 0;
    color: var(--color-text-muted);
    font-size: 0.88rem;
    font-style: italic;
  }

  .tc-status.is-bad,
  .tc-problem {
    color: var(--color-error);
    font-style: normal;
  }

  .tc-check {
    color: var(--color-success);
    font-weight: 600;
  }

  .tc-key {
    font-family: 'Roboto Mono Variable', 'Roboto Mono', monospace;
    font-size: 0.8rem;
    color: var(--color-analysis-key);
  }

  .tc-badge {
    padding: 1px 8px;
    border: 1px solid var(--color-border-surface);
    border-radius: 10px;
    color: var(--color-text-muted);
    font-size: 0.75rem;
    white-space: nowrap;
  }

  .tc-state-done {
    color: var(--color-success);
    border-color: currentColor;
  }

  /* --- 1 Script: the saved-script list ----------------------------------------------- */
  .tc-scripts {
    max-height: 260px;
    overflow: auto;
    border: 1px solid var(--color-border-surface);
    border-radius: 10px;
    background: var(--color-bg-surface);
  }

  .tc-script-row {
    display: flex;
    align-items: baseline;
    gap: 10px;
    padding: 6px 12px;
    border-bottom: 1px solid var(--color-border-surface);
    color: var(--color-text);
    font-size: 0.9rem;
    cursor: pointer;
  }

  .tc-script-row:last-child {
    border-bottom: 0;
  }

  .tc-script-row:hover {
    background: color-mix(in srgb, var(--color-accent) 6%, transparent);
  }

  .tc-script-row.is-chosen {
    background: color-mix(in srgb, var(--color-accent) 14%, transparent);
  }

  /* The saved date sits at the right end of its row. */
  .tc-row-end {
    margin-left: auto;
    white-space: nowrap;
  }

  .tc-empty {
    padding: 8px 12px;
  }

  /* --- 6 Review and repaired copy ------------------------------------------------------ */
  .tc-card {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
    padding: 12px 16px;
    border: 1px solid var(--color-border-surface);
    border-radius: 10px;
    background: var(--color-bg-surface);
  }

  .tc-card-head {
    font-weight: 600;
    color: var(--color-text-heading);
  }

  /* Saved and repaired side by side; stacked on narrow screens. */
  .tc-panes {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: 12px;
    width: 100%;
  }

  @media (max-width: 900px) {
    .tc-panes { grid-template-columns: minmax(0, 1fr); }
  }

  /* The review and the saved / repaired scripts: plain text in the code font inside a rounded
     border (as AgentWindow's tool output), not a code window. */
  .tc-pre {
    width: 100%;
    max-height: 40vh;
    margin: 0;
    padding: 8px 12px;
    overflow: auto;
    border: 1px solid var(--color-border-surface);
    border-radius: 10px;
    color: var(--color-text);
    font-family: Consolas, 'Courier New', monospace;
    font-size: 12px;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }

  .tc-pre-tall {
    max-height: 50vh;
  }

  /* --- 7 Finalize ---------------------------------------------------------------------- */
  .tc-blockers {
    margin: 0 0 0 1.2em;
    padding: 0;
    color: var(--color-text-muted);
    font-size: 0.88rem;
  }
</style>
