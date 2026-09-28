<script>
// @ts-nocheck

  import ArrowStep from '../ArrowStep.svelte';
  import Button from '../Button.svelte';
  import Table from '../Table.svelte';
  import SearchBox from '../SearchBox.svelte';
  import ConfirmModal from '../ConfirmModal.svelte';
  import { scrollToTop, scrollToStepIntro } from '../../utils/scroll.js';

  /** @type {Array<{ id: string, action: string, verify: string }>} Read-only — reactive to edits made back on Sequence */
  export let sequencedTestSteps = [];

  /** @type {Array<{ key: string, label: string, width?: number }>} */
  export let columns = [];

  /** @type {() => Promise<Array>} */
  export let onSuggestForStep = async () => [];

  /** @type {() => Promise<Array>} */
  export let onSuggestAllSteps = async () => [];

  /** @type {(query: string) => Promise<Array>} */
  export let onSearch = async () => [];

  /** @type {(() => void) | null} Called when Review & Confirm is clicked on the Summary panel */
  export let onConfirm = null;

  const SUMMARY_STEP_ID = '__summary__';

  // Per sequenced-step search state, keyed by the sequenced step's id — populated lazily below
  let scriptSearchState = {};
  let activeStepId = null;

  // Ids of sequence steps whose scripts have been explicitly confirmed via "Confirm Scripts" —
  // once confirmed a step's arrow turns green even if it has no chosen scripts.
  let confirmedSteps = [];

  $: {
    for (const step of sequencedTestSteps) {
      if (!scriptSearchState[step.id]) {
        scriptSearchState[step.id] = {
          search: '',
          candidates: [],
          chosen: [],
          selectedCandidateIds: [],
          selectedChosenIds: []
        };
      }
    }
    if (!activeStepId && sequencedTestSteps.length > 0) {
      activeStepId = sequencedTestSteps[0].id;
    }
  }

  $: activeStep = sequencedTestSteps.find((s) => s.id === activeStepId) ?? null;
  $: activeStepIndex = sequencedTestSteps.findIndex((s) => s.id === activeStepId);

  // Recomputed whenever sequencedTestSteps OR scriptSearchState change (both referenced directly
  // here, so Svelte's dependency tracking picks them up — a plain helper function calling into
  // scriptSearchState would NOT retrigger this, since Svelte only tracks identifiers referenced
  // directly in a reactive statement, not ones hidden inside a called function).
  let stepStatuses = {};
  $: {
    const next = {};
    for (const step of sequencedTestSteps) {
      const state = scriptSearchState[step.id];
      if (confirmedSteps.includes(step.id)) {
        next[step.id] = 'covered';
      } else if (state?.chosen.length > 0 || state?.candidates.length > 0) {
        next[step.id] = 'review';
      } else {
        next[step.id] = 'none';
      }
    }
    stepStatuses = next;
  }

  $: summaryStatus =
    sequencedTestSteps.length > 0 && sequencedTestSteps.every((s) => confirmedSteps.includes(s.id))
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

  let isSuggestingForStep = false;

  async function suggestForStep(stepId) {
    isSuggestingForStep = true;
    try {
      scriptSearchState[stepId].candidates = await onSuggestForStep();
      scriptSearchState[stepId].selectedCandidateIds = [];
      scriptSearchState = scriptSearchState;
    } finally {
      isSuggestingForStep = false;
    }
  }

  let isSuggestingAllSteps = false;

  async function suggestAllSteps() {
    isSuggestingAllSteps = true;
    try {
      const candidates = await onSuggestAllSteps();
      for (const step of sequencedTestSteps) {
        scriptSearchState[step.id].candidates = [...candidates];
        scriptSearchState[step.id].selectedCandidateIds = [];
      }
      scriptSearchState = scriptSearchState;
    } finally {
      isSuggestingAllSteps = false;
    }
  }

  async function searchForStep(stepId) {
    scriptSearchState[stepId].candidates = await onSearch(scriptSearchState[stepId].search);
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

  function advanceScriptSearchStep() {
    const updatedConfirmed = confirmedSteps.includes(activeStepId)
      ? confirmedSteps
      : [...confirmedSteps, activeStepId];
    confirmedSteps = updatedConfirmed;

    // Jump to the next step that isn't confirmed yet (not just the next one in order) — steps can
    // be confirmed out of sequence, so "next" must skip over ones already done. Once every step is
    // confirmed, land on the Summary arrow instead.
    const nextUnconfirmed = sequencedTestSteps.find((s) => !updatedConfirmed.includes(s.id));
    activeStepId = nextUnconfirmed ? nextUnconfirmed.id : SUMMARY_STEP_ID;
    scrollToStepIntro();
  }

  let showNoScriptsModal = false;

  function handleConfirmScriptsClick() {
    const chosenCount = scriptSearchState[activeStepId]?.chosen.length ?? 0;
    if (chosenCount === 0) {
      showNoScriptsModal = true;
      return;
    }
    advanceScriptSearchStep();
  }

  function handleConfirm() {
    onConfirm && onConfirm();
  }
</script>

<p class="step-intro">Find reusable scripts per sequence step so it's clear every step is covered. Page through the steps; for each, use its own Suggest (LLM) or keyword search to find scripts and choose the ones to reuse. Each step must be confirmed before being able to move on.</p>

<div class="arrow-step-row">
  {#each sequencedTestSteps as step, i (step.id)}
    <ArrowStep
      label={i + 1}
      status={stepStatuses[step.id] ?? 'none'}
      active={activeStepId === step.id}
      loading={isSuggestingForStep || isSuggestingAllSteps}
      onClick={() => selectStep(step.id)}
    />
  {/each}
  {#if sequencedTestSteps.length > 0}
    <ArrowStep
      label="Summary"
      wide={true}
      status={summaryStatus}
      active={activeStepId === SUMMARY_STEP_ID}
      loading={isSuggestingForStep || isSuggestingAllSteps}
      onClick={() => selectStep(SUMMARY_STEP_ID)}
    />
  {/if}
</div>

<div class="script-search-toolbar">
  <Button variant="primary" sparkle disabled={sequencedTestSteps.length === 0} loading={isSuggestingAllSteps} on:click={suggestAllSteps}>Suggest All Steps (LLM)</Button>
  <div class="script-search-progress" role="progressbar" aria-valuenow={coveragePercent} aria-valuemin="0" aria-valuemax="100">
    <div class="script-search-progress-fill" style="width: {coveragePercent}%"></div>
  </div>
</div>
<div class="step-frame">
  {#if activeStepId === SUMMARY_STEP_ID}
    <p class="step-table-label summary-title">Sequence Step Summary</p>
    <div class="script-summary">
      {#each sequencedTestSteps as step, i (step.id)}
        <div class="script-summary-section">
          <div class="sequence-step-summary">
            <span
              class="step-status-badge"
              class:covered={stepStatuses[step.id] === 'covered'}
              class:review={stepStatuses[step.id] === 'review'}
              class:none={stepStatuses[step.id] === 'none'}
              aria-hidden="true"
            >
              {stepStatuses[step.id] === 'covered' ? '✓' : stepStatuses[step.id] === 'review' ? '!' : '–'}
            </span>
            <p><strong>Sequence Step {i + 1}</strong> - {step.action}</p>
          </div>
          <Table {columns} rows={scriptSearchState[step.id]?.chosen ?? []} selectable={false} />
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
        class:covered={stepStatuses[activeStep.id] === 'covered'}
        class:review={stepStatuses[activeStep.id] === 'review'}
        class:none={stepStatuses[activeStep.id] === 'none'}
        aria-hidden="true"
      >
        {stepStatuses[activeStep.id] === 'covered' ? '✓' : stepStatuses[activeStep.id] === 'review' ? '!' : '–'}
      </span>
      <p><strong>Sequence Step {activeStepIndex + 1}</strong> - {activeStep.action}</p>
    </div>

    <div class="step-actions">
      <SearchBox
        bind:value={scriptSearchState[activeStepId].search}
        placeholder="Search scripts by keyword…"
        buttonLabel="Search"
        onSearch={() => searchForStep(activeStep.id)}
      />
      <Button variant="primary" sparkle loading={isSuggestingForStep} on:click={() => suggestForStep(activeStep.id)}>Suggest for Step {activeStepIndex + 1} (LLM)</Button>
    </div>

    <p class="step-table-label">Candidates — tick rows and choose to shortlist them for this step</p>
    <Table {columns} rows={scriptSearchState[activeStepId].candidates} bind:selected={scriptSearchState[activeStepId].selectedCandidateIds} />

    <div class="testlink-choose-actions">
      <Button variant="outline" on:click={() => chooseSelectedForStep(activeStep.id)}>↓ Choose selected</Button>
    </div>

    <p class="step-table-label">Chosen for this sequence step</p>
    <Table {columns} rows={scriptSearchState[activeStepId].chosen} bind:selected={scriptSearchState[activeStepId].selectedChosenIds} />

    <div class="testlink-final-actions">
      <Button variant="outline" on:click={() => clearSelectedForStep(activeStep.id)}>Clear Selected</Button>
      <Button variant="outline" on:click={() => clearAllForStep(activeStep.id)}>Clear All</Button>
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
    gap: 16px;
    padding: 5px 20px 8px;
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
