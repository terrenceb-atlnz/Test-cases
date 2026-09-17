<script>
  import arrowRightIcon from '../../assets/icons/arrow-right.svg';

  export let card = {
    title: '',
    description: '',
    icon: { src: '' }
  };
</script>

<button type="button" class="tool-card" on:click>
  <div class="card-icon">
    <img src={card.icon?.src} alt={card.title} />
  </div>
  <h2>{card.title}</h2>
  <p>{card.description}</p>
  <img class="card-arrow" src={arrowRightIcon} alt="" aria-hidden="true" />
</button>

<style>
  .tool-card {
    position: relative;
    min-height: 350px;
    width: 335px;
    max-width: 400px;
    border: 4px solid var(--color-tool-card-border);
    border-radius: 14px;
    background: var(--color-tool-card-bg);
    padding: 22px 18px 18px;
    text-align: center;
    display: flex;
    flex-direction: column;
    gap: 16px;
    box-shadow: inset 0 0 0 1px rgba(22, 64, 96, 0.06);
    transition: transform 0.2s ease-out, box-shadow 0.2s ease-out, background-color 0.2s ease, border-color 0.2s ease;
  }

  .tool-card:hover {
    box-shadow: inset 0 0 0 1px rgba(22, 64, 96, 0.06), 0 2px 8px rgba(22, 64, 96, 0.12);
    transform: translateY(-2px);
    cursor: pointer;
    border: 4px solid var(--color-tool-card-border-hover);
    background: var(--color-tool-card-bg-hover);
  }


  .tool-card h2 {
    margin: 0;
    font-size: 1.3rem;
    line-height: 1.3;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--color-tool-card-text);
    font-weight: 700;
    transition: color 0.2s ease;
  }

    .tool-card:hover h2{
    color: var(--accent-color, var(--color-tool-card-hover-text, var(--color-accent)));
  }


  .tool-card h2::after {
    content: '';
    display: block;
    width: 58px;
    height: 4px;
    margin: 6px auto 0;
    border-radius: 2px;
    background-color: var(--accent-color, var(--color-tool-card-text));
  }

  .tool-card:hover h2::after {
    content: '';
    display: block;
    width: 58px;
    height: 4px;
    margin: 6px auto 0;
    border-radius: 2px;
    background-color: var(--accent-color, #E20052);
  }

  .tool-card p {
    margin: 0;
    color: var(--color-tool-card-text);
    font-size: 0.98rem;
    line-height: 1.5;
    transition: color 0.2s ease;
  }

  .tool-card:hover p {
    color: var(--accent-color, var(--color-tool-card-hover-text, var(--color-accent)));
  }

  .card-icon img {
    width: 54px;
    height: 54px;
    margin: 0 auto;
    filter: var(--icon-filter-muted);
    transition: filter 0.2s ease;
  }

  .tool-card:hover .card-icon img {
    filter: var(--icon-filter-accent);
  }

  .card-arrow {
    position: absolute;
    right: 18px;
    bottom: 18px;
    width: 22px;
    height: 22px;
    filter: var(--icon-filter-arrow);
    transition: filter 0.5s ease;
  }

  .tool-card:hover .card-arrow {
    filter: var(--icon-filter-arrow-hover);
  }

</style>
