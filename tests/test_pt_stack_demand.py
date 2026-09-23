"""Plan 8.1 (2026-09-23): a stack name borrowed from fragment code is never a bench demand.

WHY. The D13 chain (PLAN-pipeline-end-to-end §8.1): two reused LLDP fragments came from
`art/1332_lldp_med/test-1332.{1001,2001}.py`, whose `TestSet.init()` binds `stk_a` —
incidental to the LLDP logic. `_detect_topology` regexed `stk_*` over sequence text PLUS
fragment code, so the frame rendered `stk_a = setup.init_stk('stk_a')`, assigned and never
used, and tb470 (no [stack] then) failed preflight: no generated script could book bench time.

The rule (Terrence, 2026-09-23): a `stk_*` named in the case's own SEQUENCE is bound for real;
one seen only in fragment code is aliased to the DUT (`stk_a = dut`) — in ART `stk_a` IS the
DUT's stack, which init() binds already — so fragment code still resolves and the script
demands nothing new. Offline: real module, no LLM, no hardware.
"""
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main" / "CK_server"))

pytest.importorskip("models")
from routers import pytest_create as pc  # noqa: E402

SEQ = [{"n": 1, "action": "Configure LLDP on the DUT port", "verify": "", "kind": "setup"},
       {"n": 2, "action": "Show lldp neighbors", "verify": "the partner is listed",
        "kind": "verify"}]
STACK_FRAG = {"code": "stk_a = setup.init_stk('stk_a')\nstk_a.cmd('show lldp neighbors')\n",
              "source_id": "art/1332_lldp_med/test-1332.1001.py", "symbol": "TestSet.init"}


def _render(sequence, fragments):
    return pc._render_skeleton("AWPTCM-T1", "t", sequence, [], fragments, "", None)


def test_a_fragment_only_stack_is_aliased_not_demanded():
    out = _render(SEQ, [STACK_FRAG])
    assert "init_stk('stk_a')" not in out
    assert "stk_a = " in out and "self.stk_a = stk_a" in out
    compile(out, "<frame>", "exec")


def test_a_stack_the_sequence_names_is_still_bound():
    seq = [dict(SEQ[0], action="Configure LLDP on stk_a"), SEQ[1]]
    out = _render(seq, [STACK_FRAG])
    assert "setup.init_stk('stk_a')" in out


def test_topology_reports_no_stack_from_fragment_code_alone():
    _sw, stacks, _pl = pc._detect_topology(SEQ, [STACK_FRAG])
    assert stacks == []
    assert pc._fragment_only_stacks(SEQ, [STACK_FRAG]) == ["stk_a"]
