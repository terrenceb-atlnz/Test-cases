// P3 (PLAN-pt-drive-followups-2026-09-24; C11 of PLAN-pt-followups-review-2026-09-24): a unit the
// SEAT refused on its usage limit gets its own pill, so twelve of them read as "wait for the
// reset" rather than "twelve bad units". The server stores the error as "seat limit: ...".
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const JS = readFileSync(resolve(HERE, '../../ask-ck/frontend/ck-main/current/pytest-creator/pytest.js'), 'utf8')
  .replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
const CSS = readFileSync(resolve(HERE, '../../ask-ck/frontend/ck-main/current/styles.css'), 'utf8');
const PILLS = JS.slice(JS.indexOf('function ptRenderUnitPills'), JS.indexOf('function ptRenderUnitErrors'));

describe('seat-limit pill', () => {
  it('keys on the server\'s "seat limit:" prefix and uses its own class and glyph', () => {
    expect(PILLS).toMatch(/\/\^seat limit:\/\.test\(u\.error/);
    expect(PILLS).toContain("limit ? 'pt-pill-limit' : cls[st]");
    expect(PILLS).toContain("limit ? '⏳'");
  });
  it('is styled', () => {
    expect(CSS).toMatch(/\.pt-pill-row button\.pt-pill-limit \{/);
  });
});
