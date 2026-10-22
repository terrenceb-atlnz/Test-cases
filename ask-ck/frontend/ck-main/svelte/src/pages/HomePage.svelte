<script>
  // @ts-nocheck

  import PageCard from "../lib/components/PageCard.svelte";
  import AdminPanel from "../lib/components/AdminPanel.svelte";
  import { resolvedTheme } from "../lib/theme.js";
  import askCKLogoDark from "../assets/askck-logo.png";
  import askCKLogoLight from "../assets/askck-logo-light.png";
  import askCKAdminDark from "../assets/askck-admin.png";
  import askCKAdminLight from "../assets/askck-admin-light.png";

  import atLogoDark from "../assets/at-logo-2.png";
  import atLogoLight from "../assets/at-logo-2-white.png";
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
          "Turns a sparse AWPTCM manual case into a refined case with declarative objects, Zephyr-ready test steps, and traceability — with a review gate at every step.",
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
  $: atLogo = $resolvedTheme === "dark" ? atLogoDark : atLogoLight;

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


</script>

<div class="home-page">
  <div class="home-banner-container">
    <div class="home-banner" style:--banner-logo={`url(${atLogo})`}>
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
          <p class="home-intro">
            Ask CK is a server-backed test-engineering workbench for the AWPTCM
            test-case program. It brings the tools for enriching manual test
            cases, mapping them to automation, and turning them into runnable
            scripts into one place. Pick a tool from below, or read the
            step-by-step guides inside the Help section. Most tools use an LLM
            via a local subscription CLI — set that up first under <span
              style="font-weight: bold;"
              >Settings → LLM → LLM Provider Login</span
            >.
          </p>
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

  {#if isAdmin}
    <AdminPanel />
  {/if}
</div>

<style>

  .home-page {
    flex: 1;
    margin: -16px 0;
    padding: 4rem 8rem 0 8rem;
  }

  .home-intro {
    padding: 12px;
  }
  .home-banner-container {
    position: relative; /* ::after is measured from here */
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
    content: '';
    position: absolute;
    inset: 0;
    z-index: -1;            
    background: linear-gradient(to bottom,
     var(--color-banner-gradient) 0%,    
    transparent 45%);           
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

</style>
