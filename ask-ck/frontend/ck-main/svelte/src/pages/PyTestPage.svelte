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
</script>

<ToolHeader title={title} tool="PYTEST CREATOR" icon={pyTestIcon} />

<Stepper {steps} {currentStep} onStepClick={goToStep} />

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
</style>

