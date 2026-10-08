<script>
// @ts-nocheck

  import ArrowStep from '../ArrowStep.svelte';
  import Button from '../Button.svelte';
  import Table from '../Table.svelte';
  import SearchBox from '../SearchBox.svelte';
  import ConfirmModal from '../ConfirmModal.svelte';
  import CodeModal from '../CodeModal.svelte';
  import LlmButton from '../LlmButton.svelte';

  import { newCallId, cancelLlmCall } from '../../services/llmProgressService.js';
  import { scrollToTop, scrollToStepIntro, scrollToBottom } from '../../utils/scroll.js';

  /** @type {Array<{ id: string, action: string, verify: string }>} Read-only — reactive to edits made back on Sequence */
  export let sequencedTestSteps = [];

  /** @type {Array<{ key: string, label: string, width?: number }>} */
  export let columns = [];

  /** @type {() => Promise<Array>} */
  export let onSuggestForStep = async () => [];

  // /** @type {() => Promise<Array>} */
  // export let onSuggestAllSteps = async () => [];

  /** @type {(query: string) => Promise<Array>} */
  export let onSearch = async () => [];

  /** @type {(() => void) | null} Called when Review & Confirm is clicked on the Summary panel */
  export let onConfirm = null;

  /** @type {(id: string) => Promise<{source: string, start?: number, end?: number}>} */
  export let onViewSource = async () => ({ source: '' });

  /** @type {Record<string, string[]>} Already-saved {stepN(str): [scriptId, ...]} from
      session.step3.selections — used to repopulate `chosen` on mount, since this component's
      own state is destroyed/recreated every time PyTestPage switches away from this step. */
  export let initialSelections = {};

  /** @type {Record<string, object>} Already-saved {scriptId: slimRecord} from
      session.step3.records — the chosen-row snapshots initialSelections' ids resolve to. */
  export let initialRecords = {};

  const SUMMARY_STEP_ID = '__summary__';

  // Per sequenced-step search state, keyed by the sequenced step's id — populated lazily below
  let scriptSearchState = {};
  let activeStepId = null;

  

  // Ids of sequence steps whose scripts have been explicitly confirmed via "Confirm Scripts" —
  // once confirmed a step's arrow turns green even if it has no chosen scripts.
  let confirmedSteps = [];

  $: {
    for (const step of sequencedTestSteps) {
      if (!scriptSearchState[step.n]) {
        // Seed `chosen` from the already-saved session, if any — resolves each saved id
        // through initialRecords for the full chosen-row shape (title/coverage/reason/...),
        // same as current/'s own "chosen tables render with full fidelity forever after".
        const savedIds = initialSelections[String(step.n)] || [];
        const chosen = savedIds.map((id) => initialRecords[id]).filter(Boolean);
        scriptSearchState[step.n] = {
          search: '',
          candidates: [],
          chosen,
          selectedCandidateIds: [],
          selectedChosenIds: []
        };
      }
    }
    if (!activeStepId && sequencedTestSteps.length > 0) {
      activeStepId = sequencedTestSteps[0].n;
    }
  }

  $: activeStep = sequencedTestSteps.find((s) => s.n === activeStepId) ?? null;
  $: activeStepIndex = sequencedTestSteps.findIndex((s) => s.n === activeStepId);

  // Recomputed whenever sequencedTestSteps OR scriptSearchState change (both referenced directly
  // here, so Svelte's dependency tracking picks them up — a plain helper function calling into
  // scriptSearchState would NOT retrigger this, since Svelte only tracks identifiers referenced
  // directly in a reactive statement, not ones hidden inside a called function).
  let stepStatuses = {};
  $: {
    const next = {};
    for (const step of sequencedTestSteps) {
      const state = scriptSearchState[step.n];
      if (confirmedSteps.includes(step.n)) {
        next[step.n] = 'covered';
      } else if (state?.chosen.length > 0 || state?.candidates.length > 0) {
        next[step.n] = 'review';
      } else {
        next[step.n] = 'none';
      }
    }
    stepStatuses = next;
  }

  $: summaryStatus =
    sequencedTestSteps.length > 0 && sequencedTestSteps.every((s) => confirmedSteps.includes(s.n))
      ? 'covered'
      : 'none';

  $: coveragePercent =
    sequencedTestSteps.length === 0
      ? 0
      : Math.round(
          (Object.values(stepStatuses).filter((s) => s === 'covered').length / sequencedTestSteps.length) * 100
        );

  function selectStep(stepId) {
    activeStepId = stepId;
  }

  let stopRequested = false;
  let currentCallId = null;
  let isSuggestingAllSteps = false;
  let suggestAllDone = 0;

  // PORTED FROM current/pytest-creator/pytest.js's saLabel — live progress text on the
  // button itself, doubling as the "click to stop" affordance discoverability.
  $: suggestAllLabel = !isSuggestingAllSteps
    ? 'Suggest All Steps'
    : stopRequested
    ? 'Suggesting stopped…'
    : `Suggesting step ${Math.min(suggestAllDone + 1, sequencedTestSteps.length)}/${sequencedTestSteps.length}… (click to stop)`;

  // Which sequence step's arrow should currently show as loading — only ever one at a time
  // (both suggestForStep and suggestAllSteps' loop are sequential), so a single step.n is
  // enough; an arrow's loading clears the moment ITS OWN step resolves, not when the whole
  // batch finishes.
  let suggestingStepN = null;

  async function suggestForStep(stepId, headers) {
    suggestingStepN = stepId;
    try {
      scriptSearchState[stepId].candidates = await onSuggestForStep(stepId, headers);
      scriptSearchState[stepId].selectedCandidateIds = [];
      scriptSearchState = scriptSearchState;
    } finally {
      suggestingStepN = null;
    }
  }

  // A tab Chromium treats as backgrounded can suspend a pending `await fetch` indefinitely
  // (see agentService.js's ckBrokerLoop comment — same phenomenon, different fetch): the
  // server can complete its side (300s budget for this endpoint) while the browser never
  // runs the JS waiting on it, leaving isSuggestingAllSteps/suggestingStepN stuck until a
  // reload. The broker loop has its own staleness/revival guard for its long-poll fetch;
  // this is the equivalent bound for THIS fetch, which has no such protection otherwise.
  // 360s gives real margin over the server's own 300s timeout for suggest_scripts_step —
  // this is a liveness backstop for a frozen tab, not a normal-latency cutoff.
  const SUGGEST_STEP_TIMEOUT_MS = 360_000;

  function withTimeout(promise, ms, message) {
    let timeoutId;
    const timeout = new Promise((_, reject) => {
      timeoutId = setTimeout(() => reject(new Error(message)), ms);
    });
    return Promise.race([promise, timeout]).finally(() => clearTimeout(timeoutId));
  }

  async function suggestAllSteps() {
    if (isSuggestingAllSteps) {
      stopRequested = true;
      cancelLlmCall(currentCallId);   // true server-side cancel of the in-flight step only
      return;
    }
    isSuggestingAllSteps = true;
    stopRequested = false;
    suggestAllDone = 0;
    for (const step of sequencedTestSteps) {
      if (stopRequested) break;
      suggestingStepN = step.n;
      currentCallId = newCallId();
      try {
        const matches = await withTimeout(
          onSuggestForStep(step.n, { 'X-CK-LLM-Call': currentCallId }),
          SUGGEST_STEP_TIMEOUT_MS,
          `Suggest for step ${step.n} timed out client-side (tab may have been backgrounded) — try again`
        );
        const existing = scriptSearchState[step.n].candidates;
        const seen = new Set(existing.map((c) => c.id));
        const newOnes = matches.filter((m) => !seen.has(m.id));
        scriptSearchState[step.n].candidates = [...existing, ...newOnes];
        scriptSearchState = scriptSearchState;
      } catch (e) {
        // record a failure for this step, same as current/'s run.failures
        // alert(`Suggest for step ${step.n} failed: ${(e && e.message) || String(e)}`);
      } finally {
        suggestingStepN = null;
        suggestAllDone += 1;
      }
    }
    isSuggestingAllSteps = false;
    currentCallId = null;
  }

  async function searchForStep(stepId) {
    // search_scripts is a plain mechanical search with no step concept at all — raw results
    // carry no `coverage` (only an LLM suggest verdict has one) and aren't linked to any
    // sequence step, so this is where that step-scoping happens, same as current/'s own
    // ptSearchStep: default coverage to 'partial' and tag every result with this step.
    const results = await onSearch(scriptSearchState[stepId].search);
    scriptSearchState[stepId].candidates = results.map((r) => ({
      ...r,
      coverage: r.coverage || 'partial',
      covers_steps: [stepId],
    }));
    scriptSearchState[stepId].selectedCandidateIds = [];
    scriptSearchState = scriptSearchState;
  }

  function chooseSelectedForStep(stepId) {
    const state = scriptSearchState[stepId];
    const moving = state.candidates.filter((c) => state.selectedCandidateIds.includes(c.id));
    if (moving.length === 0) return;
    scriptSearchState[stepId].chosen = [...state.chosen, ...moving];
    scriptSearchState[stepId].candidates = state.candidates.filter((c) => !state.selectedCandidateIds.includes(c.id));
    scriptSearchState[stepId].selectedCandidateIds = [];
    scriptSearchState = scriptSearchState;
    scrollToBottom();
  }

  function clearSelectedForStep(stepId) {
    const state = scriptSearchState[stepId];
    const moving = state.chosen.filter((c) => state.selectedChosenIds.includes(c.id));
    if (moving.length === 0) return;
    scriptSearchState[stepId].candidates = [...state.candidates, ...moving];
    scriptSearchState[stepId].chosen = state.chosen.filter((c) => !state.selectedChosenIds.includes(c.id));
    scriptSearchState[stepId].selectedChosenIds = [];
    scriptSearchState = scriptSearchState;
  }

  function clearAllForStep(stepId) {
    const state = scriptSearchState[stepId];
    scriptSearchState[stepId].candidates = [...state.candidates, ...state.chosen];
    scriptSearchState[stepId].chosen = [];
    scriptSearchState[stepId].selectedChosenIds = [];
    scriptSearchState = scriptSearchState;
  }

  async function advanceScriptSearchStep() {
    const updatedConfirmed = confirmedSteps.includes(activeStepId)
      ? confirmedSteps
      : [...confirmedSteps, activeStepId];
    confirmedSteps = updatedConfirmed;

    // Persist at every per-step confirm, not just the Summary's final Review & Confirm —
    // otherwise navigating away (e.g. to Fragments) before ever reaching the Summary loses
    // everything, since this component's own scriptSearchState is destroyed the moment
    // PyTestPage.svelte switches currentStep away from it. buildSaveMatchesPayload already
    // scans every step's current chosen list, so this is a full, correct snapshot each time,
    // not an incremental/partial one.
    try {
      const { selections, records } = buildSaveMatchesPayload();
      await onSaveMatches(selections, records);
    } catch (e) {
      alert(`Failed to save script selections: ${(e && e.message) || String(e)}`);
    }

    // Jump to the next step that isn't confirmed yet (not just the next one in order) — steps can
    // be confirmed out of sequence, so "next" must skip over ones already done. Once every step is
    // confirmed, land on the Summary arrow instead.
    const nextUnconfirmed = sequencedTestSteps.find((s) => !updatedConfirmed.includes(s.n));
    activeStepId = nextUnconfirmed ? nextUnconfirmed.n : SUMMARY_STEP_ID;
    scrollToStepIntro();
  }

  // "View source" — a button column appended to `columns` so every script table (candidates,
  // chosen, and the summary's per-step chosen table) gets it for free, matching current/'s
  // _ptMatchTable which adds the same "view" td to both kinds of script rows.
  let codeModalOpen = false;
  let codeModalTitle = '';
  let codeModalSubtitle = '';
  let codeModalSource = '';
  let codeModalLoading = false;

  async function viewSource(row) {
    codeModalOpen = true;
    codeModalLoading = true;
    codeModalTitle = row.id;
    codeModalSubtitle = '';
    codeModalSource = '';
    try {
      const d = await onViewSource(row.id);
      codeModalSource = d.source || '';
      codeModalSubtitle = `lines ${d.start ?? 1}-${d.end ?? ''}`;
    } catch (e) {
      codeModalSource = (e && e.message) || String(e);
    } finally {
      codeModalLoading = false;
    }
  }

  $: tableColumns = [...columns, { key: '_viewSource', label: '', width: 1, button: { label: 'View', onClick: viewSource } }];

  let showNoScriptsModal = false;

  function handleConfirmScriptsClick() {
    const chosenCount = scriptSearchState[activeStepId]?.chosen.length ?? 0;
    if (chosenCount === 0) {
      showNoScriptsModal = true;
      return;
    }
    advanceScriptSearchStep();
  }

  export let onSaveMatches = async () => {};

  function buildSaveMatchesPayload() {
    const selections = {};
    const records = {};
    for (const step of sequencedTestSteps) {
      const chosen = scriptSearchState[step.n]?.chosen ?? [];
      if (chosen.length) selections[step.n] = chosen.map((c) => c.id);
      for (const c of chosen) records[c.id] = c;
    }
    return { selections, records };
  }

  async function handleConfirm() {
    const { selections, records } = buildSaveMatchesPayload();
    await onSaveMatches(selections, records);
    onConfirm && onConfirm();
  }

</script>

<p class="step-intro">Find reusable scripts per sequence step so it's clear every step is covered. Page through the steps; for each, use its own Suggest (LLM) or keyword search to find scripts and choose the ones to reuse. Each step must be confirmed before being able to move on.</p>

<div class="arrow-step-row">
  {#each sequencedTestSteps as step, i (step.n)}
    <ArrowStep
      label={i + 1}
      status={stepStatuses[step.n] ?? 'none'}
      active={activeStepId === step.n}
      loading={suggestingStepN === step.n}
      onClick={() => selectStep(step.n)}
    />
  {/each}
  {#if sequencedTestSteps.length > 0}
    <ArrowStep
      label="Summary"
      wide={true}
      status={summaryStatus}
      active={activeStepId === SUMMARY_STEP_ID}
      onClick={() => selectStep(SUMMARY_STEP_ID)}
    />
  {/if}
</div>

<div class="script-search-toolbar">
  <Button variant="primary" sparkle disabled={sequencedTestSteps.length === 0 || (isSuggestingAllSteps && stopRequested)} busy={isSuggestingAllSteps} on:click={suggestAllSteps}>{suggestAllLabel}</Button>
  <div class="script-search-progress" role="progressbar" aria-valuenow={coveragePercent} aria-valuemin="0" aria-valuemax="100">
    <div class="script-search-progress-fill" style="width: {coveragePercent}%"></div>
  </div>
</div>
<div class="step-frame">
  {#if activeStepId === SUMMARY_STEP_ID}
    <p class="step-table-label summary-title">Sequence Step Summary</p>
    <div class="script-summary">
      {#each sequencedTestSteps as step, i (step.n)}
        <div class="script-summary-section">
          <div class="sequence-step-summary">
            <span
              class="step-status-badge"
              class:covered={stepStatuses[step.n] === 'covered'}
              class:review={stepStatuses[step.n] === 'review'}
              class:none={stepStatuses[step.n] === 'none'}
              aria-hidden="true"
            >
              {stepStatuses[step.n] === 'covered' ? '✓' : stepStatuses[step.n] === 'review' ? '!' : '–'}
            </span>
            <p><strong>Sequence Step {i + 1}</strong> - {step.action}</p>
          </div>
          <Table columns={tableColumns} rows={scriptSearchState[step.n]?.chosen ?? []} selectable={false} />
        </div>
      {/each}
    </div>

    <div class="step-actions">
      <Button variant="primary" disabled={summaryStatus !== 'covered'} on:click={handleConfirm}>Review &amp; Confirm</Button>
    </div>
  {:else if activeStep}
    <div class="sequence-step-summary">
      <span
        class="step-status-badge"
        class:covered={stepStatuses[activeStep.n] === 'covered'}
        class:review={stepStatuses[activeStep.n] === 'review'}
        class:none={stepStatuses[activeStep.n] === 'none'}
        aria-hidden="true"
      >
        {stepStatuses[activeStep.n] === 'covered' ? '✓' : stepStatuses[activeStep.n] === 'review' ? '!' : '–'}
      </span>
      <p><strong>Sequence Step {activeStepIndex + 1}</strong> - {activeStep.action}</p>
    </div>

    <div class="step-actions">
      <SearchBox
        bind:value={scriptSearchState[activeStepId].search}
        placeholder="Search scripts by keyword…"
        buttonLabel="Search"
        onSearch={() => searchForStep(activeStep.n)}
      />
      <LlmButton
        label="Suggest for Step {activeStepIndex + 1}"
        verb="Suggesting…"
        onRun={(headers) => suggestForStep(activeStep.n, headers)}
      />    
    </div>
    <p class="step-table-label">Candidates — tick rows and choose to shortlist them for this step</p>
    <Table columns={tableColumns} rows={scriptSearchState[activeStepId].candidates} bind:selected={scriptSearchState[activeStepId].selectedCandidateIds} />

    <div class="testlink-choose-actions">
      <Button variant="outline" on:click={() => chooseSelectedForStep(activeStep.n)}>↓ Choose selected</Button>
    </div>

    <p class="step-table-label">Chosen for this sequence step</p>
    <Table columns={tableColumns} rows={scriptSearchState[activeStepId].chosen} bind:selected={scriptSearchState[activeStepId].selectedChosenIds} />

    <div class="testlink-final-actions">
      <Button variant="outline" on:click={() => clearSelectedForStep(activeStep.n)}>Clear Selected</Button>
      <Button variant="outline" on:click={() => clearAllForStep(activeStep.n)}>Clear All</Button>
    </div>

    <div class="step-actions">
      <Button variant="primary" on:click={handleConfirmScriptsClick}>Confirm Scripts</Button>
    </div>

    <ConfirmModal
      bind:open={showNoScriptsModal}
      title="No scripts chosen"
      message="You haven't chosen any scripts for this sequence step. Continue anyway?"
      confirmText="Continue"
      cancelText="Cancel"
      onConfirm={advanceScriptSearchStep}
    />
  {/if}
</div>

<CodeModal
  bind:open={codeModalOpen}
  title={codeModalTitle}
  subtitle={codeModalSubtitle}
  code={codeModalSource}
  loading={codeModalLoading}
/>

<style>
  .step-intro {
    margin: 0 0 24px;
    color: var(--color-text-muted);
    font-size: 0.94rem;
  }

  .step-table-label {
    margin: 0 0 8px;
    font-size: 0.9rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--color-text-muted);
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

  .testlink-choose-actions {
    display: flex;
    gap: 12px;
    margin: 16px 0;
  }

  .testlink-final-actions {
    display: flex;
    gap: 12px;
    margin-top: 20px;
  }

  .script-summary {
    display: flex;
    flex-direction: column;
    gap: 24px;
    width: 100%;
  }
</style>
