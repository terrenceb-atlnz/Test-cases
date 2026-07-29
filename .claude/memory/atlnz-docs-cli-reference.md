---
name: atlnz-docs-cli-reference
description: "docs.atlnz.lc/preview/ is the authoritative AlliedWare Plus CLI reference — reachable, ~3000 command pages with real sample output; the fix for generator CLI hallucination"
metadata: 
  node_type: memory
  type: reference
  originSessionId: da9b3bee-f2e0-4c80-972d-0db43518083d
  modified: 2026-07-27T02:10:19.211Z
---

**https://docs.atlnz.lc/preview/** — internal Allied Telesis documentation preview
(resolves to marvin-builder.atlnz.lc, HTTP 200 from the Linux seat, no auth, no robots.txt).
Being built as a sole source of truth; Terrence pointed at it 2026-07-27.

**Structure (machine-consumable):**
- 37 command-reference documents, one per product family (`x530`, `x930`, `x220`, `x550`,
  `SBx8100`, `AR4050`, GS/IE/SE/TQ series, …).
- `/<product>/index.html` is a **meta-refresh redirect** (curl -L will NOT follow it) →
  `_bookmap_files/frontmatter/cmdref_Introduction.html`, which links ~3,017 per-command pages.
- Per-command URL pattern: `/<product>/<group>_cmd/<command>.html`
  e.g. `x530/int_cmd/show_interface_status.html`, `swi_cmd/speed_ak.html`,
  `swi_cmd/duplex_ak.html`, `swi_cmd/polarity_ak.html`.
- Each page is ~630KB (whole nav tree inlined) but the real content is in `<pre>` blocks —
  only ~2,200 chars (0.3%). **Extract the `<pre>` blocks; never store raw pages.**
- WebFetch's markdown conversion DROPS the `<pre>` sample-output blocks — use
  `curl` + a `<pre>` regex instead.

**Why this matters:** the PyTest Creator generate prompt says `show interface` 27 times and
contains ZERO examples of its output, so every model invents the format. Real output is:

    current duplex full, current speed 1000, current polarity mdix
    configured duplex auto, configured speed auto, configured polarity auto

and `show interface status` is column-formatted (`a-full`, `a-1000`, `connected`/`notconnect`).
Generated code asserts `'speed=1000' in output` / `'state=up' in output` — tokens that never
appear. Ports are `port1.0.1`, not `1/0/1`. Real output also distinguishes **current** vs
**configured**, which is exactly what the Fixed-Speed case tests.

**How to apply:** harvest the `<pre>` blocks per command into `ck.db` and feed the relevant
command's syntax + sample output into the generate prompt. See [[part3-grading-session]] and
[[generator-cli-hallucination]].
