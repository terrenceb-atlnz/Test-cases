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
import { modulePath, assetPath } from './helpers/frontend-paths.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const read = (p) => readFileSync(p.startsWith('js/') ? modulePath(p) : assetPath(p), 'utf8');
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
  it('follow-up #3: the legend names BOTH Fix buttons and both LLM buttons are blue', () => {
    const legend = HTML.slice(HTML.indexOf("If something's wrong &nbsp;"), HTML.indexOf('id="pt-gen-group"'));
    expect(legend).toMatch(/Fix units \(LLM\)/);
    expect(legend).toMatch(/Fix whole script \(LLM\)/);
    expect(legend).toMatch(/HELD/);                               // what a review-driven fix now does
    expect(legend).toMatch(/redundant, not harmful/);             // re-Assemble after Fix units is safe
    expect(legend).toMatch(/Don't re-Assemble after THAT one/);   // …and after the whole-script one is not
    expect(HTML).toMatch(/data-action="ptFixFromSummary" class="btn btn-primary btn-compact"/);
    expect(HTML).toMatch(/data-action="ptFixUnits" class="btn btn-primary btn-compact"/);
    expect(HTML).toMatch(/data-action="ptApplyAllHeld"[^>]*class="btn btn-compact"/);   // local = grey
  });
  it('G7: the hold actions are registered', () => {
    const reg = JS.slice(JS.indexOf('registerActions({'));
    for (const a of ['ptApplyHeld', 'ptDiscardHeld', 'ptApplyAllHeld']) expect(reg).toMatch(new RegExp(`\\b${a}\\b`));
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
  it('G7: tells the reviewer when fixes are HELD and that nothing was spliced', () => {
    expect(body).toMatch(/fu\.held/);
    expect(body).toMatch(/HELD for your approval/);
    expect(body).toMatch(/Nothing was spliced/);
  });
  it('shows structural findings as a design decision, with the reason, never as a fix (G5)', () => {
    expect(body).toMatch(/d\.structural/);
    expect(body).toMatch(/need a design decision/);
    expect(body).toMatch(/structural\.join/);        // the server's reason text is shown, not just a count
    expect(body).toMatch(/fu\.structural/);          // and again when the units land
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
