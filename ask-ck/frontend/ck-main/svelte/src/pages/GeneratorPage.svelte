<script>
// @ts-nocheck

  import PageCard from '../lib/components/PageCard.svelte';
  import PageHeader from '../lib/components/PageHeader.svelte';
  import ToolHeader from '../lib/components/ToolHeader.svelte';
  import Stepper from '../lib/components/Stepper.svelte';
  import Button from '../lib/components/Button.svelte';
  import briefcaseIcon from '../assets/icons/briefcase.svg';
  import testTubeIcon from '../assets/icons/test-tube-diagonal.svg';
  import linkIcon from '../assets/icons/link.svg';
  import libraryIcon from '../assets/icons/library.svg';
  import targetIcon from '../assets/icons/target.svg';
  import footprintsIcon from '../assets/icons/footprints.svg';

  const steps = [
    { id: 'cases', label: 'Cases', icon: briefcaseIcon },
    { id: 'testlink', label: 'TestLink', icon: testTubeIcon },
    { id: 'zephyr', label: 'Zephyr', icon: linkIcon },
    { id: 'atpylib', label: 'ATPyLib (Scored)', icon: libraryIcon },
    { id: 'objectives', label: 'Objectives (LLM)', icon: targetIcon },
    { id: 'test-steps', label: 'Test Steps (LLM)', icon: footprintsIcon }
  ];

  let currentStep = 0;

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

  let selectedOpenCase = '';
  let selectedCompleteCase = '';

  $: canLoad = !!(selectedOpenCase || selectedCompleteCase);

  function handleOpenChange() {
    if (selectedOpenCase) selectedCompleteCase = '';
  }

  function handleCompleteChange() {
    if (selectedCompleteCase) selectedOpenCase = '';
  }

  function loadAndConfirm() {
    const caseId = selectedOpenCase || selectedCompleteCase;
    const loadedCase = [...openPartialCases, ...completeCases].find((c) => c.id === caseId);
    if (loadedCase) {
      title = loadedCase.label;
    }
    currentStep = 1;
  }

  function exportSession() {
    // TODO: wire up real export
  }

  let title = 'No case loaded. Please select a test case to work on.';
</script>

<ToolHeader title={title} tool="OBJECTIVE GENERATOR" />

<Stepper {steps} {currentStep} onStepClick={goToStep} />

<div class="tool-page">
  {#if currentStep === 0}
    <div class="cases-step">
      <p class="cases-intro">Select a test case to work on, then Load it. Export or clear its session from here too.</p>

      <div class="case-picker">
        <label class="case-picker-label" for="open-partial-select">Open / Partial (0)</label>
        <select
          id="open-partial-select"
          class="case-select"
          bind:value={selectedOpenCase}
          on:change={handleOpenChange}
        >
          <option value="">Select a case…</option>
          {#each openPartialCases as c}
            <option value={c.id}>{c.label}</option>
          {/each}
        </select>
      </div>

      <div class="case-picker">
        <label class="case-picker-label" for="complete-select">Complete (0)</label>
        <select
          id="complete-select"
          class="case-select"
          bind:value={selectedCompleteCase}
          on:change={handleCompleteChange}
        >
          <option value="">Select a case…</option>
          {#each completeCases as c}
            <option value={c.id}>{c.label}</option>
          {/each}
        </select>
      </div>

      <div class="cases-actions">
        <Button variant="primary" disabled={!canLoad} on:click={loadAndConfirm}>Load &amp; Confirm</Button>
        <Button variant="outline" on:click={exportSession}>Export</Button>
      </div>
    </div>
  {:else}
    <p>Hello world</p>
  {/if}
</div>

<style>
  .cases-step {
    max-width: 640px;
  }

  .cases-intro {
    margin: 0 0 24px;
    color: var(--color-text-muted);
    font-size: 0.94rem;
  }

  .case-picker {
    margin-bottom: 20px;
  }

  .case-picker-label {
    display: block;
    margin-bottom: 8px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--color-text-muted);
  }

  .case-select {
    width: 100%;
    padding: 10px 12px;
    border-radius: 8px;
    border: 1px solid var(--color-border-surface);
    background: var(--color-bg-surface);
    color: var(--color-text);
    font: inherit;
    font-size: 0.94rem;
  }

  .cases-actions {
    display: flex;
    gap: 12px;
    margin-top: 8px;
  }
</style>
