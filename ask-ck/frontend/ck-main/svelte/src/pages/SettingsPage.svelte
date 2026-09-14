<script>
  import PageCard from '../lib/components/PageCard.svelte';

  const page = {
    title: 'Settings',
    intro: 'Adjust workspace preferences, application defaults, and operational behaviour.',
    cards: [{ title: 'Preferences', description: 'Tune the workspace for your test-generation workflow.', accent: 'gray' }]
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
