// Unit specs for the frontend half of adversarial-review batch D — missing res.ok
// checks (provenance.js:75, generator.js:480).
//
// These were the only two fetches in static/js/ without a status check. Both failed
// silently in the worst way: provRefresh rendered an HTTP error as a GREEN success with
// "(empty)" content, discarding the actionable `detail`; confirmStep assigned
// `data.session` from an error body, setting S.currentSession to undefined and wiping
// the in-memory session while the UI carried on as if the confirm had worked.
//
// The functions are not exported (they are wired through the delegated click
// dispatcher), so these specs assert the source-level invariant plus the shared idiom,
// the same drift-detection discipline used by stale-badges.spec.js.
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const JS = (name) =>
  resolve(HERE, `../ask-ck/CK-main/CK_server/static/js/${name}`);

const read = (name) => readFileSync(JS(name), 'utf8');

/** The body of a named async function, up to the next top-level declaration. */
function fnBody(src, name) {
  const start = src.indexOf(`function ${name}(`);
  if (start < 0) throw new Error(`${name} not found — did it get renamed?`);
  const rest = src.slice(start);
  const next = rest.slice(1).search(/\n(async )?function |\nexport /);
  return next < 0 ? rest : rest.slice(0, next + 1);
}

describe('provenance.js provRefresh', () => {
  const body = fnBody(read('provenance.js'), 'provRefresh');

  it('checks res.ok before treating the payload as a success', () => {
    expect(body).toMatch(/if\s*\(!res\.ok\)/);
  });

  it('throws with the server detail so the catch can surface it', () => {
    // The existing catch already does setStatus(..., true) and leaves ok=false, which
    // drives the red flash — so throwing is what routes an error to the right UI.
    expect(body).toMatch(/throw new Error\(d\.detail/);
  });

  it('tolerates a non-JSON error body', () => {
    expect(body).toMatch(/\.json\(\)\.catch\(/);
  });
});

describe('generator.js confirmStep', () => {
  const body = fnBody(read('generator.js'), 'confirmStep');

  it('checks res.ok before touching session state', () => {
    expect(body).toMatch(/if\s*\(!res\.ok\)/);
    // The guard must come BEFORE the assignment, or the session is already clobbered.
    // Compare against the real statement, not prose: strip comments first, otherwise a
    // comment mentioning the assignment skews the index.
    const code = body.replace(/\/\/.*$/gm, '');
    expect(code.indexOf('!res.ok')).toBeLessThan(code.indexOf('S.currentSession = data.session'));
  });

  it('only adopts a payload that actually carries a session', () => {
    // Defends against a malformed 200 as well as an error body.
    expect(body).toMatch(/if\s*\(data && data\.session\)\s*S\.currentSession = data\.session/);
  });

  it('reports the failure to the user instead of failing silently', () => {
    expect(body).toMatch(/Confirm failed/);
  });

  it('encodes the case key like every other call site', () => {
    expect(body).toMatch(/encodeURIComponent\(S\.currentKey\)/);
  });

  it('surfaces the batch-A invalidation so the Stale badges are explained', () => {
    expect(body).toMatch(/invalidated/);
  });
});

describe('no unguarded fetches remain in the wizard front-end', () => {
  // Every module that fetches must check the status somewhere. This is deliberately
  // coarse — it catches a NEW module added with no guard at all.
  const modules = ['provenance.js', 'generator.js', 'admin.js', 'pytest.js'];

  for (const name of modules) {
    it(`${name} checks response status`, () => {
      const src = read(name);
      if (!src.includes('fetch(')) return;              // nothing to guard
      expect(src).toMatch(/res\.ok|r\.ok|response\.ok|\.status\b/);
    });
  }
});

describe('pytest.js run polling', () => {
  const src = read('pytest.js');

  it('stops polling when the server reports the run is no longer active', () => {
    // A run orphaned by a restart used to poll forever: the persisted status stayed
    // 'running' and the spinner never resolved.
    expect(src).toMatch(/d\.active === false/);
  });

  it('tells the user the run was interrupted rather than just stopping', () => {
    expect(src).toMatch(/interrupted/);
  });
});
