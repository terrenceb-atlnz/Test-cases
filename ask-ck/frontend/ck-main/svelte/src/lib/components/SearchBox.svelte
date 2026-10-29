<script>
  //@ts-nocheck

  import Button from "./Button.svelte";

  export let value = "";

  export let placeholder = "Search…";

  export let buttonLabel = "Search";

  export let onSearch = null;

  function handleSubmit() {
    onSearch && onSearch();
  }
</script>

<form class="search-box" on:submit|preventDefault={handleSubmit}>
  <input type="text" class="search-box-input" {placeholder} bind:value />
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
