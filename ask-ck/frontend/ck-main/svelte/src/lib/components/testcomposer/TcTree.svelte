<script>
  //@ts-nocheck
  // The project's live tree, drawn like ZTT's (plan → cycle → case), filtered to what the chosen
  // template can run. Each case: PyScript (a saved script exists) or Manual; Previously Run when an
  // earlier run of the same release version has a result for it. The ticks are the run list.
  let {
    tree,
    kindOf,
    runnable,
    previously,
    ticked = $bindable(),
    runnableOnly = true,
  } = $props();

  let folded = $state({});
  const plans = $derived((tree && tree.plans) || []);

  function shown(c) {
    return !runnableOnly || runnable(c.key);
  }
  function toggle(key, on) {
    const t = new Set(ticked);
    if (on) t.add(key);
    else t.delete(key);
    ticked = t;
  }
  function toggleCycle(cy, on) {
    const t = new Set(ticked);
    for (const c of cy.cases)
      if (shown(c) && runnable(c.key)) {
        if (on) t.add(`${cy.key}/${c.key}`);
        else t.delete(`${cy.key}/${c.key}`);
      }
    ticked = t;
  }
</script>

{#if !plans.length}<div class="zt-empty">No plans loaded.</div>{/if}
{#each plans as p (p.key)}
  <div class="zt-row zt-plan" style="--zt-depth:0">
    <span class="zt-key">{p.key}</span>
    {p.name || ""}
  </div>
  {#each p.cycles as cy (cy.key)}
    {@const vis = cy.cases.filter(shown)}
    <div class="zt-row zt-cycle" style="--zt-depth:1">
      <button
        type="button"
        class="zt-fold"
        aria-expanded={!folded[cy.key]}
        onclick={() => (folded = { ...folded, [cy.key]: !folded[cy.key] })}
        >{folded[cy.key] ? "▸" : "▾"}</button
      >
      <label
        ><input
          type="checkbox"
          checked={vis.some((c) => ticked.has(`${cy.key}/${c.key}`))}
          onchange={(e) => toggleCycle(cy, e.currentTarget.checked)}
        />
        <span class="zt-key">{cy.key}</span>
        {cy.name || ""}
        <span class="zt-count">{vis.length} of {cy.cases.length} shown</span
        ></label
      >
    </div>
    {#if !folded[cy.key]}
      {#each vis as c (c.key)}
        {@const id = `${cy.key}/${c.key}`}
        {@const ok = runnable(c.key)}
        <div
          class="zt-row zt-case"
          class:is-off={!ticked.has(id)}
          style="--zt-depth:2"
        >
          <span class="zt-fold-pad"></span>
          <label
            ><input
              type="checkbox"
              disabled={!ok}
              checked={ticked.has(id)}
              onchange={(e) => toggle(id, e.currentTarget.checked)}
            />
            <span class="zt-key">{c.key}</span>
            {c.name || ""}
            <span class="tc-kind tc-kind-{kindOf(c.key)}"
              >{kindOf(c.key) === "script" ? "PyScript" : "Manual"}</span
            >
            {#if previously(c.key)}<span
                class="tc-prev"
                title={previously(c.key)}>Previously Run</span
              >{/if}
            {#if !ok}<span class="zt-count">not runnable on this template</span
              >{/if}</label
          >
        </div>
      {/each}
    {/if}
  {/each}
{/each}

<style>
  .zt-row {
    padding: 6px 0 2px calc(var(--zt-depth) * 30px);
  }

  .zt-row label {
    display: inline-flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 6px;
    cursor: pointer;
  }

  .zt-plan {
    margin-top: 6px;
    color: var(--color-text-heading);
    font-weight: 600;
  }

  .zt-key {
    color: var(--color-sidebar-nav-active-bg);
    font-family: "Roboto Mono Variable", "Roboto Mono", monospace;
    font-weight: 600;
  }

  .zt-fold {
    width: 1.4em;
    padding: 0;
    border: none;
    background: none;
    color: var(--color-text-muted);
    cursor: pointer;
  }

  .zt-fold-pad {
    display: inline-block;
    width: 1.4em;
  }

  .zt-count {
    margin-left: 12px;
    color: var(--color-text-muted);
    font-size: 0.8rem;
  }

  .zt-empty {
    color: var(--color-text-muted);
    font-style: italic;
  }

  .is-off label {
    opacity: 0.55;
  }

  .tc-kind,
  .tc-prev {
    padding: 1px 8px;
    border: 1px solid var(--color-border-surface);
    border-radius: 10px;
    color: var(--color-text-muted);
    font-size: 0.75rem;
    white-space: nowrap;
  }

  .tc-kind-script {
    color: var(--color-accent);
    border-color: currentColor;
  }

  .tc-prev {
    color: var(--color-warning);
    border-color: currentColor;
    background: color-mix(in srgb, var(--color-warning) 10%, transparent);
  }
</style>
