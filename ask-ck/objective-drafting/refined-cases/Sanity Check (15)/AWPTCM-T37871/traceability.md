# Traceability & Supporting Data for AWPTCM-T37871 ()

## Primary Decision

- **AWP-18102** – Reboots 300 iterations (master)
  - Decision confidence: med
  - Rationale: Reboots 300 iterations (master)


## Top Relevant TestLink Cases

(No TestLink selections)


## Zephyr Cross-References (Step 2)
**Relevant Zephyr Scale cases identified**

These cases were reviewed from the full Zephyr database (via `data/zephyr_full/`) for objective style, step structure, and related behaviour.


1. **[AWPTCM-T17338](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T17338)** — Rebooting stack Master for 300 iterations
   - Folder: 
   - Objective: No
   - Justification: Objective: Booting stack for 300 iterations.

Precondition: For x8100:
Fully populated Chassis with CFCs and Lifs.
For General Stack Setups
Stack formed correctly with different nodes.

Status: Approved | Has objective: True | Num steps: 1 | Labels: Stress

Steps:
1. Rebooting Stack Master over night. - repeatedly (atleast 300 iterations)


## ATPyLib Cases (Step 3)


- `1343.1.6` — Stack formation check after rebooting one backup member then another one after 20 seconds.

- `1343.1.2` — Perform rolling reboot on n-stack and check whether stack reforms.

- `1343.4.2` — With large config, perform rolling reboot on the stack and check whether stack reforms.

- `1343.1.80760` — VCS+ duplicate master after rebooting line cards


- ART string: 1343.1.6 + 1343.1.2

## Gaps Noted
The selected ART coverage (1343.1.6, 1343.1.2) exercises stack reformation following backup member reboots and rolling reboot scenarios, providing partial confidence in stack resilience under sequential or staggered member disruption. However, this coverage does not directly address the specific scenario described in AWP-18102 and AWPTCM-T17338: sustained, high-volume master reboot cycling across 300 iterations, which targets long-run stability, resource leaks, and cumulative state degradation that short-duration or single-pass tests cannot surface. The related tests 1343.4.2 (large config rolling reboot) and 1343.1.80760 (VCS+ duplicate master detection) touch on configuration scale and master-duplication edge cases but were excluded from the ART string, leaving master-role-specific endurance and duplicate-master detection under repeated reboot stress only loosely corroborated. Overall, iteration-count endurance, master-specific reboot behaviour, and longer-term observability (e.g., logging consistency, convergence timing drift across many cycles) remain gaps not well covered by the current automated selection.

## Tangential Cases Reviewed
(See selections for full list.)

## ART Test Cases String
1343.1.6 + 1343.1.2

**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.