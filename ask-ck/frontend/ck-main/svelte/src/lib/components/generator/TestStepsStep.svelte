<script>
// @ts-nocheck

  import Button from '../Button.svelte';
  import StatusModal from '../StatusModal.svelte';

  /** @type {Array<string>} The finalized objectives from the previous step (read-only display) */
  export let objectives = [];

  /** @type {() => Promise<Array<string>>} */
  export let onSynthesize = async () => [];

  /** @type {() => Promise<{ status: string, message: string }>} */
  export let onExport = async () => ({ status: 'success', message: '' });

  /** @type {(() => void) | null} Called once the export succeeds — tells the parent to mark the stepper finished */
  export let onFinished = null;

  let testSteps = [];
  let showTestSteps = false;
  let isEditingTestSteps = false;
  let testStepsDraft = '';

  let showExportStatusModal = false;
  let exportStatus = 'success';
  let exportStatusMessage = '';
  let isSynthesizing = false;

  async function synthesizeTestSteps() {
    isSynthesizing = true;
    try {
      testSteps = await onSynthesize();
      showTestSteps = true;
      isEditingTestSteps = false;
    } finally {
      isSynthesizing = false;
    }
  }

  function editTestSteps() {
    testStepsDraft = testSteps.join('\n');
    isEditingTestSteps = true;
  }

  function saveTestSteps() {
    testSteps = testStepsDraft
      .split('\n')
      .map((line) => line.trim())
      .filter((line) => line.length > 0);
    isEditingTestSteps = false;
  }

  function cancelEditTestSteps() {
    isEditingTestSteps = false;
  }


  async function exportRepeatableBundle() {
    const result = await onExport();
    exportStatus = result.status;
    exportStatusMessage = result.message;
    showExportStatusModal = true;
    if (result.status === 'success') {
      onFinished && onFinished();
    }
  }
</script>

<p class="cases-intro">Generate verification steps from the finalized objective (Step 5) plus review context. The first step is always the server-built traceability note. Export the repeatable bundle when ready.</p>

<p class="testlink-table-label">Objectives</p>
<div class="objectives-window">
  <ul class="objectives-list">
    {#each objectives as objective, i (i)}
      <li>{objective}</li>
    {/each}
  </ul>
</div>

<div class="objectives-actions">
  <Button variant="primary" sparkle disabled={objectives.length === 0} loading={isSynthesizing} on:click={synthesizeTestSteps}>Synthesize Test Steps (LLM)</Button>
</div>

{#if showTestSteps}
  <p class="testlink-table-label">Generated Test Steps</p>
  <div class="objectives-window">
    {#if isEditingTestSteps}
      <textarea class="objectives-textarea" bind:value={testStepsDraft} rows="8"></textarea>
      <div class="objectives-window-actions">
        <Button variant="primary" on:click={saveTestSteps}>Save Changes</Button>
        <Button variant="outline" on:click={cancelEditTestSteps}>Cancel</Button>
      </div>
    {:else}
      <ol class="objectives-list">
        {#each testSteps as step, i (i)}
          <li>{step}</li>
        {/each}
      </ol>
      <div class="objectives-window-actions">
        <Button variant="outline" on:click={editTestSteps}>Edit</Button>
      </div>
    {/if}
  </div>

  <div class="export-actions">
    <Button variant="success" on:click={exportRepeatableBundle}>Finish &amp; Export</Button>
  </div>
{/if}

<StatusModal
  bind:open={showExportStatusModal}
  status={exportStatus}
  title={exportStatus === 'success' ? 'Export successful' : 'Export failed'}
  message={exportStatusMessage}
/>

<style>
  .cases-intro {
    margin: 0 0 24px;
    color: var(--color-text-muted);
    font-size: 0.94rem;
  }

  .testlink-table-label {
    margin: 0 0 8px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--color-text-muted);
  }

  .objectives-actions {
    display: flex;
    margin: 24px 0 24px;
  }

  .objectives-window {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 16px;
    margin-bottom: 12px;
    border: 1px solid var(--color-border-surface);
    border-radius: 8px;
    background: var(--color-bg-surface);
    width: 100%;
  }

  .objectives-list {
    margin: 0;
    padding-left: 20px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    color: var(--color-text);
    font-size: 0.94rem;
  }

  .objectives-textarea {
    width: 100%;
    min-height: 160px;
    padding: 10px 12px;
    border-radius: 8px;
    border: 1px solid var(--color-border-surface);
    background: var(--color-bg-content);
    color: var(--color-text);
    font: inherit;
    font-size: 0.94rem;
    resize: vertical;
  }

  .objectives-window-actions {
    display: flex;
    gap: 12px;
  }

  .export-actions {
    display: flex;
    margin-top: 16px;
  }
</style>
