<script>
  // @ts-nocheck

  // Test Composer — the "Compose a Run" tab (ask-ck/plans/PLAN-test-composer.md §1): project → test
  // bench → template (with what it can run) → Validate the bench against the template → the live
  // project tree filtered to runnable cases → Start → results. Launches go through THIS seat's
  // ck-agent (D7). Ported from current/svelte-src/src/tc/TcPage.svelte.
  import { onMount } from "svelte";
  import TcAgentWindow from "./TcAgentWindow.svelte";
  import TcResultsTable from "./TcResultsTable.svelte";
  import TcRunsList from "./TcRunsList.svelte";
  import TcSetupFields from "./TcSetupFields.svelte";
  import TcTree from "./TcTree.svelte";
  import Button from "../Button.svelte";
  import LlmButton from "../LlmButton.svelte";
  import ErrorBanner from "../ErrorBanner.svelte";
  import CodeEditor from "../CodeEditor.svelte";
  import { loadSetup, runBody, saveSetup } from "./testComposerModel.js";

  import {
    httpServer,
    httpAgent,
  } from "../../services/testcomposer/testComposerService.js";
  let {
    server = httpServer(),
    agent = httpAgent(),
    preselect = null,
    openRun = null,
    pollMs = 4000,
  } = $props();

  // 1. project
  let source = $state("templated"); // templated | wiki
  let projects = $state([]);
  let projectId = $state("");
  let wikiUrl = $state("");
  let wiki = $state(null); // {title, variants}
  let variantPick = $state({}); // index → ticked
  let wikiBusy = $state(false);
  // 2. setup + template
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
    ),
  );
  let templates = $state([]);
  let template = $state("");
  let scripts = $state([]);
  // 3. validate
  let validateRun = $state(null);
  let validateState = $state(null);
  let validateMarkers = $state([]);
  let validateText = $state("");
  // 4. tree
  let tree = $state(null);
  let treeBusy = $state(false);
  let ticked = $state(new Set());
  let runnableOnly = $state(true);
  let previous = $state({}); // case → "run id, verdict"
  // 5. start
  let startAfter = $state("");
  let run = $state(null);
  let refreshKey = $state(0);
  let health = $state(null);
  let status = $state({ msg: "", bad: false });
  let dryRun = $state(null);
  let copyLabel = $state("Copy share link");

  const project = $derived(
    source === "templated"
      ? projects.find((p) => p.id === projectId) || null
      : null,
  );
  const plans = $derived(
    source === "templated"
      ? project
        ? project.plans
        : []
      : wiki
        ? wiki.variants.flatMap((v, i) =>
            variantPick[i] ? v.plans.map((p) => p.key) : [],
          )
        : [],
  );
  const version = $derived(
    project
      ? project.version
      : wiki
        ? (wiki.variants.find((v, i) => variantPick[i]) || {}).version || null
        : null,
  );
  const tmpl = $derived(templates.find((t) => t.name === template) || null);
  const scriptByCase = $derived(
    new Map(scripts.filter((s) => s.case_key).map((s) => [s.case_key, s])),
  );
  const sessionsOk = $derived(
    health && health.sessions && health.sessions.available,
  );
  // device-testing prints `PROBE <MATCH|MISMATCH|NEEDS-CHECK> <template>` (test-mode §1, da37c2d).
  const probe = $derived(
    (validateMarkers.find((l) => l.startsWith("PROBE ")) || "").split(
      /\s+/,
    )[1] || null,
  );
  const validated = $derived(probe === "MATCH");
  const tickedCases = $derived(
    tree
      ? tree.plans.flatMap((p) =>
          p.cycles.flatMap((cy) =>
            cy.cases
              .filter((c) => ticked.has(`${cy.key}/${c.key}`))
              .map((c) => ({ key: c.key, cycle: cy.key })),
          ),
        )
      : [],
  );

  // A launch only starts the seat session (the LLM work runs in it afterwards, shown in the
  // agent window), so its LlmButton has nothing to cancel: a busy click does nothing.
  const noStop = () => {};

  function setStatus(msg, bad = false) {
    status = { msg, bad };
  }
  function kindOf(key) {
    return scriptByCase.has(key) ? "script" : "manual";
  }
  function runnable(key) {
    if (!tmpl) return false;
    return kindOf(key) === "script"
      ? tmpl.runnable_scripts.includes(key)
      : tmpl.manual_cases.includes(key);
  }

  async function loadBasics() {
    try {
      projects = (await server("/projects")).projects;
    } catch (e) {
      setStatus("Projects: " + e.message, true);
    }
    try {
      scripts = (await server("/scripts")).scripts;
    } catch (_) {
      /* shown via empty kinds */
    }
    try {
      templates = (await server("/templates")).templates;
    } catch (e) {
      setStatus("Templates: " + e.message, true);
    }
    try {
      health = await agent.health();
    } catch (e) {
      health = { error: e.message };
    }
  }

  async function readWiki() {
    if (!wikiUrl.trim()) return;
    wikiBusy = true;
    try {
      wiki = await server("/projects/from-wiki", {
        method: "POST",
        body: JSON.stringify({ url: wikiUrl.trim() }),
      });
      variantPick = Object.fromEntries(
        wiki.variants.map((_, i) => [i, wiki.variants.length === 1]),
      );
      setStatus(
        wiki.variants.length > 1
          ? "Several variants share this page — tick the ones this run is for."
          : "",
      );
    } catch (e) {
      setStatus(e.message, true);
    } finally {
      wikiBusy = false;
    }
  }

  async function launch(kind, extra) {
    saveSetup(setup);
    const created = await server("/runs", {
      method: "POST",
      body: JSON.stringify(runBody(kind, setup, extra)),
    });
    const started = await agent.start({
      run_id: created.run_id,
      handoff: created.handoff,
      mode: "campaign",
    });
    if (!started.ok)
      throw new Error(started.error || "the seat agent refused the session");
    return {
      runId: created.run_id,
      sessionId: started.session_id,
      handoff: created.handoff,
    };
  }

  async function validate() {
    try {
      validateRun = await launch("composer-validate", { cases: [], template });
      validateMarkers = [];
      validateText = "";
      validateState = "starting";
      setStatus(`Validating ${setup.testbox} against ${template}…`);
    } catch (e) {
      setStatus("Validate failed: " + e.message, true);
    }
  }

  async function watchValidate() {
    if (!validateRun) return;
    try {
      const d = await server(
        `/runs/${encodeURIComponent(validateRun.runId)}/events`,
      );
      validateMarkers = d.events
        .filter((e) => e.kind === "marker")
        .map((e) => e.line);
      validateText = d.events
        .filter((e) => e.kind === "text" || e.kind === "result")
        .map((e) => e.text || "")
        .join("\n");
    } catch (_) {
      /* window shows errors */
    }
  }

  async function loadTree() {
    if (!plans.length) {
      setStatus("Pick a project (or tick a variant) first.", true);
      return;
    }
    treeBusy = true;
    try {
      tree = await server(
        `/projects/tree?plans=${encodeURIComponent(plans.join(","))}`,
      );
      const t = new Set();
      for (const p of tree.plans)
        for (const cy of p.cycles)
          for (const c of cy.cases)
            if (runnable(c.key)) t.add(`${cy.key}/${c.key}`);
      ticked = t;
      await loadPrevious();
      setStatus(`${t.size} runnable case(s) ticked.`);
    } catch (e) {
      setStatus("Could not read the project from Zephyr: " + e.message, true);
    } finally {
      treeBusy = false;
    }
  }

  /** Previously Run: an earlier composer run of the same release version with a result for the case. */
  async function loadPrevious() {
    const out = {};
    try {
      const runs = (await server("/runs?kind=composer&limit=50")).runs;
      for (const r of runs) {
        const d = await server(`/runs/${encodeURIComponent(r.run_id)}`);
        const v = d.handoff && d.handoff.project && d.handoff.project.version;
        if (!version || v !== version) continue;
        for (const row of d.table)
          if (
            row.verdict &&
            !["PENDING", "NOT TESTED"].includes(row.verdict) &&
            !out[row.case]
          )
            out[row.case] = `${r.run_id}: ${row.verdict}`;
      }
    } catch (_) {
      /* best effort */
    }
    previous = out;
  }

  function body() {
    const cases = tickedCases.map((c) => {
      const s = scriptByCase.get(c.key);
      return s
        ? { key: c.key, kind: "script", script: s.path, cycle: c.cycle }
        : { key: c.key, kind: "manual", cycle: c.cycle };
    });
    const proj = project
      ? {
          id: project.id,
          product: project.product,
          version: project.version,
          plans,
        }
      : wiki
        ? { title: wiki.title, version, plans }
        : null;
    return {
      cases,
      template,
      project: proj,
      options: {
        email: (setup.email || "").trim() || null,
        start_after: startAfter || null,
      },
    };
  }

  async function start() {
    if (!tickedCases.length) {
      setStatus("Nothing is ticked.", true);
      return;
    }
    try {
      const b = body();
      if (b.options.start_after) {
        const created = await server("/runs", {
          method: "POST",
          body: JSON.stringify(runBody("composer", setup, b)),
        });
        setStatus(
          `Scheduled ${created.run_id} for ${startAfter} (${created.handoff.start_at}). Your seat agent starts it then — keep this seat on and logged in; no tab is needed. The results arrive in the runs list and by email.`,
        );
        refreshKey += 1;
        return;
      }
      const r = await launch("composer", b);
      run = { runId: r.runId, sessionId: r.sessionId };
      refreshKey += 1;
      setStatus(`Started ${r.runId}: ${tickedCases.length} case(s).`);
    } catch (e) {
      setStatus("Start failed: " + e.message, true);
    }
  }

  function toggleDryRun() {
    dryRun = dryRun
      ? null
      : JSON.stringify(runBody("composer", setup, body()), null, 2);
  }

  // The button's own label says whether the copy worked (as Help's Copy), then resets.
  async function shareLink() {
    const u = new URL(window.location.href);
    u.searchParams.set("panel", "composer");
    if (project) u.searchParams.set("project", project.id);
    if (wikiUrl) u.searchParams.set("wiki", wikiUrl);
    if (template) u.searchParams.set("template", template);
    try {
      await navigator.clipboard.writeText(u.toString());
      copyLabel = "Copied!";
      setStatus("Share link copied.");
    } catch (_) {
      copyLabel = "Copy failed";
    }
    setTimeout(() => (copyLabel = "Copy share link"), 1500);
  }

  onMount(() => {
    loadBasics().then(() => {
      if (openRun) run = { runId: openRun, sessionId: null };
      if (preselect)
        setStatus(
          `Script ${preselect} preselected: choose its project and a template, then load the tree.`,
        );
    });
    const t = setInterval(watchValidate, pollMs);
    return () => clearInterval(t);
  });
</script>

<div class="tool-page tc-page">
  <div class="section-description">
    Pick a project and the test bench, choose the topology template, check the
    bench against it, then tick the cases to run. Script cases run their saved
    PyScript; manual cases are run by the session by hand. Everything runs
    through your seat's agent.
  </div>

  <div class="tc-step"><span class="tc-step-n">1</span> Project</div>
  <div class="tc-line">
    <div class="tc-row tc-sources">
      <label
        ><input type="radio" bind:group={source} value="templated" /> Templated Project</label
      >
      <label
        ><input type="radio" bind:group={source} value="wiki" /> Zephyr Project Link</label
      >
    </div>
    {#if source === "templated"}
      <div class="tc-row">
        <select id="tc-project" class="form-input" bind:value={projectId}>
          <option value=""
            >— choose a project uploaded by the Templating Tool —</option
          >
          {#each projects as p}<option value={p.id}
              >{p.product} · {p.version}{p.number
                ? ` · Project ${p.number}`
                : ""} ({p.plans.length} plan(s))</option
            >{/each}
        </select>
      </div>
      {#if !projects.length}<div class="tc-row tc-small">
          No templated projects yet — upload one with the Zephyr Templating
          Tool, or use a project link.
        </div>{/if}
    {:else}
      <div class="tc-row">
        <input
          id="tc-wiki"
          class="form-input"
          type="url"
          placeholder="https://wiki.atlnz.lc/awpwiki/index.php/Project:3171_AT-x230-V2"
          bind:value={wikiUrl}
        />
        <Button variant="primary" loading={wikiBusy} on:click={readWiki}
          >{wikiBusy ? "Reading…" : "Read Test Results"}</Button
        >
      </div>
      {#if wiki}
        <div class="tc-row tc-small">
          {wiki.title}: {wiki.variants.length} variant(s) in the Test Results cell.
        </div>
        {#each wiki.variants as v, i}
          <label class="tc-row tc-variant"
            ><input type="checkbox" bind:checked={variantPick[i]} />
            <b>{v.project}</b> · {v.version} ·
            <span class="tc-badge">{v.status || "status ?"}</span>
            <span class="tc-small">{v.title || ""}</span>
            <span class="tc-small"
              >{v.plans
                .map((p) => `${p.key}${p.name ? " " + p.name : ""}`)
                .join(" · ") || "no plans found"}</span
            ></label
          >
        {/each}
      {/if}
    {/if}
  </div>

  <div class="tc-step">
    <span class="tc-step-n">2</span> Test Bench and Template
  </div>
  <div class="tc-line">
    <TcSetupFields bind:setup />
    <div class="tc-row">
      <select id="tc-template" class="form-input" bind:value={template}>
        <option value="">— topology template —</option>
        {#each templates as t}<option value={t.name}
            >{t.name}: {t.runnable_count} runnable{t.note
              ? " (empty)"
              : ""}</option
          >{/each}
      </select>
      {#if tmpl}<span class="tc-small"
          >{tmpl.note ||
            `${tmpl.runnable_scripts.length} script case(s) and ${tmpl.manual_cases.length} manual case(s) can run on ${tmpl.setup}.`}</span
        >{/if}
    </div>
  </div>

  <div class="tc-step">
    <span class="tc-step-n">3</span> Validate the Bench Against the Template
  </div>
  <div class="tc-line">
    <div class="tc-row">
      <LlmButton
        label="Validate"
        verb="Validating…"
        disabled={!template || !setup.testbox || !setup.consoles || !sessionsOk}
        onRun={validate}
        onStop={noStop}
      />
      {#if validated}<span
          class="tc-check"
          title="the probe matched the template"
          >✓ the bench matches {template}</span
        >
      {:else if probe}<span class="tc-problem"
          >Probe: {probe} — the differences are in the session's report below.</span
        >
      {:else if validateState && ["done", "stopped", "error"].includes(validateState)}<span
          class="tc-problem">No probe result — see the notices below.</span
        >{/if}
      <ErrorBanner
        message={health && !sessionsOk
          ? health.error ||
            (health.sessions && health.sessions.reason) ||
            "seat agent too old"
          : ""}
      />
    </div>
    {#if validateRun}
      <div class="tc-row tc-full">
        {#key validateRun.runId}
          <TcAgentWindow
            runId={validateRun.runId}
            sessionId={validateRun.sessionId}
            {agent}
            {server}
            compact
            onstate={(s) => (validateState = s)}
          />
        {/key}
      </div>
    {/if}
  </div>

  <div class="tc-step">
    <span class="tc-step-n">4</span> What is in the Project
  </div>
  <div class="tc-line">
    <div class="tc-row">
      <Button
        variant="primary"
        loading={treeBusy}
        disabled={!plans.length || !template}
        on:click={loadTree}
        >{treeBusy ? "Reading Zephyr…" : "Load the project"}</Button
      >
      <label class="tc-small"
        ><input type="checkbox" bind:checked={runnableOnly} /> runnable on {template ||
          "the template"} only</label
      >
      {#if !validated && tree}<span class="tc-problem"
          >The bench has not been validated against the template.</span
        >{/if}
    </div>
    {#if tree}
      <div class="tc-row tc-full">
        <div class="tc-tree">
          <TcTree
            {tree}
            {kindOf}
            {runnable}
            previously={(k) => previous[k]}
            bind:ticked
            {runnableOnly}
          />
        </div>
      </div>
    {/if}
  </div>

  <div class="tc-step"><span class="tc-step-n">5</span> Start</div>
  <div class="tc-line">
    <div class="tc-row">
      <label class="tc-small"
        >Run after hours from <input
          type="time"
          class="form-input tc-time"
          bind:value={startAfter}
        /></label
      >
      <span class="tc-small">(blank = now)</span>
    </div>
    <div class="tc-row">
      <Button variant="outline" on:click={toggleDryRun}
        >{dryRun ? "Hide" : "Show"} the hand-off</Button
      >
      <Button variant="primary" copy on:click={shareLink}>{copyLabel}</Button>
      <LlmButton
        label={`Start (${tickedCases.length})`}
        verb="Starting…"
        disabled={!tickedCases.length || !sessionsOk}
        onRun={start}
        onStop={noStop}
      />
      {#if status.bad}<ErrorBanner message={status.msg} />
      {:else}<div class="tc-status" role="status">{status.msg}</div>{/if}
    </div>
    {#if dryRun}
      <div class="tc-row tc-full">
        <CodeEditor
          value={dryRun}
          readonly
          language="none"
          height="auto"
          maxHeight="40vh"
        />
      </div>
    {/if}
  </div>

  {#if run}
    <div class="tc-step">
      <span class="tc-step-n">6</span> The Campaign — {run.runId}
    </div>
    <div class="tc-line">
      {#key run.runId}
        <div class="tc-row tc-full">
          <TcAgentWindow
            runId={run.runId}
            sessionId={run.sessionId}
            {agent}
            {server}
            onstate={(s) => {
              if (["done", "stopped", "error"].includes(s)) refreshKey += 1;
            }}
          />
        </div>
        <div class="tc-row tc-full">
          <TcResultsTable runId={run.runId} {server} />
        </div>
      {/key}
    </div>
  {/if}

  <div class="tc-step tc-earlier">Earlier Campaigns</div>
  <TcRunsList
    {server}
    kind="composer"
    {refreshKey}
    onopen={(id) => (run = { runId: id, sessionId: null })}
  />
</div>

<style>
  .tc-page {
    margin-top: 1rem;
    width: 100%;
  }

  .section-description {
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
    margin: 1rem 0 1rem 0;
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

  .tc-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px;
    width: 100%;
    margin-bottom: 0.8rem;
  }

  .tc-row .form-input {
    flex: 1 1 280px;
    min-width: 0;
  }

  .tc-full {
    display: block;
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

  .tc-check {
    color: var(--color-success);
    font-weight: 600;
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

  .tc-sources {
    gap: 16px;
  }

  .tc-sources label {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.9rem;
  }

  .tc-variant {
    gap: 8px;
    align-items: baseline;
    font-size: 0.9rem;
    cursor: pointer;
  }

  .tc-badge {
    padding: 1px 8px;
    border: 1px solid var(--color-border-surface);
    border-radius: 10px;
    color: var(--color-text-muted);
    font-size: 0.75rem;
  }

  .tc-tree {
    max-height: 55vh;
    overflow: auto;
    padding: 8px 12px;
    border: 1px solid var(--color-border-surface);
    border-radius: 10px;
    background: var(--color-bg-surface);
    font-size: 0.9rem;
  }
</style>
