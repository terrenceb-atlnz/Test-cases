<script>
  export let title = '';
  export let intro = '';
</script>

<div class="page-header">
  <h1>{title}</h1>
  {#if intro}<p>{intro}</p>{/if}
</div>
<hr class="page-header-rule" />

<style>
  .page-header {
    text-align: left;
  }

  .page-header h1 {
    margin: 0 0 8px;
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--color-text-heading);
  }

  .page-header p {
    margin: 0;
    max-width: 880px;
    color: var(--color-text-muted);
    font-size: 0.9rem;
    line-height: 1.6;
  }

  .page-header-rule {
    width: 100%;
    border: none;
    border-top: 1px solid var(--color-border-surface);
    margin: 16px 0 16px;
  }
</style>
