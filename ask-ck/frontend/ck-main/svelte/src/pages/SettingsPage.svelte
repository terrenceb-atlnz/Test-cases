<script>
// @ts-nocheck

  import PageHeader from '../lib/components/PageHeader.svelte';
  import settingsIcon from '../assets/icons/settings.svg';
  import wrenchIcon from '../assets/icons/wrench.svg';
  import chartIcon from '../assets/icons/chart-column.svg';
  import eyeIcon from '../assets/icons/eye.svg';
  import { theme, setTheme } from '../lib/theme.js';

  const tabs = [
    { id: 'general', label: 'General', icon: settingsIcon },
    { id: 'llm', label: 'LLM', icon: wrenchIcon },
    { id: 'usage', label: 'Usage', icon: chartIcon },
    { id: 'appearance', label: 'Appearance', icon: eyeIcon }
  ];

  let activeTab = 'general';

  function selectTab(id) {
    activeTab = id;
  }
</script>

<PageHeader title="Settings" intro="Settings and configurations for Ask CK" />

<div class="settings-layout">
  <div class="settings-tabs">
    {#each tabs as tab}
      <button
        type="button"
        class="settings-tab"
        class:active={activeTab === tab.id}
        on:click={() => selectTab(tab.id)}
      >
        {#if tab.icon}
          <img src={tab.icon} alt="" aria-hidden="true" />
        {/if}
        <span>{tab.label}</span>
      </button>
    {/each}
  </div>

  <div class="settings-panel">
      <!-- GENERAL TAB  -->
    {#if activeTab === 'general'}
      <div class="settings-box"></div>
      <div class="settings-box"></div>

    <!-- LLM TAB  -->
    {:else if activeTab === 'llm'}
      <div class="settings-box settings-box-text">
        <h3>Model setup</h3>
        <p>Configure your local LLM connection before running automation flows.</p>
      </div>

    <!-- USAGE TAB  -->
    {:else if activeTab === 'usage'}
      <div class="settings-box"></div>

    <!-- APPEARANCE TAB  -->
    {:else if activeTab === 'appearance'}
      <div class="settings-box settings-box-text">
        <h3>Display configuration</h3>
        <p>Configure your display preferences.</p>
        <div class="theme-options">
          <label class="theme-option">
            <input
              type="radio"
              name="theme"
              value="light"
              checked={$theme === 'light'}
              on:change={() => setTheme('light')}
            />
            Light
          </label>
          <label class="theme-option">
            <input
              type="radio"
              name="theme"
              value="dark"
              checked={$theme === 'dark'}
              on:change={() => setTheme('dark')}
            />
            Dark
          </label>
          <label class="theme-option">
            <input
              type="radio"
              name="theme"
              value="system"
              checked={$theme === 'system'}
              on:change={() => setTheme('system')}
            />
            System
          </label>
        </div>
      </div>
    {/if}
    
  </div>
</div>

<style>
  .settings-layout {
    display: flex;
    gap: 24px;
    align-items: flex-start;
  }

  .settings-tabs {
    display: flex;
    flex-direction: column;
    gap: 4px;
    width: 180px;
    flex-shrink: 0;
  }

  .settings-tab {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    padding: 10px 12px;
    background: transparent;
    border: none;
    border-radius: 8px;
    font: inherit;
    font-weight: 600;
    font-size: 0.94rem;
    color: var(--color-text-heading);
    text-align: left;
    cursor: pointer;
    transition: background-color 0.2s ease, color 0.2s ease;
  }

  .settings-tab img {
    width: 18px;
    height: 18px;
    flex-shrink: 0;
    filter: var(--icon-filter-heading);
  }

  .settings-tab:hover {
    background: rgba(0, 83, 143, 0.06);
  }

  .settings-tab.active {
    background: var(--color-accent);
    color: #fff;
  }

  .settings-tab.active img {
    filter: brightness(0) invert(1);
  }

  .settings-panel {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .settings-box {
    background: var(--color-bg-surface);
    border: 1px solid var(--color-border-surface);
    border-radius: 10px;
    min-height: 120px;
    padding: 20px;
    transition: background-color 0.2s ease, border-color 0.2s ease;
  }

  .settings-box-text h3 {
    margin: 0 0 6px;
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--color-text-heading);
  }

  .settings-box-text p {
    margin: 0;
    color: var(--color-text-muted);
    font-size: 0.94rem;
    line-height: 1.5;
  }

  .theme-options {
    display: flex;
    gap: 20px;
    margin-top: 16px;
  }

  .theme-option {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--color-text);
    font-size: 0.94rem;
    font-weight: 600;
    cursor: pointer;
  }

  .theme-option input {
    accent-color: var(--color-accent);
    width: 16px;
    height: 16px;
    cursor: pointer;
  }
</style>
