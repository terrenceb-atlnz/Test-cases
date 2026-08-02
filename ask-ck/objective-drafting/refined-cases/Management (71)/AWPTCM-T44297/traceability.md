# Traceability & Supporting Data for AWPTCM-T44297 ()

## Primary Decision

- **AWP-5551** – LLDP TLV options
  - Decision confidence: med
  - Rationale: LLDP TLV options


## Top Relevant TestLink Cases

**Primary + relevant historical TestLink cases reviewed for artefacts and context**

- **AWP-5551** — LLDP TLV - test all TLV options available
  - Justification: Primary match — enables different TLV subsets per port and verifies each port transmits only its selected TLVs

- **AWP-5508** — Command Line Handler: lldp tlv-select
  - Justification: Command-line handler for `lldp tlv-select` and its `no` form, enumerating every base/dot1/dot3 option the case must exercise

- **AWP-5523** — Command Line Handler: lldp med-tlv-select
  - Justification: Command-line handler for `lldp med-tlv-select`, covering the MED half of the TLV option set

- **AWP-5541** — Enable LLDP with no TLV options
  - Justification: Negative/default baseline — LLDP running with no TLV options selected, defining the mandatory-only transmitted frame

- **AWP-5552** — LLDP enabled on one port (transmit only) with all option TLV's selected
  - Justification: Happy path at the other extreme — transmit-only port with all optional TLVs selected, including systems-capabilities behaviour when IPv4 forwarding is off

- **AWP-17661** — LLDP-CFG-018:enable specified optional TLVs
  - Justification: Modern LLDP-CFG-018 equivalent: enable specified optional TLVs, gives current-format steps and expected results

- **AWP-17662** — LLDP-CFG-019:Validate no optional TLVs via the specified ports
  - Justification: Modern LLDP-CFG-019 counterpart: validate no optional TLVs on specified ports — the deselect/teardown verification

- **AWP-5560** — Transmit management address TLV
  - Justification: Per-TLV verification pattern (management-address) showing how a single selected TLV is confirmed in the transmitted frame



## Zephyr Cross-References (Step 2)
**Relevant Zephyr Scale cases identified**

These cases were reviewed from the full Zephyr database (via `data/zephyr_full/`) for objective style, step structure, and related behaviour.


1. **[AWPTCM-T9536](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T9536)** — LLDP TLV - test all TLV options available
   - Folder: 
   - Objective: No
   - Justification: Direct equivalent of the primary TestLink case AWP-5551 — exercises every available LLDP TLV option

1. **[AWPTCM-T9720](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T9720)** — Command Line Handler: lldp tlv-select
   - Folder: 
   - Objective: No
   - Justification: CLI-handler coverage for `lldp tlv-select`, the command that selects the optional TLVs under test (AWP-5508)

1. **[AWPTCM-T9733](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T9733)** — Command Line Handler: lldp med-tlv-select
   - Folder: 
   - Objective: No
   - Justification: CLI-handler coverage for `lldp med-tlv-select`, the LLDP-MED half of TLV selection (AWP-5523)

1. **[AWPTCM-T9528](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T9528)** — Enable LLDP with no TLV options
   - Folder: 
   - Objective: No
   - Justification: Negative counterpart — LLDP enabled with no TLV options selected (AWP-5541)

1. **[AWPTCM-T9537](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T9537)** — LLDP enabled on one port (transmit only) with all option TLV's selected
   - Folder: 
   - Objective: No
   - Justification: Transmit-only port with all optional TLVs selected; same all-options intent on a single port (AWP-5552)

1. **[AWPTCM-T9763](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T9763)** — LLDP-CFG-018:enable specified optional TLVs
   - Folder: 
   - Objective: No
   - Justification: Configuration-suite variant that enables specified optional TLVs (AWP-17661)

1. **[AWPTCM-T9764](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T9764)** — LLDP-CFG-019:Validate no optional TLVs via the specified ports
   - Folder: 
   - Objective: No
   - Justification: Configuration-suite variant validating no optional TLVs on specified ports (AWP-17662)

1. **[AWPTCM-T9545](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T9545)** — Transmit management address TLV
   - Folder: 
   - Objective: No
   - Justification: Per-TLV verification of the management address TLV, one of the selectable options (AWP-5560)


## ATPyLib Cases (Step 3)


- `2016.5.3` — a) mibBasicTLVsTxEnable: This variable lists the single-instance-use basic management TLVs, each with a bit map indicating the system ports through which the referenced TLV is enabled for transmission. AND lldpPortConfigTLVsTxEnable OBJECT-TYPE SYNTAX BITS { portDesc(0), sysName(1), sysDesc(2), sysCap(3) }

- `1332.1001.8` — Check that the information contained in the LLDP frames are consistent with the CLI

- `2016.3.29` — a) At least one Management Address TLV should be included in every LLDPDU. AND b) Since there are typically a number of different addresses associated with a MSAP identifier, anindividual LLDPDU may contain more than one Management Address TLV.

- `2015.3.29` — a) At least one Management Address TLV should be included in every LLDPDU. AND b) Since there are typically a number of different addresses associated with a MSAP identifier, anindividual LLDPDU may contain more than one Management Address TLV.

- `2016.3.24` — An LLDPDU should not contain more than one System Capabilities TLV.

- `2016.3.19` — An LLDPDU should not contain more than one Port Description TLV.

- `1332.2001.8` — Check that switch's response LLDP frames have TIA TR-41 Committee TLVs

- `1332.1001.1` — This test checks the conformance of the LLDP-MED Capabilities Policy TLV received from the switch on ethA


- ART string: 2016.5.3 + 1332.1001.8 + 2016.3.29 + 2015.3.29 + 2016.3.24 + 2016.3.19 + 1332.2001.8 + 1332.1001.1

## Gaps Noted
The selected ART coverage addresses the standards-conformance side of TLV transmission: the MIB bit-map that mirrors per-port TLV selection (2016.5.3), a broad CLI-to-frame consistency check (1332.1001.8), presence and single-instance constraints for the Port Description, System Capabilities and Management Address TLVs (2016.3.19, 2016.3.24, 2016.3.29, 2015.3.29), and the MED/TIA TR-41 portion of the option set (1332.2001.8, 1332.1001.1). It does not reach the case's central claim of exclusivity and per-port divergence — a port carrying only its own selected subset while a neighbouring port carries a different one — because those checks assert that a TLV is present and non-duplicated rather than that unselected TLVs are absent. The two boundary configurations from TestLink are similarly unautomated: the mandatory-only frame with no optional TLVs selected, and the transmit-only port with the full optional set, including the capabilities-bit content shift when IPv4 forwarding is off. Deselection is thin as well, with no automated counterpart to the no-forms retiring a TLV from an already-running frame, nor to the command handlers' full base/dot1/dot3 keyword enumeration and their grouped or malformed variants. The dot1/dot3 optional TLVs also receive little attention relative to base and MED, and nothing in the automated set retains a per-port configured-versus-transmitted TLV comparison, so a partial-transmission regression would surface only under direct frame inspection.

## Tangential Cases Reviewed
(See selections for full list.)

## ART Test Cases String
2016.5.3 + 1332.1001.8 + 2016.3.29 + 2015.3.29 + 2016.3.24 + 2016.3.19 + 1332.2001.8 + 1332.1001.1

**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.