// The ATUI restyle's icon rail (ask-ck/plans/PLAN-atui-restyle.md S14, Rail A): restyle/rail.js
// collapses the sidebar to its six section icons, and clicking a section in the rail expands the
// sidebar with that section open. The opening is done by shared/nav.js's accordion, so these specs
// mount the REAL restyle sidebar (from restyle/index.html) and run the REAL accordion beside
// rail.js — the contract that matters is how the two interact with the actual markup.
import { describe, it, expect, beforeEach } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { initSidebarAccordion } from '../../ask-ck/frontend/ck-main/current/shared/nav.js';
import { initRail } from '../../ask-ck/frontend/ck-main/restyle/rail.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const RESTYLE_HTML = readFileSync(resolve(HERE, '../../ask-ck/frontend/ck-main/restyle/index.html'), 'utf8');
const NAV = RESTYLE_HTML.match(/<nav class="sidebar"[\s\S]*?<\/nav>/)[0];

function mount() {
  document.documentElement.className = 'dark';
  document.body.innerHTML = NAV;
  initSidebarAccordion();
  return initRail(document);
}

const label = (text) => Array.from(document.querySelectorAll('.sidebar-section-label'))
  .find((l) => l.textContent.trim().startsWith(text));
const collapsed = () => document.documentElement.classList.contains('rs-rail-collapsed');
const toggle = () => document.getElementById('rs-rail-toggle');

beforeEach(() => { localStorage.clear(); });

describe('restyle rail', () => {
  it('the toggle is not swallowed into a section body by the accordion (Terrence: "where is collapse?")', () => {
    mount();
    // nav.js takes every sibling after a label as that section's body and hides closed bodies,
    // so a toggle that sat after the last section vanished whenever that section was closed.
    expect(toggle().classList.contains('sidebar-section-body')).toBe(false);
    expect(toggle().classList.contains('section-collapsed')).toBe(false);
    expect(document.querySelectorAll('.sidebar-section-label').length).toBe(6);
  });

  it('the toggle collapses and expands, and remembers the choice per viewer', () => {
    mount();
    toggle().click();
    expect(collapsed()).toBe(true);
    expect(localStorage.getItem('rs-rail')).toBe('collapsed');
    expect(toggle().getAttribute('aria-expanded')).toBe('false');
    expect(toggle().textContent).toContain('Expand');
    toggle().click();
    expect(collapsed()).toBe(false);
    expect(localStorage.getItem('rs-rail')).toBe('expanded');
  });

  it('clicking a closed section in the rail expands the sidebar AND opens that section', () => {
    mount();
    toggle().click();
    const pt = label('PyTest Creator');
    expect(pt.classList.contains('section-open')).toBe(false);
    pt.click();
    expect(collapsed()).toBe(false);
    expect(pt.classList.contains('section-open')).toBe(true);
  });

  it('clicking an already-open section in the rail expands without closing it', () => {
    mount();
    const pt = label('PyTest Creator');
    pt.click();                                  // open it while expanded
    toggle().click();
    pt.click();                                  // from the rail
    expect(collapsed()).toBe(false);
    expect(pt.classList.contains('section-open')).toBe(true);
  });

  it('when expanded, a section click is left entirely to the accordion', () => {
    mount();
    const pt = label('PyTest Creator');
    pt.click();
    pt.click();
    expect(pt.classList.contains('section-open')).toBe(false);   // nav.js toggled it closed
    expect(collapsed()).toBe(false);
  });

  it('marks the section holding the active item, and follows it when it moves', async () => {
    mount();
    // The markup ships with the Generator's first step active.
    expect(label('Objective/Test Case Generator').classList.contains('rs-has-active')).toBe(true);
    document.querySelectorAll('.sidebar-nav-item.active').forEach((i) => i.classList.remove('active'));
    document.querySelector('[data-panel="panel-pt-cases"]').classList.add('active');
    await new Promise((r) => setTimeout(r, 0));  // MutationObserver callbacks are microtasks
    expect(label('Objective/Test Case Generator').classList.contains('rs-has-active')).toBe(false);
    expect(label('PyTest Creator').classList.contains('rs-has-active')).toBe(true);
  });

  it('does nothing on a page without the rail (i.e. Classic)', () => {
    document.body.innerHTML = '<nav class="sidebar"></nav>';
    expect(initRail(document)).toBeNull();
  });
});
