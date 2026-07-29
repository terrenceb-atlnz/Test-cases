# PLAN — Deterministic CLI-bounded permutation-expander (DEFERRED — plan-only)

**Status:** NOT STARTED. Design idea captured 2026-07-29 at Terrence's request ("I
absolutely do want to plan building a deterministic permutation-expander subsystem, it is
very useful, just not this session"). This file is a resume-cold brief, not an approved plan.
The complementary half — wiring the objective into Generate + baking it into the `.py` — was
built the same day (see "Relation to work already done").

## The idea

Objectives are vague **on purpose**: "test all supported speeds", "auto/full/half where
applicable". Today the LLM sequence-extraction step (step2) re-enumerates those axes into
concrete steps, and it does so **differently every run** — three divergent T33235 sequences
were observed in one session (memory `cli-fabrication-originates-step2`). An LLM prompt that
says "enumerate all permutations" cannot fix this: enumeration by a sampling model is
non-deterministic by nature. Only a **deterministic code expander** makes it stable and
complete.

So: a subsystem that takes a multi-value axis (speed, duplex, autoneg, mdi/mdix, …) and
expands it to the **full CLI-valid permutation cross-product**, each cell a best-effort test
case, **bounded by CLI-defined limits** — never by fuzzy inference of what a given port
"supports". The CLI syntax defines the domain (there is no `speed 1` command), so "all
supported speeds" becomes a reachable, reproducible target instead of a guessing game.
Terrence: *"endlessly puttering about with fuzzy logic to define 'what supported speeds
exist' is a waste of everyone's time … every single type of multi-possibility logic should
include all permutations of said possibilities and be checked as a best-effort test case."*

## Why it is a subsystem, not a prompt rule

- **Determinism** is the whole point — same objective + same device ⇒ byte-identical
  expansion. A prompt cannot guarantee that.
- **Completeness** — a code cross-product never silently drops a cell; a model does.
- **Boundedness** — the domains come from authoritative data (see below), and the physical
  prunes are a fixed rule table, both auditable.

## Data already in place (built this session)

`cli_commands` was reloaded from the authoritative device zips (`load_cli_docs_from_zips.py`,
committed 2026-07-28: 37 devices, 68,301 rows). It now carries a **`tables`** column (JSON of
the validity/parameter tables) and a **`notes`** column (JSON `{section: prose}`). The
expander reads each axis's domain from `cli_commands.tables` — this is the "CLI-defined
boundary". `cli_commands` is the one **renewable** reference table (its own writer,
content-addressed), so nothing here touches the immutable `ck.db` corpus invariant.

## Constraints the design must honour (already established)

- **Half duplex is impossible at ≥1 Gig** (memory `awplus-speed-duplex-constraint`). The CLI
  `duplex` page lists `{auto|full|half}` unconditionally, so this is NOT in `tables`. It is the
  one place hardware knowledge enters — encode it as a **deterministic PRUNE rule**
  (speed≥1000 × half ⇒ drop, or mark as expected-no-link), never as fuzzy inference.
- **`speed` has three non-interchangeable forms** — `speed {N}` (force), `speed auto [N…]`
  (negotiate, advertise-only), `no speed` (default). The expander must respect force-vs-
  advertise; already spelled out in `pt_extract_sequence.jinja` and memory.
- **Do NOT assert which speeds a port supports** — a hardware property the CLI does not state.
  Unsupported-speed cells become **best-effort/negative** cases ("link may not come up"),
  never a hard PASS.
- **Never hardcode a port name** — expansion is over axis values only; the port stays the
  `.setup`-bound attribute (hardware-agnostic).

## Open design decisions (resolve in the planning session)

1. **Plug-in point.** (A) post-process the LLM's extracted sequence — detect a multi-value
   axis in a step, expand deterministically into one entry per CLI-valid combination; or
   (B) pre-compute the permutation matrix from objective + `tables` and feed it into
   extraction as a scaffold the LLM fills per cell. (A) keeps the LLM's step semantics;
   (B) gives the LLM less room to diverge. Leaning (A) as post-process = smallest blast radius.
2. **Axis-domain parser.** The shape of `cli_commands.tables` JSON per axis needs a robust
   reader (speed values, duplex values, autoneg on/off, mdi/mdix). Verify against several
   devices — the table markup is not perfectly uniform.
3. **Explosion control.** speed(≤8) × duplex(3) × autoneg(2) × mdix(3) is large. Options:
   full cross-product / pairwise (all-pairs) reduction / per-axis independent sweeps /
   objective-scoped (only axes the objective names). Whatever the cap, **log what was
   dropped** — silent truncation reads as full coverage (memory rule). Leaning
   objective-scoped + per-axis sweep, with full cross-product available on request.
4. **Physical-prune rule table.** Where do half-duplex≥1G (and any siblings) live — a small
   data file vs code? Must be testable in isolation.
5. **Negative-cell marking.** How an unsupported/impossible combination is represented — an
   expected-link-down verify vs a skip — and how that flows into the verdict.
6. **Traceability + coverage gate.** Every expanded cell needs a `zephyr_step_idx` back to its
   source step; the existing coverage gate (every Zephyr step → ≥1 sequence entry) must still
   pass and not double-count the expansion.
7. **Determinism test.** A test asserting the same (objective, device) yields an identical
   expansion across runs — the property that justifies the whole subsystem.

## Relation to work already done (2026-07-29, Thread B)

The objective now flows into Generate and is baked into the emitted `.py` header
(`_objective_comment_lines` + skeleton `==== OBJECTIVE ====` block + `pt_generate_script.jinja`
rule 1a). That keeps the **declarative context** in the output. The expander is the
complementary deterministic fix for **enumeration instability**. Together they close the
"shit-in-shit-out" loop: objective context (done) + reproducible permutation coverage (this
plan).

## First step when resumed

Dump `cli_commands.tables` for `speed`/`duplex`/`polarity` across ~5 varied devices (a
standalone, a chassis, an x950, an IE-series, a 10G box) and eyeball the JSON shape — decision
#2 gates everything else, and it is a 20-minute read against real data before any code.
