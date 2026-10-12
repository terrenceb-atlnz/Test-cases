<script>
  // The agent window (PLAN-agent-sessions §7): W1 a read-only stream of the seat session, W2 question
  // and approval cards, W3 a message box. One long-poll at a time to the seat agent (K4); every new
  // event is relayed to the server's run record. If this tab cannot reach the agent (another seat, or
  // the agent restarted), it falls back to reading the server's copy — view-only.
  import { onDestroy, onMount, untrack } from 'svelte';
  import { fmtDuration, fmtTokens, tokensOf } from './api.js';

  let { runId, sessionId = null, agent, server, onstate = () => {}, compact = false } = $props();

  let events = $state([]);
  // The window is re-created per run ({#key runId}), so the INITIAL sessionId is what matters.
  const liveAtStart = untrack(() => !!sessionId);
  let state = $state(liveAtStart ? 'starting' : 'viewing');
  let error = $state(null);
  let mode = $state(liveAtStart ? 'live' : 'server');   // live = from the agent; server = the record
  let follow = $state(true);
  let open = $state({});                              // tool_use id → expanded
  let draft = $state('');
  let other = $state({});                             // request_id → typed "Other" answer
  let answered = $state({});                          // request_id → true once answered here
  let stopped = false;
  let box;

  const results = $derived(new Map(events.filter(e => e.kind === 'tool_result').map(e => [e.id, e])));
  const lastResult = $derived([...events].reverse().find(e => e.kind === 'result'));
  // The session's own cost plus the sentinel's Haiku updates (billed apart, device-testing orient-dt §10).
  const updatesCost = $derived(events.reduce((a, e) => a + (e.kind === 'update' && typeof e.cost_usd === 'number' ? e.cost_usd : 0), 0));
  const cost = $derived(lastResult || updatesCost ? ((lastResult && lastResult.total_cost_usd) || 0) + updatesCost : null);
  const tokens = $derived(lastResult ? tokensOf(lastResult.model_usage) : null);
  const elapsed = $derived(events.length ? Math.round((events[events.length - 1].t || 0) * 1000) : null);
  const pendingIds = $derived(new Set(events.filter(e => e.kind === 'answered').map(e => e.request_id)));
  const live = $derived(['starting', 'running'].includes(state) && mode === 'live');

  function scroll() {
    if (follow && box) queueMicrotask(() => { box.scrollTop = box.scrollHeight; });
  }

  // Events not yet acknowledged by the server: a failed relay (a server restart, a network blip)
  // keeps them and re-sends them with the next batch — the server's record is idempotent by seq.
  let unsent = [];
  async function relay(evs) {
    unsent = unsent.concat(evs);
    if (!unsent.length) return;
    try {
      await server(`/runs/${encodeURIComponent(runId)}/events`, { method: 'POST', body: JSON.stringify({ events: unsent, session_id: sessionId }) });
      unsent = [];
      if (error && error.startsWith('Could not save')) error = null;
    } catch (e) { error = `Could not save ${unsent.length} event(s) to the run record (will retry): ${e.message}`; }
  }

  function take(evs) {
    if (!evs.length) return;
    const have = new Set(events.map(e => e.seq));
    const fresh = evs.filter(e => !have.has(e.seq));
    if (!fresh.length) return;
    events = [...events, ...fresh].sort((a, b) => a.seq - b.seq);
    for (const e of fresh) if (e.kind === 'state') { state = e.state; onstate(e.state); }
    scroll();
  }

  async function pollAgent() {
    let after = 0;
    while (!stopped && mode === 'live') {
      try {
        const d = await agent.events(sessionId, after, 20);
        take(d.events);
        await relay(d.events);
        after = d.next;
        if (d.state && d.state !== state) { state = d.state; onstate(d.state); }
        if (['done', 'error', 'stopped'].includes(d.state) && !d.events.length) break;
      } catch (e) {
        error = `Lost the seat agent (${e.message}) — showing the server's copy.`;
        mode = 'server';
      }
    }
    if (mode === 'server' && !stopped) pollServer();
  }

  async function pollServer() {
    let after = events.length ? events[events.length - 1].seq : -1;
    while (!stopped && mode === 'server') {
      try {
        const d = await server(`/runs/${encodeURIComponent(runId)}/events?after=${after}`);
        take(d.events);
        if (d.events.length) after = d.events[d.events.length - 1].seq;
        if (['done', 'error', 'stopped'].includes(state)) break;
      } catch (e) { error = e.message; }
      await new Promise(r => setTimeout(r, 3000));
    }
  }

  async function answerQuestion(ev, q, label) {
    const answers = {};
    answers[q.question] = label;
    try { await agent.answer(sessionId, { request_id: ev.request_id, answers }); answered = { ...answered, [ev.request_id]: true }; }
    catch (e) { error = e.message; }
  }

  async function approve(ev, allow) {
    try { await agent.answer(sessionId, { request_id: ev.request_id, allow, message: allow ? '' : 'Denied in Ask-CK.' }); answered = { ...answered, [ev.request_id]: true }; }
    catch (e) { error = e.message; }
  }

  async function send() {
    const text = draft.trim();
    if (!text) return;
    try { await agent.message(sessionId, text); draft = ''; } catch (e) { error = e.message; }
  }

  async function stop() {
    try { await agent.stop(sessionId); } catch (e) { error = e.message; }
  }

  function markerClass(line) {
    if (line.startsWith('NOTIFY')) return 'tc-m-notify';
    if (line.startsWith('ASKCK-DONE')) return 'tc-m-done';
    const v = (line.split(/\s+/)[2] || '').toUpperCase();
    return v === 'PASS' ? 'tc-m-pass' : ['FAIL', 'ERROR'].includes(v) ? 'tc-m-fail' : 'tc-m-other';
  }

  onMount(() => { if (mode === 'live') pollAgent(); else pollServer(); });
  onDestroy(() => { stopped = true; });
</script>

<div class="tc-window" class:tc-compact={compact}>
  <div class="tc-window-head">
    <span class="tc-badge tc-state-{state}">{state}</span>
    <span class="tc-small">{mode === 'live' ? 'live from this seat' : 'from the run record'}</span>
    <span class="tc-spacer"></span>
    <span class="tc-small" title="wall clock since the session's first event">time {fmtDuration(elapsed)}</span>
    <span class="tc-small" title="all models, subagents included">tokens {fmtTokens(tokens)}</span>
    <span class="tc-small" title={`list-price estimate${updatesCost ? `, including $${updatesCost.toFixed(2)} for the running updates` : ''}`}>{cost != null ? `$${cost.toFixed(2)}` : ''}</span>
    <label class="tc-small"><input type="checkbox" bind:checked={follow}> Follow</label>
    {#if live}<button type="button" class="btn btn-secondary btn-compact-small tc-stop" onclick={stop}>Stop</button>{/if}
  </div>
  {#if error}<div class="tc-problem">{error}</div>{/if}
  <div class="tc-stream" bind:this={box} onscroll={() => { if (box) follow = box.scrollHeight - box.scrollTop - box.clientHeight < 40; }}>
    {#each events as e (e.seq)}
      {#if e.kind === 'text'}
        <div class="tc-ev tc-text" class:tc-sub={e.parent}>{e.text}</div>
      {:else if e.kind === 'tool_use'}
        {@const r = results.get(e.id)}
        <div class="tc-ev tc-tool" class:tc-sub={e.parent}>
          <button type="button" class="tc-tool-row" onclick={() => (open = { ...open, [e.id]: !open[e.id] })} aria-expanded={!!open[e.id]}>
            <span>{open[e.id] ? '▾' : '▸'}</span> <b>{e.name}</b> <span class="tc-small">{e.summary}</span>
            <span class="tc-tool-status {r ? (r.denied ? 'is-denied' : r.is_error ? 'is-error' : 'is-ok') : 'is-running'}">{r ? (r.denied ? 'denied' : r.is_error ? 'error' : 'ok') : '…'}</span>
          </button>
          {#if open[e.id]}<pre class="tc-pre">{e.input}{r ? '\n— result —\n' + r.excerpt : ''}</pre>{/if}
        </div>
      {:else if e.kind === 'task'}
        <div class="tc-ev tc-task">subagent {e.subagent_type || ''} {e.description || ''} — {e.subtype.replace('task_', '')}{e.status ? ` (${e.status})` : ''}{e.usage && e.usage.total_tokens ? ` · ${fmtTokens(e.usage.total_tokens)} tokens` : ''}</div>
      {:else if e.kind === 'update'}
        <div class="tc-ev tc-update" class:tc-attn={!!e.attention}>{e.at ? `${e.at} ` : ''}{e.text}{#if e.attention}<div class="tc-attn-why">Needs a look: {e.attention}</div>{/if}</div>
      {:else if e.kind === 'marker'}
        <div class="tc-ev tc-marker {markerClass(e.line)}">{e.line}</div>
      {:else if e.kind === 'question'}
        <div class="tc-ev tc-card">
          <div class="tc-card-head">The session asks</div>
          {#each (e.input && e.input.questions) || [] as q}
            <div class="tc-q">{q.question}</div>
            {#if e.waits && live && !pendingIds.has(e.request_id) && !answered[e.request_id]}
              <div class="tc-opts">
                {#each q.options || [] as o}<button type="button" class="btn btn-secondary btn-compact-small" title={o.description || ''} onclick={() => answerQuestion(e, q, o.label)}>{o.label}</button>{/each}
                <input class="form-input tc-other" placeholder="Other…" bind:value={other[e.request_id]}>
                <button type="button" class="btn btn-primary btn-compact-small" onclick={() => answerQuestion(e, q, other[e.request_id] || '')}>Send</button>
              </div>
            {:else}
              <div class="tc-small">{answered[e.request_id] ? 'Answered here.' : e.waits ? 'Waiting for an answer…' : 'Not waited for: the campaign carries on (D5).'}</div>
            {/if}
          {/each}
        </div>
      {:else if e.kind === 'approval'}
        <div class="tc-ev tc-card">
          <div class="tc-card-head">Permission asked: {e.tool}</div>
          <pre class="tc-pre">{e.input}</pre>
          {#if e.waits && live && !pendingIds.has(e.request_id) && !answered[e.request_id]}
            <button type="button" class="btn btn-primary btn-compact-small" onclick={() => approve(e, true)}>Allow</button>
            <button type="button" class="btn btn-secondary btn-compact-small" onclick={() => approve(e, false)}>Deny</button>
          {:else}<div class="tc-small">{answered[e.request_id] ? 'Answered here.' : 'Not approved: outside the session\'s permission profile (D6).'}</div>{/if}
        </div>
      {:else if e.kind === 'result'}
        <div class="tc-ev tc-turn">turn finished · {e.num_turns} turns · {fmtDuration(e.duration_ms)}{e.total_cost_usd != null ? ` · $${e.total_cost_usd.toFixed(2)}` : ''}</div>
      {:else if e.kind === 'user_message'}
        <div class="tc-ev tc-user">{e.text}</div>
      {:else if e.kind === 'state'}
        <div class="tc-ev tc-statechg">session {e.state}{e.error ? ': ' + e.error : ''}</div>
      {:else if e.kind === 'init'}
        <div class="tc-ev tc-statechg">session started · {e.model || ''} · permission mode {e.permission_mode || '?'} · Claude Code {e.cli_version || '?'}</div>
      {/if}
    {/each}
    {#if !events.length}<div class="tc-empty">Waiting for the session's first event…</div>{/if}
  </div>
  {#if live}
    <div class="tc-say">
      <input class="form-input" placeholder="Message the session (e.g. “don’t touch u3”)" bind:value={draft}
        onkeydown={(ev) => { if (ev.key === 'Enter') send(); }}>
      <button type="button" class="btn btn-secondary" onclick={send}>Send</button>
    </div>
  {/if}
</div>
