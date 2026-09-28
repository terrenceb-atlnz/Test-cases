<script>
// @ts-nocheck

  import { onMount } from 'svelte';
  import { scrollToTop } from '../lib/utils/scroll.js';
  import ToolHeader from '../lib/components/ToolHeader.svelte';
  import Stepper from '../lib/components/Stepper.svelte';
  import CasePicker from '../lib/components/CasePicker.svelte';
  import SequenceStep from '../lib/components/pytest/SequenceStep.svelte';
  import ScriptSearchStep from '../lib/components/pytest/ScriptSearchStep.svelte';
  import FragmentsStep from '../lib/components/pytest/FragmentsStep.svelte';
  import GenerateStep from '../lib/components/pytest/GenerateStep.svelte';
  import UnderConstruction from '../lib/components/UnderConstruction.svelte';

  import * as sequenceService from '../lib/services/pytest/sequenceService.js';
  import * as scriptSearchService from '../lib/services/pytest/scriptSearchService.js';
  import * as fragmentsService from '../lib/services/pytest/fragmentsService.js';
  import * as generateService from '../lib/services/pytest/generateService.js';

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

  // Mock case lists — replace with a real data source later
  const openPartialCases = [
    { id: 'AWPTCM-T44318', label: 'WPTCM-T44318 — (315) AdvancedManagement_AMF - AMF Master support' },
    { id: 'AWPTCM-T44201', label: 'WPTCM-T44201 — (212) VLAN_Configuration - Tagged port assignment' },
    { id: 'AWPTCM-T44087', label: 'WPTCM-T44087 — (108) StaticRouting - Default route fallback' }
  ];

  const completeCases = [
    { id: 'AWPTCM-T43991', label: 'WPTCM-T43991 — (301) LACP_Bonding - Active-active failover' },
    { id: 'AWPTCM-T43876', label: 'WPTCM-T43876 — (150) DHCP_Snooping - Trusted port enforcement' }
  ];

  let title = 'No case loaded. Please select a test case to work on.';

  function loadAndConfirm(caseId) {
    // maxStepReached > 0 means a case was already loaded and progressed past Cases in this
    // instance — switching to a different one now would leave every downstream field (sequence,
    // script search, fragments, generate, ...) still holding the old case's data. Rather than
    // manually resetting each of those, remount the whole page fresh with the new case id.
    if (maxStepReached > 0) {
      onCreateAnother && onCreateAnother(caseId);
      return;
    }

    const loadedCase = [...openPartialCases, ...completeCases].find((c) => c.id === caseId);
    if (loadedCase) {
      title = loadedCase.label;
    }
    currentStep = 1;
  }

  // A fresh instance remounted specifically to switch cases (onCreateAnother(caseId)) loads that
  // case immediately instead of landing back on the blank Cases picker. Deferred to onMount —
  // calling this during the component's own initialization (before every other `let`/`$:` below
  // it in this file has finished setting up) trips Svelte's reactivity scheduler into running a
  // reactive block against a not-yet-initialized variable, throwing a temporal-dead-zone error.
  onMount(() => {
    if (initialCaseId) {
      loadAndConfirm(initialCaseId);
    }
  });

  function exportSession() {
    // TODO: wire up real export
  }

  let sequencedTestSteps = [];
</script>

<ToolHeader title={title} tool="PYTEST CREATOR" icon={pyTestIcon} />

<Stepper {steps} {currentStep} {maxStepReached} {stepperCompleted} onStepClick={goToStep} />

<div class="tool-page">
  {#if currentStep === 0}
    <CasePicker {openPartialCases} {completeCases} onLoad={loadAndConfirm} onExport={exportSession} />
  {:else if currentStep === 1}
    <SequenceStep
      onSynthesize={sequenceService.extractSequence}
      bind:sequencedTestSteps
      onConfirm={() => { currentStep = 2; scrollToTop(); }}
    />
  {:else if currentStep === 2}
    <ScriptSearchStep
      {sequencedTestSteps}
      columns={scriptSearchService.scriptColumns}
      onSuggestForStep={scriptSearchService.suggestForStep}
      onSuggestAllSteps={scriptSearchService.suggestAllSteps}
      onSearch={scriptSearchService.searchForStep}
      onConfirm={() => { currentStep = 3; scrollToTop(); }}
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
</div>
