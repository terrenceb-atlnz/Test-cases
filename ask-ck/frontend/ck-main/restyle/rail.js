// ATUI restyle only (ask-ck/plans/PLAN-atui-restyle.md S14, Rail A). Loaded by restyle/index.html
// alone — current/ never sees it. Collapses the sidebar to a 50px rail of the six section icons
// (ATUI: only parents carry icons). In the rail, clicking a section expands the sidebar with that
// section open; shared/nav.js's accordion does the opening. The collapsed state is per viewer
// (localStorage) and is applied before first paint by an inline script in restyle/index.html.

const KEY = 'rs-rail';

export function initRail(doc = document) {
  const root = doc.documentElement;
  const btn = doc.getElementById('rs-rail-toggle');
  const nav = doc.querySelector('.sidebar');
  if (!btn || !nav) return null;

  const isCollapsed = () => root.classList.contains('rs-rail-collapsed');
  const setCollapsed = (on) => {
    root.classList.toggle('rs-rail-collapsed', on);
    try { localStorage.setItem(KEY, on ? 'collapsed' : 'expanded'); } catch (_) { /* private mode */ }
    const label = on ? 'Expand sidebar' : 'Collapse sidebar';
    btn.title = label;
    btn.setAttribute('aria-label', label);
    btn.setAttribute('aria-expanded', String(!on));
    const text = btn.querySelector('.rs-sec-text');
    if (text) text.textContent = on ? 'Expand' : 'Collapse';
  };

  btn.addEventListener('click', () => setCollapsed(!isCollapsed()));

  // Capture phase, so this runs before nav.js's own click handler on the label.
  nav.addEventListener('click', (e) => {
    if (!isCollapsed()) return;
    const label = e.target.closest('.sidebar-section-label');
    if (!label) return;
    setCollapsed(false);
    // nav.js toggles the section on click: if it is already open, stop that toggle here so
    // expanding the rail never closes the section the user reached for.
    if (label.classList.contains('section-open')) e.stopPropagation();
  }, true);

  // The rail shows which section holds the active item.
  const markActive = () => {
    nav.querySelectorAll('.sidebar-section-label').forEach((l) => {
      const i = l.dataset.sectionIndex;
      const active = i != null && !!nav.querySelector(`.sidebar-section-body[data-section-index="${i}"] .sidebar-nav-item.active`);
      l.classList.toggle('rs-has-active', active);
    });
  };
  new MutationObserver((records) => {
    if (records.some((r) => r.target.classList && r.target.classList.contains('sidebar-nav-item'))) markActive();
  }).observe(nav, { subtree: true, attributes: true, attributeFilter: ['class'] });

  setCollapsed(isCollapsed());
  markActive();
  return { setCollapsed, isCollapsed, markActive };
}

initRail();
