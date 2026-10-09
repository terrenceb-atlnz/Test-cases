<script>
  // Test Composer (ask-ck/plans/PLAN-test-composer.md §1): project → test bench → template (with what
  // it can run) → Validate the bench against the template → the live project tree filtered to
  // runnable cases → Start → results. Launches go through THIS seat's ck-agent (D7).
  import { onMount } from 'svelte';
  import AgentWindow from './AgentWindow.svelte';
  import ResultsTable from './ResultsTable.svelte';
  import RunsList from './RunsList.svelte';
  import SetupFields from './SetupFields.svelte';
  import TcTree from './TcTree.svelte';
  import { loadSetup, runBody, saveSetup } from './api.js';

  let { server, agent, preselect = null, openRun = null, pollMs = 4000 } = $props();

  // 1. project
  let source = $state('templated');             // templated | wiki
  let projects = $state([]);
  let projectId = $state('');
  let wikiUrl = $state('');
  let wiki = $state(null);                       // {title, variants}
  let variantPick = $state({});                  // index → ticked
  let wikiBusy = $state(false);
  // 2. setup + template
  let setup = $state(Object.assign({ testbox: '', consoles: '', pduIp: '', outlets: '', constraints: '', email: '' }, loadSetup()));
  let templates = $state([]);
  let template = $state('');
  let scripts = $state([]);
  // 3. validate
  let validateRun = $state(null);
  let validateState = $state(null);
  let validateMarkers = $state([]);
  let validateText = $state('');
  // 4. tree
  let tree = $state(null);
  let treeBusy = $state(false);
  let ticked = $state(new Set());
  let runnableOnly = $state(true);
  let previous = $state({});                     // case → "run id, verdict"
  // 5. start
  let startAfter = $state('');
  let run = $state(null);
  let refreshKey = $state(0);
  let health = $state(null);
  let status = $state({ msg: '', bad: false });
  let dryRun = $state(null);

  const project = $derived(source === 'templated' ? projects.find(p => p.id === projectId) || null : null);
  const plans = $derived(source === 'templated'
    ? (project ? project.plans : [])
    : (wiki ? wiki.variants.flatMap((v, i) => (variantPick[i] ? v.plans.map(p => p.key) : [])) : []));
  const version = $derived(project ? project.version : wiki ? ((wiki.variants.find((v, i) => variantPick[i]) || {}).version || null) : null);
  const tmpl = $derived(templates.find(t => t.name === template) || null);
  const scriptByCase = $derived(new Map(scripts.filter(s => s.case_key).map(s => [s.case_key, s])));
  const sessionsOk = $derived(health && health.sessions && health.sessions.available);
  // device-testing prints `PROBE <MATCH|MISMATCH|NEEDS-CHECK> <template>` (test-mode §1, da37c2d).
  const probe = $derived((validateMarkers.find(l => l.startsWith('PROBE ')) || '').split(/\s+/)[1] || null);
  const validated = $derived(probe === 'MATCH');
  const tickedCases = $derived(tree ? tree.plans.flatMap(p => p.cycles.flatMap(cy => cy.cases
    .filter(c => ticked.has(`${cy.key}/${c.key}`)).map(c => ({ key: c.key, cycle: cy.key })))) : []);

  function setStatus(msg, bad = false) { status = { msg, bad }; }
  function kindOf(key) { return scriptByCase.has(key) ? 'script' : 'manual'; }
  function runnable(key) {
    if (!tmpl) return false;
    return kindOf(key) === 'script' ? tmpl.runnable_scripts.includes(key) : tmpl.manual_cases.includes(key);
  }

  async function loadBasics() {
    try { projects = (await server('/projects')).projects; } catch (e) { setStatus('Projects: ' + e.message, true); }
    try { scripts = (await server('/scripts')).scripts; } catch (_) { /* shown via empty kinds */ }
    try { templates = (await server('/templates')).templates; } catch (e) { setStatus('Templates: ' + e.message, true); }
    try { health = await agent.health(); } catch (e) { health = { error: e.message }; }
  }

  async function readWiki() {
    if (!wikiUrl.trim()) return;
    wikiBusy = true;
    try {
      wiki = await server('/projects/from-wiki', { method: 'POST', body: JSON.stringify({ url: wikiUrl.trim() }) });
      variantPick = Object.fromEntries(wiki.variants.map((_, i) => [i, wiki.variants.length === 1]));
      setStatus(wiki.variants.length > 1 ? 'Several variants share this page — tick the ones this run is for.' : '');
    } catch (e) { setStatus(e.message, true); }
    finally { wikiBusy = false; }
  }

  async function launch(kind, extra) {
    saveSetup(setup);
    const created = await server('/runs', { method: 'POST', body: JSON.stringify(runBody(kind, setup, extra)) });
    const started = await agent.start({ run_id: created.run_id, handoff: created.handoff, mode: 'campaign' });
    if (!started.ok) throw new Error(started.error || 'the seat agent refused the session');
    return { runId: created.run_id, sessionId: started.session_id, handoff: created.handoff };
  }

  async function validate() {
    try {
      validateRun = await launch('composer-validate', { cases: [], template });
      validateMarkers = []; validateText = ''; validateState = 'starting';
      setStatus(`Validating ${setup.testbox} against ${template}…`);
    } catch (e) { setStatus('Validate failed: ' + e.message, true); }
  }

  async function watchValidate() {
    if (!validateRun) return;
    try {
      const d = await server(`/runs/${encodeURIComponent(validateRun.runId)}/events`);
      validateMarkers = d.events.filter(e => e.kind === 'marker').map(e => e.line);
      validateText = d.events.filter(e => e.kind === 'text' || e.kind === 'result').map(e => e.text || '').join('\n');
    } catch (_) { /* window shows errors */ }
  }

  async function loadTree() {
    if (!plans.length) { setStatus('Pick a project (or tick a variant) first.', true); return; }
    treeBusy = true;
    try {
      tree = await server(`/projects/tree?plans=${encodeURIComponent(plans.join(','))}`);
      const t = new Set();
      for (const p of tree.plans) for (const cy of p.cycles) for (const c of cy.cases) if (runnable(c.key)) t.add(`${cy.key}/${c.key}`);
      ticked = t;
      await loadPrevious();
      setStatus(`${t.size} runnable case(s) ticked.`);
    } catch (e) { setStatus('Could not read the project from Zephyr: ' + e.message, true); }
    finally { treeBusy = false; }
  }

  /** Previously Run: an earlier composer run of the same release version with a result for the case. */
  async function loadPrevious() {
    const out = {};
    try {
      const runs = (await server('/runs?kind=composer&limit=50')).runs;
      for (const r of runs) {
        const d = await server(`/runs/${encodeURIComponent(r.run_id)}`);
        const v = d.handoff && d.handoff.project && d.handoff.project.version;
        if (!version || v !== version) continue;
        for (const row of d.table) if (row.verdict && !['PENDING', 'NOT TESTED'].includes(row.verdict) && !out[row.case]) out[row.case] = `${r.run_id}: ${row.verdict}`;
      }
    } catch (_) { /* best effort */ }
    previous = out;
  }

  function body() {
    const cases = tickedCases.map(c => {
      const s = scriptByCase.get(c.key);
      return s ? { key: c.key, kind: 'script', script: s.path, cycle: c.cycle } : { key: c.key, kind: 'manual', cycle: c.cycle };
    });
    const proj = project ? { id: project.id, product: project.product, version: project.version, plans }
      : wiki ? { title: wiki.title, version, plans } : null;
    return { cases, template, project: proj, options: { email: (setup.email || '').trim() || null, start_after: startAfter || null } };
  }

  async function start() {
    if (!tickedCases.length) { setStatus('Nothing is ticked.', true); return; }
    try {
      const b = body();
      if (b.options.start_after) {
        const created = await server('/runs', { method: 'POST', body: JSON.stringify(runBody('composer', setup, b)) });
        setStatus(`Scheduled ${created.run_id} for ${startAfter}. NOTE: the seat agent's schedule poller is not built yet (PLAN-agent-sessions P4) — start it from the runs list when due.`, true);
        refreshKey += 1;
        return;
      }
      const r = await launch('composer', b);
      run = { runId: r.runId, sessionId: r.sessionId };
      refreshKey += 1;
      setStatus(`Started ${r.runId}: ${tickedCases.length} case(s).`);
    } catch (e) { setStatus('Start failed: ' + e.message, true); }
  }

  function shareLink() {
    const u = new URL(window.location.href);
    u.searchParams.set('panel', 'composer');
    if (project) u.searchParams.set('project', project.id);
    if (wikiUrl) u.searchParams.set('wiki', wikiUrl);
    if (template) u.searchParams.set('template', template);
    try { navigator.clipboard.writeText(u.toString()); setStatus('Share link copied.'); }
    catch (_) { setStatus(u.toString()); }
  }

  onMount(() => {
    loadBasics().then(() => {
      if (openRun) run = { runId: openRun, sessionId: null };
      if (preselect) setStatus(`Script ${preselect} preselected: choose its project and a template, then load the tree.`);
    });
    const t = setInterval(watchValidate, pollMs);
    return () => clearInterval(t);
  });
</script>

<div class="section tc-page">
  <div class="section-heading">Test Composer</div>
  <div class="section-description">Pick a project and the test bench, choose the topology template, check the bench against it, then tick the cases to run. Script cases run their saved PyScript; manual cases are run by the session by hand. Everything runs through your seat's agent.</div>

  <div class="tc-step"><span class="tc-step-n">1</span> Project</div>
  <div class="tc-line">
    <label><input type="radio" bind:group={source} value="templated"> Templated Project</label>
    <label><input type="radio" bind:group={source} value="wiki"> Zephyr Project Link</label>
  </div>
  {#if source === 'templated'}
    <select id="tc-project" class="form-input" bind:value={projectId}>
      <option value="">— choose a project uploaded by the Templating Tool —</option>
      {#each projects as p}<option value={p.id}>{p.product} · {p.version}{p.number ? ` · Project ${p.number}` : ''} ({p.plans.length} plan(s))</option>{/each}
    </select>
    {#if !projects.length}<div class="tc-small">No templated projects yet — upload one with the Zephyr Templating Tool, or use a project link.</div>{/if}
  {:else}
    <div class="tc-line">
      <input id="tc-wiki" class="form-input" type="url" placeholder="https://wiki.atlnz.lc/awpwiki/index.php/Project:3171_AT-x230-V2" bind:value={wikiUrl}>
      <button type="button" class="btn btn-secondary" disabled={wikiBusy} onclick={readWiki}>{wikiBusy ? 'Reading…' : 'Read Test Results'}</button>
    </div>
    {#if wiki}
      <div class="tc-small">{wiki.title}: {wiki.variants.length} variant(s) in the Test Results cell.</div>
      {#each wiki.variants as v, i}
        <label class="tc-variant"><input type="checkbox" bind:checked={variantPick[i]}>
          <b>{v.project}</b> · {v.version} · <span class="tc-badge">{v.status || 'status ?'}</span>
          <span class="tc-small">{v.title || ''}</span>
          <span class="tc-small">{v.plans.map(p => `${p.key}${p.name ? ' ' + p.name : ''}`).join(' · ') || 'no plans found'}</span></label>
      {/each}
    {/if}
  {/if}

  <div class="tc-step"><span class="tc-step-n">2</span> Test bench and template</div>
  <SetupFields bind:setup />
  <div class="tc-line">
    <select id="tc-template" class="form-input" bind:value={template}>
      <option value="">— topology template —</option>
      {#each templates as t}<option value={t.name}>{t.name}: {t.runnable_count} runnable{t.note ? ' (empty)' : ''}</option>{/each}
    </select>
    {#if tmpl}<span class="tc-small">{tmpl.note || `${tmpl.runnable_scripts.length} script case(s) and ${tmpl.manual_cases.length} manual case(s) can run on ${tmpl.setup}.`}</span>{/if}
  </div>

  <div class="tc-step"><span class="tc-step-n">3</span> Validate the bench against the template</div>
  <div class="tc-line">
    <button type="button" id="tc-validate" class="btn btn-primary" disabled={!template || !setup.testbox || !setup.consoles || !sessionsOk} onclick={validate}>Validate</button>
    {#if validated}<span class="tc-check" title="the probe matched the template">✓ the bench matches {template}</span>
    {:else if probe}<span class="tc-problem">Probe: {probe} — the differences are in the session's report below.</span>
    {:else if validateState && ['done', 'stopped', 'error'].includes(validateState)}<span class="tc-problem">No probe result — see the notices below.</span>{/if}
    <span class="tc-small">{health && !sessionsOk ? (health.error || (health.sessions && health.sessions.reason) || 'seat agent too old') : ''}</span>
  </div>
  {#if validateRun}
    {#key validateRun.runId}
      <AgentWindow runId={validateRun.runId} sessionId={validateRun.sessionId} {agent} {server} compact onstate={(s) => (validateState = s)} />
    {/key}
  {/if}

  <div class="tc-step"><span class="tc-step-n">4</span> What is in the project</div>
  <div class="tc-line">
    <button type="button" id="tc-load-tree" class="btn btn-secondary" disabled={!plans.length || !template || treeBusy} onclick={loadTree}>{treeBusy ? 'Reading Zephyr…' : 'Load the project'}</button>
    <label class="tc-small"><input type="checkbox" bind:checked={runnableOnly}> runnable on {template || 'the template'} only</label>
    {#if !validated && tree}<span class="tc-small tc-problem">The bench has not been validated against the template.</span>{/if}
  </div>
  {#if tree}
    <div class="zt-scroll tc-tree">
      <TcTree {tree} {kindOf} {runnable} previously={(k) => previous[k]} bind:ticked {runnableOnly} />
    </div>
  {/if}

  <div class="tc-step"><span class="tc-step-n">5</span> Start</div>
  <div class="tc-line">
    <label class="tc-small">Run after hours from <input type="time" class="form-input tc-time" bind:value={startAfter}></label>
    <button type="button" class="btn btn-secondary" onclick={() => (dryRun = dryRun ? null : JSON.stringify(runBody('composer', setup, body()), null, 2))}>{dryRun ? 'Hide' : 'Show'} the hand-off</button>
    <button type="button" class="btn btn-secondary" onclick={shareLink}>Copy share link</button>
    <button type="button" id="tc-start" class="btn btn-primary" disabled={!tickedCases.length || !sessionsOk} onclick={start}>Start ({tickedCases.length})</button>
  </div>
  {#if dryRun}<pre class="tc-pre">{dryRun}</pre>{/if}
  <div class="tc-status" class:is-bad={status.bad} role="status">{status.msg}</div>

  {#if run}
    <div class="tc-step"><span class="tc-step-n">6</span> The campaign — {run.runId}</div>
    {#key run.runId}
      <AgentWindow runId={run.runId} sessionId={run.sessionId} {agent} {server} onstate={(s) => { if (['done', 'stopped', 'error'].includes(s)) refreshKey += 1; }} />
      <ResultsTable runId={run.runId} {server} />
    {/key}
  {/if}

  <div class="tc-step">Earlier campaigns</div>
  <RunsList {server} kind="composer" {refreshKey} onopen={(id) => (run = { runId: id, sessionId: null })} />
</div>
