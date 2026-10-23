<script>
  // The Plan → Cycle → Case tree with checkboxes and folds (was renderTree in zephyr-tool.js).
  import { isOpen, rowCount, shownRows } from "./zephyrModel.js";

  let { tree, ticked, ai, folds, ontoggle, onfold } = $props();
  const rows = $derived(shownRows(tree, ai, folds));
</script>

{#if !rows.length}
  <div class="zt-empty">No templates imported yet — use Refresh templates.</div>
{:else}
  {#each rows as r (r.id)}
    {@const on = ticked.has(r.id)}
    {@const why = ai.get(r.id)}
    {@const open = r.kind !== "case" && isOpen(r.id, ai, folds)}
    {@const count = rowCount(tree, r, ticked)}
    <div
      class="zt-row zt-{r.kind}"
      class:is-off={!on}
      style="--zt-depth:{r.depth}"
    >
      {#if r.kind === "case"}
        <span class="zt-fold-pad"></span>{:else}
        <button
          type="button"
          class="zt-fold"
          data-id={r.id}
          aria-expanded={open}
          aria-label="{open ? 'Collapse' : 'Expand'} {r.key}"
          onclick={() => onfold(r.id)}
          >{open ? "▾" : "▸"}
        </button>
      {/if}
      <label>
        <input
          type="checkbox"
          class="zt-checkbox"
          data-id={r.id}
          checked={on}
          onchange={(e) => ontoggle(r.id, e.currentTarget.checked)}
        />
        <span class="zt-key">{r.key}</span>
        {r.name || ""}
        {#if count}
          <span class="zt-count">{count}</span>
        {/if}
      </label>
      {#if why}
        <div class="zt-why">
          <b>{why.question}</b>
          {why.reason} <span class="zt-source">— {why.source}</span>
        </div>
      {/if}
    </div>
  {/each}
{/if}

<style>
  .is-off {
    opacity: 55%;
  }

  .zt-key {
    color: var(--color-sidebar-nav-active-bg);
    font-family: "Roboto Mono Variable", "Roboto Mono", monospace;
    font-weight: 600;
  }
  .zt-fold {
    color: var(--color-text-muted);
    background-color: var(--color-bg-surface);
    border: none;
  }

  .zt-count {
    font-size: 0.8rem;
    margin-left: 12px;
    color: var(--color-text-muted);
  }

  .zt-why {
    margin-left: 24px;
    margin-top: 8px;
    font-size: 0.88rem;
    color: var(--color-text);
    padding: 8px;
    border-left: 2px solid var(--color-error);
  }
  .zt-row {
    padding: 8px 0 2px calc(var(--zt-depth) * 30px);
  }
</style>
