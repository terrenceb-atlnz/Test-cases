<script>
  // @ts-nocheck

  import PageCard from "../lib/components/PageCard.svelte";
  import AdminPanel from "../lib/components/AdminPanel.svelte";
  import Button from "../lib/components/Button.svelte";
  import { onMount } from "svelte";
  import { resolvedTheme } from "../lib/theme.js";
  import {
    loadConfig,
    describeLLMStatus,
  } from "../lib/services/llmConfigService.js";
  import {
    probeLocalAgent,
    describeAgentStatus,
  } from "../lib/services/agentService.js";
  import askCKLogoDark from "../assets/askck-logo.png";
  import askCKLogoLight from "../assets/askck-logo-light.png";
  import askCKAdminDark from "../assets/askck-admin.png";
  import askCKAdminLight from "../assets/askck-admin-light.png";
  import aiIcon from "../assets/icons/brain-circuit.svg";
  import atLogoDark from "../assets/at-logo-2.png";
  import atLogoLight from "../assets/at-logo-2-white.png";
  import atLogoDarkLong from "../assets/at-logo.png";
  import atLogoLightLong from "../assets/at-logo-light.png";
  import testCaseIcon from "../assets/icons/clipboard-list.svg";
  import pytestIcon from "../assets/icons/pytest.svg";
  import testComposerIcon from "../assets/icons/list-check.svg";
  import zephyrIcon from "../assets/icons/getzephyr-icon.svg";

  export let onNavigate = (pageId) => {};

  const page = {
    cards: [
      {
        pageId: "generator",
        title: "Objective Generator",
        description:
          "Turns a sparse AWPTCM manual case into a refined case with declarative objectives, Zephyr-ready test steps, and traceability — with a review gate at every step.",
        icon: { src: testCaseIcon },
      },
      {
        pageId: "pytest",
        title: "PyTest Creator",
        description:
          "Turns a complete case into a runnable Allied Telesis framework test script. Each step has a Confirm gate.",
        icon: { src: pytestIcon },
      },
      {
        pageId: "composer",
        title: "Test Composer",
        description:
          "Builds reusable test flows and orchestration layers for complex validation scenarios.",
        icon: { src: testComposerIcon },
      },
      {
        pageId: "zephyr",
        title: "Zephyr Templating",
        description:
          "Maps refined cases into structured templates that match your Zephyr workflow and reporting needs.",
        icon: { src: zephyrIcon },
      },
    ],
  };

  $: askCKLogo = $resolvedTheme === "dark" ? askCKLogoLight : askCKLogoDark;
  $: askCKAdmin = $resolvedTheme === "dark" ? askCKAdminLight : askCKAdminDark;

  // The banner's faded background logo follows the theme the same way (white on dark).
  $: bannerLogo = $resolvedTheme === "dark" ? atLogoDark : atLogoLight;
  $: atLogo = $resolvedTheme === "dark" ?  atLogoLightLong : atLogoDarkLong;

  // Clicking the logo ADMIN_CLICKS_REQUIRED times switches the page into admin mode, which
  // shows the AdminPanel (its own component) under the cards.
  let isAdmin = false;

  const ADMIN_CLICKS_REQUIRED = 8;
  let logoClickCount = 0;

  function handleLogoClick() {
    if (isAdmin) return;
    logoClickCount += 1;
    if (logoClickCount < ADMIN_CLICKS_REQUIRED) return;
    isAdmin = true;
  }

  // LLM status for the aside: the configured LLM (same text as Settings) and the seat agent.
  // probeLocalAgent only reads the agent's /health — checkLocalAgent would also ask it to
  // update the CLI. No llm_health check here: that makes a real LLM call on every visit.
  let llmStatus = null;
  let agentStatus = null;

  onMount(async () => {
    llmStatus = describeLLMStatus(await loadConfig());
    agentStatus = describeAgentStatus(await probeLocalAgent());
  });
</script>

<div class="home-page">
  <div class="home-banner-container">
    <div
      class="home-banner"
      class:admin={isAdmin}
      style:--banner-logo={`url(${bannerLogo})`}
    >
      <div class="home-hero">
        <button
          type="button"
          class="logo-button"
          on:click={handleLogoClick}
          aria-label="Ask CK logo"
        >
          <img src={isAdmin ? askCKAdmin : askCKLogo} alt="Ask CK logo" />
        </button>
        <h1>{isAdmin ? "Welcome Admin" : "Welcome to Ask CK"}</h1>

      </div>
    </div>
  </div>

  <div class="card-container">
    <div class="card-grid">
      {#each page.cards as card}
        <PageCard {card} on:click={() => onNavigate(card.pageId)} />
      {/each}
    </div>
  </div>
  {#if !isAdmin}
    <div class="home-content-container">
      <div class="home-content">
          <div class="home-content-imgs">
            <img id="ck-logo" src={askCKLogo} alt="">
            <img id="at-logo" src={atLogo} alt="">
          </div>
          <p class="home-intro">
            Ask CK is a server-backed test-engineering workbench for the AWPTCM
            test-case program. It brings the tools for enriching manual test
            cases, mapping them to automation, and turning them into runnable
            scripts into one place. Pick a tool from below, or read the
            step-by-step guides inside the Help section. Most tools use an LLM via
            a local subscription CLI — set that up first under <span
              style="font-weight: bold;">Settings → LLM → LLM Provider Login</span
            >.
          </p>
          <div class="home-links">
            <h3 class="status-label">Links</h3>
            <!-- Paste links here, one <li> each. -->
            <ul>
              <li><a href="https://wiki.atlnz.lc/awpwiki/index.php?title=Ask-ck&oldid=740690#Writing_to_Zephyr_.2F_Jira" target="_blank" rel="noopener noreferrer">Ask-ck alliedware+ wiki page</a></li>
              <li><a href="https://github.com/terrenceb-atlnz/Test-cases?tab=readme-ov-file" target="_blank" rel="noopener noreferrer">Ask CK Git Repository- Test-cases</a></li>
            </ul>
          </div>
      </div>
        <div class="home-aside">
          <!-- <h2 class="status-heading">LLM Status</h2> -->
          <p class="status-label">Configured LLM</p>
          {#if llmStatus}
            <p class="status-text tone-{llmStatus.tone}">{llmStatus.text}</p>
          {:else}
            <p class="status-text">Checking…</p>
          {/if}
          <p class="status-label">Seat agent</p>
          {#if agentStatus}
            <p class="status-text tone-{agentStatus.tone}">
              {#each agentStatus.lines as line}{line}<br />{/each}
            </p>
          {:else}
            <p class="status-text">Checking…</p>
          {/if}
          <div class="aside-actions">
            <Button variant="outline" on:click={() => onNavigate("help", { openSetupGuide: true })}>Set up seat</Button>
            <Button variant="outline" on:click={() => onNavigate("settings", { tab: "llm" })}>Configure LLM</Button>
          </div>
      </div>
    </div>
  {/if}

  {#if isAdmin}
    <AdminPanel />
  {/if}
</div>

<style>
  .home-page {
    flex: 1;
    margin: -16px 0;
    padding: 3rem 3rem 0 3rem;
  }

  .home-banner-container {
    position: relative;
  }
  .home-banner {
    border-radius: 10px;
    min-height: 10rem;
    background-color: var(--color-banner-bg);
    position: relative;
    isolation: isolate;
    overflow: hidden;
    display: flex;
  }

  .home-banner.admin {
    background-color: var(--color-banner-bg-admin);
  }

  .home-banner::before {
    content: "";
    position: absolute;
    inset: 0;
    z-index: -1;
    background: var(--banner-logo) right -80px top -240px / 820px auto no-repeat;
    mix-blend-mode: m;
    opacity: 0.15;
    pointer-events: none;
  }

  .home-banner::after {
    content: "";
    position: absolute;
    inset: 0;
    z-index: -1;
    background: linear-gradient(
      to bottom,
      var(--color-banner-gradient) 0%,
      transparent 45%
    );
    pointer-events: none;
  }

  .home-banner h1 {
    color: var(--color-banner-text);
    text-transform: uppercase;
    font-size: 3rem;
    max-width: 25rem;
  }

  .home-hero {
    display: flex;
    flex-direction: row;
    align-items: center;
    text-align: center;
  }

  .logo-button {
    background: transparent;
    border: none;
    padding: 0;
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

  .home-banner.admin .home-hero h1 {
    border-left-color: var(--color-accent);
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
    zoom: 0.9;
  }

  .home-content-container {
    display: grid;
    grid-template-columns: 3fr 2fr;
    gap: 12px;
  }

  .home-content {
    background-color: var(--color-bg-surface);
    border-radius: 10px;
    border: 1px solid var(--color-border-surface);
    padding: 12px 24px 12px 24px;
    margin: 20px auto;
    width: 100%;
    height: 50vh;
    flex-direction: column;
    display: flex;
    align-items: center;
    text-align: center;
    align-items: center;
  }

  .home-content p {
    font-size: 0.94rem;
    color: var(--color-banner-text);
    line-height: 2;
    border-top: 1px solid var(--color-border-surface);
    padding-top: 2rem;
  }

  .home-content-imgs {
    display: flex;
    align-items: center;
    gap: 4rem;
  }

  #ck-logo {
    height: 5rem;
    width: auto;
  }
  .status-heading {
    margin: 0 0 8px;
  }

  .status-label {
    margin: 12px 0 0;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--color-text-muted);
  }

  .home-aside {
    background-color: var(--color-bg-surface);
    border-radius: 10px;
    border: 1px solid var(--color-border-surface);
    padding: 24px 24px 12px 24px;
    margin: 20px auto;
    width: 100%;
    height: 50vh;
    flex-direction: column;
    display: flex;
    gap: 8px
  }

  .home-aside h2 {
    font-size: 1.2rem;
  }
  .home-aside .status-text {
    margin: 4px 0 0;
    line-height: 1.6;
  }

  .home-aside .tone-ok { color: var(--color-success); }
  .home-aside .tone-warn { color: var(--color-warning); }
  .home-aside .tone-error { color: var(--color-error); }

  .aside-actions {
    display: flex;
    gap: 12px;
    margin-top: 12px;
  }

  .home-links {
    width: 100%;
    text-align: left;
  }

  .home-links ul {
    margin: 8px 0 0;
    padding-left: 20px;
    line-height: 2;
    font-size: 0.94rem;
  }

  .home-links a {
    color: var(--color-accent);
  }

  #at-logo {
    height: 6rem;
    width: auto;
  }
</style>
