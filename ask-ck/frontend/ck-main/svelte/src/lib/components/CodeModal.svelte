<script>
// @ts-nocheck

  import Button from './Button.svelte';

  /** @type {boolean} Bindable open/closed state */
  export let open = false;

  /** @type {string} e.g. the script id */
  export let title = '';

  /** @type {string} e.g. "lines 1-120" */
  export let subtitle = '';

  /** @type {string} */
  export let code = '';

  /** @type {boolean} */
  export let loading = false;

  /** @type {(() => void) | null} */
  export let onClose = null;

  function handleClose() {
    open = false;
    onClose && onClose();
  }

  function handleBackdropKeydown(event) {
    if (event.key === 'Escape') handleClose();
  }
</script>

{#if open}
  <div
    class="modal-backdrop"
    role="button"
    tabindex="0"
    on:click={handleClose}
    on:keydown={handleBackdropKeydown}
  >
    <div
      class="modal-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="code-modal-title"
      tabindex="-1"
      on:click|stopPropagation
      on:keydown|stopPropagation
    >
      <p id="code-modal-title" class="modal-title">{title}</p>
      {#if subtitle}<p class="modal-subtitle">{subtitle}</p>{/if}
      {#if loading}
        <p class="modal-loading">Loading…</p>
      {:else}
        <pre class="code-view">{code}</pre>
      {/if}
      <div class="modal-actions">
        <Button variant="primary" on:click={handleClose}>Close</Button>
      </div>
    </div>
  </div>
{/if}

<style>
  .modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.45);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    padding: 16px;
  }

  .modal-dialog {
    width: 100%;
    max-width: 860px;
    padding: 24px;
    border-radius: 12px;
    border: 1px solid var(--color-border-surface);
    background: var(--color-bg-surface);
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.25);
  }

  .modal-title {
    margin: 0;
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--color-text);
    word-break: break-all;
  }

  .modal-subtitle {
    margin: 4px 0 16px;
    color: var(--color-text-muted);
    font-size: 0.85rem;
  }

  .modal-loading {
    margin: 0 0 16px;
    color: var(--color-text-muted);
    font-size: 0.88rem;
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
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
  }
</style>
