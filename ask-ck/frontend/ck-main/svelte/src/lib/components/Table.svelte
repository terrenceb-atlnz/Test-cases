<script>
// @ts-nocheck

  /** @type {Array<{ key: string, label: string, width?: number }>} */
  export let columns = [];

  /** @type {Array<Record<string, any> & { id: string | number }>} */
  export let rows = [];

  /** @type {boolean} Show a checkbox column and make rows selectable */
  export let selectable = true;

  /** @type {Array<string | number>} Bindable list of selected row ids */
  export let selected = [];

  /** @type {Array<string | number>} Row ids to briefly flash (e.g. just moved into this table) */
  export let flashIds = [];

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
        class:data-table-row-flash={flashIds.includes(row.id)}
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
            {row[col.key] ?? ''}
          </div>
        {/each}
      </div>
    {/each}
  {/if}
</div>

<style>
  .data-table {
    width: 100%;
    border: 1px solid var(--color-border-surface);
    border-radius: 10px;
    background: var(--color-table-header-bg);
    overflow: hidden;
  }

  .data-table-row {
    display: flex;
    align-items: center;
    padding: 10px 40px;
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

  .data-table-row-flash {
    animation: data-table-row-flash-kf 900ms ease-out;
  }

  @keyframes data-table-row-flash-kf {
    0% {
      background: color-mix(in srgb, var(--color-accent) 55%, transparent);
      filter: brightness(1.6);
    }
    100% {
      background: transparent;
      filter: brightness(1);
    }
  }

  .data-table-header {
    background: var(--color-table-header-bg);
    border-bottom: 2px solid var(--color-border-surface);

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
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
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
</style>
