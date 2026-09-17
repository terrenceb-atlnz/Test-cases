<script>
  export let variant = 'primary'; // 'primary' | 'outline'
  export let type = 'button';
  export let disabled = false;

  let className = '';
  export { className as class };
</script>

<button
  {type}
  class="btn btn-{variant} {className}"
  {disabled}
  on:click
>
  <slot />
</button>

<style>
  .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 6px 16px;
    border-radius: 999px;
    font: inherit;
    font-weight: 600;
    font-size: 0.85rem;
    cursor: pointer;
    transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease, filter 0.2s ease;
  }

  .btn:disabled {
    cursor: not-allowed;
    opacity: 0.6;
  }

  .btn-primary {
    border: none;
    background: var(--color-accent);
    color: #fff;
  }

  .btn-primary:hover:not(:disabled) {
    filter: brightness(1.1);
  }

  .btn-outline {
    border: 1px solid var(--color-accent);
    background: transparent;
    color: var(--color-accent);
  }

  .btn-outline:hover:not(:disabled) {
    background: color-mix(in srgb, var(--color-accent) 10%, transparent);
  }
</style>
