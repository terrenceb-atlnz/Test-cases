<script>
// @ts-nocheck

  import PageHeader from '../lib/components/PageHeader.svelte';
  import Button from '../lib/components/Button.svelte';
  import settingsIcon from '../assets/icons/settings.svg';
  import wrenchIcon from '../assets/icons/wrench.svg';
  import chartIcon from '../assets/icons/chart-column.svg';
  import eyeIcon from '../assets/icons/eye.svg';
  import { theme, setTheme, resolvedTheme } from '../lib/theme.js';
  import localLlmIconDark from '../assets/local-llm.png';
  import localLlmIconLight from '../assets/local-llm-light.png';
  import claudeLlmIconDark from '../assets/claude-llm.png';
  import claudeLlmIconLight from '../assets/claude-llm-light.png';
import UnderConstruction from '../lib/components/UnderConstruction.svelte';

  const tabs = [
    { id: 'general', label: 'General', icon: settingsIcon },
    { id: 'llm', label: 'LLM', icon: wrenchIcon },
    { id: 'usage', label: 'Usage', icon: chartIcon },
  ];

  let activeTab = 'general';

  function selectTab(id) {
    activeTab = id;
  }

  $: providers = [
    { id: 'local-llm', title: 'Local LLM', icon: $resolvedTheme === 'dark' ? localLlmIconLight : localLlmIconDark },
    { id: 'claude-cli', title: 'Claude Code', icon: $resolvedTheme === 'dark' ? claudeLlmIconLight : claudeLlmIconDark }
  ];

  let activeProvider = 'local-llm';

  let localLlmMode = 'fast';
  let localLlmModelOverride = '';

  let claudeModel = 'sonnet';
  let claudeModelOverride = '';
  let unitFillsRoute = '';
  let stepMatchingRoute = '';

  function checkLocalLlmHealth() {
    // TODO: wire up a real health check call to the local LLM
  }

  function checkLocalAgent() {
    // TODO: wire up a real reachability/login check for the local Claude Code agent
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

    <!-- LLM TAB  -->
    {:else if activeTab === 'llm'}
      <div class="llm-section">
        <h3>LLM Provider Login</h3>
        <!-- <p class="llm-subtitle">Log in to an LLM provider via a local subscription CLI.</p>
        <hr class="llm-rule" /> -->
        <p class="llm-description">
          Use a locally logged-in subscription CLI or the org's vLLM — no developer API keys.
          Apply / Login saves the workspace default; it is applied to cases as they load. The two
          Claude options differ in whose seat pays: my local machine brokers each call through an
          agent on the user's own box, so seats are never shared; this server runs claude here and
          spends this server's single seat for everyone. Pick the second only for a shared or
          headless deployment.
        </p>

        <div class="provider-list">
          {#each providers as provider}
            <div class="provider-card" class:active={activeProvider === provider.id}>
              <div class="provider-identity">
                <h4 class="provider-title">{provider.title}</h4>
                <img class="provider-icon" src={provider.icon} alt="" aria-hidden="true" />
              </div>

              <div class="provider-divider"></div>

              <div class="provider-config">
                {#if provider.id === 'local-llm'}
                  <p class="provider-field-label">Mode</p>
                  <div class="provider-field-row">
                    <label class="provider-radio">
                      <input type="radio" name="local-llm-mode" value="fast" bind:group={localLlmMode} />
                      Fast
                    </label>
                    <label class="provider-radio">
                      <input type="radio" name="local-llm-mode" value="thinking" bind:group={localLlmMode} />
                      Thinking
                    </label>
                    <input type="text" placeholder="Local LLM API key (leave blank to keep stored key)" class="provider-text-input" bind:value={localLlmModelOverride} />
                    <Button variant="outline" on:click={checkLocalLlmHealth}>Check Health</Button>
                  </div>
                {:else if provider.id === 'claude-cli'}
                  <p class="provider-field-label">Model</p>
                  <div class="provider-field-row">
                    <label class="provider-radio">
                      <input type="radio" name="claude-model" value="haiku" bind:group={claudeModel} />
                      Haiku
                    </label>
                    <label class="provider-radio">
                      <input type="radio" name="claude-model" value="sonnet" bind:group={claudeModel} />
                      Sonnet
                    </label>
                    <label class="provider-radio">
                      <input type="radio" name="claude-model" value="opus" bind:group={claudeModel} />
                      Opus
                    </label>
                    <input type="text" class="provider-text-input" bind:value={claudeModelOverride} />
                    <Button variant="outline" on:click={checkLocalAgent}>Check local agent</Button>
                  </div>

                  <p class="provider-field-label">Route</p>
                  <div class="provider-field-row">
                    <span class="provider-field-inline-label">unit fills:</span>
                    <select class="provider-select" bind:value={unitFillsRoute}>
                      <option value=""></option>
                    </select>
                    <span class="provider-field-inline-label">step matching:</span>
                    <select class="provider-select" bind:value={stepMatchingRoute}>
                      <option value=""></option>
                    </select>
                  </div>
                {/if}
              </div>

              {#if activeProvider === provider.id}
                <span class="provider-status">Using</span>
              {:else}
                <Button variant="primary" class="provider-position" on:click={() => (activeProvider = provider.id)}>Apply</Button>
              {/if}
            </div>
          {/each}
        </div>

        <div class="llm-note">
          <h4>Claude Code CLI — via your local agent (per-user, unshared)</h4>
          <p>
            On a shared Ask CK page, the server never runs <code>claude</code>. Instead, a tiny
            agent on <strong>your own machine</strong> runs it against <strong>your own</strong>
            Claude login, brokered through this browser tab. Your seat is never shared with
            other users, and the server never sees your credentials.
          </p>
          <ol>
            <li>On your machine, install Claude Code (anthropic.com/claude-code) and run <code>claude → /login</code>.</li>
            <li>Start the agent: <code>cd ask-ck/agent && ./run-agent.sh</code> (leave it running). See <code>ask-ck/agent/README.md</code>.</li>
            <li>Click <strong>"Check my local agent"</strong> to confirm it's reachable and logged in.</li>
            <li>Click <strong>"Apply / Login"</strong>. Leave Model blank to use the CLI's default.</li>
          </ol>
          <p class="llm-note-footer"><em>Usage counts against your own Claude seat's limits. If a call fails, make sure the agent is still running and you're logged in.</em></p>
        </div>
      </div>

    <!-- USAGE TAB  -->
    {:else if activeTab === 'usage'}
      <UnderConstruction />
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
    margin: 0 0 4px;
    font-size: 1.15rem;
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

  .llm-section {
    background: var(--color-bg-surface);
    border: 1px solid var(--color-border-surface);
    border-radius: 10px;
    padding: 20px;
    transition: background-color 0.2s ease, border-color 0.2s ease;
  }

  .llm-section h3 {
    margin: 0 0 4px;
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--color-text-heading);
  }
/* 
  .llm-subtitle {
    margin: 0;
    color: var(--color-text-muted);
    font-size: 0.9rem;
  }

  .llm-rule {
    border: none;
    border-top: 1px solid var(--color-border-surface);
    margin: 14px 0;
  } */

  .llm-description {
    margin: 0 0 20px;
    color: var(--color-text-muted);
    font-size: 0.92rem;
    line-height: 1.6;
  }

  .llm-note {
    margin-top: 20px;
  }

  .llm-note h4 {
    margin: 0 0 10px;
    font-size: 1rem;
    font-weight: 700;
    color: var(--color-text-heading);
  }

  .llm-note p {
    margin: 0 0 14px;
    color: var(--color-text-muted);
    font-size: 0.92rem;
    line-height: 1.6;
  }

  .llm-note strong {
    color: var(--color-text-heading);
  }

  .llm-note code {
    background: var(--color-code-bg);
    padding: 1px 5px;
    border-radius: 4px;
    font-size: 0.88em;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  }

  .llm-note ol {
    margin: 0 0 14px;
    padding-left: 20px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    color: var(--color-text-muted);
    font-size: 0.92rem;
    line-height: 1.5;
  }

  .llm-note-footer {
    margin-bottom: 0 !important;
  }

  .provider-list {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .provider-card {
    position: relative;
    display: flex;
    align-items: stretch;
    gap: 20px;
    border: 1px solid var(--color-border-surface);
    background: var(--color-bg-surface);
    border-radius: 10px;
    padding: 20px;
    min-height: 12em;
    transition: background-color 0.2s ease, border-color 0.2s ease;
  }

  .provider-card.active {
    border: 2px solid var(--color-accent);
    background: color-mix(in srgb, var(--color-accent) 10%, var(--color-bg-surface));
  }

  .provider-identity {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
    flex: 0 0 auto;
    min-width: 100px;
  }

  .provider-title {
    margin: 0;
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--color-text-heading);
  }

  .provider-icon {
    width: auto;
    height: 5em;
    display: block;
  }

  .provider-divider {
    flex: 0 0 auto;
    width: 1px;
    align-self: stretch;
    background: var(--color-border-surface);
  }

  .provider-config {
    flex: 1;
    min-width: 0;
    padding-bottom: 36px;
  }

  .provider-field-label {
    margin: 0 0 8px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--color-text-muted);
  }

  .provider-field-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 14px;
    margin-bottom: 18px;
  }

  .provider-field-row:last-child {
    margin-bottom: 0;
  }

  .provider-radio {
    display: flex;
    align-items: center;
    gap: 6px;
    color: var(--color-text);
    font-size: 0.9rem;
    cursor: pointer;
  }

  .provider-radio input {
    accent-color: var(--color-accent);
    width: 15px;
    height: 15px;
    cursor: pointer;
  }

  .provider-text-input {
    width: 200px;
    padding: 6px 10px;
    border-radius: 8px;
    border: 1px solid var(--color-border-surface);
    background: var(--color-bg-surface);
    color: var(--color-text);
    font: inherit;
    font-size: 0.88rem;
  }

  .provider-field-inline-label {
    color: var(--color-text-muted);
    font-size: 0.88rem;
  }

  .provider-select {
    padding: 6px 10px;
    border-radius: 8px;
    border: 1px solid var(--color-border-surface);
    background: var(--color-bg-surface);
    color: var(--color-text);
    font: inherit;
    font-size: 0.88rem;
    min-width: 200px;
  }

  .provider-status,
  :global(.provider-position) {
    position: absolute;
    right: 20px;
    bottom: 20px;
  }

  .provider-status {
    padding: 6px 16px;
    border-radius: 999px;
    font: inherit;
    font-weight: 600;
    font-size: 0.85rem;
    border: 1px solid var(--color-accent);
    color: var(--color-accent);
    background: transparent;
  }
</style>
