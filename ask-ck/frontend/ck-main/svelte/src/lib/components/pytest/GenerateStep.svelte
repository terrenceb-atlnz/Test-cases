<script>
// @ts-nocheck

  import ArrowStep from './ArrowStep.svelte';
  import StatusBadge from '../StatusBadge.svelte';
  import Button from '../Button.svelte';
  import EditableField from '../EditableField.svelte';
  import CodeEditor from '../CodeEditor.svelte';
  import StatusModal from '../StatusModal.svelte';
  import ConfirmModal from '../ConfirmModal.svelte';
  import LlmButton from '../LlmButton.svelte';
  import ReviewFindings from './ReviewFindings.svelte';
  import ErrorBanner from '../ErrorBanner.svelte';
  import { onMount, onDestroy } from 'svelte';
  import { scrollToSection } from '../../utils/scroll.js';

  // --- Props: data (all seeded once at mount from the session) ----------------------
  /** @type {string} Default Group — saved session.step6.naming.group if there is one, else
      the case's own folder. */
  export let initialGroup = '';

  /** @type {string} Already-saved session.step6.naming.name, if any. */
  export let initialName = '';

  /** @type {string} For Save Modal*/
  export let caseTitle = '';

  /** @type {string} The session's already-assembled script (step6.files.test.code), if any —
      restored so the Summary doesn't start blank after a reload. */
  export let initialAssembledCode = '';

  /** @type {Array<{ level: string, message: string }>} The lint for that script (step6.lint). */
  export let initialLintResults = [];

  /** @type {{ at: string, findings: Array } | null} The last stored review (step6.review), so
      a reload doesn't silently discard findings someone paid an LLM call for. */
  export let initialReview = null;

  /** @type {{ review_stale?: boolean, review_rounds?: number, review_rounds_free?: number,
      review_last_prompt_chars?: number } | null} The server's gen_state — NOT seeded once:
      it changes after every review/assembly, and drives the stale badge and round counts. */
  export let genState = null;

  // --- Props: callbacks — units ------------------------------------------------------
  /** @type {() => Promise<Array<{ id: string, kind: string, tc_n: number | null, action: string,
      verify: string, prompt: string, code: string, status: string, error: string }>>}
      The server's units (step_prompts) — called once on mount. */
  export let onLoadUnits = async () => [];

  /** @type {(items: Array<{ id: string, prompt?: string, edited?: boolean }>) => Promise<{
      dispatched: string[], already_running: string[], max_concurrent: number, primed: string | null }>}
      Queues the units and returns at once — progress comes from onPollStatus. */
  export let onDispatchUnits = async () => ({ dispatched: [], already_running: [], max_concurrent: 0, primed: null });

  /** @type {() => Promise<{ units: Record<string, { status: string, error: string, at: string }>, running: string[] }>}
      Per-unit status, no code — polled every couple of seconds while anything is running. */
  export let onPollStatus = async () => ({ units: {}, running: [] });

  /** @type {(unitId: string) => Promise<{ status: string, code: string, error: string, at: string }>}
      One unit's stored reply — fetched once as each unit lands. */
  export let onFetchUnitCode = async () => ({ status: 'pending', code: '', error: '', at: '' });

  // --- Props: callbacks — Summary -----------------------------------------------------
  /** @type {(group: string, name: string) => Promise<void>} Autosave-on-blur for the two
      naming fields alone — 409s once a script has already been assembled (renaming after
      that point has to move the file on disk too, which is onSave's job, not this one). */
  export let onSaveNaming = async () => {};

  /** @type {(group: string, name: string) => Promise<{ assembledCode: string, lintResults: Array }>}
      No LLM — deterministic splice + lint, server-side. 409s if any unit is still missing code. */
  export let onAssemble = async () => ({ assembledCode: '', lintResults: [] });

  // --- Props: callbacks — Review/Fix --------------------------------------------------
  /** @type {(code: string) => Promise<any>} Persists the on-screen script into the session
      (save_script, no disk write) — run before every review and fix. */
  export let onPushCodeEdits = async () => ({});

  /** @type {(code: string) => Promise<Array<{ level: string, message: string }>>} Re-lint: pushes
      the on-screen script, re-runs the server's lint on it and returns the new results. */
  export let onRelint = async () => [];

  /** @type {(headers: Record<string, string>, extraRound: boolean) => Promise<{ findings: Array, at: string }>}
      review_script — throws "review round cap: …" once the free rounds are used. */
  export let onReview = async () => ({ findings: [], at: '' });

  /** @type {(headers: Record<string, string>) => Promise<{ iterations: number }>} fix_script —
      one LLM call that rewrites the whole script. */
  export let onFixScript = async () => ({ iterations: 0 });

  /** @type {(units: string[]) => Promise<{ dispatched: string[], already_running: string[], unmapped: string[],
      structural: string[], stale: string[], primed: string | null }>} fix_units, limited to `units` —
      returns at once; the fixed units land through the same status poll as Generate. */
  export let onFixUnits = async () => ({ dispatched: [], already_running: [], unmapped: [], structural: [], stale: [], primed: null });

  /** @type {(units: string[]) => Promise<{ applied: string[], lint_ok: boolean, lint_errors: number }>}
      apply_held — applies the named units' held fixes, then re-assembles and re-lints. */
  export let onApplyHeld = async () => ({ applied: [], lint_ok: false, lint_errors: 0 });

  /** @type {() => Promise<any>} Re-fetches the session (parent keeps it) and returns step6 —
      fix results, the refreshed script/lint and the (cleared) review are read off it. */
  export let onRefreshStep6 = async () => ({});

  /** @type {() => Promise<{ changed: string[], dropped: string[] }>} rechunk — re-cuts the units
      from the assembled script (local, no LLM); run after a whole-script fix. */
  export let onRechunk = async () => ({ changed: [], dropped: [] });

  /** @type {(group: string, name: string, code: string) => Promise<{ status: string, message: string }>}
      Save and Finish: writes generated/ with this naming + code, then confirms Generate. Never
      throws — a refusal comes back as status 'error' with the server's reason. */
  export let onSave = async () => ({ status: 'success', message: '' });

  /** @type {(() => void) | null} Called once the save succeeds — parent marks the stepper finished */
  export let onFinished = null;

  /** @type {((pageId: string) => void) | null} The save modal's "Compose Test". */
  export let onNavigate = null;

  /** @type {((caseId?: string | null) => void) | null} The save modal's "Create Another PyTest". */
  export let onCreateAnother = null;

  // --- Units and per-unit state -------------------------------------------------------
  // Units for Generate come from the server (step_prompts), in file order: the "setup" unit
  // (the TestSet configure/tear_down pair) when the skeleton has one, then one unit per
  // TestCase class, keyed by the server's own ids ("tc1", "tc2", …). Arrow-step labels follow tc_n.
  let generateUnits = [];

  // Per-unit generation state, keyed by the unit's id — seeded from each unit's stored
  // chunk, so a unit the server already generated shows its code (and one whose last run
  // failed shows why) instead of starting blank. `renderedPrompt` is the prompt as loaded:
  // a prompt that differs from it is the reviewer's edit. `storedEdit` is the server saying
  // the loaded prompt is itself an earlier, kept edit. `at` is when the stored reply landed —
  // a change of `at` on the poll means new bytes exist for that unit.
  let generateState = {};
  let confirmedGenerateUnits = [];

  let isLoadingUnits = false;
  let loadUnitsError = '';

  async function loadUnits() {
    isLoadingUnits = true;
    loadUnitsError = '';
    try {
      const units = await onLoadUnits();
      const nextState = {};
      for (const u of units) {
        nextState[u.id] = {
          prompt: u.prompt,
          renderedPrompt: u.prompt,
          storedEdit: !!u.edited,
          code: u.status === 'ok' ? u.code : '',
          error: u.status === 'error' ? u.error : '',
          at: u.at || '',
          held: null,   // a held fix's {code, diff, scope}, once loaded
        };
      }
      generateState = nextState;
      // Code already stored from an earlier run counts as reviewed, so a reload doesn't
      // demand every unit be re-confirmed. New code landing on this page un-confirms its
      // unit again (fetchLandedCode) — that's the code that still needs a look.
      confirmedGenerateUnits = units.filter((u) => nextState[u.id].code).map((u) => u.id);
      generateUnits = units.map((u) =>
        u.kind === 'setup'
          ? { ...u, label: 'Setup', title: 'Setup', detail: 'TestSet setUp/tearDown pair' }
          : { ...u, label: u.tc_n, title: `Unit ${u.tc_n}`, detail: u.action }
      );
    } catch (e) {
      loadUnitsError = (e && e.message) || String(e);
      return;
    } finally {
      isLoadingUnits = false;
    }
    // A run may already be going (started before a reload, or by this page's previous
    // mount) — one poll picks it up, and stops itself if nothing is in flight.
    startPolling();
  }

  onMount(loadUnits);
  onDestroy(stopPolling);

  // --- Arrow-step navigation, statuses and progress ---------------------------------
  const GENERATE_SUMMARY_STEP_ID = '__generate_summary__';
  const GENERATE_REVIEW_STEP_ID = '__generate_review__';

  let generateActiveUnitId = null;

  $: {
    if (!generateActiveUnitId && generateUnits.length > 0) {
      generateActiveUnitId = generateUnits[0].id;
    }
  }

  $: generateActiveUnit = generateUnits.find((u) => u.id === generateActiveUnitId) ?? null;

  function selectGenerateUnit(unitId) {
    generateActiveUnitId = unitId;
  }

  // `criticalUnitIds`/`heldUnitIds` are named directly here so this block re-runs when a review lands —
  // Svelte only tracks identifiers written in the reactive statement itself.
  let generateUnitStatuses = {};
  $: {
    const next = {};
    for (const unit of generateUnits) {
      if (heldUnitIds.includes(unit.id)) {
        next[unit.id] = 'review';   // a fix is waiting for its Confirm Unit
      } else if (criticalUnitIds.has(unit.id)) {
        next[unit.id] = 'error';
      } else if (confirmedGenerateUnits.includes(unit.id)) {
        next[unit.id] = 'covered';
      } else if (generateState[unit.id]?.code) {
        next[unit.id] = 'review';
      } else {
        next[unit.id] = 'none';
      }
    }
    generateUnitStatuses = next;
  }

  // Summary shows counts, not a per-unit list. 'error' (a high-severity review finding) is
  // counted apart so the counts always add up to the number of units.
  $: summaryCounts = Object.values(generateUnitStatuses).reduce(
    (acc, st) => ({ ...acc, [st]: (acc[st] || 0) + 1 }),
    { covered: 0, review: 0, none: 0, error: 0 }
  );

  $: generateSummaryStatus =
    generateUnits.length > 0 && generateUnits.every((u) => confirmedGenerateUnits.includes(u.id))
      ? 'covered'
      : 'none';

  $: generateCoveragePercent =
    generateUnits.length === 0
      ? 0
      : Math.round(
          (Object.values(generateUnitStatuses).filter((s) => s === 'covered').length / generateUnits.length) * 100
        );

  // Next unconfirmed unit, not just the next in order; Summary once all are confirmed.
  function advanceGenerateUnit() {
    const updatedConfirmed = confirmedGenerateUnits.includes(generateActiveUnitId)
      ? confirmedGenerateUnits
      : [...confirmedGenerateUnits, generateActiveUnitId];
    confirmedGenerateUnits = updatedConfirmed;

    const nextUnconfirmed = generateUnits.find((u) => !updatedConfirmed.includes(u.id));
    generateActiveUnitId = nextUnconfirmed ? nextUnconfirmed.id : GENERATE_SUMMARY_STEP_ID;
    scrollToSection('.step-intro');
  }

  // --- Generation: one dispatch request, then one status poll ------------------------
  // Units in flight server-side, as last reported by the poll (or marked at dispatch).
  // Drives each unit's own arrow-step spinner — the rest of the row stays usable.
  let runningUnitIds = {};
  let isDispatchingAll = false;
  let runStatus = '';
  let dispatchError = '';
  // True from a Generate dispatch until its run settles — only then does the settle replace
  // runStatus with the "N/M generated" summary (a fix run writes its own message instead).
  let generationRunActive = false;

  const POLL_MS = 2000;
  let pollTimer = null;
  let pollInFlight = false;

  // One-shot: run once the poll next sees nothing in flight (Fix Units uses it to read the
  // fix result off the session after its last unit lands).
  let onRunSettled = null;

  // Units holding a fix that waits for confirmation (units_status' `held`) — shown orange
  // until Confirm Unit applies the fix.
  let heldUnitIds = [];

  function startPolling() {
    stopPolling();
    pollTimer = setInterval(pollOnce, POLL_MS);
    pollOnce();
  }

  function stopPolling() {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
  }

  function unitTitle(unitId) {
    return generateUnits.find((u) => u.id === unitId)?.title ?? unitId;
  }

  // A unit's prompt travels with the request only when it is the reviewer's own: edited
  // on this page, or an earlier kept edit the server handed back. Everything else is sent
  // as a bare id and rendered fresh server-side — sending unedited text is how a stale tab
  // once fed a whole run old prompts that the server then kept as edits (current/, 2026-09-07).
  function dispatchItem(unitId) {
    const st = generateState[unitId];
    const edited = st.storedEdit || st.prompt !== st.renderedPrompt;
    return edited && st.prompt.trim() ? { id: unitId, prompt: st.prompt, edited: true } : { id: unitId };
  }

  async function dispatch(unitIds) {
    dispatchError = '';
    for (const id of unitIds) runningUnitIds[id] = true;
    runningUnitIds = runningUnitIds;
    let d;
    try {
      d = await onDispatchUnits(unitIds.map(dispatchItem));
    } catch (e) {
      for (const id of unitIds) delete runningUnitIds[id];
      runningUnitIds = runningUnitIds;
      dispatchError = (e && e.message) || String(e);
      return;
    }
    // Anything the server did not take (or was already running) is reconciled by the poll;
    // only what it confirmed stays marked as in flight here.
    const live = new Set([...(d.dispatched || []), ...(d.already_running || [])]);
    for (const id of unitIds) if (!live.has(id)) delete runningUnitIds[id];
    runningUnitIds = runningUnitIds;
    const n = (d.dispatched || []).length;
    generationRunActive = true;
    runStatus = n === 0
      ? 'Already running — waiting for it to finish.'
      : `${n} unit${n === 1 ? '' : 's'} dispatched` +
        (d.primed ? ` — ${unitTitle(d.primed)} runs alone first to warm the prompt cache.` : '.');
    startPolling();
  }

  async function pollOnce() {
    if (pollInFlight) return;
    pollInFlight = true;
    let d;
    try {
      d = await onPollStatus();
    } catch (e) {
      pollInFlight = false;
      return;   // a dropped poll is not a failure of the work — the next tick retries
    }
    try {
      const running = new Set(d.running || []);
      const nextRunning = {};
      const landed = [];
      for (const unit of generateUnits) {
        if (running.has(unit.id)) { nextRunning[unit.id] = true; continue; }
        const st = d.units?.[unit.id];
        // `at` is the discriminator, not status: a unit generated by an earlier run is
        // already 'ok', so only a changed `at` means this run replaced its bytes.
        if (st && st.at && st.at !== generateState[unit.id].at) landed.push(unit.id);
      }
      runningUnitIds = nextRunning;
      heldUnitIds = Object.entries(d.units || {}).filter(([, s]) => s.held).map(([id]) => id);
      if (heldUnitIds.length) {
        // A held unit needs confirmation again — that confirmation is what applies its fix.
        confirmedGenerateUnits = confirmedGenerateUnits.filter((id) => !heldUnitIds.includes(id));
        loadHeldFixes(heldUnitIds);
      }
      await Promise.all(landed.map(fetchLandedCode));
      if (running.size === 0) {
        stopPolling();
        if (generationRunActive) {
          generationRunActive = false;
          runStatus = settledSummary();
        }
        if (onRunSettled) {
          const cb = onRunSettled;
          onRunSettled = null;
          try { await cb(); } catch (e) { runStatus = `Could not read the result: ${(e && e.message) || e}`; }
        }
      }
    } finally {
      pollInFlight = false;
    }
  }

  async function fetchLandedCode(unitId) {
    try {
      const r = await onFetchUnitCode(unitId);
      const st = generateState[unitId];
      st.at = r.at || st.at;
      // A failed re-run must not keep showing the old success.
      st.code = r.status === 'ok' ? r.code : '';
      st.error = r.status === 'error' ? (r.error || 'failed') : '';
      st.held = r.held || null;
      generateState = generateState;
      confirmedGenerateUnits = confirmedGenerateUnits.filter((id) => id !== unitId);
    } catch (e) {
      // Leave `at` unchanged so the next poll that sees this unit tries again.
    }
  }

  function settledSummary() {
    const total = generateUnits.length;
    const ok = generateUnits.filter((u) => generateState[u.id].code).length;
    const failed = generateUnits.filter((u) => generateState[u.id].error).length;
    return `${ok}/${total} unit${total === 1 ? '' : 's'} generated` +
      (failed ? ` — ${failed} failed; re-run ${failed === 1 ? 'it' : 'them'} individually.` : '.');
  }

  function generateUnitCode(unitId) {
    if (runningUnitIds[unitId]) return;   // already in flight
    dispatch([unitId]);
  }

  // Only units with no code yet, or whose last run failed — re-generating a unit that
  // already has code is a deliberate per-unit click.
  async function generateAllUnits() {
    const wanted = generateUnits
      .filter((u) => !runningUnitIds[u.id] && (!generateState[u.id].code || generateState[u.id].error))
      .map((u) => u.id);
    if (wanted.length === 0) {
      runStatus = 'Every unit already has code — regenerate one from its own page.';
      return;
    }
    isDispatchingAll = true;
    try {
      await dispatch(wanted);
    } finally {
      isDispatchingAll = false;
    }
  }

  // --- Summary: naming ----------------------------------------------------------------
  // Name starts blank until the reviewer types one (or one was already saved).
  let group = initialGroup;
  let name = initialName;

  async function saveNaming() {
    if (!group.trim() || !name.trim()) return;   // silent by design, matching current/'s own blur-save
    try {
      await onSaveNaming(group.trim(), name.trim());
    } catch (e) {
      // Silent on purpose — a 409 here just means a script already exists (rename is
      // onSave's job instead), and a half-typed name on a stray blur isn't worth a dialog.
    }
  }

  // --- Summary: assemble & lint -------------------------------------------------------
  let assembledCode = initialAssembledCode;
  let lintResults = initialLintResults;
  let assembled = !!initialAssembledCode;

  let isAssembling = false;
  let assembleError = '';

  // Re-lint: re-checks the script AS EDITED on screen — Assemble would re-splice the units and
  // discard hand edits, so this is the way to lint a hand repair.
  let isRelinting = false;
  let relintError = '';

  async function relint() {
    isRelinting = true;
    relintError = '';
    try {
      lintResults = await onRelint(assembledCode);
    } catch (e) {
      relintError = (e && e.message) || String(e);
    } finally {
      isRelinting = false;
    }
  }

  async function assembleAndLint() {
    isAssembling = true;
    assembleError = '';
    try {
      const result = await onAssemble(group.trim(), name.trim());
      assembledCode = result.assembledCode;
      lintResults = result.lintResults;
      assembled = true;
      scrollToSection('.assembled-script-label')
    } catch (e) {
      assembleError = (e && e.message) || String(e);
    } finally {
      isAssembling = false;
    }
  }

  // --- Review/Fix ---------------------------------------------------------------------
  // Shows the same assembled script as Summary (one shared variable, so an edit in either
  // place is the same edit).
  $: generateReviewStatus = assembled ? 'review' : 'none';

  // --- Review/Fix: review with LLM (ported from current/'s ptReviewScript/ptRenderReview) --
  // The review returns FINDINGS, never a rewrite — a finding becomes a change only through a
  // fix, where it is recorded and reviewable.
  let review = initialReview;

  // A review describes ONE version of the script; once the code has moved on (a save or hand
  // edit) it is stale. Shown by ReviewFindings; also read by the red-unit logic below.
  $: reviewStale = !!genState?.review_stale;
  $: reviewFindings = review?.findings || [];

  // How many tool review rounds this script has had, out of the free allowance.
  $: reviewButtonTitle = genState?.review_rounds_free
    ? `Tool review rounds used: ${genState.review_rounds || 0} of ${genState.review_rounds_free}` +
      (genState.review_last_prompt_chars
        ? ` (the last sent ~${Math.round(genState.review_last_prompt_chars / 1000)}k prompt characters)`
        : '') +
      ' — after that, another round needs a confirmation.'
    : '';

  // Free rounds used up: the server refuses with "review round cap: …"; another round goes
  // only if the reviewer says so. The modal's answer resolves this parked promise.
  let showReviewCapModal = false;
  let reviewCapMessage = '';
  let reviewCapResolve = null;

  function askReviewCap(message) {
    reviewCapMessage = message + ' Send another tool review round anyway?';
    showReviewCapModal = true;
    return new Promise((resolve) => { reviewCapResolve = resolve; });
  }

  function answerReviewCap(proceed) {
    reviewCapResolve && reviewCapResolve(proceed);
    reviewCapResolve = null;
  }

  async function runReview(headers) {
    // Push edits first — reviewing the session copy while the editor holds something else
    // reports findings against a script the reviewer cannot see.
    await onPushCodeEdits(assembledCode);
    try {
      return await onReview(headers, false);
    } catch (e) {
      const msg = (e && e.message) || String(e);
      if (!/^review round cap:/.test(msg)) throw e;
      if (!(await askReviewCap(msg.replace(/^review round cap: /, '')))) throw e;
      return await onReview(headers, true);
    }
  }

  function handleReviewResult(d) {
    review = { at: d.at, findings: d.findings || [] };
    fixesUnlocked = true;
  }

  // The two fix buttons are usable only after a Review with LLM, and lock again once either
  // fix has run — the next fix needs a fresh review of the fixed code. A review restored from
  // the session (and not stale) counts as having been run.
  let fixesUnlocked = !!initialReview?.at && !genState?.review_stale;
  const FIX_LOCKED_HINT = 'Run Review with LLM first — the fixes act on its findings.';

  // Lint errors also unlock the fixes. The server refuses Review while lint has blocking
  // errors ("run Fix units to clear them, then Review"), so gating the fixes on a review alone
  // left no way forward: no review without fixing, no fixing without a review.
  $: hasLintErrors = lintResults.some((r) => r.level === 'error');
  $: fixesAvailable = fixesUnlocked || hasLintErrors;

  // --- Review/Fix: fixes (ported from current/'s ptFixFromSummary / _ptFixUnitsCommon) --
  // Both push the on-screen script first — fix the script the reviewer can see, not a stale
  // session copy — and both leave the server with new code, fresh lint and NO review (it
  // described the pre-fix code), which is re-read off the session afterwards.
  let fixError = '';

  // Re-assembly after a unit fix is the user's step: the script is marked not assembled, so
  // Assemble & Lint on Summary has to be run again before Review/Fix is usable.
  function markNotAssembled(message) {
    assembled = false;
    assembledCode = '';
    lintResults = [];
    runStatus = message + ' Re-assemble on Summary once every unit is confirmed.';
  }

  // Fix whole script: one LLM call that rewrites the file, then the units are re-cut from it
  // (rechunk, local) so each unit holds its slice of the fixed script — without that the units
  // keep the OLD code, the server refuses Assemble / Fix Units as "diverged", and an Assemble
  // would discard the fix. Every unit then turns orange for confirmation (Confirm all on
  // Summary); re-assembly stays manual and now reproduces the fixed script.
  async function runFixScript(headers) {
    await onPushCodeEdits(assembledCode);
    const d = await onFixScript(headers);
    fixesUnlocked = false;
    const r = await onRechunk();
    const s = await onRefreshStep6();
    review = s.review;
    await Promise.all(generateUnits.map((u) => fetchLandedCode(u.id)));   // each unit's slice
    confirmedGenerateUnits = [];   // every unit goes orange
    const dropped = r.dropped || [];
    markNotAssembled(`Revised the whole script (iteration ${d.iterations}) and re-cut it into the units — ` +
      `every unit is now in review; check them, then use Confirm all on Summary.` +
      (dropped.length ? ` ${dropped.length} unit(s) no longer exist in the fixed script: ${dropped.map(unitTitle).join(', ')}.` : ''));
    return d;
  }

  // Fix units: re-generates ONLY the flagged units — the red ones (a high-severity finding in
  // the current review) and those a lint error names (fixUnitTargets) — each with all of its
  // own current reasons. A review-driven fix comes back HELD:
  // the unit's code is untouched and it turns orange until Confirm Unit applies the fix.
  // Run by an LlmButton that stays busy until the fixed units have landed and the result has
  // been read — the unit calls run server-side after the dispatch returns, so the button's
  // click-to-stop cannot cancel them.
  async function runFixUnits() {
    await onPushCodeEdits(assembledCode);
    const d = await onFixUnits([...fixUnitTargets]);
    const dispatched = d.dispatched || [];
    for (const id of dispatched) runningUnitIds[id] = true;
    runningUnitIds = runningUnitIds;
    const unmapped = (d.unmapped || []).length;
    const structural = d.structural || [];
    const stale = d.stale || [];
    runStatus = `${dispatched.length} unit(s) being fixed` +
      (d.primed ? ` — ${unitTitle(d.primed)} first, alone, to warm the prompt cache` : '') + '.' +
      (unmapped ? ` ${unmapped} finding(s) name no unit — use "Fix Whole Script" for those.` : '') +
      // A structural finding is a design decision: never sent to a model, its reason shown.
      (structural.length ? ` ${structural.length} structural finding(s) need a design decision, not a fix: ${structural.join(' · ')}` : '') +
      // Findings about a unit edited since the review are not re-fixed.
      (stale.length ? ` ${stale.length} review finding(s) skipped — their unit changed since the review: ${stale.join(' · ')}` : '');
    if (!dispatched.length) return d;
    fixesUnlocked = false;
    await new Promise((resolve) => {
      onRunSettled = async () => {
        try { await afterFixUnitsSettled(); } finally { resolve(); }
      };
      startPolling();
    });
    return d;
  }

  async function afterFixUnitsSettled() {
    const s = await onRefreshStep6();
    const fu = s.fixUnits || {};
    review = s.review;
    const held = fu.held || [];
    const heldNote = held.length
      ? ` ${held.length} fix(es) are ready for confirmation (${held.map(unitTitle).join(', ')}) — open each orange unit and Confirm Unit to apply it. Regenerate any red units that did not get fixed.`
      : '';
    if (fu.error) {
      markNotAssembled(`Fix units: the units landed but re-assembly failed — ${fu.error}.${heldNote}`);
    } else if ((fu.failed || []).length) {
      runStatus = `Fix units: ${fu.failed.length} unit(s) failed (${fu.failed.map(unitTitle).join(', ')}) — re-run them individually.${heldNote}`;
    } else if (fu.assembled) {
      // Lint-only fixes are spliced straight in (D2) and the server re-assembled with them.
      markNotAssembled(`Fix units: ${(fu.applied || []).length} unit(s) re-generated.${heldNote}`);
    } else {
      runStatus = `Fix units:${heldNote || ' nothing came back to apply.'}`;
    }
  }

  // Confirm Unit on an orange (held) unit APPLIES its fix: the server splices it in and
  // re-assembles; the unit takes its new code and goes green, and the script is marked not
  // assembled so the user re-assembles once every unit is confirmed.
  let isApplyingUnit = false;

  async function confirmUnit() {
    const id = generateActiveUnitId;
    if (generateState[id]?.held) {
      isApplyingUnit = true;
      fixError = '';
      try {
        const d = await onApplyHeld([id]);
        const s = await onRefreshStep6();
        review = s.review;
        generateState[id].held = null;
        heldUnitIds = heldUnitIds.filter((x) => x !== id);
        await fetchLandedCode(id);   // the unit's code is now the applied fix
        markNotAssembled(`Applied the fix for ${unitTitle(id)}; lint ` +
          `${d.lint_ok ? 'ok' : `FAILED (${d.lint_errors} error(s))`}.`);
      } catch (e) {
        fixError = (e && e.message) || String(e);
        return;
      } finally {
        isApplyingUnit = false;
      }
    }
    advanceGenerateUnit();
  }

  // Re-chunk from script: the way out of "diverged". Once the assembled script has changed
  // outside an Assemble — a hand edit pushed by Re-lint / Review / a fix / Save — the server
  // refuses Assemble, Generate, Fix Units and applying fixes, because splicing the old units
  // would discard those edits. This re-cuts the units from the current script (local, no LLM);
  // units whose code changed turn orange for confirmation.
  let isRechunking = false;
  let rechunkError = '';

  async function rechunkFromScript() {
    isRechunking = true;
    rechunkError = '';
    try {
      const r = await onRechunk();
      await onRefreshStep6();   // the parent refreshes genState, which clears `diverged`
      const changed = (r.changed || []).filter((id) => generateState[id]);
      const dropped = r.dropped || [];
      await Promise.all(changed.map(fetchLandedCode));   // un-confirms them: orange
      runStatus = `Re-chunked from the script: ${changed.length} unit(s) took new code from it` +
        (changed.length ? ' and are now in review.' : '.') +
        (dropped.length ? ` ${dropped.length} unit(s) no longer exist in the script: ${dropped.map(unitTitle).join(', ')}.` : '');
    } catch (e) {
      rechunkError = (e && e.message) || String(e);
    } finally {
      isRechunking = false;
    }
  }

  // Confirm all: confirms every orange unit in one go — applying the held fixes among them
  // (one apply_held call), exactly as Confirm Unit would one unit at a time.
  let isConfirmingAll = false;

  async function confirmAll() {
    isConfirmingAll = true;
    fixError = '';
    try {
      const orange = generateUnits.filter((u) => generateUnitStatuses[u.id] === 'review').map((u) => u.id);
      const held = orange.filter((id) => heldUnitIds.includes(id));
      if (held.length) {
        const d = await onApplyHeld(held);
        const s = await onRefreshStep6();
        review = s.review;
        for (const id of held) generateState[id].held = null;
        heldUnitIds = heldUnitIds.filter((x) => !held.includes(x));
        await Promise.all(held.map(fetchLandedCode));   // the units' code is now the applied fixes
        markNotAssembled(`Applied ${held.length} fix(es); lint ` +
          `${d.lint_ok ? 'ok' : `FAILED (${d.lint_errors} error(s))`}.`);
      }
      // After the fetches — fetchLandedCode un-confirms the units it refreshes.
      confirmedGenerateUnits = [...new Set([...confirmedGenerateUnits, ...orange])];
    } catch (e) {
      fixError = (e && e.message) || String(e);
    } finally {
      isConfirmingAll = false;
    }
  }

  // The held fix itself (code, diff, scope) — units_status only says THAT a unit is held, so
  // each newly held unit's proposed code is fetched once, for its unit page.
  async function loadHeldFixes(ids) {
    for (const id of ids) {
      if (!generateState[id] || generateState[id].held) continue;
      try {
        const r = await onFetchUnitCode(id);
        generateState[id].held = r.held || null;
        generateState = generateState;
      } catch (e) {
        // Left unloaded — the next poll that sees this unit held tries again.
      }
    }
  }

  // --- Critical units: red arrow steps ------------------------------------------------
  // A unit's arrow step turns red when the current (non-stale) review has a HIGH-severity
  // finding about it. Which unit a finding is about COPIES the server's
  // _unit_id_for_finding / _unit_id_for_text (routers/pytest_create.py) — keep the two in
  // step if either changes. `where` is authoritative and resolved ALONE first (a `where` on
  // TestSet can only ever mean setup), then `evidence`, then the finding's sequence `step`.
  const TC_NAME_RX = /\bTestCase_(\d+)\b/;
  const SETUP_REF_RX = /\bTestSet\b|\bconfigure\(\)|\btear_down\(\)|\bTestSet\.(configure|tear_down)\b/;
  const LINE_REF_RX = /\bline (\d+)\b|:(\d+):/g;

  // Each unit's 1-based line range in the assembled script, for "line N" references. The
  // server reads these off the Python AST; this is an indentation-based approximation:
  // a TestCase_N runs from its `class` line to the next top-level statement, and setup spans
  // TestSet's configure()/tear_down() methods.
  function unitLineRanges(code) {
    const lines = (code || '').split('\n');
    const ranges = [];
    const isTopLevel = (l) => l.trim() !== '' && !/^\s/.test(l);
    const lastBefore = (i, lo) => { while (i > lo && lines[i - 1].trim() === '') i--; return i; };

    for (let i = 0; i < lines.length; i++) {
      const tc = /^class TestCase_(\d+)\b/.exec(lines[i]);
      if (tc) {
        let j = i + 1;
        while (j < lines.length && !isTopLevel(lines[j])) j++;
        ranges.push({ id: `tc${tc[1]}`, lo: i + 1, hi: lastBefore(j, i + 1) });
        continue;
      }
      if (/^class TestSet\b/.test(lines[i])) {
        let lo = null, hi = null;
        let j = i + 1;
        while (j < lines.length && !isTopLevel(lines[j])) {
          const m = /^(\s+)(async\s+)?def (configure|tear_down)\(/.exec(lines[j]);
          if (m) {
            const indent = m[1].length;
            let k = j + 1;
            while (k < lines.length && (lines[k].trim() === '' || /^\s*/.exec(lines[k])[0].length > indent)) k++;
            lo = lo === null ? j + 1 : Math.min(lo, j + 1);
            hi = Math.max(hi ?? 0, lastBefore(k, j + 1));
            j = k;
            continue;
          }
          j++;
        }
        if (lo !== null) ranges.push({ id: 'setup', lo, hi });
      }
    }
    return ranges;
  }

  function unitIdForText(text, ids, ranges) {
    text = text || '';
    const m = TC_NAME_RX.exec(text);
    if (m && ids.has(`tc${m[1]}`)) return `tc${m[1]}`;
    if (SETUP_REF_RX.test(text) && ids.has('setup')) return 'setup';
    for (const lm of text.matchAll(LINE_REF_RX)) {
      const ln = Number(lm[1] || lm[2]);
      const hit = ranges.find((r) => r.lo <= ln && ln <= r.hi);
      if (hit) return hit.id;
    }
    return null;
  }

  function unitIdForFinding(f, units, ids, ranges) {
    const where = String(f.where || '');
    if (/\bTestSet\b/.test(where) && ids.has('setup')) return 'setup';
    const fromWhere = unitIdForText(where, ids, ranges);
    if (fromWhere) return fromWhere;
    const fromEvidence = unitIdForText(String(f.evidence || ''), ids, ranges);
    if (fromEvidence) return fromEvidence;
    if (f.step == null) return null;
    // The unit whose sequence row is that step — step_prompts' source_n is the server's own
    // _unit_source_step(unit).n.
    return units.find((u) => u.source_n != null && String(u.source_n) === String(f.step))?.id ?? null;
  }

  $: criticalUnitIds = (() => {
    if (reviewStale) return new Set();   // a stale review describes old code
    const ids = new Set(generateUnits.map((u) => u.id));
    const ranges = unitLineRanges(assembledCode);
    return new Set(
      reviewFindings
        .filter((f) => f.severity === 'high')
        .map((f) => unitIdForFinding(f, generateUnits, ids, ranges))
        .filter(Boolean)
    );
  })();

  // Units a lint error names — routed with the same rule as the red units (the server's
  // _unit_id_for_text), which is also how the server sorts lint errors onto units. A lint
  // error that names no unit is a whole-file problem: Fix Whole Script's job.
  $: lintErrorUnitIds = (() => {
    const ids = new Set(generateUnits.map((u) => u.id));
    const ranges = unitLineRanges(assembledCode);
    return new Set(
      lintResults
        .filter((r) => r.level === 'error')
        .map((r) => unitIdForText(r.message, ids, ranges))
        .filter(Boolean)
    );
  })();

  // What Fix Units sends: the red units plus the units with lint errors. Lint-only fixes are
  // applied by the server straight away (they aren't held), so those units land with new code.
  $: fixUnitTargets = new Set([...criticalUnitIds, ...lintErrorUnitIds]);

  function goToReviewFix() {
    generateActiveUnitId = GENERATE_REVIEW_STEP_ID;
    scrollToSection('.step-intro');
  }

  // --- Review/Fix: save and finish ----------------------------------------------------
  let showSaveModal = false;
  let saveStatus = 'success';
  let saveStatusMessage = '';
  let isSaving = false;

  async function saveAndFinish() {
    isSaving = true;
    try {
      const result = await onSave(group.trim(), name.trim(), assembledCode);
      saveStatus = result.status;
      saveStatusMessage = result.message;
      showSaveModal = true;
      if (result.status === 'success') {
        onFinished && onFinished();
      }
    } finally {
      isSaving = false;
    }
  }

  function goToComposer() {
    showSaveModal = false;
    onNavigate && onNavigate('composer');
  }

  function createAnotherPytest() {
    showSaveModal = false;
    onCreateAnother && onCreateAnother();
  }
</script>

<p class="step-intro">Generated one unit at a time — a unit is a single TestCase class, or the TestSet setup pair. The frame (imports, TestSet, the ts.add_testCase() runner) is rendered here, not by an LLM, so it cannot vary between units. Page through the units: each shows the prompt that will be sent (editable — the button sends what you see) and the code that came back. Summary assembles them locally and lints the result; Review/Fix carries the script over for a final look before you save and finish.</p>

{#if isLoadingUnits}
  <p class="fragment-empty units-loading">Rendering unit prompts…</p>
{/if}
<ErrorBanner message={loadUnitsError && `Loading units failed: ${loadUnitsError}`} />

<div class="arrow-step-row">
  {#each generateUnits as unit (unit.id)}
    <ArrowStep
      label={unit.label}
      wide={unit.kind === 'setup'}
      status={generateUnitStatuses[unit.id] ?? 'none'}
      active={generateActiveUnitId === unit.id}
      loading={!!runningUnitIds[unit.id]}
      onClick={() => selectGenerateUnit(unit.id)}
    />
  {/each}
  {#if generateUnits.length > 0}
    <ArrowStep
      label="Summary"
      wide={true}
      status={generateSummaryStatus}
      active={generateActiveUnitId === GENERATE_SUMMARY_STEP_ID}
      onClick={() => selectGenerateUnit(GENERATE_SUMMARY_STEP_ID)}
    />
    <ArrowStep
      label="Review/Fix"
      wide={true}
      status={generateReviewStatus}
      active={generateActiveUnitId === GENERATE_REVIEW_STEP_ID}
      onClick={() => selectGenerateUnit(GENERATE_REVIEW_STEP_ID)}
    />
  {/if}
</div>

<div class="script-search-toolbar">
  <Button variant="primary" sparkle disabled={generateUnits.length === 0} loading={isDispatchingAll} on:click={generateAllUnits}>Generate All Units</Button>
  <div class="script-search-progress" role="progressbar" aria-valuenow={generateCoveragePercent} aria-valuemin="0" aria-valuemax="100">
    <div class="script-search-progress-fill" style="width: {generateCoveragePercent}%"></div>
  </div>
</div>
{#if runStatus}
  <p class="generate-run-status"><span style="font-weight: 400;"></span>{runStatus}</p>
{/if}
<ErrorBanner message={dispatchError && `Dispatch failed: ${dispatchError}`} />
{#snippet divergedNotice()}
  {#if genState?.diverged}
    <div class="diverged-notice">
      <p class="review-note">{genState.reason}</p>
      <div>
        <Button variant="primary" loading={isRechunking} on:click={rechunkFromScript}>Re-chunk from script</Button>
      </div>
      <ErrorBanner message={rechunkError && `Re-chunk failed: ${rechunkError}`} />
    </div>
  {/if}
{/snippet}

<div class="step-frame">
  {#if generateActiveUnitId === GENERATE_SUMMARY_STEP_ID}
    <p class="step-table-label summary-title">Sequence Step Summary</p>
    <div class="summary-box">
      <div class="summary-counts">
        <p class="sequence-step-summary">
          <StatusBadge status="covered" />
          <span><strong>{summaryCounts.covered}</strong> Confirmed</span>
        </p>
        <p class="sequence-step-summary">
          <StatusBadge status="review" />
          <span><strong>{summaryCounts.review}</strong> In Review</span>
        </p>
        <p class="sequence-step-summary">
          <StatusBadge status="none" />
          <span><strong>{summaryCounts.none}</strong> Not started</span>
        </p>
        {#if summaryCounts.error}
          <p class="sequence-step-summary">
            <StatusBadge status="error" />
            <span><strong>{summaryCounts.error}</strong> Critical</span>
          </p>
        {/if}
      </div>

    </div>
      <div>
        <div class="step-summary-actions">
          <Button
            variant="primary"
            disabled={summaryCounts.review === 0 || Object.keys(runningUnitIds).length > 0}
            loading={isConfirmingAll}
            on:click={confirmAll}
          >Confirm all</Button>
          <Button variant="primary" disabled={generateSummaryStatus !== 'covered'} loading={isAssembling} on:click={assembleAndLint}>Assemble &amp; Lint</Button>
        </div>
      </div>

    {@render divergedNotice()}


    <ErrorBanner message={fixError && `Confirm all failed: ${fixError}`} />

    <ErrorBanner message={assembleError && `Assemble failed: ${assembleError}`} />



    <p class="step-table-label assembled-script-label">Assembled Script</p>
    <div class="generate-assembled-editor">
      <EditableField
        type="code"
        bind:value={assembledCode}
        placeholder={'Not assembled yet. Click "Assemble & Lint" above.'}
        height="700px"
      />
    </div>

    {#if assembled}
      <p class="step-table-label">Lint Results</p>
      <ul class="lint-results">
        {#each lintResults as result}
          <li class="lint-result" class:lint-pass={result.level === 'pass'} class:lint-warn={result.level === 'warn'} class:lint-error={result.level === 'error'}>{result.message}</li>
        {:else}
          <!-- No errors and no warnings — say so, or a clean lint looks like nothing happened. -->
          <li class="lint-result lint-pass">✓ Lint clean — no errors or warnings.</li>
        {/each}
      </ul>
      <ErrorBanner message={relintError && `Re-lint failed: ${relintError}`} />
      <div class="step-actions relint-row">
        <Button variant="outline" loading={isRelinting} on:click={relint}>Re-lint</Button>
      </div>
    {/if}

    <div class="step-actions">
      <Button variant="primary" disabled={!assembled} on:click={goToReviewFix}>Continue to Review/Fix</Button>
    </div>
  {:else if generateActiveUnitId === GENERATE_REVIEW_STEP_ID}
    <div class="review-fix-grid">
      <div class="script-section">
        <p class="step-table-label">Assembled Script</p>
        <div class="generate-assembled-editor">
          <EditableField
            type="code"
            bind:value={assembledCode}
            placeholder={'Not assembled yet. Assemble & Lint on the Summary step first.'}
            height="650px"
          />
        </div>
      </div>
      <div class="review-section">
        <p class="step-table-label">Script Review</p>
        {#if assembled}
          <div class="step-actions review-fix-row review-button">
            <LlmButton label="Review with LLM" verb="Reviewing…" title={reviewButtonTitle} onRun={runReview} onResult={handleReviewResult} />
          </div>
        {/if}
        <ReviewFindings {review} stale={reviewStale} code={assembledCode} />
      </div>
    </div>
   
    {@render divergedNotice()}

    {#if assembled}
      <p class="step-table-label">Fix Scripts From LLM Review</p>
      <div class="step-actions review-fix-row">
        <LlmButton
          label="Fix Whole Script"
          verb="Fixing…"
          disabled={!fixesAvailable}
          title={fixesAvailable ? '' : FIX_LOCKED_HINT}
          onRun={runFixScript}
        />
        <LlmButton
          label="Fix Units"
          verb="Fixing units…"
          disabled={!fixesAvailable || fixUnitTargets.size === 0 || Object.keys(runningUnitIds).length > 0}
          title={!fixesAvailable
            ? FIX_LOCKED_HINT
            : fixUnitTargets.size === 0
              ? 'No unit to fix — no red units, and no lint error names a unit (use Fix Whole Script for whole-file errors)'
              : ''}
          onRun={runFixUnits}
        />
      </div>
    {/if}
    <p class="step-table-label">Script Naming</p>
    <div class="naming-fields">
      <label class="naming-field">
        <span>Group</span>
        <input class="step-field" bind:value={group} on:blur={saveNaming} placeholder="e.g. AMF_Cluster" />
      </label>
      <label class="naming-field">
        <span>Script name</span>
        <input class="step-field" bind:value={name} on:blur={saveNaming} placeholder="e.g. test_amf_master" />
      </label>
    </div>
    <div class="step-actions">
      <Button variant="success" disabled={!assembled} loading={isSaving} on:click={saveAndFinish}>Save and Finish</Button>
    </div>
    <ErrorBanner message={fixError && `Fix failed: ${fixError}`} />

    <ConfirmModal
      bind:open={showReviewCapModal}
      title="Review round cap"
      message={reviewCapMessage}
      confirmText="Send another round"
      cancelText="Cancel"
      onConfirm={() => answerReviewCap(true)}
      onCancel={() => answerReviewCap(false)}
    />

    <StatusModal
      bind:open={showSaveModal}
      status={saveStatus}
      title={saveStatus === 'success' ? 'Script saved successfully' : 'Save failed'}
      message={saveStatusMessage}
      caseTitle={caseTitle}
      closeText="Close"
    >
      <svelte:fragment slot="actions">
        <Button variant="outline" on:click={createAnotherPytest}>Create Another PyTest</Button>
        <Button variant="outline" on:click={goToComposer}>Compose Test</Button>
      </svelte:fragment>
    </StatusModal>
  {:else if generateActiveUnit}
    <div class="sequence-step-summary">
      <StatusBadge status={generateUnitStatuses[generateActiveUnit.id] ?? 'none'} />
      <p><strong>{generateActiveUnit.title}</strong> - {generateActiveUnit.detail}</p>
    </div>
    <div class="step-generate">
      <Button variant="primary" sparkle loading={!!runningUnitIds[generateActiveUnitId]} on:click={() => generateUnitCode(generateActiveUnitId)}>Generate Unit</Button>
    </div>
    <ErrorBanner message={generateState[generateActiveUnitId].error && `Last generation failed: ${generateState[generateActiveUnitId].error}`} />

    {#if heldUnitIds.includes(generateActiveUnitId)}
      <ErrorBanner message={fixError && `Applying the fix failed: ${fixError}`} />
    {/if}

    <div class="generate-panes">
      <div class="generate-pane generate-pane-prompt">
        <p class="step-table-label">Prompt — editable, sent as shown</p>
        {#key generateActiveUnitId}
          <EditableField type="text" bind:value={generateState[generateActiveUnitId].prompt} />
        {/key}
      </div>
      <div class="generate-pane generate-pane-code">
        {#if heldUnitIds.includes(generateActiveUnitId)}
          <!-- A held fix: shown in place of the current code, read-only — Confirm Unit applies
               the server's stored fix, so an edit made here would not be what gets applied. -->
          <p class="step-table-label">Generated Code — proposed fix, read-only until Confirm Unit applies it</p>
          {#if generateState[generateActiveUnitId].held}
            <div class="held-fix-code">
              <CodeEditor value={generateState[generateActiveUnitId].held.code} readonly height="45vh" />
            </div>
          {:else}
            <p class="review-note">Loading the proposed fix…</p>
          {/if}
        {:else}
          <p class="step-table-label">Generated Code</p>
          {#key generateActiveUnitId}
            <EditableField
              type="code"
              bind:value={generateState[generateActiveUnitId].code}
              placeholder={'Not generated yet. Click the "Generate Unit" button above.'}
            />
          {/key}
        {/if}
      </div>
    </div>

    <div class="step-actions">
      <Button variant="primary" disabled={!generateState[generateActiveUnitId].code} loading={isApplyingUnit} on:click={confirmUnit}>Confirm Unit</Button>
    </div>
  {/if}
</div>

<style>
  .step-intro {
    margin: 0 0 24px;
    color: var(--color-text-muted);
    font-size: 0.94rem;
  }

  .step-table-label {
    margin: 0 0 8px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--color-text-muted);
  }

  .naming-fields {
    display: flex;
    gap: 16px;
    margin: 10px 0 20px;
  }

  .naming-field {
    display: flex;
    flex-direction: column;
    gap: 6px;
    flex: 1;
    font-size: 0.8rem;
    color: var(--color-text-muted);
  }

  .step-field {
    width: 100%;
    padding: 8px 10px;
    border-radius: 6px;
    border: 1px solid var(--color-border-surface);
    background: var(--color-bg-content);
    color: var(--color-text);
    font: inherit;
    font-size: 0.9rem;
  }

  .units-loading {
    margin-bottom: 16px;
  }

  .generate-run-status {
    margin: -12px 0 20px;
    color: var(--color-text-muted);
    font-size: 0.85rem;
    font-style: italic;
  }

  .summary-title {
    margin-bottom: 12px;
  }

  .step-actions {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 16px 0 32px;
  }

  .step-summary-actions {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 0px 0px 24px 0px;

  }

  /* Review with LLM, then the two fixes, stacked tight above Save and Finish. */
  .relint-row {
    margin: 0 0 16px;
  }

  .review-fix-row {
    margin: 12px 0 24px;
  }

  .arrow-step-row {
    display: flex;
    flex-wrap: wrap;
    width: 100%;
    gap: 0px 14px;
    padding: 8px 10px 8px 10px;
    border-top: 1px solid var(--color-border-surface);
    border-bottom: 1px solid var(--color-border-surface);
    margin-bottom: 16px;
  }

  .script-search-toolbar {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 24px;
  }

  .script-search-progress {
    flex: 1;
    height: 8px;
    border-radius: 999px;
    background: var(--color-border-surface);
    overflow: hidden;
  }

  .script-search-progress-fill {
    height: 100%;
    background: var(--color-success);
    transition: width 0.2s ease;
  }

  .step-frame {
    border: 1px solid var(--color-border-surface);
    border-radius: 8px;
    padding: 24px 24px 0px 24px;
    width: 100%;
  }

  .sequence-step-summary {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 10px;
  }

  .sequence-step-summary p {
    margin: 0;
    color: var(--color-text);
    font-size: 0.94rem;
  }

  .summary-box {
    border-radius: 10px;
    background-color: var(--color-bg-surface);
    border: 1px solid var(--color-border-surface);
    padding-left: 10px;
    margin-bottom: 16px;
  }
  .summary-counts {
    display: flex;
    flex-direction: row;
    margin: 0;
    gap: 24px;
    font-size: 0.94rem;
  }

  .step-generate {
    padding-bottom: 20px;
  }

  /* .script-summary {
    display: flex;
    flex-direction: column;
    gap: 24px;
    width: 100%;
  } */

  .fragment-empty {
    margin: 0;
    color: var(--color-text-muted);
    font-size: 0.94rem;
  }

  .generate-panes {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    width: 100%;
    margin-bottom: 8px;
  }

  .generate-pane {
    min-width: 0;
  }

  .generate-pane-prompt {
    flex: 1 1 0;
  }

  .generate-pane-code {
    flex: 2 1 0;
  }

  .generate-assembled-editor {
    margin: 0 0 24px;
  }

  .lint-results {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin: 0 0 24px;
    padding-left: 20px;
  }

  .lint-result {
    font-size: 0.9rem;
  }

  .lint-pass {
    color: var(--color-success);
  }

  .lint-warn {
    color: var(--color-warning);
  }

  /* The orange edge marks a proposed (held) fix; the code itself is a read-only CodeMirror. */
  .held-fix-code {
    margin: 0 0 20px;
    border: 3px solid var(--color-arrow-step-review-border);
    border-radius: 12px;
  }

  .diverged-notice {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin: 0 0 20px;
    padding: 12px 14px;
    border-left: 3px solid var(--color-warning);
    border-radius: 6px;
    background: var(--color-bg-surface);
  }

  .review-note {
    margin: 0;
    color: var(--color-text-muted);
    font-size: 0.85rem;
  }

  .lint-error {
    color: var(--color-error);
    font-weight: 600;
  }

  .review-button {
    margin-bottom: 1rem;
  }

  .review-fix-grid {
    display: flex;
    flex: 1;
  }
  .script-section {
    width: 60%;
    margin-right: 20px;
  }

  .review-section {
    width: 40%
  }
</style>
