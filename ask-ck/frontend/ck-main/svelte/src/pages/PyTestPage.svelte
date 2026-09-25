<script>
// @ts-nocheck

  import { tick } from 'svelte';
  import PageCard from '../lib/components/PageCard.svelte';
  import PageHeader from '../lib/components/PageHeader.svelte';
  import ToolHeader from '../lib/components/ToolHeader.svelte';
  import Stepper from '../lib/components/Stepper.svelte';
  import CasePicker from '../lib/components/CasePicker.svelte';
  import Button from '../lib/components/Button.svelte';
  import Table from '../lib/components/Table.svelte';
  import SequenceTable from '../lib/components/SequenceTable.svelte';
  import ArrowStep from '../lib/components/ArrowStep.svelte';
  import ConfirmModal from '../lib/components/ConfirmModal.svelte';
  import SearchBox from '../lib/components/SearchBox.svelte';
  import FragmentCard from '../lib/components/FragmentCard.svelte';
  import EditableField from '../lib/components/EditableField.svelte';
  import UnderConstruction from '../lib/components/UnderConstruction.svelte';

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

  $: if (currentStep > maxStepReached) maxStepReached = currentStep;

  function goToStep(index) {
    currentStep = index;
  }

  // Both wait for Svelte to flush the pending DOM update (a step/unit swap) before scrolling —
  // otherwise this can run while the old, taller content is still on screen, and the subsequent
  // layout shift from the swap interrupts or swallows the smooth-scroll animation.

  // Used by the main "Review & Confirm" actions (Sequence/Script Search/Fragments/Generate ->
  // the next main step) — goes all the way to the top of the page.
  async function scrollToTop() {
    await tick();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // Used when confirming an individual arrow step (Confirm Scripts/Fragments/Unit) — goes to the
  // new step's own description just above its arrow-step row, rather than the page top, since
  // that's the part actually relevant when paging between steps within the same arrow-stepper.
  async function scrollToStepIntro() {
    await tick();
    const intro = document.querySelector('.step-intro');
    if (intro) {
      intro.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
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

  const manualColumns = [
    { key: 'stepNumber', label: '#', width: 1 },
    { key: 'description', label: 'Description', width: 9 }
  ];

  // Mock manual test steps — replace with the steps from the selected case's Objective Generator output
  const manualTestSteps = [
    { id: 'step-1', stepNumber: 1, description: 'Configure the AMF cluster with the required member priorities.' },
    { id: 'step-2', stepNumber: 2, description: 'Trigger a forced reboot of the current master member.' },
    { id: 'step-3', stepNumber: 3, description: 'Wait for master re-election to complete and record the elapsed time.' },
    { id: 'step-4', stepNumber: 4, description: 'Verify the new master matches the expected priority-based candidate.' },
    { id: 'step-5', stepNumber: 5, description: 'Confirm all AMF members report a consistent cluster state.' }
  ];

  // Mock sequenced test steps — replace with real LLM extraction output
  const mockSequencedTestSteps = [
    { id: 'seq-1', from: 1, action: 'Configure the AMF cluster with the required member priorities.', verify: 'Cluster configuration is applied without errors.' },
    { id: 'seq-2', from: 2, action: 'Trigger a forced reboot of the current master member.', verify: 'Reboot command is accepted and the member goes offline.' },
    { id: 'seq-3', from: 3, action: 'Wait for master re-election to complete.', verify: 'Elapsed time is recorded and falls within the expected window.' },
    { id: 'seq-4', from: 4, action: 'Query the identity of the new master.', verify: 'New master matches the expected priority-based candidate.' },
    { id: 'seq-5', from: 5, action: 'Query cluster state from all AMF members.', verify: 'All members report a consistent cluster state.' }
  ];

  let sequencedTestSteps = [];

  function extractSequence() {
    // TODO: replace with a real LLM extraction call
    sequencedTestSteps = mockSequencedTestSteps.map((s) => ({ ...s }));
  }

  function reviewAndConfirmSequence() {
    currentStep = 2;
    scrollToTop();
  }

  const scriptColumns = [
    { key: 'name', label: 'Script', width: 2 },
    { key: 'source', label: 'Source', width: 1 },
    { key: 'description', label: 'Description', width: 3 }
  ];

  // Mock reusable-script pool — replace with a real script index search later
  const scriptPool = [
    { id: 'script-1', name: 'test_port_speed_set', source: 'test_scripts', description: "Sets port speed using the 'speed <n>' CLI command." },
    { id: 'script-2', name: 'test_port_duplex_set', source: 'test_scripts', description: "Sets port duplex mode using 'duplex full/half'." },
    { id: 'script-3', name: 'test_port_autoneg_toggle', source: 'testsuites_art', description: 'Toggles auto-negotiation on a port and verifies the resulting state.' },
    { id: 'script-4', name: 'test_port_link_status', source: 'testsuites_art', description: 'Polls and asserts link status after a configuration change.' },
    { id: 'script-5', name: 'test_port_reset', source: 'test_scripts', description: 'Resets a port to its default configuration.' }
  ];

  const SUMMARY_STEP_ID = '__summary__';

  // Per sequenced-step search state, keyed by the sequenced step's id — populated lazily below
  let scriptSearchState = {};
  let activeStepId = null;

  // Ids of sequence steps whose scripts have been explicitly confirmed via "Confirm Scripts" —
  // once confirmed a step's arrow turns green even if it has no chosen scripts.
  let confirmedSteps = [];

  $: {
    for (const step of sequencedTestSteps) {
      if (!scriptSearchState[step.id]) {
        scriptSearchState[step.id] = {
          search: '',
          candidates: [],
          chosen: [],
          selectedCandidateIds: [],
          selectedChosenIds: []
        };
      }
    }
    if (!activeStepId && sequencedTestSteps.length > 0) {
      activeStepId = sequencedTestSteps[0].id;
    }
  }

  $: activeStep = sequencedTestSteps.find((s) => s.id === activeStepId) ?? null;
  $: activeStepIndex = sequencedTestSteps.findIndex((s) => s.id === activeStepId);

  // Recomputed whenever sequencedTestSteps OR scriptSearchState change (both referenced directly here,
  // so Svelte's dependency tracking picks them up — a plain helper function calling into
  // scriptSearchState would NOT retrigger this, since Svelte only tracks identifiers referenced
  // directly in a reactive statement, not ones hidden inside a called function).
  let stepStatuses = {};
  $: {
    const next = {};
    for (const step of sequencedTestSteps) {
      const state = scriptSearchState[step.id];
      if (confirmedSteps.includes(step.id)) {
        next[step.id] = 'covered';
      } else if (state?.chosen.length > 0 || state?.candidates.length > 0) {
        next[step.id] = 'review';
      } else {
        next[step.id] = 'none';
      }
    }
    stepStatuses = next;
  }

  $: summaryStatus =
    sequencedTestSteps.length > 0 && sequencedTestSteps.every((s) => confirmedSteps.includes(s.id))
      ? 'covered'
      : 'none';

  $: coveragePercent =
    sequencedTestSteps.length === 0
      ? 0
      : Math.round(
          (Object.values(stepStatuses).filter((s) => s === 'covered').length / sequencedTestSteps.length) * 100
        );

  function selectStep(stepId) {
    activeStepId = stepId;
  }

  function suggestForStep(stepId) {
    // TODO: replace with a real script search / LLM suggestion call
    scriptSearchState[stepId].candidates = [...scriptPool];
    scriptSearchState[stepId].selectedCandidateIds = [];
    scriptSearchState = scriptSearchState;
  }

  function suggestAllSteps() {
    // TODO: replace with a real script search / LLM suggestion call across all steps
    for (const step of sequencedTestSteps) {
      scriptSearchState[step.id].candidates = [...scriptPool];
      scriptSearchState[step.id].selectedCandidateIds = [];
    }
    scriptSearchState = scriptSearchState;
  }

  function searchForStep(stepId) {
    // TODO: replace with a real keyword search call
    const q = scriptSearchState[stepId].search.trim().toLowerCase();
    scriptSearchState[stepId].candidates = q
      ? scriptPool.filter((s) => s.name.toLowerCase().includes(q) || s.description.toLowerCase().includes(q))
      : [...scriptPool];
    scriptSearchState[stepId].selectedCandidateIds = [];
    scriptSearchState = scriptSearchState;
  }

  // Briefly flashes newly-chosen rows in the "Chosen" table so it's clear where they landed.
  let flashChosenIds = [];
  let flashChosenTimeout;

  function chooseSelectedForStep(stepId) {
    const state = scriptSearchState[stepId];
    const moving = state.candidates.filter((c) => state.selectedCandidateIds.includes(c.id));
    if (moving.length === 0) return;
    scriptSearchState[stepId].chosen = [...state.chosen, ...moving];
    scriptSearchState[stepId].candidates = state.candidates.filter((c) => !state.selectedCandidateIds.includes(c.id));
    scriptSearchState[stepId].selectedCandidateIds = [];
    scriptSearchState = scriptSearchState;

    flashChosenIds = moving.map((c) => c.id);
    clearTimeout(flashChosenTimeout);
    flashChosenTimeout = setTimeout(() => { flashChosenIds = []; }, 900);
  }

  function clearSelectedForStep(stepId) {
    const state = scriptSearchState[stepId];
    const moving = state.chosen.filter((c) => state.selectedChosenIds.includes(c.id));
    if (moving.length === 0) return;
    scriptSearchState[stepId].candidates = [...state.candidates, ...moving];
    scriptSearchState[stepId].chosen = state.chosen.filter((c) => !state.selectedChosenIds.includes(c.id));
    scriptSearchState[stepId].selectedChosenIds = [];
    scriptSearchState = scriptSearchState;
  }

  function clearAllForStep(stepId) {
    const state = scriptSearchState[stepId];
    scriptSearchState[stepId].candidates = [...state.candidates, ...state.chosen];
    scriptSearchState[stepId].chosen = [];
    scriptSearchState[stepId].selectedChosenIds = [];
    scriptSearchState = scriptSearchState;
  }

  function advanceScriptSearchStep() {
    const updatedConfirmed = confirmedSteps.includes(activeStepId)
      ? confirmedSteps
      : [...confirmedSteps, activeStepId];
    confirmedSteps = updatedConfirmed;

    // Jump to the next step that isn't confirmed yet (not just the next one in order) — steps can
    // be confirmed out of sequence, so "next" must skip over ones already done. Once every step is
    // confirmed, land on the Summary arrow instead.
    const nextUnconfirmed = sequencedTestSteps.find((s) => !updatedConfirmed.includes(s.id));
    activeStepId = nextUnconfirmed ? nextUnconfirmed.id : SUMMARY_STEP_ID;
    scrollToStepIntro();
  }

  let showNoScriptsModal = false;

  function handleConfirmScriptsClick() {
    const chosenCount = scriptSearchState[activeStepId]?.chosen.length ?? 0;
    if (chosenCount === 0) {
      showNoScriptsModal = true;
      return;
    }
    advanceScriptSearchStep();
  }

  function confirmScriptSearchAndAdvance() {
    currentStep = 3;
    scrollToTop();
  }

  // Mock reusable-code fragments per sequence step — replace with a real code-reuse search / LLM
  // call later. Each step gets zero or more "recommended" (green) fragments plus zero or more
  // "redundant" alternatives (red, nested) the LLM preferred the recommended one(s) over.
  const mockFragmentGroups = {
    'seq-1': [
      { id: 'frag-1a', name: 'TestSet', source: 'art/1300_amf_cluster/test-1300.1004.py', steps: 1, recommended: true,
        description: 'selected to configure the AMF cluster (member-priority set across tb/swi_a/swi_b) — matches the priority values this step needs.',
        codeLines: 41, code: 'def test_1300_1004(tb):\n    tb.swi_a.amf.priority_set(member="swi_a", priority=100)\n    tb.swi_b.amf.priority_set(member="swi_b", priority=50)\n    ...' },
      { id: 'frag-1b', name: 'TestSet', source: 'art/1300_amf_cluster/test-1300.1002.py', steps: 1, recommended: false,
        redundantReason: 'redundant to test-1300.1004 TestSet — identical priority configuration without the multi-member topology.',
        codeLines: 22, code: 'def test_1300_1002(tb):\n    tb.swi_a.amf.priority_set(member="swi_a", priority=100)\n    ...' },
      { id: 'frag-1c', name: 'TestSet', source: 'art/6000_link_check/test-6000.1001.py', steps: 1, recommended: false,
        redundantReason: 'redundant to test-1300.1004 TestSet — generic topology init only, no AMF priority handling.',
        codeLines: 10, code: 'def test_6000_1001(tb):\n    tb.topology_init()\n    ...' }
    ],
    'seq-2': [
      { id: 'frag-2a', name: 'TestSet', source: 'art/1300_amf_cluster/test-1300.2011.py', steps: 1, recommended: true,
        description: 'selected to force-reboot the identified master member and confirm the reboot command is accepted.',
        codeLines: 28, code: 'def test_1300_2011(tb):\n    tb.amf.master().reboot(force=True)\n    ...' },
      { id: 'frag-2b', name: 'TestSet', source: 'art/1300_amf_cluster/test-1300.2003.py', steps: 1, recommended: false,
        redundantReason: 'redundant to test-1300.2011 TestSet — reboots a member by fixed index rather than by resolved master role.',
        codeLines: 19, code: 'def test_1300_2003(tb):\n    tb.swi_a.reboot(force=True)\n    ...' }
    ],
    'seq-3': [
      { id: 'frag-3a', name: 'TestSet', source: 'art/1300_amf_cluster/test-1300.3007.py', steps: 1, recommended: true,
        description: 'selected to poll cluster state until re-election completes and record the elapsed time.',
        codeLines: 33, code: 'def test_1300_3007(tb):\n    start = time.time()\n    tb.amf.wait_for_reelection()\n    ...' }
    ],
    'seq-4': [
      { id: 'frag-4a', name: 'TestSet', source: 'art/1300_amf_cluster/test-1300.4002.py', steps: 1, recommended: true,
        description: "selected to query and return the current master member's identity for comparison against the expected candidate.",
        codeLines: 17, code: 'def test_1300_4002(tb):\n    return tb.amf.master().name\n    ...' },
      { id: 'frag-4b', name: 'TestSet', source: 'art/1300_amf_cluster/test-1300.1004.py', steps: 1, recommended: false,
        redundantReason: 'redundant to test-1300.4002 TestSet — also queries member roles, but as a side effect of priority configuration rather than a direct identity query.',
        codeLines: 41, code: 'def test_1300_1004(tb):\n    tb.swi_a.amf.priority_set(member="swi_a", priority=100)\n    ...' }
    ],
    'seq-5': [
      { id: 'frag-5a', name: 'TestSet', source: 'art/1300_amf_cluster/test-1300.5001.py', steps: 1, recommended: true,
        description: 'selected to query cluster state from every member and confirm a consistent view.',
        codeLines: 25, code: 'def test_1300_5001(tb):\n    states = [m.cluster_state() for m in tb.amf.members()]\n    ...' },
      { id: 'frag-5b', name: 'TestSet', source: 'art/1300_amf_cluster/test-1300.4002.py', steps: 1, recommended: false,
        redundantReason: "redundant to test-1300.5001 TestSet — queries a single member's identity rather than full-cluster state.",
        codeLines: 17, code: 'def test_1300_4002(tb):\n    return tb.amf.master().name\n    ...' }
    ]
  };

  const FRAGMENTS_SUMMARY_STEP_ID = '__fragments_summary__';

  // Per sequenced-step fragment groups, keyed by the sequenced step's id — populated by "Gather
  // Fragments (LLM)". Each entry is a fragment list as in mockFragmentGroups above.
  let fragmentGroups = {};

  // Per-step arrays of fragment ids currently ticked for inclusion in Generate — defaults to the
  // recommended fragment(s) but can be overridden independently of the green/red grouping.
  let fragmentSelectedIds = {};

  // Per-step arrays of fragment ids whose code preview is expanded.
  let expandedFragmentIds = {};

  let fragmentActiveStepId = null;
  let confirmedFragmentSteps = [];

  $: {
    if (!fragmentActiveStepId && sequencedTestSteps.length > 0) {
      fragmentActiveStepId = sequencedTestSteps[0].id;
    }
  }

  $: fragmentActiveStep = sequencedTestSteps.find((s) => s.id === fragmentActiveStepId) ?? null;
  $: fragmentActiveStepIndex = sequencedTestSteps.findIndex((s) => s.id === fragmentActiveStepId);

  let fragmentStepStatuses = {};
  $: {
    const next = {};
    for (const step of sequencedTestSteps) {
      if (confirmedFragmentSteps.includes(step.id)) {
        next[step.id] = 'covered';
      } else if (fragmentGroups[step.id]?.length > 0) {
        next[step.id] = 'review';
      } else {
        next[step.id] = 'none';
      }
    }
    fragmentStepStatuses = next;
  }

  $: fragmentsSummaryStatus =
    sequencedTestSteps.length > 0 && sequencedTestSteps.every((s) => confirmedFragmentSteps.includes(s.id))
      ? 'covered'
      : 'none';

  $: fragmentsCoveragePercent =
    sequencedTestSteps.length === 0
      ? 0
      : Math.round(
          (Object.values(fragmentStepStatuses).filter((s) => s === 'covered').length / sequencedTestSteps.length) * 100
        );

  function selectFragmentStep(stepId) {
    fragmentActiveStepId = stepId;
  }

  function gatherFragments() {
    // TODO: replace with a real code-reuse search / LLM call
    for (const step of sequencedTestSteps) {
      if (!fragmentGroups[step.id]) {
        fragmentGroups[step.id] = (mockFragmentGroups[step.id] ?? []).map((f) => ({ ...f }));
        fragmentSelectedIds[step.id] = fragmentGroups[step.id].filter((f) => f.recommended).map((f) => f.id);
        expandedFragmentIds[step.id] = [];
      }
    }
    fragmentGroups = fragmentGroups;
    fragmentSelectedIds = fragmentSelectedIds;
  }

  function toggleFragmentSelected(stepId, fragmentId) {
    const current = fragmentSelectedIds[stepId] ?? [];
    fragmentSelectedIds[stepId] = current.includes(fragmentId)
      ? current.filter((id) => id !== fragmentId)
      : [...current, fragmentId];
    fragmentSelectedIds = fragmentSelectedIds;
  }

  function toggleFragmentExpanded(stepId, fragmentId) {
    const current = expandedFragmentIds[stepId] ?? [];
    expandedFragmentIds[stepId] = current.includes(fragmentId)
      ? current.filter((id) => id !== fragmentId)
      : [...current, fragmentId];
    expandedFragmentIds = expandedFragmentIds;
  }

  function advanceFragmentStep() {
    const updatedConfirmed = confirmedFragmentSteps.includes(fragmentActiveStepId)
      ? confirmedFragmentSteps
      : [...confirmedFragmentSteps, fragmentActiveStepId];
    confirmedFragmentSteps = updatedConfirmed;

    const nextUnconfirmed = sequencedTestSteps.find((s) => !updatedConfirmed.includes(s.id));
    fragmentActiveStepId = nextUnconfirmed ? nextUnconfirmed.id : FRAGMENTS_SUMMARY_STEP_ID;
    scrollToStepIntro();
  }

  function confirmFragmentsAndAdvance() {
    currentStep = 4;
    scrollToTop();
  }

  const GENERATE_SETUP_ID = '__generate_setup__';
  const GENERATE_SUMMARY_STEP_ID = '__generate_summary__';

  // Units for Generate: one "Setup" unit (the TestSet setUp/tearDown pair) followed by one unit
  // per sequenced step (a single TestCase class) — numbering resumes at 1 after Setup.
  $: generateUnits =
    sequencedTestSteps.length > 0
      ? [
          { id: GENERATE_SETUP_ID, label: 'Setup', kind: 'setup', title: 'Setup', detail: 'TestSet setUp/tearDown pair' },
          ...sequencedTestSteps.map((step, i) => ({
            id: step.id,
            label: i + 1,
            kind: 'testcase',
            step,
            title: `Unit ${i + 1}`,
            detail: step.action
          }))
        ]
      : [];

  function defaultPromptForUnit(unit) {
    if (unit.kind === 'setup') {
      return `Generate the TestSet setUp/tearDown pair for "${title}" — bring up the topology (tb/swi_a, tb/swi_b) and configure the AMF cluster baseline every test case below relies on.`;
    }
    return `Generate the TestCase class body for Sequence Step ${unit.label}: ${unit.step.action} Use the scripts/fragments confirmed for this step as the basis, and assert: ${unit.step.verify}`;
  }

  function mockCodeForUnit(unit) {
    // TODO: replace with the real returned code from the LLM call
    if (unit.kind === 'setup') {
      return 'def setUp(self):\n    self.tb = art.topology_init(members=["swi_a", "swi_b"])\n    self.tb.amf.enable()\n\ndef tearDown(self):\n    self.tb.amf.disable()\n    self.tb.cleanup()';
    }
    return `class TestCase_${unit.label}(TestCase):\n    def runTest(self):\n        # ${unit.step.action}\n        ...\n        self.assertTrue(True)  # ${unit.step.verify}`;
  }

  // Per-unit generation state, keyed by the unit's id — populated lazily below.
  let generateState = {};
  let generateActiveUnitId = null;
  let confirmedGenerateUnits = [];

  $: {
    for (const unit of generateUnits) {
      if (!generateState[unit.id]) {
        generateState[unit.id] = { prompt: defaultPromptForUnit(unit), code: '' };
      }
    }
    if (!generateActiveUnitId && generateUnits.length > 0) {
      generateActiveUnitId = generateUnits[0].id;
    }
  }

  $: generateActiveUnit = generateUnits.find((u) => u.id === generateActiveUnitId) ?? null;

  let generateUnitStatuses = {};
  $: {
    const next = {};
    for (const unit of generateUnits) {
      if (confirmedGenerateUnits.includes(unit.id)) {
        next[unit.id] = 'covered';
      } else if (generateState[unit.id]?.code) {
        next[unit.id] = 'review';
      } else {
        next[unit.id] = 'none';
      }
    }
    generateUnitStatuses = next;
  }

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

  function selectGenerateUnit(unitId) {
    generateActiveUnitId = unitId;
  }

  function generateUnitCode(unitId) {
    // TODO: replace with a real LLM call — sends exactly the (possibly edited) prompt text shown
    const unit = generateUnits.find((u) => u.id === unitId);
    generateState[unitId].code = mockCodeForUnit(unit);
    generateState = generateState;
  }

  function generateAllUnits() {
    // TODO: replace with a real LLM call across all units
    for (const unit of generateUnits) {
      if (!generateState[unit.id].code) {
        generateState[unit.id].code = mockCodeForUnit(unit);
      }
    }
    generateState = generateState;
  }

  function advanceGenerateUnit() {
    const updatedConfirmed = confirmedGenerateUnits.includes(generateActiveUnitId)
      ? confirmedGenerateUnits
      : [...confirmedGenerateUnits, generateActiveUnitId];
    confirmedGenerateUnits = updatedConfirmed;

    const nextUnconfirmed = generateUnits.find((u) => !updatedConfirmed.includes(u.id));
    generateActiveUnitId = nextUnconfirmed ? nextUnconfirmed.id : GENERATE_SUMMARY_STEP_ID;
    scrollToStepIntro();
  }

  // The frame (imports, TestSet class, ts.add_testCase() runner) is rendered locally — it cannot
  // vary between units, so it is never sent to or returned from the LLM.
  const GENERATE_FRAME_HEADER = 'import art\nfrom framework import TestSet, TestCase, ts\n\nclass AMF_Master_TestSet(TestSet):';
  const GENERATE_FRAME_FOOTER = '\nts.add_testCase(AMF_Master_TestSet)';

  const GENERATE_REVIEW_STEP_ID = '__generate_review__';

  let assembledCode = '';
  let lintResults = [];
  let assembled = false;

  function assembleAndLint() {
    // TODO: replace with a real local assembly + linter call
    const setupUnit = generateUnits.find((u) => u.kind === 'setup');
    const testCaseUnits = generateUnits.filter((u) => u.kind === 'testcase');
    const indent = (code) => code.split('\n').map((line) => '    ' + line).join('\n');

    assembledCode = [
      GENERATE_FRAME_HEADER,
      indent(generateState[setupUnit.id]?.code ?? ''),
      '',
      testCaseUnits.map((u) => indent(generateState[u.id]?.code ?? '')).join('\n\n'),
      GENERATE_FRAME_FOOTER
    ].join('\n');

    lintResults = [
      { level: 'pass', message: 'No unused imports.' },
      { level: 'pass', message: 'Every TestCase class is registered via ts.add_testCase().' },
      { level: 'warn', message: 'Line 14: assertion message could be more descriptive.' }
    ];

    assembled = true;
  }

  function confirmAndReviewGenerate() {
    generateActiveUnitId = GENERATE_REVIEW_STEP_ID;
    scrollToStepIntro();
  }

  // 'review' once there's an assembled script to look at — Review/Fix has no further "covered"
  // state of its own since finishing it means leaving the Generate step entirely.
  $: generateReviewStatus = assembled ? 'review' : 'none';

  let scriptFeedback = '';
  let showScriptFeedback = false;

  function reviewWithLlm() {
    // TODO: replace with a real holistic-review LLM call
    scriptFeedback =
      "The assembled script consistently uses the AMF cluster fixtures established in setUp() across every TestCase, and the assertions map cleanly back to each sequence step's verify condition. No cross-step ordering issues detected.";
    showScriptFeedback = true;
  }

  // Both "fix" actions invalidate the current assembly/lint/review and send the user back to
  // Summary — Fix Units additionally un-confirms every unit (the LLM is regenerating their code,
  // so each needs re-reviewing), while Fix Whole Script patches the assembled script directly and
  // leaves already-confirmed units alone. Either way, Assemble & Lint (and then Review with LLM)
  // must be run again before Review/Fix can be reached in a usable state.
  function backToSummaryForFix() {
    assembled = false;
    assembledCode = '';
    lintResults = [];
    scriptFeedback = '';
    showScriptFeedback = false;
    generateActiveUnitId = GENERATE_SUMMARY_STEP_ID;
    scrollToTop();
  }

  function fixUnitsWithLlm() {
    // TODO: replace with a real per-unit LLM fix call
    confirmedGenerateUnits = [];
    backToSummaryForFix();
  }

  function fixWholeScriptWithLlm() {
    // TODO: replace with a real whole-script LLM fix call
    backToSummaryForFix();
  }

  function saveAndFinish() {
    currentStep = 5;
    scrollToTop();
  }
</script>

<ToolHeader title={title} tool="PYTEST CREATOR" icon={pyTestIcon} />

<Stepper {steps} {currentStep} {maxStepReached} onStepClick={goToStep} />

<div class="tool-page">
  {#if currentStep === 0}
    <CasePicker {openPartialCases} {completeCases} onLoad={loadAndConfirm} onExport={exportSession} />
  {:else if currentStep === 1}
    <p class="step-intro">The refined case's test steps are shown first (the "before"). Extract Sequence asks the LLM to convert them into a prescriptive, runnable execution order (the "after") — the From column links each extracted row back to its source step so any re-sequencing is visible. Review/edit, then confirm.</p>

    <p class="step-table-label">Test Steps (Manual)</p>
    <Table columns={manualColumns} rows={manualTestSteps} selectable={false} />

    <div class="step-actions">
      <Button variant="primary" sparkle on:click={extractSequence}>Extract Sequence (LLM)</Button>
    </div>

    <p class="step-table-label">Test Steps (Sequenced)</p>

    <SequenceTable
      bind:rows={sequencedTestSteps}
    />

    <div class="step-actions">
      <Button variant="primary" disabled={sequencedTestSteps.length === 0} on:click={reviewAndConfirmSequence}>Review &amp; Confirm</Button>
    </div>
  {:else if currentStep === 2}
    <p class="step-intro">Find reusable scripts per sequence step so it's clear every step is covered. Page through the steps; for each, use its own Suggest (LLM) or keyword search to find scripts and choose the ones to reuse. Each step must be confirmed before being able to move on.</p>

    <div class="arrow-step-row">
      {#each sequencedTestSteps as step, i (step.id)}
        <ArrowStep
          label={i + 1}
          status={stepStatuses[step.id] ?? 'none'}
          active={activeStepId === step.id}
          onClick={() => selectStep(step.id)}
        />
      {/each}
      {#if sequencedTestSteps.length > 0}
        <ArrowStep
          label="Summary"
          wide={true}
          status={summaryStatus}
          active={activeStepId === SUMMARY_STEP_ID}
          onClick={() => selectStep(SUMMARY_STEP_ID)}
        />
      {/if}
    </div>

    <div class="script-search-toolbar">
      <Button variant="primary" sparkle disabled={sequencedTestSteps.length === 0} on:click={suggestAllSteps}>Suggest All Steps (LLM)</Button>
      <div class="script-search-progress" role="progressbar" aria-valuenow={coveragePercent} aria-valuemin="0" aria-valuemax="100">
        <div class="script-search-progress-fill" style="width: {coveragePercent}%"></div>
      </div>
    </div>
    <div class="step-frame">
      {#if activeStepId === SUMMARY_STEP_ID}
        <p class="step-table-label summary-title">Sequence Step Summary</p>
        <div class="script-summary">
          {#each sequencedTestSteps as step, i (step.id)}
            <div class="script-summary-section">
              <div class="sequence-step-summary">
                <span
                  class="step-status-badge"
                  class:covered={stepStatuses[step.id] === 'covered'}
                  class:review={stepStatuses[step.id] === 'review'}
                  class:none={stepStatuses[step.id] === 'none'}
                  aria-hidden="true"
                >
                  {stepStatuses[step.id] === 'covered' ? '✓' : stepStatuses[step.id] === 'review' ? '!' : '–'}
                </span>
                <p><strong>Sequence Step {i + 1}</strong> - {step.action}</p>
              </div>
              <Table columns={scriptColumns} rows={scriptSearchState[step.id]?.chosen ?? []} selectable={false} />
            </div>
          {/each}
        </div>

        <div class="step-actions">
          <Button variant="primary" disabled={summaryStatus !== 'covered'} on:click={confirmScriptSearchAndAdvance}>Review &amp; Confirm</Button>
        </div>
      {:else if activeStep}
        <div class="sequence-step-summary">
          <span
            class="step-status-badge"
            class:covered={stepStatuses[activeStep.id] === 'covered'}
            class:review={stepStatuses[activeStep.id] === 'review'}
            class:none={stepStatuses[activeStep.id] === 'none'}
            aria-hidden="true"
          >
            {stepStatuses[activeStep.id] === 'covered' ? '✓' : stepStatuses[activeStep.id] === 'review' ? '!' : '–'}
          </span>
          <p><strong>Sequence Step {activeStepIndex + 1}</strong> - {activeStep.action}</p>
        </div>

        <div class="step-actions">
          <SearchBox
            bind:value={scriptSearchState[activeStepId].search}
            placeholder="Search scripts by keyword…"
            buttonLabel="Search"
            onSearch={() => searchForStep(activeStep.id)}
          />
          <Button variant="primary" sparkle on:click={() => suggestForStep(activeStep.id)}>Suggest for Step {activeStepIndex + 1} (LLM)</Button>
        </div>

        <p class="step-table-label">Candidates — tick rows and choose to shortlist them for this step</p>
        <Table columns={scriptColumns} rows={scriptSearchState[activeStepId].candidates} bind:selected={scriptSearchState[activeStepId].selectedCandidateIds} />

        <div class="testlink-choose-actions">
          <Button variant="outline" on:click={() => chooseSelectedForStep(activeStep.id)}>↓ Choose selected</Button>
        </div>

        <p class="step-table-label">Chosen for this sequence step</p>
        <Table columns={scriptColumns} rows={scriptSearchState[activeStepId].chosen} bind:selected={scriptSearchState[activeStepId].selectedChosenIds} flashIds={flashChosenIds} />

        <div class="testlink-final-actions">
          <Button variant="outline" on:click={() => clearSelectedForStep(activeStep.id)}>Clear Selected</Button>
          <Button variant="outline" on:click={() => clearAllForStep(activeStep.id)}>Clear All</Button>
        </div>

        <div class="step-actions">
          <Button variant="primary" on:click={handleConfirmScriptsClick}>Confirm Scripts</Button>
        </div>

        <ConfirmModal
          bind:open={showNoScriptsModal}
          title="No scripts chosen"
          message="You haven't chosen any scripts for this sequence step. Continue anyway?"
          confirmText="Continue"
          cancelText="Cancel"
          onConfirm={advanceScriptSearchStep}
        />
      {/if}
      
    </div>


  {:else if currentStep === 3}
    <p class="step-intro">Re-use real code from the selected scripts, reviewed per sequence step. Gather Fragments (LLM) proposes, for each step, the fragment(s) worth reusing (green) plus the redundant alternatives it was preferred over (red, nested below) — so the accounting of every candidate is visible. Page through the steps; tick a fragment to include it in Generate (untick a green one or tick a red one to override). Save, then confirm.</p>

    <div class="arrow-step-row">
      {#each sequencedTestSteps as step, i (step.id)}
        <ArrowStep
          label={i + 1}
          status={fragmentStepStatuses[step.id] ?? 'none'}
          active={fragmentActiveStepId === step.id}
          onClick={() => selectFragmentStep(step.id)}
        />
      {/each}
      {#if sequencedTestSteps.length > 0}
        <ArrowStep
          label="Summary"
          wide={true}
          status={fragmentsSummaryStatus}
          active={fragmentActiveStepId === FRAGMENTS_SUMMARY_STEP_ID}
          onClick={() => selectFragmentStep(FRAGMENTS_SUMMARY_STEP_ID)}
        />
      {/if}
    </div>

    <div class="script-search-toolbar">
      <Button variant="primary" sparkle disabled={sequencedTestSteps.length === 0} on:click={gatherFragments}>Gather Fragments (LLM)</Button>
      <div class="script-search-progress" role="progressbar" aria-valuenow={fragmentsCoveragePercent} aria-valuemin="0" aria-valuemax="100">
        <div class="script-search-progress-fill" style="width: {fragmentsCoveragePercent}%"></div>
      </div>
    </div>
    <div class="step-frame">
      {#if fragmentActiveStepId === FRAGMENTS_SUMMARY_STEP_ID}
        <p class="step-table-label summary-title">Sequence Step Summary</p>
        <div class="script-summary">
          {#each sequencedTestSteps as step, i (step.id)}
            <div class="script-summary-section">
              <div class="sequence-step-summary">
                <span
                  class="step-status-badge"
                  class:covered={fragmentStepStatuses[step.id] === 'covered'}
                  class:review={fragmentStepStatuses[step.id] === 'review'}
                  class:none={fragmentStepStatuses[step.id] === 'none'}
                  aria-hidden="true"
                >
                  {fragmentStepStatuses[step.id] === 'covered' ? '✓' : fragmentStepStatuses[step.id] === 'review' ? '!' : '–'}
                </span>
                <p><strong>Sequence Step {i + 1}</strong> - {step.action}</p>
              </div>
              <div class="fragment-summary-list">
                {#each (fragmentGroups[step.id] ?? []).filter((f) => (fragmentSelectedIds[step.id] ?? []).includes(f.id)) as frag (frag.id)}
                  <p class="fragment-summary-row"><code>{frag.name} — {frag.source}</code></p>
                {:else}
                  <p class="fragment-summary-row fragment-summary-empty">No fragments selected for this step.</p>
                {/each}
              </div>
            </div>
          {/each}
        </div>

        <div class="step-actions">
          <Button variant="primary" disabled={fragmentsSummaryStatus !== 'covered'} on:click={confirmFragmentsAndAdvance}>Review &amp; Confirm</Button>
        </div>
      {:else if fragmentActiveStep}
        <div class="sequence-step-summary">
          <span
            class="step-status-badge"
            class:covered={fragmentStepStatuses[fragmentActiveStep.id] === 'covered'}
            class:review={fragmentStepStatuses[fragmentActiveStep.id] === 'review'}
            class:none={fragmentStepStatuses[fragmentActiveStep.id] === 'none'}
            aria-hidden="true"
          >
            {fragmentStepStatuses[fragmentActiveStep.id] === 'covered' ? '✓' : fragmentStepStatuses[fragmentActiveStep.id] === 'review' ? '!' : '–'}
          </span>
          <p><strong>Sequence Step {fragmentActiveStepIndex + 1}</strong> - {fragmentActiveStep.action}</p>
        </div>

        <div class="fragment-groups">
          {#each (fragmentGroups[fragmentActiveStepId] ?? []).filter((f) => f.recommended) as frag (frag.id)}
            <FragmentCard
              fragment={frag}
              recommended={true}
              selected={(fragmentSelectedIds[fragmentActiveStepId] ?? []).includes(frag.id)}
              expanded={(expandedFragmentIds[fragmentActiveStepId] ?? []).includes(frag.id)}
              onToggleSelected={() => toggleFragmentSelected(fragmentActiveStepId, frag.id)}
              onToggleExpanded={() => toggleFragmentExpanded(fragmentActiveStepId, frag.id)}
            />
          {/each}

          {#if (fragmentGroups[fragmentActiveStepId] ?? []).some((f) => !f.recommended)}
            <p class="fragment-redundant-label">Not selected — redundant to the above:</p>
            <div class="fragment-redundant-group">
              {#each (fragmentGroups[fragmentActiveStepId] ?? []).filter((f) => !f.recommended) as frag (frag.id)}
                <FragmentCard
                  fragment={frag}
                  recommended={false}
                  selected={(fragmentSelectedIds[fragmentActiveStepId] ?? []).includes(frag.id)}
                  expanded={(expandedFragmentIds[fragmentActiveStepId] ?? []).includes(frag.id)}
                  onToggleSelected={() => toggleFragmentSelected(fragmentActiveStepId, frag.id)}
                  onToggleExpanded={() => toggleFragmentExpanded(fragmentActiveStepId, frag.id)}
                />
              {/each}
            </div>
          {/if}

          {#if !(fragmentGroups[fragmentActiveStepId]?.length)}
            <p class="fragment-empty">No fragments gathered yet. Click "Gather Fragments (LLM)" above.</p>
          {/if}
        </div>

        <div class="step-actions">
          <Button variant="primary" disabled={!(fragmentGroups[fragmentActiveStepId]?.length)} on:click={advanceFragmentStep}>Confirm Fragments</Button>
        </div>
      {/if}
    </div>
  {:else if currentStep === 4}
    <p class="step-intro">Generated one unit at a time — a unit is a single TestCase class, or the TestSet setup pair. The frame (imports, TestSet, the ts.add_testCase() runner) is rendered here, not by an LLM, so it cannot vary between units. Page through the units: each shows the prompt that will be sent (editable — the button sends what you see) and the code that came back. Summary assembles them locally and lints the result; Review/Fix then runs the holistic LLM review and lets you send fixes back for another pass before you save and finish.</p>

    <div class="arrow-step-row">
      {#each generateUnits as unit (unit.id)}
        <ArrowStep
          label={unit.label}
          wide={unit.kind === 'setup'}
          status={generateUnitStatuses[unit.id] ?? 'none'}
          active={generateActiveUnitId === unit.id}
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
      <Button variant="primary" sparkle disabled={generateUnits.length === 0} on:click={generateAllUnits}>Generate All Units (LLM)</Button>
      <div class="script-search-progress" role="progressbar" aria-valuenow={generateCoveragePercent} aria-valuemin="0" aria-valuemax="100">
        <div class="script-search-progress-fill" style="width: {generateCoveragePercent}%"></div>
      </div>
    </div>
    <div class="step-frame">
      {#if generateActiveUnitId === GENERATE_SUMMARY_STEP_ID}
        <p class="step-table-label summary-title">Sequence Step Summary</p>
        <div class="script-summary">
          {#each generateUnits as unit (unit.id)}
            <div class="script-summary-section">
              <div class="sequence-step-summary">
                <span
                  class="step-status-badge"
                  class:covered={generateUnitStatuses[unit.id] === 'covered'}
                  class:review={generateUnitStatuses[unit.id] === 'review'}
                  class:none={generateUnitStatuses[unit.id] === 'none'}
                  aria-hidden="true"
                >
                  {generateUnitStatuses[unit.id] === 'covered' ? '✓' : generateUnitStatuses[unit.id] === 'review' ? '!' : '–'}
                </span>
                <p><strong>{unit.title}</strong> - {unit.detail}</p>
              </div>
            </div>
          {/each}
        </div>

        <div class="step-actions">
          <Button variant="primary" disabled={generateSummaryStatus !== 'covered'} on:click={assembleAndLint}>Assemble &amp; Lint</Button>
        </div>

        <p class="step-table-label">Assembled Script</p>
        <div class="generate-assembled-editor">
          <EditableField
            type="code"
            bind:value={assembledCode}
            placeholder={'Not assembled yet. Click "Assemble & Lint" above.'}
            height="420px"
          />
        </div>

        {#if assembled}
          <p class="step-table-label">Lint Results</p>
          <ul class="lint-results">
            {#each lintResults as result}
              <li class="lint-result" class:lint-pass={result.level === 'pass'} class:lint-warn={result.level === 'warn'}>{result.message}</li>
            {/each}
          </ul>
        {/if}

        <div class="step-actions">
          <Button variant="primary" disabled={!assembled} on:click={confirmAndReviewGenerate}>Confirm &amp; Review</Button>
        </div>
      {:else if generateActiveUnit}
        <div class="sequence-step-summary">
          <span
            class="step-status-badge"
            class:covered={generateUnitStatuses[generateActiveUnit.id] === 'covered'}
            class:review={generateUnitStatuses[generateActiveUnit.id] === 'review'}
            class:none={generateUnitStatuses[generateActiveUnit.id] === 'none'}
            aria-hidden="true"
          >
            {generateUnitStatuses[generateActiveUnit.id] === 'covered' ? '✓' : generateUnitStatuses[generateActiveUnit.id] === 'review' ? '!' : '–'}
          </span>
          <p><strong>{generateActiveUnit.title}</strong> - {generateActiveUnit.detail}</p>
        </div>
        <div class="step-generate">
          <Button variant="primary" sparkle on:click={() => generateUnitCode(generateActiveUnitId)}>Generate (LLM)</Button>
        </div>
        <div class="generate-panes">
          <div class="generate-pane generate-pane-prompt">
            <p class="step-table-label">Prompt — editable, sent as shown</p>
            {#key generateActiveUnitId}
              <EditableField type="text" bind:value={generateState[generateActiveUnitId].prompt} />
            {/key}
          </div>
          <div class="generate-pane generate-pane-code">
            <p class="step-table-label">Generated Code</p>
            {#key generateActiveUnitId}
              <EditableField
                type="code"
                bind:value={generateState[generateActiveUnitId].code}
                placeholder={'Not generated yet. Click the "Generate (LLM)" button above.'}
              />
            {/key}
          </div>
        </div>

        <div class="step-actions">
          <Button variant="primary" disabled={!generateState[generateActiveUnitId].code} on:click={advanceGenerateUnit}>Confirm Unit</Button>
        </div>
      {:else if generateActiveUnitId === GENERATE_REVIEW_STEP_ID}
        <p class="step-table-label">Assembled Script</p>
        <div class="generate-assembled-editor">
          <EditableField
            type="code"
            bind:value={assembledCode}
            placeholder={'Not assembled yet. Assemble & Lint on the Summary step first.'}
            height="420px"
          />
        </div>

        {#if !assembled}
          <p class="fragment-empty">Assemble &amp; Lint the script on the Summary step first.</p>
        {:else}
          <div class="step-actions">
            <Button variant="primary" sparkle on:click={reviewWithLlm}>Review with LLM</Button>
          </div>

          {#if showScriptFeedback}
            <p class="step-table-label">Script Feedback (LLM)</p>
            <div class="feedback-window">
              <p class="holistic-review">{scriptFeedback}</p>
            </div>
            <div class="step-actions">
              <Button variant="primary" sparkle on:click={fixUnitsWithLlm}>Fix Units (LLM)</Button>
              <Button variant="primary" sparkle on:click={fixWholeScriptWithLlm}>Fix Whole Script (LLM)</Button>
            </div>
            <div class="step-actions">
              <Button variant="success" on:click={saveAndFinish}>Save and Finish</Button>
            </div>
          {/if}
        {/if}
      {/if}
    </div>
  {:else}
    <UnderConstruction />
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

  .summary-title {
    margin-bottom: 22px;
  }

  .step-actions {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 16px 0 32px;
  }

  .arrow-step-row {
    display: flex;
    flex-wrap: wrap;
    width: 100%;
    gap: 16px;
    padding: 5px 20px 8px;
    border-top: 1px solid var(--color-border-surface);
    border-bottom: 1px solid var(--color-border-surface);

    /* border-radius: 10px; */
    /* background: var(--color-table-header-bg); */
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
    /* background: var(--color-bg-shell); */
    border-radius: 8px;
    padding: 24px 24px 0px 24px;
    width: 100%;
    /* min-height: 28rem; */
  }

  .feedback-window {
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

  .sequence-step-summary {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 10px;
    /* margin-left: 24px; */
  }

  .sequence-step-summary p {
    margin: 0;
    color: var(--color-text);
    font-size: 0.94rem;
  }

  .step-status-badge {
    flex: 0 0 auto;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    color: #fff;
    font-size: 0.75rem;
    font-weight: 700;
    margin-top: 2px;
  }

  .step-status-badge.covered {
    background: var(--color-success);
  }

  .step-status-badge.review {
    background: var(--color-warning);
  }

  .step-status-badge.none {
    background: var(--color-text-muted);
  }

  .step-generate {
    padding-bottom: 20px;
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

  .script-summary {
    display: flex;
    flex-direction: column;
    gap: 24px;
    width: 100%;
  }

  .fragment-groups {
    display: flex;
    flex-direction: column;
    gap: 12px;
    width: 100%;
  }

  .fragment-redundant-label {
    margin: 4px 0 0 4px;
    font-size: 0.85rem;
    font-style: italic;
    color: var(--color-error);
  }

  .fragment-redundant-group {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-left: 14px;
    padding-left: 16px;
    border-left: 2px dashed var(--color-error);
  }

  .fragment-empty {
    margin: 0;
    color: var(--color-text-muted);
    font-size: 0.94rem;
  }

  .fragment-summary-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .fragment-summary-row {
    margin: 0;
    color: var(--color-text);
    font-size: 0.9rem;
    margin-left: 3rem;
  }

  .fragment-summary-empty {
    color: var(--color-text-muted);
    font-style: italic;
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

  .holistic-review {
    margin: 0 0 24px;
    color: var(--color-text);
    font-size: 0.94rem;
    line-height: 1.6;
  }
</style>

