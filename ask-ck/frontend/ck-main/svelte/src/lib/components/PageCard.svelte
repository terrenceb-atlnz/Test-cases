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
      <div class="card-line"></div>
      <p>{card.description}</p>
      <img class="card-arrow" src={arrowRightIcon} alt="" aria-hidden="true" />
    </div>
  </div>

</button>

<style>
 
  .tool-card {
    --card-strip: 14px;                 
    position: relative;                
    width: 30rem;
    margin-bottom: var(--card-strip);   /* room for the closed strip, so it never overlaps */
    padding: 0;
    border: none;
    background: none;
    font: inherit;
    text-align: center;
    cursor: pointer;
  }

  /* Hovered card above its neighbours and the content below, so the grown panel overlays it. */
  .tool-card:hover,
  .tool-card:focus-visible {
    z-index: 10;
  }

  /* Top box: icon and title, always shown. */
  .header {
    display: flex;
    flex-direction: row;
    gap: 24px;
    align-items: center;
    justify-content: center;
    padding: 12px 12px 0px 12px;
    border: 3px solid var(--color-tool-card-border);
    border-bottom: none;
    border-radius: 10px 10px 0 0;
    background: var(--color-tool-card-bg);
    transition: background-color 0.2s ease, border-color 0.2s ease;
  }

  .tool-card:hover .header,
  .tool-card:focus-visible .header {
    border-color: var(--color-tool-card-border-hover);
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
  }

  .tool-card:hover h2 {
    color: var(--accent-color, var(--color-tool-card-hover-text, var(--color-accent)));
  }

  .card-line {
    margin-top: 10px;
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

  /* Bottom box: always shown as a strip (its bottom padding); the row inside opens 0fr → 1fr
     on hover. Absolutely placed under the card, so growing overlays what is below instead of
     pushing it down. */
  .card-reveal {
    position: absolute;
    top: 100%;                          /* starts at the card's bottom edge */
    left: 0;
    right: 0;
    padding: 0 18px var(--card-strip);  /* the bottom padding IS the closed strip */
    border: 3px solid var(--color-tool-card-border);
    border-top: none;                   /* joins onto .header */
    border-radius: 0 0 10px 10px;
    background: var(--color-tool-card-bg);
    display: grid;
    grid-template-rows: 0fr;
    transition: grid-template-rows 0.3s ease, background-color 0.2s ease, border-color 0.2s ease;
  }

  /* Must be allowed to shrink to 0, or the row can't close. Hidden while closed (only the
     strip shows), faded in as the box grows. */
  .card-reveal-inner {
    min-height: 0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    opacity: 0;
    transition: opacity 0.2s ease;
  }

  .tool-card:hover .card-reveal,
  .tool-card:focus-visible .card-reveal {
    grid-template-rows: 1fr;
    border-color: var(--color-tool-card-border-hover);
    background: var(--color-tool-card-bg-hover);
  }

  .tool-card:hover .card-reveal-inner,
  .tool-card:focus-visible .card-reveal-inner {
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
