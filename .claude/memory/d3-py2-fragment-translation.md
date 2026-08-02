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

**Why lib2to3 over hand-rolled regex:** it's a real Py2 parser. On 40 real legacy scripts: 38 translated cleanly, **2 failed loudly with ParseError** (not silent mistranslation). That fail-loud property makes pre-translation safe. `lib2to3` is stdlib on Py3.10 (52 fixers). ⚠ **CORRECTED 2026-08-03: `lib2to3` was REMOVED from the stdlib in Python 3.13 — the version this project tells you to prefer (the testbox runs 3.13.5). So the recommended venv was exactly the one where D3 was silently OFF: `_translate_py2` returned `status: "unavailable"` and every Py2 fragment shipped untranslated behind a soft-warn, with nothing raising. Measured on the Opus batch: 1 py2_flagged fragment, 0 translated. Now `pytest_create._py2_refactor_backend()` prefers stdlib `lib2to3` where it exists and falls back to the maintained fork **`fissix`** (same `refactor` API, own `fissix.fixes` package), declared in requirements. So 'translated == guaranteed valid Py3' holds again.**

**Design (hooks into the D1-hardened resolver, same resolved-fragment path):**
1. Fragment carries Py2 tells → run code through `lib2to3.RefactoringTool`.
2. Success → Generate sees deterministic Py3; NO prompt-steer; clean fragments = zero extra prompt weight.
3. ParseError (~5%) → do NOT ship broken translation. Fall back to untouched fragment + soft-warn preview banner + a targeted "this fragment is Py2, modernize when adapting" line. Prompt-steer is FALLBACK ONLY.

**Scope:** Py2 syntax only. **Provenance:** translated fragment tag annotated `(py2→py3)` (e.g. `# ART/legacy <id> <lines> (py2→py3)`) so a reviewer knows a block was mechanically modernized, not copied verbatim.

Py2 tell regex (also used for the null-loc cohort in D1): `^\s*print\s+[^(]`, `except\s+\w[\w.]*\s*,\s*\w+\s*:`, `\.iter(items|keys|values)\(`, `\.has_key\(`, `\bxrange\(`, `\bbasestring\b`, `^\s*raise\s+\w+\s*,`.
