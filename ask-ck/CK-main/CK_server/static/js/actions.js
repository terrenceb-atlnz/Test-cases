// Action registry + delegated event dispatch. data-action names resolve
// through this registry (not window[...]), which is what lets the tool modules
// keep their handlers out of global scope. Each tool self-registers at the
// bottom of its module via registerActions({...}).
const registry = new Map();

export function registerActions(map) {
  for (const name in map) {
    if (!Object.prototype.hasOwnProperty.call(map, name)) continue;
    if (registry.has(name)) console.warn('duplicate data-action registration:', name);
    registry.set(name, map[name]);
  }
}

// Keyboard activation for div[role="button"] nav items (Enter / Space), so
// sidebar navigation is usable without a mouse.
document.addEventListener('keydown', (e) => {
  if (e.key !== 'Enter' && e.key !== ' ') return;
  const target = e.target;
  if (target instanceof HTMLElement && target.getAttribute('role') === 'button' && target.tabIndex >= 0) {
    e.preventDefault();
    target.click();
  }
});

// Delegated click dispatcher. Elements declare their handler declaratively:
//   data-action="fnName"            — registered handler to call
//   data-args='["panel-main", 1]'   — optional JSON array of arguments
// Works for static markup and for rows injected via innerHTML at runtime.
document.addEventListener('click', (e) => {
  // A busy LLM button is re-enabled so it can be clicked to STOP (llm-progress.js).
  // Checked BEFORE data-action resolution, so the click can never re-fire the
  // action that is already in flight.
  const stopEl = e.target.closest('[data-ck-cancel]');
  if (stopEl) {
    e.preventDefault();
    if (stopEl.dataset.ckStopping !== '1') {
      stopEl.dataset.ckStopping = '1';
      const lbl = stopEl.querySelector('.ck-busy-label');
      if (lbl) lbl.textContent = 'Stopping…';
      fetch('/api/llm/cancel/' + encodeURIComponent(stopEl.dataset.ckCancel), { method: 'POST' })
        .catch(() => {});
    }
    return;
  }
  const el = e.target.closest('[data-action]');
  if (!el) return;
  const fn = registry.get(el.dataset.action);
  if (typeof fn !== 'function') {
    console.warn('data-action refers to unknown function:', el.dataset.action);
    return;
  }
  if (el.tagName === 'A') e.preventDefault();
  let args = [];
  if (el.dataset.args) {
    try {
      args = JSON.parse(el.dataset.args);
    } catch (err) {
      console.warn('Invalid data-args JSON on', el, err);
      return;
    }
  }
  fn.apply(el, args);
});
