// @ts-nocheck

function capitalize(str) {
  if (!str) return ""; // Handle empty strings safely
  return str.charAt(0).toUpperCase() + str.slice(1);
}

export const scriptColumns = [
  { key: 'id', label: 'Script', width: 3, code: true },
  { key: 'coverage', label: 'Cov', width: 1, pillClass: (v) => (capitalize(v) === 'Full' ? 'pill-success' : 'pill-muted') },
  { key: 'summary', label: 'Why', width: 9 }
];

// PORTED FROM current/pytest-creator/pytest.js 
const PT_API = '/api/pytest-create';

export async function searchScripts(query) {
  const params = new URLSearchParams({ q: query || '' });
  const res = await fetch(`${PT_API}/search_scripts?${params}`, {});
  const data = await res.json();
  return data.results || [];
}

export async function suggestStep(key, stepN, headers) {
  const res = await fetch(`${PT_API}/suggest_scripts_step/${key}/${stepN}`, {
    method: 'POST',
    body: JSON.stringify({ user_inputs: '' }),
    headers: { 'Content-Type': 'application/json', ...headers },
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t.slice(0, 200) || `HTTP ${res.status}`);
  }
  const data = await res.json();
  return data.matches || [];
  // if (el) el.textContent = `${(d.matches || []).length} match(es) for sequence step ${stepN}.`;
}

export async function getScriptSource(id) {
  const params = new URLSearchParams({ id, start: '1', end: '120' });
  const res = await fetch(`${PT_API}/script_source?${params}`, {});
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t.slice(0, 200) || `HTTP ${res.status}`);
  }
  return await res.json();
}

export async function saveMatches(key, selections, records) {
  const res = await fetch(`${PT_API}/save_matches/${key}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ selections, records }),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t.slice(0, 200) || `HTTP ${res.status}`);
  }
  return await res.json();
}