<script>
// @ts-nocheck
  import ToolHeader from '../lib/components/ToolHeader.svelte';
  import ErrorBanner from '../lib/components/ErrorBanner.svelte';
  import zephyrIcon from '../assets/icons/getzephyr-icon.svg';

  import { onDestroy, onMount } from 'svelte';
  import LlmButton from '../lib/components/LlmButton.svelte';
  import Button from '../lib/components/Button.svelte';
  import ZtAnalysis from '../lib/components/zephyr/ZtAnalysis.svelte';
  import ZtConfirm from '../lib/components/zephyr/ZtConfirm.svelte';
  import ZtTree from '../lib/components/zephyr/ZtTree.svelte';
  import ZtUpload from '../lib/components/zephyr/ZtUpload.svelte';
  import { applyProposals, cleanField, isOpen, setTick, tickSummary, treeRows, uploadSelection } from '../lib/components/zephyr/zephyrModel.js';

  import { scrollToSection } from '../lib/utils/scroll';
  import { httpApi } from '../lib/services/zephyr/zephyrService.js';

  let { api = httpApi(), pollMs = 2000 } = $props();

  let tree = $state(null);
  let job = $state(null);
  let ticked = $state(new Set());
  let ai = $state(new Map());
  let folds = $state(new Map());
  let manual = [];                     

  let url = $state('');
  let fields = $state({ version: '', product: '', middle: '', number: '' });
  let touched = { version: false, product: false, middle: false, number: false };
  let versionNote = $state('');

  let status = $state({ msg: '', bad: false });
  let confirmed = $state(false);
  let previewed = $state(null);      
  let preview = $state(null);         
  let run = $state(null);             
  let asking = $state(null);          

  let analysing = $state(false);
  let analyseId = $state(null);
  let cancelling = $state(false);
  let uploadBusy = $state(false);
  let refreshBusy = $state(false);
  let runBusy = $state(false);
  let flash = $state({ analyse: null, upload: null, refresh: null });

  let poll = null;
  let runPoll = null;

  let expanded = $state(false);   // true once Organize with LLM has been clicked

  const templatesInfo = $derived.by(() => {
    if (!tree) return 'No templates imported yet.';
    const c = tree.counts || {};
    return `Templates imported ${String(tree.imported_at || '').slice(0, 16).replace('T', ' ')} UTC: ${c.plans} plans, ${c.cycles} cycles, ${c.cases} cases.`;
  });
  const treeCount = $derived(tree ? tickSummary(tree, ticked) : '');

  function setStatus(msg, bad = false) { status = { msg: msg || '', bad: !!bad }; }

  function doFlash(name, ok) {
    flash[name] = ok ? 'done' : 'error';
    setTimeout(() => { flash[name] = null; }, 1200);
  }

  const headerTitle = $derived.by(() => {
    const parts = [
      fields.number,
      fields.product,
      fields.version,
    ].filter(Boolean);
    return parts.length ? 
      'Project ' + parts[0] + ' - ' +  parts[1] + ' v' + parts[2]
      : "No project loaded. Please paste a project link from the ATWiki to organise.";
  });

  /** What the upload targets — all four from the fields, which the analysis fills and the user may
   *  correct (Terrence 2026-10-07: a reload or a stopped analysis no longer loses them). */
  function project() {
    return { version: cleanField(fields.version) || '', product: cleanField(fields.product) || '',
             middle: cleanField(fields.middle), number: cleanField(fields.number) };
  }

  function setConfirmed(on) {
    confirmed = on;
    if (!on && !run) {                 // the selection changed: the listed calls no longer apply
      previewed = null;
      preview = null;
    }
  }

  async function loadTree() {
    const d = await api('/templates');
    tree = d.snapshot;
    ticked = new Set(treeRows(tree).map(r => r.id));
    ai = new Map();
    manual = [];
    folds = new Map();
  }

  /** The analysis's ticks, then the user's own changes on top (a poll must not undo a click). */
  function rebuildTicks() {
    const f = applyProposals(tree, job);
    const t = f.ticked;
    for (const [id, on] of manual) setTick(t, tree, id, on);
    ticked = t;
    ai = f.ai;
  }

  function fillProject(p) {
    if (!p) return;
    for (const k of ['version', 'product', 'middle', 'number']) if (!touched[k]) fields[k] = p[k] || '';
    versionNote = p.version
      ? `from the ${p.version_source}${p.project_version ? ` — the project page says ${p.project_version}` : ''}` : '';
  }

  // Resolved when the analysis ends, however it ends (done / error / cancelled / a failed poll /
  // leaving the page) — every one of those paths goes through stopPolling. Keeps the
  // Organise with LLM button busy for the whole job, not just the request that starts it.
  let finishAnalysis = null;

  function stopPolling() {
    if (poll) { clearInterval(poll); poll = null; }
    analyseId = null;
    cancelling = false;
    if (finishAnalysis) { const done = finishAnalysis; finishAnalysis = null; done(); }
  }

  async function pollOnce(id) {
    let d;
    try { d = await api('/analyse/' + encodeURIComponent(id)); } catch (e) {
      stopPolling(); analysing = false; setStatus(e.message, true); return;
    }
    job = d;
    fillProject(d.project);
    rebuildTicks();
    setConfirmed(false);
    if (['done', 'error', 'cancelled'].includes(d.state)) {
      stopPolling();
      analysing = false;
      doFlash('analyse', d.state === 'done');
      setStatus(d.state === 'done' ? 'Review the ticks, then Confirm.' : '', d.state === 'error');
    }
  }

  // Checked before the LLM button goes busy — resolving false stops it there.
  async function readyToAnalyse() {
    if (!url.trim()) { setStatus('Paste the project page URL first.', true); return false; }
    if (!tree) { setStatus('No templates imported yet — Refresh templates first.', true); return false; }
    return !analysing;
  }

  // The LLM button's run: start the job, then stay busy until polling sees it end. A failed
  // start is reported in the page's own status line, as before (not thrown into the button).
  async function analyse() {
    const u = url.trim();
    analysing = true;
    stopPolling();
    manual = [];
    folds = new Map();
    touched = { version: false, product: false, middle: false, number: false };
    run = null;
    setConfirmed(false);
    setStatus('');
    try {
      const { id } = await api('/analyse', { method: 'POST', body: JSON.stringify({ url: u }) });
      job = { id, state: 'reading', plans: {} };
      analyseId = id;
      expanded = true;
      await new Promise((resolve) => {
        finishAnalysis = resolve;
        poll = setInterval(() => pollOnce(id), pollMs);
      });
      scrollToSection('.section-description');
    } catch (e) {
      analysing = false;
      doFlash('analyse', false);
      setStatus(e.message, true);
    }
  }

  async function cancel() {
    if (!analyseId) return;
    cancelling = true;
    try {
      await api('/analyse/' + encodeURIComponent(analyseId) + '/cancel', { method: 'POST' });
      setStatus('Stopping — the calls with the model are being cancelled.');
    } catch (e) {
      setStatus(e.message, true);
      cancelling = false;
    }
  }

  function fold(id) {
    const next = new Map(folds);
    next.set(id, !isOpen(id, ai, folds));
    folds = next;
  }

  function toggle(id, on) {
    manual.push([id, on]);
    ticked = setTick(new Set(ticked), tree, id, on);
    setConfirmed(false);
  }

  function fieldInput(k) {
    touched[k] = true;
    setConfirmed(false);
  }

  function confirm() {
    if (!tree) return;
    const sel = uploadSelection(tree, ticked, project());
    if (!sel.plans.length) { setStatus('Nothing is ticked.', true); return; }
    setConfirmed(true);
    setStatus(`Confirmed: ${sel.plans.length} plan(s). API Upload shows what it would do — nothing is written yet.`);
  }

  async function upload() {
    if (!confirmed || uploadBusy) return;
    uploadBusy = true;
    let ok = false;
    try {
      const sel = uploadSelection(tree, ticked, project());
      const d = await api('/upload/preview', { method: 'POST', body: JSON.stringify(sel) });
      previewed = sel;
      preview = d;
      run = null;
      ok = true;
    } catch (e) {
      setStatus(e.message, true);
    } finally {
      uploadBusy = false;
      doFlash('upload', ok);
    }
  }

  function stopRunPolling() {
    if (runPoll) { clearInterval(runPoll); runPoll = null; }
  }

  async function pollRun(id) {
    let d;
    try { d = await api('/upload/run/' + encodeURIComponent(id)); } catch (e) {
      stopRunPolling(); setStatus(e.message, true); return;
    }
    run = d;
    if (d.state !== 'running') {
      stopRunPolling();
      setStatus(d.state === 'done' ? 'Upload complete.' : 'The upload did not complete — see below.', d.state !== 'done');
    }
  }

  function askToWrite() {
    return new Promise(resolve => { asking = resolve; });
  }

  function answer(yes) {
    const r = asking;
    asking = null;
    if (r) r(yes);
  }

  /** The real upload of exactly the selection API Upload listed (§5b). */
  async function writeToZephyr() {
    const sel = previewed;
    if (!sel || !preview) return;
    if (!(await askToWrite())) return;
    runBusy = true;
    try {
      const { id } = await api('/upload/run', { method: 'POST',
        body: JSON.stringify(Object.assign({}, sel, { confirm_product: sel.product, confirm_version: sel.version })) });
      run = { id, state: 'running', steps: [] };
      stopRunPolling();
      runPoll = setInterval(() => pollRun(id), pollMs);
    } catch (e) {
      setStatus(e.message, true);
      runBusy = false;
    }
  }

  async function refreshTemplates() {
    if (refreshBusy) return;
    refreshBusy = true;
    let ok = false;
    try {
      const d = await api('/templates/refresh', { method: 'POST' });
      await loadTree();
      if (job) rebuildTicks();
      setConfirmed(false);
      setStatus(`Templates refreshed: ${d.written ? d.written.plans + ' plans' : 'done'}.`);
      ok = true;
    } catch (e) {
      setStatus(e.message, true);
    } finally {
      refreshBusy = false;
      doFlash('refresh', ok);
    }
  }

  onMount(async () => {
    try { await loadTree(); } catch (e) { setStatus('Could not load the templates: ' + e.message, true); }
  });

  onDestroy(() => { stopPolling(); stopRunPolling(); });

  
</script>

<ToolHeader title={headerTitle} tool="ZEPHYR TEMPLATING" icon={zephyrIcon}/>


<div class="tool-page">

  <div class="section-description">Paste a project's wiki page. The model reads its Test Strategy, TPS and Feature Page and proposes which template plans, cycles and cases to leave out — every proposal cites its source, and anything it does not mention stays ticked. Review the ticks, Confirm, then API Upload shows exactly what it would send to Zephyr.</div>
  
  <div class="zt-line">
    <input 
      id="zt-url" 
      class="form-input" 
      type="url" bind:value={url}
      placeholder="https://wiki.atlnz.lc/awpwiki/index.php/Project:3296_IE520_Software" 
      aria-label="Project wiki page URL">
    <!-- Click it while busy to stop: onStop cancels the analysis job itself
         (POST /analyse/{id}/cancel) rather than the button's own call id. -->
    <LlmButton 
      label="Organise with LLM" 
      verb="Organizing…" 
      onBeforeRun={readyToAnalyse} 
      onRun={analyse} 
      onStop={cancel}
    />
  </div>

  <div class="zt-line">
    <div class="zt-field">
      <label for="zt-version">What Version (AW+) - <span id="zt-version-note" class="zt-small">{versionNote}</span></label>
      <input 
        id="zt-version" class="form-input"
        placeholder="filled in by the analysis" 
        bind:value={fields.version} 
        oninput={() => fieldInput('version')}
      >
    </div>
    <div class="zt-field">
      <label for="zt-product">What Product (DUT)</label>
      <input 
        id="zt-product" 
        class="form-input"
        placeholder="filled in by the analysis" 
        bind:value={fields.product} 
        oninput={() => fieldInput('product')}
      >
    </div>
    <div class="zt-field">
      <label for="zt-middle">What Team Subfolder</label>
      <input 
        id="zt-middle" 
        class="form-input"
        placeholder="e.g. Tomahawk — blank if none" 
        bind:value={fields.middle} 
        oninput={() => fieldInput('middle')}
      >
    </div>
    <div class="zt-field">
      <label for="zt-number">What Project Number</label>
      <input 
        id="zt-number" 
        class="form-input"
        placeholder="e.g. 3001 — blank or N/A if none" 
        bind:value={fields.number} 
        oninput={() => fieldInput('number')}
      >
    </div>
  </div>


  <div class="zt-line zt-small">
    <span id="zt-templates-info">{templatesInfo}</span>
    <Button 
      variant="outline" loading={refreshBusy} 
      title="Re-read the template plans, cycles and cases from Zephyr (read only)"
      on:click={refreshTemplates}
      >Refresh templates
    </Button>
      {#if status.bad}
        <ErrorBanner message={status.msg} />
      {:else if status.msg}
        <p id="zt-status" class="zt-status" role="status">{status.msg}</p>
      {/if}
  </div>

  <div class="zt-cols">
    <div class="zt-col">
      <div class="zt-col-head">Results Analysis</div>
      <div id="zt-analysis" class="zt-scroll"class:expanded><ZtAnalysis {job} {tree} /></div>
    </div>
    <div class="zt-col">
      <div class="zt-col-head"><span>Test Plans / Cycles / Cases</span><span id="zt-tree-count" class="zt-small">{treeCount}</span></div>
      <div id="zt-tree" class="zt-scroll" class:expanded><ZtTree {tree} {ticked} {ai} {folds} ontoggle={toggle} onfold={fold} /></div>
    </div>
  </div>

  <div class="zt-actions">
    <div>
      <!-- Locked while an analysis runs: its polls keep re-ticking the tree, so there is
           nothing stable to confirm until the job ends. -->
      <Button
        variant="outline"
        disabled={analysing}
        title={analysing ? 'Wait for the analysis to finish' : ''}
        on:click={confirm}
        >{confirmed ? 'Confirmed ✓' : 'Confirm'}
      </Button>
    </div>
    <div>
      <Button 
        variant="primary" 
        loading={uploadBusy} 
        disabled={!confirmed}
        title="Lists the calls first — nothing is written until you type the product and version and press Write to Zephyr"
        on:click={upload}
        >Preview API Upload
      </Button>
    </div>
  </div>

  <div id="zt-upload-result">
    {#if preview && previewed}
      <ZtUpload 
        d={preview} 
        sel={previewed} 
        {run} {runBusy} 
        onrun={writeToZephyr} 
      />{/if}
  </div>

  {#if asking && preview && previewed}
    <ZtConfirm d={preview} sel={previewed} onanswer={answer} />
  {/if}
</div>  



<style>
  .zt-status {
    color: var(--color-text-muted);
    font-size: 0.88rem;
    font-style: italic;
  }

  #zt-tree-count {
    color: var(--color-text-muted);
    font-weight: 400;
    font-size: 0.94rem;
    white-space: nowrap; 
  }

  .section-description {
    margin: 0 0 16px;
    color: var(--color-text-muted);
    font-size: 0.94rem;
  }

  .form-input {
    flex: 1;
    padding: 8px 12px;
    border-radius: 8px;
    border: 1px solid var(--color-border-surface);
    background: var(--color-bg-surface);
    color: var(--color-text);
    font: inherit;
    font-size: 0.94rem;
    width: 100%;
  }

  #zt-url {
    font-size: 1.1rem;
  }

  .zt-cols {
    display: grid;
    grid-template-columns: 1fr 1fr;
    align-items: baseline;
    gap: 24px;
    width: 100%;
    /* margin-top: 0px; */
    margin-bottom: 12px;

    /* border: 1px solid var(--color-border-surface);
    border-radius: 10px;
    background-color: var(--color-bg-surface); */
  }

  .zt-col {
    border-radius: 10px;
    background-color: var(--color-bg-surface);
    border: 1px solid var(--color-border-surface);
  }
  .zt-line {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 24px;
    width: 100%;
  }

  .zt-col-head {
    font-weight: 800;
    font-size: 1rem;
    display: flex;
    justify-content: space-between;   /* title on the left, count on the far right */
    align-items: center;
    color: var(--color-text);
    padding: 16px
  }

  .zt-scroll {
    padding-left: 24px;
    padding-right: 24px;
    font-size: 0.94rem;
    height: 48vh;                    
    transition: height 0.3s ease;
    overflow: scroll;
    scroll-behavior: auto;
    border-top: 3px solid var(--color-border-surface);
  }

  .zt-scroll.expanded {
    height: 65vh;
  }

  #zt-templates-info {
    font-size: 0.94rem;
    color: var(--color-text-muted)
  }

  .zt-actions {
    display: flex;
    gap: 12px;
  }

  #zt-version-note {
    font-style: italic;
    font-weight: 500;
  }

  label {
    padding-bottom: 24px;
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--color-text-muted);
  }
</style>
