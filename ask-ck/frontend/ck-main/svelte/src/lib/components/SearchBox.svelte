<script>
  import Button from './Button.svelte';

  /** @type {string} Bindable search text */
  export let value = '';

  /** @type {string} */
  export let placeholder = 'Search…';

  /** @type {string} Label for the search button */
  export let buttonLabel = 'Search';

  /** @type {(() => void) | null} */
  export let onSearch = null;

  function handleSubmit() {
    onSearch && onSearch();
  }
</script>

<form class="search-box" on:submit|preventDefault={handleSubmit}>
  <input
    type="text"
    class="search-box-input"
    {placeholder}
    bind:value
  />
  <Button type="submit" variant="outline">{buttonLabel}</Button>
</form>

<style>
  .search-box {
    display: flex;
    flex: 1;
    gap: 12px;
    align-items: center;
    max-width: 400px;
  }

  .search-box-input {
    flex: 1;
    padding: 8px 12px;
    border-radius: 8px;
    border: 1px solid var(--color-border-surface);
    background: var(--color-bg-surface);
    color: var(--color-text);
    font: inherit;
    font-size: 0.94rem;
  }
</style>
