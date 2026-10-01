<script>
// @ts-nocheck

  export let variant = 'primary'; // 'primary' | 'outline' | 'success'
  export let type = 'button';
  export let disabled = false;
  export let title = '';

  /** @type {boolean} Mid-call (e.g. an LLM response is pending) — disables the button and adds
      the `btn-loading` class as a hook for a loading animation. Design the animation via that
      class; this prop only wires the state up. */
  export let loading = false;

  /** @type {boolean} Same `btn-loading` animation as `loading`, but WITHOUT disabling the
      button — use when the button's click must still work while busy (e.g. a cancelable LLM
      call, where clicking again means Stop instead of being swallowed). */
  export let busy = false;

  /** @type {boolean} Show the sparkles icon — use for buttons that trigger an LLM call */
  export let sparkle = false;

  /** @type {boolean} Show the copy icon — use for buttons that copy text to the clipboard */
  export let copy = false;

  let className = '';
  export { className as class };
</script>

<button
  {type}
  {title}
  class="btn btn-{variant} {className}"
  class:btn-loading={loading || busy}
  disabled={disabled || loading}
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
  {#if copy}
    <!-- Inlined from assets/icons/copy.svg with stroke swapped to currentColor — see the sparkle
         icon above for why this can't be a plain <img> or CSS mask. -->
    <svg
      class="btn-copy-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      <rect width="14" height="14" x="8" y="8" rx="2" ry="2" />
      <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />
    </svg>
  {/if}
  <slot />
</button>

<style>
  /* Loading-border trace: adapted from CodeFronts' "Pure CSS Animated Border Trace Button"
     (MIT licensed) — https://codefronts.com/components/css-glowing-border-buttons/pure-css-animated-border-trace-button/
     A conic-gradient comet wedge is clipped to a thin ring via mask-composite:exclude and spun
     by animating its angle through @property, so the beam hugs the button's own border-radius.
     Swapped their :hover/:focus-visible trigger for the `.btn-loading` class instead. */
  @property --btn-spin-angle {
    syntax: '<angle>';
    inherits: false;
    initial-value: 0deg;
  }

  /* Split out from `.btn` as a zero-specificity rule so a page that needs to force its own
     `position` on a Button (e.g. absolutely placing it within a relative card) can still do so
     with a plain single-class selector — without this, Svelte's scoping quietly makes `.btn`'s
     own `position: relative` win the cascade over such an override. */
  :where(.btn) {
    position: relative;
  }

  .btn {
    --btn-beam: #E20052;
    isolation: isolate;
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

  .btn::before,
  .btn::after {
    content: '';
    position: absolute;
    inset: -1px;
    border-radius: inherit;
    padding: 2px;
    background: conic-gradient(from var(--btn-spin-angle), transparent 0 82%, color-mix(in oklab, var(--btn-beam) 45%, transparent) 88%, var(--btn-beam) 93%, transparent 97%);
    -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
    mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
    -webkit-mask-composite: xor;
    mask-composite: exclude;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.3s ease;
  }

  .btn::after {
    filter: blur(8px);
    inset: -3px;
    padding: 4px;
  }

  .btn-loading::before,
  .btn-loading::after {
    opacity: 1;
    animation: btn-loading-lap 1.4s linear infinite;
  }

  @keyframes btn-loading-lap {
    to {
      --btn-spin-angle: 360deg;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .btn-loading::before,
    .btn-loading::after {
      animation: none;
      opacity: 0.6;
    }
  }

  .btn-sparkle-icon,
  .btn-copy-icon {
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
