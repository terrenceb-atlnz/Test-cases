<script>
// @ts-nocheck

  import PageCard from '../lib/components/PageCard.svelte';
  import Button from '../lib/components/Button.svelte';
  import ConfirmModal from '../lib/components/ConfirmModal.svelte';
  import StatusModal from '../lib/components/StatusModal.svelte';
  import { resolvedTheme } from '../lib/theme.js';
  import askCKLogoDark from '../assets/askck-logo.png';
  import askCKLogoLight from '../assets/askck-logo-light.png';
  import askCKAdmin from '../assets/askck-admin.png';
  import testCaseIcon from '../assets/icons/clipboard-list.svg';
  import pytestIcon from '../assets/icons/pytest.svg';
  import testComposerIcon from '../assets/icons/list-check.svg';
  import zephyrIcon from '../assets/icons/getzephyr-icon.svg';

  export let onNavigate = (pageId) => {};

  const page = {
    cards: [
      { pageId: 'generator', title: 'Objective Generator', description: 'Turns a sparse AWPTCM manual case into a refined case with declarative objects, Zephyr-ready test steps, and traceability — with a review gate at every step.', icon: { src: testCaseIcon } },
      { pageId: 'pytest', title: 'PyTest Creator', description: 'Turns a complete case into a runnable Allied Telesis framework test script. Each step has a Confirm gate.', icon: { src: pytestIcon } },
      { pageId: 'composer', title: 'Test Composer', description: 'Builds reusable test flows and orchestration layers for complex validation scenarios.', icon: { src: testComposerIcon } },
      { pageId: 'zephyr', title: 'Zephyr Templating', description: 'Maps refined cases into structured templates that match your Zephyr workflow and reporting needs.', icon: { src: zephyrIcon } }
    ]
  };

  $: askCKLogo = $resolvedTheme === 'dark' ? askCKLogoLight : askCKLogoDark;

  let logoClicks = 0;
  let isAdmin = false;

  function handleLogoClick() {
    if (isAdmin) return;
    logoClicks += 1;
    if (logoClicks >= 8) {
      isAdmin = true;
    }
  }

  function resetCurrentCaseSession() {
    // TODO: wire up a real reset of the current case session
  }

  function resetWorkspaceLlmConfig() {
    // TODO: wire up a real reset of the workspace LLM config
  }

  function resetAllSessions() {
    // TODO: wire up a real reset of all sessions
  }

  function restartServer() {
    // TODO: wire up a real server restart/reload
  }

  // TEMP: quick access to preview/style the modal components — remove once done.
  let showConfirmModalPreview = false;
  let showStatusModalPreview = false;
</script>

<div class="home-hero">
    <button type="button" class="logo-button" on:click={handleLogoClick} aria-label="Ask CK logo">
      <img src={isAdmin ? askCKAdmin : askCKLogo} alt="Ask CK logo" />
    </button>
    <h1>{isAdmin ? 'Welcome Admin' : 'Welcome to Ask CK'}</h1>
    <p>Ask CK is a server-backed test-engineering workbench for the AWPTCM test-case program. It brings the tools for enriching manual test cases, mapping them to automation, and turning them into runnable scripts into one place. Pick a tool from below, or read the step-by-step guides inside the Help section. Most tools use an LLM via a local subscription CLI — set that up first under <span style="font-weight: bold;">LLM → Configure</span>.</p>
</div>

<!-- TEMP: preview buttons for styling the modal components — remove once done. -->
<!-- <div class="temp-modal-preview">
  <Button variant="outline" on:click={() => (showConfirmModalPreview = true)}>TEMP: Preview ConfirmModal</Button>
  <Button variant="outline" on:click={() => (showStatusModalPreview = true)}>TEMP: Preview StatusModal</Button>
</div> -->

<ConfirmModal
  bind:open={showConfirmModalPreview}
  title="Are you sure?"
  message="This is a preview of ConfirmModal's content and styling."
  confirmText="Continue"
  cancelText="Cancel"
/>

<StatusModal
  bind:open={showStatusModalPreview}
  status="success"
  title="Preview status"
  message="This is a preview of StatusModal's content and styling."
/>

{#if isAdmin}
  <div class="admin-panel">
    <div class="admin-section">
      <p class="admin-section-label">Session state</p>
      <div class="admin-actions">
        <Button variant="outline" on:click={resetCurrentCaseSession}>Reset current case session</Button>
        <Button variant="outline" on:click={resetWorkspaceLlmConfig}>Reset workspace LLM config</Button>
        <Button variant="outline" on:click={resetAllSessions}>Reset ALL sessions</Button>
      </div>
    </div>

    <div class="admin-section">
      <p class="admin-section-label">Server</p>
      <div class="admin-actions">
        <Button variant="outline" on:click={restartServer}>Restart server (reload)</Button>
      </div>
    </div>
  </div>
{:else}
  <div class="card-container">
    <div class="card-grid">
      {#each page.cards as card}
        <PageCard {card} on:click={() => onNavigate(card.pageId)} />
      {/each}
    </div>
  </div>
{/if}

<style>
    .home-hero {
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        zoom: 0.8;
    }
    
    .logo-button {
        background: transparent;
        border: none;
        padding: 0;
        /* cursor: pointer; */
    }

    .home-hero img {
        width: 18em;
        height: auto;
        margin-bottom: 1rem;
    }
    
    .home-hero h1 {
        font-size: 3rem;
        margin-bottom: 1.5rem;
    }
    
    .home-hero p {
        font-size: 1.2rem;
        color: var(--color-text-muted);
    }

    .card-container {
        display: flex;
        justify-content: center;
        align-items: center;
        text-align: center;
        zoom: 0.8;
    }

    .card-grid {
        display: flex;
        flex-direction: row;
        align-items: center;
        justify-content: center;
        text-align: center;
    }

    .admin-panel {
        display: flex;
        flex-direction: column;
        gap: 28px;
        max-width: 720px;
        margin: 0 auto;
        padding: 24px 24px;
    }

    .admin-section-label {
        margin: 0 0 8px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--color-text-muted);
    }

    .admin-actions {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
    }

    .temp-modal-preview {
        display: flex;
        justify-content: center;
        gap: 12px;
        margin-bottom: 24px;
    }

</style>