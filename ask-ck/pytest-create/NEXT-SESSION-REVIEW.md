# Next-Session Review — PyTest Creator, 2026-07-27h

> **Purpose:** everything Terrence asked to have saved for review against the previous
> tested outcomes — the re-checked cases, the re-judged results (with vllm-fast run 5x for
> consistency), and every bug/regression found. Read this first; the detail lives in
> `PLAN-pytest-testing.md` §11 and the artifacts under `judging/`.

## How to compare against last time

```bash
python3 tool/pt_compare_runs.py --list
python3 tool/pt_compare_runs.py --against 2026-07-27a-pre-grounding
```

The pre-grounding baseline is preserved at
`judging/_runs/2026-07-27a-pre-grounding/` (restored from commit `d497083`). The current
run is in `judging/Port (7)/<case>/{mechanical,criterion4}.json`.

**Snapshot this run before making further changes**, so the next comparison has a
baseline:

```bash
python3 tool/pt_compare_runs.py --snapshot 2026-07-27h-grounded
```

---

## 1. Re-checked cases — mechanical criteria

All three regenerated on `vllm-fast` after CLI grounding + coverage gate.

| Case | C1 template | C2 snippets | C3 order | C6 logging | lint | coverage |
|---|---|---|---|---|---|---|
| T33233 | exactly (11/11) | exactly (9/9) | right | yes | ✅ | 6/6 |
| T33234 | exactly (12/12) | n-a (0 selected) | n-a | yes | ✅ | 8/8 |
| T33235 | exactly (6/6) | exactly (6/6) | right | yes | ❌ | 6/6 |

**Changes vs the pre-grounding run:**

| | before | after |
|---|---|---|
| T33235 `key=value` in sequence | 13 | **0** |
| T33235 `key=value` in script | 57 | **0** |
| T33233 placeholder `portA` refs | 13 | **0** |
| real CLI formats quoted per case | 0 | 14–23 |
| objective coverage | unmeasured | **3/3 complete** |

**T33235 is the headline improvement:** it previously found zero reusable fragments and
graded `n-a` on C2/C3. The grounded sequence gave script-search better terms, so it now
finds 14 fragments, selects 9, and grades **C2 exactly / C3 right**.

---

## 2. Judging (criterion 4) — Opus + vllm-fast ×5

Judges: **Claude Opus** (1 run) + **vllm-fast run 5 times independently** on every block,
per Terrence's request to check consistency. Each repeat is a separate recorded call, not
an average — `criterion4.json` carries a `self_consistency` block per gap-fill step with
`runs`, `distinct`, `majority`, `majority_share`, `stable`, and every individual vote.

**Why 5 runs:** in the previous session vllm-fast returned *bad, bad, good, bad, bad, bad*
across six runs on T33235's physical hot-swap step — and its "good" explicitly defended
the `shutdown`/`no shutdown` substitution as "standard for automated link-flap testing".
A judge that occasionally endorses the defect you care most about is doing less work than
its vote count suggests. Opus was "bad" every time.

**Read the results with that in mind:** treat a block where `stable: false` as a block
where vllm-fast's single vote should not be trusted; weight Opus and your own read.

### Results — 14 gap-fill blocks, 84 judge calls

| | agree | near-miss | disagree |
|---|---|---|---|
| Opus vs vllm-fast | 11 | 3 | **0** |

**Verdict distribution:** Opus `bad` × 14. Every vllm-fast repeat: `bad` × 12, `good` × 2.

**Consistency answer: vllm-fast was STABLE on 12 of 14 blocks (85%).** The two splits were
4–1, not coin-flips:

| Case | step | votes |
|---|---|---|
| T33233 | 11 | bad, bad, bad, bad, **good** |
| T33234 | 1 | good, good, good, good, **bad** |

That is better than the previous session's 6-run observation implied, but it still means a
single vllm-fast vote is not decisive on a contested block — check `self_consistency` in
`criterion4.json` before trusting one.

**T33235 has zero gap-fill blocks now** (every TestCase reuses a real fragment after the
grounding improved script-search), so criterion 4 no longer applies to it — a genuine
improvement, not a gap.

**Nothing reached "good" from both judges.** The defects are consistent and specific:
verification that checks link-state but never the feature under test (e.g. `lpi disable`
asserts only `Link is UP`, never that LPI is off — a false green whenever the disable
silently fails), and assertions weaker than the step demands. These are *semantic* defects
the mechanical criteria cannot catch, which is exactly what criterion 4 is for.

---

## 3. Bugs and regressions found this session

### Regressions the CLI grounding itself caused — all 4 fixed (row 4 closed 2026-07-28)

| # | Regression | Status |
|---|---|---|
| 1 | `speed 2000` — an invented value. The prompt showed valid syntax but never said arguments must come *from* it. | **Fixed** — explicit argument rule; now emits `speed 2500 (unsupported on 1G copper)`. |
| 2 | `show interface eth1` — `prompt_block()` picked the **longest** sample output, which was the TQ wireless AP's *router* interface, not a switch port. | **Fixed** — prefers the variant the most product families share. |
| 3 | `self.dut.port1.0.1` — a **SyntaxError**; the model used a CLI port name as a Python attribute. | **Fixed** — "port names are CLI text, never identifiers" rule. |
| 4 | `framework.ATLibrary` — recorded as a hallucinated import that the lint "correctly rejects", so **T33235's `lint_ok` was False**. | **Fixed 2026-07-28 — and the diagnosis was wrong.** `ATLibrary` is a *real* framework package; the **lint** was broken, not the script. `framework_surface` is keyed by module path (`ATLibrary.ATTools`, `ATLibrary.__init__`) so a package never has a bare key — a membership test rejected **every** package import. `from framework.ATDrivers import ATSwitch`, a very common real import, was silently an error too; `ATDrivers` passed only because it sat in a hardcoded allowlist despite being *structurally identical* to `ATLibrary`. The check now resolves packages from the index and the allowlist is gone (all 6 exempted names are real keys). T33235 re-lints **0 errors / 0 warnings, script code unchanged**; `lint_ok` corrected in `mechanical.json`. +19 tests (`tests/test_framework_import_lint.py`). |
| 5 | `pt_judge.py --out` **skipped** cases with zero gap-fill blocks, leaving the previous run's `criterion4.json` in place. T33235 kept a 13:43 file claiming 7 judged blocks hours after regeneration made it 0. A stale artifact that looks current is worse than none, since the next session compares against it. | **Fixed** — a no-gap-fill case now overwrites with an explicit `gap_fill_blocks: 0` record. |

### Coverage regression that prompted the gate

Re-extracting T33234 went **14 → 9 steps and silently dropped Zephyr source step 4** —
*"configure one side to Auto and the other to forced MDI or MDIX … correct link-down
behavior in incompatible combinations"*, i.e. the **entire negative path** of an MDI/MDI-X
test, which the old sequence covered with 4 dedicated entries. Nothing absorbed it.

Cause: the grounding pushed the model to reclassify partner-side configuration as
`physical` operator prompts, collapsing the 4-way matrix into one prompt. Now prevented by
the coverage gate plus prompt rules ("a source step describing COMBINATIONS needs one
entry per combination, including the negative cases"; "don't downgrade automatable partner
config into an operator prompt").

### Product debt — writes can silently not persist ⚠

**The server can return HTTP 200 while the write never reaches `ck.db`.**
`db.get_connection()` caches one SQLite connection per thread; after an external process
writes to the DB, those long-lived connections hold a stale WAL snapshot, and
`_pt_persist` swallows the failure into a `print` that never fired.

Symptom: endpoint returns 13 steps, DB still has 0, `updated_at` unchanged. It cost real
debugging time and forced restart-and-reverify cycles throughout this session.

**Workaround:** `./run.sh --restart` around any external write to `ck.db`, then verify
`updated_at` from a *fresh* connection. **Never trust the 200.**
**Fix candidates:** refresh/drop the thread-local cache; make `_pt_persist` surface
failures instead of printing. Related to §9.4 dual-instance debt but worse — it presents
as success.

---

## 4. Open questions for your review

1. **T33234 selects 0 of 7 fragments.** It gathered 7 but marked none worth reusing, where
   T33233 selected 16/48 and T33235 9/14. Previously it had no `selected` key at all, so
   the back-compat fallback treated all 7 as selected — hence C2 `exactly` → `n-a`. Is the
   LLM right that none are reusable, or is this a selection bug?
2. ~~**T33235's `framework.ATLibrary` import** — needs the import surface grounded, or a
   prompt rule listing the real framework modules.~~ **RESOLVED 2026-07-28 — no grounding
   needed.** The import was valid; the lint was wrong (see row 4 above). Grounding the
   prompt here would have taught the model to *avoid writing correct Python*, which is
   why the fix went into the check instead.
3. **`speed 2500` on 1G copper** as the "unsupported speed" choice — plausible, but you'd
   know whether that's right for this DUT.
4. **T33234's polarity matrix is now 2 entries, not 4.** Both paths *are* covered (one
   compatible expecting `connected`, one incompatible expecting `disconnected or down`), so
   the gate passes — but it is less exhaustive than the original 4-way matrix.
5. **Skeleton scaffolding is 62% of the generate prompt** (16,071 of 26,043 chars), of
   which 7,213 chars are `# >>> FILL <<<` comments the model is then told to delete.
   Roughly halvable — cost, not correctness, so it was left alone.

---

## 5. Still blocked

**Part 3b (criteria 5–6, real tb470 execution)** — needs `configs/tb470.setup`, a
Terrence-side physical-topology prerequisite. Note the **corrected path**:
`/home/st-art/st-art/configs/` (473 `.setup` files), **not** under `framework/` as
PLAN §5b originally said.
