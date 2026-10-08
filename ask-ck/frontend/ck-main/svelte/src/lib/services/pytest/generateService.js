import { mockDelay } from '../mockDelay.js';

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

export async function saveScript() {
  // TODO: replace with a real save API call
  await mockDelay();
  const saveSucceeded = true;
  return saveSucceeded
    ? { status: 'success', message: 'Your PyTest script has been saved.' }
    : { status: 'error', message: 'Something went wrong while saving your PyTest script. Please try again.' };
}
