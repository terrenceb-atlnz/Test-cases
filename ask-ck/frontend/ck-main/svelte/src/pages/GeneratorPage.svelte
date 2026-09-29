<script>
// @ts-nocheck

  import { tick, onMount } from 'svelte';
  import ToolHeader from '../lib/components/ToolHeader.svelte';
  import Stepper from '../lib/components/Stepper.svelte';
  import CasePicker from '../lib/components/CasePicker.svelte';
  import CandidatePickerStep from '../lib/components/generator/CandidatePickerStep.svelte';
  import ObjectivesStep from '../lib/components/generator/ObjectivesStep.svelte';
  import TestStepsStep from '../lib/components/generator/TestStepsStep.svelte';

  import * as casesService from '../lib/services/generator/casesService.js';
  import * as testlinkService from '../lib/services/generator/testlinkService.js';
  import * as zephyrService from '../lib/services/generator/zephyrService.js';
  import * as atpylibService from '../lib/services/generator/atpylibService.js';
  import * as objectivesService from '../lib/services/generator/objectivesService.js';
  import * as testStepsService from '../lib/services/generator/testStepsService.js';

  import briefcaseIcon from '../assets/icons/briefcase.svg';
  import testTubeIcon from '../assets/icons/test-tube-diagonal.svg';
  import linkIcon from '../assets/icons/link.svg';
  import libraryIcon from '../assets/icons/library.svg';
  import targetIcon from '../assets/icons/target.svg';
  import footprintsIcon from '../assets/icons/footprints.svg';
  import generatorIcon from '../assets/icons/clipboard-list.svg';

  /** @type {((caseId?: string | null) => void) | null} Remounts this whole Objective Generator
      session from scratch — used here to switch cleanly into a different case without leaking any
      of this instance's state into it */
  export let onCreateAnother = null;

  /** @type {string | null} Case id to auto-load on mount (set when this instance was remounted
      specifically to switch cases, via `onCreateAnother(caseId)`) */
  export let initialCaseId = null;

  const steps = [
    { id: 'cases', label: 'Cases', icon: briefcaseIcon },
    { id: 'testlink', label: 'TestLink', icon: testTubeIcon },
    { id: 'zephyr', label: 'Zephyr', icon: linkIcon },
    { id: 'atpylib', label: 'ATPyLib', icon: libraryIcon },
    { id: 'objectives', label: 'Objectives', icon: targetIcon },
    { id: 'test-steps', label: 'Test Steps', icon: footprintsIcon }
  ];

  let currentStep = 0;
  let maxStepReached = 0;
  let stepperCompleted = false;

  $: if (currentStep > maxStepReached) maxStepReached = currentStep;

  function goToStep(index) {
    currentStep = index;
  }

  // Real /cases is an async fetch (casesService.js), where the mock was a plain synchronous
  // array — populated on mount instead of at module scope.
  let openPartialCases = [];
  let completeCases = [];
  let openPartialGroups = [];
  let completeGroups = [];

  let title = 'No case loaded. Please select a test case to work on.';

  // The server-authoritative session (models.WizardSession) — every mutating wizard call
  // returns the FULL new session, which replaces this wholesale. Downstream steps (Phase 2+)
  // read from this rather than tracking their own copy of what the server knows.
  let session = null;
  let readOnly = false;
  let lockMessage = '';

  async function loadAndConfirm(caseId) {
    // maxStepReached > 0 means a case was already loaded and progressed past Cases in this
    // instance — switching to a different one now would leave every downstream field (TestLink/
    // Zephyr/ATPyLib picks, objectives, test steps) still holding the old case's data. Rather than
    // manually resetting each of those, remount the whole page fresh with the new case id.
    if (maxStepReached > 0) {
      onCreateAnother && onCreateAnother(caseId);
      return;
    }

    const loadedCase = await casesService.findCase(caseId);
    if (loadedCase) {
      title = loadedCase.label;
    }

    // The real load: acquires this case's per-tab edit lock server-side (or, if another tab
    // already holds it, returns a read-only snapshot instead — see loadCase's own comment).
    const result = await casesService.loadCase(caseId);
    if (!result.session) {
      title = `Failed to load ${caseId}.`;
      return;
    }
    session = result.session;
    readOnly = !!result.read_only;
    lockMessage = result.message || '';
    if (result.case_title) title = result.case_title;

    currentStep = 1;
  }

  // A fresh instance remounted specifically to switch cases (onCreateAnother(caseId)) loads that
  // case immediately instead of landing back on the blank Cases picker. Deferred to onMount —
  // calling this during the component's own initialization (before every other `let`/`$:` below
  // it in this file has finished setting up) trips Svelte's reactivity scheduler into running a
  // reactive block against a not-yet-initialized variable, throwing a temporal-dead-zone error.
  onMount(async () => {
    [openPartialCases, completeCases, openPartialGroups, completeGroups] = await Promise.all([
      casesService.listOpenPartialCases(),
      casesService.listCompleteCases(),
      casesService.listOpenPartialGroups(),
      casesService.listCompleteGroups(),
    ]);
    if (initialCaseId) {
      loadAndConfirm(initialCaseId);
    }
  });

  function exportSession() {
    casesService.exportSession();
  }

  // Waits for Svelte to flush the DOM update (the {:else if currentStep === N} swap) before
  // scrolling — otherwise this can run while the old, taller content is still on screen, and the
  // subsequent layout shift from the swap interrupts or swallows the smooth-scroll animation.
  async function scrollToTop() {
    await tick();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  const testLinkColumns = [
    { key: 'id', label: 'ID', width: 1 },
    { key: 'title', label: 'Title', width: 5 },
    { key: 'score', label: 'Score', width: 1 },
    { key: 'description', label: 'Description', width: 4 }
  ];

  const summaryColumns = [...testLinkColumns, { key: 'source', label: 'Source', width: 1 }];

  let testLinkChosen = [];
  let zephyrChosen = [];
  let atpylibChosen = [];

  $: summaryRows = [
    ...testLinkChosen.map((c) => ({ ...c, source: 'TestLink' })),
    ...zephyrChosen.map((c) => ({ ...c, source: 'Zephyr' })),
    ...atpylibChosen.map((c) => ({ ...c, source: 'ATPyLib' }))
  ];
  $: chosenForObjectives = [...testLinkChosen, ...zephyrChosen, ...atpylibChosen];

  let objectives = [];
</script>

<ToolHeader title={title} tool="OBJECTIVE GENERATOR" icon={generatorIcon} />

<Stepper {steps} {currentStep} {maxStepReached} {stepperCompleted} onStepClick={goToStep} />

{#if readOnly}
  <p class="read-only-banner">{lockMessage}</p>
{/if}

<div class="tool-page">
  {#if currentStep === 0}
    <CasePicker {openPartialCases} {completeCases} {openPartialGroups} {completeGroups} selectedCaseId={session?.key} onLoad={loadAndConfirm} onExport={exportSession} />
  {:else if currentStep === 1}
    <CandidatePickerStep
      columns={testLinkColumns}
      introText="Review primary decision and TestLink candidates. Search or ask the LLM to suggest, then confirm selections."
      searchPlaceholder="Search TestLink by ID or title…"
      searchButtonLabel="Search TestLink"
      candidateLabel="TestLink Candidates"
      chosenLabel="Chosen TestLink Cases"
      onSearch={testlinkService.searchTestLink}
      onSuggest={() => testlinkService.suggestTestLink(session.key)}
      bind:chosen={testLinkChosen}
      onConfirm={() => { currentStep = 2; scrollToTop(); }}
    />
  {:else if currentStep === 2}
    <CandidatePickerStep
      columns={testLinkColumns}
      introText="Review relevance-ranked external Zephyr cases (current Cases list omitted). Search or suggest more, then confirm."
      searchPlaceholder="Search Zephyr by ID or title…"
      searchButtonLabel="Search Zephyr"
      candidateLabel="Zephyr Candidates"
      chosenLabel="Chosen Zephyr Cases"
      onSearch={zephyrService.searchZephyr}
      onSuggest={zephyrService.suggestZephyr}
      bind:chosen={zephyrChosen}
      onConfirm={() => { currentStep = 3; scrollToTop(); }}
    />
  {:else if currentStep === 3}
    <CandidatePickerStep
      columns={testLinkColumns}
      introText="Review scored ATPyLib candidates (LLM + keyword). Optionally search or re-suggest, then select relevant tests. Coverage gaps are generated by the LLM at synthesis/export for Traceability — not edited here."
      searchPlaceholder="Search ATPyLib by ID or title…"
      searchButtonLabel="Search ATPyLib"
      candidateLabel="ATPyLib Candidates"
      chosenLabel="Chosen ATPyLib Tests"
      onSearch={atpylibService.searchAtpylib}
      onSuggest={atpylibService.suggestAtpylib}
      bind:chosen={atpylibChosen}
      onConfirm={() => { currentStep = 4; scrollToTop(); }}
    />
  {:else if currentStep === 4}
    <ObjectivesStep
      {summaryColumns}
      {summaryRows}
      {chosenForObjectives}
      onSynthesize={objectivesService.synthesizeObjectives}
      bind:objectives
      onConfirm={() => { currentStep = 5; scrollToTop(); }}
    />
  {:else if currentStep === 5}
    <TestStepsStep
      {objectives}
      onSynthesize={testStepsService.synthesizeTestSteps}
      onExport={testStepsService.exportRepeatableBundle}
      onFinished={() => (stepperCompleted = true)}
    />
  {:else}
    <p>Hello world</p>
  {/if}
</div>

<style>
  .read-only-banner {
    margin: 16px 0 0;
    padding: 10px 14px;
    border-radius: 8px;
    font-size: 0.9rem;
    line-height: 1.5;
    background: color-mix(in srgb, var(--color-warning) 12%, transparent);
    color: var(--color-warning);
  }
</style>

