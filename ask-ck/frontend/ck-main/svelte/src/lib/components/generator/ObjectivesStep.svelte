<script>
// @ts-nocheck

  import Button from '../Button.svelte';
  import Table from '../Table.svelte';
  import ConfirmModal from '../ConfirmModal.svelte';
  import LlmButton from '../LlmButton.svelte';
  import ErrorBanner from '../ErrorBanner.svelte';
  import { scrollToCasesIntro, scrollToBottom } from '../../utils/scroll.js';

  /** @type {Array<{ key: string, label: string, width?: number }>} */
  export let summaryColumns = [];

  /** @type {Array} Combined chosen rows from TestLink/Zephyr/ATPyLib, tagged with `source` */
  export let summaryRows = [];

  /** @type {Array} Combined chosen rows (untagged) — used to decide whether any candidates were chosen */
  export let chosenForObjectives = [];

  /** @type {string} The finalized objective — a single server-produced, sanitized HTML
      string (`<ul><li>…</li></ul>`), not an array of bullet lines. Owned by the parent
      (derived reactively from session.step4.objective), not bound here. */
  export let objective = '';

  /** @type {(headers: Record<string, string>) => Promise<any>} Parent-owned closure —
      calls synthesize_objectives and replaces `session` itself (mirrors CandidatePickerStep's
      onConfirm convention: side-effecting calls are owned by whoever holds the session). */
  export let onSynthesize = async () => null;

  /** @type {(objective: string) => Promise<void>} Save-as-draft from the edit textarea —
      confirming always goes through the separate "Review & Confirm" action below, never
      from inside the editor itself. */
  export let onSaveObjective = async () => {};

  /** @type {(() => Promise<void>) | null} Plain "Review & Confirm" with no pending edits. */
  export let onConfirm = null;

  let isEditing = false;
  let draft = '';
  let showNoCandidatesModal = false;
  let gateResolve = null;

  // Checked by LlmButton BEFORE it starts its busy/progress state — the real current/ app
  // has no such gate (synthesizeObjectives() there just runs), but it's kept here as a
  // Svelte-only safety net per explicit instruction. Resolves once the modal is answered,
  // not before, so the gate never races a confirm dialog against the progress ticker.
  function gateBeforeRun() {
    if (chosenForObjectives.length > 0) return Promise.resolve(true);
    return new Promise((resolve) => {
      gateResolve = resolve;
      showNoCandidatesModal = true;
    });
  }
  function handleModalConfirm() {
    gateResolve && gateResolve(true);
    gateResolve = null;
  }
  function handleModalCancel() {
    gateResolve && gateResolve(false);
    gateResolve = null;
  }

  // The server stores/returns the objective as one HTML string (<ul><li>…</li></ul>), but
  // editing raw HTML tags was a bad experience — these two functions are the plain-bullet-
  // lines <-> HTML boundary, so the textarea only ever shows plain text. Falls back to a
  // single block of plain text if the HTML isn't a flat <li> list (e.g. the LLM returned
  // something else) rather than losing content.
  function htmlToLines(html) {
    if (!html) return [];
    const doc = new DOMParser().parseFromString(html, 'text/html');
    const items = [...doc.querySelectorAll('li')];
    if (items.length) return items.map((li) => li.textContent.trim()).filter(Boolean);
    const text = (doc.body.textContent || '').trim();
    return text ? [text] : [];
  }

  function escapeHtml(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function linesToHtml(text) {
    const items = text.split('\n').map((l) => l.trim()).filter(Boolean);
    if (!items.length) return '';
    return '<ul>\n' + items.map((l) => `<li>${escapeHtml(l)}</li>`).join('\n') + '\n</ul>';
  }

  function startEdit() {
    draft = htmlToLines(objective).join('\n');
    isEditing = true;
  }

  function cancelEdit() {
    isEditing = false;
  }

  let isSaving = false;
  let saveError = '';

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

  $: canReviewObjectives = !!(objective && objective.trim());

  // Grows/shrinks with the content instead of a fixed size + inner scrollbar.
  $: draftRows = Math.max(draft.split('\n').length, 4);
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
