<script>
  // Validation (ask-ck/plans/PLAN-test-validation.md): one saved script → /test-mode on the seat
  // (probe, preflight, run, repair on a scratch copy until the run is clean, review) → approve the
  // repaired copy → Finalize. Launch goes through THIS seat's ck-agent (PLAN-agent-sessions D7).
  import { onMount } from 'svelte';
  import AgentWindow from '../tc/AgentWindow.svelte';
  import ResultsTable from '../tc/ResultsTable.svelte';
  import RunsList from '../tc/RunsList.svelte';
  import SetupFields from '../tc/SetupFields.svelte';
  import { loadSetup, runBody, saveSetup } from '../tc/api.js';

  let { server, agent, preselect = null, openRun = null } = $props();

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
  const repaired = $derived(markers.filter(l => l.startsWith('REPAIRED ')));
  const reviewed = $derived(markers.some(l => l.startsWith('REVIEWED ')));
  const finalizeBlockers = $derived([
    !run && 'no run yet',
    run && runState !== 'done' && 'the latest run has not finished cleanly',
    repaired.length && 'a repaired copy is waiting for your approval',
    !reviewed && 'the review has not been written yet (PLAN-test-validation §5)',
    'Zephyr\'s "new version" request is not captured yet (V0) — Finalize writes nothing until it is',
  ].filter(Boolean));

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
    const t = setInterval(watchMarkers, 5000);
    return () => clearInterval(t);
  });
</script>

<div class="section tc-page">
  <div class="section-heading">Validation</div>
  <div class="section-description">Run one saved script on a test bench through your seat's agent. The session probes the bench, checks the script's topology needs, runs it, repairs a <i>copy</i> until the run is clean, and reviews it. Nothing changes the saved script until you approve; Finalize then marks the case automatable in Zephyr and takes it off the authoring lists.</div>

  <div class="tc-step"><span class="tc-step-n">1</span> Script</div>
  <div class="tc-scripts">
    {#each scripts as s (s.path)}
      <label class="tc-script-row" class:is-chosen={chosen === s.path}>
        <input type="radio" name="vd-script" value={s.path} bind:group={chosen}>
        <span class="tc-key">{s.case_key || '?'}</span> <span>{s.path}</span>
        <span class="tc-small">saved {String(s.saved_at || '').slice(0, 10)} · {s.iterations || 0} iteration(s)</span>
        {#if s.finalized_at}<span class="tc-badge tc-state-done">finalized</span>{/if}
      </label>
    {/each}
    {#if !scripts.length}<div class="tc-small">No saved scripts — save one from the PyTest Creator first.</div>{/if}
  </div>

  <div class="tc-step"><span class="tc-step-n">2</span> Where it runs</div>
  <SetupFields bind:setup />

  <div class="tc-step"><span class="tc-step-n">3</span> Launch</div>
  <div class="tc-line">
    <button type="button" id="vd-launch" class="btn btn-primary" disabled={!canLaunch} onclick={launch}>{busy ? 'Launching…' : 'Launch Validation'}</button>
    <span class="tc-small">
      {#if !health}checking your seat agent…
      {:else if health.error}Your seat agent is not reachable ({health.error}) — run the seat setup from the home page.
      {:else if !sessionsOk}Your seat agent cannot run sessions: {health.sessions ? health.sessions.reason : 'agent too old — re-run the seat setup'}
      {:else}Seat agent {health.agent_version} ready · Agent SDK {health.sessions.sdk_version} · device-testing at {health.sessions.dt_root}{/if}
    </span>
  </div>
  <div class="tc-status" class:is-bad={status.bad} role="status">{status.msg}</div>

  {#if run}
    <div class="tc-step"><span class="tc-step-n">4</span> The session — {run.runId}</div>
    {#key run.runId}
      <AgentWindow runId={run.runId} sessionId={run.sessionId} {agent} {server} onstate={(s) => { runState = s; if (['done', 'stopped', 'error'].includes(s)) refreshKey += 1; }} />
      <div class="tc-step"><span class="tc-step-n">5</span> Results</div>
      <ResultsTable runId={run.runId} {server} />
    {/key}

    <div class="tc-step"><span class="tc-step-n">6</span> Review and repaired copy</div>
    {#if repaired.length}
      {#each repaired as line}
        <div class="tc-card"><div class="tc-card-head">{line}</div>
          <div class="tc-small">Approving overwrites the saved script through the PyTest Creator's own save (it then reads as edited outside its units). Compare the copy in the Logs first.</div>
          <button type="button" class="btn btn-primary btn-compact-small" disabled title="Arrives with the repair loop (PLAN-test-validation V2)">Approve → save</button></div>
      {/each}
    {:else}
      <div class="tc-small">No repaired copy. The session's review appears in the window above{reviewed ? ' (written)' : ''}; a side-by-side review panel arrives with W3 (PLAN-test-validation §5).</div>
    {/if}

    <div class="tc-step"><span class="tc-step-n">7</span> Finalize</div>
    <div class="tc-line">
      <button type="button" id="vd-finalize" class="btn btn-primary" disabled>Finalize</button>
      <ul class="tc-blockers">{#each finalizeBlockers as b}<li>{b}</li>{/each}</ul>
    </div>
  {/if}

  <div class="tc-step">Earlier Validation runs</div>
  <RunsList {server} kind="validation" {refreshKey} onopen={(id) => { run = { runId: id, sessionId: null }; markers = []; }} />
</div>
