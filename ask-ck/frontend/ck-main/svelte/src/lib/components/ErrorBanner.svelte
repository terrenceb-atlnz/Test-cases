<script>
// @ts-nocheck

  /** @type {string} The full, already-composed error text (e.g. "Save failed: ..."). Renders
      nothing when falsy, so callers can bind it directly to their error state. */
  export let message = '';
</script>

{#if message}
  <p class="error-banner">{message}</p>
{/if}

<style>
  .error-banner {
    margin: -20px 0 16px;
    color: var(--color-error);
    font-size: 0.88rem;
    padding: 12px 0;
  }
</style>
