<script>
  import windowSidebarIcon from '../../assets/icons/panel-left.svg';

  /**
   * @type {{
   *   main: Array<{ id: string, label: string, icon: string }>,
   *   tool: Array<{ id: string, label: string, icon: string }>
   * }}
   */
  export let items = { main: [], tool: [] };

  /** @type {string} */
  export let activePage = 'home';

  /** @type {boolean} */
  export let collapsed = false;

  /** @type {(id: string) => void} */
  export let onSelect = () => {};

  /** @type {() => void} */
  export let onToggle = () => {};
</script>

<aside class="sidebar" class:collapsed={collapsed}>
  <button class="collapse-toggle" type="button" on:click={onToggle} aria-label="Toggle sidebar">
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
</aside>

<style>
  .sidebar-section-label {
    padding: 14px 14px 8px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: rgba(234, 246, 255, 0.7);
  }

  .nav-item {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    background: transparent;
    color: #dfeef8;
    border: none;
    padding: 12px 14px;
    border-radius: 8px;
    text-align: left;
    cursor: pointer;
    transition: background 0.2s ease, color 0.2s ease;
    font-weight: 600;

  }

  .nav-item:hover {
    background: rgba(255, 255, 255, 0.08);
  }

  .nav-item.active {
    background: var(--color-sidebar-nav-active-bg);
    color: var(--color-sidebar-nav-active-text);
  }

  .nav-icon-svg {
    width: 1.5em;
    height: auto;
    display: block;
    filter: var(--icon-filter-nav);
    flex-shrink: 0;
  }

  .nav-label {
    white-space: nowrap;
  }

  .collapse-toggle {
    width: 36px;
    height: 36px;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.2);
    background: rgba(255, 255, 255, 0.06);
    color: #fff;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    margin: 4px 8px 10px auto;
  }

  .collapse-toggle img {
    width: 1.5em;
    height: auto;
    filter: brightness(0) invert(1);
  }

  .collapse-toggle:hover {
    background: rgba(255, 255, 255, 0.12);
  }
</style>
