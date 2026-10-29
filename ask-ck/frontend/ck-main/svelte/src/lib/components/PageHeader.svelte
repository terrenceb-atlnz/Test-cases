<script>
  export let title = "";
  export let intro = "";
</script>

<div class="page-header">
  <h1>{title}</h1>
  {#if intro}<p>{intro}</p>{/if}
</div>

<style>
  .page-header {
    text-align: left;
    border-top: 1px solid var(--color-border-surface);
    margin-top: -16px;
    padding: 32px 32px 0px 48px;
    background: var(--color-bg-content);
  }

  .page-header h1 {
    margin: 0 0 8px;
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--color-text-heading);
  }

  .page-header p {
    margin: 0;
    max-width: 880px;
    color: var(--color-text-muted);
    font-size: 1rem;
    line-height: 1.6;
  }
</style>
