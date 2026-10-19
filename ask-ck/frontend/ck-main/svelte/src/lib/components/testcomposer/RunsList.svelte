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
