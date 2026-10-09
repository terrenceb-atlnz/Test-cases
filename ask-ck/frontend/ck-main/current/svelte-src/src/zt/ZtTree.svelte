<script>
  // The Plan → Cycle → Case tree with checkboxes and folds (was renderTree in zephyr-tool.js).
  import { isOpen, rowCount, shownRows } from './model.js';

  let { tree, ticked, ai, folds, ontoggle, onfold } = $props();
  const rows = $derived(shownRows(tree, ai, folds));
</script>

{#if !rows.length}
  <div class="zt-empty">No templates imported yet — use Refresh templates.</div>
{:else}
  {#each rows as r (r.id)}
    {@const on = ticked.has(r.id)}
    {@const why = ai.get(r.id)}
    {@const open = r.kind !== 'case' && isOpen(r.id, ai, folds)}
    {@const count = rowCount(tree, r, ticked)}
    <div class="zt-row zt-{r.kind}" class:is-off={!on} style="--zt-depth:{r.depth}">
      {#if r.kind === 'case'}<span class="zt-fold-pad"></span>{:else}<button type="button" class="zt-fold"
          data-id={r.id} aria-expanded={open} aria-label="{open ? 'Collapse' : 'Expand'} {r.key}"
          onclick={() => onfold(r.id)}>{open ? '▾' : '▸'}</button>{/if}
      <label><input type="checkbox" data-id={r.id} checked={on}
          onchange={(e) => ontoggle(r.id, e.currentTarget.checked)}>
        <span class="zt-key">{r.key}</span> {r.name || ''}{#if count} <span class="zt-count">{count}</span>{/if}</label>
      {#if why}<div class="zt-why"><b>{why.question}</b> {why.reason} <span class="zt-source">— {why.source}</span></div>{/if}
    </div>
  {/each}
{/if}
