// G6 (PLAN-pt-drive-followups-2026-09-24) + C6 (PLAN-pt-followups-review-2026-09-24): a sequence
// step may declare `publishes` — a value it measures that a LATER step reads. The Sequence table
// edits it as `name: what it is; …`, sends it explicitly on every save (an emptied box clears it),
// and the server validates names (_normalize_publishes).
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const RAW = readFileSync(resolve(dirname(fileURLToPath(import.meta.url)),
  '../../ask-ck/frontend/ck-main/current/pytest-creator/pytest.js'), 'utf8');
const SRC = RAW.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');

// The two pure converters, lifted out of the module and run.
const conv = new Function(
  SRC.slice(SRC.indexOf('function _ptPublishesToText'), SRC.indexOf('function _ptPublishesText('))
  + '; return { toText: _ptPublishesToText, fromText: _ptPublishesFromText };')();

describe('publishes on the Sequence table', () => {
  it('round-trips name and shape through the text box', () => {
    const pubs = [{ name: 'speedS', shape: 'int Mbps: highest common speed' }, { name: 'base', shape: '' }];
    const text = conv.toText(pubs);
    expect(text).toBe('speedS: int Mbps: highest common speed; base');
    expect(conv.fromText(text)).toEqual(pubs);
    expect(conv.fromText('  ;  ')).toEqual([]);
  });
  it('is an input on every row and is always sent', () => {
    expect(SRC).toContain('${_ptPublishesText(s.publishes, i)}');
    expect(SRC).toContain("out.publishes = pub ? _ptPublishesFromText(pub.value) : (from.publishes || []);");
  });
});
