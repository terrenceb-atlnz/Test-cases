// @ts-nocheck

// --- MOCK BEFORE PORT ---
// import { mockDelay } from '../mockDelay.js';

function capitalize(str) {
  if (!str) return ""; // Handle empty strings safely
  return str.charAt(0).toUpperCase() + str.slice(1);
}

export const scriptColumns = [
  { key: 'id', label: 'Script', width: 2 },
  { key: 'coverage', label: 'Cov', width: 1, pillClass: (v) => (capitalize(v) === 'Full' ? 'pill-success' : 'pill-muted') },
  { key: 'summary', label: 'Why', width: 3 }
];

// // Mock reusable-script pool — replace with a real script index search later
// const scriptPool = [
//   { id: 'script-1', name: 'test_port_speed_set', coverage: 'Full', why: "Sets port speed using the 'speed <n>' CLI command — matches this step's action exactly." },
//   { id: 'script-2', name: 'test_port_duplex_set', coverage: 'Full', why: "Sets port duplex mode using 'duplex full/half' — matches this step's action exactly." },
//   { id: 'script-3', name: 'test_port_autoneg_toggle', coverage: 'Partial', why: 'Toggles auto-negotiation and verifies the resulting state, but does not assert the specific values this step requires.' },
//   { id: 'script-4', name: 'test_port_link_status', coverage: 'Partial', why: 'Polls and asserts link status after a configuration change — covers the verify half of this step but not the trigger.' },
//   { id: 'script-5', name: 'test_port_reset', coverage: 'Full', why: "Resets a port to its default configuration — matches this step's teardown intent exactly." }
// ];

// export async function suggestForStep() {
//   // TODO: replace with a real script search / LLM suggestion call
//   await mockDelay();
//   return [...scriptPool];
// }

// export async function suggestAllSteps() {
//   // TODO: replace with a real script search / LLM suggestion call across all steps
//   await mockDelay();
//   return [...scriptPool];
// }

// export async function searchForStep(query) {
//   // TODO: replace with a real keyword search call
//   const q = query.trim().toLowerCase();
//   return q
//     ? scriptPool.filter((s) => s.name.toLowerCase().includes(q) || s.why.toLowerCase().includes(q))
//     : [...scriptPool];
// }

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