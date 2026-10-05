"""ask-ck/tools/zt_wiki.py — a project's wiki pages, read-only, for the Zephyr Templating Tool.

The fixture is the real `api.php?action=parse` answer for the IE520 set (2026-10-05): the project
page `Project:3296 IE520 Software`, its TPS, Test Strategy and (unwritten) Feature Page, and the
Feature Page preload template. Everything is offline: `read_project` takes the `get` it reads
through, and these tests hand it the fixture.
"""
from __future__ import annotations

import collections
import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from _prose import code_lines

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "ask-ck" / "tools" / "zt_wiki.py"
spec = importlib.util.spec_from_file_location("zt_wiki", TOOL)
zw = importlib.util.module_from_spec(spec)
sys.modules["zt_wiki"] = zw
spec.loader.exec_module(zw)  # type: ignore[union-attr]

PAGES = json.loads((Path(__file__).resolve().parent / "fixtures" / "zt_wiki_ie520.json").read_text(encoding="utf-8"))
PROJECT = "Project:3296 IE520 Software"
TPS, STRATEGY = "IE520 Software TPS", "Test:3296 Test Strategy - IE520 Software"
FEATURE = "IE520 Software - Feature Page"


def _wiki(pages=None):
    """A fake api.php over the fixture, and a log of every request."""
    pages = PAGES if pages is None else pages
    seen = []

    def get(params):
        seen.append(dict(params))
        assert params["action"] == "parse"
        d = pages.get(params["page"].replace("_", " "))
        return copy.deepcopy(d) if d else {"error": {"code": "missingtitle", "info": "The page you specified doesn't exist."}}
    return get, seen


def _edit(title, fn):
    pages = copy.deepcopy(PAGES)
    fn(pages[title]["parse"])
    return pages


def test_the_project_page_gives_version_product_number_and_the_three_pages():
    r = zw.read_project(_wiki()[0], "https://wiki.atlnz.lc/awpwiki/index.php/Project:3296_IE520_Software")
    p = r["project"]
    assert (p["version"], p["product"], p["number"]) == ("5.5.6-2", "IE520", "3296")
    assert sorted(p["version_sources"]["5.5.6-2"]) == ["Test Status", "category", "release link"]
    assert {k: (v["title"], v["exists"]) for k, v in r["pages"].items()} == {
        "tps": (TPS, True), "strategy": (STRATEGY, True), "feature": (FEATURE, True)}


def test_tps_11_3_is_738_sid_rows_ranked_M_or_dash_and_dash_is_not_supported():
    sid = zw.read_project(_wiki()[0], PROJECT)["tps"]["sid_features"]
    assert len(sid) == 738
    assert collections.Counter(x["ranking"] for x in sid) == {"M": 605, "-": 133}
    assert sum(x["supported"] for x in sid) == 605                       # D4: a `-` is not supported
    assert sid[0] == {"group": "Application Programmable Interface (API)",
                      "feature": "ACL/QoS statistics (Hit Counter) support on AW+",
                      "ranking": "M", "supported": True, "comment": ""}


def test_tps_11_4_is_260_prd_rows_with_rowspans_carried_and_red_markup_read():
    prd = zw.read_project(_wiki()[0], PROJECT)["tps"]["prd_features"]
    assert len(prd) == 260
    assert collections.Counter(x["supported_raw"] for x in prd) == {"YES": 232, "NO": 28}
    by_spec = {x["specification"]: x for x in prd}
    assert by_spec["Continuous POE (HANP)"]["item"] == "Port" and not by_spec["Continuous POE (HANP)"]["supported"]
    assert by_spec["IGMPv2 / Query Solicitation"]["item"] == "IPv4"   # item rowspan=25, IGMPv2 rowspan=2
    single = by_spec["Dynamic VLAN / Single Dynamic VLAN(Tag)"]          # <span style="color:red">NO</span>
    assert (single["supported_raw"], single["note"]) == ("NO", "Because this feature is not supported in AW+")


def test_sections_are_numbered_and_titled_as_the_wiki_numbers_them():
    for title, d in PAGES.items():
        api = [(s["number"], zw._clean(s["line"])) for s in d["parse"]["sections"]]
        assert [(s["number"], s["title"]) for s in zw.sections(d["parse"]["wikitext"]["*"])] == api, title
    tps = zw.read_project(_wiki()[0], PROJECT)["tps"]
    assert (tps["sid_section"], tps["prd_section"]) == ("11.3", "11.4")


def test_tables_are_found_by_title_not_number():
    def renumber(p):                        # a TPS revision inserts a section before the appendices
        p["wikitext"]["*"] = p["wikitext"]["*"].replace("\n=Appendices=", "\n=New Section=\nx\n=Appendices=", 1)
    tps = zw.read_project(_wiki(_edit(TPS, renumber))[0], PROJECT)["tps"]
    assert (tps["sid_section"], tps["prd_section"]) == ("12.3", "12.4")
    assert len(tps["sid_features"]) == 738 and len(tps["prd_features"]) == 260


def test_the_strategy_target_path_is_read_and_its_disagreement_reported():
    r = zw.read_project(_wiki()[0], PROJECT)
    assert r["strategy"]["target_path"]["parts"] == ["5.5.6-2", "Tomahawk", "IE570"]
    assert r["problems"] == ["the Test Strategy's target path ends 'IE570', not the product 'IE520'"]
    assert any(s["title"] == "Feature Coverage" and "EtherNet/IP" in s["body"] for s in r["strategy"]["sections"])


def test_a_version_disagreement_is_reported():
    def older(p):
        p["wikitext"]["*"] = p["wikitext"]["*"].replace("{{Test Status v2|5.5.6-2|3296}}", "{{Test Status v2|5.5.6-1|3296}}")
    r = zw.read_project(_wiki(_edit(PROJECT, older))[0], PROJECT)
    assert r["project"]["version"] == "5.5.6-2"                          # two sources against one
    assert any("more than one version" in p for p in r["problems"])


def test_the_unwritten_ie520_feature_page_reads_not_written():
    fp = zw.read_project(_wiki()[0], PROJECT)["feature_page"]
    assert (fp["status"], fp["written"], fp["sections"]) == ("not written", [], [])
    assert "What is it?" in fp["unwritten"] and "External links" in fp["unwritten"]   # <includeonly> category


def test_a_written_section_makes_the_feature_page_partly_written():
    def write(p):
        p["wikitext"]["*"] = p["wikitext"]["*"].replace(
            "=== What is it? ===\n", "=== What is it? ===\nThe IE520 is an industrial L3 switch.\n", 1)
    fp = zw.read_project(_wiki(_edit(FEATURE, write))[0], PROJECT)["feature_page"]
    assert (fp["status"], fp["written"]) == ("partly written", ["What is it?"])
    assert any("industrial L3 switch" in s["body"] for s in fp["sections"])


def test_a_page_not_yet_created_is_missing_and_never_fetched():
    def red(p):
        for l in p["links"]:
            if l["*"] == FEATURE:
                del l["exists"]
    get, seen = _wiki(_edit(PROJECT, red))
    r = zw.read_project(get, PROJECT)
    assert r["feature_page"]["status"] == "missing"
    assert f"{FEATURE!r} has not been created yet" in r["problems"]
    assert FEATURE not in [s["page"] for s in seen] and zw.FEATURE_PRELOAD not in [s["page"] for s in seen]


@pytest.mark.parametrize("given", [
    "https://wiki.atlnz.lc/awpwiki/index.php/Project:3296_IE520_Software",
    "https://wiki.atlnz.lc/awpwiki/index.php/Project%3A3296_IE520_Software#Status",
    "https://wiki.atlnz.lc/awpwiki/index.php?title=Project:3296_IE520_Software&action=view",
    "Project:3296_IE520_Software",
    " Project:3296 IE520 Software ",
])
def test_the_url_forms_a_user_might_paste(given):
    assert zw.page_title(given) == PROJECT


def test_a_url_from_another_site_or_a_missing_page_is_refused():
    with pytest.raises(ValueError, match="not a page on"):
        zw.page_title("https://example.com/awpwiki/index.php/Project:3296_IE520_Software")
    with pytest.raises(ValueError, match="no wiki page"):
        zw.read_project(_wiki()[0], "Project:9999 Nothing")


def test_wikitable_expands_rowspan_and_colspan_and_keeps_pipes_inside_links():
    body = """{| class="wikitable"
! rowspan="2" |A !! colspan="2" |B
|-
!b1!!b2
|-
| rowspan="2" |x||[[Page|label]]||{{T|1}}
|-
|y||z
|}"""
    labels, rows = zw.wikitable(body)
    assert labels == ["A", "B / b1", "B / b2"]
    assert rows == [["x", "label", "{{T|1}}"], ["x", "y", "z"]]


def test_it_is_read_only_and_never_touches_ck_db():
    with pytest.raises(ValueError, match="read-only"):
        zw._get({"action": "edit", "title": "X"})
    with pytest.raises(ValueError, match="read-only"):
        zw._get({"action": "parse", "page": "X"}, method="POST")
    get, seen = _wiki()
    zw.read_project(get, PROJECT)
    assert {s["action"] for s in seen} == {"parse"}
    assert not any("sqlite3" in ln for ln in code_lines(TOOL.read_text(encoding="utf-8")))
