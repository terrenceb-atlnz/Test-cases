<script>
  import { onMount } from 'svelte';

  import houseIcon from './assets/icons/house.svg';
  import helpIcon from './assets/icons/circle-question-mark.svg';
  import settingsIcon from './assets/icons/settings.svg';

  import testCaseIcon from './assets/icons/clipboard-list.svg';
  import pytestIcon from './assets/icons/pytest.svg';
  import testComposerIcon from './assets/icons/list-check.svg';
  import zephyrIcon from './assets/icons/getzephyr-icon.svg';

  import Sidebar from './lib/components/Sidebar.svelte';
  import Topbar from './lib/components/Topbar.svelte';

  import HomePage from './pages/HomePage.svelte';
  import HelpPage from './pages/HelpPage.svelte';
  import SettingsPage from './pages/SettingsPage.svelte';
  import ToolPage from './pages/ToolPage.svelte';
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

  // The Objective Generator keeps its whole component instance mounted (hidden via CSS,
  // never destroyed) once first visited, so switching to another sidebar item and back
  // preserves everything — loaded session, chosen candidates, current step — with no
  // persistence code. Every other page still destroys/recreates normally on nav away,
  // matching how they behaved before (e.g. Settings' cold-load-on-mount refiring is
  // desirable there, not a bug). Only a real browser refresh loses the Generator's state.
  let generatorEverVisited = false;
  $: if (activePage === 'generator') generatorEverVisited = true;

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
  function selectPage(pageId) {
    activePage = pageId;

    const target = routeMap[pageId] || '/';
    if (window.location.pathname !== target) {
      window.history.pushState({}, '', target);
    }
  }

  function toggleSidebar() {
    sidebarCollapsed = !sidebarCollapsed;
  }

  onMount(() => {
    syncActivePageFromPath(window.location.pathname);

    const handlePopState = () => {
      syncActivePageFromPath(window.location.pathname);
    };

    window.addEventListener('popstate', handlePopState);

    return () => {
      window.removeEventListener('popstate', handlePopState);
    };
  });

  /**
   * @type {{
   *   [key: string]: {
   *     title: string,
   *     intro: string,
   *     cards: Array<{ title: string, description: string, accent: string }>
   *   }
   * }}
   */
  const toolPages = {
    generator: {
      title: 'Objective Generator',
      intro: 'Turn sparse manual test cases into refined, reviewable cases.',
      cards: [{ title: 'Generator', description: 'Create a structured test narrative and validation plan.', accent: 'blue' }]
    },
    pytest: {
      title: 'PyTest Creator',
      intro: 'Translate completed case artifacts into framework-level executable test scripts.',
      cards: [{ title: 'Script export', description: 'Build the final executable framework payload.', accent: 'gray' }]
    },
    composer: {
      title: 'Test Composer',
      intro: 'Compose multi-step workflows, dependencies, and validation sequences.',
      cards: [{ title: 'Composition', description: 'Combine test blocks into larger execution plans.', accent: 'blue' }]
    },
    zephyr: {
      title: 'Zephyr Templating',
      intro: 'Prepare templates and outputs for Zephyr-ready reporting and lifecycle tracking.',
      cards: [{ title: 'Template output', description: 'Package case structure for Zephyr consumers.', accent: 'gray' }]
    }
  };
</script>

<div class="app-shell" style:--sidebar-width={sidebarCollapsed ? '82px' : '260px'}>
  <Sidebar items={navigation} activePage={activePage} collapsed={sidebarCollapsed} onSelect={selectPage} onToggle={toggleSidebar} />
  <Topbar />

  <main class="content-panel">
    <div class="content-inner">
      {#if activePage === 'home'}
        <HomePage onNavigate={selectPage} />
      {:else if activePage === 'help'}
        <HelpPage />
      {:else if activePage === 'settings'}
        <SettingsPage />
      {:else if activePage === 'generator'}
        <!-- Rendered unconditionally below instead, hidden via CSS once first visited — see
             generatorEverVisited above. Kept as its own branch here only so the {:else}
             ToolPage fallback doesn't wrongly catch 'generator'. -->
      {:else if activePage === 'pytest'}
        {#key pytestInstanceKey}
          <PyTestPage onNavigate={selectPage} onCreateAnother={resetPytest} initialCaseId={pendingPytestCaseId} />
        {/key}
      {:else if activePage === 'composer'}
        <TestComposerPage />
      {:else if activePage === 'zephyr'}
        <ZephyrPage />
      {:else}
        <ToolPage page={toolPages[activePage] || toolPages.generator} />
      {/if}

      {#if generatorEverVisited}
        <div class="keep-alive-page" style:display={activePage === 'generator' ? 'contents' : 'none'}>
          {#key generatorInstanceKey}
            <CaseGeneratorPage onCreateAnother={resetGenerator} initialCaseId={pendingGeneratorCaseId} />
          {/key}
        </div>
      {/if}
    </div>
  </main>
</div>

