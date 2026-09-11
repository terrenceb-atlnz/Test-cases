// Unit specs for the chosen-list mechanics (chosen.js) — the choose/dedup/
// restore machinery the Playwright golden-path exercised at the integration
// level (chosen table grew by the DELTA; in-progress cases pre-loaded rows).
// Here we assert the same logic exhaustively on pure state, in jsdom.
import { describe, it, expect, beforeEach } from 'vitest';
import {
  chooseByIds,
  restoreChosenFromSelections,
  chosenSelections,
} from '../ask-ck/CK-main/CK_server/static/js/chosen.js';
import { mountFromIndex, resetDom } from './helpers/fixture-dom.js';

// chooseByIds/restore call renderStepTables → both the top and chosen containers
// must exist. Mount the real ones for the kind under test.
function mountKind(kind) {
  const map = {
    testlink: ['tl-table', 'tl-chosen-table'],
    zephyr: ['zephyr-table', 'zephyr-chosen-table'],
    atp: ['atp-table', 'atp-chosen-table'],
  };
  mountFromIndex(...map[kind]);
}

beforeEach(() => resetDom());

describe('chooseByIds', () => {
  it('appends the given ids to the chosen bus, resolving records from the data bus', () => {
    mountKind('testlink');
    window.currentTestLink = [
      { id: 'AWP-1', title: 'Alpha', description: 'a' },
      { id: 'AWP-2', title: 'Beta', description: 'b' },
    ];
    chooseByIds('testlink', ['AWP-1', 'AWP-2']);
    const sel = chosenSelections('testlink');
    expect(sel.map((e) => e.id_or_key)).toEqual(['AWP-1', 'AWP-2']);
    expect(sel[0].title).toBe('Alpha');
  });

  it('dedups: choosing an already-chosen id does not duplicate it', () => {
    mountKind('testlink');
    window.currentTestLink = [{ id: 'AWP-1', title: 'Alpha' }];
    chooseByIds('testlink', ['AWP-1']);
    chooseByIds('testlink', ['AWP-1']); // again
    expect(chosenSelections('testlink').length).toBe(1);
  });

  it('grows the chosen list by the DELTA when adding to pre-existing rows (E2E parallel)', () => {
    mountKind('testlink');
    window.currentTestLink = [
      { id: 'A', title: 'a' }, { id: 'B', title: 'b' }, { id: 'C', title: 'c' },
    ];
    chooseByIds('testlink', ['A']);            // pre-existing
    expect(chosenSelections('testlink').length).toBe(1);
    chooseByIds('testlink', ['B', 'C']);       // + delta of 2
    expect(chosenSelections('testlink').length).toBe(3);
  });

  it('synthesizes a minimal record when the id is absent from the data bus', () => {
    mountKind('atp');
    window.currentATP = [];
    chooseByIds('atp', ['2034.1.1']);
    const sel = chosenSelections('atp');
    expect(sel.length).toBe(1);
    expect(sel[0].id_or_key).toBe('2034.1.1');
    expect(sel[0].title).toBe('2034.1.1'); // falls back to the id
  });

  it('ignores empty / falsy ids', () => {
    mountKind('testlink');
    window.currentTestLink = [{ id: 'A', title: 'a' }];
    chooseByIds('testlink', ['', null, undefined, 'A']);
    expect(chosenSelections('testlink').length).toBe(1);
  });
});

describe('restoreChosenFromSelections', () => {
  it('rebuilds the chosen bus from saved selections, sorted by persisted order', () => {
    mountKind('zephyr');
    window.currentZephyr = [];
    restoreChosenFromSelections('zephyr', [
      { id_or_key: 'Z-2', title: 'two', order: 2 },
      { id_or_key: 'Z-1', title: 'one', order: 1 },
    ]);
    const sel = chosenSelections('zephyr');
    expect(sel.map((e) => e.id_or_key)).toEqual(['Z-1', 'Z-2']); // order-sorted
  });

  it('falls back to list order when no persisted order is present', () => {
    mountKind('zephyr');
    restoreChosenFromSelections('zephyr', [
      { id_or_key: 'Z-1', title: 'one' },
      { id_or_key: 'Z-2', title: 'two' },
    ]);
    expect(chosenSelections('zephyr').map((e) => e.id_or_key)).toEqual(['Z-1', 'Z-2']);
  });

  it('tolerates a non-array selections argument', () => {
    mountKind('zephyr');
    expect(() => restoreChosenFromSelections('zephyr', null)).not.toThrow();
    expect(chosenSelections('zephyr').length).toBe(0);
  });
});

describe('chosenSelections (confirm payload shape)', () => {
  it('returns {id_or_key,title,justification,order} for each chosen row', () => {
    mountKind('testlink');
    window.currentTestLink = [{ id: 'A', title: 'Alpha', description: 'why-a' }];
    chooseByIds('testlink', ['A']);
    const [row] = chosenSelections('testlink');
    expect(Object.keys(row).sort()).toEqual(
      ['id_or_key', 'justification', 'order', 'title'],
    );
    expect(row.justification).toBe('why-a');
  });
});
