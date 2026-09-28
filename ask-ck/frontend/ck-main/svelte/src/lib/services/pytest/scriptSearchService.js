import { mockDelay } from '../mockDelay.js';

export const scriptColumns = [
  { key: 'name', label: 'Script', width: 2 },
  { key: 'coverage', label: 'Cov', width: 1, pillClass: (v) => (v === 'Full' ? 'pill-success' : 'pill-muted') },
  { key: 'why', label: 'Why', width: 3 }
];

// Mock reusable-script pool — replace with a real script index search later
const scriptPool = [
  { id: 'script-1', name: 'test_port_speed_set', coverage: 'Full', why: "Sets port speed using the 'speed <n>' CLI command — matches this step's action exactly." },
  { id: 'script-2', name: 'test_port_duplex_set', coverage: 'Full', why: "Sets port duplex mode using 'duplex full/half' — matches this step's action exactly." },
  { id: 'script-3', name: 'test_port_autoneg_toggle', coverage: 'Partial', why: 'Toggles auto-negotiation and verifies the resulting state, but does not assert the specific values this step requires.' },
  { id: 'script-4', name: 'test_port_link_status', coverage: 'Partial', why: 'Polls and asserts link status after a configuration change — covers the verify half of this step but not the trigger.' },
  { id: 'script-5', name: 'test_port_reset', coverage: 'Full', why: "Resets a port to its default configuration — matches this step's teardown intent exactly." }
];

export async function suggestForStep() {
  // TODO: replace with a real script search / LLM suggestion call
  await mockDelay();
  return [...scriptPool];
}

export async function suggestAllSteps() {
  // TODO: replace with a real script search / LLM suggestion call across all steps
  await mockDelay();
  return [...scriptPool];
}

export async function searchForStep(query) {
  // TODO: replace with a real keyword search call
  const q = query.trim().toLowerCase();
  return q
    ? scriptPool.filter((s) => s.name.toLowerCase().includes(q) || s.why.toLowerCase().includes(q))
    : [...scriptPool];
}
