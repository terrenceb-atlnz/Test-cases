<script>
// @ts-nocheck

  import PageCard from '../lib/components/PageCard.svelte';
  import { resolvedTheme } from '../lib/theme.js';
  import askCKLogoDark from '../assets/askck-logo.png';
  import askCKLogoLight from '../assets/askck-logo-light.png';
  import testCaseIcon from '../assets/icons/clipboard-list.svg';
  import pytestIcon from '../assets/icons/pytest.svg';
  import testComposerIcon from '../assets/icons/list-check.svg';
  import zephyrIcon from '../assets/icons/getzephyr-icon.svg';

  const page = {
    cards: [
      { title: 'Test Case Generator', description: 'Turns a sparse AWPTCM manual case into a refined case with declarative objects, Zephyr-ready test steps, and traceability — with a review gate at every step.', icon: { src: testCaseIcon } },
      { title: 'PyTest Creator', description: 'Turns a complete case into a runnable Allied Telesis framework test script. Each step has a Confirm gate.', icon: { src: pytestIcon } },
      { title: 'Test Composer', description: 'Builds reusable test flows and orchestration layers for complex validation scenarios.', icon: { src: testComposerIcon } },
      { title: 'Zephyr Templating', description: 'Maps refined cases into structured templates that match your Zephyr workflow and reporting needs.', icon: { src: zephyrIcon } }
    ]
  };

  $: askCKLogo = $resolvedTheme === 'dark' ? askCKLogoLight : askCKLogoDark;
</script>

<div class="home-hero">
    <img src={askCKLogo} alt="Ask CK logo" />
    <h1>Welcome to Ask CK</h1>
    <p>Ask CK is a server-backed test-engineering workbench for the AWPTCM test-case program. It brings the tools for enriching manual test cases, mapping them to automation, and turning them into runnable scripts into one place. Pick a tool from below, or read the step-by-step guides inside the Help section. Most tools use an LLM via a local subscription CLI — set that up first under <span style="font-weight: bold;">LLM → Configure</span>.</p>
</div>
<div class="card-container">
  <div class="card-grid">
    {#each page.cards as card}
      <PageCard {card} />
    {/each}
  </div>
</div>

<style>
    .home-hero {
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
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
        font-size: 1.1rem;
        color: var(--color-text-muted);
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
        align-items: center;
        justify-content: center;
        text-align: center;
    }

</style>