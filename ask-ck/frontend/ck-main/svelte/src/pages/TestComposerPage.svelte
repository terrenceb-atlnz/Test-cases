<script>
// @ts-nocheck

  import PageCard from '../lib/components/PageCard.svelte';
  import PageHeader from '../lib/components/PageHeader.svelte';
  import ToolHeader from '../lib/components/ToolHeader.svelte';
  import TcValidate from '../lib/components/testcomposer/TcValidate.svelte';
  import TcCompose from '../lib/components/testcomposer/TcCompose.svelte';
  import TcRun from '../lib/components/testcomposer/TcRun.svelte';

  import checkicon from '../assets/icons/circle-check-big.svg'
  import playIcon from '../assets/icons/circle-play.svg'
  import scriptsIcon from '../assets/icons/file-stack.svg'
  import composerIcon from '../assets/icons/list-check.svg'
    import { assembleScript } from '../lib/services/pytest/generateService';

  // The three Test Composer pages, switched by the tab buttons below — each its own component
  // in lib/components/testcomposer/.
  const tabs = [
    { id: 'validate', label: 'Validate a Script', icon: checkicon},
    { id: 'compose', label: 'Compose a Run', icon: playIcon },
    { id: 'run', label: 'Run Scripts', icon:scriptsIcon},
  ];

  let activeTab = 'validate';
</script>

<ToolHeader title={tabs.find(t => t.id === activeTab)?.label} tool="TEST COMPOSER" icon={composerIcon}/>

<div class="generic-page">
  <!-- Same button look as the Settings tabs, laid out across the top. -->

  <!-- <div class="section-description">Run one saved script on a bench through your seat agent; repair, review, Finalize.</div> -->

  <div class="composer-tabs" role="tablist">
    {#each tabs as tab}
      <button
        type="button"
        role="tab"
        class="composer-tab"
        class:active={activeTab === tab.id}
        aria-selected={activeTab === tab.id}
        on:click={() => (activeTab = tab.id)}
      ><img src={tab.icon} class='tab-icon' alt=''>{tab.label}</button>
    {/each}
  </div>

  <div class="composer-panel" role="tabpanel">
    {#if activeTab === 'validate'}
      <TcValidate />
    {:else if activeTab === 'compose'}
      <TcCompose />
    {:else if activeTab === 'run'}
      <TcRun />
    {/if}
  </div>
</div>

<style>

  .generic-page {
  flex: 1;
  min-height: 0;
  }

  .composer-tabs {
    display: flex;
    align-items: center;
    gap: 2px;                 
    border-bottom: 3px solid var(--color-border-surface);
    padding-left: 32px;        
  }

  .composer-tab {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 20vw;;
    padding: 10px 16px;
    margin-bottom: -3px;
    border: 3px solid var(--color-border-surface);
    border-radius: 10px 10px 0 0;
    background: var(--color-tc-inactive-bg);
    font: inherit;
    font-weight: 700;
    font-size: 0.94rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--color-text-muted);
    cursor: pointer;
  }

  .tab-icon {
    width: 18px;
    height: 18px;
    flex-shrink: 0;
    filter: var(--filter-text-muted);
  }

  .composer-tab.active .tab-icon {
    filter: var(--filter-text-heading);
  }

  .composer-tab:hover {
    background: rgba(0, 83, 143, 0.06);
  }

  .composer-tab.active {
    background: var(--color-bg-content);
    border-bottom-color: var(--color-bg-content);
    color: var(--color-text-heading);
  }

  .composer-panel {
    width: 100%;
    flex: 1;
    display: flex;
    flex-direction: column;
  }
</style>
