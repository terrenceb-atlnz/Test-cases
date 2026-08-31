---
name: checks-must-not-match-their-own-advice
description: "Any check that greps prose will fire on its own guidance text — happened 4x in one session; match structure, not strings"
metadata: 
  verified: 2026-08-31
  node_type: memory
  type: feedback
  originSessionId: 14818525-5627-4f16-882d-6bbbef6aed41
  modified: 2026-07-27T22:44:24.579Z
---

**A check that searches for a bad pattern in text will find that pattern in the text
warning against it.** This happened **four times in one session** (2026-07-28) before it
was recognised as a class rather than four accidents:

1. The port-hardcode lint flagged the skeleton's own guidance comment, which quoted
   `'port1.0.1'` while explaining never to write it. 3 false warnings per script.
2. A test asserting `self.passed(...)` absent caught the prompt sentence *"Never write
   `self.passed(...)` literally"*.
3. A test asserting `distutils` absent caught the `yesNo()` docstring explaining *why*
   distutils is avoided.
4. A test looking for the phrase `"as applicable"` missed it because the prompt wraps and
   the phrase straddled a newline.

**Why:** 1–3 are self-reference (the guidance necessarily contains the antipattern);
4 is raw-string matching against wrapped prose. Same root cause — treating prose as if it
were structured data.

**How to apply — use `tests/_prose.py` (built for this):**
- `code_lines(src)` — yields only real code: skips `#` comments, jinja `{# #}` / `{% %}`,
  docstrings, and trailing comments. Use for "this antipattern must not appear in code".
- `flat(src)` — whitespace-collapsed text. Use for "this phrase must be present in prose".
- `code_fences(src)` — just the ```python blocks. Use for "the EXAMPLE must be correct",
  which is the highest-value check of all (see [[prompt-examples-are-the-spec]]).

Rules of thumb:
- Asserting something is ABSENT → search code only, never prose.
- Asserting something is PRESENT → search `flat()`, never the raw string.
- Prefer AST/structure over text whenever the target is code.
- If a check must scan prose, exclude the lines that are *about* the pattern.

Related: [[prompt-examples-are-the-spec]], [[scripts-must-be-hardware-agnostic]].
