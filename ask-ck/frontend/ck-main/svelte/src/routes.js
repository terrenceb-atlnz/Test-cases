export const routes = {
  home: '/',
  help: '/help',
  llm: '/llm',
  settings: '/settings',
  generator: '/generator',
  pytest: '/pytest',
  composer: '/composer',
  zephyr: '/zephyr'
};

/**
 * @param {string} pathname
 * @returns {string}
 */
export function getRouteKeyFromPath(pathname) {
  const normalized = (pathname || '/').replace(/\/+$/, '') || '/';
  const match = Object.entries(routes).find(([, route]) => route === normalized);
  return match ? match[0] : 'home';
}
