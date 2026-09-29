// COPIED OVER FROM current/generator/generator.js (case listing + load_case)
const WIZARD_API = '/api/wizard';

function toOption(c) {
  return { id: c.key, label: c.title, status: c.status, progress: c.progress || null };
}

// One in-flight/cached fetch shared by listOpenPartialCases/listCompleteCases/findCase —
// GeneratorPage.svelte calls the first two together on mount; without this they'd each
// hit GET /cases separately for the same data.
let _casesPromise = null;
let _flatCases = [];

function fetchCasesOnce() {
  if (!_casesPromise) {
    _casesPromise = fetch(`${WIZARD_API}/cases`).then((r) => r.json());
    _casesPromise.then((data) => { _flatCases = (data.cases || []).map(toOption); });
  }
  return _casesPromise;
}

export async function listOpenPartialCases() {
  const data = await fetchCasesOnce();
  return (data.incomplete?.cases || []).map(toOption);
}

export async function listCompleteCases() {
  const data = await fetchCasesOnce();
  return (data.complete?.cases || []).map(toOption);
}

// The backend groups cases by Zephyr folder for optgroups (case_registry.build_case_groups),
// but a grouped entry is only {key, title} — no status/progress — and for the "in progress"
// bucket specifically, its title already has a hint baked in server-side (reviews.py's
// get_cases, distinct from the clean title the flat list carries). Use the flat list's
// {label, status, progress} throughout so CasePicker.svelte's progressHint() adds the hint
// exactly once, from the same data the flat rendering already uses correctly.
function toGroups(groups) {
  return (groups || []).map((g) => ({
    label: g.label,
    cases: (g.cases || []).map((c) => {
      const flat = _flatCases.find((f) => f.id === c.key);
      return flat || { id: c.key, label: c.title, status: undefined, progress: null };
    }),
  }));
}

export async function listOpenPartialGroups() {
  const data = await fetchCasesOnce();
  return toGroups(data.incomplete?.grouped);
}

export async function listCompleteGroups() {
  const data = await fetchCasesOnce();
  return toGroups(data.complete?.grouped);
}

export async function findCase(caseId) {
  if (!_flatCases.length) await fetchCasesOnce();
  return _flatCases.find((c) => c.id === caseId) ?? null;
}

// Acquires this case's per-tab edit lock server-side; response also carries
// `read_only`/`lock`/`message` when someone else already holds it. Not yet called from
// GeneratorPage.svelte — that's the next step (session-object + read-only banner wiring).
export async function loadCase(key) {
  const res = await fetch(`${WIZARD_API}/load_case/${encodeURIComponent(key)}`, { method: 'POST' });
  return await res.json();
}

export function exportSession() {
  // TODO: wire up real export
}
