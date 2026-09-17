# Traceability & Supporting Data for AWPTCM-T33235 ()

## Primary Decision

- **AWP-25122** – Fixed 1G copper fixed-speed
  - Decision confidence: low
  - Rationale: Fixed 1G copper fixed-speed


## Top Relevant TestLink Cases

**Primary + relevant historical TestLink cases reviewed for artefacts and context**

- **AWP-12294** — Fixed Copper_Unsupported Speed
  - Justification: Step: Set DUT speed to 10 then connect it to HUB. Also, try configure 'ecofriendly lpi' in port then connect to HUB.
Expected: Confirm that the port status column in 'show ecofrienly' will display OFF



## Zephyr Cross-References (Step 2)
**Relevant Zephyr Scale cases identified**

These cases were reviewed from the full Zephyr database (via `data/zephyr_full/`) for objective style, step structure, and related behaviour.


1. **[AWPTCM-T3611](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T3611)** — console speed - testing console speed
   - Folder: 
   - Objective: No
   - Justification: Objective: Verify console speed can be successfully configured and reflected on DUT

Status: Approved | Has objective: True | Num steps: 2 | Labels: Functional, Platform-Test, Automated

Steps:
1. Test changing console speed on active session
awplus(config)#line con 0
awplus(config-line)#speed <console-speed-in-bps>
Check active session after changing the console speed.
Re-login to DUT using new console speed and check current console speed
NOTE: Test with different console speed baud rate
2. Check configured non-default console speed settings
awplus(config)#line con 0
awplus(config-line)#speed <console-speed in-bps>
Saved current config - running-config and startup-config
Changed console speed to default
awplus(config-line)#speed 9600
NOTE: Test with different console speed baud rate

1. **[AWPTCM-T13265](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T13265)** — QSFP port speed cofiguration check
   - Folder: 
   - Objective: No
   - Justification: Objective: QSFP default configuration setting is chenged on CR-52580.
So, we need to check QSFP setting.
http://jira.atlnz.lc/browse/CR-52580

Precondition: Please save and reboot disable stack "no stack num enable".
DUT1 - connect - DUT2
Procedure.
QSFP+(fiber) TEST
1. connect QSFP module to DUT1 and DUT2.
2. check "show interface port" information.
ckeck point
- link up
- configured duplex auto, configured speed auto
- current duplex full, current speed 40000
3. change setting
DUT1
- configured duplex full, configured speed 40000
4. check "show interface port" information.
DUT1
- link up
- configured duplex full, configured speed 40000
- current duplex full, current speed 40000
DUT2
- link up
- configured duplex auto, configured speed auto
- current duplex full, current speed 40000
5. change setting
DUT2
- configured duplex full, configured speed 40000
6. check "show interface port" information.
DUT1
- link up
- configured duplex full, configured speed 40000
- current duplex full, current speed 40000
DUT2
- link up
- configured duplex full, configured speed 40000
- current duplex full, current speed 40000
QSFP (DAC: Direct Attached Cable) test
1. connect QSFP module to DUT1 and DUT2.
2. check "show interface port" information.
ckeck point
- link up
- configured duplex auto, configured speed auto
- current duplex full, current speed 40000
3. change setting
DUT1
- configured duplex full, configured speed 40000
4. check "show interface port" information.
DUT1
- link down
- configured duplex full, configured speed 40000
- current duplex full, current speed 40000
DUT2
- link down
- configured duplex auto, configured speed auto
- current duplex full, current speed 40000
5. change setting
DUT2
- configured duplex full, configured speed 40000
6. check "show interface port" information.
DUT1
- link up
- configured duplex full, configured speed 40000
- current duplex full, current speed 40000
DUT2
- link up
- configured duplex full, configured speed 40000
- current duplex full, current speed 40000

Status: Approved | Has objective: True | Num steps: 0


## ATPyLib Cases (Step 3)


- `1342.301.12` — Command Execution: Speed Bundle speed 100 speed auto shutdown speed 100 speed auto

- `1346.1001.20040000` — Confirm link comes up at speed 40000.

- `1346.1001.20000010` — Confirm link comes up at speed 10.

- `6009.2000.75853` — Console speed setting not changed by CLI, with reboot test

- `1346.1002.1` — Confirm link comes up at all supported speeds.

- `1346.1001.20` — Confirm link comes up at all supported speeds.


- ART string: 1342.301.12 + 1346.1001.20040000 + 1346.1001.20000010 + 6009.2000.75853 + 1346.1002.1 + 1346.1001.20

## Gaps Noted
The selected ART coverage exercises link establishment across supported speeds on fixed copper (1346.1001.20, 1346.1002.1) including specific fixed-speed points such as 10M and 40G, CLI-driven speed configuration and bundle interaction (1342.301.12), and console speed persistence across reboot (6009.2000.75853), so the core fixed-speed negotiation and configuration paths are reasonably addressed. Not well covered is the negative path central to this case: forcing an unsupported or mismatched fixed speed against a hub or legacy partner and observing that the port correctly remains down rather than reporting a misleading link state. Automation also does not address the 'ecofriendly lpi' configuration interaction with fixed-speed copper links, nor the associated power-saving/EEE behaviour when the peer does not support it. Observability aspects drawn from the manual case — port status column reporting, and the console-speed checks reflected in the Zephyr cross-references — remain largely manual, as does the QSFP-side speed configuration behaviour, which falls outside the fixed 1G copper scope of the automated set.

## Tangential Cases Reviewed
(See selections for full list.)

## ART Test Cases String
1342.301.12 + 1346.1001.20040000 + 1346.1001.20000010 + 6009.2000.75853 + 1346.1002.1 + 1346.1001.20

**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.