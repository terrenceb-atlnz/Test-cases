import { mockDelay } from '../mockDelay.js';

// Mock sequenced test steps — replace with real LLM extraction output
const mockSequencedTestSteps = [
  { id: 'seq-1', from: 1, action: 'Configure the AMF cluster with the required member priorities.', verify: 'Cluster configuration is applied without errors.' },
  { id: 'seq-2', from: 2, action: 'Trigger a forced reboot of the current master member.', verify: 'Reboot command is accepted and the member goes offline.' },
  { id: 'seq-3', from: 3, action: 'Wait for master re-election to complete.', verify: 'Elapsed time is recorded and falls within the expected window.' },
  { id: 'seq-4', from: 4, action: 'Query the identity of the new master.', verify: 'New master matches the expected priority-based candidate.' },
  { id: 'seq-5', from: 5, action: 'Query cluster state from all AMF members.', verify: 'All members report a consistent cluster state.' }
];

export async function extractSequence() {
  // TODO: replace with a real LLM extraction call
  await mockDelay();
  return mockSequencedTestSteps.map((s) => ({ ...s }));
}
