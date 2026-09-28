// TODO: replace with a real TestLink search / LLM suggestion API call

import { mockDelay } from '../mockDelay.js';

const testLinkPool = [
  { id: 'tl-1', caseId: 'TL-10432', title: 'AMF Master election on reboot', score: '92', description: 'Verifies AMF master re-election after a forced reboot of the current master.' },
  { id: 'tl-2', caseId: 'TL-10488', title: 'AMF backup promotion timing', score: '87', description: 'Confirms backup member promotes to master within the expected failover window.' },
  { id: 'tl-3', caseId: 'TL-10501', title: 'AMF split-brain recovery', score: '79', description: 'Validates cluster recovers cleanly from a simulated split-brain condition.' },
  { id: 'tl-4', caseId: 'TL-10556', title: 'AMF member join with mismatched firmware', score: '64', description: "Checks join behaviour when a candidate member runs a different firmware version." },
  { id: 'tl-5', caseId: 'TL-10602', title: 'AMF master priority override', score: '58', description: 'Ensures a manually configured priority correctly overrides election order.' }
];

export async function searchTestLink(query) {
  const q = query.trim().toLowerCase();
  return q
    ? testLinkPool.filter((c) => c.title.toLowerCase().includes(q) || c.caseId.toLowerCase().includes(q))
    : [...testLinkPool];
}

export async function suggestTestLink() {
  await mockDelay();
  return [...testLinkPool];
}
