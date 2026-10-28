<script>
  import windowSidebarIcon from "../../assets/icons/panel-left.svg";

  /**
   * @type {{
   *   main: Array<{ id: string, label: string, icon: string }>,
   *   tool: Array<{ id: string, label: string, icon: string }>
   * }}
   */
  export let items = { main: [], tool: [] };

  /** @type {string} */
  export let activePage = "home";

  /** @type {boolean} */
  export let collapsed = false;

  /** @type {(id: string) => void} */
  export let onSelect = () => {};

  /** @type {() => void} */
  export let onToggle = () => {};
</script>

<aside class="sidebar" class:collapsed>
  <button
    class="collapse-toggle"
    type="button"
    on:click={onToggle}
    aria-label="Toggle sidebar"
  >
    <img src={windowSidebarIcon} alt="Toggle sidebar" />
  </button>

  <div class="sidebar-section-label">MAIN</div>

  {#each items.main as item}
    <button
      class="nav-item"
      class:active={item.id === activePage}
      on:click={() => onSelect(item.id)}
      type="button"
      aria-label={item.label}
    >
      <img class="nav-icon-svg" src={item.icon} alt="" aria-hidden="true" />
      {#if !collapsed}<span class="nav-label">{item.label}</span>{/if}
    </button>
  {/each}

  <div class="sidebar-section-label">TOOLS</div>

  {#each items.tool as item}
    <button
      class="nav-item"
      class:active={item.id === activePage}
      on:click={() => onSelect(item.id)}
      type="button"
      aria-label={item.label}
    >
      <img class="nav-icon-svg" src={item.icon} alt="" aria-hidden="true" />
      {#if !collapsed}<span class="nav-label">{item.label}</span>{/if}
    </button>
  {/each}
  {#if !collapsed}<p class="sidebar-footer" aria-hidden="true">
      © 2026 Allied Telesis
    </p>{/if}
</aside>

<style>
  .sidebar-section-label {
    padding: 14px 12px 6px;
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--color-sidebar-section-label);
  }

  .nav-item {
    display: flex;
    align-items: center;
    font-size: 1.1rem;
    gap: 12px;
    width: 100%;
    background: transparent;
    color: var(--color-sidebar-nav-text);
    border: none;
    padding: 8px 20px 8px;
    border-radius: 5px;
    text-align: left;
    cursor: pointer;
    font-weight: 500;
    transition: background-color 0.2s ease, color 0.2s ease;
  }

  .nav-item:hover {
    background: var(--color-sidebar-nav-hover-bg);
  }

  .nav-item.active {
    background: var(--color-sidebar-nav-active-bg);
    /* color: var(--color-sidebar-nav-active-text); */
    /* border-left: 7px solid var(--color-sidebar-nav-active-side); */
    /* padding-left: 1.3rem; */
    transition: background-color 0.2s ease, color 0.2s ease;
  }

  .nav-icon-svg {
    width: 1.3em;
    height: auto;
    display: block;
    filter: var(--icon-filter-nav);
    flex-shrink: 0;
  }

  /* White icon on the filled active item, in both themes. */
  /* .nav-item.active .nav-icon-svg {
    filter: brightness(0) invert(1);
  } */

  .nav-label {
    white-space: nowrap;
    font-size: 0.9rem;
  }

  .collapse-toggle {
    width: 36px;
    height: 36px;
    border-radius: 8px;
    border: 1px solid var(--color-sidebar-toggle-border);
    background: rgba(255, 255, 255, 0.06);
    color: var(--color-sidebar-nav-text);
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    margin: 4px 12px 10px auto;
  }

  .collapse-toggle img {
    width: 1.3em;
    height: auto;
    filter: var(--icon-filter-nav);
  }

  .collapse-toggle:hover {
    background: var(--color-sidebar-nav-hover-bg);
  }

  .sidebar-footer {
    margin-top: auto;
    font-size: 0.72rem;
    color: var(--color-sidebar-section-label);
    text-align: left;
  }
</style>
