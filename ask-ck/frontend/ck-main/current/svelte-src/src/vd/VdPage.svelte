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

  let { server, agent, preselect = null, openRun = null, saveScript = defaultSave, pollMs = 5000 } = $props();

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
  const finalizeBlockers = $derived([
    !run && 'no run yet',
    run && runState !== 'done' && 'the latest run has not finished cleanly',
    repaired.some(r => !(compare[r.path] && compare[r.path].saved)) && 'a repaired copy is waiting for your approval',
    !reviewed && 'the review has not been written yet (test-mode §11.2)',
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
    const t = setInterval(watchMarkers, pollMs);
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
    {#each reviews as r (r.path)}
      <div class="tc-card"><div class="tc-card-head">Review of {r.case}</div>
        {#if reviewText[r.path]}<pre class="tc-pre">{reviewText[r.path]}</pre>
        {:else}<button type="button" class="btn btn-secondary btn-compact-small" onclick={() => loadReview(r)}>Read the review</button>{/if}</div>
    {/each}
    {#each repaired as r (r.path)}
      {@const c = compare[r.path]}
      <div class="tc-card"><div class="tc-card-head">Repaired copy of {r.case}</div>
        <div class="tc-small">{r.path} — the session's numbered changes are in its work/repairs.md (Logs). Approving overwrites the saved script through the PyTest Creator's save; it then reads as edited outside its units.</div>
        {#if !c}<button type="button" class="btn btn-secondary btn-compact-small" onclick={() => loadCompare(r)}>Compare with the saved script</button>
        {:else if c.busy}<span class="tc-small">Loading…</span>
        {:else}
          {#if c.error}<div class="tc-problem">{c.error}</div>{/if}
          {#if c.code}
            {@const d = changed(c.original, c.code)}
            <div class="tc-small">{d.removed} line(s) removed, {d.added} added.</div>
            <div class="tc-panes"><pre class="tc-pre tc-log">{c.original}</pre><pre class="tc-pre tc-log">{c.code}</pre></div>
            {#if c.saved}<span class="tc-check">✓ saved to the PyTest Creator</span>
            {:else}<button type="button" class="btn btn-primary btn-compact-small vd-approve" onclick={() => approve(r)}>Approve → save</button>{/if}
          {/if}
        {/if}
      </div>
    {/each}
    {#if !repaired.length && !reviews.length}
      <div class="tc-small">No repaired copy or review yet — both appear here when the session reports them.</div>
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
