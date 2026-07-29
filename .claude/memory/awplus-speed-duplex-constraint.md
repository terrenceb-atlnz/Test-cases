---
name: awplus-speed-duplex-constraint
description: "Half-duplex is impossible at 1 Gig and above — device duplex differences are a consequence of port speed range, not an independent feature flag; NOT documented in the CLI reference"
metadata: 
  node_type: memory
  type: reference
  originSessionId: da9b3bee-f2e0-4c80-972d-0db43518083d
  modified: 2026-07-27T02:20:30.046Z
---

**Half duplex does not exist at 1 Gig and above.** A device whose ports do not go below
1 Gig therefore can never offer `duplex half`. (Terrence, 2026-07-27.)

This explains the cross-family variation in the AlliedWare Plus `duplex` command page:
- x530 / x220 / x550 → `duplex {auto|full|half}`
- x930 / x950 → `duplex {auto|full}`

It is **not** fibre-vs-copper and **not** an independent per-device feature flag (I first
guessed fibre — wrong). The `half` option disappears as a *consequence* of the platform's
speed range.

**Why this matters for generation:** a support matrix keyed on DEVICE alone is insufficient.
`duplex half` is invalid *in combination with* `speed 1000`+ on ANY device, including an
x530 whose page lists `half`. A generator consulting only the x530 page would happily emit
`speed 1000` + `duplex half` — legal per the device, physically impossible.

**Critical limitation of docs.atlnz.lc as a source:** this constraint is **NOT written
anywhere** on the `speed` or `duplex` pages. The x530 page presents `half` unconditionally.
The only trace is the diff between product families, and only if you already know why the
diff exists. **Harvested page text alone will not capture cross-command physical
constraints** — they need to be encoded by hand as rules, or inferred from the real ART
corpus (which encodes them implicitly in working test code).

See [[atlnz-docs-cli-reference]] and [[generator-cli-hallucination]].
