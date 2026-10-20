<script>
  import arrowRightIcon from '../../assets/icons/arrow-right.svg';

  export let card = {
    title: '',
    description: '',
    icon: { src: '' }
  };
</script>

<button type="button" class="tool-card" on:click>
  <div class="header">
    <div class="card-icon">
      <img src={card.icon?.src} alt={card.title} />
    </div>
    <h2>{card.title}</h2>
  </div>

  <!-- Hidden until hover / keyboard focus, then drops open; icon and title stay visible. -->
  <div class="card-reveal">
    <div class="card-reveal-inner">
      <p>{card.description}</p>
      <img class="card-arrow" src={arrowRightIcon} alt="" aria-hidden="true" />
    </div>
  </div>

  <div class="card-line"></div>
</button>

<style>
  .tool-card {
    position: relative;
    min-height: 0;                
    width: 30rem;
    border: 3px solid var(--color-tool-card-border);
    border-radius: 10px;
    background: var(--color-tool-card-bg);
    padding: 12px 18px 12px;
    text-align: center;
    display: flex;
    flex-direction: column;      
    align-items: center;
    gap: 4px;
    box-shadow: inset 0 0 0 1px rgba(22, 64, 96, 0.06);
    transition: transform 0.2s ease-out, box-shadow 0.2s ease-out, background-color 0.2s ease, border-color 0.2s ease;
  }

  .header {
    display: flex;
    flex-direction: row;
    gap: 24px;
    align-items: center;
  }

  .tool-card:hover {
    /* box-shadow: inset 0 0 0 1px rgba(22, 64, 96, 0.06), 0 5px 8px rgba(22, 64, 96, 0.378); */
    /* transform: translateY(-2px); */
    cursor: pointer;
    border: 3px solid var(--color-tool-card-border-hover);
    background: var(--color-tool-card-bg-hover);
  }


  .tool-card h2 {
    margin: 0;
    font-size: 0.94rem;
    line-height: 1.3;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--color-tool-card-text);
    font-weight: 700;
    transition: color 0.2s ease;
    /* margin-top: 8px; */
  }

  .tool-card:hover h2{
    color: var(--accent-color, var(--color-tool-card-hover-text, var(--color-accent)));
  }

  .card-line {
    align-self: stretch;
    border-bottom: 4px solid var(--color-tool-card-border);
  }

  .tool-card:hover .card-line {
    border-bottom: 4px solid var(--accent-color, #E20052);
  }

  .tool-card p {
    margin: 0;
    color: var(--color-tool-card-text);
    font-size: 1rem;
    line-height: 1.5;
    transition: color 0.2s ease;
    font-style: italic;
    padding-top: 1rem;
  }

  .tool-card:hover p {
    color: var(--accent-color, var(--color-tool-card-hover-text, var(--color-accent)));
  }

  .card-icon img {
    width: 2rem;
    height: auto;
    margin: 0 auto;
    filter: var(--icon-filter-muted);
    transition: filter 0.2s ease;
  }

  .tool-card:hover .card-icon img {
    filter: var(--icon-filter-accent);
  }

  /* The drop-down: a one-row grid animated from 0fr (closed) to 1fr (the content's own
     height), which `height: auto` cannot transition. */
  .card-reveal {
    display: grid;
    grid-template-rows: 0fr;
    width: 100%;
    opacity: 0;
    transition: grid-template-rows 0.3s ease, opacity 0.2s ease;
  }

  /* Must be allowed to shrink to 0, or the row can't close. */
  .card-reveal-inner {
    min-height: 0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
  }

  .tool-card:hover .card-reveal,
  .tool-card:focus-visible .card-reveal {
    grid-template-rows: 1fr;
    opacity: 1;
  }

  /* Sits at the end of the revealed description, not pinned to the card's corner. */
  .card-arrow {
    align-self: flex-end;
    width: 22px;
    height: 22px;
    filter: var(--icon-filter-arrow);
    transition: filter 0.5s ease;
  }

  .tool-card:hover .card-arrow {
    filter: var(--icon-filter-arrow-hover);
  }

</style>
