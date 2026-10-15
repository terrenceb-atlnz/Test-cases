<script>
  // Run Scripts (ask-ck/plans/PLAN-run-scripts.md §2): validated scripts from one source, ticked in
  // the order they should run → where it runs → now or once after hours → Launch through THIS seat's
  // ck-agent (D7). No repair, review or Finalize; the bench gates and the sentinel stay (test-mode).
  // A share link (§3) fills the page and never launches; Run again refills it from a finished run.
  import { onMount, untrack } from 'svelte';
  import AgentWindow from './AgentWindow.svelte';
  import ResultsTable from './ResultsTable.svelte';
  import RunsList from './RunsList.svelte';
  import SetupFields from './SetupFields.svelte';
  import { formatOutlets, loadSetup, runBody, saveSetup, scriptsLink } from './api.js';

  let { server, agent, link = null, openRun = null } = $props();

  const TERMINAL = ['done', 'stopped', 'error'];
  // Read once, at mount: a share link fills the page and is then forgotten.
  const given = untrack(() => link) || {};

  // Link fields win over this seat's remembered answers, which are not overwritten until Launch.
  // The email is never in a link: it is always this seat's own (R-D4).
  let setup = $state(Object.assign({ testbox: '', consoles: '', pduIp: '', outlets: '', constraints: '', email: '' },
    loadSetup(), given.setup || {}));
  let sources = $state([]);
  let sourceId = $state(given.source || 'generated');
  let listing = $state(null);                // {enabled, reason, scripts}
  let filter = $state('');
  let order = $state([]);                    // ticked paths, in the order they run
  let missing = $state([]);                  // paths a link or Run again named that are not available
  let wanted = given.scripts && given.scripts.length ? given.scripts : null;
  let startAfter = $state(given.start || '');
  let health = $state(null);
  let busy = $state(false);
  let status = $state({ msg: '', bad: false });
  let shared = $state('');
  let run = $state(null);                    // {runId, sessionId}
  let runState = $state(null);
  let refreshKey = $state(0);

  const scripts = $derived(listing ? listing.scripts : []);
  const byPath = $derived(new Map(scripts.map(s => [s.path, s])));
  const shown = $derived(scripts.filter(s => !filter.trim()
    || `${s.case_key || ''} ${s.path}`.toLowerCase().includes(filter.trim().toLowerCase())));
  const groups = $derived([...new Set(shown.map(s => s.group))].map(g => ({ group: g, rows: shown.filter(s => s.group === g) })));
  const sessionsOk = $derived(health && health.sessions && health.sessions.available);
  const canLaunch = $derived(order.length > 0 && sessionsOk && setup.testbox && setup.consoles && !busy);

  function setStatus(msg, bad = false) { status = { msg, bad }; }

  function toggle(path) {
    order = order.includes(path) ? order.filter(p => p !== path) : [...order, path];
  }

  /** Tick the named scripts in their order; anything missing or no longer validated is reported. */
  function pick(paths) {
    order = paths.filter(p => byPath.has(p));
    missing = paths.filter(p => !byPath.has(p));
  }

  async function loadScripts() {
    try {
      const d = await server(`/scripts?source=${encodeURIComponent(sourceId)}&validated=true`);
      sources = d.sources || [];
      listing = { enabled: d.enabled, reason: d.reason, scripts: d.scripts || [] };
    } catch (e) {
      listing = { enabled: false, reason: e.message, scripts: [] };
    }
    if (wanted) { pick(wanted); wanted = null; }
  }

  function chooseSource(id) {
    if (id === sourceId) return;
    sourceId = id; order = []; missing = [];
    loadScripts();
  }

  async function checkAgent() {
    try { health = await agent.health(); } catch (e) { health = { error: e.message }; }
  }

  function body() {
    return {
      source: sourceId,
      cases: order.map(p => ({ key: (byPath.get(p) || {}).case_key, kind: 'script', script: p })),
      options: { email: (setup.email || '').trim() || null, start_after: startAfter || null },
    };
  }

  async function launch() {
    if (!canLaunch) return;
    busy = true;
    saveSetup(setup);
    try {
      const b = runBody('scripts', setup, body());
      const created = await server('/runs', { method: 'POST', body: JSON.stringify(b) });
      if (b.options.start_after) {
        setStatus(`Scheduled ${created.run_id} for ${startAfter} (${created.handoff.start_at}). Your seat agent starts it then — keep this seat on and logged in; no tab is needed. The results arrive in the runs list and by email.`);
      } else {
        const started = await agent.start({ run_id: created.run_id, handoff: created.handoff, mode: 'campaign' });
        if (!started.ok) throw new Error(started.error || 'the seat agent refused the session');
        run = { runId: created.run_id, sessionId: started.session_id };
        runState = null;
        setStatus(`Launched ${created.run_id} on ${b.testbox}: ${order.length} script(s).`);
      }
      refreshKey += 1;
    } catch (e) {
      setStatus('Launch failed: ' + e.message, true);
    } finally { busy = false; }
  }

  async function copyLink() {
    shared = scriptsLink(window.location.href, { source: sourceId, scripts: order, setup, start: startAfter });
    try {
      await navigator.clipboard.writeText(shared);
      setStatus('Share link copied. It carries the scripts and the bench settings, never your email.');
    } catch (_) {
      setStatus('Copy the share link below. It carries the scripts and the bench settings, never your email.');
    }
  }

  /** Refill the page from a finished run's hand-off: same scripts, order and bench; this seat's email. */
  async function runAgain() {
    try {
      const h = (await server(`/runs/${encodeURIComponent(run.runId)}`)).handoff || {};
      setup = Object.assign({}, setup, { testbox: h.testbox || '', consoles: h.consoles || '',
        pduIp: (h.pdu && h.pdu.ip) || '', outlets: formatOutlets(h.pdu && h.pdu.outlets), constraints: h.constraints || '' });
      startAfter = '';
      const paths = (h.cases || []).map(c => c.path).filter(Boolean);
      if ((h.source || 'generated') !== sourceId) { sourceId = h.source || 'generated'; wanted = paths; await loadScripts(); }
      else pick(paths);
      setStatus(`Filled from ${run.runId}. Press Launch to run it again.`);
    } catch (e) { setStatus('Could not read that run: ' + e.message, true); }
  }

  onMount(() => {
    loadScripts();
    checkAgent();
    if (openRun) run = { runId: openRun, sessionId: null };
    if (link) setStatus('Filled from a share link. Check the settings, then press Launch.');
  });
</script>

<div class="section tc-page">
  <div class="section-heading">Run Scripts</div>
  <div class="section-description">Run validated scripts on a test bench through your seat's agent, several at once, in the order you tick them. A script that fails does not stop the rest. There is no repair or review: that is Validation's job. The session still checks the bench before it runs anything.</div>

  <div class="tc-step"><span class="tc-step-n">1</span> Source</div>
  <div class="tc-line rs-sources">
    {#each sources as s (s.id)}
      <label class="tc-small" title={s.reason || ''}><input type="radio" name="rs-source" value={s.id} checked={sourceId === s.id}
        disabled={!s.enabled} onchange={() => chooseSource(s.id)}> {s.label}{s.enabled ? '' : ' (not yet)'}</label>
    {/each}
  </div>

  <div class="tc-step"><span class="tc-step-n">2</span> Scripts</div>
  {#if listing && !listing.enabled}
    <div class="tc-problem">{listing.reason}</div>
  {/if}
  <div class="tc-line"><input id="rs-filter" class="form-input" placeholder="Filter by case key or path" bind:value={filter}></div>
  <div class="rs-pick">
    <div class="tc-scripts">
      {#each groups as g (g.group)}
        <div class="rs-group">{g.group}</div>
        {#each g.rows as s (s.path)}
          <label class="tc-script-row" class:is-chosen={order.includes(s.path)}>
            <input type="checkbox" name="rs-script" value={s.path} checked={order.includes(s.path)} onchange={() => toggle(s.path)}>
            <span class="tc-key">{s.case_key || '?'}</span> <span>{s.path}</span>
            <span class="tc-small">validated {String(s.finalized_at || '').slice(0, 10)}</span>
          </label>
        {/each}
      {/each}
      {#if listing && listing.enabled && !scripts.length}
        <div class="tc-small rs-empty">No validated scripts yet. A script appears here once Validation has finalized it.</div>
      {/if}
    </div>
    <div class="rs-order">
      <div class="tc-small">Runs in this order</div>
      {#if order.length}
        <ol>{#each order as p (p)}<li><span class="tc-key">{(byPath.get(p) || {}).case_key || '?'}</span> <span class="tc-small">{p}</span></li>{/each}</ol>
      {:else}<div class="tc-small">Nothing ticked.</div>{/if}
    </div>
  </div>
  {#each missing as p (p)}<div class="tc-problem rs-missing">not available: {p}</div>{/each}

  <div class="tc-step"><span class="tc-step-n">3</span> Where it runs</div>
  <SetupFields bind:setup />

  <div class="tc-step"><span class="tc-step-n">4</span> When and launch</div>
  <div class="tc-line">
    <label class="tc-small">Run once, after hours, from <input id="rs-start" type="time" class="form-input tc-time" bind:value={startAfter}></label>
    <span class="tc-small">(blank = now)</span>
    <button type="button" id="rs-link" class="btn btn-secondary" onclick={copyLink}>Copy share link</button>
    <button type="button" id="rs-launch" class="btn btn-primary" disabled={!canLaunch} onclick={launch}>{busy ? 'Launching…' : `${startAfter ? 'Schedule' : 'Launch'} (${order.length})`}</button>
  </div>
  <div class="tc-line">
    <span class="tc-small">
      {#if !health}checking your seat agent…
      {:else if health.error}Your seat agent is not reachable ({health.error}) — run the seat setup from the home page.
      {:else if !sessionsOk}Your seat agent cannot run sessions: {health.sessions ? health.sessions.reason : 'agent too old — re-run the seat setup'}
      {:else}Seat agent {health.agent_version} ready · device-testing at {health.sessions.dt_root}{/if}
    </span>
  </div>
  {#if shared}<input id="rs-shared" class="form-input" readonly value={shared} onfocus={(e) => e.currentTarget.select()}>{/if}
  <div class="tc-status" class:is-bad={status.bad} role="status">{status.msg}</div>

  {#if run}
    <div class="tc-step"><span class="tc-step-n">5</span> The session — {run.runId}</div>
    {#key run.runId}
      <AgentWindow runId={run.runId} sessionId={run.sessionId} {agent} {server} onstate={(s) => { runState = s; if (TERMINAL.includes(s)) refreshKey += 1; }} />
      <div class="tc-step"><span class="tc-step-n">6</span> Results</div>
      <ResultsTable runId={run.runId} {server} />
    {/key}
    <div class="tc-line">
      <button type="button" id="rs-again" class="btn btn-secondary" disabled={!TERMINAL.includes(runState)} onclick={runAgain}>Run again</button>
      <span class="tc-small">{TERMINAL.includes(runState) ? 'Fills the page with this run\'s scripts, order and bench.' : 'Available when the run has finished.'}</span>
    </div>
  {/if}

  <div class="tc-step">Earlier runs</div>
  <RunsList {server} kind="scripts" {refreshKey} onopen={(id) => { run = { runId: id, sessionId: null }; runState = null; }} />
</div>
