<script>
  import Button from './Button.svelte';
  import chevronDownIcon from '../../assets/icons/chevron-down.svg';

  /** @type {Array<{ id: string, label: string }>} */
  export let openPartialCases = [];

  /** @type {Array<{ id: string, label: string }>} */
  export let completeCases = [];

  /** @type {((caseId: string) => void) | null} */
  export let onLoad = null;

  /** @type {(() => void) | null} */
  export let onExport = null;

  let selectedOpenCase = '';
  let selectedCompleteCase = '';

  $: canLoad = !!(selectedOpenCase || selectedCompleteCase);

  function handleOpenChange() {
    if (selectedOpenCase) selectedCompleteCase = '';
  }

  function handleCompleteChange() {
    if (selectedCompleteCase) selectedOpenCase = '';
  }

  function handleLoad() {
    const caseId = selectedOpenCase || selectedCompleteCase;
    onLoad && onLoad(caseId);
  }

  function handleExport() {
    onExport && onExport();
  }
</script>

<div class="cases-step">
  <p class="cases-intro">Select a test case to work on, then Load it. Export or clear its session from here too.</p>

  <div class="case-picker">
    <label class="case-picker-label" for="open-partial-select">Open / Partial (0)</label>
    <div class="case-select-wrapper">
      <select
        id="open-partial-select"
        class="case-select"
        bind:value={selectedOpenCase}
        on:change={handleOpenChange}
      >
        <option value="">Select a case…</option>
        {#each openPartialCases as c}
          <option value={c.id}>{c.label}</option>
        {/each}
      </select>
      <img class="case-select-chevron" src={chevronDownIcon} alt="" aria-hidden="true" />
    </div>
  </div>

  <div class="case-picker">
    <label class="case-picker-label" for="complete-select">Complete (0)</label>
    <div class="case-select-wrapper">
      <select
        id="complete-select"
        class="case-select"
        bind:value={selectedCompleteCase}
        on:change={handleCompleteChange}
      >
        <option value="">Select a case…</option>
        {#each completeCases as c}
          <option value={c.id}>{c.label}</option>
        {/each}
      </select>
      <img class="case-select-chevron" src={chevronDownIcon} alt="" aria-hidden="true" />
    </div>
  </div>

  <div class="cases-actions">
    <Button variant="primary" disabled={!canLoad} on:click={handleLoad}>Load &amp; Confirm</Button>
    <Button variant="outline" on:click={handleExport}>Export</Button>
  </div>
</div>

<style>
  .cases-step {
    max-width: 640px;
  }

  .cases-intro {
    margin: 0 0 24px;
    color: var(--color-text-muted);
    font-size: 0.94rem;
  }

  .case-picker {
    margin-bottom: 20px;
  }

  .case-picker-label {
    display: block;
    margin-bottom: 8px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--color-text-muted);
  }

  .case-select-wrapper {
    position: relative;
  }

  .case-select-chevron {
    position: absolute;
    top: 50%;
    right: 14px;
    width: 16px;
    height: 16px;
    transform: translateY(-50%);
    filter: var(--icon-filter-muted);
    pointer-events: none;
  }

  .case-select {
    width: 100%;
    padding: 10px 40px 10px 12px;
    border-radius: 8px;
    border: 1px solid var(--color-border-surface);
    background: var(--color-bg-surface);
    color: var(--color-text);
    font: inherit;
    font-size: 0.94rem;
    appearance: none;
    -webkit-appearance: none;
    -moz-appearance: none;
  }

  .cases-actions {
    display: flex;
    gap: 12px;
    margin-top: 8px;
  }
</style>
