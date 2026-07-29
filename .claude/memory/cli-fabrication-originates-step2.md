---
name: cli-fabrication-originates-step2
description: "The speed=1000 CLI fabrication starts at step 2 (Sequence Extraction), not step 6 (Generate) — step 6 faithfully propagates it 13→57"
metadata: 
  node_type: memory
  type: project
  originSessionId: da9b3bee-f2e0-4c80-972d-0db43518083d
  modified: 2026-07-27T02:51:32.751Z
---

Traced 2026-07-27 while asking why the generate prompt is 26k chars.

**The fabricated `speed=1000, duplex=full, state=up` schema originates in step 2
(Sequence Extraction), NOT step 6 (Generate).** It lands in each step's `verify` text,
which `_render_skeleton` then stamps into the skeleton **4× per TestCase**
(`testCaseMethod`, the FILL comment, `passed()`, `failed()`). Step 6 was being *obedient*
— it copied the verification criterion it was handed.

| Case | step2 `key=value` | step6 `key=value` |
|---|---|---|
| T33233 | 0 | 0 |
| T33234 | 0 | 0 |
| T33235 | 13 | **57** |

Perfect correlation: where step 2 was clean, step 6 was clean; where step 2 fabricated,
step 6 amplified it.

**Root cause is the same as step 6's**: `pt_extract_sequence.jinja` demands
`"verify" = the observable check (exact CLI fields...)` while showing ZERO examples of
what real CLI output looks like.

**Why it matters:** grounding step 6 alone treats the symptom, and actively creates a
contradiction — the injected CLI reference says "never use `speed=1000`" while the
skeleton says it four times per case.

**Detection at step 2 works** (verified) using `_case_payload_fields` (objective + Zephyr
steps, 1.7–2.3k chars) → `cli_lookup.detect_commands`:
T33233 → duplex, speed; T33234 → polarity, duplex, speed; T33235 → show interface, duplex,
speed. Block cost is only 300–800 chars. Note the RAW `zephyr_cases` text is too thin
(T33235 = 29 chars) — must use the refined payload via the server accessor.

**Caveat before acting:** step 2 is human-confirmed for all three cases; regrounding means
those sequences need re-reviewing.

Prompt-size breakdown while investigating (26,043 chars): skeleton **62%** (of which 7,213
chars are `# >>> FILL <<<` comments the model is then told to delete), framework surface
15%, rules 12%, CLI grounding 7%.

See [[generator-cli-hallucination]], [[atlnz-docs-cli-reference]], [[part3-grading-session]].
