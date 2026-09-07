---
name: art-suite-shape
description: "The generated frame and prompt emulate the ART house shape (2026-09-07): DUT<->testbox link on tb.ethA, neighbour named peer, per-case configure/main/tear_down with the shortcut block, checkpoint verdicts, self.supported gating, a suite library, ATPackets layers"
metadata:
  type: project
  verified: 2026-09-07
---

Terrence, 2026-09-07: *"they have a definite way they structure ART test cases, and i want to
emulate it as closely as possible."* Six ART scripts read whole and a census over all 188
(2,085 TestCase classes) fixed what that shape IS; eight divergences were closed the same day.
Numbers below are the census and are what to check against before changing the frame again.

**The ART shape (188 scripts):** `FEATURES = ['ALL']` 174; per-TestCase `configure()` 172 and
`tear_down()` 148 (the mirror, command for command in `no` form); `testCaseMethod +=`
multi-line 135; `testCaseExcl` 107 (hardware-verified platform lists); `self.supported =
False` 68 (the run-time UNSUPPORTED gate); `tb.ethX` bound in `init()` 111 — **the testbox is
the traffic partner** (`(dut.portA, tb.ethA) = setup.init_portlink(dutA, tb, type1='port')`,
tcpdump/scapy on `ethA.name`); a second switch only for multi-switch suites, named by ROLE
(`swiSrc`, `swiDst`, `dutZ`) — **never `dut`**, which is the DUT's own stack handle
(`dutB` = second stack MEMBER, not a partner); every method opens with the shortcut block
(`tb = self.testSet.tb; ethA = tb.ethA; dutA = self.testSet.dutA; portA = dut.portA`) 158;
**several verdicts per `main()`** (3,372 passed / 4,947 failed over 1,794 mains — checkpoints
then the value check, `return` after a fatal `failed()`); suite `library_NNNN.py` imported
with `*` 154 (packets + shared checks); LLDP decoded with `framework.ATPackets` layers
(`pkt.haslayer(lldp_cap_tlv)`, `pkt[lldp_cap_tlv].lldp_med_cap`), never hand-parsed.

**Why it mattered:** on T44297 both Opus and Sonnet wrote `tb.ethA` in every capture unit and
`dut.portA` for the DUT port — faithfully ART — while our frame bound nothing on the testbox
and called the partner `dut`: 59 / 63 unbound-port lint errors, all frame-caused. Our
"exactly one verdict" rule flagged correct ART-style checkpoints as defects.

**How to apply (what the frame/prompt now do; keep them this way):**
- `_detect_links` → `tb` link `(dutA.portA, tb.ethA)` for capture/inject/physical wording,
  `peer` link `(dutA.portPeer, peer.portDut)` for neighbour/negotiation wording; both allowed;
  over-inclusive on purpose (an unneeded link costs one `ck_link_*` bench line, a missing one
  dies on `interface None`). Media role `tb` requires any fitted pluggable.
- Every TestCase renders `configure()`/`main()`/`tear_down()`, each opening with the frame's
  shortcut block; a verdict in configure/tear_down is a policy lint error.
- Fill rule 1: ≥ 1 non-empty verdict per path, checkpoints welcome; LOGGING-CONTRACT §3 and
  TEMPLATE-SPEC C6 carry the dated revision. Do not re-tighten to "exactly one".
- Rule 3d: never generate `testCaseExcl`/`testCaseIncl` (hardware-agnostic, see
  [[scripts-must-be-hardware-agnostic]]); gate at run time with `self.supported = False`.
  Its framework semantics are corpus-grounded, not source-verified (framework not mounted).
- `_build_library` → `library_<case>.py` from stand-alone fragment defs/classes/constants;
  frame imports it with `*`; units are told to CALL, not paste. It REFUSES a fragment that
  re-defines a framework class (legacy `lldp_class.py` copies of the ATPackets layers would
  shadow the real ones — `haslayer()` then fails silently) and a member whose default arg
  needs an unresolvable name (import-time NameError kills the suite); both were in T44297's
  real selection.
- `_framework_surface_slice` renders `ATPackets` as layers with corpus-mined fields
  (`db.script_layer_fields`); the frame imports `framework.ATPackets` when the tb link exists.
- Tests: `tests/test_pt_art_shape.py`. Topology side: [[topology-profiles-contract]].

**Still open:** the DUT handle name comes from the fragments' vocabulary (`dutA` on T44297);
tb470's `[misc]` has no `ck_link_tb` yet, so a capture case cannot run there until the bench
declares it (bench decision). First model pass on the new shape not yet run.
