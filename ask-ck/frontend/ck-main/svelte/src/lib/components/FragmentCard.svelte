<script>
  /** @type {{ name: string, source: string, steps: number, description?: string, redundantReason?: string, codeLines: number, code: string }} */
  export let fragment;

  /** @type {boolean} Recommended (green) vs redundant alternative (red, nested) */
  export let recommended = true;

  /** @type {boolean} Whether this fragment is currently ticked for inclusion in Generate */
  export let selected = false;

  /** @type {boolean} Whether the code preview is expanded */
  export let expanded = false;

  /** @type {() => void} */
  export let onToggleSelected = () => {};

  /** @type {() => void} */
  export let onToggleExpanded = () => {};
</script>

<!-- Card color follows the live selection state (green once ticked, red once unticked) — the
     `recommended` grouping/wording below stays fixed to the LLM's original reasoning. -->
<div class="fragment-card" class:fragment-recommended={selected} class:fragment-redundant={!selected}>
  <label class="fragment-card-header">
    <input type="checkbox" checked={selected} on:change={onToggleSelected} />
    <span class="fragment-name">{fragment.name}</span>
    <span class="fragment-source">from {fragment.source} · steps {fragment.steps}</span>
  </label>

  {#if recommended}
    <p class="fragment-description">{fragment.description}</p>
  {:else}
    <p class="fragment-redundant-reason"><strong>redundant:</strong> {fragment.redundantReason}</p>
  {/if}

  <button type="button" class="fragment-code-toggle" on:click={onToggleExpanded}>
    <span class="fragment-code-caret" class:expanded>▸</span>
    code ({fragment.codeLines} lines)
  </button>

  {#if expanded}
    <pre class="fragment-code-block">{fragment.code}</pre>
  {/if}
</div>

<style>
  .fragment-card {
    border: 1px solid var(--color-border-surface);
    border-radius: 10px;
    padding: 12px 16px;
    transition: border-color 0.15s ease, background-color 0.15s ease;
  }

  .fragment-recommended {
    border-color: var(--color-success);
    background: color-mix(in srgb, var(--color-success) 6%, var(--color-bg-surface));
  }

  .fragment-redundant {
    border-color: var(--color-error);
    background: color-mix(in srgb, var(--color-error) 5%, var(--color-bg-surface));
  }

  .fragment-card-header {
    display: flex;
    align-items: center;
    gap: 10px;
    cursor: pointer;
  }

  .fragment-card-header input[type='checkbox'] {
    width: 16px;
    height: 16px;
    accent-color: var(--color-success);
  }

  .fragment-redundant .fragment-card-header input[type='checkbox'] {
    accent-color: var(--color-error);
  }

  .fragment-name {
    font-weight: 700;
    color: var(--color-text);
  }

  .fragment-source {
    font-size: 0.8rem;
    font-style: italic;
    color: var(--color-text-muted);
  }

  .fragment-description,
  .fragment-redundant-reason {
    margin: 6px 0 8px 26px;
    font-size: 0.88rem;
    color: var(--color-text);
  }

  .fragment-redundant-reason strong {
    font-style: italic;
  }

  .fragment-code-toggle {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-left: 26px;
    padding: 0;
    border: none;
    background: none;
    color: var(--color-accent);
    font: inherit;
    font-size: 0.82rem;
    cursor: pointer;
  }

  .fragment-code-caret {
    display: inline-block;
    font-size: 0.7rem;
    transition: transform 0.15s ease;
  }

  .fragment-code-caret.expanded {
    transform: rotate(90deg);
  }

  .fragment-code-block {
    margin: 8px 0 0 26px;
    padding: 10px 12px;
    border-radius: 8px;
    background: var(--color-code-bg);
    font-family: 'SFMono-Regular', Consolas, monospace;
    font-size: 0.8rem;
    overflow-x: auto;
    white-space: pre;
  }
</style>
