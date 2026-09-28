<script>
// @ts-nocheck

  import Button from '../Button.svelte';
  import Table from '../Table.svelte';
  import SearchBox from '../SearchBox.svelte';

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

  /** @type {() => Promise<Array>} */
  export let onSuggest = async () => [];

  /** @type {Array} Bindable — the rows chosen for this step */
  export let chosen = [];

  /** @type {(() => void) | null} Called when Review & Confirm is clicked */
  export let onConfirm = null;

  let search = '';
  let candidates = [];
  let selectedCandidateIds = [];
  let selectedChosenIds = [];
  let isSuggesting = false;

  async function handleSearch() {
    candidates = await onSearch(search);
    selectedCandidateIds = [];
  }

  async function handleSuggest() {
    isSuggesting = true;
    try {
      candidates = await onSuggest();
      selectedCandidateIds = [];
    } finally {
      isSuggesting = false;
    }
  }

  function chooseSelected() {
    const moving = candidates.filter((c) => selectedCandidateIds.includes(c.id));
    if (moving.length === 0) return;
    chosen = [...chosen, ...moving];
    candidates = candidates.filter((c) => !selectedCandidateIds.includes(c.id));
    selectedCandidateIds = [];
  }

  function clearSelected() {
    const moving = chosen.filter((c) => selectedChosenIds.includes(c.id));
    if (moving.length === 0) return;
    candidates = [...candidates, ...moving];
    chosen = chosen.filter((c) => !selectedChosenIds.includes(c.id));
    selectedChosenIds = [];
  }

  function clearAll() {
    candidates = [...candidates, ...chosen];
    chosen = [];
    selectedChosenIds = [];
  }

  function handleConfirm() {
    onConfirm && onConfirm();
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
  <Button variant="primary" sparkle loading={isSuggesting} on:click={handleSuggest}>Suggest with LLM</Button>
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
<div class="testlink-final-actions">
  <Button variant="primary" on:click={handleConfirm}>Review &amp; Confirm</Button>
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
