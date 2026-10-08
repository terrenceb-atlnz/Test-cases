<script>
// @ts-nocheck

  import ArrowStep from '../ArrowStep.svelte';
  import Button from '../Button.svelte';
  import EditableField from '../EditableField.svelte';
  import StatusModal from '../StatusModal.svelte';
  import ErrorBanner from '../ErrorBanner.svelte';
  import { onMount, onDestroy } from 'svelte';
  import { scrollToStepIntro } from '../../utils/scroll.js';

  /** @type {string} Default Group — the case's own folder, used only until a naming value is
      ever saved (session.step6.naming then wins on every later mount). */
  export let initialGroup = '';

  /** @type {string} Already-saved session.step6.naming.name, if any. */
  export let initialName = '';

  /** @type {string} The session's already-assembled script (step6.files.test.code), if any —
      restored so the Summary and Review/Fix don't start blank after a reload. */
  export let initialAssembledCode = '';

  /** @type {Array<{ level: string, message: string }>} The lint for that script (step6.lint). */
  export let initialLintResults = [];

  /** @type {(group: string, name: string) => Promise<void>} Autosave-on-blur for the two
      naming fields alone — 409s once a script has already been assembled (renaming after
      that point has to move the file on disk too, which is onSave's job, not this one). */
  export let onSaveNaming = async () => {};

  /** @type {() => Promise<Array<{ id: string, kind: string, tc_n: number | null, action: string,
      verify: string, prompt: string, code: string, status: string, error: string }>>}
      The server's units (step_prompts) — called once on mount. */
  export let onLoadUnits = async () => [];

  /** @type {(items: Array<{ id: string, prompt?: string, edited?: boolean }>) => Promise<{
      dispatched: string[], already_running: string[], max_concurrent: number, primed: string | null }>}
      Queues the units and returns at once — progress comes from onPollStatus. */
  export let onDispatchUnits = async () => ({ dispatched: [], already_running: [], max_concurrent: 0, primed: null });

  /** @type {() => Promise<{ units: Record<string, { status: string, error: string, at: string }>, running: string[] }>}
      Per-unit status, no code — polled every couple of seconds while anything is running. */
  export let onPollStatus = async () => ({ units: {}, running: [] });

  /** @type {(unitId: string) => Promise<{ status: string, code: string, error: string, at: string }>}
      One unit's stored reply — fetched once as each unit lands. */
  export let onFetchUnitCode = async () => ({ status: 'pending', code: '', error: '', at: '' });

  /** @type {(group: string, name: string) => Promise<{ assembledCode: string, lintResults: Array }>}
      No LLM — deterministic splice + lint, server-side. 409s if any unit is still missing code. */
  export let onAssemble = async () => ({ assembledCode: '', lintResults: [] });

  /** @type {() => Promise<{ status: string, message: string }>} */
  export let onSave = async () => ({ status: 'success', message: '' });

  /** @type {((pageId: string) => void) | null} */
  export let onNavigate = null;

  /** @type {((caseId?: string | null) => void) | null} */
  export let onCreateAnother = null;

  /** @type {(() => void) | null} Called once the save succeeds — parent marks the stepper finished */
  export let onFinished = null;

  const GENERATE_SUMMARY_STEP_ID = '__generate_summary__';

  // Group/name — seeded once at mount, same convention as Fragments'/Script Search's
  // initial* props. Name starts blank until the reviewer types one (or one was already
  // saved); group defaults to the case's own folder.
  let group = initialGroup;
  let name = initialName;

  async function saveNaming() {
    if (!group.trim() || !name.trim()) return;   // silent by design, matching current/'s own blur-save
    try {
      await onSaveNaming(group.trim(), name.trim());
    } catch (e) {
      // Silent on purpose — a 409 here just means a script already exists (rename is
      // onSave's job instead), and a half-typed name on a stray blur isn't worth a dialog.
    }
  }

  // Units for Generate come from the server (step_prompts), in file order: the "setup" unit
  // (the TestSet configure/tear_down pair) when the skeleton has one, then one unit per
  // TestCase class, keyed by the server's own ids ("tc1", "tc2", …). Arrow-step labels follow tc_n.
  let generateUnits = [];

  // Per-unit generation state, keyed by the unit's id — seeded from each unit's stored
  // chunk, so a unit the server already generated shows its code (and one whose last run
  // failed shows why) instead of starting blank. `renderedPrompt` is the prompt as loaded:
  // a prompt that differs from it is the reviewer's edit. `storedEdit` is the server saying
  // the loaded prompt is itself an earlier, kept edit. `at` is when the stored reply landed —
  // a change of `at` on the poll means new bytes exist for that unit.
  let generateState = {};
  let generateActiveUnitId = null;
  let confirmedGenerateUnits = [];

  let isLoadingUnits = false;
  let loadUnitsError = '';

  async function loadUnits() {
    isLoadingUnits = true;
    loadUnitsError = '';
    try {
      const units = await onLoadUnits();
      const nextState = {};
      for (const u of units) {
        nextState[u.id] = {
          prompt: u.prompt,
          renderedPrompt: u.prompt,
          storedEdit: !!u.edited,
          code: u.status === 'ok' ? u.code : '',
          error: u.status === 'error' ? u.error : '',
          at: u.at || '',
        };
      }
      generateState = nextState;
      // Code already stored from an earlier run counts as reviewed, so a reload doesn't
      // demand every unit be re-confirmed. New code landing on this page un-confirms its
      // unit again (fetchLandedCode) — that's the code that still needs a look.
      confirmedGenerateUnits = units.filter((u) => nextState[u.id].code).map((u) => u.id);
      generateUnits = units.map((u) =>
        u.kind === 'setup'
          ? { ...u, label: 'Setup', title: 'Setup', detail: 'TestSet setUp/tearDown pair' }
          : { ...u, label: u.tc_n, title: `Unit ${u.tc_n}`, detail: u.action }
      );
    } catch (e) {
      loadUnitsError = (e && e.message) || String(e);
      return;
    } finally {
      isLoadingUnits = false;
    }
    // A run may already be going (started before a reload, or by this page's previous
    // mount) — one poll picks it up, and stops itself if nothing is in flight.
    startPolling();
  }

  onMount(loadUnits);
  onDestroy(stopPolling);

  $: {
    if (!generateActiveUnitId && generateUnits.length > 0) {
      generateActiveUnitId = generateUnits[0].id;
    }
  }

  $: generateActiveUnit = generateUnits.find((u) => u.id === generateActiveUnitId) ?? null;

  let generateUnitStatuses = {};
  $: {
    const next = {};
    for (const unit of generateUnits) {
      if (confirmedGenerateUnits.includes(unit.id)) {
        next[unit.id] = 'covered';
      } else if (generateState[unit.id]?.code) {
        next[unit.id] = 'review';
      } else {
        next[unit.id] = 'none';
      }
    }
    generateUnitStatuses = next;
  }

  $: generateSummaryStatus =
    generateUnits.length > 0 && generateUnits.every((u) => confirmedGenerateUnits.includes(u.id))
      ? 'covered'
      : 'none';

  $: generateCoveragePercent =
    generateUnits.length === 0
      ? 0
      : Math.round(
          (Object.values(generateUnitStatuses).filter((s) => s === 'covered').length / generateUnits.length) * 100
        );

  function selectGenerateUnit(unitId) {
    generateActiveUnitId = unitId;
  }

  // --- Generation: one dispatch request, then one status poll ------------------------
  // Units in flight server-side, as last reported by the poll (or marked at dispatch).
  // Drives each unit's own arrow-step spinner — the rest of the row stays usable.
  let runningUnitIds = {};
  let isDispatchingAll = false;
  let runStatus = '';
  let dispatchError = '';

  const POLL_MS = 2000;
  let pollTimer = null;
  let pollInFlight = false;

  function startPolling() {
    stopPolling();
    pollTimer = setInterval(pollOnce, POLL_MS);
    pollOnce();
  }

  function stopPolling() {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
  }

  function unitTitle(unitId) {
    return generateUnits.find((u) => u.id === unitId)?.title ?? unitId;
  }

  // A unit's prompt travels with the request only when it is the reviewer's own: edited
  // on this page, or an earlier kept edit the server handed back. Everything else is sent
  // as a bare id and rendered fresh server-side — sending unedited text is how a stale tab
  // once fed a whole run old prompts that the server then kept as edits (current/, 2026-09-07).
  function dispatchItem(unitId) {
    const st = generateState[unitId];
    const edited = st.storedEdit || st.prompt !== st.renderedPrompt;
    return edited && st.prompt.trim() ? { id: unitId, prompt: st.prompt, edited: true } : { id: unitId };
  }

  async function dispatch(unitIds) {
    dispatchError = '';
    for (const id of unitIds) runningUnitIds[id] = true;
    runningUnitIds = runningUnitIds;
    let d;
    try {
      d = await onDispatchUnits(unitIds.map(dispatchItem));
    } catch (e) {
      for (const id of unitIds) delete runningUnitIds[id];
      runningUnitIds = runningUnitIds;
      dispatchError = (e && e.message) || String(e);
      return;
    }
    // Anything the server did not take (or was already running) is reconciled by the poll;
    // only what it confirmed stays marked as in flight here.
    const live = new Set([...(d.dispatched || []), ...(d.already_running || [])]);
    for (const id of unitIds) if (!live.has(id)) delete runningUnitIds[id];
    runningUnitIds = runningUnitIds;
    const n = (d.dispatched || []).length;
    runStatus = n === 0
      ? 'Already running — waiting for it to finish.'
      : `${n} unit${n === 1 ? '' : 's'} dispatched` +
        (d.primed ? ` — ${unitTitle(d.primed)} runs alone first to warm the prompt cache.` : '.');
    startPolling();
  }

  async function pollOnce() {
    if (pollInFlight) return;
    pollInFlight = true;
    let d;
    try {
      d = await onPollStatus();
    } catch (e) {
      pollInFlight = false;
      return;   // a dropped poll is not a failure of the work — the next tick retries
    }
    try {
      const running = new Set(d.running || []);
      const nextRunning = {};
      const landed = [];
      for (const unit of generateUnits) {
        if (running.has(unit.id)) { nextRunning[unit.id] = true; continue; }
        const st = d.units?.[unit.id];
        // `at` is the discriminator, not status: a unit generated by an earlier run is
        // already 'ok', so only a changed `at` means this run replaced its bytes.
        if (st && st.at && st.at !== generateState[unit.id].at) landed.push(unit.id);
      }
      runningUnitIds = nextRunning;
      await Promise.all(landed.map(fetchLandedCode));
      if (running.size === 0) {
        stopPolling();
        if (runStatus) runStatus = settledSummary();
      }
    } finally {
      pollInFlight = false;
    }
  }

  async function fetchLandedCode(unitId) {
    try {
      const r = await onFetchUnitCode(unitId);
      const st = generateState[unitId];
      st.at = r.at || st.at;
      // A failed re-run must not keep showing the old success.
      st.code = r.status === 'ok' ? r.code : '';
      st.error = r.status === 'error' ? (r.error || 'failed') : '';
      generateState = generateState;
      confirmedGenerateUnits = confirmedGenerateUnits.filter((id) => id !== unitId);
    } catch (e) {
      // Leave `at` unchanged so the next poll that sees this unit tries again.
    }
  }

  function settledSummary() {
    const total = generateUnits.length;
    const ok = generateUnits.filter((u) => generateState[u.id].code).length;
    const failed = generateUnits.filter((u) => generateState[u.id].error).length;
    return `${ok}/${total} unit${total === 1 ? '' : 's'} generated` +
      (failed ? ` — ${failed} failed; re-run ${failed === 1 ? 'it' : 'them'} individually.` : '.');
  }

  function generateUnitCode(unitId) {
    if (runningUnitIds[unitId]) return;   // already in flight
    dispatch([unitId]);
  }

  // Only units with no code yet, or whose last run failed — re-generating a unit that
  // already has code is a deliberate per-unit click.
  async function generateAllUnits() {
    const wanted = generateUnits
      .filter((u) => !runningUnitIds[u.id] && (!generateState[u.id].code || generateState[u.id].error))
      .map((u) => u.id);
    if (wanted.length === 0) {
      runStatus = 'Every unit already has code — regenerate one from its own page.';
      return;
    }
    isDispatchingAll = true;
    try {
      await dispatch(wanted);
    } finally {
      isDispatchingAll = false;
    }
  }

  function advanceGenerateUnit() {
    const updatedConfirmed = confirmedGenerateUnits.includes(generateActiveUnitId)
      ? confirmedGenerateUnits
      : [...confirmedGenerateUnits, generateActiveUnitId];
    confirmedGenerateUnits = updatedConfirmed;

    const nextUnconfirmed = generateUnits.find((u) => !updatedConfirmed.includes(u.id));
    generateActiveUnitId = nextUnconfirmed ? nextUnconfirmed.id : GENERATE_SUMMARY_STEP_ID;
    scrollToStepIntro();
  }

  // Seeded once at mount from the session, same convention as group/name above.
  let assembledCode = initialAssembledCode;
  let lintResults = initialLintResults;
  let assembled = !!initialAssembledCode;

  let isAssembling = false;
  let assembleError = '';

  async function assembleAndLint() {
    isAssembling = true;
    assembleError = '';
    try {
      const result = await onAssemble(group.trim(), name.trim());
      assembledCode = result.assembledCode;
      lintResults = result.lintResults;
      assembled = true;
    } catch (e) {
      assembleError = (e && e.message) || String(e);
    } finally {
      isAssembling = false;
    }
  }

  // Generate ends at a linted, unreviewed script — there is no LLM review/fix pass here.
  // Validating and fixing a script happens later, in Test Composer.
  let showSaveModal = false;
  let saveStatus = 'success';
  let saveStatusMessage = '';
  let isSaving = false;

  async function saveAndFinish() {
    isSaving = true;
    try {
      const result = await onSave();
      saveStatus = result.status;
      saveStatusMessage = result.message;
      showSaveModal = true;
      if (result.status === 'success') {
        onFinished && onFinished();
      }
    } finally {
      isSaving = false;
    }
  }

  function goToComposer() {
    showSaveModal = false;
    onNavigate && onNavigate('composer');
  }

  function createAnotherPytest() {
    showSaveModal = false;
    onCreateAnother && onCreateAnother();
  }
</script>

<p class="step-intro">Generated one unit at a time — a unit is a single TestCase class, or the TestSet setup pair. The frame (imports, TestSet, the ts.add_testCase() runner) is rendered here, not by an LLM, so it cannot vary between units. Page through the units: each shows the prompt that will be sent (editable — the button sends what you see) and the code that came back. Summary assembles them locally and lints the result, then you save and finish — the script is not LLM-reviewed here; it is validated and fixed later in Test Composer.</p>

{#if isLoadingUnits}
  <p class="fragment-empty units-loading">Rendering unit prompts…</p>
{/if}
<ErrorBanner message={loadUnitsError && `Loading units failed: ${loadUnitsError}`} />

<div class="arrow-step-row">
  {#each generateUnits as unit (unit.id)}
    <ArrowStep
      label={unit.label}
      wide={unit.kind === 'setup'}
      status={generateUnitStatuses[unit.id] ?? 'none'}
      active={generateActiveUnitId === unit.id}
      loading={!!runningUnitIds[unit.id]}
      onClick={() => selectGenerateUnit(unit.id)}
    />
  {/each}
  {#if generateUnits.length > 0}
    <ArrowStep
      label="Summary"
      wide={true}
      status={generateSummaryStatus}
      active={generateActiveUnitId === GENERATE_SUMMARY_STEP_ID}
      onClick={() => selectGenerateUnit(GENERATE_SUMMARY_STEP_ID)}
    />
  {/if}
</div>

<div class="script-search-toolbar">
  <Button variant="primary" sparkle disabled={generateUnits.length === 0} loading={isDispatchingAll} on:click={generateAllUnits}>Generate All Units</Button>
  <div class="script-search-progress" role="progressbar" aria-valuenow={generateCoveragePercent} aria-valuemin="0" aria-valuemax="100">
    <div class="script-search-progress-fill" style="width: {generateCoveragePercent}%"></div>
  </div>
</div>
{#if runStatus}
  <p class="generate-run-status">{runStatus}</p>
{/if}
<ErrorBanner message={dispatchError && `Dispatch failed: ${dispatchError}`} />
<div class="step-frame">
  {#if generateActiveUnitId === GENERATE_SUMMARY_STEP_ID}
    <p class="step-table-label summary-title">Sequence Step Summary</p>
    <div class="script-summary">
      {#each generateUnits as unit (unit.id)}
        <div class="script-summary-section">
          <div class="sequence-step-summary">
            <span
              class="step-status-badge"
              class:covered={generateUnitStatuses[unit.id] === 'covered'}
              class:review={generateUnitStatuses[unit.id] === 'review'}
              class:none={generateUnitStatuses[unit.id] === 'none'}
              aria-hidden="true"
            >
              {generateUnitStatuses[unit.id] === 'covered' ? '✓' : generateUnitStatuses[unit.id] === 'review' ? '!' : '–'}
            </span>
            <p><strong>{unit.title}</strong> - {unit.detail}</p>
          </div>
        </div>
      {/each}
    </div>

    <p class="step-table-label">Script Naming</p>
    <div class="naming-fields">
      <label class="naming-field">
        <span>Group</span>
        <input class="step-field" bind:value={group} on:blur={saveNaming} placeholder="e.g. AMF_Cluster" />
      </label>
      <label class="naming-field">
        <span>Script name</span>
        <input class="step-field" bind:value={name} on:blur={saveNaming} placeholder="e.g. test_amf_master" />
      </label>
    </div>

    <ErrorBanner message={assembleError && `Assemble failed: ${assembleError}`} />

    <div class="step-actions">
      <Button variant="primary" disabled={generateSummaryStatus !== 'covered'} loading={isAssembling} on:click={assembleAndLint}>Assemble &amp; Lint</Button>
    </div>

    <p class="step-table-label">Assembled Script</p>
    <div class="generate-assembled-editor">
      <EditableField
        type="code"
        bind:value={assembledCode}
        placeholder={'Not assembled yet. Click "Assemble & Lint" above.'}
        height="600px"
      />
    </div>

    {#if assembled}
      <p class="step-table-label">Lint Results</p>
      <ul class="lint-results">
        {#each lintResults as result}
          <li class="lint-result" class:lint-pass={result.level === 'pass'} class:lint-warn={result.level === 'warn'} class:lint-error={result.level === 'error'}>{result.message}</li>
        {/each}
      </ul>
    {/if}

    <div class="step-actions">
      <Button variant="success" disabled={!assembled} loading={isSaving} on:click={saveAndFinish}>Save and Finish</Button>
    </div>

    <StatusModal
      bind:open={showSaveModal}
      status={saveStatus}
      title={saveStatus === 'success' ? 'Save successful' : 'Save failed'}
      message={saveStatusMessage}
      closeText="Close"
    >
      <svelte:fragment slot="actions">
        <Button variant="outline" on:click={createAnotherPytest}>Create Another PyTest</Button>
        <Button variant="outline" on:click={goToComposer}>Compose Test</Button>
      </svelte:fragment>
    </StatusModal>
  {:else if generateActiveUnit}
    <div class="sequence-step-summary">
      <span
        class="step-status-badge"
        class:covered={generateUnitStatuses[generateActiveUnit.id] === 'covered'}
        class:review={generateUnitStatuses[generateActiveUnit.id] === 'review'}
        class:none={generateUnitStatuses[generateActiveUnit.id] === 'none'}
        aria-hidden="true"
      >
        {generateUnitStatuses[generateActiveUnit.id] === 'covered' ? '✓' : generateUnitStatuses[generateActiveUnit.id] === 'review' ? '!' : '–'}
      </span>
      <p><strong>{generateActiveUnit.title}</strong> - {generateActiveUnit.detail}</p>
    </div>
    <div class="step-generate">
      <Button variant="primary" sparkle loading={!!runningUnitIds[generateActiveUnitId]} on:click={() => generateUnitCode(generateActiveUnitId)}>Generate Unit</Button>
    </div>
    <ErrorBanner message={generateState[generateActiveUnitId].error && `Last generation failed: ${generateState[generateActiveUnitId].error}`} />

    <div class="generate-panes">
      <div class="generate-pane generate-pane-prompt">
        <p class="step-table-label">Prompt — editable, sent as shown</p>
        {#key generateActiveUnitId}
          <EditableField type="text" bind:value={generateState[generateActiveUnitId].prompt} />
        {/key}
      </div>
      <div class="generate-pane generate-pane-code">
        <p class="step-table-label">Generated Code</p>
        {#key generateActiveUnitId}
          <EditableField
            type="code"
            bind:value={generateState[generateActiveUnitId].code}
            placeholder={'Not generated yet. Click the "Generate Unit" button above.'}
          />
        {/key}
      </div>
    </div>

    <div class="step-actions">
      <Button variant="primary" disabled={!generateState[generateActiveUnitId].code} on:click={advanceGenerateUnit}>Confirm Unit</Button>
    </div>
  {/if}
</div>

<style>
  .step-intro {
    margin: 0 0 24px;
    color: var(--color-text-muted);
    font-size: 0.94rem;
  }

  .step-table-label {
    margin: 0 0 8px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--color-text-muted);
  }

  .naming-fields {
    display: flex;
    gap: 16px;
    margin: 0 0 20px;
  }

  .naming-field {
    display: flex;
    flex-direction: column;
    gap: 6px;
    flex: 1;
    font-size: 0.8rem;
    color: var(--color-text-muted);
  }

  .step-field {
    width: 100%;
    padding: 8px 10px;
    border-radius: 6px;
    border: 1px solid var(--color-border-surface);
    background: var(--color-bg-content);
    color: var(--color-text);
    font: inherit;
    font-size: 0.9rem;
  }

  .units-loading {
    margin-bottom: 16px;
  }

  .generate-run-status {
    margin: -12px 0 20px;
    color: var(--color-text-muted);
    font-size: 0.85rem;
  }

  .summary-title {
    margin-bottom: 22px;
  }

  .step-actions {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 16px 0 32px;
  }

  .arrow-step-row {
    display: flex;
    flex-wrap: wrap;
    width: 100%;
    gap: 0px 14px;
    padding: 8px 10px 8px 10px;
    border-top: 1px solid var(--color-border-surface);
    border-bottom: 1px solid var(--color-border-surface);
    margin-bottom: 16px;
  }

  .script-search-toolbar {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 24px;
  }

  .script-search-progress {
    flex: 1;
    height: 8px;
    border-radius: 999px;
    background: var(--color-border-surface);
    overflow: hidden;
  }

  .script-search-progress-fill {
    height: 100%;
    background: var(--color-success);
    transition: width 0.2s ease;
  }

  .step-frame {
    border: 1px solid var(--color-border-surface);
    border-radius: 8px;
    padding: 24px 24px 0px 24px;
    width: 100%;
  }

  .sequence-step-summary {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 10px;
  }

  .sequence-step-summary p {
    margin: 0;
    color: var(--color-text);
    font-size: 0.94rem;
  }

  .step-status-badge {
    flex: 0 0 auto;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    color: #fff;
    font-size: 0.75rem;
    font-weight: 700;
    margin-top: 2px;
  }

  .step-status-badge.covered {
    background: var(--color-success);
  }

  .step-status-badge.review {
    background: var(--color-warning);
  }

  .step-status-badge.none {
    background: var(--color-text-muted);
  }

  .step-generate {
    padding-bottom: 20px;
  }

  .script-summary {
    display: flex;
    flex-direction: column;
    gap: 24px;
    width: 100%;
  }

  .fragment-empty {
    margin: 0;
    color: var(--color-text-muted);
    font-size: 0.94rem;
  }

  .generate-panes {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    width: 100%;
    margin-bottom: 8px;
  }

  .generate-pane {
    min-width: 0;
  }

  .generate-pane-prompt {
    flex: 1 1 0;
  }

  .generate-pane-code {
    flex: 2 1 0;
  }

  .generate-assembled-editor {
    margin: 0 0 24px;
  }

  .lint-results {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin: 0 0 24px;
    padding-left: 20px;
  }

  .lint-result {
    font-size: 0.9rem;
  }

  .lint-pass {
    color: var(--color-success);
  }

  .lint-warn {
    color: var(--color-warning);
  }

  .lint-error {
    color: var(--color-error);
    font-weight: 600;
  }
</style>
