<script>
  // The results table (PLAN-test-composer §2.6): grouped by test cycle, a PyScript / Manual marker on
  // every row, the framework's verdict with any re-grade BESIDE it (the person at the page is top of
  // the grading tier list; the verdict itself is never overwritten), clickable logs, Feedback on a
  // script case that failed or errored, and the header readout: counts, time, tokens, cost.
  import { byCycle, effectiveVerdict, fmtDuration, fmtTokens, verdictCounts, VERDICT_ORDER } from './api.js';
  import LogViewer from './LogViewer.svelte';

  let { runId, server, refreshMs = 5000 } = $props();

  let data = $state(null);
  let error = $state(null);
  let fb = $state({});           // case → {busy, text, error}
  let regrading = $state(null);  // case being re-graded
  let rg = $state({ verdict: 'PASS', note: '' });
  let logOpen = $state(null);    // case whose logs are open
  let timer = null;

  const table = $derived(data ? data.table : []);
  const groups = $derived(byCycle(table));
  const counts = $derived(verdictCounts(table));
  const rec = $derived(data ? data.record : null);
  const duration = $derived(rec && rec.started ? ((rec.ended ? Date.parse(rec.ended) : Date.now()) - Date.parse(rec.started)) : null);

  async function load() {
    try { data = await server(`/runs/${encodeURIComponent(runId)}`); error = null; }
    catch (e) { error = e.message; }
  }

  async function feedback(row) {
    fb = { ...fb, [row.case]: { busy: true } };
    try {
      const d = await server(`/runs/${encodeURIComponent(runId)}/feedback/${encodeURIComponent(row.case)}`, { method: 'POST' });
      fb = { ...fb, [row.case]: { text: d.text, error: d.error } };
    } catch (e) { fb = { ...fb, [row.case]: { error: e.message } }; }
  }

  async function saveRegrade(row) {
    try {
      await server(`/runs/${encodeURIComponent(runId)}/regrade`, { method: 'POST',
        body: JSON.stringify({ case: row.case, verdict: rg.verdict, note: rg.note }) });
      regrading = null;
      await load();
    } catch (e) { error = e.message; }
  }

  async function accept() {
    try { await server(`/runs/${encodeURIComponent(runId)}/accept`, { method: 'POST' }); await load(); }
    catch (e) { error = e.message; }
  }

  $effect(() => {
    load();
    timer = setInterval(() => { if (!rec || !['done', 'stopped', 'error'].includes(rec.state)) load(); }, refreshMs);
    return () => clearInterval(timer);
  });
</script>

{#if error}<div class="tc-problem">{error}</div>{/if}
{#if rec}
  <div class="tc-readout">
    {#each counts as c}<span class="tc-count tc-v-{c.verdict.replace(' ', '-')}"><b>{c.n}</b> {c.verdict}</span>{/each}
    <span class="tc-spacer"></span>
    <span class="tc-small">time <b>{fmtDuration(duration)}</b></span>
    <span class="tc-small">tokens <b>{fmtTokens(rec.tokens)}</b></span>
    <span class="tc-small">{rec.cost_usd != null || rec.updates_cost_usd ? `$${((rec.cost_usd || 0) + (rec.updates_cost_usd || 0)).toFixed(2)} (list)` : ''}</span>
    <span class="tc-badge tc-state-{rec.state}">{rec.state}</span>
  </div>
  {#each groups as g}
    <div class="tc-cycle">{g.cycle ? `Cycle ${g.cycle}` : 'No cycle'}</div>
    <table class="table tc-results">
      <thead><tr><th>Case</th><th>Type</th><th>Verdict</th><th>Reason</th><th></th></tr></thead>
      <tbody>
        {#each g.rows as row (row.case)}
          {@const v = effectiveVerdict(row)}
          <tr>
            <td><span class="tc-key">{row.case}</span></td>
            <td><span class="tc-kind tc-kind-{row.kind}">{row.kind === 'script' ? 'PyScript' : row.kind === 'manual' ? 'Manual' : row.kind}</span></td>
            <td><span class="tc-verdict tc-v-{v.replace(' ', '-')}">{v}</span>
              {#if row.regrade}<div class="tc-small" title={row.regrade.note}>re-graded from {row.verdict} by {row.regrade.by}</div>{/if}</td>
            <td class="tc-reason">{row.reason}</td>
            <td class="tc-actions">
              <button type="button" class="btn btn-secondary btn-compact-small" onclick={() => (logOpen = logOpen === row.case ? null : row.case)}>Logs</button>
              <button type="button" class="btn btn-secondary btn-compact-small" onclick={() => { regrading = row.case; rg = { verdict: v, note: '' }; }}>Re-grade</button>
              {#if row.kind === 'script' && ['FAIL', 'ERROR', 'PARTIAL'].includes(row.verdict)}
                <button type="button" class="btn btn-primary btn-compact-small" disabled={fb[row.case] && fb[row.case].busy} onclick={() => feedback(row)}>{fb[row.case] && fb[row.case].busy ? 'Asking…' : 'Feedback'}</button>
              {/if}
            </td>
          </tr>
          {#if regrading === row.case}
            <tr class="tc-subrow"><td colspan="5">
              <select class="form-input" bind:value={rg.verdict}>{#each VERDICT_ORDER.filter(x => x !== 'PENDING') as x}<option value={x}>{x}</option>{/each}</select>
              <input class="form-input" placeholder="why (kept beside the framework's verdict)" bind:value={rg.note}>
              <button type="button" class="btn btn-primary btn-compact-small" onclick={() => saveRegrade(row)}>Save</button>
              <button type="button" class="btn btn-secondary btn-compact-small" onclick={() => (regrading = null)}>Cancel</button>
            </td></tr>
          {/if}
          {#if fb[row.case] && (fb[row.case].text || fb[row.case].error)}
            <tr class="tc-subrow"><td colspan="5"><div class="tc-feedback">
              {#if fb[row.case].error}<div class="tc-problem">{fb[row.case].error}</div>{/if}
              <pre class="tc-pre">{fb[row.case].text || ''}</pre></div></td></tr>
          {/if}
          {#if logOpen === row.case}
            <tr class="tc-subrow"><td colspan="5"><LogViewer {runId} {server} caseKey={row.case} /></td></tr>
          {/if}
        {/each}
      </tbody>
    </table>
  {/each}
  {#if ['done', 'stopped', 'error'].includes(rec.state)}
    <div class="tc-accept">
      {#if rec.accepted_at}<span class="tc-small">Results accepted {rec.accepted_at}. The campaign's work/ folders are kept until device-testing acts on it.</span>
      {:else}<button type="button" class="btn btn-secondary" onclick={accept} title="The evidence (work/ folders) is kept until you accept">Accept results</button>{/if}
    </div>
  {/if}
{/if}
