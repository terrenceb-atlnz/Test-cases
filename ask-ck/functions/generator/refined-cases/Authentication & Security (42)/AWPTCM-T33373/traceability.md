# Traceability & Supporting Data for AWPTCM-T33373 ()

## Primary Decision

- **AWP-9616** – Roaming authentication
  - Decision confidence: med
  - Rationale: Roaming authentication


## Top Relevant TestLink Cases

**Primary + relevant historical TestLink cases reviewed for artefacts and context**

- **AWP-156** — The Roaming Authentication
  - Justification: Step: Move to other port on same authenticator.
Expected: Each device can communicate without re-authentication.

- **AWP-9616** — Roaming with dot1x authentication
  - Justification: Step: Roaming with dot1x
Expected: Roaming auth supports MAC authentication and Web authentication, not dot1x. Confirm that roaming does not work with dot1x.

- **AWP-381** — The Roaming Authentication
  - Justification: Step: Repeat Roaming Auth overnight.
Expected: Roaming auth is possible
Communication is successful.
No error, No memory leak.

- **AWP-9546** — Disconnect no auth roaming
  - Justification: Step: no auth roaming disconnected
Expected: If the supplicant attached interface is linked down, roaming does not work, re-authentication is executed.



## Zephyr Cross-References (Step 2)
**Relevant Zephyr Scale cases identified**

These cases were reviewed from the full Zephyr database (via `data/zephyr_full/`) for objective style, step structure, and related behaviour.


1. **[AWPTCM-T12621](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T12621)** — static mode + Roaming
   - Folder: 
   - Objective: No
   - Justification: Core roaming on static auth mode — authorized MAC retained / FDB when supplicant moves

1. **[AWPTCM-T12622](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T12622)** — static mode + Auth Roaming Disconnect
   - Folder: 
   - Objective: No
   - Justification: auth roaming disconnect behavior on link-down / static mode

1. **[AWPTCM-T12624](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T12624)** — dynamic mode + Auth Roaming Disconnect
   - Folder: 
   - Objective: No
   - Justification: Roaming disconnect with dynamic VLAN mode

1. **[AWPTCM-T12658](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T12658)** — Combination of Two-Step auth and Roaming auth
   - Folder: 
   - Objective: No
   - Justification: Two-step + roaming interaction (maps to TL AWP-14932 family)

1. **[AWPTCM-T12827](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T12827)** — Auth-MAC with VCS - Roaming authentication
   - Folder: 
   - Objective: No
   - Justification: Auth-MAC roaming under VCS

1. **[AWPTCM-T12954](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T12954)** — Roaming Auth - Multi-mode, no guest VLAN, per port, dynamic VLAN
   - Folder: 
   - Objective: No
   - Justification: Multi-mode roaming auth combination matrix


## ATPyLib Cases (Step 3)


- `1340.1001.39052` — CR39052 - SBx8100 do not ARP resolve when roaming to other port leaving the linkup.

- `1331.1001.30437` — Even if Supplicant moves from the authentication port port to non-authentication port, the authentication information is not


- ART string: 1340.1001.39052 + 1331.1001.30437

## Gaps Noted
Roaming with dot1x (AWP-9616) shows dot1x roaming deliberately does not work while MAC/Web authentication roaming does, and ART cases 1340.1001.39052 and 1331.1001.30437 automate the specific link-down/port-move scenario where authentication state must persist without re-authentication — reasonably covering the core "no re-auth on same-authenticator port move" behaviour and the ARP-resolution regression it guards against. However, automation does not exercise the dot1x-specific negative case (confirming roaming explicitly fails with dot1x per AWP-9616), the disconnect/link-down re-authentication trigger (AWP-9546), or the overnight repeat-roaming endurance/memory-leak check (AWP-381). It also lacks coverage for VCS and multi-mode/dynamic-VLAN roaming contexts (AWPTCM-T12827, AWPTCM-T12954) and combined two-step/roaming authentication interplay (AWPTCM-T12658), leaving cross-mode and long-duration reliability observability as manual-only gaps.

## Tangential Cases Reviewed
(See selections for full list.)

## ART Test Cases String
1340.1001.39052 + 1331.1001.30437

**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.