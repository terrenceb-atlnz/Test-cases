// TODO: replace with a real Zephyr search / LLM suggestion API call

import { mockDelay } from '../mockDelay.js';

const zephyrPool = [
  { id: 'zep-1', caseId: 'ZEP-2201', title: 'AMF failover latency under load', score: '88', description: 'Measures failover latency for AMF master election under sustained traffic load.' },
  { id: 'zep-2', caseId: 'ZEP-2233', title: 'AMF configuration sync after rejoin', score: '81', description: 'Confirms configuration re-syncs correctly when a member rejoins after a network partition.' },
  { id: 'zep-3', caseId: 'ZEP-2260', title: 'AMF virtual MAC consistency', score: '74', description: 'Validates the virtual MAC address remains consistent across a master re-election.' },
  { id: 'zep-4', caseId: 'ZEP-2298', title: 'AMF firmware mismatch warning', score: '69', description: 'Checks that a firmware mismatch warning is raised during AMF member discovery.' },
  { id: 'zep-5', caseId: 'ZEP-2312', title: 'AMF priority tie-break behaviour', score: '55', description: 'Ensures a deterministic tie-break when two candidates share equal priority.' }
];

export async function searchZephyr(query) {
  const q = query.trim().toLowerCase();
  return q
    ? zephyrPool.filter((c) => c.title.toLowerCase().includes(q) || c.caseId.toLowerCase().includes(q))
    : [...zephyrPool];
}

export async function suggestZephyr() {
  await mockDelay();
  return [...zephyrPool];
}
