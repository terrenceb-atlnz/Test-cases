---
name: silent-degradation-audit-2026-07-30
description: Three features were silently dead or degraded because their failure paths were polite — paramiko undeclared, lib2to3 removed in py3.13, unparseable LLM reply read as "empty"; check declared deps and parse-failure paths first
metadata:
  type: feedback
---

Three defects found in one session (2026-07-30) shared a shape: **the feature was off, nothing
raised, and the symptom pointed away from the cause.**

- **`paramiko` was in no requirements file** while `pt_exec.py` had imported it since the run
  feature shipped. `import paramiko` sits inside `_connect()`, so the server booted, every other
  tool worked, and the testbox probe answered
  `{"ok": false, "detail": "SSH connection failed: No module named 'paramiko'"}` — which reads
  as a lab-network problem. PyTest Creator's whole "6. Run" step was dead on any fresh venv.
- **`lib2to3` was removed from the stdlib in Python 3.13**, the version `requirements.txt`
  tells you to prefer. `_translate_py2` degraded to `status: "unavailable"` and shipped legacy
  Py2 fragments untranslated. Its docstring blamed "a very old/stripped runtime"; the truth was
  the opposite — a NEW one. Fixed with the maintained fork `fissix`.
- **`gather_fragments` treated an unparseable LLM reply as an empty one.** `extract_json_block`
  returns `None` on a parse failure, `_parsed_list` turned that into `[]`, and the case recorded
  "no reusable code" — a legitimate outcome `confirm_step` accepts by design. Two cases carried
  0 fragments into generation while step 3 had selected 12 scripts. `extract_sequence` had always
  failed loudly here; this step never did.

**Why:** graceful degradation without a loud signal is indistinguishable from working. None of
these had a failing test, because the functional path needs hardware or an LLM — but all three
were catchable structurally, for free.

**How to apply:** (1) `tests/test_dependencies_declared.py` now asserts every third-party import
in `CK_server` is declared — run it before trusting any "feature X doesn't work on the bench"
report. (2) When an LLM step yields a suspiciously empty result, check whether the reply PARSED
before believing the emptiness. (3) An "unavailable"/"degraded" branch deserves a test that the
capability is actually present, not just that the fallback exists.

Related: [[claude-code-cli-transport-contract]], [[mutate-before-you-claim]],
[[d3-py2-fragment-translation]], [[testbox-console-access]].
