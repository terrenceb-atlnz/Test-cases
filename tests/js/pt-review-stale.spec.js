// Slice B in the UI (PLAN-generate-state-and-sequence-sanity, 2026-09-21).
//
// A review describes ONE version of the script. When the code has moved on (a Save / hand
// edit; a Fix already drops the review server-side), the findings must not read as if they
// were about the code on screen. Pinned: with `gen_state.review_stale` the panel shows a
// "stale" badge, folds the findings into <details>, and tags each finding with whether its
// quoted evidence is still present in the current code; without it the panel is unchanged.
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

import '../../ask-ck/frontend/ck-main/current/shared/actions.js';
import { S } from '../../ask-ck/frontend/ck-main/current/shared/state.js';
import { ptLoadCase, renderPtGenPanel } from '../../ask-ck/frontend/ck-main/current/pytest-creator/pytest.js';

const DOM = `
  <div id="nav-pt"></div>
  <div id="panel-pt-seq"><div id="pt-seq-case"></div><div id="pt-seq-refined"></div>
    <div id="pt-seq-list"></div><span id="pt-seq-status"></span><div id="pt-seq-prov"></div></div>
  <span id="pt-load-status"></span>
  <span id="pt-units-status"></span><div id="pt-unit-pills"></div><div id="pt-unit-errors"></div><div id="pt-unit-page"></div>
  <div id="pt-summary-page" class="hidden">
    <span id="pt-gen-path"></span><span id="pt-gen-status"></span>
    <div id="pt-lint-result"></div><div id="pt-review-result"></div>
    <textarea id="pt-gen-code"></textarea>
    <div id="pt-gen-lib-wrap" class="hidden"><span id="pt-gen-lib-name"></span><textarea id="pt-gen-lib-code"></textarea></div>
    <div id="pt-gen-prov"></div>
  </div>`;

const CODE = 'class TestCase_1:\n    def main(self):\n        self.passed(  "ok one" )\n';
const REVIEW = { at: '2026-09-18T01:11:53Z', findings: [
  { severity: 'high', kind: 'verdict_mismatch', where: 'TestCase_1.main', step: 1, what: 'still there',
    evidence: 'self.passed("ok one")', suggestion: 's' },
  { severity: 'low', kind: 'other', where: 'TestCase_2.main', step: 2, what: 'gone now',
    evidence: 'self.failed("never")', suggestion: 's' },
] };

let genState;
const reply = (body) => ({ ok: true, status: 200, json: async () => body });
const settle = async (n = 4) => { for (let i = 0; i < n; i++) await new Promise((r) => setTimeout(r, 0)); };
const session = () => ({ step2: { sequence: [] },
                         step6: { files: { test: { name: 'x.py', code: CODE } }, lint: { ok: true, errors: [], warnings: [] }, review: REVIEW } });

async function load(stale) {
  genState = { script_hash: 'h', assembled_hash: 'h', units: 1, frame_snapshot: true, diverged: false, reason: '', review_stale: stale };
  document.body.innerHTML = DOM;
  S.ptCase = { key: 'AWPTCM-T1' };
  window.alert = vi.fn();
  global.fetch = vi.fn(async (url) => {
    const u = String(url);
    if (u.includes('/load_case/')) return reply({ session: session(), case_title: 't', group_display: 'g', objective: 'o', steps: [], read_only: false, lock: null, gen_state: genState });
    if (u.includes('/session/')) return reply({ session: session(), gen_state: genState });
    if (u.includes('/step_prompts/')) return reply({ units: [] });
    return reply({});
  });
  await ptLoadCase();
  renderPtGenPanel();
  await settle();
}
afterEach(() => vi.restoreAllMocks());

describe('a review made against an earlier version of the script', () => {
  beforeEach(() => load(true));

  it('is badged stale and folded away', () => {
    const el = document.getElementById('pt-review-result');
    expect(document.getElementById('pt-review-stale')).not.toBeNull();
    expect(el.querySelector('details')).not.toBeNull();
    expect(el.textContent).toContain('2 stale finding(s)');
  });

  it('tags each finding by whether its evidence is still in the current code (whitespace-insensitive)', () => {
    const findings = Array.from(document.querySelectorAll('.pt-review-finding'));
    expect(findings).toHaveLength(2);
    expect(findings[0].querySelector('.pt-ev-present')).not.toBeNull();    // spacing differs, text present
    expect(findings[0].classList.contains('pt-review-gone')).toBe(false);
    expect(findings[1].querySelector('.pt-ev-gone')).not.toBeNull();
    expect(findings[1].classList.contains('pt-review-gone')).toBe(true);
  });
});

describe('a review made against the code on screen', () => {
  beforeEach(() => load(false));

  it('renders as before: no stale badge, no folding, no evidence tags', () => {
    const el = document.getElementById('pt-review-result');
    expect(document.getElementById('pt-review-stale')).toBeNull();
    expect(el.querySelector('details')).toBeNull();
    expect(el.textContent).toContain('review: 2 finding(s)');
    expect(el.querySelector('.pt-ev-present, .pt-ev-gone')).toBeNull();
  });
});
