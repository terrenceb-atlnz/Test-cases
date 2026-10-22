<script>
  // @ts-nocheck
  import Button from '../Button.svelte';

  // A port of the ART Log Viewer's DESIGN (author's permission, 2026-10-09): two panes, any file in
  // either pane so timestamps line up, the tail first and "Load earlier" in chunks, download, copy.
  // Reads only the run's own campaign files (GET /runs/{id}/campaign, /file, /download).
  let { runId, server, caseKey = null } = $props();

  let camp = $state(null);
  let error = $state(null);
  let panes = $state([{ path: '', text: '', start: null, more: false, busy: false },
                      { path: '', text: '', start: null, more: false, busy: false }]);

  const files = $derived(camp ? camp.files.filter(f => !caseKey || !f.case || caseKey.endsWith(String(f.case).split('-')[0])) : []);

  async function loadFiles() {
    try {
      camp = await server(`/runs/${encodeURIComponent(runId)}/campaign`);
      if (camp.found && files.length && !panes[0].path) {
        const first = files.find(f => f.final) || files[files.length - 1];
        await pick(0, first.path);
      }
    } catch (e) { error = e.message; }
  }

  async function pick(i, path) {
    panes[i] = { path, text: '', start: null, more: false, busy: true };
    if (!path) { panes[i].busy = false; return; }
    try {
      const d = await server(`/runs/${encodeURIComponent(runId)}/file?path=${encodeURIComponent(path)}`);
      panes[i] = { path, text: d.data, start: d.start, more: d.has_more_before, busy: false };
    } catch (e) { panes[i] = { ...panes[i], busy: false }; error = e.message; }
  }

  async function earlier(i) {
    const p = panes[i];
    if (!p.more || p.busy) return;
    panes[i] = { ...p, busy: true };
    try {
      const d = await server(`/runs/${encodeURIComponent(runId)}/file?path=${encodeURIComponent(p.path)}&before=${p.start}`);
      panes[i] = { ...p, text: d.data + p.text, start: d.start, more: d.has_more_before, busy: false };
    } catch (e) { panes[i] = { ...p, busy: false }; error = e.message; }
  }

  function copy(i) {
    try { navigator.clipboard.writeText(panes[i].text); } catch (_) { /* http: no clipboard API */ }
  }

  function hl(line) {
    return /\bFAIL\b|UNSUPPORTED|ERROR/.test(line) ? 'tc-log-fail' : /\bPASS\b/.test(line) ? 'tc-log-pass' : '';
  }

  $effect(() => { loadFiles(); });
</script>

<div class="tc-logs">
  {#if error}<div class="tc-problem">{error}</div>{/if}
  {#if camp && !camp.found}
    <div class="tc-small">No campaign files yet — device-testing writes them as the run goes (its queue file names this run).</div>
  {:else if camp}
    <div class="tc-small">Queue: {camp.queue} · {files.length} file(s)</div>
    <div class="tc-panes">
      {#each panes as p, i}
        <div class="tc-pane">
          <div class="tc-pane-head">
            <select class="form-input" value={p.path} onchange={(e) => pick(i, e.currentTarget.value)}>
              <option value="">— choose a file —</option>
              {#each files as f}<option value={f.path}>{f.path.split('/').slice(-3).join('/')} ({Math.round(f.size / 1024)} KB){f.final ? ' · final' : ''}</option>{/each}
            </select>
            {#if p.path}
              <a class="tc-link-btn" href={`/api/test-composer/runs/${encodeURIComponent(runId)}/download?path=${encodeURIComponent(p.path)}`}>Download</a>
              <Button variant="outline" copy on:click={() => copy(i)}>Copy</Button>
            {/if}
          </div>
          {#if p.more}<div><Button variant="outline" loading={p.busy} on:click={() => earlier(i)}>{p.busy ? 'Loading…' : 'Load earlier'}</Button></div>{/if}
          <pre class="tc-pre tc-log">{#each p.text.split('\n') as line}<span class={hl(line)}>{line}</span>{'\n'}{/each}</pre>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  /* The log viewer, in the new pages' look: two panes side by side (stacked when narrow), each
     a file picker over a scrolling log in the code font, PASS / FAIL lines coloured. */
  .tc-logs {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .tc-small {
    color: var(--color-text-muted);
    font-size: 0.85rem;
  }

  .tc-problem {
    color: var(--color-error);
    font-size: 0.88rem;
  }

  .tc-panes {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: 12px;
  }

  @media (max-width: 900px) {
    .tc-panes { grid-template-columns: minmax(0, 1fr); }
  }

  .tc-pane {
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-width: 0;
  }

  .tc-pane-head {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
  }

  .form-input {
    flex: 1 1 200px;
    min-width: 0;
    padding: 8px 12px;
    border-radius: 8px;
    border: 1px solid var(--color-border-surface);
    background: var(--color-bg-surface);
    color: var(--color-text);
    font: inherit;
    font-size: 0.9rem;
  }

  /* Download is a link (the browser saves the file), drawn like an outline Button. */
  .tc-link-btn {
    display: inline-flex;
    align-items: center;
    padding: 6px 16px;
    border: 1px solid var(--color-accent);
    border-radius: 10px;
    color: var(--color-accent);
    font-size: 0.85rem;
    font-weight: 600;
    text-decoration: none;
  }

  .tc-link-btn:hover {
    background: color-mix(in srgb, var(--color-accent) 8%, transparent);
  }

  .tc-log {
    max-height: 50vh;
    margin: 0;
    padding: 10px 12px;
    overflow: auto;
    border: 1px solid var(--color-border-surface);
    border-radius: 10px;
    background: var(--color-code-bg);
    color: var(--color-text);
    font-family: Consolas, 'Courier New', monospace;
    font-size: 12px;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }

  .tc-log-fail { color: var(--color-error); }
  .tc-log-pass { color: var(--color-success); }
</style>
