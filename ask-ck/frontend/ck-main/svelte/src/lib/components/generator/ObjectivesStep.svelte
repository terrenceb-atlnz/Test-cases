<script>
  // @ts-nocheck

  import Button from "../Button.svelte";
  import Table from "../Table.svelte";
  import ConfirmModal from "../ConfirmModal.svelte";
  import LlmButton from "../LlmButton.svelte";
  import ErrorBanner from "../ErrorBanner.svelte";
  import { scrollToSection, scrollToBottom } from "../../utils/scroll.js";

  // --- Props: data ------------------------------------------------------------------
  export let summaryColumns = [];
  export let summaryRows = [];

  /** The candidates chosen in the review steps — synthesis is gated on there being any. */
  export let chosenForObjectives = [];

  /** The objective as HTML (a <ul> of <li> lines). Edited as plain lines, stored back as HTML. */
  export let objective = "";

  // --- Props: callbacks -------------------------------------------------------------
  /** @type {() => Promise<any>} Run by the LLM button. */
  export let onSynthesize = async () => null;

  /** @type {(html: string) => Promise<void>} */
  export let onSaveObjective = async () => {};

  /** @type {(() => Promise<void>) | null} null = no confirm action; the button does nothing. */
  export let onConfirm = null;

  // --- Local state ------------------------------------------------------------------
  let isEditing = false;
  let draft = "";
  let isSaving = false;
  let saveError = "";
  let isConfirming = false;
  let confirmError = "";

  $: canReviewObjectives = !!(objective && objective.trim());
  $: draftRows = Math.max(draft.split("\n").length, 4);

  // --- No-candidates gate -----------------------------------------------------------
  // The LLM button awaits onBeforeRun before it starts. With nothing chosen, the gate parks
  // that promise here and opens the modal; the modal's answer resolves it (true = run anyway).
  let showNoCandidatesModal = false;
  let gateResolve = null;

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

  // --- HTML <-> editable lines ------------------------------------------------------
  // The editor works on one objective per line; the stored form is a <ul>. Text with no
  // <li> at all comes back as a single line rather than being lost.
  function htmlToLines(html) {
    if (!html) return [];
    const doc = new DOMParser().parseFromString(html, "text/html");
    const items = [...doc.querySelectorAll("li")];
    if (items.length)
      return items.map((li) => li.textContent.trim()).filter(Boolean);
    const text = (doc.body.textContent || "").trim();
    return text ? [text] : [];
  }

  // Edited lines are typed by the user and later rendered with {@html}, so they are escaped.
  function escapeHtml(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function linesToHtml(text) {
    const items = text
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean);
    if (!items.length) return "";
    return (
      "<ul>\n" +
      items.map((l) => `<li>${escapeHtml(l)}</li>`).join("\n") +
      "\n</ul>"
    );
  }

  // --- Editing ------------------------------------------------------------------------
  function startEdit() {
    draft = htmlToLines(objective).join("\n");
    isEditing = true;
  }

  // The draft is simply abandoned — `objective` was never touched while editing.
  function cancelEdit() {
    isEditing = false;
  }

  async function saveDraft() {
    isSaving = true;
    saveError = "";
    try {
      await onSaveObjective(linesToHtml(draft));
      isEditing = false;
    } catch (e) {
      saveError = (e && e.message) || String(e);
    } finally {
      isSaving = false;
    }
  }

  // --- Confirm ------------------------------------------------------------------------
  async function handleConfirm() {
    if (!onConfirm) return;
    isConfirming = true;
    confirmError = "";
    try {
      await onConfirm();
    } catch (e) {
      confirmError = (e && e.message) || String(e);
    } finally {
      isConfirming = false;
    }
  }
</script>

<p class="cases-intro">
  Generate declarative objective artefacts from the confirmed review summary
  (TestLink / Zephyr / ATPyLib). Review and edit, then confirm before
  synthesizing test steps in Step 6.
</p>
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
      <textarea class="objectives-textarea" bind:value={draft} rows={draftRows}
      ></textarea>
      <p class="objectives-edit-note">
        One objective per line. Keep declarative language.
      </p>
      <ErrorBanner message={saveError && `Save failed: ${saveError}`} />
      <div class="objectives-window-actions">
        <Button variant="primary" loading={isSaving} on:click={saveDraft}
          >Save Draft</Button
        >
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
    <Button
      variant="primary"
      disabled={!canReviewObjectives}
      loading={isConfirming}
      on:click={handleConfirm}>Review &amp; Confirm</Button
    >
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
    border-radius: 8px;
    background: var(--color-bg-surface);
    flex: 1;
    min-height: 0;
  }

  .objectives-html {
    color: var(--color-text);
    font-size: 0.94rem;
    font-weight: 500;
  }

  .objectives-html :global(ul) {
    margin: 0;
    padding-left: 20px;
    display: flex;
    flex-direction: column;
    gap: 24px;
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
    font-size: 0.9rem;
    line-height: 3;
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
