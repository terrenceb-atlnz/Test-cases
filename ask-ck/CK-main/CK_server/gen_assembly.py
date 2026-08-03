r"""Recover a whole generated script from an LLM reply that spans several messages.

WHY THIS EXISTS — the "output ceiling" was a parser defect, not a model limit.

`_parse_generated_blocks` used one non-greedy regex, ```` ```(?:python)?\s*\n(.*?)``` ````.
The Claude Code CLI splits a long answer across several assistant messages, and
`_parse_cli_stream` concatenates their text. Each continuation message re-opens a
```` ```python ```` fence, so the non-greedy `(.*?)` stopped at the *continuation's opening*
fence and everything after it was discarded. Because the cut usually landed mid-token, the
survivor looked like a model truncation, and three separate documents recorded the
parser-kept figures as the model's output budget.

Replaying the five stored replies in `debug-log/no-session.jsonl` (2026-08-03):

    reply      model sent   old parser kept   this module recovers
    06:47:37   40 classes   21                40
    07:00:16   17           16                17
    07:25:59   11            9                11
    07:48:13    6            6                 6
    07:56:58    6            0                 6   <- the "D15 regression"

**Every one of the five ends in `ts.run(sys.argv)`. Nothing was ever truncated.** After
recovery every class registered by `ts.add_testCase(...)` is defined, carries a `main()`,
and the whole script `ast.parse`s.

HOW THE SEAMS LOOK. Four shapes occur in the real data, and all four are handled:

1. Fence re-opened at the start of a line, mid-function. Plain concatenation is correct.
2. Fence glued onto the end of a partial line (`# SVT 3```python`). The split cut a line in
   half, so that trailing partial line is incomplete.
3. The continuation re-emits the partial line from its start
   (`self.log('LLDP transmit...` -> `self.log('LLDP transmit...s, ca`).
4. The part closes its fence cleanly and the next part opens a new one, sometimes with a
   `# ---- continuation of <file> (part N)` header, which is scaffolding, not code.

A continuation may also re-emit a whole class the previous part left half-written
(`TestCase_21` in the 4-part reply), so assembly is at TOP-LEVEL UNIT granularity. The
model itself closed that reply with plain-English assembly instructions saying precisely
this; they were being discarded along with the code.

DESIGN RULE: PREFER LOSING NOTHING, AND NEVER GUESS SILENTLY.

An adversarial review of the first version of this module found seven ways it could delete
real code while reporting a clean recovery. Each is now closed by a rule that is decided by
EVIDENCE rather than by a heuristic:

* **Seam repair is decided by parsing, not by a rule about newlines.** The first version
  always dropped a chunk's trailing line. That is right when the stream was cut mid-line,
  and wrong when the model simply wrote the fence on the same line as a complete statement
  (`CRITICAL = 1```` ``` ````) — which silently deleted that statement. Now both readings
  are tried and the one that parses is kept, preferring the one that drops nothing.
* **A unit's span stops at the next column-0 statement.** The first version gave each
  `class`/`def` everything up to the next `class`/`def`, so module-level code between them
  belonged to the preceding unit's span — and resolving a duplicate class deleted it. In a
  framework script that code is `ts = TestSuite(...)`, so the shipped script raised
  `NameError` at run time while every check here reported success.
* **Duplicate units are resolved on AST richness, not character count.** A re-emitted class
  that carries a longer description but two fewer steps is not the more complete one.
* **A block after the script's runner is not a continuation.** `ts.run(sys.argv)` is the
  last line a script can have, so a later fenced block is commentary ("to run it locally:")
  and merging it in appended module-level code that executed on import.
* **A `LIBRARY:` label survives a blank line and is inherited across a seam**, so a helper
  library split over two messages is repaired as a library instead of half-corrupted and
  half-appended to the test script.

WHAT THIS MODULE STILL CANNOT DO. Fence detection is textual, so a ```` ``` ```` inside a
string literal or docstring, and a column-0 `class`/`def` inside a docstring, are mistaken
for structure. Those cases are DETECTED — the assembly fails to parse, `report["parses"]`
is False, and the caller refuses the script — rather than shipped. That is the correct
failure direction, and it is the whole point: a caller that ships a script whose `parses`
is False is shipping a known-bad artefact.
"""
from __future__ import annotations

import ast
import itertools
import re
from typing import Any, Dict, List, Optional, Tuple

# Three or more backticks with an optional language tag, anywhere — including glued to the
# end of a code line, which is seam shape 2 and is NOT valid markdown. That invalidity is
# the point: a fence not at the start of a line can only be a continuation artefact.
# The language tag is captured so ```` ```bash ```` is recognised as an OPENING fence; the
# first version matched only the backticks of `` ```python ``, so any other language read as
# a close and its content was absorbed into the script.
_FENCE_RX = re.compile(r"(?P<ticks>`{3,})[ \t]*(?P<lang>[A-Za-z0-9_+.-]*)")

# `# ---- continuation of 261_Management_LLDP_LLDP_test.py (part 2)` and friends.
_CONT_HEADER_RX = re.compile(r"^\s*#\s*-*\s*continuation of\b.*$", re.IGNORECASE)

# The optional label the prompt asks for above a helper-library block.
_LIBRARY_LABEL_RX = re.compile(r"^LIBRARY:\s*(\S+)\s*$")

# Top-level `class X` / `def x` / `async def x` at column 0.
_UNIT_RX = re.compile(r"^(?:class|def|async\s+def)\s+([A-Za-z_]\w*)", re.MULTILINE)

# The last statement a standardized script can contain. Anything fenced after it is prose.
_RUNNER_RX = re.compile(r"^\s*ts\.run\s*\(|^if\s+__name__\s*==", re.MULTILINE)

# Trying every keep/drop combination is 2**seams; real replies have at most three seams.
_MAX_SEAM_COMBINATIONS = 6


def _normalise(content: str) -> str:
    """CRLF -> LF. `closes` tests the character after a fence, and \\r made every closing
    fence read as an opening one, so a CRLF reply was mis-assembled end to end."""
    return (content or "").replace("\r\n", "\n").replace("\r", "\n")


def _label_above(content: str, fence_start: int) -> Optional[str]:
    """The `LIBRARY: <name>` label above an opening fence, skipping blank lines.

    Blank-line tolerance matters: the prompt's own example puts the label on its own line,
    and a model that adds a blank line after it used to have its library silently demoted
    into the test script.
    """
    pos = content.rfind("\n", 0, fence_start)
    while pos > 0:
        line_start = content.rfind("\n", 0, pos) + 1
        line = content[line_start:pos].strip()
        if line:
            m = _LIBRARY_LABEL_RX.match(line)
            return m.group(1) if m else None
        pos = line_start - 1
    return None


def _fence_indent(content: str, fence_start: int) -> str:
    """The whitespace a markdown fence is indented by, to strip from its content."""
    line_start = content.rfind("\n", 0, fence_start) + 1
    prefix = content[line_start:fence_start]
    return prefix if prefix.strip() == "" else ""


def _strip_indent(chunk: str, indent: str) -> str:
    if not indent:
        return chunk
    return "\n".join(ln[len(indent):] if ln.startswith(indent) else ln
                     for ln in chunk.split("\n"))


def _skip_eol(content: str, pos: int) -> int:
    return pos + 1 if content[pos:pos + 1] == "\n" else pos


def split_fenced_parts(content: str) -> Tuple[List[Tuple[Optional[str], str, str]], str]:
    """Split a reply into ``[(library_label, language, chunk)]`` plus any trailing prose.

    An opening fence encountered while a block is already open is a continuation artefact:
    it ends the current chunk and starts the next one, and the chunk INHERITS the current
    label and language so a library split across messages stays a library. A closing fence
    followed by another opening fence is the same seam written tidily, and there both are
    re-read.

    The language is carried because a ```` ```bash ```` block is not part of the script.
    The first version matched only the backticks of `` ```python ``, so any other language
    read as a CLOSING fence and its body was absorbed into the generated code.
    """
    content = _normalise(content)
    parts: List[Tuple[Optional[str], str, str]] = []
    first = _FENCE_RX.search(content)
    if not first:
        return [], content

    label = _label_above(content, first.start())
    lang = (first.group("lang") or "").lower()
    indent = _fence_indent(content, first.start())
    start = _skip_eol(content, first.end())
    pos = start
    prose = ""

    while True:
        m = _FENCE_RX.search(content, pos)
        if not m:
            parts.append((label, lang, _strip_indent(content[start:], indent)))
            break
        parts.append((label, lang, _strip_indent(content[start:m.start()], indent)))
        # A fence closes only when it carries no language tag AND ends its line.
        closes = not m.group("lang") and content[m.end():m.end() + 1] in ("\n", "")
        nxt = _FENCE_RX.search(content, m.end())
        if closes and not nxt:
            prose = content[m.end():]
            break
        if closes:
            # A clean close then a new open: a genuinely new block, so re-read everything.
            label = _label_above(content, nxt.start())
            lang = (nxt.group("lang") or "").lower()
            indent = _fence_indent(content, nxt.start())
            start = _skip_eol(content, nxt.end())
        else:
            # A continuation artefact: same block, same label, same language.
            start = _skip_eol(content, m.end())
        pos = start
    return parts, prose


# An unlabelled fence is python by convention — the generate prompt asks for ```python and
# a bare ``` block in these replies has always been the script.
_PYTHON_LANGS = ("", "python", "python3", "py")


def _strip_continuation_header(lines: List[str]) -> List[str]:
    while lines and _CONT_HEADER_RX.match(lines[0] or ""):
        lines.pop(0)
    while lines and not lines[0].strip():
        lines.pop(0)
    return lines


def _join_with(chunks: List[str], drop_flags: Tuple[bool, ...]) -> Tuple[str, List[str]]:
    """Join chunks, dropping each non-final chunk's trailing line where flagged."""
    out: List[str] = []
    dropped: List[str] = []
    for idx, chunk in enumerate(chunks):
        lines = chunk.split("\n")
        if idx > 0:
            lines = _strip_continuation_header(lines)
        if idx < len(chunks) - 1 and drop_flags[idx] and lines and lines[-1] != "":
            dropped.append(lines.pop())
        out.append("\n".join(lines))
    return "\n".join(out), dropped


def stitch_parts(chunks: List[str]) -> Tuple[str, List[str]]:
    """Join code chunks of one file, repairing the seam between each pair.

    A chunk cut mid-stream ends on a half-written line that must go; a chunk whose author
    simply put the fence on the same line as a complete statement must keep it. Nothing in
    the text distinguishes the two, so BOTH readings are assembled and the one that parses
    wins, preferring the reading that drops the least. Only if no combination parses does
    it fall back to dropping every seam line, and the caller then sees `parses: False`.
    """
    if len(chunks) < 2:
        return _join_with(chunks, (False,) * max(len(chunks), 1))
    seams = len(chunks) - 1
    if seams <= _MAX_SEAM_COMBINATIONS:
        # fewest drops first: keeping code is preferred whenever it is valid
        combos = sorted(itertools.product([False, True], repeat=seams), key=sum)
        for flags in combos:
            code, dropped = _join_with(chunks, flags + (False,))
            if _parses(code):
                return code, dropped
    return _join_with(chunks, (True,) * seams + (False,))


def _unit_body_end(lines: List[str]) -> int:
    """Index of the first line after a unit's body — the next column-0 statement.

    A `class`/`def` owns its header plus every blank or indented line that follows. The
    first non-blank line at column 0 is module-level code, NOT part of this unit, and
    keeping the two apart is what stops duplicate resolution from deleting `ts = TestSuite(...)`.
    """
    end = 1
    for i in range(1, len(lines)):
        line = lines[i]
        if not line.strip():
            continue
        if line[:1] in (" ", "\t"):
            end = i + 1
            continue
        return end
    return len(lines)


def split_top_level_units(code: str) -> List[Tuple[str, str]]:
    """``[(name, text)]`` for each column-0 class/def; module-level code has name ``""``.

    Decorator lines immediately above a definition belong to it, not to the module-level
    run before it.
    """
    starts = [m.start() for m in _UNIT_RX.finditer(code)
              if m.start() == 0 or code[m.start() - 1] == "\n"]
    if not starts:
        return [("", code)]

    units: List[Tuple[str, str]] = []
    cursor = 0
    for pos in starts:
        if pos < cursor:
            continue                      # already consumed as part of a previous unit
        head_start = pos
        # pull in any decorator lines sitting directly above
        while True:
            prev_end = code.rfind("\n", 0, head_start - 1)
            line_start = prev_end + 1
            line = code[line_start:head_start - 1] if head_start else ""
            if head_start and line.startswith("@"):
                head_start = line_start
                continue
            break
        if head_start > cursor:
            units.append(("", code[cursor:head_start]))
        span = code[head_start:]
        lines = span.split("\n")
        # the name is on the def/class line, which may sit under decorators
        name_line = next(ln for ln in lines if _UNIT_RX.match(ln))
        name = _UNIT_RX.match(name_line).group(1)
        end_idx = _unit_body_end(lines[lines.index(name_line):]) + lines.index(name_line)
        unit_text = "\n".join(lines[:end_idx])
        units.append((name, unit_text))
        cursor = head_start + len(unit_text)
        if cursor < len(code) and code[cursor:cursor + 1] == "\n":
            unit_text += "\n"
            units[-1] = (name, unit_text)
            cursor += 1
    if cursor < len(code):
        units.append(("", code[cursor:]))
    return units


def _parses(text: str) -> bool:
    try:
        ast.parse(text)
        return True
    except (SyntaxError, ValueError):
        return False


def _richness(text: str) -> Tuple[int, int, int]:
    """How complete a definition is: (parses, AST node count, length).

    Character count alone is the wrong measure — a re-emitted class carrying a longer
    `testCaseDesc` but two fewer verification steps is longer and LESS complete. Node
    count reflects the code that would actually run.
    """
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return (0, 0, len(text))
    return (1, sum(1 for _ in ast.walk(tree)), len(text))


def _resolve_duplicates(units: List[Tuple[str, str]]) -> Tuple[List[Tuple[str, str]], List[Dict[str, Any]]]:
    """Keep the most complete definition of any name defined more than once.

    A continuation that re-emits a class the previous part left half-written produces two
    definitions of one name. Position is the FIRST occurrence, so declaration order is
    preserved. Module-level runs (name ``""``) are never merged — every one is kept in
    place, because they are statements, not definitions.
    """
    order: List[Tuple[str, Optional[str]]] = []
    best: Dict[str, str] = {}
    resolved: List[Dict[str, Any]] = []
    for name, text in units:
        if not name:
            order.append(("", text))
            continue
        if name not in best:
            best[name] = text
            order.append((name, None))
            continue
        prior = best[name]
        keep_new = _richness(text) > _richness(prior)
        best[name] = text if keep_new else prior
        resolved.append({"unit": name, "kept": "later" if keep_new else "earlier",
                         "earlier_chars": len(prior), "later_chars": len(text),
                         "earlier_nodes": _richness(prior)[1], "later_nodes": _richness(text)[1]})
    return [(n, best[n] if n else t) for n, t in order], resolved


def _code_chunks_up_to_runner(chunks: List[str]) -> Tuple[List[str], int]:
    """Chunks up to and including the one holding the script's runner; plus the count after.

    `ts.run(sys.argv)` is the last statement a standardized script can have, so a fenced
    block after it is commentary — typically "to run it locally:" — and concatenating it
    appended module-level code that would execute on import.
    """
    for i, chunk in enumerate(chunks):
        if _RUNNER_RX.search(chunk):
            return chunks[:i + 1], len(chunks) - (i + 1)
    return chunks, 0


def recover_script(content: str) -> Dict[str, Any]:
    """Recover the full script and a helper library from a possibly multi-part reply.

    Returns ``{"test_code", "library", "report"}``. ``report`` is the forensic record:
    ``parts`` (how many messages the answer spanned), ``seam_lines_dropped``,
    ``duplicate_units``, ``blocks_after_runner``, ``extra_libraries``, ``trailing_prose``
    (the model's own assembly notes), and ``parses``. A single-part reply returns
    ``parts == 1`` and touches nothing.
    """
    parts, prose = split_fenced_parts(content or "")

    code_chunks = [c for label, lang, c in parts if not label and lang in _PYTHON_LANGS]
    non_python = sorted({lang for label, lang, _c in parts
                         if not label and lang not in _PYTHON_LANGS})
    library_chunks: Dict[str, List[str]] = {}
    for label, lang, chunk in parts:
        if label and lang in _PYTHON_LANGS:
            library_chunks.setdefault(label.strip(), []).append(chunk)

    library = None
    extra_libraries: List[str] = []
    if library_chunks:
        names = list(library_chunks)
        first = names[0]
        lib_code, _ = stitch_parts(library_chunks[first])
        library = {"name": first, "code": lib_code.strip() + "\n"}
        extra_libraries = names[1:]

    code_chunks, after_runner = _code_chunks_up_to_runner(code_chunks)

    if not code_chunks:
        return {"test_code": None, "library": library,
                "report": {"parts": 0, "seam_lines_dropped": [], "duplicate_units": [],
                           "blocks_after_runner": after_runner,
                           "extra_libraries": extra_libraries,
                           "non_python_blocks": non_python,
                           "library_parses": _parses(library["code"]) if library else True,
                           "trailing_prose": prose.strip()[:2000], "parses": False}}

    joined, seam_dropped = stitch_parts(code_chunks)
    units, duplicates = _resolve_duplicates(split_top_level_units(joined))
    code = "".join(text for _, text in units)

    return {
        "test_code": code.strip() + "\n",
        "library": library,
        "report": {
            "parts": len(code_chunks),
            "seam_lines_dropped": [line[-120:] for line in seam_dropped],
            "duplicate_units": duplicates,
            "blocks_after_runner": after_runner,
            "extra_libraries": extra_libraries,
            "non_python_blocks": non_python,
            "library_parses": _parses(library["code"]) if library else True,
            "trailing_prose": prose.strip()[:2000],
            "parses": _parses(code),
        },
    }


def manifest_check(code: str) -> Dict[str, Any]:
    """Cross-check a recovered script against its own `ts.add_testCase(...)` manifest.

    A standardized script registers every case it means to run, so the registration list is
    an independent statement of what SHOULD be present — the one completeness signal in the
    artefact that does not come from the parser. Any registered-but-undefined class means
    recovery lost something, whatever the character counts say.

    Registrations are read from the AST, not by regex: a regex for `add_testCase(X())`
    silently ignores `add_testCase(X('arg'))` and then reports a clean manifest.
    """
    try:
        tree = ast.parse(code or "")
    except (SyntaxError, ValueError) as exc:
        return {"ok": False, "reason": f"does not parse: {exc}", "registered": 0,
                "defined": 0, "missing": [], "without_main": []}

    registered: List[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "add_testCase"):
            continue
        for arg in node.args:
            if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name):
                registered.append(arg.func.id)
            elif isinstance(arg, ast.Name):
                registered.append(arg.id)

    classes = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}
    missing = sorted({r for r in registered if r not in classes})
    without_main = sorted({
        name for name in registered
        if name in classes
        and not any(isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)) and f.name == "main"
                    for f in classes[name].body)
    })
    return {"ok": not missing and not without_main, "reason": "",
            "registered": len(set(registered)), "defined": len(classes),
            "missing": missing, "without_main": without_main}
