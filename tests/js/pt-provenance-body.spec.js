// The PyTest Creator's provenance panels must dry-run against the inputs the page is
// SHOWING, not the server's defaults.
//
// provenance.js documents the contract in its own header: "`bodyFn` returns the request
// body (minus dry_run) at click time so it always reflects current naming/inputs".
// pytest.js hard-coded `() => ({})` for every panel, so Refresh posted an empty body and
// the endpoint fell back to its server-side defaults. On the Generate panel that turned
// into a visible failure: the fallback group for AWPTCM-T33351 was
// 'Authentication & Security', which _validate_naming rejects, so Refresh answered 400
// "Invalid group name" naming a group the reviewer had already edited away — while the
// real Generate button, which does post the inputs, worked fine (2026-08-31).
//
// Also pinned: the naming fields autosave, because until a generation SUCCEEDED the
// server had no writer for them at all and an edit was lost on the next re-render.
//
// Source-level, like error-guards.spec.js: these are wired through the click dispatcher
// and the DOM, not exported. Comments are stripped before every assertion — this file's
// own prose quotes the very pattern it forbids, which is the trap tests/_prose.py exists
// for on the Python side.
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const read = (name) =>
  readFileSync(resolve(HERE, `../ask-ck/CK-main/CK_server/static/js/${name}`), 'utf8');

/** Source with // and /* *\/ comments removed — assert on code, never on prose. */
const code = (src) =>
  src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');

function fnBody(src, name) {
  const start = src.indexOf(`function ${name}(`);
  if (start < 0) throw new Error(`${name} not found — did it get renamed?`);
  const rest = src.slice(start);
  const next = rest.slice(1).search(/\n(async )?function |\nexport /);
  return next < 0 ? rest : rest.slice(0, next + 1);
}

const PT = code(read('pytest.js'));

describe('mountPtProvenance', () => {
  const body = fnBody(PT, 'mountPtProvenance');

  it('takes a bodyFn and forwards it to registerProvenance', () => {
    expect(body).toMatch(/function mountPtProvenance\([^)]*bodyFn/);
    expect(body).toMatch(/registerProvenance\([\s\S]*bodyFn/);
  });

  it('no longer hard-codes an empty body for every panel', () => {
    // `bodyFn || (() => ({}))` keeps the old behaviour as a DEFAULT for panels that
    // have no live inputs; what must not come back is the unconditional literal.
    expect(body).toMatch(/bodyFn\s*\|\|/);
  });
});

describe('the Generate panel', () => {
  const body = fnBody(PT, 'renderPtGenPanel');

  it('dry-runs against the live naming fields', () => {
    expect(body).toMatch(/mountPtProvenance\([\s\S]*generate_script[\s\S]*ptGenNaming/);
  });

  it('autosaves the naming fields when they lose focus', () => {
    expect(body).toMatch(/groupEl\.onblur\s*=\s*ptSaveGenNaming/);
    expect(body).toMatch(/nameEl\.onblur\s*=\s*ptSaveGenNaming/);
  });
});

describe('ptGenNaming', () => {
  const body = fnBody(PT, 'ptGenNaming');

  it('reads both fields straight from the DOM, so it cannot go stale', () => {
    expect(body).toMatch(/getElementById\('pt-gen-group'\)/);
    expect(body).toMatch(/getElementById\('pt-gen-name'\)/);
  });
});

describe('ptSaveGenNaming', () => {
  const body = fnBody(PT, 'ptSaveGenNaming');

  it('posts to the naming-only endpoint', () => {
    expect(body).toMatch(/save_naming/);
  });

  it('stays silent on failure — it fires on blur, not on a button press', () => {
    expect(body).toMatch(/if\s*\(!res\.ok\)\s*return/);
    expect(body).toMatch(/catch\s*\(/);
  });

  it('skips the round trip when nothing actually changed', () => {
    expect(body).toMatch(/cur\.group === group && cur\.name === name/);
  });
});

describe('the Script Search panel', () => {
  const body = fnBody(PT, 'renderPtSearchPanel');

  it('dry-runs the per-step endpoint the panel actually drives', () => {
    expect(body).toMatch(/mountPtProvenance\([\s\S]*ptStepSuggestEndpoint/);
  });

  it('no longer points at the retired whole-case suggest', () => {
    // That endpoint left the UI on 2026-08-20; this mount was its last frontend
    // reference, so Refresh rendered a prompt the flow never sends.
    expect(PT).not.toMatch(/suggest_scripts\/\{key\}/);
    expect(PT).not.toMatch(/pytest-create\/suggest_scripts['"`]/);
  });

  it('sends the same body a real per-step suggest sends', () => {
    expect(body).toMatch(/user_inputs/);
  });
});

describe('ptStepSuggestEndpoint', () => {
  const body = fnBody(PT, 'ptStepSuggestEndpoint');

  it('resolves the step at call time, so it follows the pager', () => {
    expect(body).toMatch(/_ptCurStep/);
    expect(body).toMatch(/suggest_scripts_step/);
  });
});

describe('mountPtProvenance endpoint resolution', () => {
  const body = fnBody(PT, 'mountPtProvenance');

  it('accepts a function endpoint for targets that depend on live state', () => {
    expect(body).toMatch(/typeof endpoint === 'function'/);
  });
});
