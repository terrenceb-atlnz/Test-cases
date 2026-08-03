---
name: generator-cli-hallucination
description: "All 5 models fabricate AlliedWare Plus CLI output formats — a resourcing gap (prompt shows zero sample output), not a model-quality problem"
metadata: 
  node_type: memory
  type: project
  originSessionId: da9b3bee-f2e0-4c80-972d-0db43518083d
  modified: 2026-07-27T04:08:48.720Z
---

Investigated 2026-07-27 after criterion-4 judging found all 9 gap-fill blocks "bad".

**It is a RESOURCING problem, not a model problem.** Evidence: across the Part 2B matrix
(5 models × 3 cases, one run per model), **every single model** fabricated `key=value` CLI
assertions on T33235 — vllm-fast 39, vllm-thinking 52, haiku 13, sonnet 39, **opus 35**.
A defect that survives Opus is not fixable by swapping models. Only Opus produced any
correct `port1.0.x` port naming (15 instances); all others used none.

**Root cause:** the generate prompt mentions `show interface` 27 times and contains ZERO
examples of what it returns (`port1.0` count = 0, `awplus` = 0, sample output = 0). The
model is asked to assert on output it has never seen, so it invents a plausible schema.

**Two distinct failure modes — do not conflate:**
1. **T33235** (zero fragments, pure gap-fill) — 57 fabricated `key=value` asserts, Cisco-style
   `'1/0/1'` ports. Garbage in the *assertions*, though structurally template-perfect.
2. **T33233/T33234** (fragment-backed) — ZERO fabricated key=value. They inherited real CLI
   idioms from the reused fragments. **Fragments are already an effective grounding
   mechanism**; the failure is concentrated where there were none.

So it is a **best-effort guess, not absolute garbage**: correct structure, correct commands
(`speed`/`duplex`/`polarity` all verified real), correct intent — wrong output schema.

**FIXED 2026-07-27.** Harvested the real reference into ck.db and grounded BOTH prompts
(step 2 `pt_extract_sequence.jinja` and step 6 `pt_generate_script.jinja`) via
`tool/cli_lookup.py::prompt_block`. Measured result across all three cases:

| | before | after |
|---|---|---|
| T33235 `key=value` in sequence | 13 | **0** |
| T33235 `key=value` in script | 57 | **0** |
| T33233 placeholder `portA` refs | 13 | **0** |
| real output formats quoted | 0 | 14-23 per case |

Verify with: `python3 tool/pt_grade.py` and grep the scripts for `(speed|duplex|state)=`.

**Regressions the grounding itself caused (all fixed, keep an eye out):**
- `speed 2000` — an invented value; the prompt showed valid syntax but never said
  arguments must come from it. Fixed with an explicit "every ARGUMENT must come from the
  reference" rule.
- `show interface eth1` — `prompt_block` picked the LONGEST sample output, which was the
  TQ wireless AP's router interface. Fixed to prefer the variant the MOST product
  families share (switches all print `port1.0.1`).
- `self.dut.port1.0.1` — a SyntaxError; the model used a CLI port name as a Python
  attribute. Fixed with a "port name is CLI TEXT, never an identifier" rule.

Still open: the model occasionally emits `framework.ATLibrary`, a hallucinated import the
existing lint correctly rejects.

**Coverage limit found 2026-08-03 — the grounding is real but INERT for most cases.** The fix
above works where it fires; it often does not fire. Measured against `ck.db`:

- **Only 1,250 of 6,323 `cli_commands` rows (20%) have a `sample_output`.** Where no variant of
  a command has one, the model is exactly as unanchored as before the fix.
- **~591 of 3,297 distinct command names (18%) are stored DE-HYPHENATED**, taken from doc-page
  slugs — `show spanningtree` where the row's own `syntax` column holds
  `show spanning-tree [interface <port-list>]`. `detect_commands` matches literal stored names,
  so **correctly-spelled AlliedWare Plus text never matches those rows.** (The exact count
  depends on the detection heuristic; 18% is a conservative floor.)
- Net effect measured across the 53 refined cases: **1 case receives real CLI sample output.**

So "we ground the prompt in real CLI output" is true of the mechanism and false of most runs.
Fixing it is normalisation (match on a de-hyphenated *and* hyphenated form) plus harvesting more
sample output — not a change to `prompt_block`, which ranks correctly once it has candidates.

Related: [[part3-grading-session]], [[physical-interaction-steps]] (T33235 step 6's
shutdown/no-shutdown substitution is a separate, non-CLI defect).
