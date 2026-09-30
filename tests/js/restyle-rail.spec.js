// The ATUI restyle's icon rail (ask-ck/plans/PLAN-atui-restyle.md S14, Rail A): restyle/rail.js
// collapses the sidebar to its six section icons, and clicking a section in the rail expands the
// sidebar with that section open. The opening is done by shared/nav.js's accordion, so these specs
// run the REAL accordion beside rail.js — the contract that matters is how the two interact.
import { describe, it, expect, beforeEach, vi } from 'vitest';

import { initSidebarAccordion } from '../../ask-ck/frontend/ck-main/current/shared/nav.js';
import { initRail } from '../../ask-ck/frontend/ck-main/restyle/rail.js';

function mount() {
  document.documentElement.className = 'dark';
  document.body.innerHTML = `
    <nav class="sidebar">
      <div class="sidebar-section-label"><span class="rs-sec-text">Help</span></div>
      <div class="sidebar-steps"><div class="sidebar-nav-item active" data-panel="panel-main">Main</div></div>
      <div class="sidebar-section-label"><span class="rs-sec-text">PyTest Creator</span></div>
      <div class="sidebar-steps"><div class="sidebar-nav-item" data-panel="panel-pt-cases">1. Cases</div></div>
      <button type="button" id="rs-rail-toggle"><span class="rs-sec-text">Collapse</span></button>
    </nav>`;
  initSidebarAccordion();
  return initRail(document);
}

const labels = () => Array.from(document.querySelectorAll('.sidebar-section-label'));
const collapsed = () => document.documentElement.classList.contains('rs-rail-collapsed');

beforeEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
});

describe('restyle rail', () => {
  it('the toggle collapses and expands, and remembers the choice per viewer', () => {
    mount();
    const btn = document.getElementById('rs-rail-toggle');
    btn.click();
    expect(collapsed()).toBe(true);
    expect(localStorage.getItem('rs-rail')).toBe('collapsed');
    expect(btn.getAttribute('aria-expanded')).toBe('false');
    expect(btn.textContent).toContain('Expand');
    btn.click();
    expect(collapsed()).toBe(false);
    expect(localStorage.getItem('rs-rail')).toBe('expanded');
  });

  it('clicking a closed section in the rail expands the sidebar AND opens that section', () => {
    mount();
    document.getElementById('rs-rail-toggle').click();
    const pt = labels()[1];
    expect(pt.classList.contains('section-open')).toBe(false);
    pt.click();
    expect(collapsed()).toBe(false);
    expect(pt.classList.contains('section-open')).toBe(true);
  });

  it('clicking an already-open section in the rail expands without closing it', () => {
    mount();
    const pt = labels()[1];
    pt.click();                                  // open it while expanded
    document.getElementById('rs-rail-toggle').click();
    pt.click();                                  // from the rail
    expect(collapsed()).toBe(false);
    expect(pt.classList.contains('section-open')).toBe(true);
  });

  it('when expanded, a section click is left entirely to the accordion', () => {
    mount();
    const pt = labels()[1];
    pt.click();
    pt.click();
    expect(pt.classList.contains('section-open')).toBe(false);   // nav.js toggled it closed
    expect(collapsed()).toBe(false);
  });

  it('marks the section holding the active item, and follows it when it moves', async () => {
    mount();
    expect(labels()[0].classList.contains('rs-has-active')).toBe(true);
    document.querySelector('[data-panel="panel-main"]').classList.remove('active');
    document.querySelector('[data-panel="panel-pt-cases"]').classList.add('active');
    await new Promise((r) => setTimeout(r, 0));  // MutationObserver callbacks are microtasks
    expect(labels()[0].classList.contains('rs-has-active')).toBe(false);
    expect(labels()[1].classList.contains('rs-has-active')).toBe(true);
  });

  it('does nothing on a page without the rail (i.e. Classic)', () => {
    document.body.innerHTML = '<nav class="sidebar"></nav>';
    expect(initRail(document)).toBeNull();
  });
});
