<script>
// @ts-nocheck

  import Button from '../Button.svelte';
  import Table from '../Table.svelte';
  import ConfirmModal from '../ConfirmModal.svelte';
  import LlmButton from '../LlmButton.svelte';
  import ErrorBanner from '../ErrorBanner.svelte';
  import { scrollToCasesIntro, scrollToBottom } from '../../utils/scroll.js';

  // Array of column definitions for the summary table
  export let summaryColumns = [];

  // Array of rows for the summary table, each row representing a summary of chosen candidates
  export let summaryRows = [];

  // Array of chosen candidates that are used to generate the objective
  export let chosenForObjectives = [];

  // The generated objective text that can be reviewed and edited by the user
  export let objective = '';

  // Function to handle the synthesis of objectives using an LLM
  export let onSynthesize = async () => null;

  // Function to handle the saving of the edited objective
  export let onSaveObjective = async () => {};

  // Function to handle the confirmation of the reviewed objective
  export let onConfirm = null;

  // Flag to indicate whether the user is currently editing the objective
  let isEditing = false;

  // The draft text of the objective that the user is currently editing
  let draft = '';

  // Flag to indicate whether the user is currently saving the edited objective
  let showNoCandidatesModal = false;

  // Variable to hold the resolve function for the modal confirmation promise
  let gateResolve = null;

  // Flag to indicate whether the user is currently saving the edited objective
  let isConfirming = false;

  // Variable to hold any error message that occurs during the saving process
  let confirmError = '';

  // Flag to indicate whether the user is currently saving the edited objective
  let isSaving = false;

  // Variable to hold any error message that occurs during the saving process
  let saveError = '';

  // Reactive statement to determine if the user can review the generated objective based on its content
  $: canReviewObjectives = !!(objective && objective.trim());

  // Reactive statement to calculate the number of rows for the textarea based on the draft content
  $: draftRows = Math.max(draft.split('\n').length, 4);

 // Function to gate the synthesis of objectives, ensuring that there are chosen candidates before proceeding
  function gateBeforeRun() {
    if (chosenForObjectives.length > 0) return Promise.resolve(true);
    return new Promise((resolve) => {
      gateResolve = resolve;
      showNoCandidatesModal = true;
    });
  }

  // Function to handle the confirmation of the modal dialog, resolving the promise with a true value
  function handleModalConfirm() {
    gateResolve && gateResolve(true);
    gateResolve = null;
  }

  // Function to handle the cancellation of the modal dialog, resolving the promise with a false value
  function handleModalCancel() {
    gateResolve && gateResolve(false);
    gateResolve = null;
  }

  // Utility function to convert HTML content into an array of text lines. It extracts text from <li> elements 
  // if present, or returns the entire text content as a single line if no <li> elements are found.
  function htmlToLines(html) {
    if (!html) return [];
    const doc = new DOMParser().parseFromString(html, 'text/html');
    const items = [...doc.querySelectorAll('li')];
    if (items.length) return items.map((li) => li.textContent.trim()).filter(Boolean);
    const text = (doc.body.textContent || '').trim();
    return text ? [text] : [];
  }

  // Utility function to escape HTML special characters in a string to prevent XSS attacks when rendering user input.
  function escapeHtml(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  // Utility function to convert a string with line breaks into an HTML unordered list. Each line is wrapped in <li> tags.
  function linesToHtml(text) {
    const items = text.split('\n').map((l) => l.trim()).filter(Boolean);
    if (!items.length) return '';
    return '<ul>\n' + items.map((l) => `<li>${escapeHtml(l)}</li>`).join('\n') + '\n</ul>';
  }

  // Function to initiate the editing of the generated objective. It converts the current objective HTML into a draft text 
  // format for editing.
  function startEdit() {
    draft = htmlToLines(objective).join('\n');
    isEditing = true;
  }

  // Function to cancel the editing of the generated objective, discarding any changes made in the draft and reverting to 
  // the original objective.
  function cancelEdit() {
    isEditing = false;
  }

  // Function to save the edited objective. It converts the draft text back into HTML format and calls the onSaveObjective 
  // prop to persist the changes.
  async function saveDraft() {
    isSaving = true;
    saveError = '';
    try {
      await onSaveObjective(linesToHtml(draft));
      isEditing = false;
    } catch (e) {
      saveError = (e && e.message) || String(e);
    } finally {
      isSaving = false;
    }
  }

  // Function to handle the confirmation of the reviewed objective. It calls the onConfirm prop and manages the isConfirming
  // and confirmError state variables to provide feedback to the user during the confirmation process.
  async function handleConfirm() {
    if (!onConfirm) return;
    isConfirming = true;
    confirmError = '';
    try {
      await onConfirm();
    } catch (e) {
      confirmError = (e && e.message) || String(e);
    } finally {
      isConfirming = false;
    }
  }
</script>

<p class="cases-intro">Generate declarative objective artefacts from the confirmed review summary (TestLink / Zephyr / ATPyLib). Review and edit, then confirm before synthesizing test steps in Step 6.</p>
<p class="testlink-table-label">Summary</p>
<Table columns={summaryColumns} rows={summaryRows} selectable={false} />

<div class="objectives-actions">
  <LlmButton
    label="Synthesize Objectives (LLM)"
    verb="Synthesizing…"
    onBeforeRun={gateBeforeRun}
    onRun={onSynthesize}
    onResult={() => scrollToBottom()}
  />
</div>

<ConfirmModal
  bind:open={showNoCandidatesModal}
  title="No candidates selected"
  message="You haven't selected any TestLink, Zephyr, or ATPyLib candidates. The LLM will do its best using only the Test Case context. Continue anyway?"
  confirmText="Continue"
  cancelText="Cancel"
  onConfirm={handleModalConfirm}
  onCancel={handleModalCancel}
/>

{#if canReviewObjectives}
  <p class="testlink-table-label">Generated Objective</p>
  <div class="objectives-window">
    {#if isEditing}
      <textarea class="objectives-textarea" bind:value={draft} rows={draftRows}></textarea>
      <p class="objectives-edit-note">One objective per line. Keep declarative language.</p>
      <ErrorBanner message={saveError && `Save failed: ${saveError}`} />
      <div class="objectives-window-actions">
        <Button variant="primary" loading={isSaving} on:click={saveDraft}>Save Draft</Button>
        <Button variant="outline" on:click={cancelEdit}>Cancel</Button>
      </div>
    {:else}
      <div class="objectives-html">{@html objective}</div>
      <div class="objectives-window-actions">
        <Button variant="outline" on:click={startEdit}>Edit</Button>
      </div>
    {/if}
  </div>
  {#if !isEditing}
    <ErrorBanner message={confirmError && `Confirm failed: ${confirmError}`} />
    <Button variant="primary" disabled={!canReviewObjectives} loading={isConfirming} on:click={handleConfirm}>Review &amp; Confirm</Button>
  {/if}
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
    padding: 24px;
    margin-bottom: 12px;
    border: 1px solid var(--color-border-surface);
    border-radius: 8px;
    background: var(--color-bg-surface);
    width: 100%;
    flex: 1;
    min-height: 0;
  }

  .objectives-html {
    color: var(--color-text);
    font-size: 0.94rem;
    line-height: 1.5;
  }

  .objectives-html :global(ul) {
    margin: 0;
    padding-left: 20px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .objectives-edit-note {
    margin: 0;
    color: var(--color-text-muted);
    font-size: 0.85rem;
  }


  .objectives-textarea {
    width: 100%;
    padding: 10px 12px;
    border-radius: 8px;
    border: 1px solid var(--color-border-surface);
    background: var(--color-bg-content);
    color: var(--color-text);
    font: inherit;
    font-size: 0.94rem;
    resize: vertical;
    flex: 1;
    min-height: 0;
  }

  .objectives-window-actions {
    display: flex;
    gap: 12px;
    flex: 1;
    min-height: 0;
  }
</style>
