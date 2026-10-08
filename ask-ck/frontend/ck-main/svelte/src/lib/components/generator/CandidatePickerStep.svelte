<script>
// @ts-nocheck

  import Button from '../Button.svelte';
  import Table from '../Table.svelte';
  import SearchBox from '../SearchBox.svelte';
  import LlmButton from '../LlmButton.svelte';
  import ErrorBanner from '../ErrorBanner.svelte';
  import { scrollToCasesIntro, scrollToBottom } from '../../utils/scroll.js';

  // Array of column definitions for the candidates table *
  export let columns = [];

  // Text to display as an introduction before the candidate list
  export let introText = '';

  // Placeholder text for the search box 
  export let searchPlaceholder = 'Search…';

  // Label for the search button 
  export let searchButtonLabel = 'Search';

  // Label above the candidates table
  export let candidateLabel = 'Candidates';

  // Label above the chosen table
  export let chosenLabel = 'Chosen';

  // Array of chosen candidates
  export let chosen = [];

  // Array of initial candidates to populate the candidates list. 
  // - This is used to seed the candidates list when the component is first rendered. 
  // - It is excluded from the chosen list to avoid duplicates.
  export let initialCandidates = [];

  // Function to handle search functionality
  export let onSearch = async () => [];

  // Function to handle LLM suggestions
  export let onSuggest = async () => [];

  // Function to handle the confirmation of chosen candidates.
  // - This function is called when the user clicks the "Review & Confirm" button.
  export let onConfirm = null;
  
  // Search string entered by the user in the search box
  let search = '';

  // Flag to indicate whether the candidates list has been seeded with initial candidates
  let candidatesSeeded = false;

  // Array of candidate objects that are currently available for selection. 
  // - This list is populated based on the initialCandidates prop and updated based on 
  //   user actions.
  let candidates = [];

  // Array of IDs of candidates that are currently selected in the candidates table
  let selectedCandidateIds = [];

  // Array of IDs of candidates that are currently selected in the chosen table
  let selectedChosenIds = [];

  // Flag to indicate whether the user is confirming their choices
  let isConfirming = false;

  // Variable to hold any error message that occurs during the confirmation process
  let confirmError = '';

  // Reactive statement to seed the candidates list with initial candidates when the component 
  // is first rendered.
  $: if (!candidatesSeeded && initialCandidates.length) {
    candidates = excludeChosen(initialCandidates);
    candidatesSeeded = true;
  }

  // Function to exclude candidates that have already been chosen from a given list of rows.
  // - This function is used to ensure that candidates that have already been chosen do not
  //   appear in the candidates list.
  function excludeChosen(rows) {
    const chosenIds = new Set(chosen.map((c) => c.id));
    return (rows || []).filter((r) => !chosenIds.has(r.id));
  }

  // Function to handle the result of the LLM suggestion process.
  // - This function updates the candidates list with the suggested candidates, excluding
  //   any candidates that have already been chosen.
  function handleSuggestResult(result) {
    candidates = excludeChosen(result);
    selectedCandidateIds = [];
    scrollToCasesIntro();
  }

  // Function to move selected candidates from the candidates list to the chosen list.
  function chooseSelected() {
    const moving = candidates.filter((c) => selectedCandidateIds.includes(c.id));
    if (moving.length === 0) return;
    chosen = [...chosen, ...moving];
    candidates = candidates.filter((c) => !selectedCandidateIds.includes(c.id));
    selectedCandidateIds = [];
    scrollToBottom();
  }

  // Function to move selected candidates from the chosen list back to the candidates list.
  function clearSelected() {
    const moving = chosen.filter((c) => selectedChosenIds.includes(c.id));
    if (moving.length === 0) return;
    candidates = [...candidates, ...moving];
    chosen = chosen.filter((c) => !selectedChosenIds.includes(c.id));
    selectedChosenIds = [];
    scrollToCasesIntro();
  }

  // Function to move all candidates from the chosen list back to the candidates list.
  // - This function is used to clear all chosen candidates and return them to the candidates list
  function clearAll() {
    candidates = [...candidates, ...chosen];
    chosen = [];
    selectedChosenIds = [];
    scrollToCasesIntro();
  }
  
  // Function to handle the search action initiated by the user.
  // - This function calls the onSearch prop with the current search string and updates the
  //   candidates list with the search results, excluding any candidates that have already been chosen.
  async function handleSearch() {
    candidates = excludeChosen(await onSearch(search));
    selectedCandidateIds = [];
    scrollToCasesIntro();
  }

  // Function to handle the confirmation of chosen candidates.
  // - This function calls the onConfirm prop and handles any errors that may occur during the
  //   confirmation process. It also manages the isConfirming and confirmError state variables.
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
