<script>
  export let variant = 'primary'; // 'primary' | 'outline' | 'success'
  export let type = 'button';
  export let disabled = false;

  /** @type {boolean} Show the sparkles icon — use for buttons that trigger an LLM call */
  export let sparkle = false;

  let className = '';
  export { className as class };
</script>

<button
  {type}
  class="btn btn-{variant} {className}"
  {disabled}
  on:click
>
  {#if sparkle}
    <!-- Inlined from assets/icons/sparkles.svg with stroke swapped to currentColor — a dynamic
         url(...) in an inline style/mask silently renders as style="" in this Svelte setup, so
         recoloring per-variant only works via an inlined SVG, not an <img> or CSS mask. -->
    <svg
      class="btn-sparkle-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      <path d="M11.017 2.814a1 1 0 0 1 1.966 0l1.051 5.558a2 2 0 0 0 1.594 1.594l5.558 1.051a1 1 0 0 1 0 1.966l-5.558 1.051a2 2 0 0 0-1.594 1.594l-1.051 5.558a1 1 0 0 1-1.966 0l-1.051-5.558a2 2 0 0 0-1.594-1.594l-5.558-1.051a1 1 0 0 1 0-1.966l5.558-1.051a2 2 0 0 0 1.594-1.594z" />
      <path d="M20 2v4" />
      <path d="M22 4h-4" />
      <circle cx="4" cy="20" r="2" />
    </svg>
  {/if}
  <slot />
</button>

<style>
  .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 6px 16px;
    border-radius: 10px;
    font: inherit;
    font-weight: 600;
    font-size: 0.85rem;
    cursor: pointer;
    transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease, filter 0.2s ease;
  }

  .btn-sparkle-icon {
    width: 15px;
    height: 15px;
    flex-shrink: 0;
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
    color: var(--color-text);
  }

  .btn-outline:hover:not(:disabled) {
    background: color-mix(in srgb, var(--color-accent) 10%, transparent);
  }

  .btn-success {
    border: none;
    background: var(--color-success);
    color: #fff;
  }

  .btn-success:hover:not(:disabled) {
    filter: brightness(1.1);
  }
</style>
