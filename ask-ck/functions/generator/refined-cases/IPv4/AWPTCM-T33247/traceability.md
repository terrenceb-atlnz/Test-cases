# Traceability & Supporting Data for AWPTCM-T33247 ()

## Primary Decision

- **AWP-4339** – ARP Commands: Clear ARP
  - Decision confidence: high
  - Rationale: ARP Commands: Clear ARP


## Top Relevant TestLink Cases

**Primary + relevant historical TestLink cases reviewed for artefacts and context**

- **AWP-4339** — ARP Commands: Clear ARP
  - Justification: Step: Add Static and Dynamic ARP, clear ARP
a. Add Static ARPs
b. Configure IXIA to send Dynamic ARPs
c. Stop stream
d. Verify ARP table using "show arp" command
e. Use "clear arp" command to erase all Dynamic ARP
NOTE: Static ARPs are not removed by "clear arp" command. You need to use "no arp A.B.C.D" to remove them.
Expected: All Dynamic ARPs removed

Step: Verify Dynamic ARPs are cleared in Hardware table (shell-mode)
a. Send ARP request from IXIA
b. Send ARP reply from IXIA
c. Execute "ip neighbor" command in shell-mode. ARP entries must be reachable.
d. Execute "show arp" and "show hsl fib". ARP entries must be saved.
e. Clear all dynamic ARP
f. Verify from "ip neighbor", "show arp" and "show hsl fib" that ARPs are removed.
Expected: Dynamic ARPs in "show arp" must be REACHABLE in "ip neighbor" (shell)
Dynamic ARPs removed by "clear arp-cache" command must be erased from "show arp", "show hsl fib" and "ip neighbor" commands.

- **AWP-23821** — Clear ARP within a VRF.
  - Justification: Step: 1) Ping a connected device and check ARP is present using show arp.
2)Then attempt to clear the ARP using the command above.
Expected: 1) ARP is present in ARP table
2) show arp should show the ARP has been removed.



## Zephyr Cross-References (Step 2)
**Relevant Zephyr Scale cases identified**

These cases were reviewed from the full Zephyr database (via `data/zephyr_full/`) for objective style, step structure, and related behaviour.


1. **[AWPTCM-T1015](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T1015)** — ARP Commands: Clear ARP
   - Folder: 
   - Objective: No
   - Justification: Has objective: None | Num steps: None

1. **[AWPTCM-T18749](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T18749)** — Clear ARP within a VRF.
   - Folder: 
   - Objective: No
   - Justification: Has objective: None | Num steps: None


## ATPyLib Cases (Step 3)


- `1331.1001.63126` — New command to allow ARPs for autoconfigure address 169.254.x.x from 0.0.0.0 in ARP security

- `1331.2001.21013` — CR21013 - x900-24XT does not send the ARP request.

- `1331.2001.22960` — CR22960 - x900 sends a wrong ARP reply to an ARP request sender after the same VLAN is re-created


- ART string: 1331.1001.63126 + 1331.2001.21013 + 1331.2001.22960

## Gaps Noted
The selected ART tests (1331.1001.63126, 1331.2001.21013, 1331.2001.22960) exercise ARP resolution behaviour: ARP security handling of link-local 169.254.x.x requests from 0.0.0.0, correct generation of ARP requests, and correct ARP reply addressing after VLAN re-creation. They provide indirect assurance that ARP entries are learned and populated correctly, but none explicitly targets the clear ARP operation. Not well covered are the mixed static and dynamic ARP scenario from AWP-4339/AWPTCM-T1015, including whether clearing removes only dynamic entries while preserving static ones, and table state before and after the clear as observed through "show arp". Clearing ARP within a VRF (AWP-23821/AWPTCM-T18749) is also uncovered, including per-VRF scoping of the clear, isolation from the global and other VRF tables, and re-learning of entries after the clear when traffic resumes.

## Tangential Cases Reviewed
(See selections for full list.)

## ART Test Cases String
1331.1001.63126 + 1331.2001.21013 + 1331.2001.22960

**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.