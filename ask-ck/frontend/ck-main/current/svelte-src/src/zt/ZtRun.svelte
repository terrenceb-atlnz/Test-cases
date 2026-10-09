<script>
  // The real upload's progress and outcome, GET /upload/run/{id} (was renderRun).
  import { RUN_HEADS } from './model.js';

  let { job } = $props();
  const res = $derived((job && job.result) || {});
  const err = $derived(job && (job.error || res.error));
</script>

{#if job}
  <div class="zt-state zt-state-{job.state}">{RUN_HEADS[job.state] || job.state}</div>
  {#if err}<div class="zt-problem">{err}</div>{/if}
  {#if res.stopped_at}<div class="zt-small">Stopped in {res.stopped_at}.</div>{/if}
  {#if (res.created || []).length}
    <div class="zt-small">Created in Zephyr: {res.created.map(x => `${x.kind} ${x.id} (from ${x.from || ''})`).join(', ')}.</div>
  {/if}
  {#if (res.skipped || []).length}<div class="zt-small">Skipped: {res.skipped.map(x => x.key).join(', ')}.</div>{/if}
  <ol class="zt-steps">{#each job.steps || [] as x}<li>{x.msg || ''}</li>{/each}</ol>
{/if}
