<script>
  import PageCard from '../lib/components/PageCard.svelte';
  import askCKLogo from '../assets/askck-logo.png';

  const page = {
    title: 'Welcome to Ask CK',
    intro:
      'Ask CK is a server-backed test-engineering workbench for the AWPTCM test-case program. It brings the tools for enriching manual test cases, mapping them to automation, and turning them into runnable scripts into one place. Pick a tool from below, or read the step-by-step guides inside the Help section. Most tools use an LLM via a local subscription CLI — set that up first under LLM — Configure.',
    cards: [
      { title: 'Test Case Generator', description: 'Turns a sparse AWPTCM manual case into a refined case with declarative objects, Zephyr-ready test steps, and traceability — with a review gate at every step.', accent: 'blue' },
      { title: 'PyTest Creator', description: 'Turns a complete case into a runnable Allied Telesis framework test script. Each step has a Confirm gate.', accent: 'gray' },
      { title: 'Test Composer', description: 'Builds reusable test flows and orchestration layers for complex validation scenarios.', accent: 'blue' },
      { title: 'Zephyr Templating', description: 'Maps refined cases into structured templates that match your Zephyr workflow and reporting needs.', accent: 'gray' }
    ]
  };
</script>

<div class="home-hero">
    <img src={askCKLogo} alt="Ask CK logo" />
    <h1>{page.title}</h1>
    <p>{page.intro}</p>
</div>

<div class="card-grid">
  {#each page.cards as card}
    <PageCard {card} />
  {/each}
</div>

<style>
    .home-hero {
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .home-hero img {
        width: 18em;
        height: auto;
        margin-bottom: 1rem;
    }
    
    .home-hero h1 {
        font-size: 3rem;
        margin-bottom: 0.5rem;
    }
    
    .home-hero p {
        font-size: 1.1rem;
    }
</style>