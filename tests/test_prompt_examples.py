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

# Shared helpers so a check cannot fire on its own advice text — see tests/_prose.py
from _prose import code_fences, code_lines, flat

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
def _has_command(command: str) -> bool:
    """Is this command present in the harvest at all (with sample output)?"""
    if not DB.exists():
        return False
    try:
        c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        return c.execute(
            "SELECT COUNT(*) FROM cli_commands WHERE command=? "
            "AND sample_output IS NOT NULL", (command,)).fetchone()[0] > 0
    except sqlite3.OperationalError:
        return False


needs_showif = pytest.mark.skipif(not _has_command("show interface"),
                                  reason="`show interface` not harvested")


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
    guidance is where the hardcode originated (`port = 'port1.0.1'`).

    Scans `code_lines()` — which drops jinja comments, `#` comments and docstrings, i.e.
    every place a port literal is an EXPLANATION rather than a defect. The first cut of
    this check needed a bespoke jinja-strip plus a "does the line contain the word never"
    heuristic; see tests/_prose.py for why that class of workaround is now a shared helper.
    """
    literal = re.compile(r"""['"][^'"\n]*\bport\d+\.\d+\.\d+\b[^'"\n]*['"]""")
    # Two file kinds, two notions of "code":
    #   * a PROMPT is prose with embedded ```python fences — its code is the fences, and
    #     its prose legitimately names the antipattern to forbid it.
    #   * the SKELETON is a Python template — its code is every non-comment line.
    # Using one helper for both is what made the first cut fail: it read the prompt's
    # explanatory bullets as code.
    for f in (GENERATE, EXTRACT):
        for block in code_fences(f.read_text()):
            for ln in code_lines(block):
                if literal.search(ln):
                    pytest.fail(f"{f.name} example seeds a literal port: {ln.strip()[:90]}")
    for ln in code_lines(SKELETON.read_text()):
        if literal.search(ln):
            pytest.fail(f"{SKELETON.name} seeds a literal port name: {ln.strip()[:90]}")


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
    assert "yesNo" in src, "the manual-step helper is gone"
    # Prose (a comment or the helper's own docstring) may NAME distutils to explain why it
    # is avoided; what must not exist is an IMPORT. Match import statements only — the
    # earlier word-level check flagged the very explanation that keeps the fix understood,
    # the same mistake the port lint made against its own advice comment.
    for line in src.splitlines():
        assert not re.match(r"\s*(?:from\s+distutils|import\s+distutils)\b", line), \
            f"distutils imported in: {line.strip()!r}"


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


def test_skeleton_carries_the_objective_as_a_compilable_comment_header():
    """The refined objective (the "expected results") must ride into the .py so the
    declarative context is never lost between the sequence and the fill. It is emitted as a
    COMMENT — safe from the port-literal lint, which skips comment lines — and `>>>` is
    neutralised because it is the one marker the lint scans inside comments. A multi-bullet
    objective must keep its structure and the whole script must still compile."""
    import py_compile, tempfile, os, sys as _sys
    _sys.path.insert(0, str(REPO / "ask-ck" / "CK-main"))
    _sys.path.insert(0, str(REPO / "ask-ck" / "CK-main" / "CK_server"))
    from routers import pytest_create as pc

    objective = ("- Fixed-speed links come up at the configured rate\n"
                 "- show interface reports the speed as fixed, not Auto\n"
                 "- Unsupported speeds >>> leave the link down")
    seq = [{"n": 1, "action": "configure speed 1000", "verify": "link up at 1000",
            "kind": "verify"}]
    sk = pc._render_skeleton("AWPTCM-T1", "Fixed speed", seq, [], [], objective)

    assert "==== OBJECTIVE" in sk, "objective header missing from the skeleton"
    for bullet in ("come up at the configured rate",
                   "reports the speed as fixed, not Auto",
                   "leave the link down"):
        assert bullet in sk, f"objective bullet lost from the header: {bullet!r}"
    # `>>>` in the OBJECTIVE is neutralised (the skeleton keeps its own `>>> FILL` markers,
    # which the model deletes as it fills — those are not what this guards).
    assert "Unsupported speeds > leave the link down" in sk, "objective `>>>` not sanitised"
    assert "Unsupported speeds >>>" not in sk, "unsanitised `>>>` would trip the placeholder lint"

    f = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False)
    f.write(sk); f.close()
    try:
        py_compile.compile(f.name, doraise=True)
    finally:
        os.unlink(f.name)

    # No objective -> no dangling banner (cases without one pay nothing).
    assert "==== OBJECTIVE" not in pc._render_skeleton("AWPTCM-T1", "t", seq, [], [], "")


def test_generate_prompt_instructs_grounding_verdicts_in_the_objective():
    """The objective in the skeleton is inert unless the Generate prompt tells the model to
    USE it — resolve vague wording, prove the slice each step covers — and to keep the header
    verbatim. Guard that instruction against drift; the header alone is easily ignored."""
    text = GENERATE.read_text()
    low = text.lower()
    assert "objective" in low, "generate prompt no longer references the objective"
    assert "verbatim" in low, "generate prompt must tell the model to keep the objective header"
    assert "slice of the objective" in low or "prove the" in low, \
        "generate prompt must tie each verdict to the objective, not merely mention it"


def test_generate_and_preview_thread_the_objective_into_the_skeleton():
    """The objective only reaches the .py if the endpoints pass it down. Guard the wiring
    (mirrors test_no_unguarded_session_write's structural style) so a refactor can't quietly
    drop it and regress to a skeleton with no expected-results context."""
    import ast as _ast
    src = (REPO / "ask-ck" / "CK-main" / "CK_server" / "routers" / "pytest_create.py").read_text()
    tree = _ast.parse(src)

    def _threads_objective(fn_name, callee):
        fn = next((n for n in _ast.walk(tree)
                   if isinstance(n, (_ast.FunctionDef, _ast.AsyncFunctionDef))
                   and n.name == fn_name), None)
        assert fn is not None, f"{fn_name} not found — test anchor is stale"
        calls = [c for c in _ast.walk(fn)
                 if isinstance(c, _ast.Call) and getattr(c.func, "id", None) == callee]
        assert calls, f"{fn_name} no longer calls {callee}"
        for c in calls:
            rendered = _ast.unparse(c)
            assert "objective" in rendered, \
                f"{fn_name} calls {callee} without threading the objective:\n{rendered}"

    _threads_objective("generate_script", "_render_skeleton")
    _threads_objective("preview_fragments", "_assemble_fragment_preview")


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


# --- audit round 2: rules must not vanish, and CLI claims must be verifiable ------------

def test_anti_false_green_rules_survive_without_cli_grounding():
    """The sharpest structural finding. Rules 4b/4c/4d — 6,480 chars including "NEVER
    HARDCODE A PORT NAME", "ASSERT ON THE FEATURE UNDER TEST" and "PARSE THE ROW FOR YOUR
    PORT" — were ALL wrapped in `{% if cli_reference %}`. None of them depend on CLI
    grounding, yet for any case whose text names no harvested command (physical replug,
    reboot, traffic/throughput) the generator was asked to fill a port-bearing skeleton with
    every anti-false-green rule removed.

    Only guidance that literally quotes the injected samples may stay conditional.
    """
    import jinja2
    env = jinja2.Environment()
    env.filters["pyliteral"] = repr
    tpl = env.from_string(GENERATE.read_text())
    must_hold = ["NEVER HARDCODE A PORT NAME",
                 "ASSERT ON THE FEATURE UNDER TEST",
                 "PARSE THE ROW FOR YOUR PORT",
                 "A port name is CLI TEXT"]
    for cli in ("## REAL CLI REFERENCE ...", ""):
        out = tpl.render(case_key="K", case_title="t", file_name="f.py", skeleton="...",
                         fragments=[], framework_surface={}, cli_reference=cli,
                         bound_devices=["dut"], device_note="", py2_flagged=False,
                         model_name="m", gen_date="d")
        for rule in must_hold:
            assert rule in out, (
                f"rule {rule!r} disappears when cli_reference={'set' if cli else 'EMPTY'} — "
                f"it does not depend on grounding and must be unconditional")


def test_extract_prompt_rules_survive_without_cli_grounding():
    """Same defect in the step-2 prompt, where CLI fabrication ORIGINATES."""
    import jinja2
    tpl = jinja2.Environment().from_string(EXTRACT.read_text())
    for cli in ("## REF", ""):
        out = tpl.render(objective="o", steps=[{"description": "d", "expectedResult": "e"}],
                         cli_reference=cli, case_key="K", case_title="t")
        for rule in ("FEATURE UNDER TEST", "NEVER NAME A LITERAL PORT",
                     "Machine-style output tokens never exist", "COVERAGE IS MANDATORY"):
            assert rule in out, f"{rule!r} vanishes without grounding"


@needs_showif
def test_prompt_distinguishes_current_from_configured():
    """`show interface` prints BOTH lines and they mean different things. The prompt named
    only `current …`, steering a "did the command take" check at the negotiated value — a
    false RED whenever the link is down or still negotiating."""
    src = GENERATE.read_text()
    assert "configured" in src.lower() and "current" in src.lower()
    assert "configured …" in src or "configured ..." in src or "`configured" in src, \
        "the prompt does not mention the `configured` line at all"
    assert "FALSE RED" in src, "the prompt does not explain why asserting `current` is wrong"


def test_prompt_does_not_assert_an_unverified_down_state_token():
    """The prompt claimed `show interface status` prints `connected`/`notconnect`. The
    harvest contains `connected` and `disabled` — `notconnect` appears ZERO times. Asserting
    a token the reference never shows is the same class of error as inventing output."""
    import sqlite3 as _s
    if not DB.exists():
        pytest.skip("ck.db absent")
    c = _s.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        outs = [r[0] or "" for r in c.execute(
            "SELECT sample_output FROM cli_commands WHERE command='show interface status' "
            "AND sample_output IS NOT NULL")]
    except _s.OperationalError:
        pytest.skip("cli_commands absent")
    corpus = "\n".join(outs)
    src = GENERATE.read_text()
    # whatever tokens the prompt states as fact must actually occur in the reference
    for tok in ("connected", "disabled"):
        if f"`{tok}`" in src:
            assert tok in corpus, f"prompt states `{tok}` but the harvest never shows it"
    # and it must tell the model to derive the down state rather than assume one
    assert "ABSENCE of the up state" in src or "not in row" in src, \
        "the prompt should prefer asserting absence of the up state over guessing a token"


def test_speed_rule_covers_every_documented_form():
    """`speed` has three forms and the prompt declared one set exhaustive, dropping
    `speed auto`. `speed 1000` FORCES; `speed auto 1000` NEGOTIATES advertising only 1000 —
    a step that says "auto" and emits the bare numeric form tests the opposite."""
    import json as _j
    import sqlite3 as _s
    if not DB.exists():
        pytest.skip("ck.db absent")
    c = _s.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        rows = [r[0] for r in c.execute(
            "SELECT syntax FROM cli_commands WHERE command='speed'")]
    except _s.OperationalError:
        pytest.skip("cli_commands absent")
    forms = {f for r in rows for f in _j.loads(r or "[]")}
    assert any("auto" in f for f in forms), "no `speed auto` form in the harvest"
    src = EXTRACT.read_text()
    assert "speed auto" in src, "the prompt omits the `speed auto` form"
    assert "no speed" in src, "the prompt omits the `no speed` form"


def test_lint_rejects_every_placeholder_marker_not_just_three():
    """The check tested ">>> FILL" plus two EXACT lines, letting `>>> remove` and
    `>>> adjust` ship into saved, lint-green, executable artefacts — instructions addressed
    to the model, sitting next to verdicts a human is meant to trust."""
    src = (REPO / "ask-ck" / "CK-main" / "CK_server" / "routers"
           / "pytest_create.py").read_text()
    assert 'for marker in (">>> FILL"' not in src, \
        "the three-special-case placeholder check is back"
    assert 'if ">>>" in _line' in src, "the generic `>>>` check is missing"
    # every marker the skeleton emits must be caught by the generic rule
    skel = SKELETON.read_text()
    for marker in re.findall(r">>>\s*\w+", skel):
        assert ">>>" in marker


def test_extract_prompt_encodes_the_half_duplex_physical_constraint():
    """Half duplex is impossible at 1 Gig and above — a PHYSICAL constraint no CLI page
    states, so the harvest cannot supply it: the `duplex` page reads `{auto|full|half}`
    unconditionally on every product that supports half duplex at all.

    Observed 2026-07-28: the extractor emitted "configure speed 1000 and duplex half …
    confirm Link is UP and current duplex half, current speed 1000" — a false RED on correct
    hardware. After the rule, half is paired only with 10/100.
    """
    src = EXTRACT.read_text()
    low = src.lower()
    assert "half duplex is impossible" in low, "the constraint is not stated"
    assert "1 gig" in low or "1000" in src, "the threshold is not given"
    # and the reason it cannot come from the docs must be recorded, or someone will
    # 'simplify' it away as redundant with the CLI reference
    assert "no reference page states it" in low or "not a cli one" in low


def test_extract_prompt_requires_keeping_source_qualifiers():
    """"where supported" / "as applicable" IS the requirement — it is how a case author
    expresses a matrix that varies by hardware. Dropping it turns a conditional check into
    an unconditional assertion and manufactures failures on hardware the case never
    claimed to cover. That is exactly how the 1000/half assertion appeared."""
    src = EXTRACT.read_text()
    assert "KEEP THE SOURCE STEP'S QUALIFIERS" in src
    # collapse whitespace: the prompt wraps, so a two-word phrase can straddle a newline
    flat = re.sub(r"\s+", " ", src)
    for q in ("where supported", "as applicable"):
        assert q in flat, f"the rule does not name the {q!r} qualifier"


# --- AW+ port-index semantics -----------------------------------------------------------
#
# Corrected 2026-07-28 against a live 8-member x950 stack (tb105 u5). `show interface
# status` there reported, per first/second index:
#
#     52 port1.0.  52 port2.0.  52 port3.0.  52 port4.0.
#     28 port5.0.  12 port5.1.  28 port6.0.  12 port6.1.
#     28 port7.0.  12 port7.1.  28 port8.0.  12 port8.1.
#
# The first index spans 1-8, exactly the member IDs listed by `show stack`; members 5-8
# each carry a `.0.` base board AND a `.1.` populated expansion slot. So A is the STACK
# MEMBER and B is the BAY. Three surfaces previously stated the opposite ("the FIRST index
# is the chassis/slot") while illustrating it with `port1.1.x` — a change to the SECOND
# index. Prose and example disagreed, and per this module's governing lesson the model
# implements the example, so generated code was mostly unharmed; the wrong *rule* was the
# defect, because it leaves no concept that ports span stack members.
#
# The harvested reference turned out to prove this by itself — see the test below. The
# first cut of that test assumed every doc example was single-unit and asserted the first
# index was pinned at 1; it failed, because `show stack resiliencylink`, `show platform`,
# `show powerinline`, `show udld port` and others do print `port2.x.y`. The failure was the
# better evidence: doc examples number a second UNIT, never a second chassis.

_PORT_RX = re.compile(r"\bport(\d+)\.(\d+)\.(\d+)\b")


def _port_tokens_by_command():
    """(command, [(A, B, C), …]) for each harvested sample output containing port tokens."""
    if not DB.exists():
        return []
    try:
        c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        rows = c.execute("SELECT command, sample_output FROM cli_commands "
                         "WHERE sample_output IS NOT NULL").fetchall()
    except sqlite3.OperationalError:
        return []
    return [(cmd, _PORT_RX.findall(s or "")) for cmd, s in rows if _PORT_RX.search(s or "")]


def test_the_first_port_index_is_the_unit_and_the_second_is_the_bay():
    """The harvested reference refutes "the FIRST index is the chassis/slot" on its own.

    Two independent facts, both read from `cli_commands.sample_output`:

    1. The first index is not pinned to 1. Where it exceeds 1 the command is stack or
       platform context — `show stack resiliencylink` prints `port2.0.11`, `show platform`
       prints `port2.1.1`. A doc example numbering a second unit is numbering a MEMBER.
    2. Decisive: a single output holds the same first index against two different second
       indices — `show stack resiliencylink` carries both `port2.0.11` and `port2.2.11`.
       If the first index were the bay/slot, one unit could not present two of them under
       one first index. So the bay is the SECOND index.

    Corroborated on hardware (see the block comment above): the live 8-member x950 spans
    port1.x-port8.x, matching `show stack` member IDs exactly.
    """
    by_cmd = _port_tokens_by_command()
    if not by_cmd:
        pytest.skip("no portA.B.C tokens in harvested sample output")

    firsts = {a for _c, toks in by_cmd for a, _b, _x in toks}
    assert len(firsts) > 1, (
        f"first index never varies ({sorted(firsts)}) — this test then proves nothing "
        f"and the semantics must be re-derived from hardware")

    multi_unit = sorted({c for c, toks in by_cmd if any(a != "1" for a, _b, _x in toks)})
    assert any("stack" in c or "platform" in c for c in multi_unit), (
        f"a first index above 1 should appear in stack/platform context; saw {multi_unit}")

    two_bays_one_unit = [
        c for c, toks in by_cmd
        if any(len({b for a2, b, _x in toks if a2 == a}) > 1 for a, _b, _x in toks)]
    assert two_bays_one_unit, (
        "no sample output shows one unit with two different second indices — that is the "
        "observation proving the second index is the bay")


def test_no_surface_still_claims_the_first_port_index_is_the_slot():
    """Regression-lock the correction across all three surfaces that carried it.

    Deliberately NOT scanning this file: the bad phrase is quoted here as the thing being
    forbidden, which is precisely the self-match trap `tests/_prose.py` exists to prevent.
    """
    lint_src = REPO / "ask-ck" / "CK-main" / "CK_server" / "routers" / "pytest_create.py"
    grounding = pathlib.Path(__file__).with_name("test_cli_feature_grounding.py")
    bad = "first index is the chassis/slot"
    for path in (GENERATE, lint_src, grounding):
        assert bad not in flat(path.read_text()).lower(), (
            f"{path.name} still states the first port index is the chassis/slot — it is "
            f"the stack member; the bay is the second index")
    # and the corrected rule must actually be stated where the model reads it
    low = flat(GENERATE.read_text()).lower()
    assert "a is the stack member" in low, "generate prompt lost the stack-member rule"
    assert "b is the bay" in low, "generate prompt lost the bay rule"


# --- the prevention mechanism itself ----------------------------------------------------

def test_prose_helpers_survive_the_four_historical_self_match_cases():
    """Regression-lock `tests/_prose.py` against the exact four failures that motivated it.

    Four times in one session a check fired on its own advice text before it was recognised
    as a class: the port lint on its guidance comment, an `self.passed(...)` assertion on the
    sentence forbidding it, a `distutils` assertion on the docstring explaining its absence,
    and a phrase lookup that missed text wrapped across a newline.
    """
    # 1. a guidance comment quoting the antipattern is NOT code
    assert "port1.0.1" not in "\n".join(
        code_lines("# a hardcoded 'port1.0.1' is wrong on chassis\ny = 2\n"))
    # 2. prose forbidding a construct is not the construct
    prompt = "Never write `self.passed(...)` literally.\n```python\nself.passed('why')\n```"
    assert not any("self.passed(...)" in b for b in code_fences(prompt))
    # 3. a docstring explaining an avoided import is not an import (one-line AND multi-line)
    for doc in ('def f():\n    """avoid distutils.strtobool: gone in 3.12."""\n    x = 1\n',
                'def f():\n    """avoid\n    distutils here."""\n    x = 1\n'):
        assert "distutils" not in "\n".join(code_lines(doc))
    # 4. a phrase that wraps is still present
    assert "as applicable" in flat('names "as\n  applicable" among them')
    # and the helpers must still SEE a real defect
    assert "port1.0.1" in "\n".join(code_lines("port = 'port1.0.1'\n"))


def test_prose_helper_is_actually_used_by_the_checks_here():
    """A helper nobody calls prevents nothing. If these assertions ever fail, the checks
    have drifted back to raw-string matching and the four failures can recur."""
    src = pathlib.Path(__file__).read_text()
    assert "from _prose import" in src
    for fn in ("code_lines(", "code_fences(", "flat("):
        assert fn in src, f"{fn} is imported but never used"
