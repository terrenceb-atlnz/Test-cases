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

  const navigation = {
    main: [
      { id: 'home', label: 'Home', icon: houseIcon },
      { id: 'help', label: 'Help', icon: helpIcon },
      { id: 'settings', label: 'Settings', icon: settingsIcon }
    ],
    tool: [
      { id: 'generator', label: 'Test Case Generator', icon: testCaseIcon },
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
      title: 'Test Case Generator',
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
        <HomePage />
      {:else if activePage === 'help'}
        <HelpPage />
      {:else if activePage === 'settings'}
        <SettingsPage />
      {:else}
        <ToolPage page={toolPages[activePage] || toolPages.generator} />
      {/if}
    </div>
  </main>
</div>

