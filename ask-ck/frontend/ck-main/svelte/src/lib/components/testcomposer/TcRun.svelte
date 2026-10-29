<script>
  // @ts-nocheck

  // Test Composer — the "Run Scripts" tab. A placeholder until the page is built.
  import { onMount, tick, untrack } from "svelte";
  import { selectForCopy, SELECTED_HINT } from "../../utils/select.js";
  import TcAgentWindow from "./TcAgentWindow.svelte";
  import TcResultsTable from "./TcResultsTable.svelte";
  import TcRunsList from "./TcRunsList.svelte";
  import TcSetupFields from "./TcSetupFields.svelte";
  import Button from "../Button.svelte";
  import LlmButton from "../LlmButton.svelte";
  import ErrorBanner from "../ErrorBanner.svelte";
  import {
    formatOutlets,
    loadSetup,
    runBody,
    saveSetup,
    scriptsLink,
  } from "./testComposerModel.js";

  import {
    httpServer,
    httpAgent,
  } from "../../services/testcomposer/testComposerService.js";
  let {
    server = httpServer(),
    agent = httpAgent(),
    link = null,
    openRun = null,
  } = $props();

  const TERMINAL = ["done", "stopped", "error"];
  // Read once, at mount: a share link fills the page and is then forgotten.
  const given = untrack(() => link) || {};

  // Link fields win over this seat's remembered answers, which are not overwritten until Launch.
  // The email is never in a link: it is always this seat's own (R-D4).
  let setup = $state(
    Object.assign(
      {
        testbox: "",
        consoles: "",
        pduIp: "",
        outlets: "",
        constraints: "",
        email: "",
      },
      loadSetup(),
      given.setup || {},
    ),
  );
  let sources = $state([]);
  let sourceId = $state(given.source || "generated");
  let listing = $state(null); // {enabled, reason, scripts}
  let filter = $state("");
  let order = $state([]); // ticked paths, in the order they run
  let missing = $state([]); // paths a link or Run again named that are not available
  let wanted = given.scripts && given.scripts.length ? given.scripts : null;
  let startAfter = $state(given.start || "");
  let health = $state(null);
  let busy = $state(false);
  let status = $state({ msg: "", bad: false });
  let copyLabel = $state("Share link");
  let shareHref = $state("");       // shown, selected, for a manual Ctrl+C (lib/utils/select.js)
  let shareInput = $state(null);
  let run = $state(null); // {runId, sessionId}
  let runState = $state(null);
  let refreshKey = $state(0);

  const scripts = $derived(listing ? listing.scripts : []);
  const byPath = $derived(new Map(scripts.map((s) => [s.path, s])));
  const shown = $derived(
    scripts.filter(
      (s) =>
        !filter.trim() ||
        `${s.case_key || ""} ${s.path}`
          .toLowerCase()
          .includes(filter.trim().toLowerCase()),
    ),
  );
  const groups = $derived(
    [...new Set(shown.map((s) => s.group))].map((g) => ({
      group: g,
      rows: shown.filter((s) => s.group === g),
    })),
  );
  const sessionsOk = $derived(
    health && health.sessions && health.sessions.available,
  );
  const canLaunch = $derived(
    order.length > 0 && sessionsOk && setup.testbox && setup.consoles && !busy,
  );

// A launch only starts the seat session (the LLM work runs in it afterwards, shown in the
  // agent window), so its LlmButton has nothing to cancel: a busy click does nothing.
  const noStop = () => {};

  function setStatus(msg, bad = false) {
    status = { msg, bad };
  }

  function toggle(path) {
    order = order.includes(path)
      ? order.filter((p) => p !== path)
      : [...order, path];
  }

  /** Tick the named scripts in their order; anything missing or no longer validated is reported. */
  function pick(paths) {
    order = paths.filter((p) => byPath.has(p));
    missing = paths.filter((p) => !byPath.has(p));
  }

  async function loadScripts() {
    try {
      const d = await server(
        `/scripts?source=${encodeURIComponent(sourceId)}&validated=true`,
      );
      sources = d.sources || [];
      listing = {
        enabled: d.enabled,
        reason: d.reason,
        scripts: d.scripts || [],
      };
    } catch (e) {
      listing = { enabled: false, reason: e.message, scripts: [] };
    }
    if (wanted) {
      pick(wanted);
      wanted = null;
    }
  }

  function chooseSource(id) {
    if (id === sourceId) return;
    sourceId = id;
    order = [];
    missing = [];
    loadScripts();
  }

  async function checkAgent() {
    try {
      health = await agent.health();
    } catch (e) {
      health = { error: e.message };
    }
  }

  function body() {
    return {
      source: sourceId,
      cases: order.map((p) => ({
        key: (byPath.get(p) || {}).case_key,
        kind: "script",
        script: p,
      })),
      options: {
        email: (setup.email || "").trim() || null,
        start_after: startAfter || null,
      },
    };
  }

  async function launch() {
    if (!canLaunch) return;
    busy = true;
    saveSetup(setup);
    try {
      const b = runBody("scripts", setup, body());
      const created = await server("/runs", {
        method: "POST",
        body: JSON.stringify(b),
      });
      if (b.options.start_after) {
        setStatus(
          `Scheduled ${created.run_id} for ${startAfter} (${created.handoff.start_at}). Your seat agent starts it then — keep this seat on and logged in; no tab is needed. The results arrive in the runs list and by email.`,
        );
      } else {
        const started = await agent.start({
          run_id: created.run_id,
          handoff: created.handoff,
          mode: "campaign",
        });
        if (!started.ok)
          throw new Error(
            started.error || "the seat agent refused the session",
          );
        run = { runId: created.run_id, sessionId: started.session_id };
        runState = null;
        setStatus(
          `Launched ${created.run_id} on ${b.testbox}: ${order.length} script(s).`,
        );
      }
      refreshKey += 1;
    } catch (e) {
      setStatus("Launch failed: " + e.message, true);
    } finally {
      busy = false;
    }
  }

  // No clipboard write — plain http has none that works on the seats (lib/utils/select.js): the
  // link appears in the box under the button, selected, and the user presses Ctrl+C.
  async function copyLink() {
    shareHref = scriptsLink(window.location.href, {
      source: sourceId,
      scripts: order,
      setup,
      start: startAfter,
    });
    await tick();
    copyLabel = selectForCopy(shareInput) ? SELECTED_HINT : "Share link";
    setStatus(
      "The share link is selected below — press Ctrl+C to copy it. It carries the scripts and the bench settings, never your email.",
    );
    setTimeout(() => (copyLabel = "Share link"), 3000);
  }

  /** Refill the page from a finished run's hand-off: same scripts, order and bench; this seat's email. */
  async function runAgain() {
    try {
      const h =
        (await server(`/runs/${encodeURIComponent(run.runId)}`)).handoff || {};
      setup = Object.assign({}, setup, {
        testbox: h.testbox || "",
        consoles: h.consoles || "",
        pduIp: (h.pdu && h.pdu.ip) || "",
        outlets: formatOutlets(h.pdu && h.pdu.outlets),
        constraints: h.constraints || "",
      });
      startAfter = "";
      const paths = (h.cases || []).map((c) => c.path).filter(Boolean);
      if ((h.source || "generated") !== sourceId) {
        sourceId = h.source || "generated";
        wanted = paths;
        await loadScripts();
      } else pick(paths);
      setStatus(`Filled from ${run.runId}. Press Launch to run it again.`);
    } catch (e) {
      setStatus("Could not read that run: " + e.message, true);
    }
  }

  onMount(() => {
    loadScripts();
    checkAgent();
    if (openRun) run = { runId: openRun, sessionId: null };
    if (link)
      setStatus(
        "Filled from a share link. Check the settings, then press Launch.",
      );
  });
</script>

<div class="tool-page tc-page">
  <div class="section-description">
    Run validated scripts on a test bench through your seat's agent, several at
    once, in the order you tick them. A script that fails does not stop the
    rest. There is no repair or review: that is Validation's job. The session
    still checks the bench before it runs anything.
  </div>

  <div class="tc-step"><span class="tc-step-n">1</span> Source</div>
  <div class="tc-line rs-sources">
    {#each sources as s (s.id)}
      <label class="tc-small" title={s.reason || ""}
        ><input
          type="radio"
          name="rs-source"
          value={s.id}
          checked={sourceId === s.id}
          disabled={!s.enabled}
          onchange={() => chooseSource(s.id)}
        />
        {s.label}{s.enabled ? "" : " (not yet)"}</label
      >
    {/each}
  </div>

  <div class="tc-step"><span class="tc-step-n">2</span> Scripts</div>

  <div class="tc-line">
    {#if listing && !listing.enabled}
      <ErrorBanner message={listing.reason} />
    {/if}
    <input
      id="rs-filter"
      class="form-input"
      placeholder="Filter by case key or path"
      bind:value={filter}
    />
    <div class="rs-pick">
      <div class="tc-scripts">
        {#each groups as g (g.group)}
          <div class="rs-group">{g.group}</div>
          {#each g.rows as s (s.path)}
            <label
              class="tc-script-row"
              class:is-chosen={order.includes(s.path)}
            >
              <input
                type="checkbox"
                name="rs-script"
                value={s.path}
                checked={order.includes(s.path)}
                onchange={() => toggle(s.path)}
              />
              <span class="tc-key">{s.case_key || "?"}</span>
              <span>{s.path}</span>
              <span class="tc-small"
                >validated {String(s.finalized_at || "").slice(0, 10)}</span
              >
            </label>
          {/each}
        {/each}
        {#if listing && listing.enabled && !scripts.length}
          <div class="tc-small rs-empty">
            No validated scripts yet. A script appears here once Validation has
            finalized it.
          </div>
        {/if}
      </div>
      <div class="rs-order">
        <div class="tc-small">Runs in this order</div>
        {#if order.length}
          <ol>
            {#each order as p (p)}<li>
                <span class="tc-key"
                  >{(byPath.get(p) || {}).case_key || "?"}</span
                > <span class="tc-small">{p}</span>
              </li>{/each}
          </ol>
        {:else}<div class="tc-small">Nothing ticked.</div>{/if}
      </div>
    </div>
    {#each missing as p (p)}<div class="tc-problem rs-missing">
        not available: {p}
      </div>{/each}
  </div>

  <div class="tc-step"><span class="tc-step-n">3</span> Where it Runs</div>
  <div class="tc-line">
    <TcSetupFields bind:setup />
  </div>

  <div class="tc-step"><span class="tc-step-n">4</span> When and Launch</div>
  <div class="tc-line">
    <div class="launch-lines">
      <div class="launch-line">
        <label class="tc-small"
          >Run once, after hours, from <input
            id="rs-start"
            type="time"
            class="form-input tc-time"
            bind:value={startAfter}
          /></label
        >
        <span class="tc-small">(blank = now)</span>
      </div>
      <div class="launch-line">
        <Button variant="primary" copy on:click={copyLink}>{copyLabel}</Button>
        {#if shareHref}
          <input class="form-input tc-share-link" readonly aria-label="Share link" bind:this={shareInput}
            value={shareHref} onclick={(e) => e.currentTarget.select()} />
        {/if}
        <LlmButton
          label={`${startAfter ? "Schedule" : "Launch"} (${order.length})`}
          verb={startAfter ? "Scheduling…" : "Launching…"}
          disabled={!canLaunch}
          onRun={launch}
          onStop={noStop}
        />
        {#if status.bad}
          <ErrorBanner message={status.msg} />
        {:else}
          <div class="tc-status" role="status">{status.msg}</div>
        {/if}
      </div>
      <div class="launch-line">
        {#if health && health.error}
          <ErrorBanner message={`Your seat agent is not reachable (${health.error}) — run the seat setup from the home page.`} />
        {:else if health && !sessionsOk}
          <ErrorBanner message={`Your seat agent cannot run sessions: ${health.sessions ? health.sessions.reason : "agent too old — re-run the seat setup"}`} />
        {:else}
          <span class="tc-small">
            {#if !health}checking your seat agent…
            {:else}Seat agent {health.agent_version} ready · device-testing at {health.sessions.dt_root}{/if}
          </span>
        {/if}
      </div>
    </div>
  </div>

  {#if run}
    <div class="tc-step">
      <span class="tc-step-n">5</span> The session — {run.runId}
    </div>
    {#key run.runId}
      <div class="tc-line">
        <TcAgentWindow
          runId={run.runId}
          sessionId={run.sessionId}
          {agent}
          {server}
          onstate={(s) => {
            runState = s;
            if (TERMINAL.includes(s)) refreshKey += 1;
          }}
        />
      </div>
      <div class="tc-step"><span class="tc-step-n">6</span> Results</div>
      <div class="tc-line">
        <TcResultsTable runId={run.runId} {server} />
      </div>
    {/key}
    <div class="tc-line">
      <Button
        variant="outline"
        disabled={!TERMINAL.includes(runState)}
        on:click={runAgain}>Run again</Button
      >
      <span class="tc-small"
        >{TERMINAL.includes(runState)
          ? "Fills the page with this run's scripts, order and bench."
          : "Available when the run has finished."}</span
      >
    </div>
  {/if}
  <div class="tc-step tc-earlier">Earlier Runs</div>

  <TcRunsList
    {server}
    kind="scripts"
    {refreshKey}
    onopen={(id) => {
      run = { runId: id, sessionId: null };
      runState = null;
    }}
  />
</div>

<style>
  .tc-page {
    margin-top: 1rem;
    width: 100%;
  }

  .section-description {
    /* margin: 0 0 16px; */
    color: var(--color-text-muted);
    font-size: 0.94rem;
    padding-bottom: 1rem;
  }

  .tc-step {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 8px 0 8px;
    font-weight: 600;
    color: var(--color-text-heading);
  }

  .tc-step-n {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 3.5rem;
    height: 3.5rem;
    border-radius: 50%;
    border: 4px solid var(--color-accent);
    background: var(--color-bg-content);
    color: var(--color-text-heading);
    font-size: 1.1rem;
  }

  .tc-earlier {
    margin: 2rem 0 1rem 0;
  }

  .tc-line {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    margin: 4px 0;
    border-left: 4px solid var(--color-accent);
    padding-left: 2.2rem;
    margin-left: 1.6rem;
    width: 100%;
  }

  .tc-line .form-input {
    flex: 1 1 280px;
    min-width: 0;
  }

  .launch-line {
    margin-bottom: 0.8rem;
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .tc-small {
    color: var(--color-text-muted);
    font-size: 0.94rem;
  }

  .tc-status {
    min-height: 18px;
    margin: 6px 0;
    color: var(--color-text-muted);
    font-size: 0.88rem;
    font-style: italic;
  }

  .tc-problem {
    color: var(--color-error);
    font-style: normal;
  }

  .tc-key {
    font-family: "Roboto Mono Variable", "Roboto Mono", monospace;
    font-size: 0.8rem;
    color: var(--color-analysis-key);
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

  .tc-time {
    flex: none;
    width: 8em;
    margin-left: 4px;
  }

  .rs-sources {
    gap: 16px;
  }

  .rs-sources label {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.9rem;
  }

  .rs-pick {
    display: grid;
    grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
    gap: 12px;
    width: 100%;
  }

  @media (max-width: 900px) {
    .rs-pick {
      grid-template-columns: minmax(0, 1fr);
    }
  }

  .tc-scripts,
  .rs-order {
    max-height: 260px;
    overflow: auto;
    border: 1px solid var(--color-border-surface);
    border-radius: 10px;
    background: var(--color-bg-surface);
  }

  .rs-order {
    padding: 8px 12px;
  }

  .rs-order ol {
    margin: 4px 0 0 1.4em;
    padding: 0;
    font-size: 0.85rem;
  }

  .rs-group {
    padding: 8px 12px 2px;
    color: var(--color-text-muted);
    font-size: 0.8rem;
    font-weight: 600;
  }

  .tc-script-row {
    display: flex;
    align-items: baseline;
    gap: 10px;
    padding: 6px 12px;
    border-bottom: 1px solid var(--color-border-surface);
    color: var(--color-text);
    font-size: 0.9rem;
    cursor: pointer;
  }

  .tc-script-row:last-child {
    border-bottom: 0;
  }

  .tc-script-row:hover {
    background: color-mix(in srgb, var(--color-accent) 6%, transparent);
  }

  .tc-script-row.is-chosen {
    background: color-mix(in srgb, var(--color-accent) 14%, transparent);
  }

  .tc-script-row .tc-small {
    margin-left: auto;
    white-space: nowrap;
  }

  .rs-empty {
    padding: 8px 12px;
  }
</style>
