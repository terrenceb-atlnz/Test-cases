// COPIED OVER FROM current/generator/generator.js (synthesizeSteps/applyStepEdits/
// exportBundle/pushToZephyr). step5.testScript.steps is a structured array of
// {description, expectedResult} — expectedResult is deliberately always empty from the
// LLM (memory `expected-results-deliberately-absent`), but a user CAN type one manually,
// matching the real app's per-step edit fields.
const WIZARD_API = '/api/wizard';

// `session` is the FULL current WizardSession, same convention as synthesizeObjectives.
export async function synthesizeSteps(session, headers) {
  const res = await fetch(`${WIZARD_API}/synthesize_steps`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...headers },
    body: JSON.stringify({ session, use_llm: true }),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t.slice(0, 200) || `HTTP ${res.status}`);
  }
  return await res.json();
}

export async function saveSteps(key, steps) {
  const res = await fetch(`${WIZARD_API}/save_steps/${encodeURIComponent(key)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ testScript: { type: 'steps', steps } }),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t.slice(0, 200) || `HTTP ${res.status}`);
  }
  return await res.json();
}

// Writes the drop-in refined-cases/ bundle (traceability.md + zephyr_payload.json) —
// the real, on-disk artefact that marks a case Complete. Not a preview; always has
// filesystem side effects when it succeeds.
export async function exportBundle(session) {
  const res = await fetch(`${WIZARD_API}/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session }),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t.slice(0, 300) || `HTTP ${res.status}`);
  }
  return await res.json();   // ExportResponse: {traceability_md, zephyr_payload, session_json, validation, saved_to, saved_files, message, wrote_bundle}
}

// dryRun=true (default) previews with no writes anywhere. dryRun=false shells out to
// upload_refined.py and performs a REAL write to the live Zephyr server — the `confirm`
// body field is the server's own safeguard (must equal `key` exactly), not decorative.
export async function pushToZephyr(key, { dryRun = true, force = false } = {}) {
  const params = new URLSearchParams({ dry_run: dryRun ? 'true' : 'false' });
  if (force) params.set('force', 'true');
  const res = await fetch(`${WIZARD_API}/push_to_zephyr/${encodeURIComponent(key)}?${params}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(dryRun ? {} : { confirm: key }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error((data && data.detail) || `HTTP ${res.status}`);
  }
  return data;   // {key, dry_run, ok, returncode, output}
}
