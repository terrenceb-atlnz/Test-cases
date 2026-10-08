// @ts-nocheck

const PT_API = '/api/pytest-create';

// Whole-case LLM call — gather_fragments has no step-id concept, it gathers against every
// script chosen in Script Search at once (and 409s unless that step is already confirmed).
export async function gatherFragments(key, headers) {
  const res = await fetch(`${PT_API}/gather_fragments/${encodeURIComponent(key)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...headers },
    body: '{}',
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t.slice(0, 200) || `HTTP ${res.status}`);
  }
  return await res.json();
}

// Persists the reviewer's selected fragments (list of {source_id, symbol}) — the full
// gathered pool stays on step5.fragments either way, only step5.selected changes.
export async function saveFragments(key, keep) {
  const res = await fetch(`${PT_API}/save_fragments/${encodeURIComponent(key)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ keep }),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t.slice(0, 200) || `HTTP ${res.status}`);
  }
  return await res.json();
}
