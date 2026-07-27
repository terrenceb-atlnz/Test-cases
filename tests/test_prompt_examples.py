"""The prompts' own code examples must be CORRECT against real harvested CLI output.

Why this exists (2026-07-28). Across one session, five defects in generated scripts were
traced to our own guidance rather than to model weakness:

  * the generate prompt instructed `port = 'port1.0.1'` -> hardcoded ports
  * its worked example tested `row.split()[-2:] == ['off','off']` -> a FALSE RED on real
    hardware (`show ecofriendly` Status legitimately reads `-`, and lags `Configured`)
  * the skeleton's FILL slot showed `self.dut.portA` -> AttributeError at init()
  * the port-hardcode lint flagged its own advice comment
  * (and pt_grade mis-attributed setup-mapped fragments)

The pattern that matters: **where prose and example disagree, the model copies the
EXAMPLE.** Rule 4c said "assert Configured"; the example next to it tested both columns;
the model followed the example. So an example is not documentation — it is the
specification the model actually implements, and it needs testing like code.

These tests execute the prompts' examples against the real `Configured`/`Status` value
pairs harvested into `ck.db`, so a wrong example fails HERE — before any LLM call, in
milliseconds, with no tokens spent. Offline: no network, no LLM, no hardware.
"""
import json
import pathlib
import re
import sqlite3

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
TPL = REPO / "ask-ck" / "CK-main" / "CK_server" / "templates"
GENERATE = TPL / "prompts" / "pt_generate_script.jinja"
EXTRACT = TPL / "prompts" / "pt_extract_sequence.jinja"
SKELETON = TPL / "pt_script_template.py.jinja"
DB = REPO / "ask-ck" / "var" / "ck.db"


def _sample_rows(command: str, prefix: str = "port"):
    """Real per-port rows for `command` from the harvested reference."""
    if not DB.exists():
        return []
    try:
        c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        outs = [r[0] for r in c.execute(
            "SELECT sample_output FROM cli_commands WHERE command=? "
            "AND sample_output IS NOT NULL", (command,))]
    except sqlite3.OperationalError:
        return []
    rows = []
    for o in outs:
        for ln in (o or "").splitlines():
            if ln.strip().startswith(prefix) and len(ln.split()) >= 3:
                rows.append(ln)
    return rows


ECO_ROWS = _sample_rows("show ecofriendly")
needs_eco = pytest.mark.skipif(not ECO_ROWS, reason="show ecofriendly not harvested")


# --- the row-selection example ---------------------------------------------------------

@needs_eco
def test_row_selection_example_picks_exactly_the_right_port():
    """`l.split()[:1] == [port]` — the prompt's row selector.

    Must match the port under test and nothing else. `startswith` was the earlier form and
    matched `port1.0.10` when asked for `port1.0.1`, silently reading the wrong row.
    """
    assert "l.split()[:1] == [port]" in GENERATE.read_text(), \
        "the exact-match row selector is no longer in the prompt"

    rows = ["port1.0.1    Port 1           lpi         lpi",
            "port1.0.10                    off         off",
            "port1.0.2                     lpi         off"]
    port = "port1.0.1"
    picked = [l for l in rows if l.split()[:1] == [port]]
    assert len(picked) == 1 and picked[0] is rows[0]
    # the rejected form would over-match
    assert len([l for l in rows if l.startswith(port)]) == 2, \
        "startswith no longer over-matches; re-check whether the warning is still needed"


# --- the column-assertion example ------------------------------------------------------

@needs_eco
def test_configured_column_example_is_correct_on_every_real_row():
    """The example must read ONE named column, and be right on all real value pairs.

    This is the test that would have caught the false RED. `show ecofriendly` really emits
    `('off','-')` (no peer) and `('lpi','off')` (configured, not yet negotiated); both are
    normal, so a two-column positional check fails after a command that worked.
    """
    pairs = {tuple(l.split()[-2:]) for l in ECO_ROWS}
    assert pairs, "no Configured/Status pairs parsed"
    # every Status value that actually occurs
    statuses = {p[1] for p in pairs}
    assert "-" in statuses or len(statuses) > 1, \
        f"expected varied Status values, got {statuses}"

    for configured, status in pairs:
        # after `ecofriendly lpi` the step asserts Configured == 'lpi'
        enabled_ok = (configured == "lpi")
        # after `no ecofriendly lpi` it asserts Configured == 'off'
        disabled_ok = (configured == "off")
        assert enabled_ok != disabled_ok or configured not in ("lpi", "off"), \
            f"row ({configured},{status}) is ambiguous"
        # the OLD two-column form must be demonstrably wrong somewhere
    two_col_fails = [p for p in pairs
                     if p[0] == "off" and list(p) != ["off", "off"]]
    assert two_col_fails, (
        "no real row disproves the two-column check — if the harvest changed, re-derive "
        "the rationale in rule 4d before trusting it")


def test_prompt_does_not_demonstrate_a_two_column_positional_check():
    """Guard the EXAMPLE, not just the prose — the model copies the example."""
    src = GENERATE.read_text()
    assert "split()[-2] == 'off'" in src, "example must assert one named column"
    assert "[-2:] == ['off', 'off']" not in src.replace("['off','off']", "['off', 'off']") \
        or "is wrong and fails on real hardware" in src, \
        "a two-column example is present without the warning that it is wrong"


# --- the port-binding examples ---------------------------------------------------------

def test_no_prompt_or_skeleton_seeds_a_literal_port_name():
    """A literal port is wrong on chassis platforms and on a populated-slot x950, and the
    guidance is where the hardcode originated (`port = 'port1.0.1'`)."""
    literal = re.compile(r"""['"][^'"\n]*\bport\d+\.\d+\.\d+\b[^'"\n]*['"]""")
    for f in (GENERATE, EXTRACT, SKELETON):
        src = f.read_text()
        # Strip jinja comment blocks `{# ... #}`: they never render, and the skeleton's
        # editor note deliberately NAMES the historical antipatterns so they stay fixed.
        src = re.sub(r"\{#-?.*?-?#\}", "", src, flags=re.S)
        for i, ln in enumerate(src.splitlines(), 1):
            # prose may NAME the antipattern while explaining it; code examples may not.
            # `port1.0.1 Port 1 lpi lpi` is quoted CLI OUTPUT, not a python literal
            is_sample = re.search(r"`port\d+\.\d+\.\d+ [\w ]+`", ln)
            if literal.search(ln) and not is_sample and not re.search(
                    r"never|not\b|wrong|instead of|antipattern|NOT\b|no longer|SyntaxError", ln):
                pytest.fail(f"{f.name}:{i} seeds a literal port name: {ln.strip()[:90]}")


def test_skeleton_fill_slot_does_not_teach_self_before_assignment():
    """`self.<dev>` in init() before the assignment block is an AttributeError. The FILL
    example previously read as `self.dut.portTB` and the model reproduced the crash."""
    src = SKELETON.read_text()
    m = re.search(r"def init\(self.*?def configure", src, re.S)
    assert m, "init() not found in the skeleton"
    init_src = m.group(0)
    # only the FILL example lines matter; `self.tb = tb` below the block is the fix, not the bug
    example = [l for l in init_src.splitlines()
               if "init_portlink" in l and l.lstrip().startswith("#")]
    assert example, "the portlink FILL example is gone"
    offenders = [l for l in example if "self." in l]
    assert not offenders, f"FILL example uses `self.` before assignment: {offenders}"
    assert "not self." in init_src or "never `self.`" in init_src, \
        "the FILL slot no longer warns against `self.` here"


# --- the substring-vs-scoped-command rule ----------------------------------------------

def test_scoped_show_command_makes_the_skeletons_substring_test_safe():
    """The skeleton's physical-step pattern is `want in output` — the shape rule 4d calls a
    false green. It is safe ONLY because the command is scoped to one port. Pin both halves:
    the scoping in the skeleton, and the CLI syntax that permits it.
    """
    src = SKELETON.read_text()
    assert re.search(r"show interface \{\} status'\.format\(port(\.name)?\)", src), \
        "the physical-step poll is no longer scoped to a single port"
    if DB.exists():
        try:
            c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
            syn = [json.loads(r[0] or "[]") for r in c.execute(
                "SELECT syntax FROM cli_commands WHERE command='show interface status'")]
        except sqlite3.OperationalError:
            syn = []
        if syn:
            flat = " ".join(s for group in syn for s in group)
            assert "port-list" in flat or "interface-list" in flat, (
                "`show interface status` no longer takes a port list — the skeleton's "
                "scoped poll may now read every port, making `want in output` a false green")


def test_connected_is_not_a_substring_of_the_down_state():
    """Opus asserted `'connected' in output` matches a down port. It does not: AW+ prints
    `notconnect` (one word). Pinned because the claim looked plausible and would have sent
    a fix in the wrong direction — and because a two-word form WOULD break it.
    """
    assert "connected" not in "notconnect"
    # if a platform ever prints the two-word form, this is the canary
    assert "connected" in "not connected", "sanity"
    rows = _sample_rows("show interface status", prefix="port") + \
        _sample_rows("show interface status", prefix="eth")
    for ln in rows:
        if re.search(r"not[\s-]connected", ln, re.I):
            pytest.fail(f"a two-word down state exists in real output: {ln.strip()!r} — "
                        f"the skeleton's `want in output` poll is now unsafe")


# --- skeleton: reduced, clarified, and rooted in the corpus -----------------------------

def test_skeleton_uses_the_house_config_mode_idiom():
    """`mode(')#')` is how the corpus enters config mode (4,812 uses); `cmd('conf t')` is
    not (54). A judge called `mode(')#')` "nonsense" precisely because nothing explained
    it — so the idiom must be STATED, with its meaning."""
    gen = GENERATE.read_text()
    assert "mode(')#')" in gen, "the config-mode idiom is not taught"
    assert "conf t" in gen, "the prompt should name the anti-idiom it replaces"
    assert "4,812" in gen or "4812" in gen, "cite the evidence, or the rule reads arbitrary"


def test_skeleton_uses_port_name_for_cli_text():
    """A port object is not its name: `.name` is 1,013 uses vs 241 bare. Being explicit
    removes a coin-flip the model was losing inconsistently across generations."""
    src = SKELETON.read_text()
    assert ".name" in src, "the skeleton no longer shows port.name for CLI text"
    assert "'show interface {} status'.format(port.name)" in src


def test_skeleton_does_not_import_a_module_removed_from_python_3_12():
    """The generated script runs on the TESTBOX's python3 — tb470 is on 3.13.5. The
    skeleton shipped `from distutils.util import strtobool`, valid syntax that compiles
    clean on this seat's 3.10 and is a hard ImportError on the target before any test runs.
    `py_compile` cannot catch a missing module; only an import can.
    """
    src = SKELETON.read_text()
    assert "from distutils" not in src and "import distutils" not in src, \
        "distutils is back — removed in Python 3.12, and the testbox runs 3.13"
    # a comment may still explain WHY it was avoided
    assert "yesNo" in src and "strtobool" not in src.replace(
        "# Hand-rolled rather than distutils.strtobool: that was removed in Python 3.12.", "")


def test_removed_stdlib_imports_are_lint_errors():
    """Generalised beyond distutils: any stdlib module removed in 3.12/3.13."""
    import ast as _ast, sys as _sys
    _sys.path.insert(0, str(REPO / "ask-ck" / "CK-main"))
    _sys.path.insert(0, str(REPO / "ask-ck" / "CK-main" / "CK_server"))
    from routers import pytest_create as pc

    for bad in ("from distutils.util import strtobool", "import telnetlib",
                "import imp", "import cgi"):
        assert pc._removed_stdlib_imports(_ast.parse(bad)), f"not rejected: {bad}"
    for good in ("import sys", "import time", "from framework import ATTestSet",
                 "import shlex", "import re"):
        assert not pc._removed_stdlib_imports(_ast.parse(good)), f"false positive: {good}"


def test_skeleton_does_not_repeat_the_idiom_example_per_step():
    """Reduction with a reason: the 3-line idiom example was emitted once per TestCase —
    14 verbatim copies on T33234, ~49% of each block was comment. It belongs in the prompt
    rules once. Guidance for the MODEL is not documentation for the TEST."""
    src = SKELETON.read_text()
    # the multi-line worked example must live in the prompt, not the per-step body
    assert src.count("dev.cmd('interface {}'.format(dev.portA.name))") <= 1, \
        "the interface-config example is repeated in the skeleton; state it in the rules"
    assert "see rule 1" in src or "rule" in src, \
        "per-step slots should point at the rules rather than restate them"
