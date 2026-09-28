// TODO: replace with a real ATPyLib search / LLM suggestion API call

import { mockDelay } from '../mockDelay.js';

const atpylibPool = [
  { id: 'atp-1', caseId: 'ATP-5510', title: 'AMF library master election helper', score: '90', description: 'Reusable ATPyLib helper covering master election setup and teardown.' },
  { id: 'atp-2', caseId: 'ATP-5544', title: 'AMF library failover assertion set', score: '84', description: 'Common assertion set for validating failover timing across AMF library calls.' },
  { id: 'atp-3', caseId: 'ATP-5567', title: 'AMF library topology fixture', score: '77', description: 'Fixture that builds a standard AMF cluster topology for reuse across scored cases.' },
  { id: 'atp-4', caseId: 'ATP-5602', title: 'AMF library firmware version guard', score: '66', description: 'Guards library calls against unsupported firmware version combinations.' },
  { id: 'atp-5', caseId: 'ATP-5631', title: 'AMF library priority helper', score: '52', description: 'Helper for configuring and asserting on AMF member priority values.' },
  { id: 'atp-6', caseId: 'ATP-5639', title: 'AMF library priority helper', score: '52', description: 'Helper for configuring and asserting on AMF member priority values.' },
  { id: 'atp-7', caseId: 'ATP-5789', title: 'AMF library priority helper', score: '52', description: 'Helper for configuring and asserting on AMF member priority values.' },
  { id: 'atp-8', caseId: 'ATP-5678', title: 'AMF library priority helper', score: '52', description: 'Helper for configuring and asserting on AMF member priority values.' },
  { id: 'atp-9', caseId: 'ATP-5780', title: 'AMF library priority helper', score: '52', description: 'Helper for configuring and asserting on AMF member priority values.' },
  { id: 'atp-10', caseId: 'ATP-5656', title: 'AMF library priority helper', score: '52', description: 'Helper for configuring and asserting on AMF member priority values.' }
];

export async function searchAtpylib(query) {
  const q = query.trim().toLowerCase();
  return q
    ? atpylibPool.filter((c) => c.title.toLowerCase().includes(q) || c.caseId.toLowerCase().includes(q))
    : [...atpylibPool];
}

export async function suggestAtpylib() {
  await mockDelay();
  return [...atpylibPool];
}
