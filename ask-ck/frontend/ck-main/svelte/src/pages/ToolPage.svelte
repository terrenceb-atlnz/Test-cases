<script>
// @ts-nocheck

  import PageCard from '../lib/components/PageCard.svelte';
  import PageHeader from '../lib/components/PageHeader.svelte';

  /**
   * @type {{
   *   title: string,
   *   intro: string,
   *   cards: Array<{ title: string, description: string, accent: string }>
   * }}
   */
  export let page;
</script>

<PageHeader title={page.title} intro={page.intro} />

<div class="generic-page">
  <div class="card-grid single-column">
    {#each page.cards as card}
      <PageCard {card} />
    {/each}
  </div>
</div>
