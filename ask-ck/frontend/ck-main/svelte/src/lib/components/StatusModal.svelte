<script>
  import Button from './Button.svelte';

  /** @type {boolean} Bindable open/closed state */
  export let open = false;

  /** @type {'success' | 'error'} */
  export let status = 'success';

  /** @type {string} */
  export let title = '';

  /** @type {string} */
  export let message = '';

  /** @type {string} */
  export let closeText = 'Close';

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
      aria-labelledby="status-modal-title"
      tabindex="-1"
      on:click|stopPropagation
      on:keydown|stopPropagation
    >
      <div class="modal-status-row">
        {#if status === 'success'}
          <span class="modal-status-badge modal-status-badge-success" aria-hidden="true">&#10003;</span>
        {:else}
          <span class="modal-status-badge modal-status-badge-error" aria-hidden="true">!</span>
        {/if}
        <p id="status-modal-title" class="modal-title" class:error={status === 'error'}>{title}</p>
      </div>
      {#if message}
        <p class="modal-message">{message}</p>
      {/if}
      <div class="modal-actions">
        <Button variant="primary" on:click={handleClose}>{closeText}</Button>
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
    max-width: 420px;
    padding: 24px;
    border-radius: 12px;
    border: 1px solid var(--color-border-surface);
    background: var(--color-bg-surface);
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.25);
  }

  .modal-status-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 8px;
  }

  .modal-status-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex: 0 0 auto;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    color: #fff;
    font-weight: 700;
    font-size: 0.9rem;
    line-height: 1;
  }

  .modal-status-badge-success {
    background: var(--color-success);
  }

  .modal-status-badge-error {
    background: var(--color-error);
  }

  .modal-title {
    margin: 0;
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--color-success);
  }

  .modal-title.error {
    color: var(--color-error);
  }

  .modal-message {
    margin: 0 0 20px;
    color: var(--color-text-muted);
    font-size: 0.92rem;
    font-style: italic;
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
  }
</style>
