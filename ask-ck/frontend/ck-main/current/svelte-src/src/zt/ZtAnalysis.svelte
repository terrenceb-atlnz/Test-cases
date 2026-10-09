<script>
  // The read-only Results Analysis column (was renderAnalysis): Q1–Q4, 5. Gaps, 6. AI Notes, then
  // what went wrong — failed calls and refused proposals are shown, never hidden.
  import { analysisView } from './model.js';

  let { job, tree } = $props();
  const v = $derived(analysisView(job, tree));
</script>

{#if !v}
  <div class="zt-empty">Paste a project page URL and press Organize with LLM.</div>
{:else}
  <div class="zt-state zt-state-{v.state}">{v.stateText}</div>
  {#if v.error}<div class="zt-problem">{v.error}</div>{/if}
  {#if v.sources}
    <div class="zt-block"><div class="zt-h">Sources</div>
      <ul>{#each v.sources as s}<li>{s.label}: <a href={s.url} target="_blank" rel="noopener">{s.title}</a>{s.exists ? '' : ' (not created)'}</li>{/each}</ul>
      <div class="zt-small">Feature Page: {v.featurePage}.{v.tpsRows}</div>
    </div>
  {/if}
  {#each v.questions as q}
    <div class="zt-block"><div class="zt-h">{q.title} <span class="zt-count">{q.items.length}</span></div>
      {#if q.items.length}
        <ul>{#each q.items as d}<li><span class="zt-key">{d.key}</span> {d.name} — {d.reason} <span class="zt-source">({d.source})</span></li>{/each}</ul>
      {:else}<div class="zt-small">{v.isDone ? 'None.' : '…'}</div>{/if}
    </div>
  {/each}
  <div class="zt-block"><div class="zt-h">5. Gaps — required, no template <span class="zt-count">{v.gaps.items.length}</span></div>
    {#if v.gaps.state === 'error'}<div class="zt-problem">{v.gaps.error}</div>{/if}
    {#if v.gaps.items.length}
      <ul>{#each v.gaps.items as x}<li>{x.requirement} <span class="zt-source">({x.source})</span>{x.why ? ' — ' + x.why : ''}</li>{/each}</ul>
    {:else}<div class="zt-small">{v.gaps.state === 'done' ? 'None found.' : v.gaps.state === 'error' ? '' : '…'}</div>{/if}
  </div>
  <div class="zt-block"><div class="zt-h">6. AI Notes <span class="zt-count">{v.notes.length}</span></div>
    {#if v.notes.length}<ul>{#each v.notes as n}<li>{n}</li>{/each}</ul>{:else}<div class="zt-small">…</div>{/if}
  </div>
  {#if v.problems.length}
    <div class="zt-block"><div class="zt-h">Check these <span class="zt-count">{v.problems.length}</span></div>
      <ul>{#each v.problems as p}<li>{p}</li>{/each}</ul></div>
  {/if}
{/if}
