"""Phase 4 — the CLI reference must match what a correctly-written command looks like.

WHAT WAS BROKEN (all measured against the real ck.db, 2026-08-04)
----------------------------------------------------------------
The generate prompt injects a block headed "REAL CLI REFERENCE (AlliedWare Plus —
authoritative; match these formats exactly, do NOT invent output tokens)". Three defects
meant that block routinely contained nothing to match:

 1. COMMAND NAMES LOST THEIR HYPHENS. `cli_commands.command` is derived from the doc-page
    slug, which either drops a hyphen (`lockout-time` -> `lockouttime`) or turns it into an
    underscore that became a space (`2fa-registration` -> `2fa registration`). 768 of 3,297
    distinct names. On the flagship LLDP case the effect was inverted grounding:

        detect_commands('configure lldp tlv-select port-description')  ->  []
        detect_commands('configure lldp tlvselect  port-description')  ->  ['lldp tlvselect']

    Spelling the command the way the CLI spells it found NOTHING.

 2. `detect_commands` ABANDONED A COMMAND whose first occurrence sat inside a longer match,
    so grounding depended on SENTENCE ORDER — `break` where it needed `continue`.

 3. THE HARVESTER'S PROMPT REGEX ONLY KNEW THE HOSTNAME `awplus`, so every page using
    `Node_1(config)#` / `master_1#` / `controller-1(config)#` had its worked examples AND
    the device reply filed as *syntax* (157 rows). Promptless output blocks went the same
    way (735 rows). 607 rows gained real `sample_output` once re-derived.

Measured effect over all 53 refined cases, replayed through the real injection path
(`detect_commands` + `feature_commands` + `prompt_block`):

    zero commands detected      15 -> 10
    commands but NO real output 19 ->  0
    real output/usage present   19 -> 43

THE STANDING RULE THIS FILE PROTECTS
------------------------------------
`cli_lookup`'s own FEATURE_ALIASES header states it: "a wrong alias injects
confidently-wrong grounding, which is worse than none". A syntax TEMPLATE misread as device
output would hand the model a fabricated output format and tell it to match exactly — the
precise failure Phase 4 exists to stop. So several tests below assert the classifier
REFUSES rather than guesses, and none of them should be relaxed to raise recall.

ck.db is read-only here (`mode=ro`), and nothing in this file writes it.
"""
import json
import sqlite3
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_TOOL = _REPO / "tool"
_DB = _REPO / "ask-ck" / "var" / "ck.db"
sys.path.insert(0, str(_TOOL))

import cli_lookup as C            # noqa: E402
import harvest_cli_docs as H      # noqa: E402

pytestmark = pytest.mark.skipif(not _DB.exists(), reason="ck.db absent")


@pytest.fixture(scope="module")
def conn():
    return sqlite3.connect(f"file:{_DB}?mode=ro", uri=True)


# ---------------------------------------------------------------------------
# 4.1 — de-hyphenation
# ---------------------------------------------------------------------------

def test_norm_cmd_collapses_hyphens_spaces_underscores():
    assert C.norm_cmd("lldp tlv-select") == C.norm_cmd("lldp tlvselect")
    assert C.norm_cmd("lockout-time") == C.norm_cmd("lockout time") == "lockouttime"


def test_real_command_name_takes_the_shortest_prefix():
    """`atmf area` must not absorb `<area-name>` from a longer syntax line."""
    got = C.real_command_name("atmf area", ["atmf area <area-name> id <1-4094> [local]"])
    assert got == "atmf area"


def test_real_command_name_stops_at_a_placeholder():
    """A command name can never be assembled out of argument syntax."""
    assert C.real_command_name("speed auto", ["speed {10|100} auto"]) is None


def test_real_command_name_recovers_the_hyphen():
    got = C.real_command_name(
        "aaa local authentication attempts lockouttime",
        ["aaa local authentication attempts lockout-time <lockout-time>"])
    assert got == "aaa local authentication attempts lockout-time"


def test_real_command_name_returns_none_when_nothing_matches():
    assert C.real_command_name("show interface", ["completely unrelated syntax"]) is None


def test_correctly_spelled_command_resolves(conn):
    """THE FLAGSHIP DEFECT: writing the command properly used to find nothing."""
    assert C.resolve_command("lldp tlv-select", conn) == ["lldp tlvselect"]
    assert C.resolve_command("show spanning-tree", conn) == ["show spanningtree"]


def test_display_name_is_the_hyphenated_spelling(conn):
    assert C.display_name("lldp tlvselect", conn) == "lldp tlv-select"
    assert C.display_name("show spanningtree", conn) == "show spanning-tree"


def test_display_name_falls_back_to_stored(conn):
    """Always safe to render, even for a name with nothing better recoverable."""
    assert C.display_name("no-such-command-anywhere", conn) == "no-such-command-anywhere"


def test_lookup_accepts_either_spelling(conn):
    hyph = C.lookup("lldp tlv-select", conn=conn)
    slug = C.lookup("lldp tlvselect", conn=conn)
    assert hyph and len(hyph) == len(slug)


def test_detect_finds_the_correct_spelling(conn):
    correct = C.detect_commands("configure lldp tlv-select port-description", conn=conn)
    assert "lldp tlvselect" in correct, "the hyphenated form still does not match"


def test_prompt_block_heads_with_the_correct_spelling(conn):
    """"Match these formats exactly" must not sit above a misspelled heading."""
    block = C.prompt_block(["lldp tlv-select"], conn=conn)
    assert "### lldp tlv-select" in block
    assert "### lldp tlvselect" not in block


# ---------------------------------------------------------------------------
# 4.2 — order dependence
# ---------------------------------------------------------------------------

def test_shorter_command_survives_a_shadowed_first_occurrence(conn):
    """`break` -> `continue`. The first `show interface` sits inside `show interface
    status`; a later standalone one must still be found."""
    text = ("first show interface status is checked and then "
            "show interface is run on its own")
    hits = C.detect_commands(text, conn=conn)
    assert "show interface status" in hits
    assert "show interface" in hits, "the shadowed command was abandoned entirely"


def test_longest_match_still_wins_when_it_is_the_only_occurrence(conn):
    """The 4.2 fix must not undo the span logic: one mention of the long form must not
    also drag in the generic one."""
    hits = C.detect_commands("run show interface status once", conn=conn)
    assert "show interface status" in hits
    assert "show interface" not in hits


# ---------------------------------------------------------------------------
# 4.3 — negated, abbreviated, and unrecognised
# ---------------------------------------------------------------------------

def test_negated_form_resolves(conn):
    res = C.check_commands(["no lldp tlv-select all"], conn)
    assert res["known"].get("no lldp tlv-select all") == "lldp tlvselect"


def test_arguments_are_stripped_to_reach_the_command(conn):
    res = C.check_commands(["show spanning-tree interface port1.0.3"], conn)
    assert res["known"].get("show spanning-tree interface port1.0.3") == "show spanningtree"


def test_unique_abbreviation_expands(conn):
    assert C._expand_abbreviation("sh int", conn) == "show interface"


def test_ambiguous_abbreviation_is_refused(conn):
    """Guessing an expansion injects grounding for a command the script never issues.

    `sh st` really is ambiguous in the harvest — `show stack`, `show startup-config`,
    `show static-channel-group`, `show storm-control` and more all match. It is used here
    INSTEAD of a shorter probe like `s i` on purpose: `s i` is rejected by the >=2-character
    token guard before the ambiguity check ever runs, so the test passed with the refusal
    deleted. Mutation testing caught that (2026-08-04); this probe exercises the branch the
    test claims to be about.
    """
    assert len(_ambiguous_matches("sh st", conn)) > 1, "fixture drifted: no longer ambiguous"
    assert C._expand_abbreviation("sh st", conn) is None


def _ambiguous_matches(probe, conn):
    """Every command an abbreviation could expand to — the fixture check above."""
    toks = probe.split()
    return [stored for stored, cmd_toks in C._command_token_lists(conn)
            if len(cmd_toks) == len(toks)
            and all(ct.lower().startswith(t) for ct, t in zip(cmd_toks, toks))]


def test_short_token_abbreviation_is_also_refused(conn):
    """The >=2-char guard, pinned separately so neither branch can hide the other."""
    assert C._expand_abbreviation("s i", conn) is None


def test_unknown_command_is_reported_not_dropped(conn):
    res = C.check_commands(["frobnicate widget"], conn)
    assert "frobnicate widget" in res["unknown"]
    assert not res["known"]


def test_detect_reports_display_names_and_unrecognised(conn):
    d = C.detect("configure lldp tlv-select port-description", conn=conn)
    assert "lldp tlv-select" in d["display"]
    assert isinstance(d["unrecognised"], list)


# ---------------------------------------------------------------------------
# 4.5 — re-classification
# ---------------------------------------------------------------------------

def test_non_awplus_hostname_is_a_prompt():
    syn, ex, best = C.reclassify([
        "Node_1(config)#int eth1\nNode_1(config-if)#atmf-link\n% Cannot configure eth1."])
    assert ex, "a non-awplus prompt was not recognised as a worked example"
    assert best and "Cannot configure" in best


def test_promptless_multiline_output_is_output():
    block = ("AAA debugging status:\n Authentication debugging is on\n"
             " Accounting debugging is off")
    syn, ex, best = C.reclassify([block])
    assert best == block.rstrip()
    assert syn == []


def test_placeholder_dense_block_stays_syntax():
    """PRECISION GUARD: a syntax template must never be served as device output."""
    tmpl = ("speed {10|100|1000}\nspeed auto [10] [100]\nno speed\n"
            "duplex {auto|full|half}")
    syn, ex, best = C.reclassify([tmpl])
    assert best is None, "a syntax template was misclassified as real output"
    assert syn == [tmpl]


def test_short_block_stays_syntax():
    syn, ex, best = C.reclassify(["duplex {auto|full|half}"])
    assert syn and best is None


def test_reclassify_recovers_output_at_scale(conn):
    """The aggregate: rows that had no sample_output and gain one."""
    gained = 0
    for so, pre in conn.execute(
            "SELECT sample_output, pre_blocks FROM cli_commands WHERE pre_blocks IS NOT NULL"):
        if so:
            continue
        try:
            if C.reclassify(json.loads(pre))[2]:
                gained += 1
        except Exception:
            continue
    assert gained > 400, f"expected hundreds of rows to gain output, got {gained}"


def test_atmf_link_gains_its_output(conn):
    """A concrete non-awplus-hostname row: 0 chars stored, real output recovered."""
    stored = conn.execute(
        "SELECT sample_output FROM cli_commands WHERE command='atmf-link'").fetchone()
    assert not (stored and stored[0]), "fixture drifted: this row now has stored output"
    v = C.lookup("atmf-link", conn=conn)
    assert v and (v[0]["sample_output"] or ""), "output not recovered"


def test_lookup_never_erases_stored_output(conn):
    """Re-derivation must not be able to LOSE what the harvest already found."""
    v = C.lookup("show spanning-tree", conn=conn)
    assert max(len(x["sample_output"] or "") for x in v) >= 2388


# ---------------------------------------------------------------------------
# 4.4 / 4.6 — tables and notes reach the prompt
# ---------------------------------------------------------------------------

def test_notes_are_read_as_an_object_not_a_list(conn):
    """`notes` is a JSON OBJECT. Reading it as a list silently yields [] on all 6,323
    rows, which would have made 4.6 look implemented while shipping nothing."""
    v = C.lookup("speed", conn=conn)
    assert any(isinstance(x["notes"], dict) and x["notes"] for x in v)


def test_legal_value_table_reaches_the_prompt(conn):
    block = C.prompt_block(["speed"], conn=conn)
    assert "legal values:" in block
    assert "fiber SFP" in block or "copper ports" in block


def test_default_and_mode_reach_the_prompt(conn):
    block = C.prompt_block(["speed"], conn=conn)
    assert "default:" in block and "mode:" in block


def test_prose_tables_are_not_dumped_into_the_prompt():
    """A wide/paragraph table is bulk, not signal."""
    prose = [[["Parameter", "Description"],
              ["<x>", "A" * 300]]]
    assert C._value_tables(prose) == []


def test_value_tables_capped_at_two():
    many = [[["a", "b"], ["1", "2"]] for _ in range(6)]
    assert len(C._value_tables(many)) == 2


def test_usage_examples_ground_a_command_with_no_output(conn):
    """`lldp tlv-select` prints nothing (config command) — its 12 worked example lines are
    the ONLY grounding available, and prompt_block used to render neither."""
    block = C.prompt_block(["lldp tlv-select"], conn=conn)
    assert "real usage:" in block
    assert "lldp tlv-select" in block


# ---------------------------------------------------------------------------
# The harvester and the read-time path must agree
# ---------------------------------------------------------------------------

def test_harvester_prompt_regex_matches_the_reader():
    """Two copies of one rule. If they drift, a future harvest re-strands the output."""
    assert H._PROMPT_ANY_RX.pattern == C._PROMPT_ANY_RX.pattern
    assert H._PLACEHOLDER_RX.pattern == C._PLACEHOLDER_RX.pattern


def test_harvester_classify_agrees_with_reclassify():
    blocks = [
        "duplex {auto|full|half}",
        "awplus#show interface\n  Link is UP\n  current duplex full",
        "Node_1(config)#atmf-link\n% Cannot configure eth1.",
        "AAA debugging status:\n Authentication on\n Accounting off",
    ]
    assert H.classify(blocks) == C.reclassify(blocks)


def test_harvester_no_longer_uses_the_awplus_only_regex():
    src = (_TOOL / "harvest_cli_docs.py").read_text()
    assert "_PROMPT_RX.search" not in src, \
        "classify() still gates on the awplus-only prompt regex"


# ---------------------------------------------------------------------------
# The plan's own verification targets
# ---------------------------------------------------------------------------

def test_target_t33277_reaches_spanning_tree_output(conn):
    """Plan: "assert T33277 ('spanning-tree') resolves to show spanningtree's 2,388 chars".

    De-hyphenation alone cannot do this — T33277 names the protocol in PROSE and never
    writes a command — so it also needs the `spanning-tree` FEATURE_ALIASES entry.
    """
    feat_cmds, terms = C.feature_commands(
        "Verify spanning-tree statistics and counters after a topology change")
    assert "show spanningtree" in feat_cmds
    block = C.prompt_block(feat_cmds, conn=conn, feature_terms=terms)
    assert "### show spanning-tree" in block
    assert "real output:" in block


def test_target_t44297_reaches_lldp_tlv_select(conn):
    det = C.detect_commands("configure lldp tlv-select port-description", conn=conn)
    assert "lldp tlvselect" in det
    assert C.display_name("lldp tlvselect", conn) == "lldp tlv-select"


def test_stp_is_deliberately_not_a_prose_alias():
    """Three letters in an acronym-dense corpus is the ambiguous alias the table's own
    header warns against. rstp/mstp/'spanning tree' cover the real mentions."""
    assert "stp" not in C.FEATURE_ALIASES["spanning-tree"]["prose"]


def test_feature_alias_commands_are_real_cli(conn):
    """Slang must be recognised on the way IN and never emitted on the way OUT."""
    for spec in C.FEATURE_ALIASES.values():
        for cmd in spec["commands"]:
            assert C.lookup(cmd, conn=conn), f"{cmd!r} is not a harvested command"
