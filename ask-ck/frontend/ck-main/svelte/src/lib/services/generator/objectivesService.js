// COPIED OVER FROM current/generator/generator.js (synthesizeObjectives/applyObjectiveEdits/
// confirmObjectives). `step4.objective` is a single server-produced, sanitized HTML string
// (<ul><li>…</li></ul>), edited as raw HTML text — not the Array<string> the old mock modeled.
const WIZARD_API = '/api/wizard';

// `session` is the FULL current WizardSession (not just the key) — synthesize_objectives
// validates it against the pydantic model and re-derives everything from it server-side.
export async function synthesizeObjectives(session, headers) {
  const res = await fetch(`${WIZARD_API}/synthesize_objectives`, {
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

export async function saveObjective(key, objective, confirm) {
  const res = await fetch(`${WIZARD_API}/save_objective/${encodeURIComponent(key)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ objective, confirm: !!confirm }),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t.slice(0, 200) || `HTTP ${res.status}`);
  }
  return await res.json();
}

// No `objective` arg: confirms whatever is already stored on the session (the plain
// "Review & Confirm" path, with no pending textarea edits).
export async function confirmObjectives(key, objective) {
  const body = objective ? { objective } : {};
  const res = await fetch(`${WIZARD_API}/confirm_objectives/${encodeURIComponent(key)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t.slice(0, 200) || `HTTP ${res.status}`);
  }
  return await res.json();
}
