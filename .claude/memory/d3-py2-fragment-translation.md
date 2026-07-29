---
name: d3-py2-fragment-translation
description: "D3 DONE (2026-07-27, uncommitted) — _translate_py2 via lib2to3 at resolve time; translated==guaranteed valid Py3 (expandtabs(8)+ast self-verify); parse-fail ships original + banner + conditional prompt-steer; (py2→py3) provenance. 27 adversarial checks green."
metadata: 
  node_type: memory
  type: project
  originSessionId: bb0cc757-a099-46f9-a0ca-b4fd8f3fbd36
  modified: 2026-07-26T19:56:06.021Z
---

D3 (Py2/old-framework contamination, from NEXT_SESSION_DECISIONS.md / [[pytest-artefact-review-worklist]]) is **DECIDED: pre-translate with `lib2to3`.**

**Exposure (measured vs ck.db):** 60 Py2-flagged scripts expose 342 reusable symbols reachable by the fragment gather — live risk. Py2 tells concentrate in the `legacy` DB (111 scripts; `print`-statement ×102, `.iteritems()` ×17) — the SAME legacy DB as [[d1-fragment-resolver-boundaries]]'s 650 null-loc cases. A separate ~274-script "old-framework" set (no `framework`/ATTestSet/ATTestCase) is DEFERRED (lib2to3 doesn't fix framework-modernity).

**Why pre-translate over an LLM prompt-steer:** mechanical fix is deterministic; an instruction is only usually-complied-with. Keeps `pt_generate_script.jinja` single-purpose. Note the prompt currently has NO Py2→Py3 rule and Rule 4 ("keep their proven CLI/parsing, don't discard") actively steers the model to PRESERVE Py2 idioms. Also: lint only `py_compile`s the RESULT and CANNOT catch runtime-only tells (`.iteritems()`/`.has_key()`/`basestring` are valid Py3 syntax that fails at runtime on the testbox).

**Why lib2to3 over hand-rolled regex:** it's a real Py2 parser. On 40 real legacy scripts: 38 translated cleanly, **2 failed loudly with ParseError** (not silent mistranslation). That fail-loud property makes pre-translation safe. `lib2to3` is stdlib on Py3.10 (52 fixers).

**Design (hooks into the D1-hardened resolver, same resolved-fragment path):**
1. Fragment carries Py2 tells → run code through `lib2to3.RefactoringTool`.
2. Success → Generate sees deterministic Py3; NO prompt-steer; clean fragments = zero extra prompt weight.
3. ParseError (~5%) → do NOT ship broken translation. Fall back to untouched fragment + soft-warn preview banner + a targeted "this fragment is Py2, modernize when adapting" line. Prompt-steer is FALLBACK ONLY.

**Scope:** Py2 syntax only. **Provenance:** translated fragment tag annotated `(py2→py3)` (e.g. `# ART/legacy <id> <lines> (py2→py3)`) so a reviewer knows a block was mechanically modernized, not copied verbatim.

Py2 tell regex (also used for the null-loc cohort in D1): `^\s*print\s+[^(]`, `except\s+\w[\w.]*\s*,\s*\w+\s*:`, `\.iter(items|keys|values)\(`, `\.has_key\(`, `\bxrange\(`, `\bbasestring\b`, `^\s*raise\s+\w+\s*,`.
