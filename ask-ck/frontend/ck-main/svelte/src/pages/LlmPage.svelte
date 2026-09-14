<script>
  import PageCard from '../lib/components/PageCard.svelte';

  const page = {
    title: 'LLM',
    intro: 'Set your local model configuration, review available providers, and confirm the environment is ready for generation tasks.',
    cards: [{ title: 'Model setup', description: 'Configure your local LLM connection before running automation flows.', accent: 'blue' }]
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
