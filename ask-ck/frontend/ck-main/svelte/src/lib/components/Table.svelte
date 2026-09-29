<script>
// @ts-nocheck

  /** @type {Array<{ key: string, label: string, width?: number, pillClass?: (value: any) => string }>} */
  export let columns = [];

  /** @type {Array<Record<string, any> & { id: string | number }>} */
  export let rows = [];

  /** @type {boolean} Show a checkbox column and make rows selectable */
  export let selectable = true;

  /** @type {Array<string | number>} Bindable list of selected row ids */
  export let selected = [];

  function toggleRow(id) {
    selected = selected.includes(id) ? selected.filter((s) => s !== id) : [...selected, id];
  }

  function handleRowKeydown(event, id) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      toggleRow(id);
    }
  }
</script>

<div class="data-table">
  <div class="data-table-row data-table-header">
    {#if selectable}
      <div class="data-table-cell data-table-checkbox-cell"></div>
    {/if}
    {#each columns as col}
      <div class="data-table-cell data-table-header-cell" style="flex: {col.width ?? 1}">
        {col.label}
      </div>
    {/each}
  </div>

  {#if rows.length === 0}
    <div class="data-table-row data-table-empty-row"></div>
  {:else}
    {#each rows as row (row.id)}
      <div
        class="data-table-row data-table-row-body"
        role="button"
        tabindex="0"
        on:click={() => toggleRow(row.id)}
        on:keydown={(e) => handleRowKeydown(e, row.id)}
      >
        {#if selectable}
          <div class="data-table-cell data-table-checkbox-cell">
            <input
              type="checkbox"
              checked={selected.includes(row.id)}
              on:click|stopPropagation
              on:change={() => toggleRow(row.id)}
              aria-label="Select row"
            />
          </div>
        {/if}
        {#each columns as col}
          <div class="data-table-cell" style="flex: {col.width ?? 1}">
            {#if col.pillClass}
              <span class="pill {col.pillClass(row[col.key])}">{row[col.key] ?? ''}</span>
            {:else}
              {row[col.key] ?? ''}
            {/if}
          </div>
        {/each}
      </div>
    {/each}
  {/if}
</div>

<style>
  .data-table {
    width: 100%;
    max-height: 600px;
    border: 1px solid var(--color-border-surface);
    border-radius: 10px;
    background: var(--color-table-header-bg);
    overflow: scroll;
  }

  .data-table-row {
    display: flex;
    align-items: center;
    padding: 10px 40px;
    height: 100%;
    /* border-bottom: 1px solid var(--color-border-surface); */
  }

  .data-table-row:last-child {
    border-bottom: none;
  }

  .data-table-row-body {
    cursor: pointer;
    transition: background-color 0.15s ease;
  }

  .data-table-row-body:hover {
    background: color-mix(in srgb, var(--color-accent) 8%, transparent);
  }

  .data-table-header {
    background: var(--color-table-header-bg);
    border-bottom: 2px solid var(--color-border-surface);
    position: sticky;
    top: 0;
    z-index: 1;
  }

  .data-table-header-cell {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--color-text);
  }

  .data-table-cell {
    flex: 1;
    min-width: 0;
    font-size: 0.8rem;
    color: var(--color-text-muted);
    /* white-space: nowrap; */
    overflow: hidden;
    text-overflow: ellipsis;
    margin-right: 24px;
  }

  .data-table-checkbox-cell {
    flex: 0 0 auto;
    width: 20px;
    padding-right: 32px;
    margin-right: 16px;
  }

  .data-table-checkbox-cell input {
    accent-color: var(--color-accent);
    width: 16px;
    height: 16px;
    cursor: pointer;
    display: block;
  }

  .data-table-row.data-table-empty-row {
    height: 40px;
  }

  .pill {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 600;
  }

  .pill-success {
    background: color-mix(in srgb, var(--color-success) 18%, transparent);
    color: var(--color-success);
  }

  .pill-muted {
    background: color-mix(in srgb, var(--color-text-muted) 18%, transparent);
    color: var(--color-text-muted);
  }
</style>
