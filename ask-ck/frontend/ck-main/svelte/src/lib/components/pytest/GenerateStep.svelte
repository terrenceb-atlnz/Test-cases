<script>
// @ts-nocheck

  import ArrowStep from '../ArrowStep.svelte';
  import Button from '../Button.svelte';
  import EditableField from '../EditableField.svelte';
  import ConfirmModal from '../ConfirmModal.svelte';
  import StatusModal from '../StatusModal.svelte';
  import { scrollToTop, scrollToStepIntro } from '../../utils/scroll.js';
  import { defaultPromptForUnit } from '../../services/pytest/generateService.js';

  /** @type {Array<{ id: string, action: string, verify: string }>} Read-only */
  export let sequencedTestSteps = [];

  /** @type {string} Read-only — used in the default per-unit prompt text */
  export let title = '';

  /** @type {(unit: object) => Promise<string>} */
  export let onGenerateUnit = async () => '';

  /** @type {(units: Array) => Promise<Record<string, string>>} */
  export let onGenerateAllUnits = async () => ({});

  /** @type {(generateUnits: Array, generateState: object) => { assembledCode: string, lintResults: Array }} */
  export let onAssemble = () => ({ assembledCode: '', lintResults: [] });

  /** @type {() => Promise<string>} */
  export let onReview = async () => '';

  /** @type {() => Promise<void>} */
  export let onFixUnits = async () => {};

  /** @type {() => Promise<void>} */
  export let onFixWholeScript = async () => {};

  /** @type {() => Promise<{ status: string, message: string }>} */
  export let onSave = async () => ({ status: 'success', message: '' });

  /** @type {((pageId: string) => void) | null} */
  export let onNavigate = null;

  /** @type {((caseId?: string | null) => void) | null} */
  export let onCreateAnother = null;

  /** @type {(() => void) | null} Called once the save succeeds — parent marks the stepper finished */
  export let onFinished = null;

  const GENERATE_SETUP_ID = '__generate_setup__';
  const GENERATE_SUMMARY_STEP_ID = '__generate_summary__';
  const GENERATE_REVIEW_STEP_ID = '__generate_review__';

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

  // Per-unit generation state, keyed by the unit's id — populated lazily below.
  let generateState = {};
  let generateActiveUnitId = null;
  let confirmedGenerateUnits = [];

  $: {
    for (const unit of generateUnits) {
      if (!generateState[unit.id]) {
        generateState[unit.id] = { prompt: defaultPromptForUnit(unit, title), code: '' };
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

  let isGeneratingUnit = false;

  async function generateUnitCode(unitId) {
    isGeneratingUnit = true;
    try {
      const unit = generateUnits.find((u) => u.id === unitId);
      generateState[unitId].code = await onGenerateUnit(unit);
      generateState = generateState;
    } finally {
      isGeneratingUnit = false;
    }
  }

  let isGeneratingAllUnits = false;

  async function generateAllUnits() {
    isGeneratingAllUnits = true;
    try {
      const missing = generateUnits.filter((u) => !generateState[u.id].code);
      const codeByUnitId = await onGenerateAllUnits(missing);
      for (const unit of missing) {
        generateState[unit.id].code = codeByUnitId[unit.id];
      }
      generateState = generateState;
    } finally {
      isGeneratingAllUnits = false;
    }
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

  let assembledCode = '';
  let lintResults = [];
  let assembled = false;

  function assembleAndLint() {
    const result = onAssemble(generateUnits, generateState);
    assembledCode = result.assembledCode;
    lintResults = result.lintResults;
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
  let isReviewingWithLlm = false;

  async function reviewWithLlm() {
    isReviewingWithLlm = true;
    try {
      scriptFeedback = await onReview();
      showScriptFeedback = true;
    } finally {
      isReviewingWithLlm = false;
    }
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

  let isFixingUnits = false;

  async function fixUnitsWithLlm() {
    isFixingUnits = true;
    try {
      await onFixUnits();
      confirmedGenerateUnits = [];
      backToSummaryForFix();
    } finally {
      isFixingUnits = false;
    }
  }

  let showFixWholeScriptModal = false;

  function handleFixWholeScriptClick() {
    showFixWholeScriptModal = true;
  }

  let isFixingWholeScript = false;

  async function fixWholeScriptWithLlm() {
    isFixingWholeScript = true;
    try {
      await onFixWholeScript();
      backToSummaryForFix();
    } finally {
      isFixingWholeScript = false;
    }
  }

  // Any LLM call in flight anywhere on the Generate step (a unit, the batch generate, the
  // holistic review, or either fix) puts every arrow in its row into the loading state.
  $: generateRowLoading =
    isGeneratingUnit || isGeneratingAllUnits || isReviewingWithLlm || isFixingUnits || isFixingWholeScript;

  let showSaveModal = false;
  let saveStatus = 'success';
  let saveStatusMessage = '';
  let isSaving = false;

  async function saveAndFinish() {
    isSaving = true;
    try {
      const result = await onSave();
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

<p class="step-intro">Generated one unit at a time — a unit is a single TestCase class, or the TestSet setup pair. The frame (imports, TestSet, the ts.add_testCase() runner) is rendered here, not by an LLM, so it cannot vary between units. Page through the units: each shows the prompt that will be sent (editable — the button sends what you see) and the code that came back. Summary assembles them locally and lints the result; Review/Fix then runs the holistic LLM review and lets you send fixes back for another pass before you save and finish.</p>

<div class="arrow-step-row">
  {#each generateUnits as unit (unit.id)}
    <ArrowStep
      label={unit.label}
      wide={unit.kind === 'setup'}
      status={generateUnitStatuses[unit.id] ?? 'none'}
      active={generateActiveUnitId === unit.id}
      loading={generateRowLoading}
      onClick={() => selectGenerateUnit(unit.id)}
    />
  {/each}
  {#if generateUnits.length > 0}
    <ArrowStep
      label="Summary"
      wide={true}
      status={generateSummaryStatus}
      active={generateActiveUnitId === GENERATE_SUMMARY_STEP_ID}
      loading={generateRowLoading}
      onClick={() => selectGenerateUnit(GENERATE_SUMMARY_STEP_ID)}
    />
    <ArrowStep
      label="Review/Fix"
      wide={true}
      status={generateReviewStatus}
      active={generateActiveUnitId === GENERATE_REVIEW_STEP_ID}
      loading={generateRowLoading}
      onClick={() => selectGenerateUnit(GENERATE_REVIEW_STEP_ID)}
    />
  {/if}
</div>

<div class="script-search-toolbar">
  <Button variant="primary" sparkle disabled={generateUnits.length === 0} loading={isGeneratingAllUnits} on:click={generateAllUnits}>Generate All Units (LLM)</Button>
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
      <Button variant="primary" sparkle loading={isGeneratingUnit} on:click={() => generateUnitCode(generateActiveUnitId)}>Generate (LLM)</Button>
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
        <Button variant="primary" sparkle loading={isReviewingWithLlm} on:click={reviewWithLlm}>Review with LLM</Button>
      </div>

      {#if showScriptFeedback}
        <p class="step-table-label">Script Feedback (LLM)</p>
        <div class="feedback-window">
          <p class="holistic-review">{scriptFeedback}</p>
        </div>
        <div class="step-actions">
          <Button variant="primary" sparkle loading={isFixingUnits} on:click={fixUnitsWithLlm}>Fix Units (LLM)</Button>
          <Button variant="primary" sparkle loading={isFixingWholeScript} on:click={handleFixWholeScriptClick}>Fix Whole Script (LLM)</Button>
        </div>
        <div class="step-actions">
          <Button variant="success" loading={isSaving} on:click={saveAndFinish}>Save and Finish</Button>
        </div>

        <ConfirmModal
          bind:open={showFixWholeScriptModal}
          title="Warning"
          message="Fixing the whole script could exhaust a large portion of your AI token usage. Would you still like to continue?"
          confirmText="Continue"
          cancelText="Cancel"
          onConfirm={fixWholeScriptWithLlm}
        />

        <StatusModal
          bind:open={showSaveModal}
          status={saveStatus}
          title={saveStatus === 'success' ? 'Save successful' : 'Save failed'}
          message={saveStatusMessage}
          closeText="Close"
        >
          <svelte:fragment slot="actions">
            <Button variant="outline" on:click={createAnotherPytest}>Create Another PyTest</Button>
            <Button variant="outline" on:click={goToComposer}>Compose Test</Button>
          </svelte:fragment>
        </StatusModal>
      {/if}
    {/if}
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

  .script-summary {
    display: flex;
    flex-direction: column;
    gap: 24px;
    width: 100%;
  }

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

  .holistic-review {
    margin: 0 0 24px;
    color: var(--color-text);
    font-size: 0.94rem;
    line-height: 1.6;
  }
</style>
