// Fixture-DOM helper: mount REAL container markup from index.html into jsdom.
//
// Decision (PLAN-frontend-unit-tests.md): specs use fragments extracted from the
// live index.html, NOT hand-written stubs — so renaming a container id in
// index.html breaks the spec (desirable drift-detection, same discipline as the
// Playwright selectors). We parse index.html with jsdom itself and copy out the
// requested elements by id.
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { JSDOM } from 'jsdom';

const HERE = dirname(fileURLToPath(import.meta.url));
const INDEX_HTML = resolve(
  HERE,
  '../../ask-ck/CK-main/CK_server/static/index.html',
);

let _cachedDoc = null;
function indexDoc() {
  if (!_cachedDoc) {
    const html = readFileSync(INDEX_HTML, 'utf8');
    _cachedDoc = new JSDOM(html).window.document;
  }
  return _cachedDoc;
}

/**
 * Mount the real index.html elements with the given ids into the current jsdom
 * document.body. Throws if an id is missing from index.html — that throw IS the
 * drift-detection: a renamed/removed container fails loudly instead of silently
 * testing a stub that no longer matches production.
 *
 * @param {...string} ids  element ids to lift out of index.html (no leading '#')
 * @returns {Record<string, HTMLElement>} mounted elements keyed by id
 */
export function mountFromIndex(...ids) {
  const src = indexDoc();
  const mounted = {};
  for (const id of ids) {
    const el = src.getElementById(id);
    if (!el) {
      throw new Error(
        `fixture-dom: #${id} not found in index.html — the id was renamed/removed, ` +
          `or the spec asked for a container that does not exist. Update the spec ` +
          `or the fixture, do not stub around it.`,
      );
    }
    // Import a deep clone into the active document so each spec gets fresh nodes.
    mounted[id] = document.importNode(el, true);
    document.body.appendChild(mounted[id]);
  }
  return mounted;
}

/** Reset the active jsdom document + the app's window.* candidate buses. */
export function resetDom() {
  document.body.innerHTML = '';
  for (const bus of [
    'currentTestLink', 'currentZephyr', 'currentATP',
    'currentTestLinkChosen', 'currentZephyrChosen', 'currentATPChosen',
  ]) {
    delete window[bus];
  }
}
