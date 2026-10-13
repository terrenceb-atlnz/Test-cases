# Project 3301 FRER: topology configs T1–T4

Device configs for the four FRER test topologies. The test plan
[AWPTCM-P3275](https://jira.atlnz.lc/secure/Tests.jspa#/testPlan/AWPTCM-P3275) defines them, and
the [Test Strategy](https://wiki.atlnz.lc/awpwiki/index.php/Test:3301_Test_Strategy_-_Frame_Replication_and_Elimination_for_Reliability)
says they are kept so ART and later releases can rebuild the setups. Written 2026-10-14.
**None of them has been loaded on hardware yet.**

Each `.cfg` is the FRER-relevant part of one switch's config, with a `!` comment header that gives
the switch's role and cabling. Management IP, users and licences are not included; add whatever
the bench needs.

## Conventions (all topologies)

| what | value |
| --- | --- |
| Ports | FOG numbering: `port1.0.1` faces the talker or listener, `port1.0.2` and up are the paths |
| Talker MAC | `74da.389c.79c5` (FOG) |
| Listener MAC | `74da.389c.79c6` (FOG); every unicast stream is identified by this DMAC |
| Multicast DMAC (T4) | `0300.0000.0101`: group, locally administered, deliberately **not** an IP-multicast MAC, so IGMP snooping cannot affect it |
| VLAN 1 | non-redundant traffic, the trunks' native VLAN, loop-protected by spanning tree (FOG) |
| VLAN 4 | the talker's VLAN, which the generation instance classifies from |
| VLAN 5, 6 | FRER VLANs, excluded from spanning tree (`spanning-tree vlan-exclude`) |
| Recovery | `match`, `reset-timeout 128`, `terminate` unless stated (FOG defaults) |

**Two additions to the FOG examples:** `hostname`, and `mru 1506` on every port that carries
FRER traffic. The FOG's own limitations section requires 1506 for 1500-byte payloads (the 6-byte
R-TAG is not excluded from the MRU), but its examples omit it. Without it, full-size test frames
are dropped and the result looks like FRER loss. The transit switches carry R-TAGged frames too,
so they get it as well.

## T1 – simple: `T1-simple/`

FOG "Simplest FRER network example". These configs are identical to the FOG's apart from the two
additions above.

| from | to |
| --- | --- |
| talker | A port1.0.1 |
| A port1.0.2 | B port1.0.2 |
| A port1.0.3 | B port1.0.3 |
| B port1.0.1 | listener |

A = generation, B = recovery (terminate). Used by 28 cases: T51103–T51109, T51111, T51117,
T51119–T51125, T51128–T51133, T51139, T51140, T51142–T51145.

## T2 – advanced: `T2-advanced/`

FOG "Advanced configuration example" (IEEE 802.1CB Annex C). These configs are identical to the
FOG's apart from the two additions above. Switches C and D share one FOG config.

| from | to |
| --- | --- |
| talker | A port1.0.1 |
| A port1.0.2 | B port1.0.1 |
| A port1.0.3 | C port1.0.1 |
| B port1.0.2 | E port1.0.3 |
| B port1.0.3 | D port1.0.1 |
| C port1.0.2 | E port1.0.2 |
| D port1.0.2 | F port1.0.3 |
| E port1.0.1 | F port1.0.2 |
| F port1.0.1 | listener |

The FOG diagram shows A's links landing on B port1.0.1 and C port1.0.1 but does not number A's
end. A.2 → B and A.3 → C is taken from A's egress list (`port1.0.2-1.0.3`). Swapping them changes
nothing.

A = generation; B, C, D = FRER-unaware transit (B re-duplicates by flooding); E = recovery,
**not** terminating (it keeps the R-TAG for F); F = recovery, terminate.

**The transit switches must support `spanning-tree vlan-exclude`**: IE220, IE340, IE360, IE560 or
IE570 on 5.5.6-2. They still run spanning tree, because the T2 long run carries non-redundant
traffic on VLAN 1, and the FRER VLAN has to stay out of it. Used by 3 cases: T51126, T51136 and
T51141 (the long run).

## T3 – bi-directional: `T3-bidirectional/`

FOG "Bi-directional FRER". These configs are identical to the FOG's apart from the two additions
above. The cabling is the same as T1, but each end station both talks and listens:

| from | to |
| --- | --- |
| end station `…79c5` | A port1.0.1 |
| A port1.0.2 | B port1.0.2 |
| A port1.0.3 | B port1.0.3 |
| B port1.0.1 | end station `…79c6` |

On each switch, `frer 1` is generation (A → B on VLAN 5, B → A on VLAN 6) and `frer 2` is recovery
on the same ports. Used by 1 case: T51110.

## T4 – wide: `T4-wide/`

**Not in the FOG.** It follows the T1 pattern, sized by Terrence on 2026-10-14 at 3 paths and
2 listeners. There are two streams, and each has its own generation/recovery pair and its own
FRER VLAN, in line with the strategy's working assumption of one FRER VLAN per instance:

| stream | DMAC | FRER VLAN | recovery egress |
| --- | --- | --- | --- |
| 1, unicast | `74da.389c.79c6` | 5 | port1.0.1 (listener 1) |
| 2, multicast | `0300.0000.0101` | 6 | port1.0.1 and port1.0.5 (listeners 1 and 2) |

| from | to |
| --- | --- |
| talker | A port1.0.1 |
| A port1.0.2 / 1.0.3 / 1.0.4 | B port1.0.2 / 1.0.3 / 1.0.4 |
| B port1.0.1 | listener 1 |
| B port1.0.5 | listener 2 |

Used by 2 cases: T51127 and T51134.

The FOG says list and range forms are accepted, but these exact forms have not been tried on a
device: `tsn-stream-id add 1-2` and `egress interface port1.0.1,port1.0.5`. If the CLI refuses
either one, use the form it accepts.

With three equal paths, `match` is enough as long as frames do not arrive out of order between
paths. A case that adds skew changes the instance to `vector`.

## What the cases change on top of these

These configs are each case's starting point. A case's own steps make its variations, for example:
- SMAC + VLAN identification: replace `dmac` with `smac 74da.389c.79c5` in the generation-side
  stream;
- the vector algorithm, other reset-timeouts, and terminate on or off;
- mixed-speed paths: move one path to an SFP+ port;
- extra streams and instances, up to the limits found by testing.

Nine cases name no topology in their precondition:
- six need one standalone switch for CLI, logging and invalid-configuration checks: T51113–T51116,
  T51118 and T51138;
- one needs two switches cabled as a stack (unsupported configurations): T51112;
- two put a third-party FRER device in place of one switch in the topology their steps name
  (interoperability): T51135 and T51137. The AW+ side uses the matching config here.
