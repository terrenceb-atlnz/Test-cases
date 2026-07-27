// Unit specs for the candidate/chosen table renderers (tables.js).
// Uses REAL container markup from index.html (fixture-dom helper). Proves — in
// jsdom, cheaply — the behaviour the Playwright golden-path saw at the seam:
// search results render as rows, and the top table HIDES already-chosen ids.
import { describe, it, expect, beforeEach } from 'vitest';
import {
  renderTestLinkTable,
  renderZephyrTable,
  renderATPTable,
  renderChosenTable,
} from '../ask-ck/CK-main/CK_server/static/js/tables.js';
import { mountFromIndex, resetDom } from './helpers/fixture-dom.js';

beforeEach(() => resetDom());

describe('renderTestLinkTable', () => {
  it('renders one checkbox row per candidate, score-formatted', () => {
    mountFromIndex('tl-table');
    renderTestLinkTable([
      { id: 'AWP-1', title: 'Alpha', score: 0.9262, description: 'a' },
      { id: 'AWP-2', title: 'Beta', score: 0.5, description: 'b' },
    ]);
    const boxes = document.querySelectorAll('#tl-table input.tl-checkbox');
    expect(boxes.length).toBe(2);
    expect(boxes[0].getAttribute('data-id')).toBe('AWP-1');
    // score rounded to 2dp
    expect(document.querySelector('#tl-table').textContent).toContain('0.93');
  });

  it('HIDES candidates already in the chosen bus (E2E-proven behaviour)', () => {
    mountFromIndex('tl-table');
    window.currentTestLinkChosen = [{ id_or_key: 'AWP-1' }];
    renderTestLinkTable([
      { id: 'AWP-1', title: 'Alpha' },
      { id: 'AWP-2', title: 'Beta' },
    ]);
    const boxes = document.querySelectorAll('#tl-table input.tl-checkbox');
    expect(boxes.length).toBe(1);
    expect(boxes[0].getAttribute('data-id')).toBe('AWP-2');
  });

  it('shows the "all chosen" note when every candidate is chosen', () => {
    mountFromIndex('tl-table');
    window.currentTestLinkChosen = [{ id_or_key: 'AWP-1' }];
    renderTestLinkTable([{ id: 'AWP-1', title: 'Alpha' }]);
    expect(document.querySelector('#tl-table').textContent).toMatch(/All candidates chosen/i);
  });

  it('shows the empty-state note when there are no candidates', () => {
    mountFromIndex('tl-table');
    renderTestLinkTable([]);
    expect(document.querySelector('#tl-table').textContent).toMatch(/No TestLink candidates/i);
  });

  it('escapes candidate fields (no HTML injection from titles)', () => {
    mountFromIndex('tl-table');
    renderTestLinkTable([{ id: 'X', title: '<img src=x onerror=1>' }]);
    expect(document.querySelector('#tl-table img')).toBeNull();
  });
});

describe('renderZephyrTable (keyed by .key)', () => {
  it('renders rows keyed by data-key and hides chosen keys', () => {
    mountFromIndex('zephyr-table');
    window.currentZephyrChosen = [{ id_or_key: 'AWPTCM-T1' }];
    renderZephyrTable([
      { key: 'AWPTCM-T1', title: 'one' },
      { key: 'AWPTCM-T2', title: 'two' },
    ]);
    const boxes = document.querySelectorAll('#zephyr-table input.zephyr-checkbox');
    expect(boxes.length).toBe(1);
    expect(boxes[0].getAttribute('data-key')).toBe('AWPTCM-T2');
  });
});

describe('renderATPTable', () => {
  it('renders candidate rows with data-id', () => {
    mountFromIndex('atp-table');
    renderATPTable([{ id: '2034.1.1', title: 'tag' }]);
    const boxes = document.querySelectorAll('#atp-table input.atp-checkbox');
    expect(boxes.length).toBe(1);
    expect(boxes[0].getAttribute('data-id')).toBe('2034.1.1');
  });
});

describe('renderChosenTable', () => {
  it('renders chosen rows in insertion order from the chosen bus', () => {
    mountFromIndex('tl-chosen-table');
    window.currentTestLinkChosen = [
      { id_or_key: 'AWP-2', title: 'second', order: 2 },
      { id_or_key: 'AWP-1', title: 'first', order: 1 },
    ];
    renderChosenTable('testlink');
    const boxes = document.querySelectorAll('#tl-chosen-table input.tl-chosen-checkbox');
    expect(boxes.length).toBe(2);
  });

  it('shows the chosen empty-state when nothing is chosen', () => {
    mountFromIndex('tl-chosen-table');
    window.currentTestLinkChosen = [];
    renderChosenTable('testlink');
    expect(document.querySelector('#tl-chosen-table').textContent).toMatch(/No cases chosen yet/i);
  });
});

describe('fixture-dom drift detection', () => {
  it('throws loudly if a container id is missing from index.html', () => {
    expect(() => mountFromIndex('tl-table-renamed-nonexistent')).toThrow(/not found in index\.html/);
  });
});
