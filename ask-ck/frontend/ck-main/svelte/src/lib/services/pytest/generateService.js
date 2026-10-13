// @ts-nocheck

const PT_API = '/api/pytest-create';

// Every unit with its prompt rendered server-side — ids are the server's own ("setup",
// "tc1", "tc2", …), the ones generate_units/unit_code key on. Each unit also carries its
// stored chunk: {prompt, edited, code, status: 'pending'|'ok'|'error', error, at}. The
// render is a few seconds on a big case (it runs in a worker thread server-side), and it
// 409s until Fragments (step 5) is confirmed.
export async function loadUnits(key) {
  const res = await fetch(`${PT_API}/step_prompts/${encodeURIComponent(key)}`);
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t.slice(0, 200) || `HTTP ${res.status}`);
  }
  const data = await res.json();   // {units, skeleton_chars}
  return data.units || [];
}

// ONE request dispatches, ONE request polls — never a request per unit. A request per unit
// holds its connection for the whole LLM call, and six of them use up the browser's
// per-origin connections, starving the broker's own /api/agent/next long-poll: a total
// self-deadlock (current/'s 2026-09-02 incident). This returns as soon as the units are
// queued; progress comes from getUnitsStatus.
//
// `items` is [{id}] or [{id, prompt, edited: true}] — only a prompt the reviewer actually
// edited travels with the request. Every other unit is rendered fresh server-side.
export async function dispatchUnits(key, items) {
  const res = await fetch(`${PT_API}/generate_units/${encodeURIComponent(key)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ units: items }),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t.slice(0, 200) || `HTTP ${res.status}`);
  }
  return await res.json();   // {dispatched, already_running, max_concurrent, primed}
}

// Cheap enough to poll every couple of seconds — deliberately carries no code.
export async function getUnitsStatus(key) {
  const res = await fetch(`${PT_API}/units_status/${encodeURIComponent(key)}`);
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t.slice(0, 200) || `HTTP ${res.status}`);
  }
  return await res.json();   // {units: {id: {status, error, at, chars, running?}}, running, changed_at}
}

// ONE unit's stored reply — fetched once per landed unit, since the status poll ships no code.
export async function getUnitCode(key, unitId) {
  const res = await fetch(`${PT_API}/unit_code/${encodeURIComponent(key)}/${encodeURIComponent(unitId)}`);
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t.slice(0, 200) || `HTTP ${res.status}`);
  }
  return await res.json();   // {unit, status, code, raw, error, at, edited}
}

// Persists Group/script-name on their own, with no generated file required — the only writer
// reachable before a first successful assembly (save_script, the other naming writer, 409s
// without a file: "Generate a script first."). 409s once step6.files.test exists — at that
// point a rename has to move the file on disk too, which is save_script's job, not this one.
export async function saveNaming(key, group, name) {
  const res = await fetch(`${PT_API}/save_naming/${encodeURIComponent(key)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ group, name }),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t.slice(0, 200) || `HTTP ${res.status}`);
  }
  return await res.json();   // {naming: {group, name}}
}

// No LLM — splices the frame + already-generated units deterministically, then lints
// (py_compile + structural AST checks). `group`/`name` are optional overrides; the backend
// falls back to session.step6.naming when omitted. 409s if any unit is still missing code —
// the server's own words, not restated here, so callers surface its message directly.
export async function assembleScript(key, group, name) {
  const res = await fetch(`${PT_API}/assemble_script/${encodeURIComponent(key)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ group, name }),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t.slice(0, 300) || `HTTP ${res.status}`);
  }
  const data = await res.json();   // {files, lint: {errors, warnings}, manifest, units}
  const assembledCode = data.files?.test?.code || '';
  return { assembledCode, lintResults: toLintResults(data.lint), files: data.files, manifest: data.manifest };
}

// Adapts the server's lint {errors, warnings} string arrays into the {level, message} shape
// the Summary panel renders — shared by a fresh assembly and a restore from session.step6.lint.
export function toLintResults(lint) {
  return [
    ...(lint?.errors || []).map((message) => ({ level: 'error', message })),
    ...(lint?.warnings || []).map((message) => ({ level: 'warn', message })),
  ];
}

// Pushes the on-screen script into the session before a review or fix, so it judges the
// code the user can see rather than a stale session copy. Code only, and write_files: false —
// as current/'s ptPushCodeEdits(false): only Save writes generated/ (a review after a bad fix
// must not overwrite the last good copy on disk), and omitting group/name leaves the
// session's naming exactly as it is.
export async function pushCodeEdits(key, code) {
  const res = await fetch(`${PT_API}/save_script/${encodeURIComponent(key)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, write_files: false }),
  });
  if (!res.ok) throw new Error(await errorDetail(res));
  return await res.json();   // {written, lint, naming}
}

// Re-runs the same offline lint Assemble runs (py_compile, structure, house rules, coverage,
// PEP 8) on the session's CURRENT script — push the on-screen edits first (pushCodeEdits), as
// current/'s ptLintScript does, so it judges what the user sees. No LLM.
export async function lintScript(key) {
  const res = await fetch(`${PT_API}/lint_script/${encodeURIComponent(key)}`, { method: 'POST' });
  if (!res.ok) throw new Error(await errorDetail(res));
  return await res.json();   // the lint dict: {ok, errors, warnings, pep8, coverage, ...}
}

// Pass C — the holistic review. Returns FINDINGS, never a rewrite. 409s with a message
// starting "review round cap:" once the script's free review rounds are used; resending
// with extraRound = true is the reviewer's explicit "send another round anyway".
export async function reviewScript(key, headers, extraRound = false) {
  const res = await fetch(`${PT_API}/review_script/${encodeURIComponent(key)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...headers },
    body: JSON.stringify(extraRound ? { extra_round: true } : {}),
  });
  if (!res.ok) throw new Error(await errorDetail(res));
  return await res.json();   // {findings, at, review_rounds, review_rounds_free, counts}
}

// One LLM call that rewrites the WHOLE script from the session's own reasons (lint errors,
// review findings, the last failed run) — no body needed. Archives the previous version and
// clears the review. A following Assemble re-splices the units and would discard it.
export async function fixScript(key, headers) {
  const res = await fetch(`${PT_API}/fix_script/${encodeURIComponent(key)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...headers },
    body: '{}',
  });
  if (!res.ok) throw new Error(await errorDetail(res));
  return await res.json();   // {files, iterations, lint, previous_archived}
}

// Re-generates ONLY the units the current reasons name, and returns at once — progress comes
// from the same units_status poll as Generate. Reasons it did NOT dispatch come back named:
// `unmapped` (no unit — the whole-script fix's job), `structural` (a design decision, never
// sent to a model) and `stale` (the unit changed since the review). `units` limits the run to
// those unit ids (each still gets ALL of its own current reasons).
export async function fixUnits(key, units) {
  const res = await fetch(`${PT_API}/fix_units/${encodeURIComponent(key)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(units ? { units } : {}),
  });
  if (!res.ok) throw new Error(await errorDetail(res));
  return await res.json();   // {dispatched, already_running, unmapped, structural, stale, primed}
}

// A review- or run-driven unit fix is HELD on its unit, never spliced on arrival (G7/D2):
// the unit's own code is untouched until this promotes the held fix of the named units
// (omitted = all), then re-assembles and re-lints.
export async function applyHeldFixes(key, units) {
  const res = await fetch(`${PT_API}/apply_held/${encodeURIComponent(key)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(units ? { units } : {}),
  });
  if (!res.ok) throw new Error(await errorDetail(res));
  return await res.json();   // {applied, assembled, lint_ok, lint_errors, previous_archived}
}

// FastAPI errors arrive as {"detail": "..."}; callers match on the message itself (e.g. the
// review round cap), so unwrap it rather than passing the raw JSON text through.
async function errorDetail(res) {
  const t = await res.text();
  try {
    const d = JSON.parse(t).detail;
    if (typeof d === 'string') return d;
  } catch (_) { /* not JSON — fall through to the raw text */ }
  return t.slice(0, 300) || `HTTP ${res.status}`;
}

// Save and Finish = current/'s "Save to generated/" then "Confirm step 5", in one go:
//  1. save_script with the on-screen code + naming and write_files: true — the one path that
//     writes generated/<group>/<name>.py; it re-lints and un-confirms Generate.
//  2. confirm_step/6 with an empty body, exactly as current/'s ptConfirm(6). The server refuses
//     on blocking lint errors, unacknowledged policy errors or a coverage gap — its own message
//     is returned as the failure (no acknowledgement prompt, same as current/).
// Never throws: the result is always {status, message} for the save modal.
export async function saveAndFinish(key, group, name, code) {
  let saved;
  try {
    const res = await fetch(`${PT_API}/save_script/${encodeURIComponent(key)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ group, name, code, write_files: true }),
    });
    if (!res.ok) throw new Error(await errorDetail(res));
    saved = await res.json();   // {written, lint, naming, gen_state}
  } catch (e) {
    return { status: 'error', message: `Save failed: ${(e && e.message) || e}` };
  }
  const written = (saved.written || []).join(', ') || '(no files written)';
  try {
    const res = await fetch(`${PT_API}/confirm_step/${encodeURIComponent(key)}/6`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{}',
    });
    if (!res.ok) throw new Error(await errorDetail(res));
  } catch (e) {
    return { status: 'error', message: `Saved (${written}), but Generate could not be confirmed: ${(e && e.message) || e}` };
  }
  return { status: 'success', message: `Saved ${written} and confirmed Generate.` };
}
