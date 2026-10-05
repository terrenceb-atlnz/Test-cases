// COPIED OVER FROM current/pytest-creator/pytest.js (ptRefreshCases/ptLoadCase) — PyTest
// Creator's case list is grouped-only ({key, title} per case, "[N/7 steps]" hint already
// baked into the title server-side for partials), unlike the Generator's flat+grouped
// /cases. toOption/toGroups adapt that shape to CasePicker.svelte's {id, label} contract.
const PT_API = '/api/pytest-create';

function toOption(c) {
  return { id: c.key, label: c.title };
}

function toGroups(groups) {
  return (groups || []).map((g) => ({
    label: g.label,
    cases: (g.cases || []).map(toOption),
  }));
}

export async function listOpenPartialGroups() {
  const res = await fetch(`${PT_API}/pt_cases`);
  const data = await res.json();
  return toGroups(data.in_progress?.grouped);
}

export async function listCompleteGroups() {
  const res = await fetch(`${PT_API}/pt_cases`);
  const data = await res.json();
  return toGroups(data.complete?.grouped);
}

// Acquires this case's per-tab edit lock server-side; response also carries
// `read_only`/`lock`/`message` when someone else already holds it (same shape as the
// Generator's load_case). `objective`/`steps` are the refined case's finalized Step-4/5
// output, exposed directly here (not nested in `session`) since PyTest Creator only reads
// them — the Generator owns writing them.
export async function loadCase(key) {
  const res = await fetch(`${PT_API}/load_case/${encodeURIComponent(key)}`, { method: 'POST' });
  return await res.json();
}

export async function getSession(key) {
  const res = await fetch(`${PT_API}/session/${encodeURIComponent(key)}`);
  return await res.json();
}

export function exportSession() {
  // The real PyTest Creator Cases panel has no Export action (unlike the Generator's) —
  // kept as a no-op so CasePicker.svelte (shared between both tools) still renders
  // consistently; matches the Generator's own currently-unwired Export button.
}
