<script>
  import Button from './Button.svelte';

  /** @type {boolean} Bindable open/closed state */
  export let open = false;

  /** @type {string} */
  export let title = 'Are you sure?';

  /** @type {string} */
  export let message = '';

  /** @type {string} */
  export let confirmText = 'Continue';

  /** @type {string} */
  export let cancelText = 'Cancel';

  /** @type {(() => void) | null} */
  export let onConfirm = null;

  /** @type {(() => void) | null} */
  export let onCancel = null;

  function handleConfirm() {
    open = false;
    onConfirm && onConfirm();
  }

  function handleCancel() {
    open = false;
    onCancel && onCancel();
  }

  function handleBackdropKeydown(event) {
    if (event.key === 'Escape') handleCancel();
  }
</script>

{#if open}
  <div
    class="modal-backdrop"
    role="button"
    tabindex="0"
    on:click={handleCancel}
    on:keydown={handleBackdropKeydown}
  >
    <div
      class="modal-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-modal-title"
      tabindex="-1"
      on:click|stopPropagation
      on:keydown|stopPropagation
    >
      <p id="confirm-modal-title" class="modal-title">{title}</p>
      {#if message}
        <p class="modal-message">{message}</p>
      {/if}
      <div class="modal-actions">
        <Button variant="outline" on:click={handleCancel}>{cancelText}</Button>
        <Button variant="primary" on:click={handleConfirm}>{confirmText}</Button>
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

  .modal-title {
    margin: 0 0 8px;
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--color-text-heading);
  }

  .modal-message {
    margin: 0 0 20px;
    color: var(--color-text-muted);
    font-size: 0.92rem;
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
  }
</style>
