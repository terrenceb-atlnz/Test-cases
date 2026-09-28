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
  import { fetchAdminStatus, describeAdminStatus, resetWorkspaceLlmConfig, resetAllSessions, restartServer } from '../lib/services/adminService.js';

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

  let isAdmin = false;
  let adminStatusText = 'Loading status…';

  function handleLogoDblClick() {
    if (isAdmin) return;
    isAdmin = true;
    fetchAdminStatus().then((data) => { adminStatusText = describeAdminStatus(data); });
  }

  // Single ConfirmModal/StatusModal pair, reused across admin actions — only one can be
  // open at a time anyway, so per-action instances would just be dead weight.
  let confirmOpen = false;
  let confirmTitle = '';
  let confirmMessage = '';
  let confirmOnConfirm = () => {};

  let statusOpen = false;
  let statusKind = 'success';
  let statusTitle = '';
  let statusMessage = '';

  function askConfirm(title, message, onConfirm) {
    confirmTitle = title;
    confirmMessage = message;
    confirmOnConfirm = onConfirm;
    confirmOpen = true;
  }

  function showStatus(kind, title, message) {
    statusKind = kind;
    statusTitle = title;
    statusMessage = message;
    statusOpen = true;
  }

  function handleResetWorkspaceLlmConfig() {
    askConfirm(
      'Reset the workspace LLM config?',
      "The saved provider/login default will be cleared (you can re-apply it on Configure). Cases and corpora are untouched.",
      async () => {
        try {
          const d = await resetWorkspaceLlmConfig();
          showStatus('success', 'Workspace LLM config reset', 'Cleared: ' + (d.cleared || []).join(', '));
        } catch (e) {
          showStatus('error', 'Reset failed', String(e));
        }
      }
    );
  }

  function handleResetAllSessions() {
    askConfirm(
      'Reset ALL sessions?',
      "EVERY case's wizard/pytest progress and the workspace LLM default will be cleared. This does NOT touch corpora (Zephyr/TestLink/ATP) — only your working sessions.",
      async () => {
        try {
          const d = await resetAllSessions();
          showStatus('success', 'All sessions reset', 'Cleared: ' + (d.cleared || []).join(', ') + ' — reload the page for a clean slate.');
        } catch (e) {
          showStatus('error', 'Reset failed', String(e));
        }
      }
    );
  }

  function handleRestartServer() {
    askConfirm(
      'Restart the server?',
      'The app reloads (dev server runs with --reload). The page will briefly lose connection and then reconnect.',
      async () => {
        try {
          await restartServer();
          adminStatusText = 'Restarting… reconnecting in a moment.';
          setTimeout(() => window.location.reload(), 2500);
        } catch (e) {
          showStatus('error', 'Restart failed', String(e));
        }
      }
    );
  }
</script>

<div class="home-hero">
    <button type="button" class="logo-button" on:dblclick={handleLogoDblClick} aria-label="Ask CK logo">
      <img src={isAdmin ? askCKAdmin : askCKLogo} alt="Ask CK logo" />
    </button>
    <h1>{isAdmin ? 'Welcome Admin' : 'Welcome to Ask CK'}</h1>
    {#if !isAdmin}
      <p>Ask CK is a server-backed test-engineering workbench for the AWPTCM test-case program. It brings the tools for enriching manual test cases, mapping them to automation, and turning them into runnable scripts into one place. Pick a tool from below, or read the step-by-step guides inside the Help section. Most tools use an LLM via a local subscription CLI — set that up first under <span style="font-weight: bold;">LLM → Configure</span>.</p>
    {/if}
  </div>

<ConfirmModal
  bind:open={confirmOpen}
  title={confirmTitle}
  message={confirmMessage}
  onConfirm={confirmOnConfirm}
/>

<StatusModal
  bind:open={statusOpen}
  status={statusKind}
  title={statusTitle}
  message={statusMessage}
/>

{#if isAdmin}
  <div class="admin-panel">
    <p class="admin-status">{adminStatusText}</p>

    <div class="admin-section">
      <p class="admin-section-label">Session state</p>
      <div class="admin-actions">
        <Button variant="outline" on:click={handleResetWorkspaceLlmConfig}>Reset workspace LLM config</Button>
        <Button variant="outline" on:click={handleResetAllSessions}>Reset ALL sessions</Button>
      </div>
    </div>

    <div class="admin-section">
      <p class="admin-section-label">Server</p>
      <div class="admin-actions">
        <Button variant="outline" on:click={handleRestartServer}>Restart server (reload)</Button>
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
        padding: 0px 24px;
    }

    .admin-status {
        margin: 0;
        font-size: 0.9rem;
        color: var(--color-text-muted);
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

</style>