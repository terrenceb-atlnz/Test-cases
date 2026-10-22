<script>

  //@ts-nocheck
  // The results table (PLAN-test-composer §2.6): grouped by test cycle, a PyScript / Manual marker on
  // every row, the framework's verdict with any re-grade BESIDE it (the person at the page is top of
  // the grading tier list; the verdict itself is never overwritten), clickable logs, Feedback on a
  // script case that failed or errored, and the header readout: counts, time, tokens, cost.
  import { byCycle, effectiveVerdict, fmtDuration, fmtTokens, verdictCounts, VERDICT_ORDER } from './testComposerModel';
  import LogViewer from './LogViewer.svelte';
  import Button from '../Button.svelte';
  import LlmButton from '../LlmButton.svelte';

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

  // Feedback is a real server-side LLM call: `headers` (from LlmButton) carries X-CK-LLM-Call,
  // so the button shows live progress and a busy click truly cancels it.
  async function feedback(row, headers = {}) {
    fb = { ...fb, [row.case]: { busy: true } };
    try {
      const d = await server(`/runs/${encodeURIComponent(runId)}/feedback/${encodeURIComponent(row.case)}`,
        { method: 'POST', headers: { 'Content-Type': 'application/json', ...headers } });
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

<div class="tc-results-block">
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
    <div class="tc-table-wrap">
    <table class="tc-results">
      <thead><tr><th>Case</th><th>Type</th><th>Verdict</th><th>Reason</th><th></th></tr></thead>
      <tbody>
        {#each g.rows as row (row.case)}
          {@const v = effectiveVerdict(row)}
          <tr>
            <td><span class="tc-key">{row.case}</span></td>
            <td><span class="tc-kind tc-kind-{row.kind}">{row.kind === 'script' ? 'PyScript' : row.kind === 'manual' ? 'Manual' : row.kind}</span></td>
            <td><span class="tc-verdict tc-v-{v.replace(' ', '-')}">{v}</span>
              {#if row.regrade}<div class="tc-small" title={row.regrade.note}>re-graded from {row.verdict} by {row.regrade.by}</div>{/if}</td>
            {#if row.reason}
              <td class="tc-reason">{row.reason}</td>
            {/if}
            <td class="tc-actions">
              <Button variant="outline" on:click={() => (logOpen = logOpen === row.case ? null : row.case)}>Logs</Button>
              <Button variant="outline" on:click={() => { regrading = row.case; rg = { verdict: v, note: '' }; }}>Re-grade</Button>
              {#if row.kind === 'script' && ['FAIL', 'ERROR', 'PARTIAL'].includes(row.verdict)}
                <LlmButton label="Feedback" verb="Asking…" onRun={(headers) => feedback(row, headers)} />
              {/if}
            </td>
          </tr>
          {#if regrading === row.case}
            <tr class="tc-subrow"><td colspan="5"><div class="tc-regrade">
              <select class="form-input" bind:value={rg.verdict}>{#each VERDICT_ORDER.filter(x => x !== 'PENDING') as x}<option value={x}>{x}</option>{/each}</select>
              <input class="form-input tc-note" placeholder="why (kept beside the framework's verdict)" bind:value={rg.note}>
              <Button variant="primary" on:click={() => saveRegrade(row)}>Save</Button>
              <Button variant="outline" on:click={() => (regrading = null)}>Cancel</Button>
            </div></td></tr>
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
    </div>
  {/each}
  {#if ['done', 'stopped', 'error'].includes(rec.state)}
    <div class="tc-accept">
      {#if rec.accepted_at}<span class="tc-small">Results accepted {rec.accepted_at}. The campaign's work/ folders are kept until device-testing acts on it.</span>
      {:else}<Button variant="outline" title="The evidence (work/ folders) is kept until you accept" on:click={accept}>Accept results</Button>{/if}
    </div>
  {/if}
{/if}
</div>

<style>
  /* The results, in the new pages' look: a readout line, then one table per test cycle in a
     surface card styled like the app's Table component. Spans its step. */
  .tc-results-block {
    display: flex;
    flex-direction: column;
    gap: 8px;
    width: 100%;
  }

  .tc-readout {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px 14px;
    padding: 4px 0;
  }

  .tc-count {
    font-size: 0.9rem;
  }

  .tc-spacer {
    flex: 1 1 auto;
  }

  .tc-small {
    color: var(--color-text-muted);
    font-size: 0.85rem;
  }

  .tc-problem {
    color: var(--color-error);
    font-size: 0.88rem;
  }

  .tc-cycle {
    margin-top: 8px;
    color: var(--color-text-heading);
    font-weight: 600;
  }

  /* --- The table (after Table.svelte: surface card, uppercase header, accent row hover) --- */
  .tc-table-wrap {
    overflow: auto;
    border: 1px solid var(--color-border-surface);
    border-radius: 10px;
    background: var(--color-bg-surface);
  }

  .tc-results {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
  }

  .tc-results th {
    padding: 10px 12px;
    border-bottom: 2px solid var(--color-border-surface);
    background: var(--color-table-header-bg);
    color: var(--color-text);
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-align: left;
    text-transform: uppercase;
  }

  .tc-results td {
    padding: 8px 12px;
    border-top: 1px solid var(--color-border-surface);
    color: var(--color-text-muted);
    vertical-align: top;
  }

  .tc-results tbody tr:not(.tc-subrow):hover {
    background: color-mix(in srgb, var(--color-accent) 6%, transparent);
  }

  .tc-subrow td {
    background: var(--color-bg-content);
  }

  .tc-reason {
    color: var(--color-text);
  }

  .tc-actions {
    white-space: nowrap;
  }

  .tc-actions :global(.btn) {
    margin-right: 6px;
  }

  .tc-key {
    font-family: 'Roboto Mono Variable', 'Roboto Mono', monospace;
    font-size: 0.8rem;
    color: var(--color-analysis-key);
  }

  /* --- Markers: kind, verdict, state ----------------------------------------------------- */
  .tc-kind,
  .tc-badge {
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

  .tc-verdict {
    font-weight: 700;
  }

  .tc-v-PASS { color: var(--color-success); }
  .tc-v-FAIL,
  .tc-v-ERROR { color: var(--color-error); }
  .tc-v-UNSUPPORTED,
  .tc-v-BLOCKED,
  .tc-v-PARTIAL { color: var(--color-warning); }

  .tc-state-starting,
  .tc-state-running {
    color: var(--color-accent);
    border-color: currentColor;
  }

  .tc-state-done {
    color: var(--color-success);
    border-color: currentColor;
  }

  .tc-state-error,
  .tc-state-stopped {
    color: var(--color-error);
    border-color: currentColor;
  }

  /* --- Re-grade, feedback, accept -------------------------------------------------------- */
  .tc-regrade {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
  }

  .form-input {
    padding: 8px 12px;
    border-radius: 8px;
    border: 1px solid var(--color-border-surface);
    background: var(--color-bg-surface);
    color: var(--color-text);
    font: inherit;
    font-size: 0.94rem;
  }

  .tc-note {
    flex: 1 1 240px;
    min-width: 0;
  }

  .tc-pre {
    margin: 0;
    color: var(--color-text);
    font-family: inherit;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }

  .tc-accept {
    margin: 8px 0;
  }
</style>
