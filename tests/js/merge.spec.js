// Unit specs for the candidate-merge logic (db-search.js merge*Candidates).
// These hold the dedup + description-preference + score-re-sort rules that the
// Playwright golden-path only observed indirectly (results land merged + sorted
// in the top table). Now asserted directly on pure state, in jsdom.
//
// The merge fns were made `export` specifically so this layer can test them
// without a fetch-stubbed handler round-trip (see PLAN-frontend-unit-tests.md).
import { describe, it, expect, beforeEach } from 'vitest';
import {
  mergeTestLinkCandidates,
  mergeZephyrCandidates,
  mergeATPCandidates,
} from '../ask-ck/CK-main/CK_server/static/js/db-search.js';
import { S } from '../ask-ck/CK-main/CK_server/static/js/state.js';
import { mountFromIndex, resetDom } from './helpers/fixture-dom.js';

beforeEach(() => {
  resetDom();
  S.currentKey = 'AWPTCM-TEST'; // chooseByIds (precheck path) requires a loaded case
  // merge* re-renders both tables; mount all six real containers.
  mountFromIndex(
    'tl-table', 'tl-chosen-table',
    'zephyr-table', 'zephyr-chosen-table',
    'atp-table', 'atp-chosen-table',
  );
});

describe('mergeTestLinkCandidates', () => {
  it('adds new candidates to the empty bus', () => {
    mergeTestLinkCandidates([{ id: 'A', title: 'Alpha', score: 0.4 }]);
    expect(window.currentTestLink.map((c) => c.id)).toEqual(['A']);
  });

  it('dedups by id (no duplicate rows for the same id)', () => {
    mergeTestLinkCandidates([{ id: 'A', title: 'Alpha', score: 0.4 }]);
    mergeTestLinkCandidates([{ id: 'A', title: 'Alpha v2', score: 0.9 }]);
    expect(window.currentTestLink.filter((c) => c.id === 'A').length).toBe(1);
  });

  it('re-sorts the merged pool by score descending', () => {
    mergeTestLinkCandidates([
      { id: 'LO', title: 'lo', score: 0.2 },
      { id: 'HI', title: 'hi', score: 0.95 },
      { id: 'MID', title: 'mid', score: 0.6 },
    ]);
    expect(window.currentTestLink.map((c) => c.id)).toEqual(['HI', 'MID', 'LO']);
  });

  it('prefers the longer description when merging (never re-truncates a rich body)', () => {
    mergeTestLinkCandidates([{ id: 'A', title: 'a', description: 'a full detailed body', score: 0.5 }]);
    mergeTestLinkCandidates([{ id: 'A', title: 'a', description: 'short', score: 0.5 }]);
    expect(window.currentTestLink.find((c) => c.id === 'A').description).toBe('a full detailed body');
  });

  it('defaults a missing score to 0.6', () => {
    mergeTestLinkCandidates([{ id: 'A', title: 'a' }]);
    expect(window.currentTestLink[0].score).toBe(0.6);
  });

  it('ignores rows with no id', () => {
    mergeTestLinkCandidates([{ title: 'no id' }, { id: 'A', title: 'a' }]);
    expect(window.currentTestLink.map((c) => c.id)).toEqual(['A']);
  });

  it('precheckIds moves picks straight into the chosen bus', () => {
    mergeTestLinkCandidates(
      [{ id: 'A', title: 'a', score: 0.5 }, { id: 'B', title: 'b', score: 0.4 }],
      { precheckIds: ['A'], source: 'llm' },
    );
    expect((window.currentTestLinkChosen || []).map((e) => e.id_or_key)).toEqual(['A']);
  });
});

describe('mergeZephyrCandidates (keyed by .key, .id fallback)', () => {
  it('keys by .key and dedups', () => {
    mergeZephyrCandidates([{ key: 'Z-1', title: 'one', score: 0.5 }]);
    mergeZephyrCandidates([{ key: 'Z-1', title: 'one v2', score: 0.5 }]);
    expect(window.currentZephyr.filter((c) => c.key === 'Z-1').length).toBe(1);
  });

  it('accepts .id as the key when .key is absent', () => {
    mergeZephyrCandidates([{ id: 'Z-9', title: 'nine', score: 0.5 }]);
    expect(window.currentZephyr[0].key).toBe('Z-9');
  });

  it('sorts by score descending', () => {
    mergeZephyrCandidates([
      { key: 'A', title: 'a', score: 0.1 },
      { key: 'B', title: 'b', score: 0.8 },
    ]);
    expect(window.currentZephyr.map((c) => c.key)).toEqual(['B', 'A']);
  });
});

describe('mergeATPCandidates', () => {
  it('dedups by id and sorts by score', () => {
    mergeATPCandidates([
      { id: '1.1', title: 'one', score: 0.3 },
      { id: '2.2', title: 'two', score: 0.7 },
    ]);
    mergeATPCandidates([{ id: '1.1', title: 'one again', score: 0.3 }]);
    expect(window.currentATP.map((c) => c.id)).toEqual(['2.2', '1.1']);
  });

  it('defaults a missing score to 0.5', () => {
    mergeATPCandidates([{ id: '1.1', title: 'one' }]);
    expect(window.currentATP[0].score).toBe(0.5);
  });

  it('keeps a higher existing LLM score but refreshes a richer description', () => {
    // Seed an existing high-score LLM row.
    window.currentATP = [{ id: '1.1', title: 'one', description: 'x', score: 0.9, source: 'llm' }];
    // Incoming lower-score search row with a richer description.
    mergeATPCandidates([{ id: '1.1', title: 'one', description: 'a much richer body', score: 0.4, source: 'search' }]);
    const row = window.currentATP.find((c) => c.id === '1.1');
    expect(row.score).toBe(0.9);                       // kept the higher LLM score
    expect(row.description).toBe('a much richer body'); // but took the richer desc
  });
});
