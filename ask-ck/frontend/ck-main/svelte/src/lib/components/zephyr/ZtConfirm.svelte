<script>
  // The confirm modal (was renderConfirm + askToWrite; Terrence 2026-10-07: "just have a confirm
  // modal popup"). It shows the product and version FROM THE FIELDS, where it writes, and — first —
  // any folders this project has under another version: a delayed project may carry an old one.
  let { d, sel, onanswer } = $props();
  const t = $derived(d.targets || {});
  const c = $derived(d.counts || {});
  const other = $derived((d.project_folders || []).filter(f => f.version !== sel.version));
  let noBtn = $state();

  $effect(() => { if (noBtn) noBtn.focus(); });
</script>

<svelte:window onkeydown={(e) => { if (e.key === 'Escape') onanswer(false); }} />

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
<div class="update-overlay" onclick={(e) => { if (e.target === e.currentTarget) onanswer(false); }}>
  <div class="update-dialog zt-confirm" role="alertdialog" aria-modal="true" aria-labelledby="zt-confirm-title">
    <div class="update-title" id="zt-confirm-title">Write to Zephyr?</div>
    <div class="update-body">
      <div class="zt-confirm-what"><b>{sel.product || ''}</b> · AW+ <b>{sel.version || ''}</b></div>
      {#if other.length}
        <div class="zt-problem">This project also has folders under another version — is {sel.version || ''} still right?
          <ul>{#each other as f}<li>{f.kind === 'testplan' ? 'plans' : 'cycles'}: {f.path}</li>{/each}</ul></div>
      {/if}
      <div>Into {(t.testplan && t.testplan.path) || '?'}</div>
      <div>{c.plans || 0} plan(s), {c.cycles || 0} cycle(s), {c.writes || 0} writes{c.skipped ? ` — ${c.skipped} skipped, already there` : ''}.</div>
      <div class="zt-small">If the product or version is wrong, Cancel and correct What Product / What Version above.</div>
    </div>
    <div class="zt-confirm-actions">
      <button type="button" class="btn btn-secondary" data-zt-confirm="no" bind:this={noBtn} onclick={() => onanswer(false)}>Cancel</button>
      <button type="button" class="btn btn-primary" data-zt-confirm="yes" onclick={() => onanswer(true)}>Write to Zephyr</button>
    </div>
  </div>
</div>
