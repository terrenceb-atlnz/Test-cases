// COPIED OVER FROM current/generator/db-search.js (ATPyLib search/suggest) — mirrors
// testlinkService.js/zephyrService.js exactly; search_atp needs no case_key (unlike
// search_zephyr), matching search_testlink.
const WIZARD_API = '/api/wizard';

export async function fetchStepCandidates(key) {
  const res = await fetch(`${WIZARD_API}/step_candidates/${encodeURIComponent(key)}/3`);
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
  const res = await fetch(`${WIZARD_API}/confirm_step/${encodeURIComponent(key)}/3`, {
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

export async function searchAtpylib(query) {
  const params = new URLSearchParams({ q: query || '' });
  const res = await fetch(`${WIZARD_API}/search_atp?${params}`);
  const data = await res.json();
  return data.results || [];
}

export async function suggestAtpylib(key, headers) {
  const res = await fetch(`${WIZARD_API}/suggest_atp/${encodeURIComponent(key)}`, {
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
