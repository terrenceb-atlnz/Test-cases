<script>
  import PageCard from '../lib/components/PageCard.svelte';

  /**
   * @type {{
   *   title: string,
   *   intro: string,
   *   cards: Array<{ title: string, description: string, accent: string }>
   * }}
   */
  export let page;
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
