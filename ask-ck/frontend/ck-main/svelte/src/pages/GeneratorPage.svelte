<script>
// @ts-nocheck

  import { tick } from 'svelte';
  import PageCard from '../lib/components/PageCard.svelte';
  import PageHeader from '../lib/components/PageHeader.svelte';
  import ToolHeader from '../lib/components/ToolHeader.svelte';
  import Stepper from '../lib/components/Stepper.svelte';
  import Button from '../lib/components/Button.svelte';
  import Table from '../lib/components/Table.svelte';
  import CasePicker from '../lib/components/CasePicker.svelte';
  import ConfirmModal from '../lib/components/ConfirmModal.svelte';
  import StatusModal from '../lib/components/StatusModal.svelte';
  import SearchBox from '../lib/components/SearchBox.svelte';

  import briefcaseIcon from '../assets/icons/briefcase.svg';
  import testTubeIcon from '../assets/icons/test-tube-diagonal.svg';
  import linkIcon from '../assets/icons/link.svg';
  import libraryIcon from '../assets/icons/library.svg';
  import targetIcon from '../assets/icons/target.svg';
  import footprintsIcon from '../assets/icons/footprints.svg';
  import generatorIcon from '../assets/icons/clipboard-list.svg';

  const steps = [
    { id: 'cases', label: 'Cases', icon: briefcaseIcon },
    { id: 'testlink', label: 'TestLink', icon: testTubeIcon },
    { id: 'zephyr', label: 'Zephyr', icon: linkIcon },
    { id: 'atpylib', label: 'ATPyLib', icon: libraryIcon },
    { id: 'objectives', label: 'Objectives (LLM)', icon: targetIcon },
    { id: 'test-steps', label: 'Test Steps (LLM)', icon: footprintsIcon }
  ];

  let currentStep = 0;
  let maxStepReached = 0;

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

  function loadAndConfirm(caseId) {
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

  const testLinkColumns = [
    { key: 'caseId', label: 'ID', width: 1 },
    { key: 'title', label: 'Title', width: 2 },
    { key: 'score', label: 'Score', width: 1 },
    { key: 'description', label: 'Description', width: 3 }
  ];

  const summaryColumns = [...testLinkColumns, { key: 'source', label: 'Source', width: 1 }];

  // Mock TestLink candidate pool — replace with a real data source later
  const testLinkPool = [
    { id: 'tl-1', caseId: 'TL-10432', title: 'AMF Master election on reboot', score: '92', description: 'Verifies AMF master re-election after a forced reboot of the current master.' },
    { id: 'tl-2', caseId: 'TL-10488', title: 'AMF backup promotion timing', score: '87', description: 'Confirms backup member promotes to master within the expected failover window.' },
    { id: 'tl-3', caseId: 'TL-10501', title: 'AMF split-brain recovery', score: '79', description: 'Validates cluster recovers cleanly from a simulated split-brain condition.' },
    { id: 'tl-4', caseId: 'TL-10556', title: 'AMF member join with mismatched firmware', score: '64', description: "Checks join behaviour when a candidate member runs a different firmware version." },
    { id: 'tl-5', caseId: 'TL-10602', title: 'AMF master priority override', score: '58', description: 'Ensures a manually configured priority correctly overrides election order.' }
  ];

  let testLinkSearch = '';
  let testLinkCandidates = [];
  let testLinkChosen = [];
  let selectedTestLinkRows = [];
  let selectedChosenRows = [];

  function searchTestLink() {
    // TODO: replace with a real TestLink search call
    const q = testLinkSearch.trim().toLowerCase();
    testLinkCandidates = q
      ? testLinkPool.filter((c) => c.title.toLowerCase().includes(q) || c.caseId.toLowerCase().includes(q))
      : [...testLinkPool];
    selectedTestLinkRows = [];
  }

  function suggestWithLlm() {
    // TODO: replace with a real LLM suggestion call
    testLinkCandidates = [...testLinkPool];
    selectedTestLinkRows = [];
  }

  function chooseSelected() {
    const moving = testLinkCandidates.filter((c) => selectedTestLinkRows.includes(c.id));
    if (moving.length === 0) return;
    testLinkChosen = [...testLinkChosen, ...moving];
    testLinkCandidates = testLinkCandidates.filter((c) => !selectedTestLinkRows.includes(c.id));
    selectedTestLinkRows = [];
  }

  function clearSelected() {
    const moving = testLinkChosen.filter((c) => selectedChosenRows.includes(c.id));
    if (moving.length === 0) return;
    testLinkCandidates = [...testLinkCandidates, ...moving];
    testLinkChosen = testLinkChosen.filter((c) => !selectedChosenRows.includes(c.id));
    selectedChosenRows = [];
  }

  function clearAll() {
    testLinkCandidates = [...testLinkCandidates, ...testLinkChosen];
    testLinkChosen = [];
    selectedChosenRows = [];
  }

  // Waits for Svelte to flush the DOM update (the {:else if currentStep === N} swap) before
  // scrolling — otherwise this can run while the old, taller content is still on screen, and the
  // subsequent layout shift from the swap interrupts or swallows the smooth-scroll animation.
  async function scrollToTop() {
    await tick();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function reviewAndConfirmTestLink() {
    currentStep = 2;
    scrollToTop();
  }

  // Mock Zephyr candidate pool — replace with a real data source later
  const zephyrPool = [
    { id: 'zep-1', caseId: 'ZEP-2201', title: 'AMF failover latency under load', score: '88', description: 'Measures failover latency for AMF master election under sustained traffic load.' },
    { id: 'zep-2', caseId: 'ZEP-2233', title: 'AMF configuration sync after rejoin', score: '81', description: 'Confirms configuration re-syncs correctly when a member rejoins after a network partition.' },
    { id: 'zep-3', caseId: 'ZEP-2260', title: 'AMF virtual MAC consistency', score: '74', description: 'Validates the virtual MAC address remains consistent across a master re-election.' },
    { id: 'zep-4', caseId: 'ZEP-2298', title: 'AMF firmware mismatch warning', score: '69', description: 'Checks that a firmware mismatch warning is raised during AMF member discovery.' },
    { id: 'zep-5', caseId: 'ZEP-2312', title: 'AMF priority tie-break behaviour', score: '55', description: 'Ensures a deterministic tie-break when two candidates share equal priority.' }
  ];

  let zephyrSearch = '';
  let zephyrCandidates = [];
  let zephyrChosen = [];
  let selectedZephyrRows = [];
  let selectedChosenZephyrRows = [];

  function searchZephyr() {
    // TODO: replace with a real Zephyr search call
    const q = zephyrSearch.trim().toLowerCase();
    zephyrCandidates = q
      ? zephyrPool.filter((c) => c.title.toLowerCase().includes(q) || c.caseId.toLowerCase().includes(q))
      : [...zephyrPool];
    selectedZephyrRows = [];
  }

  function suggestZephyrWithLlm() {
    // TODO: replace with a real LLM suggestion call
    zephyrCandidates = [...zephyrPool];
    selectedZephyrRows = [];
  }

  function chooseSelectedZephyr() {
    const moving = zephyrCandidates.filter((c) => selectedZephyrRows.includes(c.id));
    if (moving.length === 0) return;
    zephyrChosen = [...zephyrChosen, ...moving];
    zephyrCandidates = zephyrCandidates.filter((c) => !selectedZephyrRows.includes(c.id));
    selectedZephyrRows = [];
  }

  function clearSelectedZephyr() {
    const moving = zephyrChosen.filter((c) => selectedChosenZephyrRows.includes(c.id));
    if (moving.length === 0) return;
    zephyrCandidates = [...zephyrCandidates, ...moving];
    zephyrChosen = zephyrChosen.filter((c) => !selectedChosenZephyrRows.includes(c.id));
    selectedChosenZephyrRows = [];
  }

  function clearAllZephyr() {
    zephyrCandidates = [...zephyrCandidates, ...zephyrChosen];
    zephyrChosen = [];
    selectedChosenZephyrRows = [];
  }

  function reviewAndConfirmZephyr() {
    currentStep = 3;
    scrollToTop();
  }

  // Mock ATPyLib candidate pool — replace with a real data source later
  const atpylibPool = [
    { id: 'atp-1', caseId: 'ATP-5510', title: 'AMF library master election helper', score: '90', description: 'Reusable ATPyLib helper covering master election setup and teardown.' },
    { id: 'atp-2', caseId: 'ATP-5544', title: 'AMF library failover assertion set', score: '84', description: 'Common assertion set for validating failover timing across AMF library calls.' },
    { id: 'atp-3', caseId: 'ATP-5567', title: 'AMF library topology fixture', score: '77', description: 'Fixture that builds a standard AMF cluster topology for reuse across scored cases.' },
    { id: 'atp-4', caseId: 'ATP-5602', title: 'AMF library firmware version guard', score: '66', description: 'Guards library calls against unsupported firmware version combinations.' },
    { id: 'atp-5', caseId: 'ATP-5631', title: 'AMF library priority helper', score: '52', description: 'Helper for configuring and asserting on AMF member priority values.' },
    { id: 'atp-6', caseId: 'ATP-5639', title: 'AMF library priority helper', score: '52', description: 'Helper for configuring and asserting on AMF member priority values.' },
    { id: 'atp-7', caseId: 'ATP-5789', title: 'AMF library priority helper', score: '52', description: 'Helper for configuring and asserting on AMF member priority values.' },
    { id: 'atp-8', caseId: 'ATP-5678', title: 'AMF library priority helper', score: '52', description: 'Helper for configuring and asserting on AMF member priority values.' },
    { id: 'atp-9', caseId: 'ATP-5780', title: 'AMF library priority helper', score: '52', description: 'Helper for configuring and asserting on AMF member priority values.' },
    { id: 'atp-10', caseId: 'ATP-5656', title: 'AMF library priority helper', score: '52', description: 'Helper for configuring and asserting on AMF member priority values.' },

  ];

  let atpylibSearch = '';
  let atpylibCandidates = [];
  let atpylibChosen = [];
  let selectedAtpylibRows = [];
  let selectedChosenAtpylibRows = [];

  function searchAtpylib() {
    // TODO: replace with a real ATPyLib search call
    const q = atpylibSearch.trim().toLowerCase();
    atpylibCandidates = q
      ? atpylibPool.filter((c) => c.title.toLowerCase().includes(q) || c.caseId.toLowerCase().includes(q))
      : [...atpylibPool];
    selectedAtpylibRows = [];
  }

  function suggestAtpylibWithLlm() {
    // TODO: replace with a real LLM suggestion call
    atpylibCandidates = [...atpylibPool];
    selectedAtpylibRows = [];
  }

  function chooseSelectedAtpylib() {
    const moving = atpylibCandidates.filter((c) => selectedAtpylibRows.includes(c.id));
    if (moving.length === 0) return;
    atpylibChosen = [...atpylibChosen, ...moving];
    atpylibCandidates = atpylibCandidates.filter((c) => !selectedAtpylibRows.includes(c.id));
    selectedAtpylibRows = [];
  }

  function clearSelectedAtpylib() {
    const moving = atpylibChosen.filter((c) => selectedChosenAtpylibRows.includes(c.id));
    if (moving.length === 0) return;
    atpylibCandidates = [...atpylibCandidates, ...moving];
    atpylibChosen = atpylibChosen.filter((c) => !selectedChosenAtpylibRows.includes(c.id));
    selectedChosenAtpylibRows = [];
  }

  function clearAllAtpylib() {
    atpylibCandidates = [...atpylibCandidates, ...atpylibChosen];
    atpylibChosen = [];
    selectedChosenAtpylibRows = [];
  }

  function reviewAndConfirmAtpylib() {
    currentStep = 4;
    scrollToTop();
  }

  // Hard-coded placeholder objectives — replace with real LLM output once the backend is connected
  const hardcodedObjectives = [
    'Verify AMF master election completes within the expected time window after a forced reboot.',
    'Confirm failover to a backup member preserves configuration state and network reachability.',
    'Validate the system reports a clear warning when firmware versions mismatch during AMF discovery.'
  ];

  let objectives = [];
  let showObjectives = false;
  let isEditingObjectives = false;
  let objectivesDraft = '';

  $: summaryRows = [
    ...testLinkChosen.map((c) => ({ ...c, source: 'TestLink' })),
    ...zephyrChosen.map((c) => ({ ...c, source: 'Zephyr' })),
    ...atpylibChosen.map((c) => ({ ...c, source: 'ATPyLib' }))
  ];
  $: chosenForObjectives = [...testLinkChosen, ...zephyrChosen, ...atpylibChosen];

  let showNoCandidatesModal = false;

  function handleSynthesizeObjectivesClick() {
    if (chosenForObjectives.length === 0) {
      showNoCandidatesModal = true;
      return;
    }
    synthesizeObjectives();
  }

  function synthesizeObjectives() {
    // TODO: replace with a real LLM synthesis call — with no candidates chosen, the LLM will do its
    // best using the Test Case context alone
    objectives = [...hardcodedObjectives];
    showObjectives = true;
    isEditingObjectives = false;
  }

  function editObjectives() {
    objectivesDraft = objectives.join('\n');
    isEditingObjectives = true;
  }

  function saveObjectives() {
    objectives = objectivesDraft
      .split('\n')
      .map((line) => line.trim())
      .filter((line) => line.length > 0);
    isEditingObjectives = false;
  }

  function cancelEditObjectives() {
    isEditingObjectives = false;
  }

  $: canReviewObjectives = objectives.length > 0;

  function reviewAndConfirmObjectives() {
    currentStep = 5;
    scrollToTop();
  }

  // Hard-coded placeholder test steps — replace with real LLM output derived from objectives once the backend is connected
  const hardcodedTestSteps = [
    'Configure the AMF cluster with the required member priorities.',
    'Trigger a forced reboot of the current master member.',
    'Wait for master re-election to complete and record the elapsed time.',
    'Verify the new master matches the expected priority-based candidate.',
    'Confirm all AMF members report a consistent cluster state.'
  ];

  let testSteps = [];
  let showTestSteps = false;
  let isEditingTestSteps = false;
  let testStepsDraft = '';

  function synthesizeTestSteps() {
    // TODO: replace with a real LLM synthesis call deriving steps from `objectives`
    testSteps = [...hardcodedTestSteps];
    showTestSteps = true;
    isEditingTestSteps = false;
  }

  function editTestSteps() {
    testStepsDraft = testSteps.join('\n');
    isEditingTestSteps = true;
  }

  function saveTestSteps() {
    testSteps = testStepsDraft
      .split('\n')
      .map((line) => line.trim())
      .filter((line) => line.length > 0);
    isEditingTestSteps = false;
  }

  function cancelEditTestSteps() {
    isEditingTestSteps = false;
  }

  let showExportStatusModal = false;
  let exportStatus = 'success';
  let exportStatusMessage = '';

  function exportRepeatableBundle() {
    // TODO: replace with a real export call — for now, mock a successful export
    const exportSucceeded = true;
    if (exportSucceeded) {
      exportStatus = 'success';
      exportStatusMessage = 'The repeatable bundle was exported successfully.';
    } else {
      exportStatus = 'error';
      exportStatusMessage = 'Something went wrong while exporting the repeatable bundle. Please try again.';
    }
    showExportStatusModal = true;
  }
</script>

<ToolHeader title={title} tool="OBJECTIVE GENERATOR" icon={generatorIcon} />

<Stepper {steps} {currentStep} {maxStepReached} onStepClick={goToStep} />

<div class="tool-page">
  {#if currentStep === 0}
    <CasePicker {openPartialCases} {completeCases} onLoad={loadAndConfirm} onExport={exportSession} />
    {:else if currentStep === 1}
    <p class="cases-intro">Review primary decision and TestLink candidates. Search or ask the LLM to suggest, then confirm selections.</p>

    <div class="testlink-search">
      <SearchBox
        bind:value={testLinkSearch}
        placeholder="Search TestLink by ID or title…"
        buttonLabel="Search TestLink"
        onSearch={searchTestLink}
      />
      <Button variant="primary" sparkle on:click={suggestWithLlm}>Suggest with LLM</Button>
    </div>

    <p class="testlink-table-label">TestLink Candidates</p>
    <Table columns={testLinkColumns} rows={testLinkCandidates} bind:selected={selectedTestLinkRows} />

    <div class="testlink-choose-actions">
      <Button variant="outline" on:click={chooseSelected}>↓ Choose selected</Button>
    </div>

    <p class="testlink-table-label">Chosen TestLink Cases</p>
    <Table columns={testLinkColumns} rows={testLinkChosen} bind:selected={selectedChosenRows} />

    <div class="testlink-final-actions">
      <Button variant="primary" on:click={reviewAndConfirmTestLink}>Review &amp; Confirm</Button>
      <Button variant="outline" on:click={clearSelected}>Clear Selected</Button>
      <Button variant="outline" on:click={clearAll}>Clear All</Button>
    </div>
    {:else if currentStep === 2}
    <p class="cases-intro">Review relevance-ranked external Zephyr cases (current Cases list omitted). Search or suggest more, then confirm.</p>

    <div class="testlink-search">
      <SearchBox
        bind:value={zephyrSearch}
        placeholder="Search Zephyr by ID or title…"
        buttonLabel="Search Zephyr"
        onSearch={searchZephyr}
      />
      <Button variant="primary" sparkle on:click={suggestZephyrWithLlm}>Suggest with LLM</Button>
    </div>

    <p class="testlink-table-label">Zephyr Candidates</p>
    <Table columns={testLinkColumns} rows={zephyrCandidates} bind:selected={selectedZephyrRows} />

    <div class="testlink-choose-actions">
      <Button variant="outline" on:click={chooseSelectedZephyr}>↓ Choose selected</Button>
    </div>

    <p class="testlink-table-label">Chosen Zephyr Cases</p>
    <Table columns={testLinkColumns} rows={zephyrChosen} bind:selected={selectedChosenZephyrRows} />

    <div class="testlink-final-actions">
      <Button variant="primary" on:click={reviewAndConfirmZephyr}>Review &amp; Confirm</Button>
      <Button variant="outline" on:click={clearSelectedZephyr}>Clear Selected</Button>
      <Button variant="outline" on:click={clearAllZephyr}>Clear All</Button>
    </div>
    {:else if currentStep === 3}
    <p class="cases-intro">Review scored ATPyLib candidates (LLM + keyword). Optionally search or re-suggest, then select relevant tests. Coverage gaps are generated by the LLM at synthesis/export for Traceability — not edited here.</p>

    <div class="testlink-search">
      <SearchBox
        bind:value={atpylibSearch}
        placeholder="Search ATPyLib by ID or title…"
        buttonLabel="Search ATPyLib"
        onSearch={searchAtpylib}
      />
      <Button variant="primary" sparkle on:click={suggestAtpylibWithLlm}>Suggest with LLM</Button>
    </div>

    <p class="testlink-table-label">ATPyLib Candidates</p>
    <Table columns={testLinkColumns} rows={atpylibCandidates} bind:selected={selectedAtpylibRows} />

    <div class="testlink-choose-actions">
      <Button variant="outline" on:click={chooseSelectedAtpylib}>↓ Choose selected</Button>
    </div>

    <p class="testlink-table-label">Chosen ATPyLib Tests</p>
    <Table columns={testLinkColumns} rows={atpylibChosen} bind:selected={selectedChosenAtpylibRows} />

    <div class="testlink-final-actions">
      <Button variant="primary" on:click={reviewAndConfirmAtpylib}>Review &amp; Confirm</Button>
      <Button variant="outline" on:click={clearSelectedAtpylib}>Clear Selected</Button>
      <Button variant="outline" on:click={clearAllAtpylib}>Clear All</Button>
    </div>
  {:else if currentStep === 4}  
    <p class="cases-intro">Generate declarative objective artefacts from the confirmed review summary (TestLink / Zephyr / ATPyLib). Review and edit, then confirm before synthesizing test steps in Step 6.</p>
    <p class="testlink-table-label">Summary</p>
    <Table columns={summaryColumns} rows={summaryRows} selectable={false} />

    <div class="objectives-actions">
      <Button variant="primary" sparkle on:click={handleSynthesizeObjectivesClick}>Synthesize Objectives (LLM)</Button>
    </div>

    <ConfirmModal
      bind:open={showNoCandidatesModal}
      title="No candidates selected"
      message="You haven't selected any TestLink, Zephyr, or ATPyLib candidates. The LLM will do its best using only the Test Case context. Continue anyway?"
      confirmText="Continue"
      cancelText="Cancel"
      onConfirm={synthesizeObjectives}
    />

    {#if showObjectives}
      <p class="testlink-table-label">Generated Objectives</p>
      <div class="objectives-window">
        {#if isEditingObjectives}
          <textarea class="objectives-textarea" bind:value={objectivesDraft} rows="8"></textarea>
          <div class="objectives-window-actions">
            <Button variant="primary" on:click={saveObjectives}>Save Changes</Button>
            <Button variant="outline" on:click={cancelEditObjectives}>Cancel</Button>
          </div>
        {:else}
          <ul class="objectives-list">
            {#each objectives as objective, i (i)}
              <li>{objective}</li>
            {/each}
          </ul>
          <div class="objectives-window-actions">
            <Button variant="outline" on:click={editObjectives}>Edit</Button>
          </div>
        {/if}
      </div>
      <Button variant="primary" disabled={!canReviewObjectives} on:click={reviewAndConfirmObjectives}>Review &amp; Confirm</Button>
    {/if}
  {:else if currentStep === 5}
    <p class="cases-intro">Generate verification steps from the finalized objective (Step 5) plus review context. The first step is always the server-built traceability note. Export the repeatable bundle when ready.</p>

    <p class="testlink-table-label">Objectives</p>
    <div class="objectives-window">
      <ul class="objectives-list">
        {#each objectives as objective, i (i)}
          <li>{objective}</li>
        {/each}
      </ul>
    </div>

    <div class="objectives-actions">
      <Button variant="primary" sparkle disabled={objectives.length === 0} on:click={synthesizeTestSteps}>Synthesize Test Steps (LLM)</Button>
    </div>

    {#if showTestSteps}
      <p class="testlink-table-label">Generated Test Steps</p>
      <div class="objectives-window">
        {#if isEditingTestSteps}
          <textarea class="objectives-textarea" bind:value={testStepsDraft} rows="8"></textarea>
          <div class="objectives-window-actions">
            <Button variant="primary" on:click={saveTestSteps}>Save Changes</Button>
            <Button variant="outline" on:click={cancelEditTestSteps}>Cancel</Button>
          </div>
        {:else}
          <ol class="objectives-list">
            {#each testSteps as step, i (i)}
              <li>{step}</li>
            {/each}
          </ol>
          <div class="objectives-window-actions">
            <Button variant="outline" on:click={editTestSteps}>Edit</Button>
          </div>
        {/if}
      </div>

      <div class="export-actions">
        <Button variant="success" on:click={exportRepeatableBundle}>Finish & Export</Button>
      </div>
    {/if}

    <StatusModal
      bind:open={showExportStatusModal}
      status={exportStatus}
      title={exportStatus === 'success' ? 'Export successful' : 'Export failed'}
      message={exportStatusMessage}
    />
  {:else}
    <p>Hello world</p>
  {/if}
</div>

<style>
  .cases-intro {
    margin: 0 0 24px;
    color: var(--color-text-muted);
    font-size: 0.94rem;
  }

  .testlink-search {
    display: flex;
    gap: 12px;
    align-items: center;
    margin-bottom: 20px;
  }

  .testlink-table-label {
    margin: 0 0 8px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--color-text-muted);
  }

  .testlink-choose-actions {
    display: flex;
    gap: 12px;
    margin: 16px 0;
  }

  .testlink-final-actions {
    display: flex;
    gap: 12px;
    margin-top: 20px;
  }

  .objectives-actions {
    display: flex;
    margin: 24px 0 24px;
  }

  .objectives-window {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 16px;
    margin-bottom: 12px;
    border: 1px solid var(--color-border-surface);
    border-radius: 8px;
    background: var(--color-bg-surface);
    width: 100%;
  }

  .objectives-list {
    margin: 0;
    padding-left: 20px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    color: var(--color-text);
    font-size: 0.94rem;
  }

  .objectives-textarea {
    width: 100%;
    min-height: 160px;
    padding: 10px 12px;
    border-radius: 8px;
    border: 1px solid var(--color-border-surface);
    background: var(--color-bg-content);
    color: var(--color-text);
    font: inherit;
    font-size: 0.94rem;
    resize: vertical;
  }

  .objectives-window-actions {
    display: flex;
    gap: 12px;
  }

  .export-actions {
    display: flex;
    margin-top: 16px;
  }
</style>
