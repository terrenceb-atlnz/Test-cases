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
    src = GENERATE.read_text()
    # The selector must compare against a STRING. `[port]` with a SwitchPort object never
    # equals any token from split(), so `row` is always None and every such step is a
    # guaranteed false RED — the defect this example itself shipped (2026-07-28).
    assert "l.split()[:1] == [name]" in src or "l.split()[:1] == [port.name]" in src, \
        "the row selector no longer compares against a string"
    assert "l.split()[:1] == [port])" not in src, \
        "the selector compares a SwitchPort OBJECT to a token — always False"

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


def test_skeleton_init_cannot_use_self_before_assignment():
    """SUPERSEDED APPROACH, kept as the invariant: `self.<dev>` inside init() before the
    assignment block is an AttributeError, and warning against it did not work — the model
    reproduced the crash twice. The fix was structural: the assignments now come FIRST, so
    every spelling in the FILL slot is valid. What must hold is that nothing in init()
    touches `self.` before `self.tb = tb`.
    """
    src = SKELETON.read_text()
    m = re.search(r"def init\(self.*?def configure", src, re.S)
    assert m, "init() not found in the skeleton"
    body = m.group(0)
    first_assign = body.index("self.tb = tb")
    before = body[:first_assign]
    # strip jinja control lines and comments; what remains is rendered code
    for line in before.splitlines():
        code_part = line.split("#", 1)[0]
        if "{%" in line or "{#" in line:
            continue
        assert "self." not in code_part, (
            f"init() touches `self.` before the assignment block: {line.strip()!r}")


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


# --- findings from the fan-out audit (2026-07-28) ---------------------------------------

def test_row_selector_compares_a_string_not_a_port_object():
    """A SwitchPort never equals a token from `split()`, so `[port]` matches nothing and
    `row is None` fires on every run — a GUARANTEED false RED on working hardware. The
    prompt shipped exactly this, because rule 3b binds `port = dev.portA` (an object) while
    rule 4d's example compared `[port]` as though it were a string."""
    class FakePort:                       # stands in for ATSwitch.SwitchPort
        name = "port1.0.1"
        def __eq__(self, other): return self is other
        def __hash__(self): return id(self)

    port = FakePort()
    row = "port1.0.1    Port 1           off         off"
    assert row.split()[:1] != [port], "sanity: an object must not equal a token"
    assert row.split()[:1] == [port.name], "the .name form is what matches"


def test_prompt_documents_switchport_api_without_inventing_methods():
    """`SwitchPort` really has name/ifName/is_up/up/get_mac_addr/set_mac_addr. `.down()`
    and `.speed` belong to `ATTestBox.Eth` — the TESTBOX interface. The prompt claimed them
    for the switch port, and `dev.portA.speed = 1000` does NOT raise: it creates a dead
    attribute and the device is never configured."""
    src = GENERATE.read_text()
    assert "NO `.down()`" in src and "`.speed`" in src, \
        "the prompt no longer warns that .down()/.speed are not SwitchPort methods"
    assert "ATTestBox.Eth" in src, "the real owner of those methods is not named"


def test_every_branch_of_the_row_example_reaches_a_verdict():
    """Rule 4c's whole purpose is catching a silent failure. An example with `if/elif` and
    no `else` writes NO marker in exactly that case, which the framework scores as a pass."""
    src = GENERATE.read_text()
    block_start = src.index("row = next((l for l in output.splitlines()")
    block = src[block_start:block_start + 700]
    assert "else:" in block, "the worked example has no else branch — silent failure = pass"
    # Only inside ```python fences — the prose deliberately NAMES `self.passed(...)` to
    # warn against it, and flagging that is the same mistake the port lint made when it
    # flagged its own advice comment.
    import re as _re
    fences = _re.findall(r"```python\n(.*?)```", src, _re.S)
    for block in fences:
        assert "self.passed(...)" not in block, (
            "a code example writes `self.passed(...)`: `...` is Ellipsis, so the script "
            "lints clean, runs clean, and logs `PASS: Ellipsis` as its evidence")


def test_prompt_corpus_counts_reproduce():
    """Rule 3b says "the counts are why", so a number a reader cannot reproduce discredits
    the whole rule. Two were wrong: literals (125 -> 350, a narrower regex had missed
    embedded ones) and `conf t` (54 -> 69)."""
    import re as _re
    import sqlite3 as _s
    if not DB.exists():
        pytest.skip("ck.db absent")
    try:
        c = _s.connect(f"file:{DB}?mode=ro", uri=True)
        rows = [r[0] for r in c.execute(
            "SELECT source_text FROM scripts WHERE source_text IS NOT NULL")]
    except _s.OperationalError:
        pytest.skip("scripts table absent")
    counts = {
        "bound": sum(len(_re.findall(r"\.port[A-Z]\w*\b", t)) for t in rows),
        "literals": sum(len(_re.findall(
            r"""['"][^'"\n]*\bport\d+\.\d+\.\d+\b[^'"\n]*['"]""", t)) for t in rows),
        "conft": sum(len(_re.findall(r"cmd\(\s*['\"]conf(?:igure)?[ ]?t", t)) for t in rows),
        "mode_cfg": sum(len(_re.findall(r"mode\(\s*'\)#'\s*\)", t)) for t in rows),
    }
    src = GENERATE.read_text()
    for label, n in (("bound", counts["bound"]), ("literals", counts["literals"]),
                     ("conft", counts["conft"]), ("mode_cfg", counts["mode_cfg"])):
        pretty = f"{n:,}"
        assert pretty in src or str(n) in src, (
            f"prompt does not cite the reproducible {label} count ({n}); "
            f"an unverifiable number discredits rule 3b")


def test_skeleton_renders_and_compiles_for_every_step_kind_mix():
    """A whole-matrix render, because the defects found were combination-specific: a
    physical step with no link wording left `dut.portA` unbound, and an empty `verify`
    rendered `self.passed('')` (Jinja `default()` only fires on UNDEFINED, not on '')."""
    import py_compile, tempfile, os, re as _re, sys as _sys
    _sys.path.insert(0, str(REPO / "ask-ck" / "CK-main"))
    _sys.path.insert(0, str(REPO / "ask-ck" / "CK-main" / "CK_server"))
    from routers import pytest_create as pc

    mixes = {
        "verify": [{"n": 1, "action": "a", "verify": "v", "kind": "verify"}],
        "physical-no-link-wording": [
            {"n": 1, "action": "power-cycle the unit", "verify": "boots", "kind": "physical"}],
        "manual": [{"n": 1, "action": "LED", "verify": "green", "kind": "manual"}],
        "setup+verify": [{"n": 1, "action": "cfg", "verify": "", "kind": "setup"},
                         {"n": 2, "action": "a", "verify": "v", "kind": "verify"}],
        "empty-text": [{"n": 1, "action": "", "verify": "", "kind": "verify"}],
        "empty-physical": [{"n": 1, "action": "", "verify": "", "kind": "physical"}],
        "stack-b": [{"n": 1, "action": "check stk_b", "verify": "up", "kind": "verify"}],
    }
    for label, seq in mixes.items():
        sk = pc._render_skeleton("AWPTCM-T1", "t", seq, [], [])
        f = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False)
        f.write(sk); f.close()
        try:
            py_compile.compile(f.name, doraise=True)
        finally:
            os.unlink(f.name)
        assert not _re.search(r"self\.(?:passed|failed)\(\s*''\s*\)", sk), \
            f"{label}: empty verdict reason emits NO log marker, so the step is invisible"
        binds = set(_re.findall(r"^\s*(\w+) = setup\.init_(?:swi|stk)\(", sk, _re.M))
        orphan = set(_re.findall(r"\b(swi_[a-z])\.port", sk)) - binds
        assert not orphan, f"{label}: references unbound device(s) {orphan}"
        # a physical step polls a port, so the portlink slot must exist wherever portA is used
        if "port = dut.portA" in sk:
            assert "setup.init_portlink" in sk, \
                f"{label}: uses dut.portA but init() never binds a port link -> AttributeError"
        # stack variable and lookup key must agree
        for var, key in _re.findall(r"(\w+) = setup\.init_stk\('([^']+)'\)", sk):
            assert var == key, f"{label}: {var} looks up a different stack ({key})"


def test_duplicate_portlink_binding_is_a_lint_error():
    """Each `init_portlink()` ASSIGNS the attribute, so binding the same one twice silently
    discards the first link — the script drives one topology while believing it has two.
    Observed 2026-07-28: `(dut.portA, tb.ethA)` then `(dut.portA, lp.portA)`, losing the
    testbox link with nothing downstream to reveal it."""
    import re as _re
    binds = {}
    code = (
        "        (dut.portA, tb.ethA) = setup.init_portlink(dut, tb, type1='port')\n"
        "        (dut.portA, lp.portA) = setup.init_portlink(dut, lp, type1='port')\n")
    for i, line in enumerate(code.splitlines(), 1):
        if "init_portlink" not in line or line.lstrip().startswith("#"):
            continue
        for m in _re.finditer(r"\b(\w+\.port[A-Za-z]\w*)\b", line.split("=")[0]):
            binds.setdefault(m.group(1), []).append(i)
    dupes = {k: v for k, v in binds.items() if len(v) > 1}
    assert "dut.portA" in dupes, "the duplicate binding is not detected"

    ok = (
        "        (dut.portA, tb.ethA) = setup.init_portlink(dut, tb, type1='port')\n"
        "        (dut.portB, lp.portA) = setup.init_portlink(dut, lp, type1='port')\n")
    binds2 = {}
    for i, line in enumerate(ok.splitlines(), 1):
        for m in _re.finditer(r"\b(\w+\.port[A-Za-z]\w*)\b", line.split("=")[0]):
            binds2.setdefault(m.group(1), []).append(i)
    assert not {k: v for k, v in binds2.items() if len(v) > 1}, "false positive on distinct attrs"


def test_self_assignments_precede_the_portlink_slot():
    """Designed out rather than warned about. The FILL slot used to sit ABOVE the
    `self.<dev> = <dev>` block, so a model that read ahead wrote `self.dut.portA` and
    crashed with AttributeError — twice, despite the slot saying "not self.". Assigning
    first makes BOTH spellings valid and removes the trap."""
    src = SKELETON.read_text()
    m = re.search(r"def init\(self.*?def configure", src, re.S)
    assert m, "init() not found"
    body = m.group(0)
    assign = body.index("self.tb = tb")
    slot = body.find("init_portlink")
    assert slot > assign, (
        "the portlink FILL slot precedes the self.<dev> assignments again — a model that "
        "uses the attribute form there produces an AttributeError at init")
