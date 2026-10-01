// COPIED OVER FROM current/generator/db-search.js (TestLink search/suggest)
const WIZARD_API = '/api/wizard';

// The real app fetches a step's candidates lazily, the first time it's opened — not at
// load_case time (that was a measured ~60s LLM-prefetch regression for Step 3, and a
// blocking 45k-row scan for Step 2; see reviews.py's load_case docstring). Step 1 is
// cheap either way, but this keeps all three steps on the same fetch-on-open contract.
export async function fetchStepCandidates(key) {
  const res = await fetch(`${WIZARD_API}/step_candidates/${encodeURIComponent(key)}/1`);
  const data = await res.json();
  return data.candidates || [];
}

// COPIED OVER FROM current/generator/chosen.js's toEntry (the justification fallback chain)
// AND generator.js's confirmStep. `chosen` rows come from three different sources (search,
// suggest, restore) with different field names for "why" — description/justification/reason/
// snippet — so the fallback picks whichever is present, matching the original exactly.
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
  const res = await fetch(`${WIZARD_API}/confirm_step/${encodeURIComponent(key)}/1`, {
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

export async function searchTestLink(query) {
  const params = new URLSearchParams({ q: query || '' });
  const res = await fetch(`${WIZARD_API}/search_testlink?${params}`);
  const data = await res.json();
  return data.results || [];
}

// `key` is required server-side (the suggestion is scoped to this case's loaded session).
// `headers` carries X-CK-LLM-Call (llmProgressService.startLlmProgress) so the server can
// track/cancel this exact call — GeneratorPage.svelte supplies both via a closure, since
// CandidatePickerStep's onSuggest only knows about the headers, not the case key.
export async function suggestTestLink(key, headers) {
  const res = await fetch(`${WIZARD_API}/suggest_testlink/${encodeURIComponent(key)}`, {
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
