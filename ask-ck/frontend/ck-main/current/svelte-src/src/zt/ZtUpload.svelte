<script>
  // The API Upload result (was renderUpload): where the project has folders in EVERY version (a
  // project that slipped a release can carry an old version — P6), what is skipped (D15), the
  // calls, and — only when nothing stands in the way — the Write to Zephyr button. No typing here.
  import ZtRun from './ZtRun.svelte';

  let { d, sel, run, runBusy, onrun } = $props();
  const t = $derived(d.targets || {});
  const c = $derived(d.counts || {});
  const version = $derived((sel && sel.version) || '');
  const folders = $derived(d.project_folders || []);
  const other = $derived(folders.filter(f => f.version !== version));
  const canWrite = $derived(!(d.problems || []).length && (d.calls || []).length && sel);
</script>

<div class="zt-h">API Upload — what it will do (nothing is written yet)</div>
<div class="zt-small">Plan folder: {(t.testplan && t.testplan.path) || 'not found'} · Cycle folder: {(t.testrun && t.testrun.path) || 'not found'} · {c.plans || 0} plan(s), {c.cycles || 0} cycle(s), {c.calls || 0} calls{c.skipped ? `, ${c.skipped} skipped` : ''}.</div>
<div class="zt-block"><div class="zt-h">Where {(sel && sel.product) || 'the project'} has folders in Zephyr</div>
  {#if folders.length}
    <ul>{#each folders as f}<li class={f.version !== version ? 'zt-problem' : ''}>{f.kind === 'testplan' ? 'plans' : 'cycles'}: {f.path}{f.version !== version ? ` — a different version from What Version (${version})` : ''}</li>{/each}</ul>
  {:else}<div class="zt-small">None found.</div>{/if}
  {#if other.length}<div class="zt-small zt-problem">Check What Version: if the project slipped a release, the wiki may still name the old one.</div>{/if}
</div>
{#if (d.duplicates || []).length}
  <div class="zt-block"><div class="zt-h">Skipped — already in the project folder</div>
    <ul>{#each d.duplicates as x}<li><span class="zt-key">{x.key}</span> → {x.name} exists</li>{/each}</ul></div>
{/if}
{#if (d.problems || []).length}
  <ul>{#each d.problems as p}<li class="zt-problem">{p}</li>{/each}</ul>
{/if}
<table class="table zt-calls"><thead><tr><th>#</th><th>step</th><th>call</th><th>what</th></tr></thead>
  <tbody>{#each d.calls || [] as x}<tr class={x.known ? '' : 'zt-unknown'}><td>{x.n}</td><td>{x.op}</td><td><code>{x.method} {x.path}</code></td><td>{x.about}</td></tr>{/each}</tbody></table>
{#if canWrite}
  <div class="zt-block zt-run"><button id="zt-run" type="button" class="btn btn-primary" disabled={runBusy}
      onclick={onrun}>Write to Zephyr…</button> <span class="zt-small">asks you to confirm the product and version first</span>
    <div id="zt-run-result"><ZtRun job={run} /></div></div>
{/if}
