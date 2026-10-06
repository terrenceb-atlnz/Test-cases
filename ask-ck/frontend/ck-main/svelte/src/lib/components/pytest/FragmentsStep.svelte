<script>
// @ts-nocheck

  import ArrowStep from '../ArrowStep.svelte';
  import Button from '../Button.svelte';
  import FragmentCard from '../FragmentCard.svelte';
  import { scrollToTop, scrollToStepIntro } from '../../utils/scroll.js';

  /** @type {Array<{ id: string, action: string, verify: string }>} Read-only */
  export let sequencedTestSteps = [];

  /** @type {() => Promise<{fragments: Array, selected: Array, accounting: Object}>} Whole-case
      call — gather_fragments has no step-id concept, it gathers against every script chosen in
      Script Search at once. */
  export let onGatherFragments = async () => ({});

  /** @type {(keep: Array<{source_id: string, symbol: string}>) => Promise<void>} Persists the
      selected fragments — called once, from the Summary panel's Review & Confirm (matches
      ScriptSearchStep's onSaveMatches: save once at the end, not on every per-step advance). */
  export let onSaveFragments = async () => {};

  /** @type {(() => void) | null} Called when Review & Confirm is clicked on the Summary panel */
  export let onConfirm = null;

  const FRAGMENTS_SUMMARY_STEP_ID = '__fragments_summary__';

  // Flat pool — one entry per unique (source_id, symbol), same shape gather_fragments returns.
  let fragmentPool = [];

  // Flat list of selected fragment keys ("source_id||symbol") — global, not per-step, since
  // one fragment's maps_to can cover several sequence steps at once.
  let selectedKeys = [];

  // Server-built {stepN (string): [{chosen: [source_id, symbol], redundant: [{key, why}]}]} —
  // kept exactly as gather_fragments returns it, not reshaped.
  let accounting = {};

  // Expand/collapse is a pure UI nicety with no server equivalent (current/ just uses a native
  // <details> element) — flat by fragment key is simplest, since a fragment's own code doesn't
  // change depending on which step you're viewing it from.
  let expandedKeys = [];

  // PORTED FROM current/pytest-creator/pytest.js's _fragKey/_keyOf — fragment identity is the
  // composite (source_id, symbol), not a flat id.
  function fragKey(f) {
    return `${f.source_id}||${f.symbol}`;
  }

  // Fragments mapping to step n via maps_to (the "leftover, not in accounting" case — legacy/
  // stale gathers with no accounting entry, or manually-relevant fragments).
  function fragmentsForStep(n) {
    return fragmentPool.filter((f) => (f.maps_to || []).includes(n));
  }

  // Everything shown under step n: accounting's chosen+redundant entries, plus any maps_to
  // fragment the accounting didn't place at all. PORTED FROM current/'s _fragKeysForStep (minus
  // the flattening to a Set of keys — the render pass in a later step needs the chosen/redundant
  // structure intact, not just a flat key list).
  function entriesForStep(n) {
    return accounting[String(n)] || [];
  }

  function fragByKey(key) {
    return fragmentPool.find((f) => fragKey(f) === key);
  }

  // Resolve step n's accounting entries + maps_to leftovers into actual fragment objects, in
  // the same order current/'s ptRenderFragSteps renders them: each chosen fragment immediately
  // followed by its own nested redundant alternatives, then any leftover maps_to fragment the
  // accounting never placed. Called directly from the template (not wrapped in a `$:` reactive
  // declaration) so it re-resolves on every render without needing fragmentPool/accounting
  // listed as explicit dependencies — the same dependency-tracking gap `fragmentStepStatuses`
  // above has to work around with `void` references doesn't apply to markup expressions.
  function cardsForStep(n) {
    const cards = [];
    const shown = new Set();
    for (const entry of entriesForStep(n)) {
      const chosenKey = (entry.chosen || []).join('||');
      const chosenFrag = fragByKey(chosenKey);
      if (chosenFrag) {
        cards.push({ frag: chosenFrag, recommended: true });
        shown.add(chosenKey);
      }
      for (const r of entry.redundant || []) {
        const rKey = (r.key || []).join('||');
        const rFrag = fragByKey(rKey);
        if (rFrag) {
          cards.push({ frag: rFrag, recommended: false, redundantWhy: r.why });
          shown.add(rKey);
        }
      }
    }
    for (const f of fragmentsForStep(n)) {
      const k = fragKey(f);
      if (!shown.has(k)) {
        cards.push({ frag: f, recommended: true });
        shown.add(k);
      }
    }
    return cards;
  }

  // Adapts a real fragment ({source_id, symbol, code, why, maps_to}) into FragmentCard's
  // existing prop shape ({name, source, steps, description, codeLines, code}) — FragmentCard
  // itself is untouched for now, this is purely a mapping layer.
  function toCardFragment(f) {
    return {
      name: f.symbol,
      source: f.source_id,
      steps: (f.maps_to || []).join(', '),
      description: f.why || '',
      codeLines: (f.code || '').split('\n').length,
      code: f.code || '',
    };
  }

  // Every fragment key SHOWN under step n (accounting's chosen + nested redundant, plus any
  // maps_to leftover not in accounting) — matching current/'s _fragKeysForStep so the coverage
  // check below can never contradict what the step actually renders.
  function fragKeysForStep(n) {
    const keys = new Set();
    for (const entry of entriesForStep(n)) {
      if (entry.chosen) keys.add(entry.chosen.join('||'));
      for (const r of entry.redundant || []) {
        if (r.key) keys.add(r.key.join('||'));
      }
    }
    for (const f of fragmentsForStep(n)) keys.add(fragKey(f));
    return keys;
  }

  // Selected fragment keys shown under step n — what "covered" actually means.
  function selectedKeysForStep(n) {
    return [...fragKeysForStep(n)].filter((k) => selectedKeys.includes(k));
  }

  let fragmentActiveStepId = null;
  let confirmedFragmentSteps = [];

  $: {
    if (!fragmentActiveStepId && sequencedTestSteps.length > 0) {
      fragmentActiveStepId = sequencedTestSteps[0].n;
    }
  }

  $: fragmentActiveStep = sequencedTestSteps.find((s) => s.n === fragmentActiveStepId) ?? null;
  $: fragmentActiveStepIndex = sequencedTestSteps.findIndex((s) => s.n === fragmentActiveStepId);

  let fragmentStepStatuses = {};
  $: {
    // Referenced directly so this block re-runs when any of them change — selectedKeysForStep()
    // reads all three, but only inside a function body, which Svelte's dependency tracker can't
    // see into (it only tracks identifiers written directly in this reactive statement).
    void selectedKeys; void accounting; void fragmentPool;
    const next = {};
    for (const step of sequencedTestSteps) {
      if (confirmedFragmentSteps.includes(step.n)) {
        next[step.n] = 'covered';
      } else if (selectedKeysForStep(step.n).length > 0) {
        next[step.n] = 'review';
      } else {
        next[step.n] = 'none';
      }
    }
    fragmentStepStatuses = next;
  }

  $: fragmentsSummaryStatus =
    sequencedTestSteps.length > 0 && sequencedTestSteps.every((s) => confirmedFragmentSteps.includes(s.n))
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
      const result = await onGatherFragments();
      fragmentPool = result.fragments || [];
      selectedKeys = (result.selected || []).map(fragKey);
      accounting = result.accounting || {};
    } finally {
      isGatheringFragments = false;
    }
  }

  function toggleFragmentSelected(fragmentKey) {
    selectedKeys = selectedKeys.includes(fragmentKey)
      ? selectedKeys.filter((k) => k !== fragmentKey)
      : [...selectedKeys, fragmentKey];
  }

  function toggleFragmentExpanded(fragmentKey) {
    expandedKeys = expandedKeys.includes(fragmentKey)
      ? expandedKeys.filter((k) => k !== fragmentKey)
      : [...expandedKeys, fragmentKey];
  }

  function advanceFragmentStep() {
    const updatedConfirmed = confirmedFragmentSteps.includes(fragmentActiveStepId)
      ? confirmedFragmentSteps
      : [...confirmedFragmentSteps, fragmentActiveStepId];
    confirmedFragmentSteps = updatedConfirmed;

    const nextUnconfirmed = sequencedTestSteps.find((s) => !updatedConfirmed.includes(s.n));
    fragmentActiveStepId = nextUnconfirmed ? nextUnconfirmed.n : FRAGMENTS_SUMMARY_STEP_ID;
    scrollToStepIntro();
  }

  async function handleConfirm() {
    const keep = selectedKeys
      .map(fragByKey)
      .filter(Boolean)
      .map((f) => ({ source_id: f.source_id, symbol: f.symbol }));
    await onSaveFragments(keep);
    onConfirm && onConfirm();
  }
</script>

<p class="step-intro">Re-use real code from the selected scripts, reviewed per sequence step. Gather Fragments (LLM) proposes, for each step, the fragment(s) worth reusing (green) plus the redundant alternatives it was preferred over (red, nested below) — so the accounting of every candidate is visible. Page through the steps; tick a fragment to include it in Generate (untick a green one or tick a red one to override). Save, then confirm.</p>

<div class="arrow-step-row">
  {#each sequencedTestSteps as step, i (step.n)}
    <ArrowStep
      label={i + 1}
      status={fragmentStepStatuses[step.n] ?? 'none'}
      active={fragmentActiveStepId === step.n}
      loading={isGatheringFragments}
      onClick={() => selectFragmentStep(step.n)}
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
      {#each sequencedTestSteps as step, i (step.n)}
        <div class="script-summary-section">
          <div class="sequence-step-summary">
            <span
              class="step-status-badge"
              class:covered={fragmentStepStatuses[step.n] === 'covered'}
              class:review={fragmentStepStatuses[step.n] === 'review'}
              class:none={fragmentStepStatuses[step.n] === 'none'}
              aria-hidden="true"
            >
              {fragmentStepStatuses[step.n] === 'covered' ? '✓' : fragmentStepStatuses[step.n] === 'review' ? '!' : '–'}
            </span>
            <p><strong>Sequence Step {i + 1}</strong> - {step.action}</p>
          </div>
          <div class="fragment-summary-list">
            {#each selectedKeysForStep(step.n).map(fragByKey).filter(Boolean) as frag (fragKey(frag))}
              <p class="fragment-summary-row"><code>{frag.symbol} — {frag.source_id}</code></p>
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
        class:covered={fragmentStepStatuses[fragmentActiveStep.n] === 'covered'}
        class:review={fragmentStepStatuses[fragmentActiveStep.n] === 'review'}
        class:none={fragmentStepStatuses[fragmentActiveStep.n] === 'none'}
        aria-hidden="true"
      >
        {fragmentStepStatuses[fragmentActiveStep.n] === 'covered' ? '✓' : fragmentStepStatuses[fragmentActiveStep.n] === 'review' ? '!' : '–'}
      </span>
      <p><strong>Sequence Step {fragmentActiveStepIndex + 1}</strong> - {fragmentActiveStep.action}</p>
    </div>

    <div class="fragment-groups">
      {#each cardsForStep(fragmentActiveStepId).filter((c) => c.recommended) as card (fragKey(card.frag))}
        <FragmentCard
          fragment={toCardFragment(card.frag)}
          recommended={true}
          selected={selectedKeys.includes(fragKey(card.frag))}
          expanded={expandedKeys.includes(fragKey(card.frag))}
          onToggleSelected={() => toggleFragmentSelected(fragKey(card.frag))}
          onToggleExpanded={() => toggleFragmentExpanded(fragKey(card.frag))}
        />
      {/each}

      {#if cardsForStep(fragmentActiveStepId).some((c) => !c.recommended)}
        <p class="fragment-redundant-label">Not selected — redundant to the above:</p>
        <div class="fragment-redundant-group">
          {#each cardsForStep(fragmentActiveStepId).filter((c) => !c.recommended) as card (fragKey(card.frag))}
            <FragmentCard
              fragment={{ ...toCardFragment(card.frag), redundantReason: card.redundantWhy }}
              recommended={false}
              selected={selectedKeys.includes(fragKey(card.frag))}
              expanded={expandedKeys.includes(fragKey(card.frag))}
              onToggleSelected={() => toggleFragmentSelected(fragKey(card.frag))}
              onToggleExpanded={() => toggleFragmentExpanded(fragKey(card.frag))}
            />
          {/each}
        </div>
      {/if}

      {#if !cardsForStep(fragmentActiveStepId).length}
        <p class="fragment-empty">No fragments gathered yet. Click "Gather Fragments (LLM)" above.</p>
      {/if}
    </div>

    <div class="step-actions">
      <Button variant="primary" disabled={!cardsForStep(fragmentActiveStepId).length} on:click={advanceFragmentStep}>Confirm Fragments</Button>
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
    font-size: 0.8rem;
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
    background: var(--color-bg-surface);
    padding: 4px 8px;
    border-radius: 6px;
  }

  .fragment-summary-empty {
    color: var(--color-text-muted);
    font-style: italic;
  }
</style>
