// The fragments coverage pill must agree with the cards it is sitting above.
//
// THE DEFECT (2026-09-02, AWPTCM-T44297)
// -------------------------------------
// The step body renders from `_ptFragAcct` (per-step accounting from the last Gather); the
// coverage pill, the ✓/✗ badge and the "no fragment selected" note read `_fragsForStep`
// (the pool's `maps_to`). Two sources of truth for one question, so they can disagree.
//
// They did. After the sequence was re-extracted from 13 steps to 31, the fragment pool
// survived with `maps_to` keyed on the OLD numbering — `accounting` was non-empty for all
// 31 steps while `maps_to` covered only 25. Step 14 displayed three TICKED fragment cards
// and reported "no fragment selected" with a ✗ pill. Both halves were telling the truth
// about different data.
//
// The backend merge is fixed separately (tests/test_pt_fragment_maps_to.py). This pins the
// UI half: the pill must be computed from the same set the body renders, so it can never
// contradict what the user can see, even when the underlying data is imperfect.
//
// Source-level, matching the other pt specs: these are module-scoped functions driven
// through the click dispatcher. Comments are stripped before every assertion — this file's
// prose names the very identifiers it forbids.
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const SRC = readFileSync(
  resolve(HERE, '../ask-ck/CK-main/CK_server/static/js/pytest.js'), 'utf8');
const CODE = SRC.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');

// The fragments renderer only.
const FRAG = CODE.slice(CODE.indexOf('function ptRenderFragSteps'),
                        CODE.indexOf('function ptFragGoStep'));

describe('fragments coverage source', () => {
  it('derives a step\'s key set from the accounting as well as maps_to', () => {
    expect(CODE).toContain('function _fragKeysForStep');
    const fn = CODE.slice(CODE.indexOf('function _fragKeysForStep'),
                          CODE.indexOf('function _selectedKeysForStep'));
    expect(fn).toContain('_ptFragAcct');      // what the cards come from
    expect(fn).toContain('_fragsForStep');    // plus the maps_to leftovers the body shows
  });

  it('counts a ticked REDUNDANT fragment as covering the step', () => {
    // Redundant entries are unticked by default, but the reviewer may tick one to
    // override — and a ticked fragment serving the step does cover it. The body renders
    // them, so the pill must see them.
    const fn = CODE.slice(CODE.indexOf('function _fragKeysForStep'),
                          CODE.indexOf('function _selectedKeysForStep'));
    expect(fn).toContain('redundant');
  });

  it('computes the pill and the badge from that set, not from maps_to alone', () => {
    expect(FRAG).toContain('_selectedKeysForStep');
    // The old implementation is the bug; it must not come back.
    expect(FRAG).not.toMatch(/stepHasSel\s*=\s*\(n\)\s*=>\s*_fragsForStep\(n\)\.some/);
  });

  it('computes the per-step selected COUNT from the same set', () => {
    // selCount drives "N selected" vs "no fragment selected" in the step header — the
    // exact text that contradicted the cards.
    const line = FRAG.split('\n').find(l => l.includes('selCount ='));
    expect(line).toBeTruthy();
    expect(line).toContain('_selectedKeysForStep');
  });

  it('still keeps maps_to as one of the inputs', () => {
    // Not a rewrite: a fragment that maps to a step but was never placed by the accounting
    // (a legacy gather with no accounting at all) must still count.
    expect(CODE).toContain('function _fragsForStep');
  });
});
