<script>
  //@ts-nocheck
  import { onDestroy, onMount } from 'svelte';

  import houseIcon from './assets/icons/house.svg';
  import helpIcon from './assets/icons/circle-question-mark.svg';
  import settingsIcon from './assets/icons/settings.svg';

  import testCaseIcon from './assets/icons/clipboard-list.svg';
  import pytestIcon from './assets/icons/pytest.svg';
  import testComposerIcon from './assets/icons/list-check.svg';
  import zephyrIcon from './assets/icons/getzephyr-icon.svg';

  import Sidebar from './lib/components/Sidebar.svelte';
  import Topbar from './lib/components/Topbar.svelte';

  import { loadConfig } from './lib/services/llmConfigService.js';
  import { deepLink } from './lib/components/testcomposer/testComposerModel.js';
  import { ckBrokerLoop } from './lib/services/agentService.js';
  import { startVersionWatch } from './lib/services/versionService.js';
  import ConfirmModal from './lib/components/ConfirmModal.svelte';

  import HomePage from './pages/HomePage.svelte';
  import HelpPage from './pages/HelpPage.svelte';
  import SettingsPage from './pages/SettingsPage.svelte';
  import CaseGeneratorPage from './pages/GeneratorPage.svelte';
  import PyTestPage from './pages/PyTestPage.svelte';
  import TestComposerPage from './pages/TestComposerPage.svelte';
  import ZephyrPage from './pages/ZephyrPage.svelte';

  const navigation = {
    main: [
      { id: 'home', label: 'Home', icon: houseIcon },
      { id: 'help', label: 'Help', icon: helpIcon },
      { id: 'settings', label: 'Settings', icon: settingsIcon }
    ],
    tool: [
      { id: 'generator', label: 'Objective Generator', icon: testCaseIcon },
      { id: 'pytest', label: 'PyTest Creator', icon: pytestIcon },
      { id: 'composer', label: 'Test Composer', icon: testComposerIcon },
      { id: 'zephyr', label: 'Zephyr Templating', icon: zephyrIcon }
    ]
  };

/** @type {Record<string, string>} */
  const routeMap = {
    home: '/',
    help: '/help',
    settings: '/settings',
    generator: '/generator',
    pytest: '/pytest',
    composer: '/composer',
    zephyr: '/zephyr'
  };

  /** @type {string} */
  let activePage = 'home';

  // Stale-tab guard (versionService.js, ported from current/shared/version.js): the server's
  // build id moved while this tab was open, so it is running an older bundle. Prompt only —
  // the reload is the user's click, never automatic (unsaved work, live case locks).
  let serverUpdated = false;
  let stopVersionWatch = null;

  // The Objective Generator keeps its whole component instance mounted (hidden via CSS,
  // never destroyed) once first visited, so switching to another sidebar item and back
  // preserves everything — loaded session, chosen candidates, current step — with no
  // persistence code. Every other page still destroys/recreates normally on nav away,
  // matching how they behaved before (e.g. Settings' cold-load-on-mount refiring is
  // desirable there, not a bug). Only a real browser refresh loses the Generator's state.
  let generatorEverVisited = false;
  $: if (activePage === 'generator') generatorEverVisited = true;

  let pyTestEverVisited = false;
  $: if (activePage === 'pytest') pyTestEverVisited = true;

  // Test Composer and Zephyr Templating are kept alive the same way.
  let composerEverVisited = false;
  $: if (activePage === 'composer') composerEverVisited = true;

  let zephyrEverVisited = false;
  $: if (activePage === 'zephyr') zephyrEverVisited = true;

  // Test Composer reads `preselect` only when it mounts, so a navigation that carries one
  // (PyTest Creator's "Validate Test") remounts it; a plain sidebar visit keeps its state.
  let composerInstanceKey = 0;

  // Bumped to force PyTestPage to remount from scratch — used both for "Create Another
  // PyTest" (caseId omitted) and for switching to a different case mid-session (caseId given),
  // so a stale case's downstream state (sequence/scripts/fragments/generate/...) can never leak
  // into the next one: the whole component instance is thrown away and re-initialized instead of
  // trying to manually reset every field.
  let pytestInstanceKey = 0;

  /** @type {string | null} */
  let pendingPytestCaseId = null;

  /** @param {string | null} [caseId] */
  function resetPytest(caseId = null) {
    pendingPytestCaseId = caseId;
    pytestInstanceKey += 1;
  }

  // Same remount-on-case-switch mechanism, for the Objective Generator.
  let generatorInstanceKey = 0;

  /** @type {string | null} */
  let pendingGeneratorCaseId = null;

  /** @param {string | null} [caseId] */
  function resetGenerator(caseId = null) {
    pendingGeneratorCaseId = caseId;
    generatorInstanceKey += 1;
  }

  /** @type {boolean} */
  let sidebarCollapsed = false;

  /**
   * @param {string} path
   */
  function syncActivePageFromPath(path) {
    const normalized = (path || '/').replace(/\/+$/, '') || '/';
    const matchingKey = Object.entries(routeMap).find(([, route]) => route === normalized)?.[0] || 'home';
    activePage = matchingKey;
  }

  /**
   * @param {string} pageId
   */
  // What to select when Test Composer opens (PyTest Creator's "Validate Test" passes the case
  // key). Set on every navigation, so a plain sidebar click to Test Composer starts clean.
  let composerPreselect = null;
  // A deep link's tab and run id (testComposerModel.deepLink) — set with the preselect, cleared the same way.
  let composerTab = null;
  let composerOpenRun = null;
  let helpOpenSetupGuide = false;
  let settingsInitialTab = 'general';

  /** @param {string} pageId @param {{ preselect?: string | null, openRun?: string | null, openSetupGuide?: boolean, tab?: string }} [opts] */
  function selectPage(pageId, opts = {}) {
    composerPreselect = opts.preselect ?? null;
    composerOpenRun = opts.openRun ?? null;
    composerTab = pageId === 'composer' ? (opts.tab ?? null) : null;
    if (pageId === 'composer' && (composerPreselect || composerOpenRun || composerTab)) composerInstanceKey += 1;
    helpOpenSetupGuide = opts.openSetupGuide ?? false;
    settingsInitialTab = opts.tab ?? 'general';
    activePage = pageId;

    const target = routeMap[pageId] || '/';
    if (window.location.pathname !== target) {
      window.history.pushState({}, '', target);
    }
  }

  onDestroy(() => stopVersionWatch && stopVersionWatch());

  function toggleSidebar() {
    sidebarCollapsed = !sidebarCollapsed;
  }

  onMount(() => {
    syncActivePageFromPath(window.location.pathname);

    // A deep link the server wrote (Finalize's link in Zephyr, the run e-mails) or Classic's
    // `?panel=` form wins over the path: open Test Composer on the tab it names, with its script
    // or run (PLAN-svelte-cutover D7, ported 2026-10-30). Read once, at load.
    const link = deepLink(window.location.search, window.location.pathname);
    if (link) selectPage('composer', { preselect: link.preselect, openRun: link.openRun, tab: link.tab });

    stopVersionWatch = startVersionWatch(() => (serverUpdated = true));

    const handlePopState = () => {
      syncActivePageFromPath(window.location.pathname);
    };

    window.addEventListener('popstate', handlePopState);

    // Starting the broker only from SettingsPage.svelte meant any session that went
    // straight to a tool page without visiting Settings first had no broker running at
    // all — a claude_agent-mode LLM call would sit unclaimed for 60s and silently "fail"
    // with an empty result (see Generator Suggest-with-LLM, 2026-10-01). Cold-load the
    // effective config here instead, app-wide, so this can't depend on which page loads
    // first. SettingsPage's own load/Apply calls remain — this is additive, and
    // ckBrokerLoop() is a no-op when a live loop already exists.
    loadConfig().then((config) => {
      if (config?.auth_method === 'claude_agent') ckBrokerLoop();
    });

    return () => {
      window.removeEventListener('popstate', handlePopState);
    };
  });

</script>

<ConfirmModal
  bind:open={serverUpdated}
  title="Server updated"
  message="This page is running an older version of Ask CK. Refresh to load the current one. Anything you have not saved will be lost."
  confirmText="Refresh page"
  cancelText="Not now"
  onConfirm={() => window.location.reload()}
/>

<div class="app-shell" style:--sidebar-width={sidebarCollapsed ? '80px' : '240px'}>
  <Sidebar items={navigation} activePage={activePage} collapsed={sidebarCollapsed} onSelect={selectPage} onToggle={toggleSidebar} />
  <Topbar />

  <main class="content-panel" class:home={activePage === 'home'}>
    <div class="content-inner">
      {#if activePage === 'home'}
        <HomePage onNavigate={selectPage} />
      {:else if activePage === 'help'}
        <HelpPage openSetupGuide={helpOpenSetupGuide} />
      {:else if activePage === 'settings'}
        <SettingsPage initialTab={settingsInitialTab} />
      {:else if activePage === 'generator'}
        <!-- Rendered unconditionally below instead, hidden via CSS once first visited — see
             generatorEverVisited above. -->
      {:else if activePage === 'pytest'}
        <!-- {#key pytestInstanceKey}
          <PyTestPage onNavigate={selectPage} onCreateAnother={resetPytest} initialCaseId={pendingPytestCaseId} />
        {/key} -->
      {:else if activePage === 'composer' || activePage === 'zephyr'}
        <!-- Kept alive below, like the Generator and PyTest Creator. -->
      {/if}

      {#if generatorEverVisited}
        <div class="keep-alive-page" style:display={activePage === 'generator' ? 'contents' : 'none'}>
          {#key generatorInstanceKey}
            <CaseGeneratorPage onCreateAnother={resetGenerator} initialCaseId={pendingGeneratorCaseId} />
          {/key}
        </div>
      {/if}

      {#if pyTestEverVisited}
        <div class="keep-alive-page" style:display={activePage === 'pytest' ? 'contents' : 'none'}>
          {#key pytestInstanceKey}
            <PyTestPage onNavigate={selectPage} onCreateAnother={resetPytest} initialCaseId={pendingPytestCaseId} />
          {/key}
        </div>
      {/if}

      {#if composerEverVisited}
        <div class="keep-alive-page" style:display={activePage === 'composer' ? 'contents' : 'none'}>
          {#key composerInstanceKey}
            <TestComposerPage preselect={composerPreselect} initialTab={composerTab} openRun={composerOpenRun} />
          {/key}
        </div>
      {/if}

      {#if zephyrEverVisited}
        <div class="keep-alive-page" style:display={activePage === 'zephyr' ? 'contents' : 'none'}>
          <ZephyrPage />
        </div>
      {/if}
    </div>
  </main>
</div>

