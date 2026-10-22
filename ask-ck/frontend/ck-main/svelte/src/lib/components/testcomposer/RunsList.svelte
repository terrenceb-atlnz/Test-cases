<script>

  //@ts-nocheck
  // Earlier runs of one kind, newest first; picking one reopens its window and table.
  import { fmtTokens } from './testComposerModel.js';

  let { server, kind, onopen, refreshKey = 0 } = $props();
  let runs = $state([]);
  let error = $state(null);

  async function load() {
    try { runs = (await server(`/runs?kind=${encodeURIComponent(kind)}&limit=25`)).runs; error = null; }
    catch (e) { error = e.message; }
  }

  $effect(() => { refreshKey; load(); });
</script>

<div class="tc-runs">
  {#if error}<div class="tc-problem">{error}</div>{/if}
  {#if !runs.length}<div class="tc-small">No runs yet.</div>{/if}
  {#each runs as r (r.run_id)}
    <button type="button" class="tc-run-row" onclick={() => onopen(r.run_id)}>
      <span class="tc-key">{r.run_id}</span>
      <span class="tc-badge tc-state-{r.state}">{r.state}</span>
      <span class="tc-small">{r.testbox} · {(r.cases || []).join(', ') || 'no cases'}</span>
      <span class="tc-small">{Object.entries(r.counts || {}).map(([k, v]) => `${v} ${k}`).join(', ')}</span>
      <span class="tc-small">{r.tokens ? `${fmtTokens(r.tokens)} tokens` : ''}</span>
    </button>
  {/each}
</div>

<style>
  .tc-runs {
    width: 100%;
    max-height: 260px;
    overflow: auto;
    border: 1px solid var(--color-border-surface);
    border-radius: 10px;
    background: var(--color-bg-surface);
  }

  .tc-run-row {
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 4px 12px;
    width: 100%;
    padding: 8px 12px;
    border: 0;
    border-bottom: 1px solid var(--color-border-surface);
    background: none;
    color: var(--color-text);
    font: inherit;
    font-size: 0.9rem;
    text-align: left;
    cursor: pointer;
  }

  .tc-run-row:last-child {
    border-bottom: 0;
  }

  .tc-run-row:hover {
    background: color-mix(in srgb, var(--color-accent) 6%, transparent);
  }

  .tc-run-row:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: -2px;
  }

  .tc-key {
    font-family: 'Roboto Mono Variable', 'Roboto Mono', monospace;
    font-size: 0.8rem;
    color: var(--color-analysis-key);
  }

  .tc-small {
    color: var(--color-text-muted);
    font-size: 0.85rem;
  }

  .tc-runs > .tc-small,
  .tc-problem {
    padding: 8px 12px;
  }

  .tc-problem {
    color: var(--color-error);
  }

  .tc-badge {
    padding: 1px 8px;
    border: 1px solid var(--color-border-surface);
    border-radius: 10px;
    color: var(--color-text-muted);
    font-size: 0.75rem;
    white-space: nowrap;
  }

  .tc-state-starting,
  .tc-state-running {
    color: var(--color-accent);
    border-color: currentColor;
  }

  .tc-state-done {
    color: var(--color-success);
    border-color: currentColor;
  }

  .tc-state-error,
  .tc-state-stopped {
    color: var(--color-error);
    border-color: currentColor;
  }
</style>
