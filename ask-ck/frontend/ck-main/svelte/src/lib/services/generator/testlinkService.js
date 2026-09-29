// COPIED OVER FROM current/generator/db-search.js (TestLink search/suggest)
const WIZARD_API = '/api/wizard';

export async function searchTestLink(query) {
  const params = new URLSearchParams({ q: query || '' });
  const res = await fetch(`${WIZARD_API}/search_testlink?${params}`);
  const data = await res.json();
  return data.results || [];
}

// `key` is required server-side (the suggestion is scoped to this case's loaded session);
// GeneratorPage.svelte supplies it via a closure since CandidatePickerStep's onSuggest takes
// no arguments of its own.
export async function suggestTestLink(key) {
  const res = await fetch(`${WIZARD_API}/suggest_testlink/${encodeURIComponent(key)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{}',
  });
  const data = await res.json();
  return data.suggestions || [];
}
