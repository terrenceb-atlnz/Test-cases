<script>
// @ts-nocheck

  import Button from '../Button.svelte';
  import ConfirmModal from '../ConfirmModal.svelte';
  import StatusModal from '../StatusModal.svelte';
  import LlmButton from '../LlmButton.svelte';
  import ErrorBanner from '../ErrorBanner.svelte';
  import UploadIcon from '../../../assets/icons/upload.svg';
  import { scrollToBottom } from '../../utils/scroll.js';

  export let caseKey = '';

  export let objective = '';

  export let steps = [];

  export let onSynthesize = async () => null;

  export let onSaveSteps = async () => {};

  export let onExport = async () => ({});

  export let onPushToZephyr = async () => ({});

  export let onFinished = null;

  let isEditing = false;
  let draftSteps = [];

  function startEdit() {
    draftSteps = steps.map((s) => ({ description: s.description || '', expectedResult: s.expectedResult || '' }));
    isEditing = true;
  }

  function cancelEdit() {
    isEditing = false;
  }

  function addStep() {
    draftSteps = [...draftSteps, { description: '', expectedResult: '' }];
  }

  function removeStep(idx) {
    draftSteps = draftSteps.filter((_, i) => i !== idx);
  }

  let isSaving = false;
  let saveError = '';

  async function saveChanges() {
    isSaving = true;
    saveError = '';
    try {
      await onSaveSteps(draftSteps.map((s) => ({
        description: (s.description || '').trim(),
        expectedResult: (s.expectedResult || '').trim(),
      })));
      isEditing = false;
    } catch (e) {
      saveError = (e && e.message) || String(e);
    } finally {
      isSaving = false;
    }
  }
  // Function to handle the confirmation of the reviewed test steps. It calls the onConfirm prop and manages the isConfirming
  // and confirmError state variables to provide feedback to the user during the confirmation process.
  let isExporting = false;
  let showExportModal = false;
  let exportStatus = 'success';
  let exportTitle = '';
  let exportMessage = '';

  async function handleExport() {
    isExporting = true;
    try {
      const data = await onExport();
      const v = data.validation || {};
      if (data.wrote_bundle === false) {
        exportStatus = 'error';
        exportTitle = 'Export blocked';
        const headline = data.message ? data.message.split('\n')[0] : 'Export blocked — no bundle written.';
        const issues = (v.issues && v.issues.length) ? ' Issues: ' + v.issues.join('; ') : '';
        exportMessage = headline + issues;
      } else {
        exportStatus = 'success';
        exportTitle = 'Export successful';
        const files = (data.saved_files && data.saved_files.length) ? data.saved_files.join(', ') : '';
        const warnings = (v.warnings && v.warnings.length) ? ' Advisory warnings: ' + v.warnings.join('; ') : '';
        exportMessage = `Saved to ${data.saved_to}/ (${files}).${warnings}`;
        onFinished && onFinished();
      }
    } catch (e) {
      exportStatus = 'error';
      exportTitle = 'Export failed';
      exportMessage = (e && e.message) || String(e);
    } finally {
      isExporting = false;
      showExportModal = true;
    }
  }

  let isPushingPreview = false;
  let isPushingExecute = false;
  let pushOutput = '';
  let showPushConfirmModal = false;

  function formatPushOutput(data, execute) {
    const header = data.ok === false
      ? `⚠ Push ${execute ? 'FAILED' : 'preview reported problems'} (exit ${data.returncode}) — check JIRA_KEY in secrets.md and output below:\n\n`
      : (execute ? '✓ Push complete:\n\n' : 'Dry-run preview (no changes made):\n\n');
    return header + (data.output || '');
  }

  async function handlePreviewPush() {
    isPushingPreview = true;
    pushOutput = 'Previewing (dry-run, no writes)…';
    try {
      const data = await onPushToZephyr({ dryRun: true });
      pushOutput = formatPushOutput(data, false);
    } catch (e) {
      pushOutput = 'Push preview failed: ' + ((e && e.message) || String(e));
    } finally {
      isPushingPreview = false;
    }
  }

  function handlePushClick() {
    showPushConfirmModal = true;
  }

  async function executePush() {
    isPushingExecute = true;
    pushOutput = 'Pushing to Zephyr…';
    try {
      const data = await onPushToZephyr({ dryRun: false });
      pushOutput = formatPushOutput(data, true);
    } catch (e) {
      pushOutput = 'Push failed: ' + ((e && e.message) || String(e));
    } finally {
      isPushingExecute = false;
    }
  }

  $: pushConfirmMessage = `Push ${caseKey} to the LIVE Zephyr server?\n\n`
    + 'This will:\n'
    + '  1. Strip a leading "(N)" group from the test-case title\n'
    + '  2. Create a NEW version (e.g. 1.0 → 2.0)\n'
    + '  3. Upload the objective + test steps onto the new version\n'
    + '  4. Attach traceability.md + web links\n\n'
    + 'Tip: run "Preview Push (dry-run)" first. Continue?';

  $: hasSteps = steps.length > 0;
</script>

<p class="cases-intro">Generate verification steps from the finalized objective plus review context. The first step is always the server-built traceability note. Export the repeatable bundle when ready.</p>

<p class="testlink-table-label">Objective</p>
<div class="objectives-window">
  <div class="objectives-html">{@html objective || '<em>No objective on session.</em>'}</div>
</div>

<div class="objectives-actions">
  {#if objective}
    <LlmButton
      label="Synthesize Test Steps (LLM)"
      verb="Synthesizing…"
      onRun={onSynthesize}
      onResult={() => scrollToBottom()}
    />
  {:else}
    <Button variant="primary" disabled>Synthesize Test Steps</Button>
  {/if}
</div>

{#if hasSteps}
  <p class="testlink-table-label">Generated Test Steps</p>
  <div class="objectives-window">
    {#if isEditing}
      <div class="editable-steps">
        {#each draftSteps as step, i (i)}
          <div class="editable-step">
            <div class="editable-step-num">{i + 1}.</div>
            <div class="editable-step-fields">
              <input class="step-field" bind:value={step.description} placeholder="Step description" />
              <input class="step-field" bind:value={step.expectedResult} placeholder="Expected result (optional)" />
            </div>
            <Button variant="outline" on:click={() => removeStep(i)}>Remove</Button>
          </div>
        {/each}
      </div>
      <ErrorBanner message={saveError && `Save failed: ${saveError}`} />
      <div class="objectives-window-actions">
        <Button variant="primary" loading={isSaving} on:click={saveChanges}>Save Changes</Button>
        <Button variant="outline" on:click={cancelEdit}>Cancel</Button>
        <Button variant="outline" on:click={addStep}>+ Add step</Button>
      </div>
    {:else}
      <ol class="steps-list">
        {#each steps as step, i (i)}
          <li>
            <div>{step.description}</div>
            {#if step.expectedResult}
              <div class="step-expected"><em>Expected:</em> {step.expectedResult}</div>
            {/if}
          </li>
        {/each}
      </ol>
      <div class="objectives-window-actions">
        <Button variant="outline" on:click={startEdit}>Edit</Button>
      </div>
    {/if}
  </div>

  <div class="export-actions">
    <Button variant="success" loading={isExporting} on:click={handleExport}>Export Repeatable Bundle</Button>
  </div>

  <div class="push-actions">
    <Button variant="outline" loading={isPushingPreview} on:click={handlePreviewPush}>Preview Push (dry-run)</Button>
    <Button variant="primary" loading={isPushingExecute} on:click={handlePushClick}>Push to Zephyr</Button>
  </div>
  <p class="push-note">Push uses the <strong>last exported bundle on disk</strong> (click <em>Export Repeatable Bundle</em> first if you've made edits). On the live Zephyr case it strips a leading <code>(N)</code> title group, ensures version 2.0, and uploads the objective + steps + traceability onto it. Run <em>Preview</em> first.</p>
  {#if pushOutput}<pre class="push-output">{pushOutput}</pre>{/if}
{/if}

<ConfirmModal
  bind:open={showPushConfirmModal}
  title="Push to the LIVE Zephyr server?"
  message={pushConfirmMessage}
  confirmText="Push"
  cancelText="Cancel"
  onConfirm={executePush}
/>

<StatusModal
  bind:open={showExportModal}
  status={exportStatus}
  title={exportTitle}
  message={exportMessage}
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
    flex: 1;
    min-height: 0;
  }

  .objectives-html :global(ul) {
    margin: 0;
    padding-left: 20px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .steps-list {
    margin: 0;
    padding-left: 20px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    color: var(--color-text);
    font-size: 0.94rem;
    flex: 1;
    min-height: 0;
  }

  .step-expected {
    margin-top: 2px;
    color: var(--color-text-muted);
    font-size: 0.88rem;
  }

  .editable-steps {
    display: flex;
    flex-direction: column;
    gap: 10px;
    flex: 1;
    min-height: 0;
  }

  .editable-step {
    display: flex;
    align-items: flex-start;
    gap: 10px;
  }

  .editable-step-num {
    flex: 0 0 auto;
    padding-top: 8px;
    color: var(--color-text-muted);
    font-size: 0.88rem;
  }

  .editable-step-fields {
    flex: 1 1 auto;
    display: flex;
    flex-direction: column;
    gap: 6px;
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


  .objectives-window-actions {
    display: flex;
    gap: 12px;
  }

  .export-actions {
    display: flex;
    margin-top: 16px;
  }

  .push-actions {
    display: flex;
    gap: 12px;
    margin-top: 16px;
  }

  .push-note {
    margin: 12px 0 0;
    color: var(--color-text-muted);
    font-size: 0.85rem;
  }

  .push-output {
    margin-top: 12px;
    padding: 12px;
    border-radius: 8px;
    border: 1px solid var(--color-border-surface);
    background: var(--color-bg-content);
    color: var(--color-text);
    font-size: 0.85rem;
    white-space: pre-wrap;
    word-break: break-word;
  }
</style>
