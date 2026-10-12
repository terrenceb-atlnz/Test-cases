<script>
// @ts-nocheck

  import Button from '../Button.svelte';
  import Table from '../Table.svelte';
  import SearchBox from '../SearchBox.svelte';
  import LlmButton from '../LlmButton.svelte';
  import ErrorBanner from '../ErrorBanner.svelte';
  import { scrollToCasesIntro, scrollToBottom } from '../../utils/scroll.js';

  // --- Props: display text ---------------------------------------------------------
  export let introText = '';
  export let searchPlaceholder = 'Search…';
  export let searchButtonLabel = 'Search';
  export let candidateLabel = 'Candidates';
  export let chosenLabel = 'Chosen';

  // --- Props: data ------------------------------------------------------------------
  /** Column definitions, shared by both tables. */
  export let columns = [];

  /** Two-way bound (`bind:chosen`) — choosing or clearing here writes straight back to the
      parent's list. */
  export let chosen = [];

  /** Seeds the candidates table once, on first arrival — see the seeding block below. */
  export let initialCandidates = [];

  // --- Props: callbacks -------------------------------------------------------------
  /** @type {(query: string) => Promise<Array>} */
  export let onSearch = async () => [];

  /** @type {() => Promise<Array>} Run by the LLM button; its result replaces the candidates. */
  export let onSuggest = async () => [];

  /** @type {(() => Promise<void>) | null} null = no confirm action; the button does nothing. */
  export let onConfirm = null;

  // --- Local state ------------------------------------------------------------------
  let search = '';
  let candidates = [];
  let selectedCandidateIds = [];
  let selectedChosenIds = [];
  let isConfirming = false;
  let confirmError = '';

  // Seed ONCE: after the first non-empty initialCandidates, the list belongs to the user —
  // a later prop change must not overwrite what they have searched or moved since.
  let candidatesSeeded = false;
  $: if (!candidatesSeeded && initialCandidates.length) {
    candidates = excludeChosen(initialCandidates);
    candidatesSeeded = true;
  }

  // Every refill of the candidates table (seed, search, suggest) goes through this, so a row
  // can never appear in both tables at once.
  function excludeChosen(rows) {
    const chosenIds = new Set(chosen.map((c) => c.id));
    return (rows || []).filter((r) => !chosenIds.has(r.id));
  }

  // --- Refilling the candidates table -----------------------------------------------
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

  // --- Moving rows between the two tables -------------------------------------------
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

  // --- Confirm ------------------------------------------------------------------------
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
