<script>
  import Button from './Button.svelte';
  import chevronDownIcon from '../../assets/icons/chevron-down.svg';

  /** @type {Array<{ id: string, label: string }>} */
  export let openPartialCases = [];

  /** @type {Array<{ id: string, label: string }>} */
  export let completeCases = [];

  /** @type {Array<{ label: string, cases: Array<{ id: string, label: string }> }>} Optional —
      when non-empty, renders as <optgroup>s (folder-based categories) instead of the flat
      openPartialCases/completeCases lists. GeneratorPage.svelte passes both the flat lists
      AND groups (progressHint below reads the flat list's {status, progress} even in grouped
      mode); PyTestPage.svelte's /pt_cases is grouped-only, so it passes groups alone and
      leaves the flat arrays at their [] default — the displayed counts below account for
      that (see openCount/completeCount). */
  export let openPartialGroups = [];

  /** @type {Array<{ label: string, cases: Array<{ id: string, label: string }> }>} */
  export let completeGroups = [];

  /** @type {((caseId: string) => void) | null} */
  export let onLoad = null;

  /** @type {(() => void) | null} */
  export let onExport = null;

  /** @type {string | null} The currently loaded case's id, if any — GeneratorPage.svelte
      destroys and recreates this component on every step switch (it's one branch of an
      {#if}/{:else if} chain), so without this a case selected earlier reverts to blank the
      moment you step back to Cases. Only used to seed the initial selection below; the two
      selects are otherwise plain local state once mounted. */
  export let selectedCaseId = null;

  let selectedOpenCase = openPartialCases.some((c) => c.id === selectedCaseId) ? selectedCaseId : '';
  let selectedCompleteCase = completeCases.some((c) => c.id === selectedCaseId) ? selectedCaseId : '';

  $: canLoad = !!(selectedOpenCase || selectedCompleteCase);

  // The displayed count must reflect whichever mode is actually rendering — grouped or
  // flat — not just the flat array, which a grouped-only caller (PyTestPage.svelte) never
  // populates at all.
  $: openCount = openPartialGroups.length
    ? openPartialGroups.reduce((n, g) => n + g.cases.length, 0)
    : openPartialCases.length;
  $: completeCount = completeGroups.length
    ? completeGroups.reduce((n, g) => n + g.cases.length, 0)
    : completeCases.length;

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

  // MODIFIED FROM current/generator/generator.js's get_cases progress-hint logic TO WORK
  // WITH SVELTE (same three hints, just returned as a string suffix instead of built into
  // a server-rendered <option> label).
  function progressHint(c) {
    const p = c.progress;
    if (!p) return '';
    if (p.has_step4 && p.confirms) return ' [synth done]';
    if (p.has_step4) return ' [has draft]';
    if (p.confirms) return ` [${p.confirms}/3 steps]`;
    return '';
  }
</script>

<div class="cases-step">
  <p class="cases-intro">Select a test case to work on, then Load it. Export or clear its session from here too.</p>

  <div class="case-picker">
    <label class="case-picker-label" for="open-partial-select">Open / Partial ({openCount})</label>
    <div class="case-select-wrapper">
      <select
        id="open-partial-select"
        class="case-select"
        bind:value={selectedOpenCase}
        on:change={handleOpenChange}
      >
        <option value="">Select a case…</option>
        {#if openPartialGroups.length}
          {#each openPartialGroups as g}
            <optgroup label={g.label}>
              {#each g.cases as c}
                <option value={c.id}>{c.label}{progressHint(c)}</option>
              {/each}
            </optgroup>
          {/each}
        {:else}
          {#each openPartialCases as c}
            <option value={c.id}>{c.label}{progressHint(c)}</option>
          {/each}
        {/if}
      </select>
      <img class="case-select-chevron" src={chevronDownIcon} alt="" aria-hidden="true" />
    </div>
  </div>

  <div class="case-picker">
    <label class="case-picker-label" for="complete-select">Complete ({completeCount})</label>
    <div class="case-select-wrapper">
      <select
        id="complete-select"
        class="case-select"
        bind:value={selectedCompleteCase}
        on:change={handleCompleteChange}
      >
        <option value="">Select a case…</option>
        {#if completeGroups.length}
          {#each completeGroups as g}
            <optgroup label={g.label}>
              {#each g.cases as c}
                <option value={c.id}>{c.label}</option>
              {/each}
            </optgroup>
          {/each}
        {:else}
          {#each completeCases as c}
            <option value={c.id}>{c.label}</option>
          {/each}
        {/if}
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
