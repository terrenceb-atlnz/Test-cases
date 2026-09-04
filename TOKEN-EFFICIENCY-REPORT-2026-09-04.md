# Token-efficiency investigation — report for review

**Date:** 2026-09-04 · **Author:** Claude (Fable 5.1), afternoon session · **For:** Terrence
**Scope:** the PyTest Creator's LLM spend, prompted by a ~$44 per-unit generate on AWPTCM-T44297
and a usage-limit spike the same morning. Terrence's brief: *"prompt bloat, the lack of cache,
the harness overhead, everything"*; judge quality in-context, not with judge calls.

Everything measured here is reproducible from two sources that are still on disk: the server
debug log `CK_server/debug-log/sess-wn1ql4ajvm-mt93mbg2.jsonl` (257 records with `usage`) and
the CLI's own transcripts under `~/.claude/projects/` (raw `cache_creation` / `cache_read`
token fields, which the server folds away). Probe spend for the day: about $5.40.

---

## 1. Findings, in one page

1. **Nothing in this run touched the org vLLM.** All 257 calls were Claude Opus 4.8, via the
   `claude -p` CLI on the server (`claude_code`) or on the user's machine (`claude_agent`).
   The handoff's step one ("does vLLM discount the prefix?") was the wrong question.

2. **The prompt cache never hit. Not once, on either transport.** Every per-unit call wrote
   14k–27k tokens to the 1-hour cache tier and read back a constant ~2.5k (Claude Code's own
   fixed head) or nothing — even for 38 calls inside five minutes. The 2026-09-02 template
   reorder that hoisted the invariant blocks into a shared prefix was inert. Cause: Claude
   Code's harness system prompt sits in front of ours and varies per invocation, so no prefix
   of ours is ever a prefix of the previous call.

3. **The harness was more than half of every call.** From the server's working directory the
   CLI folded both CLAUDE.md files **and the 24 KB memory index** into every call: 16,104
   tokens for a trivial prompt against 2,602 from a bare directory. My own repair of the
   memory symlinks at 12:19 turned the memory index on for the server and made every server
   call ~10.5k tokens dearer than the day before (21,865 → 32,378 for the same prompt).

4. **A per-unit note inside the shared rules capped our own prefix at 27%.** The
   `DEVICE NAME RECONCILIATION` paragraph (built from each unit's fragments, 6 variants) was
   interpolated at rules line 72 and stranded 8,400 identical bytes after it. This is the
   `device_note` decision the 2026-09-02 session deferred pending cost figures.

5. **Fragments are 27% of all prompt text as re-sends.** One 6.2k-character fragment goes to 32
   of 38 units — 193k characters, 12.5% of the whole pass, on its own.

6. **Per-unit produces better units; whole-script produces a better script** (§4). The per-unit
   defects are integration defects with three root causes, all preventable deterministically.

7. **Sonnet 5 is close to Opus on the units sampled at ~55% of the cost; Haiku 4.5 is not
   viable for unit generation** (§5). For step matching, Sonnet 5 matches Opus's picks at
   ~40% of the cost and a third of the latency.

**Shipped today, both approved by Terrence, gate green (1263 passed):** the transport fix (§3)
and the device-note move (§3). **Nothing else was changed.** §6 lists the decisions still open.

---

## 2. Where the money went (T44297, whole debug log)

| bucket | calls | input tokens | output tokens | cost |
|---|---:|---:|---:|---:|
| per-unit generate | 108 | 3,736,507 | 667,113 | $43.55 |
| step match | 114 | 2,463,472 | 172,123 | $17.15 |
| whole-script generate | 4 | 259,317 | 160,555 | $5.60 |
| fix | 2 | 263,529 | 137,963 | $5.53 |
| gather fragments | 4 | 152,050 | 96,356 | $3.66 |
| review | 2 | 138,828 | 30,077 | $2.24 |
| extract sequence | 3 | 91,703 | 21,003 | $1.02 |
| **total** | **237** | **7,105,406** | **1,285,190** | **$78.76** |

The last complete 38-unit pass alone: 852,599 input tokens, 181,272 output, **$12.82**, median 53 s
per unit. The whole-script generation of the same case (an earlier 30-step revision) was one
call: 104,962 input, 58,715 output, **$1.58**, 673 s.

Costs are the CLI's `total_cost_usd`, i.e. list API prices. On a seat the real constraint is the
usage limit, and cache **reads** weigh roughly a tenth of writes against it — so every finding
below matters more for the seat than the dollar figures suggest.

### 2a. Anatomy of one per-unit call (production, before today)

| component | tokens | notes |
|---|---:|---|
| our rendered prompt | ~16,400 | 39,660 chars; code-heavy text runs ~2.4 chars/token on this tokenizer |
| Claude Code core system prompt | ~2,600 | "you are an interactive coding agent…" |
| CLAUDE.md × 2 + memory index | ~13,500 | auto-discovered from the cwd; memory half new today |
| **total, all written to 1h cache** | **~32,400** | read back: 0 |

### 2b. Anatomy of the rendered prompt (38 real prompts, 1.54M chars)

| section | per prompt | share | distinct / 38 | cacheable before | cacheable now |
|---|---:|---:|---:|---|---|
| fill rules | 14,516 | 36% | 6 → 1 | first 5.3k only | all |
| reviewer-approved fragments | 13,179 | 33% | 38 | no | no (see §6.5) |
| framework surface | 4,920 | 12% | 1 | yes | yes |
| CLI reference | 4,032 | 10% | 25 | no, genuinely per-unit | no |
| exact block to return | 2,135 | 5% | 38 | no, genuinely per-unit | no |
| unit, case, devices, output format | ~1,400 | 4% | mixed | partly | partly |

Shared prefix: 10,934 chars (27%) before the device-note move; 19,447 (48%) after, simulated
on the 38 real prompts.

---

## 3. What was measured, what shipped

### 3a. The probe (15 calls, ~$3.60)

Same 39.7k-char real unit prompt, two identical sequential calls per configuration, from the
server's cwd. Usage read straight from the stream-json envelope.

| configuration | context / call | 2nd-call cache read | cost 1st → 2nd |
|---|---:|---:|---|
| A. production flags as they were | 32,378 | 0 | $0.37 → $0.37 |
| B. A + `--exclude-dynamic-system-prompt-sections` | 32,269 | 1,059 | $0.34 → $0.34 |
| C. A + `--system-prompt "<one line>"` | 29,676 | **29,674** | $0.42 → $0.14 |
| D. A + `--bare` | fails | fails | needs `ANTHROPIC_API_KEY`; OAuth never read |
| E. C + neutral cwd + `--no-session-persistence` | **16,525** | **16,523** | $0.27 → $0.11 |

In C and E the model actually generated the unit (~3,800 output tokens), so most of the second-call
cost is output; input fell from ~$0.18 to ~$0.02. A trivial prompt from four places isolated the
harness: 16,104 tokens (repo cwd), 16,070 (repo root), 13,452 (repo cwd with `--system-prompt`,
still carrying CLAUDE.md + memory), 2,602 (bare directory).

### 3b. Shipped: transport (Layer 0) — `llm.py`, `agent_jobs.py`, `agent_bridge.py`, `agent.js`, `ck_agent.py`

- `--system-prompt` **replaces** the harness prompt with the caller's steer (or a one-line
  default). It was `--append-system-prompt`; the reversed test explains why.
- The CLI starts in `llm._cli_neutral_cwd()` (under the system temp dir): nothing to
  auto-discover.
- `--no-session-persistence`: 66 transcripts a day stop landing in `~/.claude/projects`.
- The agent path (`ck_agent.py`) mirrors all of it and additionally gains `--tools ""` and
  `stream-json`; the server's steer now rides with each job. Before this the agent ran with
  tools, under the harness prompt, unsteered — one unit call went agentic for 20 turns and
  528k input tokens trying to read `/home/st-art/framework`.
- Tests: `tests/test_claude_cli_transport.py` (reversed + 4 new), new
  `tests/test_ck_agent_transport.py` (11, drives a real fake `claude`), `test_agent_job_pickup.py`
  (+1). Docs: `SERVER-README.md`, `ask-ck/agent/README.md`.

### 3c. Shipped: the device note moved below the line — `pt_fill_rules.jinja`, both generate templates

The note now renders beside the per-unit content in `pt_generate_step.jinja` and after the
rules in `pt_generate_script.jinja`. The whole-script render snapshot was regenerated after a
line-by-line diff showed exactly the moved paragraph (3 lines out, 4 in). Prefix pin test
updated to give the two fixture units *different* notes and still require the full invariant
region to be shared.

### 3d. Expected effect on a 38-unit pass (input side, list prices)

| | per call | per pass |
|---|---|---|
| production yesterday | 22k written | ~$8.3 |
| production this morning (memory index on) | 32k written | ~$12.3 |
| after Layer 0 alone | ~12k written + ~4.5k read | ~$4.7 |
| after Layer 0 + device-note move | ~8k written + ~8.3k read | ~$3.2 |

Output (~$4.5 per pass) is unchanged by any of this. Step match (38 calls, 5k prompt under 16k
harness) goes from ~$8 to ~$1.9 per pass. **These are projections from two-call probes; a real
fan-out with 8 concurrent workers has not been run on the new transport yet** — that is step
one in §6.

---

## 4. Whole-script vs per-unit — judged in-context

I read both artifacts in full: the whole-script generation of 2026-09-01 (29 classes, from the
30-step sequence of that day, one Opus call, $1.58) and the 38 raw per-unit chunks of 2026-09-03/04
as they landed before Review or Fix (Opus, $12.82 for the pass). Neither has run on hardware; I
cannot assess runtime behaviour, only what the code would do. The case objective and the
current 38-step sequence were my reference.

### 4a. Whole-script

**Strengths.** Every case is self-contained: it sets its own TLV selection before observing,
so no case depends on a predecessor's state. Device handles are used consistently and match the
frame (`dut` = DUT, `dutA` = partner, `ck_far_port`). The suite `configure()` plants known
values — `description CK-T44297` on the test port and a management IP on vlan1 — so later
content comparisons have something concrete to compare against; that is genuinely good test
design. Zero handle errors, zero helper-signature errors, tear-downs restore what they changed.

**Weaknesses.** It never captures a packet. Having bound no testbox tap for the DUT↔partner link,
it observes "the wire" through the partner's `show lldp neighbors detail` and the DUT's own
`show lldp local-info`. For roughly a third of the verifies that is a materially weaker
stand-in, and for a few it is a false green:
- TC5 (no duplicate single-instance TLVs) counts label occurrences in the neighbour display,
  which prints each field once regardless of what was on the wire — it cannot fail.
- TC4 and TC13 ("no optional TLV on the wire") check only that the port description is gone.
- TC16/17 accept `'MED' in nb_med` as proof of correctly encoded organisationally specific TLVs.
- TC22 substitutes `lldp faststart-count 15` for an out-of-range TLV argument; TC12/13 call
  `dut.get_all_ports()`, which I could not confirm exists on the framework surface.

**Verdict:** coherent and honest as a script, weak on wire fidelity. A reviewer would accept it
with edits to the capture-centric cases. "good" for structure, "bad" for the observation model
on about 10 of 29 cases.

### 4b. Per-unit, raw

**Strengths.** Unit-local verification is markedly stronger: real `tcpdump` captures with
35–70 s waits, raw TLV-header walks by type (4/5/6/7/8, end marker 0), per-LLDPDU duplicate
counts, MED OUI 0x0012bb + subtype checks, `show lldp interface` row-matching that deliberately
avoids the legend false green. About 25 of 38 units honour their `verify` text more faithfully
than the whole-script equivalents.

**Weaknesses — three systematic root causes, none of them "the model can't do it":**
1. **Handle confusion, ~30 of 38 units.** The frame binds `dutA` as the DUT and `dut` as the
   partner; most units configure `dutA` but read the test port as `dut.portA` (unbound → renders
   as `interface None`), because the fragments say `dut`. The device note, whose whole purpose
   was this, did not prevent it. Also `.portB`, `tb.ethB`, `stk_a` used as if bound (TC13, 23,
   24, 35).
2. **Cross-unit state dependence, ~6 units.** TC6 ("with the complete set now selected") relies
   on TC1–5 having selected TLVs, but each of those tears its TLV down again; TC37 likewise.
   These fail for setup reasons, not product reasons. The whole-script model never made this
   mistake because it saw the whole sequence at once.
3. **Idiom divergence, ~7 units.** Two units copy a library fragment's
   `start_tcpdump(tb.ethA, filter=…)` / `stop_tcpdump()` shape that no other unit uses (TC8, 9);
   TC10 issues `wireless` → `management address` (a misapplied command set); TC11 invents a
   global `management address`; TC20 issues `no lldp tlv-select` with no argument.

Review found 12 of these across two calls; Fix then rewrote 9 of 38 classes at 64k output tokens.

**Verdict:** as *units*, better than whole-script; as a *script*, not runnable until Review+Fix.
Roughly 40% of what Review found was lint work (handle set, call shape, capture-with-no-wait);
the rest is semantic.

### 4c. What this says about the shape of the pipeline (Q3/Q4/Q5/Q6)

- **Q3 — did parallelising reduce quality?** It improved the units and broke the integration.
  Net, before Review+Fix, the per-unit script is worse; after, it is better than the whole-script
  one on the capture-heavy steps. The cost of that "after" was ~$5.50 of Fix and two Reviews.
- **Q4 — return to single prompt?** No. The whole-script observation model is the weaker one for
  this case class, and it truncated at 29 classes on a 30-step sequence (the later 38-step
  sequence would be worse). The right hybrid is not "small cases whole-script"; it is per-unit
  plus deterministic integration checks plus a self-contained-unit rule — the three root causes
  above, each cheap to prevent.
- **Q5 — is Assemble+Lint a deviance source?** No. It is where root causes 1 and 3 should be
  caught, mechanically. Today it catches neither.
- **Q6 — engineer Review so Fix is rarer.** Shift left: bound-handle lint, call-shape lint
  against the framework surface, capture-with-no-wait heuristic, and a per-unit prompt rule
  that every unit establishes its own precondition. That removes roughly half of this run's
  Review findings before the LLM sees the script.

---

## 5. Smaller models — Sonnet 5 and Haiku 4.5, judged in-context

Five representative units (setup, TC1, TC8, TC12, TC36) and four step-match prompts were
regenerated on Sonnet 5 and Haiku 4.5 with the production Layer-0 flags and the production
steers, from the same stored prompts Opus received. I read every output; deterministic checks
(parse, class shape, bound handles, tcpdump call shape, banned modules) ran on all fifteen.

### 5a. Unit generation

| unit | Opus (production) | Sonnet 5 | Haiku 4.5 |
|---|---|---|---|
| setup | correct roles, both switches configured, link up, clean teardown. $0.36 | same structure, **but uses `self.testSet.X` inside `TestSet` methods, where `self` is the TestSet — AttributeError at run time**; starts a suite-wide capture. $0.17 | configures only the DUT side, inherits the fragment's `dut.portA` on the wrong device, teardown does not undo config. $0.06 |
| TC1 | row-matched CLI check + raw TLV type-4 walk, 35 s wait. $0.39 | same approach; regex hunts a `Base TLVs Enabled for Tx` label that may not appear in the per-port table form (possible false fail); `re` used without import. $0.25 | adds a `configure()` the frame forbids, captures for 2 s (always empty), tests `lldp_mac_tlv` as "port description", legend false green. $0.06 |
| TC8 | wrong library tcpdump shape, no wait, MED TLV as mgmt address (Review's findings). $0.25 | same wrong shape, **adds the 35 s wait**; same TLV class; slightly better than Opus here. $0.11 | invents `start_tcpdump(port=, pcap_file=)`, reads a `/tmp` pcap with scapy, imports inside `main`. $0.04 |
| TC12 | strong: local-info + `show system`, capture, decoded dump, four label comparisons + capabilities. $0.45 | comparable: same comparisons via attribute probing on the decoded layer with graceful fallbacks; 131 s, 14k output tokens. $0.33 | sends an invented trigger frame, 5 s capture, treats `lldp_sn_tlv` as a serial number, substring checks that cannot fail. $0.05 |
| TC36 | right structure; parser keys do not match its own parser (Review finding); 35 s wait. $0.35 | same approach, regex parser; `.get(k,-1)` equality passes vacuously if a key is absent; 5 s wait. $0.20 | error counters only, omits the frame-consistency half of the verify, 2 s waits. $0.06 |
| **five units** | **$1.80** | **$1.07 (59%)** | **$0.26 (14%)** |

**Judgement.** Sonnet 5 tracks Opus closely: on four of five units the approach, the API use and
the failure modes are the same, once slightly better (TC8), once slightly worse (TC1's label
regex). The setup unit's `self.testSet` error is a real defect a lint would catch (unbound
attribute on the TestSet) and Opus did not make it. Haiku 4.5 is not viable: every one of its
five units invents an API, picks the wrong TLV class or breaks the frame, and its 2–5 s
captures can never see a 30 s-interval LLDPDU.

Caveat: n=5 units, one case, one run each. Sonnet's outputs also arrive faster on four of five
units but took 131 s on TC12.

### 5b. Step matching

Overlap with the reviewer's confirmed selections (three prompts from the current sequence; a
fourth prompt came from an older sequence revision and is excluded):

| model | precision | recall | agreement with Opus's picks | cost / call | latency |
|---|---|---|---|---|---|
| Opus (production) | 18/18 | 18/18 | — | $0.12 median | 21 s |
| Sonnet 5 | 16/17 | 16/18 | 16 of 19 | ~$0.055 | 7–13 s |
| Haiku 4.5 | 12/14 | 12/18 | 12 of 20 | ~$0.055 | 58–102 s |

Note the reviewer's confirmed set was seeded by Opus's own suggestions, so "precision against
the reviewer" flatters Opus. Even so: Sonnet 5 returns essentially the same shortlist at under
half the cost and a third of the latency. Haiku returns shorter lists and is no cheaper, because
it spends 5–11k output tokens getting there.

---

## 6. Decisions open for Terrence

1. **Run a real 38-unit pass on the new transport** and read the cache fields from the CLI
   transcripts (`--no-session-persistence` means they are no longer written — the server's
   debug log `input_tokens` will show the drop, but the read/write split needs one run with
   persistence on, or the envelope's `usage` captured). This turns §3d from projection to fact.
2. **Deterministic integration lint at Assemble** (bound-handle set, tcpdump call shape,
   capture-with-no-wait). Sized at ~40% of Review findings, and it would have caught Sonnet's
   setup defect too.
3. **Self-contained-unit rule** in the per-unit prompt: each unit establishes its own
   precondition. Sized at 2 of 7 findings; also the whole-script generation's main structural
   edge.
4. **Prime the fan-out** so the first wave of 8 does not all miss the cache. Small.
5. **Fragment appendix** in the cacheable prefix: 27% of all prompt text; needs a quality check
   because every unit would then read all 38 fragments. Middle path: hoist only fragments used
   by >50% of units (one fragment alone is 12.5% of the pass).
6. **Sonnet 5 for unit fills and/or step matching.** Evidence in §5. If wanted, the next step is
   a full 38-unit pass on Sonnet, judged in-context against the Opus artifact.
7. **Per-unit-scoped Fix** and **two-tier Review**, from the morning's handoff, unchanged.

---

## 7. Things I got wrong or could not do, for the record

- The morning handoff (same day, earlier session) aimed step one at the vLLM. Every call was
  Claude via the CLI. The debug log's `provider`/`auth_method` fields said so all along.
- My memory-symlink repair at 12:19 raised every server-side LLM call by ~10.5k tokens for the
  three hours until the neutral cwd shipped. Correct fix for interactive sessions; the server
  should never have been reading the repo's context in the first place.
- The `--exclude-dynamic-system-prompt-sections` flag is documented as improving cross-user
  cache reuse and did not produce a hit here. I did not chase why; `--system-prompt` made it moot.
- Whether a fixed `--session-id` would make the *default* system prompt cache is untested. The
  default prompt is wrong for a completion anyway.
- The whole-script and per-unit artifacts were generated from different sequence revisions
  (30 vs 38 steps), so §4 compares approaches, not identical inputs.
- Nothing here has been run on a testbox.
