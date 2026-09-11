// Unit specs for deferred per-step candidate loading (generator.loadStepCandidates).
//
// The Generator's three review steps used to receive their candidate pools inside the
// load_case response. That pre-loaded data for panels the user had not opened, and it
// caused two separate incidents (a ~60s LLM prefetch for Step 3, and a 2.7s 45k-row
// scan for Step 2 running bare on the event loop). Now each step fetches its own pool
// on first visit — see PLAN-backend-module-split.md A1.
//
// The rules worth pinning are all about NOT losing user work to an in-flight fetch,
// which is invisible in a golden-path E2E run:
//   * fetch once per (case, step), so revisiting a step is free
//   * a failed fetch retries on the next visit (must not memoize a failure)
//   * Search/Suggest results already merged into the bus outrank the default view
//   * a response for a case the user has navigated away from is dropped
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { loadStepCandidates } from '../ask-ck/CK-main/CK_server/static/js/generator.js';
import { S } from '../ask-ck/CK-main/CK_server/static/js/state.js';
import { mountFromIndex, resetDom } from './helpers/fixture-dom.js';

const BUS = { 1: 'currentTestLink', 2: 'currentZephyr', 3: 'currentATP' };

// The fetch-once memo lives in generator.js module scope and is only cleared by
// loadCase(). Rather than export a reset just for tests, give every spec its own case
// key — so specs are independent while the memo is still exercised WITHIN a spec.
let _caseN = 0;
function freshKey() {
  _caseN += 1;
  return `AWPTCM-TSPEC${_caseN}`;
}

function okResponse(candidates) {
  return {
    ok: true,
    status: 200,
    json: async () => ({ candidates }),
    text: async () => '',
  };
}

beforeEach(() => {
  resetDom();
  // loadStepCandidates writes a loading/error state into the candidate container and
  // renderStepTables re-renders both tables, so mount all six real containers.
  mountFromIndex(
    'tl-table', 'tl-chosen-table',
    'zephyr-table', 'zephyr-chosen-table',
    'atp-table', 'atp-chosen-table',
  );
  S.currentKey = freshKey();
  window.currentTestLink = [];
  window.currentZephyr = [];
  window.currentATP = [];
  vi.restoreAllMocks();
});

describe('loadStepCandidates — fetch once per (case, step)', () => {
  it.each([1, 2, 3])('populates step %i\'s bus from the endpoint', async (step) => {
    const fetchMock = vi.fn().mockResolvedValue(okResponse([{ id: 'A', key: 'A', title: 'Alpha', score: 0.5 }]));
    vi.stubGlobal('fetch', fetchMock);

    await loadStepCandidates(step);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0])
      .toBe(`/api/wizard/step_candidates/${S.currentKey}/${step}`);
    expect(window[BUS[step]].map((c) => c.title)).toEqual(['Alpha']);
  });

  it('does not re-fetch when the same step is revisited', async () => {
    const fetchMock = vi.fn().mockResolvedValue(okResponse([{ id: 'A', key: 'A', title: 'Alpha', score: 0.5 }]));
    vi.stubGlobal('fetch', fetchMock);

    await loadStepCandidates(2);
    await loadStepCandidates(2);
    await loadStepCandidates(2);

    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('fetches each step separately (one memo entry per step, not per case)', async () => {
    const fetchMock = vi.fn().mockResolvedValue(okResponse([{ id: 'A', key: 'A', title: 'Alpha', score: 0.5 }]));
    vi.stubGlobal('fetch', fetchMock);

    await loadStepCandidates(1);
    await loadStepCandidates(2);
    await loadStepCandidates(3);

    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it('re-fetches the same step for a DIFFERENT case', async () => {
    const fetchMock = vi.fn().mockResolvedValue(okResponse([{ id: 'A', key: 'A', title: 'Alpha', score: 0.5 }]));
    vi.stubGlobal('fetch', fetchMock);

    await loadStepCandidates(2);
    const second = freshKey();
    S.currentKey = second;
    window.currentZephyr = [];      // loadCase clears the pools
    await loadStepCandidates(2);

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[1][0]).toContain(second);
  });

  it('does nothing when no case is loaded', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    S.currentKey = null;

    await loadStepCandidates(2);

    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('ignores a step outside 1-3', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);

    await loadStepCandidates(4);
    await loadStepCandidates(0);

    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe('loadStepCandidates — must not destroy user work', () => {
  it('does NOT overwrite rows already merged in by Search / Suggest', async () => {
    // The user opened step 2 and hit Search before the default fetch landed.
    const searched = [{ id: 'FOUND', key: 'FOUND', title: 'From an explicit search', score: 0.9 }];
    const fetchMock = vi.fn().mockImplementation(async () => {
      window.currentZephyr = searched;          // merge lands while the fetch is in flight
      return okResponse([{ id: 'DEFAULT', key: 'DEFAULT', title: 'Default view', score: 0.4 }]);
    });
    vi.stubGlobal('fetch', fetchMock);

    await loadStepCandidates(2);

    expect(window.currentZephyr.map((c) => c.key)).toEqual(['FOUND']);
  });

  it('drops a response that arrives after the user loaded a different case', async () => {
    const fetchMock = vi.fn().mockImplementation(async () => {
      S.currentKey = freshKey();                // navigated away mid-flight
      return okResponse([{ id: 'STALE', key: 'STALE', title: 'Stale', score: 0.4 }]);
    });
    vi.stubGlobal('fetch', fetchMock);

    await loadStepCandidates(2);

    expect(window.currentZephyr).toEqual([]);
  });
});

describe('loadStepCandidates — failure handling', () => {
  it('surfaces an error in the candidate container and does not throw', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false, status: 500, text: async () => 'boom', json: async () => ({}),
    }));

    await expect(loadStepCandidates(2)).resolves.toBeUndefined();
    expect(document.getElementById('zephyr-table').textContent).toMatch(/Could not load candidates/i);
  });

  it('retries on the next visit after a failure (a failure is not memoized)', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: false, status: 500, text: async () => 'boom', json: async () => ({}) })
      .mockResolvedValueOnce(okResponse([{ id: 'A', key: 'A', title: 'Alpha', score: 0.5 }]));
    vi.stubGlobal('fetch', fetchMock);

    await loadStepCandidates(2);        // fails
    await loadStepCandidates(2);        // must try again

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(window.currentZephyr.map((c) => c.key)).toEqual(['A']);
  });

  it('survives a network rejection', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));

    await expect(loadStepCandidates(2)).resolves.toBeUndefined();
    expect(document.getElementById('zephyr-table').textContent).toMatch(/offline/i);
  });
});
