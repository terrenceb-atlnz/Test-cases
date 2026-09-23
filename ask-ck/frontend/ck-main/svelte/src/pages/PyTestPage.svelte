<script>
// @ts-nocheck

  import PageCard from '../lib/components/PageCard.svelte';
  import PageHeader from '../lib/components/PageHeader.svelte';
  import ToolHeader from '../lib/components/ToolHeader.svelte';
  import Stepper from '../lib/components/Stepper.svelte';
  import CasePicker from '../lib/components/CasePicker.svelte';
  import Button from '../lib/components/Button.svelte';
  import Table from '../lib/components/Table.svelte';
  import SequenceTable from '../lib/components/SequenceTable.svelte';
  import ArrowStep from '../lib/components/ArrowStep.svelte';
  import ConfirmModal from '../lib/components/ConfirmModal.svelte';

  import briefcaseIcon from '../assets/icons/briefcase.svg';
  import listSortIcon from '../assets/icons/list-sort-descending.svg';
  import folderSearchIcon from '../assets/icons/folder-search.svg';
  import puzzleIcon from '../assets/icons/puzzle.svg';
  import codeIcon from '../assets/icons/code.svg';
  import checkIcon from '../assets/icons/circle-check-big.svg';
  import pyTestIcon from '../assets/icons/pytest.svg';

  const steps = [
    { id: 'cases', label: 'Cases', icon: briefcaseIcon },
    { id: 'sequence', label: 'Sequence', icon: listSortIcon },
    { id: 'script-search', label: 'Script Search', icon: folderSearchIcon },
    { id: 'fragments', label: 'Fragments', icon: puzzleIcon },
    { id: 'generate', label: 'Generate', icon: codeIcon },
    { id: 'validate', label: 'Validate', icon: checkIcon }
  ];

  let currentStep = 0;
  let maxStepReached = 0;

  $: if (currentStep > maxStepReached) maxStepReached = currentStep;

  function goToStep(index) {
    currentStep = index;
  }

  // Mock case lists — replace with a real data source later
  const openPartialCases = [
    { id: 'AWPTCM-T44318', label: 'WPTCM-T44318 — (315) AdvancedManagement_AMF - AMF Master support' },
    { id: 'AWPTCM-T44201', label: 'WPTCM-T44201 — (212) VLAN_Configuration - Tagged port assignment' },
    { id: 'AWPTCM-T44087', label: 'WPTCM-T44087 — (108) StaticRouting - Default route fallback' }
  ];

  const completeCases = [
    { id: 'AWPTCM-T43991', label: 'WPTCM-T43991 — (301) LACP_Bonding - Active-active failover' },
    { id: 'AWPTCM-T43876', label: 'WPTCM-T43876 — (150) DHCP_Snooping - Trusted port enforcement' }
  ];

  function loadAndConfirm(caseId) {
    const loadedCase = [...openPartialCases, ...completeCases].find((c) => c.id === caseId);
    if (loadedCase) {
      title = loadedCase.label;
    }
    currentStep = 1;
  }

  function exportSession() {
    // TODO: wire up real export
  }

  let title = 'No case loaded. Please select a test case to work on.';

  const manualColumns = [
    { key: 'stepNumber', label: '#', width: 1 },
    { key: 'description', label: 'Description', width: 6 }
  ];

  // Mock manual test steps — replace with the steps from the selected case's Objective Generator output
  const manualTestSteps = [
    { id: 'step-1', stepNumber: 1, description: 'Configure the AMF cluster with the required member priorities.' },
    { id: 'step-2', stepNumber: 2, description: 'Trigger a forced reboot of the current master member.' },
    { id: 'step-3', stepNumber: 3, description: 'Wait for master re-election to complete and record the elapsed time.' },
    { id: 'step-4', stepNumber: 4, description: 'Verify the new master matches the expected priority-based candidate.' },
    { id: 'step-5', stepNumber: 5, description: 'Confirm all AMF members report a consistent cluster state.' }
  ];

  // Mock sequenced test steps — replace with real LLM extraction output
  const mockSequencedTestSteps = [
    { id: 'seq-1', from: 1, action: 'Configure the AMF cluster with the required member priorities.', verify: 'Cluster configuration is applied without errors.' },
    { id: 'seq-2', from: 2, action: 'Trigger a forced reboot of the current master member.', verify: 'Reboot command is accepted and the member goes offline.' },
    { id: 'seq-3', from: 3, action: 'Wait for master re-election to complete.', verify: 'Elapsed time is recorded and falls within the expected window.' },
    { id: 'seq-4', from: 4, action: 'Query the identity of the new master.', verify: 'New master matches the expected priority-based candidate.' },
    { id: 'seq-5', from: 5, action: 'Query cluster state from all AMF members.', verify: 'All members report a consistent cluster state.' }
  ];

  let sequencedTestSteps = [];

  function extractSequence() {
    // TODO: replace with a real LLM extraction call
    sequencedTestSteps = mockSequencedTestSteps.map((s) => ({ ...s }));
  }

  function reviewAndConfirmSequence() {
    currentStep = 2;
  }

  const scriptColumns = [
    { key: 'name', label: 'Script', width: 2 },
    { key: 'source', label: 'Source', width: 1 },
    { key: 'description', label: 'Description', width: 3 }
  ];

  // Mock reusable-script pool — replace with a real script index search later
  const scriptPool = [
    { id: 'script-1', name: 'test_port_speed_set', source: 'test_scripts', description: "Sets port speed using the 'speed <n>' CLI command." },
    { id: 'script-2', name: 'test_port_duplex_set', source: 'test_scripts', description: "Sets port duplex mode using 'duplex full/half'." },
    { id: 'script-3', name: 'test_port_autoneg_toggle', source: 'testsuites_art', description: 'Toggles auto-negotiation on a port and verifies the resulting state.' },
    { id: 'script-4', name: 'test_port_link_status', source: 'testsuites_art', description: 'Polls and asserts link status after a configuration change.' },
    { id: 'script-5', name: 'test_port_reset', source: 'test_scripts', description: 'Resets a port to its default configuration.' }
  ];

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

  // Recomputed whenever sequencedTestSteps OR scriptSearchState change (both referenced directly here,
  // so Svelte's dependency tracking picks them up — a plain helper function calling into
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

  function suggestForStep(stepId) {
    // TODO: replace with a real script search / LLM suggestion call
    scriptSearchState[stepId].candidates = [...scriptPool];
    scriptSearchState[stepId].selectedCandidateIds = [];
    scriptSearchState = scriptSearchState;
  }

  function suggestAllSteps() {
    // TODO: replace with a real script search / LLM suggestion call across all steps
    for (const step of sequencedTestSteps) {
      scriptSearchState[step.id].candidates = [...scriptPool];
      scriptSearchState[step.id].selectedCandidateIds = [];
    }
    scriptSearchState = scriptSearchState;
  }

  function searchForStep(stepId) {
    // TODO: replace with a real keyword search call
    const q = scriptSearchState[stepId].search.trim().toLowerCase();
    scriptSearchState[stepId].candidates = q
      ? scriptPool.filter((s) => s.name.toLowerCase().includes(q) || s.description.toLowerCase().includes(q))
      : [...scriptPool];
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

  function confirmScriptSearchAndAdvance() {
    currentStep = 3;
  }
</script>

<ToolHeader title={title} tool="PYTEST CREATOR" icon={pyTestIcon} />

<Stepper {steps} {currentStep} {maxStepReached} onStepClick={goToStep} />

<div class="tool-page">
  {#if currentStep === 0}
    <CasePicker {openPartialCases} {completeCases} onLoad={loadAndConfirm} onExport={exportSession} />
  {:else if currentStep === 1}
    <p class="step-intro">The refined case's test steps are shown first (the "before"). Extract Sequence asks the LLM to convert them into a prescriptive, runnable execution order (the "after") — the From column links each extracted row back to its source step so any re-sequencing is visible. Review/edit, then confirm.</p>

    <p class="step-table-label">Test Steps (Manual)</p>
    <Table columns={manualColumns} rows={manualTestSteps} selectable={false} />

    <div class="step-actions">
      <Button variant="primary" on:click={extractSequence}>Extract Sequence (LLM)</Button>
    </div>

    <p class="step-table-label">Test Steps (Sequenced)</p>

    <SequenceTable
      bind:rows={sequencedTestSteps}
      emptyMessage='No sequenced steps yet. Click "Extract Sequence (LLM)" above.'
    />

    <div class="step-actions">
      <Button variant="primary" disabled={sequencedTestSteps.length === 0} on:click={reviewAndConfirmSequence}>Review &amp; Confirm</Button>
    </div>
  {:else if currentStep === 2}
    <p class="step-intro">Find reusable scripts per sequence step so it's clear every step is covered. Page through the steps; for each, use its own Suggest (LLM) or keyword search to find scripts and choose the ones to reuse. Each step must be confirmed before being able to move on.</p>

    <div class="arrow-step-row">
      {#each sequencedTestSteps as step, i (step.id)}
        <ArrowStep
          label={i + 1}
          status={stepStatuses[step.id] ?? 'none'}
          active={activeStepId === step.id}
          onClick={() => selectStep(step.id)}
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
      <Button variant="primary" disabled={sequencedTestSteps.length === 0} on:click={suggestAllSteps}>Suggest All Steps (LLM)</Button>
      <div class="script-search-progress" role="progressbar" aria-valuenow={coveragePercent} aria-valuemin="0" aria-valuemax="100">
        <div class="script-search-progress-fill" style="width: {coveragePercent}%"></div>
      </div>
    </div>

    {#if activeStepId === SUMMARY_STEP_ID}
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
            <Table columns={scriptColumns} rows={scriptSearchState[step.id]?.chosen ?? []} selectable={false} />
          </div>
        {/each}
      </div>

      <div class="step-actions">
        <Button variant="primary" disabled={summaryStatus !== 'covered'} on:click={confirmScriptSearchAndAdvance}>Review &amp; Confirm</Button>
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
        <Button variant="primary" on:click={() => suggestForStep(activeStep.id)}>Suggest for Sequence Step {activeStepIndex + 1} (LLM)</Button>
      </div>

      <p class="step-table-label">Candidates — tick rows and choose to shortlist them for this step</p>
      <Table columns={scriptColumns} rows={scriptSearchState[activeStepId].candidates} bind:selected={scriptSearchState[activeStepId].selectedCandidateIds} />

      <div class="testlink-choose-actions">
        <Button variant="outline" on:click={() => chooseSelectedForStep(activeStep.id)}>↓ Choose selected</Button>
      </div>

      <p class="step-table-label">Chosen</p>
      <Table columns={scriptColumns} rows={scriptSearchState[activeStepId].chosen} bind:selected={scriptSearchState[activeStepId].selectedChosenIds} />

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
  {:else}
    <p>Hello world</p>
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

  .step-actions {
    display: flex;
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

    /* border-radius: 10px; */
    /* background: var(--color-table-header-bg); */
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

  .sequence-step-summary {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 16px;
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

