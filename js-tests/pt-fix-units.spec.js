// Per-unit Fix in the UI (token-efficiency decision 7, 2026-09-07).
//
// Source-level, like pt-provenance-body.spec.js: the handlers are wired through the click
// dispatcher and the DOM, not exported. Pinned:
//   1. both buttons exist in index.html and their actions are registered;
//   2. the handlers hit /fix_units and then POLL — they must not hold a connection per unit
//      (the six-connection deadlock generate_units was rewritten to avoid);
//   3. the poll fires the one-shot settled callback once nothing is in flight, so the
//      Summary refreshes after the server-side re-assembly.
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const read = (p) => readFileSync(resolve(HERE, `../ask-ck/CK-main/CK_server/static/${p}`), 'utf8');
const code = (src) => src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
const JS = code(read('js/pytest.js'));
const HTML = read('index.html');

function fnBody(name) {
  const start = JS.indexOf(`function ${name}(`);
  if (start < 0) throw new Error(`${name} not found`);
  const rest = JS.slice(start);
  const next = rest.slice(1).search(/\n(async )?function |\nexport /);
  return next < 0 ? rest : rest.slice(0, next + 1);
}

describe('the buttons', () => {
  it('exist on the Summary and on step 7, and their actions are registered', () => {
    expect(HTML).toMatch(/data-action="ptFixUnits"[^>]*id="pt-fix-units-btn"/);
    expect(HTML).toMatch(/data-action="ptFixUnitsFromValidate"[^>]*id="pt-fix-units-validate-btn"/);
    const reg = JS.slice(JS.indexOf('registerActions({'));
    expect(reg).toMatch(/\bptFixUnits\b/);
    expect(reg).toMatch(/\bptFixUnitsFromValidate\b/);
  });

  it('keep the whole-script Fix reachable for findings that name no unit', () => {
    expect(HTML).toMatch(/data-action="ptFixFromSummary"/);
    expect(HTML).toMatch(/data-action="ptFixScript"/);
  });
});

describe('the handler', () => {
  const body = fnBody('_ptFixUnitsCommon');
  it('posts once to /fix_units and then polls instead of holding connections', () => {
    expect(body).toMatch(/\/fix_units\/\$\{S\.ptCase\.key\}/);
    expect(body).toMatch(/_ptStartUnitPoll\(\)/);
    expect(body).not.toMatch(/llm:\s*true/);        // not one blocking LLM request
  });
  it('pushes the on-screen edits first, so the fix targets what the reviewer sees', () => {
    expect(body.indexOf('ptPushCodeEdits(false)')).toBeLessThan(body.indexOf('/fix_units/'));
  });
  it('tells the reviewer about findings that name no unit', () => {
    expect(body).toMatch(/unmapped/);
    expect(body).toMatch(/Fix whole script/);
  });
});

describe('the poll', () => {
  it('fires the one-shot settled callback once nothing is in flight', () => {
    const poll = fnBody('_ptPollUnitsOnce');
    expect(poll).toMatch(/if \(!stillRunning\)/);
    expect(poll).toMatch(/_ptOnUnitsSettled/);
    expect(poll).toMatch(/_ptOnUnitsSettled = null/);
  });
});
