# Session State — Objective Drafting Workflow (2026-06-25 / 2026-06-26)

> **Path note (2026-07-13):** entries before the "Repo Restructure + Ask CK" entry use the pre-restructure layout. Mapping: `drafting-tool/` → `ask-ck/CK-main/` (server code `drafting_server/` → `CK_server/`); root `data/` and `refined-cases/` and the process docs → `ask-ck/objective-drafting/`. Historical entries are kept verbatim.

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

## 2026-07-03 Session — Drafting Tool: Real Claude/Grok Subscription Auth (Headless CLI), Removed Fictional Login Flow

**Accomplishments:**
- Determined the existing "Subscription Account" Claude login was non-functional: it sent a pasted claude.ai "session token" as an `x-api-key` to `api.anthropic.com`, but no such token exists for third-party use — that endpoint only accepts a real developer API key.
- Implemented a working alternative for the stated deployment (locally hosted, multiple users each with their own Claude Team subscription, minimal LLM calls per step): **headless Claude Code CLI mode** (`auth_method: "claude_code"`). The server shells out to a locally installed + logged-in `claude` CLI (`claude -p --output-format json`), so each user's own subscription seat is used with no key/token stored server-side. Includes CLI presence/version check (`check_claude_cli`, `GET /api/wizard/claude_cli_status`), full frontend UI (Step 0 radio, "Check CLI Status" button, accurate setup instructions), and a fixed bug where Step 3 LLM helpers would silently fall back to MOCK under headless auth (which has no stored credential by design).
- The equivalent **Grok CLI headless mode** (`auth_method: "grok_cli"`, SuperGrok/X Premium+ subscriptions via `grok login --oauth`) was added to the backend (`llm.py`/`wizard.py`/`models.py`), mirroring the Claude Code pattern; its frontend UI is not yet built.
- Tested end-to-end using a scripted fake `claude` CLI binary (no real subscription needed): CLI status check, config set/validation (including rejecting `claude_code` for non-Claude providers), the full confirm-gate → synthesize flow through the headless path, and error handling (CLI not found, not logged in, timeout). Not yet validated against a real Claude Code login.
- No output-generation work this session — `zephyr_payload.json` completion remains the top priority in `drafting-tool/PROGRESS.md`.

**Key Lessons:**
- Verify a proposed third-party auth mechanism is technically real (i.e., the receiving API actually documents that credential type as valid) before building UI/instructions around it.
- Claude Code's own subscription login (`claude /login`) is a distinct credential from Anthropic Developer Platform API-key/OAuth auth — conflating them is how the fictional flow got built in the first place.
- Headless CLI auth is appropriate specifically because of the deployment model here (each user runs the tool locally under their own login) — it would not be appropriate for a shared multi-tenant backend.

**Later in same session (Grok continuation):**
- Strengthened Zephyr Step 2 omission: `current_cases` set (from candidates) is now used to exclude *all* members of the current Cases list from the Step 2 Zephyr `zrefs` (including the primary case itself). The table now returns only external cross-referenced Zephyr cases. Primary Zephyr data still appears in server-generated traceability notes.
- Completed and tested full **Grok CLI subscription integration** (`grok_cli`): `check_grok_cli()`, `_call_grok_cli_headless()` (using `--prompt-file`, clean stdout parsing), status endpoint, wiring through synthesize/ATP/analyze. Direct CLI tests + full Python `synthesize_objectives_and_steps(..., grok_cli)` succeeded on a machine with active subscription login (`grok login --oauth`).
- Final UI simplification (user request): removed the provider `<select>` dropdown entirely. Removed the "API Key (developer)" radio and credential input from the visible UI. The interface now consists *only* of two radio buttons for the subscription CLI modes (Grok CLI default + Claude Code CLI). All JS (setLLMConfig, restore, update*, clear, init) updated to derive provider+auth_method from the radio and hide credential paths. Description and instructions refreshed.
- Updated `drafting-tool/PROGRESS.md`, `LESSONS_LEARNED.md`, `SERVER-README.md` with the new state. Detailed handoff notes preserved under `drafting-tool/`.

**Key additional lessons:**
- When the user says "omit any test cases included in our current Cases list" from a review step, apply the rule literally (and also evaluate whether the primary belongs in that table).
- Local CLIs (`grok`, `claude`) after their native OAuth login (`grok login`, `claude /login`) are the canonical way to use subscription quotas from code without developer API keys.
- Once radios fully represent the desired modes, eliminate the redundant provider dropdown and unsupported paths (API key) to reduce confusion.

**Cross-refs:** All drafting-tool state/docs consolidated under `drafting-tool/`. Updated `drafting-tool/PROGRESS.md`, `LESSONS_LEARNED.md`, `SERVER-README.md`; appended here. See `drafting-tool/PROGRESS.md` for current status, backlog (frontend polish + critical load_case bug logged), and handoff. Root `README.md` and `OBJECTIVE_DRAFTING_PROCESS.md` cross-referenced where relevant. External `AGENTS.md` noted for environment/CLI install context.

**Bug logged (high priority for next session start)**: NameError: name 'f' is not defined in load_case (wizard.py) for zrefs["folder"] when loading new cases like AWPTCM-T44210 (500 error). Fixed in this session by restoring variable, but must be verified first next session with additional cases. See PROGRESS.md and LESSONS_LEARNED.md.

## 2026-07-03 Session — Drafting Tool: MOCK/Demo Removal + Output Persistence to refined-cases + Frontend Polish

**Accomplishments:**
- Full removal of MOCK/demo fallbacks and T33234 hardcodes from code (llm.py, routers/wizard.py, static/index.html, run.sh, main.py). Tool is now real-only (requires LLM_API_KEY or local CLI login; errors cleanly otherwise). Pre-computed LLM analysis replaces demo data.
- Output generation: export endpoint enhanced to auto-persist traceability.md + zephyr_payload.json (drop-in format) + session to `refined-cases/<Group>/AWPTCM-Txxxx/` (creates dirs via group resolution that matches existing folders like "Port (7)"). Client downloads retained. Builds on prior note/validation work.
- Frontend polish (high-prio #2): removed numerous inline styles (replaced with .hidden, utility classes like .instructions-panel, .btn-compact-*; updated JS for class toggles); enhanced renderReviewSummary (richer previews with more selections, justifications, counts + badges); improved post-synth editor (better form classes); neutralized last demo pre-select logic and cleaned comments/strings (pre-filled → pre-computed).
- Process page (main.py) basic rendering present; real flows enforced.
- Cross-refs and updates to PROGRESS, LESSONS, SERVER-README, root README/SESSION_STATE.

**State:**
- MOCK/demo fully excised from implementation (docs updated where user-facing).
- Output persistence addresses "drop-in refined-cases artifacts".
- UI more maintainable, less demo-tied, review/editing improved.
- See `drafting-tool/PROGRESS.md` for refreshed status (output advanced, polish in progress), updated backlog/hand off (real-only tests, no MOCK).

**Cross-refs:** All under `drafting-tool/`. Appended here and to root README. AGENTS.md for CLI login details.

---

## 2026-07-13 Session — Drafting Tool UX, Gaps-at-Completion, Dual Case Lists, LFS Push

**Focus:** Resume server-backed drafting tool; fix critical UX/process issues; handoff docs.

**Accomplishments:**
- Verified `load_case` zrefs NameError fix (T44210+); implemented **relevance-ranked external Zephyr** cross-refs.
- Frontend: dual case dropdowns (**Open/partial** with in-progress first vs **Complete**); Search+Suggest on Steps 1–3; table column CSS fix; stack-overflow fix (`updateAuthMethodUI`/`updateLLMDefaults`); Step renames (1 TestLink, 3 ATPyLib scored); no gaps textarea on Step 3.
- **Gaps** for Traceability generated by LLM at **synthesize/export** (`generate_gaps.jinja`), not user-edited mid-wizard.
- **Workspace LLM** preference (`sessions/_workspace_llm.json`) survives case switches; clear-session keeps it.
- Favicon; README cleanup (root + drafting-tool); PROGRESS/LESSONS/SERVER-README handoff update.
- Git: `git lfs migrate` so Zephyr XML is LFS in all history; public GitHub repo push path unblocked.

**State:** Tool is usable mid-implementation. Next: real CLI full-path smoke, output hardening vs exemplars, requirements.txt + error UX, Process page.

**Primary handoff:** always start at `drafting-tool/PROGRESS.md`. Cross-ref `drafting-tool/SERVER-README.md`, `LESSONS_LEARNED.md`, root `README.md`. `OBJECTIVE_DRAFTING_PROCESS.md` unchanged as process source of truth (gaps still part of Traceability artefacts). External `AGENTS.md` for CLI/env if present.

---



## 2026-07-13 Session (later) — Repo Restructure + "Ask CK" Multi-Tool Facelift

**Focus:** Convert the single-use drafting tool into the **Ask CK** multi-tool workbench: repo restructure support (repathing), UI facelift, new-tool scaffolding, docs repathed repo-wide.

**Restructure (user-initiated, mid-session):**
- `drafting-tool/` → `ask-ck/CK-main/`; `drafting_server/` → `CK_server/`.
- Root `data/`, `refined-cases/`, and process docs (PROGRESS, LESSONS_LEARNED, PLAN-server-backed, OBJECTIVE_DRAFTING_PROCESS) → `ask-ck/objective-drafting/`.
- Per-tool asset dirs pre-staged: `ask-ck/pytest-create/`, `ask-ck/test-composer/`, `ask-ck/zephyr-tool/`.

**Accomplishments:**
- **Repathing:** new `CK_server/paths.py` (DATA_DIR / REFINED_DIR / PROCESS_MD anchors); fixed `data.py` (was CWD-relative), both `refined-cases` roots in `wizard.py`, `/process` path in `main.py`, and `run.sh` (`PYTHONPATH=CK-main`, `CK_server.main:app`). Boot-verified with full data: 410 cases (368 open / 42 complete / 3 in progress).
- **Facelift** (plan: `ask-ck/ck-facelift/PLAN-facelift.md`): renamed to **Ask CK** (tab title, sidebar logo, FastAPI title). Sidebar sections (always expanded, top→bottom): **LLM** (status + **Configure** main-area panel — the relocated LLM Provider Login, element ids preserved, zero LLM-JS changes), **Zephyr Templating Tool** (1. Info / 2. Test Plan / Cycle / Cases / 3. Link Test Scripts / 4. TBD), **Test Composer** (1. TBD), **PyTest Creator** (1. Cases / 2. Creator), **Objective/Test Case Generator** (visible steps renumbered **1–6**, display-only — internal `data-step`/session-key/`confirm_step` scheme untouched).
- **Navigation:** generic `goToPanel(panelId)` + `goToStep()` wrapper + `PANEL_META` page-header registry; ✓ nav-badges scoped to the Generator; dead code removed (`showLLMConfig`, `#llm-config-card`, phantom `#llmCredential`).
- **PyTest Creator Cases wired:** independent dropdown pair fed by the same `/api/wizard/cases` fetch (shared `handleCasePairChange`); selection isolated in `ptCase` (never touches the Generator's `currentKey`).
- **Backend stubs:** `routers/zephyr_tool.py`, `test_composer.py`, `pytest_create.py` → `/api/zephyr-tool|test-composer|pytest-create/status` (+ pytest `generate/{key}` → 501).
- **Docs repathed:** root `README.md`, `PROGRESS.md`, `SERVER-README.md`, `LESSONS_LEARNED.md`, BoS/EoS prompts, `objective-drafting/README.md`, `CK_server/README.md`, `OBJECTIVE_DRAFTING_PROCESS.md` tool notes; historical docs (this file's earlier entries, PLAN-server-backed.md) keep original paths with banner notes.

**State:** Generator fully functional at new paths (automated verification: boot + data counts, stub endpoints, served UI, JS syntax). Next: manual browser smoke of the facelift, output hardening, real-CLI E2E, first real step of a new tool. `tool/` scripts not yet verified against new paths.

**Primary handoff:** start at `ask-ck/objective-drafting/PROGRESS.md`. Run with `./ask-ck/CK-main/run.sh`.

---


## 2026-07-14 Session — PyTest Creator (test cases → runnable framework scripts)

**Focus:** Build out the **PyTest Creator** (previously a 501 stub) into a full 8-step gated tool that turns a Complete refined case into a runnable Allied Telesis `framework` (ATTestSet/ATTestCase) test script, executes it on a real testbox, and iterates via an LLM fix loop until Final Validation. Plan + living tracker: `ask-ck/pytest-create/PLAN-pytest-creator.md`.

**Flow (each step has an explicit server-side Confirm gate; confirming step N invalidates later steps):**
1. Cases → 2. Sequence (LLM extracts prescriptive automatable steps from the refined payload; traceability note skipped) → 3. Script Search (mechanical index scoring + LLM coverage verdicts) → 4. Fit Decision (reuse/extend/new) → 5. Fragments (LLM proposes symbols; server resolves to real source by indexed line range; invented symbols dropped) → 6. Generate (composite script + editable `generated/<Group>/<Name>.py` naming + offline lint) → 7. Run (SSH/SFTP to a stored testbox, `sudo python3 <script> -s <setup> -v`, parse framework log) → 8. Validate (all cases PASS + zero fails + exit 0 → human confirm; failures loop via LLM fix, previous iteration archived).

**Key decisions (user):** hybrid index (mechanical AST + resumable LLM enrichment); the tool executes on a real testbox chosen from a stored dropdown (tb_number + IP minimum, "Add new testbox…" inline); function-based output names under the refined-case group structure (`generated/Port/MDIX_test.py`), editable at creation; `framework` treated as a whole library (drivers, ATLibrary helpers, ATPackets), not just the two base classes.

**Accomplishments:**
- **Script index** — new `tool/build_script_index.py`: AST scan of `testsuites_art` / `svt_scripts` / `test_scripts` (999 files; 120 py2-vintage regex fallbacks) capturing per-TestCase desc/ref/method (incl. `+=` accumulation), class line ranges, topology, imports; plus a `--framework` pass → `framework_surface.json` (55 modules from `DeviceSkrips/framework`). Outputs to `ask-ck/pytest-create/data/`. `tool/enrich_script_index.py` adds a resumable (sha1-keyed) LLM tagging/summary pass.
- **Backend** — `CK_server`: `paths.py`/`data.py` load the index at startup (graceful when absent); `models.py` `PtSession`; `llm.py` gained a `timeout` param threaded through the CLI callers + generic `run_prompt`/`extract_json_block`; new `pt_exec.py` (testbox profiles in gitignored `secrets.testboxes.json` @0600 with write-only/redacted passwords, `parse_framework_log()`, threaded paramiko SSH runner with per-stage persisted status + stale-marking on restart); full rewrite of `routers/pytest_create.py` (~25 endpoints across status/session/confirm/sequence/search/fit/fragments/generate/lint/profiles/run/fix/validate).
- **Prompts** — 7 templates: `pt_extract_sequence`, `pt_match_scripts`, `pt_assess_fit`, `pt_gather_fragments`, `pt_generate_script`, `pt_fix_script`, `enrich_script_index`.
- **Frontend** (`static/index.html`) — PyTest Creator sidebar expanded to 8 steps + a Testboxes panel; each panel follows the Run-LLM → review/edit → Confirm skeleton; ✓ badges driven by `data-pt-step` / `updatePtBadges()` (separate from the Generator's `data-step`, per the facelift scoping rule). Run panel has the testbox dropdown (`name — tb<NN> (IP)` + "➕ Add new testbox…"), poll + PASS/FAIL chips + raw log tail.
- **Docs** — `SERVER-README.md` PyTest Creator section; root `README.md` status row + workflow section + repo-layout note; tracker checklist/log kept current in `ask-ck/pytest-create/PLAN-pytest-creator.md`.

**Verified without hardware:** server boots and loads the index (999 files, 55 modules); `load_case` snapshots the refined payload and skips the traceability step; mechanical search returns `legacy/5000_mdi_mdix/*` as top hits for AWPTCM-T33234; confirm gates 409 out-of-order actions; `parse_framework_log()` unit tests pass (PASS/FAIL/crash-mid-case); profile CRUD redacts+chmods and is gitignored; all new Python + the page JS syntax-check clean; served page contains all panels.

**State / next:** Code complete across Phases A–D. Remaining (needs credentials/hardware): run `tool/enrich_script_index.py` with a logged-in CLI then rebuild; first real-LLM walkthrough of steps 2–6 (suggested case AWPTCM-T33234); first real-testbox SSH run; decide gitignore/LFS for the regenerable `ask-ck/pytest-create/data/` index (~2.6 MB, currently untracked).

**Primary handoff for PyTest Creator work:** start at `ask-ck/pytest-create/PLAN-pytest-creator.md`. Run with `./ask-ck/CK-main/run.sh`.

---


## 2026-07-16 Session — ES-module split + two-table review shortlist + search relevance

**Focus:** Execute the approved `ask-ck/ck-facelift/PLAN-es-module-split.md`, then two follow-on Generator improvements that grew out of a reported "ATP search doesn't work" quirk. All work is **staged in the working tree, not committed** (branch `main`; Terrence commits himself).

**1. ES-module split (plan executed).** Split the 2663-line `CK_server/static/app.js` into 14 browser-native ES modules under `CK_server/static/js/` — **no bundler, no package.json**. `index.html` now loads `<script type="module" src="/static/js/main.js?v=1">`; `app.js` deleted.
- **Keystone:** `js/actions.js` action registry (`registerActions`) replaced the `window[data-action]` dispatcher — module scope removes handlers from `window`, so each tool self-registers its own actions.
- Staged in two logical commits (registry-in-classic-app.js first to de-risk the 52-name contract, then the atomic split), plus `js/README.md` documenting conventions + the remaining `window.current*`/`lastLLMConfig` bus debt.
- Five bare globals (`currentSession`/`currentKey`/`currentStep`/`currentPanel`/`ptCase`) moved into a shared `S` object in `js/state.js` (137 rename sites).
- **Verified:** all modules parse, 65 imports resolve, action-name contract exact, zero console errors driving the app in real Chrome (`load_case → 200`), Terrence manual-signed-off.

**2. Two-table "chosen shortlist" (Generator steps 2/3/4 — TestLink/Zephyr/ATPyLib).** Replaced each step's single candidates-table+confirm with: candidates table → **↓ Choose selected** → insertion-ordered **Chosen** table → footer **Mark Reviewed + Confirmed** | **Clear selected contents**. Chosen rows disappear from the top; Clear moves them back. **Confirm reads ONLY the chosen table.** LLM Suggest drops picks straight into Chosen; keyword Search populates the top for manual Choose — this fixed the original "search results get buried" complaint.
- New module `js/chosen.js` (insertion-ordered `window.current*Chosen` arrays, choose/clear/restore/`chosenSelections`); `js/tables.js` rewritten (top tables hide already-chosen rows; shared `renderChosenTable`). `Selection.order` added to `models.py` to persist click order (optional → old sessions still deserialize). Confirm/restore rewired in `generator.js`; merges in `db-search.js` simplified.

**3. Search relevance scoring + pool re-scoring.** The old ATP/TestLink/Zephyr keyword search used a flat `0.45+0.1*hit` that gave every single-keyword hit an identical score (all 0.55), so ordering was meaningless. New shared `_relevance_score()` in `routers/wizard.py`: title>body field weighting, term frequency, whole-word bonus, phrase bonus, coverage. Wired into `_get_atp_candidates`, `_search_testlink`, `_search_zephyr_external`. Then fixed a follow-on: a **new search now re-scores the existing candidate pool** against the new query (search endpoints take a `keep_ids` param; frontend `poolIds()` sends current pool) so prior-search rows re-rank instead of staying pinned at stale scores — rows relevant to both queries stay up, non-matching ones sink (not discarded).

**Accomplishments:**
- `static/js/` — 14 modules + `chosen.js` + `README.md`; `app.js` removed; `index.html` module tag + two-table markup on steps 1/2/3; `styles.css` chosen-table/toolbar styles.
- `models.py` — `Selection.order: Optional[int]`.
- `routers/wizard.py` — `_relevance_score()`, three scorers reworked, `keep_ids` on all three search endpoints (`math` import added).
- Memory notes: `pending-approved-plans` updated (split done; DB-migration + LLM-observability still pending), `atp-search-merge-ux` documents the quirk + all three fixes.

**Verified:** JS syntax + 58-name action contract (52 original + 6 choose/clear) clean; Python imports clean; `_relevance_score` unit assertions pass; live-corpus checks (ATP "IGMP" ranks IGMP-titled rows on top; IGMP-pool re-scored to 0 when searching PIM). **Terrence manually tested and confirmed all three pieces working.**

**Note:** testing overwrote `CK_server/sessions/AWPTCM-T43865.json` (re-confirmed steps, new timestamps + `order` fields + richer justifications) — Terrence chose to keep these changes.

**State / next:** All three pieces complete + tested, staged uncommitted. The other two approved facelift plans — `PLAN-db-migration.md` (SQLite/FTS5/sqlite-vec) and `PLAN-llm-observability.md` — remain **not started**; the observability plan's frontend now targets a `static/js/` module since the split landed. Score-spread bunching near the cap and duplicate-title rows in the ATP corpus were noted and deliberately deferred.

**Primary handoff:** start at `ask-ck/objective-drafting/PROGRESS.md`. Run with `./ask-ck/CK-main/run.sh`.

---

## Session Close / Handoff (2026-07-16) — SQLite migration DONE; DB-only-search direction planned

**1. DB migration (`PLAN-db-migration.md`, SQLite/FTS5/sqlite-vec) — COMPLETE, all four commits landed.**
The corpora now live in `ask-ck/var/ck.db` (gitignored, rebuildable). Commits: **A `6cb97ca`**
(schema + `db.py` connection factory/reads/FTS searches + `tool/build_db.py`), **B `bdb2043`**
(server read paths → DB; killed the per-request `zephyr_cases.jsonl` scan + ~50 MB boot RAM),
**C `14cf4ad`** (sessions → DB; `llm_config` isolated in its own column), **D `1a0ef2a`**
(semantic + hybrid RRF search on sqlite-vec, keyword-degrade when the extension can't load).
Search parity vs. the live `_relevance_score` was verified 79/80 top-10. Tokenizer dropped `_`
so `mdi` matches inside `5000_mdi_mdix`. **KEY ENV:** vector `--embed` + live KNN only run where
`enable_load_extension` exists (Linux / `pysqlite3-binary`), not this mac system Python.

**2. Two feature branches built THIS session — STAGED, UNCOMMITTED, unit-verified, DB-rebuild pending.**
- **Scripts literal-code:** captures the actual `.py` source (currently the DB has only
  enrichment/tags/signatures). `scripts.source_text` (whole file) + `script_chunks` (per
  test-case/helper/testset, sliced by loc, whole-file fallback) + `chunks_fts` (word-split
  tokenizer) + `vec_chunks` (embeddings). New `db.search_code` / `search_code_hybrid`,
  `get_script_source/chunks`. `build_script_index.py` emits a `scripts_sources.jsonl` courier;
  `build_db` ingests it (graceful if absent). Extractor chunk logic unit-tested here.
- **Zephyr enrichment:** fixes two silent-drop bugs + adds two fields — `<details>` plain-script
  bodies (~1,300 cases were coming out `''`) → `script_text`; per-step `<testData>` (~1,285) →
  steps; `issues` (JSON `[{key,summary}]`, ~480 cases) + `attachments` (filenames, ~250) as
  nullable columns; `script_text`+`refs_text` added to `zephyr_fts` RECALL only (scorer still
  key+title+folder, so results unchanged). Extractor logic unit-tested here. Deliberately did NOT
  capture: createdBy/On, updatedBy/On, owner, estimatedTime, or the always-empty containers
  (customFields, confluencePageLinks, parameters) — Terrence's explicit exclusions.

**Working tree (uncommitted — Terrence commits himself):** `M` `db.py`, `schema.sql`,
`tool/build_db.py`, `tool/build_script_index.py`, `tool/extract_zephyr_xml.py`; `??`
`ask-ck/ck-facelift/PLAN-db-only-search.md`. Nothing verified against a DB rebuild yet — the
single `build_db --fresh --verify` (+ `--embed`) is deferred to the coordinated testbox pass so
both branches + real extractions land in ONE rebuild.

**3. Architecture DECISION — strict DB-only search (Terrence, 2026-07-16).** `ck.db` is the SOLE
source for all search + all runtime reference; the server must read ZERO JSON; originals ingest
direct-to-DB; JSON survives only as a build courier for physically-remote sources (testbox
scripts, live APIs), never searched. **Full phased plan + testbox checklist:**
`ask-ck/ck-facelift/PLAN-db-only-search.md`. Phase-1 gap is small (repoint 5 runtime JSON reads
in `data.py` + one in `pytest_create.py` to `db.*` getters that already exist). To run in a
FUTURE session — not started.

**Primary handoff:** `ask-ck/objective-drafting/PROGRESS.md`, then
`ask-ck/ck-facelift/PLAN-db-only-search.md`. Rebuild the DB anytime with
`python3 tool/build_db.py --fresh --verify`. Run the server with `./ask-ck/CK-main/run.sh`.

---

## 2026-07-16 Session (later) — Repo hygiene scrub (vestigial files)

Scrubbed a small set of genuinely-vestigial files. **Deliberately narrow** — most apparent
cruft in this tree is still live and was left untouched (see the guard note below).

**Removed (committed):**
- `zephyr-auto_negotiation.xml` (repo root) — stray 4.9 KB single-suite Zephyr export from the
  2026-07-13 restructure commit (`2361dcb`); referenced by zero tools, not an LFS-tracked source.
  An untracked duplicate had drifted into `data/zephyr_full/` — deleted that too.
- `data/suites/_gather_suite.py`, `_remaining_suites.txt`, `_todo_suites.json` — enrichment
  working-scratch; Phase 2 enrichment is complete. `_enrichment_agent_spec.md` kept (it's a
  referenced doc). `ENRICHMENT_STATE.md` Assets block updated to record the removal.
- `CK_server/debug-log/{b-test,c-test,c}.jsonl` — gitignored LLM debug test scratch (on-disk
  only, never tracked).

**GUARD — do NOT delete in a general scrub (still live, despite looking redundant):** the
`data/suites/suite_*_enriched.json` corpora (~130 files), `zephyr_full/*.jsonl`/`index.json`/
`slim_index.json`, `candidates.json`, `data/decisions/*.json`, and the `CK_server/sessions/*.json`
+ `pt-*.json` files. The corpora are still the rebuildable **build input** for `ck.db`
(`build_db.py`) — DB-only search (`PLAN-db-only-search.md`) is planned, NOT started, so nothing
reads the DB as sole source yet. Session JSON is an intentional *frozen pre-migration backup*
(`wizard.py:_persist_session`). These retire only in **Phase 5** of the DB-only plan, as a
coordinated step — not ad-hoc.

---

## 2026-07-20 Session (later) — LLM-config bug, prompt trims, health check, provenance/dry-run

Started as "test the trimmed Objectives/Steps prompts"; the new LLM debug-log immediately
surfaced a real bug, and the session grew into four related pieces of work. **ALL UNCOMMITTED**
at session end (Terrence commits himself). Server verified live throughout via `./run.sh`.

**1. LLM-config bug (dangerous — FIXED).** PyTest Creator's LLM endpoints resolved
`_llm_cfg(sess)` raw and only `load_case` applied the workspace login, so a session with a
stale/inactive persisted config silently fell back to the LLM layer's default backend
(`claude_agent` → api.anthropic.com, `model=default`) instead of the configured `local_llm`.
Caught by the debug-log: a real `extract_sequence` on T33233 recorded `auth=claude_agent` and a
180s timeout ("local Claude agent did not respond"). **Fix:** folded the workspace-apply into
`_llm_cfg` itself (`pytest_create.py`) so no endpoint can forget it. Audit found the **same latent
pattern in the wizard** — hardened `_session_llm_cfg` and routed suggest_atp/synthesize/coverage
through it (`load_case`→analyze_atp was already safe). Memory: `pytest-creator-llm-config-bug`.

**2. Prompt trims** (`pt_extract_sequence` −46%, `generate_steps` −51%, `generate_objectives`
−16%). Dropped: the reviewer-facing traceability dump (sequence extraction), the raw selections
(steps — the finalized objective already carries them), the duplicate `process_principles`, the
raw `primary` dict, blank-line loop padding. **Removed a `(typically 4-10)` bullet-count anchor
that contradicted `OBJECTIVE_DRAFTING_PROCESS.md`** ("not uniform") — plus the matching silent
code caps (`bullets[:10]`, `ranked[:10]`, fallback `[:6]`, suggest/analyze selection caps).
Ranking now covers all relevant candidates; input-pool caps (`candidates[:20]`) kept as legit
token bounds.

**3. Health check** (Configure page, by "key stored ✓"): `POST /api/wizard/llm_health` +
`_health_ping` — minimal completion via the real path. Both vLLM models confirmed up (earlier
500s were transient). Token badges relabelled `N in / M out (total)` (was ambiguous `17→179 tok`)
via one shared `fmtTokens`. Memory: `llm-health-check-button`.

**4. LLM Provenance + dry-run** (permanent portability feature). Every LLM panel gets a copyable,
live-`Refresh` prompt preview via a `dry_run` flag that renders the prompt through the real path
and returns it **without sending** — verified byte-identical to a real send + zero tokens. New
`static/js/provenance.js`. Purpose: paste the exact prompt into a competing/free LLM. The
debug-log is dev-only scaffolding; Provenance is its durable replacement. Memory:
`llm-provenance-portability`.

**Also:** created a **root `./run.sh`** thin wrapper (forwards to `ask-ck/CK-main/run.sh`) so the
primary launcher is at the root next to `setup.sh`; README now has a `setup.sh` vs `run.sh`
decision table.

**Working tree (uncommitted):** `M` `ask-ck/CK-main/CK_server/{llm.py, models.py,
routers/wizard.py, routers/pytest_create.py, static/index.html, static/styles.css,
static/js/{generator,pytest,db-search,llm,llm-debug,main}.js}`, 4 prompt templates, `README.md`,
`ask-ck/CK-main/SERVER-README.md`, `ask-ck/pytest-create/PLAN-pytest-creator.md`,
`ask-ck/ck-facelift/PLAN-llm-observability.md`, this file. `??` `run.sh` (root wrapper),
`ask-ck/CK-main/CK_server/static/js/provenance.js`.

**Primary handoff:** the four features are complete + verified but UNCOMMITTED — commit at a clean
point (suggest four commits, one per feature, or one grouped). Then the **actual pending goal**:
retry the PyTest Creator **first LLM walkthrough** (T33234/T33233) on `local_llm`/`vllm-thinking`
now that dispatch resolves correctly — that produces the Phase B milestone (first lint-clean
generated script). Run the server with `./run.sh --bg`. See `HANDOFF.md` for the full uncommitted
state.

---

## Session Close / Handoff (2026-07-20b) — Strict DB-only Phase 1 + script-code + semantic embeddings

> Supersedes the "DB-only search … NOT started" notes in the 2026-07-16 entry above — Phase 1 is now done + committed.

**What landed (all committed + pushed this session):**
- **Literal script source code** now in the DB: `build_script_index.py` → `scripts_sources.jsonl`
  (830 files, 5,782 code chunks) → `build_db.py --fresh` fills `scripts.source_text` +
  `script_chunks` + `chunks_fts`. `db.search_code` / `search_code_hybrid` return real code.
- **Semantic embeddings**: `build_db.py --embed` → ~84k vectors across all 5 entities incl.
  `vec_chunks`. `/health` → `vector_search:true, embeddings:83816`.
- **Stand-alone embedding model**: bundled at `ask-ck/var/models/`, forced `HF_HUB_OFFLINE` in
  `db.py` + `run.sh`. No external dependency but the org vLLM LLM (which is the tool's function).
- **Strict DB-only runtime (Phase 1)**: `data.py` + `pytest_create.py` read every corpus/reference
  from `db.*`; `main.py` fails fast without `ck.db`; **`tool/guard_db_only.py`** locks the invariant.
- **Three latent bugs fixed**: embed `HAS_VEC` guard ran before the connection opened (`--embed`
  never ran); sqlite-vec KNN issued as a JOIN → silently returned nothing (hybrid was keyword-only);
  huggingface load-time ping.

**Why ck.db is gitignored:** it's a derived, rebuildable cache (regenerates byte-identically from
tracked source exports), not a source of truth. Rebuild: `python3 tool/build_db.py --fresh --verify`
then `--embed`.

**Next:** PLAN-db-only-search Phase 2 (fold local XML straight into the DB, retire the jsonl
courier) + Phase 5 (prune legacy offline JSON tools, wire the guard into CI). Docs synced this
session: README, SERVER-README, both DB plans, PROGRESS.

---

## Session Close / Handoff (2026-07-21) — PyTest Creator: DB-only fix, framework read-only, standardized template (Part 1)

Planning + build session for the PyTest Creator standardization/testing effort. All work
committed + pushed to `main`. Living plan: `ask-ck/pytest-create/PLAN-pytest-testing.md`.

**Shipped this session (commits `c29f53e`, `152e86b`, `ca90ff8`, + Part 1 template commit):**

- **DB-only source fix.** `routers/pytest_create.py::_read_source` had been reading script
  source off the retired `testsuites_art/` mount (gone from disk). Repointed to `ck.db`
  (`scripts.source_text` / `db.get_script_source`); `rec["path"]` is now provenance-only. A
  four-subagent audit read all 17 `CK_server/*.py` in full and confirmed this was the ONLY live
  DB-only violation; removed dead scaffolding (`DATA_DIR`/`PT_DATA_DIR` anchors, vestigial
  `SESSIONS_DIR`/`_session_path`/`GLOBAL_LLM_PATH`, stale comments). Extended
  `tool/guard_db_only.py` from 1→4 detected regression shapes.

- **Testbox framework dir is READ-ONLY.** New standing constraint: `/home/st-art/framework`
  (profile `framework_path`) must never be written/edited/mutated (copy locally to edit).
  Enforced at runtime in `pt_exec.py` (write-target + command guards, source-vs-dest aware) and
  by the runnable `tool/guard_framework_readonly.py` (15 cases).

- **Part 0 — logging contract** (`ask-ck/pytest-create/LOGGING-CONTRACT.md`): the required
  per-step log format, verified three ways (framework source on tb470 + a real 101-case log +
  the tool's `parse_framework_log`).

- **Part 1 — standardized script template.** Generation now fills a fixed skeleton
  (`templates/pt_script_template.py.jinja`) rather than composing freely: data-driven `init`,
  suite `configure`/`tear_down` (no pass/fail), one `TestCase` per verification step with the
  logging contract + per-case `tear_down`. `pt_generate_script.jinja` rewritten to fill-not-
  compose; `_lint_generated` extended for template/logging-contract conformance. Docs:
  `TEMPLATE-SPEC.md`; the ART run chain in `ask-ck/test-composer/ART-EXECUTION-CHAIN.md`.

**State:** guards green (`guard_db_only`, `guard_framework_readonly`); `/health` ok; `ck.db`
remains the permanent LFS-committed single source of truth (unchanged this session). Testbox
`tb470` reachable (device on u5); `configs/tb470.setup`/`.cfg` not yet created (Part 3b prereq).

**Next:** Part 2A (first real end-to-end walkthrough on T33234 — also the pipeline's maiden run
against the live DB), Part 2B (keyword-vs-LLM + model-matrix harness), Part 3a/3b (judging +
tb470 execution with two LLM judges + human holistic review).

**Note on an older entry below:** the 2026-07-20b entry's line *"Why ck.db is gitignored: it's a
derived, rebuildable cache"* was **superseded on 2026-07-20c** — `ck.db` is now the permanent,
LFS-committed single source of truth (not gitignored, not rebuildable). See the 2026-07-20c
PROGRESS entry and `db-is-permanent-source` memory.

---

## Session Close / Handoff (2026-07-21b) — PyTest Creator Part 2A + vLLM-path hardening

**Scope:** first real end-to-end walkthrough of the 8-step PyTest Creator flow on
T33234 (`AWPTCM-T33234`, Port Auto MDI/MDI-X), headless via the org vLLM against the
permanent `ck.db`. Two commits, both pushed to main: `e6c0d64`, `1ccf1a7`. Full
per-step record: `ask-ck/pytest-create/PART2A-WALKTHROUGH.md`.

- **Pipeline verified steps 1–6.** load_case → extract_sequence → suggest_scripts →
  assess_fit → gather_fragments → generate_script all produce correct output against
  the live DB; the generated script compiles + passes conformance lint. Step 7 (run)
  gates cleanly (`400`) with no testbox profile — fails safe. Every step verdict KEEP;
  decomposition + confirm-gating sound. Live run (7–8) blocked only on the `tb470`
  profile + `.setup` prereq (Part 3b).

- **Three vLLM-path bugs fixed (`e6c0d64`, `llm.py`),** all from the org models being
  reasoning models (CoT in `message.reasoning_content` before `message.content`):
  (1) `max_tokens` 2000→16000 for `local_llm`; (2) response parser guards
  null/empty/`finish_reason=length`-truncated content with a clear error +
  `reasoning_content` fallback; (3) `extract_json_block` picks whichever of `{`/`[`
  appears first (was returning a nested array instead of the outer object). The tiny
  health-ping had masked all three.

- **vLLM system+user shape adopted + FILL-marker guarantee (`1ccf1a7`).** `run_prompt`
  now sends the documented system+user pair with a default JSON-only steer
  (`_JSON_SYSTEM_PROMPT`) — measured −35% completion tokens / −37% latency on
  `extract_sequence`, and it made the model honor the prompt's skip-and-note rule
  (`notes` empty→populated). Deterministic `_strip_fill_markers` (router) + a stronger
  `pt_generate_script.jinja` rule guarantee no `# >>> FILL` scaffolding survives.

- **Open content items for Part 2B/3 (documented, not blocking):** inline provenance
  tags (§1.5) are prompted but **not emitted** by the model; `— not yet implemented`
  leaks into `failed()` reasons; assess_fit verdict is non-deterministic; generated CLI
  syntax needs on-device validation.

**State:** guards green (`guard_db_only`, `guard_framework_readonly`); `/health` ok
(830 scripts, 83816 embeddings); `ck.db` unchanged — still the permanent LFS-committed
single source of truth. No data-layer, courier, or rebuild-path changes this session.

**Next:** Part 2B (keyword-vs-LLM + model matrix: vLLM fast/thinking, Claude
Haiku/Sonnet/Opus, logged per-case), then Part 3a (offline judging, criteria 1–4 for
T33233/T33234/T33235) and Part 3b (tb470 execution + log parsing, criteria 5–6, two
LLM judges + human review) — the latter gated on creating `configs/tb470.setup` + a
PyTest Creator testbox profile.

## ✅ FIXED 2026-07-22 (partially) — vLLM read timeout on suggest_zephyr (from debug-log)

**Update 2026-07-22:** Fix option 1 below (split connect/read timeout, raised
read floor) is DONE — see `llm.py`, verified against real requests. **Fix
option 2 (streaming) is NOT done and Part 2B's real model-matrix run found it
is still needed**: `vllm-thinking` on `generate_script` (the largest-output
step) still hit `Read timed out. (read timeout=600)` in 2 of 3 test cases even
at the new 600s floor — a bigger static ceiling helps but a sufficiently long
reasoning phase can still exceed any fixed number. See
`ask-ck/pytest-create/PLAN-pytest-testing.md` §7.7 for the full data. The
original symptom below is preserved for reference.

## (historical symptom, root-caused above) vLLM read timeout on suggest_zephyr (from debug-log)

**Symptom (last recorded LLM failure).** `sess-7y2z6q1y98w-mrs6n343.jsonl`, entry
`2026-07-20T23:44:47Z`, endpoint `/api/wizard/suggest_zephyr/AWPTCM-T43865`
(template `suggest_zephyr`), provider `openai/vllm-thinking` via `local_llm`.
Ran **120,105 ms** then died with a **client-side read timeout** (no provider error
body):

```
ERROR: LLM call failed (openai via local_llm):
HTTPConnectionPool(host='vllm.ai.atlnz.lc', port=80):
Read timed out. (read timeout=120)
```

**Root cause (working theory).** Not a prompt/model error — the request reached the
vLLM host but no bytes returned within the 120 s socket read window. Consistent with
[[vllm-reasoning-model-path]]: these org models are reasoning models that emit a long
`reasoning_content` phase *before* any `content`. On a large ranking prompt (this one
listed ~30 candidate Zephyr cases to rank down to 3–8) the reasoning phase alone
exceeds 120 s, and a **non-streaming** call has nothing to reset the read clock → it
hits the ceiling and aborts.

**Fix options (do in `llm.py`, `local_llm`/vLLM path), most→least important:**
1. Raise the **read** timeout for the vLLM path well above reasoning latency
   (e.g. 300–600 s); split connect vs read timeouts rather than one value.
2. **Stream** vLLM responses so token/reasoning deltas keep the socket alive and reset
   the read clock (best structural fix).
3. Optionally steer/cap reasoning length for ranking-style prompts where a short JSON
   answer is expected.

**Confirmed on a second endpoint (same error, same case).**
`2026-07-20T23:55:15Z`, endpoint `/api/wizard/synthesize_objectives`
(template `generate_objectives`), same provider `openai/vllm-thinking` via `local_llm`,
ran **120,102 ms**, identical failure:

```
ERROR: LLM call failed (openai via local_llm):
HTTPConnectionPool(host='vllm.ai.atlnz.lc', port=80):
Read timed out. (read timeout=120)
```

So this is **not** specific to `suggest_zephyr` — it hits any large-prompt vLLM call
(seen on **LLM suggest** and **Synthesize Objectives**, both on `AWPTCM-T43865`).
Confirms the root cause is the shared 120 s read timeout / non-streaming path in
`llm.py`, not one template.

**Where to look:** [llm.py](ask-ck/CK-main/CK_server/llm.py) (timeout + request shape),
shared by all vLLM calls. Reproduce against `AWPTCM-T43865` via either
`suggest_zephyr` or `synthesize_objectives`.
Note the `120000 ms` durations in the same log for other large-prompt calls — same
class of failure, so a fix here likely helps `extract_sequence`/`suggest_scripts` too.

## FIX NEXT SESSION — LLM button loading state (UI, all panels)

**Ask.** Every LLM-triggering button needs a visible **button state change** on click so
the user knows (a) the click registered and (b) a call is in flight / awaiting a
response (loading / spinner / "Working…" / disabled-with-label — pick a consistent
treatment). Right now a long call (see the vLLM timeout above — these can run 120 s+)
gives no feedback, so the button looks dead.

**Also (the important half).** While a call is in flight the button (and ideally sibling
LLM actions on that panel) must be **disabled** so the user can't fire multiple LLM
calls — accidentally or deliberately — against the same panel while waiting on a prior
result. Re-enable on completion or error.

**Scope.** Apply consistently across all LLM panels (the same set the provenance work
touched — see [[llm-provenance-portability]]). One shared helper/pattern for
in-flight → disabled+spinner → restore, rather than per-button one-offs.

**Note.** This pairs with the vLLM timeout fix above — until reasoning-model calls are
faster/streamed, the in-flight window is long, which makes the loading state and the
double-call lockout more important, not less.

## Session Close / Handoff (2026-07-22) — vLLM timeout fix (partial) + §1.5 provenance tags + Part 2B model matrix

**All work this session is UNCOMMITTED — Terrence commits himself.** Full
bug-by-bug log with rationale: `ask-ck/pytest-create/PLAN-pytest-testing.md` §7.

- **vLLM read-timeout fix (Option 1 from the note above): DONE.** `llm.py`'s two
  hardcoded `timeout=120` HTTP calls (which silently ignored every caller's
  actual requested timeout) are now a `(connect=10, read=<caller's timeout>)`
  split, with the `local_llm` read floor raised to 600s only when the caller
  asked for ≥120s (the health-ping's 30s stays fast-failing). **Option 2
  (streaming) is still needed** — see the Part 2B finding below.
- **§1.5 inline source-provenance tags: BUILT** (`# ART/SVT/legacy <suite/file>
  lines a-b` mechanical tags, or `# AI <model> <date>` gap-fill; authoritative
  server-side re-stamp, never trusting LLM self-report). Verified on a real
  live T33234 regenerate; found + fixed a real duplicate-tag bug along the way
  (model echoed the prompt's own instruction text as a second comment line).
  Also scrubbed a `— not yet implemented` string leaking from the skeleton's
  placeholder `failed()` text.
- **`max_tokens` threading:** found live (not assumed) that `generate_script`
  hit `finish_reason=length` at the 16000-token default while verifying §1.5.
  Threaded an optional `max_tokens` override end-to-end; `generate_script`/
  `fix_script` now request 32000.
- **Two more real pipeline-blocking bugs found + fixed** while setting up all
  three target cases for Part 2B: (1) a session's stale `llm_config`
  (leftover `claude_agent`) never re-syncs to the workspace default —
  `_llm_is_active()` treats headless-CLI auth methods as unconditionally
  active; same gap exists in `wizard.py`, deliberately NOT fixed there this
  session (bigger blast radius, not blocking). (2) `confirm_step` rejected a
  legitimate `fragments: []`/`matches: []` answer (Python falsy-checks an
  empty list same as "never ran") — blocked the whole rest of the pipeline for
  any case whose Fit Decision is genuinely "new, no reuse". Both fixed
  narrowly, verified live against the real DB/vLLM.
- **Part 2B built AND run for real** (`tool/pt_model_matrix.py`, new): 75 real
  LLM calls (3 cases × 5 LLM-bearing steps × vLLM-fast/thinking + Claude
  Haiku/Sonnet/Opus). Grok CLI verified logged in but genuinely
  quota-exhausted (real 403) — logged as an omission per the plan's own
  instruction, not silently skipped. Results committed at
  `ask-ck/pytest-create/comparison/Port (7)/<CaseKey>/<step>.json`.
  **Headline: `vllm-fast` is the clear reliability+latency winner (0/15
  errors, fastest); `vllm-thinking` failed 3/15**, including
  `generate_script` timing out even at the raised 600s floor in 2 of 3
  cases — confirms streaming (fix option 2, not yet built) is the real
  structural fix still needed for the thinking model on large-output steps.
  Keyword-vs-LLM Step-3 search: one case showed full agreement with
  mechanical rank; the other showed the LLM genuinely promoting a
  better-matching script (misleading keyword vocabulary overlap between two
  suite families) that the mechanical scorer under-ranked — real, useful
  signal either way.
- **Verified every LLM access path live before assuming any block** (a prior
  turn had wrongly claimed several hard blocks from file-absence alone —
  corrected after being challenged): vLLM key present + working, Claude
  Haiku/Sonnet/Opus all reachable via `claude -p --model <alias>`, Grok
  logged in but quota-exhausted, tb470 reachable (SSH/sudo/framework
  confirmed) but `configs/tb470.setup` genuinely absent — the one real
  remaining external block, Terrence-side (physical topology), per §5b.

**Not done / explicitly deferred:** the `wizard.py` twin of the stale-`llm_config`
bug (same root cause, not fixed there — bigger blast radius); the second
standing note above (LLM button loading state, UI) — untouched this session;
streaming for vLLM (Option 2) — the data now shows it's not optional for
`vllm-thinking` at scale, recommend prioritizing it.

**Next:** Part 3a (offline judging, criteria 1-4, two LLM judges: Claude Opus +
vLLM-thinking) for all three cases; Part 3b (tb470 execution, criteria 5-6) —
gated only on `configs/tb470.setup` (topology) + a stored PyTest Creator
testbox profile, both Terrence-side.

---

## Session Close / Handoff — 2026-07-22b — vLLM streaming transport + stale-`llm_config` re-sync

Two changes this session: (1) the streaming transport that Part 2B §7.7 named as
the real structural fix for `vllm-thinking` read-timing-out on `generate_script`;
(2) the §7.3 stale-`llm_config` root-cause fix in both routers. Committed at session
close; push to main pending — this environment lacks GitHub SSH auth (Terrence to
push). Terrence enabled auto commit+push on the end-of-session doc-sync this session.
Full record:
`ask-ck/pytest-create/PLAN-pytest-testing.md` §8 (streaming) + §9 (re-sync).

- **`CK_server/llm.py` — OpenAI-compatible branch of `_call_llm_raw` now streams**
  (`stream: true` + `stream_options: {include_usage: true}`). The SSE body is
  consumed with `requests.post(..., stream=True)` + `iter_lines()`; streamed
  `content`/`reasoning_content` deltas and the final `finish_reason`/usage chunk
  are accumulated into the SAME `(content, finish, usage)` triplet the non-streamed
  path built, and a reconstructed `raw_response` keeps `normalize_usage` /
  debug-log / provenance identical. Every existing guard (finish_reason=length,
  null→reasoning_content fallback, mid-JSON truncation) and the token badges are
  unchanged.
- **Why structural, not a bigger ceiling:** with a streamed body the `read`
  component of the `(connect, read)` timeout bounds the gap BETWEEN chunks, not the
  whole response. vLLM streams `reasoning_content` throughout the thinking phase, so
  the socket never goes silent and a reasoning pass of any length completes. The
  prior fix's static 600s floor could still be exceeded (§7.7: it was) — this
  removes the ceiling. Anthropic native path left non-streaming (no such failure).
- **Verified live (real org vLLM):** `vllm-fast` trivial ask 1.0s + correct
  badges; `vllm-thinking` `generate_script`-scale prompt completed at 395.6s
  (`finish=stop`); ceiling-gone proof — a `vllm-thinking` call with a deliberately
  short 30s read timeout ran 21+ min with no read-timeout error (killed for time,
  not failure), proving the read budget is now inter-chunk.
- **Token-processing-over-time (in progress):** identical prompt through both
  models, chunk-instrumented. `vllm-fast` baseline: 48.7s, first answer token at
  21.3s (21s reasoning-only first), 8,733 completion tokens, 8,731 chunks. **Key
  finding: `vllm-fast` is ALSO a reasoning model** — both reason and both stream
  `reasoning_content`; the fast-vs-thinking difference is reasoning-phase
  *duration/volume*, not reasoning-vs-not. Same vLLM SSE structure for both.
  **`vllm-thinking` on the same prompt (complete): 2,149s (35.8 min, 44× slower),
  `finish=length`, ZERO answer emitted** — spent the whole 32k-token budget on
  reasoning (29,137 reasoning tokens), never transitioned to the answer. Streaming
  fixed the transport (the 35.8-min call completed with no read-timeout; the 600s
  ceiling would have aborted it) but NOT the model's fitness — `vllm-thinking` is
  unfit for `generate_script`-scale generation, which strengthens the
  vllm-fast-default call. Infographic (token curves over time, both models):
  `ask-ck/pytest-create/comparison/vllm_tokens.html` + `vllm_tokens_data.json`
  (also published as a Claude artifact).

**Stale-`llm_config` re-sync (`routers/wizard.py` + `routers/pytest_create.py`) —
the §7.3 root-cause fix, PLAN §9.**

- **Root cause:** both workspace-apply functions gated only on `_llm_is_active`,
  which reports the headless CLI modes (`claude_agent`/`claude_code`/`grok_cli`)
  active **unconditionally** (correct — no server-side key to check). So a session
  whose *stale* config was a headless mode was judged active → never re-synced to
  the workspace default → kept silently hitting the wrong backend (the T33233
  `suggest_scripts`→`claude_agent` degrade §7.3 hit).
- **Fix:** the active workspace default is now authoritative. New helper
  `wizard._same_backend(a,b)` compares the dispatch-selecting fields
  (auth_method/provider/model, ignoring credentials); both
  `_apply_workspace_llm_if_needed` (wizard) and `_apply_workspace_llm` (pytest, which
  imports the helper) re-sync whenever the session config is inactive OR diverges
  from the workspace default. `_llm_is_active` left untouched (its status/`has_key`
  uses are correct as-is).
- **Safe by construction:** `set_llm_config` is the only writer of a case's config
  and always writes it === the workspace default, so no legitimate per-case
  divergence exists to protect. When the workspace default is inactive/absent the
  apply is a no-op, so "workspace login persists across cases" still holds.
- **Verified:** unit-level, 8/8 (no vLLM) — stale `claude_agent` re-syncs, matching
  config untouched, Fast↔Thinking divergence re-syncs, empty→applied, inactive
  workspace→untouched, `_same_backend` spot-checks. Concurrency-reviewed (PLAN §9.3):
  atomic within a coroutine, distinct sessions write distinct rows, same-session
  writes converge to the same value; WAL + `busy_timeout` absorb the bounded
  one-extra-write-per-divergent-session cost.
- **Pre-existing debt surfaced (NOT introduced here), PLAN §9.4:** dual-instance
  sessions — `sessions[key]` in-memory vs a fresh `_load_persisted` copy can produce
  two live objects for one key under concurrency; last-persist-wins can drop the
  *other* request's unrelated state (e.g. a confirm flag). Independent of
  `llm_config` (which converges). Proper closure = single-flight per key or an
  `updated_at`/version compare-and-swap on `db.save_session`. Logged, not blocking.
- **Still deferred:** Part 3a/3b (the `wizard.py` twin bug is now fixed).

---

## Session Close / Handoff (2026-07-22d) — Claude-agent token reporting + model selector + Traceability-gaps decoupling

**Two chunks of work, both committed this session.**

### 1. Traceability gaps decoupled from Objective synthesis (commit `8503cea`)
- `synthesize_objectives` (`llm.py`) was making a second LLM call (`generate_coverage_gaps`)
  only to inject an "Automation gaps (Traceability context)" block into
  `generate_objectives.jinja`. It didn't shape the declarative objective bullets, and
  gaps are already generated independently at export time when `traceability.md` is
  rendered. Removed the gaps block from the template AND the internal gaps call.
- **Step 4 is now a single self-contained objective call**; dry-run preview == real send
  byte-for-byte. `traceability.md` + its gaps unchanged (still built at `/api/wizard/export`).
  Existing cases carry gaps on disk → unaffected. Prompted by a two-model comparison
  where the extra gaps call was pure noise + tokens.

### 2. "— tok" diagnosis → Claude-agent token usage + cost (this commit)
- **Diagnosis (corrected):** the user compared two Objective runs — one badge showed
  `937 in / 2,971 out`, the other "— tok". The debug-log (`CK_server/debug-log/`) proved
  the first was **vLLM** (`local_llm`) and the second was **Claude via the agent bridge**
  (`claude_agent`), which wasn't forwarding usage → `normalize_usage` returned `None` →
  honest "— tok". (An earlier claim that the debug-log was empty was WRONG — a flaky
  relative `cd` over the `/media/.../mnt` mount + a wrong template filter; the dir has 4
  session files.) Both responses rendered fine — observability gap, not a truncation.
- **Fix (4 files, all in-repo):** `ask-ck/agent/ck_agent.py` lifts `usage` +
  `total_cost_usd` from the `claude -p --output-format json` envelope; `static/js/agent.js`
  forwards them in `/api/agent/result`; `routers/agent_bridge.py` passes `total_cost_usd`;
  `agent_jobs.py` `deliver()` stores both in the shape `normalize_usage` expects. Verified
  with a simulated deliver (cache tokens fold into input; cost surfaces; no-usage → `None`).
- **⚠ ck-agent runs on the USER's machine** — Terrence must restart it
  (`cd ask-ck/agent && ./run-agent.sh`) for token reporting to take effect. Server + browser
  changes are live on reload.

### 3. Haiku / Sonnet / Opus model selector (this commit)
- Mirrors the vLLM Fast/Thinking toggle: `claudeAgentRow` radios in `index.html` (shown only
  for `claude_agent`, default Sonnet); `static/js/llm.js` wires Apply + live-persist toggle
  (`applyClaudeMode`) + restore + status line; `main.js` binds the radios. Flows
  `llm_config.model` → `job.model` → `claude --model <name>` (aliases haiku/sonnet/opus).
  Free-text model field still overrides.

### State
- Guards green (`guard_db_only`, `guard_framework_readonly`); `/health` 200; Python + JS
  syntax checked. Docs synced (README status row + LLM bullet, SERVER-README agent-bridge
  section + template-roles, PROGRESS 2026-07-22d).
- **Push caveat unchanged:** this environment has no GitHub SSH auth, so `git push` fails
  (`Permission denied (publickey)`). Commits land locally; Terrence pushes `main`.
  > **Superseded (2026-07-27):** this was **Mac-seat-specific**, not a repo property. The
  > Linux seat pushes to `main` fine (verified `1478952`). Don't treat "can't push" as a
  > standing caveat — check the seat.

## Session Close / Handoff (2026-07-23) — PyTest Creator UX revision + adversarial-review worklist

### Focus
A large hands-on revision of the **PyTest Creator** while Terrence tested it live, then a
step-by-step pass through the **T33233 adversarial-review worklist**. This session's earlier
`## State` note at line ~1408 (2026-07-22d) is not superseded — this is additive.

### What shipped
**Flow / UX (steps 1–4):**
- 1. Cases → **Open/Partial + Complete** dropdowns (split by PyTest work state; partials on top).
- 2. Sequence → current steps + LLM execution order, **drag-and-drop reorder**, static source
  column, and per-step **kind** classification.
- 3. Script Search → **per-step carousel** (one step/screen, Prev/Next + green-✓/yellow-✗ step
  pills); per-step candidate→chosen tables; selections stored `{stepN:[ids]}`, flattened downstream.
- **4. Fit Decision REMOVED** (moot under the fixed skeleton); visible 5–8 → 4–7; internal
  `stepN` keys unchanged (step5=fragments etc.).
- 4. Fragments → per-step, **no cap**, selected/not-selected split, chosen/redundant accounting
  (redundant nested faint-red), collapsible assembled-artefact preview.
- Generator `load_case` slow-load fixed (dropped a blocking `analyze_atp_coverage` LLM call:
  ~64s → ~2.4s). Bootloader/GRUB + 5 named cases hidden from Generator lists (display-only).

**Adversarial-review worklist (T33233):**
- #1 device-name reconciliation — DONE.
- #2 physical-step handling — DONE (setup/verify/physical/manual; physical → operator-prompt +
  wait-for-state-change SVT 3009 pattern; manual → yesNo; `_split_sequence` non-mutating).
- #3 fragment quality — PARTIAL (dedupe already done; **added `maps_to` phantom-step validation**;
  line-vs-class + cap deferred).
- #4 provenance divergence — **FIXED + unit-verified** (`_restamp_provenance` remaps original-step →
  `TestCase_<n>` class number; both generate + fix call sites pass the sequence).
- #5 guaranteed-fail default — no change needed (lint already rejects the sentinels).
- #7 zero-reuse marker — ADDED (NO REUSE on uncovered verify steps).

### Open decisions (next session)
`NEXT_SESSION_DECISIONS.md` (repo root): **D1** fragment granularity (whole-class vs render-time
`main()`-trim vs method-level index — the last bumps the never-rebuild-`ck.db` invariant), **D2**
per-step cap (Terrence said no cap — keep unless a real dump is seen), **D3** Py2/old-framework
contamination (recommend soft-warn banner). Resume by getting D1/D2/D3 answers, implement in one pass.
NOTE: physical classification only appears after **re-running Sequence** on a case with plug/unplug
steps; legacy sequences default every step to `verify`.

### State
- Guards green (`guard_db_only`, `guard_framework_readonly`); `/health` 200; Python + JS +
  jinja syntax checked; provenance remap + preview gap-marker unit-tested. Docs synced
  (README status row + PyTest section, SERVER-README PyTest flow + step-kind/provenance notes,
  PROGRESS 2026-07-23).
- `ck.db` invariant intact — no runtime JSON reads, no courier files, no rebuild path added.

## Session Close / Handoff (2026-07-27) — PyTest Creator D1/D3: fragment resolver + Py2→Py3 pre-translation

### Focus
Resolved the three open PyTest Creator decisions (D1/D2/D3) interactively, one at a time, each
grounded in real `ck.db` corpus measurement; then implemented D1+D3 and adversarially tested
them. The 2026-07-23 entry above is not superseded — this is additive. Committed + pushed to
`main` this session (`1478952`). NOTE: `git push` works from this (Linux) seat — the earlier
"no GitHub SSH auth" caveat in prior entries was Mac-seat-specific, not a property of the repo.

### Decisions (rationale preserved in memory, since NEXT_SESSION_DECISIONS.md was deleted)
- **D2 — keep no cap** (no code): chosen/redundant split surfaces dumps; only SELECTED fragments
  reach the Generate prompt, so a display cap doesn't help the token/context concern.
- **D1 — one hardened resolver, not per-library.** The review's "whole-class vs main()-trim vs
  method-index" framing was ART-only; ~423/830 scripts aren't ART-class-shaped and the real
  defect was the blind `loc[0]+60` fallback (fires on 650/3517 `test_case` entries, ~18%, ALL
  legacy). New `_resolve_end`: exact `loc[1]` → next-unit-start−1 (573) → `loc_total` (77) →
  clamp. Helpers now use their real `loc` (dropped the nested-def-mis-slicing regex). `db.py`
  already normalizes all 3 DBs to one schema, so no per-DB dispatch. No `ck.db` rebuild.
- **D3 — deterministic Py2→Py3 via stdlib `lib2to3`** at resolve time (`_translate_py2`), chosen
  over an LLM prompt-steer (deterministic) and over regex (lib2to3 is a real Py2 parser that
  fails loud). Hardened so `status=="translated"` GUARANTEES valid Py3: `expandtabs(8)` (Py2
  tab/space mixing) + `ast.parse` self-verify that degrades to `parse_error` (ship original).
  Untranslatable → ⚠ preview banner + conditional Generate-prompt modernize rule (present only
  when a `py2_flagged` fragment is selected). Translated blocks carry a `(py2→py3)` provenance
  suffix. Scope: Py2 syntax only; old-framework idioms deferred.

### Files touched
- `routers/pytest_create.py` — `_has_py2_tells`/`_translate_py2`, `_unit_starts`/`_resolve_end`,
  rewritten `_resolve_symbol_code` (now returns `(loc, code, py2_status)`), `_fragment_tag` +
  `(py2→py3)`, py2 flags into the fragment pool, preview banner, generate `py2_flagged` context.
- `templates/prompts/pt_generate_script.jinja` — conditional Py3-required rule after Rule 4.
- Deleted `NEXT_SESSION_DECISIONS.md` (all three decisions closed).

### Adversarial testing
Found + fixed a real defect: 9/85 translations were invalid Py3 due to Py2 tab/space mixing
lib2to3 preserves → fixed at source. Final: **27 checks green** (unit + integration);
**6,193 symbols resolved across the whole corpus, zero exceptions, zero empties**; both known
ParseError files ship originals verbatim; conditional prompt steer verified on (423 chars) / off.

### State
- Guards green (`guard_db_only`, `guard_framework_readonly`); server boots, `/health` 200
  (830 scripts, 83816 embeddings). `ck.db` invariant intact — no runtime JSON, no courier
  files, no rebuild path added. Memory added: `d1-fragment-resolver-boundaries`,
  `d3-py2-fragment-translation`.
- **Follow-ups still open:** PyTest Creator Part 3a/3b (offline judging + real tb470 execution),
  gated on `configs/tb470.setup` + a stored testbox profile (Terrence-side prereq).

---

## Session Close / Handoff (2026-07-27c–e — full adversarial review + security/correctness fixes + test suite)

**Theme:** ran a full 14-domain adversarial review of the whole Ask-CK app, then triaged and fixed
the confirmed critical/high findings in batches. All committed + pushed to `main`
(`3ab0474`, `1340d9b`, `a1608d5`). All verification was **in-process only** (FastAPI TestClient,
inert payloads) — no live Zephyr writes, no testbox SSH, no outbound network (a deliberate
constraint this session).

**What shipped:**
- **Backlog reconciliation + 4 quality items** (`3ab0474`): reconciled the stale PROGRESS backlog;
  in-page error/status banners; export refuse-to-write hardening (`wrote_bundle`, stale-bundle-aware);
  `/process` heading-anchor fix (deduped slugs); **first backend test suite** (`tests/`, `pytest.ini`,
  `requirements-dev.txt`, `tool/run_tests.sh`).
- **10 security/integrity fixes** (`1340d9b`): SSH command injection (validate + `shlex.quote`),
  framework-guard bypass (redirection/interpreter/subst/`rsync`/`install`/`cp -t`), stored XSS (new
  `html_sanitize.py` applied at every objective store point), secret leak (`redact_llm_config`/
  `safe_session_dict` — `api_key`/`token` no longer reach the browser or the on-disk `*-session.json`),
  admin-reset wrong session-kind (`pytest`→`pt`), export step-0 overwrite (prepend not clobber),
  library-filename + export `case_key` path-traversal, agent-bridge job-ownership (session-bound),
  CORS lockdown.
- **5 correctness fixes** (`a1608d5`): unified the `llm.py` JSON-parse sites behind one string-aware
  `extract_json_block` (greedy-regex + braces-in-strings silent-drop bugs gone).

**State at close:** working tree clean; **48 tests green**; `guard_db_only` + `guard_framework_readonly`
green; `/health` 200 (830 scripts, 83816 embeddings). `ck.db` invariant intact — no runtime JSON, no
courier files, no rebuild path, still LFS-committed.

**Open for next session** (from `ask-ck/pytest-create/ADVERSARIAL-REVIEW-BACKLOG.md`, ~40 candidates,
**verify before fixing**): the state-machine/correctness cluster (`confirm_step` invalidation cascade,
run_status stale-after-restart, dual-session-instance divergence, `synthesize_steps` first-step drop),
two `_restamp_provenance` provenance issues, and a robustness tail. Two **medium security** items are
intentionally *accepted* for the localhost/single-user model (0.0.0.0-bind no-auth; SSH `AutoAddPolicy`)
— treat as a conscious "accept or harden" decision, not a silent change. The paused review workflow can
be resumed (`resumeFromRunId wf_f53aa173-a88`) to finish verification + full synthesis. PyTest Creator
Part 3a/3b still gated on `configs/tb470.setup`.

> *Superseded by the 2026-07-27g entry: the backlog is CLOSED (62 candidates → 31 fixed / 31
> dismissed / 0 open) and the two "accepted" security items were actioned. Two corrections to the
> text above — the paused workflow was **not** resumable across sessions (the completion pass ran a
> fresh workflow over the recorded rows), and `pytest_create.py:1097` ("first-step drop" cluster
> member) was **refuted**, not fixed.*

## Session Close / Handoff (2026-07-27f) — LLM-button UX + a 3-layer automated-test suite

Two threads this session, both committed + pushed to `main` (`4f990ea`→`e871caa`; tree clean,
guard green, `/health` 200).

**1. LLM-button UX (`27c5d39`).** Closed the three reported gaps — no pressed feedback, no success
signal, no in-flight state (which invited repeat clicks stacking LLM calls). One shared mechanism in
`dom-helpers.js`: `setButtonBusy` (pressed + spinner + working-label + disable + label stash/restore;
returns `false` when already busy so the handler bails — the anti-stacked-call guard) and
`flashButtonDone` (green ✓ / red ✗). Net-new CSS (spinner keyframes + `.btn.is-busy/.is-done/.is-error`
+ reduced-motion fallback). Applied to all ~13 LLM buttons (generator, db-search, pytest via the
shared `ptApi` wrapper, llm health-check, provenance). No backend change.

**2. A three-layer automated-test suite (the bulk of the session).** Built in the sequence the user
chose: E2E first as a **known-good reference**, then the unit layer derived from it.
- **Playwright E2E** (`e2e/`, `4f990ea`) — sparingly-run gate driving the real app through the
  deterministic non-LLM golden path, asserting the export **validation gate blocks** an un-synthesized
  case (Option A — a *green* export is impossible without LLM synthesis, which the design discussion
  established). Selectors grounded in the real DOM via an Explore pass; three real-DOM facts corrected
  the naive plan (collapsed accordion; `#load-status` self-clears; in-progress cases pre-load chosen
  rows). Stable 4/4. Pinned Chromium 1234 downloaded (cache 1228 mismatched PW 1.62).
- **Vitest + jsdom units** (`js-tests/`, `8759903` + `e871caa`) — 47 tests / 5 files, the regular
  layer, re-asserting the E2E-proven behaviours exhaustively and cheaply. DOM fixtures lifted from the
  real `index.html` (throws on a renamed id → drift-detection). Tool chosen (Vitest over Jasmine)
  explicitly for readable diff+source-frame failure output, familiarity set aside. The `db-search.js`
  `merge*` fns were made `export` (one-line, runtime-unchanged) to unit-test them directly rather than
  via a brittle fetch-stub.
- **Unified gate** (`e871caa`) — `tool/run_tests.sh` runs guards + pytest (48) + Vitest (47) in one
  command, failing loudly if Node deps are absent; the E2E stays out (sparingly-run). Verified all
  green, exit 0.

**Layout note:** JS test tooling lives at repo root — `e2e/`, `js-tests/`, `package.json`,
`playwright.config.js`, `vitest.config.js` — deliberately separate from the `static/js` module tree;
`node_modules` + Playwright artifacts gitignored. Two plans (`ck-facelift/PLAN-playwright-e2e.md`,
`PLAN-frontend-unit-tests.md`) authored then marked BUILT+PASSING.

**Still open / next:** no CI runner yet (`.github/workflows`) — the gate is run-before-commit
discipline; a second E2E that reaches a *green* export (pre-seed or LLM-intercept) is parked in the
E2E plan; the adversarial-review backlog (35 candidates) is untouched this session.

> *Superseded by the 2026-07-27g entry below: the 35-candidate backlog was verified and closed
> (19 fixed across four batches, 14 dismissed), and the test counts here (48/47) are now 190/72.*

---

## Session Close / Handoff (2026-07-27g) — adversarial review CLOSED + network hardening + multi-user plan

**Scope.** Finished the verification paused at ~50% in 27c, fixed everything real it found, took
the two accepted-risk security items to a decision, and captured the multi-user end-state as a
plan. 11 commits, `6b50f80`→`94b98cf`, all pushed to `main`.

### The verification
Re-fired over exactly the 35 unadjudicated rows (`wf_f4fcd274-366`, 40 agents, ~19 min, 1.9M
tokens): one verifier per file-cluster against live code, then a dedicated refuting skeptic per
confirmed finding, then synthesis. **21 survived, 14 dismissed** (10 refuted at verify, 4 killed by
the skeptic), 0 unclear. The original run (`wf_f53aa173-a88`) was not resumable — prior session, no
saved script — so this was a fresh workflow over the recorded rows. Nothing was lost; only the
verdicts were missing.

### What shipped
| Commit | Batch | Substance |
|---|---|---|
| `6b50f80` | A — export authority | client-session fallback removed (404), `_can_synthesize` gate (400), downstream invalidation with amber "Stale" badges, atomic bundle write with the Complete marker last. Migration guard so the 43 existing bundles stay re-exportable |
| `40ec299` | B — event-loop blocking | 7 sites wrapped (review named 3; an AST sweep found 4 more incl. `load_case`), a *guaranteed* 180s `claude_agent` self-deadlock killed, background model warmup (cold load measured 16.2s vs the estimated 8.5s) |
| `ba69e22` | C — silent content loss | anchored traceability-note strip, `pyliteral` filter on 13 jinja slots, setup-step provenance fix, tightened echo regex |
| `be9149d` | D — error signals | Claude empty/truncated guards, 2 missing `res.ok`, `keep_ids` pinning, stale run-status sweep, dead `gc()` |
| `e54fdd2` | data | `AWPTCM-T37861`'s unparseable bundle (one `\'`) — 42/43 → 43/43 pass the export gate |
| `6eaa43e` | security | loopback default, `--force` de-hardcoded, SSH host keys pinned |
| `94b98cf` | plan | multi-user auth + per-case locking (no code) |

`d35f061` also landed a small PyTest step-label UX change whose tests had been committed separately
by a parallel stream — committed so the tree and the suite agreed.

### Things worth remembering
- **The finding lists were incomplete more than once.** Batch B named three blocking sites; a
  mechanical AST sweep found seven. Prefer a sweep over the filed list wherever the defect has a
  machine-checkable shape, and leave the sweep behind as a test.
- **A suggested fix was wrong.** Batch C's row proposed reusing `_PROVENANCE_TAG_RX`; it is a loose
  lint check that also matches prose, so it deleted the same comments it was meant to save. The
  tests caught it, inspection did not.
- **Skeptics found two defects while refuting.** The SSE latin-1 mojibake — `text/event-stream`
  makes `requests` default to ISO-8859-1, so every non-ASCII byte on the live vLLM streaming path
  corrupted *silently* and as valid JSON, into stored objectives and on to Zephyr — was the most
  consequential correctness bug of the pass, and it came from an agent disproving a narrower claim.
- **A security test had started passing for the wrong reason.** Batch A's confirm gate ran before
  the path-traversal guard, so the traversal test hit the confirm-gate 400 and never exercised the
  guard it names. Ordering fixed; both tests now pin the *reason*, not just the status code.
- **Test fixtures were leaking into `ck.db`** (cleared memory but not the persisted row). Fixed, and
  two stray rows from earlier runs removed.

### The security decision
Both remaining items were *documented accepted risks*, so they went to Terrence rather than being
fixed unilaterally. Verified live first: the box answered on its LAN IP and an unauthenticated
`POST /push_to_zephyr` returned 200. The new fact the acceptance had not covered — **`--force` was
hardcoded**, disabling `upload_refined.py`'s own "already refined — SKIP" guard on every push — plus
the observation that the "localhost" rationale never fitted the SSH item (that connection is
*outbound* to a lab testbox). All three actions approved and implemented; verified after: LAN
refused, localhost 200, SKIP fires by default and is still overridable with `?force=true`.

### Next session
- **Six open decisions in `ck-facelift/PLAN-auth-and-case-locking.md`** (deferred deliberately),
  notably D1: where identity comes from. Likely an org/IT call, which is why Phase 1 (locking) is
  sequenced first and does not depend on it.
- **Phase 1 is the live one.** The concurrency bug does not need a second user — two tabs on one
  case silently overwrite each other today (`db.py:918` is an unconditional whole-blob upsert keyed
  by case with no owner; 32 write paths reach it).
- **The repo gate is currently red** from `tests/test_cli_docs.py` — untracked in-progress CLI-docs
  work from another stream (`tool/harvest_cli_docs.py`, `tool/cli_lookup.py`), failing independently
  of everything above. My layers: 190 pytest / 72 Vitest green.

  > **✅ CORRECTION — re-verified at session end: the gate is GREEN, ignore the line above.**
  > The other stream fixed those two failures while the doc sync was being written.
  > `./tool/run_tests.sh` → guards OK, **208 pytest** (190 mine + 18 theirs), 72 Vitest, ALL GREEN.
  > Terrence asked for this note specifically so a future reader is not led astray by the stale
  > claim; the commit message on `4b54376` repeats the same stale statement and is likewise wrong
  > (left as-is — a commit message is a point-in-time record).
  >
  > What was still accurate: their CLI-docs work is **uncommitted** — `pytest_create.py`,
  > `pt_extract_sequence.jinja`, `pt_generate_script.jinja`, `tool/cli_lookup.py`,
  > `tool/harvest_cli_docs.py`, `tests/test_cli_docs.py` (plus `ck.db` session churn).
  >
  > **Why it happened, and the rule it implies:** the claim came from a check ~40 min earlier and
  > was restated in a close-out summary without re-running. This tree is shared with an active
  > parallel stream, so **gate status and working-tree contents have a shelf life of minutes** —
  > re-run `./tool/run_tests.sh` and `git status` before acting on either, rather than trusting a
  > statement made earlier in the same session.
- Still no CI runner (`.github/workflows`); the gate remains run-before-commit discipline.

## Session Close / Handoff (2026-07-27h) — CLI grounding + objective-coverage gate + re-judging

**Started from:** Part 3a's criterion-4 result (all 9 gap-fill blocks graded "bad") and the
question *is the generator prompt the problem?* It was — but not in the way it looked.

### What the investigation actually found

Terrence asked five questions; each was answered against the live corpus and the real CLI
docs, not from inference:

1. **Syntax correct?** Python yes (lint-clean, real framework calls). CLI *commands* yes
   (`speed`/`duplex`/`polarity` all verified real). CLI *output assertions* — fabricated.
2. **Resourcing problem?** **Yes.** The generate prompt named `show interface` 27 times and
   contained ZERO examples of its output.
3. **Hallucinated or another dialect?** Hallucinated, but coherently — one invented schema
   applied consistently 57 times.
4. **Best-effort or garbage?** Best-effort. Fragment-backed cases fabricated **zero**; only
   the zero-fragment case did. Reused fragments were already acting as grounding.
5. **All models?** 5 models x 3 cases, one run each. **Every model** fabricated on T33235 —
   including **Opus (35)**. Not a model-quality problem.

**Then a deeper cause:** the fabrication originates at **step 2 (Sequence Extraction)**, not
step 6. It lands in `verify` text and `_render_skeleton` stamps it into the skeleton 4x per
TestCase. T33235: 13 in the sequence -> 57 in the script; the clean cases 0 -> 0. Grounding
step 6 alone would have left the generator arguing with its own skeleton.

### Built

- **`tool/harvest_cli_docs.py`** — renewable harvest of the internal AlliedWare Plus command
  reference (`docs.atlnz.lc/preview/`) into `ck.db`. Full run: **73,006 fetches, 58.6 min,
  ZERO failures**; 4,652 unique commands (993 with sample output), 61,240 product x command
  rows. Content-addressed (a page is byte-identical across families ~96% of the time), so
  per-product rows are a thin support matrix.
- **`tool/cli_lookup.py`** — retrieval, `detect_commands()`, `prompt_block()`.
- **`tool/pt_compare_runs.py`** — snapshot/compare grading runs across sessions.
- **Grounding wired into BOTH prompts**; `tests/test_cli_docs.py` (18 tests).
- **Objective-coverage gate** — `_coverage_report()` + `_coverage_gate_error()`, enforced on
  **Confirm** for *2. Sequence* and *5. Generate*.

### Results

| | before | after |
|---|---|---|
| T33235 `key=value` (sequence / script) | 13 / 57 | **0 / 0** |
| T33233 placeholder `portA` refs | 13 | **0** |
| real CLI formats quoted per case | 0 | 14-23 |
| objective coverage | unmeasured | **3/3 complete** |

Mechanical grades after regeneration: **C1/C2/C3/C6 clean on all three cases.** T33235 is
the headline — previously zero fragments and `n-a`, now 14 fragments, C2 *exactly*, C3
*right*.

### Regressions the grounding itself caused (three fixed, one open)

Each found by checking output rather than trusting the change:
1. `speed 2000` — an invented value; the prompt showed valid syntax but never said arguments
   must come FROM it. Fixed; now emits `speed 2500 (unsupported on 1G copper)`.
2. `show interface eth1` — `prompt_block` picked the LONGEST sample output, which was a **TQ
   wireless AP router interface**, not a switch port. Fixed to prefer the variant the most
   product families share. *Caveat on "commands are standard across devices": the command is,
   but sample OUTPUT is family-specific, and picking the wrong family is silent.*
3. `self.dut.port1.0.1` — a SyntaxError; a CLI port name used as a Python attribute. Fixed.
4. ~~**OPEN:** a hallucinated `framework.ATLibrary` import keeps T33235's `lint_ok` false. The
   existing lint catches it correctly; the prompt's import guidance needs the same treatment
   the CLI grounding got.~~ **CLOSED 2026-07-28 — the diagnosis above is wrong on both
   counts.** The import is valid (`ATLibrary` is a real framework package) and the lint did
   **not** catch it correctly — the lint was the bug. See the 2026-07-28 session entry.

### Product debt found (not fixed)

**The server can return HTTP 200 while the write never reaches `ck.db`.** `db.get_connection()`
caches one SQLite connection per thread; after an external process writes to the DB those
connections hold a stale WAL snapshot, and `_pt_persist` swallows the failure into a `print`
that never fired. Symptom: endpoint returns 13 steps, DB still has 0, `updated_at` unchanged.
Cost real debugging time and forced restart-and-reverify cycles. Related to the §9.4
dual-instance debt but worse, because it presents as success. Fix candidates: refresh/drop the
thread-local cache; make `_pt_persist` surface failures.

### State at close

- Tests: **208 pytest + 72 Vitest green**; both guards green; `/health` 200.
- `ck.db` 420 MB, LFS-tracked; corpora untouched (the CLI tables are a new externally-sourced
  reference, **not** a corpus rebuild — the no-rebuild invariant still holds).
- Judging artifacts under `ask-ck/pytest-create/judging/Port (7)/<case>/`, with the
  pre-grounding baseline preserved at `judging/_runs/2026-07-27a-pre-grounding/` for
  next-session comparison via `tool/pt_compare_runs.py --against`.
- **Part 3b (criteria 5-6) still blocked** on `configs/tb470.setup` (Terrence-side physical
  topology). Note the corrected path: `/home/st-art/st-art/configs/`, NOT under `framework/`.

## Session Close / Handoff (2026-07-28b) — the prompts were the defect

**Started from:** the two items left open by 27h (`framework.ATLibrary` lint red, and the
criterion-4 "checks link state but never the feature under test" false green). Terrence then
set the direction: *"prioritize improving the prompts, the judges are a symptom not the
cause."* That turned out to be exactly right.

12 commits, `ed419aa`→`86993e8`, all pushed.

### The finding that shaped everything else

**Every defect this session came from our own guidance or measurement — none from model
quality.** And the mechanism was consistent enough to state as a rule:

> Where a prompt's prose and its code EXAMPLE disagree, the model implements the EXAMPLE.

Four defects in generated scripts traced directly to wrong examples in our own files, so an
example is not documentation — it is the spec. `tests/test_prompt_examples.py` now executes
each prompt example against real harvested CLI output from `ck.db`; the two worst bugs below
were pure data checks that would have failed in milliseconds for zero tokens.

### The two that were guaranteed wrong on working hardware

1. Rule 3b bound `port = dev.portA` (an `ATSwitch.SwitchPort`) while rule 4d compared
   `[port]` to a token from `split()`. An object never equals a string, so `row` was always
   `None` and **every `show ecofriendly` step failed on every run**. Two rules disagreeing
   with each other, each defensible alone.
2. Rule 4d's worked example had `if/elif` and no `else`. The "command silently failed" case —
   the exact thing rule 4c exists to catch — therefore wrote **no verdict at all**, which the
   framework scores as a pass. A false green nested inside the anti-false-green rule.

### The structural one

Rules 4b/4c/4d — 6,480 chars, 91 lines, including *NEVER HARDCODE A PORT NAME*, *ASSERT ON
THE FEATURE UNDER TEST* and *PARSE THE ROW FOR YOUR PORT* — were all wrapped in
`{% if cli_reference %}`. None of them depend on CLI grounding. So for any case whose text
names no harvested command (physical replug, reboot, traffic/throughput) the generator was
handed a port-bearing skeleton with **every guard against a false green removed**. The step-2
prompt had the same defect. Both now render every critical rule with grounding empty.

### Skeleton deep dive (reduce / clarify / root in truth)

39% smaller — 22,833 → 14,150 chars on a 14-step case. The 3-line idiom example had been
emitted **once per TestCase** (14 verbatim copies; ~49% of each block was comment). Guidance
for the MODEL now lives in the prompt rules; the skeleton carries only what a reader of the
finished test needs — a distinction that matters because skeleton comments ship into every
artefact, and one of them caused 3 false lint warnings by quoting a port.

Assumptions verified against the 830-script corpus rather than assumed: `FEATURES=['ALL']`
291/306, `init_swi('swi_a')` 621/~650, `init_stk('stk_a')` 191/191, `Switch.cmd(log=)` real.
Wrong ones fixed:
- `mode(')#')` is the config-mode idiom (**4,812** uses); `cmd('conf t')` is not (**69**).
  Nothing had ever explained it, which is why a judge called `mode(')#')` "nonsense".
- `port.name` for CLI text (**1,013** vs 241 bare) — was left to chance.
- `{{ devices }}` in the `configure()` example was **never passed**, so it silently fell back
  to `swi_a` every render and never named the real device.
- `.down()` / `.speed` were attributed to `SwitchPort`; they belong to `ATTestBox.Eth`.
  `dev.portA.speed = 1000` does not raise — it creates a dead Python attribute and the
  device is never configured.
- All 14 `| default(...)` filters were DEAD: Jinja fires `default()` only on *undefined*, not
  on `''`, so an empty `verify` rendered `self.passed('')` — and an empty reason emits no log
  marker, making the step invisible in results.
- `stk_b` rendered `init_stk('stk_a')` — a positional rewrite of a name that was already a
  valid `.setup` key.

### Two whole-run failures

- **`distutils.strtobool` was a LIVE break.** Removed in Python 3.12; tb470 runs **3.13.5**.
  Every manual-step script would have `ImportError`ed on the target before running a test.
  `py_compile` proves syntax, never that a module exists — which is how it shipped. Now a
  lint over stdlib modules removed in 3.12/3.13.
- **A manual step could discard an entire run.** `yesNo()` called bare `input()` while the
  runner never writes to stdin → 30-minute block. The timeout then `raise`d *before* writing
  stdout, throwing away every PASS/FAIL already produced. Both halves fixed; `yesNo` is now
  `select`-bounded and fails only its own step.

### The data-loss debt, root-caused

"Returns HTTP 200 but the write never reaches `ck.db`" was **never a lost write**. A
controlled generate-then-read passed. `_pt_get` preferred a per-process cache over the DB, so
an instance with a warm stale copy answered a request **and re-persisted it**, overwriting
newer committed work — indistinguishable from a lost write from outside. Found a **24-day-old
`drafting_server` process** still answering on :8991 from a module directory that no longer
exists; killed it. `_pt_get` now reloads when the DB is newer; `_pt_persist` raises instead
of printing into the void.

### A measurement bug that invented two regressions

`pt_grade` resolved a fragment's `maps_to` step to a TestCase number, falling back to the raw
step number when the step was not a verify step — but fragments legitimately map to SETUP
steps, whose code goes to `TestSet.configure()`. 15 of 41 mappings misresolved. So T33234's
reported **C2 "partially" and C3 "wrong" were pure measurement error**; both are clean
(exactly 10/10, right). A metric I had built on top of that mapping ("ignored reuse") looked
like a finding and dissolved on inspection — worth distrusting new metrics until their inputs
are verified.

### Domain rules the CLI docs cannot supply

The re-extracted sequence asserted *"configure speed 1000 + duplex half … confirm Link is UP
and current duplex half, current speed 1000"*. **Half duplex is impossible at 1 Gig and
above** — a physical constraint no reference page states, since the `duplex` page reads
`{auto|full|half}` unconditionally wherever half is supported at all. Compound cause: the
**source Zephyr step** said "half and full duplex WHERE SUPPORTED" and the extractor dropped
the qualifier. Both rules added (the constraint, and "keep the source step's qualifiers");
1G+half assertions 1 → 0, and `(where supported by the …)` is now carried through.

Also corrected: three CLI claims of mine that the harvest disproves — `show interface` prints
**both** `current …` and `configured …` (asserting `current` after a config command is a
false RED while negotiating); `show interface status` shows `connected` and **`disabled`**,
while `notconnect` appears **zero** times yet I had stated it as fact; and `speed` has
**three** forms, so a step saying "auto" that emits the bare numeric form tests the opposite.

### Environment: Python 3.13.14

Moved the venv to match the testbox (`032f521`), following the procedure already written in
`PLAN-backend-module-split.md` Part 0 — suite green on 3.13 *first*, then rename. `.venv313`
was missing `sentence-transformers` (already in `requirements.txt`), which would have booted
fine and silently degraded to keyword-only search. A venv is **not relocatable**: every
console script hardcodes its build path, so `.venv/bin/pytest` died with "bad interpreter"
after the rename — the documented recipe now includes the fix-up step.

`setup.sh` had two real bugs: `ensure_python` tried bare `python3` **first** despite a comment
claiming newest-first (3.10 here while 3.13 was installed, so a fresh run would have rebuilt
on 3.10), and an existing venv meeting the floor is reused and **never upgraded**. Both fixed;
it now reports the mismatch with the full upgrade recipe.

### Prevention mechanism (Terrence's request)

Four times this session a check fired on its own advice text: the port lint on its guidance
comment, and three of my own tests matching words rather than meaning (one missed a phrase
that wrapped across a newline). `tests/_prose.py` encodes the rules as functions —
`code_lines` / `flat` / `code_fences` — the existing checks were refactored onto it so it is
load-bearing, and all four historical cases are regression-locked. Memory:
`checks-must-not-match-their-own-advice`, `prompt-examples-are-the-spec`.

### State at close

- **295 pytest + 72 Vitest** green on Python 3.13.14; `guard_db_only` + framework-RO green;
  `/health` ok with sqlite-vec loaded and all 83,816 embeddings.
- `ck.db` still the permanent LFS-committed source of truth — no rebuild, no couriers, no
  corpus API. The CLI tables remain an externally-sourced reference, not a corpus rebuild.
- Every prompt fix verified by **regeneration**, not only by test.
- **Open:** T33234 TestCase_8 (configures the partner's `polarity mdi` but never the local
  `polarity auto`; judges 5 bad / 1 good). Part 3b still blocked on `configs/tb470.setup`
  (`/home/st-art/st-art/configs/`). `PLAN-backend-module-split.md` is committed but
  unimplemented — its own conclusion is that Part A (perf/correctness) outranks the split.

---

## Session Activity (2026-07-28c) — Generator: deferred per-step loading (`PLAN-backend-module-split.md` A1)

Started as a code review of `routers/wizard.py` ("this looks monolithic, should it be split?").
The review said yes but argued size was **not** the real defect: two measured performance bugs
and one silent-data-loss bug outranked the refactor. Plan written as
`ask-ck/ck-facelift/PLAN-backend-module-split.md` (11 commits); commit 1 shipped this session.

### What shipped

- **`0c06586` `fix(pytest-create): pt_cases blocked the event loop on two reads`** —
  `_refined_complete_keys()` (rglob) + `dbx.list_pt_progress()` (ck.db) ran bare in an async
  handler: ~18 ms warm, up to **343 ms** cold, exactly when the PyTest Creator panel loads.
  Verified green in an isolated `git worktree` at that commit, so the split is bisectable.
- **`4578030` `perf(generator): defer all three data steps off case load`** — 10 files,
  +972/−261.

### The core change

`load_case` used to build candidate pools for all three DB-review steps, i.e. the server did
work for panels the user had not opened. That pattern has now caused **two** incidents: Step 3's
`analyze_atp_coverage` LLM call (~60 s on every load, removed earlier) and Step 2's 45,427-row
Python scan — **2708 ms bare on the event loop**, freezing every concurrent request including
the agent-bridge long-poll that `claude_agent` self-deadlocks without.

All three steps are now uniform: none works at load; each fetches on first visit via one
endpoint, `GET /step_candidates/{key}/{step}`, dispatched through a `_STEP_BUILDERS` table so
the symmetry is structural. Deleted outright: `_select_related_zephyr_refs`,
`_score_zephyr_candidate`, `_ZREF_WEAK_ALONE`, `db.iter_zephyr_slim`.

    step 1 TestLink   ~0 ms at load  ->   16 ms on open
    step 2 Zephyr     2708 ms !!     ->  175 ms mean / 716 ms max
    step 3 ATP        ~440 ms        ->   44 ms on open

### Three things measurement caught that reasoning had not

1. **The naive swap REGRESSED the flagship case.** For "Port - Auto Negotiation" both "port"
   and "auto" are generic tokens, so `rank_words` collapsed to `["negotiation"]`, all 12 matches
   scored an identical `0.7683`, and ordering fell back to key order — the best cross-ref
   ("interface: port status, speed, duplex and negotiation") landed **9th and dropped out of the
   top 8**, replaced by "Test modem support. TPS says Japan only". The old scorer ranked it 1st
   via an `area_support` boost (`12.0 + 8.0 + 0.8 = 20.3` vs `12.8`). Fix: `db._relevance_score`
   gains an **opt-in `area_words` third tier** — a binary specific/stripped stoplist cannot
   express "too common to rank on, still real area signal". Defaults to `()`; only
   `search_zephyr` opts in, so TestLink/ATP/scripts are provably bit-for-bit unchanged.
   Now rank 1 at `0.8103`.
2. **Hybrid is the wrong default for a panel-open view** — warm, step 2 hybrid is
   763 ms mean / 2692 ms max, *no better than the scan being deleted*, plus a ~11.8 s cold
   model construction landing on a plain panel open. Step builders pin keyword; hybrid stays
   for `/search_*`, where the user actually typed a query.
3. **Two query bugs.** The decision rationale leaked process prose ("Zephyr says covered" →
   "TPS SAYS Japan only" ranked) but must not be dropped wholesale — it moves the QoS case's
   best ref 20→4 and DHCPv6's 143→3. `_DECISION_META_TOKENS` strips only coverage-status words.
   And pre-filtering generics in the builder starved the new area tier. Rule now written down:
   **the caller decides which TEXT is relevant, `db` decides how to WEIGHT it.**

### Tests

+13 Vitest (`js-tests/step-candidates.spec.js`) and +14 Playwright
(`e2e/deferred-step-load.spec.js`) — zero candidate requests at load, exactly one per step
open, no re-fetch on revisit, no row leak across cases, honest "not fetched" placeholder
(distinct from "none found"), both in-flight races, API 400/404 paths. **Both suites were
mutation-checked**: removing the fetch-once memo fails 3 tests, removing the clobber guard
fails 1 — so they are not vacuous.

Widening `_BLOCKING` (adding `_refined_complete_keys` / `_session_progress_map` /
`_select_related_zephyr_refs`) generalized batch B's invariant from "don't block on I/O" to
"don't block, period" — and immediately caught the `pt_cases` bug above. **Caveat learned the
hard way:** a `lambda` passed to `run_in_threadpool` satisfies the runtime requirement while
hiding the call from that AST check. Always dispatch a **named** function; `wizard._cases_index`
and `pytest_create._pt_cases_index` exist for that reason.

### State at close

- **295 pytest + 85 Vitest** green on 3.13.14; guards green. **Playwright 15/15** (14 new +
  golden path) — still NOT in `./tool/run_tests.sh`, so a green gate says nothing about it.
- Live-server verified: `/health` answers in 3–215 ms while a step-2 fetch is in flight.
- **Open:** `PLAN-backend-module-split.md` commits **2–11** (next: A2, `get_data()` →
  `app.state.app_data`). Its *What A1 taught* section records that the plan's
  "expect an improvement, not a regression to defend" assumption was **falsified** — the
  consolidation commits (7–9) need before/after comparison on real data, not just a green gate.
- Unchanged from the previous entry: T33234 TestCase_8, Part 3b blocked on `configs/tb470.setup`.

---

## Session Close / Handoff (2026-07-28d) — first real CLI session on hardware; it falsified a documented rule

**Shape of the session: drove a live device for the first time (tb105 `u5` — an 8-member
x950 stack), used what it reported to review the project's CLI-facing surfaces, and found a
rule that was stated in three places and wrong in all three. Nothing but hardware would have
shown it.**

### Getting onto the device

`ssh tb105` → `u5`. That alias is `minicom --wrap -D /dev/u5`, and `/dev/u5` is a udev
symlink onto `/dev/ttyUSB20`. Minicom needs a TTY, so it cannot be driven from one-shot
commands; the same port was driven with pyserial instead (`/dev/u5`, 115200, read until the
prompt, answer `--More--` with a space). Read-only `show` commands plus a session-scoped
`terminal length 0`. Nothing left on the box.

Answering the question that started the session — which tb105 Eth port reaches the stack:
**`eth2` only**, and it is a shared management LAN, not a dedicated cable. tb105 `eth2`
(10.37.105.100/25, `00:90:0b:2a:11:ad`) ↔ x950 `eth0` (10.37.105.6/25), confirmed from both
ends (`show arp` on the switch lists tb105's eth2 MAC on eth0). 37 ARP neighbours on eth2
with two live simultaneously proves a shared segment. **No data-plane link at all**: none of
tb105's six NIC MACs appear anywhere in the stack's MAC table, even after forcing ARP
broadcasts out all six. Independently corroborated afterwards — `kochi_uni_tb105.setup`
declares zero `tb-` portlinks.

Incidental: tb105 `eth5` is down with **973 carrier changes** — flapping, probably a bad
cable or SFP.

### The defect: "the FIRST index is the chassis/slot" is false

In `portA.B.C`, **A is the STACK MEMBER**, B is the bay (0 = base board, 1+ = a populated
expansion slot), C the port. The live stack reported:

    52 port1.0.  52 port2.0.  52 port3.0.  52 port4.0.
    28 port5.0.  12 port5.1.  28 port6.0.  12 port6.1.
    28 port7.0.  12 port7.1.  28 port8.0.  12 port8.1.

First index 1-8, exactly the `show stack` member IDs; members 5-8 each carry a base board
AND an expansion slot. The wrong claim sat in `pt_generate_script.jinja`, the port-hardcode
lint's own comment, and `test_cli_feature_grounding.py`'s docstring — each **contradicting
itself**, since all three illustrated it with `port1.1.x`, a change to the SECOND index.

Per the governing lesson (the model implements the EXAMPLE, not the prose), generated code
was mostly unharmed. The wrong *rule* was the defect: it leaves no concept that ports span
stack members, which is exactly the case coming next.

### The harvested reference proved it, after my first test got it wrong

That test assumed every doc example was single-unit and asserted the first index was pinned
at 1. It **failed** — `show stack resiliencylink`, `show platform`, `show powerinline` and
`show udld port` all print `port2.x.y`. The failure was better evidence than the hypothesis:
doc examples number a second UNIT, never a second chassis, and `show stack resiliencylink`
carries both `port2.0.11` and `port2.2.11`, so one unit shows two bays under one first index.

### Shipped

- **Index semantics corrected** in all three surfaces, keeping the chassis rationale an
  existing test depends on (it caught the first attempt at dropping it).
- **Two lint warnings** for hazards only visible on hardware: `interface eth0` under config
  (eth0 reports `Vlan: none`, is in no VLAN, yet appears in `show interface status` as an
  ordinary connected row), and enumerate-then-configure with no `stackport` exclusion (stack
  links appear in that table with `stackport` in the Vlan column — such a loop can split the
  stack mid-run). Both key off code shape, not case text. Zero false positives across all
  three real generated scripts.
- **5 tests**, including the data-backed index proof. The guard test caught that the
  stackport check read only `ast.Constant`, so `'show interface {}'.format(p)` — how
  generated code actually writes commands — was misread as config; `_cmd_text` now handles
  `.format()`, f-strings and `%`.
- **`ask-ck/pytest-create/SETUP-FILE-REFERENCE.md`** — the `.setup` schema and a real worked
  example, closing the open TODO in `ART-EXECUTION-CHAIN.md`.

### Built, then reverted — Terrence caught it

A prose alias set (`_STACK_PROSE` + `is_stack_case`) to gate a conditional stack block in the
Generate prompt. **The `.setup` already declares all of it**: `[stack]` (membership),
`[configured_stackport]` (ports never to touch), `[portlink] tb-swi_X = ethN-portA.B.C`
(testbox cabling), `[switch] swi_a = /dev/u0` (console). Inferring any of it from case prose
repeats the mistake this project already recorded for port naming — *a RUNTIME hardware
property; take it from the .setup, do not guess*.

Measured before reverting, and the numbers make the case: `_STK_RX` hits **192/195** corpus
scripts that call `init_stk` (98%) but **0/4** stack cases written in prose. So the gate
would have failed silently on precisely the new cases it was built for.

**The right fix is to PARSE the `.setup`** — nothing in `CK_server` does today. That makes
the stackport rule exact rather than heuristic, and gives the lint the real topology to check
against at Run time. Not started.

### State at close

- **424 pytest + 85 Vitest** green, both guards green, `/health` ok, `ck.db` signature
  unchanged. The count moved 393→398→407→424 during the session — another stream was landing
  ck.db-isolation tests throughout, so treat it as a snapshot.
- **Not reconciled:** the corpus port-literal count reads 350 in the generate prompt and 125
  in the lint comment and test docstring. An independent count gave 294 literals / 9,923
  bound uses — matching neither, because the method differs. Needs whoever took the original
  measurement; left alone rather than picking one and making it look settled.
- `configs/tb470.setup` is **no longer schema-blocked** — it needs tb470's device list and
  cabling, nothing more.
- Unchanged: module-split commits 7-11 (6 dropped in `323c1db`), T33234 TestCase_8,
  Playwright still outside the gate.

---

## Session Close / Handoff (2026-07-28e) — wizard Part A finished, commit 6 dropped, and I deleted a real session row

Continues `2026-07-28c` (A1). This stream owns `ask-ck/ck-facelift/PLAN-backend-module-split.md`.
The other stream (`2026-07-28d`) was working in `pytest_create.py` / prompts concurrently —
every commit below was staged by explicit path, never `git add -A`.

### What shipped

| commit | what |
|---|---|
| `9178659` | `perf(wizard): serve app.state.app_data instead of reloading per request` (A2) |
| `91d86ef` | `fix(wizard): confirm_step silently dropped malformed selections` (A3) |
| `77cb383` | `chore(wizard): logging, dead code, and an inverted pydantic-v2 hedge` (A4+A5) |
| `0b47926` | `fix: tz-aware UTC timestamps (replace deprecated datetime.utcnow)` (commit 5) |
| `323c1db` | `docs: DROP commit 6 (type step4/step5)` + `SURVEY-step4-step5.md` |
| `ac760fd` | `test: isolate the suite from ck.db, and verify it correctly` |
| `7e80289` | `test: two fail-closed layers so a test cannot write the real ck.db` |

**Part A of the module-split plan is complete.** Commits 1-5 done, 6 dropped. Next is
**commit 7** — `refactor: extract wizard/descriptions.py`, the first Part B extraction.

### Three bugs that were filed as hygiene items

- **The pydantic "portability" hedge was inverted.** 19 sites did
  `obj.dict() if hasattr(obj, "dict") else obj.model_dump()`. On v2 `BaseModel.dict()` still
  exists as a deprecated alias, so `hasattr` is ALWAYS true — every site took the v1 path and
  the `else` branches were unreachable. Replaced by `models.model_to_dict`. Deleting the
  `.dict()` fallback outright broke `safe_session_dict`'s llm_config **redaction**;
  `test_security_fixes` caught it, so the fallback stayed, just last instead of first.
- **`print()` → `logging` would have DELETED output.** There was no logging config anywhere,
  so the root logger sat at WARNING and every `log.info()` would have been dropped —
  including `[export] Saved drop-in bundle to …`. `main.py` now calls `basicConfig(...,
  force=True)` (`force` because uvicorn installs its own root handlers).
- **`pytest_create._score_script_candidate` would have crashed if called** — it referenced
  `_PT_GENERIC_TOKENS` / `_PT_AREA_SUPPORT`, defined only in `db.py`. Verified `NameError`.
  The comment directly above it already claimed "no private copy here".

The plan's own dead-code list was wrong: it named `slim_by_key` and `test_id_desc`, which are
**live local variables**. Found the real set by AST scan. Treat every line ref and dead-code
claim in that plan as a hypothesis to verify, not a fact.

### Commit 6 (type step4/step5) was DROPPED — user decision

Evidence in `ask-ck/ck-facelift/SURVEY-step4-step5.md` (21-agent survey; 11 of 13 hazards
survived adversarial verification, 4 blockers). Two independently hand-verified:

- **17 `isinstance(…, dict)` guards.** A model is not a dict, so each takes its `else` branch.
  `wizard.py:2241` would make **export write the placeholder "Objective not yet synthesized"
  into the published bundle**; `:2219-2220` empties the exported testScript; `:296-348` kills
  the invalidation cascade; `db.py:1024-1035` makes the case list report nothing done.
- **The `stale` key is invisible to any census of stored data.** Written `wizard.py:298,303`,
  popped at 4 sites, read only by `generator.js:163,185`. It is **0 of 35** in ck.db because
  it is transient. Default `extra='ignore'` drops it, killing the badge that
  `generator.js:158-161` documents as the guard against a contradictory bundle reaching export.
- **The whole 393-test suite passed with the fields typed.** No test could see any of it.

And the commit had no remaining purpose: its goal was normalizing `confirmed_at`, which has
**zero readers** (6 write sites, no Python or JS reader). `provenance` stays `Dict[str, Any]` —
it is inert (14 writes, 0 reads, display-only in the JS panel), and Terrence called that
correctly: *"it's a non-functional set of data… a blackhole."*

Also recorded there: `REFINED_DIR` is `ask-ck/objective-drafting/refined-cases/` (**not**
`ask-ck/refined-cases/`), holding 43 `zephyr_payload.json` + 2 `*-session.json`. Since
`_backfill_from_refined` copies `testScript` verbatim from the payloads, those 43 are the
shape contract: **276/276 steps exactly `{description, expectedResult}`**, 350/350 with ck.db.

### THE INCIDENT — I deleted AWPTCM-T30649 from the permanent ck.db

Read this before touching test infrastructure.

**What happened.** After isolating the suite from ck.db, I mutation-tested the new guards by
disabling the isolation. One of those guards picked `sorted(real_ids)[0]` and called
`_clear_persisted` on it, on the reasoning that isolation made that safe. It deleted the real
session `AWPTCM-T30649`.

**Why it wasn't caught.** I was verifying "ck.db untouched" with `md5sum ask-ck/var/ck.db`.
**ck.db is WAL-mode** — the delete landed in `ck.db-wal`, and the main file's bytes AND mtime
never changed. The check could not detect any write, and reported "byte-identical" throughout.

**Recovery** came from a `backup()` copy left in the scratchpad from benchmarking 10 minutes
earlier — luck, not design. Restored and verified by full-row hash over all 39 sessions
(`30185cd466774462`), matching the pre-damage state exactly, including the other stream's
`llm_config` switch to `vllm-fast`.

**Four contributing causes, each now closed:**
1. *One layer.* `CK_DB_PATH` redirection was the only protection. → `7e80289` adds a
   fail-closed `connect()` guard that refuses any writable open of the real ck.db regardless
   of `CK_DB_PATH`, plus a reserved-key guard at `db.save_session`/`delete_session`.
2. *Blind verification.* → `tool/ckdb_signature.py` asks SQLite (reads main+WAL together).
   `tool/run_tests.sh` now captures it before/after and **fails the gate** on any change.
3. *A test naming real data.* → that test now writes a throwaway key to the isolated copy and
   asserts the real DB's id set is unchanged. Reserved namespace: `AWPTCM-T99980..T99999`, or
   a non-numeric suffix (real keys are `AWPTCM-T` + digits only).
4. *Mutation-testing safety infrastructure against live data.* Process, not tooling: raise
   the plan first. Layer 1 makes this specific mistake impossible anyway.

**The safeguard's first version did not work, and the test caught it.** I patched stdlib
`sqlite3`, but `db.py:34-38` does `try: import pysqlite3 as sqlite3` (pysqlite3 bundles a
modern SQLite with `enable_load_extension` for sqlite-vec) and it IS installed — so
**`db.sqlite3 is not sqlite3`** and the guard never saw `get_connection()`'s call, the exact
path that deleted the row. What exposed it was writing the test as the **incident path**
(break the isolation, assert it raises) rather than as "does the guard work". Anyone
monkeypatching sqlite in this repo must patch `db.sqlite3`, not just the stdlib module.

### Mutation testing caught three overclaims I had already written up

Worth internalising: a mutation that stays GREEN is the valuable result.

1. `_pt_get`'s stamp comparison — I wrote it up as fixing a live data-loss path. Reverting to
   the string compare left everything green; enumerating the 8 reachable stamp shapes showed
   the two strategies **agree** once stamps are coerced. It is defence-in-depth, and the
   docstrings now say so.
2. `_coerce_utc(None)` — a mutation making it fabricate a stamp stayed green, because pydantic
   resolves `None` on an `Optional[...]` union *before* the annotated validator runs. The
   branch was unreachable; deleted.
3. "plain `cp` of ck.db loses WAL data" — does not reproduce; the WAL happens to be
   checkpointed. `backup()` is still correct (consistent by construction, not by timing), but
   the claim is false as stated, so that property is pinned by source, labelled as such.

### State at close

- **424 pytest + 85 Vitest**, both invariant guards, and the new ck.db signature check all
  green. Count moved 295→…→424 across the session; the other stream was landing tests too.
- `ck.db` at `sessions_rows 30185cd466774462`, **39 sessions** — the exact value from before
  any of this session's work.
- The suite is **~2-3x faster** (12-19s → ~6s) as a side effect: the isolated copy lives on
  local ext4 instead of over NFS.
- **Declined:** a snapshot/restore tool (`tool/ckdb_snapshot.py`, proposed as Layer 2).
  Recovery therefore still depends on a copy existing somewhere. ~30 lines if wanted.
- **Playwright E2E is deliberately outside all of this** — it boots a real server that
  legitimately writes ck.db. Not run this session (standing instruction: never without
  explicit say-so).
- **Next: commit 7**, `refactor: extract wizard/descriptions.py`. Read *What A1 taught* and
  the **A4+A5** section of the plan first — both record assumptions that measurement falsified.

---

## Session Close / Handoff (2026-07-28f) — Part B of the wizard split; 10 of 11 commits done

Continues `2026-07-28e` (which finished Part A). This stream owns
`ask-ck/ck-facelift/PLAN-backend-module-split.md`. Seven commits, `591dbb9`→`e0886c0`, all
gated before landing, staged by explicit path, and pushed.

### What shipped

| commit | what |
|---|---|
| `591dbb9` | `refactor: extract wizard/descriptions.py` (plan commit 7) |
| `1f3b7e4` | `test: the ck.db snapshot cache key could not see a WAL write` (out of plan) |
| `104d3e6` | `refactor: extract llm_config.py + case_registry.py; drop pytest_create's wizard imports` (8) |
| `e15c360` | `refactor: extract session_store.py + wizard/{gates,backfill}.py` (9) |
| `77ab960` | `refactor: decompose export()` (11 — taken *before* 10, deliberately) |
| `03a0aac` | `refactor: rename CK_server/wizard → generator; a lost session write now 500s` |
| `e0886c0` | `test: E2E and smoke checks must not write the permanent ck.db` |

`routers/wizard.py` **2515 → 1971 lines**. Tests **424 → 559** pytest (+85 Vitest unchanged).
**Only plan commit 10 remains**: the atomic `routers/wizard.py` → `routers/wizard/` move.

New modules at `CK_server/`: `llm_config.py`, `case_registry.py`, `session_store.py`, and the
`generator/` package (`descriptions.py`, `gates.py`, `backfill.py`).

### The point of Part B, achieved

`pytest_create.py` opened with **six underscore-private imports out of `routers/wizard.py`** —
a sibling router reaching into another router's internals, so renaming any one of them
silently broke a different feature. Gone. `grep -rn "from routers.wizard import"` now returns
`main.py` and tests only, which is the plan's own acceptance check.

Also gone: `pytest_create._apply_workspace_llm`, a hand-maintained copy of the wizard function
whose docstring literally said "Mirrors wizard…". Proven byte-identical in body (the ONLY
difference was the parameter annotation, `WizardSession` vs `PtSession`) and collapsed into one
duck-typed `llm_config.apply_workspace_llm`. That drift is not hypothetical — the two tools
disagreeing about which LLM to talk to shipped once already, fixed 2026-07-20.

Three duplicate definitions were retired in total. Two the plan predicted
(`_ZREF_GENERIC_TOKENS`, byte-identical in `db.py` and `wizard.py`), one it did not:
`_split_atp_title_description` also existed twice, and `db.py`'s copy was labelled "Verbatim
from wizard.py". Both now live in `db` — the leaf, and `search_atp` calls one itself.

### "Mechanical, no behaviour change" was verified every time

A1's lesson (a supposedly-mechanical query builder shipped two real behaviour changes the
295-test suite could not see) was taken literally. Every moved function was unparsed from
HEAD, had the commit's deliberate renames applied, and compared: **20 of 20 identical**, bar
three in `session_store` where a `'wizard'` literal became a `KIND` constant — asserted
mechanically (`a.replace("'wizard'", "KIND") == b`), not eyeballed.

`export()` got a stronger check, because it writes the artefact that marks a case Complete.
HEAD's monolithic `wizard.py` was loaded as a **second module** (`exec` into a module object
with `__file__` set so `BASE_DIR` still resolves) and both `export()`s run over the same
session with `REFINED_DIR` pointed at tmp: `traceability.md` and `zephyr_payload.json`
byte-identical, whole `ExportResponse` equal, `wrote_bundle=True`. The harness was deleted
rather than committed (it pins HEAD) — **but it is the technique commit 10 should reuse.**

That check earned its keep: comparing responses through the live server first returned an
identical **400** for `AWPTCM-T33233` (Complete on disk, but its session already carries
step4/step5 so backfill does not fire and the reviews are unconfirmed). Identical, and it
never reached the write. **Equivalence on the error path is not equivalence.**

### Three false greens, all in tests, all found by moving code

1. **A test passing for the wrong reason.** `from paths import REFINED_DIR` binds per
   importing module, so when commit 8 moved the reader to `case_registry`, three tests that
   patched `wizard.REFINED_DIR` were affected. Two went red.
   `test_backfill_noop_leaves_gate_closed` **kept passing** — its key has no bundle in the
   real tree either, so "backfill did nothing" was true whether or not the redirect worked,
   while it silently read the production `refined-cases/`. It now asserts the redirect is in
   force before drawing a conclusion from a not-found.
2. **A guard matching its own advice — 5th time in this repo.** My new check that the scratch
   copy uses `Connection.backup()` grepped the whole file, so mutating the call to
   `pass  # src.backup(dst)` left it GREEN: the docstring above it and the commented-out call
   both contain `.backup(`. Now reads **code lines only** via `tests/_prose.py`, which exists
   for precisely this.
3. **An end-to-end test accepting the wrong status.** The lost-write 500 test did not seed a
   session, so `confirm_step` 404'd ("Call load_case first") long before reaching the persist.
   It accepted 404-or-500 and asserted nothing.

A fourth, subtler one was designed out rather than found: renaming
`_get_atp_candidates` → `get_atp_candidates` interacts badly with
`test_event_loop_blocking_batch_b.py`, which matches an unwrapped blocking call by `ast.Name`.
`from generator import descriptions` + `descriptions.get_atp_candidates(…)` would satisfy the
invariant **without being covered by it** — suite green, handler silently unprotected. Three
defences: routers import the names directly, `_BLOCKING` lists both spellings, and a new
`test_blocking_helpers_are_imported_by_name` fails on any attribute-style call. Its `glob` was
also widened to `rglob` ahead of commit 10, where a top-level glob would quietly stop matching
the wizard handlers.

### Moving code moves its logger

`test_pydantic_v2_and_logging.py` asserted "no `print()` in wizard.py" and watched logger
`"routers.wizard"`. Commit 9 moved the persist-failure ERROR that suite exists to pin into
`session_store`, and two of its tests went red. `caplog` and every log filter select by logger
NAME, so this is real, not cosmetic. Both checks are now parametrized over every module Part B
extracted — grepping one file would have silently stopped covering the exact site.

### Two deliberate deviations from the plan

- **`session_store` is NOT generic over `kind='wizard'|'pt'`, and `pytest_create` is NOT
  rewired to it.** `_pt_persist` raises where wizard's swallowed, and `_pt_get` reloads when
  the DB is ahead so a stale process cannot clobber newer work — there is no wizard
  equivalent of the latter. Merging them would be a behaviour change wearing a refactor's
  clothes. The asymmetry is documented in the module.
- **`_authoritative_session` stayed in the router.** It raises `HTTPException(404)`, so moving
  it would drag fastapi into the leaf and cost the framework-free property that makes the rest
  unit-testable. It is an HTTP gate, not storage.

And one reordering: **commit 11 was done before commit 10.** The plan sequenced it last so it
would not be attempted *during* the move; doing it first honours that and leaves commit 10
relocating six short functions instead of one 351-line handler.

### Two behaviour changes, decided by Terrence

- **A lost session write now fails the request.** `persist_session` logged ERROR and returned,
  so a confirm or export answered **200 with the user's work gone**. Raises `SessionWriteError`
  — a DOMAIN error, so the module stays framework-free — and `main.py` registers one app-wide
  handler that turns it into a 500 saying the work was not saved. Closes the asymmetry with
  `_pt_persist`.
- **Case ids sort numerically.** `build_case_groups` sorted on `k.split("-T")[-1]`, a string,
  so `AWPTCM-T100` came before `AWPTCM-T9`. Invisible only because every real key is
  `AWPTCM-T` + five digits. `_case_sort_key` separates numeric from non-numeric so
  `pt-AWPTCM-Txxxx` and malformed rows still sort instead of raising `TypeError`.

### ck.db: the rule, and the incident it came from

Terrence, when I proposed committing a dirty ck.db: *"ck.db is designed to go dirty when users
actually operate in it. When tests are run for smoke checks or E2E or whatever, that data is
useless and shouldn't be propagated."*

The in-process suite was already isolated (`ac760fd`/`7e80289`). **Two paths were not:**

- **Playwright** — `webServer: './run.sh --bg'` on port 8000 with
  `reuseExistingServer: true`. That means "attach to whatever already answers this URL", which
  on a developer's seat is the real-database dev server, and E2E drives real case loads. The
  scratch launcher would never even have run.
- **My own curl smoke checks** verifying commits 7-9. They created a session row for
  `AWPTCM-T45102` and bumped the stamps on `T33233`/`T33241`.

Those three rows were **discarded**: server stopped, `ck.db-wal` + `ck.db-shm` removed *before*
`git checkout -- ask-ck/var/ck.db` (a stale WAL must never replay onto a restored main file),
then verified — back to `sessions_rows 30185cd466774462` / 39 sessions, the exact value recorded
at the close of `2026-07-28e`.

Both paths now go through **`tool/run_scratch_server.sh`**: `CK_DB_PATH` → a WAL-consistent
`backup()` copy (`tool/ckdb_scratch.py`), `PORT` 8123 so it cannot be confused with the dev
server, and `CK_RUN_TAG` so it keeps its own `.ck-server-scratch.{pid,log}` and `--stop` on one
never stops the other. Verified by driving the exact offending case load against it: the real
ck.db stayed byte- AND signature-identical while the copy took the write.
`/health` now reports `db.db_path` + `db.is_permanent_db` — previously the only way to know
which database a running server was on was to read its process environment, which is why this
went unnoticed for so long.

**A related trap, worth internalising:** I initially proposed committing the dirty ck.db, and
when asked whether the WAL was needed, the honest answer is that **an un-checkpointed WAL holds
the NEWEST commits, not stale leftovers** — deleting it loses data. It also explains why
`git status` showed ck.db *clean* for an hour after the writes and *dirty* later with nothing
new written: SQLite auto-checkpointed at 16:03 and folded the WAL into the main file. Same
blind spot, seen from the other side, as the `md5sum` check that hid the `AWPTCM-T30649`
deletion. `1f3b7e4` fixes the same flaw in `tests/conftest.py`, whose snapshot cache was keyed
on the main file's `(size, mtime_ns)` alone and therefore served a **stale** copy after those
writes — caught by `test_the_copy_reflects_the_current_real_db`, unaided, with a failure
message that named the cause.

### State at close

- **559 pytest + 85 Vitest**, both invariant guards, and the ck.db signature check all green.
- `ck.db` clean at `sessions_rows 30185cd466774462`, **39 sessions** — pristine.
- Every commit mutation-checked. Roughly 30 mutations across the session; the ones that stayed
  green were the valuable results (see the `.backup(` grep above).
- **Playwright not run** — standing instruction, never without explicit say-so. Note its
  config changed this session, so the first run will exercise the new scratch-server path.
- **Next: plan commit 10.** See `PLAN-backend-module-split.md` → *Commit 10 — what it now
  faces* for the six test files that read the router as text, and *Part B — as executed* for
  what each finished extraction got wrong.
