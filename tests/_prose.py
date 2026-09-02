"""Helpers for asserting things about PROSE and TEMPLATES without self-matching.

WHY THIS MODULE EXISTS
----------------------
A check that searches for a bad pattern in text will find that pattern in the text
warning against it. This happened FOUR times in one session (2026-07-28) before it was
recognised as a class rather than four separate accidents:

  1. The port-hardcode lint flagged the skeleton's own guidance comment, which quoted
     `'port1.0.1'` while explaining never to write it — 3 false warnings per script,
     against its own advice.
  2. A test asserting `self.passed(...)` is absent caught the prompt sentence
     "Never write `self.passed(...)` literally".
  3. A test asserting `distutils` is absent caught the `yesNo()` docstring explaining
     WHY distutils is avoided.
  4. A test looking for the phrase "as applicable" missed it, because the prompt wraps
     and the phrase straddled a newline.

Cases 1-3 are self-reference: guidance necessarily contains the antipattern it forbids.
Case 4 is raw-string matching against wrapped prose. Same root cause — treating prose as
if it were structured data.

THE RULES, encoded as functions so the correct thing is the easy thing:

  * Asserting a pattern is ABSENT  -> scan `code_lines()`, never the raw text.
  * Asserting a phrase is PRESENT  -> scan `flat()`, never the raw text.
  * Checking a worked EXAMPLE      -> scan `code_fences()`. Highest-value check there is:
                                      where prose and example disagree, the model copies
                                      the example.
  * Target is real code            -> prefer `ast`, not text, wherever possible.

TWO FILE KINDS, TWO NOTIONS OF "CODE" (learned immediately after writing this module):

  * A PROMPT (`*.jinja` full of rules) is PROSE with embedded ```python fences. Its code
    is `code_fences()`; its prose legitimately names the antipatterns it forbids, so
    running `code_lines()` over a whole prompt reads every explanatory bullet as code.
  * A TEMPLATE (`pt_script_template.py.jinja`) is Python. Its code is `code_lines()`.

Pick by file kind, or nest: `code_lines(block) for block in code_fences(src)`.
"""
from __future__ import annotations

import re
from typing import Iterator, List

__all__ = ["code_lines", "flat", "code_fences", "strip_jinja_comments"]

_JINJA_COMMENT = re.compile(r"\{#-?.*?-?#\}", re.S)
_JINJA_TAG = re.compile(r"\{%-?.*?-?%\}", re.S)
_TRIPLE = re.compile(r'("""|\'\'\')')


def strip_jinja_comments(src: str) -> str:
    """Drop `{# ... #}` blocks — they never render, so they are not shipped text."""
    return _JINJA_COMMENT.sub("", src)


def code_lines(src: str, *, jinja: bool = True) -> Iterator[str]:
    """Yield only lines that are (or render as) real CODE.

    Excludes, in order: jinja comment blocks, jinja control tags, whole-line `#`
    comments, trailing `#` comments, and triple-quoted docstring bodies. What remains is
    what actually executes — the only place an antipattern is a defect rather than an
    explanation of one.

    Deliberately conservative about docstrings: it tracks an open triple-quote and skips
    until it closes, so a docstring mentioning `distutils` (case 3 above) is invisible.
    """
    text = strip_jinja_comments(src) if jinja else src
    in_doc = False
    for raw in text.splitlines():
        line = raw
        if jinja:
            line = _JINJA_TAG.sub("", line)
        # docstring tracking: an odd number of delimiters on a line toggles the state
        delims = len(_TRIPLE.findall(line))
        if in_doc:
            if delims % 2 == 1:
                in_doc = False
            continue
        if delims % 2 == 1:
            in_doc = True
            # the part before the opening delimiter can still be code
            line = line.split('"""')[0].split("'''")[0]
        elif delims >= 2:
            # A complete one-line triple-quoted string. Blank its CONTENT, not just the
            # delimiters — a one-line docstring is exactly where "why we avoid X" lives,
            # and leaving the text in was how case 3 slipped through the first cut.
            line = re.sub(r'""".*?"""', '""', line)
            line = re.sub(r"'''.*?'''", "''", line)
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        if "#" in line:
            line = line.split("#", 1)[0]
        if line.strip():
            yield line


def flat(src: str) -> str:
    """Whitespace-collapsed text, for asserting a PHRASE is present.

    Prompts and docs wrap, so `"as applicable"` can straddle a newline and a raw `in`
    test fails on text that is plainly there (case 4 above).
    """
    return re.sub(r"\s+", " ", src)


def code_fences(src: str, lang: str = "python") -> List[str]:
    """The bodies of ```<lang> fenced blocks — a prompt's worked EXAMPLES.

    These are the highest-value thing to check in a prompt: the model implements the
    example, not the prose, so an example that is wrong IS the bug.
    """
    return re.findall(rf"```{lang}\n(.*?)```", src, re.S)


def expand_includes(path, _depth: int = 0) -> str:
    """A template's source with `{% include 'x' %}` inlined from the same directory.

    WHY THIS EXISTS (2026-09-02)
    ----------------------------
    18 tests asserted "the generate prompt conveys rule X" by grepping
    `pt_generate_script.jinja` as a FILE. When the slot-filling rules were extracted into
    `pt_fill_rules.jinja` so the whole-script and per-unit prompts could share one copy,
    all 18 broke — while the RENDERED prompt was byte-identical (proved by
    tests/test_pt_prompt_rules_partial.py against a pre-extraction snapshot).

    The tests were right about the intent and wrong about the unit: what reaches the model
    is the template WITH its includes resolved, so that is what an assertion about the
    prompt should read. Textual rather than a Jinja render, because these tests inspect
    the template's own source — its `{% if %}` branches, its jinja comments, its fenced
    examples — none of which survive rendering.
    """
    import pathlib
    p = pathlib.Path(path)
    src = p.read_text(encoding="utf-8")
    if _depth > 4:                      # cycles are a bug, not something to recurse into
        return src
    def _sub(m):
        name = m.group(1)
        target = p.parent / name
        return expand_includes(target, _depth + 1) if target.exists() else m.group(0)
    return re.sub(r"\{%-?\s*include\s+['\"]([^'\"]+)['\"]\s*-?%\}", _sub, src)
