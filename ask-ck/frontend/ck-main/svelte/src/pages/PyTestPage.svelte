<script>
// @ts-nocheck

  import { onMount, onDestroy } from 'svelte';
  import { scrollToTop } from '../lib/utils/scroll.js';
  import ToolHeader from '../lib/components/ToolHeader.svelte';
  import Stepper from '../lib/components/Stepper.svelte';
  import CasePicker from '../lib/components/CasePicker.svelte';
  import Button from '../lib/components/Button.svelte';
  import SequenceStep from '../lib/components/pytest/SequenceStep.svelte';
  import ScriptSearchStep from '../lib/components/pytest/ScriptSearchStep.svelte';
  import FragmentsStep from '../lib/components/pytest/FragmentsStep.svelte';
  import GenerateStep from '../lib/components/pytest/GenerateStep.svelte';
  import UnderConstruction from '../lib/components/UnderConstruction.svelte';

  import * as casesService from '../lib/services/pytest/casesService.js';
  import * as sequenceService from '../lib/services/pytest/sequenceService.js';
  import * as scriptSearchService from '../lib/services/pytest/scriptSearchService.js';
  import * as fragmentsService from '../lib/services/pytest/fragmentsService.js';
  import * as generateService from '../lib/services/pytest/generateService.js';
  import * as lockService from '../lib/services/lockService.js';

  /** @type {((pageId: string) => void) | null} */
  export let onNavigate = null;

  /** @type {((caseId?: string | null) => void) | null} Remounts this whole PyTest Creator
      session from scratch — with no case id for "Create Another PyTest", or with one to switch
      straight into a different case without leaking any of this instance's state into it */
  export let onCreateAnother = null;

  /** @type {string | null} Case id to auto-load on mount (set when this instance was remounted
      specifically to switch cases, via `onCreateAnother(caseId)`) */
  export let initialCaseId = null;

  import briefcaseIcon from '../assets/icons/briefcase.svg';
  import listSortIcon from '../assets/icons/list-sort-descending.svg';
  import folderSearchIcon from '../assets/icons/folder-search.svg';
  import puzzleIcon from '../assets/icons/puzzle.svg';
  import codeIcon from '../assets/icons/code.svg';
  import checkIcon from '../assets/icons/circle-check-big.svg';
  import pyTestIcon from '../assets/icons/pytest.svg';

  const steps = [
    { id: 'cases', label: 'Cases', icon: briefcaseIcon },
    { id: 'sequence', label: 'Sequence', icon: listSortIcon },
    { id: 'script-search', label: 'Script Search', icon: folderSearchIcon },
    { id: 'fragments', label: 'Fragments', icon: puzzleIcon },
    { id: 'generate', label: 'Generate', icon: codeIcon }
    // { id: 'validate', label: 'Validate', icon: checkIcon }
  ];

  let currentStep = 0;
  let maxStepReached = 0;
  let stepperCompleted = false;

  $: if (currentStep > maxStepReached) maxStepReached = currentStep;

  function goToStep(index) {
    currentStep = index;
  }

  // Real /pt_cases is grouped-only — no flat list, so CasePicker gets empty flat arrays
  // and renders purely from the groups (its own fallback behavior when groups are present).
  let openPartialGroups = [];
  let completeGroups = [];

  let title = 'No case loaded. Please select a test case to work on.';

  // The server-authoritative PtSession — every mutating call (extract/save_sequence,
  // confirm_step) returns or implies a new one; re-fetched via casesService.getSession
  // after calls that don't return it directly (extract_sequence/save_sequence return
  // {sequence,...} only, not {session}).
  let session = null;
  let readOnly = false;
  let lockMessage = '';
  let lockInfo = null;
  let stopLockLifecycle = null;

  // load_case exposes the refined case's objective/steps directly on the response (NOT
  // nested in session — PyTest Creator only reads them, the Generator owns writing them).
  let caseInfo = null;

  async function loadAndConfirm(caseId) {
    // maxStepReached > 0 means a case was already loaded and progressed past Cases in this
    // instance — switching to a different one now would leave every downstream field (sequence,
    // script search, fragments, generate, ...) still holding the old case's data. Rather than
    // manually resetting each of those, remount the whole page fresh with the new case id.
    if (maxStepReached > 0) {
      // Deliberately abandoning this case for another — release its lock explicitly rather
      // than letting it idle out (matches current/'s onCaseLoaded: "switching cases: drop
      // the lock we held on the previous case so others aren't kept waiting for it to idle
      // out"). Must come before stopping the heartbeat so the two can't race.
      if (stopLockLifecycle) { stopLockLifecycle(); stopLockLifecycle = null; }
      if (session?.key && !readOnly) lockService.releaseLock('pt', session.key);
      onCreateAnother && onCreateAnother(caseId);
      return;
    }

    const result = await casesService.loadCase(caseId);
    if (!result.session) {
      title = `Failed to load ${caseId}.`;
      return;
    }
    session = result.session;
    readOnly = !!result.read_only;
    lockInfo = result.lock || null;
    lockMessage = readOnly ? lockService.formatLockMessage('pt', caseId, lockInfo) : '';
    caseInfo = { title: result.case_title, groupDisplay: result.group_display,
                 objective: result.objective, steps: result.steps || [] };
    if (result.case_title) title = result.case_title;

    // Only a real editor heartbeats/arms release — a read-only viewer holds no lock to
    // keep alive.
    if (!readOnly) stopLockLifecycle = lockService.startLockLifecycle('pt', session.key);

    // The real app always lands on Sequence after a non-read-only load, regardless of how
    // far along the session already is — it has no per-step "resume" logic the way the
    // Generator does.
    if (!readOnly) currentStep = 1;
  }

  // Unlike the Generator, this page is destroyed/recreated on every navigation away (it's
  // not kept alive in App.svelte) — so this fires far more often than a deliberate case
  // switch, e.g. just clicking over to Settings for a moment. Only stop the heartbeat/
  // pagehide listener here, never release: the lock simply idles out after 15 min if the
  // user genuinely doesn't come back, instead of being given up the instant they look away.
  onDestroy(() => {
    if (stopLockLifecycle) stopLockLifecycle();
  });

  async function handleTakeOver() {
    if (!session?.key) return;
    const state = await lockService.acquireLock('pt', session.key);
    if (state && state.by_me) {
      onCreateAnother && onCreateAnother(session.key);
    } else {
      lockInfo = state;
      lockMessage = lockService.formatLockMessage('pt', session.key, lockInfo);
    }
  }

  // A fresh instance remounted specifically to switch cases (onCreateAnother(caseId)) loads that
  // case immediately instead of landing back on the blank Cases picker. Deferred to onMount —
  // calling this during the component's own initialization (before every other `let`/`$:` below
  // it in this file has finished setting up) trips Svelte's reactivity scheduler into running a
  // reactive block against a not-yet-initialized variable, throwing a temporal-dead-zone error.
  onMount(async () => {
    [openPartialGroups, completeGroups] = await Promise.all([
      casesService.listOpenPartialGroups(),
      casesService.listCompleteGroups(),
    ]);
    if (initialCaseId) {
      loadAndConfirm(initialCaseId);
    }
  });

  $: sequencedTestSteps = session?.step2?.sequence || [];

</script>

<ToolHeader title={title} tool="PYTEST CREATOR" icon={pyTestIcon} />

<Stepper {steps} {currentStep} {maxStepReached} {stepperCompleted} onStepClick={goToStep} />

{#if readOnly}
  <p class="read-only-banner">
    {lockMessage}
    {#if lockInfo?.stealable}
      <Button variant="outline" on:click={handleTakeOver}>Take over</Button>
    {/if}
  </p>
{/if}

<div class="tool-page">
  {#if currentStep === 0}
    <CasePicker
      {openPartialGroups}
      {completeGroups}
      selectedCaseId={session?.key}
      onLoad={loadAndConfirm}
      onExport={casesService.exportSession}
    />
  {:else}
  <!-- Only steps 1-4 become read-only when another tab/user holds the lock — Cases stays
       usable so a viewer can still switch to a different, unlocked case. A native
       <fieldset disabled> propagates to every real control nested inside, including ones
       inside child components. -->
  <fieldset class="tool-fieldset" disabled={readOnly}>
  {#if currentStep === 1}
    <SequenceStep
      refinedSteps={caseInfo?.steps || []}
      sequence={session?.step2?.sequence || []}
      onSynthesize={async (headers) => {
        const result = await sequenceService.extractSequence(session.key, headers);
        const sessResult = await casesService.getSession(session.key);
        session = sessResult.session;
        return result;
      }}
      onSaveEdits={async (seq) => {
        await sequenceService.saveSequence(session.key, seq);
        const sessResult = await casesService.getSession(session.key);
        session = sessResult.session;
      }}
      onConfirm={async () => {
        const result = await sequenceService.confirmStep(session.key, 2);
        session = result.session;
        currentStep = 2;
        scrollToTop();
      }}
    />
  {:else if currentStep === 2}
    <ScriptSearchStep
      {sequencedTestSteps}
      columns={scriptSearchService.scriptColumns}
      onSuggestForStep={(stepN, headers) => scriptSearchService.suggestStep(session.key, stepN, headers)}
      onSearch={scriptSearchService.searchScripts}
      onViewSource={scriptSearchService.getScriptSource}
      onConfirm={async () => {
        const result = await sequenceService.confirmStep(session.key, 3);
        session = result.session;
        currentStep = 3;
        scrollToTop();
      }}      onSaveMatches={async (selections, records) => {
        await scriptSearchService.saveMatches(session.key, selections, records);
      }}
    />                            
  {:else if currentStep === 3}
    <FragmentsStep
      {sequencedTestSteps}
      onGatherFragments={fragmentsService.gatherFragments}
      onConfirm={() => { currentStep = 4; scrollToTop(); }}
    />
  {:else if currentStep === 4}
    <GenerateStep
      {sequencedTestSteps}
      {title}
      onGenerateUnit={generateService.generateUnitCode}
      onGenerateAllUnits={generateService.generateAllUnits}
      onAssemble={generateService.assembleScript}
      onReview={generateService.reviewScript}
      onFixUnits={generateService.fixUnitsWithLlm}
      onFixWholeScript={generateService.fixWholeScriptWithLlm}
      onSave={generateService.saveScript}
      {onNavigate}
      {onCreateAnother}
      onFinished={() => (stepperCompleted = true)}
    />
  {:else}
    <UnderConstruction />
  {/if}
  </fieldset>
  {/if}
</div>

<style>
  .read-only-banner {
    margin: 16px 80px 0;
    padding: 10px 14px;
    border-radius: 8px;
    font-size: 0.9rem;
    line-height: 1.5;
    background: color-mix(in srgb, var(--color-warning) 12%, transparent);
    color: var(--color-warning);
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .tool-fieldset {
    border: none;
    margin: 0;
    padding: 0;
    min-width: 0;
  }
</style>
