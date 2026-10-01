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
  import { restoreChosen } from '../lib/services/generator/chosenService.js';
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

  // Lazy per-step candidate fetch (GET step_candidates/{key}/{step}) the first time a step
  // opens for this case — mirrors current/generator/generator.js's `_stepFetched` memo. Only
  // one case can ever be active in a given GeneratorPage instance (switching cases remounts
  // the whole page — see onCreateAnother), so a single "already fetched for this key" flag
  // per step is enough; no need for the original's {key}:{step} composite.
  // Restoring session.step1.selections happens in the SAME fetch, right after — enrichment
  // (pulling in a restored pick's full score/description) needs the candidate pool to have
  // landed first, matching current/generator/chosen.js's restoreChosenFromSelections.
  let testLinkCandidates = [];
  let fetchedTestLinkFor = null;
  $: if (currentStep === 1 && session?.key && fetchedTestLinkFor !== session.key) {
    fetchedTestLinkFor = session.key;
    testlinkService.fetchStepCandidates(session.key).then((c) => {
      testLinkCandidates = c;
      testLinkChosen = restoreChosen(session.step1?.selections, c);
    });
  }

  let zephyrCandidates = [];
  let fetchedZephyrFor = null;
  $: if (currentStep === 2 && session?.key && fetchedZephyrFor !== session.key) {
    fetchedZephyrFor = session.key;
    zephyrService.fetchStepCandidates(session.key).then((c) => {
      zephyrCandidates = c;
      zephyrChosen = restoreChosen(session.step2?.selections, c);
    });
  }

  let atpylibCandidates = [];
  let fetchedAtpylibFor = null;
  $: if (currentStep === 3 && session?.key && fetchedAtpylibFor !== session.key) {
    fetchedAtpylibFor = session.key;
    atpylibService.fetchStepCandidates(session.key).then((c) => {
      atpylibCandidates = c;
      atpylibChosen = restoreChosen(session.step3?.selections, c);
    });
  }

  // A saved session's chosen tables and stepper position must both reflect real progress —
  // resuming always lands on the first NOT-yet-confirmed step (steps 1-3 gate on their own
  // `confirmed`; step 5 has no confirm step of its own, so step4.confirmed is the last gate).
  function resumeStep(sess) {
    if (!sess?.step1?.confirmed) return 1;
    if (!sess?.step2?.confirmed) return 2;
    if (!sess?.step3?.confirmed) return 3;
    if (!sess?.step4?.confirmed) return 4;
    return 5;
  }

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

    // Populate every chosen table immediately, from the saved selections alone — landing
    // straight on, say, step 4 must not leave step1-3's chosen tables (and therefore the
    // Objectives summary/count) empty just because the user never visited those steps in
    // THIS page load. restoreChosen's own fallback (id/title/justification from the
    // selection itself) is good enough here; the per-step lazy-fetch blocks below still
    // upgrade these to fully-enriched rows the first time the user actually opens that step.
    testLinkChosen = restoreChosen(session.step1?.selections, []);
    zephyrChosen = restoreChosen(session.step2?.selections, []);
    atpylibChosen = restoreChosen(session.step3?.selections, []);

    currentStep = resumeStep(session);
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
    { key: 'title', label: 'Title', width: 2 },
    { key: 'score', label: 'Score', width: 1 },
    { key: 'description', label: 'Description', width: 7 }
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

  // Unlike the candidate steps, step4/step5 ride on the session from load_case/confirm_step
  // directly — no separate lazy-fetch endpoint, so a plain reactive derivation is enough.
  $: objective = session?.step4?.objective || '';
  $: testSteps = session?.step5?.testScript?.steps || session?.step4?.testScript?.steps || [];
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
      onSuggest={(headers) => testlinkService.suggestTestLink(session.key, headers)}
      initialCandidates={testLinkCandidates}
      bind:chosen={testLinkChosen}
      onConfirm={async () => {
        const result = await testlinkService.confirmStep(session.key, testLinkChosen);
        session = result.session;
        currentStep = 2;
        scrollToTop();
      }}
    />
  {:else if currentStep === 2}
    <CandidatePickerStep
      columns={testLinkColumns}
      introText="Review relevance-ranked external Zephyr cases (current Cases list omitted). Search or suggest more, then confirm."
      searchPlaceholder="Search Zephyr by ID or title…"
      searchButtonLabel="Search Zephyr"
      candidateLabel="Zephyr Candidates"
      chosenLabel="Chosen Zephyr Cases"
      onSearch={(q) => zephyrService.searchZephyr(session.key, q)}
      onSuggest={(headers) => zephyrService.suggestZephyr(session.key, headers)}
      initialCandidates={zephyrCandidates}
      bind:chosen={zephyrChosen}
      onConfirm={async () => {
        const result = await zephyrService.confirmStep(session.key, zephyrChosen);
        session = result.session;
        currentStep = 3;
        scrollToTop();
      }}
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
      onSuggest={(headers) => atpylibService.suggestAtpylib(session.key, headers)}
      initialCandidates={atpylibCandidates}
      bind:chosen={atpylibChosen}
      onConfirm={async () => {
        const result = await atpylibService.confirmStep(session.key, atpylibChosen);
        session = result.session;
        currentStep = 4;
        scrollToTop();
      }}
    />
  {:else if currentStep === 4}
    <ObjectivesStep
      {summaryColumns}
      {summaryRows}
      {chosenForObjectives}
      {objective}
      onSynthesize={async (headers) => {
        const result = await objectivesService.synthesizeObjectives(session, headers);
        session = result.session;
        return result;
      }}
      onSaveObjective={async (html) => {
        const result = await objectivesService.saveObjective(session.key, html, false);
        session = result.session;
      }}
      onConfirm={async () => {
        const result = await objectivesService.confirmObjectives(session.key);
        session = result.session;
        currentStep = 5;
        scrollToTop();
      }}
    />
  {:else if currentStep === 5}
    <TestStepsStep
      caseKey={session?.key || ''}
      {objective}
      steps={testSteps}
      onSynthesize={async (headers) => {
        const result = await testStepsService.synthesizeSteps(session, headers);
        session = result.session;
        return result;
      }}
      onSaveSteps={async (steps) => {
        const result = await testStepsService.saveSteps(session.key, steps);
        session = result.session;
      }}
      onExport={() => testStepsService.exportBundle(session)}
      onPushToZephyr={(opts) => testStepsService.pushToZephyr(session.key, opts)}
      onFinished={() => (stepperCompleted = true)}
    />
  {:else}
    <p>Hello world</p>
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
  }
</style>

