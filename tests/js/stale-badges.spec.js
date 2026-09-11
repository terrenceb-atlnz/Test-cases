// Unit specs for the Step 4/5 "stale" badges (adversarial-review batch A,
// finding wizard.py:1381 — the frontend half).
//
// The server marks step4/step5 `stale` when an upstream DB review is re-confirmed
// with DIFFERENT selections: the generated content is kept, but it no longer matches
// what it was synthesized from. Showing it as "✓ Confirmed" / "✓ Ready" there is
// exactly what let a self-contradictory bundle reach export, so `stale` must outrank
// both — that precedence is what these specs lock.
//
// The badge logic lives inside generator.js's un-exported updateUI(), which pulls in
// the session/fetch plumbing. Rather than reshape production code for the test, we
// mirror the decision table here and assert the real source still implements it
// (see the drift-detection spec at the bottom) — same discipline as fixture-dom.js.
import { describe, it, expect, beforeEach } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const GENERATOR_JS = resolve(
  HERE,
  '../ask-ck/CK-main/CK_server/static/js/generator.js',
);

// The badge4/badge5 decision table, mirrored from generator.js updateUI().
function badge4For(s) {
  const hasObj = !!(s.step4 && (s.step4.objective || '').trim());
  const objStale = !!(s.step4 && s.step4.stale && hasObj);
  const objConf = !!(s.step4 && s.step4.confirmed && hasObj && !objStale);
  if (objStale) return { cls: 'badge badge-warning', text: '⚠ Stale — selections changed' };
  if (objConf) return { cls: 'badge badge-success', text: '✓ Confirmed' };
  if (hasObj) return { cls: 'badge', text: 'Draft' };
  return { cls: 'hidden', text: '' };
}

function badge5For(s, steps) {
  const hasSteps = !!(steps && steps.steps && steps.steps.length);
  const stepsStale = !!(s.step5 && s.step5.stale && hasSteps);
  if (stepsStale) return { cls: 'badge badge-warning', text: '⚠ Stale — selections changed' };
  if (hasSteps) return { cls: 'badge badge-success', text: '✓ Ready' };
  return { cls: 'hidden', text: '' };
}

const OBJ = '<ul><li>a</li><li>b</li><li>c</li></ul>';
const STEPS = { type: 'steps', steps: [{ description: 'd', expectedResult: 'e' }] };

beforeEach(() => {
  document.body.innerHTML = '';
});

describe('step 4 objective badge', () => {
  it('shows Confirmed for a confirmed, non-stale objective', () => {
    const b = badge4For({ step4: { objective: OBJ, confirmed: true } });
    expect(b.text).toBe('✓ Confirmed');
    expect(b.cls).toContain('badge-success');
  });

  it('shows Stale — and NOT Confirmed — when the server flags it stale', () => {
    // The regression: confirmed:true + stale:true previously rendered as green.
    const b = badge4For({ step4: { objective: OBJ, confirmed: true, stale: true } });
    expect(b.text).toContain('Stale');
    expect(b.cls).toContain('badge-warning');
    expect(b.cls).not.toContain('badge-success');
  });

  it('shows Draft for an unconfirmed objective', () => {
    expect(badge4For({ step4: { objective: OBJ, confirmed: false } }).text).toBe('Draft');
  });

  it('hides the badge when there is no objective', () => {
    expect(badge4For({ step4: {} }).cls).toBe('hidden');
  });

  it('ignores a stale flag when there is no objective to be stale', () => {
    expect(badge4For({ step4: { stale: true } }).cls).toBe('hidden');
  });
});

describe('step 5 steps badge', () => {
  it('shows Ready for non-stale steps', () => {
    const b = badge5For({ step5: {} }, STEPS);
    expect(b.text).toBe('✓ Ready');
    expect(b.cls).toContain('badge-success');
  });

  it('shows Stale — and NOT Ready — when the server flags it stale', () => {
    const b = badge5For({ step5: { stale: true } }, STEPS);
    expect(b.text).toContain('Stale');
    expect(b.cls).toContain('badge-warning');
    expect(b.cls).not.toContain('badge-success');
  });

  it('hides the badge when there are no steps', () => {
    expect(badge5For({ step5: { stale: true } }, { type: 'steps', steps: [] }).cls).toBe('hidden');
  });
});

describe('generator.js source (drift detection)', () => {
  // If the mirrored table above drifts from production, these fail — the specs above
  // would otherwise keep passing against a decision table the app no longer uses.
  const src = readFileSync(GENERATOR_JS, 'utf8');

  it('reads the stale flag for both step 4 and step 5', () => {
    expect(src).toMatch(/objStale\s*=\s*!!\(s\.step4 && s\.step4\.stale/);
    expect(src).toMatch(/stepsStale\s*=\s*!!\(s\.step5 && s\.step5\.stale/);
  });

  it('excludes stale from the confirmed state so stale wins', () => {
    expect(src).toMatch(/objConf\s*=.*!objStale/);
  });

  it('renders the warning badge class for both stale states', () => {
    const warnings = src.match(/badge badge-warning/g) || [];
    expect(warnings.length).toBe(2);
  });
});
