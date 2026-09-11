// Where the current front-end lives and which page directory each module sits in
// (PLAN-restructure-2026-09-11, batch 7). Specs resolve modules through here so the next
// move is a one-file change. PAGE_OF must match the directories under current/.
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
export const FRONTEND = resolve(HERE, '../../../ask-ck/frontend/ck-main/current');

export const PAGE_OF = {
  'generator.js': 'generator', 'db-search.js': 'generator', 'chosen.js': 'generator', 'tables.js': 'generator',
  'pytest.js': 'pytest-creator',
  'llm.js': 'llm-config', 'agent.js': 'llm-config',
  'admin.js': 'admin',
  'main.js': 'shared', 'actions.js': 'shared', 'nav.js': 'shared', 'state.js': 'shared', 'session.js': 'shared',
  'session-restore.js': 'shared', 'cases.js': 'shared', 'dom-helpers.js': 'shared', 'llm-debug.js': 'shared',
  'llm-progress.js': 'shared', 'locks.js': 'shared', 'provenance.js': 'shared', 'theme.js': 'shared', 'version.js': 'shared',
};

/** Absolute path of a front-end module by bare name (a leading `js/` is tolerated). */
export function modulePath(name) {
  const base = name.replace(/^js\//, '');
  const page = PAGE_OF[base];
  if (!page) throw new Error(`unknown front-end module: ${name}`);
  return resolve(FRONTEND, page, base);
}
/** Absolute path of a non-module asset at current/ (index.html, styles.css, …). */
export const assetPath = (rel) => resolve(FRONTEND, rel);
