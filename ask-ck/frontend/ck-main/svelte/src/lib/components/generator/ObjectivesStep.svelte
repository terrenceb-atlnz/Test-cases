<script>
// @ts-nocheck

  import Button from '../Button.svelte';
  import Table from '../Table.svelte';
  import ConfirmModal from '../ConfirmModal.svelte';

  /** @type {Array<{ key: string, label: string, width?: number }>} */
  export let summaryColumns = [];

  /** @type {Array} Combined chosen rows from TestLink/Zephyr/ATPyLib, tagged with `source` */
  export let summaryRows = [];

  /** @type {Array} Combined chosen rows (untagged) — used to decide whether any candidates were chosen */
  export let chosenForObjectives = [];

  /** @type {() => Promise<Array<string>>} */
  export let onSynthesize = async () => [];

  /** @type {Array<string>} Bindable — the finalized objectives */
  export let objectives = [];

  /** @type {(() => void) | null} Called when Review & Confirm is clicked */
  export let onConfirm = null;

  let showObjectives = false;
  let isEditingObjectives = false;
  let objectivesDraft = '';
  let showNoCandidatesModal = false;
  let isSynthesizing = false;

  function handleSynthesizeClick() {
    if (chosenForObjectives.length === 0) {
      showNoCandidatesModal = true;
      return;
    }
    synthesize();
  }

  async function synthesize() {
    isSynthesizing = true;
    try {
      objectives = await onSynthesize();
      showObjectives = true;
      isEditingObjectives = false;
    } finally {
      isSynthesizing = false;
    }
  }

  function editObjectives() {
    objectivesDraft = objectives.join('\n');
    isEditingObjectives = true;
  }

  function saveObjectives() {
    objectives = objectivesDraft
      .split('\n')
      .map((line) => line.trim())
      .filter((line) => line.length > 0);
    isEditingObjectives = false;
  }

  function cancelEditObjectives() {
    isEditingObjectives = false;
  }

  $: canReviewObjectives = objectives.length > 0;

  function handleConfirm() {
    onConfirm && onConfirm();
  }
</script>

<p class="cases-intro">Generate declarative objective artefacts from the confirmed review summary (TestLink / Zephyr / ATPyLib). Review and edit, then confirm before synthesizing test steps in Step 6.</p>
<p class="testlink-table-label">Summary</p>
<Table columns={summaryColumns} rows={summaryRows} selectable={false} />

<div class="objectives-actions">
  <Button variant="primary" sparkle loading={isSynthesizing} on:click={handleSynthesizeClick}>Synthesize Objectives (LLM)</Button>
</div>

<ConfirmModal
  bind:open={showNoCandidatesModal}
  title="No candidates selected"
  message="You haven't selected any TestLink, Zephyr, or ATPyLib candidates. The LLM will do its best using only the Test Case context. Continue anyway?"
  confirmText="Continue"
  cancelText="Cancel"
  onConfirm={synthesize}
/>

{#if showObjectives}
  <p class="testlink-table-label">Generated Objectives</p>
  <div class="objectives-window">
    {#if isEditingObjectives}
      <textarea class="objectives-textarea" bind:value={objectivesDraft} rows="8"></textarea>
      <div class="objectives-window-actions">
        <Button variant="primary" on:click={saveObjectives}>Save Changes</Button>
        <Button variant="outline" on:click={cancelEditObjectives}>Cancel</Button>
      </div>
    {:else}
      <ul class="objectives-list">
        {#each objectives as objective, i (i)}
          <li>{objective}</li>
        {/each}
      </ul>
      <div class="objectives-window-actions">
        <Button variant="outline" on:click={editObjectives}>Edit</Button>
      </div>
    {/if}
  </div>
  <Button variant="primary" disabled={!canReviewObjectives} on:click={handleConfirm}>Review &amp; Confirm</Button>
{/if}

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
</style>
