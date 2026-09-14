<script>
  import PageCard from '../lib/components/PageCard.svelte';

  const page = {
    title: 'Help',
    intro: 'Review onboarding material, walkthroughs, and troubleshooting guidance for the Ask CK workflow.',
    cards: [{ title: 'Quick start', description: 'Use the left-side tabs to move between major workflows and tools.', accent: 'blue' }]
  };
</script>

<div class="generic-page">
  <h1>{page.title}</h1>
  <p>{page.intro}</p>

  <div class="card-grid single-column">
    {#each page.cards as card}
      <PageCard {card} />
    {/each}
  </div>
</div>
