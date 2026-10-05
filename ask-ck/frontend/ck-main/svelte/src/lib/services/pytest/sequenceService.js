// COPIED OVER FROM current/pytest-creator/pytest.js (ptExtractSequence/ptSaveSequence) —
// unlike the Generator's synthesize_objectives, extract_sequence takes NO body (reads the
// authoritative stored session) and returns {sequence, notes, coverage} directly, not a
// wrapped {session}. The caller re-fetches the session separately (casesService.getSession)
// to pick up confirmed/provenance state.
const PT_API = '/api/pytest-create';

export async function extractSequence(key, headers) {
  const res = await fetch(`${PT_API}/extract_sequence/${encodeURIComponent(key)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...headers },
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t.slice(0, 200) || `HTTP ${res.status}`);
  }
  return await res.json();   // {sequence, notes, coverage}
}

export async function saveSequence(key, sequence) {
  const res = await fetch(`${PT_API}/save_sequence/${encodeURIComponent(key)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sequence }),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t.slice(0, 200) || `HTTP ${res.status}`);
  }
  return await res.json();   // {sequence, coverage}
}

export async function confirmStep(key, step) {
  const res = await fetch(`${PT_API}/confirm_step/${encodeURIComponent(key)}/${step}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{}',
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t.slice(0, 300) || `HTTP ${res.status}`);
  }
  return await res.json();   // {session}
}
