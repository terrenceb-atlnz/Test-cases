<script>
  export let title = '';
  export let tool = '';
  export let icon = '';
</script>

<div class="page-header">
  {#if icon}
    <img src={icon} alt="Tool Icon" class="tool-icon" />
  {/if}
  <div class="tool-header">
    <p>{tool}</p>
    <h1>{title}</h1>
  </div>
</div>
<hr class="page-header-rule" />

<style>
  .page-header {
    text-align: left;
    display: flex;
    align-items: center;
    padding: 8px 32px 8px;
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
    font-size: 1rem;
    font-weight: 700;
    line-height: 1.6;
  }

  .page-header-rule {
    /* width: 100%; */
    border: none;
    border-bottom: 1px solid var(--color-border-surface);
    margin-left: 80px;
    margin-right: 80px;
  }

  .tool-header {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .tool-icon {
    width: 40px;
    height: 40px;
    margin-right: 20px;
    vertical-align: middle;
    filter: var(--icon-filter-node-current);

  }
</style>
