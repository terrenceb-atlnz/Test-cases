"""Grounding must cover features named in PROSE, and must not hide the field under test.

Why this exists (2026-07-28): criterion-4 judging flagged "verification that checks link
state but never the feature under test" — `lpi disable` asserting only `Link is UP`, a
false green whenever the disable silently fails. Terrence identified the cause: the whole
`ecomode` CLI command tree was never passed to the prompt. It is called **`ecofriendly`**
in AW+, it was in `ck.db` all along, and TWO independent defects kept it out:

(a) `detect_commands()` matches literal command strings, so "EcoMode" / "LPI" / "EEE" —
    none of which appear inside the command name `ecofriendly lpi` — matched nothing. No
    matcher tuning can bridge that; it needs the alias table.

(b) Worse: `prompt_block()` picked the `show interface` variant with the MOST product
    families, and only 1 of 8 variants prints `current ecofriendly lpi`. So three of the
    four affected steps were grounded on authoritative output with NO EEE field while
    being told "match these formats exactly, do NOT invent output tokens" — grounding that
    steered the model INTO the false green. Same failure mode as the earlier
    `show interface eth1` regression, and the fix for THAT one (prefer most-shared) is
    what caused this one, so the eth1 guard below is load-bearing.

Two terminology facts from Terrence that shaped the fix, recorded so they are not
re-derived wrongly (both were got wrong once already):

  * `ecofriendly` is the PROPER CLI name; "ecomode" is SLANG. So slang is recognised on
    the INPUT side only and never emitted. `lpi` is DEPRECATED terminology (modern
    diagnostics say EEE) but stays first-class here: it is the only spelling the config
    command accepts, it is the live `Configured`/`Status` value in `show ecofriendly`, and
    TestLink cases — several years old, the corpus fragments come from — almost
    unanimously say LPI.
  * The variant printing `current ecofriendly lpi` covers x8100/x908gen2/x908gen3 and uses
    `port1.1.x`. Both traits track CHASSIS vs standalone, **not** firmware age: x908gen3 is
    current (x8100 is the old one), and an x950 with a populated card slot also uses
    `port1.1.x`. So port naming is a RUNTIME hardware property — which is why the fix for
    it is "take the port from the .setup topology", not "guess from the platform".

Offline: reads the committed `ck.db`, no network and no LLM. Skips cleanly when the CLI
harvest is absent.
"""
import sys
import sqlite3
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tool"))

cli_lookup = pytest.importorskip("cli_lookup")
DB = REPO / "ask-ck" / "var" / "ck.db"


def _has(command: str) -> bool:
    if not DB.exists():
        return False
    try:
        c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        return c.execute("SELECT COUNT(*) FROM cli_commands WHERE command = ?",
                         (command,)).fetchone()[0] > 0
    except sqlite3.OperationalError:
        return False


needs_eco = pytest.mark.skipif(not _has("show ecofriendly"),
                               reason="`show ecofriendly` not harvested yet")
needs_showif = pytest.mark.skipif(not _has("show interface"),
                                  reason="`show interface` not harvested yet")


# --- (a) the alias layer --------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "Enable EcoMode on the port.",
    "Disable EcoMode on the port.",
    "lpi disable on <port>. LPI is disabled and link remains stable.",
    "lpi enable on <port>.",
    "Verify Energy Efficient Ethernet is active",
    "confirm EEE negotiation completes",
    "check 802.3az low power idle state",
])
def test_prose_feature_names_resolve_to_the_command_tree(text):
    """The four real T33233/T33234 step texts, plus the other spellings in the wild."""
    cmds, terms = cli_lookup.feature_commands(text)
    assert "show ecofriendly" in cmds, f"no ecofriendly grounding for {text!r}"
    assert "ecofriendly lpi" in cmds
    assert terms, "output terms are what steer variant selection"


def test_the_lexical_matcher_alone_misses_them():
    """Pins the premise: this is why the alias table is needed, not matcher tuning."""
    assert cli_lookup.detect_commands("Enable EcoMode on the port.") == []
    assert cli_lookup.detect_commands("lpi disable on <port>.") == []


@pytest.mark.parametrize("text", [
    "Verify IEEE 802.3 frame format",          # 'eee' inside 'IEEE'
    "Run `show interface status` and confirm link is connected",
    "Configure speed and duplex to auto",
    "check the seee typo does not fire",
])
def test_unrelated_text_does_not_pull_in_ecofriendly(text):
    """A wrong alias injects confidently-wrong grounding — worse than none."""
    cmds, terms = cli_lookup.feature_commands(text)
    assert cmds == [] and terms == []


# --- (b) variant relevance ------------------------------------------------------------

@needs_showif
def test_show_interface_does_report_lpi_on_some_families():
    """The fact the fix rests on. `show interface` was assumed not to report EEE at all
    (Opus's judge rationale said so too); it does — on the chassis variant, which is why
    relevance ranking has something to find."""
    variants = cli_lookup.lookup("show interface", None)
    with_lpi = [v for v in variants
                if "ecofriendly lpi" in (v["sample_output"] or "").lower()]
    assert with_lpi, "no show interface variant reports LPI; re-read the fix rationale"
    assert len(with_lpi) < len(variants), "expected LPI to be family-specific"


@needs_showif
def test_lpi_variant_is_chosen_when_the_step_is_about_lpi():
    """The defect: breadth alone shipped the variant that OMITS the field under test."""
    _, terms = cli_lookup.feature_commands("Disable EcoMode on the port.")
    block = cli_lookup.prompt_block(["show interface"], None,
                                    max_output_lines=14, feature_terms=terms)
    assert "ecofriendly lpi" in block, (
        "show interface was grounded WITHOUT the LPI field on an LPI step — the model is "
        "told to match the reference exactly, so this steers it to link-state-only")


@needs_showif
def test_eth1_regression_stays_fixed():
    """LOAD-BEARING. The previous fix (prefer most-shared) is what caused this defect;
    a naive relevance tie-break would resurrect `show interface eth1` on switch tests."""
    block = cli_lookup.prompt_block(["show interface"], None, max_output_lines=8)
    assert "eth1" not in block
    assert "port1.0" in block or "port1.1" in block


@needs_showif
def test_unrelated_feature_terms_do_not_change_selection():
    """Degrades exactly to previous behaviour when relevance says nothing."""
    base = cli_lookup.prompt_block(["show interface"], None, max_output_lines=8)
    with_noise = cli_lookup.prompt_block(["show interface"], None, max_output_lines=8,
                                         feature_terms=["nonexistentfeature"])
    assert base == with_noise


@needs_eco
def test_relevance_is_graded_not_boolean():
    """`show ecofriendly` has a 10-family variant whose ports are ALL `off` — it mentions
    the feature while demonstrating none of it. Prefer output that exercises the field."""
    _, terms = cli_lookup.feature_commands("lpi disable on port1.0.1")
    block = cli_lookup.prompt_block(["show ecofriendly"], None,
                                    max_output_lines=20, feature_terms=terms)
    assert "Configured" in block and "Status" in block, "the proving columns are missing"
    assert "lpi" in block.lower(), "chose the all-`off` variant; it demonstrates nothing"


@needs_showif
def test_feature_lines_survive_a_tight_output_budget():
    """`current ecofriendly lpi` sits ~line 10, so a small budget could trim away the very
    field relevance-selection just chose — leaving output that looks like proof the field
    does not exist."""
    _, terms = cli_lookup.feature_commands("Disable EcoMode on the port.")
    block = cli_lookup.prompt_block(["show interface"], None,
                                    max_output_lines=4, feature_terms=terms)
    assert "ecofriendly lpi" in block


@needs_showif
def test_family_specific_field_is_flagged():
    """A model told to match formats exactly should know the field is not universal."""
    _, terms = cli_lookup.feature_commands("Disable EcoMode on the port.")
    block = cli_lookup.prompt_block(["show interface"], None,
                                    max_output_lines=14, feature_terms=terms)
    assert "family-specific" in block


# --- end-to-end through the server helper ---------------------------------------------

@needs_eco
def test_server_grounding_block_covers_the_real_steps():
    """Both call sites (step 2 and step 6) route through `_cli_reference_for_text`."""
    sys.path.insert(0, str(REPO / "ask-ck" / "CK-main"))
    sys.path.insert(0, str(REPO / "ask-ck" / "CK-main" / "CK_server"))
    from routers import pytest_create as pc

    sequence = [
        {"action": "Enable EcoMode on the port.",
         "verify": "Run `show interface` to confirm EcoMode is active and link remains "
                   "`connected` with stable negotiated parameters."},
        {"action": "lpi disable on <port>.",
         "verify": "LPI is disabled and link remains stable."},
    ]
    block = pc._cli_reference_block(sequence, [])
    assert "show ecofriendly" in block, "the feature's own show command never reached the prompt"
    assert "ecofriendly lpi" in block, "the config command never reached the prompt"
    assert "Configured" in block, "the columns that prove LPI state are absent"
    assert "current ecofriendly lpi" in block, "show interface shipped without the LPI field"


def test_prompts_require_asserting_on_the_feature():
    """The prompt rules are the other half: with the reference present, the model must be
    told to assert on the feature rather than on link survival."""
    tpl = REPO / "ask-ck" / "CK-main" / "CK_server" / "templates" / "prompts"
    extract = (tpl / "pt_extract_sequence.jinja").read_text()
    generate = (tpl / "pt_generate_script.jinja").read_text()
    for name, src in (("extract", extract), ("generate", generate)):
        assert "show ecofriendly" in src, f"{name} prompt lost the worked example"
        low = src.lower()
        assert "silently fail" in low, f"{name} prompt lost the false-green rationale"


# --- port names must come from the .setup topology -------------------------------------

def test_port_hardcode_lint_matches_real_literals_only():
    """A literal port name is wrong on chassis platforms and on a populated-slot x950.

    The FIRST index of an AW+ port name is the chassis/slot, so `'port1.0.1'` is not a
    safe default — x8100/x908gen2/x908gen3 use `port1.1.x`, and so does an x950 once its
    card slot is populated (a RUNTIME property, not a per-model one). Ports must come from
    the .setup topology via the attribute `init_portlink()` binds; the corpus does this
    10,578 times vs 125 literals.

    Warning-not-error is deliberate: `invalidIfRangeList.append('port1.0.1')` is a
    legitimate literal feeding a negative test.
    """
    import re
    rx = re.compile(r"""['"][^'"\n]*\bport\d+\.\d+\.\d+\b[^'"\n]*['"]""")

    def warns(line: str) -> bool:
        """Mirror of the lint's per-line logic (comment-aware)."""
        if line.lstrip().startswith("#"):
            return False
        for m in rx.finditer(line):
            if "#" in line[:m.start()]:
                continue                      # match sits in a trailing comment
            return True
        return False

    should_warn = ["invalidIfRangeList.append('port1.0.1')",
                   "dut.cmd('interface port1.1.3')",
                   'port = "port1.0.24"',
                   "msg = 'use port1.0.1 # not this'"]   # '#' inside a string
    should_not = ["port = self.testSet.dut.portA.name",
                  "dut.cmd('interface {}'.format(port))",
                  "dut.cmd('show interface {} status'.format(portA))",
                  "# port1.0.1 in a comment is not a literal",
                  # prose ABOUT hardcoding is not a hardcode — the first cut of this check
                  # flagged the skeleton's own guidance comment, warning against its advice
                  "        # a hardcoded 'port1.0.1' is wrong on chassis platforms",
                  "port = dut.portA  # not 'port1.0.1'"]
    for s in should_warn:
        assert warns(s), f"missed a hardcoded port: {s}"
    for s in should_not:
        assert not warns(s), f"false positive on: {s}"


def test_skeleton_and_prompt_do_not_teach_hardcoded_ports():
    """Both used to INSTRUCT the literal: the skeleton slot said `port = 'portX.Y.Z'` and
    the prompt said "a string variable (`port = 'port1.0.1'`)". That is where the
    hardcode came from, so the guidance itself has to be right."""
    tpl = REPO / "ask-ck" / "CK-main" / "CK_server" / "templates"
    skeleton = (tpl / "pt_script_template.py.jinja").read_text()
    generate = (tpl / "prompts" / "pt_generate_script.jinja").read_text()
    assert "'portX.Y.Z'" not in skeleton, "skeleton still seeds a literal port name"
    assert "port = dut.portA" in skeleton, "skeleton should bind from the topology"
    assert "port = 'port1.0.1'" not in generate, "prompt still instructs a literal"
    assert "NEVER HARDCODE A PORT NAME" in generate
    # the chassis rationale must survive, since it is the reason the rule exists
    assert "x908gen3" in generate and "x950" in generate


# --- hardware-agnostic topology binding ------------------------------------------------

def test_setup_lookup_key_is_separate_from_the_role_variable():
    """Two layers, and conflating them broke the first generated scripts (2026-07-28).

    Real ART code does `dutA = setup.init_swi('swi_a')` — the VARIABLE carries the role,
    the STRING is the .setup `[switch]` key. The generator emitted `init_swi('dut')`, which
    simply fails against any real .setup (tb470 declares swi_a/swi_c/swi_d). The convention
    is swi_a/swi_b/... — 621 of ~650 corpus `init_swi()` calls.
    """
    sys.path.insert(0, str(REPO / "ask-ck" / "CK-main"))
    sys.path.insert(0, str(REPO / "ask-ck" / "CK-main" / "CK_server"))
    from routers import pytest_create as pc

    assert pc._setup_keys_for(["dut", "lp"]) == ["swi_a", "swi_b"]
    # a name that already looks like a .setup key is passed through untouched
    assert pc._setup_keys_for(["swi_a", "swi_c"]) == ["swi_a", "swi_c"]
    # mixed: real keys preserved, roles allocated around them without collision
    got = pc._setup_keys_for(["dutA", "swi_c", "swiSrc"])
    assert got[1] == "swi_c" and len(set(got)) == len(got), got


def test_skeleton_binds_devices_and_never_names_a_port():
    """The point of `.setup`: the script is HARDWARE-AGNOSTIC and runs unchanged on any
    platform, because [portlink] supplies the port names at runtime. That is also why the
    same code works on a chassis (port1.1.x) and a standalone switch (port1.0.x)."""
    sys.path.insert(0, str(REPO / "ask-ck" / "CK-main"))
    sys.path.insert(0, str(REPO / "ask-ck" / "CK-main" / "CK_server"))
    from routers import pytest_create as pc
    import re

    seq = [{"n": 1, "action": "Enable ecofriendly lpi on the port",
            "verify": "show ecofriendly shows lpi", "kind": "verify"}]
    sk = pc._render_skeleton("AWPTCM-T99999", "probe", seq, [], [])

    # lookups use .setup keys, not role names
    assert "init_swi('swi_a')" in sk
    assert "init_swi('dut')" not in sk and "init_swi('lp')" not in sk
    # and no literal port name is seeded anywhere
    assert not re.search(r"""['"][^'"\n]*\bport\d+\.\d+\.\d+\b[^'"\n]*['"]""", sk), \
        "skeleton seeds a literal port name — it must come from the .setup topology"


def test_skeleton_assigns_self_before_any_attribute_use():
    """A real bug the lint did not catch: the first generated script referenced
    `self.dut.portA` on the init_portlink line BEFORE `self.dut` was assigned three lines
    later — an AttributeError at init. Nothing may touch `self.<dev>` before the
    assignment block."""
    sys.path.insert(0, str(REPO / "ask-ck" / "CK-main"))
    sys.path.insert(0, str(REPO / "ask-ck" / "CK-main" / "CK_server"))
    from routers import pytest_create as pc

    seq = [{"n": 1, "action": "connect the link partner",
            "verify": "link comes up", "kind": "verify"}]
    sk = pc._render_skeleton("AWPTCM-T99999", "probe", seq, [], [])
    lines = sk.splitlines()
    try:
        init_i = next(i for i, l in enumerate(lines) if "def init(self" in l)
        end_i = next(i for i, l in enumerate(lines[init_i + 1:], init_i + 1)
                     if l.strip().startswith("def "))
    except StopIteration:                        # pragma: no cover
        pytest.fail("could not locate init() in the rendered skeleton")

    body = lines[init_i:end_i]
    first_assign = next((i for i, l in enumerate(body) if l.strip().startswith("self.tb =")), None)
    assert first_assign is not None, "init() never assigns self.tb"
    for i, line in enumerate(body[:first_assign]):
        code = line.split("#", 1)[0]
        assert "self." not in code, (
            f"init() uses `self.` before the assignment block (line {i}): {line.strip()!r}")
