import { mockDelay } from '../mockDelay.js';

// The frame (imports, TestSet class, ts.add_testCase() runner) is rendered locally — it cannot
// vary between units, so it is never sent to or returned from the LLM.
export const GENERATE_FRAME_HEADER = 'import art\nfrom framework import TestSet, TestCase, ts\n\nclass AMF_Master_TestSet(TestSet):';
export const GENERATE_FRAME_FOOTER = '\nts.add_testCase(AMF_Master_TestSet)';

export function defaultPromptForUnit(unit, title) {
  if (unit.kind === 'setup') {
    return `Generate the TestSet setUp/tearDown pair for "${title}" — bring up the topology (tb/swi_a, tb/swi_b) and configure the AMF cluster baseline every test case below relies on.`;
  }
  return `Generate the TestCase class body for Sequence Step ${unit.label}: ${unit.step.action} Use the scripts/fragments confirmed for this step as the basis, and assert: ${unit.step.verify}`;
}

function mockCodeForUnit(unit) {
  // TODO: replace with the real returned code from the LLM call
  if (unit.kind === 'setup') {
    return 'def setUp(self):\n    self.tb = art.topology_init(members=["swi_a", "swi_b"])\n    self.tb.amf.enable()\n\ndef tearDown(self):\n    self.tb.amf.disable()\n    self.tb.cleanup()';
  }
  return `class TestCase_${unit.label}(TestCase):\n    def runTest(self):\n        # ${unit.step.action}\n        ...\n        self.assertTrue(True)  # ${unit.step.verify}`;
}

export async function generateUnitCode(unit) {
  // TODO: replace with a real LLM call — sends exactly the (possibly edited) prompt text shown
  await mockDelay();
  return mockCodeForUnit(unit);
}

// Returns a { [unit.id]: code } map for the given units — the caller decides which units still
// need code (only those missing it get regenerated, same as before).
export async function generateAllUnits(units) {
  // TODO: replace with a real LLM call across all units
  await mockDelay();
  const codeByUnitId = {};
  for (const unit of units) {
    codeByUnitId[unit.id] = mockCodeForUnit(unit);
  }
  return codeByUnitId;
}

// Not an LLM call — assembly and linting both happen locally — but kept alongside the rest of
// this step's logic so the component stays pure UI orchestration.
export function assembleScript(generateUnits, generateState) {
  // TODO: replace with a real local assembly + linter call
  const setupUnit = generateUnits.find((u) => u.kind === 'setup');
  const testCaseUnits = generateUnits.filter((u) => u.kind === 'testcase');
  const indent = (code) => code.split('\n').map((line) => '    ' + line).join('\n');

  const assembledCode = [
    GENERATE_FRAME_HEADER,
    indent(generateState[setupUnit.id]?.code ?? ''),
    '',
    testCaseUnits.map((u) => indent(generateState[u.id]?.code ?? '')).join('\n\n'),
    GENERATE_FRAME_FOOTER
  ].join('\n');

  const lintResults = [
    { level: 'pass', message: 'No unused imports.' },
    { level: 'pass', message: 'Every TestCase class is registered via ts.add_testCase().' },
    { level: 'warn', message: 'Line 14: assertion message could be more descriptive.' }
  ];

  return { assembledCode, lintResults };
}

export async function reviewScript() {
  // TODO: replace with a real holistic-review LLM call
  await mockDelay();
  return "The assembled script consistently uses the AMF cluster fixtures established in setUp() across every TestCase, and the assertions map cleanly back to each sequence step's verify condition. No cross-step ordering issues detected.";
}

export async function fixUnitsWithLlm() {
  // TODO: replace with a real per-unit LLM fix call
  await mockDelay();
}

export async function fixWholeScriptWithLlm() {
  // TODO: replace with a real whole-script LLM fix call
  await mockDelay();
}

export async function saveScript() {
  // TODO: replace with a real save API call
  await mockDelay();
  const saveSucceeded = true;
  return saveSucceeded
    ? { status: 'success', message: 'Your PyTest script has been saved.' }
    : { status: 'error', message: 'Something went wrong while saving your PyTest script. Please try again.' };
}
