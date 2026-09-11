// A testbox profile's `.setup` files are a NAMED MAP owned by the people who add
// them — never a "default".
//
// The Testboxes form used to write every setup under the literal key `default`.
// Three things followed. It silently RENAMED whatever key was already stored (the
// live tb470 profile keys its setup `tb470`), so an edit rewrote a name its owner
// chose. On a server shared over the LAN it meant the last person to save named
// everyone else's setup. And because the form only ever wrote one entry, the
// multi-entry map the Run dropdown already renders could not be filled in from the
// UI at all — `Object.entries(p.setups)` was being fed a map the form kept to one.
//
// Terrence, 2026-09-01: "there should NOT be a default setting at all. This will be
// used by multiple people to run their own setups, i dont want a 'default'."
//
// Source-level, matching pt-provenance-body.spec.js: these functions are wired
// through the click dispatcher and the DOM rather than exported. Comments are
// stripped before every assertion — this file's own prose quotes the very literal
// it forbids, which is the trap that discipline exists for.
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const read = (name) =>
  readFileSync(resolve(HERE, `../ask-ck/CK-main/CK_server/static/js/${name}`), 'utf8');
const INDEX = readFileSync(
  resolve(HERE, '../ask-ck/CK-main/CK_server/static/index.html'),
  'utf8',
);

/** Source with // and block comments removed — assert on code, never on prose. */
const code = (src) =>
  src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');

const JS = code(read('pytest.js'));

/** The body of a named function, brace-matched from its declaration. */
function fnBody(src, decl) {
  const start = src.indexOf(decl);
  if (start < 0) throw new Error(`not found: ${decl}`);
  let i = src.indexOf('{', start);
  let depth = 0;
  for (let j = i; j < src.length; j++) {
    if (src[j] === '{') depth++;
    else if (src[j] === '}' && --depth === 0) return src.slice(i, j + 1);
  }
  throw new Error(`unbalanced: ${decl}`);
}

describe('no "default" setup key is ever invented', () => {
  it('the save path does not write a hardcoded setups key', () => {
    const save = fnBody(JS, 'async function ptSaveProfile()');
    expect(save).not.toMatch(/setups\s*:\s*\{\s*default\s*:/);
    expect(save).not.toContain("'default'");
    expect(save).not.toContain('"default"');
  });

  it('the whole module is free of a literal default setups key', () => {
    expect(JS).not.toMatch(/\bdefault\s*:\s*document\.getElementById/);
  });

  it('setups are keyed by the name the operator typed', () => {
    const save = fnBody(JS, 'async function ptSaveProfile()');
    expect(save).toMatch(/setups\[\s*r\.name\s*\]\s*=\s*r\.path/);
  });
});

describe('editing round-trips the owner\'s names', () => {
  it('seeds the editor from every stored entry, keys included', () => {
    const edit = fnBody(JS, 'function ptEditProfile(name)');
    expect(edit).toMatch(/Object\.entries\(p\.setups \|\| \{\}\)/);
    expect(edit).toMatch(/\(\[name, path\]\)\s*=>\s*\(\{ name, path \}\)/);
  });

  it('reads rows back from the DOM rather than from a remembered index', () => {
    const readRows = fnBody(JS, 'function ptReadSetupRows()');
    expect(readRows).toContain('.tb-setup-name');
    expect(readRows).toContain('.tb-setup-path');
  });

  it('removing a row re-reads first, so typed-but-unsaved rows survive', () => {
    const rm = fnBody(JS, 'function ptRemoveSetupRow(i)');
    expect(rm).toContain('ptReadSetupRows()');
    const add = fnBody(JS, 'function ptAddSetupRow()');
    expect(add).toContain('ptReadSetupRows()');
  });
});

describe('setups are optional, and half-filled rows are refused', () => {
  it('no setup field is in the required list', () => {
    const start = JS.indexOf('const PT_TB_REQUIRED');
    const block = JS.slice(start, JS.indexOf('];', start));
    expect(block).not.toContain('setup');
    expect(block).toContain('pt-tb-user');
  });

  it('a row with a name but no path (or vice versa) is rejected, not dropped', () => {
    const save = fnBody(JS, 'async function ptSaveProfile()');
    expect(save).toMatch(/if \(!r\.name \|\| !r\.path\)/);
  });

  it('a duplicate name is rejected rather than silently overwriting', () => {
    const save = fnBody(JS, 'async function ptSaveProfile()');
    expect(save).toMatch(/hasOwnProperty\.call\(setups, r\.name\)/);
  });
});

describe('the Run panel consumes the whole map', () => {
  it('renders an option per stored setup, labelled by its own name', () => {
    const sel = fnBody(JS, 'export function ptProfileSelected(sel)');
    expect(sel).toMatch(/Object\.entries\(p\.setups\)/);
  });
});

describe('the markup carries the editor, and no default field', () => {
  const panel = INDEX.slice(
    INDEX.indexOf('id="panel-pt-testbox"'),
    INDEX.indexOf('<details id="session-debug"'),
  );

  it('has a setups container and an add control', () => {
    expect(panel).toContain('id="pt-tb-setups"');
    expect(panel).toContain('data-action="ptAddSetupRow"');
  });

  it('no longer has the single default .setup input', () => {
    expect(panel).not.toContain('id="pt-tb-setup"');
    expect(panel).not.toMatch(/Default \.setup/);
  });

  it('marks setups optional rather than required', () => {
    const block = panel.slice(panel.indexOf('class="tb-setups"'));
    expect(block).toContain('tb-optional');
    expect(block.slice(0, block.indexOf('</div>'))).not.toContain('tb-req');
  });
});
