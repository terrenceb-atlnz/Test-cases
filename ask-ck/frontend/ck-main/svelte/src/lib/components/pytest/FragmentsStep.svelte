<script>
// @ts-nocheck

  import ArrowStep from '../ArrowStep.svelte';
  import Button from '../Button.svelte';
  import FragmentCard from '../FragmentCard.svelte';
  import { scrollToTop, scrollToStepIntro } from '../../utils/scroll.js';

  /** @type {Array<{ id: string, action: string, verify: string }>} Read-only */
  export let sequencedTestSteps = [];

  /** @type {(stepIds: string[]) => Promise<Record<string, Array>>} */
  export let onGatherFragments = async () => ({});

  /** @type {(() => void) | null} Called when Review & Confirm is clicked on the Summary panel */
  export let onConfirm = null;

  const FRAGMENTS_SUMMARY_STEP_ID = '__fragments_summary__';

  // Per sequenced-step fragment groups, keyed by the sequenced step's id — populated by "Gather
  // Fragments (LLM)". Each entry is a fragment list.
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

  let isGatheringFragments = false;

  async function gatherFragments() {
    isGatheringFragments = true;
    try {
      const missingIds = sequencedTestSteps.filter((s) => !fragmentGroups[s.id]).map((s) => s.id);
      const groups = await onGatherFragments(missingIds);
      for (const id of missingIds) {
        fragmentGroups[id] = groups[id] ?? [];
        fragmentSelectedIds[id] = fragmentGroups[id].filter((f) => f.recommended).map((f) => f.id);
        expandedFragmentIds[id] = [];
      }
      fragmentGroups = fragmentGroups;
      fragmentSelectedIds = fragmentSelectedIds;
    } finally {
      isGatheringFragments = false;
    }
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

  function handleConfirm() {
    onConfirm && onConfirm();
  }
</script>

<p class="step-intro">Re-use real code from the selected scripts, reviewed per sequence step. Gather Fragments (LLM) proposes, for each step, the fragment(s) worth reusing (green) plus the redundant alternatives it was preferred over (red, nested below) — so the accounting of every candidate is visible. Page through the steps; tick a fragment to include it in Generate (untick a green one or tick a red one to override). Save, then confirm.</p>

<div class="arrow-step-row">
  {#each sequencedTestSteps as step, i (step.id)}
    <ArrowStep
      label={i + 1}
      status={fragmentStepStatuses[step.id] ?? 'none'}
      active={fragmentActiveStepId === step.id}
      loading={isGatheringFragments}
      onClick={() => selectFragmentStep(step.id)}
    />
  {/each}
  {#if sequencedTestSteps.length > 0}
    <ArrowStep
      label="Summary"
      wide={true}
      status={fragmentsSummaryStatus}
      active={fragmentActiveStepId === FRAGMENTS_SUMMARY_STEP_ID}
      loading={isGatheringFragments}
      onClick={() => selectFragmentStep(FRAGMENTS_SUMMARY_STEP_ID)}
    />
  {/if}
</div>

<div class="script-search-toolbar">
  <Button variant="primary" sparkle disabled={sequencedTestSteps.length === 0} loading={isGatheringFragments} on:click={gatherFragments}>Gather Fragments (LLM)</Button>
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
      <Button variant="primary" disabled={fragmentsSummaryStatus !== 'covered'} on:click={handleConfirm}>Review &amp; Confirm</Button>
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
</style>
