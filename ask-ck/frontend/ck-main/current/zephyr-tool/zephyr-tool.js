// Zephyr Templating Tool — the page is a Svelte island since 2026-10-09 (PLAN-test-composer Z1).
// Source: ../svelte-src/src/zt/ (ZtPage.svelte + model.js); built bundle: ../islands/zt.js.
// This module is the adapter nav.js calls when the panel is shown: it mounts the island into
// #zt-root once (both index.html files carry that one element). The page's own clicks are Svelte
// handlers, not data-action entries, so nothing here registers actions.

let mounted = null;

/** Called by nav.js whenever the panel is shown. Mounts the island on first show. */
export async function renderZtPanel() {
  if (mounted) return;
  const root = document.getElementById('zt-root');
  if (!root) return;
  mounted = 'mounting';
  try {
    const { mountZt } = await import('../islands/zt.js');
    mounted = mountZt(root);
  } catch (e) {
    mounted = null;
    root.textContent = 'Could not load the Zephyr Templating Tool: ' + e.message;
  }
}
