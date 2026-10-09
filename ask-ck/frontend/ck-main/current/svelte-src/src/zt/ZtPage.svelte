<script>
  // Zephyr Templating Tool — the single page (ask-ck/plans/PLAN-zephyr-templating.md §5a,
  // docs/zephyr.txt "UI"); ported from zephyr-tool.js to Svelte 2026-10-09 (PLAN-test-composer Z1)
  // with its behaviour unchanged. Paste a project's wiki URL → Organize with LLM → the four fields
  // fill in → Results Analysis (read-only) beside the Plan → Cycle → Case tree → Confirm un-greys
  // API Upload, which lists the calls (D9) and where the project has folders in every version →
  // Write to Zephyr asks in a modal (§5b P6), then the real upload, polled like the analysis.
  //
  // One request, then polling (the browser connection ceiling): POST /analyse returns an id and
  // GET /analyse/{id} is polled every pollMs.
  import { onDestroy, onMount } from 'svelte';
  import BusyButton from '../shared/BusyButton.svelte';
  import ZtAnalysis from './ZtAnalysis.svelte';
  import ZtConfirm from './ZtConfirm.svelte';
  import ZtTree from './ZtTree.svelte';
  import ZtUpload from './ZtUpload.svelte';
  import { applyProposals, cleanField, isOpen, setTick, tickSummary, treeRows, uploadSelection } from './model.js';

  let { api, pollMs = 2000 } = $props();

  let tree = $state(null);
  let job = $state(null);
  let ticked = $state(new Set());
  let ai = $state(new Map());
  let folds = $state(new Map());
  let manual = [];                     // [id, on] the user's own ticks, replayed over each poll

  let url = $state('');
  let fields = $state({ version: '', product: '', middle: '', number: '' });
  let touched = { version: false, product: false, middle: false, number: false };
  let versionNote = $state('');

  let status = $state({ msg: '', bad: false });
  let confirmed = $state(false);
  let previewed = $state(null);        // the selection API Upload listed — the one Write to Zephyr sends
  let preview = $state(null);          // what API Upload returned for it
  let run = $state(null);              // the latest GET /upload/run/{id}
  let asking = $state(null);           // the open confirm modal's resolve()

  let analysing = $state(false);
  let analyseId = $state(null);
  let cancelling = $state(false);
  let uploadBusy = $state(false);
  let refreshBusy = $state(false);
  let runBusy = $state(false);
  let flash = $state({ analyse: null, upload: null, refresh: null });

  let poll = null;
  let runPoll = null;

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

  function stopPolling() {
    if (poll) { clearInterval(poll); poll = null; }
    analyseId = null;
    cancelling = false;
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

  async function analyse() {
    const u = url.trim();
    if (!u) { setStatus('Paste the project page URL first.', true); return; }
    if (!tree) { setStatus('No templates imported yet — Refresh templates first.', true); return; }
    if (analysing) return;
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
      poll = setInterval(() => pollOnce(id), pollMs);
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

<div class="section">
  <div class="section-heading">Zephyr Templating Tool</div>
  <div class="section-description">Paste a project's wiki page. The model reads its Test Strategy, TPS and Feature Page and proposes which template plans, cycles and cases to leave out — every proposal cites its source, and anything it does not mention stays ticked. Review the ticks, Confirm, then API Upload shows exactly what it would send to Zephyr.</div>
  <div class="zt-line">
    <input id="zt-url" class="form-input" type="url" bind:value={url}
      placeholder="https://wiki.atlnz.lc/awpwiki/index.php/Project:3296_IE520_Software" aria-label="Project wiki page URL">
    <BusyButton id="zt-analyse" label="Organize with LLM" busyLabel="Organizing…" busy={analysing}
      flash={flash.analyse} onclick={analyse} />
    {#if analyseId}
      <button id="zt-cancel" type="button" class="btn btn-secondary" disabled={cancelling} onclick={cancel}>{cancelling ? 'Stopping…' : 'Stop'}</button>
    {/if}
  </div>
  <div class="zt-line">
    <div class="zt-field"><label for="zt-version">What Version (AW+)</label><input id="zt-version" class="form-input"
      placeholder="filled in by the analysis" bind:value={fields.version} oninput={() => fieldInput('version')}><span id="zt-version-note" class="zt-small">{versionNote}</span></div>
    <div class="zt-field"><label for="zt-product">What Product (DUT)</label><input id="zt-product" class="form-input"
      placeholder="filled in by the analysis" bind:value={fields.product} oninput={() => fieldInput('product')}></div>
    <div class="zt-field"><label for="zt-middle">What Team Subfolder</label><input id="zt-middle" class="form-input"
      placeholder="e.g. Tomahawk — blank if none" bind:value={fields.middle} oninput={() => fieldInput('middle')}></div>
    <div class="zt-field"><label for="zt-number">What Project Number</label><input id="zt-number" class="form-input"
      placeholder="e.g. 3001 — blank or N/A if none" bind:value={fields.number} oninput={() => fieldInput('number')}></div>
  </div>
  <div id="zt-status" class="zt-status" class:is-bad={status.bad} role="status">{status.msg}</div>
  <div class="zt-cols">
    <div class="zt-col">
      <div class="zt-col-head">Results Analysis</div>
      <div id="zt-analysis" class="zt-scroll"><ZtAnalysis {job} {tree} /></div>
    </div>
    <div class="zt-col">
      <div class="zt-col-head"><span>Test Plans / Cycles / Cases</span><span id="zt-tree-count" class="zt-small">{treeCount}</span></div>
      <div id="zt-tree" class="zt-scroll"><ZtTree {tree} {ticked} {ai} {folds} ontoggle={toggle} onfold={fold} /></div>
    </div>
  </div>
  <div class="zt-line zt-small"><span id="zt-templates-info">{templatesInfo}</span>
    <BusyButton id="zt-refresh" cls="btn btn-secondary btn-compact-small" label="Refresh templates" busyLabel="Reading Zephyr…"
      busy={refreshBusy} flash={flash.refresh} title="Re-read the template plans, cycles and cases from Zephyr (read only)"
      onclick={refreshTemplates} /></div>
  <div class="zt-actions">
    <button id="zt-confirm" type="button" class="btn btn-secondary" onclick={confirm}>{confirmed ? 'Confirmed ✓' : 'Confirm'}</button>
    <BusyButton id="zt-upload" label="API Upload" busyLabel="Preparing…" busy={uploadBusy} flash={flash.upload}
      disabled={!confirmed} title="Lists the calls first — nothing is written until you type the product and version and press Write to Zephyr"
      onclick={upload} />
  </div>
  <div id="zt-upload-result">{#if preview && previewed}<ZtUpload d={preview} sel={previewed} {run} {runBusy} onrun={writeToZephyr} />{/if}</div>
</div>

{#if asking && preview && previewed}
  <ZtConfirm d={preview} sel={previewed} onanswer={answer} />
{/if}
