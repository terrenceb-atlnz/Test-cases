// COPIED OVER FROM current/generator/db-search.js (Zephyr search/suggest) — mirrors
// testlinkService.js exactly; db.py's search_zephyr row already carries both `key` and `id`
// (same value), so no extra id-field mapping is needed here.
const WIZARD_API = '/api/wizard';

export async function fetchStepCandidates(key) {
  const res = await fetch(`${WIZARD_API}/step_candidates/${encodeURIComponent(key)}/2`);
  const data = await res.json();
  return data.candidates || [];
}

// COPIED OVER FROM current/generator/chosen.js's toEntry (the justification fallback chain)
// AND generator.js's confirmStep.
function toSelection(row, order) {
  return {
    id_or_key: row.id,
    title: row.title || row.id,
    justification: row.description || row.justification || row.reason || row.snippet || '',
    order,
  };
}

export async function confirmStep(key, chosen) {
  const selections = (chosen || []).map(toSelection);
  const res = await fetch(`${WIZARD_API}/confirm_step/${encodeURIComponent(key)}/2`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ selections }),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t.slice(0, 200) || `HTTP ${res.status}`);
  }
  return await res.json();
}

// `key` is required server-side (search_zephyr excludes the current Cases list + this key).
export async function searchZephyr(key, query) {
  const params = new URLSearchParams({ q: query || '', case_key: key || '' });
  const res = await fetch(`${WIZARD_API}/search_zephyr?${params}`);
  const data = await res.json();
  return data.results || [];
}

export async function suggestZephyr(key, headers) {
  const res = await fetch(`${WIZARD_API}/suggest_zephyr/${encodeURIComponent(key)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...headers },
    body: '{}',
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t.slice(0, 200) || `HTTP ${res.status}`);
  }
  const data = await res.json();
  return data.suggestions || [];
}
