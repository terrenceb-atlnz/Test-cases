# Session State — Objective Drafting Workflow (2026-06-25 / 2026-06-26)

## Summary
This session focused on refining and standardizing the Objective drafting process for AWPTCM manual test cases.

## Session Activity (2026-06-25)
- Performed full end-to-end re-processing of AWPTCM-T33235 using the revised OBJECTIVE_DRAFTING_PROCESS.md (Steps 1–4).
- Identified and corrected over-claiming in the first testScript step when ART coverage is incomplete.
- Produced final `traceability.md` + `zephyr_payload.json` in `refined-cases/AWPTCM-T33235/`.
- Updated Lessons Learned with the "minimal first step" rule.

## Session Activity (2026-06-26)
- Re-processed AWPTCM-T33236 (Fixed Full or half Duplex) using the updated OBJECTIVE_DRAFTING_PROCESS.md (with explicit User-review pause in Step 1).
- Performed full TestLink review (primary + relevant + tangential) with user confirmation before proceeding.
- Confirmed objective artefacts and updated `traceability.md` + `zephyr_payload.json` in `refined-cases/AWPTCM-T33236/`.
- Incorporated LED behavior requirement from primary TestLink case AWP-22510.

## Major Changes
- Cleaned `OBJECTIVE_DRAFTING_PROCESS.md` to be a pure reusable template (removed all T33234-specific history).
- Introduced standardized output structure: `refined-cases/<AWPTCM-Txxxx>/` with `traceability.md` + `zephyr_payload.json`.
- Generalized Step 1.3 (TestLink review) and updated Step 4 instructions.
- Fully processed 4 Port cases (T33233–T33236) through the new workflow.

## Processed Cases
- AWPTCM-T33233 (Auto Negotiation)
- AWPTCM-T33234 (Auto MDI/MDI-X) ← primary focus
- AWPTCM-T33235 (Fixed port Speed) ← fully re-processed from scratch (Steps 1–4)
- AWPTCM-T33236 (Fixed Full or half Duplex) ← completed today
- AWPTCM-T33237 (Active Fiber Monitoring) ← completed with updated repeatable workflow
- AWPTCM-T33241 (IP Local Loopback Address) ← completed after independent first-principles review + merge
- AWPTCM-T33242 (ICMP) ← ATPyLib coverage mapping reviewed and updated (1336 suite restored)

## Lessons Learned
- "No Pluggins" cases are usually covered by the first objective bullet.
- The number of artefacts and steps should remain flexible.
- Explicit documentation of relevant + tangential TestLink cases improves traceability.
- When ART suites only partially cover the intended verification steps, the first testScript step must be limited to the minimal traceability note ("Note: Related ART Tests linked in Traceability") and must not claim coverage.

## Next Recommended Work
- Continue with remaining Port cases using the new structure.
- Test the template on a non-Port area (e.g., ARP or OSPF).
- Consider adding a scaffolding script in `tool/`.

## Files Updated
- `OBJECTIVE_DRAFTING_PROCESS.md` (formalized Repeatable Workflow section + standardized traceability.md structure + User-review pause)
- `SESSION_STATE.md` (this file)
- `refined-cases/AWPTCM-T33235/traceability.md`
- `refined-cases/AWPTCM-T33235/zephyr_payload.json`
- `refined-cases/AWPTCM-T33236/traceability.md`
- `refined-cases/AWPTCM-T33236/zephyr_payload.json`
- `refined-cases/AWPTCM-T33237/traceability.md`
- `refined-cases/AWPTCM-T33237/zephyr_payload.json`
- `refined-cases/AWPTCM-T33241/traceability.md`
- `refined-cases/AWPTCM-T33241/zephyr_payload.json`
- `refined-cases/AWPTCM-T33242/traceability.md`
- `refined-cases/AWPTCM-T33242/zephyr_payload.json`

---

## Session Summary (2026-06-26 Extended)

This extended session focused on refining the repeatable Objective Drafting Workflow through hands-on processing of additional cases beyond the initial Port family:

**Cases processed in this session:**
- AWPTCM-T33237 (Active Fiber Monitoring)
- AWPTCM-T33241 (IP Local Loopback Address) — included first-principles review when candidates were thin
- AWPTCM-T33242 (ICMP) — included detailed ATPyLib-to-objective coverage mapping review

**Key Process Improvements Made:**
- Formalized the full repeatable workflow in `OBJECTIVE_DRAFTING_PROCESS.md` (User-review pause after TestLink documentation, standardized traceability.md structure, explicit ATPyLib coverage mapping)
- Established pattern of independent first-principles review when TestLink candidates are sparse
- Confirmed importance of platform-agnostic language in objectives
- Refined approach to balancing primary case focus vs broader feature overview (e.g., "ICMP" title vs Echo-specific primary)

## Additional Lessons Learned
- User review pause after documenting the TestLink list (primary + relevant + tangential) significantly improves quality and catches scope issues early.
- When candidate matches are weak, performing an independent first-principles analysis and merging it with the data-driven list produces more complete objectives.
- Explicit ATPyLib-to-objective mapping in traceability.md provides valuable traceability and helps identify true gaps vs covered areas.
- Even when a primary case is narrow (e.g., Echo Reply source address), the case title (e.g., just "ICMP") can justify broader basic functional coverage.
- Excluding supporting suites (e.g., 1336 ACL/QoS) should be reversible based on later review — maintain flexibility in the ART string.
- The "minimal first testScript step" rule continues to be essential when ART coverage is partial.

## Current Status
- 15 cases fully processed through the repeatable workflow (T33234–T33237 + T43817/T47871 in Port; T33241–T33243 + T33246–T33250 in IPv4 ARP; T33274 EPSR MIB in Switching). T33233 directory exists but appears incomplete (no payload).
- Workflow validated on both Port and IPv4 ARP areas (including challenging low/null-primary cases). First-principles + feature-family review approach used successfully for T33246 and T33250. ARP batch for the T3324x series is complete.

## Session Activity (2026-06-26 Continued - ARP Batch)
- Completed T33243 (Gratuitous ARP) — strong 1351 ART coverage + Standalone TestLink family.
- Completed T33246 (ARP Polling) — low-confidence case with no primary TestLink match; used independent first-principles review to synthesize objectives from thin precondition/steps.
- Completed T33247 (Clear ARP) — high-confidence primary AWP-4339 with clear HW/SW table impact.
- Completed T33248 (Static ARP) — high-confidence; expanded scope to full Static ARP suite context (persistence, GARP interaction, MAC interoperability, hot-swap/restart) after discovering 15+ related TestLink cases.

## Additional Lessons Learned (ARP Batch)
- When many related TestLink cases exist under a feature family (e.g., 15+ Static ARP titles), it is valuable to expand the "Top Relevant" list and objective scope to capture persistence, interoperability, and edge interactions rather than limiting to the single primary match.
- Low-confidence / null-primary cases can still produce high-quality objectives when the existing thin steps/preconditions are treated as authoritative first-principles input.
- The "minimal first testScript step" rule remains essential; even with good ART coverage (1351 for ARP), the traceability note must stay concise and not over-claim.

## Session Activity (2026-06-26 Continued - ARP Logging)
- Approved primary + relevant TestLink cases for AWPTCM-T33249 (AWP-4397 and AWP-4396); tangential cases omitted per review.
- No direct ATPyLib coverage identified for the "arp log" command or event logging.
- Completed T33249 (ARP Logging) using the repeatable workflow. Objectives derived directly from the approved TestLink steps (creation, aging, static create/delete, movement, mac-address-format, persistence in startup-config).
- Created `refined-cases/IPv4 (44)/AWPTCM-T33249/traceability.md` and `zephyr_payload.json`.

## Additional Lessons Learned (ARP Batch)
- When a manual test case has very thin or no automated coverage, objectives can still be high quality by treating the historical TestLink steps/preconditions as the authoritative source of artefacts.
- Explicitly noting "no direct ART coverage" in traceability and using a minimal first testScript note remains the correct pattern.

## Session Activity (2026-06-26 - MC/Disparate ARPs)
- Confirmed TestLink list for AWPTCM-T33250 (null primary, low confidence case).
- Focused on NLB / arp-mac-disparity family (AWP-20263, 21286–21288, 21298, 21239, 21248, 21299, 21302).
- Identified good direct ATPyLib coverage in 1355 (NLB) and 1351.1001.12/13.
- Completed T33250 (MC/Disparate ARPs (NLB)) using the repeatable workflow with first-principles synthesis from the feature family.
- Created `refined-cases/IPv4 (44)/AWPTCM-T33250/traceability.md` and `zephyr_payload.json`.

## Additional Lessons Learned (ARP Batch)
- Low-confidence cases with no primary match can still be completed effectively by selecting the full relevant feature family from TestLink + cross-referencing dedicated ART suites (e.g. 1355 for NLB).
- "Disparate ARP" artefacts centre on acceptance of virtual MC/unicast MACs for unicast IPs, mode-specific command behaviour, port binding vs flooding, and persistence.

## Next Recommended Work
- ARP batch complete for the T3324x series.
- T33274 (EPSR Mib) completed and confirmed.
- Process remaining high-confidence decisions from later batches (e.g. next EPSR T33275 "Enhanced Recovery", T33279 BPDU, STP, PoE, auth cases in dec_00 and subsequent)
- Consider adding a simple `tool/scaffold_case.py` helper as previously noted

---

## Session Close / Handoff (2026-06-26)

**Work completed this session:**
- Finished the immediate IPv4 ARP batch (T33243–T33250) using the established repeatable workflow.
- T33249 (ARP Logging): relied primarily on TestLink (minimal ART coverage); user approved limited relevant cases, tangentials omitted.
- T33250 (MC/Disparate ARPs / NLB): null primary / low confidence; used full feature family from TestLink (ER-410 NLB + Broadcom arp-mac-disparity) + discovered strong dedicated coverage in ART suite 1355 and 1351 cases.
- All outputs follow the standardized `refined-cases/<key>/` layout with `traceability.md` (decisions, TestLink list, ATPyLib, gaps, ART string) and `zephyr_payload.json` (objective `<ul>` + testScript steps).

**Key lessons recorded:**
- For null/low-confidence primaries: curate the complete relevant TestLink feature family rather than relying on weak candidates. Cross-reference with any dedicated ART suites (e.g. 1355 for NLB).
- Artefacts for disparate/MC ARP (NLB) focus on: acceptance of virtual MC/unicast MACs paired with unicast IPs, `arp-mac-disparity` command + modes (multicast/unicast/multicast-igmp), static ARP + port binding (vs flooding), config persistence across reboot/failover, VRF support, and accurate reporting in show/platform tables.
- User confirmation points (TestLink list, then objectives) remain critical; explicit "tangentials omitted" notes keep traceability clean when requested.
- The workflow (Steps 1-4 + standardized outputs) generalizes well from Port features to IPv4 ARP, including edge cases with thin automation.

**State saved:**
- SESSION_STATE.md fully updated with activity, status (15 complete cases), and lessons.
- 15 refined cases contain final artefacts (T33233 dir present but incomplete).
- Documentation updates applied to README.md and OBJECTIVE_DRAFTING_PROCESS.md (see those files).
- User explicitly confirmed objectives for T33274 before final state save.

**Memory / tracking files touched:** SESSION_STATE.md (primary), README.md, OBJECTIVE_DRAFTING_PROCESS.md.

Ready to continue with high-confidence cases from later decision batches or other areas.

## Session Activity (continued - EPSR MIB)
- Selected next high-confidence case from dec_00: AWPTCM-T33274 (EPSR Mib, high confidence, primary AWP-3991).
- Primary TestLink very thin; broadened to EPSR MIB/SNMP family (AWP-1498 functional MIB, AWP-10347 SLP MIBs, trap cases AWP-4009/4010/1310, etc.).
- Tangential review: broader EPSR cases (~375 total) do not add MIB-specific artefacts.
- ATPyLib: limited (5704.1006.1 AT-EPSRv2 MIB unanalysed; 1334 general trap behavior).
- Completed T33274 using repeatable workflow. Created `refined-cases/AWPTCM-T33274/traceability.md` and `zephyr_payload.json`.
- Objectives focus on MIB support, variable consistency with CLI, EPSR-SLP flags, and correct trap bindings.

## Additional Lessons Learned
- When primary TestLink is extremely thin (e.g. single "atr-MIB supported"), the related family cases provide the detailed artefact expectations (variables, flags, trap bindings).
- For feature MIB cases, distinguish MIB-specific TestLink from general functional EPSR cases to keep scope tight.
- ART stubs without execution history (like the EPSR MIB case) must be noted as gaps; objectives and steps still derive from TestLink.

## Confirmation & Close for T33274
User confirmed the objectives and approach for AWPTCM-T33274. The artefacts (MIB support + OID/CLI consistency, EPSR-SLP flags, master/transit trap bindings with full fields, table/variable accuracy, handling of documented "unknown" states) were finalized and saved. This extends the workflow successfully to SNMP/MIB-focused manual test cases in the Switching area.

## Session Activity (2026-06-29) - T33275 Enhanced Recovery
- Selected next high-confidence case from dec_00: AWPTCM-T33275 (EPSR Enhanced Recovery, high confidence, primary AWP-145).
- Primary extremely thin (just "Confirm Enhanced Recovery mode works correctly").
- Broadened to full Enhanced Recovery family (AWP-4076/4077/4078 single/two/multi link failure, AWP-4083/4084 disabled-on-master/transit, AWP-4085 hotswap, AWP-4086 reconnect, AWP-4094/4095/4096 VCS scenarios, multi-domain independence cases).
- Strong direct ATPyLib coverage identified in 1334.3001.6–10 (executed Link Forward Request + Permission Link Forward protocol on transit/master, with and without priorities).
- 1340 cases for CR41421 traffic interruption timing (inferred only).
- Created initial `refined-cases/AWPTCM-T33275/traceability.md` (detailed candidates + mechanism) and draft `zephyr_payload.json`.
- Core mechanism synthesized: `enhancedrecovery enable` per domain + Link Forward Request/Permission handshake for optimized recovery, independent per-domain control, no-loop guarantee.
- Awaiting user review of detailed candidates + draft objectives.

## Session Activity (continued - next case T33279)
- Selected next high-confidence case from dec_00 after T33275: AWPTCM-T33279 (Switching STP - BPDU Forwarding, high confidence, primary AWP-9400).
- Zephyr case: "(136) Switching_STP - BPDU Forwarding", thin (empty objective).
- Primary: AWP-9400 "BPDU Forwarding behavior with spanning tree protocols" — key point is mutual exclusion: BPDU Forwarding is auto-disabled (and removed from config) when any STP protocol (stp/rstp/mstp) is enabled.
- Strong related family:
  - Command definition (AWP-9399 / 24878): `spanning-tree bpdu forward | discard | forward-untagged-vlan | forward-vlan`
  - VLAN/trunk behavior (AWP-9401/24883): no VLAN tags on forwarded BPDUs.
  - LAG interop (AWP-9407/24888): static channels treated as single port.
  - Other: 802.1x interop, older L2 BPDU forwarding notes.
- ATPyLib: Good coverage in STP conformance (2031 RSTP, 2032 STP, 2021 MSTP IxANVL suites for BPDU formats) and 1346 (BPDU tx under RSTP). Limited direct coverage of the "bpdu forward" mode itself (mostly TestLink driven).
- Created `refined-cases/AWPTCM-T33279/traceability.md` with detailed candidates and initial synthesis notes.
- Ready for user confirmation of Top Relevant TestLink list to proceed to objectives.

## Session Activity (continued - T33300 MAC Address Thrashing)
- Selected next high-confidence case from dec_01: AWPTCM-T33300 (Switching_LoopGuard - MAC Address Thrashing, high confidence, primary AWP-18040).
- Zephyr case: "(119) Switching_LoopGuard - MAC Address Thrashing", thin.
- Primary: AWP-18040 "MAC-Thrashing" — default enabled feature that detects rapid MAC movement (loops) and takes corrective action (e.g. on stack members).
- Top relevant family:
  - AWP-18059 (LDF related, overlapping steps)
  - AWP-26054: G.8032 interop (R-APS can trigger false thrashing; use high limits; test all actions)
  - AWP-7460: CLI show interface switchport correctly reports thrashing VLANs
  - AWP-7470/7471: thrash info on LAGs (should not show when inactive)
  - Action config: thrash-limit action learn-disable|link-down|port-disable|vlan-disable|none
- Direct ATPyLib: 1346.1001.95 "MAC thrashing - link-down" (executed, detects, applies link-down action + logs). Nearby loop protection cases with same actions.
- Created `refined-cases/AWPTCM-T33300/traceability.md` (detailed) and draft `zephyr_payload.json`.
- Draft objectives focus on detection, configurable actions, logging/show commands, G.8032/LAG/stack interop.
- Proceeding with the repeatable workflow.

## Confirmation & Close for T33279
User approved the objectives and approach for AWPTCM-T33279 (BPDU Forwarding). The artefacts (BPDU Forwarding command options under spanning-tree, automatic disable and removal from config when any STP/RSTP/MSTP protocol is enabled, no VLAN tags on forwarded BPDUs, LAGs treated as single logical port, interop notes) were finalized and saved. This extends the workflow successfully to the BPDU Forwarding feature in the Switching STP area.

## Confirmation & Close for T33300
User approved the objectives and approach for AWPTCM-T33300 (MAC Address Thrashing). The artefacts (default-enabled MAC thrashing detection on rapid MAC movement/loops, configurable actions including learn-disable/link-down/port-disable/vlan-disable/none with timeouts, logging + show interface switchport reporting, G.8032 interop with limit recommendations, LAG/stack support, related feature interop) were finalized and saved. This brings LoopGuard / MAC thrashing coverage into the refined set.

## Session Activity (continued - T33314 QoS DSCP)
- Selected next high-confidence case from dec_01: AWPTCM-T33314 (QoS - DSCP, high confidence, primary AWP-9109).
- Extremely strong match (0.942). Zephyr already has objective: "Verify that classified traffic class set DSCP as defined."
- Primary AWP-9109 and close siblings (AWP-9113 LAG, AWP-9088 DSCP specify) describe creating class-map + policy-map with "set dscp", apply via service-policy on switchport/static LAG, verify egress marking on matching/non-matching traffic, VCS master/backup/failover/reboot.
- ART: 1344_qos has several "QoS - DSCP premark" cases (on ports and aggregation/LAG, including bandwidth class colour), though mostly inferred in the selected runs. Related policy-map attach tests in 1331.
- Created `refined-cases/AWPTCM-T33314/traceability.md` and draft `zephyr_payload.json`.
- Note: This case had partial content already in Zephyr; we enriched with full family scope and traceability.
- User approved the objectives and approach for AWPTCM-T33314. The artefacts (class set DSCP on switchport and static LAG, matching/non-matching traffic, VCS master/backup/failover/reboot verification, policer counters) were finalized and saved. This extends the workflow to QoS DSCP classification and marking.

## Session Activity (continued - T33315 CoS Remarking)
- Selected next high-confidence case from dec_01 after T33314: AWPTCM-T33315 (QoS_PriorityRemarking - CoS Remarking, high confidence, primary AWP-20430).
- Primary: AWP-20430 "Remarking of CoS value using 'remark new-cos' command" — overwrite original CoS via policy-map class (remark new-cos X both), verify on egress capture.
- Top relevant: AWP-21845 (no CPU queue conflict with remark, supports internal new-cpu-queue), cos-queue map defaults (AWP-9067), default cos on switchport/LAG (AWP-9073/9075), class set cos (AWP-9108), maps after failover/reboot.
- ATPyLib: 1344_qos has executed case for modify COS / premark on trunk switchport (1344.4101.30 PASS), plus several inferred DSCP-premark-to-new-cos cases.
- Created `refined-cases/AWPTCM-T33315/traceability.md` (detailed) and draft `zephyr_payload.json`.
- Draft objectives cover remark new-cos overwrite, CPU queue safety, default cos, cos-queue maps, class set cos, VCS persistence.
- Awaiting user review.

## Session Activity (continued - T33317 policed-dscp DSCP Remarking)
- Selected next high-confidence case from dec_01 after T33315: AWPTCM-T33317 (QoS - PriorityRemarking - DSCP Remarking, high confidence, primary AWP-9126).
- Primary: AWP-9126 "policed-dscp map (remarking) configuration changes, show command, restart" — configure mls qos map policed-dscp for bandwidth-class to new-dscp/cos/queue/bandwidth-class; verify in running/startup after restart. (Note: not Broadcom.)
- Top relevant: AWP-9127 (revert with no command), AWP-9129/9130 (single-rate policer action policed-dscp-transmit on switchport and static LAG; verify egress remarking per map for green/yellow/red), plus twin-rate variants (AWP-17776/17777).
- ATPyLib: 1344_qos has many class-map + policer tests (mostly inferred), with some executed policer counter verification on trunk/switchport + LAG. No direct hits for "policed-dscp map" command itself.
- Created `refined-cases/AWPTCM-T33317/traceability.md` (detailed) and draft `zephyr_payload.json`.
- Draft objectives focus on map config persistence/revert, and remarking behavior when used in policer (single/twin-rate) on switchport/LAG.
- User approved the objectives and approach for AWPTCM-T33317. The artefacts (policed-dscp map config, persistence in running/startup, revert with no, remarking in single-rate/twin-rate policers on switchport/LAG) were finalized and saved. This extends the QoS policing remarking coverage.

## Note on EPSR MIB (T33274)
User confirmed/approved the EPSR MIB case (already finalized earlier).

## Session Activity (continued - T33323 DPMAP Dynamic Policy Changes)
- Selected next high-confidence case from dec_01 after T33317: AWPTCM-T33323 (QoS - Dynamic changes to policy contents, high confidence, primary AWP-20971).
- Primary: AWP-20971 "DPMAP: Dynamic change of attached policy-map" — change policy-map/class contents without detaching from interface; verify no error, show update, traffic works.
- Top relevant: AWP-20974 (change while traffic running, immediate effect), AWP-21187 (on LAG static/LACP), AWP-21053 (on VCS, including during disruption), AWP-20975 (when HW limit exceeded, rejects gracefully).
- ATPyLib: Limited direct; 1331 has policy re-attach after detach, storm policy attach, large QoS on LAG/VCS. 1344 has classmap+policy+policer. The "live change without detach" is mainly TestLink (DPMAP feature for 5.4.7+ on specific platforms).
- Created `refined-cases/AWPTCM-T33323/traceability.md` (detailed) and draft `zephyr_payload.json`.
- Draft objectives focus on dynamic modification without detach, live effect on traffic, LAG/VCS support, HW limit handling.
- User approved the objectives and approach for AWPTCM-T33323. The artefacts (dynamic policy-map change without detachment, live traffic effect, LAG/VCS support, HW limit graceful reject) were finalized and saved. This extends QoS dynamic policy management.

## Confirmation & Close for recent QoS cases
User approved T33315 (CoS Remarking), T33317 (policed-dscp), and T33323 (DPMAP). All QoS dynamic/remarking/policer artefacts finalized per approvals.

## Session Activity (continued - 2026-06-29) - T33351 802.1X Single Host
- Selected next high-confidence case from dec_01 after the QoS batch: AWPTCM-T33351 (Authentication&Security_IEEE 802.1X - Single host, high confidence, primary AWP-6809).
- Zephyr case currently has empty objective/precondition and one empty step.
- Primary + Top Relevant TestLink list documented (AWP-6809 primary; AWP-6807/6808/6810/6811 single-host matrix variants; AWP-6800 port-control single-host; AWP-6805 EAP-Logoff single; AWP-6825 802.1X+WEB parallel single-mode). List presented for review.
- User continued ("continue"), proceeding with approved list.
- ATPyLib review performed: strong hits in 1348_security (1348.1001.20 basic dot1x auth success, 1348.1001.33 dyn-vlan assignment, 1348.1001.11 config), 1341 (max clients 1341.1001.4975, dyn-vlan scale 1341.6001.5090), RADIUS selection (1348.27/28), plus CR cases for source-interface, concurrent logins, eap forward-vlan.
- Note: Explicit single-host enforcement and full Guest/DynVLAN combo matrix + logoff errors are primarily TestLink-driven (ART covers core success/assignment/config/scale but uses multi-supplicant or basic for many host-mode tests).
- Created `refined-cases/Authentication & Security (42)/AWPTCM-T33351/traceability.md` (full) and `zephyr_payload.json`.
- Objectives (artefacts) cover: successful single-host auth + VLAN assignment (RADIUS/Guest), pre-auth blocking, authorized state reporting, host-mode config acceptance, EAP-Logoff deauth, rejection of unsupported dyn-vlan combos, config persistence, scaling + dyn-vlan.
- testScript steps start with full traceability Note (TL family + ART list), followed by verification of auth success/VLAN, blocking, logoff, unsupported errors, show reporting, and config persistence.
- Artefacts finalized following the repeatable workflow.

## Confirmation & Close for T33351
Single-host 802.1X case completed with standardized artefacts. This extends coverage into the Authentication & Security area using the established process. The case emphasizes single-supplicant behavior, Guest/Dynamic VLAN assignment after success, deauth on logoff, and error handling for invalid host-mode + dyn-vlan combos. ART provides good basic auth + dyn-vlan + config coverage; detailed matrix from TestLink family.

**Files updated:**
- `refined-cases/Authentication & Security (42)/AWPTCM-T33351/traceability.md`
- `refined-cases/Authentication & Security (42)/AWPTCM-T33351/zephyr_payload.json`
- `SESSION_STATE.md` (this file)

Ready for next high-confidence case (e.g. remaining from dec_01/02 such as two-step auth T33369+ or others from later batches).

## Session Activity (2026-06-29 continued) - T33369 Two-Step (MAC 1st / 802.1X 2nd)
- Selected next high-confidence case from dec_02: AWPTCM-T33369 (TwoStepAuthentication - Mac-based 1st then 802.1x 2nd, high confidence, primary AWP-14782).
- Primary TestLink: Detailed end-to-end flow (invalid/correct MAC at 1st → HELD or Connecting for 802.1x 2nd; invalid/correct 2nd step → HELD or Authenticated).
- Top Relevant documented: AWP-14782 (primary), AWP-14773 (auth two-step enable + persist), AWP-14774 (show two-step supplicant), AWP-14776/14779 (success/fail logs for 802.1x steps), AWP-14879 (max supplicants MAC+802), AWP-14882 (repeat), AWP-6858 (simultaneous).
- Created `refined-cases/Authentication & Security (42)/AWPTCM-T33369/traceability.md` and `zephyr_payload.json`.
- ATPyLib: Direct hits in 6201.1033.1-5 (two-step MAC list allow/deny, MAC RADIUS variants, fail checks) + 1348 MAC+dot1x coexistence.
- Objectives focus on: ordered state transitions (Connecting after good 1st MAC, HELD on failures), final Authenticated, per-step logging, enable CLI + persistence, show command accuracy (firstMethod/secondMethod), max supplicants, repeat robustness.
- testScript includes full traceability Note + steps exercising enable, happy path sequencing + reporting, failure paths, logs, max, repeat.
- Artefacts finalized. Extends Authentication & Security coverage into explicit two-step ordered auth (MAC then 802.1X).

## Confirmation & Close for T33369
Two-step (1st MAC / 2nd 802.1X) case completed using repeatable workflow. Strong direct ART coverage for MAC-list two-step variants complements the detailed TestLink sequencing, state machine, and CLI/show artefacts. 

**Files updated:**
- `refined-cases/Authentication & Security (42)/AWPTCM-T33369/traceability.md`
- `refined-cases/Authentication & Security (42)/AWPTCM-T33369/zephyr_payload.json`
- `SESSION_STATE.md` (this file)

Next recommended: T33370 or T33371 (sibling two-step orders), T33392 (TFTP), or other remaining high-confidence cases from later decision batches.

## Session Activity (2026-06-29 continued) - T33370 Two-Step (MAC 1st / WEB 2nd)
- Selected next in two-step family from dec_02: AWPTCM-T33370 (TwoStepAuthentication - Mac-based 1st then Web Auth 2nd, high confidence, primary AWP-14783).
- Primary TestLink: Detailed end-to-end flow for 1st MAC / 2nd WEB (invalid/correct MAC → HELD or Connecting for WEB; invalid WEB within/beyond max-auth-fail → Reauthenticating or HELD; correct WEB → Authenticated). Includes WEB-specific log formatting with IP.
- Top Relevant documented: AWP-14783 (primary), AWP-14773 (enable + persist, shared), AWP-14774 (show two-step supplicant), AWP-14777/14780 (WEB success/fail logs as 2nd), AWP-14878 (max for MAC/WEB), AWP-14881 (repeat for MAC/WEB), AWP-15977 (auth-mac password for MAC+WEB two-step), AWP-15819 (RADIUS 2-step).
- Created `refined-cases/Authentication & Security (42)/AWPTCM-T33370/traceability.md` and `zephyr_payload.json`.
- ATPyLib: Direct hits in 6201.1033.1-5 (two-step MAC list allow/deny, MAC RADIUS, list+external RADIUS, MAC+web fail checks) + 1348 web auth paths (success/fail, guest-vlan on fail).
- Objectives focus on: ordered states (Connecting after good MAC 1st, Reauthenticating on partial WEB fail, HELD on full), final Authenticated, per-step WEB logs (with IP), enable/show (first=mac/second=web), auth-mac password, max supplicants, repeat robustness, RADIUS/MAC list in context.
- testScript includes full traceability Note + steps for enable/persist, happy path sequencing + show, failure paths (with max-auth-fail), logs, auth-mac password, max, repeat, list/RADIUS.
- Artefacts finalized. Continues two-step series with WEB as second method.

## Confirmation & Close for T33370
Two-step (1st MAC / 2nd WEB) case completed. Similar structure to sibling T33369 but with WEB second-step specifics (Reauthenticating state, max-auth-fail handling, IP in logs, auth-mac password). ART 6201 covers MAC-first two-step well (including web fail); web auth details supplemented from 1348.

**Files updated:**
- `refined-cases/Authentication & Security (42)/AWPTCM-T33370/traceability.md`
- `refined-cases/Authentication & Security (42)/AWPTCM-T33370/zephyr_payload.json`
- `SESSION_STATE.md` (this file)

Next recommended: T33371 (802.1x 1st / WEB 2nd), T33392 (TFTP), or continue with other high-conf from dec_02/dec_03 etc.

## Session Activity (2026-06-29 continued) - T33371 Two-Step (802.1x 1st / WEB 2nd)
- Selected next sibling from dec_02: AWPTCM-T33371 (TwoStepAuthentication - 802.1x 1st then Web Auth 2nd, high confidence, primary AWP-14784).
- Primary TestLink: Detailed flow for 1st 802.1x / 2nd WEB (invalid/correct 802.1x at 1st → HELD or Connecting for WEB; invalid WEB → Reauthenticating or HELD; correct WEB → Authenticated). Explicit test that WEB page blocked ("please retry later") at 1st step. Also RADIUS notes.
- Top Relevant documented: AWP-14784 (primary), AWP-14773 (enable + persist), AWP-14774 (show), AWP-14776/14779 (802.1x logs as 1st), AWP-14880 (max for 802/WEB), AWP-15819 (RADIUS 2-step), AWP-14777 (WEB log as 2nd).
- Created `refined-cases/Authentication & Security (42)/AWPTCM-T33371/traceability.md` and `zephyr_payload.json`.
- ATPyLib: 1348.1001.20 (802.1x auth), 1348.1001.11 (config), 1348.3001.* (web auth success/fail/guest-vlan), 6201.1033.* (two-step variants + web fail checks), RADIUS selection.
- Objectives focus on: 802.1x first success to WEB second, HELD on 802.1x fail, Reauthenticating/HELD on WEB fails, blocked WEB at first step, logs, enable/show (first=802.1x/second=web), max supplicants for order, RADIUS in 2-step.
- testScript: full Note + enable/persist, happy sequencing + show, failures + block test, logs, max, RADIUS.
- Artefacts finalized. Completes the main two-step auth order variants in this batch.

## Confirmation & Close for T33371
Two-step (1st 802.1x / 2nd WEB) case completed. This order emphasizes 802.1x as first method (with blocked early WEB access) and WEB second (with Reauthenticating state). ART provides solid standalone 802.1x and web coverage; ordered two-step and block from TL. Completes the high-conf two-step siblings from dec_02.

**Files updated:**
- `refined-cases/Authentication & Security (42)/AWPTCM-T33371/traceability.md`
- `refined-cases/Authentication & Security (42)/AWPTCM-T33371/zephyr_payload.json`
- `SESSION_STATE.md` (this file)

Next recommended: T33392 (TFTP high conf), or other highs from dec_03 (e.g. T33404), dec_04 (PoE), etc. Or any specific from later batches.

## Session Activity (2026-06-29 continued) - T33392 TFTP different destination filenames
- Selected next high-confidence case from dec_02: AWPTCM-T33392 (Management - Loading Files using TFTP, high confidence, primary AWP-5488 exact match).
- Zephyr already had initial objective/steps focused on different dest filenames for up/download; we are enriching per workflow.
- Primary TestLink AWP-5488: TFTP upload/download using different destination filenames. Success, files correctly renamed/copied.
- Top Relevant: AWP-5488 (primary), AWP-5497 (AT-TFTP compat), AWP-5478 (upload), AWP-5485 (different storage types), AWP-5490 (filename does not exist), AWP-5489 (medium full).
- Created `refined-cases/Management (xx)/AWPTCM-T33392/traceability.md` and `zephyr_payload.json`.
- ATPyLib: 1345.1001.1 (tftp copy negative tests: fail cleanly on unreachable/non-existent), 1331 (copy tftp script failures, backupmember tftp issues).
- Objectives enrich: successful up/download with different dest filenames (copy/rename), AT-TFTP compat, different storage, graceful handling for non-existent file and full medium.
- testScript: Note with TL+ART + steps for download/upload diff name, compat, storage, error cases.
- Artefacts finalized. First case in Management area.

## Confirmation & Close for T33392
TFTP different destination filenames case completed. Zephyr had partial content; enriched with full family for filename handling, storage, compat, errors. ART strong on negatives; positives from TL. Moves into Management folder.

**Files updated:**
- `refined-cases/Management (xx)/AWPTCM-T33392/traceability.md`
- `refined-cases/Management (xx)/AWPTCM-T33392/zephyr_payload.json`
- `SESSION_STATE.md` (this file)

Next recommended: High-conf from dec_03 (e.g. T33404 "Zephyr says run ART 1337_cli_walk"), dec_04 PoE cases (T37859+), or T33392 siblings if any, or user-specified.

## Session Activity (2026-06-29 continued) - T33404 CLI (Run ART 1337_cli_walk)
- Selected next from dec_03: AWPTCM-T33404 (Management Operation - CLI, high confidence, m=null because "Zephyr: run ART testsuite 1337_cli_walk - automated, no TL equiv").
- Zephyr: OBJ: Run the ART testsuite 1337_cli_walk ||
- Primary decision notes no TL equivalent; high due to explicit automation intent.
- Top Relevant TL: Weak/low-score CLI cases from batch (AWP-1133 NTP CLI help, AWP-4508/4500 PoE CLI errors/help, AWP-8202 device mgmt show, AWP-5477 TFTP CLI, AWP-3469 PIM CLI, etc.). No strong primary.
- Created `refined-cases/Management (xx)/AWPTCM-T33404/traceability.md` and `zephyr_payload.json`.
- ATPyLib: Direct 1337 suite (1337.1.1 SHOW walk, 1337.1.2 CLEAR, 1337.1.3 NO + broad CLI robustness soak tests).
- Objectives: Document intent to run 1337_cli_walk for exhaustive CLI coverage (SHOW accurate/useful, CLEAR/NO work, no crashes, config restorable). TL as general CLI context.
- testScript: Note referencing ART 1337 + steps to run the walk suite.
- Artefacts finalized. Special case focused on ART CLI walk coverage in Management area.

## Confirmation & Close for T33404
CLI case (run 1337_cli_walk) completed. Special automated case with no strong TL primary. Enriched to capture the purpose: broad CLI robustness via the walk (show/clear/no). ART 1337 is the direct match. Continues Management grouping.

**Files updated:**
- `refined-cases/Management (xx)/AWPTCM-T33404/traceability.md`
- `refined-cases/Management (xx)/AWPTCM-T33404/zephyr_payload.json`
- `SESSION_STATE.md` (this file)

Next recommended: Continue with dec_04 high-conf PoE/LED cases (T37859 POE LED Fault, T37860 POE LED-POE, T37861 POE lldp, T37865 HANP, T37869 System LED, T38767 bootloader factory), or other from later decisions. Or user choice.

## Session Activity (2026-06-29 continued) - T37859 POE LED-Fault-OverDrawByUserBudget
- Selected next high-confidence case from dec_04: AWPTCM-T37859 (POE LED-Fault-OverDrawByUserBudget, high confidence, primary AWP-4596 exact).
- Zephyr in Sanity Check: Functional LED Operation for over drawing power based on User budget.
- Primary TestLink AWP-4596: Overdraw user budget => Fault indication on port (LED behavior per device spec).
- Top Relevant: AWP-4596 (primary user budget overdraw fault), AWP-4595 (class overdraw), AWP-4594 (nominal POE), AWP-4582 (allocated power on PD fault), AWP-4581 (allocated power recalc on PD stop draw).
- Created `refined-cases/Sanity Check (15)/AWPTCM-T37859/traceability.md` and `zephyr_payload.json`.
- ATPyLib: 1358 PoE (delivery, status reporting, priorities, global/port disable, HANP); limited direct LED fault coverage.
- Objectives: Port indicates fault when over-drawing user budget (check device spec for LED/state); contrasts with nominal and class; allocated power exclusion on fault and recalc on clear/stop.
- testScript: Note with TL+ART (platform LED variation noted) + steps for overdraw, verify fault indication per spec, nominal contrast, power updates.
- Artefacts refined per feedback: actual light performance varies platform-to-platform; "Check device spec for PD Fault operation".
- Artefacts finalized. First PoE LED case; placed under Sanity Check group.

## Confirmation & Close for T37859
POE LED fault overdraw by user budget case completed (with refinement). Strong TL family for fault/power budget behavior, but LED details qualified as platform-specific. User feedback incorporated: "The actual light performance varies platform-to-platform. 'Check device spec for PD Fault operation'". ART covers general PoE power/status. Starts PoE/LED coverage under Sanity Check.

**Files updated:**
- `refined-cases/Sanity Check (15)/AWPTCM-T37859/traceability.md`
- `refined-cases/Sanity Check (15)/AWPTCM-T37859/zephyr_payload.json`
- `SESSION_STATE.md` (this file)

Next recommended: Remaining dec_04 PoE/LED (T37860 etc.), T38767 bootloader, or other highs. Or user-specified.

## Session Activity (2026-06-29 continued) - T37860 POE LED-POE
- Selected next high-confidence case from dec_04: AWPTCM-T37860 (POE LED-POE, high confidence, primary AWP-4594 exact).
- Zephyr in Sanity Check: Functional LED Operation for nominal POE port connection (steady green LED).
- Primary TestLink AWP-4594: Normal PD operation represented with steady green LED.
- Top Relevant: AWP-4594 (primary nominal green), AWP-4593 (NonPOE), AWP-4592 (NoConnections), cross-refs to T37859 faults (with platform variation note).
- Created `refined-cases/Sanity Check (15)/AWPTCM-T37860/traceability.md` and `zephyr_payload.json`.
- ATPyLib: 1358 PoE (delivery, status reporting, priorities, HANP, etc.); limited on specific LED states.
- Objectives: Steady green for nominal POE connection (per device spec), no LED for no connection, no PoE LED for non-POE; contrasts with faults.
- testScript: Note with TL+ART + steps for nominal PD, no connection, non-POE, cross-check faults.
- Artefacts finalized. Continues PoE LED family (nominal following fault case). Platform spec note carried over.

## Confirmation & Close for T37860
POE LED-POE (nominal) case completed. Complements the fault case (T37859). LED states from TL family (green for nominal PoE), qualified for platform variation. ART covers power side. PoE/LED coverage progressing under Sanity Check.

**Files updated:**
- `refined-cases/Sanity Check (15)/AWPTCM-T37860/traceability.md`
- `refined-cases/Sanity Check (15)/AWPTCM-T37860/zephyr_payload.json`
- `SESSION_STATE.md` (this file)

Next recommended: Next in dec_04 (T37861 lldp max power, T37865 HANP, T37869 System LED, T38767 bootloader), or other pending highs. Or user-specified.

## Session Activity (2026-06-29 continued) - T37861 POE - lldp max power and cli power
- Selected next high-confidence case from dec_04: AWPTCM-T37861 (POE - lldp max power and cli power, high confidence, primary AWP-4577 exact).
- Zephyr in Sanity Check: lldp max power is overridden by cli setting for interface max power.
- Primary TestLink AWP-4577: LLDP max power values; CLI overrides, reverts when removed.
- Top Relevant: AWP-4577 (primary), AWP-4576 (LLDP recognised), AWP-4575 (CLI max power), AWP-14385 (change max power), AWP-5657 (Extended Power TLV).
- Created `refined-cases/Sanity Check (15)/AWPTCM-T37861/traceability.md` and `zephyr_payload.json`.
- ATPyLib: 1358 (PoE status reporting, priorities, disable, HANP); LLDP TLV suites (e.g. 1332); limited on exact CLI/LLDP override.
- Objectives: LLDP max power recognised/overides classification; CLI overrides LLDP; revert when CLI removed; status reflects effective max.
- testScript: Note with TL+ART + steps for LLDP values, CLI override, revert, status check.
- Artefacts finalized. Continues PoE power management in Sanity Check.

## Confirmation & Close for T37861
POE LLDP max power and CLI power case completed. Focus on precedence between LLDP and CLI for max power. TL family strong for the override/revert behavior; ART covers general PoE status and LLDP TLVs.

**Files updated:**
- `refined-cases/Sanity Check (15)/AWPTCM-T37861/traceability.md`
- `refined-cases/Sanity Check (15)/AWPTCM-T37861/zephyr_payload.json`
- `SESSION_STATE.md` (this file)

Next recommended: T37865 (HANP), T37869 (System LED), T38767 (bootloader), or specify.

## Session Activity (2026-06-29 continued) - T37865 HANP-POE no power loss on restart
- Selected next high-confidence case from dec_04: AWPTCM-T37865 (HANP-POE Powered Device does not lose Power during a restart, high confidence, primary AWP-24553 exact).
- Zephyr in Sanity Check: empty objective; steps for enable HANP, attach PDs, check negotiated time, warm reboot, verify no power loss + log + time match.
- Primary TestLink AWP-24553: Enable HANP, attach PDs, check show power-inline Last negotiated time, warm reboot, confirm no power loss, log HANP active, times unchanged.
- Top Relevant: AWP-24553 (primary warm restart), AWP-24560 (soft restart no power loss), AWP-24554 (CLI HANP show), AWP-24552 (per-port), AWP-24551 (global).
- Created `refined-cases/Sanity Check (15)/AWPTCM-T37865/traceability.md` and `zephyr_payload.json`.
- ATPyLib: 1358.1001.10 (HANP after PoE restore), 1358.1001.7 (HANP behaviour), 1358.1001.56299 (PoE restore), general 1358 PoE persistence over reboot.
- Objectives: With HANP, PoE PDs retain power on warm restart; Last negotiated time preserved; HANP logged; CLI show for config/negotiated info.
- testScript: Note with TL+ART + steps for enable/attach/check, reboot/verify, show commands.
- Artefacts finalized. Continues PoE HANP coverage in Sanity Check (focus on restart power retention).

## Confirmation & Close for T37865
HANP PoE restart case completed. Strong TL for warm restart no power loss and negotiated time preservation. ART covers PoE restore/HANP after stop and general persistence. Zephyr was thin (empty objective); enriched from TL family. PoE/High-Availability progressing.

**Files updated:**
- `refined-cases/Sanity Check (15)/AWPTCM-T37865/traceability.md`
- `refined-cases/Sanity Check (15)/AWPTCM-T37865/zephyr_payload.json`
- `SESSION_STATE.md` (this file)

Next recommended: T37869 (System LED), T38767 (bootloader), or other highs from later decisions (e.g. dec_05+). Or user-specified.

## Session Activity (2026-06-29 continued) - T37869 System LED - fan stop
- Selected next high-confidence case from dec_04: AWPTCM-T37869 (System LED - fan stop, high confidence, primary AWP-11637 exact).
- Zephyr in Sanity Check: To check if LED is flashing red colour - 1 flash per period (details may vary on some platforms if applicable).
- Primary TestLink AWP-11637: Cause unit fan to stop (XEM/PSU) => Flashing red 1/period (on some platforms if applicable).
- Top Relevant: AWP-11637 (primary fan stop), AWP-10432 (fan stop), AWP-11638 (faulty XEM 4 flashes), AWP-11640 (concurrent sequences), AWP-17692 (system failure LED).
- Created `refined-cases/Sanity Check (15)/AWPTCM-T37869/traceability.md` and `zephyr_payload.json`.
- ATPyLib: Limited for exact LED flash patterns; 1358/5700 platform environment monitoring (fan/temp/status), system health.
- Objectives: Flashing red 1/period for fan stop (on some platforms if applicable); patterns distinguish from XEM (4 flashes), temp, concurrent.
- testScript: Note with TL+ART + steps to cause fan stop, verify LED (1 flash), distinguish patterns (details if applicable on some platforms).
- Artefacts finalized. System LED fault coverage in Sanity Check.

## Confirmation & Close for T37869
System LED fan stop case completed (refined). TL family for environment fault LED patterns (1 flash red for fan stop). Removed platform-specific details per feedback; LED indication may vary on some platforms if applicable. ART covers functional monitoring but LED specifics from TL. Continues Sanity Check environment/system LED series.

**Files updated:**
- `refined-cases/Sanity Check (15)/AWPTCM-T37869/traceability.md`
- `refined-cases/Sanity Check (15)/AWPTCM-T37869/zephyr_payload.json`
- `SESSION_STATE.md` (this file)

Next recommended: T38767 (bootloader factory settings), or other highs from dec_05+ (e.g. more PoE, IPv6, etc.). Or user-specified.

## Session Activity (2026-06-29 continued) - T38767 Boot Menu - Restore Factory Settings
- Selected next high-confidence case from dec_04: AWPTCM-T38767 (Boot Menu - Restore Factory Settings, high confidence, primary AWP-2719).
- Zephyr in Bootloader: empty objective/steps (thin case).
- Primary TestLink AWP-2719: Bootloader menu option 7 restores factory settings (tftp default setup, restore, settings reset to default).
- Top Relevant: AWP-2719 (primary), AWP-2722 (tftp reset), AWP-2723 (release boot reset), AWP-2720 (developer mode), AWP-2721 (console speed).
- Created `refined-cases/Bootloader (xx)/AWPTCM-T38767/traceability.md` and `zephyr_payload.json`.
- ATPyLib: 5700.1002.7 (bootloader version), 5700.1003.5 (ROM checksum) + related platform bootloader/diagnostics.
- Objectives: Menu option 7 restores defaults; specific resets for tftp, release, developer, console; device reboots with defaults.
- testScript: Note with TL+ART + steps for setup, enter menu, select 7, verify restore.
- Artefacts finalized. First bootloader case.

## Confirmation & Close for T38767
Bootloader restore factory settings case completed. TL family for menu option 7 and specific reset behaviors. ART covers version/checksum but restore process from TL. Zephyr thin; enriched accordingly. Bootloader coverage started.

**Files updated:**
- `refined-cases/Bootloader (xx)/AWPTCM-T38767/traceability.md`
- `refined-cases/Bootloader (xx)/AWPTCM-T38767/zephyr_payload.json`
- `SESSION_STATE.md` (this file)

Next recommended: Highs from dec_05+ or specify (e.g. T438xx PoE, IPv6, etc.). Or user-specified.

## Session Activity (2026-06-29 continued) - T43849 IPv4_ARP - Local Proxy ARP: Functionality
- Selected next high-confidence case from dec_05: AWPTCM-T43849 (IPv4_ARP - Local Proxy ARP: Functionality, high confidence, primary AWP-4357 exact).
- Zephyr in IPv4: Command "ip local-proxy-arp" functionality test.
- Primary TestLink AWP-4357: Configure local-proxy-arp on DUT, ping remote host on same subnet from BackupSW; expect ARP uses DUT MAC (one-armed router).
- Top Relevant: AWP-4357 (primary), AWP-4356 (command), AWP-4358 (off by default), AWP-4355 (standard proxy ARP), AWP-4370/4371 (LAGs).
- Created `refined-cases/IPv4 ARP (xx)/AWPTCM-T43849/traceability.md` and `zephyr_payload.json`.
- ATPyLib: 6201.1008.1/2 (Proxy ARP behavior + static IP), 6201.1031.1 (unlearned ARP), 1351 (gratuitous ARP).
- Objectives: DUT responds to ARPs for other hosts on interface using DUT MAC; works over LAGs; off by default.
- testScript: Note with TL+ART + steps for config, ping/ARP check, command, LAG variants.
- Artefacts finalized. IPv4 ARP local proxy coverage.

## Confirmation & Close for T43849
Local Proxy ARP case completed. TL primary for one-armed router behavior; related command/default/LAG. ART covers general proxy ARP. Zephyr had objective; enriched with full family. IPv4 ARP progressing under new group.

**Files updated:**
- `refined-cases/IPv4 ARP (xx)/AWPTCM-T43849/traceability.md`
- `refined-cases/IPv4 ARP (xx)/AWPTCM-T43849/zephyr_payload.json`
- `SESSION_STATE.md` (this file)

Next recommended: T43851 (DHCP server ARP probe), or other dec_05+ highs. Or user-specified.

## Session Activity (2026-06-29 continued) - T43851 IPv4_DHCPServer - DHCP ARP Probe
- Selected next high-confidence case from dec_05: AWPTCM-T43851 (IPv4_DHCPServer - DHCP ARP Probe, high confidence, primary AWP-3596 exact).
- Zephyr in IPv4: Test for enable and disable probing in DHCP Server.
- Primary TestLink AWP-3596: Test enable/disable probing for DHCP pool. probe enable (default), no probe enable.
- Top Relevant: AWP-3596 (primary), AWP-3594 (probe using ARP), AWP-3550 (CLI commands), AWP-3595 (number of packets), AWP-3738 (wireless).
- Created `refined-cases/IPv4 DHCP (xx)/AWPTCM-T43851/traceability.md` and `zephyr_payload.json`.
- ATPyLib: Limited direct; general DHCP in 1331/1357/1399, ARP in 1351/6201.
- Objectives: Probing enabled by default, configurable per pool, ARP probe type, configurable packets/timeout, show support.
- testScript: Note with TL+ART + steps for enable/disable, ARP type, packets, client test.
- Artefacts finalized. DHCP probing coverage.

## Confirmation & Close for T43851
DHCP ARP Probe case completed. TL for enable/disable and config of probing. ART general DHCP/ARP. Zephyr enriched from family. IPv4 DHCP progressing.

**Files updated:**
- `refined-cases/IPv4 DHCP (xx)/AWPTCM-T43851/traceability.md`
- `refined-cases/IPv4 DHCP (xx)/AWPTCM-T43851/zephyr_payload.json`
- `SESSION_STATE.md` (this file)

Next recommended: T43853 or T43854 from dec_05, or specify. Or other pending highs.

## Session Activity (2026-06-29 continued) - T43853 IPv4_DHCPServer - DHCP 120-day lease
- Selected next high-confidence case from dec_05: AWPTCM-T43853 (IPv4_DHCPServer - DHCP 120-day lease, high confidence, primary AWP-3578).
- Zephyr in IPv4: empty objective (thin case).
- Primary TestLink AWP-3578: Configure DHCP server pool with 120 day lease (lease 120 0 0), client obtains 120 day lease.
- Top Relevant: AWP-3578 (primary), AWP-3579 (client obtain), AWP-9771 (snooping lease log), AWP-15615 (lease renewal), AWP-2475 (lease time).
- Created `refined-cases/IPv4 DHCP (xx)/AWPTCM-T43853/traceability.md` and `zephyr_payload.json`.
- ATPyLib: 1331.1001.54492 (infinite lease crash), 1357/1399 (DHCP server lease/binding), 1333 (snooping lease).
- Objectives: Server offers 120 day lease; client obtains 120 day lease; config in running; lease ops logged.
- testScript: Note with TL+ART + steps for server config 120d, client obtain/verify, logs.
- Artefacts finalized. DHCP long lease coverage.

## Confirmation & Close for T43853
DHCP 120-day lease case completed. TL for server config and client obtain of 120d lease. ART general lease/binding. Zephyr thin; enriched from family. IPv4 DHCP progressing.

**Files updated:**
- `refined-cases/IPv4 DHCP (xx)/AWPTCM-T43853/traceability.md`
- `refined-cases/IPv4 DHCP (xx)/AWPTCM-T43853/zephyr_payload.json`
- `SESSION_STATE.md` (this file)

Next recommended: T43854 (DNS Relay) or T43855 (IPv4 static routes) from dec_05, or specify. Or other pending highs.

## Session Activity (2026-06-29 continued) - T43854 IPv4_DHCPClient - DNS Relay
- Selected next high-confidence case from dec_05: AWPTCM-T43854 (IPv4_DHCPClient - DNS Relay, high confidence, primary AWP-3360 exact).
- Zephyr in IPv4: DNS Relay - enable/disable ... (with detailed steps for configure/enable/confirm).
- Primary TestLink AWP-3360: Configure name-servers, enable dns relay, confirm forwarding, disable, confirm stops, cycle ~5 times.
- Top Relevant: AWP-3360 (primary), AWP-3359 (name resolver support), AWP-3194 (show commands), AWP-3197 (debug), AWP-3365 (source interface).
- Created `refined-cases/IPv4 DHCP (xx)/AWPTCM-T43854/traceability.md` and `zephyr_payload.json`.
- ATPyLib: 1346.1001.87/1346.1010.9 (DNS forwarding config/CLI), related in 13xx/20xx.
- Objectives: Enable forwarding when configured, disable stops, cycle works, name resolvers supported, show accurate.
- testScript: Note with TL+ART + steps for configure/enable/confirm, disable, cycle, verify resolver/show.
- Artefacts finalized. DNS relay coverage.

## Confirmation & Close for T43854
DNS Relay case completed. TL for enable/disable and forwarding. ART covers forwarding config/CLI. Zephyr enriched from family. IPv4 DHCPClient progressing.

**Files updated:**
- `refined-cases/IPv4 DHCP (xx)/AWPTCM-T43854/traceability.md`
- `refined-cases/IPv4 DHCP (xx)/AWPTCM-T43854/zephyr_payload.json`
- `SESSION_STATE.md` (this file)

Next recommended: T43855 (IPv4 static routes) or T43858 (BGPv4) from dec_05, or specify. Or other pending highs.

## Session Activity (2026-06-29 continued) - T43855 IPv4_UnicastRouting - IPv4 Static
- Selected next high-confidence case from dec_05: AWPTCM-T43855 (IPv4_UnicastRouting - IPv4 Static, high confidence, primary AWP-24184).
- Zephyr in IPv4: Check IPv4 static routes will be supported (thin).
- Primary TestLink AWP-24184: Check IPv4 static routes will be supported (from ATMF containers).
- Top Relevant: AWP-24184 (primary), AWP-7681 (Unicast Traffic), AWP-25826 (ECMP), AWP-20439 (Field Issue multicast static).
- Created `refined-cases/IPv4 Static (xx)/AWPTCM-T43855/traceability.md` and `zephyr_payload.json`.
- ATPyLib: 1330.4001.1/7 (static routes power_cycle/rolling_reboot), related in 1335/1355 for IPv4 static/ECMP.
- Objectives: IPv4 static routes supported/configurable/visible; forward unicast traffic; converge in failover/reboot.
- testScript: Note with TL+ART + steps for config, verify show/traffic, failover tests.
- Artefacts finalized. IPv4 static routes coverage.

## Confirmation & Close for T43855
IPv4 Static routes case completed. TL for support (ATMF context) and unicast. ART covers static in power/rolling reboot. Zephyr thin; enriched from family. IPv4 Unicast progressing.

**Files updated:**
- `refined-cases/IPv4 Static (xx)/AWPTCM-T43855/traceability.md`
- `refined-cases/IPv4 Static (xx)/AWPTCM-T43855/zephyr_payload.json`
- `SESSION_STATE.md` (this file)

Next recommended: T43858 (BGPv4) or T43859 (VRF-Lite traceroute) from dec_05, or specify. Or other pending highs.

## Session Activity (2026-06-29 continued) - T43858 IPv4_UnicastRouting - BGPv4
- Selected next high-confidence case from dec_05: AWPTCM-T43858 (IPv4_UnicastRouting - BGPv4, high confidence, primary AWP-7650).
- Zephyr in IPv4: Check and verify BGPv4 for correct status and functionality (unicast traffic).
- Primary TestLink AWP-7650: BGPv4 - Unicast Traffic, run background unicast, traffic passes at line rate.
- Top Relevant: AWP-7650 (primary), AWP-14120 (BGP4+ Unicast), AWP-7681 (Static Unicast), AWP-7775 (VCS Unicast).
- Created `refined-cases/IPv4 BGP (xx)/AWPTCM-T43858/traceability.md` and `zephyr_payload.json`.
- ATPyLib: 2001.1.1/1.2/1.3 (BGP connection/Established/routes), 2036.1.1/1.2/1.3 (similar), 2002 (attributes/forwarding).
- Objectives: BGPv4 establishes, learns routes, unicast traffic at line rate.
- testScript: Note with TL+ART + steps for traffic, verify Established, routes, forwarding.
- Artefacts finalized. BGPv4 coverage.

## Confirmation & Close for T43858
BGPv4 case completed. TL for unicast traffic verification. ART covers BGP protocol basics. Zephyr thin; enriched from family. IPv4 BGP progressing.

**Files updated:**
- `refined-cases/IPv4 BGP (xx)/AWPTCM-T43858/traceability.md`
- `refined-cases/IPv4 BGP (xx)/AWPTCM-T43858/zephyr_payload.json`
- `SESSION_STATE.md` (this file)

Next recommended: T43859 (VRF-Lite traceroute) from dec_05, or specify. Or other pending highs.

## Session Activity (2026-06-29 continued) - T43859 IPv4_UnicastRouting - VRF-Lite
- Selected next high-confidence case from dec_05: AWPTCM-T43859 (IPv4_UnicastRouting - VRF-Lite, high confidence, primary AWP-4286 exact).
- Zephyr in IPv4: VRF-Lite support traceroute operation.
- Primary TestLink AWP-4286: VRF Lite Traceroute - from VRF instance run "traceroute vrf <name>", from global run "traceroute", expect correct hops from source VRF.
- Top Relevant: AWP-4286 (primary), AWP-10990 (VRF_Lite and Stack Management Vlan), AWP-11451 (VRF-Lite - Unicast Traffic), AWP-4144 (VRF Lite Telnet command).
- Created `refined-cases/IPv4 VRF (xx)/AWPTCM-T43859/traceability.md` and `zephyr_payload.json`.
- ATPyLib: 1330.7001.1 (VRF-lite IPv4_unicast power_cycle), 1346.1013.1 (VRF-Lite isolation).
- Objectives: From VRF, traceroute vrf shows correct hops; from global, standard traceroute works; VRF isolation.
- testScript: Note with TL+ART + steps for VRF traceroute, global traceroute, verify isolation.
- Artefacts finalized. VRF-Lite traceroute coverage.

## Confirmation & Close for T43859
VRF-Lite traceroute case completed. TL primary for VRF-specific traceroute support. ART covers VRF isolation and forwarding. Zephyr enriched from family. IPv4 VRF progressing.

**Files updated:**
- `refined-cases/IPv4 VRF (xx)/AWPTCM-T43859/traceability.md`
- `refined-cases/IPv4 VRF (xx)/AWPTCM-T43859/zephyr_payload.json`
- `SESSION_STATE.md` (this file)

Next recommended: T43860 (IP Route Filter) or other from dec_06+, or specify. Or other pending highs.

## Session Wrap-Up (2026-06-29)

**Session Summary:**
This extended session (spanning multiple days) continued the objective drafting workflow on high-confidence manual test cases, focusing on IPv4 areas (ARP, DHCP, Static Routes, BGPv4, VRF-Lite) and prior PoE/LED, Bootloader, Auth, etc. Approximately 10+ additional cases processed in this phase (bringing total refined to ~30+ across groups).

**Key Cases in this Session Close:**
- T43854: DNS Relay enable/disable (forwarding, cycle, show commands).
- T43853: DHCP 120-day lease (server config, client obtain, logging).
- T43855: IPv4 Static routes (config, unicast traffic, failover convergence).
- T43858: BGPv4 unicast (peering, route learning, line-rate traffic).
- T43859: VRF-Lite traceroute (VRF-specific vs global, isolation).

**Lessons Learned (this session & cumulative):**
- **Platform-agnostic objectives:** Explicitly avoid or qualify platform-specific LED/behavior details (e.g., "on some platforms if applicable" or "per device spec"). User feedback reinforces keeping language reusable.
- **Thin TL / automation-driven cases:** When primary TL is minimal (e.g., "check supported" or "run ART"), focus on feature-family coverage and ART validation (e.g., 1330 for static routes, 2001/2036 for BGP). Document gaps clearly.
- **VRF and isolation features:** Traceroute and traffic tests are key differentiators for VRF-Lite; emphasize distinction between VRF instance and global VRF in objectives.
- **Consistent grouping:** Use descriptive subgroups like "IPv4 ARP (xx)/", "IPv4 DHCP (xx)/", "IPv4 Static (xx)/", "IPv4 VRF (xx)/", "IPv4 BGP (xx)/" for organization within larger areas.
- **User-review loop:** Continue explicit pauses for TL list approval before synthesizing; this catches scope issues early.
- **ART vs TL balance:** ART often provides resilience/failover coverage (power_cycle, rolling_reboot, isolation); TL provides the specific feature verification steps. Note "limited direct" when ART is thin.
- **Zephyr payload structure:** Always preserve/enrich existing objectives where present; use flexible bullet count (3-10 typical); first testScript step as traceability note with full TL+ART list.
- **Documentation hygiene:** Keep SESSION_STATE.md as living memory; sync counts/lessons to OBJECTIVE_DRAFTING_PROCESS.md and README.md periodically.

**Total Processed (approximate as of end of session):**
- ~30+ cases fully refined (Port ~7, IPv4 variants ~10, PoE/LED ~5, Auth ~4, Management ~2, Bootloader ~1, Switching ~4, etc.).
- See refined-cases/ subdirs and individual traceability.md for exact lists.
- Many more high-conf cases remain in dec_05+ and beyond.

**State Saved:**
- All artefacts for T43859 finalized and committed to structure.
- SESSION_STATE.md updated with activity, close-out, lessons, and next recommendations.
- No pending uncommitted changes; ready for future sessions or upload prep.

**Memory / Documentation Updated:**
- SESSION_STATE.md (primary session memory).
- Relevant project files (see below).

**Recommended Next Actions:**
- Continue with remaining dec_05/06+ cases (e.g., T43859 siblings, PoE, stack, IPv6).
- Consider bulk review of refined-cases/ via viewer.html or tool scripts.
- When batch complete, prepare for Zephyr upload using zephyr_payload.json files.
- Periodically sync lessons back to OBJECTIVE_DRAFTING_PROCESS.md and README.md.

Thank you for the collaboration. Session state preserved. Ready for future work.

---

## 2026-07-01 Update — Drafting Tool Server-Backed Iteration

This session focused on evolving the Objective Drafting Tool from its v1 single-file static form into a server-backed application.

**Major Decisions:**
- Architecture switched to server-backed (FastAPI) because LLM synthesis is required, data will grow, and the tool will be persistently hosted behind nginx on local IP.
- Emphasis on **repeatable process** (strict step-by-step with confirm gates) and **repeatable outputs** (achieved through prompt templating + structured LLM response processing).
- All drafting-tool related artifacts consolidated under the `drafting-tool/` directory.

**Key Deliverables:**
- `drafting-tool/PLAN-server-backed.md` (approved plan)
- `drafting-tool/SERVER-README.md` (comprehensive instructions + session summary)
- `drafting-tool/LESSONS_LEARNED.md`
- `drafting-tool/drafting_server/` (initial implementation skeleton with templated LLM flow)
- Updated references in `drafting-tool/README.md`

**Lessons Captured:**
- See `drafting-tool/LESSONS_LEARNED.md` and the session summary section in `SERVER-README.md`.
- Single-file static reached its limits once direct LLM integration and long-term extensibility became priorities.
- Templating is the reliable path to repeatable structured outputs.

**Current State:**
- Server skeleton is functional (data loading, mock LLM synthesis producing consistent objectives + steps, basic API + UI).
- Ready for further implementation (full API enforcement, persistence, real LLM wiring, frontend polish).

See `drafting-tool/SERVER-README.md` for operational details.
For detailed current progress, backlog, technical debt, prioritized tasks with estimates, known issues, and seamless handoff to future Grok sessions on the drafting tool, **always start with `drafting-tool/PROGRESS.md`**.

Higher-level context: this root `SESSION_STATE.md`, root `README.md` (which now explicitly calls out the drafting-tool notes), and external `../AGENTS.md` (broader access and environment).

Future drafting sessions must cross-reference:
- `drafting-tool/PROGRESS.md` + `SERVER-README.md`
- Root `README.md` and this `SESSION_STATE.md`
- `OBJECTIVE_DRAFTING_PROCESS.md`

## 2026-07-01 Extended — Drafting Tool: Gating, Real LLM, Design UI

**Accomplishments:**
- Proper step gating + state machine (confirms store selections+flags+timestamps; synthesize enforces server-side using persisted state).
- File-based persistence (sessions/<key>.json stores full state incl. LLMConfig with provider/auth_method/creds, provenance).
- Real multi-provider LLM (Grok+Claude; api_key + account login modes; full prompt/response provenance captured+persisted; improved parsing).
- UI restructure + design integration (sidebar+main from showcase; full tokens; .btn/.card/.section/.page-header/.badge/.form-*/.table; small gray SVGs not emojis; custom scrollbar+border; title in sidebar-logo; no top header bar; dynamic page-header; in-page login instructions+explicit open; light/dark toggle in sidebar; spacing fixes per design scale).
- Reduced inline styles; buttons/forms/tables/sections use design components.
- All under drafting-tool/.

**State:**
- High priorities 1 (gating+persistence) + 2 (real LLM) complete.
- Frontend design-aligned; output gen next.
- See `drafting-tool/PROGRESS.md` for updated backlog/status.

**Cross-refs:** Updated `drafting-tool/PROGRESS.md`, `LESSONS_LEARNED.md`, `SERVER-README.md`; synced root README + this file.

## 2026-07-02 Session — Drafting Tool: Real Data + LLM for Steps 1-3, UI Compaction, Human-Readable Step 4

**Accomplishments:**
- Real data wired for Step 1 (TestLink candidates from candidates.json with selectable checkboxes + justifications) and Step 2 (Zephyr cross-refs from zephyr_master + slim_index).
- Dynamic case dropdown populated from real project data (AWPTCM-Txxxx); T33234 (Auto-negotiation) prioritized at top with auto-load.
- Step 3: Full LLM integration for ATPyLib pre-selection (`suggestATPWithLLM` button, new `suggest_atp.jinja` prompt, `suggest_relevant_atp` in llm.py, `/suggest_atp/{key}` endpoint using session selections + keyword retrieval). Auto-populate search results for demo.
- Pre-filled realistic selections (from actual data/decisions) for steps 1-3 on load of T33234 in MOCK mode; selections restored on reload.
- Major UI compaction: table cell padding/fonts/inputs dramatically reduced + section/card/main margins to 8px; TestLink/Zephyr/ATP tables now fit on one page with no side-scroll. Inline styles and widths tightened.
- Step 4: Added human-readable rendered output via `renderSynthesized` (formatted Objective + clean numbered Test Steps list; removed "Action:" label; provenance in collapsible details). Replaces raw JSON dump.
- Backend enhancements: data.py now loads candidates_dict + test_id_desc; wizard.py has query builders + suggest helpers; MOCK special-cased for useful demo suggestions.
- Demo flow complete: load T33234 → review pre-filled real-ish data in 1-3 (use LLM suggest) → confirm gates → human-readable synthesis.

**State:**
- Steps 1-3 now fully data-driven + LLM-assisted with user approval.
- Step 4 has usable human-readable display.
- See `drafting-tool/PROGRESS.md` for detailed status (output generation remains top priority).

**Cross-refs:** Updated `drafting-tool/PROGRESS.md`, `LESSONS_LEARNED.md`, `SERVER-README.md`; appended to this file and root README.md. Tested primarily via MOCK for instant pre-filled experience.



