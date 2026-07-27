"""Tests for the AlliedWare Plus CLI-reference harvest + lookup.

The harvest exists to stop the generator inventing CLI output: every model in the Part 2B
matrix (Opus included) asserted on `speed=1000` / `state=up`, tokens the switch never
prints. Real output is `current duplex full, current speed 1000, current polarity mdix`.

Parsing tests are pure/offline (no network, no DB). The DB-backed lookup tests skip
cleanly when the harvest has not been run, so the gate stays green on a fresh clone.
"""
import json
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tool"))

harvest = pytest.importorskip("harvest_cli_docs")
cli_lookup = pytest.importorskip("cli_lookup")

DB = REPO / "ask-ck" / "var" / "ck.db"


def _has_command(name: str) -> bool:
    """Is this specific command present?

    A partial harvest is common — pages are fetched alphabetically per product, so a run
    in progress has `aaa_cmd` but not yet `swi_cmd`. Gating on row-count alone made these
    tests fail purely because `duplex`/`polarity` had not been reached, which is a false
    alarm, not a regression. Each DB-backed test declares the command it actually needs.
    """
    if not DB.exists():
        return False
    try:
        c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        return c.execute("SELECT COUNT(*) FROM cli_commands WHERE command = ?",
                         (name,)).fetchone()[0] > 0
    except sqlite3.OperationalError:
        return False


def needs(command: str):
    return pytest.mark.skipif(
        not _has_command(command),
        reason=f"{command!r} not harvested yet (run tool/harvest_cli_docs.py --all)")


needs_harvest = needs("show interface")


# --------------------------------------------------------------------------- parsing

# A faithful slice of a real x530 page: syntax block, a config example, and the
# show-interface reply that carries the format the generator kept inventing.
REAL_PAGE = """
<html><body>
<pre class="pre codeblock">show interface [&lt;interface-list&gt;]</pre>
<pre class="pre codeblock">awplus# configure terminal
awplus(config)# interface port1.0.4
awplus(config-if)# duplex full</pre>
<pre class="pre codeblock">awplus#show interface
Interface port1.0.1
  Link is UP, administrative state is UP
  current duplex full, current speed 1000, current polarity mdix
  configured duplex auto, configured speed auto, configured polarity auto</pre>
</body></html>
"""


def test_pre_blocks_extracts_and_unescapes():
    blocks = harvest.pre_blocks(REAL_PAGE)
    assert len(blocks) == 3
    assert blocks[0] == "show interface [<interface-list>]"   # &lt; &gt; unescaped


def test_classify_splits_syntax_examples_and_output():
    syntax, examples, sample = harvest.classify(harvest.pre_blocks(REAL_PAGE))
    assert syntax == ["show interface [<interface-list>]"]
    assert len(examples) == 2
    # the richest switch reply becomes the sample output
    assert "current duplex full, current speed 1000" in sample


def test_sample_output_carries_the_format_models_invented():
    """The regression this whole harvest exists for."""
    _, _, sample = harvest.classify(harvest.pre_blocks(REAL_PAGE))
    assert "current speed 1000" in sample
    assert "speed=1000" not in sample          # the fabricated form must NOT appear
    assert "state=up" not in sample


def test_config_example_is_not_mistaken_for_output():
    _, examples, _ = harvest.classify(harvest.pre_blocks(REAL_PAGE))
    cfg = [e for e in examples if "configure terminal" in e["cmd"]]
    assert len(cfg) == 1
    assert "duplex full" in cfg[0]["output"]   # continuation lines, not a switch reply


def test_command_name_strips_the_two_letter_disambiguator():
    # real filenames: speed_ak.html, duplex_ak.html, show_interface_memory_ad.html
    assert harvest.command_name("swi_cmd/speed_ak.html") == "speed"
    assert harvest.command_name("swi_cmd/duplex_ak.html") == "duplex"
    assert harvest.command_name("int_cmd/show_interface_status.html") == "show interface status"


def test_command_name_keeps_real_trailing_words():
    # 'status' must survive -- only a bare 2-letter suffix is a disambiguator
    assert harvest.command_name("int_cmd/show_interface_brief.html") == "show interface brief"


def test_soft_404_is_detected():
    """The preview site is mid-build and serves HTTP 200 placeholders. Recording those as
    'command exists, no examples' would silently poison the reference."""
    body = ("<html><body><p>Mostly harmless. This part of the site serves files a "
            "pipeline wrote to disk, and the one asked for isn't there — it may have "
            "moved in the latest rebuild.</p></body></html>")
    assert harvest.parse_page("swi_cmd/x_ak.html", body) == "soft404"


def test_page_without_examples_is_distinguished_from_soft_404():
    body = "<html><body><h1>AAA Commands</h1><p>Introduction</p></body></html>"
    assert harvest.parse_page("aaa_cmd/aaa_cmd.html", body) == "no-pre"


def test_parse_page_is_content_addressed():
    a = harvest.parse_page("int_cmd/show_interface.html", REAL_PAGE)
    b = harvest.parse_page("int_cmd/show_interface.html", REAL_PAGE)
    assert a["content_sha"] == b["content_sha"]
    assert len(a["content_sha"]) == 64
    # identical content across families dedupes to one row -- the storage design
    other = harvest.parse_page("int_cmd/show_interface.html",
                               REAL_PAGE.replace("port1.0.1", "port1.0.9"))
    assert other["content_sha"] != a["content_sha"]


# --------------------------------------------------------------------------- lookup


@needs_harvest
def test_show_interface_output_format_is_available():
    res = cli_lookup.lookup("show interface")
    assert res, "show interface not harvested"
    assert any("current speed" in (v["sample_output"] or "") for v in res)


@needs("show interface status")
def test_show_interface_status_is_column_formatted():
    res = cli_lookup.lookup("show interface status")
    assert res
    out = max((v["sample_output"] or "" for v in res), key=len)
    assert "Duplex" in out and "Speed" in out       # column headers, not key=value
    assert "speed=" not in out


@needs("speed")
def test_speed_syntax_lists_real_values():
    res = cli_lookup.lookup("speed")
    assert res
    syn = " ".join(s for v in res for s in v["syntax"])
    assert "1000" in syn and "auto" in syn


@needs("duplex")
def test_duplex_variants_are_recorded_per_product():
    """x530/x220/x550 offer {auto|full|half}; x930/x950 drop `half` because half duplex
    is impossible at >=1 Gig and those ports do not go below it."""
    res = cli_lookup.lookup("duplex")
    syns = {tuple(v["syntax"]) for v in res}
    assert len(syns) >= 2, f"expected per-product duplex variants, got {syns}"
    assert any("half" in " ".join(s) for s in syns)
    assert any("half" not in " ".join(s) for s in syns)


@needs("duplex")
def test_product_filter_returns_only_that_families_variant():
    all_v = cli_lookup.lookup("duplex")
    x930 = cli_lookup.lookup("duplex", product="x930")
    if len(all_v) > 1 and x930:
        assert len(x930) <= len(all_v)
        assert all("x930" in v["products"] for v in x930)


@needs("duplex")
def test_prompt_block_includes_real_output_and_warns_against_inventing():
    block = cli_lookup.prompt_block(["show interface", "speed", "duplex"])
    assert block
    assert "current speed" in block            # the actual grounding
    assert "do NOT invent" in block
    assert "speed=1000" not in block


@needs("polarity")
def test_prompt_block_is_compact_enough_to_inject():
    """The generate prompt is already ~24k chars; grounding must add signal, not bulk."""
    block = cli_lookup.prompt_block(["show interface", "show interface status",
                                     "speed", "duplex", "polarity"])
    assert 0 < len(block) < 6000, f"prompt block too large: {len(block)} chars"


@needs("polarity")
def test_search_finds_commands_by_concept():
    hits = cli_lookup.search("polarity")
    assert any("polarity" in h["command"] for h in hits)


@needs_harvest
def test_missing_command_returns_empty_not_error():
    assert cli_lookup.lookup("no such command at all") == []
