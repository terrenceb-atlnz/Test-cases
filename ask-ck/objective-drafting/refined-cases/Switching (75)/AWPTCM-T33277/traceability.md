# Traceability & Supporting Data for AWPTCM-T33277 ()

## Primary Decision

- **AWP-9637** – STP/RSTP interoperability
  - Decision confidence: med
  - Rationale: STP/RSTP interoperability


## Top Relevant TestLink Cases

**Primary + relevant historical TestLink cases reviewed for artefacts and context**

- **AWP-9637** — Interoperability with STP/RSTP
  - Justification: Primary match named by the decision — MSTP/STP/RSTP interoperability objective, the anchor for the main verification statement

- **AWP-13049** — Interop with STP and RSTP
  - Justification: Closest procedural twin: explicit DUT-in-RSTP vs partner-in-STP mode configuration plus link/traffic verification steps — supplies the concrete happy-path sequence

- **AWP-9464** — Interop with STP & MSTP on other devices.
  - Justification: 3-switch mixed-mode topology (RSTP default / STP / MSTP) — gives the multi-device setup and role assignment the thin case omits

- **AWP-9370** — Interop with   RSTP  & MSTP on other devices.
  - Justification: Sibling interop objective (RSTP with MSTP on other devices) — covers the reverse mode pairing so the artefact set spans both directions

- **AWP-7541** — Interoperability with RSTP
  - Justification: Two-device RSTP loop with named linking ports — concrete cabling/loop-control setup for a minimal-device variant

- **AWP-9431** — RSTP timers are 802.1D2004 based
  - Justification: RSTP timers per 802.1D-2004 with continuous ping across a root-port disconnect — the convergence-time assertion that makes STP/RSTP interop measurable rather than cosmetic

- **AWP-11428** — RSTP - Disconnect / Reconnect Links
  - Justification: Negative/recovery path: disconnect and reconnect links, verify re-convergence — including physical plug/unplug as a listed method

- **AWP-9424** — RSTP Debugging
  - Justification: RSTP/MSTP debug modes (packet, protocol, timer) — reporting and evidence-collection commands for diagnosing an interop failure



## Zephyr Cross-References (Step 2)
**Relevant Zephyr Scale cases identified**

These cases were reviewed from the full Zephyr database (via `data/zephyr_full/`) for objective style, step structure, and related behaviour.


1. **[AWPTCM-T20293](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T20293)** — Interoperability with STP/RSTP
   - Folder: 
   - Objective: No
   - Justification: Exact title match for the primary decision AWP-9637 'Interoperability with STP/RSTP' — sibling xSTP case, shows the expected interop step style from the MSTP side

1. **[AWPTCM-T20386](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T20386)** — Interop with STP & MSTP on other devices.
   - Folder: 
   - Objective: No
   - Justification: Confirmed TestLink AWP-9464 'Interop with STP & MSTP on other devices' in the same /xSTP/RSTP folder — direct mixed-protocol interop coverage

1. **[AWPTCM-T20454](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T20454)** — Interop with   RSTP  & MSTP on other devices.
   - Folder: 
   - Objective: No
   - Justification: Confirmed TestLink AWP-9370 'Interop with RSTP & MSTP on other devices' — STP-folder counterpart of the same interop matrix

1. **[AWPTCM-T6671](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T6671)** — Interop with STP and RSTP
   - Folder: 
   - Objective: No
   - Justification: Confirmed TestLink AWP-13049 'Interop with STP and RSTP' — same intent, useful for wording even though it is filed outside /xSTP

1. **[AWPTCM-T20385](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T20385)** — Interoperability with Alliedware (at least 3 switches)
   - Folder: 
   - Objective: No
   - Justification: RSTP interoperability against AlliedWare with at least 3 switches — same folder, gives the multi-switch topology pattern interop needs

1. **[AWPTCM-T20312](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T20312)** — Interoperability with Cisco
   - Folder: 
   - Objective: No
   - Justification: xSTP interoperability with Cisco — third-party 802.1w/802.1D peer coverage that complements the AlliedWare interop cases

1. **[AWPTCM-T20353](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T20353)** — RSTP timers are 802.1D2004 based
   - Folder: 
   - Objective: No
   - Justification: Confirmed TestLink AWP-9431 'RSTP timers are 802.1D2004 based' — the timer/standards baseline that STP/RSTP interop depends on

1. **[AWPTCM-T20453](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T20453)** — Interoperability with Alliedware (at least 3 switches)
   - Folder: 
   - Objective: No
   - Justification: STP-side 'Interoperability with Alliedware (at least 3 switches)' — mirrors T20385 and covers the legacy-STP half of the interop pair


## ATPyLib Cases (Step 3)


- `2021.4.1` — NOTE 2: This ability of MSTP Bridges to communicate the full set of MSTP information on shared LANs to which RSTP Bridges are attached avoids the need for the Port Protocol Migration machines to detect RSTP Bridges.

- `2031.10.1` — An administrative Force Protocol Version parameter (17.13.4) causes an RSTP Bridge to use STP compatible BPDUs and timer values on all Bridge Ports. Rapid transitions are disabled (Test for Root Port)

- `2031.10.2` — An administrative Force Protocol Version parameter (17.13.4) causes an RSTP Bridge to use STP compatible BPDUs and timer values on all Bridge Ports. Rapid transitions are disabled (Test for an Edge Port)

- `2021.5.5` — a) STP BPDUs,...,are transmitted if Force Version is 0 b) RST BPDUs,...,are transmitted if Force Version is 2 e) The MSTP state machines allow full MSTP behavior if Force Protocol Version is 3 or more.

- `2021.23.4` — Once the mdelayWhile timer has expired in CHECKING_RSTP state, receipt of a Config or TCN BPDU on the Port (rcvdSTP is TRUE) causes a transition to SELECTING_STP

- `2021.23.8` — Once the mdelayWhile timer has expired, receipt of an MST BPDU on the Port (rcvdRSTP is TRUE) causes a transition to CHECKING_RSTP.

- `2021.23.1` — When the Port is operable, transition to CHECKING_RSTP state occur and BPDUs are sent depending on ForceVersion

- `2021.23.7` — The SENSING state entered is from CHECKING_RSTP on mdelayWhile expiry. If mcheck becomes TRUE, indicating that management has requested re-checking of the appropriate BPDU type to send, the state machine returns to CHECKING_RSTP.


- ART string: 2021.4.1 + 2031.10.1 + 2031.10.2 + 2021.5.5 + 2021.23.4 + 2021.23.8 + 2021.23.1 + 2021.23.7

## Gaps Noted
The selected ART coverage is strongest on the protocol-migration mechanics that underpin STP/RSTP interoperability: Force Protocol Version driving STP-compatible BPDUs and timer values, the suppression of rapid transitions on both root and edge ports, and the CHECKING_RSTP / SENSING / SELECTING_STP transitions governed by mdelayWhile expiry, received BPDU type and mcheck — together with the full-MSTP-information case that removes the need for migration detection on shared LANs. That is per-port conformance behaviour on a stimulated bridge, observed at the BPDU level. What the manual material asks for and automation does not reach is interoperability as a topology property: mixed-mode multi-device arrangements pairing a default-RSTP bridge with STP-only and MSTP peers, the reverse mode pairings, third-party and multi-switch same-vendor sets, and the data-plane consequence of migration — loop-free forwarding and uninterrupted traffic across the resulting port roles. Convergence remains unmeasured, since the 802.1D-2004 timer behaviour is only meaningful as a re-convergence time under continuous traffic when a root port is lost, and the disconnect/reconnect recovery path depends on physical link interruption as the stimulus. The automation also has no equivalent of the operator-facing observability the manual cases lean on when interop fails: packet, protocol and timer debug output plus port state and role reporting as diagnostic evidence.

## Tangential Cases Reviewed
(See selections for full list.)

## ART Test Cases String
2021.4.1 + 2031.10.1 + 2031.10.2 + 2021.5.5 + 2021.23.4 + 2021.23.8 + 2021.23.1 + 2021.23.7

**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.