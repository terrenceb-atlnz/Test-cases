<script>
// @ts-nocheck

  import Button from '../Button.svelte';
  import Table from '../Table.svelte';
  import SequenceTable from '../SequenceTable.svelte';

  /** @type {() => Promise<Array>} */
  export let onSynthesize = async () => [];

  /** @type {Array} Bindable — the extracted, editable sequence of test steps */
  export let sequencedTestSteps = [];

  /** @type {(() => void) | null} Called when Review & Confirm is clicked */
  export let onConfirm = null;

  const manualColumns = [
    { key: 'stepNumber', label: '#', width: 1 },
    { key: 'description', label: 'Description', width: 9 }
  ];

  // Mock manual test steps — replace with the steps from the selected case's Objective Generator output
  const manualTestSteps = [
    { id: 'step-1', stepNumber: 1, description: 'Configure the AMF cluster with the required member priorities.' },
    { id: 'step-2', stepNumber: 2, description: 'Trigger a forced reboot of the current master member.' },
    { id: 'step-3', stepNumber: 3, description: 'Wait for master re-election to complete and record the elapsed time.' },
    { id: 'step-4', stepNumber: 4, description: 'Verify the new master matches the expected priority-based candidate.' },
    { id: 'step-5', stepNumber: 5, description: 'Confirm all AMF members report a consistent cluster state.' }
  ];

  let isExtractingSequence = false;

  async function extractSequence() {
    isExtractingSequence = true;
    try {
      sequencedTestSteps = await onSynthesize();
    } finally {
      isExtractingSequence = false;
    }
  }

  function handleConfirm() {
    onConfirm && onConfirm();
  }
</script>

<p class="step-intro">The refined case's test steps are shown first (the "before"). Extract Sequence asks the LLM to convert them into a prescriptive, runnable execution order (the "after") — the From column links each extracted row back to its source step so any re-sequencing is visible. Review/edit, then confirm.</p>

<p class="step-table-label">Test Steps (Manual)</p>
<Table columns={manualColumns} rows={manualTestSteps} selectable={false} />

<div class="step-actions">
  <Button variant="primary" sparkle loading={isExtractingSequence} on:click={extractSequence}>Extract Sequence (LLM)</Button>
</div>

<p class="step-table-label">Test Steps (Sequenced)</p>

<SequenceTable bind:rows={sequencedTestSteps} />

<div class="step-actions">
  <Button variant="primary" disabled={sequencedTestSteps.length === 0} on:click={handleConfirm}>Review &amp; Confirm</Button>
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
    align-items: center;
    gap: 12px;
    margin: 16px 0 32px;
  }
</style>
