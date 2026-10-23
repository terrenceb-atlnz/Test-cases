<script>
  // The read-only Results Analysis column (was renderAnalysis): Q1–Q4, 5. Gaps, 6. AI Notes, then
  // what went wrong — failed calls and refused proposals are shown, never hidden.

  //@ts-nocheck
  import { analysisView } from './zephyrModel.js';
  import StatusBadge from '../StatusBadge.svelte';
  import ErrorBanner from '../ErrorBanner.svelte';

  let { job, tree } = $props();
  const v = $derived(analysisView(job, tree));

  // Zephyr keys inside a note (e.g. "AWPTCM-T15496: …") are tagged so .zt-key styles them:
  // AWPTCM- then T (case), P (plan) or C (cycle) and digits. Splitting on a pattern with a
  // capture group keeps the matches — even items are plain text, odd items are keys — and each
  // piece renders as ordinary text, so a note can never inject markup.
  const KEY_RX = /(\bAWPTCM-[TPC]\d+\b)/;
  const keyParts = (text) => String(text ?? '').split(KEY_RX);
</script>

{#if !v}
  <div class="zt-empty">Paste a project page URL and press Organize with LLM.</div>
{:else}
  <!-- A finished analysis gets the green check; the job's own error uses the app's ErrorBanner. -->
  <div class="zt-state zt-state-{v.state}">
    {#if v.state === 'done'}<StatusBadge status="covered" />{/if}
    <span>{v.stateText}</span>
  </div>
  <ErrorBanner message={v.error} />
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
  <div class="zt-block">
    <div class="zt-h">5. Gaps — required, no template <span class="zt-count">{v.gaps.items.length}</span></div>
    {#if v.gaps.state === 'error'}
     <ErrorBanner message={v.gaps.error} />
    {/if}
    {#if v.gaps.items.length}
      <ul>{#each v.gaps.items as x}
        <li>{x.requirement} <span class="zt-source">({x.source})</span>{x.why ? ' — ' + x.why : ''}</li>{/each}
      </ul>
    {:else}
      <div class="zt-small">{v.gaps.state === 'done' ? 'None found.' : v.gaps.state === 'error' ? '' : '…'}</div>
    {/if}
  </div>
  <div class="zt-block"><div class="zt-h">6. AI Notes <span class="zt-count">{v.notes.length}</span></div>
    {#if v.notes.length}
      <ul>
        {#each v.notes as n}
          <li>{#each keyParts(n) as part, i}{#if i % 2}<span class="zt-key">{part}</span>{:else}{part}{/if}{/each}</li>
        {/each}
      </ul>
    {:else}
      <div class="zt-small">…</div>
    {/if}
  </div>

  {#if v.problems.length}
    <div class="zt-block"><div class="zt-h">Check these <span class="zt-count">{v.problems.length}</span></div>
      <ul>
        {#each v.problems as p}
          <li>{p}</li>
        {/each}
      </ul>
    </div>
  {/if}
{/if}

<style>
  .zt-empty {
    margin: 16px 0 16px;
    color: var(--color-text-muted);
    font-size: 1rem;
  }

  .zt-small {
    font-size: 0.8rem;
    padding-top: 8px;
    padding-left: 24px;
  }

  .zt-key {
    color: var(--color-analysis-key);
    font-family: 'Roboto Mono Variable', 'Roboto Mono', monospace;
    font-weight: 600;
  }

  .zt-state {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 16px 0px 16px;
  }
  .zt-h {
    font-weight: 700;
    font-size: 0.94rem;
    text-transform: uppercase;
  }

  .zt-block {
    margin-bottom: 12px;
  }

  .zt-count {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    background: color-mix(in srgb, var(--color-text-muted) 18%, transparent);
    color: var(--color-text);
    margin-left: 0.4rem;
  }

  :global li {
    margin-bottom: 16px;

  }
</style>