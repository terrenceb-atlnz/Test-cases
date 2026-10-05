<script>
// @ts-nocheck

  import Button from '../Button.svelte';
  import Table from '../Table.svelte';
  import SearchBox from '../SearchBox.svelte';
  import LlmButton from '../LlmButton.svelte';
  import ErrorBanner from '../ErrorBanner.svelte';
  import { scrollToCasesIntro, scrollToBottom } from '../../utils/scroll.js';

  /** @type {Array<{ key: string, label: string, width?: number }>} */
  export let columns = [];

  /** @type {string} */
  export let introText = '';

  /** @type {string} */
  export let searchPlaceholder = 'Search…';

  /** @type {string} */
  export let searchButtonLabel = 'Search';

  /** @type {string} Label above the candidates table */
  export let candidateLabel = 'Candidates';

  /** @type {string} Label above the chosen table */
  export let chosenLabel = 'Chosen';

  /** @type {(query: string) => Promise<Array>} */
  export let onSearch = async () => [];

  /** @type {(headers: Record<string, string>) => Promise<Array>} headers carries
      X-CK-LLM-Call (llmProgressService) so the server can track/cancel this exact call. */
  export let onSuggest = async () => [];

  /** @type {Array} Bindable — the rows chosen for this step */
  export let chosen = [];

  /** @type {Array} Lazily fetched by the parent (GET step_candidates/{key}/{step}) the
      first time this step opens for a case — arrives asynchronously, generally after this
      component has already mounted, so it's seeded in reactively below rather than at
      creation (contrast CasePicker's selectedCaseId, which is never late like this). */
  export let initialCandidates = [];

  /** @type {(() => Promise<void>) | null} Called when Review & Confirm is clicked — the
      parent owns the real POST confirm_step call (it already has the case key and the
      session to update); this just awaits it so a failure surfaces here instead of
      silently advancing the step. */
  export let onConfirm = null;

  // Excludes anything already in `chosen` — matching current/generator/chosen.js's "the top
  // table hides any id already present" behavior. chooseSelected/clearSelected keep the two
  // lists disjoint themselves by moving rows explicitly, but candidates ARRIVING from
  // outside (the initial seed, a fresh Search, a fresh Suggest) aren't aware of `chosen` at
  // all unless every one of those call sites applies this the same way.
  function excludeChosen(rows) {
    const chosenIds = new Set(chosen.map((c) => c.id));
    return (rows || []).filter((r) => !chosenIds.has(r.id));
  }

  let search = '';
  let candidates = [];
  let candidatesSeeded = false;
  // Late-arriving (see initialCandidates' own doc comment above) — seeded once, not on
  // every `chosen` change, so a later choose/restore doesn't retroactively re-filter rows
  // the user is actively looking at.
  $: if (!candidatesSeeded && initialCandidates.length) {
    candidates = excludeChosen(initialCandidates);
    candidatesSeeded = true;
  }
  let selectedCandidateIds = [];
  let selectedChosenIds = [];

  async function handleSearch() {
    candidates = excludeChosen(await onSearch(search));
    selectedCandidateIds = [];
    scrollToCasesIntro();
  }

  function handleSuggestResult(result) {
    candidates = excludeChosen(result);
    selectedCandidateIds = [];
    scrollToCasesIntro();
  }

  function chooseSelected() {
    const moving = candidates.filter((c) => selectedCandidateIds.includes(c.id));
    if (moving.length === 0) return;
    chosen = [...chosen, ...moving];
    candidates = candidates.filter((c) => !selectedCandidateIds.includes(c.id));
    selectedCandidateIds = [];
    scrollToBottom();
  }

  function clearSelected() {
    const moving = chosen.filter((c) => selectedChosenIds.includes(c.id));
    if (moving.length === 0) return;
    candidates = [...candidates, ...moving];
    chosen = chosen.filter((c) => !selectedChosenIds.includes(c.id));
    selectedChosenIds = [];
    scrollToCasesIntro();
  }

  function clearAll() {
    candidates = [...candidates, ...chosen];
    chosen = [];
    selectedChosenIds = [];
    scrollToCasesIntro();
  }

  let isConfirming = false;
  let confirmError = '';

  async function handleConfirm() {
    if (!onConfirm) return;
    isConfirming = true;
    confirmError = '';
    try {
      await onConfirm();
    } catch (e) {
      confirmError = (e && e.message) || String(e);
    } finally {
      isConfirming = false;
    }
  }
</script>

<p class="cases-intro">{introText}</p>

<div class="testlink-search">
  <SearchBox
    bind:value={search}
    placeholder={searchPlaceholder}
    buttonLabel={searchButtonLabel}
    onSearch={handleSearch}
  />
  <LlmButton label="Suggest with LLM" verb="Suggesting…" onRun={onSuggest} onResult={handleSuggestResult} />
</div>

<p class="testlink-table-label">{candidateLabel}</p>
<Table {columns} rows={candidates} bind:selected={selectedCandidateIds} />

<div class="testlink-choose-actions">
  <Button variant="outline" on:click={chooseSelected}>↓ Choose selected</Button>
</div>

<p class="testlink-table-label">{chosenLabel}</p>
<Table {columns} rows={chosen} bind:selected={selectedChosenIds} />

<div class="testlink-final-actions">
  <Button variant="outline" on:click={clearSelected}>Clear Selected</Button>
  <Button variant="outline" on:click={clearAll}>Clear All</Button>
</div>
<ErrorBanner message={confirmError && `Confirm failed: ${confirmError}`} />
<div class="testlink-final-actions">
  <Button variant="primary" loading={isConfirming} on:click={handleConfirm}>Review &amp; Confirm</Button>
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
</style>
