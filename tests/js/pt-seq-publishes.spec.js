// G6 (PLAN-pt-drive-followups-2026-09-24, 2026-09-24): a sequence step may declare `publishes` —
// a value it measures that a LATER step reads. The Sequence table shows it read-only, and it
// must survive a drag or a Save on its OWN row, through the same row cache `claim` uses (the
// server's carry-over matches rows by action text, so a reorder would otherwise lose it).
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const SRC = readFileSync(resolve(dirname(fileURLToPath(import.meta.url)),
  '../../ask-ck/frontend/ck-main/current/pytest-creator/pytest.js'), 'utf8')
  .replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');

describe('publishes on the Sequence table', () => {
  it('is rendered on the row', () => {
    expect(SRC).toContain('${_ptPublishesText(s.publishes)}');
    expect(SRC).toMatch(/function _ptPublishesText\(pubs\)[\s\S]*escapeHtml\(p\.name/);
  });
  it('rides the row cache into the saved row', () => {
    expect(SRC).toMatch(/publishes: Array\.isArray\(s\.publishes\)/);
    expect(SRC).toContain('if (from.publishes) out.publishes = from.publishes;');
  });
});
