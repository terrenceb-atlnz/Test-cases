<script>
  import Button from './Button.svelte';
  import CodeEditor from './CodeEditor.svelte';

  /** @type {string} Bindable committed value */
  export let value = '';

  /** @type {'text' | 'code'} */
  export let type = 'text';

  /** @type {string} */
  export let placeholder = '';

  /** @type {string} CSS height for the display/edit box */
  export let height = '450px';

  let editing = false;
  let draft = value;

  // Keep the draft mirroring the committed value while not editing, so entering edit mode
  // always starts from whatever is current (e.g. after switching units elsewhere).
  $: if (!editing) draft = value;

  function startEdit() {
    draft = value;
    editing = true;
  }

  function saveChanges() {
    value = draft;
    editing = false;
  }

  function cancelEdit() {
    draft = value;
    editing = false;
  }
</script>

{#if editing}
  {#if type === 'code'}
    <CodeEditor bind:value={draft} {placeholder} {height} />
  {:else}
    <textarea
      class="editable-field-textarea"
      style="height: {height}"
      bind:value={draft}
      {placeholder}
    ></textarea>
  {/if}

  <div class="editable-field-actions">
    <Button variant="primary" on:click={saveChanges}>Save Changes</Button>
    <Button variant="outline" on:click={cancelEdit}>Cancel</Button>
  </div>
{:else}
  {#if type === 'code'}
    <pre class="code-view" style="height: {height}">{value || placeholder}</pre>
  {:else}
    <div class="editable-field-view" class:is-placeholder={!value} style="height: {height}">{value || placeholder}</div>
  {/if}

  <div class="editable-field-actions">
    <Button variant="outline" on:click={startEdit}>Edit</Button>
  </div>
{/if}

<style>
  .editable-field-textarea,
  .editable-field-view {
    width: 100%;
    padding: 12px 14px;
    border-radius: 10px;
    border: 1px solid var(--color-border-surface);
    background: var(--color-bg-surface);
    color: var(--color-text);
    font: inherit;
    font-size: 0.94rem;
    line-height: 1.5;
    overflow-y: auto;
  }

  .editable-field-textarea {
    resize: vertical;
    border-color: var(--color-accent);
  }

  .editable-field-view {
    margin: 0;
    white-space: pre-wrap;
    /* Long space-free runs (e.g. a dotted call in a unit prompt) must break inside the box —
       pre-wrap alone only wraps at spaces, so they spilled sideways and widened the page. */
    overflow-wrap: anywhere;
    color: var(--color-text);
    overflow-wrap: anywhere;
  }

  .editable-field-view.is-placeholder {
    color: var(--color-text-muted);
  }

  .editable-field-actions {
    display: flex;
    gap: 10px;
    margin-top: 10px;
  }

  .code-view {
    margin: 0 0 20px;
    max-height: 60vh;
    overflow: auto;
    padding: 16px;
    border-radius: 8px;
    background: var(--color-code-bg);
    border: 1px solid var(--color-border-surface);
    color: var(--color-text);
    font-family: 'SFMono-Regular', Consolas, monospace;
    font-size: 0.82rem;
    line-height: 1.5;
    white-space: pre;
    max-width: 100%;
  }
</style>
