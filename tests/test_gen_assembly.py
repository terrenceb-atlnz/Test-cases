"""Multi-message reply reassembly — the defect behind the phantom "output ceiling".

Every shape asserted here was taken from a real stored reply in
`CK_server/debug-log/no-session.jsonl`, not invented. The four seam shapes and the
duplicate-class case are each pinned separately, because the old parser failed all of them
in the same silent way: it returned a shorter script and no error.

The stored replies themselves are exercised by `test_recovers_the_five_stored_replies`,
which skips when the debug log is absent so the gate stays green on a clean checkout.
"""
import ast
import json
import os
import re

import pytest

from gen_assembly import (manifest_check, recover_script, split_fenced_parts,
                          split_top_level_units, stitch_parts)

# The regex this module replaced. Kept ONLY so the tests can demonstrate what it lost —
# never import it into production code.
_OLD_RX = re.compile(r"(?:^|\n)(LIBRARY:\s*(\S+)\s*\n)?```(?:python)?\s*\n(.*?)```", re.DOTALL)


def _old_parser(content):
    for _, label, code in _OLD_RX.findall(content):
        if not label:
            return code
    return ""


HEAD = "#!/usr/bin/python3\nimport sys\n\n"
TAIL = "\ndef main():\n    ts.add_testCase(TestCase_1())\n    ts.run(sys.argv)\n"


def _case(n, body="        pass\n"):
    return (f"class TestCase_{n}(TestCase):\n"
            f"    testCaseDesc = 'case {n}'\n\n"
            f"    def main(self):\n{body}\n")


# --------------------------------------------------------------------------- single part

def test_single_part_reply_is_untouched():
    code = HEAD + _case(1) + TAIL
    out = recover_script(f"```python\n{code}```")
    assert out["report"]["parts"] == 1
    assert out["report"]["parses"]
    assert out["report"]["seam_lines_dropped"] == []
    assert "TestCase_1" in out["test_code"]


def test_library_block_is_still_recognised():
    out = recover_script(
        f"```python\n{HEAD}{_case(1)}{TAIL}```\n\nLIBRARY: helpers.py\n```python\ndef helper():\n    return 1\n```")
    assert out["library"]["name"] == "helpers.py"
    assert "def helper" in out["library"]["code"]
    assert "def helper" not in out["test_code"]


def test_no_code_block_returns_none():
    out = recover_script("I cannot produce that script.")
    assert out["test_code"] is None
    assert out["report"]["parses"] is False


# ------------------------------------------------------------------ the four seam shapes

def test_seam_shape_1_fence_reopens_at_line_start_midfunction():
    """Reply 07:00:16: the continuation resumes mid-body. Plain concatenation is right."""
    reply = (f"```python\n{HEAD}class TestCase_1(TestCase):\n    def main(self):\n"
             f"        a = 1\n"
             f"```python\n        b = 2\n{TAIL}```")
    out = recover_script(reply)
    assert out["report"]["parts"] == 2
    assert out["report"]["parses"]
    assert "a = 1" in out["test_code"] and "b = 2" in out["test_code"]


def test_seam_shape_2_fence_glued_to_a_partial_line():
    """Reply 06:47:37 seam 1: the cut landed inside a string literal.

    Keeping the half-written line leaves an unterminated string, so it must be dropped —
    and that is decided by PARSING, not by a rule about newlines.
    """
    reply = (f"```python\n{HEAD}class TestCase_1(TestCase):\n"
             f"    testCaseDesc = 'verify the port transmits frames carrying```python\n"
             f"    def main(self):\n        self.log('ok')\n{TAIL}```")
    out = recover_script(reply)
    assert out["report"]["parts"] == 2
    assert out["report"]["parses"]
    assert len(out["report"]["seam_lines_dropped"]) == 1
    assert "transmits frames carrying" in out["report"]["seam_lines_dropped"][0]


def test_a_complete_line_glued_to_a_fence_is_kept():
    """Regression: the first version deleted it. `CRITICAL = 1```` ``` ````.

    "Chunk does not end on a newline" conflated "cut mid-stream" with "the fence was
    written on the code line". Dropping unconditionally silently deleted real statements —
    including, in a framework script, the `ts = TestSuite(...)` the whole file depends on.
    """
    reply = (f"```python\n{HEAD}CRITICAL = 1```python\n"
             f"{_case(1)}{TAIL}```")
    out = recover_script(reply)
    assert out["report"]["parses"]
    assert "CRITICAL = 1" in out["test_code"], "a complete statement was deleted at the seam"
    assert out["report"]["seam_lines_dropped"] == []


def test_a_partial_comment_at_a_seam_is_kept_because_it_is_harmless():
    """Reply 07:25:59: the cut landed in a comment, which parses either way.

    Preferring the reading that drops nothing means the comment survives.
    """
    reply = (f"```python\n{HEAD}class TestCase_1(TestCase):\n    def main(self):\n"
             f"        self.log('ok')\n        # the system description TLV```python\n"
             f"        self.log('more')\n{TAIL}```")
    out = recover_script(reply)
    assert out["report"]["parses"]
    assert out["report"]["seam_lines_dropped"] == []


def test_seam_shape_3_continuation_reemits_the_partial_line():
    """Reply 07:56:58 (the "D15 regression"): the cut line is restarted from its beginning.

    The old parser kept ZERO classes from this reply.
    """
    partial = "        self.log('interval: {}"
    reply = (f"```python\n{HEAD}class TestCase_1(TestCase):\n    def main(self):\n"
             f"{partial}```python\n{partial}s'.format(n))\n{TAIL}```")
    out = recover_script(reply)
    assert out["report"]["parses"]
    # exactly one copy of the line, and it is the COMPLETE one
    assert out["test_code"].count("self.log('interval:") == 1
    assert "s'.format(n))" in out["test_code"]
    # What we were shipping: the old parser stopped at the continuation's fence, so it kept
    # the half-written line and lost the completion AND the whole tail. (In the real reply
    # the classes sat after the seam, so it kept nothing at all — pinned separately by
    # test_recovers_the_five_stored_replies.)
    old = _old_parser(reply)
    assert old.endswith("self.log('interval: {}")
    assert "ts.run(sys.argv)" not in old


def test_seam_shape_4_clean_close_reopen_with_continuation_header():
    """Reply 06:47:37 part 3: `` ``` `` then `` ```python `` then a `# ---- continuation` line."""
    reply = (f"```python\n{HEAD}{_case(1)}```\n\n"
             f"```python\n# ---- continuation of foo_test.py (part 2)\n{_case(2)}{TAIL}```")
    out = recover_script(reply)
    assert out["report"]["parts"] == 2
    assert out["report"]["parses"]
    assert "continuation of" not in out["test_code"]
    assert "TestCase_1" in out["test_code"] and "TestCase_2" in out["test_code"]
    # the old parser silently dropped every block after the first
    assert "TestCase_2" not in _old_parser(reply)


# ------------------------------------------------------------------- duplicate resolution

def test_partial_class_reemitted_complete_keeps_the_complete_one():
    """Reply 06:47:37 re-emits TestCase_21, which part 1 left half-written."""
    partial = "class TestCase_2(TestCase):\n    def main(self):\n        x = ("
    reply = (f"```python\n{HEAD}{_case(1)}{partial}```python\n{_case(2)}{TAIL}```")
    out = recover_script(reply)
    assert out["report"]["parses"]
    assert out["test_code"].count("class TestCase_2") == 1
    assert "x = (" not in out["test_code"]
    assert [d["unit"] for d in out["report"]["duplicate_units"]] == ["TestCase_2"]
    assert out["report"]["duplicate_units"][0]["kept"] == "later"


def test_duplicate_resolution_preserves_declaration_order():
    reply = (f"```python\n{HEAD}{_case(1)}class TestCase_2(TestCase):\n    def main(self):\n        y = (")
    reply += f"```python\n{_case(2)}{_case(3)}{TAIL}```"
    code = recover_script(reply)["test_code"]
    assert code.index("class TestCase_1") < code.index("class TestCase_2") < code.index("class TestCase_3")


# ------------------------------------------------------------------------- manifest check

def test_manifest_flags_a_registered_but_undefined_case():
    code = HEAD + _case(1) + "\ndef main():\n    ts.add_testCase(TestCase_1())\n    ts.add_testCase(TestCase_9())\n"
    report = manifest_check(code)
    assert report["ok"] is False
    assert report["missing"] == ["TestCase_9"]


def test_manifest_flags_a_case_with_no_main():
    code = (HEAD + "class TestCase_1(TestCase):\n    testCaseDesc = 'x'\n\n    def tear_down(self):\n        pass\n"
            + "\ndef main():\n    ts.add_testCase(TestCase_1())\n")
    report = manifest_check(code)
    assert report["ok"] is False
    assert report["without_main"] == ["TestCase_1"]


def test_manifest_ok_on_a_whole_script():
    assert manifest_check(HEAD + _case(1) + TAIL)["ok"] is True


def test_manifest_reports_unparseable_code():
    report = manifest_check("class Broken(:\n")
    assert report["ok"] is False
    assert "does not parse" in report["reason"]


# ------------------------------------------------------------------------------- helpers

def test_split_top_level_units_ignores_indented_defs():
    units = dict(split_top_level_units(HEAD + _case(1)))
    assert "TestCase_1" in units
    assert "main" not in units          # `def main` is indented inside the class


def test_stitch_drops_nothing_when_the_join_already_parses():
    joined, dropped = stitch_parts(["a = 1\nb = 2", "c = 3\nd = 4"])
    assert dropped == [], "valid code must never be discarded at a seam"
    for stmt in ("a = 1", "b = 2", "c = 3", "d = 4"):
        assert stmt in joined
    assert joined.endswith("d = 4")     # final part is complete, nothing dropped


def test_stitch_drops_only_the_seam_that_needs_it():
    """Three chunks, one genuinely cut mid-string: the other seams keep their lines."""
    chunks = ["import sys\nA = 1", "B = 2\nC = 'unterminated", "D = 3\n"]
    joined, dropped = stitch_parts(chunks)
    assert len(dropped) == 1 and "unterminated" in dropped[0]
    for stmt in ("import sys", "A = 1", "B = 2", "D = 3"):
        assert stmt in joined


def test_split_fenced_parts_captures_trailing_prose():
    parts, prose = split_fenced_parts("```python\nx = 1\n```\n\nEmitted in one block.")
    assert len(parts) == 1
    assert "Emitted in one block." in prose


# ------------------------------------------------- adversarial review regressions (2026-08-03)
#
# An independent reviewer found seven ways the first version of this module could delete
# real code while reporting `parses: True` and a clean manifest — i.e. while the caller's
# `_recovery_failure()` check waved it through. Silent loss is the exact failure this whole
# effort exists to end, so each one is pinned here.

def test_module_level_code_between_classes_survives_duplicate_resolution():
    """S1, the worst of them: `ts = TestSuite(...)` was deleted, and nothing noticed.

    Units used to own everything up to the next class/def, so module-level statements
    belonged to the preceding unit's span. Resolving a duplicate class replaced that whole
    span, taking the statements with it — and in a framework script those statements are
    the TestSuite the file depends on. The result parsed, passed the manifest, and raised
    NameError on the bench.
    """
    part1 = (HEAD + "class TestCase_1(TestCase):\n    def main(self):\n        x = ("
             "\n\nts = TestSuite('261_LLDP')\nPOLL_INTERVAL = 30\n")
    part2 = _case(1) + TAIL
    out = recover_script(f"```python\n{part1}```python\n{part2}```")
    assert out["report"]["parses"]
    assert "ts = TestSuite('261_LLDP')" in out["test_code"], \
        "module-level code was deleted along with a duplicate class span"
    assert "POLL_INTERVAL = 30" in out["test_code"]


def test_duplicate_resolution_prefers_the_richer_definition_not_the_longer_one():
    """S2: a re-emitted class with a longer description but fewer steps is LESS complete."""
    complete = ("class TestCase_1(TestCase):\n    def main(self):\n"
                "        self.step_one()\n        self.verify_traffic()\n        self.cleanup()\n")
    longer_but_thinner = (
        "class TestCase_1(TestCase):\n"
        "    testCaseDesc = 'a very much longer description that pads the character count "
        "well beyond the complete definition without adding any executable behaviour'\n"
        "    testCaseId = 'T-1'\n    def main(self):\n        self.step_one()\n")
    assert len(longer_but_thinner) > len(complete)
    out = recover_script(f"```python\n{HEAD}{complete}```python\n{longer_but_thinner}{TAIL}```")
    assert "self.verify_traffic()" in out["test_code"], \
        "character count picked the thinner definition and deleted two steps"
    assert out["report"]["duplicate_units"][0]["kept"] == "earlier"


def test_a_block_after_the_runner_is_commentary_not_a_continuation():
    """S3: a "to run it locally:" block was concatenated and executed on import."""
    reply = (f"```python\n{HEAD}{_case(1)}{TAIL}```\n\nTo run it locally:\n\n"
             f"```python\nimport foo_test\nfoo_test.main()\n```")
    out = recover_script(reply)
    assert out["report"]["parses"]
    assert "import foo_test" not in out["test_code"]
    assert out["report"]["blocks_after_runner"] == 1


def test_library_label_survives_a_blank_line():
    """S4: one blank line demoted the library into the test script."""
    out = recover_script(
        f"```python\n{HEAD}{_case(1)}{TAIL}```\n\nLIBRARY: helpers.py\n\n```python\ndef helper():\n    return 1\n```")
    assert out["library"] is not None, "the LIBRARY label was lost to a blank line"
    assert out["library"]["name"] == "helpers.py"
    assert "def helper" not in out["test_code"]


def test_a_library_split_across_a_seam_is_repaired_as_a_library():
    """S5: the continuation was unlabelled, so half the library leaked into the script."""
    reply = ("LIBRARY: helpers.py\n```python\ndef helper_one():\n    return 1\n"
             "def helper_tw```python\ndef helper_two():\n    return 2\n```")
    out = recover_script(reply)
    assert out["library"] is not None
    assert "def helper_two" in out["library"]["code"], "the library continuation was lost"
    assert out["report"]["library_parses"], "a corrupted library was reported as fine"
    assert not (out["test_code"] or "").strip().startswith("def helper_two")


def test_a_second_library_block_is_reported_rather_than_silently_dropped():
    """S7: only the first library was kept, and the loss went unrecorded."""
    out = recover_script(
        f"```python\n{HEAD}{_case(1)}{TAIL}```\nLIBRARY: a.py\n```python\nA = 1\n```\n"
        f"LIBRARY: b.py\n```python\nB = 2\n```")
    assert out["library"]["name"] == "a.py"
    assert out["report"]["extra_libraries"] == ["b.py"]


def test_crlf_replies_are_assembled_correctly():
    """D4: `closes` saw \\r, so every closing fence read as an opener."""
    reply = f"```python\n{HEAD}{_case(1)}{TAIL}```\n\nDone.".replace("\n", "\r\n")
    out = recover_script(reply)
    assert out["report"]["parses"]
    assert "Done." not in out["test_code"]
    assert "TestCase_1" in out["test_code"]


def test_a_non_python_fence_is_not_treated_as_a_closing_fence():
    """D3: ```` ```bash ```` matched the bare-backtick pattern and its body became code."""
    reply = f"```bash\nssh tb470\n```\n\n```python\n{HEAD}{_case(1)}{TAIL}```"
    out = recover_script(reply)
    assert out["report"]["parses"]
    assert "ssh tb470" not in out["test_code"]


def test_an_indented_markdown_fence_does_not_produce_indented_code():
    """D7: a fence under a list item kept its markdown indent -> IndentationError."""
    body = "\n".join("   " + ln for ln in (HEAD + _case(1) + TAIL).split("\n"))
    out = recover_script(f"1. The script:\n\n   ```python\n{body}\n   ```")
    assert out["report"]["parses"], "markdown indentation leaked into the code"


def test_a_four_backtick_fence_is_handled():
    """D8: the extra backtick became the first character of the code."""
    out = recover_script(f"````python\n{HEAD}{_case(1)}{TAIL}````")
    assert out["report"]["parses"]
    assert not out["test_code"].lstrip().startswith("`")


def test_manifest_reads_registrations_from_the_ast_not_a_regex():
    """A regex for `add_testCase(X())` ignores `add_testCase(X('arg'))` and reports ok."""
    code = (HEAD + _case(1)
            + "\ndef main():\n    ts.add_testCase(TestCase_1('arg'))\n"
              "    ts.add_testCase(TestCase_99('arg'))\n")
    report = manifest_check(code)
    assert report["ok"] is False
    assert report["missing"] == ["TestCase_99"]


def test_a_fence_inside_a_string_literal_is_detected_not_silently_mangled():
    """D1/D2/D6 are NOT recoverable — but they must fail loudly, not ship.

    Fence detection is textual, so a ``` inside a string splits the code. The contract is
    that this ends up with `parses: False`, which makes the caller refuse the script.
    """
    reply = (f"```python\n{HEAD}class TestCase_1(TestCase):\n    def main(self):\n"
             f"        self.log('use ``` to fence')\n{TAIL}```")
    out = recover_script(reply)
    assert out["report"]["parses"] is False, \
        "an unrecoverable reply must be reported as unrecoverable, not shipped"


# ---------------------------------------------------------------- against the real replies

_DEBUG_LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "ask-ck", "CK-main", "CK_server", "debug-log", "no-session.jsonl")

# line index in no-session.jsonl -> (unique classes the model sent, classes the OLD parser kept)
_STORED = {204: (40, 21), 207: (17, 16), 211: (11, 9), 215: (6, 6), 216: (6, 0)}


def _load_stored():
    found = {}
    with open(_DEBUG_LOG, encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if i not in _STORED:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            resp = rec.get("response")
            found[i] = resp if isinstance(resp, str) else json.dumps(resp)
    return found


@pytest.mark.skipif(not os.path.exists(_DEBUG_LOG), reason="debug log not present")
def test_recovers_the_five_stored_replies():
    """The measurement that refutes the ceiling. Recovery must be COMPLETE, not merely better.

    Completeness is judged by the script's own ts.add_testCase(...) manifest, which is
    independent of the parser: every registered case defined, and carrying a main().
    """
    for idx, (sent, old_kept) in _STORED.items():
        content = _load_stored().get(idx)
        if content is None:
            pytest.skip(f"record {idx} not in debug log")
        out = recover_script(content)
        code = out["test_code"]
        assert _old_parser(content).count("class TestCase") == old_kept, \
            f"record {idx}: the old parser's loss is the premise of this fix"
        assert out["report"]["parses"], f"record {idx} did not reassemble into valid Python"
        defined = {n.name for n in ast.parse(code).body if isinstance(n, ast.ClassDef)}
        assert len([d for d in defined if d.startswith("TestCase_")]) == sent, \
            f"record {idx}: expected {sent} unique TestCase classes"
        assert manifest_check(code)["ok"], f"record {idx} failed its own manifest"
        # every stored reply ends in ts.run(sys.argv): nothing was ever truncated
        assert "ts.run(sys.argv)" in code


# ------------------------------------------------ diagnosis, NOT recovery (Phase 7.8)
#
# A fence inside a string literal stays unrecoverable ON PURPOSE. Adding "treat this fence
# as being inside a string" as another candidate reading would enlarge the candidate set
# from readings that differ by one line to readings that differ structurally — and once the
# candidates differ structurally, "it parses" stops being strong evidence and starts being a
# weak filter. That would turn a loud refusal into a possible SILENT wrong assembly, which
# is the failure class this module exists to prevent. Measured frequency of the underlying
# case: zero, across 830 corpus scripts, 1,250 CLI samples and 5 stored generations.

def test_an_unrecoverable_reply_explains_itself():
    from gen_assembly import diagnose_unrecoverable
    reply = (f"```python\n{HEAD}class TestCase_1(TestCase):\n    def main(self):\n"
             f"        self.log('use ``` to fence')\n{TAIL}```")
    out = recover_script(reply)
    assert out["report"]["parses"] is False
    note = diagnose_unrecoverable(reply, out["test_code"] or "")
    assert "does not parse" in note
    assert "string literal or docstring" in note, \
        "the fence-in-a-string signature should be named, not left as a bare SyntaxError"
    assert "regenerate" in note


def test_diagnosis_is_silent_when_the_script_is_fine():
    from gen_assembly import diagnose_unrecoverable
    code = HEAD + _case(1) + TAIL
    assert diagnose_unrecoverable(f"```python\n{code}```", code) == ""


def test_no_string_fence_repair_path_was_added():
    """Guard against the fix we deliberately did not build.

    If a future change starts *recovering* these replies rather than refusing them, this
    fails and the reasoning above has to be re-argued rather than quietly overturned.
    """
    reply = (f"```python\n{HEAD}class TestCase_1(TestCase):\n    def main(self):\n"
             f"        self.log('use ``` to fence')\n{TAIL}```")
    out = recover_script(reply)
    assert out["report"]["parses"] is False, (
        "a fence inside a string literal is now being 'recovered'. That trades a loud "
        "refusal for a possible silent wrong assembly — see the note above.")
