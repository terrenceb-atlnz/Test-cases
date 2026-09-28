// TODO: replace with a real LLM synthesis call — with no candidates chosen, the LLM will do its
// best using the Test Case context alone

import { mockDelay } from '../mockDelay.js';

const hardcodedObjectives = [
  'Verify AMF master election completes within the expected time window after a forced reboot.',
  'Confirm failover to a backup member preserves configuration state and network reachability.',
  'Validate the system reports a clear warning when firmware versions mismatch during AMF discovery.'
];

export async function synthesizeObjectives() {
  await mockDelay();
  return [...hardcodedObjectives];
}
