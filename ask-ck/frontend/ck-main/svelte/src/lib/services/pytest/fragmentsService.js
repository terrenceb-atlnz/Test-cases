import { mockDelay } from '../mockDelay.js';

// Mock reusable-code fragments per sequence step — replace with a real code-reuse search / LLM
// call later. Each step gets zero or more "recommended" (green) fragments plus zero or more
// "redundant" alternatives (red, nested) the LLM preferred the recommended one(s) over.
const mockFragmentGroups = {
  'seq-1': [
    { id: 'frag-1a', name: 'TestSet', source: 'art/1300_amf_cluster/test-1300.1004.py', steps: 1, recommended: true,
      description: 'selected to configure the AMF cluster (member-priority set across tb/swi_a/swi_b) — matches the priority values this step needs.',
      codeLines: 41, code: 'def test_1300_1004(tb):\n    tb.swi_a.amf.priority_set(member="swi_a", priority=100)\n    tb.swi_b.amf.priority_set(member="swi_b", priority=50)\n    ...' },
    { id: 'frag-1b', name: 'TestSet', source: 'art/1300_amf_cluster/test-1300.1002.py', steps: 1, recommended: false,
      redundantReason: 'redundant to test-1300.1004 TestSet — identical priority configuration without the multi-member topology.',
      codeLines: 22, code: 'def test_1300_1002(tb):\n    tb.swi_a.amf.priority_set(member="swi_a", priority=100)\n    ...' },
    { id: 'frag-1c', name: 'TestSet', source: 'art/6000_link_check/test-6000.1001.py', steps: 1, recommended: false,
      redundantReason: 'redundant to test-1300.1004 TestSet — generic topology init only, no AMF priority handling.',
      codeLines: 10, code: 'def test_6000_1001(tb):\n    tb.topology_init()\n    ...' }
  ],
  'seq-2': [
    { id: 'frag-2a', name: 'TestSet', source: 'art/1300_amf_cluster/test-1300.2011.py', steps: 1, recommended: true,
      description: 'selected to force-reboot the identified master member and confirm the reboot command is accepted.',
      codeLines: 28, code: 'def test_1300_2011(tb):\n    tb.amf.master().reboot(force=True)\n    ...' },
    { id: 'frag-2b', name: 'TestSet', source: 'art/1300_amf_cluster/test-1300.2003.py', steps: 1, recommended: false,
      redundantReason: 'redundant to test-1300.2011 TestSet — reboots a member by fixed index rather than by resolved master role.',
      codeLines: 19, code: 'def test_1300_2003(tb):\n    tb.swi_a.reboot(force=True)\n    ...' }
  ],
  'seq-3': [
    { id: 'frag-3a', name: 'TestSet', source: 'art/1300_amf_cluster/test-1300.3007.py', steps: 1, recommended: true,
      description: 'selected to poll cluster state until re-election completes and record the elapsed time.',
      codeLines: 33, code: 'def test_1300_3007(tb):\n    start = time.time()\n    tb.amf.wait_for_reelection()\n    ...' }
  ],
  'seq-4': [
    { id: 'frag-4a', name: 'TestSet', source: 'art/1300_amf_cluster/test-1300.4002.py', steps: 1, recommended: true,
      description: "selected to query and return the current master member's identity for comparison against the expected candidate.",
      codeLines: 17, code: 'def test_1300_4002(tb):\n    return tb.amf.master().name\n    ...' },
    { id: 'frag-4b', name: 'TestSet', source: 'art/1300_amf_cluster/test-1300.1004.py', steps: 1, recommended: false,
      redundantReason: 'redundant to test-1300.4002 TestSet — also queries member roles, but as a side effect of priority configuration rather than a direct identity query.',
      codeLines: 41, code: 'def test_1300_1004(tb):\n    tb.swi_a.amf.priority_set(member="swi_a", priority=100)\n    ...' }
  ],
  'seq-5': [
    { id: 'frag-5a', name: 'TestSet', source: 'art/1300_amf_cluster/test-1300.5001.py', steps: 1, recommended: true,
      description: 'selected to query cluster state from every member and confirm a consistent view.',
      codeLines: 25, code: 'def test_1300_5001(tb):\n    states = [m.cluster_state() for m in tb.amf.members()]\n    ...' },
    { id: 'frag-5b', name: 'TestSet', source: 'art/1300_amf_cluster/test-1300.4002.py', steps: 1, recommended: false,
      redundantReason: "redundant to test-1300.5001 TestSet — queries a single member's identity rather than full-cluster state.",
      codeLines: 17, code: 'def test_1300_4002(tb):\n    return tb.amf.master().name\n    ...' }
  ]
};

// Returns a { [stepId]: fragment[] } map for the given step ids — replace with a real
// code-reuse search / LLM call later.
export async function gatherFragments(stepIds) {
  await mockDelay();
  const groups = {};
  for (const id of stepIds) {
    groups[id] = (mockFragmentGroups[id] ?? []).map((f) => ({ ...f }));
  }
  return groups;
}
