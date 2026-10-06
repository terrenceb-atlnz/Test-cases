<script>
// @ts-nocheck

  /** @type {string} The full, already-composed error text (e.g. "Save failed: ..."). Renders
      nothing when falsy, so callers can bind it directly to their error state. */
  export let message = '';
</script>

{#if message}
  <p class="error-banner"><span class="error-label">Error -</span> {message}</p>
{/if}

<style>
  .error-banner {
    /* margin: -20px 0 16px; */
    color: var(--color-error);
    font-size: 0.9rem;
    padding: 12px 0;
    background: var(--color-error-surface);
    border: 1px solid var(--color-error-border);
    padding: 8px 12px;
    border-radius: 4px;
  }

  .error-label {
    font-weight: 700;
  }
</style>
