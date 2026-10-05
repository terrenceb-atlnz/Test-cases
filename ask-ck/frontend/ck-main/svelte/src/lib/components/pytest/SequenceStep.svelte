<script>
// @ts-nocheck

  import Button from '../Button.svelte';
  import Table from '../Table.svelte';
  import SequenceTable from '../SequenceTable.svelte';
  import LlmButton from '../LlmButton.svelte';
  import ErrorBanner from '../ErrorBanner.svelte';

  /** @type {Array<{description: string, expectedResult: string}>} The refined case's
      original test steps (the "before") — read-only, from load_case's `steps` field. */
  export let refinedSteps = [];

  /** @type {Array<{n: number, action: string, verify: string, zephyr_step_idx?: number}>}
      The current sequence — owned by the parent (derived from session.step2.sequence or
      a fresh extract result), not bound here. */
  export let sequence = [];

  /** @type {(headers: Record<string, string>) => Promise<any>} Parent-owned closure —
      calls extract_sequence and updates `sequence`/session itself. */
  export let onSynthesize = async () => null;

  /** @type {(sequence: Array) => Promise<void>} Save Edits — persists the edited rows
      without confirming. */
  export let onSaveEdits = async () => {};

  /** @type {(() => Promise<void>) | null} Confirm Step 2. */
  export let onConfirm = null;

  const manualColumns = [
    { key: 'stepNumber', label: '#', width: 1 },
    { key: 'description', label: 'Description', width: 9 }
  ];

  $: manualRows = refinedSteps.map((s, i) => ({ id: `refined-${i}`, stepNumber: i + 1, description: s.description }));

  // SequenceTable's own row shape ({id, from, action, verify}) <-> the API's
  // ({n, action, verify, zephyr_step_idx}). Kept as plain functions (not a service) since
  // this is pure UI-row shaping, not a network call.
  function toRows(seq) {
    return (seq || []).map((s, i) => ({
      id: `seq-${i}`,
      from: typeof s.zephyr_step_idx === 'number' ? s.zephyr_step_idx : '—',
      action: s.action || '',
      verify: s.verify || '',
      zephyr_step_idx: s.zephyr_step_idx,
    }));
  }

  function toSequence(rows) {
    return rows
      .map((r) => ({
        action: (r.action || '').trim(),
        verify: (r.verify || '').trim(),
        ...(typeof r.zephyr_step_idx === 'number' ? { zephyr_step_idx: r.zephyr_step_idx } : {}),
      }))
      .filter((s) => s.action)
      .map((s, i) => ({ ...s, n: i + 1 }));
  }

  let rows = [];
  let seededFor = null;
  // Re-seed whenever the parent hands us a genuinely different sequence (a fresh extract,
  // or switching case) — not on every keystroke, since `rows` is this component's own
  // editable copy the user is actively typing into.
  $: {
    const fingerprint = JSON.stringify(sequence);
    if (fingerprint !== seededFor) {
      rows = toRows(sequence);
      seededFor = fingerprint;
    }
  }

  function handleSynthesizeResult(result) {
    // onSynthesize already updated the parent's `sequence`/session; the fingerprint check
    // above re-seeds `rows` from the new prop value on next tick.
    if (result?.notes) notes = result.notes;
  }

  let notes = '';
  let isSaving = false;
  let saveError = '';
  let saveMessage = '';

  async function handleSaveEdits() {
    isSaving = true;
    saveError = '';
    saveMessage = '';
    try {
      await onSaveEdits(toSequence(rows));
      saveMessage = 'Saved.';
    } catch (e) {
      saveError = (e && e.message) || String(e);
    } finally {
      isSaving = false;
    }
  }

  let isConfirming = false;
  let confirmError = '';

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

  $: hasRows = rows.length > 0;
</script>

<p class="step-intro">The refined case's test steps are shown first (the "before"). Extract Sequence asks the LLM to convert them into a prescriptive, runnable execution order (the "after") — the From column links each extracted row back to its source step so any re-sequencing is visible. Review/edit, then confirm.</p>

<p class="step-table-label">Test Steps (Manual)</p>
<Table columns={manualColumns} rows={manualRows} selectable={false} />

<div class="step-actions">
  <LlmButton
    label="Extract Sequence (LLM)"
    verb="Extracting…"
    onRun={onSynthesize}
    onResult={handleSynthesizeResult}
  />
</div>
{#if notes}<p class="step-notes"><span class="llm-note-header">LLM Notes: </span> {notes}</p>{/if}

<p class="step-table-label">Test Steps (Sequenced)</p>

<SequenceTable bind:rows>
  <svelte:fragment slot="extra-actions">
    <Button variant="outline" disabled={!hasRows} loading={isSaving} on:click={handleSaveEdits}>Save Edits</Button>
    {#if saveMessage}<span class="step-save-message">{saveMessage}</span>{/if}
  </svelte:fragment>
</SequenceTable>

<ErrorBanner message={saveError && `Save failed: ${saveError}`} />
<ErrorBanner message={confirmError && `Confirm failed: ${confirmError}`} />

<div class="step-actions">
  <Button variant="primary" disabled={!hasRows} loading={isConfirming} on:click={handleConfirm}>Confirm Step 2</Button>
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

  .step-notes {
    margin: -20px 0 24px;
    color: var(--color-text-muted);
    font-size: 0.88rem;
    border-top: 1px solid var(--color-border-surface);
    border-bottom: 1px solid var(--color-border-surface);
    padding: 12px 0;
    font-style: italic;
  }

  .llm-note-header {
    font-weight: 700;
    font-style: normal;
  }

  .step-save-message {
    color: var(--color-success);
    font-size: 0.88rem;
  }
</style>
