<script>
  import Button from './Button.svelte';
  import squarePenIcon from '../../assets/icons/square-pen.svg';
  import trashIcon from '../../assets/icons/trash.svg';

  /** @type {Array<{ id: string | number, from: string | number, action: string, verify: string }>} Bindable list of sequenced rows */
  export let rows = [];

  /** @type {string} */
  export let emptyMessage = 'No sequenced steps yet.';

  /**
     * @type {string | null}
     */
  let editingRowId = null;
  /**
     * @type {number | null}
     */
  let draggedIndex = null;
  /**
     * @type {{ index: any; position: any; } | null}
     */
  let dropIndicator = null; // { index, position: 'above' | 'below' }

  function toggleEditRow(id) {
    editingRowId = editingRowId === id ? null : id;
  }

  function saveRow() {
    editingRowId = null;
  }

  function removeRow(id) {
    rows = rows.filter((r) => r.id !== id);
    if (editingRowId === id) editingRowId = null;
  }

  function addStep() {
    const newRow = { id: `seq-${Date.now()}`, from: '', action: '', verify: '' };
    rows = [...rows, newRow];
    editingRowId = newRow.id;
  }

  function handleDragStart(index) {
    draggedIndex = index;
  }

  function handleDragOver(event, index) {
    event.preventDefault();
    const rect = event.currentTarget.getBoundingClientRect();
    const isAfter = event.clientY - rect.top > rect.height / 2;
    dropIndicator = { index, position: isAfter ? 'below' : 'above' };
  }

  function handleDragLeave(index) {
    if (dropIndicator?.index === index) dropIndicator = null;
  }

  function handleDrop(index) {
    if (draggedIndex === null) {
      resetDrag();
      return;
    }
    const position = dropIndicator?.position ?? 'above';
    let desiredIndex = position === 'below' ? index + 1 : index;
    const updated = [...rows];
    const [moved] = updated.splice(draggedIndex, 1);
    if (desiredIndex > draggedIndex) desiredIndex -= 1;
    updated.splice(desiredIndex, 0, moved);
    rows = updated;
    resetDrag();
  }

  function resetDrag() {
    draggedIndex = null;
    dropIndicator = null;
  }
</script>

<div class="sequence-editor">
  <div class="sequence-editor-row sequence-editor-header">
    <div class="col-handle"></div>
    <div class="col-from">From</div>
    <div class="col-num">#</div>
    <div class="col-text">Action</div>
    <div class="col-text">Verify</div>
    <div class="col-row-actions"></div>
  </div>
  {#if rows.length === 0}
    <div class="sequence-editor-row sequence-editor-empty">
      <div class="col-text">{emptyMessage}</div>
    </div>
  {:else}
    {#each rows as row, i (row.id)}
      <div
        class="sequence-editor-row"
        class:sequence-editor-row-dragging={draggedIndex === i}
        class:sequence-editor-row-editing={editingRowId === row.id}
        class:drop-indicator-above={dropIndicator?.index === i && dropIndicator.position === 'above'}
        class:drop-indicator-below={dropIndicator?.index === i && dropIndicator.position === 'below'}
        role="listitem"
        draggable="true"
        on:dragstart={() => handleDragStart(i)}
        on:dragover={(event) => handleDragOver(event, i)}
        on:dragleave={() => handleDragLeave(i)}
        on:drop={() => handleDrop(i)}
        on:dragend={resetDrag}
      >
        <span class="col-handle drag-handle" aria-hidden="true">⠿</span>
        <div class="col-from">{row.from}</div>
        <div class="col-num">{i + 1}</div>
        {#if editingRowId === row.id}
          <input class="sequence-editor-input col-text" type="text" bind:value={row.action} />
          <input class="sequence-editor-input col-text" type="text" bind:value={row.verify} />
        {:else}
          <div class="col-text">{row.action}</div>
          <div class="col-text">{row.verify}</div>
        {/if}
        <div class="col-row-actions">
          {#if editingRowId === row.id}
            <Button
              variant="primary"
              class="sequence-save-btn"
              disabled={!row.action.trim() || !row.verify.trim()}
              on:click={saveRow}
            >Save Changes</Button>
          {:else}
            <button
              type="button"
              class="row-icon-btn"
              on:click={() => toggleEditRow(row.id)}
              aria-label="Edit step"
            >
              <img class="row-icon" src={squarePenIcon} alt="" aria-hidden="true" />
            </button>
            <button
              type="button"
              class="row-icon-btn row-icon-btn-danger"
              on:click={() => removeRow(row.id)}
              aria-label="Remove step"
            >
              <img class="row-icon" src={trashIcon} alt="" aria-hidden="true" />
            </button>
          {/if}
        </div>
      </div>
    {/each}
  {/if}
</div>

<div class="sequence-table-actions">
  <Button variant="outline" on:click={addStep}>+ Add Step</Button>
</div>

<style>
  .sequence-editor {
    width: 100%;
    border: 1px solid var(--color-border-surface);
    border-radius: 10px;
    overflow: hidden;
    background: var(--color-table-header-bg);
  }

  .sequence-editor-row {
    position: relative;
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 16px;
  }

  .sequence-editor-row:hover {
    background: color-mix(in srgb, var(--color-accent) 8%, transparent);
  }

  .sequence-editor-row:not(.sequence-editor-header):not(:last-child) {
    border-bottom: 0px solid var(--color-border-surface);
  }

  .drop-indicator-above::before,
  .drop-indicator-below::after {
    content: '';
    position: absolute;
    left: 0;
    right: 0;
    height: 3px;
    background: var(--color-accent);
    border-radius: 2px;
    pointer-events: none;
    z-index: 1;
  }

  .drop-indicator-above::before {
    top: -2px;
  }

  .drop-indicator-below::after {
    bottom: -2px;
  }

  .sequence-editor-header {
    background: var(--color-table-header-bg);
    border-bottom: 2px solid var(--color-border-surface);
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--color-text);
  }

  .sequence-editor-header:hover {
    background: var(--color-table-header-bg);
  }

  .col-handle {
    flex: 0 0 18px;
  }

  .drag-handle {
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--color-text-muted);
    cursor: grab;
    font-size: 1rem;
    line-height: 1;
    user-select: none;
  }

  .sequence-editor-row-dragging {
    opacity: 0.5;
  }

  .col-from {
    flex: 0 0 70px;
    font-size: 0.8rem;
    color: var(--color-text-muted);
  }

  .col-num {
    flex: 0 0 60px;
    font-size: 0.8rem;

    color: var(--color-text-muted);
  }

  .col-text {
    flex: 1;
    min-width: 0;
    font-size: 0.8rem;
    color: var(--color-text-muted);
  }

  .sequence-editor-empty {
    color: var(--color-text-muted);
    font-size: 0.85rem;
  }

  .col-row-actions {
    flex: 0 0 130px;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 4px;
    opacity: 0;
    transition: opacity 0.15s ease;
  }

  .sequence-editor-row:hover .col-row-actions,
  .sequence-editor-row-editing .col-row-actions {
    opacity: 1;
  }

  .sequence-editor-input {
    padding: 8px 10px;
    border-radius: 6px;
    border: 1px solid var(--color-border-surface);
    background: var(--color-bg-surface);
    color: var(--color-text);
    font: inherit;
    font-size: 0.85rem;
    min-width: 0;
  }

  .row-icon-btn {
    width: 28px;
    height: 28px;
    border-radius: 6px;
    border: none;
    background: transparent;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    transition: background-color 0.15s ease;
  }

  .row-icon-btn:hover {
    background: color-mix(in srgb, var(--color-accent) 10%, transparent);
  }

  .row-icon-btn-danger:hover {
    background: color-mix(in srgb, var(--color-error) 12%, transparent);
  }

  .row-icon {
    width: 16px;
    height: 16px;
    filter: brightness(0) var(--icon-filter-muted);
  }

  :global(.sequence-save-btn) {
    padding: 4px 12px;
    font-size: 0.78rem;
    white-space: nowrap;
  }

  .sequence-table-actions {
    display: flex;
    margin-top: 16px;
  }
</style>
