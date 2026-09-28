// TODO: replace with a real LLM synthesis call deriving steps from the finalized objectives, and
// a real export call

import { mockDelay } from '../mockDelay.js';

const hardcodedTestSteps = [
  'Configure the AMF cluster with the required member priorities.',
  'Trigger a forced reboot of the current master member.',
  'Wait for master re-election to complete and record the elapsed time.',
  'Verify the new master matches the expected priority-based candidate.',
  'Confirm all AMF members report a consistent cluster state.'
];

export async function synthesizeTestSteps() {
  await mockDelay();
  return [...hardcodedTestSteps];
}

export async function exportRepeatableBundle() {
  // TODO: replace with a real export call — for now, mock a successful export
  const exportSucceeded = true;
  return exportSucceeded
    ? { status: 'success', message: 'The repeatable bundle was exported successfully.' }
    : { status: 'error', message: 'Something went wrong while exporting the repeatable bundle. Please try again.' };
}
