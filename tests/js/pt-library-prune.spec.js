// The PRUNE control (PLAN-art-family-numbering-and-prune.md §4, D4).
//
// Prune deletes a reviewer's working code, so what this pins is mostly what the UI must NOT
// do: never offer a one-click removal, never claim success from a blocked run, and never let
// "nothing to prune" and "prune refused" look alike — those two have opposite next actions.
import { describe, it, expect } from 'vitest';

import '../../ask-ck/frontend/ck-main/current/shared/actions.js';
import { ptPruneSummary } from '../../ask-ck/frontend/ck-main/current/pytest-creator/pytest.js';

const REMOVED = [
  { tag: '# AI: dependency `_fmt_port` of # ART art/1332_lldp_med/library_1332.py lines 18-41',
    names: ['_fmt_port'] },
];
const PREVIEW = { group: 'Port', family: 9001, library: 'library_9001.py',
                  scripts: ['test-9001.33234.py'], candidates: 1, removed: REMOVED,
                  applied: false, blocked: '' };
const APPLIED = { ...PREVIEW, applied: true };
const CLEAN = { ...PREVIEW, removed: [], candidates: 2 };
const NONE = { ...PREVIEW, removed: [], candidates: 0 };
const BLOCKED = { ...PREVIEW, removed: [],
                  blocked: 'test-9001.33234.py does not parse, so it reports no references' };

describe('the preview', () => {
  it('names every member it would remove, with its provenance tag', () => {
    const s = ptPruneSummary(PREVIEW);
    expect(s.html).toContain('_fmt_port');
    expect(s.html).toContain('# AI: dependency');
    expect(s.html).toContain('Would remove 1');
  });

  it('offers a SECOND, separate click to apply — never removes on the first', () => {
    const s = ptPruneSummary(PREVIEW);
    expect(s.html).toContain('data-action="ptPruneLibraryApply"');
    expect(s.className).toContain('is-warning');
  });

  it('says which scripts were checked, so an empty group cannot read as proof', () => {
    expect(ptPruneSummary(PREVIEW).html).toContain('test-9001.33234.py');
    expect(ptPruneSummary({ ...PREVIEW, scripts: [] }).html)
      .toContain('no other script in this group');
  });

  it('says reviewer-selected members are out of scope', () => {
    expect(ptPruneSummary(PREVIEW).html).toContain('# AI: dependency');
    expect(ptPruneSummary(PREVIEW).html).toMatch(/reviewer selected|a reviewer selected/i);
  });
});

describe('after applying', () => {
  it('reports what went, and offers no further button', () => {
    const s = ptPruneSummary(APPLIED);
    expect(s.className).toContain('is-success');
    expect(s.html).toContain('Removed 1');
    expect(s.html).not.toContain('ptPruneLibraryApply');
  });
});

describe('the two quiet outcomes are not the same outcome', () => {
  it('"nothing to prune" is neutral and offers no button', () => {
    const s = ptPruneSummary(CLEAN);
    expect(s.html).toContain('Nothing to prune');
    expect(s.className).not.toContain('is-warning');
    expect(s.html).not.toContain('ptPruneLibraryApply');
  });

  it('a BLOCKED run is amber and says why — it is not "nothing to prune"', () => {
    const s = ptPruneSummary(BLOCKED);
    expect(s.className).toContain('is-warning');
    expect(s.html).toContain('did not run');
    expect(s.html).toContain('does not parse');
    expect(s.html).not.toContain('Nothing to prune');
  });

  it('distinguishes "no candidates" from "candidates, all referenced"', () => {
    expect(ptPruneSummary(NONE).html).toContain('0 auto-added members');
    expect(ptPruneSummary(CLEAN).html).toContain('all still referenced');
  });
});

describe('failure and hostile input', () => {
  it('a null response is an error, not a silent success', () => {
    const s = ptPruneSummary(null);
    expect(s.className).toContain('is-error');
    expect(s.html).not.toContain('ptPruneLibraryApply');
  });

  it('escapes the member names and tags it renders', () => {
    const s = ptPruneSummary({ ...PREVIEW,
      removed: [{ tag: '<img src=x onerror=1>', names: ['<script>'] }] });
    expect(s.html).not.toContain('<img src=x');
    expect(s.html).not.toContain('<script>');
    expect(s.html).toContain('&lt;');
  });

  it('survives a response missing every optional key', () => {
    expect(() => ptPruneSummary({})).not.toThrow();
    expect(ptPruneSummary({}).html).toContain('Nothing to prune');
  });
});
