<script>
  // The API Upload result (was renderUpload): where the project has folders in EVERY version (a
  // project that slipped a release can carry an old version — P6), what is skipped (D15), the
  // calls, and — only when nothing stands in the way — the Write to Zephyr button. No typing here.
  
  //@ts-nocheck

  import ZtRun from './ZtRun.svelte';
  import Table from '../Table.svelte';
  import ErrorBanner from '../ErrorBanner.svelte';

  let { d, sel, run, runBusy, onrun } = $props();
  const t = $derived(d.targets || {});
  const c = $derived(d.counts || {});
  const version = $derived((sel && sel.version) || '');
  const folders = $derived(d.project_folders || []);
  const other = $derived(folders.filter(f => f.version !== version));
  const canWrite = $derived(!(d.problems || []).length && (d.calls || []).length && sel);

  // The calls, in the shape the shared Table takes: one row per call, keyed by its number.
  const callColumns = [
    { key: 'n', label: '#', width: 1 },
    { key: 'op', label: 'Step', width: 1 },
    { key: 'call', label: 'Call', width: 4, code: true },
    { key: 'about', label: 'What', width: 9 },
  ];
  const callRows = $derived((d.calls || []).map((x) => ({
    id: x.n, n: x.n, op: x.op, call: `${x.method} ${x.path}`, about: x.about,
  })));
</script>

<div class="zt-h">API Upload — what it will do (nothing is written yet)</div>
<div class="zt-small">Plan folder: {(t.testplan && t.testplan.path) || 'not found'} · Cycle folder: {(t.testrun && t.testrun.path) || 'not found'} · {c.plans || 0} plan(s), {c.cycles || 0} cycle(s), {c.calls || 0} calls{c.skipped ? `, ${c.skipped} skipped` : ''}.</div>
<div class="zt-block"><div class="zt-h">Where {(sel && sel.product) || 'the project'} has folders in Zephyr</div>
  {#if folders.length}
    <ul>{#each folders as f}<li class={f.version !== version ? 'zt-problem' : ''}>{f.kind === 'testplan' ? 'plans' : 'cycles'}: {f.path}{f.version !== version ? ` — a different version from What Version (${version})` : ''}</li>{/each}</ul>
  {:else}<div class="zt-small">None found.</div>{/if}
  {#if other.length}<div class="zt-small zt-problem">Check What Version: if the project slipped a release, the wiki may still name the old one.</div>{/if}
  {#if (d.duplicates || []).length}
    <div class="zt-block"><div class="zt-h">Skipped — already in the project folder</div>
      <ul>{#each d.duplicates as x}<li><span class="zt-key">{x.key}</span> → {x.name} exists</li>{/each}</ul></div>
  {/if}
  {#if (d.problems || []).length}
    {#each d.problems as p}<ErrorBanner message={p} />{/each}
  {/if}
</div>

<Table columns={callColumns} rows={callRows} selectable={false} style='height = 80vh;'/>
{#if canWrite}
  <div class="zt-block zt-run"><button id="zt-run" type="button" class="btn btn-primary" disabled={runBusy}
      onclick={onrun}>Write to Zephyr…</button> <span class="zt-small">asks you to confirm the product and version first</span>
    <div id="zt-run-result"><ZtRun job={run} /></div></div>
{/if}

<style>
  /* Matches ZtAnalysis: same headings, spacing and key style, from the app's theme tokens. */
  .zt-h {
    margin: 16px 0 8px;
    font-weight: 700;
    font-size: 1rem;
    color: var(--color-text);
  }

  .zt-small {
    margin: 0 0 8px;
    color: var(--color-text-muted);
    font-size: 0.94rem;
  }

  .zt-block {
    margin: 0 0 24px;
    padding: 8px 24px;
    border: 1px solid var(--color-border-surface);
    border-radius: 10px;
    background: var(--color-bg-surface);
  }

  .zt-block ul {
    margin: 0px 4px 24px;
    padding-left: 20px;
  }

  .zt-block li {
    margin-bottom: 12px;
    font-size: 0.94rem;
  }

  .zt-key {
    color: var(--color-sidebar-nav-active-side);
    font-family: 'Roboto Mono Variable', 'Roboto Mono', monospace;
    font-weight: 600;
  }

  /* A folder in a different version, a refusal: the thing to check before writing. */
  .zt-problem {
    color: var(--color-error);
    font-weight: 600;
  }

  /* The Write to Zephyr box — the one step that changes the live server. */
  .zt-run {
    margin-top: 24px;
    border-color: var(--color-warning);
  }
</style>