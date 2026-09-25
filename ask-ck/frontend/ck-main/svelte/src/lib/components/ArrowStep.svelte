<script>
  /** @type {'none' | 'review' | 'covered'} */
  export let status = 'none';

  /** @type {boolean} */
  export let active = false;

  /** @type {string | number} */
  export let label = '';

  /** @type {(() => void) | null} */
  export let onClick = null;

  /** @type {boolean} Extend the arrow's straight body (not a uniform stretch) for longer labels */
  export let wide = false;

  const normalPath = `M31.697,15.287
    c-0.011-0.011-6.947-6.993-6.947-6.993c-0.203-0.203-0.47-0.298-0.735-0.291c-0.008,0-0.015-0.005-0.023-0.005h-23
    c-0.88,0-1.32,1.109-0.705,1.727l6.242,6.295l-6.169,6.222C-0.305,22.859-0.009,24,1.203,23.998h22.78
    c0.278,0.018,0.561-0.07,0.774-0.284l6.94-6.999C32.09,16.321,32.09,15.681,31.697,15.287z`;

  // Same tip/notch curves as normalPath — only the two straight body lines (h-23/h22.78) are
  // extended (to h-53/h52.78), with the notch's absolute anchor shifted to match, so the shape
  // widens without stretching the angled ends.
  const widePath = `M31.697,15.287
    c-0.011-0.011-6.947-6.993-6.947-6.993c-0.203-0.203-0.47-0.298-0.735-0.291c-0.008,0-0.015-0.005-0.023-0.005h-53
    c-0.88,0-1.32,1.109-0.705,1.727l6.242,6.295l-6.169,6.222C-30.305,22.859-30.009,24,-28.797,23.998h52.78
    c0.278,0.018,0.561-0.07,0.774-0.284l6.94-6.999C32.09,16.321,32.09,15.681,31.697,15.287z`;

  $: arrowPath = wide ? widePath : normalPath;
  $: arrowViewBox = wide ? '-30 8 62 16' : '0 8 32 16';

  // The active step is hollow (no fill) but its border color is the same status-border token
  // used when inactive — selecting a step must never shift the border to a different shade.
  $: fillValue = active ? 'none' : 'currentColor';

  $: borderColorVar =
    status === 'covered'
      ? 'var(--color-arrow-step-complete-border)'
      : status === 'review'
      ? 'var(--color-arrow-step-review-border)'
      : 'var(--color-arrow-step-border)';
</script>

<button
  type="button"
  class="arrow-step"
  class:arrow-step-wide={wide}
  class:arrow-none={status === 'none'}
  class:arrow-review={status === 'review'}
  class:arrow-covered={status === 'covered'}
  class:arrow-step-active={active}
  aria-pressed={active}
  aria-label={`Sequence step ${label}`}
  on:click={() => onClick && onClick()}
>
  <svg class="arrow-shape" viewBox={arrowViewBox} aria-hidden="true" focusable="false">
    <path
      d={arrowPath}
      fill={fillValue}
      stroke={borderColorVar}
      stroke-width="1"
    />
  </svg>
  <span class="arrow-label">{label}</span>
</button>

<style>
  .arrow-step {
    position: relative;
    flex: 0 0 auto;
    width: 72px;
    height: 80px;
    padding: 0;
    border: none;
    background: none;
    cursor: pointer;
    color: var(--color-arrow-step-text);
    transition: color 0.15s ease, filter 0.15s ease;
  }

  .arrow-shape {
    position: absolute;
    inset: 0;
    width: 130%;
    height: 100%;
    display: block;
    overflow: visible;
  }

  .arrow-shape path {
    transition: fill 0.15s ease, stroke 0.15s ease;
  }

  .arrow-step-wide {
    width: 160px;
  }

  .arrow-step-wide .arrow-shape {
    /* Wider viewBox aspect ratio than the normal arrow (3.875:1 vs 2:1) means 100% width would
       letterbox to a visibly thinner shape; this percentage renders at the same visual
       thickness as the normal arrows (measured empirically, not just eyeballed). */
    width: 113.4%;
  }

  .arrow-step-wide .arrow-label {
    padding-left: 20px;
    padding-right: 20px;
    font-size: 1rem;
  }

  .arrow-step:hover {
    filter: var(--arrow-filter-hover);
  }

  /* The selected step's border is a deliberate status color — hovering it (which happens
     right after a click, since the cursor is still over the button) must not brighten/darken it. */
  .arrow-step-active:hover {
    filter: none;
  }

  .arrow-none {
    color: var(--color-arrow-step-bg);
  }

  .arrow-review {
    color: var(--color-arrow-step-review-bg);
  }

  .arrow-covered {
    color: var(--color-arrow-step-complete-bg);
  }

  .arrow-label {
    position: relative;
    z-index: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
    padding-right: 10px;
    padding-left: 30px;

    font-size: 1.1rem;
    font-style: italic;
    font-weight: 700;
    transition: color 0.15s ease;
  }

  .arrow-label:hover {
    color: var(--color-arrow-text-hover);
  }

  .arrow-none .arrow-label {
    color: var(--color-arrow-step-text);
  }

  .arrow-review .arrow-label {
    color: var(--color-arrow-step-review-text);
  }

  .arrow-covered .arrow-label {
    color: var(--color-arrow-step-complete-text);
  }

  /* The active step always shows the "active" palette, overriding its own status color. */
  /* .arrow-step-active {
    color: var(--color-arrow-step-active-bg);
  } */

  .arrow-step-active .arrow-label {
    color: var(--color-arrow-step-active-text);
  }
</style>
