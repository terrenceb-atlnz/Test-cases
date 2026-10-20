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
  import atLogoDark from '../assets/at-logo-2.png';
  import atLogoLight from '../assets/at-logo-2-white.png';
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
  // The banner's faded background logo follows the theme the same way (white on dark).
  $: atLogo = $resolvedTheme === 'dark' ? atLogoDark : atLogoLight;

  let isAdmin = false;
  let adminStatusText = 'Loading status…';

  const ADMIN_CLICKS_REQUIRED = 8;
  let logoClickCount = 0;

  function handleLogoClick() {
    if (isAdmin) return;
    logoClickCount += 1;
    if (logoClickCount < ADMIN_CLICKS_REQUIRED) return;
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

<div class="home-page">
  <div class="home-banner-container">
    <div class="home-banner" style:--banner-logo={`url(${atLogo})`}>
      <!-- <h1>Ask CK</h1> -->
       <div class="home-hero">
      <button type="button" class="logo-button" on:click={handleLogoClick} aria-label="Ask CK logo">
        <img src={isAdmin ? askCKAdmin : askCKLogo} alt="Ask CK logo" />
      </button>
      <h1>{isAdmin ? 'Welcome Admin' : 'Welcome to Ask CK'}</h1>
      {#if !isAdmin}
        <p>Ask CK is a server-backed test-engineering workbench for the AWPTCM test-case program. It brings the tools for enriching manual test cases, mapping them to automation, and turning them into runnable scripts into one place. Pick a tool from below, or read the step-by-step guides inside the Help section. Most tools use an LLM via a local subscription CLI — set that up first under <span style="font-weight: bold;">Settings → LLM → LLM Provider Login</span>.</p>
      {/if}
  </div>
    </div>
  </div>

  

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
</div>

<style>
    /* Fills the content panel's full height (it is a flex column), and runs under its 16px
       top/bottom padding so the gradient reaches both edges. Colours per theme in app.css. */
  .home-page {
      flex: 1;
      margin: -16px 0;
      padding: 4rem 8rem 0 8rem
      /* background: linear-gradient(235deg, 
        var(--color-home-grad-1) 20% 10%, 
        var(--color-home-grad-2) 30% 70%, 
        var(--color-home-grad-3) 100% 20%
      ); */
  }

  .home-banner-container {
    position: relative;               /* ::after is measured from here */
  }
  .home-banner {
    /* remove margin-top, margin-left, margin-right from here */
    border-radius: 10px;
    min-height: 10rem;
    /* padding: 0.8rem; */
    background-color: var(--color-banner-bg);
    position: relative;
    isolation: isolate;
    overflow: hidden;      
    display: flex;
  }

  .home-banner::before {
    content: '';
    position: absolute;
    inset: 0;                               
    z-index: -1;                         
    background: var(--banner-logo) right -80px top -240px / 820px auto no-repeat;
    mix-blend-mode:m;
    opacity: 0.15;                          
    pointer-events: none;
  }

  /* .home-banner::after {
    content: '';
    position: absolute;
    inset: 0;
    z-index: -1;            
    background: linear-gradient(to bottom,
    rgba(107, 107, 107, 0.25) 0%,    
    transparent 45%);           
    pointer-events: none;
  } */


  /* .home-banner-container::after {
    content: '';
    position: absolute;
    left: 5rem;                       
    top: -3.3rem;                      
    width: 18rem;
    height: 18rem;
    z-index: 1;                       
    background: url('../assets/askck-logo.png') center / contain no-repeat;
    pointer-events: none;
  } */
  .home-banner h1 {
    color: var(--color-banner-text); 
    text-transform: uppercase;
    font-size: 3rem;
    max-width: 25rem;
  }

  .home-hero {
      display: flex;
      flex-direction: row;
      /* flex-direction: column; */
      align-items: center;
      text-align: center;
  }
    
    .logo-button {
        background: transparent;
        border: none;
        padding: 0;
        /* cursor: pointer; */
    }

    .home-hero img {
        width: 12em;
        height: auto;
        margin-bottom: 1rem;
        margin-top: 1rem;
    }
    
    .home-hero h1 {
        font-size: 2.5rem;
        margin-bottom: 1.5rem;
        padding-bottom: 0.5rem;
        margin-left: 2rem;
        padding-left: 2rem;
        border-left: 3px solid var(--color-banner-accent);
        display: flex;
        align-items: flex-start;
        text-align: left;
        padding: 1rem;
    }
    
    .home-hero p {
      font-size: 1rem;
      color: var(--color-banner-text);
    }

    .card-container {
        display: flex;
        justify-content: center;
        align-items: center;
        text-align: center;
    }

    .card-grid {
        display: flex;
        flex-direction: row;
        align-items: start;
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